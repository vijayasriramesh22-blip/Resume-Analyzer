"""
streamlit_app.py
------------------
Streamlit version of CareerPilot AI - Resume Analyzer.

This reuses the exact same backend logic as the FastAPI app
(backend/resume_parser.py, ats_scorer.py, jd_matcher.py, roadmap_generator.py,
interview_generator.py, resume_rewriter.py) - just wrapped in a Streamlit UI
instead of HTML/JS, so it can be deployed straight to Streamlit Community
Cloud with one file.

Run locally with:
    streamlit run streamlit_app.py

Deploy on https://share.streamlit.io by pointing it at this file.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "backend"))

import streamlit as st

from resume_parser import parse_resume
from ats_scorer import compute_ats_score
from jd_matcher import match_resume_to_jd
from roadmap_generator import generate_roadmap, list_roles
from interview_generator import generate_questions, score_answers
from resume_rewriter import rewrite_resume, build_resume_docx


st.set_page_config(page_title="CareerPilot AI", page_icon="🧭", layout="centered")

# ---------------------------------------------------------------------------
# Session state defaults
# ---------------------------------------------------------------------------
defaults = {
    "parsed": None,
    "ats": None,
    "jd_missing_skills": [],
    "detected_role": "",
    "interview_questions": [],
    "interview_results": None,
    "rewritten": None,
}
for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value


def _lower_words(items):
    return sorted(set(w.strip() for w in items if w and w.strip()))


# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
st.title("🧭 CareerPilot AI")
st.caption("Resume analyzer, ATS scorer, JD matcher, career roadmap, mock interview & resume rewriter — 100% rule-based, no external AI API.")

# ---------------------------------------------------------------------------
# Step 1: Upload resume — file, camera photo, or a gallery image
# ---------------------------------------------------------------------------
st.header("1. Upload your resume")

tab_file, tab_camera, tab_gallery = st.tabs(["📁 Upload File", "📷 Take a Photo", "🖼️ Choose from Gallery"])

with tab_file:
    file_upload = st.file_uploader("PDF or DOCX", type=["pdf", "docx"], key="file_upload")

with tab_camera:
    camera_upload = st.camera_input("Take a photo of your resume", key="camera_upload")

with tab_gallery:
    gallery_upload = st.file_uploader(
        "Choose a photo of your resume", type=["jpg", "jpeg", "png", "webp", "bmp"], key="gallery_upload"
    )

# Whichever of the three was used most recently wins.
active_file, active_name = None, None
if file_upload is not None:
    active_file, active_name = file_upload, file_upload.name
elif camera_upload is not None:
    active_file, active_name = camera_upload, "resume-photo.jpg"
elif gallery_upload is not None:
    active_file, active_name = gallery_upload, gallery_upload.name

analyze_clicked = st.button("🔍 Analyze Resume", type="primary", disabled=active_file is None)

if analyze_clicked and active_file is not None:
    with st.spinner("Reading and scoring your resume..."):
        try:
            file_bytes = active_file.getvalue()
            parsed = parse_resume(file_bytes, active_name)
            ats = compute_ats_score(parsed)
            st.session_state.parsed = parsed
            st.session_state.ats = ats
            st.session_state.jd_missing_skills = []
            st.session_state.detected_role = ""
            st.session_state.interview_questions = []
            st.session_state.interview_results = None
            st.session_state.rewritten = None
        except ValueError as e:
            st.error(str(e))
        except Exception as e:
            st.error(f"Failed to parse resume: {e}")

parsed = st.session_state.parsed
ats = st.session_state.ats

if not parsed:
    st.info("Upload a resume above (file, camera photo, or gallery image) and click **Analyze Resume** to get started.")
    st.stop()

# ---------------------------------------------------------------------------
# Profile summary
# ---------------------------------------------------------------------------
st.success("Resume analyzed!")
col1, col2 = st.columns(2)
with col1:
    st.markdown(f"**Name:** {parsed.get('name') or '—'}")
    st.markdown(f"**Email:** {parsed.get('email') or '—'}")
with col2:
    st.markdown(f"**Phone:** {parsed.get('phone') or '—'}")
    links = ", ".join(l for l in [parsed.get("linkedin"), parsed.get("github"), parsed.get("portfolio")] if l)
    st.markdown(f"**Links:** {links or '—'}")

if parsed.get("skills"):
    st.markdown("**Detected skills:** " + ", ".join(parsed["skills"]))

st.divider()

tab_ats, tab_jd, tab_roadmap, tab_interview, tab_rewrite = st.tabs(
    ["📊 ATS Score", "🎯 JD Match", "🗺️ Roadmap", "🎤 Mock Interview", "✍️ Rewrite & Download"]
)

# ---------------------------------------------------------------------------
# ATS Score tab
# ---------------------------------------------------------------------------
with tab_ats:
    st.metric("Overall ATS Score", f"{ats['overall_score']} / 100")

    for category, data in ats["breakdown"].items():
        st.progress(min(max(data["score"], 0), 100) / 100, text=f"{category}: {data['score']}/100")
        for issue in data.get("issues", []):
            st.caption(f"⚠️ {issue}")

    if ats.get("weak_bullets"):
        with st.expander(f"Weak bullet points found ({len(ats['weak_bullets'])})"):
            for b in ats["weak_bullets"]:
                st.write(f"- {b}")

    if ats.get("missing_keywords"):
        st.warning("Missing keywords: " + ", ".join(ats["missing_keywords"]))

# ---------------------------------------------------------------------------
# JD Match tab
# ---------------------------------------------------------------------------
with tab_jd:
    jd_text = st.text_area("Paste a job description to compare against", height=180, key="jd_text")
    if st.button("Match against JD"):
        if jd_text.strip():
            match = match_resume_to_jd(parsed.get("skills", []), jd_text)
            st.session_state.jd_missing_skills = match.get("missing_skills", [])
            st.metric("Match %", f"{match['match_percent']}%")
            st.markdown("**Matched skills:** " + (", ".join(match["matched_skills"]) or "None"))
            st.markdown("**Missing skills:** " + (", ".join(match["missing_skills"]) or "None - fully covered!"))
        else:
            st.warning("Paste a job description first.")

# ---------------------------------------------------------------------------
# Roadmap tab
# ---------------------------------------------------------------------------
with tab_roadmap:
    role_options = ["Auto-detect"] + list_roles()
    chosen_role = st.selectbox("Target role", role_options, key="role_select")
    if st.button("Generate Roadmap"):
        target_role = None if chosen_role == "Auto-detect" else chosen_role
        roadmap = generate_roadmap(parsed.get("skills", []), target_role)
        st.session_state.detected_role = roadmap["role"]

        st.markdown(f"**Role:** {roadmap['role']}" + ("  _(auto-detected)_" if roadmap["auto_detected"] else ""))
        st.metric("Readiness", f"{roadmap['readiness_percent']}%")
        st.markdown("**You already have:** " + (", ".join(roadmap["matched_skills"]) or "—"))
        st.markdown("**Still missing:** " + (", ".join(roadmap["missing_skills"]) or "None - you're fully ready!"))

        for stage in roadmap["roadmap"]:
            with st.expander(f"{stage['stage']} ({stage['estimated_duration']})"):
                for item in stage.get("skills", []):
                    st.write(f"- **{item['skill']}**: {item['note']}")

# ---------------------------------------------------------------------------
# Mock Interview tab
# ---------------------------------------------------------------------------
with tab_interview:
    if st.button("Start Mock Interview"):
        st.session_state.interview_questions = generate_questions(
            skills=parsed.get("skills", []),
            role=st.session_state.detected_role,
            projects_bullets=parsed.get("projects_bullets", []),
            experience_bullets=parsed.get("experience_bullets", []),
        )
        st.session_state.interview_results = None

    questions = st.session_state.interview_questions
    if questions:
        answers = []
        with st.form("interview_form"):
            for i, q in enumerate(questions):
                st.markdown(f"**{i + 1}. {q['question']}**  \n*({q.get('category', '')})*")
                ans = st.text_area("Your answer", key=f"answer_{i}", label_visibility="collapsed")
                answers.append({**q, "answer": ans})
            submitted = st.form_submit_button("Submit Answers")

        if submitted:
            st.session_state.interview_results = score_answers(answers)

        results = st.session_state.interview_results
        if results:
            st.metric("Interview Score", f"{results['overall_score']} / 100")
            st.write(results["summary"])
            for pq in results["per_question"]:
                with st.expander(f"{pq['question'][:80]}... — {pq['score']}/100"):
                    for issue in pq.get("issues", []):
                        st.caption(f"⚠️ {issue}")
    else:
        st.info("Click **Start Mock Interview** to get personalized questions based on your resume.")

# ---------------------------------------------------------------------------
# Rewrite & Download tab
# ---------------------------------------------------------------------------
with tab_rewrite:
    st.caption(
        "Weak bullet points get rewritten with strong action verbs, a professional "
        "summary is added if missing, and any AI-flagged missing keywords are added "
        "to your skills — giving you a full, updated resume to download."
    )
    if st.button("✨ Generate Improved Resume"):
        missing_keywords = _lower_words(ats.get("missing_keywords", []) + st.session_state.jd_missing_skills)
        st.session_state.rewritten = rewrite_resume(parsed, st.session_state.detected_role, missing_keywords)

    rewritten = st.session_state.rewritten
    if rewritten:
        edited_summary = st.text_area("Professional Summary", value=rewritten["summary_text"], height=120)
        edited_skills_text = st.text_area("Skills (comma-separated)", value=", ".join(rewritten["skills"]))
        edited_experience = st.text_area(
            "Experience bullets (one per line)", value="\n".join(rewritten["experience_bullets"]), height=140
        )
        edited_projects = st.text_area(
            "Project bullets (one per line)", value="\n".join(rewritten["projects_bullets"]), height=140
        )
        edited_achievements = st.text_area(
            "Achievement bullets (one per line)", value="\n".join(rewritten["achievements_bullets"]), height=100
        )

        resume_data = {
            "name": parsed.get("name"),
            "email": parsed.get("email"),
            "phone": parsed.get("phone"),
            "linkedin": parsed.get("linkedin"),
            "github": parsed.get("github"),
            "portfolio": parsed.get("portfolio"),
            "skills": [s.strip() for s in edited_skills_text.split(",") if s.strip()],
            "languages": parsed.get("languages"),
            "education_text": parsed.get("education_text"),
            "certifications_text": parsed.get("certifications_text"),
            "summary_text": edited_summary.strip(),
            "experience_bullets": [b.strip() for b in edited_experience.split("\n") if b.strip()],
            "projects_bullets": [b.strip() for b in edited_projects.split("\n") if b.strip()],
            "achievements_bullets": [b.strip() for b in edited_achievements.split("\n") if b.strip()],
        }

        docx_bytes = build_resume_docx(resume_data)
        st.download_button(
            "⬇️ Download Updated Resume (.docx)",
            data=docx_bytes,
            file_name="Updated_Resume.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            type="primary",
        )
    else:
        st.info("Click **Generate Improved Resume** to preview and download your updated resume.")
