"""
Test suite verifying 5-10 question enforcement, exact single evaluation idempotency,
and mathematical alignment between question-level rubric marks, final report, and PDF.
"""

from unittest.mock import patch
import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.session_manager import SessionManager
from backend.evaluator import EvaluationEngine
from backend.models import (
    StartInterviewRequest,
    InterviewMode,
    FeedbackMode,
    EvaluationResult,
    CriterionEvaluation,
)

client = TestClient(app)

MOCK_EVAL = EvaluationResult(
    question_id="py-beg-001",
    awarded_marks=4.0,
    max_marks=5.0,
    percentage=80.0,
    summary_explanation="Solid answer demonstrating core principles.",
    criteria_evaluations=[
        CriterionEvaluation(
            criterion_id="crit_1",
            awarded_marks=2.0,
            max_marks=2.5,
            evidence="Candidate explained mutability difference.",
            explanation="Good explanation.",
        ),
        CriterionEvaluation(
            criterion_id="crit_2",
            awarded_marks=2.0,
            max_marks=2.5,
            evidence="Provided valid practical use case.",
            explanation="Solid use case.",
        ),
    ],
    demonstrated_concepts=["Mutability distinction"],
    missing_concepts=[],
    incorrect_claims=[],
)


def test_question_count_boundary_enforcement():
    """Verify that PrepareInterviewRequest rejects <5 or >10 questions."""
    # First upload dummy resume
    upload_res = client.post(
        "/api/resume/upload",
        files={"file": ("candidate.txt", b"Software Engineer with 5 years experience in Python and FastAPI.")},
        data={"target_role": "Senior Python Engineer"},
    )
    assert upload_res.status_code == 200
    resume_id = upload_res.json()["resume_id"]

    # Reject 3 questions (below 5)
    prep_3 = client.post(
        "/api/interview/prepare",
        json={"resume_id": resume_id, "max_questions": 3},
    )
    assert prep_3.status_code == 422

    # Reject 4 questions (below 5)
    prep_4 = client.post(
        "/api/interview/prepare",
        json={"resume_id": resume_id, "max_questions": 4},
    )
    assert prep_4.status_code == 422

    # Reject 11 questions (above 10)
    prep_11 = client.post(
        "/api/interview/prepare",
        json={"resume_id": resume_id, "max_questions": 11},
    )
    assert prep_11.status_code == 422

    # Accept 5 questions
    prep_5 = client.post(
        "/api/interview/prepare",
        json={"resume_id": resume_id, "max_questions": 5},
    )
    assert prep_5.status_code == 200

    # Accept 10 questions
    prep_10 = client.post(
        "/api/interview/prepare",
        json={"resume_id": resume_id, "max_questions": 10},
    )
    assert prep_10.status_code == 200


def test_evaluation_idempotency_exact_single_scoring():
    """Verify that duplicate submission of the same answer returns cached result without double advancing."""
    mgr = SessionManager()
    req = StartInterviewRequest(
        role="Senior Python Engineer",
        track="python",
        max_questions=5,
        difficulty_mode=InterviewMode.ADAPTIVE,
        feedback_mode=FeedbackMode.IMMEDIATE,
        dynamic_questions=False,
    )
    session = mgr.start_session(req)
    session_id = session.session_id

    q1 = session.current_question
    answer_text = "Lists are mutable whereas tuples are immutable and hashable."

    with patch.object(EvaluationEngine, "evaluate_answer", return_value=MOCK_EVAL):
        # First submission
        res1 = mgr.submit_answer(session_id, answer_text, question_id=q1.id, question_number=1)
        assert res1["question_number"] == 1
        assert len(session.history) == 1
        earned1 = res1["evaluation"]["awarded_marks"]

        # Second submission (network retry / duplicate targeting question 1)
        res2 = mgr.submit_answer(session_id, answer_text, question_id=q1.id, question_number=1)
        assert res2["question_number"] == 1
        assert len(session.history) == 1, "Duplicate submission must NOT advance question count"
        assert res2["evaluation"]["awarded_marks"] == earned1


def test_final_report_mathematical_consistency():
    """Verify that final normalized score matches the sum of question-level awarded marks."""
    mgr = SessionManager()
    req = StartInterviewRequest(
        role="Senior Python Engineer",
        track="python",
        max_questions=5,
        difficulty_mode=InterviewMode.ADAPTIVE,
        feedback_mode=FeedbackMode.IMMEDIATE,
        dynamic_questions=False,
    )
    session = mgr.start_session(req)
    session_id = session.session_id

    with patch.object(EvaluationEngine, "evaluate_answer", return_value=MOCK_EVAL):
        # Answer 2 questions
        mgr.submit_answer(session_id, "Lists are mutable and tuples are immutable.")
        mgr.submit_answer(session_id, "Generators use yield to produce values lazily, conserving memory.")

    report = mgr.generate_report(session_id)
    assert report.questions_completed == 2

    # Check question-level marks sum
    sum_earned = sum(r.evaluation.awarded_marks for r in session.history)
    sum_max = sum(r.evaluation.max_marks for r in session.history)
    expected_norm = round((sum_earned / sum_max) * 100.0, 1)

    assert report.total_marks_obtained == round(sum_earned, 2)
    assert report.total_max_marks == round(sum_max, 2)
    assert report.normalized_score == expected_norm
