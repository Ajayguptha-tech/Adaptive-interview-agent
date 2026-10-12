# Adaptive Interview Intelligence Platform

> **Google Student Club Welcome Hackathon 2026**  
> **Problem Statement 3**: Adaptive Interview Intelligence (Full-Stack Agent Architecture & 3D Interactive Implementation)

---

## 🌌 Overview

**Adaptive Interview Intelligence** is an evidence-driven interview intelligence web platform designed to transform technical hiring from static scripts and subjective impressions into an adaptive, verifiable, and explainable evaluation model.

In strict alignment with **Responsible AI & Human-in-the-Loop** principles, Adaptive Interview Intelligence **never** makes autonomous hiring or rejection decisions. Instead, it:
1. Plans calibrated interview rubrics from candidate resume claims and job specifications.
2. Dynamically routes questions to explore skill gaps and test competency boundaries.
3. Transcribes spoken answers and extracts verbatim quotes with decoupled confidence scores.
4. Records neutral, non-accusatory sensory telemetry for recruiter context review.
5. Synthesizes an evidence-based recruiter dossier with verified strengths, residual gaps, and suggested follow-up questions.

---

## ✨ 3D Interactive Experience & Visual Architecture

Adaptive Interview Intelligence features a custom, high-performance **Three.js** 3D interactive hero scene alongside tactile Framer Motion card tilt physics:

1. **Futuristic 3D Hero Scene (`SkillOrbitHeroScene.tsx`)**:
   - **Glowing Cyan Core**: Pulsing emissive core sphere (`#00f2fe`) with inner point lighting.
   - **Wireframe Cube & Chip**: Dual concentric geometric frames with corner micro-processors rotating on dual axes.
   - **Tilted Elliptical Rings**: Independent elliptical particle streams in electric cyan (`#00f2fe`) and magenta (`#ec4899`) orbiting the central core.
   - **Five Connected Agent Nodes**: Five orbital nodes representing the 5 Adaptive Interview Intelligence agents (Planner, Interviewer, Evaluator, Integrity, Decision) connected by pulsating constellation line segments.
   - **Camera Parallax**: Smooth, damped camera response tracking mouse cursor and touch inputs.
   - **Luminous Bloom Flare Transition**: Smooth intro sequence with camera push-in and a luminous bloom flare that softly transitions into the dark neon landing interface.
   - **Visible Skip Intro Control**: Instant bypass control with gentle fade transitions.
2. **Miniature Glass-Like Headline Orb (`MiniGlassOrb.tsx`)**:
   - Translucent glass sphere with physical material refraction, internal cyan glow, and rotation beside the landing headline.
3. **Animated Harmonic Sine-Wave Ribbon (`SineWaveRibbon.tsx`)**:
   - Dual undulating harmonic canvas ribbons running behind the workflow and module showcase cards.
4. **Reliability & Accessibility**:
   - **WebGL Capability Detection** (`detectWebGLSupport`): Automatically checks WebGL/WebGL2 support and hardware tier.
   - **CSS Hologram Fallback**: If WebGL is unavailable or disabled, gracefully switches to a lightweight CSS hologram fallback with orbiting SVG rings.
   - **Reduced Motion Support**: Honors `prefers-reduced-motion` across both 3D camera animations and 2D interface transitions.
   - **Resource Disposal**: Comprehensive cleanup of geometries, materials, textures, renderers, and event listeners on component unmount.

---

## 🤖 The 5 Adaptive Interview Intelligence AI Agents

| Agent | Module | Core Functionality |
| :--- | :--- | :--- |
| **1. Interview Planner Agent** | `src/agents/planner.ts` | Ingests candidate resume claims & JD requisition, extracts competencies, identifies pre-interview skill gaps, and formats weighted evaluation rubrics with 3-tier indicators. |
| **2. Adaptive Interviewer Agent** | `src/agents/interviewer.ts` | Analyzes previous answers and unassessed competencies; dynamically generates targeted follow-up inquiries on gaps or escalates difficulty (intermediate to advanced). |
| **3. Answer Evaluation Agent** | `src/agents/evaluator.ts` | Evaluates responses against rubrics; extracts verbatim transcript quotations; calculates score impact and decoupled confidence bounds; identifies missing information. |
| **4. Interview Integrity Agent** | `src/agents/integrity.ts` | Records objective, non-accusatory sensory telemetry (acoustic fluctuations, tab focus loss, extended cognitive pauses) for recruiter context review. |
| **5. Decision Intelligence Agent** | `src/agents/decision.ts` | Synthesizes an explainable candidate report with verified strengths, unvalidated claims, critical gaps, and suggested follow-up questions without automated hiring/rejection decisions. |

---

## 🎙️ Speech, Audio & Media Pipeline

- **Text-to-Speech (TTS) Service (`src/services/tts.ts`)**:
  - Accessible question playback using browser SpeechSynthesis with natural voice matching, pause, resume, cancel, and speaking state callbacks.
  - *User-initiated only: never plays audio automatically without user action.*
- **Speech-to-Text (STT) Service (`src/services/stt.ts`)**:
  - Real-time streaming speech recognition via Web Speech API (`webkitSpeechRecognition` / `SpeechRecognition`), continuously outputting interim and final transcripts.
- **Real-Time Microphone Hook (`src/hooks/useMicRecorder.ts`)**:
  - Explicit browser microphone capture via `navigator.mediaDevices.getUserMedia`.
  - Web Audio API `AudioContext` with `AnalyserNode` generating real 12-band frequency data and volume levels for dynamic live audio visualizer waveforms (replaces static dummy bars).
  - Handles permission denials, unsupported browsers, and device errors gracefully.

