"""
Skill Gap Intelligence Module.
Consumes resume analyzer results and interview evaluation history to perform
evidence-based skill-gap analysis, distinguishing:
- Demonstrated: Supported by sufficient interview or coding evidence.
- Claimed but unvalidated: Mentioned in the resume but not yet verified.
- Not demonstrated: Assessed, but candidate failed or evidence did not establish competency.
- Not assessed: Neither mentioned in resume nor assessed in interview.
"""

import re
from typing import Dict, Any, List, Optional
from enum import Enum
from pydantic import BaseModel, Field


class SkillStatus(str, Enum):
    DEMONSTRATED = "demonstrated"
    CLAIMED_UNVALIDATED = "claimed_unvalidated"
    NOT_DEMONSTRATED = "not_demonstrated"
    NOT_ASSESSED = "not_assessed"


# Common skill-to-topic semantic mapping
SKILL_TOPIC_SYNONYMS = {
    "python": ["python", "python core", "python fundamentals", "data structures & mutability", "built-in sequence functions"],
    "data structures": ["data structures", "data structures & mutability", "built-in sequence functions", "sets & dictionary hashing", "comprehensions & expressions"],
    "algorithms": ["algorithms", "time & space complexity", "data structures & mutability", "sorting & lambdas"],
    "oop": ["oop", "object-oriented programming", "mro & multiple inheritance", "dataclasses & slots", "classes", "inheritance"],
    "object-oriented programming": ["oop", "object-oriented programming", "mro & multiple inheritance", "dataclasses & slots"],
    "fastapi": ["fastapi", "rest api", "backend & rest apis", "web framework", "backend", "asyncio & coroutines"],
    "django": ["django", "web framework", "backend & rest apis", "backend"],
    "flask": ["flask", "web framework", "backend & rest apis", "backend"],
    "asyncio": ["asyncio", "asyncio & coroutines", "async", "event loop", "coroutines", "concurrency & gil", "concurrency"],
    "concurrency": ["concurrency", "concurrency & gil", "threading", "multiprocessing", "asyncio & coroutines"],
    "celery": ["celery", "task queue", "concurrency & gil", "asyncio & coroutines"],
    "redis": ["redis", "caching", "sql & databases", "concurrency & gil"],
    "sql": ["sql", "sql & databases", "database", "sqlite", "postgresql", "queries", "joins"],
    "postgresql": ["sql & databases", "sql", "postgresql", "postgres", "rdbms"],
    "javascript": ["javascript", "javascript core", "modern javascript", "js", "event loop", "closures"],
    "typescript": ["typescript", "ts", "javascript core"],
    "react": ["react", "react & component architecture", "react hooks", "frontend"],
    "node.js": ["node", "node.js", "express", "backend & rest apis"],
    "express": ["express", "node.js", "backend & rest apis"],
    "html": ["html", "html & semantic web", "semantic html", "frontend"],
    "css": ["css", "css layout & box model", "flexbox", "grid", "styling"],
    "docker": ["docker", "containers", "devops", "containerization", "full-stack integration & architecture", "testing & testable design"],
    "git": ["git", "version control", "testing & testable design", "full-stack integration & architecture"],
    "testing": ["testing", "jest", "pytest", "unit test", "testing & testable design", "full-stack integration & architecture"],
    "security": ["security", "auth", "authentication", "jwt", "full-stack integration & architecture"],
}


class SkillEvidenceItem(BaseModel):
    skill_name: str
    status: SkillStatus
    category: str = "Technical Competency"
    resume_claims: List[Dict[str, Any]] = Field(default_factory=list)
    interview_evidence: List[Dict[str, Any]] = Field(default_factory=list)
    score_percentage: Optional[float] = None
    verdict: str = ""


class SkillGapReport(BaseModel):
    total_skills_tracked: int = 0
    demonstrated_count: int = 0
    claimed_unvalidated_count: int = 0
    not_demonstrated_count: int = 0
    not_assessed_count: int = 0
    skills: List[SkillEvidenceItem] = Field(default_factory=list)
    demonstrated_skills: List[str] = Field(default_factory=list)
    claimed_unvalidated_skills: List[str] = Field(default_factory=list)
    not_demonstrated_skills: List[str] = Field(default_factory=list)
    not_assessed_skills: List[str] = Field(default_factory=list)
    summary_verdict: str = ""


