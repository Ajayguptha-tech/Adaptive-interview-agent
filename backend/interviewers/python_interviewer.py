"""
Python Interviewer Adapter.
Wraps the existing Python Question Bank, Evaluation Engine,
and Adaptive Engine under the BaseInterviewer interface.
Preserves 100% of existing Python interviewer behavior and tests.
"""

from typing import Dict, Any, List, Optional, Tuple
from backend.interviewers.base import BaseInterviewer
from backend.models import (
    Question,
    InterviewMode,
    EvaluationResult,
)
from backend.adaptive_engine import AdaptiveEngine, CompetencyTracker
from backend.evaluator import EvaluationEngine, default_llm_client
from backend.question_bank import (
    get_all_topics,
    get_all_competencies,
    get_all_questions,
)


class PythonInterviewer(BaseInterviewer):
    """Adapter for existing Python interviewer systems."""

    def __init__(self, eval_engine: Optional[EvaluationEngine] = None):
        self.eval_engine = eval_engine or EvaluationEngine()

    def select_first_question(
        self,
        mode: InterviewMode,
        topics: Optional[List[str]] = None,
        use_dynamic: bool = True,
        tech_stack: Optional[str] = None,
    ) -> Tuple[Question, str]:
        return AdaptiveEngine.select_first_question(
            mode=mode,
            topics=topics,
            use_dynamic=use_dynamic,
        )

    def evaluate_answer(
        self,
        question: Question,
        candidate_answer: str,
    ) -> EvaluationResult:
        return self.eval_engine.evaluate_answer(
            question=question,
            candidate_answer=candidate_answer,
        )

    def select_next_question(
        self,
        tracker: Any,
        mode: InterviewMode,
        allowed_topics: Optional[List[str]] = None,
        last_question: Optional[Question] = None,
        last_evaluation: Optional[EvaluationResult] = None,
        question_number: int = 2,
        session_asked_texts: Optional[List[str]] = None,
        use_dynamic: bool = True,
        tech_stack: Optional[str] = None,
    ) -> Tuple[Optional[Question], str]:
        return AdaptiveEngine.select_next_question(
            tracker=tracker,
            mode=mode,
            allowed_topics=allowed_topics,
            last_question=last_question,
            last_evaluation=last_evaluation,
            question_number=question_number,
            session_asked_texts=session_asked_texts,
            use_dynamic=use_dynamic,
        )

    def get_topics_and_competencies(self) -> Dict[str, Any]:
        return {
            "track": "python",
            "name": "Python Interviewer",
            "topics": get_all_topics(),
            "competencies": get_all_competencies(),
            "total_questions": len(get_all_questions()),
        }

    def create_tracker(self) -> CompetencyTracker:
        return CompetencyTracker()
