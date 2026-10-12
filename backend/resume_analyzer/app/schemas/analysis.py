"""Analysis, skills matching, scoring, and response schemas."""
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from .resume import ResumeParsedData
from .job_description import JobDescriptionInput, JobDescriptionParsed
from .integrity import IntegrityAuditResult


class SkillMatchItem(BaseModel):
    skill: str
    match_type: str = Field(..., description="exact | alias | missing_required | missing_preferred | candidate_extra")
    matched_resume_term: Optional[str] = None
    confidence: float = 1.0
    category: Optional[str] = "General"
    source: Optional[str] = "explicit"  # "explicit" | "experience" | "project" | "summary"
    evidence_snippet: Optional[str] = None


class SkillsAnalysisResult(BaseModel):
    total_required: int
    total_preferred: int
    matched_required_count: int
    matched_preferred_count: int
    required_match_percentage: float
    preferred_match_percentage: float
    exact_matches: List[str] = Field(default_factory=list)
    alias_matches: List[Dict[str, str]] = Field(default_factory=list, description="list of {requested, found}")
    missing_required: List[str] = Field(default_factory=list)
    missing_preferred: List[str] = Field(default_factory=list)
    candidate_extra_skills: List[str] = Field(default_factory=list)
    inferred_matches: List[str] = Field(default_factory=list)
    all_match_items: List[SkillMatchItem] = Field(default_factory=list)


class CategoryScore(BaseModel):
    category_key: str
    category_name: str
    raw_score: float = Field(..., ge=0, le=100)
    weight: float = Field(..., ge=0, le=1.0)
    weighted_score: float = Field(..., ge=0, le=100)
    explanation: str
    evidence: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)


class ScoringBreakdown(BaseModel):
    overall_score: float = Field(..., ge=0, le=100)
    categories: Dict[str, CategoryScore]
    weights: Dict[str, float]
    methodology_notes: List[str] = Field(default_factory=list)
    disclaimer: str = (
        "This score is an estimate calculated by transparent, deterministic criteria to help you improve your resume. "
        "It does not represent an endorsement from or official scoring by any third-party ATS vendor, "
        "and does not constitute a hiring guarantee or employment decision."
    )


class BulletRewrite(BaseModel):
    original_bullet: str
    rewritten_bullet: str
    reasoning: str
    target_role_or_project: Optional[str] = None


class ResumeImprovementResult(BaseModel):
    strengths: List[str] = Field(default_factory=list)
    critical_improvements: List[str] = Field(default_factory=list)
    bullet_rewrites: List[BulletRewrite] = Field(default_factory=list)
    recruiter_summary: str
    tailored_summary_draft: str
    action_plan: List[str] = Field(default_factory=list)
    is_ai_generated: bool = False
    ai_model_used: Optional[str] = None


class AnalysisCreateRequest(BaseModel):
    resume_text: str = Field(..., min_length=20, description="Extracted resume text")
    file_name: Optional[str] = "Uploaded_Resume.pdf"
    job_description: JobDescriptionInput


class AnalysisSummaryResponse(BaseModel):
    id: str
    created_at: str
    file_name: str
    job_title: str
    company: Optional[str] = None
    overall_score: float
    matched_skills_count: int
    missing_required_count: int
    is_ai_powered: bool = False


class AnalysisDetailResponse(BaseModel):
    id: str
    created_at: str
    file_name: str
    overall_score: float
    resume_data: ResumeParsedData
    job_description: JobDescriptionParsed
    skills_analysis: SkillsAnalysisResult
    scoring_breakdown: ScoringBreakdown
    improvements: ResumeImprovementResult
    integrity_audit: Optional[IntegrityAuditResult] = None


class ChatMessage(BaseModel):
    id: str
    sender: str  # "user" | "assistant"
    content: str
    timestamp: str


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=1500)


class ChatResponse(BaseModel):
    reply: str
    sources_grounded_in: List[str] = Field(default_factory=list)
    is_ai: bool = False


class SystemSettingsResponse(BaseModel):
    ai_provider: str
    ai_configured: bool
    model_name: str
    weights: Dict[str, float]
    max_upload_size_mb: int
    data_retention_policy: str
    privacy_notice: str
