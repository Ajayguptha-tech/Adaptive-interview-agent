"""Agent: Resume Completeness and Integrity Detection Agent.
Performs thorough structural validation, template detection, timeline consistency checks,
and completeness scoring without unfair or defamatory accusations.
"""
import re
from typing import List, Dict, Optional, Tuple, Set
from ..schemas.resume import ResumeParsedData, WorkExperienceItem
from ..schemas.integrity import (
    IntegrityIssue,
    IntegrityAuditResult,
    SectionCompletenessItem,
    SectionStatus,
    OverallCompletenessStatus,
)


# Known placeholder patterns
PLACEHOLDER_TEXT_PATTERNS = [
    (r"\[insert\s+[^\]]+\]", "Bracketed placeholder tag (e.g. '[Insert ...]')"),
    (r"\[company\s*name\]", "Template company placeholder '[Company Name]'"),
    (r"\[job\s*title\]", "Template job title placeholder '[Job Title]'"),
    (r"\[your\s*name\]", "Template name placeholder '[Your Name]'"),
    (r"\[date\]", "Template date placeholder '[Date]'"),
    (r"\[city,?\s*state\]", "Template location placeholder '[City, State]'"),
    (r"\blorem\s+ipsum\b", "Standard filler text ('Lorem ipsum')"),
    (r"\bdolor\s+sit\s+amet\b", "Standard filler text ('dolor sit amet')"),
    (r"\bTODO:?\b", "Incomplete developer/template note ('TODO')"),
    (r"\bTBD:?\b", "Unspecified placeholder note ('TBD')"),
    (r"\bXXXX+\b", "Redacted or template placeholder ('XXXX')"),
    (r"\binsert\s+your\s+text\b", "Instructional template filler ('Insert your text')"),
    (r"\{insert\s+[^}]+\}", "Braced placeholder tag '{Insert ...}'"),
]

PLACEHOLDER_EMAILS = [
    r"^your\.name@email\.com$",
    r"^your\.name@example\.com$",
    r"^name@email\.com$",
    r"^user@example\.com$",
    r"^email@domain\.com$",
    r"^john\.doe@example\.com$",
    r"^jane\.doe@example\.com$",
    r"^test@test\.com$",
    r"^placeholder@.*",
]

PLACEHOLDER_PHONES = [
    r"123[-.\s]?456[-.\s]?7890",
    r"000[-.\s]?000[-.\s]?0000",
    r"555[-.\s]?000[-.\s]?0000",
    r"555[-.\s]?555[-.\s]?5555",
    r"\(?123\)?[-.\s]?456[-.\s]?7890",
    r"^0123456789$",
]

PLACEHOLDER_NAMES = [
    "john doe", "jane doe", "your name", "first last", "candidate name",
    "insert name", "full name", "your name here"
]


