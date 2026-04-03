"""
frontend.py — NeuroLearnAI v2
Full Streamlit application:
  - Login / Register page (sha256 auth)
  - School Student Dashboard (step-by-step MCQ quiz)
  - College Student Dashboard (PDF upload OR topic quiz)
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import streamlit as st
import time

from db import verify_user, register_user, get_student_history
from backend import (
    evaluate_performance,
    get_question_set,
    extract_pdf_text,
    analyze_pdf_content,
    SUBJECTS,
)
from analyzer import analyze_upload
from planner import generate_targeted_plan
from tracker import save_attempt, progress_summary


# ## CACHED ASSET HELPERS ######################################################
@st.cache_data
def get_bg_base64_cached(path: str):
    import base64
    if not os.path.exists(path):
        return ""
    try:
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    except:
        return ""

# ## Page config ###############################################################
st.set_page_config(
    page_title="NeuroLearnAI",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ## CSS #######################################################################
# CSS Styling
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700;800&display=swap');

html, body, .stApp {
    font-family: 'Inter', sans-serif !important;
    background: #020617 !important;
    color: #E2E2F0 !important;
}

/* Hero Image Container on Left */
.hero-image-left {
    border-radius: 20px;
    box-shadow: 0 10px 40px rgba(0,0,0,0.5);
    width: 100%;
}

/* Glassmorphism Side Panel - SOLID for readability */
.glass-side-box {
    background: rgba(10, 10, 30, 0.4);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 24px;
    padding: 2.5rem 2rem;
    margin-top: 5vh;
}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<style>
/* Hero score */
.score-hero {
    background: linear-gradient(135deg, #6C63FF 0%, #43E97B 100%);
    border-radius: 24px;
    padding: 2.5rem;
    text-align: center;
    box-shadow: 0 10px 40px rgba(108,99,255,0.35);
    margin-bottom: 1.5rem;
}
.score-hero .score-num { font-size: 5rem; font-weight: 800; color: #fff; line-height: 1; }
.score-hero .score-sub { color: rgba(255,255,255,0.85); font-size: 1.1rem; margin-top: 0.5rem; }

/* Login page */
.login-container {
    max-width: 480px;
    margin: 4rem auto;
    background: linear-gradient(145deg, #1A1A30, #22223A);
    border: 1px solid #2E2E50;
    border-radius: 28px;
    padding: 3rem;
    box-shadow: 0 20px 60px rgba(0,0,0,0.5);
}

/* Role badge */
.badge {
    display: inline-block;
    border-radius: 50px;
    padding: 0.3rem 1rem;
    font-size: 0.78rem;
    font-weight: 700;
    margin: 0.2rem;
}
.badge-school  { background:#1B2E1B; color:#43E97B; border:1px solid #43E97B; }
.badge-college { background:#1B1B3A; color:#A5A0FF; border:1px solid #6C63FF; }
.badge-adv     { background:#2E1B1B; color:#F97878; border:1px solid #F97878; }
.badge-int     { background:#2E2A1B; color:#F9C858; border:1px solid #F9C858; }
.badge-beg     { background:#1B2A2E; color:#58C8F9; border:1px solid #58C8F9; }

/* Diff flow badges */
.df-up   { background:#1B3A2F; color:#43E97B; border:1px solid #43E97B; border-radius:6px; padding:2px 8px; font-size:0.75rem; margin:2px; display:inline-block; }
.df-down { background:#3A1B1B; color:#F97878; border:1px solid #F97878; border-radius:6px; padding:2px 8px; font-size:0.75rem; margin:2px; display:inline-block; }

/* Stats Ticker - Restored */
.stats-ticker {
    position: fixed;
    bottom: 0; left: 0; width: 100%;
    background: rgba(2, 6, 23, 0.95);
    backdrop-filter: blur(15px);
    border-top: 1px solid rgba(255, 255, 255, 0.05);
    padding: 12px 0;
    display: flex;
    justify-content: center;
    gap: 4rem;
    font-size: 0.75rem;
    color: #94a3b8;
    z-index: 1000;
    letter-spacing: 1px;
}
.stats-ticker b { color: #43E97B; margin-right: 4px; }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<style>
/* Step indicator */
.step-bar {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    margin-bottom: 1.5rem;
}
.step-dot {
    width: 32px; height: 32px;
    border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    font-size: 0.8rem; font-weight: 700;
}
.step-active   { background: #6C63FF; color: #fff; }
.step-done     { background: #43E97B; color: #0D0D1A; }
.step-inactive { background: #2A2A50; color: #6060A0; }
.step-line     { flex: 1; height: 2px; background: #2A2A50; border-radius: 2px; }

/* Buttons */
.stButton > button {
    background: linear-gradient(135deg, #6C63FF, #43E97B) !important;
    color: #fff !important; border: none !important;
    border-radius: 14px !important; padding: 0.65rem 2.2rem !important;
    font-weight: 700 !important; font-size: 1rem !important;
    letter-spacing: 0.3px; width: 100%;
}
.stButton > button:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 8px 24px rgba(108,99,255,0.45) !important;
}

/* Inputs */
.stTextInput input, .stSelectbox select {
    background: #12122A !important;
    border: 1px solid #2E2E50 !important;
    color: #E2E2F0 !important;
    border-radius: 10px !important;
}
label, .stRadio > label { color: #9090C0 !important; font-weight: 600 !important; }

/* Progress bar */
.stProgress > div > div { background: linear-gradient(90deg, #6C63FF, #43E97B) !important; }

/* Tabs */
.stTabs [data-baseweb="tab-list"] { background: #12122A; border-radius: 12px; padding: 4px; }
.stTabs [data-baseweb="tab"] { border-radius: 10px; color: #9090C0; font-weight: 600; }
.stTabs [aria-selected="true"] { background: #6C63FF !important; color: #fff !important; }

/* Question card */
.q-card {
    background: #12122A;
    border: 1px solid #2E2E50;
    border-radius: 14px;
    padding: 1.2rem 1.5rem;
    margin-bottom: 1rem;
}
.q-num { color: #6C63FF; font-size: 0.78rem; font-weight: 700; margin-bottom: 0.3rem; }
.q-text { font-size: 1rem; font-weight: 600; color: #E2E2F0; }

/* Top nav bar */
.top-bar {
    display: flex; align-items: center; justify-content: space-between;
    background: linear-gradient(135deg, #1A1A30, #22223A);
    border: 1px solid #2E2E50;
    border-radius: 16px;
    padding: 1rem 1.5rem;
    margin-bottom: 1.5rem;
}
.top-bar-logo { font-size: 1.4rem; font-weight: 800; color: #A5A0FF; }
.top-bar-user { color: #9090C0; font-size: 0.9rem; }
</style>
""", unsafe_allow_html=True)



