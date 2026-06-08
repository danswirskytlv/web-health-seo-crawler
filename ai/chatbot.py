"""
chatbot.py
==========

"Ask Your Site" — the conversational interface (Stage 15).

This is the natural-language front door to everything the tool knows. The user
asks questions in plain English; the assistant answers using the current scan
results and a little recent history as grounding context.

Behaviour (decided with the project owner):
- Answers questions about THIS site's data AND general web-health/SEO
  education, connecting the two where natural.
- Politely declines + redirects anything off-topic (see prompts.py).
- Remembers the whole conversation in the session, so follow-ups work.

Like the other AI modules it mirrors ai/ai_assistant.py:
- is_available() gates the Gemini call.
- Any failure (no key, network, etc.) degrades to a graceful fallback message
  so the chat UI never shows a stack trace.

The actual conversation memory lives in the Streamlit page's session_state;
this module is stateless and is handed the history on each call.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional

from dotenv import load_dotenv

from ai.prompts import (
    CHATBOT_SYSTEM_INSTRUCTION,
    build_chatbot_context_message,
)

if TYPE_CHECKING:  # avoid import cycles; these are only used for typing
    from database.db import ScanSummary
    from models.result_models import ScanResult

logger = logging.getLogger(__name__)
load_dotenv()

_API_KEY_ENV = "GEMINI_API_KEY"
_MODEL_ENV = "GEMINI_MODEL"
_DEFAULT_MODEL = "gemini-2.0-flash"

# How many top issues to include in the context (keeps the prompt compact).
_MAX_CONTEXT_ISSUES = 25


@dataclass
class ChatReply:
    """One assistant reply."""
    text: str
    source: str  # "gemini" | "fallback"


def is_available() -> bool:
    key = os.environ.get(_API_KEY_ENV, "").strip()
    return bool(key) and key != "your_gemini_api_key_here"


def _model_name() -> str:
    return os.environ.get(_MODEL_ENV, "").strip() or _DEFAULT_MODEL


# --- Context building -----------------------------------------------------

def build_context(
    current: Optional["ScanResult"],
    recent: Optional[list["ScanSummary"]] = None,
) -> str:
    """
    Build the compact text block describing the user's site for grounding.

    Includes the current scan's score and a capped, severity-sorted list of
    issues, plus a few recent scans from history so trend questions work.
    Pure function — no AI, no network.
    """
    lines: list[str] = []

    if current is None or current.score is None:
        lines.append("No scan has been run yet in this session.")
    else:
        s = current.score
        lines.append(f"Current scan of {current.root_url}:")
        lines.append(f"  Health score: {s.score}/100 ({s.grade})")
        lines.append(f"  Pages scanned: {current.pages_scanned}")
        lines.append(f"  Issues: {s.high_count} High, {s.medium_count} Medium, "
                     f"{s.low_count} Low")
        if s.category_scores:
            cats = ", ".join(f"{c} {v}/100" for c, v in sorted(s.category_scores.items()))
            lines.append(f"  Category scores: {cats}")

        # Severity-sorted, capped list of concrete issues.
        order = {"High": 0, "Medium": 1, "Low": 2}
        issues = sorted(current.issues, key=lambda i: order.get(i.severity, 9))
        if issues:
            lines.append(f"  Top issues (up to {_MAX_CONTEXT_ISSUES}):")
            for i in issues[:_MAX_CONTEXT_ISSUES]:
                lines.append(f"    - [{i.severity}/{i.category}] {i.issue_type} @ {i.url}")

    if recent:
        lines.append("")
        lines.append("Recent scan history (newest first):")
        for r in recent:
            lines.append(f"  - {r.scanned_at}: score {r.score}/100 "
                         f"({r.issues_count} issues) on {r.root_url}")

    return "\n".join(lines)


# --- Conversation ---------------------------------------------------------

def _to_gemini_history(context: str, history: list[dict]) -> list[dict]:
    """
    Build the message list for Gemini's chat API.

    We prime the conversation with the scan context as a 'user' turn followed
    by a short 'model' acknowledgement, then replay the real conversation.
    `history` items are {"role": "user"|"assistant", "content": str}.
    """
    messages: list[dict] = [
        {"role": "user", "parts": [build_chatbot_context_message(context=context)]},
        {"role": "model", "parts": ["Understood. I'll use this site's data to "
                                    "help with website-health and SEO questions."]},
    ]
    for turn in history:
        role = "model" if turn.get("role") == "assistant" else "user"
        messages.append({"role": role, "parts": [turn.get("content", "")]})
    return messages


def _fallback(reason: str) -> ChatReply:
    return ChatReply(
        text=(
            "AI chat isn't available right now "
            f"({reason}). Set GEMINI_API_KEY in your .env to enable it. In the "
            "meantime, you can review the detected issues on the main page."
        ),
        source="fallback",
    )


def answer(message: str, history: list[dict], context: str) -> ChatReply:
    """
    Produce the assistant's reply to `message`.

    `history` is the prior conversation (excluding the new `message`), each
    item {"role": "user"|"assistant", "content": str}. `context` is the
    grounding block from build_context(). Always returns a ChatReply.
    """
    if not is_available():
        return _fallback("no API key configured")

    try:
        import google.generativeai as genai
    except ImportError as exc:
        return _fallback(f"google-generativeai not installed ({exc})")

    try:
        genai.configure(api_key=os.environ[_API_KEY_ENV].strip())
        model = genai.GenerativeModel(
            model_name=_model_name(),
            system_instruction=CHATBOT_SYSTEM_INSTRUCTION,
        )
        chat = model.start_chat(history=_to_gemini_history(context, history))
        result = chat.send_message(message)
        text = (result.text or "").strip()
    except Exception as exc:  # noqa: BLE001
        logger.exception("Chatbot Gemini call failed")
        return _fallback(f"Gemini API error ({exc})")

    if not text:
        return _fallback("Gemini returned an empty response")
    return ChatReply(text=text, source="gemini")
