"""
jd_matcher.py
--------------
Simple keyword-overlap based Job Description matcher.
No AI API needed - extracts known skills from the JD text and
compares against the resume's extracted skills.
"""

from typing import Dict, List
from resume_parser import extract_skills


def match_resume_to_jd(resume_skills: List[str], jd_text: str) -> Dict:
    jd_skills = extract_skills(jd_text)

    resume_set = set(s.lower() for s in resume_skills)
    jd_set = set(s.lower() for s in jd_skills)

    if not jd_set:
        return {
            "match_percent": 0,
            "matched_skills": [],
            "missing_skills": [],
            "jd_skills": [],
        }

    matched = sorted(resume_set & jd_set)
    missing = sorted(jd_set - resume_set)
    match_percent = round(100 * len(matched) / len(jd_set))

    return {
        "match_percent": match_percent,
        "matched_skills": matched,
        "missing_skills": missing,
        "jd_skills": sorted(jd_set),
    }
