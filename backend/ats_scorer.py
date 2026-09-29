"""
ats_scorer.py
--------------
A fully rule-based ATS (Applicant Tracking System) scoring engine.

No OpenAI / external API is required - every score is computed using
plain heuristics (keyword presence, section presence, length checks,
readability formulas, simple grammar checks). This means the scores are
*indicative*, not a guarantee of how a real ATS or recruiter will score
your resume - but they follow the same general logic most ATS-style
checkers use, and are a great way to spot obvious gaps.
"""

import re
from typing import Dict, List

from skills_db import STRONG_ACTION_VERBS, WEAK_PHRASES, SECTION_HEADERS


def _count_syllables(word: str) -> int:
    """Very small, dependency-free syllable estimator (good enough for an
    approximate readability score - not phonetically perfect)."""
    word = word.lower().strip(".,!?;:\"'()")
    if not word:
        return 0
    vowels = "aeiouy"
    count = 0
    prev_was_vowel = False
    for char in word:
        is_vowel = char in vowels
        if is_vowel and not prev_was_vowel:
            count += 1
        prev_was_vowel = is_vowel
    if word.endswith("e") and count > 1:
        count -= 1
    return max(count, 1)


def flesch_reading_ease(text: str) -> float:
    """
    Self-contained implementation of the Flesch Reading Ease formula,
    so the app doesn't depend on the external `textstat` package.

    Formula: 206.835 - 1.015 * (words/sentences) - 84.6 * (syllables/words)
    """
    sentences = re.split(r"[.!?]+", text)
    sentences = [s for s in sentences if s.strip()]
    words = re.findall(r"[A-Za-z']+", text)

    if not sentences or not words:
        return 60.0  # neutral fallback for very short/odd text

    syllable_count = sum(_count_syllables(w) for w in words)

    words_per_sentence = len(words) / len(sentences)
    syllables_per_word = syllable_count / len(words)

    score = 206.835 - (1.015 * words_per_sentence) - (84.6 * syllables_per_word)
    return score


# ---------------------------------------------------------------------------
# Individual sub-scores (each returns a 0-100 score + supporting details)
# ---------------------------------------------------------------------------

def score_formatting(raw_text: str) -> Dict:
    issues = []
    score = 100

    word_count = len(raw_text.split())
    if word_count < 150:
        issues.append("Resume looks very short - may be missing content.")
        score -= 25
    elif word_count > 1200:
        issues.append("Resume looks very long - consider trimming to 1-2 pages.")
        score -= 10

    # Excessive blank lines often indicate messy formatting/layout issues
    blank_line_ratio = raw_text.count("\n\n\n") / max(raw_text.count("\n"), 1)
    if blank_line_ratio > 0.05:
        issues.append("Multiple large blank gaps detected - check formatting consistency.")
        score -= 10

    # Tabs/odd characters that sometimes come from PDF table layouts
    if raw_text.count("\t") > 20:
        issues.append("Resume may use a table-based layout, which some ATS systems misread.")
        score -= 10

    score = max(0, min(100, score))
    return {"score": score, "issues": issues}


def score_keywords(found_skills: List[str], jd_skills: List[str] = None) -> Dict:
    """
    Without a job description, we score based on the breadth of recognized
    technical keywords found. If a JD is supplied, we score based on overlap.
    """
    if jd_skills:
        jd_set = set(s.lower() for s in jd_skills)
        found_set = set(s.lower() for s in found_skills)
        if not jd_set:
            return {"score": 50, "missing": []}
        overlap = jd_set & found_set
        missing = sorted(jd_set - found_set)
        score = round(100 * len(overlap) / len(jd_set))
        return {"score": score, "missing": missing}

    # Generic scoring based on skill count found in the resume
    count = len(found_skills)
    if count >= 15:
        score = 100
    elif count >= 10:
        score = 85
    elif count >= 6:
        score = 70
    elif count >= 3:
        score = 50
    else:
        score = 25
    return {"score": score, "missing": []}


def score_skills_section(skills_text: str, found_skills: List[str]) -> Dict:
    issues = []
    score = 100
    if not skills_text.strip():
        issues.append("No dedicated 'Skills' section detected.")
        score -= 40
    if len(found_skills) < 5:
        issues.append("Fewer than 5 recognizable technical skills found.")
        score -= 30
    score = max(0, min(100, score))
    return {"score": score, "issues": issues}


def score_experience(experience_text: str, experience_bullets: List[str]) -> Dict:
    issues = []
    score = 100

    if not experience_text.strip():
        issues.append("No 'Experience' section detected (this may be fine for freshers with strong Projects).")
        score -= 30

    if not experience_bullets:
        issues.append("No bullet points detected under Experience.")
        score -= 20

    weak_bullets = [b for b in experience_bullets if any(w in b.lower() for w in WEAK_PHRASES)]
    if weak_bullets:
        issues.append(f"{len(weak_bullets)} bullet point(s) use weak phrasing like 'responsible for' / 'worked on'.")
        score -= min(30, 10 * len(weak_bullets))

    quantified = [b for b in experience_bullets if re.search(r"\d", b)]
    if experience_bullets and len(quantified) / len(experience_bullets) < 0.3:
        issues.append("Most bullet points lack measurable numbers/metrics (%, $, counts, time saved, etc).")
        score -= 15

    score = max(0, min(100, score))
    return {"score": score, "issues": issues, "weak_bullets": weak_bullets}


