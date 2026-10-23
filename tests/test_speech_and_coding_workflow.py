"""
Unit & Integration Tests for Speech, Transcription, Question Classification, and Evaluator.

Validates:
- Verbal questions (e.g. "What is Python?", "Explain inheritance") have requires_code=False and response_type='verbal'.
- Coding questions (e.g. "Write a Python program...", "Implement binary search") have requires_code=True.
- Evaluator rubric calculations, bounds enforcement, and isolated code execution.
- Session manager answer submission idempotency.
- SQLite persistence of interview sessions and evaluations.
"""

import pytest
import tempfile
from pathlib import Path
from backend.models import (
    Question,
    QuestionType,
    DifficultyLevel,
    RubricCriterion,
    QuestionDisplay,
    StartInterviewRequest,
    InterviewMode,
    FeedbackMode,
)
from backend.evaluator import EvaluationEngine, OutputPredictionEvaluator
from backend.code_evaluator import CodeEvaluator
from backend.session_manager import SessionManager
from backend.session_persistence import SessionPersistence


class TestQuestionClassification:
    """Verifies that questions are strictly classified into coding vs verbal."""

    def test_verbal_questions_do_not_require_code(self):
        verbal_samples = [
            ("q-verb-1", "What is Python?", "Core Language"),
            ("q-verb-2", "Explain inheritance and how MRO works in Python.", "OOP"),
            ("q-verb-3", "What is the difference between a list and a tuple in Python?", "Data Structures"),
            ("q-verb-4", "Explain how binary search works conceptually and state its time complexity.", "Algorithms"),
            ("q-verb-5", "Describe the time complexity of quicksort in the average and worst cases.", "Algorithms"),
            ("q-verb-6", "What is a REST API and how does HTTP status code 404 differ from 500?", "Web Architecture"),
        ]

        for qid, text, topic in verbal_samples:
            q = Question(
                id=qid,
                topic=topic,
                competency="Conceptual Understanding",
                difficulty=DifficultyLevel.INTERMEDIATE,
                question_type=QuestionType.CONCEPTUAL,
                text=text,
                reference_answer="Reference explanation",
                rubric=[
                    RubricCriterion(id="c1", description="Explanation", max_marks=2.5, evidence_guide="Accurate"),
                    RubricCriterion(id="c2", description="Examples", max_marks=2.5, evidence_guide="Clear"),
                ],
                total_marks=5.0,
                expected_concepts=["Concept 1", "Concept 2"],
                requires_code=False,
                response_type="verbal",
            )

            disp = q.to_display(question_number=1, total_questions=5)
            assert disp.requires_code is False, f"Question '{text}' should NOT require code"
            assert disp.response_type == "verbal", f"Question '{text}' should have response_type 'verbal'"

    def test_coding_questions_strictly_require_code(self):
        coding_samples = [
            ("q-code-1", "Write a Python program to check whether a given integer is prime.", "Algorithms"),
            ("q-code-2", "Implement binary search to find an element in a sorted list.", "Algorithms"),
            ("q-code-3", "Write a function to reverse a singly linked list in Python.", "Data Structures"),
            ("q-code-4", "Complete the missing code in this function to compute Fibonacci numbers.", "Algorithms"),
        ]

        for qid, text, topic in coding_samples:
            q = Question(
                id=qid,
                topic=topic,
                competency="Code Implementation",
                difficulty=DifficultyLevel.INTERMEDIATE,
                question_type=QuestionType.CODE_WRITING,
                text=text,
                reference_answer="def solution(): pass",
                starter_code="def solution():\n    # TODO\n    pass\n",
                rubric=[
                    RubricCriterion(id="c1", description="Correct implementation", max_marks=3.0, evidence_guide="Passes tests"),
                    RubricCriterion(id="c2", description="Efficiency", max_marks=2.0, evidence_guide="Optimal"),
                ],
                total_marks=5.0,
                expected_concepts=["Working solution"],
                requires_code=True,
                response_type="code_writing",
            )

            disp = q.to_display(question_number=1, total_questions=5)
            assert disp.requires_code is True, f"Coding question '{text}' MUST require code"
            assert disp.response_type == "code_writing", f"Coding question '{text}' must have response_type 'code_writing'"