class SkillGapAnalyzer:
    """Evidence-based skill gap analyzer linking resume claims to interview evaluations."""

    @classmethod
    def analyze_skill_gap(
        cls,
        resume_profile: Optional[Dict[str, Any]],
        interview_history: List[Dict[str, Any]],
        track: str = "python",
    ) -> SkillGapReport:
        """
        Correlates resume claims, target job requirements, and interview question history.
        """
        if not resume_profile:
            return SkillGapReport(
                summary_verdict="No resume was attached to this interview session. Standard interview evaluation applies."
            )

        # 1. Collect all candidate claimed skills
        claimed_skills: List[str] = resume_profile.get("skills", []) or []
        evidence_snippets: List[Dict[str, Any]] = resume_profile.get("skill_evidence", []) or []

        # 2. Collect target job description skills if present
        job_matching = resume_profile.get("job_matching") or {}
        jd_required = job_matching.get("missing_required", []) or []
        jd_preferred = job_matching.get("missing_preferred", []) or []
        all_jd_skills = list(set(jd_required + jd_preferred))

        # Combine tracked universe of skills
        tracked_skills_set = set(claimed_skills)
        tracked_skills_set.update(all_jd_skills)

        # Ensure track-relevant core skills are in the tracked universe
        if track == "python":
            tracked_skills_set.add("Python")
        elif track == "fullstack":
            tracked_skills_set.update(["JavaScript", "React", "SQL", "Backend & APIs"])

        # 3. Analyze each skill against interview evaluations
        items: List[SkillEvidenceItem] = []

        for skill in sorted(list(tracked_skills_set)):
            low_skill = skill.lower()
            matching_synonyms = SKILL_TOPIC_SYNONYMS.get(low_skill, [low_skill])

            # Gather resume claims for this skill
            skill_resume_claims = []
            for ev in evidence_snippets:
                if ev.get("skill", "").lower() == low_skill or any(syn in ev.get("skill", "").lower() for syn in matching_synonyms):
                    skill_resume_claims.append(ev)

            # If no detailed snippet, but in claimed_skills list
            if not skill_resume_claims and skill in claimed_skills:
                skill_resume_claims.append({
                    "skill": skill,
                    "source": "skills_list",
                    "evidence_snippet": f"Listed under technical skills section in {resume_profile.get('filename', 'resume')}",
                    "confidence": 1.0,
                })

            # Check if this skill was tested in interview history
            tested_questions = []
            for h in interview_history:
                h_target_skills = [s.lower() for s in h.get("target_skills", [])]
                h_topic = (h.get("topic") or "").lower()
                h_text = (h.get("question_text") or "").lower()
                h_competency = (h.get("competency") or "").lower()

                # Prioritize explicit target_skills metadata to avoid cross-skill contamination
                is_match = False
                if h_target_skills:
                    if low_skill in h_target_skills:
                        is_match = True
                else:
                    # Fallback for questions without explicit target metadata:
                    # Match exact topic or specific synonym in topic, NOT generic competency
                    if any(syn == h_topic or syn in h_topic for syn in matching_synonyms):
                        is_match = True

                if is_match:
                    awarded = float(h.get("awarded_marks", 0.0) or 0.0)
                    max_marks = float(h.get("max_marks", 5.0) or 5.0)
                    pct = (awarded / max_marks) * 100.0 if max_marks > 0 else 0.0
                    tested_questions.append({
                        "question_number": h.get("question_number", len(tested_questions) + 1),
                        "question_text": h.get("question_text", ""),
                        "topic": h.get("topic", ""),
                        "question_type": h.get("question_type", ""),
                        "awarded_marks": awarded,
                        "max_marks": max_marks,
                        "percentage": round(pct, 1),
                        "evaluation_summary": h.get("evaluation_summary") or h.get("summary") or "",
                        "correctness_status": h.get("correctness_status", "evaluated"),
                        "execution_result": h.get("execution_result"),
                    })

            # 4. Determine status based on actual evidence
            if tested_questions:
                # Assessed in interview
                avg_pct = sum(q["percentage"] for q in tested_questions) / len(tested_questions)

                # Robust code execution safeguard: code execution failures or syntax errors cannot count as demonstrated
                has_exec_failure = any(
                    (q.get("correctness_status") in ("failed_execution", "syntax_error"))
                    or (isinstance(q.get("execution_result"), dict) and not q["execution_result"].get("all_passed", True))
                    for q in tested_questions
                )

                is_passed = (avg_pct >= 60.0) and not has_exec_failure

                if is_passed:
                    status = SkillStatus.DEMONSTRATED
                    q_ids = ", ".join(f"Q#{q['question_number']}" for q in tested_questions)
                    verdict = (
                        f"Demonstrated across {q_ids}: Average score {round(avg_pct, 1)}%. "
                        f"Candidate demonstrated verified technical competence matching rubric."
                    )
                else:
                    status = SkillStatus.NOT_DEMONSTRATED
                    q_ids = ", ".join(f"Q#{q['question_number']}" for q in tested_questions)
                    fail_detail = "execution failure on code test" if has_exec_failure and avg_pct >= 60.0 else f"score {round(avg_pct, 1)}% below passing standard"
                    verdict = (
                        f"Assessed in {q_ids}: {fail_detail}. "
                        f"Demonstrated gaps in tested requirements."
                    )
                score_pct = round(avg_pct, 1)
            else:
                # Not assessed in interview
                score_pct = None
                if skill_resume_claims:
                    status = SkillStatus.CLAIMED_UNVALIDATED
                    verdict = (
                        f"Claimed on resume ({skill_resume_claims[0].get('source', 'experience')}), "
                        f"but not tested or assessed during this interview session."
                    )
                else:
                    status = SkillStatus.NOT_ASSESSED
                    verdict = (
                        "Target job competency not assessed during interview and not documented in resume."
                    )

            items.append(SkillEvidenceItem(
                skill_name=skill,
                status=status,
                category=cls._categorize_skill(skill),
                resume_claims=skill_resume_claims,
                interview_evidence=tested_questions,
                score_percentage=score_pct,
                verdict=verdict,
            ))

        # 5. Summarize counts and lists
        demonstrated = [i.skill_name for i in items if i.status == SkillStatus.DEMONSTRATED]
        claimed_unvalidated = [i.skill_name for i in items if i.status == SkillStatus.CLAIMED_UNVALIDATED]
        not_demonstrated = [i.skill_name for i in items if i.status == SkillStatus.NOT_DEMONSTRATED]
        not_assessed = [i.skill_name for i in items if i.status == SkillStatus.NOT_ASSESSED]

        summary_verdict = (
            f"Candidate demonstrated {len(demonstrated)} verified competencies during the interview. "
            f"{len(claimed_unvalidated)} resume skills remain unvalidated. "
            f"{len(not_demonstrated)} assessed skills showed gaps."
        )

        return SkillGapReport(
            total_skills_tracked=len(items),
            demonstrated_count=len(demonstrated),
            claimed_unvalidated_count=len(claimed_unvalidated),
            not_demonstrated_count=len(not_demonstrated),
            not_assessed_count=len(not_assessed),
            skills=items,
            demonstrated_skills=demonstrated,
            claimed_unvalidated_skills=claimed_unvalidated,
            not_demonstrated_skills=not_demonstrated,
            not_assessed_skills=not_assessed,
            summary_verdict=summary_verdict,
        )

    @staticmethod
    def _categorize_skill(skill: str) -> str:
        low = skill.lower()
        if low in ("python", "javascript", "typescript", "c++", "go", "java"):
            return "Programming Languages"
        elif low in ("react", "angular", "vue", "next.js", "html", "css", "frontend"):
            return "Frontend Frameworks"
        elif low in ("fastapi", "django", "flask", "node.js", "express", "backend & apis"):
            return "Backend & APIs"
        elif low in ("sql", "postgresql", "sqlite", "mongodb", "redis", "database"):
            return "Databases & Storage"
        elif low in ("docker", "kubernetes", "aws", "ci/cd", "git", "devops"):
            return "DevOps & Cloud"
        elif low in ("asyncio", "concurrency", "threading", "oop"):
            return "Core Architecture"
        return "Technical Competencies"
