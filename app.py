from datetime import datetime
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

from ai_workflow import MODEL_DEFAULT, flatten_text, run_workflow
from benchmarks import score_band
from nayanisab_pdf_style import build_curriculum_report
from pdf_utils import extract_pdf_text

BASE_DIR = Path(__file__).parent
LOGO_PATH = BASE_DIR / "NayaNisab logo.jpg"


# --- tolerant readers -------------------------------------------------------
# The AI workflow returns compact JSON where several lists hold plain strings
# (gaps, course updates, course inventory), while older/richer payloads held
# dictionaries. These helpers render either shape instead of raising
# "'str' object has no attribute 'get'".

def _field(item, *keys, default=""):
    """Read a key from a dict item; return the default for anything else."""
    if isinstance(item, dict):
        for key in keys:
            value = item.get(key)
            if value not in (None, "", [], {}):
                return flatten_text(value) or default
    return default


def _label(item, *keys, default=""):
    """Headline text for an item that may be a plain string or a dict."""
    if isinstance(item, str):
        return flatten_text(item).strip() or default
    if isinstance(item, dict):
        return _field(item, *keys, default="") or flatten_text(item) or default
    return flatten_text(item) or default


def _sublist(item, key):
    """A list of strings from a dict item; empty for anything else."""
    value = item.get(key) if isinstance(item, dict) else None
    if not isinstance(value, list):
        return []
    return [text for text in (flatten_text(x) for x in value) if text]