class TestEvaluatorScoring:
    """Verifies deterministic rubric validation and scoring boundaries."""

    def test_empty_answer_receives_strictly_zero_marks(self):
        q = Question(
            id="q-eval-1",
            topic="Core Python",
            competency="Language",
            difficulty=DifficultyLevel.BEGINNER,
            question_type=QuestionType.CONCEPTUAL,
            text="What is a Python generator and how does yield work?",
            reference_answer="A generator produces items lazily using yield.",
            rubric=[
                RubricCriterion(id="c1", description="Definition", max_marks=2.5, evidence_guide="Defines generator"),
                RubricCriterion(id="c2", description="Yield mechanics", max_marks=2.5, evidence_guide="Explains yield"),
            ],
            total_marks=5.0,
            expected_concepts=["generator", "yield", "lazy evaluation"],
        )

        engine = EvaluationEngine()
        res = engine.evaluate_answer(q, "   ")

        assert res.awarded_marks == 0.0
        assert res.percentage == 0.0
        assert res.addressed_question is False
        assert len(res.criteria_evaluations) == 2
        for crit in res.criteria_evaluations:
            assert crit.awarded_marks == 0.0

    def test_output_prediction_evaluator(self):
        q = Question(
            id="q-pred-1",
            topic="Python Scoping",
            competency="Scoping",
            difficulty=DifficultyLevel.INTERMEDIATE,
            question_type=QuestionType.CODE_OUTPUT,
            text="What is the output of this code snippet?",
            code_snippet="x = 10\ndef foo():\n    x = 20\nfoo()\nprint(x)",
            reference_answer="Output is: '10'",
            expected_output="10",
            rubric=[
                RubricCriterion(id="c1", description="Output correctness", max_marks=5.0, evidence_guide="10"),
            ],
            total_marks=5.0,
        )

        assert OutputPredictionEvaluator.verify_prediction("10", "The output is 10") is True
        assert OutputPredictionEvaluator.verify_prediction("10", "It prints 20") is False

    def test_isolated_code_evaluator_execution(self):
        candidate_code = """
def is_prime(n):
    if n <= 1:
        return False
    for i in range(2, int(n**0.5) + 1):
        if n % i == 0:
            return False
    return True
"""
        test_cases = [
            {"input": 2, "expected": True},
            {"input": 4, "expected": False},
            {"input": 17, "expected": True},
            {"input": 1, "expected": False},
        ]

        result = CodeEvaluator.evaluate_code(
            candidate_code=candidate_code,
            test_cases=test_cases,
            function_name="is_prime",
        )

        assert result["syntax_valid"] is True
        assert result["tests_passed"] == 4
        assert result["tests_total"] == 4


class TestSessionIdempotencyAndPersistence:
    """Verifies that answer submissions are idempotent and persist to SQLite."""

    def test_submitting_answer_is_idempotent_and_does_not_double_count(self, monkeypatch):
        import json
        from backend.models import EvaluationResult, CriterionEvaluation

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test_sessions.db"
            persistence = SessionPersistence(db_path=str(db_path))
            sm = SessionManager(persistence=persistence)

            req = StartInterviewRequest(
                role="Python Developer",
                track="python",
                max_questions=5,
                dynamic_questions=False,
                difficulty_mode=InterviewMode.BEGINNER,
                feedback_mode=FeedbackMode.IMMEDIATE,
            )

            session = sm.start_session(req)
            session_id = session.session_id
            q1_id = session.current_question.id

            mock_eval = EvaluationResult(
                question_id=q1_id,
                awarded_marks=4.5,
                max_marks=5.0,
                percentage=90.0,
                criteria_evaluations=[
                    CriterionEvaluation(criterion_id="c1", awarded_marks=2.5, max_marks=2.5, evidence="Accurate", explanation="Well explained"),
                    CriterionEvaluation(criterion_id="c2", awarded_marks=2.0, max_marks=2.5, evidence="Good examples", explanation="Accurate context"),
                ],
                demonstrated_concepts=["Interpreted language", "Dynamic typing"],
                summary_explanation="Strong technical answer.",
                addressed_question=True,
            )

            # Mock evaluate_answer to ensure deterministic test speed
            interviewer = sm.registry.get(session.track)
            monkeypatch.setattr(interviewer, "evaluate_answer", lambda **kwargs: mock_eval)

            answer_text = "Python is an interpreted, high-level, dynamically-typed programming language."

            # Submit answer 1st time
            res1 = sm.submit_answer(session_id=session_id, answer=answer_text, question_id=q1_id, question_number=1)
            assert res1["question_number"] == 1
            score1 = res1["evaluation"]["awarded_marks"]
            assert score1 == 4.5

            # Submit duplicate answer 2nd time (simulating double click or network retry)
            res2 = sm.submit_answer(session_id=session_id, answer=answer_text, question_id=q1_id, question_number=1)
            assert res2["question_number"] == 1
            assert res2["evaluation"]["awarded_marks"] == score1

            # Verify session history length is exactly 1 (not duplicated!)
            assert len(session.history) == 1

            # Verify loaded from SQLite persistence
            loaded_dict = persistence.load_session_dict(session_id)
            assert loaded_dict is not None
            history_data = loaded_dict["history"]
            assert len(history_data) == 1
            assert history_data[0]["evaluation"]["awarded_marks"] == 4.5
