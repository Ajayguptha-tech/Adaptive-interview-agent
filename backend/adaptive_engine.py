"""
Adaptive question selection and competency tracking engine.
Manages candidate mastery estimation, gradual difficulty transitions,
topic balancing, misconception tracking, and reason generation.
"""

from typing import Dict, List, Optional, Tuple, Set
from backend.models import (
    Question,
    DifficultyLevel,
    InterviewMode,
    QuestionType,
    EvaluationResult,
)
from backend.question_bank import (
    QUESTION_BANK,
    get_all_questions,
    get_all_topics,
)
from backend.question_generator import default_question_generator


class CompetencyTracker:
    """
    Tracks demonstrated candidate competency, topic coverage,
    difficulty distribution, and identified misconceptions.
    """

    def __init__(self):
        self.asked_question_ids: Set[str] = set()
        self.topic_scores: Dict[str, Dict[str, float]] = {}  # topic -> {earned, max, count}
        self.competency_scores: Dict[str, Dict[str, float]] = {}  # competency -> {earned, max, count}
        self.difficulty_scores: Dict[str, Dict[str, float]] = {
            DifficultyLevel.BEGINNER.value: {"earned": 0.0, "max": 0.0, "count": 0},
            DifficultyLevel.INTERMEDIATE.value: {"earned": 0.0, "max": 0.0, "count": 0},
            DifficultyLevel.ADVANCED.value: {"earned": 0.0, "max": 0.0, "count": 0},
        }
        self.demonstrated_concepts: List[str] = []
        self.missing_concepts: List[str] = []
        self.misconceptions: List[str] = []
        self.recent_percentages: List[float] = []
        self.current_difficulty: DifficultyLevel = DifficultyLevel.BEGINNER

    def record_answer(self, question: Question, evaluation: EvaluationResult):
        """Updates internal state with the evaluated question and score."""
        self.asked_question_ids.add(question.id)

        # Topic tracking
        t_stats = self.topic_scores.setdefault(
            question.topic, {"earned": 0.0, "max": 0.0, "count": 0}
        )
        t_stats["earned"] += evaluation.awarded_marks
        t_stats["max"] += evaluation.max_marks
        t_stats["count"] += 1

        # Competency tracking
        c_stats = self.competency_scores.setdefault(
            question.competency, {"earned": 0.0, "max": 0.0, "count": 0}
        )
        c_stats["earned"] += evaluation.awarded_marks
        c_stats["max"] += evaluation.max_marks
        c_stats["count"] += 1

        # Difficulty tracking
        d_stats = self.difficulty_scores.setdefault(
            question.difficulty.value, {"earned": 0.0, "max": 0.0, "count": 0}
        )
        d_stats["earned"] += evaluation.awarded_marks
        d_stats["max"] += evaluation.max_marks
        d_stats["count"] += 1

        # Concepts and misconceptions
        for c in evaluation.demonstrated_concepts:
            if c not in self.demonstrated_concepts:
                self.demonstrated_concepts.append(c)

        for m in evaluation.missing_concepts:
            if m not in self.missing_concepts:
                self.missing_concepts.append(m)

        for claim in evaluation.incorrect_claims:
            self.misconceptions.append(claim)

        # Rolling percentage history
        self.recent_percentages.append(evaluation.percentage)

    def get_unassessed_topics(self, allowed_topics: Optional[List[str]] = None) -> List[str]:
        """Returns list of topics that haven't been asked yet."""
        all_topics = allowed_topics if allowed_topics else get_all_topics()
        return [t for t in all_topics if t not in self.topic_scores]

    def get_mastery_percentage(self) -> float:
        """Returns overall cumulative score percentage so far."""
        total_earned = sum(s["earned"] for s in self.topic_scores.values())
        total_max = sum(s["max"] for s in self.topic_scores.values())
        if total_max == 0:
            return 0.0
        return round((total_earned / total_max) * 100.0, 2)


