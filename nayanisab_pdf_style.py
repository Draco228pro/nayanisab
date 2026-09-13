"""Standard NayaNisab PDF report design.

This module is the single source of truth for the downloadable 4-page PDF.
Every subject uses the same visual language; only the report content changes.
"""

from __future__ import annotations

import io
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    HRFlowable,
    Image,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

PAGE_W, PAGE_H = A4
NAVY = colors.HexColor("#101936")
GREEN = colors.HexColor("#0B6E43")
GREEN_DARK = colors.HexColor("#075333")
GREEN_PALE = colors.HexColor("#EEF7F2")
GREEN_LIGHT = colors.HexColor("#DCEFE4")
RED = colors.HexColor("#B9382D")
RED_PALE = colors.HexColor("#FFF3F1")
AMBER = colors.HexColor("#A66B00")
AMBER_PALE = colors.HexColor("#FFF8E9")
INK = colors.HexColor("#273142")
MUTED = colors.HexColor("#667085")
LINE = colors.HexColor("#DCE3E0")
WHITE = colors.white


def _safe(value: Any, fallback: str = "") -> str:
    if isinstance(value, dict):
        value = " - ".join(_safe(v) for v in value.values() if v not in (None, "", [], {}))
    elif isinstance(value, (list, tuple)):
        value = "; ".join(part for part in (_safe(v) for v in value) if part)
    text = "" if value is None else str(value)
    # ReportLab's built-in Helvetica uses a limited encoding. Some AI-generated
    # text can contain Unicode punctuation such as non-breaking hyphens (U+2011),
    # which render as black boxes in the PDF. Normalise these characters before
    # sending text to Paragraph/Table cells.
    replacements = {
        "\u2010": "-",  # hyphen
        "\u2011": "-",  # non-breaking hyphen (the main source of black boxes)
        "\u2012": "-",  # figure dash
        "\u2013": "-",  # en dash
        "\u2014": "-",  # em dash
        "\u2212": "-",  # minus sign
        "\u2018": "'",  # left single quote
        "\u2019": "'",  # right single quote
        "\u201c": '"',  # left double quote
        "\u201d": '"',  # right double quote
        "\u00a0": " ",  # non-breaking space
        "\u2022": "-",  # bullet
        "\u00b7": "-",  # middle dot
        "\u2026": "...",  # ellipsis
    }
    for source, target in replacements.items():
        text = text.replace(source, target)
    # Final safety pass: replace remaining non-ASCII characters that Helvetica
    # cannot represent with a plain ASCII fallback rather than a black glyph box.
    text = text.encode("latin-1", "replace").decode("latin-1")
    text = re.sub(r"\s+", " ", text).strip()
    return text or fallback




def _as_dict(value: Any) -> dict:
    """Return a dictionary for PDF sections that may be malformed/string values.

    LLM JSON can occasionally return a string where a list item/object was expected.
    The PDF renderer should degrade gracefully instead of failing with:
    'str' object has no attribute 'get'.
    """
    return value if isinstance(value, dict) else {}


def _as_list(value: Any) -> list:
    """Return a list for PDF sections that may be malformed."""
    if isinstance(value, list):
        return value
    if value is None:
        return []
    return [value]

def _clip(text: str, limit: int = 420) -> str:
    text = _safe(text)
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."


def _bullet_text(items: list[Any], limit: int = 5, item_chars: int = 250) -> list[str]:
    out = []
    for item in (items or [])[:limit]:
        if isinstance(item, dict):
            value = item.get("title") or item.get("change") or item.get("name") or item.get("text") or item.get("reason")
        else:
            value = item
        value = _clip(_safe(value), item_chars)
        if value:
            out.append(value)
    return out


def _status_color(status: str):
    s = _safe(status).lower()
    if "immediate" in s or "critical" in s or "high" in s:
        return RED, RED_PALE
    if "mandatory" in s or "medium" in s or "update" in s:
        return AMBER, AMBER_PALE
    return GREEN, GREEN_PALE


