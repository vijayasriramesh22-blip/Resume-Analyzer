"""
roadmap_generator.py
----------------------
A fully rule-based Career Roadmap generator.

Given the skills extracted from a resume (and optionally a target role
chosen by the user), this works out:
- The best-matching role for the candidate right now (if no role is chosen)
- Which skills from that role's expected skill set are missing
- A 3-stage learning roadmap (Foundation -> Intermediate -> Advanced) for
  those missing skills, each with a short learning note

No external AI API is used - everything is plain dictionary lookups and
simple scoring, matching the rest of this app's offline, rule-based design.
"""

from typing import Dict, List, Optional

from skills_db import ROLE_SKILLS_MAP, SKILL_LEARNING_NOTES


def list_roles() -> List[str]:
    """Returns the list of supported target roles (for a dropdown, etc.)."""
    return sorted(ROLE_SKILLS_MAP.keys())


def _best_matching_role(resume_skills: List[str]) -> str:
    """
    Picks the role whose expected skill set overlaps the most with the
    candidate's current skills (ties broken by role name for determinism).
    """
    resume_set = set(s.lower() for s in resume_skills)
    best_role = None
    best_overlap = -1
    for role, role_skills in sorted(ROLE_SKILLS_MAP.items()):
        role_set = set(s.lower() for s in role_skills)
        overlap = len(resume_set & role_set)
        if overlap > best_overlap:
            best_overlap = overlap
            best_role = role
    return best_role or "Full Stack Developer"


def _learning_note(skill: str) -> str:
    note = SKILL_LEARNING_NOTES.get(skill.lower())
    if note:
        return note
    return f"Learn the fundamentals of {skill} through official docs/tutorials, then apply it in a small project."


def _split_into_stages(missing_skills: List[str]) -> List[Dict]:
    """
    Splits the missing skills into 3 roughly-equal stages. Earlier stages
    get the more 'foundational' looking skills where possible (no strict
    ordering data available, so this is a simple even split - good enough
    for a directional roadmap).
    """
    stage_names = ["Foundation", "Intermediate", "Advanced"]
    stage_durations = ["2-4 weeks", "4-6 weeks", "6-8 weeks"]
    if not missing_skills:
        return []

    n = len(missing_skills)
    chunk_size = max(1, -(-n // 3))  # ceil division into up to 3 chunks
    stages = []
    for i, name in enumerate(stage_names):
        start = i * chunk_size
        end = start + chunk_size
        chunk = missing_skills[start:end]
        if not chunk:
            continue
        stages.append({
            "stage": name,
            "estimated_duration": stage_durations[i],
            "skills": [
                {"skill": s, "note": _learning_note(s)} for s in chunk
            ],
        })
    return stages


def generate_roadmap(resume_skills: List[str], target_role: Optional[str] = None) -> Dict:
    """
    Main entry point. Returns a dict with:
    - detected_role / target_role (whichever applies)
    - matched_skills / missing_skills (vs the role's expected skill set)
    - readiness_percent: how ready the candidate already is for that role
    - roadmap: list of stages, each with skills + short learning notes
    - role_options: all supported roles (for letting the user switch)
    """
    role_options = list_roles()

    if target_role and target_role in ROLE_SKILLS_MAP:
        role = target_role
        auto_detected = False
    else:
        role = _best_matching_role(resume_skills)
        auto_detected = True

    role_skills = ROLE_SKILLS_MAP[role]
    resume_set = set(s.lower() for s in resume_skills)
    role_set = set(s.lower() for s in role_skills)

    matched = sorted(resume_set & role_set)
    missing = sorted(role_set - resume_set)

    readiness_percent = round(100 * len(matched) / len(role_set)) if role_set else 0
    roadmap_stages = _split_into_stages(missing)

    return {
        "role": role,
        "auto_detected": auto_detected,
        "role_options": role_options,
        "matched_skills": matched,
        "missing_skills": missing,
        "readiness_percent": readiness_percent,
        "roadmap": roadmap_stages,
    }
