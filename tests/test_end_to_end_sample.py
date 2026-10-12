"""
End-to-end sample interview workflow simulation.
Tests complete interactive candidate lifecycle from landing configuration
through question progression and final performance report generation.
"""

from unittest.mock import patch
import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.models import EvaluationResult, CriterionEvaluation

client = TestClient(app)


def test_complete_interview_lifecycle():
    # 1. Start Interview
    start_payload = {
        "role": "Python Developer",
        "difficulty_mode": "adaptive",
        "max_questions": 3,
        "feedback_mode": "immediate",
        "dynamic_questions": False,
    }
    start_resp = client.post("/api/interview/start", json=start_payload)
    assert start_resp.status_code == 200
    start_data = start_resp.json()
    session_id = start_data["session_id"]
    assert start_data["question_number"] == 1
    assert start_data["status"] == "active"
    first_q_id = start_data["question"]
    assert len(first_q_id) > 0

    # 2. Answer Question 1 with strong answer
    eval_q1 = EvaluationResult(
        question_id="py-beg-001",
        awarded_marks=5.0,
        max_marks=5.0,
        percentage=100.0,
        criteria_evaluations=[
            CriterionEvaluation(
                criterion_id="mutability_distinction",
                awarded_marks=2.5,
                max_marks=2.5,
                evidence="Lists mutable, tuples immutable",
                explanation="Demonstrated clear distinction",
            ),
            CriterionEvaluation(
                criterion_id="practical_use_case",
                awarded_marks=1.5,
                max_marks=1.5,
                evidence="Used for coordinates and dict keys",
                explanation="Valid use case",
            ),
            CriterionEvaluation(
                criterion_id="technical_depth",
                awarded_marks=1.0,
                max_marks=1.0,
                evidence="Hashable and lower memory",
                explanation="Accurate",
            ),
        ],
        demonstrated_concepts=["Mutability distinction", "Hashability"],
        missing_concepts=[],
        incorrect_claims=[],
        summary_explanation="Strong opening answer.",
    )

    with patch("backend.session_manager.EvaluationEngine.evaluate_answer", return_value=eval_q1):
        ans1_resp = client.post(
            f"/api/interview/{session_id}/answer",
            json={"answer": "Lists are mutable, tuples are immutable. Tuples are hashable and used for coordinates."},
        )
        assert ans1_resp.status_code == 200
        ans1_data = ans1_resp.json()
        assert ans1_data["is_complete"] is False
        assert ans1_data["question_number"] == 1
        assert ans1_data["evaluation"]["awarded_marks"] == 5.0
        # Difficulty should adapt to intermediate
        assert ans1_data["next_question_details"]["difficulty"] == "intermediate"

    # 3. Answer Question 2 (Intermediate) with partial answer
    eval_q2 = EvaluationResult(
        question_id="py-int-001",
        awarded_marks=2.5,
        max_marks=5.0,
        percentage=50.0,
        criteria_evaluations=[
            CriterionEvaluation(
                criterion_id="args_kwargs_definition",
                awarded_marks=2.0,
                max_marks=2.0,
                evidence="*args unpacks tuples and **kwargs unpacks dicts",
                explanation="Accurate packing definition",
            ),
            CriterionEvaluation(
                criterion_id="signature_ordering",
                awarded_marks=0.5,
                max_marks=2.0,
                evidence="args before kwargs",
                explanation="Omitted keyword-only arguments nuance",
            ),
            CriterionEvaluation(
                criterion_id="call_site_unpacking",
                awarded_marks=0.0,
                max_marks=1.0,
                evidence="",
                explanation="Did not mention call-site unpacking",
            ),
        ],
        demonstrated_concepts=["*args and **kwargs packaging"],
        missing_concepts=["Signature ordering rules with keyword-only arguments"],
        incorrect_claims=[],
        summary_explanation="Partially demonstrated argument mechanics.",
    )

    with patch("backend.session_manager.EvaluationEngine.evaluate_answer", return_value=eval_q2):
        ans2_resp = client.post(
            f"/api/interview/{session_id}/answer",
            json={"answer": "*args is for positional arguments and **kwargs is for keyword arguments."},
        )
        assert ans2_resp.status_code == 200
        ans2_data = ans2_resp.json()
        assert ans2_data["is_complete"] is False
        assert ans2_data["question_number"] == 2
        assert ans2_data["evaluation"]["awarded_marks"] == 2.5

    # 4. Answer Question 3 (Final Question)
    eval_q3 = EvaluationResult(
        question_id="py-int-002",
        awarded_marks=4.0,
        max_marks=5.0,
        percentage=80.0,
        criteria_evaluations=[
            CriterionEvaluation(
                criterion_id="yield_mechanics",
                awarded_marks=2.0,
                max_marks=2.0,
                evidence="yield pauses and saves state",
                explanation="Accurate mechanics",
            ),
            CriterionEvaluation(
                criterion_id="memory_advantages",
                awarded_marks=2.0,
                max_marks=2.0,
                evidence="generates on demand in O(1) memory",
                explanation="Clear memory efficiency explanation",
            ),
        ],
        demonstrated_concepts=["Lazy evaluation", "Memory efficiency"],
        missing_concepts=[],
        incorrect_claims=[],
        summary_explanation="Solid generator explanation.",
    )

    with patch("backend.session_manager.EvaluationEngine.evaluate_answer", return_value=eval_q3):
        ans3_resp = client.post(
            f"/api/interview/{session_id}/answer",
            json={"answer": "Generators use yield to lazily produce values one by one in O(1) memory."},
        )
        assert ans3_resp.status_code == 200
        ans3_data = ans3_resp.json()
        assert ans3_data["is_complete"] is True
        assert ans3_data["status"] == "completed"

    # 5. Fetch Final Report
    report_resp = client.get(f"/api/interview/{session_id}/report")
    assert report_resp.status_code == 200
    report = report_resp.json()

    assert report["status"] == "completed"
    assert report["questions_completed"] == 3
    # Total marks: 5.0 + 2.5 + 4.0 = 11.5 / 15.0 -> 76.7% normalized
    assert report["total_marks_obtained"] == 11.5
    assert report["total_max_marks"] == 15.0
    assert report["normalized_score"] == 76.7
    assert len(report["topic_scores"]) > 0
    assert len(report["difficulty_scores"]) > 0
    assert len(report["recommendations"]) > 0
    assert len(report["history"]) == 3
