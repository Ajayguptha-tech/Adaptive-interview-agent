"""
Data models for Resume Intelligence & Adaptive Question Generation Agent.
Defines schemas for resume evidence, interview blueprints, question formats,
candidates, validation results, and question catalog entries.
"""

from enum import Enum
from typing import Dict, List, Optional, Any, Set
from pydantic import BaseModel, Field
import uuid

from backend.models import (
    DifficultyLevel,
    InterviewMode,
    Question,
    QuestionType,
    RubricCriterion,
)


class QuestionFormat(str, Enum):
    """The 12 comprehensive question formats supported by the agent."""
    TECHNICAL_FUNDAMENTALS = "technical_fundamentals"
    CONCEPTUAL_EXPLANATION = "conceptual_explanation"
    PRACTICAL_IMPLEMENTATION = "practical_implementation"
    CODE_WRITING = "code_writing"
    CODE_DEBUGGING = "code_debugging"
    OUTPUT_PREDICTION = "output_prediction"
    DESIGN_ARCHITECTURE = "design_architecture"
    PROJECT_DEEP_DIVE = "project_deep_dive"
    TROUBLESHOOTING_SCENARIO = "troubleshooting_scenario"
    TRADEOFF_DECISION = "tradeoff_decision"
    APPLIED_REAL_WORLD = "applied_real_world"
    ADAPTIVE_FOLLOW_UP = "adaptive_follow_up"


# Mapping from agent question format to existing system QuestionType for backward compatibility
FORMAT_TO_QUESTION_TYPE: Dict[QuestionFormat, QuestionType] = {
    QuestionFormat.TECHNICAL_FUNDAMENTALS: QuestionType.CONCEPTUAL,
    QuestionFormat.CONCEPTUAL_EXPLANATION: QuestionType.CONCEPTUAL,
    QuestionFormat.PRACTICAL_IMPLEMENTATION: QuestionType.PRACTICAL,
    QuestionFormat.CODE_WRITING: QuestionType.CODE_WRITING,
    QuestionFormat.CODE_DEBUGGING: QuestionType.DEBUGGING,
    QuestionFormat.OUTPUT_PREDICTION: QuestionType.CODE_OUTPUT,
    QuestionFormat.DESIGN_ARCHITECTURE: QuestionType.SCENARIO,
    QuestionFormat.PROJECT_DEEP_DIVE: QuestionType.SCENARIO,
    QuestionFormat.TROUBLESHOOTING_SCENARIO: QuestionType.DEBUGGING,
    QuestionFormat.TRADEOFF_DECISION: QuestionType.PRACTICAL,
    QuestionFormat.APPLIED_REAL_WORLD: QuestionType.PRACTICAL,
    QuestionFormat.ADAPTIVE_FOLLOW_UP: QuestionType.FOLLOW_UP,
}


class ProjectEvidence(BaseModel):
    """Structured evidence of a project claimed on a resume."""
    title: str
    description: Optional[str] = None
    technologies: List[str] = Field(default_factory=list)
    objectives: Optional[str] = None
    responsibilities: List[str] = Field(default_factory=list)
    challenges: Optional[str] = None
    evidence_snippet: Optional[str] = None
    is_verified: bool = False  # False = claimed on resume; True = verified via interview evaluation


class ResumeIntelligenceProfile(BaseModel):
    """Grounded resume profile isolating claims, evidence, and projects."""
    candidate_name: str = "Candidate"
    total_experience_years: float = 0.0
    programming_languages: List[str] = Field(default_factory=list)
    frameworks: List[str] = Field(default_factory=list)
    tools_platforms: List[str] = Field(default_factory=list)
    verified_skills: List[str] = Field(default_factory=list)
    unverified_claims: List[str] = Field(default_factory=list)
    projects: List[ProjectEvidence] = Field(default_factory=list)
    coursework_and_certs: List[str] = Field(default_factory=list)
    summary: str = ""
    raw_text_safe: str = ""  # Sanitized, injection-safe resume excerpt


class InterviewBlueprint(BaseModel):
    """Candidate-specific interview plan defining coverage, formats, and history."""
    blueprint_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    candidate_id: Optional[str] = None
    target_role: str = "Python Developer"
    interview_mode: str = "mock"  # "mock" (practice/dynamic) or "main" (rigorous evaluation)
    difficulty_mode: str = "adaptive"
    target_track: str = "python"  # "python" or "fullstack"
    tech_stack: Optional[str] = None
    max_questions: int = Field(default=5, ge=5, le=10)
    resume_profile: Optional[ResumeIntelligenceProfile] = None
    required_job_skills: List[str] = Field(default_factory=list)
    investigate_projects: List[ProjectEvidence] = Field(default_factory=list)
    planned_topics: List[str] = Field(default_factory=list)
    planned_formats: List[QuestionFormat] = Field(default_factory=list)
    difficulty_progression: List[DifficultyLevel] = Field(default_factory=list)
    session_asked_fingerprints: List[str] = Field(default_factory=list)
    prior_candidate_fingerprints: List[str] = Field(default_factory=list)
    summary: str = ""


class ValidationResult(BaseModel):
    """Validation outcome for a generated question."""
    is_valid: bool = True
    rubric_valid: bool = True
    grounding_valid: bool = True
    role_relevant: bool = True
    uniqueness_score: float = 1.0  # 1.0 = completely unique, 0.0 = exact duplicate
    relevance_score: float = 1.0
    issues: List[str] = Field(default_factory=list)


class QuestionCandidate(BaseModel):
    """Encapsulates a generated or catalog question with metadata."""
    question: Question
    format: QuestionFormat = QuestionFormat.CONCEPTUAL_EXPLANATION
    target_project: Optional[str] = None
    source_type: str = "model_generated"  # "model_generated" | "catalog_curated" | "adaptive_follow_up"
    validation: ValidationResult = Field(default_factory=ValidationResult)
    generation_latency_ms: float = 0.0
    attempt_number: int = 1
    # Detailed timing instrumentation
    profile_prep_ms: float = 0.0
    blueprint_prep_ms: float = 0.0
    queue_wait_ms: float = 0.0
    prompt_eval_ms: float = 0.0
    token_gen_ms: float = 0.0
    output_parse_ms: float = 0.0
    validation_ms: float = 0.0
    duplicate_check_ms: float = 0.0
    tokens_per_second: float = 0.0
    eval_token_count: int = 0


class CatalogQuestionEntry(BaseModel):
    """Metadata-rich question record stored in reusable question catalog."""
    id: str
    role: str
    track: str  # "python" or "fullstack"
    technology: str
    skill: str
    subtopic: str
    topic: str
    difficulty: DifficultyLevel
    question_format: QuestionFormat
    resume_relevance_keywords: List[str] = Field(default_factory=list)
    question: Question
    source_type: str = "curated"  # "curated" or "model_generated"
    validation_status: str = "validated"
    usage_count: int = 0
    last_used_timestamp: float = 0.0
    fingerprint: str = ""
