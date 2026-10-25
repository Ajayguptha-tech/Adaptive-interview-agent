"""
Comprehensive regression tests for Fair Deterministic Fallback Evaluation.
Tests requirements 1-10:
- Provider failure (Gemini 429 RESOURCE_EXHAUSTED / Ollama connection offline)
- Correct answers awarded proper credit during provider failure
- Partial answers awarded partial credit (e.g. mutability explained, example omitted)
- Genuinely incorrect answers receive 0 marks
- Missing real-world examples deducted only for that specific criterion
- Code output prediction evaluated deterministically
- Code execution with test cases evaluated deterministically
- Reliable score unavailable marked as 'pending' without false 0 penalty
- Rate-limit error handling (no repeated hammering, delays respected)
- Candidate answer and transcript preservation
- FullStack evaluator fallback integration
"""

import time
from unittest.mock import MagicMock, patch
import pytest

from backend.models import (
    Question,
    QuestionType,
    RubricCriterion,
    EvaluationResult,
    FeedbackMode,
    StartInterviewRequest,
)
from backend.evaluator import EvaluationEngine, evaluate_deterministically
from backend.fullstack.evaluator import FullStackEvaluationEngine
from backend.fullstack.question_bank import get_all_fullstack_questions
from backend.question_bank import get_question_by_id
from backend.llm_client import LLMClient, RateLimitError, _is_rate_limit_error, _sanitize_error
from backend.session_manager import SessionManager


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def list_tuple_question() -> Question:
    q = get_question_by_id("py-beg-001")
    assert q is not None, "py-beg-001 must exist in question bank"
    return q


@pytest.fixture
def output_prediction_question() -> Question:
    q = get_question_by_id("py-beg-002")
    assert q is not None, "py-beg-002 must exist in question bank"
    return q


@pytest.fixture
def palindrome_code_question() -> Question:
    q = get_question_by_id("py-beg-004")
    assert q is not None, "py-beg-004 must exist in question bank"
    return q


@pytest.fixture
def fullstack_html_question() -> Question:
    questions = get_all_fullstack_questions()
    for q in questions:
        if "html" in q.id.lower():
            return q
    # Fallback to first question in fullstack bank
    return questions[0]


@pytest.fixture
def gemini_429_client() -> LLMClient:
    """Mock LLMClient simulating Gemini 429 RESOURCE_EXHAUSTED."""
    client = MagicMock(spec=LLMClient)
    client.provider = "gemini"
    client.model_name = "gemini-2.5-flash"
    client.generate_json.side_effect = RateLimitError(
        "Google Gemini API error 429: RESOURCE_EXHAUSTED - Quota exceeded for model gemini-2.5-flash",
        retry_after=15.0,
    )
    return client


@pytest.fixture
def ollama_offline_client() -> LLMClient:
    """Mock LLMClient simulating Ollama offline / connection error."""
    client = MagicMock(spec=LLMClient)
    client.provider = "ollama"
    client.model_name = "qwen2.5:7b"
    client.generate_json.side_effect = RuntimeError("Ollama connection error: [Errno 111] Connection refused")
    return client


# =============================================================================
# 1. Correct Answers During Provider Failure
# =============================================================================

def test_correct_answer_during_gemini_429(list_tuple_question, gemini_429_client):
    """
    Requirement 4 & 9: Candidate provides a complete, accurate response.
    When Gemini returns HTTP 429, fallback must award full marks (5.0/5.0),
    populate demonstrated concepts, and identify no misconceptions.
    """
    engine = EvaluationEngine(llm_client=gemini_429_client)
    full_answer = (
        "Lists are mutable meaning they can be modified, appended, or sorted in place. "
        "Tuples are immutable and cannot be changed after creation. "
        "You would choose a tuple for coordinates like (x, y) or as dictionary keys "
        "because tuples are hashable and protect data integrity. "
        "Syntactically, lists use square brackets [] while tuples use parentheses ()."
    )

    result = engine.evaluate_answer(list_tuple_question, full_answer)

    assert result.awarded_marks == 5.0
    assert result.max_marks == 5.0
    assert result.percentage == 100.0
    assert result.addressed_question is True
    assert "mutable" in result.demonstrated_concepts[0].lower()
    assert len(result.incorrect_claims) == 0

    # Every criterion in rubric was satisfied
    crit_scores = {c.criterion_id: c.awarded_marks for c in result.criteria_evaluations}
    assert crit_scores["mutability_distinction"] == 2.5
    assert crit_scores["practical_use_case"] == 1.5
    assert crit_scores["technical_depth"] == 1.0


