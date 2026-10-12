"""
Role-Based Eligibility Assessment Engine.
Performs preliminary role-readiness assessments before interview settings:
1. Eligible
2. Potentially eligible
3. Not currently eligible

Maintains configurable role profiles for 12 engineering role families:
- Python Developer
- Full-Stack Developer
- Frontend Developer
- Backend Developer
- Java Developer
- C/C++ Developer
- Data Analyst
- Data Engineer
- Machine Learning Engineer
- AI/ML Engineer
- SQL/Database Developer
- General Software Engineer

Enforces fair preliminary evaluation without arbitrary exclusion:
Transferable skills and foundational aptitude allow candidates to validate capabilities during interview.
"""

import re
from typing import Dict, Any, List, Optional
from enum import Enum
from pydantic import BaseModel, Field


class EligibilityOutcome(str, Enum):
    ELIGIBLE = "eligible"
    POTENTIALLY_ELIGIBLE = "potentially_eligible"
    NOT_CURRENTLY_ELIGIBLE = "not_currently_eligible"


class RoleRequirementProfile(BaseModel):
    role_key: str
    display_title: str
    mandatory_prerequisites: List[str] = Field(
        default_factory=list,
        description="Core foundational skills strictly necessary for role (e.g. at least one core language/concept)"
    )
    required_competencies: List[str] = Field(
        default_factory=list,
        description="Key competency areas expected for standard role readiness"
    )
    preferred_skills: List[str] = Field(
        default_factory=list,
        description="Valuable specialized tools, frameworks, and domain enhancements"
    )
    transferable_competencies: List[str] = Field(
        default_factory=list,
        description="Alternative competencies that compensate for absent specific tools"
    )
    min_evidence_score: float = 40.0


