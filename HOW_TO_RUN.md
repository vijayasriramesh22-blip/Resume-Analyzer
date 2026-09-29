# CareerPilot AI — How to Run

## Run locally (your own PC)

```
cd CareerPilotAI
python -m venv venv
venv\Scripts\activate        (Windows)   OR   source venv/bin/activate   (Mac/Linux)
pip install -r requirements.txt
cd backend
uvicorn main:app --reload
```

Open http://localhost:8000 — this only works on the machine running the command.

### One extra system dependency for photo uploads (camera / gallery)
Reading a resume from a **photo** uses OCR (Tesseract), which needs a system
binary in addition to the `pip install`:
- Windows: install from https://github.com/UB-Mannheim/tesseract/wiki (or `choco install tesseract`)
- Mac: `brew install tesseract`
- Linux: `sudo apt-get install tesseract-ocr`

Uploading a PDF or DOCX still works with no extra setup.

## Deploy so anyone (friends, recruiters) can use it

1. Push this folder to GitHub (venv/ is already excluded via .gitignore):
   ```
   git init
   git add .
   git commit -m "CareerPilot AI"
   git branch -M main
   git remote add origin https://github.com/vijayasriramesh22-blip/CareerPilot-AI.git
   git push -u origin main --force
   ```

2. Go to https://render.com → New → Web Service → connect this repo.
   Render will read render.yaml automatically:
   - Build Command: pip install -r requirements.txt
   - Start Command: uvicorn backend.main:app --host 0.0.0.0 --port $PORT

3. Click Create Web Service. Wait for the build to finish.

4. You'll get a public link like:
   https://careerpilot-ai.onrender.com

   Share THIS link — not the HTML file — so uploads work for everyone.

Note: Free Render apps sleep after 15 min idle; first request after that takes ~30-50 sec to wake up.

## Running / deploying on Streamlit

A Streamlit version of this app is included: `streamlit_app.py`. It reuses
the exact same backend logic (parsing, ATS scoring, JD match, roadmap, mock
interview, resume rewriter) - just with a Streamlit UI instead of the
HTML/JS frontend, in a single file, so it deploys easily to Streamlit
Community Cloud.

**Run it locally:**
```
pip install -r requirements.txt
streamlit run streamlit_app.py
```
It opens at http://localhost:8501. Upload options are built in natively:
"Upload File" (PDF/DOCX), "Take a Photo" (uses `st.camera_input`, opens your
device's actual camera), and "Choose from Gallery" (image file picker).

**Deploy to Streamlit Community Cloud (free):**
1. Push this project to a GitHub repo.
2. Go to https://share.streamlit.io, sign in with GitHub, click "New app".
3. Pick your repo/branch, and set **Main file path** to `streamlit_app.py`.
4. Deploy. Streamlit Cloud installs everything in `requirements.txt`
   automatically.

**Photo upload (OCR) needs one extra system package** on Streamlit Cloud:
add a file named `packages.txt` (already included in this project, at the
repo root, next to `requirements.txt`) containing just:
```
tesseract-ocr
```
Streamlit Cloud reads `packages.txt` and installs it via `apt-get`
automatically during deploy - no extra steps needed from you.