def test_correct_answer_during_ollama_offline(list_tuple_question, ollama_offline_client):
    """
    Requirement 7 & 9: Fallback works identically for Ollama provider failures.
    """
    engine = EvaluationEngine(llm_client=ollama_offline_client)
    full_answer = (
        "Lists can be modified in place so they are mutable. "
        "Tuples cannot be modified after creation so they are immutable. "
        "Tuples are preferred for fixed records, coordinates, and dictionary keys. "
        "Lists use brackets [] and tuples use parentheses ()."
    )

    result = engine.evaluate_answer(list_tuple_question, full_answer)

    assert result.awarded_marks >= 4.0
    assert result.percentage >= 80.0
    assert "deterministic fallback" in result.summary_explanation.lower()


# =============================================================================
# 2. Partial Answers and Missing Real-World Examples
# =============================================================================

def test_partial_answer_mutability_explained_example_omitted(list_tuple_question, gemini_429_client):
    """
    Requirement 4 & 9: An answer explaining that lists are mutable and tuples are immutable
    should receive credit for those correct concepts (2.5 marks), even if it omits a requested
    real-world example (0 marks for practical use case).
    Total marks: 2.5 / 5.0 (50.0%). Must NOT be 0/5.
    """
    engine = EvaluationEngine(llm_client=gemini_429_client)
    partial_answer = "Lists are mutable and can be changed in place. Tuples are immutable and cannot be modified."

    result = engine.evaluate_answer(list_tuple_question, partial_answer)

    assert result.awarded_marks == 2.5
    assert result.max_marks == 5.0
    assert result.percentage == 50.0
    assert result.addressed_question is True

    crit_map = {c.criterion_id: c for c in result.criteria_evaluations}
    # Mutability received full marks
    assert crit_map["mutability_distinction"].awarded_marks == 2.5
    # Practical use case received 0 because example was omitted
    assert crit_map["practical_use_case"].awarded_marks == 0.0
    # Technical depth received 0 because syntax/hashability not mentioned
    assert crit_map["technical_depth"].awarded_marks == 0.0

    # Summary clearly states partial credit awarded
    assert "2.5/5.0" in result.summary_explanation


def test_missing_example_only_deducts_example_criterion(list_tuple_question, gemini_429_client):
    """
    Requirement 9: Candidate explains mutability AND technical depth (syntax, memory, hashability)
    but omits the practical real-world scenario.
    Marks: 2.5 (mutability) + 1.0 (technical depth) = 3.5 / 5.0 (70.0%).
    """
    engine = EvaluationEngine(llm_client=gemini_429_client)
    answer_with_tech_depth_no_example = (
        "Lists are mutable and use square brackets []. "
        "Tuples are immutable, use parentheses (), and are hashable so they can be stored in sets. "
        "Tuples also use less memory and have lower memory overhead than lists."
    )

    result = engine.evaluate_answer(list_tuple_question, answer_with_tech_depth_no_example)

    assert result.awarded_marks == 3.5
    assert result.percentage == 70.0

    crit_map = {c.criterion_id: c for c in result.criteria_evaluations}
    assert crit_map["mutability_distinction"].awarded_marks == 2.5
    assert crit_map["technical_depth"].awarded_marks == 1.0
    assert crit_map["practical_use_case"].awarded_marks == 0.0


# =============================================================================
# 3. Genuinely Incorrect Answers and Refusals
# =============================================================================

def test_genuinely_incorrect_answer_receives_zero(list_tuple_question, gemini_429_client):
    """
    Requirement 4 & 9: Genuinely incorrect answers receive strictly 0 marks.
    No fabricated marks should be awarded.
    """
    engine = EvaluationEngine(llm_client=gemini_429_client)
    incorrect_answer = (
        "Lists are immutable in Python and you cannot change them after creation. "
        "Tuples on the other hand are dynamic and mutable."
    )

    result = engine.evaluate_answer(list_tuple_question, incorrect_answer)

    assert result.awarded_marks == 0.0
    assert result.percentage == 0.0


def test_explicit_refusal_receives_zero_marks(list_tuple_question, gemini_429_client):
    """
    Requirement 4 & 9: Candidate says 'I don't know' or 'no idea'.
    Must receive 0 marks without crashing or raising exceptions.
    """
    engine = EvaluationEngine(llm_client=gemini_429_client)
    for phrase in ["I don't know", "no idea", "pass"]:
        result = engine.evaluate_answer(list_tuple_question, phrase)
        assert result.awarded_marks == 0.0
        assert result.percentage == 0.0
        assert result.addressed_question is True
        assert result.evaluation_status == "completed"