# Configurable Role Requirement Profiles for 12 Role Families
ROLE_REQUIREMENT_PROFILES: Dict[str, RoleRequirementProfile] = {
    "python": RoleRequirementProfile(
        role_key="python",
        display_title="Python Developer",
        mandatory_prerequisites=["python"],
        required_competencies=["python", "data structures", "oop", "debugging"],
        preferred_skills=["fastapi", "django", "flask", "pytest", "asyncio", "sql", "docker"],
        transferable_competencies=["algorithms", "backend", "rest api", "software engineering"],
        min_evidence_score=50.0,
    ),
    "fullstack": RoleRequirementProfile(
        role_key="fullstack",
        display_title="Full-Stack Developer",
        mandatory_prerequisites=["javascript|typescript|python", "html|css|react|frontend"],
        required_competencies=["frontend", "backend", "rest api", "sql|databases"],
        preferred_skills=["react", "node.js", "express", "fastapi", "postgresql", "docker", "typescript"],
        transferable_competencies=["web development", "software architecture", "git", "api design"],
        min_evidence_score=45.0,
    ),
    "frontend": RoleRequirementProfile(
        role_key="frontend",
        display_title="Frontend Developer",
        mandatory_prerequisites=["javascript|typescript", "html|css"],
        required_competencies=["javascript", "html", "css", "react|vue|angular"],
        preferred_skills=["react", "typescript", "tailwind", "redux", "responsive design", "webpack|vite"],
        transferable_competencies=["ui/ux", "web performance", "dom manipulation", "frontend testing"],
        min_evidence_score=50.0,
    ),
    "backend": RoleRequirementProfile(
        role_key="backend",
        display_title="Backend Developer",
        mandatory_prerequisites=["python|javascript|node|java|go|c#|backend"],
        required_competencies=["rest api", "sql|databases", "backend architecture", "concurrency|caching"],
        preferred_skills=["fastapi", "express", "postgresql", "redis", "docker", "microservices"],
        transferable_competencies=["system design", "data modeling", "security", "ci/cd"],
        min_evidence_score=50.0,
    ),
    "java": RoleRequirementProfile(
        role_key="java",
        display_title="Java Developer",
        mandatory_prerequisites=["java"],
        required_competencies=["java", "oop", "data structures", "spring|spring boot|backend"],
        preferred_skills=["spring boot", "hibernate", "maven|gradle", "junit", "sql", "microservices"],
        transferable_competencies=["c#", "object-oriented programming", "enterprise architecture"],
        min_evidence_score=50.0,
    ),
    "cpp": RoleRequirementProfile(
        role_key="cpp",
        display_title="C/C++ Developer",
        mandatory_prerequisites=["c++|c"],
        required_competencies=["c++", "memory management", "pointers", "data structures", "oop"],
        preferred_skills=["stl", "cmake", "multithreading", "linux", "gdb", "embedded"],
        transferable_competencies=["c", "systems programming", "computer architecture", "algorithms"],
        min_evidence_score=50.0,
    ),
    "data_analyst": RoleRequirementProfile(
        role_key="data_analyst",
        display_title="Data Analyst",
        mandatory_prerequisites=["sql|excel|python|r"],
        required_competencies=["sql", "data analysis", "data visualization", "statistics"],
        preferred_skills=["python", "pandas", "tableau", "power bi", "excel", "matplotlib|seaborn"],
        transferable_competencies=["business intelligence", "metrics design", "data querying"],
        min_evidence_score=45.0,
    ),
    "data_engineer": RoleRequirementProfile(
        role_key="data_engineer",
        display_title="Data Engineer",
        mandatory_prerequisites=["python|java|scala", "sql"],
        required_competencies=["data pipelines", "sql", "etl", "distributed systems|data warehousing"],
        preferred_skills=["spark", "airflow", "kafka", "postgresql", "snowflake", "docker", "aws"],
        transferable_competencies=["backend", "database optimization", "data modeling", "bash"],
        min_evidence_score=45.0,
    ),
    "ml_engineer": RoleRequirementProfile(
        role_key="ml_engineer",
        display_title="Machine Learning Engineer",
        mandatory_prerequisites=["python", "machine learning|scikit-learn|tensorflow|pytorch"],
        required_competencies=["python", "machine learning", "model evaluation", "numpy|pandas"],
        preferred_skills=["scikit-learn", "pytorch", "tensorflow", "mlops", "feature engineering", "docker"],
        transferable_competencies=["statistics", "data science", "linear algebra", "algorithms"],
        min_evidence_score=45.0,
    ),
    "aiml_engineer": RoleRequirementProfile(
        role_key="aiml_engineer",
        display_title="AI/ML Engineer",
        mandatory_prerequisites=["python", "ai|machine learning|deep learning|llm"],
        required_competencies=["python", "deep learning|llms", "neural networks", "embeddings|nlp"],
        preferred_skills=["pytorch", "transformers", "langchain", "ollama", "rag", "vector databases"],
        transferable_competencies=["prompt engineering", "model fine-tuning", "applied mathematics"],
        min_evidence_score=45.0,
    ),
    "sql_developer": RoleRequirementProfile(
        role_key="sql_developer",
        display_title="SQL / Database Developer",
        mandatory_prerequisites=["sql"],
        required_competencies=["sql", "data modeling", "indexing & optimization", "joins & subqueries"],
        preferred_skills=["postgresql", "mysql", "stored procedures", "schema design", "acid & transactions"],
        transferable_competencies=["relational algebra", "database administration", "etl"],
        min_evidence_score=50.0,
    ),
    "software_engineer": RoleRequirementProfile(
        role_key="software_engineer",
        display_title="General Software Engineer",
        mandatory_prerequisites=["python|javascript|java|c++|c#|go"],
        required_competencies=["data structures", "algorithms", "problem solving", "oop|design patterns"],
        preferred_skills=["git", "unit testing", "system design", "docker", "ci/cd", "rest apis"],
        transferable_competencies=["computer science fundamentals", "code quality", "debugging"],
        min_evidence_score=45.0,
    ),
}