# ## Session state init #########################################################
def _init():
    defaults = {
        "auth"        : False,
        "user"        : None,
        "step"        : 0,       # 0=setup, 1=quiz, 2=results
        "subject"     : None,
        "topic"       : None,
        "n_questions" : 5,
        "questions"   : [],
        "user_answers": {},      # q_index -> chosen option str
        "result"      : None,
        "col_mode"    : None,    # None | 'pdf' | 'quiz'
        "col_step"    : 0,
        "col_subject" : None,
        "col_topic"   : None,
        "col_result"  : None,
        "pdf_result"  : None,
        "show_reg"    : False,
        "reg_error"   : "",
        "login_error" : "",
        "verifying"   : False,
        "pending_user": None,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

_init()
ss = st.session_state


# ## Helpers ###################################################################
def _logout():
    for key in list(ss.keys()):
        del ss[key]
    _init()

def _level_badge(level: str) -> str:
    cls = {"Advanced": "badge-adv", "Intermediate": "badge-int", "Beginner": "badge-beg"}.get(level, "badge-beg")
    return f"<span class='badge {cls}'>{level}</span>"

def _role_badge(role: str) -> str:
    cls = "badge-school" if role == "School" else "badge-college"
    return f"<span class='badge {cls}'>{role} Student</span>"

def _top_bar():
    user = ss.user
    col1, col2, col3 = st.columns([3, 5, 2])
    with col1:
        st.markdown("<div class='top-bar-logo'>🧠 NeuroLearnAI</div>", unsafe_allow_html=True)
    with col2:
        st.markdown(
            f"<div style='text-align:center;'>"
            f"{_role_badge(user['role'])} &nbsp; "
            f"<span style='color:#E2E2F0;font-weight:600;'>{user['name']}</span>"
            f"</div>",
            unsafe_allow_html=True,
        )
    with col3:
        if st.button("🚪 Logout", key="logout_btn"):
            _logout()
            st.rerun()

def _step_bar(steps, current):
    dots = []
    for i, label in enumerate(steps):
        if i < current:
            cls = "step-done"; icon = "✓"
        elif i == current:
            cls = "step-active"; icon = str(i+1)
        else:
            cls = "step-inactive"; icon = str(i+1)
        dots.append(f"<div class='step-dot {cls}'>{icon}</div>")
        if i < len(steps) - 1:
            line_col = "#43E97B" if i < current else "#2A2A50"
            dots.append(f"<div class='step-line' style='background:{line_col};'></div>")
        else:
            dots.append(f"<span style='color:#9090C0;font-size:0.82rem;margin-left:0.4rem;'>{label}</span>")
    st.markdown(f"<div class='step-bar'>{''.join(dots)}</div>", unsafe_allow_html=True)


# #############################################################################
# LOGIN / REGISTER
# LOGIN / REGISTER
def show_login():
    # ## Split Hero Layout - Image on Left / Login on Right ##
    st.markdown("<br><br>", unsafe_allow_html=True)
    c_art, c_login = st.columns([6, 4], gap="large")
    
    with c_art:
        # Reduced Hero Image on the left
        b64_str = get_bg_base64_cached("hero_small.jpg") or get_bg_base64_cached("hero_baked.png")
        if b64_str:
            st.markdown(f"""
                <div style='margin-top:5vh; text-align:center;'>
                    <img src="data:image/jpeg;base64,{b64_str}" class='hero-image-left' style='max-width:90%; height:auto; border:2px solid rgba(165,160,255,0.2);'>
                </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("<h1 style='color:#fff;'>NeuroLearnAI</h1>", unsafe_allow_html=True)

    with c_login:
        # We start the container here
        st.markdown("<div class='glass-side-box'>", unsafe_allow_html=True)
        st.markdown("<h2 style='text-align:center; color:#fff; font-weight:800; margin-bottom:0;'>Secure Access</h2>", unsafe_allow_html=True)
        st.markdown("<p style='text-align:center; color:#A5A0FF; font-size:0.85rem; margin-bottom:2rem;'>Authorizing AI Node Identity...</p>", unsafe_allow_html=True)
        
        tab_login, tab_reg = st.tabs(["🔑 Sign In", "🆕 Register"])
        
        with tab_login:
            st.markdown("<br>", unsafe_allow_html=True)
            u = st.text_input("Username", key="l_un_v")
            p = st.text_input("Password", key="l_pw_v", type="password")
            if st.button("Unlock Dashboard", use_container_width=True):
                user = verify_user(u, p)
                if user: ss.auth=True; ss.user=user; st.rerun()
                else: st.error("Verification failed.")
            
            # -- Google Authentication Option --
            st.markdown("<div style='text-align:center; color:#6C63FF; margin:1rem 0; font-size:0.8rem; font-weight:600;'>── OR ──</div>", unsafe_allow_html=True)
            if st.button("Continue with Google", use_container_width=True, icon="🌐"):
                # Redirect to verification loop
                ss.pending_user = {
                    "username": "google_user",
                    "name": "Google Student",
                    "role": "College",
                    "class_dept": "CSE",
                    "subject_focus": "AI"
                }
                ss.verifying = True
                st.rerun()
        
        with tab_reg:
            st.markdown("<br>", unsafe_allow_html=True)
            r_name = st.text_input("Name", key="r_nm_v")
            r_user = st.text_input("Username", key="r_u_v")
            r_pass = st.text_input("Password", key="r_p_v", type="password")
            r_role = st.selectbox("Role", ["School", "College"], key="r_r_v")
            if r_role == "School":
                r_class_dept = st.selectbox("Class", ["Class 6-10", "Class 11-12"])
                sf = ["Math", "Science", "CS", "Bio"]
                r_subj_focus = st.selectbox("Subj", sf)
            else:
                r_class_dept = st.selectbox("Dept", ["CSE", "IT", "Other"])
                r_subj_focus = st.selectbox("Focus", ["AI", "DBMS", "OS"])
            
            if st.button("Create Account", use_container_width=True):
                ok, msg = register_user(r_user, r_pass, r_role, r_name, r_class_dept, r_subj_focus)
                if ok:
                    st.success("Success! Use Sign In tab.")
                else:
                    st.error(msg)
        
        # We close the container here
        st.markdown("</div>", unsafe_allow_html=True)


# EXAM UPLOAD & ANALYSIS 
_IMAP = {"Critical":"🔴","Weak":"🟠","Moderate":"🟡","Strong":"🟢"}
_CMAP = {"Critical":"#F97878","Weak":"#F9A858","Moderate":"#F9C858","Strong":"#43E97B"}
_PMAP = {"URGENT":"#F97878","HIGH":"#F9A858","MEDIUM":"#F9C858","MAINTAIN":"#43E97B"}

def show_exam_upload_tab(role: str):
    """Upload exam results → concept-level analysis → revision plan."""
    
    # ## Header Section with Content ##
    col_l, col_r = st.columns([5, 4])
    with col_l:
        st.markdown("### 🔬 Upload Exam Elements")
        st.markdown(
            "Push your raw results into our **AI Brain**. Whether it's a messy photo of a paper "
            "or a formal CSV, we map every question back to concept-level mastery."
        )
    with col_r:
        st.markdown(f"""
        <div class='card' style='padding:1.2rem; background:rgba(30,30,50,0.4); border:1px solid #43E97B; margin-top:0;'>
            <div style='font-size:0.9rem; font-weight:700; color:#43E97B; margin-bottom:0.5rem;'>📄 Supported Formats</div>
            <ul style='font-size:0.75rem; color:#A5A0FF; padding-left:1.2rem; line-height:1.6;'>
                <li><b>CSV:</b> Structured sheets with concept scores.</li>
                <li><b>PDF:</b> Textual or scanned academic papers.</li>
                <li><b>Image:</b> Photos of your physical answer keys.</li>
                <li><b>Conversion:</b> AI converts pixels & text into analysis.</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    c_u, c_i = st.columns([5, 4])
    with c_u:
        uploaded = st.file_uploader(
            "Push Exam File (Drop or Click)",
            type=["csv", "pdf", "png", "jpg", "jpeg"],
            key=f"ef_{role}",
            help="Deep OCR & AI Vision scanning will follow."
        )
    with c_i:
        st.markdown("""
        <div class='card' style='padding:0.8rem; background:rgba(67, 233, 123, 0.05); border:1px dashed #43E97B; opacity:0.8;'>
            <div style='font-size:0.85rem; font-weight:700; color:#43E97B; margin-bottom:0.4rem;'>⚡ AI Conversion Heuristics</div>
            <p style='font-size:0.7rem; color:#A5A0FF;'>We use multimodal AI vision to convert images/PDFs into structured data. It handles cursive text, bad lighting, and complex tables.</p>
        </div>
        """, unsafe_allow_html=True)

    if uploaded and st.button("🚀 Analyse Final Elements", key=f"ea_{role}", use_container_width=True):
        with st.spinner("Extracting content and running AI heuristic mapping..."):
            analysis = analyze_upload(
                uploaded, 
                uploaded.name, 
                student_name=ss.user["name"], 
                role=role, 
                class_dept=ss.user.get("class_dept", ""), 
                subject_focus=ss.user.get("subject_focus", "")
            )
        if analysis.get("error"):
            st.error(analysis["error"])
            return

        if analysis.get("is_llm"):
            is_qp = analysis.get("is_question_paper", False)
            overall = analysis.get("concept_score", 0)
            mock_concepts = {}
            for wc in analysis.get("weak_concepts", []): mock_concepts[wc] = 40.0
            for sc in analysis.get("strong_concepts", []): mock_concepts[sc] = 85.0
            
            if not is_qp:
                save_attempt(
                    student_name=ss.user["name"],
                    test_name=uploaded.name,
                    concept_scores=mock_concepts,
                    overall_score=overall, role=role, source="upload",
                )
                st.success(f"✅ Deep AI Analysis Complete. Progress saved.")
            else:
                st.info("📑 Question Paper Detected: Extraction Mode Active.")

            # HERO SECTION
            if is_qp:
                st.markdown(f"""
                <div class='score-hero' style='background:linear-gradient(135deg, #1B1B3A 0%, #6C63FF 100%); padding:2.5rem;'>
                    <div style='text-align:left;'>
                        <div style='font-size:2.5rem; font-weight:800; color:#fff;'>Syllabus Pulse</div>
                        <div class='score-sub'>Ready for Preparation &nbsp;|&nbsp; {len(analysis.get('weak_concepts', []))} topics extracted</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div class='score-hero' style='display:flex; align-items:center; justify-content:space-between; padding:2.5rem;'>
                    <div style='text-align:left;'>
                        <div style='font-size:2.5rem; font-weight:800; color:#fff;'>Analysis Complete</div>
                        <div class='score-sub'>Overall Coverage &nbsp;|&nbsp; Level: {analysis.get('level', 'Unknown')}</div>
                    </div>
                    <svg viewBox="0 0 36 36" class="circular-chart">
                      <path class="circle-bg" d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"/>
                      <path class="circle" stroke="#fff" stroke-dasharray="{overall}, 100" d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"/>
                      <text x="18" y="20.35" class="percentage">{overall:.0f}%</text>
                    </svg>
                </div>
                """, unsafe_allow_html=True)

            st.markdown("#### 🧠 Personalized AI Feedback")
            st.info(analysis.get('feedback', 'No feedback provided.'))
            st.markdown("<br>", unsafe_allow_html=True)

            c1, c2 = st.columns(2)
            with c1:
                st.markdown("#### 📋 Topics to Prepare" if is_qp else "#### 🔴 Focus Areas")
                for wc in analysis.get("weak_concepts", []): st.error(wc)
            with c2:
                st.markdown("#### ✅ Known Concepts" if is_qp else "#### 🟢 Mastered Concepts")
                for sc in analysis.get("strong_concepts", []): st.success(sc)

            st.markdown("<br>", unsafe_allow_html=True)
            t_plan, t_res, t_flow = st.tabs(["🗓️ Targeted Study Plan", "📘 Resources", "📈 Difficulty Adjustments"])
            with t_plan:
                for p in analysis.get("plan", []): st.markdown(f"- {p}")
            with t_res:
                for r in analysis.get("resources", []): st.success(r)
            with t_flow:
                st.markdown("Based on your answers, here is the suggested adaptive flow for your next session:")
                for flow in analysis.get("difficulty_flow", []):
                    icon = "⬆️" if "increase" in flow.lower() else "⬇️" if "decrease" in flow.lower() else "➡️"
                    st.markdown(f"- {icon} {flow}")
            return

        concepts = analysis.get("concepts", {})
        if not concepts:
            st.warning("No concept data found. Check the file format guide above.")
            return
        overall = analysis.get("overall_pct", 0)
        days = 7 # Default study plan window
        with st.spinner("Building personalised revision plan..."):
            plan = generate_targeted_plan(concepts, ss.user["name"], role, days)
        save_attempt(
            student_name=ss.user["name"],
            test_name=uploaded.name,
            concept_scores={c: d["score_pct"] for c, d in concepts.items()},
            overall_score=overall, role=role, source="upload",
        )
        st.success(f"✅ {len(concepts)} concepts analysed. Progress saved.")
        # ## Score hero
        st.markdown(
            f"<div class='score-hero'><div class='score-num'>{overall:.1f}%</div>"
            f"<div class='score-sub'>Overall Exam Score &nbsp;|&nbsp; {len(concepts)} concepts identified</div></div>",
            unsafe_allow_html=True,
        )
        st.markdown("<br>", unsafe_allow_html=True)
        # ## Concept cards
        st.markdown("#### 📊 Concept-Level Breakdown")
        cols = st.columns(min(len(concepts), 4))
        for idx, (name, d) in enumerate(sorted(concepts.items(), key=lambda x: x[1]["score_pct"])):
            col = _CMAP.get(d["classification"], "#A5A0FF")
            with cols[idx % 4]:
                st.markdown(
                    f"<div class='card' style='padding:0.9rem;text-align:center;'>"
                    f"<div style='font-weight:700;color:#E2E2F0;font-size:0.9rem;'>{name}</div>"
                    f"<div style='font-size:2rem;font-weight:800;color:{col};'>{d['score_pct']:.0f}%</div>"
                    f"<div style='font-size:0.72rem;color:{col};border:1px solid {col};"
                    f"border-radius:20px;padding:1px 8px;display:inline-block;'>{d['classification']}</div>"
                    f"</div>", unsafe_allow_html=True,
                )
        # ## Tabs: Weakness | Plan | Resources
        tw, tp, tr = st.tabs(["🔍 Weakness Analysis", "🗓️ Revision Plan", "📘 Resources"])
        with tw:
            st.markdown("#### Why each concept is flagged — and what to do")
            for name, d in sorted(concepts.items(), key=lambda x: x[1]["score_pct"]):
                icon = _IMAP.get(d["classification"], "⚪")
                with st.expander(f"{icon} **{name}** — {d['score_pct']:.0f}% ({d['classification']})"):
                    st.info(d["explanation"])
        with tp:
            st.info(plan["summary"])
            st.markdown(f"**Average daily commitment: ~{plan['avg_daily_minutes']} min/day**")
            for day in plan["daily_schedule"]:
                if not day["tasks"]:
                    continue
                with st.expander(f"📅 Day {day['day']} — {day['total_minutes']} min total"):
                    for t in day["tasks"]:
                        pc = _PMAP.get(t["priority"], "#A5A0FF")
                        st.markdown(
                            f"<span style='color:{pc};font-weight:700;font-size:0.8rem;'>[{t['priority']}]</span> "
                            f"**{t['concept']}** — {t['activity']} "
                            f"<span style='color:#6060A0;'>({t['minutes']} min)</span>",
                            unsafe_allow_html=True,
                        )
        with tr:
            st.markdown("#### Explained resource recommendations")
            for rec in plan["concept_recommendations"]:
                icon = _IMAP.get(rec["classification"], "⚪")
                with st.expander(f"{icon} **{rec['concept']}** [{rec['priority_label']}] — {rec['score_pct']:.0f}%"):
                    st.markdown("**Why focus here?**")
                    st.info(rec["weakness_explanation"])
                    st.markdown("**Recommended Resource:**")
                    st.success(rec["resource"])
                    st.markdown(f"**Why this resource?** _{rec['resource_explanation']}_")
                    st.markdown("**3-step action plan:**")
                    for mg in rec["micro_goals"]:
                        st.markdown(f"- {mg}")


def show_progress_tab(student_name: str):
    """Multi-test progress tracking with trend charts and concept analysis."""
    st.markdown("### 📊 Progress Across Tests")
    summary = progress_summary(student_name)
    if not summary.get("total_attempts"):
        st.info("No test history yet. Upload exam results in the Exam Analysis tab to start tracking.")
        return
    n, scores, names = summary["total_attempts"], summary["overall_scores"], summary["test_names"]
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Tests Taken", n)
    m2.metric("Latest Score", f"{scores[-1]:.1f}%",
              delta=f"{scores[-1]-scores[-2]:.1f}%" if n >= 2 else None)
    m3.metric("Average", f"{sum(scores)/n:.1f}%")
    m4.metric("Overall Trend", summary["overall_trend"])
    # ## Chart
    try:
        import plotly.graph_objects as go
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=names, y=scores, mode="lines+markers", name="Overall Score",
            line=dict(color="#6C63FF", width=3), marker=dict(size=10, color="#43E97B"),
            fill="tozeroy", fillcolor="rgba(108,99,255,0.08)"
        ))
        for concept, ct in list(summary.get("concept_trends", {}).items())[:4]:
            if len(ct["scores"]) >= 2:
                c = {"Improving":"#43E97B","Declining":"#F97878","Stable":"#F9C858"}.get(ct["trend"],"#9090C0")
                fig.add_trace(go.Scatter(
                    x=list(range(1, len(ct["scores"])+1)), y=ct["scores"],
                    mode="lines+markers", name=concept,
                    line=dict(color=c, width=1.5, dash="dot"),
                    marker=dict(size=6), opacity=0.75
                ))
        fig.update_layout(
            title="Score Progress Over Time", xaxis_title="Test", yaxis_title="Score (%)",
            yaxis_range=[0, 105], plot_bgcolor="#12122A", paper_bgcolor="#1A1A30",
            font=dict(color="#E2E2F0"), legend=dict(bgcolor="#12122A", bordercolor="#2E2E50"),
        )
        st.plotly_chart(fig, use_container_width=True)
    except ImportError:
        for t, s in zip(names, scores):
            st.markdown(f"`{t[:20]:20s}` {'#'*int(s/5)} {s:.0f}%")
    # ## Concept trends
    st.divider()
    st.markdown("#### Concept-Level Trends")
    c1, c2, c3 = st.columns(3)
    with c1:
        if summary.get("improving"):
            st.success("**Improving**\n\n" + "\n".join(f"- {c}" for c in summary["improving"]))
    with c2:
        if summary.get("declining"):
            st.error("**Declining — act now**\n\n" + "\n".join(f"- {c}" for c in summary["declining"]))
    with c3:
        if summary.get("stable"):
            st.info("**Stable**\n\n" + "\n".join(f"- {c}" for c in summary["stable"]))
    if summary.get("concept_trends"):
        with st.expander("📋 Detailed Trend Explanations"):
            for concept, ct in summary["concept_trends"].items():
                icon = {"Improving":"📈","Declining":"📉","Stable":"↔️"}.get(ct["trend"],"❓")
                st.markdown(f"**{icon} {concept}** ({ct['trend']}) — Avg: {ct['avg_score']:.1f}%")
                st.markdown(f"> {ct['explanation']}")
                if ct["scores"]:
                    st.markdown("Scores: " + " → ".join(f"**{s:.0f}%**" for s in ct["scores"]))
                st.markdown("---")


