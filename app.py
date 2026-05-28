"""
app.py
======

Streamlit UI for the Web Health & SEO Crawler.

This is the user-facing layer. All the heavy lifting is delegated to:
    - crawler.crawler      : actual site crawling
    - analyzer.seo_analyzer: rule-based issue detection
    - analyzer.scoring     : 0-100 health score
    - ai.ai_assistant      : Gemini-powered fix suggestions (added in stage 6)
    - reports              : CSV / PDF export      (added in stage 7)

Run with:
    streamlit run app.py

Design notes
------------
- ONE FILE on purpose. Streamlit apps are top-to-bottom scripts that re-run
  on every user interaction; splitting them across modules without a real
  reason makes them harder to follow.

- We use st.session_state to remember the last scan result, so that clicking
  "Ask AI" on an issue doesn't trigger a fresh crawl of the entire site.

- Every scan call is wrapped in try/except so that a bad URL or unreachable
  server shows a friendly message instead of a stack trace.
"""

from __future__ import annotations

import logging
import os
from typing import Optional

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

from ai import ai_assistant
from analyzer.scoring import calculate_score
from analyzer.seo_analyzer import analyze_pages
from crawler.crawler import crawl_site
from models.result_models import Issue, ScanResult
from reports.csv_exporter import issues_to_csv, pages_to_csv, suggested_filename
from reports.pdf_exporter import scan_to_pdf

# Load .env once at startup so AI_MAX_CALLS_PER_SESSION etc. are available.
load_dotenv()


# Per-session limit on AI calls. Acts as a cost / quota guardrail and protects
# against accidental run-away loops. Configurable via .env.
try:
    AI_MAX_CALLS_PER_SESSION = int(os.environ.get("AI_MAX_CALLS_PER_SESSION", "20"))
except ValueError:
    AI_MAX_CALLS_PER_SESSION = 20


# --- Page configuration ---------------------------------------------------

# st.set_page_config MUST be the first Streamlit call.
st.set_page_config(
    page_title="Web Health & SEO Crawler",
    page_icon="🌐",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Set up logging so the crawler's INFO lines show up in the terminal where
# Streamlit was launched — useful for debugging during demos.
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
    datefmt="%H:%M:%S",
)


# --- Severity color map (used in tables and AI panels) -------------------

SEVERITY_COLORS = {
    "High": "#E74C3C",      # red
    "Medium": "#F39C12",    # orange
    "Low": "#3498DB",       # blue
}

# Streamlit-native badge palettes for st.dataframe column config.
SEVERITY_EMOJI = {
    "High": "🔴",
    "Medium": "🟠",
    "Low": "🔵",
}


# --- Session state initialization ----------------------------------------

def _init_session_state() -> None:
    """Create empty state entries on the first run."""
    if "scan_result" not in st.session_state:
        st.session_state.scan_result = None     # type: Optional[ScanResult]
    if "ai_responses" not in st.session_state:
        # Cache of AI answers keyed by (issue_type, url) so re-clicking an
        # "Ask AI" button doesn't re-hit the API (will matter in stage 6).
        st.session_state.ai_responses = {}
    if "ai_call_count" not in st.session_state:
        st.session_state.ai_call_count = 0


_init_session_state()


# --- Sidebar: scan settings ----------------------------------------------

