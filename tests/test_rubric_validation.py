"""
Tests for Rubric Validation:
Enforces score clamping within [0.0, max_marks], prevents duplicate criteria,
ignores foreign criteria, and guarantees deterministic Python calculation.
(Addresses Requirements 7 & Cases N, O).
"""

import pytest
from backend.models import Question, DifficultyLevel, QuestionType, RubricCriterion
from backend.evaluator import EvaluationEngine


@pytest.fixture
def sample_question():
    return Question(
        id="test-q-01",
        topic="Python Fundamentals",
        competency="Python Fundamentals",
        difficulty=DifficultyLevel.BEGINNER,
        question_type=QuestionType.CONCEPTUAL,
        text="Sample question",
        expected_concepts=["Concept A", "Concept B"],
        rubric=[
            RubricCriterion(id="crit_a", description="Concept A", max_marks=3.0),
            RubricCriterion(id="crit_b", description="Concept B", max_marks=2.0),
        ],
    )


def test_score_clamping_upper_bound(sample_question):
    """Case N: Model returns score higher than criterion max_marks (e.g., 5.0 on a 3.0 max criterion)."""
    raw_evals = [
        {"criterion_id": "crit_a", "awarded_marks": 999.0, "explanation": "Too high"},
        {"criterion_id": "crit_b", "awarded_marks": 2.0, "explanation": "Exact"},
    ]
    total, evals = EvaluationEngine.validate_and_calculate_rubric(sample_question, raw_evals)
    
    # crit_a should be clamped to 3.0, crit_b to 2.0 -> total 5.0
    assert total == 5.0
    eval_a = next(e for e in evals if e.criterion_id == "crit_a")
    assert eval_a.awarded_marks == 3.0


def test_score_clamping_lower_bound(sample_question):
    """Case N: Model returns negative score (e.g., -5.0). Must clamp to 0.0."""
    raw_evals = [
        {"criterion_id": "crit_a", "awarded_marks": -10.0, "explanation": "Negative"},
        {"criterion_id": "crit_b", "awarded_marks": 1.5, "explanation": "Valid"},
    ]
    total, evals = EvaluationEngine.validate_and_calculate_rubric(sample_question, raw_evals)
    
    assert total == 1.5
    eval_a = next(e for e in evals if e.criterion_id == "crit_a")
    assert eval_a.awarded_marks == 0.0


def test_duplicate_rubric_criteria_prevention(sample_question):
    """Case O: Model returns duplicate criterion IDs; should not be double-counted."""
    raw_evals = [
        {"criterion_id": "crit_a", "awarded_marks": 2.0, "explanation": "First occurrence"},
        {"criterion_id": "crit_a", "awarded_marks": 2.0, "explanation": "Duplicate occurrence"},
        {"criterion_id": "crit_b", "awarded_marks": 1.0, "explanation": "Valid"},
    ]
    total, evals = EvaluationEngine.validate_and_calculate_rubric(sample_question, raw_evals)
    
    # crit_a should only be counted once (2.0) + crit_b (1.0) = 3.0
    assert total == 3.0
    a_count = sum(1 for e in evals if e.criterion_id == "crit_a")
    assert a_count == 1


def test_foreign_rubric_criteria_ignored(sample_question):
    """Model invents an unknown criterion ID not in the rubric; must be rejected."""
    raw_evals = [
        {"criterion_id": "crit_a", "awarded_marks": 3.0, "explanation": "Valid"},
        {"criterion_id": "invented_criterion", "awarded_marks": 5.0, "explanation": "Hallucinated"},
    ]
    total, evals = EvaluationEngine.validate_and_calculate_rubric(sample_question, raw_evals)
    
    # Only crit_a (3.0) + crit_b (missing -> 0.0) = 3.0
    assert total == 3.0
    assert not any(e.criterion_id == "invented_criterion" for e in evals)


def test_missing_criterion_handled_safely(sample_question):
    """Model omits crit_b completely. Should be filled with 0.0 marks and explanation."""
    raw_evals = [
        {"criterion_id": "crit_a", "awarded_marks": 2.5, "explanation": "Demonstrated"},
    ]
    total, evals = EvaluationEngine.validate_and_calculate_rubric(sample_question, raw_evals)
    
    assert total == 2.5
    crit_b_eval = next(e for e in evals if e.criterion_id == "crit_b")
    assert crit_b_eval.awarded_marks == 0.0
    assert "not demonstrated" in crit_b_eval.explanation
