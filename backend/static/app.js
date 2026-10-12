/**
 * Adaptive Interview Intelligence - Frontend Application
 * Resume-driven, voice-first, adaptive technical assessment orchestration.
 * Automatically adapts workspace based on question metadata.
 * No manual track or answer-type selectors exposed to candidate.
 */

const API_BASE = "";

// Application State
const state = {
  // Candidate & Onboarding
  selectedFile: null,
  targetRole: "",
  resumeId: null,
  resumeProfile: null,
  interviewPlan: null,
  routedTrack: "python",

  // Configuration (Selected on Screen 2)
  interviewMode: "mock", // "mock" (dynamic) or "predefined"
  questionCount: 5,
  difficultyMode: "adaptive",
  autoSpeakQuestion: true,
  debounceSeconds: 4,

  // Active Interview Session
  sessionId: null,
  currentQuestion: null,
  isSubmitting: false,

  // Audio Recording (STT)
  mediaRecorder: null,
  audioChunks: [],
  recordStartTime: null,
  recordTimerInterval: null,
  activeAudioElement: null,

  // Auto-Evaluation Countdown Management
  autoEvalInterval: null,
  autoEvalRemainingMs: 0,
  autoEvalTotalMs: 4000,
  isAutoEvalPaused: false,
  activeSubmitCallback: null,
  typingPauseTimeout: null,

  // Feedback Auto-Advance Countdown
  feedbackAdvanceInterval: null,
  feedbackAdvanceRemaining: 5,
  isFeedbackAdvancePaused: false,
};

// DOM Elements Registry
const elements = {
  // Status indicators
  ollamaStatus: document.getElementById("ollama-status"),
  voiceStatus: document.getElementById("voice-status"),

  // Stepper
  stepNavUpload: document.getElementById("step-nav-upload"),
  stepNavSettings: document.getElementById("step-nav-settings"),
  stepNavInterview: document.getElementById("step-nav-interview"),
  stepNavReport: document.getElementById("step-nav-report"),

  // Views
  uploadView: document.getElementById("upload-view"),
  settingsView: document.getElementById("settings-view"),
  interviewView: document.getElementById("interview-view"),
  reportView: document.getElementById("report-view"),

  // View 1: Resume Upload
  initialTargetRole: document.getElementById("initial-target-role"),
  initialDropZone: document.getElementById("initial-drop-zone"),
  initialResumeFile: document.getElementById("initial-resume-file"),
  fileSelectedBadge: document.getElementById("file-selected-badge"),
  selectedFileName: document.getElementById("selected-file-name"),
  selectedFileSize: document.getElementById("selected-file-size"),
  changeFileBtn: document.getElementById("change-file-btn"),
  uploadErrorBanner: document.getElementById("upload-error-banner"),
  uploadErrorText: document.getElementById("upload-error-text"),
  analyzeResumeBtn: document.getElementById("analyze-resume-btn"),
  analyzeSpinner: document.getElementById("analyze-spinner"),
  analysisLoadingState: document.getElementById("analysis-loading-state"),
  analysisStepTitle: document.getElementById("analysis-step-title"),
  analysisStepText: document.getElementById("analysis-step-text"),

  // View 2: Profile & Settings
  profileCandidateName: document.getElementById("profile-candidate-name"),
  profileTargetRole: document.getElementById("profile-target-role"),
  profileExpBadge: document.getElementById("profile-exp-badge"),
  profileIntegrityBadge: document.getElementById("profile-integrity-badge"),
  profileSkillsChips: document.getElementById("profile-skills-chips"),
  profileAgendaSummary: document.getElementById("profile-agenda-summary"),
  eligibilityCard: document.getElementById("eligibility-card"),
  eligibilityStatusBadge: document.getElementById("eligibility-status-badge"),
  eligibilityHeadline: document.getElementById("eligibility-headline"),
  eligibilityTargetRole: document.getElementById("eligibility-target-role"),
  integrityDot: document.getElementById("integrity-dot"),
  integrityText: document.getElementById("integrity-text"),
  eligibilityFoundSkills: document.getElementById("eligibility-found-skills"),
  eligibilitySupportedSkills: document.getElementById("eligibility-supported-skills"),
  eligibilityMissingSkills: document.getElementById("eligibility-missing-skills"),
  eligibilityReasonsList: document.getElementById("eligibility-reasons-list"),
  modePills: document.getElementById("mode-pills"),
  difficultyPills: document.getElementById("difficulty-pills"),
  lengthPills: document.getElementById("length-pills"),
  voiceAutoPills: document.getElementById("voice-auto-pills"),
  prepIndicatorCard: document.getElementById("prep-indicator-card"),
  prepStep1: document.getElementById("prep-step-1"),
  prepStep2: document.getElementById("prep-step-2"),
  prepStep3: document.getElementById("prep-step-3"),
  prepStep4: document.getElementById("prep-step-4"),
  startInterviewBtn: document.getElementById("start-interview-btn"),
  startSpinner: document.getElementById("start-spinner"),

  // View 3: Active Interview
  activityStatusCard: document.getElementById("activity-status-card"),
  activityStatusDot: document.getElementById("activity-status-dot"),
  activityStatusState: document.getElementById("activity-status-state"),
  activityStatusDetail: document.getElementById("activity-status-detail"),
  progressBadge: document.getElementById("progress-badge"),
  modeBadge: document.getElementById("mode-badge"),
  topicBadge: document.getElementById("topic-badge"),
  difficultyBadge: document.getElementById("difficulty-badge"),
  typeBadge: document.getElementById("type-badge"),
  questionMaxMarks: document.getElementById("question-max-marks"),
  progressBarFill: document.getElementById("progress-bar-fill"),
  endInterviewBtn: document.getElementById("end-interview-btn"),
  selectionReasonBanner: document.getElementById("selection-reason-banner"),
  selectionReasonText: document.getElementById("selection-reason-text"),

  // Question Card & Audio Controls
  questionText: document.getElementById("question-text"),
  speakQuestionBtn: document.getElementById("speak-question-btn"),
  stopSpeakingBtn: document.getElementById("stop-speaking-btn"),
  speakQuestionLabel: document.getElementById("speak-question-label"),
  questionAudioPlayer: document.getElementById("question-audio-player"),
  codeSnippetBox: document.getElementById("code-snippet-box"),
  codeSnippetHeader: document.getElementById("code-snippet-header"),
  codeSnippetContent: document.getElementById("code-snippet-content"),

  // Auto-Evaluation Countdown Banner
  autoEvalBanner: document.getElementById("auto-eval-banner"),
  autoEvalStatusText: document.getElementById("auto-eval-status-text"),
  autoEvalTimerFill: document.getElementById("auto-eval-timer-fill"),
  pauseCountdownBtn: document.getElementById("pause-countdown-btn"),
  evaluateNowBtn: document.getElementById("evaluate-now-btn"),

  // Workspaces
  workspaceVoice: document.getElementById("workspace-voice"),
  workspaceCode: document.getElementById("workspace-code"),
  workspaceOutput: document.getElementById("workspace-output"),

  // Workspace 1: Voice
  hostMicCheckbox: document.getElementById("host-mic-checkbox"),
  micModeLabel: document.getElementById("mic-mode-label"),
  recordToggleBtn: document.getElementById("record-toggle-btn"),
  recordBtnIcon: document.getElementById("record-btn-icon"),
  recordBtnLabel: document.getElementById("record-btn-label"),
  recordingLiveIndicator: document.getElementById("recording-live-indicator"),
  recordingTimer: document.getElementById("recording-timer"),
  transcribingIndicator: document.getElementById("transcribing-indicator"),
  transcriptReviewPanel: document.getElementById("transcript-review-panel"),
  transcriptInput: document.getElementById("transcript-input"),
  retryRecordBtn: document.getElementById("retry-record-btn"),
  submitTranscriptBtn: document.getElementById("submit-transcript-btn"),
  transcriptSpinner: document.getElementById("transcript-spinner"),

  // Workspace 2: Code Editor
  codeWorkspaceTitle: document.getElementById("code-workspace-title"),
  codeWorkspaceSubtitle: document.getElementById("code-workspace-subtitle"),
  codeEditorBadge: document.getElementById("code-editor-badge"),
  dbSchemaBox: document.getElementById("db-schema-box"),
  dbSchemaContent: document.getElementById("db-schema-content"),
  codeEditorInput: document.getElementById("code-editor-input"),
  codeEvaluateNowBtn: document.getElementById("code-evaluate-now-btn"),
  codeSpinner: document.getElementById("code-spinner"),

  // Workspace 3: Code Output
  outputPredictionInput: document.getElementById("output-prediction-input"),
  outputEvaluateNowBtn: document.getElementById("output-evaluate-now-btn"),
  outputSpinner: document.getElementById("output-spinner"),

  // Feedback Card
  feedbackCard: document.getElementById("feedback-card"),
  feedbackEarned: document.getElementById("feedback-earned"),
  feedbackMax: document.getElementById("feedback-max"),
  feedbackPercent: document.getElementById("feedback-percent"),
  feedbackAssessmentBadge: document.getElementById("feedback-assessment-badge"),
  feedbackSummary: document.getElementById("feedback-summary"),
  feedbackCriteriaList: document.getElementById("feedback-criteria-list"),
  feedbackMisconceptions: document.getElementById("feedback-misconceptions"),
  speakFeedbackBtn: document.getElementById("speak-feedback-btn"),
  feedbackAutoAdvance: document.getElementById("feedback-auto-advance"),
  feedbackTimerText: document.getElementById("feedback-timer-text"),
  feedbackTimerFill: document.getElementById("feedback-timer-fill"),
  feedbackPauseBtn: document.getElementById("feedback-pause-btn"),
  nextQuestionBtn: document.getElementById("next-question-btn"),

  // View 4: Report View
  reportNormalizedScore: document.getElementById("report-normalized-score"),
  reportRoleBadge: document.getElementById("report-role-badge"),
  reportGradeBadge: document.getElementById("report-grade-badge"),
  reportHeadline: document.getElementById("report-headline"),
  reportMetaText: document.getElementById("report-meta-text"),
  reportTopicBreakdown: document.getElementById("report-topic-breakdown"),
  reportDifficultyBreakdown: document.getElementById("report-difficulty-breakdown"),
  reportStrongCompetencies: document.getElementById("report-strong-competencies"),
  reportWeakCompetencies: document.getElementById("report-weak-competencies"),
  reportRecommendations: document.getElementById("report-recommendations"),
  reportStudyTopics: document.getElementById("report-study-topics"),
  reportResumePlanCard: document.getElementById("report-resume-plan-card"),
  reportPlanSummaryText: document.getElementById("report-plan-summary-text"),
  reportResumeSkillsChips: document.getElementById("report-resume-skills-chips"),
  reportSkillGapCard: document.getElementById("report-skill-gap-card"),
  reportGapSummaryBadge: document.getElementById("report-gap-summary-badge"),
  reportGapSummaryText: document.getElementById("report-gap-summary-text"),
  reportSkillGapGrid: document.getElementById("report-skill-gap-grid"),
  reportHistoryAccordion: document.getElementById("report-history-accordion"),
  downloadPdfBtn: document.getElementById("download-pdf-btn"),
  heroDownloadPdfBtn: document.getElementById("hero-download-pdf-btn"),
  restartInterviewBtn: document.getElementById("restart-interview-btn"),
};

