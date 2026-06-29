"""
Tests for the sitePulse API (api.main).

Uses FastAPI's TestClient. The crawl is monkeypatched so no real network is
used, and scans go to a temporary DB. Requires fastapi + httpx installed
(they're in requirements.txt); skipped cleanly if FastAPI isn't available.
"""

from __future__ import annotations

import os
import tempfile

import pytest

pytest.importorskip("fastapi")  # skip the whole module if FastAPI isn't installed

from fastapi.testclient import TestClient  # noqa: E402

import api.main as api_main  # noqa: E402
import database.db as db  # noqa: E402
from models.result_models import (  # noqa: E402
    CATEGORY_SEO,
    Issue,
    PageResult,
    SEVERITY_HIGH,
)


@pytest.fixture
def client(monkeypatch):
    """A TestClient whose DB is a fresh temp file and whose crawl is faked."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    db.init_db(path)

    # Point every db call the API makes at the temp DB.
    for fn in ("save_scan", "list_scans", "get_scan", "get_diff", "init_db"):
        real = getattr(db, fn)
        monkeypatch.setattr(api_main, fn,
                            (lambda *a, _r=real, **k: _r(*a, db_path=path, **k)))

    # Fake the crawl so no network is used: two simple OK pages.
    def fake_crawl(root_url, **kwargs):
        return [
            PageResult(url=root_url, status_code=200, response_time=0.1,
                       html="<html><head></head><body></body></html>",
                       final_url=root_url),
            PageResult(url=root_url + "about", status_code=200, response_time=0.2,
                       html="<html><head></head><body></body></html>",
                       final_url=root_url + "about"),
        ]
    monkeypatch.setattr(api_main, "crawl_site", fake_crawl)

    # Force offline analysis (no real TLS sockets / path probes) regardless of
    # the flags the request sends.
    _real_analyze = api_main.analyze_pages
    monkeypatch.setattr(
        api_main, "analyze_pages",
        lambda pages, **k: _real_analyze(pages, check_tls=False, check_exposed_paths=False),
    )

    c = TestClient(api_main.app)
    yield c
    try:
        os.unlink(path)
    except FileNotFoundError:
        pass


# --- Health ---------------------------------------------------------------

class TestHealth:
    def test_health_ok(self, client):
        r = client.get("/api/health")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"
        assert "aiAvailable" in r.json()


# --- Scan -----------------------------------------------------------------

class TestScan:
    def test_scan_returns_result_shape(self, client):
        r = client.post("/api/scan", json={"url": "http://test.local/", "save": True})
        assert r.status_code == 200
        body = r.json()
        assert body["rootUrl"] == "http://test.local/"
        assert "score" in body and "metrics" in body and "issues" in body
        assert body["metrics"]["pagesScanned"] == 2
        assert isinstance(body["categoryScores"], list)
        assert body["scanId"] is not None  # it was saved

    def test_scan_rejects_bad_url(self, client):
        r = client.post("/api/scan", json={"url": "not-a-url"})
        assert r.status_code == 400

    def test_scan_without_save_has_null_id(self, client):
        r = client.post("/api/scan", json={"url": "http://test.local/", "save": False})
        assert r.status_code == 200
        assert r.json()["scanId"] is None


# --- History --------------------------------------------------------------

class TestHistory:
    def test_list_scans_after_scan(self, client):
        client.post("/api/scan", json={"url": "http://test.local/", "save": True})
        r = client.get("/api/scans")
        assert r.status_code == 200
        scans = r.json()["scans"]
        assert len(scans) >= 1
        assert scans[0]["rootUrl"] == "http://test.local/"

    def test_get_one_scan(self, client):
        sid = client.post("/api/scan", json={"url": "http://test.local/"}).json()["scanId"]
        r = client.get(f"/api/scans/{sid}")
        assert r.status_code == 200
        assert r.json()["scanId"] == sid

    def test_missing_scan_is_404(self, client):
        assert client.get("/api/scans/99999").status_code == 404


# --- AI fix (no key -> deterministic fallback) ----------------------------

class TestAiFix:
    def test_fix_returns_fallback_shape(self, client, monkeypatch):
        # Force the no-key fallback so the test never calls a real API.
        monkeypatch.setattr(api_main.ai_assistant, "is_available", lambda: False)
        r = client.post("/api/ai/fix", json={"issue": {
            "url": "http://x/", "issueType": "Missing Title", "severity": "High",
            "category": "SEO", "description": "d", "recommendation": "r",
        }})
        assert r.status_code == 200
        body = r.json()
        assert body["source"] == "fallback"
        assert "suggested_fix" in body


# --- Regression guards for the reported bugs ------------------------------

class TestBrokenLinkAndDedupeViaApi:
    """End-to-end through the API: no false 200/429 broken-links, deduped."""

    def _crawl_with_issues(self, monkeypatch):
        # Home (200) links to a real 404 and a rate-limited 429. Many pages
        # share the SAME missing-meta issue (to exercise de-duplication).
        def fake_crawl(root_url, **kwargs):
            home_html = (
                "<html><head><title>t</title></head><body><h1>h</h1>"
                f'<a href="{root_url}gone">x</a>'
                f'<a href="{root_url}rate">y</a>'
                "</body></html>"
            )
            # 5 pages all missing a meta description (same issue, different URL).
            dup_pages = [
                PageResult(url=f"{root_url}p{i}", status_code=200, response_time=0.1,
                           html="<html><head><title>t</title></head><body><h1>h</h1></body></html>",
                           final_url=f"{root_url}p{i}")
                for i in range(5)
            ]
            return [
                PageResult(url=root_url, status_code=200, response_time=0.1,
                           html=home_html, links=[root_url + "gone", root_url + "rate"],
                           final_url=root_url),
                PageResult(url=root_url + "gone", status_code=404, response_time=0.1,
                           html=None, final_url=root_url + "gone"),
                PageResult(url=root_url + "rate", status_code=429, response_time=0.1,
                           html=None, final_url=root_url + "rate"),
                *dup_pages,
            ]
        monkeypatch.setattr(api_main, "crawl_site", fake_crawl)

    def test_no_200_or_429_broken_links(self, client, monkeypatch):
        self._crawl_with_issues(monkeypatch)
        body = client.post("/api/scan", json={"url": "http://test.local/", "save": False}).json()
        for issue in body["issues"]:
            if issue["issueType"] == "Broken Link":
                # Every broken-link row must reference a genuine 404/410 —
                # never a 200 or 429.
                assert "HTTP 200" not in issue["description"]
                assert "429" not in issue["description"]

    def test_duplicate_issues_are_deduped(self, client, monkeypatch):
        self._crawl_with_issues(monkeypatch)
        body = client.post("/api/scan", json={"url": "http://test.local/", "save": False}).json()
        metas = [i for i in body["issues"] if i["issueType"] == "Missing Meta Description"]
        # 5 pages share the issue -> ONE display row with affectedPages >= 5.
        assert len(metas) == 1
        assert metas[0]["affectedPages"] >= 5


class TestReportDownloads:
    def test_pdf_report_downloads(self, client):
        sid = client.post("/api/scan", json={"url": "http://test.local/"}).json()["scanId"]
        r = client.get(f"/api/scans/{sid}/report/report.pdf")
        assert r.status_code == 200
        assert r.content[:4] == b"%PDF"
        assert "attachment" in r.headers.get("content-disposition", "")

    def test_issues_csv_downloads(self, client):
        sid = client.post("/api/scan", json={"url": "http://test.local/"}).json()["scanId"]
        r = client.get(f"/api/scans/{sid}/report/issues.csv")
        assert r.status_code == 200
        assert "text/csv" in r.headers.get("content-type", "")