with st.sidebar:
    st.title("⚙️ Scan settings")

    website_url = st.text_input(
        "Website URL",
        value="http://localhost:8000",
        help="Full URL including http:// or https://",
    )

    max_pages = st.slider(
        "Max pages",
        min_value=5,
        max_value=200,
        value=50,
        step=5,
        help="Maximum number of pages to crawl.",
    )

    max_depth = st.slider(
        "Max depth",
        min_value=1,
        max_value=5,
        value=2,
        help="How many link-clicks deep from the root URL to follow.",
    )

    timeout = st.slider(
        "Request timeout (seconds)",
        min_value=2,
        max_value=30,
        value=10,
        help="How long to wait before giving up on an unresponsive page.",
    )

    with st.expander("Advanced", expanded=False):
        max_workers = st.slider(
            "Concurrent workers",
            min_value=1,
            max_value=16,
            value=8,
            help="Number of pages fetched in parallel. Higher = faster, but heavier on the target server.",
        )
        polite_delay = st.slider(
            "Polite delay (seconds)",
            min_value=0.0,
            max_value=2.0,
            value=0.1,
            step=0.1,
            help="Pause after each fetch, inside each worker. Lowers load on the target site.",
        )
        respect_robots = st.checkbox(
            "Respect robots.txt",
            value=True,
            help="If enabled, the crawler will not visit URLs disallowed by the site's robots.txt.",
        )
        ai_enabled = st.checkbox(
            "Enable AI Assistant",
            value=True,
            help="If enabled, lets you click 'Ask AI' on any issue to get a Gemini-powered fix suggestion.",
        )

    # Show AI status so the user knows whether they're hitting real Gemini
    # or the built-in fallback before they click anything.
    if ai_assistant.is_available():
        st.caption("🤖 AI Assistant: **Gemini connected**")
    else:
        st.caption("🤖 AI Assistant: **fallback mode** (set GEMINI_API_KEY in `.env`)")

    st.divider()

    scan_clicked = st.button(
        "🔍 Scan",
        type="primary",
        use_container_width=True,
    )

    if st.session_state.scan_result is not None:
        if st.button("🗑️ Clear results", use_container_width=True):
            st.session_state.scan_result = None
            st.session_state.ai_responses = {}
            st.session_state.ai_call_count = 0
            st.rerun()


# --- Header ---------------------------------------------------------------

st.title("🌐 Web Health & SEO Crawler")
st.caption(
    "Scan your website, detect technical SEO issues, and get AI-powered repair suggestions."
)


# --- Scan execution -------------------------------------------------------

def _run_scan(
    url: str,
    max_pages: int,
    max_depth: int,
    timeout: float,
    max_workers: int,
    polite_delay: float,
    respect_robots: bool,
) -> Optional[ScanResult]:
    """
    Run crawler + analyzer + scoring and bundle the result.

    Returns None on failure (after showing an error in the UI).
    """
    progress_placeholder = st.empty()
    progress_bar = progress_placeholder.progress(0, text="Starting crawl...")

    def _update_progress(pages_done: int, target_total: int) -> None:
        # Use min(pages_done / target_total, 1.0) so we never exceed 100%.
        pct = min(pages_done / max(target_total, 1), 1.0)
        progress_bar.progress(
            pct,
            text=f"Crawling… {pages_done} pages fetched",
        )

    try:
        pages = crawl_site(
            root_url=url,
            max_pages=max_pages,
            max_depth=max_depth,
            timeout=timeout,
            max_workers=max_workers,
            polite_delay=polite_delay,
            respect_robots=respect_robots,
            progress_callback=_update_progress,
        )
    except Exception as exc:  # noqa: BLE001
        progress_placeholder.empty()
        st.error(
            f"**Scan failed.**\n\n{exc}\n\n"
            "Check that the URL is correct and reachable, then try again."
        )
        return None

    progress_bar.progress(1.0, text="Analyzing pages...")
    issues = analyze_pages(pages)
    score = calculate_score(issues)
    progress_placeholder.empty()

    return ScanResult(
        root_url=url,
        pages=pages,
        issues=issues,
        score=score,
    )


# Trigger a scan when the button was clicked.
if scan_clicked:
    if not website_url.strip():
        st.error("Please enter a website URL.")
    elif not (website_url.startswith("http://") or website_url.startswith("https://")):
        st.error("URL must start with http:// or https://")
    else:
        with st.spinner("Scanning the website..."):
            result = _run_scan(
                url=website_url.strip(),
                max_pages=max_pages,
                max_depth=max_depth,
                timeout=float(timeout),
                max_workers=max_workers,
                polite_delay=polite_delay,
                respect_robots=respect_robots,
            )
        if result is not None:
            st.session_state.scan_result = result
            # Clear stale AI responses from previous scans.
            st.session_state.ai_responses = {}
            st.session_state.ai_call_count = 0


# --- Empty state ---------------------------------------------------------

if st.session_state.scan_result is None:
    st.info(
        "👈 Enter a URL in the sidebar and click **Scan** to begin.\n\n"
        "Tip: for development, run the bundled test site with "
        "`python serve_test_site.py` and scan `http://localhost:8000`."
    )
    st.stop()


# --- Result rendering -----------------------------------------------------

result: ScanResult = st.session_state.scan_result
score = result.score
assert score is not None  # always set when we reach this branch


# --- Dashboard cards ------------------------------------------------------

st.subheader(f"📊 Scan results for `{result.root_url}`")