// =============================================================================
// NAVIGATION & VIEW SWITCHING
// =============================================================================

function showView(viewName) {
  // viewName: 'upload', 'settings', 'interview', 'report'
  const views = {
    upload: elements.uploadView,
    settings: elements.settingsView,
    interview: elements.interviewView,
    report: elements.reportView,
  };

  Object.entries(views).forEach(([name, panel]) => {
    if (panel) {
      if (name === viewName) {
        panel.classList.add("active");
      } else {
        panel.classList.remove("active");
      }
    }
  });

  // Update Stepper
  const stepperMap = {
    upload: elements.stepNavUpload,
    settings: elements.stepNavSettings,
    interview: elements.stepNavInterview,
    report: elements.stepNavReport,
  };

  [elements.stepNavUpload, elements.stepNavSettings, elements.stepNavInterview, elements.stepNavReport].forEach((step) => {
    if (step) step.classList.remove("active");
  });

  if (stepperMap[viewName]) {
    stepperMap[viewName].classList.add("active");
  }

  window.scrollTo({ top: 0, behavior: "smooth" });
}

// =============================================================================
// PHASE 7: VISIBLE ACTIVITY STATUS INDICATOR
// =============================================================================

function updateActivityStatus(statusState, detail) {
  if (!elements.activityStatusState) return;

  const stateConfigs = {
    preparing_question: {
      label: "Preparing question",
      defaultDetail: "Calibrating next adaptive question against candidate competency...",
      dotClass: "status-pulse-dot pulsing state-evaluating",
    },
    speaking_question: {
      label: "Speaking question",
      defaultDetail: "AI voice synthesis reading question aloud. Listen carefully.",
      dotClass: "status-pulse-dot pulsing state-speaking",
    },
    ready_to_listen: {
      label: "Ready to listen",
      defaultDetail: "Microphone active. Click Start Speaking Answer or begin typing code.",
      dotClass: "status-pulse-dot state-ready",
    },
    recording_answer: {
      label: "Recording answer",
      defaultDetail: "Microphone active. Listening to candidate spoken answer...",
      dotClass: "status-pulse-dot pulsing state-recording",
    },
    stopping_recording: {
      label: "Stopping recording",
      defaultDetail: "Finalizing audio capture buffer...",
      dotClass: "status-pulse-dot state-transcribing",
    },
    transcribing_audio: {
      label: "Transcribing audio",
      defaultDetail: "Speech-to-Text agent converting spoken words to transcript...",
      dotClass: "status-pulse-dot pulsing state-transcribing",
    },
    evaluating_answer: {
      label: "Evaluating answer",
      defaultDetail: "Running deterministic rubric scoring and evidence extraction...",
      dotClass: "status-pulse-dot pulsing state-evaluating",
    },
    preparing_next_question: {
      label: "Preparing next question",
      defaultDetail: "Adapting difficulty based on previous score...",
      dotClass: "status-pulse-dot pulsing state-evaluating",
    },
    interview_completed: {
      label: "Interview completed",
      defaultDetail: "Finalizing assessment scores and assembling intelligence report...",
      dotClass: "status-pulse-dot state-ready",
    },
    recoverable_error: {
      label: "Recoverable error",
      defaultDetail: detail || "An issue occurred. You can retry recording without losing progress.",
      dotClass: "status-pulse-dot state-error",
    },
  };

  const cfg = stateConfigs[statusState] || {
    label: statusState,
    defaultDetail: detail || "",
    dotClass: "status-pulse-dot state-ready",
  };

  elements.activityStatusState.textContent = cfg.label;
  elements.activityStatusDetail.textContent = detail || cfg.defaultDetail;
  if (elements.activityStatusDot) {
    elements.activityStatusDot.className = cfg.dotClass;
  }
}

// =============================================================================
// INITIAL SCREEN (RESUME UPLOAD ONLY) LOGIC
// =============================================================================

function validateFile(file) {
  if (!file) return { valid: false, error: "Please select a file." };

  const validExtensions = [".pdf", ".docx", ".txt"];
  const fileName = file.name.toLowerCase();
  const isValidExt = validExtensions.some((ext) => fileName.endsWith(ext));

  if (!isValidExt) {
    return {
      valid: false,
      error: `Unsupported file format '${fileName.split(".").pop()}'. Allowed formats: PDF, DOCX, TXT.`,
    };
  }

  const maxBytes = 10 * 1024 * 1024; // 10 MB
  if (file.size > maxBytes) {
    const mb = (file.size / (1024 * 1024)).toFixed(1);
    return {
      valid: false,
      error: `File size (${mb} MB) exceeds maximum allowed limit of 10 MB.`,
    };
  }

  if (file.size === 0) {
    return { valid: false, error: "Uploaded file is empty (0 bytes)." };
  }

  return { valid: true };
}

