/* ===========================================================
   CareerPilot AI — script.js
   Talks to the FastAPI backend at /api/analyze and /api/match
=========================================================== */

const API_BASE = ""; // same origin, since FastAPI serves this frontend too

// ---- Element references ----
const fileInput = document.getElementById("fileInput");
const cameraBtn = document.getElementById("cameraBtn");
const cameraFallbackInput = document.getElementById("cameraFallbackInput");
const galleryInput = document.getElementById("galleryInput");
const dropzone = document.getElementById("dropzone");
const dropzoneText = document.getElementById("dropzoneText");
const jdText = document.getElementById("jdText");
const analyzeBtn = document.getElementById("analyzeBtn");
const uploadError = document.getElementById("uploadError");

const uploadSection = document.getElementById("uploadSection");
const loadingSection = document.getElementById("loadingSection");
const resultsSection = document.getElementById("resultsSection");
const reanalyzeBtn = document.getElementById("reanalyzeBtn");

let selectedFile = null;
let lastResumeSkills = [];
let lastParsed = null;
let lastDetectedRole = "";
let lastAtsMissingKeywords = [];
let lastJdMissingSkills = [];
let interviewQuestions = [];

const IMAGE_EXTENSIONS = [".jpg", ".jpeg", ".png", ".webp", ".bmp", ".heic"];

// ---- File selection (click or drag/drop, or gallery) ----
fileInput.addEventListener("change", (e) => {
  if (e.target.files.length > 0) {
    handleFileSelected(e.target.files[0]);
  }
});

galleryInput.addEventListener("change", (e) => {
  if (e.target.files.length > 0) {
    handleFileSelected(e.target.files[0]);
  }
});

cameraFallbackInput.addEventListener("change", (e) => {
  if (e.target.files.length > 0) {
    handleFileSelected(e.target.files[0]);
  }
});

// ---- Live camera capture ("Take a Photo") ----
const cameraModal = document.getElementById("cameraModal");
const cameraVideo = document.getElementById("cameraVideo");
const cameraCanvas = document.getElementById("cameraCanvas");
const cameraError = document.getElementById("cameraError");
const cameraCancelBtn = document.getElementById("cameraCancelBtn");
const cameraCaptureBtn = document.getElementById("cameraCaptureBtn");
let cameraStream = null;

cameraBtn.addEventListener("click", async () => {
  // Live in-page camera needs getUserMedia, which needs a secure context
  // (https, or http://localhost). If it isn't available, fall back to the
  // OS's own camera capture via the hidden capture-enabled file input.
  if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
    cameraFallbackInput.click();
    return;
  }

  cameraError.textContent = "";
  cameraModal.classList.remove("hidden");

  try {
    cameraStream = await navigator.mediaDevices.getUserMedia({
      video: { facingMode: "environment" },
      audio: false,
    });
    cameraVideo.srcObject = cameraStream;
  } catch (err) {
    console.error("Camera access failed:", err);
    closeCameraModal();
    // Permission denied / no camera - fall back to the OS camera capture.
    cameraFallbackInput.click();
  }
});

cameraCaptureBtn.addEventListener("click", () => {
  if (!cameraStream) return;
  const width = cameraVideo.videoWidth;
  const height = cameraVideo.videoHeight;
  cameraCanvas.width = width;
  cameraCanvas.height = height;
  const ctx = cameraCanvas.getContext("2d");
  ctx.drawImage(cameraVideo, 0, 0, width, height);

  cameraCanvas.toBlob(
    (blob) => {
      if (blob) {
        const file = new File([blob], "resume-photo.jpg", { type: "image/jpeg" });
        handleFileSelected(file);
      }
      closeCameraModal();
    },
    "image/jpeg",
    0.92
  );
});

cameraCancelBtn.addEventListener("click", closeCameraModal);

function closeCameraModal() {
  if (cameraStream) {
    cameraStream.getTracks().forEach((track) => track.stop());
    cameraStream = null;
  }
  cameraVideo.srcObject = null;
  cameraModal.classList.add("hidden");
}

