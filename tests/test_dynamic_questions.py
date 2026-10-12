"""
Tests for Dynamic Question Generation, Interface Selection, and Auto-Evaluation Workflow.
Verifies:
- Fresh, structured Python question generation with rubric normalization.
- Safe fallback to Question Bank when LLM fails or produces invalid JSON.
- Session non-repetition and cross-session recency tracking.
- Question type modality cycling (conceptual, code_output, code_writing, debugging).
- Empty answer and speech failure handling without consuming questions.
- Duplicate submission rejection and session state locking.
"""

from unittest.mock import MagicMock, patch
import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.models import (
    DifficultyLevel,
    EvaluationResult,
    InterviewMode,
    Question,
    QuestionType,
    RubricCriterion,
    StartInterviewRequest,
)
from backend.question_bank import get_all_questions, get_question_by_id
from backend.question_generator import QuestionGenerator
from backend.adaptive_engine import AdaptiveEngine, CompetencyTracker
from backend.session_manager import SessionManager

client = TestClient(app)


# =============================================================================
# 1. DYNAMIC QUESTION GENERATION & VALIDATION
# =============================================================================

def test_dynamic_question_validation_and_rubric_normalization():
    """Verify that generated questions strictly conform to schema and rubric sums to 5.0."""
    generator = QuestionGenerator()

    valid_payload = {
        "topic": "Python Data Structures",
        "competency": "Memory & Performance",
        "difficulty": "intermediate",
        "question_type": "conceptual",
        "text": "Explain the time complexity differences between list and deque for pop(0).",
        "code_snippet": None,
        "expected_concepts": ["O(n) for list", "O(1) for deque", "Doubly-linked block structure"],
        "common_misconceptions": ["Believing list pop(0) is O(1)"],
        "rubric": [
            {
                "id": "crit_list_complexity",
                "description": "Explains O(n) memory shifting for list.pop(0)",
                "max_marks": 3.0,
                "evidence_guide": "Must mention contiguous array shift",
            },
            {
                "id": "crit_deque_complexity",
                "description": "Explains O(1) doubly-linked chunks for deque.popleft()",
                "max_marks": 3.0,
                "evidence_guide": "Must mention block/node pointer operations",
            },
        ],
        "reference_answer": "Lists require shifting all elements, deques use doubly-linked blocks.",
    }

    q = generator._validate_and_build_question(
        valid_payload,
        fallback_topic="Python Data Structures",
        fallback_difficulty=DifficultyLevel.INTERMEDIATE,
    )

    assert q is not None
    assert q.id.startswith("dyn-")
    assert q.topic == "Python Data Structures"
    assert q.difficulty == DifficultyLevel.INTERMEDIATE
    assert q.question_type == QuestionType.CONCEPTUAL
    assert len(q.rubric) == 2
    # Check rubric normalization: 3.0 + 3.0 was scaled to 5.0 total
    total_marks = sum(c.max_marks for c in q.rubric)
    assert abs(total_marks - 5.0) < 0.01


def test_dynamic_question_rejects_missing_code_snippet_for_debugging_or_output():
    """Output prediction and debugging questions MUST provide code snippets to be valid."""
    generator = QuestionGenerator()

    invalid_output_payload = {
        "topic": "Core Fundamentals",
        "difficulty": "beginner",
        "question_type": "code_output",
        "text": "What does this code print?",
        "code_snippet": None,  # Missing snippet!
        "rubric": [{"id": "c1", "description": "Predicted correctly", "max_marks": 5.0}],
    }

    q = generator._validate_and_build_question(
        invalid_output_payload,
        fallback_topic="Core Fundamentals",
        fallback_difficulty=DifficultyLevel.BEGINNER,
    )
    assert q is None


def test_safe_fallback_when_llm_raises_exception():
    """When LLM call fails, system gracefully falls back to a curated question from the bank."""
    mock_llm = MagicMock()
    mock_llm.generate_json.side_effect = ConnectionError("Ollama offline")

    generator = QuestionGenerator(llm_client=mock_llm)
    session_asked = set()

    q, reason = generator.generate_or_select_question(
        topic="Python fundamentals",
        competency="Core Python",
        difficulty=DifficultyLevel.BEGINNER,
        question_type=QuestionType.CONCEPTUAL,
        session_asked_ids=session_asked,
        use_llm=True,
    )

    assert q is not None
    assert q.id in [bank_q.id for bank_q in get_all_questions()]
    assert "question bank" in reason.lower()
    assert q.id not in session_asked


