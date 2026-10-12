# Adaptive Interview Intelligence

[![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110%2B-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-19-61DAFB?style=flat-square&logo=react&logoColor=black)](https://react.dev)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.x-3178C6?style=flat-square&logo=typescript&logoColor=white)](https://www.typescriptlang.org)
[![Three.js](https://img.shields.io/badge/Three.js-3D-black?style=flat-square&logo=three.js&logoColor=white)](https://threejs.org)
[![License](https://img.shields.io/badge/License-MIT-blue?style=flat-square)](LICENSE)

An evidence-driven, voice-first technical interview intelligence platform that transforms hiring from static question checklists into an adaptive, verifiable, and explainable evaluation system.

---

## 🌌 Overview

**Adaptive Interview Intelligence** is designed to address the key shortcomings of conventional technical interviews: memorized rote questions, subjective interviewer grading, and lack of verifiable audit trails. 

In strict alignment with **Responsible AI and Human-in-the-Loop** principles, the platform **never** makes autonomous hiring or rejection decisions. Instead, it:
1. **Parses & Audits Resumes**: Extracts candidate claims, skills, and work history while detecting timeline anomalies and keyword-stuffing.
2. **Evaluates Job Eligibility & Skill Gaps**: Maps candidate competencies against role requirements across a 4-tier evidence model (*Demonstrated*, *Assessed-Not-Demonstrated*, *Claimed-Unvalidated*, *Not-Assessed*).
3. **Orchestrates Adaptive Interviews**: Dynamically selects and generates technical questions across **Python Backend** and **Full-Stack** tracks that probe identified skill gaps and scale difficulty based on live performance.
4. **Applies Deterministic Rubric Evaluation**: Grades candidate answers using multi-criterion rubrics normalized to 100%, extracting verbatim transcript quotes with decoupled confidence scores.
5. **Generates Multi-Page PDF Dossiers**: Produces an executive assessment report featuring score breakdowns, competency matrices, question-by-question analysis, and personalized learning plans.

---

## 🏗️ Architecture & Technology Stack

```
                              ┌──────────────────────────────────────────────┐
                              │            Web Presentation Tier             │
                              ├──────────────────────┬───────────────────────┤
                              │ Built-in FastWeb UI  │ Standalone React SPA  │
                              │ (HTML/CSS/Three.js)  │ (React 19/TS/Tailwind)│
                              └──────────┬───────────┴───────────┬───────────┘
                                         │                       │
                                         ▼                       ▼
┌────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                       FastAPI Backend Core (:8000)                                     │
├─────────────────────────┬──────────────────────────┬─────────────────────────┬─────────────────────────┤
│    Session Manager      │  Domain Router & Tracks  │  Speech Bridge Service  │  ReportLab PDF Engine   │
│  - Session Lifecycle    │  - Python Interviewer    │  - SpeechRecognition    │  - Multi-Page Canvas    │
│  - State Machine        │  - Full-Stack Track      │  - pyttsx3 TTS Engine   │  - Scoring Breakdown    │
├─────────────────────────┼──────────────────────────┼─────────────────────────┼─────────────────────────┤
│  Resume Analyzer Suite  │ Dynamic Question Engine  │  Rubric Evaluation Core │   Integrity Telemetry   │
│  - PDF/DOCX/TXT Parser  │  - Recency Cache Filter  │  - Deterministic Math   │  - Audio Variance       │
│  - ATS & Skills Matcher │  - Jaccard De-duplication│  - Verbatim Extraction  │  - Attention Tracking   │
└─────────────────────────┴────────────┬─────────────┴─────────────────────────┴─────────────────────────┘
                                       │
                        ┌──────────────┴──────────────┐
                        ▼                             ▼
         ┌────────────────────────────┐ ┌───────────────────────────┐
         │     Local LLM (Ollama)     │ │   Google Gemini API       │
         │       qwen2.5:7b           │ │ (Optional Hosted Fallback)│
         └────────────────────────────┘ └───────────────────────────┘
```

### Backend Components
- **Framework**: FastAPI with AsyncIO, Pydantic v2 schemas, and CORS middleware.
- **LLM Engine**: Local Ollama (`qwen2.5:7b`) with health-checking, JSON enforcement, and robust offline question-bank fallbacks.
- **Resume Analysis**: Multi-agent pipeline with structure extractors (`PyMuPDF`, `python-docx`), ATS scoring, and anomaly detection.
- **Question Generation**: Two-tier architecture combining an extensive curated question bank with dynamic LLM generation, guarded by token/bigram Jaccard deduplication.
- **Evaluation Engine**: Criteria-weighted scoring with code execution validation and conceptual keyword checks.
- **Audio Pipeline**: Server-side Speech Bridge (`SpeechRecognition`, `pyttsx3`) and browser-side Web Speech API support.
- **Reporting**: ReportLab 5.0 with custom two-pass `NumberedCanvas` for running headers, footers, and page tallies.

### Frontend Options
1. **Built-in Web Application (`backend/static/`)**: Served directly by FastAPI at `/`. Includes Three.js 3D orbital scene, harmonic sine wave canvas, audio visualizers, and resume upload flow.
2. **Standalone React Application (`frontend/`)**: React 19, TypeScript, Vite, Tailwind CSS, Framer Motion, and Vitest test suite. Supports dual modes: Direct FastAPI integration or client-side Agent demo mode.

---

## ⚙️ Prerequisites

- **Python**: 3.10 or higher (Python 3.11 recommended).
- **Node.js**: 18.x or higher (optional, for running the standalone Vite frontend).
- **Ollama**: (Recommended for local LLM inference) Download from [ollama.com](https://ollama.com).
- **Audio Hardware**: Microphone and speakers/headphones for voice interview features.

---

## 🚀 Installation & Setup

### 1. Clone the Repository
```bash
git clone https://github.com/Ajayguptha-tech/Adaptive-interview-agent.git
cd Adaptive-interview-agent
```

### 2. Configure Python Virtual Environment
```bash
# Create virtual environment
python -m venv .venv

# Activate environment (Windows PowerShell)
.\.venv\Scripts\Activate.ps1
# Or Windows CMD:
# .\.venv\Scripts\activate.bat
# Or Linux/macOS:
# source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Environment Configuration
Copy the configuration template:
```bash
cp .env.example .env
```
Default parameters in `.env`:
```env
HOST=127.0.0.1
PORT=8000
OLLAMA_BASE_URL=http://127.0.0.1:11434
OLLAMA_MODEL=qwen2.5:7b
GEMINI_API_KEY=
DATABASE_PATH=resumeiq.db
```

### 4. Setup Ollama (Recommended)
Start Ollama and pull the default model:
```bash
ollama pull qwen2.5:7b
ollama run qwen2.5:7b
```
> **Note**: If Ollama is not running, the application automatically falls back to its built-in curated question bank of over 100+ vetted technical interview questions.

---

## 🖥️ Running the Application

### Start the FastAPI Server
```bash
uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```

Once running:
- **Interactive Web UI**: [http://127.0.0.1:8000/](http://127.0.0.1:8000/)
- **Interactive Swagger API Docs**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **ReDoc API Documentation**: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)
- **API Health Check**: [http://127.0.0.1:8000/api/health](http://127.0.0.1:8000/api/health)

### (Optional) Start the Standalone React Frontend
If you wish to use the standalone React application:
```bash
cd frontend
npm install
npm run dev
```
Open [http://localhost:5173/](http://localhost:5173/) in your browser. Configure `VITE_API_BASE_URL=http://127.0.0.1:8000` in `frontend/.env` to link to the backend.

---

## 🧪 Running Automated Tests

### Python Backend Test Suite
The backend includes 18 comprehensive test modules covering unit, integration, and end-to-end workflows:
```bash
python -m pytest tests -v
```

Test coverage includes:
- `tests/test_adaptive_selection.py`: Difficulty scaling and skill gap routing logic.
- `tests/test_api_endpoints.py`: FastAPI route contracts, session management, error handling.
- `tests/test_code_evaluator.py`: Isolated code execution and syntax evaluation.
- `tests/test_dynamic_questions.py`: Ollama prompting, JSON parsing, recency cache filtering.
- `tests/test_evaluation_engine_mocked.py`: Rubric criterion scoring and percentage normalization.
- `tests/test_fullstack_interviewer.py`: Multi-stack domain routing (HTML, CSS, React, Node, SQL).
- `tests/test_resume_integration.py`: Resume text extraction and ATS skill matching.
- `tests/test_role_intelligence_pdf.py`: Multi-page PDF generation and schema validation.
- `tests/test_rubric_validation.py`: Rubric structure and criterion verification.
- `tests/test_speech_bridge.py`: Audio synthesis, STT transcription mock flows, and timeout handling.

> **Windows 11 Security Note**: On Windows 11 systems with **Smart App Control (SAC)** enabled in strict mode, importing unsigned native binary extensions (`.pyd`) from user folders may be intercepted. Ensure execution permissions or virtual environment paths are appropriately allowed by your security policy.

### Frontend Vitest Suite
```bash
cd frontend
npm test
```
Runs 8 focused component and agent tests validating agent contracts, rubric citation extraction, timer countdown, and pause/resume logic.

---

## 📖 End-to-End Workflow Guide

### 1. Resume Ingestion & Pre-Screening
1. Navigate to the web application at `http://127.0.0.1:8000/`.
2. Upload a candidate resume (`.pdf`, `.docx`, or `.txt`) or use the built-in synthetic candidate (`candidate_resume.txt`).
3. Select the target track (**Python Backend Engineer** or **Full-Stack Developer**).
4. Review extracted candidate profile, ATS compatibility score, identified strengths, and pre-interview skill gaps.

### 2. Adaptive Interview Execution
1. Configure session settings (number of questions, difficulty level, speech/voice mode).
2. Begin the interview:
   - The agent reads questions aloud via Text-to-Speech (TTS).
   - Candidate responds via microphone (Speech-to-Text) or code/text input.
3. The adaptive engine dynamically adjusts questions:
   - High scores (>75%) escalate difficulty from *Intermediate* to *Advanced*.
   - Identified gaps trigger targeted conceptual or implementation follow-ups.
   - Cross-session recency caches prevent repeated questions.

### 3. Fair Rubric Evaluation & Telemetry
1. Every answer is evaluated against deterministic rubric criteria:
   - Specific criteria weights (e.g., Syntax, Complexity, Error Handling).
   - Verbatim quote citations extracted from transcripts.
   - Non-accusatory integrity telemetry logged (audio level fluctuations, focus switches).

### 4. Recruiter Dossier & PDF Export
1. Upon completing the interview, view the comprehensive performance breakdown.
2. Click **Download PDF Report** to generate an enterprise-grade PDF report containing:
   - Executive scorecards with normalized percentages.
   - 4-category competency matrix (*Demonstrated*, *Assessed-Not-Demonstrated*, *Claimed-Unvalidated*, *Not-Assessed*).
   - Question-by-question breakdown with ideal model answers and feedback.
   - Prioritized learning paths for candidate development.

---

## 📁 Repository Structure

```
Adaptive-Interview-Intelligence/
├── backend/
│   ├── fullstack/               # Full-Stack track questions & adaptive engine
│   ├── interviewers/            # Agent registry & domain interviewers
│   ├── resume_analyzer/         # Multi-agent resume parser & ATS scoring
│   ├── static/                  # Built-in web app (HTML, CSS, JS, Three.js)
│   ├── adaptive_engine.py       # Difficulty progression & skill gap router
│   ├── code_evaluator.py        # Sandboxed code evaluation engine
│   ├── domain_router.py         # Multi-track routing manager
│   ├── evaluator.py             # Rubric-based deterministic scoring
│   ├── interview_plan.py        # Resume-informed interview agenda generator
│   ├── llm_client.py            # Ollama client with fallback handling
│   ├── main.py                  # FastAPI application entry point
│   ├── models.py                # Pydantic data schemas
│   ├── pdf_generator.py         # ReportLab multi-page PDF generator
│   ├── question_bank.py         # Curated Python question bank
│   ├── question_generator.py    # Dynamic question generator & cache
│   ├── session_manager.py       # State machine & in-memory session store
│   └── speech_bridge.py         # STT & TTS hardware integration
├── frontend/                    # Standalone React 19 + TypeScript SPA
│   ├── src/                     # React components, agents, hooks, services
│   ├── package.json             # NPM dependencies & scripts
│   └── vite.config.ts           # Vite build configuration
├── tests/                       # Automated pytest test suite (18 test files)
├── candidate_resume.txt         # Synthetic sample resume for quick testing
├── requirements.txt             # Python dependencies
├── .env.example                 # Environment configuration template
├── .gitignore                   # Git exclusion rules
└── README.md                    # Platform documentation
```

---

## 🔒 Security & Privacy

- **No Secret Hardcoding**: All keys and endpoints are configured via environment variables.
- **Privacy-First**: No candidate personal identifiable information (PII) is stored externally. All resumes and sessions are processed locally in memory.
- **Explainable Decisions**: In compliance with ethical AI standards, all evaluations include rationale, specific criteria marks, and transcript citations.

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
