"""
main.py
--------
FastAPI backend for CareerPilot AI - Resume Analyzer.

Run with:
    uvicorn main:app --reload

This serves:
- The HTML/CSS/JS frontend (from the ../frontend folder)
- API endpoints used by that frontend:
    POST /api/analyze            -> upload a resume, get parsed details + ATS score
    POST /api/match              -> match previously-extracted skills against a JD
    GET  /api/roles              -> list of supported target roles
    POST /api/roadmap            -> generate a career roadmap from skills
    POST /api/interview/start    -> generate mock interview questions
    POST /api/interview/score    -> score a set of mock interview answers
    POST /api/resume/rewrite     -> get improved summary + bullet points
    POST /api/resume/download    -> download the rewritten resume as .docx
"""

import os
import io
from typing import Dict, List, Optional

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from resume_parser import parse_resume, IMAGE_EXTENSIONS
from ats_scorer import compute_ats_score
from jd_matcher import match_resume_to_jd
from roadmap_generator import generate_roadmap, list_roles
from interview_generator import generate_questions, score_answers
from resume_rewriter import rewrite_resume, build_resume_docx

app = FastAPI(title="CareerPilot AI - Resume Analyzer API")

# Allow the frontend to call this API even if served from a different port
# while developing (e.g. opening index.html directly).
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------

class MatchRequest(BaseModel):
    resume_skills: List[str]
    jd_text: str


class RoadmapRequest(BaseModel):
    skills: List[str]
    target_role: Optional[str] = None


class InterviewStartRequest(BaseModel):
    skills: List[str] = []
    role: str = ""
    projects_bullets: List[str] = []
    experience_bullets: List[str] = []


class InterviewAnswerItem(BaseModel):
    question: str
    category: str = ""
    keywords: List[str] = []
    answer: str = ""


class InterviewScoreRequest(BaseModel):
    items: List[InterviewAnswerItem]


class ResumeRewriteRequest(BaseModel):
    parsed: Dict
    detected_role: Optional[str] = ""
    missing_keywords: List[str] = []


class ResumeDownloadRequest(BaseModel):
    resume_data: Dict


# ---------------------------------------------------------------------------
# Resume analysis + JD match (existing features)
# ---------------------------------------------------------------------------

@app.post("/api/analyze")
async def analyze_resume(file: UploadFile = File(...)):
    """
    Accepts a PDF, DOCX, or a photo (camera capture / gallery upload) of a
    resume, parses it, and returns:
    - parsed resume fields (name, email, skills, etc.)
    - the ATS score breakdown
    """
    allowed_extensions = (".pdf", ".docx") + IMAGE_EXTENSIONS
    if not file.filename.lower().endswith(allowed_extensions):
        raise HTTPException(
            status_code=400,
            detail="Please upload a PDF, DOCX, or a clear photo (JPG/PNG) of your resume.",
        )

    file_bytes = await file.read()

    try:
        parsed = parse_resume(file_bytes, file.filename)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to parse resume: {e}")

    ats = compute_ats_score(parsed)

    # raw_text can be large and isn't needed by the frontend - drop it from the response
    parsed_response = {k: v for k, v in parsed.items() if k != "raw_text"}

    return {"parsed": parsed_response, "ats": ats}


@app.post("/api/match")
async def match_jd(payload: MatchRequest):
    """
    Compares a resume's previously-extracted skills against a pasted job description.
    """
    if not payload.jd_text or not payload.jd_text.strip():
        raise HTTPException(status_code=400, detail="Job description text is empty.")

    result = match_resume_to_jd(payload.resume_skills, payload.jd_text)
    return result


# ---------------------------------------------------------------------------
# Career Roadmap
# ---------------------------------------------------------------------------

@app.get("/api/roles")
async def get_roles():
    """Returns the list of supported target roles, for a dropdown in the UI."""
    return {"roles": list_roles()}


@app.post("/api/roadmap")
async def get_roadmap(payload: RoadmapRequest):
    """
    Generates a rule-based career roadmap: detects (or accepts) a target
    role, finds missing skills, and returns a staged learning plan.
    """
    result = generate_roadmap(payload.skills, payload.target_role)
    return result


# ---------------------------------------------------------------------------
# Mock Interview
# ---------------------------------------------------------------------------

@app.post("/api/interview/start")
async def start_interview(payload: InterviewStartRequest):
    """
    Builds a personalized set of mock interview questions based on the
    candidate's skills and resume content (general + technical + project-based).
    """
    questions = generate_questions(
        skills=payload.skills,
        role=payload.role,
        projects_bullets=payload.projects_bullets,
        experience_bullets=payload.experience_bullets,
    )
    return {"questions": questions}


@app.post("/api/interview/score")
async def score_interview(payload: InterviewScoreRequest):
    """
    Scores the candidate's typed answers using keyword coverage + answer
    depth heuristics, and returns an overall mock-interview score.
    """
    items = [item.dict() for item in payload.items]
    result = score_answers(items)
    return result


# ---------------------------------------------------------------------------
# Resume Rewriter
# ---------------------------------------------------------------------------

@app.post("/api/resume/rewrite")
async def rewrite_resume_endpoint(payload: ResumeRewriteRequest):
    """
    Returns an improved, ready-to-download version of the resume: the
    professional summary and bullet points are rewritten (weak phrasing
    replaced with strong action verbs), and any AI-flagged missing
    keywords/skills are folded into the skills list - so this is the full
    resume content with every suggested point applied, not just a list of
    the changes.
    """
    result = rewrite_resume(payload.parsed, payload.detected_role or "", payload.missing_keywords)
    return result


@app.post("/api/resume/download")
async def download_resume(payload: ResumeDownloadRequest):
    """
    Builds a clean, ATS-friendly .docx from the (possibly edited) resume
    data and streams it back to the browser as a downloadable file.
    """
    try:
        docx_bytes = build_resume_docx(payload.resume_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to build resume document: {e}")

    filename = "Updated_Resume.docx"
    return StreamingResponse(
        io.BytesIO(docx_bytes),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.get("/api/health")
async def health_check():
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Serve the frontend (index.html, style.css, script.js) as static files.
# This means you can open http://localhost:8000 directly - no separate
# frontend server needed.
# ---------------------------------------------------------------------------
app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
