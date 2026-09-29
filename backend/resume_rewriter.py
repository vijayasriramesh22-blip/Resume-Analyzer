"""
resume_rewriter.py
---------------------
A fully rule-based Resume Rewriter.

- rewrite_resume(): improves weak bullet points (replacing filler phrases
  like "responsible for" with a strong action verb) and fills in a
  templated professional summary if one is missing. Pure text processing,
  no external AI API needed.
- build_resume_docx(): takes the (possibly edited) resume content and
  renders a clean, ATS-friendly Word document the user can download.
"""

import io
import itertools
import re
from typing import Dict, List

from docx import Document
from docx.shared import Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH

from skills_db import STRONG_ACTION_VERBS, WEAK_PHRASES

# A small, varied rotation of strong verbs to use when a bullet needs one.
_VERB_CYCLE = itertools.cycle(STRONG_ACTION_VERBS)

_WEAK_PHRASE_PATTERN = re.compile(
    r"^\s*(" + "|".join(re.escape(p) for p in WEAK_PHRASES) + r")\b[:,]?\s*",
    re.IGNORECASE,
)


def _starts_with_strong_verb(bullet: str) -> bool:
    first_word = bullet.strip().split(" ")[0].lower().strip(".,:;")
    return first_word in STRONG_ACTION_VERBS


def improve_bullet(bullet: str) -> str:
    """
    Rewrites a single bullet point:
    1. Strips leading weak phrases ("responsible for", "worked on", etc.)
    2. Makes sure it starts with a strong action verb
    3. Capitalizes the first letter and ensures it ends cleanly
    """
    text = bullet.strip()
    if not text:
        return text

    had_weak_phrase = bool(_WEAK_PHRASE_PATTERN.match(text))
    text = _WEAK_PHRASE_PATTERN.sub("", text).strip()

    if not text:
        return bullet.strip()

    if had_weak_phrase or not _starts_with_strong_verb(text):
        verb = next(_VERB_CYCLE).capitalize()
        # Avoid duplicating the verb if, coincidentally, the text already starts with it
        if not text.lower().startswith(verb.lower()):
            text = f"{verb} {text[0].lower()}{text[1:]}" if text else verb

    # Capitalize the very first character of the final bullet
    text = text[0].upper() + text[1:] if text else text

    # Tidy up double spaces left behind by phrase stripping
    text = re.sub(r"\s{2,}", " ", text).strip()
    return text


def _generate_summary(name: str, skills: List[str], detected_role: str) -> str:
    top_skills = ", ".join(skills[:6]) if skills else "a range of technical tools"
    role_text = detected_role if detected_role else "technology"
    first_name = (name or "Candidate").split(" ")[0]
    return (
        f"Motivated {role_text} professional with hands-on experience in {top_skills}. "
        f"{first_name} enjoys building and shipping complete, working projects, and is "
        f"looking to apply these skills in a full-time role where they can keep growing."
    )


def _merge_skills(existing_skills: List[str], missing_keywords: List[str]) -> List[str]:
    """Adds AI-flagged missing keywords/skills to the existing skills list,
    without creating duplicates (case-insensitive)."""
    merged = list(existing_skills or [])
    seen_lower = {s.strip().lower() for s in merged if s.strip()}
    for kw in missing_keywords or []:
        kw = kw.strip()
        if kw and kw.lower() not in seen_lower:
            merged.append(kw)
            seen_lower.add(kw.lower())
    return merged


def rewrite_resume(parsed: Dict, detected_role: str = "", missing_keywords: List[str] = None) -> Dict:
    """
    Takes the parsed resume dict (from resume_parser.parse_resume) and
    returns a fully rebuilt, ready-to-download version of it: improved
    summary, improved bullet points, and the skills list with any
    AI-flagged missing keywords added - without mutating the original.
    """
    experience_bullets = parsed.get("experience_bullets", []) or []
    projects_bullets = parsed.get("projects_bullets", []) or []
    achievements_bullets = parsed.get("achievements_bullets", []) or []

    improved_experience = [improve_bullet(b) for b in experience_bullets]
    improved_projects = [improve_bullet(b) for b in projects_bullets]
    improved_achievements = [improve_bullet(b) for b in achievements_bullets]

    summary_text = (parsed.get("summary_text") or "").strip()
    if not summary_text:
        summary_text = _generate_summary(
            parsed.get("name", ""), parsed.get("skills", []), detected_role
        )

    skills = _merge_skills(parsed.get("skills", []), missing_keywords)

    return {
        "summary_text": summary_text,
        "skills": skills,
        "experience_bullets": improved_experience,
        "projects_bullets": improved_projects,
        "achievements_bullets": improved_achievements,
    }


# ---------------------------------------------------------------------------
# DOCX export
# ---------------------------------------------------------------------------

def _add_heading(document: Document, text: str):
    heading = document.add_heading(text, level=2)
    for run in heading.runs:
        run.font.size = Pt(13)


def build_resume_docx(resume_data: Dict) -> bytes:
    """
    Builds a clean, single-column, ATS-friendly .docx from the given resume
    data (name, contact info, summary, skills, bullets, etc.) and returns
    the file as raw bytes, ready to be streamed back to the browser.
    """
    document = Document()

    # Reasonable default font/margins for an ATS-friendly doc
    style = document.styles["Normal"]
    style.font.name = "Calibri"
    style.font.size = Pt(11)

    name = resume_data.get("name") or "Your Name"
    title = document.add_heading(name, level=0)
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER

    contact_bits = [
        resume_data.get("email", ""),
        resume_data.get("phone", ""),
        resume_data.get("linkedin", ""),
        resume_data.get("github", ""),
        resume_data.get("portfolio", ""),
    ]
    contact_line = " | ".join(b for b in contact_bits if b)
    if contact_line:
        p = document.add_paragraph(contact_line)
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER

    if resume_data.get("summary_text"):
        _add_heading(document, "Professional Summary")
        document.add_paragraph(resume_data["summary_text"])

    if resume_data.get("skills"):
        _add_heading(document, "Skills")
        document.add_paragraph(", ".join(resume_data["skills"]))

    if resume_data.get("experience_bullets"):
        _add_heading(document, "Experience")
        for bullet in resume_data["experience_bullets"]:
            document.add_paragraph(bullet, style="List Bullet")

    if resume_data.get("projects_bullets"):
        _add_heading(document, "Projects")
        for bullet in resume_data["projects_bullets"]:
            document.add_paragraph(bullet, style="List Bullet")

    if resume_data.get("education_text"):
        _add_heading(document, "Education")
        for line in resume_data["education_text"].split("\n"):
            if line.strip():
                document.add_paragraph(line.strip())

    if resume_data.get("certifications_text"):
        _add_heading(document, "Certifications")
        for line in resume_data["certifications_text"].split("\n"):
            if line.strip():
                document.add_paragraph(line.strip())

    if resume_data.get("achievements_bullets"):
        _add_heading(document, "Achievements")
        for bullet in resume_data["achievements_bullets"]:
            document.add_paragraph(bullet, style="List Bullet")

    if resume_data.get("languages"):
        _add_heading(document, "Languages")
        document.add_paragraph(", ".join(resume_data["languages"]))

    buffer = io.BytesIO()
    document.save(buffer)
    return buffer.getvalue()