["dragover", "dragenter"].forEach((evt) => {
  dropzone.addEventListener(evt, (e) => {
    e.preventDefault();
    dropzone.classList.add("dragover");
  });
});

["dragleave", "drop"].forEach((evt) => {
  dropzone.addEventListener(evt, (e) => {
    e.preventDefault();
    dropzone.classList.remove("dragover");
  });
});

dropzone.addEventListener("drop", (e) => {
  if (e.dataTransfer.files.length > 0) {
    handleFileSelected(e.dataTransfer.files[0]);
  }
});

function handleFileSelected(file) {
  const lowerName = file.name.toLowerCase();
  const isPdfOrDocx = lowerName.endsWith(".pdf") || lowerName.endsWith(".docx");
  const isImage = IMAGE_EXTENSIONS.some((ext) => lowerName.endsWith(ext)) || file.type.startsWith("image/");

  if (!isPdfOrDocx && !isImage) {
    uploadError.textContent = "Please choose a PDF, DOCX, or a photo (JPG/PNG) of your resume.";
    selectedFile = null;
    analyzeBtn.disabled = true;
    return;
  }
  selectedFile = file;
  uploadError.textContent = "";
  dropzoneText.textContent = `Selected: ${file.name}`;
  analyzeBtn.disabled = false;
}

// ---- Analyze button ----
analyzeBtn.addEventListener("click", async () => {
  if (!selectedFile) return;

  uploadError.textContent = "";
  uploadSection.classList.add("hidden");
  loadingSection.classList.remove("hidden");
  resultsSection.classList.add("hidden");

  const formData = new FormData();
  // Camera captures sometimes come through without a recognizable file
  // extension (e.g. just "image") - fall back to the MIME type so the
  // backend can still tell it's a photo to run OCR on.
  let uploadName = selectedFile.name;
  const hasKnownExt = /\.(pdf|docx|jpg|jpeg|png|webp|bmp|heic)$/i.test(uploadName);
  if (!hasKnownExt && selectedFile.type.startsWith("image/")) {
    const ext = selectedFile.type.split("/")[1] || "jpg";
    uploadName = `resume-photo.${ext}`;
  }
  formData.append("file", selectedFile, uploadName);

  try {
    const res = await fetch(`${API_BASE}/api/analyze`, {
      method: "POST",
      body: formData,
    });

    if (!res.ok) {
      const errBody = await res.json().catch(() => ({}));
      throw new Error(errBody.detail || `Server error (${res.status})`);
    }

    const data = await res.json();
    lastResumeSkills = data.parsed.skills || [];
    lastParsed = data.parsed;
    lastAtsMissingKeywords = data.ats.missing_keywords || [];
    lastJdMissingSkills = [];
    renderResults(data.parsed, data.ats);
    resetFeatureSections();

    // If a JD was pasted, run the match too
    const jd = jdText.value.trim();
    if (jd) {
      await runJdMatch(jd);
    }

    loadingSection.classList.add("hidden");
    resultsSection.classList.remove("hidden");
  } catch (err) {
    loadingSection.classList.add("hidden");
    uploadSection.classList.remove("hidden");
    uploadError.textContent = `Something went wrong: ${err.message}`;
  }
});

// ---- Re-analyze (go back to upload screen) ----
reanalyzeBtn.addEventListener("click", () => {
  resultsSection.classList.add("hidden");
  uploadSection.classList.remove("hidden");
  fileInput.value = "";
  cameraFallbackInput.value = "";
  galleryInput.value = "";
  selectedFile = null;
  dropzoneText.textContent = "Click to choose a file or drag it here";
  analyzeBtn.disabled = true;
  resetFeatureSections();
});