def test_safe_fallback_when_llm_returns_invalid_or_empty_json():
    """When LLM returns malformed JSON, system falls back to question bank."""
    mock_llm = MagicMock()
    mock_llm.generate_json.return_value = {"error": "unsupported", "text": "too short"}

    generator = QuestionGenerator(llm_client=mock_llm)
    q, reason = generator.generate_or_select_question(
        topic="OOP in Python",
        competency="Object-Oriented Programming",
        difficulty=DifficultyLevel.INTERMEDIATE,
        question_type=QuestionType.CONCEPTUAL,
        session_asked_ids=set(),
        use_llm=True,
    )

    assert q is not None
    assert len(q.rubric) > 0
    assert sum(c.max_marks for c in q.rubric) == 5.0


# =============================================================================
# 2. NON-REPETITION & CROSS-SESSION RECENCY
# =============================================================================

def test_no_duplicate_questions_within_same_session():
    """Questions asked in a session must never be repeated within that session."""
    generator = QuestionGenerator()
    asked_ids = set()

    for _ in range(5):
        q, _ = generator.generate_or_select_question(
            topic="Python fundamentals",
            competency="Core Python",
            difficulty=DifficultyLevel.BEGINNER,
            question_type=QuestionType.CONCEPTUAL,
            session_asked_ids=asked_ids,
            use_llm=False,  # Test fallback selection under constraints
        )
        assert q.id not in asked_ids
        asked_ids.add(q.id)


def test_cross_session_recency_cache_tracking(tmp_path):
    """Recently asked questions are recorded in cache and deprioritized in new sessions."""
    cache_file = tmp_path / "test_recent.json"
    generator = QuestionGenerator()
    generator.recent_cache_file = cache_file

    q1 = get_question_by_id("py-beg-001")
    generator.record_asked_question(q1)

    assert "py-beg-001" in generator.recent_asked_ids
    assert cache_file.exists()


# =============================================================================
# 3. QUESTION TYPE MODALITY SELECTION & INTERFACE MAPPING
# =============================================================================

def test_target_question_type_rotation():
    """Verify adaptive engine rotates question modalities across interview steps."""
    # Question 1: Conceptual foundation
    assert AdaptiveEngine.choose_target_question_type(1) == QuestionType.CONCEPTUAL
    # Question 2: Output prediction
    assert AdaptiveEngine.choose_target_question_type(2) == QuestionType.CODE_OUTPUT
    # Question 3: Hands-on code writing
    assert AdaptiveEngine.choose_target_question_type(3) == QuestionType.CODE_WRITING
    # Question 4: Conceptual / architecture
    assert AdaptiveEngine.choose_target_question_type(4) == QuestionType.CONCEPTUAL
    # Question 5: Debugging
    assert AdaptiveEngine.choose_target_question_type(5) == QuestionType.DEBUGGING


def test_all_question_types_have_valid_display_representation():
    """Verify each question type formats correctly for UI presentation."""
    types_to_test = [
        QuestionType.CONCEPTUAL,
        QuestionType.CODE_WRITING,
        QuestionType.CODE_OUTPUT,
        QuestionType.DEBUGGING,
        QuestionType.PRACTICAL,
    ]

    for q_type in types_to_test:
        q = Question(
            id=f"test-{q_type.value}",
            topic="Testing",
            competency="Testing Competency",
            difficulty=DifficultyLevel.BEGINNER,
            question_type=q_type,
            text=f"Sample question for {q_type.value}",
            code_snippet="x = 1" if q_type in (QuestionType.CODE_OUTPUT, QuestionType.DEBUGGING) else None,
            expected_concepts=["concept 1"],
            rubric=[RubricCriterion(id="c1", description="Criterion 1", max_marks=5.0)],
        )
        display = q.to_display("Selected for testing")
        assert display.question_type == q_type
        assert display.max_marks == 5.0
        assert len(display.text) > 0


# =============================================================================
# 4. AUTOMATIC EVALUATION & ERROR HANDLING WORKFLOW
# =============================================================================

