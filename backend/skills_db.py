"""
skills_db.py
-------------
A static knowledge base of skills, action verbs, and section keywords
used by the parser and the ATS scoring engine.

This is intentionally a plain Python data file (no external API calls)
so the whole app works completely offline / without an OpenAI key.
You can keep adding to these lists over time.
"""

# Master list of tech skills the parser will look for in the resume text.
# Keep these lowercase - matching is done in a case-insensitive way.
SKILLS_DB = [
    # Programming languages
    "python", "java", "c++", "c", "c#", "javascript", "typescript", "go", "rust",
    "kotlin", "swift", "php", "ruby", "r", "scala", "matlab", "sql", "html", "css",

    # Web / frontend
    "react", "react.js", "next.js", "vue", "vue.js", "angular", "redux", "tailwind",
    "tailwindcss", "bootstrap", "jquery", "webpack", "vite", "sass",

    # Backend
    "node.js", "express", "express.js", "django", "flask", "fastapi", "spring",
    "spring boot", "asp.net", ".net", "graphql", "rest api", "restful api",

    # Databases
    "mysql", "postgresql", "postgres", "mongodb", "sqlite", "redis", "firebase",
    "oracle", "cassandra", "dynamodb", "elasticsearch",

    # ML / AI / Data
    "machine learning", "deep learning", "data science", "nlp",
    "natural language processing", "computer vision", "scikit-learn", "sklearn",
    "tensorflow", "pytorch", "keras", "pandas", "numpy", "matplotlib", "seaborn",
    "opencv", "huggingface", "transformers", "llm", "generative ai", "data analysis",
    "data visualization", "statistics", "regression", "classification", "clustering",
    "neural network", "cnn", "rnn", "lstm", "xgboost", "data mining",

    # Cloud / DevOps
    "aws", "azure", "gcp", "google cloud", "docker", "kubernetes", "jenkins",
    "ci/cd", "terraform", "ansible", "linux", "git", "github", "gitlab", "bitbucket",
    "nginx", "apache",

    # Mobile
    "android", "ios", "flutter", "react native", "swiftui",

    # Tools / Misc
    "jira", "agile", "scrum", "figma", "postman", "vs code", "excel", "power bi",
    "tableau", "selenium", "junit", "pytest", "unit testing", "api testing",

    # Soft / domain skills (lower weight but still recognized)
    "leadership", "communication", "teamwork", "problem solving", "project management",
    "time management", "critical thinking",
]

# Strong action verbs ATS systems / recruiters like to see at the start of bullet points.
STRONG_ACTION_VERBS = [
    "achieved", "improved", "trained", "led", "managed", "created", "resolved",
    "negotiated", "increased", "decreased", "reduced", "researched", "developed",
    "built", "designed", "implemented", "launched", "automated", "optimized",
    "engineered", "architected", "deployed", "spearheaded", "streamlined",
    "delivered", "executed", "established", "directed", "coordinated", "analyzed",
    "evaluated", "generated", "boosted", "accelerated", "transformed", "pioneered",
    "mentored", "orchestrated", "scaled", "migrated", "refactored", "integrated",
]

# Weak / filler phrases that hurt resumes - used to flag weak bullet points.
WEAK_PHRASES = [
    "responsible for", "worked on", "helped with", "involved in", "tasked with",
    "duties included", "in charge of", "assisted with", "participated in",
    "was part of", "dealt with", "handled",
]

# Section header keywords used to detect which sections exist in the resume.
SECTION_HEADERS = {
    "summary": ["summary", "objective", "profile", "about me"],
    "experience": ["experience", "work experience", "employment", "professional experience",
                   "internship", "internships"],
    "education": ["education", "academic", "qualification"],
    "projects": ["projects", "academic projects", "personal projects"],
    "skills": ["skills", "technical skills", "competencies", "core competencies"],
    "certifications": ["certification", "certifications", "licenses"],
    "achievements": ["achievements", "awards", "honors", "accomplishments"],
    "languages": ["languages"],
}


