"""
Full-Stack Interviewer Model Adapter.
Implements the BaseInterviewer interface for the Full-Stack domain.
Orchestrates:
- Full-Stack Question Bank
- Full-Stack Question Generator
- Full-Stack Adaptive Engine
- Full-Stack Multi-Language Evaluation Engine
"""

from typing import Dict, Any, List, Optional, Tuple
from backend.interviewers.base import BaseInterviewer
from backend.models import (
    Question,
    InterviewMode,
    EvaluationResult,
)
from backend.fullstack.adaptive_engine import (
    FullStackAdaptiveEngine,
    FullStackCompetencyTracker,
)
from backend.fullstack.evaluator import FullStackEvaluationEngine
from backend.fullstack.question_bank import (
    get_all_fullstack_topics,
    get_all_fullstack_competencies,
    get_all_fullstack_questions,
)


class FullStackInterviewer(BaseInterviewer):
    """Independent interviewer model for Full-Stack Engineering."""

    def __init__(self, eval_engine: Optional[FullStackEvaluationEngine] = None):
        self.eval_engine = eval_engine or FullStackEvaluationEngine()

    def select_first_question(
        self,
        mode: InterviewMode,
        topics: Optional[List[str]] = None,
        use_dynamic: bool = True,
        tech_stack: Optional[str] = None,
    ) -> Tuple[Question, str]:
        return FullStackAdaptiveEngine.select_first_question(
            mode=mode,
            topics=topics,
            use_dynamic=use_dynamic,
            tech_stack=tech_stack,
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
        return FullStackAdaptiveEngine.select_next_question(
            tracker=tracker,
            mode=mode,
            allowed_topics=allowed_topics,
            last_question=last_question,
            last_evaluation=last_evaluation,
            question_number=question_number,
            session_asked_texts=session_asked_texts,
            use_dynamic=use_dynamic,
            tech_stack=tech_stack,
        )

    def get_topics_and_competencies(self) -> Dict[str, Any]:
        return {
            "track": "fullstack",
            "name": "Full-Stack Interviewer",
            "topics": get_all_fullstack_topics(),
            "competencies": get_all_fullstack_competencies(),
            "total_questions": len(get_all_fullstack_questions()),
            "tech_stacks": [
                {
                    "id": "react_node_sql",
                    "name": "React + Node.js + Express + SQL",
                    "description": "Full-stack web application development with React frontend, Node/Express API, and relational database.",
                },
                {
                    "id": "react_fastapi_postgres",
                    "name": "React + FastAPI + PostgreSQL",
                    "description": "Modern async stack with React frontend, Python FastAPI backend, and PostgreSQL database.",
                },
                {
                    "id": "fundamentals",
                    "name": "Full-Stack Fundamentals",
                    "description": "Balanced coverage of HTML/CSS, Core JavaScript, REST APIs, and SQL modeling.",
                },
                {
                    "id": "frontend_heavy",
                    "name": "Frontend Specialist (HTML/CSS + JS + React)",
                    "description": "Deep focus on client-side rendering, component lifecycle, styling, and browser mechanics.",
                },
                {
                    "id": "backend_heavy",
                    "name": "Backend Specialist (Node/APIs + SQL + Architecture)",
                    "description": "Deep focus on API design, database schemas, authentication, and system scalability.",
                },
            ],
        }

    def create_tracker(self) -> FullStackCompetencyTracker:
        return FullStackCompetencyTracker()