function updateUploadUI() {
  const role = elements.initialTargetRole.value.trim();
  const hasFile = !!state.selectedFile;

  elements.uploadErrorBanner.style.display = "none";

  if (hasFile) {
    elements.initialDropZone.style.display = "none";
    elements.fileSelectedBadge.style.display = "flex";
    elements.selectedFileName.textContent = state.selectedFile.name;
    const kb = (state.selectedFile.size / 1024).toFixed(1);
    elements.selectedFileSize.textContent = kb >= 1024 ? `${(kb / 1024).toFixed(1)} MB` : `${kb} KB`;
  } else {
    elements.initialDropZone.style.display = "block";
    elements.fileSelectedBadge.style.display = "none";
  }

  // Analyze button enabled ONLY when both inputs are valid
  const canAnalyze = hasFile && role.length > 0;
  elements.analyzeResumeBtn.disabled = !canAnalyze;
}

function setupUploadEvents() {
  // Target role input
  elements.initialTargetRole.addEventListener("input", () => {
    state.targetRole = elements.initialTargetRole.value.trim();
    updateUploadUI();
  });

  // Drop zone clicks
  elements.initialDropZone.addEventListener("click", () => {
    elements.initialResumeFile.click();
  });

  // File browse change
  elements.initialResumeFile.addEventListener("change", (e) => {
    if (e.target.files && e.target.files[0]) {
      handleSelectedFile(e.target.files[0]);
    }
  });

  // Change file button
  elements.changeFileBtn.addEventListener("click", () => {
    state.selectedFile = null;
    elements.initialResumeFile.value = "";
    updateUploadUI();
  });

  // Drag & drop
  ["dragenter", "dragover"].forEach((eventName) => {
    elements.initialDropZone.addEventListener(eventName, (e) => {
      e.preventDefault();
      elements.initialDropZone.classList.add("dragover");
    });
  });

  ["dragleave", "drop"].forEach((eventName) => {
    elements.initialDropZone.addEventListener(eventName, (e) => {
      e.preventDefault();
      elements.initialDropZone.classList.remove("dragover");
    });
  });

  elements.initialDropZone.addEventListener("drop", (e) => {
    if (e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleSelectedFile(e.dataTransfer.files[0]);
    }
  });

  // Analyze Resume Button Click
  elements.analyzeResumeBtn.addEventListener("click", performResumeAnalysis);
}

function handleSelectedFile(file) {
  const check = validateFile(file);
  if (!check.valid) {
    elements.uploadErrorText.textContent = check.error;
    elements.uploadErrorBanner.style.display = "flex";
    state.selectedFile = null;
    updateUploadUI();
    return;
  }

  state.selectedFile = file;
  updateUploadUI();
}

async function performResumeAnalysis() {
  if (!state.selectedFile || !state.targetRole) return;

  elements.analyzeResumeBtn.disabled = true;
  elements.analyzeSpinner.style.display = "inline-block";
  elements.uploadErrorBanner.style.display = "none";
  elements.analysisLoadingState.style.display = "flex";

  const progressSteps = [
    { title: "Parsing Resume Structure...", text: "Extracting contact details, text tokens, and structural sections..." },
    { title: "Analyzing Technical Skills...", text: "Auditing technical claims, frameworks, tools, and experience..." },
    { title: "Evaluating Target Role Alignment...", text: "Routing to domain-specific technical assessment model..." },
    { title: "Structuring Interview Plan...", text: "Binding curriculum rubrics and questions to candidate claims..." },
  ];

  let stepIdx = 0;
  const stepInterval = setInterval(() => {
    stepIdx = (stepIdx + 1) % progressSteps.length;
    elements.analysisStepTitle.textContent = progressSteps[stepIdx].title;
    elements.analysisStepText.textContent = progressSteps[stepIdx].text;
  }, 1200);

  try {
    const formData = new FormData();
    formData.append("file", state.selectedFile);
    formData.append("target_role", state.targetRole);

    const res = await fetch(`${API_BASE}/api/resume/upload`, {
      method: "POST",
      body: formData,
    });

    clearInterval(stepInterval);

    if (!res.ok) {
      const errData = await res.json().catch(() => ({ detail: "Upload failed." }));
      throw new Error(errData.detail || "Failed to analyze resume document.");
    }

    const data = await res.json();
    state.resumeId = data.resume_id;
    state.resumeProfile = data.profile || data;
    state.routedTrack = data.routed_track || "python";
    state.interviewPlan = data.interview_plan || null;

    // Populate Settings View
    populateSettingsView(data);

    // Transition to Screen 2
    showView("settings");
  } catch (err) {
    clearInterval(stepInterval);
    elements.uploadErrorText.textContent = err.message || "An error occurred during resume analysis.";
    elements.uploadErrorBanner.style.display = "flex";
    elements.analyzeResumeBtn.disabled = false;
  } finally {
    elements.analyzeSpinner.style.display = "none";
    elements.analysisLoadingState.style.display = "none";
  }
}

// =============================================================================
// SCREEN 2: PROFILE & SETTINGS
// =============================================================================

function populateSettingsView(data) {
  elements.profileCandidateName.textContent = data.candidate_name || "Candidate Profile";
  elements.profileTargetRole.textContent = `Target Role: ${state.targetRole || data.target_role || "Software Engineer"}`;
  
  const expYears = data.total_experience_years || 0;
  elements.profileExpBadge.textContent = `${expYears} ${expYears === 1 ? "Year" : "Years"} Experience`;

  const integrity = data.integrity_status || "passed";
  elements.profileIntegrityBadge.textContent = integrity === "passed" ? "✓ Integrity Verified" : "⚠️ Minor Discrepancy Audited";
  elements.profileIntegrityBadge.className = integrity === "passed" ? "badge badge-success" : "badge badge-warning";

  // Skills chips
  elements.profileSkillsChips.innerHTML = "";
  const skills = data.skills || data.claimed_skills || [];
  if (skills.length > 0) {
    skills.slice(0, 15).forEach((skill) => {
      const chip = document.createElement("span");
      chip.className = "skill-chip";
      chip.textContent = skill;
      elements.profileSkillsChips.appendChild(chip);
    });
  } else {
    elements.profileSkillsChips.innerHTML = '<span class="chip-muted">Foundational curriculum competencies</span>';
  }

  // Agenda summary
  if (state.interviewPlan && state.interviewPlan.summary) {
    elements.profileAgendaSummary.textContent = state.interviewPlan.summary;
  } else {
    elements.profileAgendaSummary.textContent =
      `Personalized assessment established to evaluate verified claims against ${state.targetRole} benchmarks.`;
  }

  // Prep steps
  elements.prepStep1.className = "prep-step-item done";
  elements.prepStep2.className = "prep-step-item done";
  elements.prepStep3.className = "prep-step-item done";
  elements.prepStep4.className = "prep-step-item ready";

  // Phase 3: Populate Eligibility & Integrity Card
  populateEligibilityView(data);
}

// =============================================================================
// PHASE 3: ROLE-BASED ELIGIBILITY & INTEGRITY VIEW
// =============================================================================