# ---------------------------------------------------------------------------
# Career Roadmap data
# ---------------------------------------------------------------------------
# A small set of common target roles, each mapped to the skills that role
# typically expects. Used to figure out the closest-matching role for a
# resume, and which skills are missing for that role.
ROLE_SKILLS_MAP = {
    "Frontend Developer": [
        "html", "css", "javascript", "typescript", "react", "react.js", "redux",
        "next.js", "tailwind", "tailwindcss", "bootstrap", "git", "rest api", "figma",
    ],
    "Backend Developer": [
        "python", "java", "node.js", "express", "express.js", "django", "flask",
        "fastapi", "spring", "spring boot", "sql", "mysql", "postgresql", "mongodb",
        "rest api", "git", "docker",
    ],
    "Full Stack Developer": [
        "html", "css", "javascript", "react", "node.js", "express", "mongodb", "sql",
        "rest api", "git", "docker", "django", "flask",
    ],
    "Data Scientist": [
        "python", "pandas", "numpy", "machine learning", "statistics", "sql",
        "scikit-learn", "matplotlib", "data visualization", "data analysis",
        "regression", "classification",
    ],
    "Machine Learning Engineer": [
        "python", "machine learning", "deep learning", "tensorflow", "pytorch",
        "scikit-learn", "numpy", "pandas", "sql", "docker", "neural network",
    ],
    "Data Analyst": [
        "sql", "excel", "power bi", "tableau", "python", "pandas", "data analysis",
        "data visualization", "statistics",
    ],
    "DevOps Engineer": [
        "docker", "kubernetes", "aws", "azure", "gcp", "ci/cd", "linux", "terraform",
        "ansible", "git", "jenkins",
    ],
    "Mobile App Developer": [
        "android", "ios", "flutter", "react native", "java", "kotlin", "swift",
        "swiftui", "sql",
    ],
}

# Short, beginner-friendly learning notes for common skills. Used by the
# roadmap generator. Falls back to a generic templated note for any skill
# that isn't listed here.
SKILL_LEARNING_NOTES = {
    "python": "Practice core syntax, then build 2-3 small scripts/automation projects.",
    "java": "Cover OOP basics, collections, then build a small console/REST project.",
    "javascript": "Learn ES6+ fundamentals (functions, async/await, arrays) via small projects.",
    "typescript": "Add static types to an existing JS project to learn interfaces & generics.",
    "html": "Practice semantic tags and accessible markup by rebuilding a real webpage.",
    "css": "Learn Flexbox & Grid, then rebuild a UI you like pixel-by-pixel.",
    "react": "Build 2-3 small apps (todo list, weather app) using hooks & component state.",
    "react.js": "Build 2-3 small apps (todo list, weather app) using hooks & component state.",
    "node.js": "Build a small REST API with routing, middleware, and error handling.",
    "express": "Build a CRUD API with Express + a database to practice routing/middleware.",
    "fastapi": "Build a CRUD API with FastAPI + Pydantic models and automatic docs.",
    "django": "Build a small app using Django's ORM, views, and templates end to end.",
    "flask": "Build a small Flask app with routes, templates, and a database.",
    "sql": "Practice SELECT/JOIN/GROUP BY on a sample database (e.g. via SQLZoo/LeetCode SQL).",
    "mysql": "Set up a local MySQL DB and practice schema design + queries.",
    "postgresql": "Set up a local Postgres DB and practice schema design + queries.",
    "mongodb": "Learn document modeling and practice CRUD with the Mongo shell/driver.",
    "git": "Practice branching, merging, and resolving conflicts on a personal repo.",
    "docker": "Containerize one of your own projects and write a Dockerfile from scratch.",
    "kubernetes": "Learn pods/deployments/services by deploying a sample app to a local cluster (minikube).",
    "aws": "Get hands-on with EC2, S3, and IAM via the AWS Free Tier.",
    "azure": "Get hands-on with Azure App Service and Storage via the free tier.",
    "machine learning": "Cover supervised/unsupervised learning basics, then build 2-3 model projects.",
    "deep learning": "Learn neural network fundamentals, then build a small CNN/RNN project.",
    "tensorflow": "Follow the official TensorFlow tutorials and rebuild one model from scratch.",
    "pytorch": "Follow the official PyTorch tutorials and rebuild one model from scratch.",
    "scikit-learn": "Practice the fit/predict workflow on a few classic datasets.",
    "pandas": "Practice data cleaning, grouping, and merging on a real messy dataset.",
    "numpy": "Practice array operations, broadcasting, and vectorized math.",
    "data visualization": "Recreate 3-4 charts from real data using matplotlib/seaborn or Power BI.",
    "statistics": "Review probability, distributions, and hypothesis testing fundamentals.",
    "power bi": "Build a small interactive dashboard from a public dataset.",
    "tableau": "Build a small interactive dashboard from a public dataset.",
    "excel": "Practice pivot tables, lookups, and basic formulas on real data.",
    "rest api": "Build and consume a REST API end to end (CRUD + auth).",
    "react native": "Build a small cross-platform app using navigation and device APIs.",
    "flutter": "Build a small cross-platform app using widgets and state management.",
    "android": "Build a small app using Android Studio and Kotlin/Java.",
    "ios": "Build a small app using Xcode and Swift/SwiftUI.",
    "ci/cd": "Set up a simple pipeline (GitHub Actions) that tests & deploys a personal project.",
    "linux": "Practice the command line: file ops, permissions, processes, and shell scripting.",
    "terraform": "Provision a small piece of cloud infra (e.g. an S3 bucket) using Terraform.",
}