col_pages, col_issues, col_broken, col_time, col_score = st.columns(5)

col_pages.metric(
    label="Pages scanned",
    value=result.pages_scanned,
)
col_issues.metric(
    label="Issues found",
    value=result.issues_found,
)
col_broken.metric(
    label="Broken links",
    value=result.broken_links,
)
avg_rt = result.average_response_time
col_time.metric(
    label="Avg. response time",
    value=f"{avg_rt:.2f}s" if avg_rt is not None else "—",
)
col_score.metric(
    label="Health Score",
    value=f"{score.score}/100",
    delta=score.grade,
    delta_color=(
        "normal" if score.grade in {"Excellent", "Good"}
        else "inverse"  # show in red for problems
    ),
)


# --- Health Score gauge (visual progress bar by severity counts) ---------

# A simple visual: a progress-bar-style gauge whose color matches the grade.
# Streamlit doesn't include a real gauge widget, so we synthesize one using
# CSS + a div bar. This stays in pure Streamlit (no extra dependencies).
_GAUGE_COLORS = {
    "Excellent": "#27AE60",
    "Good": "#2ECC71",
    "Needs Improvement": "#F39C12",
    "Critical": "#E74C3C",
}

st.markdown(
    f"""
    <div style="margin-top: 8px; margin-bottom: 24px;">
      <div style="display:flex; justify-content:space-between; font-size:0.85em; color:#888;">
        <span>0</span>
        <span><b>{score.score}/100 — {score.grade}</b></span>
        <span>100</span>
      </div>
      <div style="background:#eee; border-radius:8px; height:14px; overflow:hidden; margin-top:4px;">
        <div style="background:{_GAUGE_COLORS.get(score.grade, '#888')};
                    width:{score.score}%; height:100%; border-radius:8px;"></div>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)


# --- Export buttons ------------------------------------------------------

st.subheader("📥 Export results")

export_col_csv, export_col_pages, export_col_pdf = st.columns(3)

# Issues CSV — the main artifact: one row per detected problem.
export_col_csv.download_button(
    label="Issues CSV",
    data=issues_to_csv(result),
    file_name=suggested_filename("seo-issues", result, "csv"),
    mime="text/csv",
    use_container_width=True,
)

# Pages CSV — secondary: status codes and response times for every URL.
export_col_pages.download_button(
    label="Pages CSV",
    data=pages_to_csv(result),
    file_name=suggested_filename("crawled-pages", result, "csv"),
    mime="text/csv",
    use_container_width=True,
)

# PDF — printable report with health score, summary, severity counts, issues.
# We render the PDF lazily inside a try/except so a rare reportlab quirk
# (e.g. a single odd character) never breaks the whole results page.
try:
    pdf_bytes = scan_to_pdf(result)
    export_col_pdf.download_button(
        label="PDF Report",
        data=pdf_bytes,
        file_name=suggested_filename("seo-report", result, "pdf"),
        mime="application/pdf",
        use_container_width=True,
    )
except Exception as exc:  # noqa: BLE001
    export_col_pdf.button("PDF Report", disabled=True, use_container_width=True)
    export_col_pdf.caption(f"PDF generation failed: {exc}")


# --- Issues table --------------------------------------------------------

st.subheader("⚠️ Detected issues")

if not result.issues:
    st.success("No issues detected. Your site looks great!")
else:
    # Build a DataFrame for nice table rendering with sorting + search.
    rows = []
    severity_order = {"High": 0, "Medium": 1, "Low": 2}
    for i, issue in enumerate(sorted(
        result.issues,
        key=lambda x: (severity_order.get(x.severity, 9), x.issue_type, x.url),
    )):
        rows.append({
            "Severity": f"{SEVERITY_EMOJI.get(issue.severity, '')}  {issue.severity}",
            "Type": issue.issue_type,
            "URL": issue.url,
            "Status": issue.status_code if issue.status_code is not None else "—",
            "Time (s)": (
                f"{issue.response_time:.2f}"
                if issue.response_time is not None else "—"
            ),
            "Description": issue.description,
        })
    issues_df = pd.DataFrame(rows)

    # Severity filter
    severities_present = sorted(
        {i.severity for i in result.issues},
        key=lambda s: severity_order.get(s, 9),
    )
    severity_filter = st.multiselect(
        "Filter by severity",
        options=severities_present,
        default=severities_present,
    )
    if severity_filter:
        mask = issues_df["Severity"].str.contains("|".join(severity_filter))
        filtered = issues_df[mask]
    else:
        filtered = issues_df

    st.dataframe(
        filtered,
        use_container_width=True,
        hide_index=True,
        column_config={
            "URL": st.column_config.TextColumn(width="medium"),
            "Description": st.column_config.TextColumn(width="large"),
        },
    )

    # Severity breakdown for visual clarity.
    breakdown_cols = st.columns(3)
    breakdown_cols[0].metric("🔴 High", score.high_count)
    breakdown_cols[1].metric("🟠 Medium", score.medium_count)
    breakdown_cols[2].metric("🔵 Low", score.low_count)


# --- AI Assistant section -------------------------------------------------

st.subheader("🤖 AI Assistant")

if not ai_enabled:
    st.info("The AI Assistant is disabled in the sidebar.")
elif not result.issues:
    st.caption("Nothing to ask the AI about — no issues were detected.")
else:
    st.caption(
        "Pick a detected issue and ask the AI for a plain-language explanation "
        "and a ready-to-paste HTML fix."
    )

    # Build labels in a stable, predictable order.
    issue_options = []
    issue_lookup: dict[str, Issue] = {}
    for i, issue in enumerate(sorted(
        result.issues,
        key=lambda x: (severity_order.get(x.severity, 9), x.issue_type, x.url),
    )):
        label = f"[{issue.severity}] {issue.issue_type} — {issue.url}"
        # Disambiguate identical labels (e.g. 3 Missing Alt on the same page)
        # by appending an index.
        if label in issue_lookup:
            label = f"{label}  (#{i})"
        issue_options.append(label)
        issue_lookup[label] = issue

    selected_label = st.selectbox(
        "Issue",
        options=issue_options,
        index=0,
    )
    selected_issue = issue_lookup[selected_label]

    ask_col, info_col = st.columns([1, 3])
    with ask_col:
        ask_clicked = st.button("💡 Ask AI for Fix", use_container_width=True)
    info_col.caption(
        f"AI calls this session: "
        f"{st.session_state.ai_call_count} / {AI_MAX_CALLS_PER_SESSION}"
    )

    cache_key = (selected_issue.issue_type, selected_issue.url)

    if ask_clicked:
        if cache_key in st.session_state.ai_responses:
            # Already answered — just re-render below. (Cache hit is free.)
            pass
        elif st.session_state.ai_call_count >= AI_MAX_CALLS_PER_SESSION:
            st.warning(
                f"You've reached the per-session limit of "
                f"{AI_MAX_CALLS_PER_SESSION} AI calls. "
                "Clear results to start a new session."
            )
        else:
            # Find the page that this issue came from, so the AI can use
            # the actual current title / H1 / meta description as context.
            origin_page = next(
                (p for p in result.pages if p.url == selected_issue.url),
                None,
            )
            with st.spinner("Asking Gemini..."):
                ai_response = ai_assistant.generate_ai_fix(
                    issue=selected_issue,
                    page=origin_page,
                )
            st.session_state.ai_responses[cache_key] = ai_response.to_dict()
            # Only count real Gemini calls — fallback responses are free.
            if ai_response.source == "gemini":
                st.session_state.ai_call_count += 1

    if cache_key in st.session_state.ai_responses:
        response = st.session_state.ai_responses[cache_key]
        with st.container(border=True):
            st.markdown(f"### {selected_issue.issue_type}")
            st.markdown(f"**Page:** `{selected_issue.url}`")
            st.markdown(f"**Severity:** {selected_issue.severity}")
            source = response.get("source", "gemini")
            if source == "fallback":
                reason = response.get("fallback_reason", "").strip()
                if reason:
                    st.caption(f"ℹ️ Built-in fallback answer — {reason}")
                else:
                    st.caption("ℹ️ Built-in fallback answer.")
            else:
                st.caption("✨ Generated by Google Gemini.")
            st.divider()
            st.markdown("**Simple explanation**")
            st.write(response["simple_explanation"])
            st.markdown("**Why it matters**")
            st.write(response["why_it_matters"])
            st.markdown("**Suggested fix**")
            st.write(response["suggested_fix"])
            if response.get("code_snippet"):
                st.markdown("**Code snippet**")
                st.code(response["code_snippet"], language="html")
