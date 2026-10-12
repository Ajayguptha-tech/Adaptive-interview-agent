"""
Data models for the Adaptive Python Interviewer.
Covers question banks, rubrics, evaluations, sessions, and reports.
"""

from enum import Enum
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field


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
        resp_type = (
            "code_writing" if self.question_type == QuestionType.CODE_WRITING
            else "debugging" if self.question_type == QuestionType.DEBUGGING
            else "code_output" if self.question_type == QuestionType.CODE_OUTPUT
            else "verbal"
        )
        req_code = self.question_type in (QuestionType.CODE_WRITING, QuestionType.DEBUGGING)

        return QuestionDisplay(
            question_number=question_number,
            total_questions=total_questions,
            id=self.id,
            topic=self.topic,
            competency=self.competency,
            difficulty=self.difficulty,
            question_type=self.question_type,
            response_type=getattr(self, "response_type", None) or resp_type,
            requires_code=getattr(self, "requires_code", None) if hasattr(self, "requires_code") else req_code,
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
    target_role: Optional[str] = None
    interview_mode: str = "mock"  # "mock" (dynamic) or "predefined"
    max_questions: int = Field(default=5, ge=1, le=25)
    difficulty_mode: InterviewMode = InterviewMode.ADAPTIVE
    tech_stack: Optional[str] = None


class StartInterviewRequest(BaseModel):
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


class AnswerRequest(BaseModel):
    answer: str


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
    history: List[Dict[str, Any]]
    note: str