def _footer(canvas, doc):
    canvas.saveState()
    canvas.setStrokeColor(LINE)
    canvas.setLineWidth(0.5)
    canvas.line(18 * mm, 13 * mm, PAGE_W - 18 * mm, 13 * mm)
    canvas.setFont("Helvetica", 7.2)
    canvas.setFillColor(MUTED)
    canvas.drawString(18 * mm, 8 * mm, "NayaNisab - Bringing Pakistani curricula up to tomorrow's standards.")
    canvas.drawRightString(PAGE_W - 18 * mm, 8 * mm, f"Page {doc.page} of 4")
    canvas.restoreState()


def _styles():
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle("NNTitle", parent=base["Title"], fontName="Helvetica-Bold", fontSize=20, leading=23, textColor=NAVY, spaceAfter=4),
        "subtitle": ParagraphStyle("NNSubtitle", parent=base["Normal"], fontName="Helvetica", fontSize=9.5, leading=13, textColor=MUTED, spaceAfter=8),
        "h1": ParagraphStyle("NNH1", parent=base["Heading1"], fontName="Helvetica-Bold", fontSize=14, leading=17, textColor=NAVY, spaceBefore=2, spaceAfter=6),
        "h2": ParagraphStyle("NNH2", parent=base["Heading2"], fontName="Helvetica-Bold", fontSize=10.5, leading=13, textColor=GREEN_DARK, spaceBefore=3, spaceAfter=4),
        "body": ParagraphStyle("NNBody", parent=base["BodyText"], fontName="Helvetica", fontSize=8.3, leading=11.6, textColor=INK, spaceAfter=4),
        "small": ParagraphStyle("NNSmall", parent=base["BodyText"], fontName="Helvetica", fontSize=7.1, leading=9.3, textColor=MUTED, spaceAfter=2),
        "tiny": ParagraphStyle("NNTiny", parent=base["BodyText"], fontName="Helvetica", fontSize=6.4, leading=8.1, textColor=MUTED, spaceAfter=1),
        "table": ParagraphStyle("NNTable", parent=base["BodyText"], fontName="Helvetica", fontSize=6.8, leading=8.3, textColor=INK),
        "table_bold": ParagraphStyle("NNTableBold", parent=base["BodyText"], fontName="Helvetica-Bold", fontSize=6.8, leading=8.3, textColor=NAVY),
        # Header cells sit on a dark fill. The Paragraph colour wins over the
        # table's TEXTCOLOR, so header text needs its own white style.
        "table_head": ParagraphStyle("NNTableHead", parent=base["BodyText"], fontName="Helvetica-Bold", fontSize=6.9, leading=8.4, textColor=WHITE),
        "score": ParagraphStyle("NNScore", parent=base["BodyText"], fontName="Helvetica-Bold", fontSize=30, leading=31, textColor=NAVY, alignment=TA_LEFT),
        "score_label": ParagraphStyle("NNScoreLabel", parent=base["BodyText"], fontName="Helvetica-Bold", fontSize=10.5, leading=12.5, textColor=NAVY, alignment=TA_LEFT),
        "callout": ParagraphStyle("NNCallout", parent=base["BodyText"], fontName="Helvetica", fontSize=8.0, leading=11.2, textColor=INK),
    }


def _card(title: str, value: str, width: float, styles, accent=GREEN, background=GREEN_PALE):
    clean_value = _safe(value)
    value_style = styles["score"] if len(clean_value) <= 9 else styles["score_label"]
    data = [[Paragraph(_safe(title).upper(), styles["tiny"])], [Paragraph(clean_value, value_style)]]
    table = Table(data, colWidths=[width], hAlign="LEFT")
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), background),
        ("BOX", (0, 0), (-1, -1), 0.7, accent),
        ("ROUNDEDCORNERS", [7, 7, 7, 7]),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    return table


def _header(logo_path: Path | None, title: str, subtitle: str, styles):
    left = []
    logo_path = Path(logo_path) if logo_path else None
    if logo_path and logo_path.exists():
        img = Image(str(logo_path), width=26 * mm, height=16 * mm)
        img.hAlign = "LEFT"
        left = [img]
    else:
        left = [Paragraph("<b>NayaNisab</b>", styles["h1"])]
    right = [Paragraph(_clip(title, 95), styles["title"]), Paragraph(_clip(subtitle, 150), styles["subtitle"])]
    t = Table([[left[0], right]], colWidths=[31 * mm, PAGE_W - 31 * mm - 36 * mm])
    t.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    return [t, HRFlowable(width="100%", thickness=0.8, color=LINE), Spacer(1, 5)]


