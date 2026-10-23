"""
Test suite validating session-level randomization, role-specific question selection,
and duplicate prevention across multiple sessions without fixed global random seed.
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


def test_zero_duplicates_within_session():
    """Verify that within an interview session, no question is ever repeated."""
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
    asked_ids = [session.current_question.id]
    asked_texts = [session.current_question.text]

    with patch.object(EvaluationEngine, "evaluate_answer", return_value=MOCK_EVAL):
        for q_idx in range(4):
            mgr.submit_answer(
                session_id=session.session_id,
                answer="Detailed answer discussing Python data models, execution mechanics, and design patterns.",
            )
            if session.current_question:
                asked_ids.append(session.current_question.id)
                asked_texts.append(session.current_question.text)

    # Check that all asked question IDs and texts are unique
    assert len(asked_ids) == len(set(asked_ids)), f"Duplicate question ID found: {asked_ids}"
    assert len(asked_texts) == len(set(asked_texts)), f"Duplicate question text found: {asked_texts}"


def test_independent_sessions_produce_distinct_seeds_and_sequences():
    """Verify that multiple independent sessions receive distinct random seeds."""
    mgr = SessionManager()
    seeds = set()
    first_q_ids = []

    for i in range(10):
        req = StartInterviewRequest(
            candidate_id=f"candidate_{i}",
            role="Python Developer",
            track="python",
            max_questions=5,
            difficulty_mode=InterviewMode.ADAPTIVE,
            dynamic_questions=False,
        )
        session = mgr.start_session(req)
        seeds.add(session.seed)
        first_q_ids.append(session.current_question.id)

    # All session seeds must be distinct
    assert len(seeds) == 10, f"Expected 10 unique session seeds, got {len(seeds)}"
