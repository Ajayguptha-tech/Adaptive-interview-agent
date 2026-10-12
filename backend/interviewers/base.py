"""
Abstract base class for domain-specific technical interviewers.
Defines the common interface shared by Python and Full-Stack interviewers.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Tuple
from backend.models import (
    Question,
    InterviewMode,
    EvaluationResult,
)


class BaseInterviewer(ABC):
    """Contract for independent interviewer models."""

    @abstractmethod
    def select_first_question(
        self,
        mode: InterviewMode,
        topics: Optional[List[str]] = None,
        use_dynamic: bool = True,
        tech_stack: Optional[str] = None,
    ) -> Tuple[Question, str]:
        """Selects or generates the opening question with transparency rationale."""
        pass

    @abstractmethod
    def evaluate_answer(
        self,
        question: Question,
        candidate_answer: str,
    ) -> EvaluationResult:
        """Evaluates candidate response against rubrics, tests, and outputs."""
        pass

    @abstractmethod
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
        """Selects or generates the next question adaptively based on demonstrated understanding."""
        pass

    @abstractmethod
    def get_topics_and_competencies(self) -> Dict[str, Any]:
        """Returns topics, competencies, and available question bank summary."""
        pass

    @abstractmethod
    def create_tracker(self) -> Any:
        """Instantiates an independent competency tracker for a new session."""
        pass
