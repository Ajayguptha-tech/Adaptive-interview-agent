"""
Resume Intelligence & Adaptive Question Generation Agent.
Coordinates resume intelligence, candidate blueprints, layered question diversity,
quality validation, adaptive follow-ups, and session coverage tracking.
"""

import logging
import random
import time
from typing import Dict, Any, List, Optional, Set, Tuple

from backend.models import (
    DifficultyLevel,
    Question,
    QuestionType,
    EvaluationResult,
)
from backend.question_agent.models import (
    QuestionFormat,
    QuestionCandidate,
    ResumeIntelligenceProfile,
    InterviewBlueprint,
    ProjectEvidence,
    FORMAT_TO_QUESTION_TYPE,
)
from backend.question_agent.resume_intelligence import ResumeIntelligenceEngine
from backend.question_agent.diversity_engine import (
    QuestionDiversityEngine,
    CandidateQuestionHistoryStore,
)
from backend.question_agent.question_validator import QuestionQualityValidator
from backend.question_agent.catalog import QuestionCatalog
from backend.question_agent.generator import QuestionGeneratorEngine
from backend.llm_client import LLMClient, default_llm_client

logger = logging.getLogger(__name__)


class ResumeAdaptiveQuestionAgent:
    """
    Unified agent coordinating Resume Intelligence and Adaptive Question Generation.
    Integrates seamlessly with existing InterviewEngine and SessionManager.
    """

    def __init__(
        self,
        llm_client: Optional[LLMClient] = None,
        catalog: Optional[QuestionCatalog] = None,
        history_store: Optional[CandidateQuestionHistoryStore] = None,
    ):
        self.llm_client = llm_client or default_llm_client
        self.catalog = catalog or QuestionCatalog()
        self.history_store = history_store or CandidateQuestionHistoryStore()
        self.generator = QuestionGeneratorEngine(llm_client=self.llm_client, catalog=self.catalog)

    # =========================================================================
    # 1. RESUME INTELLIGENCE & SKILL PROFILING
    # =========================================================================

    def analyze_resume(self, resume_profile: Dict[str, Any]) -> ResumeIntelligenceProfile:
        """Extracts structured, grounded intelligence from candidate resume."""
        return ResumeIntelligenceEngine.extract_intelligence(resume_profile)

    # =========================================================================
    # 2. CANDIDATE-SPECIFIC INTERVIEW BLUEPRINT
    # =========================================================================

    def create_blueprint(
        self,
        resume_profile: Optional[Dict[str, Any]] = None,
        target_role: str = "Python Developer",
        interview_mode: str = "mock",
        difficulty_mode: str = "adaptive",
        target_track: Optional[str] = None,
        tech_stack: Optional[str] = None,
        max_questions: int = 5,
        candidate_id: Optional[str] = None,
        required_job_skills: Optional[List[str]] = None,
    ) -> InterviewBlueprint:
        """
        Builds a candidate-specific interview blueprint before interview starts.
        Prioritizes top skills and projects for the selected 5-10 question interview length.
        """
        # Strictly enforce 5 to 10 questions limit
        num_questions = max(5, min(10, int(max_questions)))

        # 1. Parse resume intelligence if available
        intel_profile: Optional[ResumeIntelligenceProfile] = None
        if resume_profile:
            intel_profile = self.analyze_resume(resume_profile)

        # 2. Determine track
        track = target_track
        if not track:
            if resume_profile and resume_profile.get("routed_track"):
                track = resume_profile["routed_track"]
            elif "fullstack" in target_role.lower() or "frontend" in target_role.lower() or "web" in target_role.lower():
                track = "fullstack"
            else:
                track = "python"

        # 3. Ingest candidate's cross-session question history from Layer 4 store
        prior_texts: List[str] = []
        prior_fingerprints: List[str] = []
        if candidate_id:
            prior_records = self.history_store.get_recent_questions(candidate_id, limit=30)
            for r in prior_records:
                prior_texts.append(r["question_text"])
                prior_fingerprints.append(r["fingerprint"])

        # 4. Select topics based on track and resume evidence
        planned_topics: List[str] = []
        if track == "python":
            from backend.interview_plan import PYTHON_SKILL_TOPIC_RULES
            rules = PYTHON_SKILL_TOPIC_RULES
        else:
            from backend.interview_plan import FULLSTACK_SKILL_TOPIC_RULES
            rules = FULLSTACK_SKILL_TOPIC_RULES

        matched_topics: List[str] = []
        if intel_profile:
            claimed_lower = {s.lower() for s in (intel_profile.verified_skills + intel_profile.unverified_claims)}
            for r in rules:
                if any(sk.lower() in claimed_lower for sk in r["skills"]):
                    if r["topic"] not in matched_topics:
                        matched_topics.append(r["topic"])

        for t in matched_topics:
            if len(planned_topics) < num_questions and t not in planned_topics:
                planned_topics.append(t)

        # Fill remaining slots with default and track rules
        for r in rules:
            if len(planned_topics) < num_questions and r.get("default", False) and r["topic"] not in planned_topics:
                planned_topics.append(r["topic"])

        for r in rules:
            if len(planned_topics) < num_questions and r["topic"] not in planned_topics:
                planned_topics.append(r["topic"])

        # 5. Formulate planned format rotation across the 12 formats
        # Balanced format distribution:
        # Q1: Technical Fundamentals / Conceptual
        # Q2: Practical Implementation or Code Writing
        # Q3: Project Deep Dive (if projects exist) or Applied Real-World
        # Q4: Code Debugging or Output Prediction
        # Q5: Design & Architecture or Trade-off Decision
        # Q6-10: Rotated troubleshooting, scenario, and deeper implementation
        planned_formats: List[QuestionFormat] = []
        has_projects = bool(intel_profile and intel_profile.projects)

        format_template = [
            QuestionFormat.TECHNICAL_FUNDAMENTALS,
            QuestionFormat.CODE_WRITING,
            QuestionFormat.PROJECT_DEEP_DIVE if has_projects else QuestionFormat.APPLIED_REAL_WORLD,
            QuestionFormat.CODE_DEBUGGING,
            QuestionFormat.DESIGN_ARCHITECTURE,
            QuestionFormat.TRADEOFF_DECISION,
            QuestionFormat.OUTPUT_PREDICTION,
            QuestionFormat.TROUBLESHOOTING_SCENARIO,
            QuestionFormat.PRACTICAL_IMPLEMENTATION,
            QuestionFormat.CONCEPTUAL_EXPLANATION,
        ]

        for i in range(num_questions):
            planned_formats.append(format_template[i % len(format_template)])

        # 6. Difficulty progression baseline
        diff_progression: List[DifficultyLevel] = []
        base_diff = DifficultyLevel.INTERMEDIATE
        if difficulty_mode == "beginner":
            base_diff = DifficultyLevel.BEGINNER
        elif difficulty_mode == "advanced":
            base_diff = DifficultyLevel.ADVANCED
        elif difficulty_mode == "adaptive":
            exp = intel_profile.total_experience_years if intel_profile else 0.0
            base_diff = DifficultyLevel.ADVANCED if exp >= 4.0 else (DifficultyLevel.INTERMEDIATE if exp >= 1.5 else DifficultyLevel.BEGINNER)

        for _ in range(num_questions):
            diff_progression.append(base_diff)

        cand_name = intel_profile.candidate_name if intel_profile else "Candidate"
        summary = (
            f"Adaptive interview blueprint generated for {cand_name} ({target_role}, {track} track). "
            f"Allocated {num_questions} questions across {len(planned_topics)} topics covering "
            f"{len(planned_formats)} distinct question modalities."
        )

        return InterviewBlueprint(
            candidate_id=candidate_id,
            target_role=target_role,
            interview_mode=interview_mode,
            difficulty_mode=difficulty_mode,
            target_track=track,
            tech_stack=tech_stack,
            max_questions=num_questions,
            resume_profile=intel_profile,
            required_job_skills=required_job_skills or [],
            investigate_projects=intel_profile.projects if intel_profile else [],
            planned_topics=planned_topics[:num_questions],
            planned_formats=planned_formats,
            difficulty_progression=diff_progression,
            prior_candidate_fingerprints=prior_fingerprints,
            summary=summary,
        )

    # =========================================================================
    # 3. DYNAMIC QUESTION GENERATION & SELECTION
    # =========================================================================

    def select_or_generate_question(
        self,
        blueprint: InterviewBlueprint,
        topic: str,
        competency: str,
        difficulty: DifficultyLevel,
        question_number: int,
        session_asked_texts: List[str],
        candidate_context: Optional[Dict[str, Any]] = None,
        use_dynamic: bool = True,
        session_asked_ids: Optional[Set[str]] = None,
    ) -> Tuple[Question, str]:
        """
        Generates or selects candidate question using Layer 1-6 pipeline.
        Records question into session and cross-session candidate history.
        """
        # Determine format for this question slot from blueprint
        fmt_idx = min(question_number - 1, len(blueprint.planned_formats) - 1)
        target_format = blueprint.planned_formats[fmt_idx] if blueprint.planned_formats else QuestionFormat.CONCEPTUAL_EXPLANATION

        # Identify project to ground in if format is PROJECT_DEEP_DIVE
        target_project: Optional[str] = None
        if target_format == QuestionFormat.PROJECT_DEEP_DIVE and blueprint.investigate_projects:
            proj = blueprint.investigate_projects[(question_number - 1) % len(blueprint.investigate_projects)]
            target_project = proj.title

        prior_texts: List[str] = []
        if blueprint.candidate_id:
            prior_records = self.history_store.get_recent_questions(blueprint.candidate_id, limit=30)
            prior_texts = [r["question_text"] for r in prior_records]

        # Execute candidate generation
        question, reason, candidate = self.generator.generate_candidate_question(
            blueprint=blueprint,
            topic=topic,
            competency=competency,
            difficulty=difficulty,
            question_format=target_format,
            session_asked_texts=session_asked_texts,
            prior_candidate_texts=prior_texts,
            candidate_context=candidate_context,
            target_project=target_project,
            use_llm=use_dynamic,
            session_asked_ids=session_asked_ids,
        )

        # Record question into cross-session store (Layer 4)
        if blueprint.candidate_id and question:
            self.history_store.record_question(
                candidate_id=blueprint.candidate_id,
                session_id=blueprint.blueprint_id,
                question_id=question.id,
                question_text=question.text,
                topic=question.topic,
            )

        # Ingest into reusable catalog if newly generated and validated
        if candidate.source_type == "model_generated" and candidate.validation.is_valid:
            from backend.question_agent.models import CatalogQuestionEntry
            entry = CatalogQuestionEntry(
                id=question.id,
                role=blueprint.target_role,
                track=blueprint.target_track,
                technology=(blueprint.tech_stack or blueprint.target_track),
                skill=question.competency,
                subtopic=question.topic,
                topic=question.topic,
                difficulty=question.difficulty,
                question_format=target_format,
                resume_relevance_keywords=[blueprint.target_track, question.topic.lower()],
                question=question,
                source_type="model_generated",
                validation_status="validated",
                usage_count=1,
                last_used_timestamp=time.time(),
                fingerprint=QuestionDiversityEngine.generate_fingerprint(question.text),
            )
            self.catalog.add_entry(entry)

        return question, reason

    # =========================================================================
    # 4. ADAPTIVE FOLLOW-UP GENERATION
    # =========================================================================

    def generate_adaptive_follow_up(
        self,
        blueprint: InterviewBlueprint,
        last_question: Question,
        last_evaluation: EvaluationResult,
        session_asked_texts: List[str],
        session_asked_ids: Optional[Set[str]] = None,
    ) -> Optional[Tuple[Question, str]]:
        """
        Generates an adaptive follow-up question when candidate performance indicates:
        - Specific missing concepts or misconceptions
        - Ambiguous answer requiring clarification
        - Partial score (40-70%) on critical technical topic
        Returns None if follow-up is not warranted, allowing topic progression.
        """
        # Determine if follow-up is warranted
        needs_follow_up = False
        reasons_for_followup = []

        if last_evaluation.is_ambiguous:
            needs_follow_up = True
            reasons_for_followup.append("resolve ambiguity in candidate's response")

        if last_evaluation.missing_concepts:
            needs_follow_up = True
            reasons_for_followup.append(f"probe missing concept: {last_evaluation.missing_concepts[0]}")

        if last_evaluation.incorrect_claims:
            needs_follow_up = True
            reasons_for_followup.append(f"address misconception: {last_evaluation.incorrect_claims[0]}")

        # If answer was completely answered (>85%) or completely missed (<20%), move to next topic
        if last_evaluation.percentage >= 85.0 or last_evaluation.percentage < 25.0:
            needs_follow_up = False

        if not needs_follow_up:
            return None

        # Build candidate context specific to follow-up
        context = {
            "missing_concepts": list(last_evaluation.missing_concepts),
            "misconceptions": list(last_evaluation.incorrect_claims),
            "last_score": last_evaluation.percentage,
            "previous_question_text": last_question.text,
            "previous_answer_summary": last_evaluation.summary_explanation,
        }

        followup_reason_str = ", ".join(reasons_for_followup)
        logger.info("[ADAPTIVE_FOLLOWUP] Generating targeted follow-up to %s", followup_reason_str)

        try:
            q, reason, _ = self.generator.generate_candidate_question(
                blueprint=blueprint,
                topic=last_question.topic,
                competency=last_question.competency,
                difficulty=last_question.difficulty,
                question_format=QuestionFormat.ADAPTIVE_FOLLOW_UP,
                session_asked_texts=session_asked_texts,
                candidate_context=context,
                use_llm=True,
                session_asked_ids=session_asked_ids,
            )
            q.follow_up_to = last_question.id
            followup_reason = (
                f"Targeted adaptive follow-up on '{last_question.topic}' to {followup_reason_str}."
            )
            return q, followup_reason
        except Exception as exc:
            logger.warning("Adaptive follow-up generation failed: %s", exc)
            return None


# Global singleton instance
default_question_agent = ResumeAdaptiveQuestionAgent()
