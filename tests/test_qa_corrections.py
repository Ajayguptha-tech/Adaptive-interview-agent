"""
Tests for Final Quality Assurance and Corrections:
- Dynamic mode vs Predefined mode.
- Semantic duplicate detection and regeneration attempt loop.
- Persistent recent-question history across restarts.
- Candidate-specific adaptive steering in generation.
- Strict scoring policies:
  * Functional code correctness: failing code -> 0 marks, passing code -> awarded marks.
  * Output prediction: wrong output -> 0 marks, correct output -> awarded marks.
  * Conceptual answers: partial marks for demonstrated concepts, 0 marks for irrelevant.
- Cancel and End Interview early:
  * Session status ended_early/cancelled.
  * Accurate report with completed and unanswered counts.
  * No post-finalization updates (409 Conflict).
"""

import json
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
    EndInterviewRequest,
)
from backend.question_generator import (
    QuestionGenerator,
    FingerprintEngine,
    MAX_REGENERATION_ATTEMPTS,
)
from backend.adaptive_engine import AdaptiveEngine, CompetencyTracker
from backend.session_manager import SessionManager
from backend.evaluator import EvaluationEngine, OutputPredictionEvaluator
from backend.code_evaluator import CodeEvaluator

client = TestClient(app)


# =============================================================================
# 1. DYNAMIC VS PREDEFINED MODE SELECTION
# =============================================================================

def test_dynamic_mode_default_and_predefined_mode():
    """Verify dynamic mode is default (True) and predefined mode sets dynamic_questions=False."""
    req_default = StartInterviewRequest()
    assert req_default.dynamic_questions is True

    req_predefined = StartInterviewRequest(dynamic_questions=False)
    assert req_predefined.dynamic_questions is False

    # Start session via API in predefined mode
    res_pre = client.post("/api/interview/start", json={"dynamic_questions": False, "max_questions": 2})
    assert res_pre.status_code == 200
    data_pre = res_pre.json()
    assert data_pre["dynamic_questions"] is False


# =============================================================================
# 2. SEMANTIC DUPLICATE DETECTION & REGENERATION LOOP
# =============================================================================

def test_semantic_duplicate_fingerprint_engine():
    """FingerprintEngine detects identical and semantically equivalent questions."""
    q1 = "What is the difference between a list and a tuple in Python regarding mutability?"
    q2 = "Explain the difference between Python list and tuple regarding mutability."
    q3 = "How does the Global Interpreter Lock impact multithreading performance in CPython?"

    # q1 and q2 share high semantic overlap
    is_similar = FingerprintEngine.are_semantically_similar(q1, q2, threshold=0.45)
    assert is_similar is True

    # q1 and q3 are completely distinct
    is_distinct = FingerprintEngine.are_semantically_similar(q1, q3, threshold=0.45)
    assert is_distinct is False


def test_regeneration_loop_on_duplicate_detection(tmp_path):
    """QuestionGenerator regenerates when a duplicate is produced and limits to 3 attempts."""
    mock_llm = MagicMock()
    # First response: duplicate of existing question
    # Second response: fresh unique question
    dup_json = {
        "topic": "Python Fundamentals",
        "competency": "Core Python",
        "difficulty": "beginner",
        "question_type": "conceptual",
        "text": "What is the difference between lists and tuples in Python?",
        "expected_concepts": ["Lists are mutable", "Tuples are immutable"],
        "rubric": [{"id": "c1", "description": "Mutability distinction", "max_marks": 5.0}],
        "reference_answer": "Lists are mutable and tuples are immutable.",
    }
    fresh_json = {
        "topic": "Python Fundamentals",
        "competency": "Core Python",
        "difficulty": "beginner",
        "question_type": "conceptual",
        "text": "How do Python dictionary hash maps handle key lookups under collision?",
        "expected_concepts": ["Open addressing", "Perturbation hash sequence"],
        "rubric": [{"id": "c1", "description": "Lookup mechanics", "max_marks": 5.0}],
        "reference_answer": "Python dicts use open addressing with quadratic perturbation probing.",
    }

    mock_llm.generate_json.side_effect = [dup_json, fresh_json]

    cache_file = tmp_path / "recent.json"
    generator = QuestionGenerator(llm_client=mock_llm, recent_cache_file=cache_file)

    existing_asked = ["What is the difference between lists and tuples in Python?"]

    q, reason = generator.generate_or_select_question(
        topic="Python Fundamentals",
        competency="Core Python",
        difficulty=DifficultyLevel.BEGINNER,
        question_type=QuestionType.CONCEPTUAL,
        session_asked_ids=set(),
        session_asked_texts=existing_asked,
        use_llm=True,
    )

    assert q is not None
    assert "dictionary hash maps" in q.text
    # Proves LLM was called twice due to duplicate regeneration
    assert mock_llm.generate_json.call_count == 2


