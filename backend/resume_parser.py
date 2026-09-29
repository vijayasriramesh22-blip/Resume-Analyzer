"""
resume_parser.py
------------------
Handles:
1. Extracting raw text from an uploaded PDF, DOCX, or photo/image (via OCR)
   of a resume.
2. Pulling out structured fields (name, email, phone, links, skills,
   education, experience, projects, certifications, achievements, languages).

No external AI API is used here - everything is done with plain text
processing (regex + keyword matching), so it runs fully offline. Image
resumes (camera photo or gallery upload) are read with Tesseract OCR.
"""

import re
import io
from typing import Dict, List

import pdfplumber
import docx  # python-docx
from PIL import Image
import pytesseract

from skills_db import SKILLS_DB, SECTION_HEADERS

IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png", ".webp", ".bmp", ".heic")


# ---------------------------------------------------------------------------
# Step 1: Extract raw text from the uploaded file
# ---------------------------------------------------------------------------

def extract_text_from_pdf(file_bytes: bytes) -> str:
    text_chunks = []
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text_chunks.append(page_text)
    return "\n".join(text_chunks)


def extract_text_from_docx(file_bytes: bytes) -> str:
    document = docx.Document(io.BytesIO(file_bytes))
    paragraphs = [p.text for p in document.paragraphs]
    # Also pull text out of tables (some resumes use table layouts)
    for table in document.tables:
        for row in table.rows:
            for cell in row.cells:
                if cell.text.strip():
                    paragraphs.append(cell.text)
    return "\n".join(paragraphs)


def extract_text_from_image(file_bytes: bytes) -> str:
    """
    Runs OCR (Tesseract) on a photo/screenshot of a resume - used for
    both the camera-capture and gallery-upload flows.
    """
    image = Image.open(io.BytesIO(file_bytes))
    if image.mode != "RGB":
        image = image.convert("RGB")
    text = pytesseract.image_to_string(image)
    return text


def extract_text(file_bytes: bytes, filename: str) -> str:
    lower_name = filename.lower()
    if lower_name.endswith(".pdf"):
        return extract_text_from_pdf(file_bytes)
    elif lower_name.endswith(".docx"):
        return extract_text_from_docx(file_bytes)
    elif lower_name.endswith(IMAGE_EXTENSIONS):
        return extract_text_from_image(file_bytes)
    else:
        raise ValueError(
            "Unsupported file type. Please upload a PDF, DOCX, or a photo (JPG/PNG) of your resume."
        )


# ---------------------------------------------------------------------------
# Step 2: Field extraction helpers
# ---------------------------------------------------------------------------

EMAIL_REGEX = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
PHONE_REGEX = re.compile(r"(\+?\d{1,3}[-.\s]?)?\(?\d{3,5}\)?[-.\s]?\d{3,4}[-.\s]?\d{3,4}")
LINKEDIN_REGEX = re.compile(r"(https?://)?(www\.)?linkedin\.com/[A-Za-z0-9_/\-.%]+", re.IGNORECASE)
GITHUB_REGEX = re.compile(r"(https?://)?(www\.)?github\.com/[A-Za-z0-9_/\-.%]+", re.IGNORECASE)
PORTFOLIO_REGEX = re.compile(
    r"(https?://)?(www\.)?[a-zA-Z0-9\-]+\.(dev|me|io|com|in|netlify\.app|vercel\.app|github\.io)\S*",
    re.IGNORECASE,
)

COMMON_LANGUAGES = [
    "english", "hindi", "tamil", "telugu", "kannada", "malayalam", "marathi",
    "gujarati", "bengali", "punjabi", "urdu", "french", "german", "spanish",
    "japanese", "chinese", "mandarin", "korean", "russian", "arabic",
]


def extract_email(text: str) -> str:
    match = EMAIL_REGEX.search(text)
    return match.group(0) if match else ""


def extract_phone(text: str) -> str:
    match = PHONE_REGEX.search(text)
    return match.group(0).strip() if match else ""