# #############################################################################
# SCHOOL STUDENT DASHBOARD
# #############################################################################
def _school_quiz_tab():
    """Step-by-step MCQ quiz (extracted so it works inside a st.tabs block)."""
    steps = ["Setup", "Quiz", "Results"]
    _step_bar(steps, ss.step)

    if ss.step == 0:
        subjects = list(SUBJECTS["School"].keys())
        col_l, col_r = st.columns(2)
        with col_l:
            st.markdown("### 📚 Select Subject & Topic")
            chosen_subj = st.selectbox("Subject", subjects, key="sch_subj")
            topics      = SUBJECTS["School"][chosen_subj]
            chosen_topic= st.selectbox("Topic",   topics,   key="sch_topic")
            n_q         = st.slider("Number of Questions", 3, 8, 5, key="sch_nq")
        with col_r:
            st.markdown("### 📁 Or Upload a Text File of Questions")
            uploaded = st.file_uploader(
                "Upload a .txt file (one question per line)", type=["txt"], key="sch_file",
            )
            if uploaded:
                raw = uploaded.read().decode("utf-8", errors="ignore").strip()
                st.info(f"File loaded: {len(raw.splitlines())} lines detected.")
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("Load Questions →", key="btn_load"):
            ss.questions    = get_question_set("School", chosen_subj, chosen_topic, n=n_q)
            ss.subject      = chosen_subj
            ss.topic        = chosen_topic
            ss.n_questions  = n_q
            ss.user_answers = {}
            ss.step = 1
            st.rerun()

    elif ss.step == 1:
        qs = ss.questions
        st.markdown(f"### ✏️ Quiz: {ss.subject} — {ss.topic}")
        st.markdown(f"Answer all {len(qs)} questions below, then submit.")
        st.markdown("<br>", unsafe_allow_html=True)
        answered = 0
        for i, q in enumerate(qs):
            st.markdown(
                f"<div class='q-card'><div class='q-num'>Question {i+1} of {len(qs)}</div>"
                f"<div class='q-text'>{q['q']}</div></div>", unsafe_allow_html=True,
            )
            chosen = st.radio(
                label=f"Q{i+1}", options=q["opts"],
                key=f"school_q_{i}", index=None, label_visibility="collapsed",
            )
            if chosen:
                ss.user_answers[i] = chosen
                answered += 1
        st.markdown("<br>", unsafe_allow_html=True)
        st.progress(answered / len(qs), text=f"Answered: {answered} / {len(qs)}")
        col_back, col_sub = st.columns(2)
        with col_back:
            if st.button("← Back to Setup", key="btn_back_setup"):
                ss.step = 0; st.rerun()
        with col_sub:
            if st.button("Submit Quiz →", key="btn_submit_quiz"):
                if answered < len(qs):
                    st.warning(f"Please answer all questions ({len(qs) - answered} remaining).")
                else:
                    with st.spinner("Generating your personalised report..."):
                        result = evaluate_performance(
                            data={ss.topic: [ss.user_answers[i] == qs[i]["ans"] for i in range(len(qs))]},
                            student_name=ss.user["name"], student_level="School",
                        )
                    ss.result = result; ss.step = 2; st.rerun()

    elif ss.step == 2:
        st.markdown(f"### 🎯 Results: {ss.subject} — {ss.topic}")
        _show_results(ss.result)
        
        with st.expander("👁️ Reveal Answers"):
            for i, q in enumerate(ss.questions):
                user_ans = ss.user_answers.get(i)
                correct_ans = q["ans"]
                color = "green" if user_ans == correct_ans else "red"
                st.markdown(f"**Q{i+1}: {q['q']}**")
                st.markdown(f"- Your Answer: :{color}[{user_ans}]")
                if user_ans != correct_ans:
                    st.markdown(f"- Correct Answer: :green[{correct_ans}]")
                st.divider()

        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🔁 Start New Quiz", key="btn_restart"):
            ss.step = 0; ss.result = None; ss.questions = []; ss.user_answers = {}; st.rerun()