function populateEligibilityView(data) {
  const elig = data.eligibility_assessment || {};
  const auth = data.authenticity_assessment || {};

  if (elements.eligibilityCard) {
    elements.eligibilityCard.style.display = "block";
  }

  // 1. Understandable Eligibility Result
  const outcome = elig.outcome || data.eligibility_status || "eligible";
  const outcomeLabels = {
    eligible: "Eligible",
    potentially_eligible: "Potentially Eligible",
    not_currently_eligible: "Not Currently Eligible",
  };

  if (elements.eligibilityStatusBadge) {
    elements.eligibilityStatusBadge.textContent = outcomeLabels[outcome] || outcome.toUpperCase();
    elements.eligibilityStatusBadge.className = `eligibility-status-badge ${outcome}`;
  }

  if (elements.eligibilityHeadline) {
    elements.eligibilityHeadline.textContent = elig.headline || "Role-Readiness Assessment";
  }

  if (elements.eligibilityTargetRole) {
    elements.eligibilityTargetRole.textContent = `Target Role: ${state.targetRole || elig.target_role || "Software Engineer"}`;
  }

  // 2. Resume Authenticity & Integrity Status (4-outcome compliant)
  const integrityOutcome = auth.outcome || data.authenticity_outcome || "no_inconsistencies";
  const integrityLabel = auth.outcome_label || "No significant inconsistencies detected";
  if (elements.integrityText) {
    elements.integrityText.textContent = integrityLabel;
  }
  if (elements.integrityDot) {
    elements.integrityDot.className =
      integrityOutcome === "no_inconsistencies"
        ? "status-dot dot-online"
        : integrityOutcome === "potential_inconsistencies"
        ? "status-dot dot-warning"
        : "status-dot dot-offline";
  }

  // 3. Relevant Skills Found, Evidence-Supported, and Missing/Weak
  const renderChips = (container, list, defaultText) => {
    if (!container) return;
    container.innerHTML = "";
    if (list && list.length > 0) {
      list.forEach((s) => {
        const span = document.createElement("span");
        span.className = "skill-chip";
        span.textContent = s;
        container.appendChild(span);
      });
    } else {
      container.innerHTML = `<span class="chip-muted">${defaultText}</span>`;
    }
  };

  renderChips(elements.eligibilityFoundSkills, elig.relevant_skills_found, "No explicit skills found");
  renderChips(elements.eligibilitySupportedSkills, elig.evidence_supported_skills, "None explicitly verified in projects/exp");
  renderChips(elements.eligibilityMissingSkills, elig.missing_or_weak_skills, "None (All required competencies present)");

  // 4. Reasons Supporting Assessment Result
  if (elements.eligibilityReasonsList) {
    elements.eligibilityReasonsList.innerHTML = "";
    const reasons = elig.reasons_supporting_result || data.eligibility_reasons || [];
    if (reasons.length > 0) {
      reasons.forEach((r) => {
        const li = document.createElement("li");
        li.textContent = r;
        elements.eligibilityReasonsList.appendChild(li);
      });
    } else {
      const li = document.createElement("li");
      li.textContent = "Candidate meets foundational qualifications for this technical assessment track.";
      elements.eligibilityReasonsList.appendChild(li);
    }
  }
}

function setupSettingsEvents() {
  // Mode pills (Mock vs Predefined)
  elements.modePills.querySelectorAll(".pill").forEach((pill) => {
    pill.addEventListener("click", () => {
      elements.modePills.querySelectorAll(".pill").forEach((p) => p.classList.remove("active"));
      pill.classList.add("active");
      state.interviewMode = pill.getAttribute("data-mode") || "mock";
    });
  });

  // Difficulty pills
  elements.difficultyPills.querySelectorAll(".pill").forEach((pill) => {
    pill.addEventListener("click", () => {
      elements.difficultyPills.querySelectorAll(".pill").forEach((p) => p.classList.remove("active"));
      pill.classList.add("active");
      state.difficultyMode = pill.getAttribute("data-difficulty") || "adaptive";
    });
  });

  // Length pills
  elements.lengthPills.querySelectorAll(".pill-sm").forEach((pill) => {
    pill.addEventListener("click", () => {
      elements.lengthPills.querySelectorAll(".pill-sm").forEach((p) => p.classList.remove("active"));
      pill.classList.add("active");
      state.questionCount = parseInt(pill.getAttribute("data-count") || "5", 10);
    });
  });

  // Voice pills
  elements.voiceAutoPills.querySelectorAll(".pill-sm").forEach((pill) => {
    pill.addEventListener("click", () => {
      elements.voiceAutoPills.querySelectorAll(".pill-sm").forEach((p) => p.classList.remove("active"));
      pill.classList.add("active");
      state.autoSpeakQuestion = pill.getAttribute("data-voice-auto") === "true";
    });
  });

  // Start interview button
  elements.startInterviewBtn.addEventListener("click", startAssessmentSession);
}

async function startAssessmentSession() {
  elements.startInterviewBtn.disabled = true;
  elements.startSpinner.style.display = "inline-block";

  try {
    // 1. Prepare questions with pre-configured plan
    await fetch(`${API_BASE}/api/interview/prepare`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        resume_id: state.resumeId,
        target_role: state.targetRole,
        interview_mode: state.interviewMode,
        max_questions: state.questionCount,
        difficulty_mode: state.difficultyMode,
      }),
    }).catch((e) => console.warn("Prepare call warning:", e));

    // 2. Start session
    const startPayload = {
      role: state.targetRole,
      track: state.routedTrack,
      max_questions: state.questionCount,
      difficulty_mode: state.difficultyMode,
      dynamic_questions: state.interviewMode === "mock",
      resume_id: state.resumeId,
    };

    const res = await fetch(`${API_BASE}/api/interview/start`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(startPayload),
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "Could not start interview." }));
      throw new Error(err.detail || "Failed to start interview session.");
    }

    const startData = await res.json();
    state.sessionId = startData.session_id;

    // Transition to Screen 3
    showView("interview");

    // Render Question 1
    renderQuestion(startData);
  } catch (err) {
    alert(`Could not start interview: ${err.message}`);
    elements.startInterviewBtn.disabled = false;
  } finally {
    elements.startSpinner.style.display = "none";
  }
}

// =============================================================================
// SCREEN 3: ACTIVE INTERVIEW & QUESTION-DRIVEN WORKSPACE
// =============================================================================

function renderQuestion(q) {
  state.currentQuestion = q;
  state.isSubmitting = false;

  // Clear any existing timers
  cancelAutoEvalCountdown();
  cancelFeedbackAdvance();

  // Hide feedback card
  elements.feedbackCard.style.display = "none";
  elements.autoEvalBanner.style.display = "none";

  // Header & Badges
  elements.progressBadge.textContent = `Question ${q.question_number} of ${q.max_questions || state.questionCount}`;
  const pct = Math.round(((q.question_number - 1) / (q.max_questions || state.questionCount)) * 100);
  elements.progressBarFill.style.width = `${Math.max(15, pct)}%`;

  elements.modeBadge.textContent = state.interviewMode === "mock" ? "✨ AI Dynamic" : "📚 Curated Benchmark";
  elements.topicBadge.textContent = q.topic || "Core Engineering";
  elements.difficultyBadge.textContent = (q.difficulty || "intermediate").toUpperCase();
  elements.typeBadge.textContent = (q.question_type || "conceptual").toUpperCase();
  elements.questionMaxMarks.textContent = (q.max_marks || 5.0).toFixed(1);

  // Selection Reason
  elements.selectionReasonText.textContent = q.reason || q.selection_reason || "Assessing targeted technical competency.";

  // Question Text
  elements.questionText.textContent = q.text || q.question || "";

  // Code Snippet Box (if provided)
  if (q.code_snippet) {
    elements.codeSnippetBox.style.display = "block";
    elements.codeSnippetContent.textContent = q.code_snippet;
    elements.codeSnippetHeader.textContent = `${q.language ? q.language.toUpperCase() : "CODE"} SNIPPET`;
  } else {
    elements.codeSnippetBox.style.display = "none";
  }

  // Determine Response Workspace from Structured Question Metadata
  const respType = q.response_type || (
    q.question_type === "code_writing" ? "code_writing" :
    q.question_type === "debugging" ? "debugging" :
    q.question_type === "code_output" ? "code_output" : "verbal"
  );

  // Reset & route workspaces
  elements.workspaceVoice.style.display = "none";
  elements.workspaceCode.style.display = "none";
  elements.workspaceOutput.style.display = "none";

  if (respType === "code_writing" || respType === "debugging") {
    // Reveal Code Workspace
    elements.workspaceCode.style.display = "block";
    const lang = (q.language || "python").toLowerCase();
    elements.codeEditorBadge.textContent = `${lang.toUpperCase()} Sandbox`;

    if (respType === "debugging") {
      elements.codeWorkspaceTitle.textContent = `${lang.toUpperCase()} Debugging Workspace`;
      elements.codeWorkspaceSubtitle.textContent = "Analyze the defect in the code and type your fixed implementation below.";
      elements.codeEditorInput.value = q.starter_code || q.code_snippet || "";
    } else {
      elements.codeWorkspaceTitle.textContent = `${lang.toUpperCase()} Implementation Workspace`;
      elements.codeWorkspaceSubtitle.textContent = "Implement your solution below. Pausing typing initiates automatic evaluation.";
      elements.codeEditorInput.value = q.starter_code || "";
    }

    // DB Schema preview if present
    if (q.db_schema) {
      elements.dbSchemaBox.style.display = "block";
      elements.dbSchemaContent.textContent = q.db_schema;
    } else {
      elements.dbSchemaBox.style.display = "none";
    }

    elements.codeEditorInput.focus();
  } else if (respType === "code_output") {
    // Reveal Output Prediction Workspace
    elements.workspaceOutput.style.display = "block";
    elements.outputPredictionInput.value = "";
    elements.outputPredictionInput.focus();
  } else {
    // Verbal Workspace (Conceptual, Scenario, Practical)
    elements.workspaceVoice.style.display = "block";
    elements.transcriptInput.value = "";
    elements.transcriptReviewPanel.style.display = "none";
    elements.recordingLiveIndicator.style.display = "none";
    elements.transcribingIndicator.style.display = "none";
    elements.recordBtnLabel.textContent = "Start Speaking Answer";
    elements.recordBtnIcon.textContent = "🎙️";
  }

  // Update live activity status
  updateActivityStatus("ready_to_listen", "Question presented. Read prompt and begin speaking or coding.");

  // Audio speech: read question aloud if enabled
  if (state.autoSpeakQuestion) {
    speakQuestionAloud();
  }
}