// ---- Rendering ----
function renderResults(parsed, ats) {
  // Score banner
  document.getElementById("overallScoreNumber").textContent = ats.overall_score;
  document.getElementById("profileName").textContent = parsed.name || "—";
  document.getElementById("profileEmail").textContent = parsed.email ? `📧 ${parsed.email}` : "";
  document.getElementById("profilePhone").textContent = parsed.phone ? `📞 ${parsed.phone}` : "";

  const linksEl = document.getElementById("profileLinks");
  linksEl.innerHTML = "";
  const linkDefs = [
    ["linkedin", "LinkedIn"],
    ["github", "GitHub"],
    ["portfolio", "Portfolio"],
  ];
  linkDefs.forEach(([key, label]) => {
    if (parsed[key]) {
      const a = document.createElement("a");
      const href = parsed[key].startsWith("http") ? parsed[key] : `https://${parsed[key]}`;
      a.href = href;
      a.target = "_blank";
      a.rel = "noopener";
      a.textContent = label;
      linksEl.appendChild(a);
    }
  });

  // Score circle color based on score
  const circle = document.getElementById("overallScoreCircle");
  circle.style.background = scoreToGradient(ats.overall_score);

  // Breakdown grid
  const grid = document.getElementById("breakdownGrid");
  grid.innerHTML = "";
  Object.entries(ats.breakdown).forEach(([name, data]) => {
    const item = document.createElement("div");
    item.className = "breakdown-item";
    item.innerHTML = `
      <div class="breakdown-top">
        <span>${name}</span>
        <span>${data.score}/100</span>
      </div>
      <div class="progress-bar">
        <div class="progress-fill ${scoreToClass(data.score)}" style="width:${data.score}%"></div>
      </div>
    `;
    grid.appendChild(item);
  });

  // Issues
  const issuesContainer = document.getElementById("issuesContainer");
  issuesContainer.innerHTML = "";
  let anyIssue = false;

  Object.entries(ats.breakdown).forEach(([name, data]) => {
    if (data.issues && data.issues.length > 0) {
      anyIssue = true;
      const details = document.createElement("details");
      details.className = "issue-group";
      const summary = document.createElement("summary");
      summary.textContent = `${name} — ${data.issues.length} suggestion(s)`;
      const ul = document.createElement("ul");
      data.issues.forEach((issue) => {
        const li = document.createElement("li");
        li.textContent = issue;
        ul.appendChild(li);
      });
      details.appendChild(summary);
      details.appendChild(ul);
      issuesContainer.appendChild(details);
    }
  });

  if (ats.weak_bullets && ats.weak_bullets.length > 0) {
    anyIssue = true;
    const details = document.createElement("details");
    details.className = "issue-group";
    const summary = document.createElement("summary");
    summary.textContent = `⚠️ Weak bullet points (${ats.weak_bullets.length})`;
    const ul = document.createElement("ul");
    ats.weak_bullets.forEach((b) => {
      const li = document.createElement("li");
      li.textContent = b;
      ul.appendChild(li);
    });
    details.appendChild(summary);
    details.appendChild(ul);
    issuesContainer.appendChild(details);
  }

  if (!anyIssue) {
    const p = document.createElement("p");
    p.className = "success-msg";
    p.textContent = "No major issues detected! 🎉";
    issuesContainer.appendChild(p);
  }

  // Tabs content
  const skillsTab = document.getElementById("tab-skills");
  skillsTab.innerHTML = "";
  if (parsed.skills && parsed.skills.length > 0) {
    parsed.skills.forEach((s) => {
      const chip = document.createElement("span");
      chip.className = "skill-chip";
      chip.textContent = s;
      skillsTab.appendChild(chip);
    });
  } else {
    skillsTab.innerHTML = '<p class="muted">No recognizable technical skills found.</p>';
  }
  if (parsed.languages && parsed.languages.length > 0) {
    const langP = document.createElement("p");
    langP.className = "muted";
    langP.style.marginTop = "0.8rem";
    langP.textContent = `Languages: ${parsed.languages.join(", ")}`;
    skillsTab.appendChild(langP);
  }

  renderBulletTab("tab-experience", parsed.experience_bullets, "No Experience section detected.");
  renderBulletTab("tab-projects", parsed.projects_bullets, "No Projects section detected.");

  const eduTab = document.getElementById("tab-education");
  eduTab.innerHTML = `<p>${parsed.education_text || "No Education section detected."}</p>`;

  // Reset JD match panel text if no JD provided
  if (!jdText.value.trim()) {
    document.getElementById("jdMatchContent").innerHTML =
      '<p class="muted">Paste a job description above and re-run analysis to see your match score.</p>';
  }
}

