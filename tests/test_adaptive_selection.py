"""
Tests for Adaptive Selection, Competency Tracking, Session Progression,
and Score Normalization (Cases P, Q, R, T).
"""

from unittest.mock import MagicMock
import pytest
from backend.models import (
    StartInterviewRequest,
    InterviewMode,
    FeedbackMode,
    DifficultyLevel,
    QuestionType,
    EvaluationResult,
    CriterionEvaluation,
)
from backend.session_manager import SessionManager
from backend.adaptive_engine import AdaptiveEngine, CompetencyTracker
from backend.question_bank import get_question_by_id, get_all_questions


def test_case_q_adaptive_difficulty_progression():
    """Case Q: Elevating difficulty on strong score (>=80%) and stepping down on low score (<40%)."""
    tracker = CompetencyTracker()
    tracker.current_difficulty = DifficultyLevel.BEGINNER

    q_beg = get_question_by_id("py-beg-001")
    eval_strong = EvaluationResult(
        question_id=q_beg.id,
        awarded_marks=5.0,
        max_marks=5.0,
        percentage=100.0,
        criteria_evaluations=[],
        summary_explanation="Strong",
    )
    tracker.record_answer(q_beg, eval_strong)

    # Next question should adapt upwards to intermediate
    next_q, reason = AdaptiveEngine.select_next_question(
        tracker=tracker,
        mode=InterviewMode.ADAPTIVE,
        last_question=q_beg,
        last_evaluation=eval_strong,
    )

    assert next_q is not None
    assert next_q.difficulty == DifficultyLevel.INTERMEDIATE
    assert "intermediate" in reason.lower()

    # Now simulate low score on intermediate (<40%)
    eval_weak = EvaluationResult(
        question_id=next_q.id,
        awarded_marks=1.0,
        max_marks=5.0,
        percentage=20.0,
        criteria_evaluations=[],
        summary_explanation="Weak",
    )
    tracker.record_answer(next_q, eval_weak)

    next_q2, reason2 = AdaptiveEngine.select_next_question(
        tracker=tracker,
        mode=InterviewMode.ADAPTIVE,
        last_question=next_q,
        last_evaluation=eval_weak,
    )

    assert next_q2 is not None
    assert next_q2.difficulty == DifficultyLevel.BEGINNER
    assert "beginner" in reason2.lower()


def test_case_p_session_progression_and_question_limit():
    """Case P: Interview respects configured question limit (e.g., 3 questions)."""
    mock_eval = MagicMock()
    mock_eval.evaluate_answer.return_value = EvaluationResult(
        question_id="py-beg-001",
        awarded_marks=4.0,
        max_marks=5.0,
        percentage=80.0,
        criteria_evaluations=[
            CriterionEvaluation(
                criterion_id="mutability_distinction",
                awarded_marks=2.5,
                max_marks=2.5,
                evidence="Good",
                explanation="Good",
            )
        ],
        summary_explanation="Good answer",
    )

    manager = SessionManager(evaluation_engine=mock_eval)
    req = StartInterviewRequest(max_questions=3, difficulty_mode=InterviewMode.BEGINNER, dynamic_questions=False)
    session = manager.start_session(req)

    # Question 1
    res1 = manager.submit_answer(session.session_id, "Answer 1")
    assert res1["question_number"] == 1
    assert res1["is_complete"] is False
    assert res1["questions_remaining"] == 2

    # Question 2
    res2 = manager.submit_answer(session.session_id, "Answer 2")
    assert res2["question_number"] == 2
    assert res2["is_complete"] is False
    assert res2["questions_remaining"] == 1

    # Question 3 (final)
    res3 = manager.submit_answer(session.session_id, "Answer 3")
    assert res3["question_number"] == 3
    assert res3["is_complete"] is True
    assert res3["questions_remaining"] == 0
    assert session.status == "completed"

    # Attempting to answer when completed should raise ValueError
    with pytest.raises(ValueError, match="already ended"):
        manager.submit_answer(session.session_id, "Answer 4")


def test_case_t_multiple_question_lengths_normalized_to_100():
    """Case T: Verifies final score is properly normalized to 100 for 5, 10, and 20 question lengths."""
    for length in [5, 10, 20]:
        mock_eval = MagicMock()
        mock_eval.evaluate_answer.return_value = EvaluationResult(
            question_id="test",
            awarded_marks=4.0,
            max_marks=5.0,
            percentage=80.0,
            criteria_evaluations=[],
            summary_explanation="80% performance",
        )
        manager = SessionManager(evaluation_engine=mock_eval)
        req = StartInterviewRequest(max_questions=length, dynamic_questions=False)
        session = manager.start_session(req)

        for i in range(length):
            # Bypass question bank exhaustion in test by assigning current question if None
            if session.current_question is None:
                session.current_question = get_all_questions()[0]
            manager.submit_answer(session.session_id, f"Answer {i+1}")

        report = manager.generate_report(session.session_id)
        assert report.questions_completed == length
        # 4.0 / 5.0 per question -> 80.0% overall -> normalized score 80.0 / 100
        assert report.normalized_score == 80.0
        assert report.total_marks_obtained == length * 4.0
        assert report.total_max_marks == length * 5.0


def test_case_r_competency_coverage_and_report_calculation():
    """Case R: Verifies competency and topic tracking, strengths, weaknesses, and unassessed topics."""
    mock_eval = MagicMock()
    mock_eval.evaluate_answer.return_value = EvaluationResult(
        question_id="py-beg-001",
        awarded_marks=5.0,
        max_marks=5.0,
        percentage=100.0,
        criteria_evaluations=[],
        demonstrated_concepts=["Immutability of tuples"],
        missing_concepts=[],
        incorrect_claims=[],
        summary_explanation="Perfect",
    )
    manager = SessionManager(evaluation_engine=mock_eval)
    req = StartInterviewRequest(max_questions=2, dynamic_questions=False)
    session = manager.start_session(req)

    manager.submit_answer(session.session_id, "Solid answer 1")
    manager.submit_answer(session.session_id, "Solid answer 2")

    report = manager.generate_report(session.session_id)
    assert report.normalized_score == 100.0
    assert len(report.strong_competencies) > 0
    assert len(report.unassessed_topics) > 0
    assert "Immutability of tuples" in [
        c for rec in report.history for c in rec.get("demonstrated_concepts", [])
    ]