# ---------------------------------------------------------------------------
# Mock Interview question bank
# ---------------------------------------------------------------------------
# Each entry: question text + a list of keywords we'd expect in a solid
# answer (used for rule-based scoring - no AI grading needed).
GENERAL_INTERVIEW_QUESTIONS = [
    {
        "question": "Tell me about yourself and your career goals.",
        "category": "General",
        "keywords": ["experience", "skills", "project", "goal", "learn", "role", "interest"],
    },
    {
        "question": "What are your biggest strengths and weaknesses?",
        "category": "General",
        "keywords": ["strength", "weakness", "improve", "example", "learn"],
    },
    {
        "question": "Describe a challenging problem you solved recently and how you solved it.",
        "category": "Behavioral",
        "keywords": ["problem", "challenge", "solution", "approach", "result", "learned"],
    },
    {
        "question": "How do you handle tight deadlines or conflicting priorities?",
        "category": "Behavioral",
        "keywords": ["priorit", "deadline", "plan", "communicat", "time", "manage"],
    },
    {
        "question": "Why should we hire you for this role?",
        "category": "General",
        "keywords": ["skill", "experience", "fit", "value", "contribute", "team"],
    },
]

SKILL_INTERVIEW_QUESTIONS = {
    "python": [
        {"question": "What's the difference between a list and a tuple in Python?",
         "keywords": ["mutable", "immutable", "list", "tuple"]},
        {"question": "How does Python's garbage collection / memory management work, at a high level?",
         "keywords": ["reference", "count", "garbage", "memory"]},
    ],
    "java": [
        {"question": "What is the difference between an interface and an abstract class in Java?",
         "keywords": ["interface", "abstract", "implement", "extend", "method"]},
    ],
    "sql": [
        {"question": "What's the difference between an INNER JOIN and a LEFT JOIN?",
         "keywords": ["inner", "left", "join", "match", "null"]},
        {"question": "How would you find duplicate rows in a table using SQL?",
         "keywords": ["group by", "count", "having", "distinct"]},
    ],
    "react": [
        {"question": "What's the difference between state and props in React?",
         "keywords": ["state", "props", "component", "render", "immutable"]},
    ],
    "react.js": [
        {"question": "What's the difference between state and props in React?",
         "keywords": ["state", "props", "component", "render", "immutable"]},
    ],
    "machine learning": [
        {"question": "What's the difference between supervised and unsupervised learning?",
         "keywords": ["label", "supervised", "unsupervised", "data", "cluster"]},
        {"question": "How would you handle an overfitting model?",
         "keywords": ["overfit", "regulariz", "data", "cross-validation", "simplify"]},
    ],
    "data analysis": [
        {"question": "How would you approach cleaning a messy real-world dataset?",
         "keywords": ["missing", "duplicate", "outlier", "clean", "validate"]},
    ],
    "django": [
        {"question": "What's the role of Django's ORM, and why is it useful?",
         "keywords": ["orm", "database", "model", "query", "migration"]},
    ],
    "docker": [
        {"question": "What's the difference between a Docker image and a Docker container?",
         "keywords": ["image", "container", "instance", "build", "run"]},
    ],
    "git": [
        {"question": "How do you resolve a merge conflict in Git?",
         "keywords": ["conflict", "merge", "branch", "resolve", "commit"]},
    ],
}
