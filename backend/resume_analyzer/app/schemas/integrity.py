"""Schemas for Resume Completeness and Integrity Detection Agent."""
from typing import List, Optional, Literal
from pydantic import BaseModel, Field


SectionStatus = Literal["complete", "partial", "missing"]
OverallCompletenessStatus = Literal["complete", "partially_complete", "incomplete"]


class SectionCompletenessItem(BaseModel):
    section_key: str = Field(..., description="Machine-readable section key e.g. contact, education, experience, skills, projects, summary")
    section_name: str = Field(..., description="Human-readable section title")
    status: SectionStatus = Field(..., description="complete | partial | missing")
    is_core: bool = Field(default=True, description="True if essential for all candidates; False if bonus/recommended")
    content_count: int = Field(default=0, description="Count of identified items, bullets, or distinct entries")
    explanation: str = Field(default="", description="Objective description of what was found or missing")
    recommendation: Optional[str] = Field(default=None, description="Actionable suggestion to resolve gaps")


class IntegrityIssue(BaseModel):
    id: str
    category: str = Field(
        ...,
        description="completeness | formatting | timeline | placeholder | contact | integrity",
    )
    severity: str = Field(
        ...,
        description="info | warning | caution",
    )
    title: str
    explanation: str
    evidence_snippet: Optional[str] = None


class IntegrityAuditResult(BaseModel):
    # Overall Completeness Status
    status: OverallCompletenessStatus = Field(
        default="complete",
        description="complete | partially_complete | incomplete",
    )
    completeness_score: float = Field(..., ge=0, le=100, description="Overall completeness score from 0 to 100")
    explanation: str = Field(
        default="",
        description="Clear summary of why this completeness status was assigned",
    )
    present_sections: List[str] = Field(
        default_factory=list,
        description="List of sections with verified meaningful content",
    )
    partial_sections: List[str] = Field(
        default_factory=list,
        description="List of partially completed sections needing elaboration",
    )
    missing_sections: List[str] = Field(
        default_factory=list,
        description="List of missing core or recommended sections",
    )
    section_details: List[SectionCompletenessItem] = Field(
        default_factory=list,
        description="Detailed section-by-section audit with status, explanations, and recommendations",
    )
    recommendations: List[str] = Field(
        default_factory=list,
        description="Actionable steps to fix incomplete or missing sections",
    )

    # Legacy / Additional Status & Diagnostics
    integrity_status: str = Field(
        default="passed",
        description="passed | advisory | attention_needed",
    )
    total_issues: int = 0
    cautions_count: int = 0
    warnings_count: int = 0
    info_count: int = 0
    issues: List[IntegrityIssue] = Field(default_factory=list)
    detected_sections: List[str] = Field(
        default_factory=list,
        description="Raw sections detected in text layout",
    )
    timeline_summary: str = "Standard chronological career timeline."
    disclaimer: str = Field(
        default=(
            "Advisory Notice: This audit checks for document completeness, layout structure, date consistency, "
            "and template placeholders. It distinguishes incomplete information from potential integrity concerns. "
            "A missing section or unusual timeline does not imply dishonesty or fraudulent intent. "
            "ResumeIQ does not claim a resume is authentic or unauthentic without independent human verification."
        )
    )