---

## 🔌 Dual Operation Modes: Demo Mode vs FastAPI Backend

Adaptive Interview Intelligence supports dual operational modes without misleading live-service labels:

1. **DEMO MODE (Client-Side AI Agent Pipeline)**:
   - When no backend URL is set or when toggled in the top navigation bar, the full 5-agent pipeline runs completely client-side in the browser.
   - Deterministic resume parsing, gap identification, rubric evaluation, adaptive question generation, and report synthesis allow complete end-to-end testing without external servers.
   - All simulated features are explicitly labelled `[DEMO MODE]`.
2. **FASTAPI BACKEND MODE**:
   - Set `VITE_API_BASE_URL` in `.env` (e.g. `http://localhost:8000`).
   - Requests are routed to FastAPI endpoints (`/api/v1/planner/generate-plan`, `/api/v1/interviewer/next-question`, `/api/v1/evaluator/evaluate-answer`, `/api/v1/integrity/events`, `/api/v1/reports/generate`).

---

## 🛠️ Windows Installation, Testing & Running Commands

Run the following commands in **Windows Command Prompt (CMD)** or **PowerShell**:

### 1. Install Dependencies
```cmd
npm install
```
*(If behind a corporate SSL inspection proxy, use: `npm install --strict-ssl=false`)*

### 2. Run TypeScript Type Checks (Lint)
```cmd
npm run lint
```

### 3. Run Automated Unit & Integration Tests
```cmd
npm run test
```
Runs 8 focused tests covering agent contracts, rubric citation extraction, adaptive routing, session timing countdown, and pause/resume logic using Vitest.

### 4. Build for Production
```cmd
npm run build
```

### 5. Start Development Server
```cmd
npm run dev
```
Open `http://localhost:5173` in your browser.

---

## 📁 Project Directory Structure

```
skillorbit-frontend-full/
├── src/
│   ├── agents/
│   │   ├── planner.ts          # Agent 1: Interview Planner Agent
│   │   ├── interviewer.ts      # Agent 2: Adaptive Interviewer Agent
│   │   ├── evaluator.ts        # Agent 3: Answer Evaluation Agent
│   │   ├── integrity.ts        # Agent 4: Interview Integrity Agent
│   │   └── decision.ts         # Agent 5: Decision Intelligence Agent
│   ├── components/
│   │   ├── 3d/
│   │   │   ├── SkillOrbitHeroScene.tsx # 3D Hero scene with core, rings, nodes
│   │   │   ├── MiniGlassOrb.tsx        # Glass-like core orb beside headline
│   │   │   └── SineWaveRibbon.tsx      # Undulating canvas sine-wave ribbon
│   │   ├── common/                     # Interactive cards, tilt physics, buttons
│   │   ├── dashboard/                  # Recruiter Workspace & dynamic KPIs
│   │   ├── evidence/                   # 4-quadrant skill gap matrix & citations
│   │   ├── integrity/                  # Chronological telemetry stream & triage
│   │   ├── landing/                    # Landing page with 3D hero & workflow
│   │   ├── layout/                     # Navbar with Demo toggle & Footer
│   │   ├── live/                       # Live Cockpit with real timer, mic, STT, TTS
│   │   ├── report/                     # Candidate Dossier with sign-off panel
│   │   └── setup/                      # Role specification & resume ingestion
│   ├── context/
│   │   └── InterviewContext.tsx        # Session state, real timer, 5-agent dispatch
│   ├── hooks/
│   │   └── useMicRecorder.ts           # Web Audio API mic recorder & analyser
│   ├── services/
│   │   ├── interviewService.ts         # API requests & data synchronization
│   │   ├── stt.ts                      # Web Speech API Speech-to-Text
│   │   └── tts.ts                      # SpeechSynthesis Text-to-Speech
│   ├── types/
│   │   └── index.ts                    # Full TypeScript contract definitions
│   └── utils/
│       └── webgl.ts                    # WebGL support & device profiling
├── __tests__/
│   ├── agents.test.ts                  # Agent contract & adaptive tests
│   └── timing.test.ts                  # Timer & pause/resume tests
├── .env.example                        # Environment variables template
├── package.json
└── vite.config.ts
```

---

## 🎨 UI Redesign (lime / charcoal / off-white)

What changed (frontend presentation only; agents, services, context, API client and tests are untouched):

- **Design tokens** (`tailwind.config.js`, `src/index.css`): the existing `slate`, `cyan`, `violet`, `emerald`, `amber` and `rose` Tailwind scales are re-pointed to a warm off-white / charcoal / lime palette and flipped, so every existing screen restyles without logic changes.
- **New landing page** (`src/components/landing/LandingPage.tsx`): nav, hero, features, five-agent section, how-it-works, about, final CTA and footer. Describes only features that exist. The earlier Three.js hero components remain in `src/components/3d/` but are no longer used by the landing page.
- **New app shell**: charcoal `Sidebar.tsx` (desktop), slim `Navbar.tsx` status bar with mobile navigation row, same seven `NavigationTab` routes.
- **Not verified in the redesign environment**: install, type-check, tests, build, browser rendering and the microphone/TTS flows could not be run there (no network access). Run the commands above and review each screen visually; some screens that used hardcoded dark-theme classes may need small contrast tweaks.
