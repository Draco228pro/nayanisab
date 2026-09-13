from datetime import datetime
from pathlib import Path

import pandas as pd
import plotly.express as px
import requests
import streamlit as st
from streamlit_lottie import st_lottie

from ai_workflow import MODEL_DEFAULT, flatten_text, run_workflow
from benchmarks import score_band
from nayanisab_pdf_style import build_curriculum_report
from pdf_utils import extract_pdf_text

BASE_DIR = Path(__file__).parent
LOGO_PATH = BASE_DIR / "NayaNisab logo.jpg"
STYLE_PATH = BASE_DIR / "style.css"

# --- Tolerant readers -------------------------------------------------------
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


@st.cache_data(show_spinner=False)
def load_lottie_url(url: str):
    """Fetch and cache lottie animations."""
    try:
        r = requests.get(url, timeout=5)
        return r.json() if r.status_code == 200 else None
    except Exception:
        return None


# --- Page Config & Styling ---------------------------------------------------
st.set_page_config(
    page_title="NayaNisab | Curriculum Intelligence",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded",
)

if STYLE_PATH.exists():
    with open(STYLE_PATH, "r", encoding="utf-8") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)


def get_secret(name: str, default: str = ""):
    try:
        return st.secrets.get(name, default)
    except Exception:
        return default


def render_logo():
    if LOGO_PATH.exists():
        st.image(str(LOGO_PATH), width=220)
    else:
        st.markdown("### NayaNisab")
        st.caption("Bringing Pakistani curricula up to tomorrow's standards.")


def render_band(score: float):
    b = score_band(score)
    cls = "band-warning" if score < 50 else "band-improve" if score <= 80 else "band-future"
    st.markdown(
        f'<div class="{cls} animate-entrance"><b>{b["label"]}</b> — {b["headline"]}<br><span style="color: #64748b; font-size: 0.88rem;">{b["action"]}</span></div>',
        unsafe_allow_html=True,
    )


# --- Sidebar -----------------------------------------------------------------
with st.sidebar:
    render_logo()
    st.markdown("---")
    st.markdown("**NayaNisab Engine**")
    st.caption("AI-powered curriculum intelligence for Pakistani higher education institutions.")
    st.markdown("**Pipeline Workflow**")
    st.caption("1. Understand syllabus structure")
    st.caption("2. Compare against international standards")
    st.caption("3. Identify critical baseline gaps")
    st.caption("4. Recommend action items")
    st.caption("5. Generate updated curriculum proposal")
    st.markdown("---")
    st.caption("The score is a heuristic decision-support system, not formal academic accreditation.")