def test_persistent_recent_history_across_restarts(tmp_path):
    """Recent questions persist across instances in the cache file."""
    cache_file = tmp_path / "persistent_recent.json"

    # Instance 1 records a question
    gen1 = QuestionGenerator(recent_cache_file=cache_file)
    sample_q = Question(
        id="dyn-test-101",
        topic="OOP",
        competency="Polymorphism",
        difficulty=DifficultyLevel.INTERMEDIATE,
        question_type=QuestionType.CONCEPTUAL,
        text="Explain method resolution order (MRO) and C3 linearization.",
        expected_concepts=["C3 linearization"],
        rubric=[RubricCriterion(id="c1", description="MRO", max_marks=5.0)],
    )
    gen1.record_asked_question(sample_q)

    assert cache_file.exists()

    # Instance 2 initializes from the same file
    gen2 = QuestionGenerator(recent_cache_file=cache_file)
    assert "dyn-test-101" in gen2.recent_asked_ids
    assert any("method resolution order" in text.lower() for text in gen2.recent_asked_texts)


# =============================================================================
# 3. CANDIDATE-SPECIFIC ADAPTIVE STEERING
# =============================================================================

def test_candidate_context_injected_into_generation_prompt():
    """Candidate context with missing concepts and last score is passed into the prompt."""
    mock_llm = MagicMock()
    mock_llm.generate_json.return_value = {
        "topic": "Python Memory",
        "competency": "Reference Counting",
        "difficulty": "intermediate",
        "question_type": "conceptual",
        "text": "How does Python handle cyclic references when reference counting drops to zero?",
        "expected_concepts": ["Generational cyclic GC", "Garbage collector collects cycles"],
        "rubric": [{"id": "c1", "description": "Cyclic GC", "max_marks": 5.0}],
    }

    generator = QuestionGenerator(llm_client=mock_llm)
    candidate_ctx = {
        "last_score_pct": 30.0,
        "missing_concepts": ["Cyclic reference collection", "Weakref mechanics"],
        "misconceptions": ["Assumed reference counting frees cycles"],
    }

    q, reason = generator.generate_or_select_question(
        topic="Python Memory",
        competency="Reference Counting",
        difficulty=DifficultyLevel.INTERMEDIATE,
        question_type=QuestionType.CONCEPTUAL,
        session_asked_ids=set(),
        candidate_context=candidate_ctx,
        use_llm=True,
    )

    assert q is not None
    # Verify the prompt sent to LLM contained candidate context
    prompt_sent = mock_llm.generate_json.call_args.kwargs.get("prompt", "")
    assert "Cyclic reference collection" in prompt_sent
    assert "Weakref mechanics" in prompt_sent


# =============================================================================
# 4. STRICT SCORING POLICY (CODE, OUTPUT, CONCEPTUAL)
# =============================================================================

def test_code_writing_syntax_error_receives_strictly_zero_marks():
    """A solution with a syntax error receives strictly 0.0 marks."""
    q = Question(
        id="dyn-code-001",
        topic="Algorithms",
        competency="Functions",
        difficulty=DifficultyLevel.BEGINNER,
        question_type=QuestionType.CODE_WRITING,
        text="Write a function `is_even(n)` that returns True if n is even, else False.",
        expected_concepts=["Modulo operator"],
        rubric=[RubricCriterion(id="correctness", description="Returns True for even", max_marks=5.0)],
        test_cases=[{"input": [4], "expected": True}, {"input": [5], "expected": False}],
        function_name="is_even",
    )

    bad_syntax_code = "def is_even(n):\n    retur n % 2 == 0"  # Syntax error

    mock_llm = MagicMock()
    mock_llm.generate_json.return_value = {
        "addressed_question": True,
        "criteria_evaluations": [{"criterion_id": "correctness", "awarded_marks": 5.0, "explanation": "LLM falsely awards marks"}],
    }
    engine = EvaluationEngine(llm_client=mock_llm)
    result = engine.evaluate_answer(q, bad_syntax_code)

    assert result.awarded_marks == 0.0
    assert result.percentage == 0.0
    assert any("syntax error" in ce.explanation.lower() for ce in result.criteria_evaluations)