function renderBulletTab(tabId, bullets, emptyMessage) {
  const tab = document.getElementById(tabId);
  tab.innerHTML = "";
  if (bullets && bullets.length > 0) {
    bullets.forEach((b) => {
      const div = document.createElement("div");
      div.className = "bullet-item";
      div.textContent = `• ${b}`;
      tab.appendChild(div);
    });
  } else {
    tab.innerHTML = `<p class="muted">${emptyMessage}</p>`;
  }
}

function scoreToClass(score) {
  if (score >= 75) return "good";
  if (score >= 50) return "ok";
  return "bad";
}

function scoreToGradient(score) {
  if (score >= 75) return "linear-gradient(135deg, #34d399 0%, #059669 100%)";
  if (score >= 50) return "linear-gradient(135deg, #fbbf24 0%, #d97706 100%)";
  return "linear-gradient(135deg, #f87171 0%, #b91c1c 100%)";
}

// ---- Tabs switching ----
document.querySelectorAll(".tab-btn").forEach((btn) => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".tab-btn").forEach((b) => b.classList.remove("active"));
    document.querySelectorAll(".tab-panel").forEach((p) => p.classList.add("hidden"));
    btn.classList.add("active");
    document.getElementById(`tab-${btn.dataset.tab}`).classList.remove("hidden");
  });
});

// ---- JD Match ----
async function runJdMatch(jd) {
  try {
    const res = await fetch(`${API_BASE}/api/match`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ resume_skills: lastResumeSkills, jd_text: jd }),
    });
    if (!res.ok) return;
    const match = await res.json();
    lastJdMissingSkills = match.missing_skills || [];
    renderJdMatch(match);
  } catch (err) {
    // Non-fatal: if the JD match fails, the rest of the report still shows.
    console.error("JD match failed:", err);
  }
}

function renderJdMatch(match) {
  const container = document.getElementById("jdMatchContent");
  container.innerHTML = `
    <p><strong>Match Score:</strong> ${match.match_percent}%</p>
    <div class="progress-bar" style="margin-bottom:1rem;">
      <div class="progress-fill ${scoreToClass(match.match_percent)}" style="width:${match.match_percent}%"></div>
    </div>
    <div class="jd-match-cols">
      <div class="jd-col">
        <h4>✅ Matched Skills</h4>
        <p>${match.matched_skills.length ? match.matched_skills.join(", ") : "None"}</p>
      </div>
      <div class="jd-col">
        <h4>❌ Missing Skills</h4>
        <p>${match.missing_skills.length ? match.missing_skills.join(", ") : "None"}</p>
      </div>
    </div>
  `;
}

/* ===========================================================
   Feature navigation (Mock Interview / Career Roadmap / Rewrite)
=========================================================== */
const featureSections = {
  interview: document.getElementById("interviewSection"),
  roadmap: document.getElementById("roadmapSection"),
  rewrite: document.getElementById("rewriteSection"),
};

document.querySelectorAll(".feature-btn").forEach((btn) => {
  btn.addEventListener("click", () => {
    const feature = btn.dataset.feature;
    const isAlreadyOpen = !featureSections[feature].classList.contains("hidden");

    // Hide all feature sections, deactivate all buttons
    Object.values(featureSections).forEach((section) => section.classList.add("hidden"));
    document.querySelectorAll(".feature-btn").forEach((b) => b.classList.remove("active"));

    // Toggle: clicking an already-open section's button just closes it
    if (!isAlreadyOpen) {
      featureSections[feature].classList.remove("hidden");
      btn.classList.add("active");
      featureSections[feature].scrollIntoView({ behavior: "smooth", block: "start" });

      if (feature === "roadmap") {
        ensureRoleDropdownPopulated();
      }
    }
  });
});

