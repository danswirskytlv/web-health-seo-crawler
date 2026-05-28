"""
pdf_exporter.py
===============

Render a scan result as a print-ready PDF report.

Layout:
    1. Title block: tool name, scanned URL, generation timestamp.
    2. Health score banner — big number + grade.
    3. Summary stats (pages, issues, broken links, avg response time).
    4. Severity breakdown (High / Medium / Low counts).
    5. Issues table — one row per issue, color-coded by severity.

We use ReportLab's "platypus" flowable layout (Story + SimpleDocTemplate)
because it handles page breaks, tables and font styles cleanly without us
needing to compute Y-coordinates by hand.
"""

from __future__ import annotations

import io
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from models.result_models import ScanResult

# --- Color palette --------------------------------------------------------

SEVERITY_COLORS = {
    "High":   colors.HexColor("#E74C3C"),
    "Medium": colors.HexColor("#F39C12"),
    "Low":    colors.HexColor("#3498DB"),
}

GRADE_COLORS = {
    "Excellent":         colors.HexColor("#27AE60"),
    "Good":              colors.HexColor("#2ECC71"),
    "Needs Improvement": colors.HexColor("#F39C12"),
    "Critical":          colors.HexColor("#E74C3C"),
}


# --- Styles --------------------------------------------------------------

def _styles() -> dict[str, ParagraphStyle]:
    """Build the paragraph styles used throughout the document."""
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "Title",
            parent=base["Title"],
            fontSize=22,
            spaceAfter=4,
            textColor=colors.HexColor("#222"),
        ),
        "subtitle": ParagraphStyle(
            "Subtitle",
            parent=base["Normal"],
            fontSize=11,
            textColor=colors.HexColor("#666"),
            spaceAfter=12,
        ),
        "section": ParagraphStyle(
            "Section",
            parent=base["Heading2"],
            fontSize=14,
            spaceBefore=14,
            spaceAfter=6,
            textColor=colors.HexColor("#222"),
        ),
        "score_big": ParagraphStyle(
            "ScoreBig",
            parent=base["Normal"],
            fontSize=36,
            alignment=1,  # CENTER
            spaceAfter=0,
        ),
        "score_grade": ParagraphStyle(
            "ScoreGrade",
            parent=base["Normal"],
            fontSize=14,
            alignment=1,
            spaceAfter=10,
        ),
        "body": ParagraphStyle(
            "Body",
            parent=base["Normal"],
            fontSize=9,
            leading=11,
        ),
    }


# --- Helpers --------------------------------------------------------------

def _wrap(text: str, style: ParagraphStyle) -> Paragraph:
    """Wrap arbitrary text into a Paragraph so it word-wraps inside a cell."""
    # Escape XML-like characters that ReportLab will otherwise interpret.
    safe = (
        str(text or "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )
    return Paragraph(safe, style)


def _summary_table(scan: ScanResult, styles: dict) -> Table:
    """The four-card summary row (Pages / Issues / Broken / Avg time)."""
    avg = scan.average_response_time
    avg_str = f"{avg:.2f}s" if avg is not None else "—"

    data = [
        ["Pages scanned", "Issues found", "Broken links", "Avg response time"],
        [str(scan.pages_scanned), str(scan.issues_found), str(scan.broken_links), avg_str],
    ]
    t = Table(data, colWidths=[4.2 * cm] * 4)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F2F2F2")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#666")),
        ("FONTSIZE", (0, 0), (-1, 0), 9),
        ("FONTSIZE", (0, 1), (-1, 1), 16),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#DDDDDD")),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#EEEEEE")),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    return t


def _severity_breakdown(scan: ScanResult) -> Table:
    """Three colored cells: High / Medium / Low counts."""
    score = scan.score
    h = score.high_count if score else 0
    m = score.medium_count if score else 0
    l = score.low_count if score else 0

    data = [
        ["High", "Medium", "Low"],
        [str(h), str(m), str(l)],
    ]
    t = Table(data, colWidths=[5.6 * cm] * 3)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, 0), SEVERITY_COLORS["High"]),
        ("BACKGROUND", (1, 0), (1, 0), SEVERITY_COLORS["Medium"]),
        ("BACKGROUND", (2, 0), (2, 0), SEVERITY_COLORS["Low"]),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, 0), 10),
        ("FONTSIZE", (0, 1), (-1, 1), 18),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#DDDDDD")),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#EEEEEE")),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    return t