def extract_links(text: str) -> Dict[str, str]:
    linkedin = LINKEDIN_REGEX.search(text)
    github = GITHUB_REGEX.search(text)

    # Strip out the email's domain so it isn't mistaken for a portfolio link
    email_match = EMAIL_REGEX.search(text)
    email_domain = email_match.group(0).split("@")[1].lower() if email_match else None

    # Portfolio: any URL-like string that isn't linkedin/github/the email domain
    portfolio = ""
    for match in PORTFOLIO_REGEX.finditer(text):
        candidate = match.group(0)
        candidate_lower = candidate.lower()
        if "linkedin.com" in candidate_lower or "github.com" in candidate_lower:
            continue
        if email_domain and email_domain in candidate_lower:
            continue
        portfolio = candidate
        break

    return {
        "linkedin": linkedin.group(0) if linkedin else "",
        "github": github.group(0) if github else "",
        "portfolio": portfolio,
    }


def extract_name(text: str) -> str:
    """
    Heuristic: the name is usually the first non-empty line that
    doesn't look like an email/phone/section header and is reasonably short.
    """
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    for line in lines[:6]:
        if EMAIL_REGEX.search(line) or PHONE_REGEX.search(line):
            continue
        if len(line.split()) <= 5 and len(line) < 60 and not line.isupper():
            # Avoid lines that are clearly section headers
            lowered = line.lower()
            if any(lowered.startswith(h) for headers in SECTION_HEADERS.values() for h in headers):
                continue
            return line
    return lines[0] if lines else "Not found"


def extract_skills(text: str) -> List[str]:
    text_lower = text.lower()
    found = []
    for skill in SKILLS_DB:
        # Use word-boundary-ish matching to avoid partial false positives like "r" inside "are"
        pattern = r"(?<![a-zA-Z0-9])" + re.escape(skill) + r"(?![a-zA-Z0-9])"
        if re.search(pattern, text_lower):
            found.append(skill)
    return sorted(set(found))


def extract_languages(text: str) -> List[str]:
    text_lower = text.lower()
    found = [lang.capitalize() for lang in COMMON_LANGUAGES if re.search(
        r"(?<![a-zA-Z])" + re.escape(lang) + r"(?![a-zA-Z])", text_lower)]
    return sorted(set(found))


def _get_section_text(text: str, section_key: str) -> str:
    """
    Extracts the block of text belonging to a given section (e.g. "experience")
    by finding its header and reading until the next known header.
    """
    lines = text.split("\n")
    lower_lines = [l.lower().strip() for l in lines]

    all_headers = [h for header_list in SECTION_HEADERS.values() for h in header_list]
    start_idx = None

    for idx, line in enumerate(lower_lines):
        for header in SECTION_HEADERS.get(section_key, []):
            if line == header or line.startswith(header):
                start_idx = idx + 1
                break
        if start_idx is not None:
            break

    if start_idx is None:
        return ""

    end_idx = len(lines)
    for idx in range(start_idx, len(lines)):
        candidate = lower_lines[idx]
        if candidate and any(candidate == h or candidate.startswith(h) for h in all_headers):
            end_idx = idx
            break

    return "\n".join(lines[start_idx:end_idx]).strip()


def extract_bullet_points(section_text: str) -> List[str]:
    bullets = []
    for line in section_text.split("\n"):
        clean = line.strip(" \u2022-*\t")
        if clean and len(clean) > 3:
            bullets.append(clean)
    return bullets


def parse_resume(file_bytes: bytes, filename: str) -> Dict:
    raw_text = extract_text(file_bytes, filename)

    if not raw_text or len(raw_text.strip()) < 30:
        raise ValueError(
            "Could not extract readable text from this file. "
            "It may be a scanned/image-based resume, which this tool can't read yet."
        )

    links = extract_links(raw_text)

    parsed = {
        "raw_text": raw_text,
        "name": extract_name(raw_text),
        "email": extract_email(raw_text),
        "phone": extract_phone(raw_text),
        "linkedin": links["linkedin"],
        "github": links["github"],
        "portfolio": links["portfolio"],
        "skills": extract_skills(raw_text),
        "languages": extract_languages(raw_text),
        "summary_text": _get_section_text(raw_text, "summary"),
        "experience_text": _get_section_text(raw_text, "experience"),
        "education_text": _get_section_text(raw_text, "education"),
        "projects_text": _get_section_text(raw_text, "projects"),
        "certifications_text": _get_section_text(raw_text, "certifications"),
        "achievements_text": _get_section_text(raw_text, "achievements"),
    }

    parsed["experience_bullets"] = extract_bullet_points(parsed["experience_text"])
    parsed["projects_bullets"] = extract_bullet_points(parsed["projects_text"])
    parsed["achievements_bullets"] = extract_bullet_points(parsed["achievements_text"])

    return parsed
