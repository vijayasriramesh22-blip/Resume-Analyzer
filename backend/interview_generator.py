"""
interview_generator.py
------------------------
A fully rule-based Mock Interview engine.

- generate_questions(): builds a personalized set of interview questions
  from the candidate's extracted skills and project/experience bullets,
  mixed with general/behavioral questions.
- score_answers(): scores typed answers using keyword coverage + answer
  depth (word count) heuristics - the same kind of rule-based approach
  used by the ATS scorer, so no external AI grading is required.
"""

import re
from typing import Dict, List

from skills_db import GENERAL_INTERVIEW_QUESTIONS, SKILL_INTERVIEW_QUESTIONS, STRONG_ACTION_VERBS


def _project_question(bullet: str, idx: int) -> Dict:
    short = bullet.strip()
    if len(short) > 140:
        short = short[:137].rstrip() + "..."
    return {
        "id": f"project-{idx}",
        "category": "Project",
        "question": f"Walk me through this point from your resume: \"{short}\" "
                    f"What was your specific role, and what was the outcome?",
        "keywords": ["role", "result", "outcome", "challenge", "learned", "impact"],
    }


def generate_questions(
    skills: List[str],
    role: str = "",
    projects_bullets: List[str] = None,
    experience_bullets: List[str] = None,
    max_questions: int = 8,
) -> List[Dict]:
    """
    Builds a mixed set of interview questions:
    - 1-2 general/behavioral questions
    - up to 3 skill-specific technical questions (based on extracted skills)
    - up to 2 project/experience based questions (from resume bullets)
    """
    projects_bullets = projects_bullets or []
    experience_bullets = experience_bullets or []
    questions: List[Dict] = []

    # General / behavioral (always include a couple, for a well-rounded mock interview)
    for i, q in enumerate(GENERAL_INTERVIEW_QUESTIONS[:2]):
        questions.append({
            "id": f"general-{i}",
            "category": q["category"],
            "question": q["question"],
            "keywords": q["keywords"],
        })

    # Skill-specific technical questions, based on skills actually found in the resume
    tech_added = 0
    for skill in skills:
        bank = SKILL_INTERVIEW_QUESTIONS.get(skill.lower())
        if not bank:
            continue
        for q in bank:
            if tech_added >= 4:
                break
            questions.append({
                "id": f"tech-{tech_added}",
                "category": f"Technical ({skill})",
                "question": q["question"],
                "keywords": q["keywords"],
            })
            tech_added += 1
        if tech_added >= 4:
            break

    # Project / experience based questions, pulled directly from the resume
    source_bullets = (projects_bullets or [])[:2] + (experience_bullets or [])[:1]
    for i, bullet in enumerate(source_bullets[:3]):
        questions.append(_project_question(bullet, i))

    # One more behavioral question to round things out
    if len(GENERAL_INTERVIEW_QUESTIONS) > 2:
        q = GENERAL_INTERVIEW_QUESTIONS[2]
        questions.append({
            "id": "general-2",
            "category": q["category"],
            "question": q["question"],
            "keywords": q["keywords"],
        })

    return questions[:max_questions]


def _score_single_answer(answer: str, keywords: List[str]) -> Dict:
    issues = []
    answer_clean = answer.strip()
    answer_lower = answer_clean.lower()
    word_count = len(answer_clean.split())

    if not answer_clean:
        return {
            "score": 0,
            "word_count": 0,
            "matched_keywords": [],
            "issues": ["No answer was given."],
        }

    matched_keywords = [kw for kw in keywords if kw in answer_lower]
    keyword_coverage = len(matched_keywords) / len(keywords) if keywords else 0.5

    # Depth score: rewards a reasonably detailed answer, without requiring an essay
    if word_count < 15:
        depth_score = 0.3
        issues.append("Answer is quite short - try to add more specific detail or an example.")
    elif word_count < 40:
        depth_score = 0.7
    else:
        depth_score = 1.0

    # Bonus: using a strong action verb signals a confident, structured answer
    first_words = re.findall(r"[a-zA-Z']+", answer_lower)[:25]
    used_strong_verb = any(w in STRONG_ACTION_VERBS for w in first_words)
    verb_bonus = 0.05 if used_strong_verb else 0

    raw_score = (0.65 * keyword_coverage) + (0.35 * depth_score) + verb_bonus
    score = round(min(1.0, raw_score) * 100)

    if keyword_coverage < 0.4:
        issues.append("Try to mention the key concepts/terms the question is asking about.")
    if not used_strong_verb and word_count >= 15:
        issues.append("Consider starting with a strong action verb (e.g. 'Built', 'Led', 'Improved').")

    return {
        "score": score,
        "word_count": word_count,
        "matched_keywords": matched_keywords,
        "issues": issues,
    }


def score_answers(items: List[Dict]) -> Dict:
    """
    items: list of {"question": str, "category": str, "keywords": [...], "answer": str}
    Returns an overall mock-interview score plus per-question feedback.
    """
    per_question = []
    total = 0

    for item in items:
        result = _score_single_answer(item.get("answer", ""), item.get("keywords", []))
        per_question.append({
            "question": item.get("question", ""),
            "category": item.get("category", ""),
            **result,
        })
        total += result["score"]

    overall_score = round(total / len(items)) if items else 0

    if overall_score >= 80:
        summary = "Strong performance! Your answers were relevant and reasonably detailed."
    elif overall_score >= 55:
        summary = "Decent attempt - a few answers could use more specific detail or key terms."
    else:
        summary = "Needs more practice - try giving more complete answers with concrete examples."

    return {
        "overall_score": overall_score,
        "summary": summary,
        "per_question": per_question,
    }