def test_empty_answer_receives_zero_marks_immediately(list_tuple_question, gemini_429_client):
    """
    Empty answer should receive 0 marks and addressed_question=False.
    """
    engine = EvaluationEngine(llm_client=gemini_429_client)
    result = engine.evaluate_answer(list_tuple_question, "   ")
    assert result.awarded_marks == 0.0
    assert result.percentage == 0.0
    assert result.addressed_question is False


# =============================================================================
# 4. Output Prediction & Code Execution Questions During Fallback
# =============================================================================

def test_output_prediction_correct_during_fallback(output_prediction_question, gemini_429_client):
    """
    Requirement 9: Output prediction question with correct prediction receives credit in fallback.
    """
    engine = EvaluationEngine(llm_client=gemini_429_client)
    # Expected output for py-beg-002: "[1, 3, 5]" or "[1, 3, 5]" depending on question
    expected = output_prediction_question.expected_output or "24"
    candidate_answer = f"The output will be {expected} because of the accumulator loop."

    result = engine.evaluate_answer(output_prediction_question, candidate_answer)
    assert result.awarded_marks > 0.0
    assert result.percentage > 0.0


def test_output_prediction_incorrect_during_fallback(output_prediction_question, gemini_429_client):
    """
    Requirement 9: Output prediction question with incorrect output receives 0 marks.
    """
    engine = EvaluationEngine(llm_client=gemini_429_client)
    result = engine.evaluate_answer(output_prediction_question, "The output will be 999999")
    assert result.awarded_marks == 0.0
    assert result.percentage == 0.0


def test_code_writing_test_cases_during_fallback(palindrome_code_question, gemini_429_client):
    """
    Requirement 9: Code-writing question evaluates candidate code using test cases in isolated runner.
    """
    engine = EvaluationEngine(llm_client=gemini_429_client)
    valid_code = "def is_palindrome(text: str) -> bool:\n    clean = ''.join(c.lower() for c in text if c.isalnum())\n    return clean == clean[::-1]"

    result = engine.evaluate_answer(palindrome_code_question, valid_code)
    assert result.awarded_marks == palindrome_code_question.total_marks
    assert result.percentage == 100.0
    assert result.execution_result is not None
    assert result.execution_result["tests_passed"] == result.execution_result["tests_total"]


def test_code_writing_syntax_error_during_fallback(palindrome_code_question, gemini_429_client):
    """
    Syntax errors during code execution receive 0 marks deterministically.
    """
    engine = EvaluationEngine(llm_client=gemini_429_client)
    syntax_error_code = "def is_palindrome(text:\n return text =="

    result = engine.evaluate_answer(palindrome_code_question, syntax_error_code)
    assert result.awarded_marks == 0.0
    assert result.percentage == 0.0
    assert result.execution_result["syntax_valid"] is False


# =============================================================================
# 5. Reliable Score Unavailable Marked as 'Pending' (Requirement 5)
# =============================================================================

def test_unreliable_scoring_marked_pending_not_zero_penalty(gemini_429_client):
    """
    Requirement 5: If a reliable score cannot be calculated (e.g. candidate wrote a
    substantive 25-word paragraph on an unmapped topic with zero keyword overlap),
    the evaluation is marked as 'pending' instead of penalizing with zero.
    """
    # Create an arbitrary question with narrow rubric
    narrow_q = Question(
        id="py-spec-test-001",
        topic="Metaclasses",
        competency="Python Advanced",
        difficulty="advanced",
        question_type=QuestionType.CONCEPTUAL,
        text="Explain how __prepare__ is used in custom metaclasses.",
        rubric=[
            RubricCriterion(
                id="prepare_namespace",
                max_marks=5.0,
                description="Explains __prepare__ returns a custom mapping for class body namespace",
                evidence_guide="Must mention OrderedDict or custom dict namespace.",
            )
        ],
        expected_concepts=["__prepare__ method", "custom namespace", "OrderedDict"],
        reference_answer="__prepare__ returns a custom dictionary namespace for class body execution.",
        total_marks=5.0,
    )

    engine = EvaluationEngine(llm_client=gemini_429_client)
    # Candidate writes a detailed answer about metaclasses but with non-matching vocabulary
    candidate_answer = (
        "In Python object orientation, class creation invokes special type machinery "
        "allowing developers to intercept class construction at runtime before instantiation."
    )

    result = engine.evaluate_answer(narrow_q, candidate_answer)

    # Marked as pending, not penalized with a definitive final zero
    assert result.evaluation_status == "pending"
    assert "pending" in result.summary_explanation.lower()
    assert result.addressed_question is True


# =============================================================================
# 6. Rate Limit Handling and Non-Hammering (Requirement 6)
# =============================================================================

