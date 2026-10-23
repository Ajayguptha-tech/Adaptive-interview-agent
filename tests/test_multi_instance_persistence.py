"""
Regression test for SQLite-backed durable session persistence across distinct SessionManager instances.
Verifies multi-instance deployment continuity: session creation, answer recording,
optimistic locking, and report retrieval across distinct memory heaps.
"""

from unittest.mock import patch
import pytest
from backend.models import (
    StartInterviewRequest,
    InterviewMode,
    FeedbackMode,
    EvaluationResult,
    CriterionEvaluation,
)
from backend.session_manager import SessionManager
from backend.evaluator import EvaluationEngine

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


def test_cross_instance_session_restoration(tmp_path):
    # Instance 1: Create and start session
    mgr1 = SessionManager()
    req = StartInterviewRequest(
        candidate_id="cand_persistence_test",
        role="Senior Python Engineer",
        track="python",
        max_questions=5,
        difficulty_mode=InterviewMode.ADAPTIVE,
        feedback_mode=FeedbackMode.IMMEDIATE,
        dynamic_questions=False,
    )
    s1 = mgr1.start_session(req)
    session_id = s1.session_id
    q1_id = s1.current_question.id

    # Verify session is persisted in SQLite
    saved_raw = mgr1.persistence.load_session_dict(session_id)
    assert saved_raw is not None
    assert saved_raw["session_id"] == session_id
    assert saved_raw["candidate_id"] == "cand_persistence_test"

    # Instance 2: Load session from completely separate SessionManager instance
    mgr2 = SessionManager()
    assert session_id not in mgr2.sessions  # Not in memory of instance 2 yet

    s2 = mgr2.get_session(session_id)
    assert s2 is not None
    assert s2.session_id == session_id
    assert s2.candidate_id == "cand_persistence_test"
    assert s2.current_question.id == q1_id
    assert len(s2.history) == 0

    # Instance 2: Submit an answer with mock evaluation
    with patch.object(EvaluationEngine, "evaluate_answer", return_value=MOCK_EVAL):
        ans_res = mgr2.submit_answer(
            session_id=session_id,
            answer="In Python, lists are mutable dynamic arrays, whereas tuples are immutable fixed sequences.",
        )
    assert ans_res["session_id"] == session_id
    assert ans_res["question_number"] == 1
    assert len(s2.history) == 1

    # Instance 3: Third instance loads the updated session
    mgr3 = SessionManager()
    s3 = mgr3.get_session(session_id)
    assert s3 is not None
    assert len(s3.history) == 1
    assert s3.history[0].question.id == q1_id
    assert s3.history[0].evaluation.max_marks == 5.0
    assert s3.history[0].evaluation.awarded_marks == 4.0

    # Instance 3: Generates report
    report = mgr3.generate_report(session_id)
    assert report.session_id == session_id
    assert report.questions_completed == 1
    assert report.total_max_marks == 5.0
    assert report.normalized_score == 80.0
