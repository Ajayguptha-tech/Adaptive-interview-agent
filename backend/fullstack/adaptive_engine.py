"""
Adaptive question selection and competency tracking for Full-Stack Interviews.
Manages candidate mastery estimation across frontend, backend, APIs, databases,
and system architecture with topic balancing and difficulty progression.
"""

from typing import Dict, List, Optional, Tuple, Set, Any
from backend.models import (
    Question,
    DifficultyLevel,
    InterviewMode,
    QuestionType,
    EvaluationResult,
)
from backend.fullstack.question_bank import (
    FULLSTACK_QUESTION_BANK,
    get_all_fullstack_questions,
    get_all_fullstack_topics,
)

TECH_STACK_TOPICS: Dict[str, List[str]] = {
    "react_node_sql": [
        "React & Component Architecture",
        "JavaScript Core",
        "Backend & REST APIs",
        "SQL & Databases",
        "Full-Stack Integration & Architecture",
    ],
    "react_fastapi_postgres": [
        "React & Component Architecture",
        "JavaScript Core",
        "Backend & REST APIs",
        "SQL & Databases",
        "Full-Stack Integration & Architecture",
    ],
    "frontend_heavy": [
        "HTML & Semantic Web",
        "CSS Layout & Box Model",
        "JavaScript Core",
        "React & Component Architecture",
    ],
    "backend_heavy": [
        "JavaScript Core",
        "Backend & REST APIs",
        "SQL & Databases",
        "Full-Stack Integration & Architecture",
    ],
    "fundamentals": [
        "HTML & Semantic Web",
        "CSS Layout & Box Model",
        "JavaScript Core",
        "Backend & REST APIs",
        "SQL & Databases",
        "Full-Stack Integration & Architecture",
    ],
}


class FullStackCompetencyTracker:
    """Tracks demonstrated candidate competency across all Full-Stack layers."""

    def __init__(self):
        self.asked_question_ids: Set[str] = set()
        self.topic_scores: Dict[str, Dict[str, float]] = {}
        self.competency_scores: Dict[str, Dict[str, float]] = {}
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
        """Records evaluation outcomes and updates competency metrics."""
        self.asked_question_ids.add(question.id)
        self.recent_percentages.append(evaluation.percentage)

        # Update topic metrics
        t = question.topic
        if t not in self.topic_scores:
            self.topic_scores[t] = {"earned": 0.0, "max": 0.0, "count": 0}
        self.topic_scores[t]["earned"] += evaluation.awarded_marks
        self.topic_scores[t]["max"] += evaluation.max_marks
        self.topic_scores[t]["count"] += 1

        # Update competency metrics
        c = question.competency
        if c not in self.competency_scores:
            self.competency_scores[c] = {"earned": 0.0, "max": 0.0, "count": 0}
        self.competency_scores[c]["earned"] += evaluation.awarded_marks
        self.competency_scores[c]["max"] += evaluation.max_marks
        self.competency_scores[c]["count"] += 1

        # Update difficulty metrics
        d_val = question.difficulty.value
        if d_val in self.difficulty_scores:
            self.difficulty_scores[d_val]["earned"] += evaluation.awarded_marks
            self.difficulty_scores[d_val]["max"] += evaluation.max_marks
            self.difficulty_scores[d_val]["count"] += 1

        # Track concepts
        for item in evaluation.demonstrated_concepts:
            if item not in self.demonstrated_concepts:
                self.demonstrated_concepts.append(item)
        for item in evaluation.missing_concepts:
            if item not in self.missing_concepts:
                self.missing_concepts.append(item)
        for item in evaluation.incorrect_claims:
            if item not in self.misconceptions:
                self.misconceptions.append(item)

    def get_unassessed_topics(self, allowed_topics: Optional[List[str]] = None) -> List[str]:
        candidates = allowed_topics if allowed_topics else get_all_fullstack_topics()
        return [t for t in candidates if t not in self.topic_scores]