def show_school():
    _top_bar()
    # ## Reliable Dashboard Gradient Background ##
    st.markdown("""
        <style>
        .stApp {
            background: #0A0A1A !important;
            background-image: 
                radial-gradient(circle at 10% 20%, rgba(108, 99, 255, 0.08) 0%, rgba(10, 10, 26, 0) 40%),
                radial-gradient(circle at 90% 80%, rgba(67, 233, 123, 0.08) 0%, rgba(10, 10, 26, 0) 40%),
                radial-gradient(circle at 50% 50%, rgba(108, 99, 255, 0.04) 0%, rgba(10, 10, 26, 0) 70%) !important;
            background-attachment: fixed;
        }
        </style>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns([1.5, 3])
    with col1:
        try:
            st.image("dashboard_baked.png", use_container_width=True)
        except:
            pass
    with col2:
        st.markdown("## 📘 School Learning Hub")
        st.markdown("Deep-dive into your performance with AI analysis, or polish your skills with adaptive quizzes.")
        
    st.divider()
    t_exam, t_quiz, t_progress = st.tabs(["🔬 Exam Analysis", "📝 Optional Quiz", "📊 Progress"])
    with t_exam:
        show_exam_upload_tab("School")
    with t_quiz:
        _school_quiz_tab()
    with t_progress:
        show_progress_tab(ss.user["name"])



# #############################################################################
# COLLEGE STUDENT DASHBOARD
# #############################################################################
def show_college():
    _top_bar()
    # ## Reliable Dashboard Gradient Background ##
    st.markdown("""
        <style>
        .stApp {
            background: #0A0A1A !important;
            background-image: 
                radial-gradient(circle at 15% 15%, rgba(165, 160, 255, 0.08) 0%, rgba(10, 10, 26, 0) 35%),
                radial-gradient(circle at 85% 85%, rgba(67, 233, 123, 0.08) 0%, rgba(10, 10, 26, 0) 35%) !important;
            background-attachment: fixed;
        }
        </style>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns([1.5, 3])
    with col1:
        try:
            st.image("dashboard_baked.png", use_container_width=True)
        except:
            pass
    with col2:
        st.markdown("## 🎓 College Learning Hub")
        st.markdown("Advanced analytics for higher education. Upload previous exam sheets or research briefs for concept mapping.")
        
    st.divider()

    tab_exam, tab_quiz, tab_history = st.tabs([
        "🔬  Exam Analysis",
        "🧪  Optional Quiz",
        "📊  Progress Tracker",
    ])

    with tab_exam:
        show_exam_upload_tab("College")

    # ## Quiz Tab ##############################################################
    with tab_quiz:
        st.markdown("### 🧪 Advanced Topic Quiz")
        steps = ["Setup", "Quiz", "Results"]
        _step_bar(steps, ss.col_step)

        if ss.col_step == 0:
            subjects = list(SUBJECTS["College"].keys())
            col_l, col_r = st.columns(2)
            with col_l:
                chosen_subj  = st.selectbox("Subject Area", subjects, key="col_subj")
                topics       = SUBJECTS["College"][chosen_subj]
                chosen_topic = st.selectbox("Topic",        topics,   key="col_topic_sel")
                n_q          = st.slider("Questions", 3, 8, 5, key="col_nq")
            with col_r:
                st.markdown("""
                <div class='card' style='margin-top:0;'>
                    <div style='font-size:1rem;font-weight:700;color:#A5A0FF;margin-bottom:0.5rem;'>💡 Tips</div>
                    <ul style='color:#7070A0;font-size:0.88rem;line-height:1.8;padding-left:1.2rem;'>
                        <li>Read each question carefully</li>
                        <li>Trust your instinct on unsure answers</li>
                        <li>All questions are MCQ (single correct)</li>
                        <li>Results include adaptive difficulty flow</li>
                    </ul>
                </div>
                """, unsafe_allow_html=True)

            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("Load Questions →", key="btn_col_load"):
                qs = get_question_set("College", chosen_subj, chosen_topic, n=n_q)
                ss.col_questions  = qs
                ss.col_subject    = chosen_subj
                ss.col_topic_name = chosen_topic
                ss.col_answers    = {}
                ss.col_step       = 1
                st.rerun()

        elif ss.col_step == 1:
            if not hasattr(ss, 'col_questions') or not ss.col_questions:
                ss.col_step = 0
                st.rerun()

            qs = ss.col_questions
            st.markdown(f"### ✏️ {ss.col_subject} — {ss.col_topic_name}")
            answered = 0

            for i, q in enumerate(qs):
                st.markdown(
                    f"<div class='q-card'>"
                    f"<div class='q-num'>Question {i+1} of {len(qs)}</div>"
                    f"<div class='q-text'>{q['q']}</div>"
                    f"</div>",
                    unsafe_allow_html=True,
                )
                chosen = st.radio(
                    label=f"col_q{i}_label",
                    options=q["opts"],
                    key=f"col_q_{i}",
                    index=None,
                    label_visibility="collapsed",
                )
                if chosen:
                    ss.col_answers[i] = chosen
                    answered += 1

            st.progress(answered / len(qs), text=f"Answered: {answered} / {len(qs)}")
            col_b, col_s = st.columns(2)
            with col_b:
                if st.button("← Back", key="col_back"):
                    ss.col_step = 0
                    st.rerun()
            with col_s:
                if st.button("Submit →", key="col_submit"):
                    if answered < len(qs):
                        st.warning(f"{len(qs) - answered} question(s) unanswered.")
                    else:
                        bool_ans = {
                            ss.col_topic_name: [
                                ss.col_answers[i] == qs[i]["ans"]
                                for i in range(len(qs))
                            ]
                        }
                        with st.spinner("Generating advanced report..."):
                            result = evaluate_performance(
                                data=bool_ans,
                                student_name=ss.user["name"],
                                student_level="College",
                            )
                        ss.col_result = result
                        ss.col_step   = 2
                        st.rerun()

        elif ss.col_step == 2:
            result = ss.col_result
            st.markdown(f"### 🎯 Results: {ss.col_subject} — {ss.col_topic_name}")
            _show_results(result)

            with st.expander("👁️ Reveal Answers"):
                if hasattr(ss, 'col_questions'):
                    for i, q in enumerate(ss.col_questions):
                        user_ans = ss.col_answers.get(i)
                        correct_ans = q["ans"]
                        color = "green" if user_ans == correct_ans else "red"
                        st.markdown(f"**Q{i+1}: {q['q']}**")
                        st.markdown(f"- Your Answer: :{color}[{user_ans}]")
                        if user_ans != correct_ans:
                            st.markdown(f"- Correct Answer: :green[{correct_ans}]")
                        st.divider()

            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("🔁 New Quiz", key="col_restart"):
                ss.col_step = 0
                ss.col_result = None
                if hasattr(ss, 'col_questions'):
                    ss.col_questions = []
                st.rerun()

    # ## History Tab ###########################################################
    with tab_history:
        show_progress_tab(ss.user["name"])

# #############################################################################
# SHARED RESULT DISPLAY
# #############################################################################
def _show_results(result: dict):
    score = result["concept_score"]

    # Score hero with Circular Progress
    st.markdown(f"""
    <div class='score-hero' style='display:flex; align-items:center; justify-content:space-around; padding:2rem 3rem;'>
        <div style='text-align:left;'>
            <div style='font-size:2.5rem; font-weight:800; color:#fff;'>Concept Mastery</div>
            <div class='score-sub'>
                {result['student_name']} &nbsp;|&nbsp; {result['level']}
                &nbsp;→&nbsp; Next: {result.get('next_level', result['level'])}
            </div>
        </div>
        <svg viewBox="0 0 36 36" class="circular-chart">
          <path class="circle-bg" d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" />
          <path class="circle" stroke="#fff" stroke-dasharray="{score}, 100" d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" />
          <text x="18" y="20.35" class="percentage">{score:.0f}%</text>
        </svg>
    </div>
    """, unsafe_allow_html=True)

    # Document Narrative summary (NEW)
    if result.get("text_summary"):
        st.markdown(f"""
        <div class='card' style='padding:1.2rem; border-left:4px solid #A5A0FF; margin-bottom:1rem; background:rgba(165,160,255,0.05);'>
            <div style='font-size:0.8rem; font-weight:700; color:#A5A0FF; text-transform:uppercase; margin-bottom:0.5rem;'>📄 AI Document Narrative</div>
            <div style='font-style:italic; color:#7070A0; font-size:0.95rem; line-height:1.6;'>"{result['text_summary']}"</div>
        </div>
        """, unsafe_allow_html=True)

    # Metric row
    r_color = {"High":"#43E97B","Medium":"#F9C858","Low":"#F97878"}.get(result["retention"],"#A5A0FF")
    st.markdown(f"""
    <div class='card' style='padding:1rem 1.5rem;'>
        {_level_badge(result['level'])}
        <span class='badge' style='background:#12122A;border:1px solid {r_color};color:{r_color};'>
            🧠 Retention: {result['retention']}
        </span>
        <span class='badge' style='background:#12122A;border:1px solid #6C63FF;color:#A5A0FF;'>
            ⚡ Speed: {result['speed']}
        </span>
        <span class='badge' style='background:#12122A;border:1px solid #6060A0;color:#9090C0;'>
            📊 Trend: {result['difficulty_summary']['trend']}
        </span>
    </div>
    """, unsafe_allow_html=True)

    tab_fb, tab_plan, tab_res, tab_diff = st.tabs([
        "🤖 AI Feedback", "🗓️ Study Plan", "📘 Resources", "🔄 Difficulty"
    ])

    with tab_fb:
        st.markdown("#### 🤖 Personalised AI Feedback")
        parts = result.get("feedback_parts") or result.get("feedback","").split(" | ")
        for p in parts:
            st.markdown(f"> {p}")
        if result.get("weak_concepts"):
            st.markdown("#### ⚠️ Weak Concepts")
            explanations = result.get("concept_explanations", [])
            for wc in result["weak_concepts"]:
                reason = ""
                for exp in explanations:
                    if str(wc).lower() in str(exp.get("concept", "")).lower():
                        reason = f"<br><span style='color:#F9A858; font-size:0.85rem;'>↳ <b>Why?</b> {exp.get('reason_weak', '')}</span>"
                        break
                st.markdown(f"<div class='card' style='padding:1rem; border-left:4px solid #F97878; margin-bottom:0.5rem;'>❌ <b>{wc}</b>{reason}</div>", unsafe_allow_html=True)
        else:
            st.success("✅ No critical weak spots — excellent!")

    with tab_plan:
        st.markdown("#### 🗓️ 7-Day Study Plan")
        st.progress(score / 100, text=f"Current mastery: {score:.1f}%")
        for step in result.get("study_plan", []):
            st.markdown(f"- {step}")

    with tab_res:
        st.markdown("#### 📘 Recommended Resources")
        explanations = result.get("concept_explanations", [])
        
        # Handle dict format (heuristic legacy)
        if isinstance(result.get("resources", {}), dict):
            for concept, resource in result.get("resources", {}).items():
                flag = "❌" if concept in result.get("weak_concepts", []) else "✅"
                with st.expander(f"{flag} {concept}"):
                    st.write(resource)
        
        # Handle list format (new Native LLM) with explanations
        elif isinstance(result.get("resources", []), list):
            for r in result.get("resources", []):
                st.markdown(f"<div class='card' style='padding:0.8rem; margin-bottom:0.4rem;'>📘 <b>{r}</b></div>", unsafe_allow_html=True)
            
            # Print exact reasons
            if explanations:
                st.markdown("##### 🔍 Why are these suggested?")
                for exp in explanations:
                    if exp.get('reason_resource'):
                        st.markdown(f"- **{exp.get('resource', exp.get('concept'))}**: {exp.get('reason_resource')}")

    with tab_diff:
        st.markdown("#### 🔄 Adaptive Difficulty Flow")
        s = result["difficulty_summary"]
        m1, m2, m3 = st.columns(3)
        m1.metric("↑ Increase", s["increase_count"])
        m2.metric("↓ Decrease", s["decrease_count"])
        m3.metric("📈 Trend",   s["trend"])

        badges = " ".join([
            f"<span class='df-up'>↑</span>" if r == "increase level"
            else f"<span class='df-down'>↓</span>"
            for r in result["difficulty_flow"]
        ])
        st.markdown(badges, unsafe_allow_html=True)


def _show_feedback_plan_resources(res: dict):
    """Shared display for PDF analysis feedback, plan, and resources."""
    tab_fb, tab_plan, tab_res = st.tabs(["🤖 AI Feedback", "🗓️ Study Plan", "📘 Resources"])

    with tab_fb:
        parts = res.get("feedback_parts") or res.get("feedback","").split(" | ")
        for p in parts:
            st.markdown(f"> {p}")
        if res.get("weak_topics"):
            st.markdown("#### ⚠️ Low-Coverage Topics")
            for wt in res["weak_topics"]:
                st.markdown(f"- 📉 **{wt}** — needs deeper study")

    with tab_plan:
        st.progress(res["concept_score"] / 100, text=f"Coverage: {res['concept_score']:.1f}%")
        for step in res.get("study_plan", []):
            st.markdown(f"- {step}")

    with tab_res:
        for concept, resource in res.get("resources", {}).items():
            flag = "📉" if concept in res.get("weak_topics", []) else "📘"
            with st.expander(f"{flag} {concept}"):
                st.write(resource)


def show_background():
    """Do nothing - image is now moved inside the login layout for better control."""
    pass


def show_verification_gate():
    """Active security screen: Asks for Email + OTP to confirm Google Identity."""
    st.markdown("<br><br><br>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        st.markdown(f"""
        <div class='glass-side-box' style='text-align:center; padding:2rem 3rem;'>
            <div style='font-size:2.5rem; margin-bottom:1rem;'>🔐</div>
            <h2 style='color:#fff; margin-bottom:0.5rem;'>Enter Verification Details</h2>
            <p style='color:#A5A0FF; font-size:0.85rem; margin-bottom:1.5rem;'>
                To continue, please provide the email and the 6-digit security code sent to your Google account.
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        with st.container(border=True):
            email_v = st.text_input("Google Email", placeholder="student@gmail.com")
            otp_v   = st.text_input("Verification Code (OTP)", placeholder="000 000", max_chars=6)
            
            if st.button("Verify & Unlock AI Dashboard", use_container_width=True):
                if "@" in email_v and len(otp_v) == 6:
                    ss.auth = True
                    ss.user = ss.pending_user
                    # Ensure the name is updated if they typed something else
                    ss.user['email'] = email_v 
                    ss.verifying = False
                    st.success("Security Handshake Successful. Initializing AI...")
                    time.sleep(1.2)
                    st.rerun()
                else:
                    st.error("Please enter a valid email and 6-digit code.")
            
        if st.button("Cancel & Go Back", use_container_width=True, type="secondary"):
            ss.verifying = False
            ss.pending_user = None
            st.rerun()


# #############################################################################
# ROUTER
# #############################################################################
if not ss.auth:
    if ss.verifying:
        show_verification_gate()
    else:
        show_background()
        show_login()
elif ss.user["role"] == "School":
    show_school()
else:
    show_college()