def test_code_writing_failing_test_cases_receives_strictly_zero_marks():
    """A solution that fails required functional tests receives strictly 0.0 marks."""
    q = Question(
        id="dyn-code-002",
        topic="Algorithms",
        competency="Functions",
        difficulty=DifficultyLevel.BEGINNER,
        question_type=QuestionType.CODE_WRITING,
        text="Write a function `multiply(a, b)` returning the product.",
        expected_concepts=["Multiplication"],
        rubric=[RubricCriterion(id="correctness", description="Multiplication logic", max_marks=5.0)],
        test_cases=[{"input": [2, 3], "expected": 6}, {"input": [0, 5], "expected": 0}],
        function_name="multiply",
    )

    incorrect_code = "def multiply(a, b):\n    return a + b"  # Adds instead of multiplies

    mock_llm = MagicMock()
    mock_llm.generate_json.return_value = {
        "addressed_question": True,
        "criteria_evaluations": [{"criterion_id": "correctness", "awarded_marks": 5.0, "explanation": "LLM falsely awards marks"}],
    }
    engine = EvaluationEngine(llm_client=mock_llm)
    result = engine.evaluate_answer(q, incorrect_code)

    assert result.awarded_marks == 0.0
    assert result.percentage == 0.0
    assert any("functional tests failed" in ce.explanation.lower() for ce in result.criteria_evaluations)


def test_code_writing_passing_test_cases_receives_full_marks():
    """A solution passing all required test cases receives full marks."""
    q = Question(
        id="dyn-code-003",
        topic="Algorithms",
        competency="Functions",
        difficulty=DifficultyLevel.BEGINNER,
        question_type=QuestionType.CODE_WRITING,
        text="Write a function `square(n)` returning n * n.",
        expected_concepts=["Squaring"],
        rubric=[RubricCriterion(id="correctness", description="Correct square computation", max_marks=5.0)],
        test_cases=[{"input": [4], "expected": 16}, {"input": [-3], "expected": 9}],
        function_name="square",
    )

    correct_code = "def square(n):\n    return n * n"

    mock_llm = MagicMock()
    mock_llm.generate_json.return_value = {
        "addressed_question": True,
        "demonstrated_concepts": ["Squaring logic"],
        "criteria_evaluations": [
            {"criterion_id": "correctness", "awarded_marks": 5.0, "evidence": "n * n", "explanation": "Passes all tests"}
        ],
        "summary_explanation": "Solution is functionally correct.",
    }

    engine = EvaluationEngine(llm_client=mock_llm)
    result = engine.evaluate_answer(q, correct_code)

    assert result.awarded_marks == 5.0
    assert result.percentage == 100.0


def test_output_prediction_incorrect_receives_strictly_zero_marks():
    """Output prediction question with wrong answer receives strictly 0.0 marks."""
    q = Question(
        id="dyn-out-001",
        topic="Strings & Slicing",
        competency="Python Fundamentals",
        difficulty=DifficultyLevel.BEGINNER,
        question_type=QuestionType.CODE_OUTPUT,
        text="What does this code print?",
        code_snippet="s = 'python'\nprint(s[::-1])",
        expected_output="nohtyp",
        expected_concepts=["Negative step slice reverses string"],
        rubric=[RubricCriterion(id="correct_output", description="Exact output", max_marks=5.0)],
        reference_answer="Output is: 'nohtyp'",
    )

    wrong_prediction = "The output is 'python' because strings are immutable."

    mock_llm = MagicMock()
    # LLM should not be able to override strict zero marks for wrong output
    mock_llm.generate_json.return_value = {
        "addressed_question": True,
        "criteria_evaluations": [
            {"criterion_id": "correct_output", "awarded_marks": 4.0, "explanation": "Convincing reasoning"}
        ],
    }

    engine = EvaluationEngine(llm_client=mock_llm)
    result = engine.evaluate_answer(q, wrong_prediction)

    assert result.awarded_marks == 0.0
    assert result.percentage == 0.0
    assert any("incorrect" in ce.explanation.lower() for ce in result.criteria_evaluations)


