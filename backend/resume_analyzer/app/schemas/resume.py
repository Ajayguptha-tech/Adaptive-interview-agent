"""Resume parsing and candidate understanding schemas."""
from typing import List, Optional
from pydantic import BaseModel, Field


class ContactInfo(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    linkedin: Optional[str] = None
    github: Optional[str] = None
    website: Optional[str] = None
    location: Optional[str] = None


class EducationItem(BaseModel):
    degree: Optional[str] = None
    institution: Optional[str] = None
    field_of_study: Optional[str] = None
    graduation_year: Optional[str] = None
    gpa: Optional[str] = None
    honors: Optional[str] = None
    raw_text: Optional[str] = None


class WorkExperienceItem(BaseModel):
    job_title: Optional[str] = None
    company: Optional[str] = None
    dates: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    years_calculated: Optional[float] = 0.0
    responsibilities: List[str] = Field(default_factory=list)
    inferred_skills: List[str] = Field(default_factory=list)
    raw_text: Optional[str] = None


class ProjectItem(BaseModel):
    title: str
    description: Optional[str] = None
    technologies: List[str] = Field(default_factory=list)
    link: Optional[str] = None
    inferred_skills: List[str] = Field(default_factory=list)
    evidence_snippet: Optional[str] = None


class CertificationItem(BaseModel):
    name: str
    issuer: Optional[str] = None
    year: Optional[str] = None


class AchievementItem(BaseModel):
    title: str
    description: Optional[str] = None
    year: Optional[str] = None
    evidence_snippet: Optional[str] = None


class LanguageItem(BaseModel):
    language: str
    proficiency: Optional[str] = None  # e.g., Native, Fluent, Professional, Intermediate, Basic


class SkillEvidenceItem(BaseModel):
    name: str
    category: str = "General"
    source: str = "explicit"  # "explicit" | "experience" | "project" | "summary"
    is_explicit: bool = True
    evidence_snippet: Optional[str] = None
    confidence: float = 1.0


class ResumeParsedData(BaseModel):
    raw_text: str
    normalized_text: str
    file_name: Optional[str] = "Uploaded_Resume"
    file_type: Optional[str] = "unknown"
    word_count: int = 0
    character_count: int = 0
    contact_info: ContactInfo = Field(default_factory=ContactInfo)
    summary: Optional[str] = None
    # Backward compatible flat skills list
    skills: List[str] = Field(default_factory=list)
    # Distinct explicit vs inferred skill representation
    explicit_skills: List[str] = Field(default_factory=list)
    inferred_skills: List[SkillEvidenceItem] = Field(default_factory=list)
    all_skills_detailed: List[SkillEvidenceItem] = Field(default_factory=list)
    experience: List[WorkExperienceItem] = Field(default_factory=list)
    education: List[EducationItem] = Field(default_factory=list)
    projects: List[ProjectItem] = Field(default_factory=list)
    certifications: List[CertificationItem] = Field(default_factory=list)
    achievements: List[AchievementItem] = Field(default_factory=list)
    languages: List[LanguageItem] = Field(default_factory=list)
    detected_sections: List[str] = Field(default_factory=list)
    missing_sections: List[str] = Field(default_factory=list)
    is_scanned_pdf: bool = False
    warning_message: Optional[str] = None


class ExtractionResponse(BaseModel):
    success: bool
    file_name: str
    file_size_bytes: int
    char_count: int
    word_count: int
    extracted_text: str
    is_scanned_pdf: bool = False
    warning: Optional[str] = None
    preview_snippet: str
