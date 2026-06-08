"""
Unit tests for ai.root_cause (Stage 14).

The Gemini call is mocked, so these run fully offline with no API key.
"""

from __future__ import annotations

import pytest

import ai.root_cause as root_cause
from ai.root_cause import (
    RootCauseResult,
    _extract_json_block,
    _result_from_payload,
    _url_folder,
    analyze_diff,
    summarize_diff,
)
from database.db import ScanDiff, ScanSummary
from models.result_models import (
    CATEGORY_ACCESSIBILITY,
    CATEGORY_SEO,
    Issue,
    SEVERITY_HIGH,
    SEVERITY_MEDIUM,
)


def _summary(score: int, root="https://x.test", sid=1) -> ScanSummary:
    return ScanSummary(id=sid, root_url=root, scanned_at="2026-06-08",
                       score=score, grade="Good", pages_count=10, issues_count=5,
                       high_count=1, medium_count=2, low_count=2, avg_response_time=0.5)


def _iss(url, cat=CATEGORY_SEO, sev=SEVERITY_MEDIUM, t="Missing H1") -> Issue:
    return Issue(url=url, issue_type=t, severity=sev, category=cat,
                 description="d", recommendation="r")


def _diff(*, new=None, fixed=None, unchanged=None, from_score=80, to_score=60) -> ScanDiff:
    return ScanDiff(
        from_scan=_summary(from_score, sid=1),
        to_scan=_summary(to_score, sid=2),
        fixed_issues=fixed or [],
        new_issues=new or [],
        unchanged_issues=unchanged or [],
        score_delta=to_score - from_score,
    )


# --- URL folder helper ----------------------------------------------------

class TestUrlFolder:
    def test_top_folder(self):
        assert _url_folder("https://x.test/blog/post-1") == "/blog"

    def test_root(self):
        assert _url_folder("https://x.test/") == "/"
        assert _url_folder("https://x.test") == "/"


# --- Diff summarisation ---------------------------------------------------

class TestSummarizeDiff:
    def test_includes_score_delta(self):
        s = summarize_diff(_diff(from_score=80, to_score=60))
        assert "80 -> 60" in s and "change -20" in s

    def test_detects_folder_cluster(self):
        new = [_iss("https://x.test/blog/a"), _iss("https://x.test/blog/b"),
               _iss("https://x.test/blog/c")]
        s = summarize_diff(_diff(new=new))
        assert "/blog" in s and "3/3" in s

    def test_detects_category_cluster(self):
        new = [_iss("https://x.test/1", CATEGORY_ACCESSIBILITY),
               _iss("https://x.test/2", CATEGORY_ACCESSIBILITY)]
        s = summarize_diff(_diff(new=new))
        assert "Accessibility" in s

    def test_lists_examples(self):
        new = [_iss("https://x.test/p", t="Missing Title")]
        s = summarize_diff(_diff(new=new))
        assert "Missing Title" in s

    def test_no_new_issues_still_summarises(self):
        s = summarize_diff(_diff(new=[], fixed=[_iss("https://x.test/a")]))
        assert "Fixed issues: 1" in s and "New issues: 0" in s


# --- JSON parsing / payload ----------------------------------------------

class TestParsing:
    def test_plain_json(self):
        d = _extract_json_block('{"summary": "s", "likely_cause": "c"}')
        assert d["summary"] == "s"

    def test_fenced_json(self):
        d = _extract_json_block('```json\n{"summary": "s"}\n```')
        assert d["summary"] == "s"

    def test_garbage_is_none(self):
        assert _extract_json_block("no json") is None

    def test_payload_defaults(self):
        r = _result_from_payload({"summary": "only summary"})
        assert r.summary == "only summary"
        assert r.likely_cause and r.recommended_action  # filled with placeholders
        assert r.source == "gemini"


# --- analyze_diff (mocked) ------------------------------------------------

@pytest.fixture
def force_available(monkeypatch):
    monkeypatch.setattr(root_cause, "is_available", lambda: True)


class TestAnalyzeDiff:
    def test_fallback_when_no_key(self, monkeypatch):
        monkeypatch.setattr(root_cause, "is_available", lambda: False)
        r = analyze_diff(_diff(from_score=80, to_score=60))
        assert r.source == "fallback"
        assert "dropped" in r.summary

    def test_fallback_score_improved_wording(self, monkeypatch):
        monkeypatch.setattr(root_cause, "is_available", lambda: False)
        r = analyze_diff(_diff(from_score=60, to_score=85))
        assert "improved" in r.summary

    def test_uses_gemini_when_available(self, force_available, monkeypatch):
        # Patch the lazy genai import path by faking generate_content via a stub.
        class _FakeResult:
            text = '{"summary":"S","likely_cause":"C","recommended_action":"A"}'

        class _FakeModel:
            def __init__(self, *a, **k): pass
            def generate_content(self, prompt): return _FakeResult()

        import types as _t
        fake_genai = _t.SimpleNamespace(
            configure=lambda **k: None,
            GenerativeModel=_FakeModel,
        )
        monkeypatch.setitem(__import__("sys").modules, "google.generativeai", fake_genai)
        monkeypatch.setenv("GEMINI_API_KEY", "test-key")

        r = analyze_diff(_diff(new=[_iss("https://x.test/blog/a")]))
        assert r.source == "gemini"
        assert r.summary == "S" and r.likely_cause == "C" and r.recommended_action == "A"

    def test_bad_json_falls_back(self, force_available, monkeypatch):
        class _FakeResult:
            text = "not json at all"

        class _FakeModel:
            def __init__(self, *a, **k): pass
            def generate_content(self, prompt): return _FakeResult()

        import types as _t
        fake_genai = _t.SimpleNamespace(configure=lambda **k: None, GenerativeModel=_FakeModel)
        monkeypatch.setitem(__import__("sys").modules, "google.generativeai", fake_genai)
        monkeypatch.setenv("GEMINI_API_KEY", "test-key")

        r = analyze_diff(_diff())
        assert r.source == "fallback"
