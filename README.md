# CareerPilot AI — Resume Analyzer (HTML/CSS + FastAPI edition)

This is the same Resume Analyzer & ATS Scorer as before, rebuilt with:
- **Backend:** Python FastAPI (serves the API + the website itself)
- **Frontend:** plain HTML, CSS, and JavaScript (no React/Next.js needed)

Still runs 100% locally — no OpenAI key, no internet connection needed
after install.

---

## Step-by-step setup (Windows)

### 1. Use Python 3.11 or 3.12

(Same as before — avoids the Pillow/pandas build issues on Python 3.14.)

### 2. Unzip this project

Extract to somewhere like `C:\Users\YourName\Desktop\careerpilot-html`.

### 3. Open a terminal inside the extracted folder

Open the folder in File Explorer → click the address bar → type `cmd` → Enter.

### 4. Create and activate a virtual environment

```
python -m venv venv
venv\Scripts\activate
```

### 5. Install dependencies

```
pip install -r requirements.txt
```

### 6. Run the backend server

```
cd backend
uvicorn main:app --reload
```

You should see something like:
```
Uvicorn running on http://127.0.0.1:8000
```

### 7. Open the app in your browser

Go to: **http://localhost:8000**

That's it — the same FastAPI server serves both the website (HTML/CSS/JS)
and the API it talks to, so you only need ONE thing running.

---

## How it works

- `backend/main.py` is the FastAPI server. It exposes:
  - `POST /api/analyze` — accepts a resume file, returns parsed details + ATS score
  - `POST /api/match` — accepts skills + a job description, returns a match score
  - `GET /api/roles` — lists supported target roles (Frontend Developer, Backend Developer, Data Scientist, etc.)
  - `POST /api/roadmap` — generates a staged career roadmap from your skills (and an optional target role)
  - `POST /api/interview/start` — generates personalized mock interview questions from your resume
  - `POST /api/interview/score` — scores your typed interview answers and gives feedback
  - `POST /api/resume/rewrite` — rewrites weak bullet points + generates a summary if missing
  - `POST /api/resume/download` — builds and downloads the improved resume as a `.docx`
  - Also serves the `frontend/` folder as the website itself
- `frontend/index.html` / `style.css` / `script.js` is the UI. It uses the
  browser's built-in `fetch()` to call the API above — no frameworks, no
  build step, no `npm install` needed.
- `backend/resume_parser.py`, `ats_scorer.py`, `jd_matcher.py`, `skills_db.py`
  contain the resume parsing + ATS scoring logic (rule-based engine).
- `backend/roadmap_generator.py` — rule-based career roadmap generator (role skill
  maps + a small learning-notes dictionary, no AI API).
- `backend/interview_generator.py` — rule-based mock interview question
  generator + keyword/depth-based answer scorer.
- `backend/resume_rewriter.py` — rule-based bullet-point rewriter (replaces weak
  phrasing with strong action verbs, generates a summary if missing) and a
  `.docx` builder using `python-docx`.

## New features

### 🎤 Mock Interview
Click **"Mock Interview"** after analyzing a resume. The app generates a mix of
general/behavioral questions, technical questions based on the skills found in
your resume, and questions about your specific projects/experience bullets.
Type your answers and click **"Submit Answers & Get Score"** to get a score
per question (based on keyword coverage + answer depth) plus an overall score
and feedback — all computed locally, no AI API key needed.

### 🗺️ Career Roadmap
Click **"Career Roadmap"**. The app either auto-detects the role your current
skills best match, or you can pick a target role from the dropdown (Frontend
Developer, Backend Developer, Data Scientist, etc.). It then shows your
readiness %, which skills you're missing, and a 3-stage (Foundation →
Intermediate → Advanced) learning plan with a short note on how to learn each
missing skill.

### ✍️ Rewrite Resume
Click **"Rewrite Resume"**. The app rewrites weak bullet points (e.g.
"Responsible for managing the timeline" → "Achieved managing the timeline")
and fills in a professional summary if one is missing. You can edit any of
the generated text directly in the browser, then click **"Download Updated
Resume (.docx)"** to download a clean, ATS-friendly Word document.

## Project structure

```
careerpilot-html/
├── backend/
│   ├── main.py                 # FastAPI app (run this with uvicorn)
│   ├── resume_parser.py
│   ├── ats_scorer.py
│   ├── jd_matcher.py
│   ├── roadmap_generator.py    # NEW: career roadmap
│   ├── interview_generator.py  # NEW: mock interview
│   ├── resume_rewriter.py      # NEW: resume rewrite + .docx export
│   └── skills_db.py
├── frontend/
│   ├── index.html
│   ├── style.css
│   └── script.js
├── requirements.txt
└── README.md
```

## Troubleshooting

- **"uvicorn: command not found"** → make sure your virtual environment is
  activated (you should see `(venv)` in your terminal prompt) and that
  `pip install -r requirements.txt` finished without errors.
- **Page loads but "Analyze Resume" does nothing** → open the browser's
  DevTools (F12) → Console tab, and check for a red error message. Send it
  to me if you're stuck.
- **CORS errors in console** → shouldn't happen since the frontend is
  served by the same FastAPI server, but if you ever open `index.html`
  directly as a file instead of through `http://localhost:8000`, that's
  what causes it. Always access the app through the link above.
- **Download button doesn't do anything** → check DevTools Console; this is
  usually a backend error visible in the terminal running `uvicorn`.

## What's NOT included yet (future modules)

LinkedIn/GitHub/Portfolio analyzers, Auth + Dashboard, PDF report export.
Let me know when you're ready to add one of these next.