function resetFeatureSections() {
  Object.values(featureSections).forEach((section) => section.classList.add("hidden"));
  document.querySelectorAll(".feature-btn").forEach((b) => b.classList.remove("active"));

  document.getElementById("interviewIntro").classList.remove("hidden");
  document.getElementById("interviewQuestions").classList.add("hidden");
  document.getElementById("interviewQuestions").innerHTML = "";
  document.getElementById("interviewSubmitWrap").classList.add("hidden");
  document.getElementById("interviewResults").classList.add("hidden");
  document.getElementById("interviewResults").innerHTML = "";
  interviewQuestions = [];

  document.getElementById("roadmapContent").innerHTML = "";
  document.getElementById("roleSelect").value = "";
  lastDetectedRole = "";

  document.getElementById("rewriteIntro").classList.remove("hidden");
  document.getElementById("rewriteContent").classList.add("hidden");
  document.getElementById("rewriteContent").innerHTML = "";
  document.getElementById("rewriteDownloadWrap").classList.add("hidden");
}

/* ===========================================================
   Mock Interview
=========================================================== */
const startInterviewBtn = document.getElementById("startInterviewBtn");
const submitInterviewBtn = document.getElementById("submitInterviewBtn");

startInterviewBtn.addEventListener("click", async () => {
  if (!lastParsed) return;
  startInterviewBtn.disabled = true;
  startInterviewBtn.textContent = "Loading questions...";

  try {
    const res = await fetch(`${API_BASE}/api/interview/start`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        skills: lastResumeSkills,
        role: lastDetectedRole,
        projects_bullets: lastParsed.projects_bullets || [],
        experience_bullets: lastParsed.experience_bullets || [],
      }),
    });
    const data = await res.json();
    interviewQuestions = data.questions || [];
    renderInterviewQuestions(interviewQuestions);

    document.getElementById("interviewIntro").classList.add("hidden");
    document.getElementById("interviewQuestions").classList.remove("hidden");
    document.getElementById("interviewSubmitWrap").classList.remove("hidden");
  } catch (err) {
    console.error("Failed to start interview:", err);
  } finally {
    startInterviewBtn.disabled = false;
    startInterviewBtn.textContent = "Start Mock Interview";
  }
});

function renderInterviewQuestions(questions) {
  const container = document.getElementById("interviewQuestions");
  container.innerHTML = "";
  questions.forEach((q, idx) => {
    const div = document.createElement("div");
    div.className = "interview-question";
    div.innerHTML = `
      <span class="q-category">${q.category}</span>
      <p class="q-text">${idx + 1}. ${q.question}</p>
      <textarea id="answer-${idx}" placeholder="Type your answer here..."></textarea>
    `;
    container.appendChild(div);
  });
}

submitInterviewBtn.addEventListener("click", async () => {
  if (!interviewQuestions.length) return;
  submitInterviewBtn.disabled = true;
  submitInterviewBtn.textContent = "Scoring...";

  const items = interviewQuestions.map((q, idx) => ({
    question: q.question,
    category: q.category,
    keywords: q.keywords || [],
    answer: document.getElementById(`answer-${idx}`).value.trim(),
  }));

  try {
    const res = await fetch(`${API_BASE}/api/interview/score`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ items }),
    });
    const data = await res.json();
    renderInterviewResults(data);
  } catch (err) {
    console.error("Failed to score interview:", err);
  } finally {
    submitInterviewBtn.disabled = false;
    submitInterviewBtn.textContent = "Submit Answers & Get Score";
  }
});

function renderInterviewResults(result) {
  const container = document.getElementById("interviewResults");
  container.classList.remove("hidden");

  let html = `
    <div class="interview-overall">
      <div class="score-circle" style="background:${scoreToGradient(result.overall_score)}">
        <span>${result.overall_score}</span><span class="score-max">/100</span>
      </div>
      <p>${result.summary}</p>
    </div>
  `;

  result.per_question.forEach((pq, idx) => {
    html += `
      <div class="interview-question">
        <span class="q-category">${pq.category}</span>
        <p class="q-text">${idx + 1}. ${pq.question}</p>
        <div class="progress-bar" style="margin-bottom:0.5rem;">
          <div class="progress-fill ${scoreToClass(pq.score)}" style="width:${pq.score}%"></div>
        </div>
        <div class="interview-feedback">
          <span class="q-score">${pq.score}/100</span> · ${pq.word_count} word(s)
          ${pq.issues && pq.issues.length ? "<ul>" + pq.issues.map((i) => `<li>${i}</li>`).join("") + "</ul>" : ""}
        </div>
      </div>
    `;
  });

  container.innerHTML = html;
}