class RoleEligibilityResult(BaseModel):
    target_role: str
    canonical_role_key: str
    role_display_title: str
    outcome: EligibilityOutcome
    outcome_label: str
    headline: str
    summary_explanation: str
    relevant_skills_found: List[str] = Field(default_factory=list)
    required_skills_identified: List[str] = Field(default_factory=list)
    skills_with_evidence: List[str] = Field(default_factory=list)
    missing_or_weak_skills: List[str] = Field(default_factory=list)
    transferable_skills_noted: List[str] = Field(default_factory=list)
    resume_integrity_status: str = "passed"
    integrity_caveat: str = "Integrity analysis is advisory and checked for consistency."
    is_provisional: bool = False
    reasons_supporting_result: List[str] = Field(default_factory=list)
    recommended_interview_focus: List[str] = Field(default_factory=list)
    can_proceed_to_interview: bool = True


class RoleEligibilityAssessor:
    """Evaluates candidate claims against specific engineering role benchmarks."""

    @classmethod
    def resolve_role_profile(cls, target_role: str) -> RoleRequirementProfile:
        role_lower = (target_role or "").strip().lower()

        # Direct alias checks
        if any(k in role_lower for k in ["aiml", "ai/ml", "artificial intelligence", "generative ai", "llm"]):
            return ROLE_REQUIREMENT_PROFILES["aiml_engineer"]
        if any(k in role_lower for k in ["ml", "machine learning"]):
            return ROLE_REQUIREMENT_PROFILES["ml_engineer"]
        if any(k in role_lower for k in ["data engineer", "etl", "pipeline"]):
            return ROLE_REQUIREMENT_PROFILES["data_engineer"]
        if any(k in role_lower for k in ["data analyst", "business analyst", "bi engineer"]):
            return ROLE_REQUIREMENT_PROFILES["data_analyst"]
        if any(k in role_lower for k in ["sql", "database developer", "database admin", "dba"]):
            return ROLE_REQUIREMENT_PROFILES["sql_developer"]
        if any(k in role_lower for k in ["frontend", "front-end", "ui engineer", "react developer"]):
            return ROLE_REQUIREMENT_PROFILES["frontend"]
        if any(k in role_lower for k in ["fullstack", "full-stack", "mern", "mean"]):
            return ROLE_REQUIREMENT_PROFILES["fullstack"]
        if any(k in role_lower for k in ["backend", "api engineer"]):
            return ROLE_REQUIREMENT_PROFILES["backend"]
        if any(k in role_lower for k in ["java"]):
            return ROLE_REQUIREMENT_PROFILES["java"]
        if any(k in role_lower for k in ["c++", "cpp", "c developer"]):
            return ROLE_REQUIREMENT_PROFILES["cpp"]
        if any(k in role_lower for k in ["python"]):
            return ROLE_REQUIREMENT_PROFILES["python"]

        # Default to General Software Engineer
        return ROLE_REQUIREMENT_PROFILES["software_engineer"]

    @classmethod
    def assess_eligibility(
        cls,
        resume_profile: Dict[str, Any],
        target_role: str,
        integrity_status: str = "passed",
    ) -> RoleEligibilityResult:
        profile = cls.resolve_role_profile(target_role)

        claimed_skills = [s.strip().lower() for s in (resume_profile.get("skills") or resume_profile.get("claimed_skills") or [])]
        raw_text = (resume_profile.get("raw_text") or "").lower()

        # Build full searchable text corpus
        corpus = " ".join(claimed_skills) + " " + raw_text

        # 1. Evaluate Mandatory Prerequisites
        prereqs_met = []
        prereqs_missing = []
        for prereq_expr in profile.mandatory_prerequisites:
            options = [opt.strip().lower() for opt in prereq_expr.split("|")]
            found = False
            for opt in options:
                pattern = rf"\b{re.escape(opt)}\b"
                if any(opt == cs for cs in claimed_skills) or re.search(pattern, corpus):
                    found = True
                    prereqs_met.append(opt)
                    break
            if not found:
                prereqs_missing.append(options[0])

        # 2. Evaluate Required Competencies
        req_found = []
        req_missing = []
        for req_expr in profile.required_competencies:
            options = [opt.strip().lower() for opt in req_expr.split("|")]
            found = False
            for opt in options:
                pattern = rf"\b{re.escape(opt)}\b"
                if any(opt in cs for cs in claimed_skills) or re.search(pattern, corpus):
                    found = True
                    req_found.append(options[0])
                    break
            if not found:
                req_missing.append(options[0])

        # 3. Check for Project/Experience Evidence for Found Skills
        skill_evidence = resume_profile.get("skill_evidence") or []
        evidence_backed_skills = set()
        for se in skill_evidence:
            s_name = se.get("skill", "").lower()
            if se.get("evidence_snippet") or se.get("is_explicit"):
                evidence_backed_skills.add(s_name)

        # Also inspect projects descriptions
        projects = resume_profile.get("projects") or []
        for p in projects:
            p_desc = (p.get("description") or "").lower() + " " + " ".join(p.get("technologies") or []).lower()
            for cs in claimed_skills:
                if cs in p_desc:
                    evidence_backed_skills.add(cs)

        skills_with_evidence = [
            s.title() for s in claimed_skills if s in evidence_backed_skills
        ][:8]

        # 4. Check Transferable Skills
        transferable_found = []
        for trans in profile.transferable_competencies:
            if trans in corpus:
                transferable_found.append(trans.title())

        # 5. Determine Outcome and Rationale
        reasons: List[str] = []
        is_provisional = profile.role_key == "software_engineer" and target_role.lower() not in ["software engineer", "general software engineer"]

        if is_provisional:
            reasons.append(
                f"Target role '{target_role}' matched to general software engineering profile; assessment is provisional."
            )

        if not prereqs_missing and len(req_found) >= max(2, len(profile.required_competencies) // 2):
            outcome = EligibilityOutcome.ELIGIBLE
            outcome_label = "Eligible"
            headline = f"Strong foundational alignment identified for {profile.display_title}"
            reasons.append(
                f"Candidate meets core prerequisites ({', '.join(prereqs_met) or 'Fundamental competencies'}) "
                f"with evidence in {len(req_found)} key competency areas."
            )
            can_proceed = True
        elif not prereqs_missing or len(transferable_found) >= 2 or len(req_found) >= 1:
            outcome = EligibilityOutcome.POTENTIALLY_ELIGIBLE
            outcome_label = "Potentially eligible"
            headline = f"Transferable skills identified; adaptive interview will validate key competencies"
            reasons.append(
                f"Relevant technical skills identified ({', '.join(req_found[:3]) or 'General programming'}), "
                f"though some domain specializations ({', '.join(req_missing[:2]) or 'Advanced frameworks'}) show limited direct evidence."
            )
            reasons.append("Interview will assess fundamental problem solving and transferable engineering concepts.")
            can_proceed = True
        else:
            outcome = EligibilityOutcome.NOT_CURRENTLY_ELIGIBLE
            outcome_label = "Not currently eligible"
            headline = f"Prerequisite gap detected for {profile.display_title}"
            reasons.append(
                f"Primary required competencies for '{profile.display_title}' ({', '.join(prereqs_missing or req_missing[:2])}) "
                "were not detected in resume text or verified project history."
            )
            # Permitted to proceed for practice or diagnostic assessment unless safety rule intervenes
            can_proceed = True

        summary_explanation = " ".join(reasons)

        recommended_focus = [
            f"Validate {comp.title()}" for comp in (req_missing[:2] + req_found[:2])
        ]

        return RoleEligibilityResult(
            target_role=target_role,
            canonical_role_key=profile.role_key,
            role_display_title=profile.display_title,
            outcome=outcome,
            outcome_label=outcome_label,
            headline=headline,
            summary_explanation=summary_explanation,
            relevant_skills_found=[s.title() for s in (req_found + prereqs_met)[:8]],
            required_skills_identified=[s.title() for s in profile.required_competencies[:6]],
            skills_with_evidence=skills_with_evidence,
            missing_or_weak_skills=[s.title() for s in req_missing[:5]],
            transferable_skills_noted=transferable_found[:4],
            resume_integrity_status=integrity_status,
            is_provisional=is_provisional,
            reasons_supporting_result=reasons,
            recommended_interview_focus=recommended_focus,
            can_proceed_to_interview=can_proceed,
        )
