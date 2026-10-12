"""
Resume Authenticity and Integrity Assessment Engine.
Performs evidence-based resume integrity audits distinguishing:
1. No significant inconsistencies detected
2. Potential inconsistencies requiring clarification
3. Strong integrity concerns requiring further verification
4. Unable to assess because insufficient evidence is available

Produces non-defamatory risk indicators with objective explanations and actionable clarification paths.
Never classifies a resume as fraudulent based on formatting, ambitious claims, or absence of external verification.
Does NOT evaluate or discriminate based on protected personal characteristics.
"""

import re
from typing import Dict, Any, List, Optional
from enum import Enum
from pydantic import BaseModel, Field


class IntegrityOutcome(str, Enum):
    NO_INCONSISTENCIES = "no_inconsistencies"
    POTENTIAL_INCONSISTENCIES = "potential_inconsistencies"
    STRONG_CONCERNS = "strong_concerns"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"


class IntegrityRiskIndicator(BaseModel):
    indicator_id: str
    category: str  # "timeline", "skills_vs_projects", "content_repetition", "placeholder", "document_structure"
    severity: str  # "info", "advisory", "review_recommended"
    title: str
    explanation: str
    evidence_snippet: Optional[str] = None
    clarification_prompt: Optional[str] = None


class ResumeIntegrityReport(BaseModel):
    outcome: IntegrityOutcome
    outcome_label: str
    headline: str
    summary_explanation: str
    risk_score: float = Field(default=0.0, ge=0.0, le=100.0, description="0=Clean, 100=Severe concerns")
    indicators: List[IntegrityRiskIndicator] = Field(default_factory=list)
    section_consistency: Dict[str, str] = Field(default_factory=dict)
    clarification_topics: List[str] = Field(default_factory=list)
    caveat_notice: str = (
        "Automated integrity analysis identifies potential document consistency risks and informational gaps. "
        "It does not constitute definitive proof of misrepresentation or fraud. Candidates are provided "
        "opportunities to clarify flagged items during the technical interview."
    )


