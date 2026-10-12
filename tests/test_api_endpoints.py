"""
Tests for FastAPI API endpoints and backward compatibility with voice_interview.py.
"""

from unittest.mock import patch, MagicMock
import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.models import EvaluationResult, CriterionEvaluation

client = TestClient(app)


def test_home_endpoint_json():
    response = client.get("/", headers={"accept": "application/json"})
    assert response.status_code == 200
    data = response.json()
    assert "Adaptive Python Interviewer API is running" in data["message"]


def test_health_endpoint():
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["api"] == "running"
    assert "ollama" in data


def test_topics_endpoint():
    response = client.get("/api/topics")
    assert response.status_code == 200
    data = response.json()
    assert "topics" in data
    assert "competencies" in data
    assert len(data["topics"]) > 0


def test_interview_start_and_voice_compatibility():
    """Verify start response contains all fields required by both web UI and voice_interview.py."""
    payload = {
        "role": "Python Developer",
        "job_description": "Core python fundamentals",
        "resume_summary": "",
        "competencies": ["Python fundamentals"],
        "max_questions": 3,
        "difficulty_mode": "beginner",
        "dynamic_questions": False,
    }
    response = client.post("/api/interview/start", json=payload)
    assert response.status_code == 200
    data = response.json()

    # Required by voice_interview.py
    assert "session_id" in data
    assert "question" in data
    assert isinstance(data["question"], str)
    assert len(data["question"]) > 0

    # Required by adaptive system
    assert data["status"] == "active"
    assert data["question_number"] == 1
    assert data["max_questions"] == 3


def test_answer_submission_and_voice_compatibility():
    """Verify answer response contains exact structure expected by voice_interview.py."""
    start_res = client.post("/api/interview/start", json={"max_questions": 2, "dynamic_questions": False})
    session_id = start_res.json()["session_id"]

    mock_eval = EvaluationResult(
        question_id="py-beg-001",
        awarded_marks=4.5,
        max_marks=5.0,
        percentage=90.0,
        criteria_evaluations=[
            CriterionEvaluation(
                criterion_id="mutability_distinction",
                awarded_marks=2.5,
                max_marks=2.5,
                evidence="Lists mutable, tuples immutable",
                explanation="Good distinction",
            )
        ],
        demonstrated_concepts=["Mutability difference"],
        missing_concepts=["Advanced hashing nuances"],
        incorrect_claims=[],
        summary_explanation="Solid response",
    )

    with patch("backend.session_manager.EvaluationEngine.evaluate_answer", return_value=mock_eval):
        ans_res = client.post(
            f"/api/interview/{session_id}/answer",
            json={"answer": "Lists are mutable and tuples are immutable."},
        )
        assert ans_res.status_code == 200
        data = ans_res.json()

        # Check voice_interview.py exact contract:
        # 1. evaluation["competency"]
        # 2. evaluation["assessment"]
        # 3. evaluation["evidence_from_answer"]
        # 4. evaluation["missing_knowledge"]
        # 5. next_question (str)
        # 6. is_complete (bool)
        evaluation = data["evaluation"]
        assert "competency" in evaluation
        assert evaluation["assessment"] in ("strong", "partial", "insufficient")
        assert isinstance(evaluation["evidence_from_answer"], list)
        assert isinstance(evaluation["missing_knowledge"], list)
        assert "next_question" in data
        assert isinstance(data["next_question"], str)
        assert "is_complete" in data
        assert data["is_complete"] is False


def test_empty_answer_rejected_without_advancing_count():
    start_res = client.post("/api/interview/start", json={"max_questions": 3, "dynamic_questions": False})
    session_id = start_res.json()["session_id"]

    ans_res = client.post(
        f"/api/interview/{session_id}/answer",
        json={"answer": "    "},
    )
    assert ans_res.status_code == 400
    assert "Answer cannot be empty" in ans_res.json()["detail"]

    # Verify session remains on question 1
    session_res = client.get(f"/api/interview/{session_id}")
    assert session_res.json()["question_count"] == 0


def test_final_report_structure_and_voice_compatibility():
    """Verify final report contains both voice_interview.py fields and normalized 100 score."""
    start_res = client.post("/api/interview/start", json={"max_questions": 2, "dynamic_questions": False})
    session_id = start_res.json()["session_id"]

    mock_eval = EvaluationResult(
        question_id="py-beg-001",
        awarded_marks=5.0,
        max_marks=5.0,
        percentage=100.0,
        criteria_evaluations=[],
        demonstrated_concepts=["All concepts demonstrated"],
        summary_explanation="Full marks",
    )

    with patch("backend.session_manager.EvaluationEngine.evaluate_answer", return_value=mock_eval):
        client.post(
            f"/api/interview/{session_id}/answer",
            json={"answer": "Complete valid answer 1."},
        )
        client.post(
            f"/api/interview/{session_id}/answer",
            json={"answer": "Complete valid answer 2."},
        )

        rep_res = client.get(f"/api/interview/{session_id}/report")
        assert rep_res.status_code == 200
        rep_data = rep_res.json()

        # voice_interview.py contract:
        # report["status"]
        # report["answers_evaluated"]
        # report["competency_report"][competency] -> list of records with assessment, evidence, missing_knowledge
        assert "status" in rep_data
        assert rep_data["answers_evaluated"] == 2
        assert "competency_report" in rep_data
        for comp_name, records in rep_data["competency_report"].items():
            for rec in records:
                assert "assessment" in rec
                assert "evidence" in rec
                assert "missing_knowledge" in rec

        # Normalized scoring
        assert rep_data["normalized_score"] == 100.0
        assert rep_data["total_marks_obtained"] == 10.0
        assert rep_data["total_max_marks"] == 10.0
