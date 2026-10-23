"""
Interview Plan Engine for Resume-First Adaptive Interview Intelligence.
Generates candidate-specific, track-tailored interview plans from parsed resume profiles.
Maps claimed technical skills to curriculum topics and structures the verification agenda.
"""

import time
import logging
from typing import Dict, Any, List, Optional
import uuid
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class PlannedQuestionCriterion(BaseModel):
    question_number: int
    topic: str
    target_skills: List[str] = Field(default_factory=list)
    question_type: str = "conceptual"
    target_difficulty: str = "intermediate"
    verification_goal: str = ""


class InterviewPlan(BaseModel):
    plan_id: str
    candidate_name: str
    track: str  # "python" or "fullstack"
    target_role: Optional[str] = None
    target_company: Optional[str] = None
    initial_difficulty: str = "intermediate"
    claimed_skills: List[str] = Field(default_factory=list)
    skills_requiring_verification: List[str] = Field(default_factory=list)
    selected_topics: List[str] = Field(default_factory=list)
    topic_skill_mapping: Dict[str, List[str]] = Field(default_factory=dict)
    planned_questions_criteria: List[PlannedQuestionCriterion] = Field(default_factory=list)
    total_planned_questions: int = 5
    summary: str = ""


# Curriculum topic mapping rules for Python Track
PYTHON_SKILL_TOPIC_RULES = [
    {
        "topic": "Data Structures & Mutability",
        "skills": ["python", "data structures", "algorithms", "lists", "dictionaries", "tuples", "sets"],
        "default": True,
    },
    {
        "topic": "Object-Oriented Programming",
        "skills": ["oop", "object-oriented programming", "design patterns", "classes", "inheritance"],
        "default": False,
    },
    {
        "topic": "Asyncio & Coroutines",
        "skills": ["asyncio", "async", "coroutines", "event loop", "fastapi"],
        "default": False,
    },
    {
        "topic": "Concurrency & GIL",
        "skills": ["concurrency", "threading", "multiprocessing", "gil", "celery", "redis"],
        "default": False,
    },
    {
        "topic": "Generators & Lazy Evaluation",
        "skills": ["generators", "iterators", "yield", "memory optimization", "streaming"],
        "default": False,
    },
    {
        "topic": "Decorators & Closures",
        "skills": ["decorators", "metaprogramming", "closures", "functools", "wrappers"],
        "default": False,
    },
    {
        "topic": "File Handling & Context Managers",
        "skills": ["file handling", "context managers", "with statement", "resource management"],
        "default": False,
    },
    {
        "topic": "Testing & Testable Design",
        "skills": ["testing", "pytest", "unit test", "unittest", "mock", "docker", "ci/cd"],
        "default": False,
    },
    {
        "topic": "Function Arguments & Packing",
        "skills": ["functions", "args", "kwargs", "functional programming", "clean code"],
        "default": True,
    },
    {
        "topic": "Exception Handling",
        "skills": ["exceptions", "error handling", "debugging"],
        "default": False,
    },
    {
        "topic": "Database & SQL Optimization",
        "skills": ["sql", "postgresql", "mysql", "database", "sqlite", "sqlalchemy", "django", "orm", "indexing", "query optimization"],
        "default": False,
    },
]

# Curriculum topic mapping rules for Full-Stack Track
FULLSTACK_SKILL_TOPIC_RULES = [
    {
        "topic": "HTML & Semantic Web",
        "skills": ["html", "html5", "semantic html", "accessibility", "a11y", "seo"],
        "default": True,
    },
    {
        "topic": "CSS Layout & Box Model",
        "skills": ["css", "css3", "flexbox", "grid", "responsive design", "tailwind", "sass", "bootstrap"],
        "default": False,
    },
    {
        "topic": "JavaScript Core",
        "skills": ["javascript", "typescript", "es6", "event loop", "promises", "async/await", "closures"],
        "default": True,
    },
    {
        "topic": "React & Component Architecture",
        "skills": ["react", "redux", "next.js", "hooks", "jsx", "state management", "frontend"],
        "default": False,
    },
    {
        "topic": "Backend & REST APIs",
        "skills": ["rest", "api", "apis", "node.js", "node", "express", "fastapi", "http", "microservices"],
        "default": True,
    },
    {
        "topic": "SQL & Databases",
        "skills": ["sql", "postgresql", "mysql", "database", "sqlite", "mongodb", "orm"],
        "default": False,
    },
    {
        "topic": "Full-Stack Integration & Architecture",
        "skills": ["security", "jwt", "auth", "authentication", "cors", "oauth", "csrf", "docker", "ci/cd", "deployment"],
        "default": False,
    },
]


