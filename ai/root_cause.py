"""
root_cause.py
=============

Root-Cause Analysis (Stage 14).

When the user re-scans a site, the database can already diff two scans into
"fixed / new / still-present" issues plus a score delta (database.ScanDiff).
This module turns that diff into a plain-language explanation of WHAT changed
and WHY, using Google Gemini.

It deliberately does two things before ever calling the AI:
  1. Summarises the diff into a compact, structured text block — including
     useful signals like whether new issues cluster in one URL folder or one
     category. This both feeds the AI good input and lets us show a basic
     answer when no AI is available.
  2. Mirrors ai/ai_assistant.py: is_available() gates the call, and any
     failure (no key, network, bad JSON) degrades to a deterministic fallback
     so the UI always gets a usable result.

The AI never invents data: it only explains the diff it is given.
"""

from __future__ import annotations

import json
import logging
import os
import re
from collections import Counter
from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional
from urllib.parse import urlparse

from dotenv import load_dotenv

from ai.prompts import ROOT_CAUSE_SYSTEM_INSTRUCTION, build_root_cause_prompt

if TYPE_CHECKING:  # avoid a runtime import cycle with database.db
    from database.db import ScanDiff

logger = logging.getLogger(__name__)
load_dotenv()

_API_KEY_ENV = "GEMINI_API_KEY"
_MODEL_ENV = "GEMINI_MODEL"
_DEFAULT_MODEL = "gemini-2.0-flash"


# --- Result shape ---------------------------------------------------------

@dataclass
class RootCauseResult:
    """The structured root-cause answer the UI renders."""
    summary: str
    likely_cause: str
    recommended_action: str
    source: str               # "gemini" | "fallback"
    fallback_reason: str = ""


# --- Availability ---------------------------------------------------------

def is_available() -> bool:
    key = os.environ.get(_API_KEY_ENV, "").strip()
    return bool(key) and key != "your_gemini_api_key_here"


def _model_name() -> str:
    return os.environ.get(_MODEL_ENV, "").strip() or _DEFAULT_MODEL


# --- Diff summarisation (the structured signals) --------------------------

def _url_folder(url: str) -> str:
    """Top-level path folder of a URL, e.g. https://x/blog/p -> '/blog'."""
    path = urlparse(url).path or "/"
    parts = [p for p in path.split("/") if p]
    return f"/{parts[0]}" if parts else "/"


def _top_cluster(issues, key_fn) -> Optional[tuple[str, int, int]]:
    """
    Return (key, count_in_that_key, total) for the most common key, or None.

    Used to detect 'all new issues are under /blog' or 'all in Accessibility'.
    """
    if not issues:
        return None
    counts = Counter(key_fn(i) for i in issues)
    key, count = counts.most_common(1)[0]
    return key, count, len(issues)


def summarize_diff(diff: "ScanDiff") -> str:
    """
    Build the compact, structured text block we hand to the AI (and can show
    as a basic answer). Pure function — no AI, no network.
    """
    lines: list[str] = []
    lines.append(f"Site: {diff.to_scan.root_url}")
    lines.append(f"Score: {diff.from_scan.score} -> {diff.to_scan.score} "
                 f"(change {diff.score_delta:+d})")
    lines.append(f"Fixed issues: {len(diff.fixed_issues)}")
    lines.append(f"New issues: {len(diff.new_issues)}")
    lines.append(f"Still present: {len(diff.unchanged_issues)}")

    # Clustering signals on the NEW issues (the interesting ones).
    folder = _top_cluster(diff.new_issues, lambda i: _url_folder(i.url))
    if folder and folder[1] > 1:
        key, count, total = folder
        lines.append(f"New-issue location: {count}/{total} new issues are under {key}")

    category = _top_cluster(diff.new_issues, lambda i: i.category)
    if category and category[1] > 1:
        key, count, total = category
        lines.append(f"New-issue category: {count}/{total} new issues are {key}")

    sev = _top_cluster(diff.new_issues, lambda i: i.severity)
    if sev and sev[1] > 0:
        key, count, total = sev
        lines.append(f"New-issue severity: most common is {key} ({count}/{total})")

    # A couple of concrete examples so the AI can be specific.
    if diff.new_issues:
        examples = diff.new_issues[:3]
        lines.append("Examples of new issues:")
        for i in examples:
            lines.append(f"  - [{i.severity}/{i.category}] {i.issue_type} @ {i.url}")

    return "\n".join(lines)


# --- Response parsing -----------------------------------------------------

def _extract_json_block(text: str) -> Optional[dict]:
    if not text:
        return None
    fenced = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
    if fenced:
        text = fenced.group(1)
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1 or end < start:
        return None
    try:
        return json.loads(text[start:end + 1])
    except json.JSONDecodeError:
        return None


def _result_from_payload(payload: dict) -> RootCauseResult:
    def _s(key: str) -> str:
        v = payload.get(key, "")
        return v.strip() if isinstance(v, str) else ""
    return RootCauseResult(
        summary=_s("summary") or "(no summary provided)",
        likely_cause=_s("likely_cause") or "(no likely cause provided)",
        recommended_action=_s("recommended_action") or "(no recommendation provided)",
        source="gemini",
    )


# --- Fallback -------------------------------------------------------------

def _fallback(diff: "ScanDiff", reason: str) -> RootCauseResult:
    """Minimal, deterministic answer when AI isn't available."""
    direction = "improved" if diff.score_delta > 0 else (
        "dropped" if diff.score_delta < 0 else "stayed the same")
    return RootCauseResult(
        summary=(
            f"Between the two scans the health score {direction} "
            f"({diff.from_scan.score} → {diff.to_scan.score}). "
            f"{len(diff.new_issues)} new issue(s), {len(diff.fixed_issues)} fixed, "
            f"{len(diff.unchanged_issues)} still present."
        ),
        likely_cause=(
            "AI insight is unavailable, so no automated cause analysis was "
            "produced. Review the 'New issues' list to see what appeared."
        ),
        recommended_action=(
            "Set GEMINI_API_KEY in your .env to get an AI explanation, or "
            "inspect the new issues below for a pattern (same folder, same "
            "category)."
        ),
        source="fallback",
        fallback_reason=reason,
    )


# --- Public API -----------------------------------------------------------

def analyze_diff(diff: "ScanDiff") -> RootCauseResult:
    """
    Explain what changed between two scans. Always returns a RootCauseResult.
    """
    if not is_available():
        return _fallback(diff, reason="no API key configured")

    try:
        import google.generativeai as genai
    except ImportError as exc:
        return _fallback(diff, reason=f"google-generativeai not installed ({exc})")

    try:
        genai.configure(api_key=os.environ[_API_KEY_ENV].strip())
        model = genai.GenerativeModel(
            model_name=_model_name(),
            system_instruction=ROOT_CAUSE_SYSTEM_INSTRUCTION,
        )
        prompt = build_root_cause_prompt(diff_summary=summarize_diff(diff))
        result = model.generate_content(prompt)
        text = (result.text or "").strip()
    except Exception as exc:  # noqa: BLE001
        logger.exception("Root-cause AI call failed")
        return _fallback(diff, reason=f"Gemini API error ({exc})")

    payload = _extract_json_block(text)
    if not payload:
        return _fallback(diff, reason="Gemini returned unparseable response")
    return _result_from_payload(payload)