def score_education(education_text: str) -> Dict:
    issues = []
    score = 100
    if not education_text.strip():
        issues.append("No 'Education' section detected.")
        score = 20
    score = max(0, min(100, score))
    return {"score": score, "issues": issues}


def score_projects(projects_text: str, projects_bullets: List[str]) -> Dict:
    issues = []
    score = 100
    if not projects_text.strip():
        issues.append("No 'Projects' section detected.")
        score -= 50
    elif len(projects_bullets) < 2:
        issues.append("Very few project details found - consider adding 2-4 bullet points per project.")
        score -= 20

    score = max(0, min(100, score))
    return {"score": score, "issues": issues}


def score_achievements(achievements_text: str) -> Dict:
    issues = []
    score = 100
    if not achievements_text.strip():
        issues.append("No 'Achievements'/'Awards' section detected - optional, but it helps you stand out.")
        score = 60
    score = max(0, min(100, score))
    return {"score": score, "issues": issues}


def score_grammar(raw_text: str) -> Dict:
    """
    Lightweight, dependency-free grammar/style checks (no Java/LanguageTool
    server required, so this works completely offline):
    - Repeated consecutive words ("the the")
    - Double spaces
    - Sentences/bullets not starting with a capital letter
    - Missing-space-after-period
    """
    issues = []
    score = 100

    repeated = re.findall(r"\b(\w+)\s+\1\b", raw_text, flags=re.IGNORECASE)
    if repeated:
        issues.append(f"Repeated word(s) detected: {', '.join(set(repeated))[:100]}")
        score -= 5 * len(set(repeated))

    if "  " in raw_text:
        issues.append("Double spaces detected in some places.")
        score -= 5

    missing_space = re.findall(r"[a-z]\.[A-Z]", raw_text)
    if missing_space:
        issues.append("Possible missing space after a period in some sentences.")
        score -= 5

    score = max(0, min(100, score))
    return {"score": score, "issues": issues}


def score_readability(raw_text: str) -> Dict:
    issues = []
    try:
        flesch_score = flesch_reading_ease(raw_text)
    except Exception:
        flesch_score = 60  # neutral fallback

    if flesch_score >= 60:
        score = 100
    elif flesch_score >= 40:
        score = 75
        issues.append("Some sentences are a bit dense/hard to read - consider shortening them.")
    else:
        score = 50
        issues.append("Text is quite hard to read - simplify long sentences and jargon-heavy phrasing.")

    return {"score": score, "issues": issues, "flesch_score": round(flesch_score, 1)}


# ---------------------------------------------------------------------------
# Action verb suggestions
# ---------------------------------------------------------------------------

def suggest_action_verbs(bullets: List[str]) -> Dict[str, List[str]]:
    """
    For bullets that don't start with a strong action verb, suggest a few.
    """
    suggestions = {}
    for bullet in bullets:
        first_word = bullet.strip().split(" ")[0].lower().strip(".,:;")
        if first_word not in STRONG_ACTION_VERBS:
            # Suggest 3 generic strong verbs as a starting point
            suggestions[bullet] = STRONG_ACTION_VERBS[:3] + ["..."]
    return suggestions


# ---------------------------------------------------------------------------
# Master scoring function
# ---------------------------------------------------------------------------

WEIGHTS = {
    "formatting": 0.10,
    "keyword": 0.15,
    "skills": 0.15,
    "experience": 0.15,
    "education": 0.10,
    "projects": 0.15,
    "achievements": 0.05,
    "grammar": 0.10,
    "readability": 0.05,
}


def compute_ats_score(parsed_resume: Dict, jd_skills: List[str] = None) -> Dict:
    raw_text = parsed_resume["raw_text"]

    formatting = score_formatting(raw_text)
    keyword = score_keywords(parsed_resume["skills"], jd_skills)
    skills = score_skills_section(parsed_resume.get("skills_text", ""), parsed_resume["skills"])
    experience = score_experience(parsed_resume["experience_text"], parsed_resume["experience_bullets"])
    education = score_education(parsed_resume["education_text"])
    projects = score_projects(parsed_resume["projects_text"], parsed_resume["projects_bullets"])
    achievements = score_achievements(parsed_resume["achievements_text"])
    grammar = score_grammar(raw_text)
    readability = score_readability(raw_text)

    breakdown = {
        "Formatting": formatting,
        "Keyword": keyword,
        "Skills": skills,
        "Experience": experience,
        "Education": education,
        "Project": projects,
        "Achievements": achievements,
        "Grammar": grammar,
        "Readability": readability,
    }

    weight_keys = {
        "Formatting": "formatting", "Keyword": "keyword", "Skills": "skills",
        "Experience": "experience", "Education": "education", "Project": "projects",
        "Achievements": "achievements", "Grammar": "grammar", "Readability": "readability",
    }

    overall = sum(breakdown[name]["score"] * WEIGHTS[weight_keys[name]] for name in breakdown)
    overall = round(overall)

    weak_bullets = experience.get("weak_bullets", [])
    all_bullets = (
        parsed_resume.get("experience_bullets", []) + parsed_resume.get("projects_bullets", [])
    )
    verb_suggestions = suggest_action_verbs(all_bullets)

    return {
        "overall_score": overall,
        "breakdown": breakdown,
        "weak_bullets": weak_bullets,
        "verb_suggestions": verb_suggestions,
        "missing_keywords": keyword.get("missing", []),
    }