class ResumeIntegrityAgent:
    """Agent: Evaluates document completeness, date consistency, repeated text, and template placeholders."""

    def __init__(self):
        pass

    def audit(
        self,
        resume: ResumeParsedData,
        raw_text: str = "",
        file_name: str = "Resume.pdf",
        is_scanned: bool = False,
        warning: str = "",
    ) -> IntegrityAuditResult:
        issues: List[IntegrityIssue] = []
        full_text = raw_text or resume.raw_text or resume.normalized_text
        word_count = len(full_text.split())

        # 1. Document & File Health Validation
        self._check_document_health(resume, full_text, is_scanned, warning, issues)

        # 2. Detailed Section-Level Completeness Evaluation
        (
            section_details,
            present_sections,
            partial_sections,
            missing_sections,
            recommendations,
            base_score,
        ) = self._evaluate_sections(resume, full_text)

        # 3. Contact Information Health
        self._check_contact_information(resume, issues)

        # 4. Template & Placeholder Detection
        placeholder_issues = self._check_template_placeholders(full_text, issues)

        # 5. Suspicious Repeated Content Check
        self._check_repeated_content(resume, issues)

        # 6. Timeline and Date Consistency
        timeline_summary = self._check_timeline_consistency(resume, issues)

        # Add section completeness issues to issues list
        self._generate_section_issues(section_details, issues)

        # Calculate final completeness score with quality adjustments
        deductions = 0.0
        if word_count < 60:
            deductions += 15.0
        if placeholder_issues > 0:
            deductions += min(20.0, placeholder_issues * 8.0)

        completeness_score = max(0.0, min(100.0, round(base_score - deductions, 1)))

        # Determine overall completeness status
        # Condition for INCOMPLETE:
        # Score < 50, OR word count < 60, OR missing >= 2 core sections (e.g. missing Education and Experience/Projects)
        core_missing_count = sum(1 for s in section_details if s.is_core and s.status == "missing")
        core_complete_count = sum(1 for s in section_details if s.is_core and s.status == "complete")

        if completeness_score < 50.0 or core_missing_count >= 2 or word_count < 60:
            status: OverallCompletenessStatus = "incomplete"
        elif completeness_score < 75.0 or core_missing_count == 1 or core_complete_count < 3:
            status = "partially_complete"
        else:
            status = "complete"

        # Construct clear user-facing explanation
        missing_titles = [s.section_name for s in section_details if s.status == "missing" and s.is_core]
        partial_titles = [s.section_name for s in section_details if s.status == "partial"]

        if status == "incomplete":
            explanation = (
                f"Your resume appears incomplete (Completeness Score: {completeness_score}%). "
                f"Several critical sections are missing ({', '.join(missing_titles) or 'key sections'}). "
                "Add the recommended information before using this resume for job applications."
            )
        elif status == "partially_complete":
            parts = []
            if missing_titles:
                parts.append(f"missing {', '.join(missing_titles)}")
            if partial_titles:
                parts.append(f"needs elaboration in {', '.join(partial_titles)}")
            explanation = (
                f"Your resume is partially complete (Completeness Score: {completeness_score}%). "
                f"Core structure is present, but {'; '.join(parts) or 'some areas require more detail'}."
            )
        else:
            explanation = (
                f"Your resume structure is complete and well-documented (Completeness Score: {completeness_score}%). "
                "Core career sections are present with clear evidence."
            )

        # Metrics for integrity
        cautions = [i for i in issues if i.severity == "caution"]
        warnings = [i for i in issues if i.severity == "warning"]
        infos = [i for i in issues if i.severity == "info"]

        # Integrity diagnostic status
        if len(cautions) >= 2 or status == "incomplete":
            integrity_status = "attention_needed"
        elif len(cautions) == 1 or len(warnings) >= 2 or status == "partially_complete":
            integrity_status = "advisory"
        else:
            integrity_status = "passed"

        # List of missing section machine keys
        all_missing_keys = [s.section_key for s in section_details if s.status == "missing"]

        return IntegrityAuditResult(
            status=status,
            completeness_score=completeness_score,
            explanation=explanation,
            present_sections=present_sections,
            partial_sections=partial_sections,
            missing_sections=all_missing_keys,
            section_details=section_details,
            recommendations=recommendations,
            integrity_status=integrity_status,
            total_issues=len(issues),
            cautions_count=len(cautions),
            warnings_count=len(warnings),
            info_count=len(infos),
            issues=issues,
            detected_sections=resume.detected_sections,
            timeline_summary=timeline_summary,
        )

    def _evaluate_sections(
        self,
        resume: ResumeParsedData,
        full_text: str,
    ) -> Tuple[List[SectionCompletenessItem], List[str], List[str], List[str], List[str], float]:
        """Performs constructive, transparent section-level quality evaluation."""
        details: List[SectionCompletenessItem] = []
        present_sections: List[str] = []
        partial_sections: List[str] = []
        missing_sections: List[str] = []
        recommendations: List[str] = []
        score = 0.0

        ci = resume.contact_info

        # 1. Contact Information (Core, 15%)
        has_email = bool(ci.email)
        has_phone = bool(ci.phone)
        has_name = bool(ci.name)
        has_location = bool(ci.location)

        if has_email and has_phone and has_name:
            contact_status: SectionStatus = "complete"
            score += 15.0
            present_sections.append("contact")
            details.append(
                SectionCompletenessItem(
                    section_key="contact",
                    section_name="Contact Information",
                    status="complete",
                    is_core=True,
                    content_count=sum([has_name, has_email, has_phone, has_location]),
                    explanation=f"Full contact header verified: {ci.name}, {ci.email}, {ci.phone}{', ' + ci.location if ci.location else ''}.",
                    recommendation=None,
                )
            )
        elif has_email or has_phone:
            contact_status = "partial"
            score += 7.5
            partial_sections.append("contact")
            rec = "Add your active telephone number and location (City, State) to your contact details."
            recommendations.append(rec)
            details.append(
                SectionCompletenessItem(
                    section_key="contact",
                    section_name="Contact Information",
                    status="partial",
                    is_core=True,
                    content_count=sum([has_name, has_email, has_phone, has_location]),
                    explanation="Contact details are partially provided (email or phone present, but missing full phone number, legal name, or location).",
                    recommendation=rec,
                )
            )
        else:
            contact_status = "missing"
            missing_sections.append("contact")
            rec = "Add contact information at the top of your resume with your full name, email, phone number, and location."
            recommendations.append(rec)
            details.append(
                SectionCompletenessItem(
                    section_key="contact",
                    section_name="Contact Information",
                    status="missing",
                    is_core=True,
                    content_count=0,
                    explanation="No contact details (email or phone) detected.",
                    recommendation=rec,
                )
            )

        # 2. Education (Core, 25%)
        edu_items = resume.education
        if len(edu_items) >= 1:
            # Check if degree has graduation year or institution
            has_details = any(e.graduation_year or e.institution or len(e.degree or "") > 15 for e in edu_items)
            if has_details:
                score += 25.0
                present_sections.append("education")
                details.append(
                    SectionCompletenessItem(
                        section_key="education",
                        section_name="Education",
                        status="complete",
                        is_core=True,
                        content_count=len(edu_items),
                        explanation=f"Identified {len(edu_items)} educational credential(s).",
                        recommendation=None,
                    )
                )
            else:
                score += 12.5
                partial_sections.append("education")
                rec = "Specify your degree title, college/university name, and year of graduation in your Education section."
                recommendations.append(rec)
                details.append(
                    SectionCompletenessItem(
                        section_key="education",
                        section_name="Education",
                        status="partial",
                        is_core=True,
                        content_count=len(edu_items),
                        explanation="Education entry listed, but college name, major, or graduation year is missing.",
                        recommendation=rec,
                    )
                )
        else:
            missing_sections.append("education")
            rec = "Add an 'Education' section detailing your degree, university or college, major, and graduation year."
            recommendations.append(rec)
            details.append(
                SectionCompletenessItem(
                    section_key="education",
                    section_name="Education",
                    status="missing",
                    is_core=True,
                    content_count=0,
                    explanation="No Education or Academic History section recognized.",
                    recommendation=rec,
                )
            )

        # 3. Technical Skills (Core, 20%)
        skills_count = len(resume.skills)
        if skills_count >= 5:
            score += 20.0
            present_sections.append("skills")
            details.append(
                SectionCompletenessItem(
                    section_key="skills",
                    section_name="Technical Skills",
                    status="complete",
                    is_core=True,
                    content_count=skills_count,
                    explanation=f"Identified {skills_count} technical and professional competencies.",
                    recommendation=None,
                )
            )
        elif 1 <= skills_count < 5:
            score += 8.0
            partial_sections.append("skills")
            rec = "Expand your technical skills list to 6–12 relevant languages, frameworks, developer tools, and methodologies aligned with your target role."
            recommendations.append(rec)
            details.append(
                SectionCompletenessItem(
                    section_key="skills",
                    section_name="Technical Skills",
                    status="partial",
                    is_core=True,
                    content_count=skills_count,
                    explanation=f"Only {skills_count} skill(s) listed ({', '.join(resume.skills)}). This is limited compared to standard industry expectations.",
                    recommendation=rec,
                )
            )
        else:
            missing_sections.append("skills")
            rec = "Add a dedicated 'Technical Skills' section categorizing languages, frameworks, developer tools, and domain proficiencies."
            recommendations.append(rec)
            details.append(
                SectionCompletenessItem(
                    section_key="skills",
                    section_name="Technical Skills",
                    status="missing",
                    is_core=True,
                    content_count=0,
                    explanation="No skills or technical competencies section identified.",
                    recommendation=rec,
                )
            )

        # 4. Work Experience & Internships (Core, 20% base)
        exp_items = resume.experience
        total_bullets = sum(len(e.responsibilities) for e in exp_items)

        # 5. Projects (Recommended / Core for Freshers, 15% base)
        proj_items = resume.projects
        detailed_projects = [p for p in proj_items if len(p.description or "") > 25 or len(p.technologies) > 0]

        has_exp = len(exp_items) >= 1 and total_bullets >= 2
        has_partial_exp = len(exp_items) >= 1 and total_bullets < 2
        has_proj = len(detailed_projects) >= 2 or len(proj_items) >= 2
        has_partial_proj = len(proj_items) == 1

        # Check if fresher / student context where projects serve as practical experience
        is_fresher_with_projects = not has_exp and has_proj and len(edu_items) >= 1

        # Evaluate Experience
        if has_exp:
            present_sections.append("experience")
            details.append(
                SectionCompletenessItem(
                    section_key="experience",
                    section_name="Work Experience / Internships",
                    status="complete",
                    is_core=True,
                    content_count=len(exp_items),
                    explanation=f"Documented {len(exp_items)} professional position(s) with {total_bullets} achievement bullet(s).",
                    recommendation=None,
                )
            )
        elif is_fresher_with_projects:
            present_sections.append("experience")
            details.append(
                SectionCompletenessItem(
                    section_key="experience",
                    section_name="Work Experience / Internships",
                    status="complete",
                    is_core=False,
                    content_count=len(proj_items),
                    explanation=f"Practical technical experience demonstrated through {len(proj_items)} detailed project(s) (Student / Early Career profile).",
                    recommendation=None,
                )
            )
        elif has_partial_exp:
            partial_sections.append("experience")
            rec = "Elaborate each role with 2–4 accomplishment bullet points using action verbs and measurable impact."
            recommendations.append(rec)
            details.append(
                SectionCompletenessItem(
                    section_key="experience",
                    section_name="Work Experience / Internships",
                    status="partial",
                    is_core=True,
                    content_count=len(exp_items),
                    explanation=f"Listed {len(exp_items)} role(s) but with minimal descriptive detail (fewer than 2 bullet points).",
                    recommendation=rec,
                )
            )
        else:
            missing_sections.append("experience")
            rec = "Add your employment history, internships, or relevant work engagements. (If you are a fresher or student, ensure you provide substantial academic or personal projects)."
            recommendations.append(rec)
            details.append(
                SectionCompletenessItem(
                    section_key="experience",
                    section_name="Work Experience / Internships",
                    status="missing",
                    is_core=True,
                    content_count=0,
                    explanation="No Work Experience, Professional History, or Internships section was identified.",
                    recommendation=rec,
                )
            )

        # Evaluate Projects
        if has_proj:
            present_sections.append("projects")
            details.append(
                SectionCompletenessItem(
                    section_key="projects",
                    section_name="Key Projects",
                    status="complete",
                    is_core=True,
                    content_count=len(proj_items),
                    explanation=f"Identified {len(proj_items)} project(s) with technical descriptions and deliverables.",
                    recommendation=None,
                )
            )
        elif has_partial_proj:
            partial_sections.append("projects")
            rec = "Add 1–2 additional technical or academic projects describing architecture, tools, and outcomes."
            recommendations.append(rec)
            details.append(
                SectionCompletenessItem(
                    section_key="projects",
                    section_name="Key Projects",
                    status="partial",
                    is_core=True,
                    content_count=1,
                    explanation="Only 1 project entry identified. Presenting 2–3 substantial projects demonstrates broader technical capability.",
                    recommendation=rec,
                )
            )
        else:
            missing_sections.append("projects")
            rec = "Add a 'Key Projects' section featuring 2–3 applications, capstones, or open-source initiatives with technologies used and links."
            recommendations.append(rec)
            details.append(
                SectionCompletenessItem(
                    section_key="projects",
                    section_name="Key Projects",
                    status="missing",
                    is_core=True,
                    content_count=0,
                    explanation="No Projects or Key Technical Deliverables section identified.",
                    recommendation=rec,
                )
            )

        # Adaptive Experience + Projects scoring (Combined max 30%)
        if has_exp and has_proj:
            score += 30.0
        elif has_exp:
            score += 25.0 + (5.0 if has_partial_proj else 0.0)
        elif is_fresher_with_projects:
            # Fresher/student context: rich projects and education fulfill experience requirement
            score += 30.0
        elif has_proj:
            score += 15.0
        elif has_partial_exp:
            score += 12.0
        elif has_partial_proj:
            score += 6.0
        else:
            score += 0.0

        # 6. Professional Summary / Objective (Recommended, 10%)
        summary_words = len((resume.summary or "").split())
        if summary_words >= 15:
            score += 10.0
            present_sections.append("summary")
            details.append(
                SectionCompletenessItem(
                    section_key="summary",
                    section_name="Professional Summary",
                    status="complete",
                    is_core=False,
                    content_count=summary_words,
                    explanation=f"Professional summary verified ({summary_words} words).",
                    recommendation=None,
                )
            )
        elif 1 <= summary_words < 15:
            score += 5.0
            partial_sections.append("summary")
            rec = "Expand your summary into a concise 2–3 sentence statement highlighting your target role, core stack, and top value proposition."
            recommendations.append(rec)
            details.append(
                SectionCompletenessItem(
                    section_key="summary",
                    section_name="Professional Summary",
                    status="partial",
                    is_core=False,
                    content_count=summary_words,
                    explanation=f"Summary is very brief ({summary_words} words).",
                    recommendation=rec,
                )
            )
        else:
            missing_sections.append("summary")
            rec = "Add a 2–3 sentence professional summary or career objective at the top of the resume highlighting your core qualifications."
            recommendations.append(rec)
            details.append(
                SectionCompletenessItem(
                    section_key="summary",
                    section_name="Professional Summary",
                    status="missing",
                    is_core=False,
                    content_count=0,
                    explanation="No Professional Summary or Career Objective section found.",
                    recommendation=rec,
                )
            )

        # 7. Certifications (Bonus/Recommended, up to +3%)
        if len(resume.certifications) >= 1:
            score = min(100.0, score + 3.0)
            present_sections.append("certifications")
            details.append(
                SectionCompletenessItem(
                    section_key="certifications",
                    section_name="Certifications & Credentials",
                    status="complete",
                    is_core=False,
                    content_count=len(resume.certifications),
                    explanation=f"Identified {len(resume.certifications)} verified certification(s).",
                    recommendation=None,
                )
            )
        else:
            missing_sections.append("certifications")
            details.append(
                SectionCompletenessItem(
                    section_key="certifications",
                    section_name="Certifications & Credentials",
                    status="missing",
                    is_core=False,
                    content_count=0,
                    explanation="No certifications or professional licenses listed (optional).",
                    recommendation="Include relevant cloud, vendor, or professional certifications (e.g. AWS, CKA, PMP) if obtained.",
                )
            )

        # 8. Achievements & Honors (Bonus/Recommended, up to +2%)
        if len(resume.achievements) >= 1:
            score = min(100.0, score + 2.0)
            present_sections.append("achievements")
            details.append(
                SectionCompletenessItem(
                    section_key="achievements",
                    section_name="Honors & Achievements",
                    status="complete",
                    is_core=False,
                    content_count=len(resume.achievements),
                    explanation=f"Identified {len(resume.achievements)} honor(s) or award(s).",
                    recommendation=None,
                )
            )
        else:
            missing_sections.append("achievements")
            details.append(
                SectionCompletenessItem(
                    section_key="achievements",
                    section_name="Honors & Achievements",
                    status="missing",
                    is_core=False,
                    content_count=0,
                    explanation="No distinct honors or awards section listed (optional).",
                    recommendation="Add notable academic distinctions, hackathon wins, or company awards where applicable.",
                )
            )

        return details, present_sections, partial_sections, missing_sections, recommendations, score

    def _generate_section_issues(
        self,
        section_details: List[SectionCompletenessItem],
        issues: List[IntegrityIssue],
    ) -> None:
        """Emits structured integrity issues for missing core sections."""
        for s in section_details:
            if s.section_key == "experience" and s.status == "missing":
                issues.append(
                    IntegrityIssue(
                        id="comp_missing_experience",
                        category="completeness",
                        severity="caution",
                        title="Missing Work Experience Section",
                        explanation=(
                            "No standard 'Experience', 'Work History', or 'Internships' heading was identified. "
                            "Applicant Tracking Systems typically expect documented roles or substantive deliverables."
                        ),
                        evidence_snippet="Missing header: Experience / Work History / Internships",
                    )
                )
            elif s.section_key == "experience" and s.status == "partial":
                issues.append(
                    IntegrityIssue(
                        id="comp_sparse_experience",
                        category="completeness",
                        severity="warning",
                        title="Unusually Brief Experience Descriptions",
                        explanation=s.explanation,
                        evidence_snippet="Fewer than 2 descriptive bullet points recorded.",
                    )
                )
            elif s.section_key == "education" and s.status == "missing":
                issues.append(
                    IntegrityIssue(
                        id="comp_missing_education",
                        category="completeness",
                        severity="warning",
                        title="Missing Education Section",
                        explanation=(
                            "No 'Education' or 'Academic History' section was recognized. Many ATS filters check for a degree or credential."
                        ),
                        evidence_snippet="Missing header: Education / Academic Background",
                    )
                )
            elif s.section_key == "skills" and s.status == "missing":
                issues.append(
                    IntegrityIssue(
                        id="comp_missing_skills",
                        category="completeness",
                        severity="warning",
                        title="Missing Dedicated Skills Section",
                        explanation=(
                            "No dedicated 'Skills' or 'Technical Competencies' section was found. "
                            "Grouping core proficiencies into a structured list boosts ATS keyword matching rate."
                        ),
                        evidence_snippet="Missing header: Skills / Technical Skills",
                    )
                )
            elif s.section_key == "skills" and s.status == "partial":
                issues.append(
                    IntegrityIssue(
                        id="comp_sparse_skills",
                        category="completeness",
                        severity="info",
                        title="Sparse Skills Inventory",
                        explanation=s.explanation,
                        evidence_snippet=f"Only {s.content_count} skill(s) listed.",
                    )
                )
            elif s.section_key == "projects" and s.status == "missing":
                issues.append(
                    IntegrityIssue(
                        id="comp_missing_projects",
                        category="completeness",
                        severity="info",
                        title="Missing Key Projects Section",
                        explanation="No technical projects or software deliverables section was recognized.",
                        evidence_snippet="Missing header: Projects / Academic Projects",
                    )
                )
            elif s.section_key == "summary" and s.status == "missing":
                issues.append(
                    IntegrityIssue(
                        id="comp_missing_summary",
                        category="completeness",
                        severity="info",
                        title="Missing Professional Summary",
                        explanation=(
                            "An introductory professional summary or career profile provides a quick executive overview for human recruiters."
                        ),
                        evidence_snippet="Missing header: Professional Summary / Profile",
                    )
                )

    def _check_document_health(
        self,
        resume: ResumeParsedData,
        full_text: str,
        is_scanned: bool,
        warning: str,
        issues: List[IntegrityIssue],
    ) -> None:
        if is_scanned or resume.is_scanned_pdf:
            issues.append(
                IntegrityIssue(
                    id="doc_scanned_pdf",
                    category="formatting",
                    severity="caution",
                    title="Image-Only or Scanned PDF Detected",
                    explanation=(
                        "The uploaded PDF contains little or no selectable digital text. "
                        "Applicant Tracking Systems (ATS) and parsers cannot index image-only documents without OCR. "
                        "Please export a clean PDF with selectable text or upload a DOCX file."
                    ),
                    evidence_snippet=warning or "Extracted character count < 50 characters",
                )
            )

        word_count = len(full_text.split())
        if word_count < 60:
            issues.append(
                IntegrityIssue(
                    id="doc_insufficient_text",
                    category="completeness",
                    severity="caution",
                    title="Insufficient Extractable Content",
                    explanation=(
                        f"The document yielded only {word_count} words. Standard professional resumes typically contain "
                        "between 350 and 900 words to adequately describe background and qualifications."
                    ),
                    evidence_snippet=f"Total document word count: {word_count} words",
                )
            )
        elif word_count > 1800:
            issues.append(
                IntegrityIssue(
                    id="doc_unusually_long",
                    category="formatting",
                    severity="info",
                    title="Lengthy Document Format",
                    explanation=(
                        f"The document contains {word_count} words (likely 3+ pages). Recruiters recommend keeping "
                        "resumes concise (1–2 pages) for optimal review."
                    ),
                    evidence_snippet=f"Total document word count: {word_count} words",
                )
            )

    def _check_contact_information(
        self,
        resume: ResumeParsedData,
        issues: List[IntegrityIssue],
    ) -> None:
        ci = resume.contact_info

        # Name checks
        if not ci.name:
            issues.append(
                IntegrityIssue(
                    id="contact_missing_name",
                    category="contact",
                    severity="warning",
                    title="Candidate Name Not Clearly Identified",
                    explanation="Could not unambiguously identify candidate full name at the top of the resume.",
                    evidence_snippet="Top lines do not contain clear name pattern",
                )
            )
        elif ci.name.lower() in PLACEHOLDER_NAMES:
            issues.append(
                IntegrityIssue(
                    id="contact_placeholder_name",
                    category="placeholder",
                    severity="caution",
                    title="Potential Placeholder Candidate Name",
                    explanation=(
                        f"The candidate name appears to be a generic placeholder: '{ci.name}'. "
                        "Ensure your genuine legal or professional name is displayed."
                    ),
                    evidence_snippet=f"Detected name: '{ci.name}'",
                )
            )

        # Email checks
        if not ci.email:
            issues.append(
                IntegrityIssue(
                    id="contact_missing_email",
                    category="contact",
                    severity="caution",
                    title="Missing Email Address",
                    explanation="No valid email address was detected. Recruiters cannot reach out without contact details.",
                    evidence_snippet="No email pattern found in document",
                )
            )
        else:
            low_email = ci.email.lower()
            for pattern in PLACEHOLDER_EMAILS:
                if re.match(pattern, low_email):
                    issues.append(
                        IntegrityIssue(
                            id="contact_placeholder_email",
                            category="placeholder",
                            severity="caution",
                            title="Placeholder Email Address Detected",
                            explanation=(
                                f"The email address '{ci.email}' matches a known template placeholder pattern. "
                                "Replace it with your active professional contact address."
                            ),
                            evidence_snippet=ci.email,
                        )
                    )
                    break

        # Phone checks
        if not ci.phone:
            issues.append(
                IntegrityIssue(
                    id="contact_missing_phone",
                    category="contact",
                    severity="warning",
                    title="Missing Phone Number",
                    explanation="No phone number was identified in the contact header.",
                    evidence_snippet="No phone format detected",
                )
            )
        else:
            for pattern in PLACEHOLDER_PHONES:
                if re.search(pattern, ci.phone):
                    issues.append(
                        IntegrityIssue(
                            id="contact_placeholder_phone",
                            category="placeholder",
                            severity="caution",
                            title="Placeholder Phone Number Detected",
                            explanation=(
                                f"The phone number '{ci.phone}' appears to be a mock or placeholder number. "
                                "Update it with your valid telephone number."
                            ),
                            evidence_snippet=ci.phone,
                        )
                    )
                    break

    def _check_template_placeholders(
        self,
        full_text: str,
        issues: List[IntegrityIssue],
    ) -> int:
        found_tags: Set[str] = set()

        for pattern, desc in PLACEHOLDER_TEXT_PATTERNS:
            matches = re.findall(pattern, full_text, re.IGNORECASE)
            for m in matches:
                clean_m = m.strip()
                if clean_m.lower() not in found_tags:
                    found_tags.add(clean_m.lower())
                    issues.append(
                        IntegrityIssue(
                            id=f"placeholder_{abs(hash(clean_m)) % 10000}",
                            category="placeholder",
                            severity="caution",
                            title="Unfilled Template Placeholder Found",
                            explanation=(
                                f"Detected unresolved template marker: '{clean_m}' ({desc}). "
                                "Replace template placeholders with genuine accomplishments before submitting."
                            ),
                            evidence_snippet=clean_m,
                        )
                    )

        return len(found_tags)

    def _check_repeated_content(
        self,
        resume: ResumeParsedData,
        issues: List[IntegrityIssue],
    ) -> None:
        bullet_map: Dict[str, List[str]] = {}

        for exp in resume.experience:
            role = exp.job_title or "Role"
            for bullet in exp.responsibilities:
                norm_b = re.sub(r"\s+", " ", bullet.strip().lower())
                # Only check non-trivial bullets > 30 chars
                if len(norm_b) > 30:
                    if norm_b not in bullet_map:
                        bullet_map[norm_b] = []
                    bullet_map[norm_b].append(role)

        for bullet, roles in bullet_map.items():
            if len(roles) >= 2:
                issues.append(
                    IntegrityIssue(
                        id=f"repeated_content_{abs(hash(bullet)) % 10000}",
                        category="formatting",
                        severity="warning",
                        title="Identical Content Repeated Across Roles",
                        explanation=(
                            f"Identical bullet description appears in multiple positions ({', '.join(roles[:2])}). "
                            "Recruiters look for tailored accomplishments specific to each tenure."
                        ),
                        evidence_snippet=bullet[:120],
                    )
                )
                break  # Alert on first significant repetition

    def _check_timeline_consistency(
        self,
        resume: ResumeParsedData,
        issues: List[IntegrityIssue],
    ) -> str:
        roles_with_dates: List[Tuple[str, int, int, str]] = []  # (title, start_year, end_year, raw_dates)
        current_year = 2026

        for exp in resume.experience:
            dates = exp.dates or ""
            years = [int(y) for y in re.findall(r"\b(19\d\d|20\d\d)\b", dates)]

            if len(years) >= 2:
                start_y, end_y = years[0], years[1]
                # Check for inverted dates (e.g. 2024 - 2020)
                if end_y < start_y:
                    issues.append(
                        IntegrityIssue(
                            id=f"time_inverted_{exp.job_title}",
                            category="timeline",
                            severity="caution",
                            title=f"Inverted Date Range in {exp.job_title or 'Role'}",
                            explanation=(
                                f"End date ({end_y}) is chronologically earlier than start date ({start_y}). "
                                "Check for accidental typo in date formatting."
                            ),
                            evidence_snippet=dates,
                        )
                    )
                elif start_y > current_year or end_y > current_year + 1:
                    issues.append(
                        IntegrityIssue(
                            id=f"time_future_{exp.job_title}",
                            category="timeline",
                            severity="caution",
                            title=f"Future Employment Date in {exp.job_title or 'Role'}",
                            explanation=(
                                f"Start or end year ({start_y} - {end_y}) is in the future. "
                                "Verify that employment dates represent accurate historical tenure."
                            ),
                            evidence_snippet=dates,
                        )
                    )
                roles_with_dates.append((exp.job_title or "Role", start_y, end_y, dates))
            elif len(years) == 1 and "present" in dates.lower():
                start_y = years[0]
                if start_y > current_year:
                    issues.append(
                        IntegrityIssue(
                            id=f"time_future_{exp.job_title}",
                            category="timeline",
                            severity="caution",
                            title=f"Future Start Date in {exp.job_title or 'Role'}",
                            explanation=f"Start year {start_y} exceeds the current calendar year.",
                            evidence_snippet=dates,
                        )
                    )
                roles_with_dates.append((exp.job_title or "Role", start_y, current_year, dates))

        # Check for multiple concurrent full-time positions (> 2 overlapping ongoing roles)
        concurrent_current = sum(1 for _, start_y, end_y, raw in roles_with_dates if "present" in raw.lower())
        if concurrent_current > 2:
            issues.append(
                IntegrityIssue(
                    id="time_concurrent_roles",
                    category="timeline",
                    severity="info",
                    title="Multiple Concurrent Present Roles",
                    explanation=(
                        f"{concurrent_current} concurrent positions are listed as currently ongoing ('Present'). "
                        "Clarify primary versus advisory or part-time roles for recruiter clarity."
                    ),
                    evidence_snippet=f"{concurrent_current} roles marked Present",
                )
            )

        if not roles_with_dates:
            return "No verifiable chronological dates identified."

        return f"Verified timeline across {len(roles_with_dates)} dated position(s)."