// =============================================================================
// SPEECH INTEGRATION & AUDIO PLAYBACK
// =============================================================================

async function speakQuestionAloud() {
  if (!state.sessionId) return;

  try {
    elements.speakQuestionLabel.textContent = "Playing...";
    elements.speakQuestionBtn.style.display = "none";
    elements.stopSpeakingBtn.style.display = "inline-flex";
    updateActivityStatus("speaking_question", "AI voice synthesis reading question aloud...");

    const audioUrl = `${API_BASE}/api/interview/${state.sessionId}/audio?t=${Date.now()}`;
    elements.questionAudioPlayer.src = audioUrl;

    elements.questionAudioPlayer.onended = () => {
      elements.speakQuestionLabel.textContent = "Listen";
      elements.speakQuestionBtn.style.display = "inline-flex";
      elements.stopSpeakingBtn.style.display = "none";
      updateActivityStatus("ready_to_listen", "Question read. Ready to listen to your answer.");
    };

    elements.questionAudioPlayer.onerror = () => {
      elements.speakQuestionLabel.textContent = "Listen";
      elements.speakQuestionBtn.style.display = "inline-flex";
      elements.stopSpeakingBtn.style.display = "none";
      updateActivityStatus("ready_to_listen", "Microphone ready to capture your answer.");
    };

    await elements.questionAudioPlayer.play();
  } catch (err) {
    console.warn("Audio playback error:", err);
    elements.speakQuestionLabel.textContent = "Listen";
    elements.speakQuestionBtn.style.display = "inline-flex";
    elements.stopSpeakingBtn.style.display = "none";
    updateActivityStatus("ready_to_listen", "Microphone ready to capture your answer.");
  }
}

function stopQuestionAudio() {
  if (elements.questionAudioPlayer) {
    elements.questionAudioPlayer.pause();
    elements.questionAudioPlayer.currentTime = 0;
  }
  elements.speakQuestionLabel.textContent = "Listen";
  elements.speakQuestionBtn.style.display = "inline-flex";
  elements.stopSpeakingBtn.style.display = "none";
  updateActivityStatus("ready_to_listen", "Microphone ready to capture your answer.");
}

// =============================================================================
// MICROPHONE RECORDING & STT TRANSCRIPTION
// =============================================================================

function setupSpeechEvents() {
  // Listen / Stop question audio buttons
  elements.speakQuestionBtn.addEventListener("click", speakQuestionAloud);
  elements.stopSpeakingBtn.addEventListener("click", stopQuestionAudio);

  // Host vs Browser mic toggle
  elements.hostMicCheckbox.addEventListener("change", (e) => {
    elements.micModeLabel.textContent = e.target.checked ? "System Microphone" : "Browser Mic";
  });

  // Record Toggle Button
  elements.recordToggleBtn.addEventListener("click", toggleRecording);

  // Retry Recording Button
  elements.retryRecordBtn.addEventListener("click", () => {
    cancelAutoEvalCountdown();
    elements.transcriptReviewPanel.style.display = "none";
    elements.transcriptInput.value = "";
    elements.recordBtnLabel.textContent = "Start Speaking Answer";
    elements.recordBtnIcon.textContent = "🎙️";
  });

  // Submit Transcript Now Button
  elements.submitTranscriptBtn.addEventListener("click", () => {
    const text = elements.transcriptInput.value.trim();
    if (text) {
      cancelAutoEvalCountdown();
      submitAnswer(text);
    }
  });

  // Code evaluate now button
  elements.codeEvaluateNowBtn.addEventListener("click", () => {
    const code = elements.codeEditorInput.value.trim();
    if (code) {
      cancelAutoEvalCountdown();
      submitAnswer(code);
    }
  });

  // Output evaluate now button
  elements.outputEvaluateNowBtn.addEventListener("click", () => {
    const text = elements.outputPredictionInput.value.trim();
    if (text) {
      cancelAutoEvalCountdown();
      submitAnswer(text);
    }
  });

  // Auto-evaluation pause & now buttons
  elements.pauseCountdownBtn.addEventListener("click", toggleAutoEvalPause);
  elements.evaluateNowBtn.addEventListener("click", () => {
    if (state.activeSubmitCallback) {
      state.activeSubmitCallback();
    }
  });

  // Code editor tab support and typing debounce
  elements.codeEditorInput.addEventListener("keydown", (e) => {
    if (e.key === "Tab") {
      e.preventDefault();
      const start = elements.codeEditorInput.selectionStart;
      const end = elements.codeEditorInput.selectionEnd;
      elements.codeEditorInput.value =
        elements.codeEditorInput.value.substring(0, start) +
        "    " +
        elements.codeEditorInput.value.substring(end);
      elements.codeEditorInput.selectionStart = elements.codeEditorInput.selectionEnd = start + 4;
    }
  });

  elements.codeEditorInput.addEventListener("input", () => {
    handleTypingInactivity(() => {
      const code = elements.codeEditorInput.value.trim();
      if (code) submitAnswer(code);
    });
  });

  elements.outputPredictionInput.addEventListener("input", () => {
    handleTypingInactivity(() => {
      const pred = elements.outputPredictionInput.value.trim();
      if (pred) submitAnswer(pred);
    });
  });

  // Feedback Pause & Next Question
  elements.feedbackPauseBtn.addEventListener("click", toggleFeedbackAdvancePause);
  elements.nextQuestionBtn.addEventListener("click", advanceToNextQuestion);

  // End interview button
  elements.endInterviewBtn.addEventListener("click", endInterviewEarly);
  elements.restartInterviewBtn.addEventListener("click", restartAssessment);

  // PDF Report Download Buttons (Phase 11)
  const triggerPdfDownload = () => {
    if (!state.sessionId) {
      alert("No active interview session available for PDF download.");
      return;
    }
    window.open(`${API_BASE}/api/interview/${state.sessionId}/pdf`, "_blank");
  };

  if (elements.downloadPdfBtn) {
    elements.downloadPdfBtn.addEventListener("click", triggerPdfDownload);
  }
  if (elements.heroDownloadPdfBtn) {
    elements.heroDownloadPdfBtn.addEventListener("click", triggerPdfDownload);
  }
}