class InterviewPlanner:
    """Creates deterministic, personalized interview plans from candidate resume claims."""

    @classmethod
    def create_plan(
        cls,
        resume_profile: Dict[str, Any],
        track: str = "python",
        max_questions: int = 5,
        difficulty_mode: str = "adaptive",
        tech_stack: Optional[str] = None,
        target_role: Optional[str] = None,
        job_description: Optional[str] = None,
        company: Optional[str] = None,
    ) -> InterviewPlan:
        t_start = time.perf_counter()
        plan_id = str(uuid.uuid4())
        candidate_name = resume_profile.get("candidate_name") or "Candidate"
        claimed_skills = resume_profile.get("claimed_skills") or resume_profile.get("skills") or []
        exp_years = float(resume_profile.get("total_experience_years") or resume_profile.get("years_experience") or 0.0)

        # 1. Determine initial recommended difficulty
        if difficulty_mode.lower() == "adaptive":
            if exp_years >= 4.0:
                initial_difficulty = "advanced"
            elif exp_years >= 1.5:
                initial_difficulty = "intermediate"
            else:
                initial_difficulty = "beginner"
        else:
            initial_difficulty = difficulty_mode.lower()

        # 2. Select track mapping rules
        rules = PYTHON_SKILL_TOPIC_RULES if track == "python" else FULLSTACK_SKILL_TOPIC_RULES

        # 3. Match candidate's claimed skills to curriculum topics
        topic_skill_map: Dict[str, List[str]] = {}
        matched_topics_set = set()
        skills_to_verify: List[str] = []

        claimed_lower = {s.lower(): s for s in claimed_skills}

        for rule in rules:
            topic = rule["topic"]
            associated_skills = []
            for skill_alias in rule["skills"]:
                if skill_alias in claimed_lower:
                    orig_skill = claimed_lower[skill_alias]
                    if orig_skill not in associated_skills:
                        associated_skills.append(orig_skill)
                    if orig_skill not in skills_to_verify:
                        skills_to_verify.append(orig_skill)

            if associated_skills:
                topic_skill_map[topic] = associated_skills
                matched_topics_set.add(topic)

        # 4. Build prioritized topic order
        # Prioritize topics that directly validate candidate's claimed skills
        selected_topics: List[str] = []
        for rule in rules:
            topic = rule["topic"]
            if topic in matched_topics_set and topic not in selected_topics:
                selected_topics.append(topic)

        # If more slots needed, add default foundational topics
        for rule in rules:
            topic = rule["topic"]
            if rule.get("default", False) and topic not in selected_topics:
                selected_topics.append(topic)

        # If still more slots needed, add remaining topics
        for rule in rules:
            topic = rule["topic"]
            if topic not in selected_topics:
                selected_topics.append(topic)

        # Cap selected topics to max_questions
        final_topics = selected_topics[:max_questions]

        # 5. Build planned question criteria
        modality_cycle = ["conceptual", "code_writing", "code_output", "debugging", "conceptual"]
        planned_criteria: List[PlannedQuestionCriterion] = []

        for i, topic in enumerate(final_topics):
            q_num = i + 1
            q_type = modality_cycle[(i) % len(modality_cycle)]
            q_skills = topic_skill_map.get(topic, [])
            skills_label = ", ".join(q_skills) if q_skills else "Track Fundamentals"

            verification_goal = (
                f"Verify candidate claims in '{skills_label}' via {q_type} challenge on '{topic}'."
                if q_skills
                else f"Evaluate baseline technical competency on '{topic}'."
            )

            planned_criteria.append(
                PlannedQuestionCriterion(
                    question_number=q_num,
                    topic=topic,
                    target_skills=q_skills,
                    question_type=q_type,
                    target_difficulty=initial_difficulty,
                    verification_goal=verification_goal,
                )
            )

        role_str = target_role or ("Full-Stack Developer" if track == "fullstack" else "Python Developer")
        summary = (
            f"Personalized interview plan created for {candidate_name} ({exp_years} yrs exp). "
            f"Identified {len(skills_to_verify)} claimed skills requiring verification across "
            f"{len(final_topics)} assessment topics in {role_str} track."
        )

        duration_sec = time.perf_counter() - t_start
        logger.info(
            "[PERF] Interview plan generation completed in %.3fs for track '%s' (%d topics, %d skills)",
            duration_sec, track, len(final_topics), len(skills_to_verify)
        )

        return InterviewPlan(
            plan_id=plan_id,
            candidate_name=candidate_name,
            track=track,
            target_role=role_str,
            target_company=company,
            initial_difficulty=initial_difficulty,
            claimed_skills=claimed_skills,
            skills_requiring_verification=skills_to_verify,
            selected_topics=final_topics,
            topic_skill_mapping=topic_skill_map,
            planned_questions_criteria=planned_criteria,
            total_planned_questions=len(final_topics),
            summary=summary,
        )