class FullStackAdaptiveEngine:
    """Selects and sequences Full-Stack interview questions."""

    @classmethod
    def choose_target_question_type(
        cls,
        question_number: int,
        last_question: Optional[Question] = None,
        last_evaluation: Optional[EvaluationResult] = None,
    ) -> QuestionType:
        """Adapts question modalities based on candidate performance."""
        if question_number == 1:
            return QuestionType.CONCEPTUAL

        if last_evaluation and last_question:
            score = last_evaluation.percentage
            last_type = last_question.question_type

            # Strong: advance to practical coding or multi-layer scenario
            if score >= 75.0:
                if last_type in (QuestionType.CONCEPTUAL, QuestionType.CODE_OUTPUT):
                    return QuestionType.CODE_WRITING
                elif last_type == QuestionType.CODE_WRITING:
                    return QuestionType.SCENARIO
                else:
                    return QuestionType.CODE_OUTPUT

            # Struggling: diagnostic or code output
            elif score < 40.0:
                if last_type in (QuestionType.CODE_WRITING, QuestionType.SCENARIO, QuestionType.DEBUGGING):
                    return QuestionType.CONCEPTUAL
                else:
                    return QuestionType.CODE_OUTPUT
            else:
                if last_type == QuestionType.CONCEPTUAL:
                    return QuestionType.CODE_OUTPUT
                elif last_type == QuestionType.CODE_OUTPUT:
                    return QuestionType.CODE_WRITING
                else:
                    return QuestionType.DEBUGGING

        # Fallback rotation
        rotation = [
            QuestionType.CONCEPTUAL,
            QuestionType.CODE_OUTPUT,
            QuestionType.CODE_WRITING,
            QuestionType.SCENARIO,
            QuestionType.DEBUGGING,
        ]
        return rotation[(question_number - 1) % len(rotation)]

    @classmethod
    def select_first_question(
        cls,
        mode: InterviewMode,
        topics: Optional[List[str]] = None,
        use_dynamic: bool = True,
        tech_stack: Optional[str] = None,
    ) -> Tuple[Question, str]:
        from backend.fullstack.question_generator import default_fullstack_generator

        target_diff = {
            InterviewMode.BEGINNER: DifficultyLevel.BEGINNER,
            InterviewMode.INTERMEDIATE: DifficultyLevel.INTERMEDIATE,
            InterviewMode.ADVANCED: DifficultyLevel.ADVANCED,
            InterviewMode.ADAPTIVE: DifficultyLevel.BEGINNER,
        }.get(mode, DifficultyLevel.BEGINNER)

        candidate_topics = topics or get_all_fullstack_topics()
        target_topic = candidate_topics[0]

        chosen, gen_reason = default_fullstack_generator.generate_or_select_question(
            topic=target_topic,
            competency="Full-Stack Technical Competency",
            difficulty=target_diff,
            question_type=QuestionType.CONCEPTUAL,
            session_asked_ids=set(),
            use_llm=use_dynamic,
            tech_stack=tech_stack,
        )

        reason = (
            f"Starting Full-Stack assessment in {mode.value} mode with foundational "
            f"{chosen.question_type.value} question on '{chosen.topic}' to establish baseline competency."
        )
        return chosen, reason

    @classmethod
    def select_next_question(
        cls,
        tracker: FullStackCompetencyTracker,
        mode: InterviewMode,
        allowed_topics: Optional[List[str]] = None,
        last_question: Optional[Question] = None,
        last_evaluation: Optional[EvaluationResult] = None,
        question_number: int = 2,
        session_asked_texts: Optional[List[str]] = None,
        use_dynamic: bool = True,
        tech_stack: Optional[str] = None,
    ) -> Tuple[Optional[Question], str]:
        from backend.fullstack.question_generator import default_fullstack_generator

        session_asked_texts = session_asked_texts or []
        target_diff = tracker.current_difficulty
        reason_diff_change = ""

        # 1. Adapt difficulty
        if mode == InterviewMode.ADAPTIVE and last_evaluation:
            score = last_evaluation.percentage
            if score >= 80.0:
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
                        reason_diff_change = "Maintaining intermediate level to consolidate high performance."
            elif score < 40.0:
                if tracker.current_difficulty == DifficultyLevel.ADVANCED:
                    target_diff = DifficultyLevel.INTERMEDIATE
                    tracker.current_difficulty = DifficultyLevel.INTERMEDIATE
                    reason_diff_change = "Stepping down to intermediate after candidate struggled with advanced question."
                elif tracker.current_difficulty == DifficultyLevel.INTERMEDIATE:
                    target_diff = DifficultyLevel.BEGINNER
                    tracker.current_difficulty = DifficultyLevel.BEGINNER
                    reason_diff_change = "Stepping down to beginner to diagnose prerequisite understanding."
                else:
                    reason_diff_change = "Maintaining beginner level to build foundational confidence."
            else:
                reason_diff_change = f"Maintaining {target_diff.value} level following steady performance ({score:.0f}%)."

        # 2. Topic balancing: prioritize unassessed topics
        unassessed = tracker.get_unassessed_topics(allowed_topics)
        if unassessed:
            target_topic = unassessed[0]
        elif allowed_topics:
            target_topic = allowed_topics[(question_number - 1) % len(allowed_topics)]
        else:
            all_t = get_all_fullstack_topics()
            target_topic = all_t[(question_number - 1) % len(all_t)]

        # 3. Choose target question type
        target_type = cls.choose_target_question_type(
            question_number=question_number,
            last_question=last_question,
            last_evaluation=last_evaluation,
        )

        # 4. Context for candidate-specific generation
        candidate_context = {
            "missing_concepts": list(tracker.missing_concepts),
            "demonstrated_concepts": list(tracker.demonstrated_concepts),
            "misconceptions": list(tracker.misconceptions),
            "last_score": last_evaluation.percentage if last_evaluation else None,
            "tech_stack": tech_stack,
        }

        # 5. Generate or select question
        chosen, gen_reason = default_fullstack_generator.generate_or_select_question(
            topic=target_topic,
            competency="Full-Stack Engineering",
            difficulty=target_diff,
            question_type=target_type,
            session_asked_ids=tracker.asked_question_ids,
            session_asked_texts=session_asked_texts,
            candidate_context=candidate_context,
            use_llm=use_dynamic,
            tech_stack=tech_stack,
        )

        full_reason = f"{reason_diff_change} {gen_reason}".strip()
        return chosen, full_reason