class ResumeIntegrityAssessor:
    """Evaluates cross-section coherence, timelines, detail sufficiency, and document authenticity."""

    @classmethod
    def audit_profile(
        cls,
        parsed_resume: Any,
        raw_text: str = "",
        filename: str = "resume.pdf",
    ) -> ResumeIntegrityReport:
        indicators: List[IntegrityRiskIndicator] = []
        clarifications: List[str] = []
        section_consistency = {
            "skills_to_projects": "consistent",
            "experience_timeline": "consistent",
            "education_credentials": "consistent",
            "content_originality": "consistent",
        }

        clean_text = (raw_text or "").strip()
        word_count = len(clean_text.split())

        # Check 1: Insufficient Evidence
        if word_count < 60:
            return ResumeIntegrityReport(
                outcome=IntegrityOutcome.INSUFFICIENT_EVIDENCE,
                outcome_label="Unable to assess because insufficient evidence is available",
                headline="Document content too sparse for reliable verification",
                summary_explanation=(
                    f"The submitted document contains only {word_count} words. A comprehensive integrity audit "
                    "requires substantive work experience, technical skills, or project descriptions."
                ),
                risk_score=25.0,
                indicators=[
                    IntegrityRiskIndicator(
                        indicator_id="sparse_content",
                        category="document_structure",
                        severity="advisory",
                        title="Sparse Document Content",
                        explanation=f"Extracted document length ({word_count} words) is below the minimum threshold required for rigorous cross-section validation.",
                        clarification_prompt="Provide a more detailed resume detailing project responsibilities and engineering accomplishments.",
                    )
                ],
                section_consistency={"general": "insufficient_data"},
                clarification_topics=["Provide full project details and professional background during interview."],
            )

        # Check 2: Template Placeholders & Dummy Values
        placeholder_patterns = [
            (r"\[insert\s+[^\]]+\]", "Bracketed placeholder tag (e.g. '[Insert ...]')"),
            (r"\[company\s*name\]", "Template company placeholder '[Company Name]'"),
            (r"\[job\s*title\]", "Template job title placeholder '[Job Title]'"),
            (r"\blorem\s+ipsum\b", "Standard filler text ('Lorem ipsum')"),
            (r"\bdolor\s+sit\s+amet\b", "Standard filler text ('dolor sit amet')"),
            (r"\bTODO:?\b", "Unresolved developer/template note ('TODO')"),
            (r"\bTBD:?\b", "Unspecified placeholder note ('TBD')"),
        ]
        found_placeholders = []
        for pattern, desc in placeholder_patterns:
            matches = re.findall(pattern, clean_text, flags=re.IGNORECASE)
            if matches:
                found_placeholders.append((desc, matches[0]))

        if found_placeholders:
            indicators.append(
                IntegrityRiskIndicator(
                    indicator_id="template_placeholders",
                    category="placeholder",
                    severity="review_recommended",
                    title="Unresolved Template Placeholders Detected",
                    explanation=f"Detected {len(found_placeholders)} template tags in text: {found_placeholders[0][0]}.",
                    evidence_snippet=found_placeholders[0][1],
                    clarification_prompt="Confirm whether template boilerplate was left in the document unintentionally.",
                )
            )
            clarifications.append("Clarify unresolved template tags identified in document text.")
            section_consistency["content_originality"] = "contains_placeholders"

        # Check 3: Skills Claimed vs Project Detail Sufficiency
        skills = getattr(parsed_resume, "skills", []) or []
        projects = getattr(parsed_resume, "projects", []) or []
        experience = getattr(parsed_resume, "experience", []) or []

        # If candidate claims 15+ advanced skills but projects list has 0 projects and no description bullets
        total_project_words = sum(
            len((getattr(p, "description", "") or "").split())
            for p in projects
        )
        total_exp_words = sum(
            len(" ".join(getattr(e, "responsibilities", []) or []).split())
            for e in experience
        )

        if len(skills) >= 12 and (total_project_words + total_exp_words) < 50:
            indicators.append(
                IntegrityRiskIndicator(
                    indicator_id="unsupported_skill_volume",
                    category="skills_vs_projects",
                    severity="advisory",
                    title="Skills Claimed with Limited Contextual Detail",
                    explanation=(
                        f"Resume lists {len(skills)} technical skills, but accompanying work experience "
                        "and project descriptions provide very brief contextual evidence."
                    ),
                    clarification_prompt="Ask the candidate to explain real-world usage and implementation challenges for claimed skills.",
                )
            )
            clarifications.append("Demonstrate practical implementation context for listed skills.")
            section_consistency["skills_to_projects"] = "limited_contextual_evidence"

        # Check 4: Suspiciously Repeated Text / Duplicated Blocks
        paragraphs = [p.strip() for p in clean_text.split("\n\n") if len(p.strip()) > 60]
        repeated_paragraphs = set()
        seen = set()
        for p in paragraphs:
            normalized = re.sub(r"\s+", " ", p.lower())
            if normalized in seen:
                repeated_paragraphs.add(p[:80])
            seen.add(normalized)

        if repeated_paragraphs:
            sample_dup = list(repeated_paragraphs)[0]
            indicators.append(
                IntegrityRiskIndicator(
                    indicator_id="repeated_content",
                    category="content_repetition",
                    severity="advisory",
                    title="Identical Repeated Paragraph Content",
                    explanation="Identified duplicate responsibility or project description blocks repeated in multiple sections.",
                    evidence_snippet=f"{sample_dup}...",
                    clarification_prompt="Verify if identical responsibility text was intentionally copied across roles.",
                )
            )
            clarifications.append("Clarify duplicated bullet points across multiple positions.")
            section_consistency["content_originality"] = "contains_duplicate_blocks"

        # Check 5: Timeline Overlap & Impossible Durations
        # e.g., Dates in future (beyond current year + 1) or overlapping full-time roles
        current_year = 2026
        future_years = re.findall(r"\b(20[3-9]\d)\b", clean_text)
        if any(int(y) > current_year + 1 for y in future_years):
            invalid_y = [y for y in future_years if int(y) > current_year + 1][0]
            indicators.append(
                IntegrityRiskIndicator(
                    indicator_id="implausible_future_date",
                    category="timeline",
                    severity="review_recommended",
                    title="Implausible Calendar Year Mentioned",
                    explanation=f"Resume mentions calendar year {invalid_y}, which is significantly in the future.",
                    evidence_snippet=invalid_y,
                    clarification_prompt="Clarify date typo or anticipated graduation/completion timeline.",
                )
            )
            clarifications.append(f"Confirm timeline accuracy regarding year {invalid_y}.")
            section_consistency["experience_timeline"] = "date_typo_or_future_year"

        # Check 6: Unsubstantiated High-Stakes Certification Claims
        cert_keywords = ["aws certified solutions architect", "cka", "ckad", "cissp", "pmp", "ccie", "gcp professional"]
        text_lower = clean_text.lower()
        claimed_certs = [c for c in cert_keywords if c in text_lower]
        if claimed_certs and not any(k in text_lower for k in ["credential", "license", "id:", "certificate", "verify", "issued", "expiration", "valid"]):
            indicators.append(
                IntegrityRiskIndicator(
                    indicator_id="unsubstantiated_certification",
                    category="skills_vs_projects",
                    severity="info",
                    title="High-Level Certification Mentioned Without Credential ID",
                    explanation=(
                        f"Resume cites professional certification '{claimed_certs[0].title()}', "
                        "but does not list an issuance date or verification credential identifier."
                    ),
                    evidence_snippet=claimed_certs[0],
                    clarification_prompt="Candidate can describe verification badge or issuance date during interview.",
                )
            )
            clarifications.append(f"Briefly describe scope of '{claimed_certs[0].title()}' certification.")

        # Determine Final Outcome & Risk Score
        review_count = sum(1 for i in indicators if i.severity == "review_recommended")
        advisory_count = sum(1 for i in indicators if i.severity == "advisory")
        info_count = sum(1 for i in indicators if i.severity == "info")

        risk_score = round(min(100.0, review_count * 35.0 + advisory_count * 15.0 + info_count * 5.0), 1)

        if review_count >= 2 or risk_score >= 60.0:
            outcome = IntegrityOutcome.STRONG_CONCERNS
            outcome_label = "Strong integrity concerns requiring further verification"
            headline = "Multiple cross-section anomalies warrant structured interviewer verification"
            summary = (
                "Automated review flagged notable discrepancies (such as template tags, implausible dates, "
                "or significant claim-to-detail mismatches). While not definitive proof of inaccuracy, "
                "interview questions should systematically probe real-world application."
            )
        elif review_count == 1 or advisory_count >= 1:
            outcome = IntegrityOutcome.POTENTIAL_INCONSISTENCIES
            outcome_label = "Potential inconsistencies requiring clarification"
            headline = "Minor contextual or timeline gaps flagged for standard clarification"
            summary = (
                "Resume provides credible overall background with minor areas warranting clarification "
                "(e.g., broad skill claims with concise project descriptions or minor date ambiguities). "
                "The adaptive interview will explore these topics naturally."
            )
        else:
            outcome = IntegrityOutcome.NO_INCONSISTENCIES
            outcome_label = "No significant inconsistencies detected"
            headline = "High structural coherence across skills, projects, and career history"
            summary = (
                "Skills, project responsibilities, and timeline show consistent internal alignment. "
                "No template artifacts, implausible dates, or content contradictions detected."
            )

        return ResumeIntegrityReport(
            outcome=outcome,
            outcome_label=outcome_label,
            headline=headline,
            summary_explanation=summary,
            risk_score=risk_score,
            indicators=indicators,
            section_consistency=section_consistency,
            clarification_topics=clarifications,
        )