async function toggleRecording() {
  if (state.mediaRecorder && state.mediaRecorder.state === "recording") {
    stopBrowserRecording();
  } else {
    const useHost = elements.hostMicCheckbox.checked;
    if (useHost) {
      recordHostMicrophone();
    } else {
      startBrowserRecording();
    }
  }
}

async function startBrowserRecording() {
  try {
    cancelAutoEvalCountdown();
    stopQuestionAudio();

    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    state.audioChunks = [];
    state.mediaRecorder = new MediaRecorder(stream);

    state.mediaRecorder.ondataavailable = (e) => {
      if (e.data && e.data.size > 0) {
        state.audioChunks.push(e.data);
      }
    };

    state.mediaRecorder.onstop = async () => {
      stream.getTracks().forEach((track) => track.stop());
      await transcribeRecordedAudioChunks();
    };

    state.mediaRecorder.start();

    // UI & Activity Updates
    updateActivityStatus("recording_answer", "Microphone listening to your answer...");
    elements.recordBtnLabel.textContent = "Stop Speaking (Finish Answer)";
    elements.recordBtnIcon.textContent = "⏹️";
    elements.recordingLiveIndicator.style.display = "flex";
    elements.recordingTimer.textContent = "00:00";
    state.recordStartTime = Date.now();

    clearInterval(state.recordTimerInterval);
    state.recordTimerInterval = setInterval(() => {
      const elapsedSec = Math.floor((Date.now() - state.recordStartTime) / 1000);
      const m = String(Math.floor(elapsedSec / 60)).padStart(2, "0");
      const s = String(elapsedSec % 60).padStart(2, "0");
      elements.recordingTimer.textContent = `${m}:${s}`;
    }, 1000);
  } catch (err) {
    updateActivityStatus("recoverable_error", "Microphone access denied or unavailable.");
    alert(`Microphone permission denied or unavailable: ${err.message}`);
  }
}

function stopBrowserRecording() {
  if (state.mediaRecorder && state.mediaRecorder.state === "recording") {
    state.mediaRecorder.stop();
  }
  clearInterval(state.recordTimerInterval);
  elements.recordingLiveIndicator.style.display = "none";
  elements.recordBtnLabel.textContent = "Start Speaking Answer";
  elements.recordBtnIcon.textContent = "🎙️";
  updateActivityStatus("stopping_recording", "Recording stopped. Uploading audio for transcription...");
}

async function transcribeRecordedAudioChunks() {
  if (!state.audioChunks.length) return;

  elements.transcribingIndicator.style.display = "flex";
  updateActivityStatus("transcribing_audio", "Transcribing captured audio with Speech-to-Text agent...");

  try {
    const blob = new Blob(state.audioChunks, { type: "audio/wav" });
    const formData = new FormData();
    formData.append("file", blob, "recording.wav");

    const res = await fetch(`${API_BASE}/api/interview/${state.sessionId}/transcribe_upload`, {
      method: "POST",
      body: formData,
    });

    const data = await res.json();
    if (data.is_success && data.transcript && data.transcript.trim()) {
      elements.transcriptInput.value = data.transcript.trim();
      elements.transcriptReviewPanel.style.display = "block";
      updateActivityStatus("evaluating_answer", "Transcription successful. Evaluating answer automatically...");
      // Spoken workflow Phase 7: Automatically evaluate immediately after transcription
      await submitAnswer(data.transcript.trim());
    } else {
      updateActivityStatus("recoverable_error", "No speech recognized. Click Discard & Retry to re-record.");
      elements.transcriptReviewPanel.style.display = "block";
      elements.transcriptInput.value = "";
      alert(`Could not transcribe speech: ${data.error_message || "No audible words recognized."}`);
    }
  } catch (err) {
    updateActivityStatus("recoverable_error", "Speech transcription network or server failure.");
    alert(`Speech transcription error: ${err.message}`);
  } finally {
    elements.transcribingIndicator.style.display = "none";
  }
}

async function recordHostMicrophone() {
  try {
    cancelAutoEvalCountdown();
    stopQuestionAudio();
    elements.transcribingIndicator.style.display = "flex";
    updateActivityStatus("recording_answer", "Listening via host microphone...");

    const res = await fetch(`${API_BASE}/api/interview/${state.sessionId}/listen`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ timeout: 8.0, phrase_time_limit: 30.0 }),
    });

    const data = await res.json();
    if (data.is_success && data.transcript && data.transcript.trim()) {
      elements.transcriptInput.value = data.transcript.trim();
      elements.transcriptReviewPanel.style.display = "block";
      updateActivityStatus("evaluating_answer", "Host speech transcribed. Evaluating answer automatically...");
      await submitAnswer(data.transcript.trim());
    } else {
      updateActivityStatus("recoverable_error", "No speech detected on host microphone. Please retry.");
      elements.transcriptReviewPanel.style.display = "block";
      elements.transcriptInput.value = "";
      alert(`System microphone recognition: ${data.error_message || "No speech detected."}`);
    }
  } catch (err) {
    updateActivityStatus("recoverable_error", "Microphone connection error.");
    alert(`Microphone error: ${err.message}`);
  } finally {
    elements.transcribingIndicator.style.display = "none";
  }
}

// =============================================================================
// AUTO-EVALUATION COUNTDOWN & INACTIVITY DEBOUNCE
// =============================================================================

function handleTypingInactivity(callback) {
  clearTimeout(state.typingPauseTimeout);
  cancelAutoEvalCountdown();

  state.typingPauseTimeout = setTimeout(() => {
    startAutoEvalCountdown(callback);
  }, 1000);
}

function startAutoEvalCountdown(callback) {
  cancelAutoEvalCountdown();
  state.activeSubmitCallback = callback;
  state.autoEvalTotalMs = 4000;
  state.autoEvalRemainingMs = state.autoEvalTotalMs;
  state.isAutoEvalPaused = false;

  elements.autoEvalBanner.style.display = "flex";
  elements.pauseCountdownBtn.textContent = "Pause Timer";
  updateAutoEvalBannerUI();

  const intervalStepMs = 100;
  state.autoEvalInterval = setInterval(() => {
    if (state.isAutoEvalPaused) return;

    state.autoEvalRemainingMs -= intervalStepMs;
    updateAutoEvalBannerUI();

    if (state.autoEvalRemainingMs <= 0) {
      cancelAutoEvalCountdown();
      if (state.activeSubmitCallback) {
        state.activeSubmitCallback();
      }
    }
  }, intervalStepMs);
}

function updateAutoEvalBannerUI() {
  const sec = Math.ceil(Math.max(0, state.autoEvalRemainingMs) / 1000);
  elements.autoEvalStatusText.innerHTML = `Inactivity detected: Evaluating answer automatically in <strong>${sec}</strong>s...`;
  const pct = Math.max(0, (state.autoEvalRemainingMs / state.autoEvalTotalMs) * 100);
  elements.autoEvalTimerFill.style.width = `${pct}%`;
}

function toggleAutoEvalPause() {
  state.isAutoEvalPaused = !state.isAutoEvalPaused;
  elements.pauseCountdownBtn.textContent = state.isAutoEvalPaused ? "Resume Timer" : "Pause Timer";
}

function cancelAutoEvalCountdown() {
  clearInterval(state.autoEvalInterval);
  state.autoEvalInterval = null;
  state.activeSubmitCallback = null;
  elements.autoEvalBanner.style.display = "none";
}

// =============================================================================
// SUBMISSION & ACCURATE EVALUATION
// =============================================================================

async function submitAnswer(answerText) {
  if (state.isSubmitting || !state.sessionId) return;
  if (!answerText || !answerText.trim()) return;

  state.isSubmitting = true;
  cancelAutoEvalCountdown();
  updateActivityStatus("evaluating_answer", "Evaluating response against calibrated rubrics...");

  // Show spinners
  elements.transcriptSpinner.style.display = "inline-block";
  elements.codeSpinner.style.display = "inline-block";
  elements.outputSpinner.style.display = "inline-block";

  try {
    const res = await fetch(`${API_BASE}/api/interview/${state.sessionId}/answer`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ answer: answerText }),
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "Answer submission failed." }));
      throw new Error(err.detail || "Evaluation failed.");
    }

    const data = await res.json();
    displayEvaluationFeedback(data);
  } catch (err) {
    updateActivityStatus("recoverable_error", "Evaluation failed. You may retry your submission.");
    alert(`Evaluation Error: ${err.message}`);
    state.isSubmitting = false;
  } finally {
    elements.transcriptSpinner.style.display = "none";
    elements.codeSpinner.style.display = "none";
    elements.outputSpinner.style.display = "none";
  }
}