class AdaptiveEngine:
    """
    Determines next question based on interview mode, competency tracker,
    previous performance, topic balancing rules, and dynamic generation.
    """

    @classmethod
    def choose_target_question_type(
        cls,
        question_number: int,
        last_question: Optional[Question] = None,
        last_evaluation: Optional[EvaluationResult] = None,
    ) -> QuestionType:
        """
        Dynamically selects question modality based on candidate performance:
        - If candidate performs strongly on conceptual theory (>=75%), challenges them with
          practical code writing or output prediction.
        - If candidate struggles (<40%), eases back to diagnostic conceptual theory or guided debugging.
        - If steady (40-74%), tests code prediction or debugging to isolate specific gaps.
        """
        if question_number == 1:
            return QuestionType.CONCEPTUAL

        if last_evaluation and last_question:
            score = last_evaluation.percentage
            last_type = last_question.question_type

            # Strong performance: escalate to hands-on implementation or advanced analysis
            if score >= 75.0:
                if last_type in (QuestionType.CONCEPTUAL, QuestionType.SCENARIO, QuestionType.PRACTICAL):
                    return QuestionType.CODE_WRITING
                elif last_type == QuestionType.CODE_WRITING:
                    return QuestionType.CODE_OUTPUT
                else:
                    return QuestionType.CONCEPTUAL

            # Struggling: step down to diagnostic or concrete prediction
            elif score < 40.0:
                if last_type in (QuestionType.CODE_WRITING, QuestionType.DEBUGGING):
                    return QuestionType.CONCEPTUAL  # Probe prerequisite concepts
                else:
                    return QuestionType.CODE_OUTPUT  # Concrete trace rather than open theory

            # Steady intermediate
            else:
                if last_type == QuestionType.CONCEPTUAL:
                    return QuestionType.CODE_OUTPUT
                elif last_type == QuestionType.CODE_OUTPUT:
                    return QuestionType.DEBUGGING
                else:
                    return QuestionType.CONCEPTUAL

        # Fallback multi-modal rotation
        cycle = [
            QuestionType.CONCEPTUAL,
            QuestionType.CODE_OUTPUT,
            QuestionType.CODE_WRITING,
            QuestionType.CONCEPTUAL,
            QuestionType.DEBUGGING,
        ]
        return cycle[(question_number - 1) % len(cycle)]

    @classmethod
    def select_first_question(
        cls,
        mode: InterviewMode,
        topics: Optional[List[str]] = None,
        use_dynamic: bool = False,
        tech_stack: Optional[str] = None,
        **kwargs,
    ) -> Tuple[Question, str]:
        """Selects or generates the opening question and provides a transparent rationale."""
        target_diff = {
            InterviewMode.BEGINNER: DifficultyLevel.BEGINNER,
            InterviewMode.INTERMEDIATE: DifficultyLevel.INTERMEDIATE,
            InterviewMode.ADVANCED: DifficultyLevel.ADVANCED,
            InterviewMode.ADAPTIVE: DifficultyLevel.BEGINNER,
        }[mode]

        # Choose opening topic grounded in candidate's blueprint or requested topics
        all_topics = get_all_topics()
        chosen_topic = "Data Structures & Mutability"
        if kwargs.get("blueprint") and kwargs["blueprint"].planned_topics:
            if not topics:
                chosen_topic = kwargs["blueprint"].planned_topics[0]
        elif topics:
            all_topics_lower_map = {t.lower(): t for t in all_topics}
            matched = [all_topics_lower_map[t.lower()] for t in topics if t.lower() in all_topics_lower_map]
            if matched:
                chosen_topic = matched[0]
            else:
                chosen_topic = topics[0]

        target_type = QuestionType.CONCEPTUAL

        if use_dynamic:
            from backend.question_agent import default_question_agent
            blueprint = kwargs.get("blueprint")
            if not blueprint:
                blueprint = default_question_agent.create_blueprint(
                    resume_profile=kwargs.get("resume_profile"),
                    target_role=kwargs.get("target_role", "Python Developer"),
                    interview_mode=mode.value,
                    difficulty_mode=mode.value,
                    target_track="python",
                    tech_stack=tech_stack,
                    max_questions=kwargs.get("max_questions", 5),
                    candidate_id=kwargs.get("candidate_id"),
                )
            # Re-check opening topic from newly constructed blueprint if needed
            if not topics and blueprint.planned_topics:
                chosen_topic = blueprint.planned_topics[0]

            chosen, gen_reason = default_question_agent.select_or_generate_question(
                blueprint=blueprint,
                topic=chosen_topic,
                competency=f"{blueprint.target_role} Competency",
                difficulty=target_diff,
                question_number=1,
                session_asked_texts=[],
                use_dynamic=True,
            )
        else:
            chosen, gen_reason = default_question_generator.generate_or_select_question(
                topic=chosen_topic,
                competency="Python Fundamentals",
                difficulty=target_diff,
                question_type=target_type,
                session_asked_ids=set(),
                use_llm=False,
            )

        reason = (
            f"Starting assessment in {mode.value} mode with foundational {chosen.question_type.value} question on "
            f"'{chosen.topic}' to establish baseline competency."
        )
        return chosen, reason

    @classmethod
    def select_next_question(
        cls,
        tracker: CompetencyTracker,
        mode: InterviewMode,
        allowed_topics: Optional[List[str]] = None,
        last_question: Optional[Question] = None,
        last_evaluation: Optional[EvaluationResult] = None,
        question_number: int = 2,
        session_asked_texts: Optional[List[str]] = None,
        use_dynamic: bool = False,
        tech_stack: Optional[str] = None,
        **kwargs,
    ) -> Tuple[Optional[Question], str]:
        """
        Selects or generates next question adaptively based on demonstrated understanding,
        difficulty progression, topic balancing, and candidate-specific weaknesses.
        """
        session_asked_texts = session_asked_texts or []

        # Determine target difficulty
        target_diff = tracker.current_difficulty
        reason_diff_change = ""

        if mode == InterviewMode.ADAPTIVE and last_evaluation:
            last_score = last_evaluation.percentage

            # Strong performance: advance difficulty
            if last_score >= 80.0:
                if tracker.current_difficulty == DifficultyLevel.BEGINNER:
                    target_diff = DifficultyLevel.INTERMEDIATE
                    tracker.current_difficulty = DifficultyLevel.INTERMEDIATE
                    reason_diff_change = "Elevating difficulty to intermediate following strong performance (>=80%)."
                elif tracker.current_difficulty == DifficultyLevel.INTERMEDIATE:
                    if len(tracker.recent_percentages) >= 2 and sum(tracker.recent_percentages[-2:]) / 2 >= 75.0:
                        target_diff = DifficultyLevel.ADVANCED
                        tracker.current_difficulty = DifficultyLevel.ADVANCED
                        reason_diff_change = "Elevating difficulty to advanced based on sustained high performance."
                    else:
                        reason_diff_change = "Continuing at intermediate level to consolidate high performance."

            # Low performance: ease difficulty or diagnostic
            elif last_score < 40.0:
                if tracker.current_difficulty == DifficultyLevel.ADVANCED:
                    target_diff = DifficultyLevel.INTERMEDIATE
                    tracker.current_difficulty = DifficultyLevel.INTERMEDIATE
                    reason_diff_change = "Stepping down to intermediate to verify core principles after candidate struggled with advanced question."
                elif tracker.current_difficulty == DifficultyLevel.INTERMEDIATE:
                    target_diff = DifficultyLevel.BEGINNER
                    tracker.current_difficulty = DifficultyLevel.BEGINNER
                    reason_diff_change = "Stepping down to beginner to diagnose prerequisite understanding."
                else:
                    reason_diff_change = "Maintaining beginner level to build foundational confidence."
            else:
                reason_diff_change = f"Maintaining {target_diff.value} level following steady performance ({last_score:.0f}%)."

        elif mode != InterviewMode.ADAPTIVE:
            target_diff = {
                InterviewMode.BEGINNER: DifficultyLevel.BEGINNER,
                InterviewMode.INTERMEDIATE: DifficultyLevel.INTERMEDIATE,
                InterviewMode.ADVANCED: DifficultyLevel.ADVANCED,
            }.get(mode, DifficultyLevel.BEGINNER)
            tracker.current_difficulty = target_diff

        # Check for targeted follow-up if previous answer was ambiguous
        if last_question and last_evaluation and (last_evaluation.is_ambiguous or 40.0 <= last_evaluation.percentage < 70.0):
            all_bank = get_all_questions()
            follow_ups = [q for q in all_bank if q.follow_up_to == last_question.id and q.id not in tracker.asked_question_ids]
            if follow_ups:
                chosen = follow_ups[0]
                reason = (
                    f"Selected targeted follow-up ({chosen.id}) to probe deeper into "
                    f"'{last_question.topic}' nuances following candidate's response."
                )
                return chosen, reason

        # Candidate adaptive context
        candidate_context = {
            "missing_concepts": list(tracker.missing_concepts),
            "demonstrated_concepts": list(tracker.demonstrated_concepts),
            "misconceptions": list(tracker.misconceptions),
            "last_score": last_evaluation.percentage if last_evaluation else None,
            "last_evaluation_summary": last_evaluation.summary_explanation if last_evaluation else None,
        }

        # Topic Balancing: prioritize unassessed topics matching target difficulty
        unassessed_topics = tracker.get_unassessed_topics(allowed_topics)
        all_bank_questions = get_all_questions()
        matching_diff_topics = [
            t for t in unassessed_topics
            if any(q.topic == t and q.difficulty == target_diff and q.id not in tracker.asked_question_ids for q in all_bank_questions)
        ]
        if matching_diff_topics:
            target_topic = matching_diff_topics[0]
        elif unassessed_topics:
            target_topic = unassessed_topics[0]
        elif allowed_topics:
            target_topic = allowed_topics[(question_number - 1) % len(allowed_topics)]
        else:
            all_topics = get_all_topics()
            target_topic = all_topics[(question_number - 1) % len(all_topics)]

        # Target question type based on candidate performance
        target_type = cls.choose_target_question_type(
            question_number=question_number,
            last_question=last_question,
            last_evaluation=last_evaluation,
        )

        # Generate or select next question
        if use_dynamic:
            from backend.question_agent import default_question_agent
            blueprint = kwargs.get("blueprint")
            if not blueprint:
                blueprint = default_question_agent.create_blueprint(
                    resume_profile=kwargs.get("resume_profile"),
                    target_role=kwargs.get("target_role", "Python Developer"),
                    interview_mode=mode.value,
                    difficulty_mode=mode.value,
                    target_track="python",
                    tech_stack=tech_stack,
                    max_questions=kwargs.get("max_questions", 5),
                    candidate_id=kwargs.get("candidate_id"),
                )
            chosen, gen_reason = default_question_agent.select_or_generate_question(
                blueprint=blueprint,
                topic=target_topic,
                competency="Python Technical Competency",
                difficulty=target_diff,
                question_number=question_number,
                session_asked_texts=session_asked_texts,
                candidate_context=candidate_context,
                use_dynamic=True,
                session_asked_ids=kwargs.get("session_asked_ids") or tracker.asked_question_ids,
            )
        else:
            chosen, gen_reason = default_question_generator.generate_or_select_question(
                topic=target_topic,
                competency="Python Technical Competency",
                difficulty=target_diff,
                question_type=target_type,
                session_asked_ids=tracker.asked_question_ids,
                session_asked_texts=session_asked_texts,
                candidate_context=candidate_context,
                use_llm=False,
            )

        full_reason = f"{reason_diff_change} {gen_reason}".strip()
        return chosen, full_reason