st.set_page_config(
    page_title="NayaNisab | Curriculum Intelligence",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
<style>
:root { --navy:#101936; --green:#087443; --paper:#F7FAF8; }
.block-container { max-width: 1380px; padding-top: 1.2rem; padding-bottom: 3rem; }
[data-testid="stSidebar"] { background: #f5f8f6; }
.hero { background: linear-gradient(120deg,#ffffff 0%,#f3faf6 55%,#eaf5ef 100%); border:1px solid #dce9e0; border-radius:22px; padding:26px 30px; margin-bottom:18px; }
.eyebrow { text-transform:uppercase; letter-spacing:.14em; font-size:.74rem; font-weight:800; color:#087443; }
.hero h1 { color:#101936; font-size:2.6rem; margin:5px 0 4px; }
.hero p { color:#4b5563; font-size:1.02rem; margin:0; }
.metric-card { background:white; border:1px solid #e5ebe7; border-radius:18px; padding:18px; box-shadow:0 5px 22px rgba(16,25,54,.05); }
.score { font-size:3.6rem; line-height:1; font-weight:850; color:#101936; }
.score-label { font-size:.8rem; font-weight:800; letter-spacing:.12em; color:#5e6a71; text-transform:uppercase; }
.warning { border-left:5px solid #d33c2d; background:#fff5f3; padding:15px 18px; border-radius:11px; }
.improve { border-left:5px solid #d89a00; background:#fffaf0; padding:15px 18px; border-radius:11px; }
.future { border-left:5px solid #087443; background:#f1fbf5; padding:15px 18px; border-radius:11px; }
.small { color:#667085; font-size:.86rem; }
.card { background:#ffffff; border:1px solid #e5ebe7; border-radius:16px; padding:18px; height:100%; }
.stButton > button { border-radius:12px; font-weight:750; }
</style>
""",
    unsafe_allow_html=True,
)


def get_secret(name: str, default: str = ""):
    try:
        return st.secrets.get(name, default)
    except Exception:
        return default


def render_logo():
    if LOGO_PATH.exists():
        st.image(str(LOGO_PATH), width=235)
    else:
        st.markdown("### NayaNisab")
        st.caption("Bringing Pakistani curricula up to tomorrow's standards.")


def render_band(score: float):
    b = score_band(score)
    cls = "warning" if score < 50 else "improve" if score <= 80 else "future"
    st.markdown(
        f'<div class="{cls}"><b>{b["label"]}</b> — {b["headline"]}<br><span class="small">{b["action"]}</span></div>',
        unsafe_allow_html=True,
    )


with st.sidebar:
    render_logo()
    st.markdown("---")
    st.markdown("**NayaNisab**")
    st.caption("AI-powered curriculum intelligence for Pakistani universities.")
    st.markdown("**What NayaNisab does**")
    st.caption("Understand the submitted curriculum")
    st.caption("Compare it with modern benchmarks")
    st.caption("Identify where important gaps begin")
    st.caption("Recommend practical improvements")
    st.caption("Prepare a teacher-reviewable updated curriculum")
    st.markdown("---")
    st.caption("The score is a decision-support heuristic, not accreditation or formal academic approval.")

st.markdown(
    '<div class="hero"><div class="eyebrow">Curriculum intelligence • Pakistan</div><h1>NayaNisab</h1><p>Bringing Pakistani curricula up to tomorrow’s standards.</p></div>',
    unsafe_allow_html=True,
)

if "result" not in st.session_state:
    st.session_state.result = None

if st.session_state.result is None:
    st.subheader("Analyse a university curriculum")
    st.write(
        "Enter the university and subject, then upload the curriculum and learning objectives. NayaNisab will assess the curriculum against a subject-aware modern benchmark, explain the most important gaps, and prepare an updated draft for teacher review."
    )

    c1, c2 = st.columns([1.25, 1])
    with c1:
        university = st.text_input(
            "University name",
            placeholder="e.g., International Islamic University Islamabad",
        )
        subject = st.text_input(
            "Subject / programme",
            placeholder="e.g., Power Distribution and Utilization",
        )
    with c2:
        curriculum_file = st.file_uploader(
            "Official curriculum PDF", type=["pdf"], key="curriculum"
        )
        objectives_file = st.file_uploader(
            "Learning objectives PDF", type=["pdf"], key="objectives"
        )

    st.markdown("### What NayaNisab returns")
    cols = st.columns(5)
    for col, title, body in zip(
        cols,
        [
            "Modernisation score",
            "Gap starting point",
            "Priority recommendations",
            "Updated curriculum",
            "Change log",
        ],
        [
            "A transparent 0–100 alignment score.",
            "The first meaningful point where modernisation pressure appears.",
            "Immediate, mandatory and optional improvement actions.",
            "A structured proposed curriculum for teacher review.",
            "A clear record of what changed and why.",
        ],
    ):
        with col:
            st.markdown(
                f'<div class="card"><b>{title}</b><p class="small">{body}</p></div>',
                unsafe_allow_html=True,
            )

    analyze = st.button(
        "🚀 Analyse & Modernise Curriculum", type="primary", use_container_width=True
    )
    if analyze:
        if not university.strip():
            st.error("Enter the university name first.")
        elif not subject.strip():
            st.error("Enter the subject / programme first.")
        elif not curriculum_file or not objectives_file:
            st.error("Upload both PDFs before starting the analysis.")
        else:
            api_key = get_secret("GROQ_API_KEY")
            if not api_key:
                st.error("GROQ_API_KEY is missing. Add it in Streamlit Cloud → Settings → Secrets.")
            else:
                progress = st.progress(0, text="Preparing your documents...")
                try:
                    with st.spinner("Reading the uploaded PDFs..."):
                        curriculum_text, c_pages, _ = extract_pdf_text(curriculum_file)
                        objectives_text, o_pages, _ = extract_pdf_text(objectives_file)

                    def report(p, msg):
                        progress.progress(p, text=msg)

                    result = run_workflow(
                        api_key,
                        university.strip(),
                        subject.strip(),
                        curriculum_text,
                        objectives_text,
                        progress=report,
                    )
                    st.session_state.result = result
                    st.session_state.pdf_report = None
                    progress.empty()
                    st.rerun()
                except Exception as exc:
                    progress.empty()
                    st.error(f"Analysis failed: {exc}")
                    st.caption("Please check that both PDFs contain selectable text and try again.")

else:
    result = st.session_state.result
    score = float(result["score"])
    st.markdown(f"### {result['university']} · {result['subject']}")
    st.caption(f"Analysis completed {datetime.now().strftime('%d %b %Y, %H:%M')}")

    a, b, c = st.columns([1, 1, 1])
    with a:
        st.markdown(
            f'<div class="metric-card"><div class="score">{score:.0f}</div><div class="score-label">Modernisation score / 100</div></div>',
            unsafe_allow_html=True,
        )
    with b:
        high = sum(1 for d in result["benchmark"]["dimension_scores"] if d["score"] < 50)
        mid = sum(1 for d in result["benchmark"]["dimension_scores"] if 50 <= d["score"] <= 80)
        st.markdown(
            f'<div class="metric-card"><b style="font-size:1.6rem">{high}</b><div class="score-label">High-gap domains</div><br><b>{mid}</b> domains require improvement</div>',
            unsafe_allow_html=True,
        )
    with c:
        st.markdown(
            '<div class="metric-card"><b>Teacher decision</b><p class="small">Review the proposed changes and seek institutional approval before formal curriculum adoption.</p></div>',
            unsafe_allow_html=True,
        )

    render_band(score)
    st.write("")

    tab1, tab2, tab3, tab4, tab5 = st.tabs(
        ["📊 Dashboard", "🧭 Gap map", "🛠 Recommendations", "📘 Updated draft", "🔎 Evidence"]
    )

    with tab1:
        dims = pd.DataFrame(result["benchmark"]["dimension_scores"])
        fig = px.bar(
            dims.sort_values("score"),
            x="score",
            y="name",
            orientation="h",
            range_x=[0, 100],
            text="score",
        )
        fig.update_traces(texttemplate="%{text:.0f}", textposition="outside")
        fig.update_layout(
            height=540,
            margin=dict(l=10, r=20, t=20, b=20),
            xaxis_title="Alignment score",
            yaxis_title="",
        )
        st.plotly_chart(fig, use_container_width=True)
        note = result["benchmark"].get("benchmark_note", "")
        if note:
            st.caption(note)

    with tab2:
        st.markdown("#### Where does the gap begin?")
        st.info(
            _label(
                result["benchmark"].get("first_gap_point"),
                default="The analysis could not confidently identify a first gap point.",
            )
        )
        st.markdown("#### Top global gaps")
        for gap in result["benchmark"].get("top_global_gaps", []):
            reason = _field(gap, "reason")
            st.markdown(f"**{_label(gap, 'title', default='Gap')}**" + (f" — {reason}" if reason else ""))
            courses = _sublist(gap, "affected_courses")
            if courses:
                st.caption("Affected areas: " + ", ".join(courses))

        st.markdown("#### Domain-by-domain diagnosis")
        for d in sorted(result["benchmark"]["dimension_scores"], key=lambda x: x["score"]):
            with st.expander(f"{d['name']} · {d['score']:.0f}/100 · {d['status']}"):
                st.write("**Evidence found:**", d["evidence"])
                st.write("**Missing / weak:**", d["missing"])
                st.caption(f"Priority: {d['priority']}")

        if result.get("gaps", {}).get("teacher_message"):
            st.markdown("#### Teacher-facing explanation")
            st.write(_label(result["gaps"]["teacher_message"]))

        if result.get("gaps", {}).get("first_gap"):
            fg = result["gaps"]["first_gap"]
            st.markdown("#### First meaningful gap")
            if isinstance(fg, dict):
                st.markdown(f"**{_field(fg, 'course_or_stage')}**")
                st.write(_field(fg, "what_is_missing"))
                st.caption(_field(fg, "why_it_matters"))
            else:
                st.write(str(fg))

    with tab3:
        recs = result.get("recommendations", {}).get("recommendations", [])
        if not recs:
            st.info("No recommendations were returned.")
        else:
            for rec in recs:
                priority = _field(rec, "priority", default="Mandatory")
                icon = "🔴" if priority == "Immediate" else "🟠" if priority == "Mandatory" else "🟢"
                title = _label(rec, "title", "change", default="Curriculum change")
                with st.expander(f"{icon} {priority} — {title}"):
                    where = _field(rec, "where_to_apply")
                    why = _field(rec, "reason")
                    how = _field(rec, "action", "implementation")
                    if where:
                        st.write("**Where:**", where)
                    if why:
                        st.write("**Why:**", why)
                    if how:
                        st.write("**How:**", how)
                    if not (where or why or how):
                        st.write("Apply this change at programme level during the next review.")

        st.markdown("#### Proposed course updates")
        updates = result.get("recommendations", {}).get("proposed_course_updates", [])
        for update in updates:
            st.markdown(f"**{_label(update, 'course', default='Course')}**")
            focus = _field(update, "updated_focus", "current_focus")
            if focus:
                st.write(focus)
            topics = _sublist(update, "new_topics")
            if topics:
                st.caption("New / strengthened topics: " + ", ".join(topics))

    with tab4:
        draft = result.get("draft", {})
        st.markdown(f"### {draft.get('title', 'Proposed Modernised Curriculum Draft')}")
        st.write(_label(draft.get("executive_summary", "")))
        if draft.get("principles"):
            st.markdown("#### Principles")
            for principle in draft["principles"]:
                st.write("• " + _label(principle))

        revised = [r for r in draft.get("revised_curriculum", []) if isinstance(r, dict)]
        if revised:
            table = pd.DataFrame(revised)
            display_cols = [
                c for c in [
                    "course_or_area",
                    "status",
                    "updated_scope",
                    "practical_work",
                    "assessment",
                ] if c in table.columns
            ]
            st.dataframe(table[display_cols], use_container_width=True, hide_index=True)

        st.markdown("#### Change log")
        for change in draft.get("change_log", []):
            st.markdown(f"**{_label(change, 'change', default='Change')}**")
            detail = " · ".join(
                part for part in [
                    f"Old: {_field(change, 'old_state')} → New: {_field(change, 'new_state')}"
                    if _field(change, "old_state") or _field(change, "new_state") else "",
                    f"Reason: {_field(change, 'reason')}" if _field(change, "reason") else "",
                ] if part
            )
            if detail:
                st.caption(detail)
        if draft.get("teacher_review_points"):
            st.markdown("#### Teacher review points")
            for point in draft["teacher_review_points"]:
                st.write("• " + _label(point))
        st.warning(
            draft.get(
                "disclaimer",
                "AI-generated proposal requiring academic review and institutional approval.",
            )
        )

    with tab5:
        st.markdown("#### What NayaNisab used")
        structure = result.get("structure", {})
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**Course inventory**")
            for course in structure.get("course_inventory", [])[:25]:
                level = _field(course, "level_or_semester")
                st.write(f"• {_label(course, 'course', default='Unknown')}" + (f" — {level}" if level else ""))
        with col2:
            st.markdown("**Tools / technologies detected**")
            tools = structure.get("tools_and_technologies", [])
            st.write(", ".join(_label(t) for t in tools[:40]) if tools else "No explicit technologies detected.")

        st.markdown("#### Evidence / uncertainty")
        if structure.get("uncertainties"):
            for item in structure["uncertainties"]:
                st.write("• " + _label(item))
        else:
            st.write("No major extraction uncertainty was flagged.")

    st.markdown("---")
    download_col, new_col = st.columns([2, 1])
    with download_col:
        if st.session_state.get("pdf_report") is None:
            try:
                st.session_state.pdf_report = build_curriculum_report(result, LOGO_PATH)
            except Exception as exc:
                st.session_state.pdf_report_error = str(exc)
        if st.session_state.get("pdf_report"):
            st.download_button(
                "⬇️ Download NayaNisab report (4-page PDF)",
                data=st.session_state.pdf_report,
                file_name=f"NayaNisab_{result['subject'].replace(' ', '_')}_Curriculum_Report.pdf",
                mime="application/pdf",
                use_container_width=True,
            )
            st.caption("Standard NayaNisab report format. The PDF is designed for teacher review and institutional discussion.")
        elif st.session_state.get("pdf_report_error"):
            st.error(f"Could not prepare the PDF report: {st.session_state.pdf_report_error}")
    with new_col:
        if st.button("↩️ Start a new analysis", use_container_width=True):
            st.session_state.result = None
            st.session_state.pdf_report = None
            st.session_state.pdf_report_error = None
            st.rerun()
