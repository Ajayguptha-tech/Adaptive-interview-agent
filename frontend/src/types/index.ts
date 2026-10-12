// Adaptive Interview Intelligence Core TypeScript Definitions
// Built for FastAPI Backend Integration (Problem Statement 3: Adaptive Interview Intelligence)

export type CompetencyCategory = 'technical' | 'communication' | 'behavioral' | 'role_specific';

export type SkillClassification = 
  | 'demonstrated' 
  | 'claimed_needs_validation' 
  | 'not_assessed' 
  | 'skill_gap';

export type QuestionDifficulty = 'foundational' | 'intermediate' | 'advanced';

export type IntegritySeverity = 'advisory' | 'low' | 'medium' | 'high';

export type IntegrityStatus = 
  | 'pending_review' 
  | 'verified_benign' 
  | 'verified_technical' 
  | 'requires_followup';

export type RecommendationOutcome = 
  | 'proceed_to_human_review' 
  | 'request_follow_up' 
  | 'insufficient_evidence';

export type InterviewStatus = 'scheduled' | 'in_progress' | 'paused' | 'completed' | 'reviewed';

export interface Resume {
  id: string;
  candidateId: string;
  fileName?: string;
  fileSize?: number;
  uploadedAt: string;
  parsedSummary?: string;
  extractedSkills: string[];
  experienceYears?: number;
  education?: string[];
  rawText?: string;
}

export interface Candidate {
  id: string;
  name: string;
  email?: string;
  role: string;
  experienceYears?: number;
  location?: string;
  avatarUrl?: string;
  headline?: string;
  resumeId?: string;
  resume?: Resume;
  status: InterviewStatus;
  createdAt: string;
  updatedAt?: string;
}

export interface JobRole {
  id: string;
  title: string;
  department: string;
  level: string;
  description: string;
  requiredCompetencies: string[];
  niceToHaveCompetencies: string[];
  createdAt?: string;
}

export interface Competency {
  id: string;
  name: string;
  category: CompetencyCategory;
  score?: number | null;        // 0 - 100, null if unassessed
  confidence?: number | null;   // 0 - 100, null if unassessed
  evidenceCount: number;
  description?: string;
  classification?: SkillClassification;
}

export interface Evidence {
  id: string;
  interviewId: string;
  questionId?: string;
  timestamp: string;            // e.g. "14:22" or ISO string
  quote: string;
  competencyId: string;
  competencyName: string;
  scoreImpact?: number;         // e.g. +8, -3
  confidenceImpact?: number;    // e.g. +14
  rationale: string;
  signalStrength: 'high' | 'medium' | 'contextual';
}

export interface InterviewQuestion {
  id: string;
  interviewId?: string;
  order: number;
  text: string;
  category: CompetencyCategory;
  targetCompetencies: string[];
  difficulty: QuestionDifficulty;
  whyThisQuestion?: {
    contextAnalysis?: string;
    gapDetected?: string;
    difficultyReason?: string;
    timeBalanceReason?: string;
  };
}

export interface InterviewAnswer {
  id: string;
  questionId: string;
  interviewId: string;
  transcriptText: string;
  audioDurationSeconds?: number;
  timestamp: string;
  extractedEvidenceIds?: string[];
}

export interface IntegrityEvent {
  id: string;
  interviewId: string;
  timestampSeconds: number;
  timestampFormatted: string;   // e.g. "04:12"
  type: 'audio_fluctuation' | 'inactivity_window' | 'multiple_voices' | 'gaze_shift' | 'focus_loss';
  title: string;
  description: string;
  severity: IntegritySeverity;
  confidence: number;           // 0 - 100
  recruiterStatus: IntegrityStatus;
  recruiterNotes?: string;
}

export interface Interview {
  id: string;
  candidateId: string;
  jobRoleId: string;
  status: InterviewStatus;
  startedAt?: string;
  completedAt?: string;
  currentQuestionId?: string;
  timeRemainingSeconds?: number;
  overallScore?: number | null;
  overallConfidence?: number | null;
}

export interface CandidateReport {
  id: string;
  candidateId: string;
  jobRoleId: string;
  interviewId: string;
  alignmentScore?: number | null;
  overallConfidence?: number | null;
  evidencePointsTotal: number;
  durationMinutes?: number | null;
  outcome?: RecommendationOutcome | null;
  executiveSummary?: string;
  verifiedStrengths?: {
    skill: string;
    score: number;
    evidence: string;
  }[];
  criticalGaps?: {
    skill: string;
    gapType: string;
    notes: string;
  }[];
  unvalidatedClaims?: string[];
  suggestedFollowUpQuestions?: string[];
  integritySummary?: {
    totalEvents: number;
    reviewedCount: number;
    statusSummary: string;
  };
  recruiterSignoff?: {
    reviewedBy: string;
    decisionDate: string;
    recruiterNotes: string;
  };
}

// -------------------------------------------------------------
// Extended Agent Contracts & Evaluation Specifications
// -------------------------------------------------------------