def _issues_table(scan: ScanResult, styles: dict) -> Table:
    """The full issues table — one row per detected issue."""
    header = ["Severity", "Type", "URL", "Description"]
    rows: list[list] = [header]

    severity_order = {"High": 0, "Medium": 1, "Low": 2}
    sorted_issues = sorted(
        scan.issues,
        key=lambda i: (severity_order.get(i.severity, 9), i.url, i.issue_type),
    )

    body_style = styles["body"]
    for issue in sorted_issues:
        rows.append([
            issue.severity,
            _wrap(issue.issue_type, body_style),
            _wrap(issue.url, body_style),
            _wrap(issue.description, body_style),
        ])

    t = Table(
        rows,
        colWidths=[2.0 * cm, 3.5 * cm, 5.5 * cm, 6.0 * cm],
        repeatRows=1,  # repeat the header on every new page
    )

    style = TableStyle([
        # Header
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#333333")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, 0), 10),
        ("ALIGN", (0, 0), (-1, 0), "LEFT"),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
        ("TOPPADDING", (0, 0), (-1, 0), 6),
        # Body
        ("FONTSIZE", (0, 1), (-1, -1), 9),
        ("VALIGN", (0, 1), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 1), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 1), (-1, -1), 4),
        # Grid
        ("INNERGRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#DDDDDD")),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#CCCCCC")),
    ])

    # Color the severity column per row.
    for row_idx, issue in enumerate(sorted_issues, start=1):
        color = SEVERITY_COLORS.get(issue.severity, colors.grey)
        style.add("BACKGROUND", (0, row_idx), (0, row_idx), color)
        style.add("TEXTCOLOR", (0, row_idx), (0, row_idx), colors.white)
        style.add("ALIGN", (0, row_idx), (0, row_idx), "CENTER")
        style.add("FONTNAME", (0, row_idx), (0, row_idx), "Helvetica-Bold")

    t.setStyle(style)
    return t


# --- Public API -----------------------------------------------------------

def scan_to_pdf(scan: ScanResult) -> bytes:
    """
    Render the scan result as a PDF and return it as raw bytes.

    Returning bytes (rather than writing to a file) means Streamlit can
    serve the PDF via st.download_button without touching the filesystem.
    """
    styles = _styles()
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=1.6 * cm,
        rightMargin=1.6 * cm,
        topMargin=1.6 * cm,
        bottomMargin=1.6 * cm,
        title="Web Health & SEO Scan Report",
    )

    story: list = []

    # --- Header ---
    story.append(Paragraph("Web Health & SEO Scan Report", styles["title"]))
    story.append(Paragraph(
        f"Site: <b>{scan.root_url}</b><br/>"
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        styles["subtitle"],
    ))

    # --- Health score banner ---
    score = scan.score
    if score is not None:
        grade_color = GRADE_COLORS.get(score.grade, colors.grey)
        score_text = (
            f'<para alignment="center">'
            f'<font color="{grade_color.hexval()}" size="44"><b>{score.score}/100</b></font>'
            f'<br/>'
            f'<font color="{grade_color.hexval()}" size="14"><b>{score.grade}</b></font>'
            f'</para>'
        )
        story.append(Paragraph(score_text, styles["body"]))
        story.append(Spacer(1, 0.5 * cm))

    # --- Summary ---
    story.append(Paragraph("Summary", styles["section"]))
    story.append(_summary_table(scan, styles))
    story.append(Spacer(1, 0.4 * cm))

    # --- Severity breakdown ---
    story.append(Paragraph("Issues by severity", styles["section"]))
    story.append(_severity_breakdown(scan))
    story.append(Spacer(1, 0.4 * cm))

    # --- Issues table ---
    story.append(Paragraph("Detected issues", styles["section"]))
    if scan.issues:
        story.append(_issues_table(scan, styles))
    else:
        story.append(Paragraph(
            "<i>No issues detected. The site looks great.</i>",
            styles["body"],
        ))

    doc.build(story)
    return buf.getvalue()