/* ===========================================================
   Career Roadmap
=========================================================== */
let roleDropdownPopulated = false;

async function ensureRoleDropdownPopulated() {
  if (roleDropdownPopulated) return;
  try {
    const res = await fetch(`${API_BASE}/api/roles`);
    const data = await res.json();
    const select = document.getElementById("roleSelect");
    (data.roles || []).forEach((role) => {
      const opt = document.createElement("option");
      opt.value = role;
      opt.textContent = role;
      select.appendChild(opt);
    });
    roleDropdownPopulated = true;
  } catch (err) {
    console.error("Failed to load roles:", err);
  }
}

document.getElementById("generateRoadmapBtn").addEventListener("click", async () => {
  if (!lastParsed) return;
  const targetRole = document.getElementById("roleSelect").value || null;
  const container = document.getElementById("roadmapContent");
  container.innerHTML = '<p class="muted">Generating roadmap...</p>';

  try {
    const res = await fetch(`${API_BASE}/api/roadmap`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ skills: lastResumeSkills, target_role: targetRole }),
    });
    const data = await res.json();
    lastDetectedRole = data.role || "";
    renderRoadmap(data);
  } catch (err) {
    container.innerHTML = '<p class="error-text">Failed to generate roadmap. Please try again.</p>';
    console.error("Roadmap error:", err);
  }
});

function renderRoadmap(data) {
  const container = document.getElementById("roadmapContent");

  let html = `
    <div class="roadmap-summary">
      <div class="score-circle-wrap">
        <div class="score-circle" style="width:90px;height:90px;font-size:1.6rem;background:${scoreToGradient(data.readiness_percent)}">
          <span>${data.readiness_percent}</span><span class="score-max">%</span>
        </div>
        <span class="score-label">Readiness</span>
      </div>
      <div>
        <h3>${data.role}${data.auto_detected ? " <span class='muted' style='font-size:0.8rem;'>(auto-detected best match)</span>" : ""}</h3>
        <p class="muted">✅ Matched: ${data.matched_skills.length ? data.matched_skills.join(", ") : "None yet"}</p>
        <p class="muted">📌 Missing: ${data.missing_skills.length ? data.missing_skills.join(", ") : "None - you're fully covered!"}</p>
      </div>
    </div>
  `;

  if (data.roadmap.length === 0) {
    html += '<p class="success-msg">🎉 You already have all the key skills for this role!</p>';
  } else {
    data.roadmap.forEach((stage) => {
      html += `
        <div class="roadmap-stage">
          <h4>${stage.stage}</h4>
          <p class="stage-duration">Estimated time: ${stage.estimated_duration}</p>
          ${stage.skills.map((s) => `
            <div class="roadmap-skill-item">
              <span class="skill-name">${s.skill}</span>
              <span class="skill-note">${s.note}</span>
            </div>
          `).join("")}
        </div>
      `;
    });
  }

  container.innerHTML = html;
}

/* ===========================================================
   Resume Rewriter
=========================================================== */
let rewrittenResumeData = null;

document.getElementById("generateRewriteBtn").addEventListener("click", async () => {
  if (!lastParsed) return;
  const btn = document.getElementById("generateRewriteBtn");
  btn.disabled = true;
  btn.textContent = "Rewriting...";

  try {
    const missingKeywords = Array.from(
      new Set([...lastAtsMissingKeywords, ...lastJdMissingSkills])
    );

    const res = await fetch(`${API_BASE}/api/resume/rewrite`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        parsed: lastParsed,
        detected_role: lastDetectedRole,
        missing_keywords: missingKeywords,
      }),
    });
    const data = await res.json();
    renderRewrite(data);
    document.getElementById("rewriteIntro").classList.add("hidden");
    document.getElementById("rewriteContent").classList.remove("hidden");
    document.getElementById("rewriteDownloadWrap").classList.remove("hidden");
  } catch (err) {
    console.error("Failed to rewrite resume:", err);
  } finally {
    btn.disabled = false;
    btn.textContent = "Generate Improved Resume";
  }
});