export interface RubricCriterion {
  id: string;
  competencyId: string;
  name: string;
  description: string;
  weight: number; // 0.0 - 1.0
  indicators: {
    inadequate: string;
    proficient: string;
    exceptional: string;
  };
}

export interface EvaluationRubric {
  id: string;
  roleId: string;
  criteria: RubricCriterion[];
}

export interface InterviewPlan {
  id: string;
  candidateId: string;
  roleId: string;
  roleTitle: string;
  department: string;
  seniority: string;
  targetDurationMinutes: number;
  competencies: Competency[];
  rubric: EvaluationRubric;
  initialQuestions: InterviewQuestion[];
  preInterviewSkillGaps: string[];
  resumeClaims: string[];
  createdAt: string;
}

export interface EvaluationResult {
  questionId: string;
  transcriptText: string;
  overallScore: number;         // 0 - 100
  confidenceScore: number;      // 0 - 100
  extractedEvidence: Evidence[];
  missingInformation: string[];
  unaddressedCompetencies: string[];
  demonstratedCompetencies: string[];
  rubricFeedback: string;
  evaluatedAt: string;
}

export interface AdaptiveRoutingDecision {
  nextQuestion: InterviewQuestion;
  targetCompetencyName: string;
  reasoning: string;
  triggerType: 'gap_followup' | 'depth_escalation' | 'breadth_exploration' | 'calibration';
}

export type AgentName = 
  | 'planner' 
  | 'interviewer' 
  | 'evaluator' 
  | 'integrity' 
  | 'decision';

export interface AgentLogEntry {
  id: string;
  agent: AgentName;
  timestamp: string;
  action: string;
  details: string;
  level: 'info' | 'decision' | 'warning';
}

export interface CandidateSetupInput {
  candidateName: string;
  candidateEmail: string;
  roleTitle: string;
  department: string;
  experienceLevel: string;
  jobDescription: string;
  resumeFileName?: string;
  resumeText?: string;
  sessionDurationMinutes: number;
  adaptiveSensitivity: 'standard' | 'high';
}

export type AudioRecordingStatus = 
  | 'idle' 
  | 'requesting_permission' 
  | 'recording' 
  | 'paused' 
  | 'stopped' 
  | 'permission_denied' 
  | 'unsupported';

// -------------------------------------------------------------
// FastAPI Backend Integration Contracts (Adaptive Interview Intelligence)
// -------------------------------------------------------------

export interface BackendRoleEligibility {
  outcome: 'eligible' | 'potentially_eligible' | 'not_currently_eligible';
  target_role: string;
  prerequisites_met: boolean;
  competencies_found: string[];
  missing_competencies: string[];
  reasons: string[];
}

export interface BackendIntegrityReport {
  outcome: 'no_inconsistencies' | 'potential_inconsistencies' | 'strong_concerns' | 'insufficient_evidence';
  risk_score: number;
  risk_factors: string[];
  positive_indicators: string[];
  summary: string;
}

export interface BackendResumeUploadResponse {
  status: string;
  resume_id: string;
  candidate_name: string;
  target_role: string;
  routed_track: string;
  specialization_mode?: string;
  experience_years: number;
  extracted_skills: string[];
  ats_score: number;
  integrity_report?: BackendIntegrityReport;
  role_eligibility?: BackendRoleEligibility;
}

export interface BackendQuestion {
  question_id: string;
  question_number: number;
  text: string;
  type: 'conceptual' | 'code_writing' | 'code_output' | 'practical';
  difficulty: string;
  max_marks: number;
  code_snippet?: string;
  expected_answer_format: 'verbal' | 'code';
  topic?: string;
}

export interface BackendRubricItem {
  criterion: string;
  marks_awarded: number;
  max_marks: number;
  reason: string;
}

export interface BackendAnswerResponse {
  marks_awarded: number;
  max_marks: number;
  percentage: number;
  rubric_breakdown: BackendRubricItem[];
  feedback: string;
  misconceptions: string[];
  next_question?: BackendQuestion | null;
  is_complete: boolean;
}

export interface BackendFinalReport {
  session_id: string;
  total_score: number;
  max_possible: number;
  normalized_score: number;
  grade: string;
  questions: {
    question_id: string;
    question_number: number;
    text: string;
    type: string;
    difficulty: string;
    candidate_answer: string;
    score: number;
    max_marks: number;
    feedback: string;
    model_answer?: string;
    mistakes?: string[];
  }[];
  topics_breakdown: Record<string, { earned: number; possible: number; percentage: number }>;
  difficulty_breakdown: Record<string, { earned: number; possible: number; percentage: number }>;
  demonstrated_skills: string[];
  unassessed_skills: string[];
  weak_skills: string[];
  claimed_unvalidated_skills: string[];
  recommendations: string[];
  integrity_audit?: BackendIntegrityReport;
  role_eligibility?: BackendRoleEligibility;
}