def test_is_rate_limit_detection():
    """
    Requirement 6: Detects 429, RESOURCE_EXHAUSTED, and quota errors accurately.
    """
    e1 = Exception("429 Resource has been exhausted (e.g. check quota).")
    is_rl, delay = _is_rate_limit_error(e1)
    assert is_rl is True

    e2 = Exception("RESOURCE_EXHAUSTED: Quota exceeded for quota metric 'GenerateContent'")
    is_rl, delay = _is_rate_limit_error(e2)
    assert is_rl is True

    e3 = Exception("Rate limit reached. Please retry after 1.5s.")
    is_rl, delay = _is_rate_limit_error(e3)
    assert is_rl is True
    assert delay == 1.5

    e4 = ValueError("Syntax error in user prompt")
    is_rl, delay = _is_rate_limit_error(e4)
    assert is_rl is False
    assert delay is None


def test_gemini_rate_limit_does_not_hammer_api():
    """
    Requirement 6: When rate limited with a delay > 2.0s, generate_json raises RateLimitError
    immediately instead of sleeping and stalling the user session.
    """
    client = LLMClient(provider="gemini", api_key="AIzaSyFakeKeyToTest")
    mock_genai_client = MagicMock()
    mock_genai_client.models.generate_content.side_effect = Exception(
        "RESOURCE_EXHAUSTED: Quota exceeded. Please retry after 30s."
    )
    client._gemini_client = mock_genai_client

    start = time.perf_counter()
    with pytest.raises(RateLimitError) as exc_info:
        client.generate_json(prompt="Hello", system_prompt="Test")
    elapsed = time.perf_counter() - start

    # Took < 1 second; did NOT sleep for 30s
    assert elapsed < 1.0
    assert "RESOURCE_EXHAUSTED" in str(exc_info.value)
    # API key masked
    assert "AIzaSyFakeKeyToTest" not in str(exc_info.value)


def test_sanitize_error_masks_all_api_keys():
    """
    Requirement 8: API keys are masked and never exposed.
    """
    raw_key = "AIzaSySecretApiKey1234567890abcdef"
    err = f"Failed to authenticate with key={raw_key} on endpoint"
    sanitized = _sanitize_error(err, raw_key)
    assert raw_key not in sanitized
    assert "[REDACTED]" in sanitized


# =============================================================================
# 7. FullStack Evaluation Fallback Integration
# =============================================================================

def test_fullstack_evaluator_fallback(fullstack_html_question, gemini_429_client):
    """
    Verifies FullStackEvaluationEngine uses deterministic fallback and awards marks.
    """
    engine = FullStackEvaluationEngine(llm_client=gemini_429_client)
    candidate_answer = (
        "Semantic HTML elements like <header>, <nav>, <main>, <article>, and <footer> "
        "provide clear meaning to both the browser and screen readers, which significantly "
        "improves accessibility and SEO."
    )

    result = engine.evaluate_answer(fullstack_html_question, candidate_answer)

    assert result.awarded_marks > 0.0
    assert result.percentage > 0.0
    assert "deterministic fallback" in result.summary_explanation.lower()


# =============================================================================
# 8. Session Answer Submission & Transcript Preservation (Requirement 5)
# =============================================================================

def test_session_submission_preserves_answer_and_transcript_under_429(list_tuple_question):
    """
    Requirement 5: When Gemini hits 429 during an interactive session, the candidate's
    answer and transcript are accurately preserved in session.history, and a valid
    deterministic score is returned without crashing the interview.
    """
    mock_client = MagicMock(spec=LLMClient)
    mock_client.provider = "gemini"
    mock_client.model_name = "gemini-2.5-flash"
    mock_client.generate_json.side_effect = RateLimitError("429 RESOURCE_EXHAUSTED", retry_after=10.0)

    eval_engine = EvaluationEngine(llm_client=mock_client)
    mgr = SessionManager(evaluation_engine=eval_engine)
    req = StartInterviewRequest(
        role="Python Developer",
        track="python",
        max_questions=3,
        feedback_mode=FeedbackMode.IMMEDIATE,
        dynamic_questions=False,
    )
    session = mgr.start_session(req)

    candidate_text = "Lists are mutable and can be modified. Tuples are immutable and cannot be changed."
    result = mgr.submit_answer(session_id=session.session_id, answer=candidate_text)

    # Evaluation returned valid non-zero score for correct mutability concepts
    assert result["status"] == "active"
    assert result["question_number"] == 1
    assert result["evaluation"]["awarded_marks"] > 0.0
    assert result["evaluation"]["percentage"] > 0.0

    # Candidate answer and history record accurately preserved
    assert len(session.history) == 1
    last_record = session.history[0]
    assert last_record.candidate_answer == candidate_text
    assert last_record.evaluation.awarded_marks > 0.0
    assert last_record.question is not None