function renderRewrite(data) {
  const container = document.getElementById("rewriteContent");

  const bulletEditorHtml = (idPrefix, bullets) =>
    bullets.map((b, i) => `
      <div class="rewrite-bullet-row">
        <span class="bullet-dot">•</span>
        <textarea id="${idPrefix}-${i}">${escapeHtml(b)}</textarea>
      </div>
    `).join("") || '<p class="muted">None detected.</p>';

  container.innerHTML = `
    <div class="rewrite-block">
      <h4>Professional Summary</h4>
      <textarea id="rewrite-summary" rows="4">${escapeHtml(data.summary_text)}</textarea>
    </div>
    <div class="rewrite-block">
      <h4>Skills</h4>
      <p class="muted" style="margin:0 0 0.4rem;font-size:0.85rem;">
        Comma-separated. AI-flagged missing keywords have already been added.
      </p>
      <textarea id="rewrite-skills" rows="2">${escapeHtml((data.skills || []).join(", "))}</textarea>
    </div>
    <div class="rewrite-block">
      <h4>Experience</h4>
      <div id="rewrite-experience-wrap">${bulletEditorHtml("rewrite-exp", data.experience_bullets)}</div>
    </div>
    <div class="rewrite-block">
      <h4>Projects</h4>
      <div id="rewrite-projects-wrap">${bulletEditorHtml("rewrite-proj", data.projects_bullets)}</div>
    </div>
    <div class="rewrite-block">
      <h4>Achievements</h4>
      <div id="rewrite-achievements-wrap">${bulletEditorHtml("rewrite-ach", data.achievements_bullets)}</div>
    </div>
  `;

  rewrittenResumeData = data;
}

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str || "";
  return div.innerHTML;
}

function collectEditedBullets(idPrefix, count) {
  const result = [];
  for (let i = 0; i < count; i++) {
    const el = document.getElementById(`${idPrefix}-${i}`);
    if (el && el.value.trim()) result.push(el.value.trim());
  }
  return result;
}

document.getElementById("downloadResumeBtn").addEventListener("click", async () => {
  if (!rewrittenResumeData || !lastParsed) return;
  const btn = document.getElementById("downloadResumeBtn");
  btn.disabled = true;
  btn.textContent = "Preparing download...";

  const editedSummary = document.getElementById("rewrite-summary").value.trim();
  const editedSkills = document.getElementById("rewrite-skills").value
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean);
  const editedExperience = collectEditedBullets("rewrite-exp", rewrittenResumeData.experience_bullets.length);
  const editedProjects = collectEditedBullets("rewrite-proj", rewrittenResumeData.projects_bullets.length);
  const editedAchievements = collectEditedBullets("rewrite-ach", rewrittenResumeData.achievements_bullets.length);

  const resumeData = {
    name: lastParsed.name,
    email: lastParsed.email,
    phone: lastParsed.phone,
    linkedin: lastParsed.linkedin,
    github: lastParsed.github,
    portfolio: lastParsed.portfolio,
    skills: editedSkills.length ? editedSkills : lastParsed.skills,
    languages: lastParsed.languages,
    education_text: lastParsed.education_text,
    certifications_text: lastParsed.certifications_text,
    summary_text: editedSummary,
    experience_bullets: editedExperience,
    projects_bullets: editedProjects,
    achievements_bullets: editedAchievements,
  };

  try {
    const res = await fetch(`${API_BASE}/api/resume/download`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ resume_data: resumeData }),
    });
    if (!res.ok) throw new Error("Failed to generate document");

    const blob = await res.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "Updated_Resume.docx";
    document.body.appendChild(a);
    a.click();
    a.remove();
    window.URL.revokeObjectURL(url);
  } catch (err) {
    console.error("Download failed:", err);
    alert("Sorry, something went wrong generating the document. Please try again.");
  } finally {
    btn.disabled = false;
    btn.textContent = "⬇️ Download Updated Resume (.docx)";
  }
});