def test_output_prediction_correct_receives_marks():
    """Output prediction question with matching output tokens receives marks."""
    q = Question(
        id="dyn-out-002",
        topic="Strings & Slicing",
        competency="Python Fundamentals",
        difficulty=DifficultyLevel.BEGINNER,
        question_type=QuestionType.CODE_OUTPUT,
        text="What does this code print?",
        code_snippet="s = 'python'\nprint(s[::-1])",
        expected_output="nohtyp",
        expected_concepts=["Negative step slice reverses string"],
        rubric=[RubricCriterion(id="correct_output", description="Exact output", max_marks=5.0)],
        reference_answer="Output is: 'nohtyp'",
    )

    correct_prediction = "It prints nohtyp because the slice has a step of -1."

    mock_llm = MagicMock()
    mock_llm.generate_json.return_value = {
        "addressed_question": True,
        "demonstrated_concepts": ["Reverse slice"],
        "criteria_evaluations": [
            {"criterion_id": "correct_output", "awarded_marks": 5.0, "evidence": "prints nohtyp", "explanation": "Exact"}
        ],
    }

    engine = EvaluationEngine(llm_client=mock_llm)
    result = engine.evaluate_answer(q, correct_prediction)

    assert result.awarded_marks == 5.0
    assert result.percentage == 100.0


def test_conceptual_empty_or_irrelevant_receives_zero():
    """Empty or completely off-topic answer receives 0.0 marks."""
    q = Question(
        id="dyn-con-001",
        topic="Core Python",
        competency="Memory",
        difficulty=DifficultyLevel.BEGINNER,
        question_type=QuestionType.CONCEPTUAL,
        text="Explain what the Global Interpreter Lock (GIL) is in Python.",
        expected_concepts=["Mutex that protects access to Python objects", "Prevents multi-core parallelism in bytecode"],
        rubric=[RubricCriterion(id="gil_def", description="GIL explanation", max_marks=5.0)],
    )

    engine = EvaluationEngine()

    # Empty answer
    res_empty = engine.evaluate_answer(q, "   ")
    assert res_empty.awarded_marks == 0.0

    # Completely off-topic answer with no demonstrated concepts
    mock_llm = MagicMock()
    mock_llm.generate_json.return_value = {
        "addressed_question": False,
        "demonstrated_concepts": [],
        "criteria_evaluations": [
            {"criterion_id": "gil_def", "awarded_marks": 2.0, "explanation": "Talked about weather"}
        ],
    }
    engine_mock = EvaluationEngine(llm_client=mock_llm)
    res_irrelevant = engine_mock.evaluate_answer(q, "I like ice cream")
    assert res_irrelevant.awarded_marks == 0.0


# =============================================================================
# 5. CANCEL AND END INTERVIEW EARLY & ACCURATE REPORT
# =============================================================================

def test_cancel_interview_early_preserves_completed_and_marks_status():
    """Ending an interview early finalizes completed questions and marks status as ended_early."""
    start_res = client.post("/api/interview/start", json={"max_questions": 4, "dynamic_questions": False})
    session_id = start_res.json()["session_id"]

    mock_eval = EvaluationResult(
        question_id="py-beg-001",
        awarded_marks=4.0,
        max_marks=5.0,
        percentage=80.0,
        criteria_evaluations=[],
        summary_explanation="Good answer",
    )

    with patch("backend.session_manager.EvaluationEngine.evaluate_answer", return_value=mock_eval):
        # Answer Question 1
        ans1 = client.post(f"/api/interview/{session_id}/answer", json={"answer": "Valid response 1."})
        assert ans1.status_code == 200

        # Candidate ends interview on Question 2 before answering
        end_res = client.post(f"/api/interview/{session_id}/end", json={"status": "ended_early"})
        assert end_res.status_code == 200
        report = end_res.json()["report"]

        # Status and question metrics
        assert report["status"] == "ended_early"
        assert report["questions_completed"] == 1
        assert report["questions_unanswered"] == 3
        assert report["max_questions"] == 4
        assert report["total_marks_obtained"] == 4.0
        # Denominator is completed questions: 4.0 / 5.0 -> 80.0% normalized
        assert report["total_max_marks"] == 5.0
        assert report["normalized_score"] == 80.0

        # Report can still be retrieved via GET
        get_rep = client.get(f"/api/interview/{session_id}/report")
        assert get_rep.status_code == 200
        assert get_rep.json()["status"] == "ended_early"


def test_post_finalization_mutation_rejected():
    """Once an interview is ended early or cancelled, further answer submissions return HTTP 409."""
    start_res = client.post("/api/interview/start", json={"max_questions": 3, "dynamic_questions": False})
    session_id = start_res.json()["session_id"]

    # End immediately
    client.post(f"/api/interview/{session_id}/end", json={"status": "cancelled"})

    # Attempt to answer after cancellation
    late_ans = client.post(f"/api/interview/{session_id}/answer", json={"answer": "Too late answer."})
    assert late_ans.status_code == 409
    assert "already finished" in late_ans.json()["detail"].lower()