def build_curriculum_report(result: dict[str, Any], logo_path: Path | None = None) -> bytes:
    """Create the canonical 4-page NayaNisab report and return PDF bytes."""
    styles = _styles()
    uni = _safe(result.get("university"), "University")
    subject = _safe(result.get("subject"), "Subject")
    score = float(result.get("score", 0) or 0)
    score = max(0, min(100, score))
    band = _safe(result.get("band"), "IMPROVEMENT REQUIRED")
    benchmark = _as_dict(result.get("benchmark", {}))
    dimensions = _as_list(benchmark.get("dimension_scores", []))
    gaps = _as_dict(result.get("gaps", {}))
    recommendations = _as_dict(result.get("recommendations", {}))
    draft = _as_dict(result.get("draft", {}))
    generated = datetime.now().strftime("%d %B %Y")

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=15 * mm,
        bottomMargin=17 * mm,
        title=f"NayaNisab - {subject}",
        author="NayaNisab",
        subject="Curriculum modernisation report",
    )

    story: list[Any] = []

    # PAGE 1 - overview
    story += _header(logo_path, f"{subject} - Curriculum Intelligence Report", f"{uni} | Generated {generated}", styles)
    story.append(Paragraph("Executive overview", styles["h1"]))
    summary = _clip(draft.get("executive_summary") or gaps.get("teacher_message") or "NayaNisab analysed the submitted curriculum and learning objectives against a modern subject-aware benchmark.", 900)
    story.append(Paragraph(summary, styles["body"]))
    story.append(Spacer(1, 3))

    accent, bg = (RED, RED_PALE) if score < 50 else (AMBER, AMBER_PALE) if score <= 80 else (GREEN, GREEN_PALE)
    cards = Table([[
        _card("Modernisation score", f"{score:.0f}/100", 54 * mm, styles, accent, bg),
        _card("Decision band", band, 54 * mm, styles, accent, bg),
        _card("Benchmark areas", str(len(dimensions)), 54 * mm, styles, GREEN, GREEN_PALE),
    ]], colWidths=[57 * mm] * 3)
    cards.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    story.append(cards)
    story.append(Spacer(1, 7))

    story.append(Paragraph("What the score means", styles["h2"]))
    story.append(Paragraph(
        "0-49: high-priority modernisation needs. 50-80: meaningful improvements are required. 81-100: no major benchmark gap was identified, although optional improvements may still be useful. The score is a prototype decision-support heuristic, not accreditation or formal academic approval.",
        styles["callout"],
    ))
    story.append(Spacer(1, 5))

    story.append(Paragraph("Strongest and weakest benchmark areas", styles["h2"]))
    dim_rows = []
    safe_dimensions = []
    for raw_d in dimensions:
        d = _as_dict(raw_d)
        if not d and raw_d not in (None, ""):
            d = {"name": _safe(raw_d), "score": 0, "missing": "No structured benchmark detail returned."}
        safe_dimensions.append(d)
    for d in sorted(safe_dimensions, key=lambda x: float(x.get("score", 0) or 0), reverse=True)[:6]:
        s = float(d.get("score", 0) or 0)
        dim_rows.append([Paragraph(_clip(d.get("name", "Dimension"), 65), styles["table_bold"]), Paragraph(f"{s:.0f}/100", styles["table"]), Paragraph(_clip(d.get("missing") or d.get("evidence") or "No detail returned.", 125), styles["table"])])
    if dim_rows:
        dt = Table([[Paragraph("Benchmark area", styles["table_head"]), Paragraph("Score", styles["table_head"]), Paragraph("Key reading", styles["table_head"])] ] + dim_rows, colWidths=[47 * mm, 18 * mm, 104 * mm], repeatRows=1)
        dt.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), NAVY), ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
            ("GRID", (0, 0), (-1, -1), 0.3, LINE), ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, GREEN_PALE]),
            ("LEFTPADDING", (0, 0), (-1, -1), 5), ("RIGHTPADDING", (0, 0), (-1, -1), 5),
            ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(dt)
    else:
        story.append(Paragraph("No benchmark dimensions were returned.", styles["body"]))

    story.append(PageBreak())

    # PAGE 2 - gap diagnosis
    story += _header(logo_path, f"Where the curriculum gap begins", f"{uni} | {subject}", styles)
    first_gap = _as_dict(gaps.get("first_gap"))
    story.append(Paragraph("First meaningful gap", styles["h1"]))
    if first_gap:
        fg = Table([[Paragraph("Starting point", styles["table_bold"]), Paragraph(_clip(first_gap.get("course_or_stage"), 210), styles["table"])],
                    [Paragraph("What is missing", styles["table_bold"]), Paragraph(_clip(first_gap.get("what_is_missing"), 440), styles["table"])],
                    [Paragraph("Why it matters", styles["table_bold"]), Paragraph(_clip(first_gap.get("why_it_matters"), 440), styles["table"])]], colWidths=[37 * mm, 132 * mm])
        fg.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (0, -1), GREEN_PALE), ("BOX", (0, 0), (-1, -1), 0.5, LINE),
            ("INNERGRID", (0, 0), (-1, -1), 0.25, LINE), ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 6), ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ]))
        story.append(fg)
    else:
        story.append(Paragraph(_clip(benchmark.get("first_gap_point"), 600) or "The analysis did not identify a confident first gap point.", styles["body"]))
    story.append(Spacer(1, 7))

    story.append(Paragraph("Priority gaps", styles["h2"]))
    critical = _as_list(gaps.get("critical_gaps", []))
    gap_headers = ["Gap", "Severity", "Recommended direction"]
    gap_weights = [53.0, 28.0, 88.0]
    gap_data = []
    for raw_g in critical[:5]:
        g = _as_dict(raw_g)
        if not g:
            # A plain-text gap carries no severity or direction of its own:
            # leave those cells empty instead of inventing a rating.
            if raw_g not in (None, ""):
                gap_data.append([_safe(raw_g), "", ""])
            continue
        gap_data.append([
            _safe(g.get("title") or g.get("gap")),
            _safe(g.get("severity")),
            _safe(g.get("recommended_change") or g.get("desired_state") or g.get("why_now") or g.get("action")),
        ])
    keep = [i for i in range(3) if any(row[i].strip() for row in gap_data)]
    if len(keep) == 1 and keep[0] == 0:
        gap_headers[0] = "Priority gap"
    if gap_data and keep:
        total = sum(gap_weights[i] for i in keep)
        widths = [(gap_weights[i] / total) * 169.0 * mm for i in keep]
        limits = [int(w / mm * 3.8) for w in widths]
        gap_rows = [[Paragraph(gap_headers[i], styles["table_head"]) for i in keep]]
        for row in gap_data:
            gap_rows.append([
                Paragraph(_clip(row[i], limits[n]), styles["table_bold"] if i == 0 else styles["table"])
                for n, i in enumerate(keep)
            ])
        gt = Table(gap_rows, colWidths=widths, repeatRows=1)
        gt.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), NAVY), ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
            ("GRID", (0, 0), (-1, -1), 0.3, LINE), ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, colors.HexColor("#FAFCFB")]),
            ("LEFTPADDING", (0, 0), (-1, -1), 5), ("RIGHTPADDING", (0, 0), (-1, -1), 5),
            ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]))
        story.append(gt)
    else:
        story.append(Paragraph("No critical gaps were returned.", styles["body"]))
    story.append(Spacer(1, 6))

    story.append(Paragraph("Top benchmark gaps", styles["h2"]))
    top_gaps = benchmark.get("top_global_gaps", []) or []
    for item in top_gaps[:4]:
        title = _safe(item.get("title"), "Gap") if isinstance(item, dict) else _safe(item, "Gap")
        reason = _safe(item.get("reason"), "") if isinstance(item, dict) else ""
        courses = item.get("affected_courses", []) if isinstance(item, dict) else []
        line = f"<b>{_clip(title, 95)}</b>"
        if reason:
            line += f" - {_clip(reason, 190)}"
        if courses:
            line += f" <font color='#667085'>Areas: {_clip(', '.join(map(str, courses[:4])), 150)}</font>"
        story.append(Paragraph(line, styles["body"]))

    story.append(Spacer(1, 5))
    story.append(Paragraph("Teacher-facing interpretation", styles["h2"]))
    story.append(Paragraph(_clip(gaps.get("teacher_message"), 620) or "NayaNisab identified areas where the submitted curriculum may need updating for current academic and professional expectations.", styles["callout"]))

    story.append(PageBreak())

    # PAGE 3 - recommendations
    story += _header(logo_path, "Recommended curriculum improvements", f"{uni} | {subject}", styles)
    story.append(Paragraph("Priority actions", styles["h1"]))
    recs = _as_list(recommendations.get("recommendations", []))
    rec_rows = [[Paragraph("Priority", styles["table_head"]), Paragraph("Change", styles["table_head"]), Paragraph("Where / how", styles["table_head"])]]
    for raw_r in recs[:6]:
        r = _as_dict(raw_r)
        if not r and raw_r not in (None, ""):
            r = {"priority": "Mandatory", "change": _safe(raw_r), "where_to_apply": "Programme-level review"}
        priority = _safe(r.get("priority"), "Mandatory")
        change = r.get("change") or r.get("title")
        where = _safe(r.get("where_to_apply"))
        how = _safe(r.get("implementation") or r.get("action"))
        detail = where + (" - " if where and how else "") + how
        rec_rows.append([Paragraph(priority, styles["table_bold"]), Paragraph(_clip(change, 145), styles["table"]), Paragraph(_clip(detail or "Programme-level review", 180), styles["table"])])
    if len(rec_rows) > 1:
        rt = Table(rec_rows, colWidths=[25 * mm, 67 * mm, 77 * mm], repeatRows=1)
        rt.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), NAVY), ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
            ("GRID", (0, 0), (-1, -1), 0.3, LINE), ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, GREEN_PALE]),
            ("LEFTPADDING", (0, 0), (-1, -1), 5), ("RIGHTPADDING", (0, 0), (-1, -1), 5),
            ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]))
        story.append(rt)
    else:
        story.append(Paragraph("No recommendations were returned.", styles["body"]))

    story.append(Spacer(1, 8))
    story.append(Paragraph("Course and programme updates", styles["h2"]))
    updates = _as_list(recommendations.get("proposed_course_updates", []))
    upd_headers = ["Course / area", "Updated focus", "New / strengthened topics", "Practical / assessment"]
    upd_weights = [37.0, 46.0, 45.0, 42.0]
    upd_data = []
    for raw_u in updates[:5]:
        u = _as_dict(raw_u)
        if not u:
            # Compact payloads send one sentence per update: show it in full
            # rather than padding three columns with placeholder text.
            if raw_u not in (None, ""):
                upd_data.append([_safe(raw_u), "", "", ""])
            continue
        topics = _as_list(u.get("new_topics", []))
        practical = _safe(u.get("practical_component"))
        assess = _safe(u.get("assessment_update"))
        upd_data.append([
            _safe(u.get("course") or u.get("course_or_area")),
            _safe(u.get("updated_focus") or u.get("current_focus")),
            ", ".join(_safe(x) for x in topics[:4]),
            practical + (" | " if practical and assess else "") + assess,
        ])
    # Keep only the columns that actually carry content, so the table never
    # renders half-empty, and give the freed width back to what remains.
    keep = [i for i in range(4) if any(row[i].strip() for row in upd_data)]
    if len(keep) == 1 and keep[0] == 0:
        upd_headers[0] = "Proposed update"
    if upd_data and keep:
        total = sum(upd_weights[i] for i in keep)
        widths = [(upd_weights[i] / total) * 170.0 * mm for i in keep]
        limits = [int(w / mm * 3.8) for w in widths]
        upd_rows = [[Paragraph(upd_headers[i], styles["table_head"]) for i in keep]]
        for row in upd_data:
            upd_rows.append([
                Paragraph(_clip(row[i], limits[n]), styles["table_bold"] if i == 0 else styles["table"])
                for n, i in enumerate(keep)
            ])
        ut = Table(upd_rows, colWidths=widths, repeatRows=1)
        ut.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), GREEN_DARK), ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
            ("GRID", (0, 0), (-1, -1), 0.3, LINE), ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, colors.HexColor("#FAFCFB")]),
            ("LEFTPADDING", (0, 0), (-1, -1), 4), ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(ut)

    story.append(Spacer(1, 8))
    story.append(Paragraph("Implementation principle", styles["h2"]))
    story.append(Paragraph(_clip("Prefer strengthening existing courses and practical components before creating many new courses. Retain strong foundational learning, then add durable modern skills, current tools, applied work, and assessment methods where the benchmark indicates a gap.", 520), styles["callout"]))

    story.append(PageBreak())

    # PAGE 4 - proposed revised curriculum + change log
    story += _header(logo_path, "Proposed modernised curriculum", f"{uni} | {subject}", styles)
    story.append(Paragraph(_clip(draft.get("title"), 100) or "Proposed Modernised Curriculum Draft", styles["h1"]))
    story.append(Paragraph(_clip(draft.get("executive_summary"), 650), styles["body"]))
    story.append(Spacer(1, 3))

    revised = _as_list(draft.get("revised_curriculum", []))
    rows = [[Paragraph("Course / area", styles["table_head"]), Paragraph("Status", styles["table_head"]), Paragraph("Updated scope", styles["table_head"]), Paragraph("Practical work / assessment", styles["table_head"])]]
    for raw_r in revised[:6]:
        r = _as_dict(raw_r)
        if not r and raw_r not in (None, ""):
            r = {"course_or_area": _safe(raw_r), "status": "Update", "updated_scope": "Review and modernise this area."}
        practical = _safe(r.get("practical_work"))
        assessment = _safe(r.get("assessment"))
        rows.append([
            Paragraph(_clip(r.get("course_or_area"), 80), styles["table_bold"]),
            Paragraph(_safe(r.get("status"), "Update"), styles["table"]),
            Paragraph(_clip(r.get("updated_scope"), 190), styles["table"]),
            Paragraph(_clip(practical + (" | " if practical and assessment else "") + assessment, 170), styles["table"]),
        ])
    if len(rows) > 1:
        table = Table(rows, colWidths=[37 * mm, 24 * mm, 63 * mm, 46 * mm], repeatRows=1)
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), NAVY), ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
            ("GRID", (0, 0), (-1, -1), 0.3, LINE), ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, GREEN_PALE]),
            ("LEFTPADDING", (0, 0), (-1, -1), 4), ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(table)
    else:
        story.append(Paragraph("A revised curriculum table was not returned by the analysis.", styles["body"]))

    story.append(Spacer(1, 6))
    story.append(Paragraph("Change log", styles["h2"]))
    changes = _as_list(draft.get("change_log", []))
    change_rows = [[Paragraph("Change", styles["table_head"]), Paragraph("From", styles["table_head"]), Paragraph("To", styles["table_head"]), Paragraph("Reason", styles["table_head"])]]
    for raw_c in changes[:4]:
        c = _as_dict(raw_c)
        if not c and raw_c not in (None, ""):
            c = {"change": _safe(raw_c), "old_state": "Current curriculum", "new_state": "Modernised proposal", "reason": "Benchmark-driven improvement."}
        change_rows.append([
            Paragraph(_clip(c.get("change"), 80), styles["table_bold"]),
            Paragraph(_clip(c.get("old_state"), 95), styles["table"]),
            Paragraph(_clip(c.get("new_state"), 95), styles["table"]),
            Paragraph(_clip(c.get("reason"), 100), styles["table"]),
        ])
    if len(change_rows) > 1:
        ct = Table(change_rows, colWidths=[37 * mm, 45 * mm, 45 * mm, 43 * mm], repeatRows=1)
        ct.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), GREEN_DARK), ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
            ("GRID", (0, 0), (-1, -1), 0.3, LINE), ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, colors.HexColor("#FAFCFB")]),
            ("LEFTPADDING", (0, 0), (-1, -1), 4), ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(ct)

    story.append(Spacer(1, 5))
    disclaimer = _safe(draft.get("disclaimer"), "AI-generated proposal requiring academic review and institutional approval.")
    story.append(Paragraph(f"<b>Review status:</b> {_clip(disclaimer, 280)}", styles["small"]))

    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    data = buffer.getvalue()
    buffer.close()
    return data