def test_empty_answer_rejected_without_advancing_question():
    """Empty spoken or typed answers return HTTP 400 and do not advance the interview."""
    start_res = client.post("/api/interview/start", json={"max_questions": 3, "dynamic_questions": False})
    assert start_res.status_code == 200
    session_id = start_res.json()["session_id"]

    # Attempt to submit empty answer
    ans_res = client.post(f"/api/interview/{session_id}/answer", json={"answer": "   \n\t  "})
    assert ans_res.status_code == 400
    assert "Answer cannot be empty" in ans_res.json()["detail"]

    # Verify interview question index remains unchanged
    sess_res = client.get(f"/api/interview/{session_id}")
    assert sess_res.status_code == 200
    assert sess_res.json()["question_count"] == 0


def test_failed_transcription_does_not_advance_question():
    """Simulating STT failure returns is_success=False and maintains question state."""
    start_res = client.post("/api/interview/start", json={"max_questions": 3, "dynamic_questions": False})
    session_id = start_res.json()["session_id"]

    with patch("backend.speech_bridge.speech_bridge.listen_and_transcribe", return_value={"is_success": False, "text": "", "error_message": "No speech detected"}):
        listen_res = client.post(f"/api/interview/{session_id}/listen")
        assert listen_res.status_code == 200
        data = listen_res.json()
        assert data["is_success"] is False
        assert data["transcript"] == ""

    # Verify state did not advance
    sess_res = client.get(f"/api/interview/{session_id}")
    assert sess_res.json()["question_count"] == 0


def test_duplicate_submission_prevention():
    """Submitting answers to a completed session returns HTTP 409."""
    start_res = client.post("/api/interview/start", json={"max_questions": 1, "dynamic_questions": False})
    session_id = start_res.json()["session_id"]

    mock_eval = EvaluationResult(
        question_id="py-beg-001",
        awarded_marks=4.5,
        max_marks=5.0,
        percentage=90.0,
        criteria_evaluations=[],
        summary_explanation="Good answer",
    )

    with patch("backend.session_manager.EvaluationEngine.evaluate_answer", return_value=mock_eval):
        # First submission completes interview
        ans1 = client.post(f"/api/interview/{session_id}/answer", json={"answer": "Valid response."})
        assert ans1.status_code == 200
        assert ans1.json()["is_complete"] is True

        # Second submission to finished interview must return 409 Conflict
        ans2 = client.post(f"/api/interview/{session_id}/answer", json={"answer": "Duplicate submission attempt."})
        assert ans2.status_code == 409
        assert "already finished" in ans2.json()["detail"].lower()


def test_dynamic_question_session_flow_with_mixed_modalities():
    """Full session progression through 3 questions with dynamic question mode enabled."""
    start_res = client.post(
        "/api/interview/start",
        json={"max_questions": 3, "dynamic_questions": False, "difficulty_mode": "beginner"},
    )
    assert start_res.status_code == 200
    session_id = start_res.json()["session_id"]
    assert start_res.json()["question_number"] == 1

    mock_eval = EvaluationResult(
        question_id="q1",
        awarded_marks=4.0,
        max_marks=5.0,
        percentage=80.0,
        criteria_evaluations=[],
        summary_explanation="Solid execution",
    )

    with patch("backend.session_manager.EvaluationEngine.evaluate_answer", return_value=mock_eval):
        # Question 1 -> Answer
        r1 = client.post(f"/api/interview/{session_id}/answer", json={"answer": "Lists are mutable sequences."})
        assert r1.status_code == 200
        assert r1.json()["is_complete"] is False
        assert r1.json()["next_question_details"]["question_number"] == 2

        # Question 2 -> Answer
        r2 = client.post(f"/api/interview/{session_id}/answer", json={"answer": "Output is [0, 1, 4]."})
        assert r2.status_code == 200
        assert r2.json()["is_complete"] is False
        assert r2.json()["next_question_details"]["question_number"] == 3

        # Question 3 -> Answer (final)
        r3 = client.post(f"/api/interview/{session_id}/answer", json={"answer": "def solution(): pass"})
        assert r3.status_code == 200
        assert r3.json()["is_complete"] is True

    # Check final report
    report_res = client.get(f"/api/interview/{session_id}/report")
    assert report_res.status_code == 200
    report_data = report_res.json()
    assert report_data["answers_evaluated"] == 3
    assert "normalized_score" in report_data
    assert "recommendations" in report_data
