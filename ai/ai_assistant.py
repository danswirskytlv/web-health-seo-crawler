"""
ai_assistant.py
===============

The AI Assistant module.

Given an already-detected Issue (from the analyzer) and optional page context,
asks Google Gemini for:
  - a plain-language explanation,
  - why it matters,
  - a concrete fix,
  - a copy-paste code snippet (when applicable).

Important design points:
- The AI does NOT detect issues. It only explains issues already detected
  by the rule-based analyzer. This boundary is what makes the system
  predictable, testable, and defensible to non-technical users.
- The module degrades gracefully:
    * No API key set    -> returns a deterministic fallback response
    * Network failure   -> returns a fallback response
    * Malformed JSON    -> returns a fallback response, logs the error
  In every failure case the UI still gets a usable AIResponse dict,
  so the user never sees a stack trace.
"""

from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import dataclass
from typing import Optional

from bs4 import BeautifulSoup
from dotenv import load_dotenv

from ai.prompts import (
    SYSTEM_INSTRUCTION,
    build_pages_404_prompt,
    build_user_prompt,
)
from models.result_models import Issue, PageResult

logger = logging.getLogger(__name__)

# Load environment variables from .env at import time so that any caller
# (the API, CLI, tests) sees them.
load_dotenv()


# --- Configuration --------------------------------------------------------

_API_KEY_ENV = "GEMINI_API_KEY"
_MODEL_ENV = "GEMINI_MODEL"
_DEFAULT_MODEL = "gemini-2.0-flash"


# --- Response shape -------------------------------------------------------

@dataclass
class AIResponse:
    """
    The structured AI answer the UI renders.

    All fields are strings — never None — so the UI doesn't need defensive
    rendering. Empty string means "this section is intentionally blank"
    (e.g. no code snippet for a slow-response issue).
    """
    simple_explanation: str
    why_it_matters: str
    suggested_fix: str
    code_snippet: str
    source: str         # "gemini" | "fallback" — for UI badges / debugging
    fallback_reason: str = ""  # short, user-friendly reason when source="fallback"

    def to_dict(self) -> dict:
        """Convenience for storing in st.session_state."""
        return {
            "simple_explanation": self.simple_explanation,
            "why_it_matters": self.why_it_matters,
            "suggested_fix": self.suggested_fix,
            "code_snippet": self.code_snippet,
            "source": self.source,
            "fallback_reason": self.fallback_reason,
        }


# --- API availability ----------------------------------------------------

def is_available() -> bool:
    """Return True if a Gemini API key has been configured."""
    key = os.environ.get(_API_KEY_ENV, "").strip()
    # Treat the placeholder value from .env.example as "not configured".
    return bool(key) and key != "your_gemini_api_key_here"


def _model_name() -> str:
    return os.environ.get(_MODEL_ENV, "").strip() or _DEFAULT_MODEL


# --- Page context extraction ---------------------------------------------

def extract_page_context(page: Optional[PageResult]) -> dict[str, str]:
    """
    Pull the current title / h1 / meta description out of a page's HTML.

    These are passed to the AI so it can give context-aware suggestions
    (e.g. "Your current title is empty; try 'Plumbing Services Tel-Aviv'").

    Returns a dict with empty strings for anything we couldn't find.
    """
    out = {"title": "", "h1": "", "meta_description": ""}
    if page is None or not page.html:
        return out

    soup = BeautifulSoup(page.html, "html.parser")

    title_tag = soup.find("title")
    if title_tag:
        out["title"] = title_tag.get_text(strip=True)

    h1_tag = soup.find("h1")
    if h1_tag:
        out["h1"] = h1_tag.get_text(strip=True)

    meta_tag = soup.find("meta", attrs={"name": "description"})
    if meta_tag:
        out["meta_description"] = meta_tag.get("content", "").strip()

    return out


# --- Response parsing ----------------------------------------------------

def _extract_json_block(text: str) -> Optional[dict]:
    """
    Try to extract a JSON object from `text`.

    Gemini sometimes wraps its JSON in ```json ... ``` even when told not to,
    so we tolerate that. We also tolerate leading or trailing prose by
    finding the first `{` and the last `}`.
    """
    if not text:
        return None

    # Strip ```json fences if present.
    fenced = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
    if fenced:
        text = fenced.group(1)

    # Find the outermost JSON object.
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end < start:
        return None

    candidate = text[start:end + 1]
    try:
        return json.loads(candidate)
    except json.JSONDecodeError as exc:
        logger.warning("Could not parse AI JSON: %s\nRaw: %s", exc, candidate[:500])
        return None