# --- App Body ----------------------------------------------------------------
st.markdown(
    """
    <div class="hero-container animate-entrance">
        <div class="hero-tag">Curriculum Intelligence • Pakistan</div>
        <h1 class="hero-title">NayaNisab</h1>
        <p class="hero-subtitle">Modernizing higher education curricula with precision gap analysis.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

if "result" not in st.session_state:
    st.session_state.result = None

# --- Upload & Analysis Screen ------------------------------------------------
if st.session_state.result is None:
    left_col, right_col = st.columns([1.6, 1])

    with left_col:
        st.markdown("### 📋 Upload Curriculum Dossier")
        st.write(
            "Provide the basic academic details along with both syllabus and learning objective documents to initiate benchmark matching."
        )

        c1, c2 = st.columns(2)
        with c1:
            university = st.text_input(
                "University Name",
                placeholder="e.g., NUST Islamabad",
            )
        with c2:
            subject = st.text_input(
                "Subject / Programme",
                placeholder="e.g., Power Distribution & Utilization",
            )

        curriculum_file = st.file_uploader(
            "Official Curriculum PDF", type=["pdf"], key="curriculum"
        )
        objectives_file = st.file_uploader(
            "Learning Objectives PDF", type=["pdf"], key="objectives"
        )

    with right_col:
        st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
        anim_data = load_lottie_url("https://assets10.lottiefiles.com/packages/lf20_1a8dx7zj.json")
        if anim_data:
            st_lottie(anim_data, height=270, key="doc_anim")

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("### Output Deliverables")
    cols = st.columns(5)
    for col, title, body in zip(
        cols,
        [
            "Modernisation Score",
            "Gap Point Detection",
            "Prioritized Steps",
            "Structured Draft",
            "Auditable Change Log",
        ],
        [
            "0–100 alignment score mapped to industry domains.",
            "The exact structural point where obsolescence emerges.",
            "Immediate, mandatory, and long-term improvements.",
            "A ready-to-circulate modernization curriculum.",
            "Contextual line-item justifications for your board.",
        ],
    ):
        with col:
            st.markdown(
                f'<div class="content-card"><b>{title}</b><p style="color: #64748b; font-size: 0.85rem; margin-top: 6px;">{body}</p></div>',
                unsafe_allow_html=True,
            )

    st.markdown("<br>", unsafe_allow_html=True)
    analyze = st.button(
        "🚀 Run Diagnostic & Modernize Curriculum", type="primary", use_container_width=True
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
                    with st.spinner("Extracting contents from uploaded PDFs..."):
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

# --- Results Presentation ----------------------------------------------------
else:
    result = st.session_state.result
    score = float(result["score"])

    head_col, lottie_col = st.columns([3.5, 0.8])
    with head_col:
        st.markdown(f"## {result['university']} — {result['subject']}")
        st.caption(f"Analysis successfully conducted on {datetime.now().strftime('%d %b %Y, %H:%M')}")
    with lottie_col:
        success_anim = load_lottie_url("https://assets5.lottiefiles.com/packages/lf20_jbrw3hcz.json")
        if success_anim:
            st_lottie(success_anim, height=75, loop=False, key="success_anim")

    a, b, c = st.columns([1, 1.2, 1.2])
    with a:
        st.markdown(
            f'<div class="metric-box animate-entrance"><div class="metric-big-num">{score:.0f}</div><div class="metric-label-tag">Modernisation Score / 100</div></div>',
            unsafe_allow_html=True,
        )
    with b:
        high = sum(1 for d in result["benchmark"]["dimension_scores"] if d["score"] < 50)
        mid = sum(1 for d in result["benchmark"]["dimension_scores"] if 50 <= d["score"] <= 80)
        st.markdown(
            f'<div class="metric-box animate-entrance"><div class="metric-big-num" style="color: #ef4444;">{high}</div><div class="metric-label-tag">High Gap Domains</div><div style="font-size:0.86rem; color:#64748b; margin-top:4px;"><b>{mid}</b> additional domains require review</div></div>',
            unsafe_allow_html=True,
        )
    with c:
        st.markdown(
            '<div class="metric-box animate-entrance"><b>Institutional Guidance</b><p style="color:#64748b; font-size:0.86rem; margin-top:6px;">Draft findings should be deliberated within the departmental Board of Studies prior to statutory updates.</p></div>',
            unsafe_allow_html=True,
        )

    st.write("")
    render_band(score)
    st.write("")

    tab1, tab2, tab3, tab4, tab5 = st.tabs(
        ["📊 Dashboard", "🧭 Gap Map", "🛠 Recommendations", "📘 Updated Draft", "🔎 Evidence"]
    )

    with tab1:
        dims = pd.DataFrame(result["benchmark"]["dimension_scores"])
        dims_sorted = dims.sort_values("score", ascending=True)

        fig = px.bar(
            dims_sorted,
            x="score",
            y="name",
            orientation="h",
            range_x=[0, 100],
            text="score",
            color="score",
            color_continuous_scale=[(0.0, "#ef4444"), (0.5, "#f59e0b"), (1.0, "#10b981")],
        )
        fig.update_traces(texttemplate="%{text:.0f}", textposition="outside", cliponaxis=False)
        fig.update_layout(
            height=460,
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=10, r=40, t=20, b=20),
            xaxis=dict(title="Alignment Score (%)", showgrid=True, gridcolor="#e2e8f0"),
            yaxis=dict(title="", tickfont=dict(size=12)),
            coloraxis_showscale=False,
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

        st.markdown("#### Top Global Gaps")
        for gap in result["benchmark"].get("top_global_gaps", []):
            reason = _field(gap, "reason")
            st.markdown(f"**{_label(gap, 'title', default='Gap')}**" + (f" — {reason}" if reason else ""))
            courses = _sublist(gap, "affected_courses")
            if courses:
                st.caption("Affected areas: " + ", ".join(courses))

        st.markdown("<br>#### Dimension Diagnoses", unsafe_allow_html=True)
        for d in sorted(result["benchmark"]["dimension_scores"], key=lambda x: x["score"]):
            with st.expander(f"{d['name']} — {d['score']:.0f}/100 ({d['status']})"):
                st.write("**Evidence found:**", d["evidence"])
                st.write("**Missing / weak:**", d["missing"])
                st.caption(f"Priority: {d['priority']}")

        if result.get("gaps", {}).get("teacher_message"):
            st.markdown("<br>#### Teacher Guidance Note", unsafe_allow_html=True)
            st.write(_label(result["gaps"]["teacher_message"]))

        if result.get("gaps", {}).get("first_gap"):
            fg = result["gaps"]["first_gap"]
            st.markdown("<br>#### First Meaningful Structural Gap", unsafe_allow_html=True)
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
                        st.write("Apply this change at programme level during the next review cycle.")

        st.markdown("<br>#### Proposed Course Updates", unsafe_allow_html=True)
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
            st.markdown("#### Foundational Principles")
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

        st.markdown("<br>#### Change Log & Justification", unsafe_allow_html=True)
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
            st.markdown("<br>#### Teacher Review Points", unsafe_allow_html=True)
            for point in draft["teacher_review_points"]:
                st.write("• " + _label(point))

        st.warning(
            draft.get(
                "disclaimer",
                "AI-generated proposal requiring academic review and institutional approval.",
            )
        )

    with tab5:
        st.markdown("#### Analysis Inputs")
        structure = result.get("structure", {})
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**Identified Course Inventory**")
            for course in structure.get("course_inventory", [])[:25]:
                level = _field(course, "level_or_semester")
                st.write(f"• {_label(course, 'course', default='Unknown')}" + (f" — {level}" if level else ""))
        with col2:
            st.markdown("**Detected Tools & Frameworks**")
            tools = structure.get("tools_and_technologies", [])
            st.write(", ".join(_label(t) for t in tools[:40]) if tools else "No explicit technologies detected.")

        st.markdown("<br>#### Pipeline Uncertainty & Flags", unsafe_allow_html=True)
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
                "⬇️ Download Official Assessment Report (PDF)",
                data=st.session_state.pdf_report,
                file_name=f"NayaNisab_{result['subject'].replace(' ', '_')}_Curriculum_Report.pdf",
                mime="application/pdf",
                use_container_width=True,
            )
            st.caption("Standardized NayaNisab layout designed for Board of Studies and departmental committees.")
        elif st.session_state.get("pdf_report_error"):
            st.error(f"Could not compile PDF report: {st.session_state.pdf_report_error}")

    with new_col:
        if st.button("↩️ Reset & Start New Analysis", use_container_width=True):
            st.session_state.result = None
            st.session_state.pdf_report = None
            st.session_state.pdf_report_error = None
            st.rerun()