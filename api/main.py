"""
main.py
=======

sitePulse API — a thin FastAPI layer over the existing backend.

This module adds NO analysis logic. Every endpoint just calls the functions
that already power the Streamlit app (crawl_site, analyze_pages,
calculate_score, the DB layer, the AI modules) and returns JSON via the
serializers. The React frontend talks only to this API.

Run it (on your machine):
    uvicorn api.main:app --reload --port 8001

Then the React dev server (Vite) calls http://localhost:8001/api/...
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from ai import ai_assistant, chatbot, root_cause
from analyzer.scoring import calculate_score
from analyzer.seo_analyzer import analyze_pages
from api.serializers import (
    diff_to_dict,
    issue_to_dict,
    scan_result_to_dict,
    scan_summary_to_dict,
)
from crawler.crawler import crawl_site
from database.db import get_diff, get_scan, init_db, list_scans, save_scan
from models.result_models import Issue, ScanResult
from reports.csv_exporter import issues_to_csv, pages_to_csv, suggested_filename
from reports.pdf_exporter import scan_to_pdf

logger = logging.getLogger(__name__)


@asynccontextmanager
async def _lifespan(app: FastAPI):
    # Ensure the SQLite schema exists before the first request.
    init_db()
    yield


app = FastAPI(
    title="sitePulse API",
    description="Website health intelligence — API for the sitePulse frontend.",
    version="1.0.0",
    lifespan=_lifespan,
)

# The React dev server runs on a different origin (e.g. :5173), so allow it.
# For a local project this permissive setup is fine; tighten for production.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Request models -------------------------------------------------------

class ScanRequest(BaseModel):
    url: str
    maxPages: int = 50
    maxDepth: int = 2
    timeout: float = 10.0
    politeDelay: float = 0.1
    respectRobots: bool = True
    checkTls: bool = True
    checkExposedPaths: bool = False
    save: bool = True


class IssueModel(BaseModel):
    url: str
    issueType: str
    severity: str
    category: str = "SEO"
    description: str = ""
    recommendation: str = ""
    statusCode: Optional[int] = None
    responseTime: Optional[float] = None


class AiFixRequest(BaseModel):
    issue: IssueModel


class ChatTurn(BaseModel):
    role: str   # "user" | "assistant"
    content: str


class ChatRequest(BaseModel):
    message: str
    history: list[ChatTurn] = []
    scanId: Optional[int] = None


# --- Health & meta --------------------------------------------------------

@app.get("/api/health")
def health() -> dict:
    return {
        "status": "ok",
        "aiAvailable": ai_assistant.is_available(),
    }


# --- Scan -----------------------------------------------------------------

@app.post("/api/scan")
def run_scan(req: ScanRequest) -> dict:
    """Crawl, analyze, score, (optionally) save — return the full result."""
    if not (req.url.startswith("http://") or req.url.startswith("https://")):
        raise HTTPException(status_code=400, detail="URL must start with http:// or https://")

    try:
        pages = crawl_site(
            root_url=req.url,
            max_pages=req.maxPages,
            max_depth=req.maxDepth,
            timeout=req.timeout,
            polite_delay=req.politeDelay,
            respect_robots=req.respectRobots,
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("Crawl failed")
        raise HTTPException(status_code=502, detail=f"Crawl failed: {exc}")

    issues = analyze_pages(
        pages,
        check_tls=req.checkTls,
        check_exposed_paths=req.checkExposedPaths,
    )
    score = calculate_score(issues, pages)
    scan = ScanResult(root_url=req.url, pages=pages, issues=issues, score=score)

    scan_id = None
    if req.save:
        try:
            scan_id = save_scan(scan)
        except Exception:  # noqa: BLE001 — saving shouldn't fail the response
            logger.exception("Saving scan failed; returning unsaved result")

    return scan_result_to_dict(scan, scan_id=scan_id)


# --- History --------------------------------------------------------------

@app.get("/api/scans")
def get_scans(rootUrl: Optional[str] = None, limit: int = 50) -> dict:
    summaries = list_scans(root_url=rootUrl, limit=limit)
    return {"scans": [scan_summary_to_dict(s) for s in summaries]}


@app.get("/api/scans/{scan_id}")
def get_one_scan(scan_id: int) -> dict:
    scan = get_scan(scan_id)
    if scan is None:
        raise HTTPException(status_code=404, detail="Scan not found")
    return scan_result_to_dict(scan, scan_id=scan_id)


@app.get("/api/diff")
def diff(fromId: int, toId: int) -> dict:
    d = get_diff(fromId, toId)
    if d is None:
        raise HTTPException(status_code=404, detail="One or both scans not found")
    return diff_to_dict(d)


# --- Reports (downloads) --------------------------------------------------

def _load_or_404(scan_id: int):
    scan = get_scan(scan_id)
    if scan is None:
        raise HTTPException(status_code=404, detail="Scan not found")
    return scan


def _download(content, media_type: str, filename: str) -> Response:
    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.get("/api/scans/{scan_id}/report/issues.csv")
def report_issues_csv(scan_id: int) -> Response:
    scan = _load_or_404(scan_id)
    return _download(issues_to_csv(scan), "text/csv",
                     suggested_filename("issues", scan, "csv"))


@app.get("/api/scans/{scan_id}/report/pages.csv")
def report_pages_csv(scan_id: int) -> Response:
    scan = _load_or_404(scan_id)
    return _download(pages_to_csv(scan), "text/csv",
                     suggested_filename("pages", scan, "csv"))


@app.get("/api/scans/{scan_id}/report/report.pdf")
def report_pdf(scan_id: int) -> Response:
    scan = _load_or_404(scan_id)
    return _download(scan_to_pdf(scan), "application/pdf",
                     suggested_filename("report", scan, "pdf"))


# --- AI -------------------------------------------------------------------

def _issue_from_model(m: IssueModel) -> Issue:
    return Issue(
        url=m.url,
        issue_type=m.issueType,
        severity=m.severity,
        category=m.category,
        description=m.description,
        recommendation=m.recommendation,
        status_code=m.statusCode,
        response_time=m.responseTime,
    )


@app.post("/api/ai/fix")
def ai_fix(req: AiFixRequest) -> dict:
    """Explain one issue + suggest a fix (the per-issue AI Assistant)."""
    response = ai_assistant.generate_ai_fix(_issue_from_model(req.issue))
    return response.to_dict()


@app.post("/api/ai/root-cause")
def ai_root_cause(fromId: int, toId: int) -> dict:
    """AI explanation of what changed between two scans."""
    d = get_diff(fromId, toId)
    if d is None:
        raise HTTPException(status_code=404, detail="One or both scans not found")
    result = root_cause.analyze_diff(d)
    return {
        "summary": result.summary,
        "likelyCause": result.likely_cause,
        "recommendedAction": result.recommended_action,
        "source": result.source,
    }


@app.post("/api/ai/chat")
def ai_chat(req: ChatRequest) -> dict:
    """One chatbot turn, grounded in the given scan + recent history."""
    current = get_scan(req.scanId) if req.scanId is not None else None
    root = current.root_url if current else None
    try:
        recent = list_scans(root_url=root, limit=5) if root else list_scans(limit=5)
    except Exception:  # noqa: BLE001
        recent = []
    context = chatbot.build_context(current, recent)
    history = [{"role": t.role, "content": t.content} for t in req.history]
    reply = chatbot.answer(req.message, history, context)
    return {"text": reply.text, "source": reply.source}
