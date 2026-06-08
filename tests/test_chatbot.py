"""
Unit tests for ai.chatbot (Stage 15).

Gemini's chat API is mocked, so these run fully offline with no API key.
"""

from __future__ import annotations

import sys
import types as _t

import pytest

import ai.chatbot as chatbot
from ai.chatbot import (
    ChatReply,
    _to_gemini_history,
    answer,
    build_context,
)
from database.db import ScanSummary
from models.result_models import (
    CATEGORY_SECURITY_HEADERS,
    CATEGORY_SEO,
    Issue,
    PageResult,
    ScanResult,
    ScoreResult,
    SEVERITY_HIGH,
    SEVERITY_MEDIUM,
)


def _scan() -> ScanResult:
    issues = [
        Issue(url="https://x.test/a", issue_type="Missing Title", severity=SEVERITY_HIGH,
              category=CATEGORY_SEO, description="d", recommendation="r"),
        Issue(url="https://x.test/b", issue_type="Missing CSP", severity=SEVERITY_MEDIUM,
              category=CATEGORY_SECURITY_HEADERS, description="d", recommendation="r"),
    ]
    return ScanResult(
        root_url="https://x.test",
        pages=[PageResult(url="https://x.test/", status_code=200, response_time=0.1)],
        issues=issues,
        score=ScoreResult(score=72, grade="Needs Improvement", high_count=1,
                          medium_count=1, low_count=0,
                          category_scores={"SEO": 90, "Security Headers": 80}),
    )


def _summary(score, when, sid=1) -> ScanSummary:
    return ScanSummary(id=sid, root_url="https://x.test", scanned_at=when, score=score,
                       grade="Good", pages_count=5, issues_count=2, high_count=1,
                       medium_count=1, low_count=0, avg_response_time=0.3)


# --- Context building -----------------------------------------------------

class TestBuildContext:
    def test_includes_score_and_issues(self):
        ctx = build_context(_scan(), None)
        assert "72/100" in ctx and "Missing Title" in ctx and "Missing CSP" in ctx

    def test_includes_category_scores(self):
        ctx = build_context(_scan(), None)
        assert "SEO 90/100" in ctx and "Security Headers 80/100" in ctx

    def test_includes_recent_history(self):
        recent = [_summary(72, "2026-06-08", 2), _summary(85, "2026-06-01", 1)]
        ctx = build_context(_scan(), recent)
        assert "Recent scan history" in ctx and "85/100" in ctx

    def test_no_scan_message(self):
        assert "No scan has been run yet" in build_context(None, None)

    def test_caps_issue_list(self):
        many = [Issue(url=f"https://x.test/{i}", issue_type="Missing Title",
                      severity=SEVERITY_MEDIUM, category=CATEGORY_SEO,
                      description="d", recommendation="r") for i in range(40)]
        sr = ScanResult(root_url="https://x.test", pages=[], issues=many,
                        score=ScoreResult(score=10, grade="Critical",
                                          high_count=0, medium_count=40, low_count=0))
        ctx = build_context(sr, None)
        # Capped at 25 -> issue #30's URL shouldn't appear.
        assert "https://x.test/30" not in ctx


# --- History conversion ---------------------------------------------------

class TestHistoryConversion:
    def test_primes_with_context(self):
        msgs = _to_gemini_history("CTX", [])
        assert msgs[0]["role"] == "user" and "CTX" in msgs[0]["parts"][0]
        assert msgs[1]["role"] == "model"

    def test_maps_assistant_to_model(self):
        history = [{"role": "user", "content": "hi"},
                   {"role": "assistant", "content": "hello"}]
        msgs = _to_gemini_history("CTX", history)
        assert msgs[-2]["role"] == "user" and msgs[-2]["parts"] == ["hi"]
        assert msgs[-1]["role"] == "model" and msgs[-1]["parts"] == ["hello"]


# --- answer() with mocked Gemini -----------------------------------------

def _install_fake_genai(monkeypatch, reply_text, capture=None):
    class _FakeChat:
        def __init__(self): self.sent = []
        def send_message(self, msg):
            self.sent.append(msg)
            if capture is not None:
                capture["message"] = msg
            return _t.SimpleNamespace(text=reply_text)

    class _FakeModel:
        def __init__(self, *a, **k):
            if capture is not None:
                capture["system_instruction"] = k.get("system_instruction", "")
        def start_chat(self, history=None):
            if capture is not None:
                capture["history"] = history
            return _FakeChat()

    fake = _t.SimpleNamespace(configure=lambda **k: None, GenerativeModel=_FakeModel)
    monkeypatch.setitem(sys.modules, "google.generativeai", fake)
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setattr(chatbot, "is_available", lambda: True)


class TestAnswer:
    def test_fallback_when_no_key(self, monkeypatch):
        monkeypatch.setattr(chatbot, "is_available", lambda: False)
        r = answer("what's urgent?", [], "ctx")
        assert r.source == "fallback"

    def test_returns_gemini_reply(self, monkeypatch):
        _install_fake_genai(monkeypatch, "Fix your missing title first.")
        r = answer("what's most urgent?", [], build_context(_scan(), None))
        assert r.source == "gemini"
        assert r.text == "Fix your missing title first."

    def test_passes_context_and_history(self, monkeypatch):
        cap = {}
        _install_fake_genai(monkeypatch, "ok", capture=cap)
        history = [{"role": "user", "content": "earlier q"},
                   {"role": "assistant", "content": "earlier a"}]
        answer("follow up", history, "MY-CONTEXT")
        # The context primes the chat history, and the prior turns are replayed.
        flat = " ".join(p for m in cap["history"] for p in m["parts"])
        assert "MY-CONTEXT" in flat and "earlier q" in flat and "earlier a" in flat
        assert cap["message"] == "follow up"

    def test_empty_reply_falls_back(self, monkeypatch):
        _install_fake_genai(monkeypatch, "")
        r = answer("hi", [], "ctx")
        assert r.source == "fallback"
