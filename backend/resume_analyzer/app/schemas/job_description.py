"""Job description schemas."""
from typing import List, Optional
from pydantic import BaseModel, Field


class JobDescriptionInput(BaseModel):
    title: str = Field(..., min_length=2, max_length=150, description="Target job title")
    company: Optional[str] = Field(None, max_length=150, description="Hiring company")
    description: str = Field(..., min_length=30, description="Full job description text")
    required_skills: Optional[List[str]] = Field(default_factory=list, description="Explicit required skills if provided")
    preferred_skills: Optional[List[str]] = Field(default_factory=list, description="Explicit preferred skills if provided")
    experience_level: Optional[str] = Field("Mid", description="Entry, Mid, Senior, Lead, Executive")


class JobDescriptionParsed(BaseModel):
    title: str
    company: Optional[str] = None
    experience_level: Optional[str] = None
    min_years_experience: float = 0.0
    required_skills: List[str] = Field(default_factory=list)
    preferred_skills: List[str] = Field(default_factory=list)
    key_responsibilities: List[str] = Field(default_factory=list)
    education_requirements: List[str] = Field(default_factory=list)
    extracted_keywords: List[str] = Field(default_factory=list)
    normalized_text: str
