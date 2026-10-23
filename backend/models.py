"""
Data models for the Adaptive Python Interviewer.
Covers question banks, rubrics, evaluations, sessions, and reports.
"""

from enum import Enum
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field, model_validator


class DifficultyLevel(str, Enum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


class QuestionType(str, Enum):
    CONCEPTUAL = "conceptual"
    PRACTICAL = "practical"
    CODE_OUTPUT = "code_output"
    DEBUGGING = "debugging"
    CODE_WRITING = "code_writing"
    FOLLOW_UP = "follow_up"
    SCENARIO = "scenario"


class FeedbackMode(str, Enum):
    IMMEDIATE = "immediate"
    ASSESSMENT = "assessment"


class InterviewMode(str, Enum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    ADAPTIVE = "adaptive"


class RubricCriterion(BaseModel):
    id: str = Field(..., description="Unique criterion identifier for the question")
    description: str = Field(..., description="What concept or behavior this criterion assesses")
    max_marks: float = Field(..., ge=0.5, description="Maximum marks awarded for this criterion")
    evidence_guide: str = Field("", description="Guidance on what constitutes strong vs partial evidence")


class QuestionDisplay(BaseModel):
    question_number: int
    total_questions: int
    id: str
    topic: str
    competency: str
    difficulty: DifficultyLevel
    question_type: QuestionType
    response_type: str = "verbal"  # "verbal", "code_writing", "code_output", "debugging"
    requires_code: bool = False
    text: str
    code_snippet: Optional[str] = None
    max_marks: float
    selection_reason: str
    language: Optional[str] = "python"
    track: Optional[str] = "python"
    starter_code: Optional[str] = None
    expected_output: Optional[str] = None
    db_schema: Optional[str] = None
    target_skills: List[str] = Field(default_factory=list)


class Question(BaseModel):
    id: str
    topic: str
    competency: str
    difficulty: DifficultyLevel
    question_type: QuestionType
    response_type: str = "verbal"
    requires_code: bool = False
    text: str
    code_snippet: Optional[str] = None
    expected_concepts: List[str] = Field(default_factory=list)
    optional_concepts: List[str] = Field(default_factory=list)
    common_misconceptions: List[str] = Field(default_factory=list)
    rubric: List[RubricCriterion] = Field(default_factory=list)
    reference_answer: str = ""
    test_cases: Optional[List[Dict[str, Any]]] = None  # For code execution
    expected_output: Optional[str] = None  # For output prediction questions
    starter_code: Optional[str] = None  # Starter code or function signature
    function_name: Optional[str] = None  # Expected callable function name for automated tests
    follow_up_to: Optional[str] = None  # If this is a follow-up question to another ID
    language: Optional[str] = "python"  # "python", "javascript", "sql", "html", etc.
    track: Optional[str] = "python"  # "python" or "fullstack"
    db_schema: Optional[str] = None  # For SQL questions: schema setup and seed DDL
    target_skills: List[str] = Field(default_factory=list)

    @property
    def total_marks(self) -> float:
        return sum(c.max_marks for c in self.rubric)

    def to_display(
        self,
        reason: str = "",
        question_number: int = 1,
        total_questions: int = 5,
    ) -> QuestionDisplay:
        req_code = bool(self.requires_code or self.question_type in (QuestionType.CODE_WRITING, QuestionType.DEBUGGING))
        if req_code:
            resp_type = "code_writing" if self.question_type == QuestionType.CODE_WRITING else "debugging"
        elif self.question_type == QuestionType.CODE_OUTPUT:
            resp_type = "code_output"
        elif getattr(self, "response_type", None) and self.response_type != "verbal":
            resp_type = self.response_type
        else:
            resp_type = "verbal"

        return QuestionDisplay(
            question_number=question_number,
            total_questions=total_questions,
            id=self.id,
            topic=self.topic,
            competency=self.competency,
            difficulty=self.difficulty,
            question_type=self.question_type,
            response_type=resp_type,
            requires_code=req_code,
            text=self.text,
            code_snippet=self.code_snippet,
            max_marks=self.total_marks,
            selection_reason=reason,
            language=self.language or "python",
            track=self.track or "python",
            starter_code=self.starter_code,
            expected_output=self.expected_output,
            db_schema=self.db_schema,
            target_skills=list(self.target_skills),
        )


class CriterionEvaluation(BaseModel):
    criterion_id: str
    awarded_marks: float
    max_marks: float
    evidence: str
    explanation: str


class EvaluationResult(BaseModel):
    question_id: str
    awarded_marks: float
    max_marks: float
    percentage: float
    criteria_evaluations: List[CriterionEvaluation]
    demonstrated_concepts: List[str] = Field(default_factory=list)
    partial_concepts: List[str] = Field(default_factory=list)
    missing_concepts: List[str] = Field(default_factory=list)
    incorrect_claims: List[str] = Field(default_factory=list)
    summary_explanation: str
    addressed_question: bool = True
    is_ambiguous: bool = False
    clarification_question: Optional[str] = None
    execution_result: Optional[Dict[str, Any]] = None  # Static or isolated run results


class QuestionRecord(BaseModel):
    question_number: int
    question: Question
    candidate_answer: str
    evaluation: EvaluationResult
    selection_reason: str
    timestamp: str
    target_skills: List[str] = Field(default_factory=list)


class PrepareInterviewRequest(BaseModel):
    resume_id: str
    candidate_id: Optional[str] = None
    target_role: Optional[str] = None
    interview_mode: str = "mock"  # "mock" (dynamic) or "predefined"
    max_questions: int = Field(default=5, ge=5, le=10, description="Configured interview length (strictly 5 to 10 questions)")
    difficulty_mode: InterviewMode = InterviewMode.ADAPTIVE
    tech_stack: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def normalize_aliases(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "question_count" in data and "max_questions" not in data:
                data["max_questions"] = data["question_count"]
            if "mode" in data and "interview_mode" not in data:
                data["interview_mode"] = data["mode"]
            if "difficulty" in data and "difficulty_mode" not in data:
                data["difficulty_mode"] = data["difficulty"]
        return data


class StartInterviewRequest(BaseModel):
    candidate_id: Optional[str] = None
    role: str = "Python Developer"
    track: Optional[str] = Field(default=None, description="Optional track: 'python' or 'fullstack'. If omitted, automatically determined from resume.")
    tech_stack: Optional[str] = None  # e.g. "React + Node.js + Express + SQL"
    job_description: str = ""
    resume_summary: str = ""
    competencies: List[str] = Field(default_factory=lambda: [
        "Python fundamentals",
        "Data structures",
        "Object-oriented programming",
        "Advanced Python concepts",
        "Problem solving and debugging",
    ])
    max_questions: int = Field(default=5, ge=1, le=25)
    difficulty_mode: InterviewMode = InterviewMode.ADAPTIVE
    topics: Optional[List[str]] = None
    feedback_mode: FeedbackMode = FeedbackMode.IMMEDIATE
    dynamic_questions: bool = True
    resume_id: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def normalize_aliases(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "target_questions" in data and "max_questions" not in data:
                data["max_questions"] = data["target_questions"]
            elif "question_count" in data and "max_questions" not in data:
                data["max_questions"] = data["question_count"]
            if "difficulty" in data and "difficulty_mode" not in data:
                data["difficulty_mode"] = data["difficulty"]
            if "mode" in data:
                m = str(data["mode"]).lower()
                if m == "predefined":
                    data["dynamic_questions"] = False
                elif m == "mock":
                    data["dynamic_questions"] = True
        return data


class AnswerRequest(BaseModel):
    answer: str
    question_id: Optional[str] = None
    question_number: Optional[int] = None


class EndInterviewRequest(BaseModel):
    status: str = "ended_early"  # "ended_early", "cancelled", "completed"


class AnswerSubmissionResponse(BaseModel):
    session_id: str
    status: str
    question_number: int
    is_complete: bool
    questions_remaining: int
    evaluation: Optional[Dict[str, Any]] = None  # Hidden or concise in assessment mode
    feedback_mode: FeedbackMode
    next_question: Optional[QuestionDisplay] = None
    reason_for_next_question: str = ""


class FinalReport(BaseModel):
    session_id: str
    role: str
    track: str = "python"
    tech_stack: Optional[str] = None
    resume_id: Optional[str] = None
    resume_summary: Optional[Dict[str, Any]] = None
    resume_skill_gap: Optional[Dict[str, Any]] = None
    interview_plan: Optional[Dict[str, Any]] = None
    status: str  # "completed", "ended_early", "cancelled"
    question_mode: str = "Dynamic"  # "Dynamic" or "Predefined"
    created_at: str = ""
    total_marks_obtained: float
    total_max_marks: float
    normalized_score: float  # Out of 100
    questions_completed: int
    questions_unanswered: int = 0
    questions_failed: int = 0
    scoring_denominator: str = "Evaluated questions maximum marks"
    max_questions: int
    difficulty_mode: str
    feedback_mode: str
    topic_scores: Dict[str, Dict[str, Any]]
    difficulty_scores: Dict[str, Dict[str, Any]]
    competency_scores: Dict[str, Dict[str, Any]]
    strong_competencies: List[str]
    weak_competencies: List[str]
    identified_misconceptions: List[str]
    unassessed_topics: List[str]
    recommendations: List[str]
    strongest_demonstrations: List[Dict[str, str]]
    suggested_study_topics: List[str]
    integrity_summary: Optional[Dict[str, Any]] = None
    decision_recommendation: Optional[Dict[str, Any]] = None
    history: List[Dict[str, Any]]
    note: str


class IntegrityEventType(str, Enum):
    FOCUS_LOSS = "focus_loss"
    TAB_SWITCH = "tab_switch"
    WINDOW_BLUR = "window_blur"
    AUDIO_ANOMALY = "audio_anomaly"
    STREAM_INTERRUPTED = "stream_interrupted"
    MANUAL_FLAG = "manual_flag"
    LATENCY_SPIKE = "latency_spike"


class IntegritySeverity(str, Enum):
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class IntegrityReviewStatus(str, Enum):
    PENDING_REVIEW = "pending_review"
    VERIFIED_BENIGN = "verified_benign"
    VERIFIED_TECHNICAL = "verified_technical"
    REQUIRES_FOLLOWUP = "requires_followup"


class IntegrityEventCreateRequest(BaseModel):
    event_type: str = "window_blur"
    severity: str = "info"
    confidence: float = 85.0
    title: str = "Window Focus Transition"
    description: str = "Candidate window temporarily transitioned focus away from interview window."
    timestamp_offset_seconds: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = None


class IntegrityEventRecord(BaseModel):
    id: str
    session_id: str
    candidate_id: Optional[str] = None
    timestamp_offset_seconds: float = 0.0
    timestamp_iso: str = ""
    event_type: str
    severity: str
    confidence: float
    title: str
    description: str
    recruiter_status: str = "pending_review"
    recruiter_notes: Optional[str] = None
    created_at: str = ""


class IntegrityEventUpdateRequest(BaseModel):
    status: str
    notes: Optional[str] = None


class IntegritySummary(BaseModel):
    session_id: str
    total_events: int = 0
    focus_loss_count: int = 0
    tab_switch_count: int = 0
    audio_anomaly_count: int = 0
    stream_interruption_count: int = 0
    manual_flags_count: int = 0
    pending_review_count: int = 0
    verified_benign_count: int = 0
    requires_followup_count: int = 0
    ethical_notice: str = (
        "Telemetry observations represent raw sensory and browser events, never definitive allegations of cheating. "
        "Observations must be evaluated in contextual totality by human hiring panel."
    )


class DecisionOutcome(str, Enum):
    PROCEED_TO_HUMAN_REVIEW = "proceed_to_human_review"
    REQUEST_FOLLOW_UP = "request_follow_up"
    CONSIDER_ALTERNATE_ROLE = "consider_alternate_role"
    NEEDS_FURTHER_EVALUATION = "needs_further_evaluation"


class CandidateDecisionRecord(BaseModel):
    session_id: str
    candidate_id: str
    candidate_name: str
    target_role: str
    track: str
    normalized_score: float
    grade: str
    outcome: str = DecisionOutcome.PROCEED_TO_HUMAN_REVIEW.value
    confidence_score: float = 90.0
    executive_summary: str = ""
    demonstrated_competencies: List[str] = Field(default_factory=list)
    critical_gaps: List[str] = Field(default_factory=list)
    unvalidated_claims: List[str] = Field(default_factory=list)
    prerequisites_satisfied: bool = True
    integrity_review_needed: bool = False
    evidence_points_count: int = 0
    recruiter_outcome_override: Optional[str] = None
    recruiter_notes: Optional[str] = None
    created_at: str = ""
    updated_at: str = ""


class CandidateDecisionUpdateRequest(BaseModel):
    outcome: str
    notes: Optional[str] = None


class CandidateComparisonRequest(BaseModel):
    session_ids: List[str]