function displayEvaluationFeedback(data) {
  const evalData = data.evaluation || {};
  elements.feedbackCard.style.display = "block";
  updateActivityStatus("ready_to_listen", "Answer evaluated. Review your marks and rubric feedback.");

  // Score
  const earned = evalData.awarded_marks !== undefined ? evalData.awarded_marks : 0;
  const max = evalData.max_marks !== undefined ? evalData.max_marks : 5;
  const pct = evalData.percentage !== undefined ? Math.round(evalData.percentage) : 0;

  elements.feedbackEarned.textContent = earned.toFixed(1);
  elements.feedbackMax.textContent = max.toFixed(1);
  elements.feedbackPercent.textContent = pct;

  // Assessment badge
  const assessment = evalData.assessment || (pct >= 75 ? "strong" : pct >= 40 ? "partial" : "insufficient");
  elements.feedbackAssessmentBadge.textContent = assessment.toUpperCase();
  elements.feedbackAssessmentBadge.className =
    pct >= 75 ? "badge badge-success" : pct >= 40 ? "badge badge-warning" : "badge badge-danger";

  // Summary
  elements.feedbackSummary.textContent = evalData.summary || "Evaluation completed against explicit criteria.";

  // Criteria list
  elements.feedbackCriteriaList.innerHTML = "";
  if (evalData.criteria && evalData.criteria.length > 0) {
    evalData.criteria.forEach((crit) => {
      const item = document.createElement("div");
      item.className = "criterion-item";
      item.innerHTML = `
        <div class="criterion-header">
          <strong>${crit.criterion_id}</strong>
          <span>${crit.awarded_marks.toFixed(1)} / ${crit.max_marks.toFixed(1)} pts</span>
        </div>
        <p class="criterion-desc">${crit.explanation || crit.evidence || ""}</p>
      `;
      elements.feedbackCriteriaList.appendChild(item);
    });
  }

  // Misconceptions
  if (evalData.incorrect_claims && evalData.incorrect_claims.length > 0) {
    elements.feedbackMisconceptions.style.display = "block";
    elements.feedbackMisconceptions.innerHTML = `
      <strong>Misconceptions Detected:</strong> ${evalData.incorrect_claims.join("; ")}
    `;
  } else {
    elements.feedbackMisconceptions.style.display = "none";
  }

  // Auto-advance or Next Question setup
  state.cachedNextData = data;

  if (data.is_complete) {
    elements.nextQuestionBtn.textContent = "View Final Assessment Report →";
    startFeedbackAdvanceCountdown(loadFinalReport);
  } else {
    elements.nextQuestionBtn.textContent = "Continue to Next Question Now →";
    startFeedbackAdvanceCountdown(() => {
      advanceToNextQuestion();
    });
  }
}

function startFeedbackAdvanceCountdown(callback) {
  cancelFeedbackAdvance();
  state.activeAdvanceCallback = callback;
  state.feedbackAdvanceRemaining = 5;
  state.isFeedbackAdvancePaused = false;

  elements.feedbackPauseBtn.textContent = "Pause Timer";
  updateFeedbackTimerUI();

  state.feedbackAdvanceInterval = setInterval(() => {
    if (state.isFeedbackAdvancePaused) return;

    state.feedbackAdvanceRemaining -= 1;
    updateFeedbackTimerUI();

    if (state.feedbackAdvanceRemaining <= 0) {
      cancelFeedbackAdvance();
      if (state.activeAdvanceCallback) {
        state.activeAdvanceCallback();
      }
    }
  }, 1000);
}

function updateFeedbackTimerUI() {
  elements.feedbackTimerText.innerHTML =
    `Continuing automatically in <strong>${Math.max(0, state.feedbackAdvanceRemaining)}</strong>s...`;
  const pct = Math.max(0, (state.feedbackAdvanceRemaining / 5) * 100);
  elements.feedbackTimerFill.style.width = `${pct}%`;
}

function toggleFeedbackAdvancePause() {
  state.isFeedbackAdvancePaused = !state.isFeedbackAdvancePaused;
  elements.feedbackPauseBtn.textContent = state.isFeedbackAdvancePaused ? "Resume Timer" : "Pause Timer";
}

function cancelFeedbackAdvance() {
  clearInterval(state.feedbackAdvanceInterval);
  state.feedbackAdvanceInterval = null;
  state.activeAdvanceCallback = null;
}

function advanceToNextQuestion() {
  cancelFeedbackAdvance();
  updateActivityStatus("preparing_question", "Preparing next adaptive question...");
  if (state.cachedNextData && state.cachedNextData.next_question_details) {
    renderQuestion(state.cachedNextData.next_question_details);
  } else if (state.cachedNextData && state.cachedNextData.is_complete) {
    loadFinalReport();
  }
}

async function endInterviewEarly() {
  if (!confirm("Are you sure you want to end the interview early? A final report will be generated for your completed answers.")) {
    return;
  }

  cancelAutoEvalCountdown();
  cancelFeedbackAdvance();

  try {
    const res = await fetch(`${API_BASE}/api/interview/${state.sessionId}/end`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ status: "ended_early" }),
    });

    if (res.ok) {
      loadFinalReport();
    }
  } catch (err) {
    alert(`Could not end interview: ${err.message}`);
  }
}

// =============================================================================
// SCREEN 4: PERFORMANCE & INTELLIGENCE REPORT
// =============================================================================

async function loadFinalReport() {
  cancelAutoEvalCountdown();
  cancelFeedbackAdvance();
  updateActivityStatus("interview_completed", "Assessment completed. Report ready.");

  try {
    const res = await fetch(`${API_BASE}/api/interview/${state.sessionId}/report`);
    if (!res.ok) throw new Error("Failed to fetch final report.");

    const report = await res.json();
    renderFinalReport(report);
    showView("report");
  } catch (err) {
    alert(`Error loading report: ${err.message}`);
  }
}