def _response_from_payload(payload: dict) -> AIResponse:
    """Build an AIResponse from a parsed JSON payload, with safe defaults."""
    def _str(key: str) -> str:
        v = payload.get(key, "")
        return v.strip() if isinstance(v, str) else ""

    return AIResponse(
        simple_explanation=_str("simple_explanation") or "(no explanation provided)",
        why_it_matters=_str("why_it_matters") or "(no impact analysis provided)",
        suggested_fix=_str("suggested_fix") or "(no fix suggested)",
        code_snippet=_str("code_snippet"),
        source="gemini",
    )


# --- Fallback -------------------------------------------------------------

def _short_reason(reason: str) -> str:
    """Trim a raw error into something the UI can show without flooding the page."""
    # Keep the first line / first ~120 chars so noisy stack traces stay readable.
    one_line = reason.replace("\n", " ").strip()
    if len(one_line) > 140:
        one_line = one_line[:140].rstrip() + "..."
    return one_line


def _fallback_response(issue: Issue, reason: str) -> AIResponse:
    """
    Return a deterministic, useful answer when Gemini isn't available.

    The UI still gets all four fields populated so it can render normally.
    """
    logger.info("Using fallback AI response (%s)", reason)
    short = _short_reason(reason)
    return AIResponse(
        simple_explanation=(
            "The detected issue is described below. "
            "Live AI explanations from Gemini are not available right now, so this "
            "is a built-in suggestion based on the rules in the analyzer."
        ),
        why_it_matters=issue.description,
        suggested_fix=issue.recommendation,
        code_snippet="",
        source="fallback",
        fallback_reason=short,
    )


# --- Public API -----------------------------------------------------------

def generate_ai_fix(
    issue: Issue,
    page: Optional[PageResult] = None,
) -> AIResponse:
    """
    Ask Gemini to explain `issue` and suggest a fix.

    Parameters
    ----------
    issue : Issue
        The detected issue, already classified by the analyzer.
    page : PageResult, optional
        The original page for this URL. Used to extract current title,
        h1 and meta description so the AI can give context-aware
        suggestions. If None, the prompt simply says "(not detected)".

    Returns
    -------
    AIResponse
        Always populated. Caller never needs to handle exceptions.
    """
    if not is_available():
        return _fallback_response(issue, reason="no API key configured")

    # Import lazily so the rest of the app works even if the package isn't
    # installed or fails to initialize.
    try:
        import google.generativeai as genai
    except ImportError as exc:
        return _fallback_response(issue, reason=f"google-generativeai not installed ({exc})")

    api_key = os.environ[_API_KEY_ENV].strip()
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(
            model_name=_model_name(),
            system_instruction=SYSTEM_INSTRUCTION,
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("Failed to initialize Gemini model")
        return _fallback_response(issue, reason=f"could not initialize Gemini ({exc})")

    # The grouped "Pages Returning 404" note carries a list of URLs in
    # issue.details["urls"]. It needs a different prompt — one that analyzes
    # the actual URLs for patterns (e.g. malformed external links) instead of
    # the single-issue/single-page template.
    details = getattr(issue, "details", None) or {}
    urls_404 = details.get("urls") if isinstance(details, dict) else None
    if urls_404:
        prompt = build_pages_404_prompt(root_url=issue.url, urls=urls_404)
    else:
        context = extract_page_context(page)
        prompt = build_user_prompt(
            url=issue.url,
            issue_type=issue.issue_type,
            severity=issue.severity,
            description=issue.description,
            recommendation=issue.recommendation,
            title=context["title"],
            h1=context["h1"],
            meta_description=context["meta_description"],
        )

    try:
        result = model.generate_content(prompt)
        text = (result.text or "").strip()
    except Exception as exc:  # noqa: BLE001
        # Any API failure — quota, network, server error — falls back gracefully.
        logger.exception("Gemini API call failed")
        return _fallback_response(issue, reason=f"Gemini API error ({exc})")

    payload = _extract_json_block(text)
    if not payload:
        logger.warning("Gemini returned unparseable text:\n%s", text[:500])
        return _fallback_response(issue, reason="Gemini returned unparseable response")

    return _response_from_payload(payload)