function renderFinalReport(report) {
  // Score out of 100
  const normalized = Math.round(report.normalized_score !== undefined ? report.normalized_score : 0);
  elements.reportNormalizedScore.textContent = normalized;

  // Grade badge & headline
  elements.reportRoleBadge.textContent = state.targetRole || report.role || "Technical Assessment";
  let grade = "Proficient";
  if (normalized >= 85) grade = "Distinction (Senior / Advanced)";
  else if (normalized >= 70) grade = "Proficient (Intermediate)";
  else if (normalized >= 50) grade = "Developing (Foundational)";
  else grade = "Needs Improvement";

  elements.reportGradeBadge.textContent = grade;
  elements.reportHeadline.textContent = `Assessment Completed: ${normalized}/100`;
  elements.reportMetaText.textContent =
    `Completed ${report.questions_completed} questions • Total marks obtained: ${report.total_marks_obtained.toFixed(1)} / ${report.total_max_marks.toFixed(1)}`;

  // Topic Performance
  elements.reportTopicBreakdown.innerHTML = "";
  if (report.topic_scores) {
    Object.entries(report.topic_scores).forEach(([topic, scores]) => {
      const pct = Math.round(scores.percentage || 0);
      const earned = (scores.earned !== undefined ? scores.earned : (scores.awarded || 0)).toFixed(1);
      const maxVal = (scores.max || 0).toFixed(1);
      const row = document.createElement("div");
      row.className = "breakdown-row";
      row.innerHTML = `
        <span class="breakdown-name">${topic}</span>
        <div class="breakdown-bar-col">
          <div class="progress-bar-track">
            <div class="progress-bar-fill" style="width: ${pct}%;"></div>
          </div>
        </div>
        <span class="breakdown-val">${earned} / ${maxVal} (${pct}%)</span>
      `;
      elements.reportTopicBreakdown.appendChild(row);
    });
  }

  // Difficulty Performance
  elements.reportDifficultyBreakdown.innerHTML = "";
  if (report.difficulty_scores) {
    Object.entries(report.difficulty_scores).forEach(([diff, scores]) => {
      const pct = Math.round(scores.percentage || 0);
      const earned = (scores.earned !== undefined ? scores.earned : (scores.awarded || 0)).toFixed(1);
      const maxVal = (scores.max || 0).toFixed(1);
      const row = document.createElement("div");
      row.className = "breakdown-row";
      row.innerHTML = `
        <span class="breakdown-name">${diff.toUpperCase()}</span>
        <div class="breakdown-bar-col">
          <div class="progress-bar-track">
            <div class="progress-bar-fill" style="width: ${pct}%;"></div>
          </div>
        </div>
        <span class="breakdown-val">${earned} / ${maxVal} (${pct}%)</span>
      `;
      elements.reportDifficultyBreakdown.appendChild(row);
    });
  }

  // Strengths & Weaknesses
  elements.reportStrongCompetencies.innerHTML = "";
  (report.strong_competencies || []).forEach((c) => {
    const tag = document.createElement("span");
    tag.className = "badge badge-success";
    tag.textContent = `✓ ${c}`;
    elements.reportStrongCompetencies.appendChild(tag);
  });

  elements.reportWeakCompetencies.innerHTML = "";
  (report.weak_competencies || []).forEach((c) => {
    const tag = document.createElement("span");
    tag.className = "badge badge-danger";
    tag.textContent = `! ${c}`;
    elements.reportWeakCompetencies.appendChild(tag);
  });

  // Recommendations
  elements.reportRecommendations.innerHTML = "";
  (report.recommendations || []).forEach((r) => {
    const li = document.createElement("li");
    li.textContent = r;
    elements.reportRecommendations.appendChild(li);
  });

  elements.reportStudyTopics.innerHTML = "";
  (report.suggested_study_topics || []).forEach((t) => {
    const tag = document.createElement("span");
    tag.className = "skill-chip";
    tag.textContent = t;
    elements.reportStudyTopics.appendChild(tag);
  });

  // Skill Gap Intelligence Card
  if (report.resume_skill_gap) {
    elements.reportSkillGapCard.style.display = "block";
    const gap = report.resume_skill_gap;
    elements.reportGapSummaryText.textContent = gap.gap_summary || "";

    elements.reportSkillGapGrid.innerHTML = `
      <div class="gap-col">
        <h4 class="gap-title text-success">Demonstrated Skills (${gap.demonstrated_skills ? gap.demonstrated_skills.length : 0})</h4>
        <div class="gap-chips">
          ${(gap.demonstrated_skills || []).map((s) => `<span class="badge badge-success">✓ ${s.skill || s}</span>`).join("") || '<span class="chip-muted">None verified</span>'}
        </div>
      </div>
      <div class="gap-col">
        <h4 class="gap-title text-warning">Claimed but Unvalidated (${gap.claimed_unvalidated_skills ? gap.claimed_unvalidated_skills.length : 0})</h4>
        <div class="gap-chips">
          ${(gap.claimed_unvalidated_skills || []).map((s) => `<span class="badge badge-warning">? ${s.skill || s}</span>`).join("") || '<span class="chip-muted">None</span>'}
        </div>
      </div>
      <div class="gap-col">
        <h4 class="gap-title text-danger">Assessed - Not Demonstrated (${gap.assessed_not_demonstrated ? gap.assessed_not_demonstrated.length : 0})</h4>
        <div class="gap-chips">
          ${(gap.assessed_not_demonstrated || []).map((s) => `<span class="badge badge-danger">✗ ${s.skill || s}</span>`).join("") || '<span class="chip-muted">None</span>'}
        </div>
      </div>
      <div class="gap-col">
        <h4 class="gap-title text-muted">Unassessed Skills (${gap.unassessed_skills ? gap.unassessed_skills.length : 0})</h4>
        <div class="gap-chips">
          ${(gap.unassessed_skills || []).map((s) => `<span class="badge badge-secondary">${s.skill || s}</span>`).join("") || '<span class="chip-muted">None</span>'}
        </div>
      </div>
    `;
  } else {
    elements.reportSkillGapCard.style.display = "none";
  }

  // Interview Plan Card
  if (report.interview_plan) {
    elements.reportResumePlanCard.style.display = "block";
    elements.reportPlanSummaryText.textContent = report.interview_plan.summary || "";
    elements.reportResumeSkillsChips.innerHTML = "";
    (report.interview_plan.claimed_skills || []).forEach((s) => {
      const chip = document.createElement("span");
      chip.className = "skill-chip";
      chip.textContent = s;
      elements.reportResumeSkillsChips.appendChild(chip);
    });
  } else {
    elements.reportResumePlanCard.style.display = "none";
  }

  // Detailed History Accordion
  elements.reportHistoryAccordion.innerHTML = "";
  if (report.history && report.history.length > 0) {
    report.history.forEach((h, idx) => {
      const q = h.question || {};
      const ev = h.evaluation || {};
      const item = document.createElement("details");
      item.className = "history-item";
      item.innerHTML = `
        <summary class="history-summary">
          <span>Q${h.question_number || idx + 1}: ${q.text ? q.text.substring(0, 70) : "Question"}...</span>
          <span class="badge badge-primary">${ev.awarded_marks ? ev.awarded_marks.toFixed(1) : 0} / ${ev.max_marks ? ev.max_marks.toFixed(1) : 5} pts</span>
        </summary>
        <div class="history-content">
          <p><strong>Topic:</strong> ${q.topic || ""}</p>
          <p><strong>Candidate Answer:</strong></p>
          <pre><code>${h.candidate_answer || ""}</code></pre>
          <p><strong>Examiner Feedback:</strong> ${ev.summary_explanation || ""}</p>
        </div>
      `;
      elements.reportHistoryAccordion.appendChild(item);
    });
  }
}

function restartAssessment() {
  state.selectedFile = null;
  state.targetRole = "";
  state.resumeId = null;
  state.resumeProfile = null;
  state.interviewPlan = null;
  state.sessionId = null;
  state.currentQuestion = null;

  elements.initialResumeFile.value = "";
  elements.initialTargetRole.value = "";
  updateUploadUI();
  showView("upload");
}

// =============================================================================
// SYSTEM HEALTH CHECKS
// =============================================================================

async function checkSystemHealth() {
  try {
    const res = await fetch(`${API_BASE}/api/health`);
    if (res.ok) {
      const data = await res.json();
      if (data.ollama === "connected") {
        elements.ollamaStatus.innerHTML = '<span class="status-dot dot-online"></span> Ollama Live';
      } else {
        elements.ollamaStatus.innerHTML = '<span class="status-dot dot-offline"></span> Ollama Offline';
      }
    }
  } catch (e) {
    elements.ollamaStatus.innerHTML = '<span class="status-dot dot-offline"></span> API Error';
  }

  try {
    const sRes = await fetch(`${API_BASE}/api/speech/status`);
    if (sRes.ok) {
      const sData = await sRes.json();
      if (sData.tts_available && sData.stt_available) {
        elements.voiceStatus.innerHTML = '<span class="status-dot dot-online"></span> Voice Ready (TTS & STT)';
      } else {
        elements.voiceStatus.innerHTML = '<span class="status-dot dot-online"></span> Voice Active';
      }
    }
  } catch (e) {
    elements.voiceStatus.innerHTML = '<span class="status-dot dot-offline"></span> Voice Offline';
  }
}

// =============================================================================
// INITIALIZATION
// =============================================================================

document.addEventListener("DOMContentLoaded", () => {
  setupUploadEvents();
  setupSettingsEvents();
  setupSpeechEvents();
  checkSystemHealth();
  updateUploadUI();
  showView("upload");
});
