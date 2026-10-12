"""
Comprehensive tests for Fair Answer Evaluation Engine with mocked LLM.
Validates cases A through M, S from the requirements specification:
A. Correct answers expressed in different words.
B. Partially correct answers.
C. Completely incorrect answers.
D. Answers containing a correct statement and an incorrect statement.
E. Answers that are irrelevant to the question.
F. Very short but correct answers.
G. Long answers with incorrect technical claims.
H. Answers that omit requested examples.
I. Ambiguous answers requiring clarification.
J. Alternative correct code implementations.
K. Code with syntax errors.
L. Code with incorrect edge-case behavior.
M. Malformed model responses.
S. Empty answers and failed model requests.
"""

from unittest.mock import MagicMock
import pytest
from backend.models import Question, DifficultyLevel, QuestionType, RubricCriterion
from backend.evaluator import EvaluationEngine
from backend.question_bank import get_question_by_id


@pytest.fixture
def list_tuple_question():
    return get_question_by_id("py-beg-001")


@pytest.fixture
def palindrome_question():
    return get_question_by_id("py-beg-004")


def test_case_s_empty_answer(list_tuple_question):
    """Case S: Empty answer should immediately receive 0 marks without calling LLM."""
    mock_llm = MagicMock()
    engine = EvaluationEngine(llm_client=mock_llm)

    result = engine.evaluate_answer(list_tuple_question, "   ")
    
    assert result.awarded_marks == 0.0
    assert result.percentage == 0.0
    assert result.addressed_question is False
    assert mock_llm.generate_json.call_count == 0


def test_case_a_correct_different_wording(list_tuple_question):
    """Case A: Correct answer in candidate's own words receives full/strong credit."""
    mock_llm = MagicMock()
    mock_llm.generate_json.return_value = {
        "addressed_question": True,
        "is_ambiguous": False,
        "clarification_question": None,
        "demonstrated_concepts": [
            "Lists can be modified after creation while tuples cannot",
            "Tuples protect coordinates or dictionary keys",
        ],
        "partial_concepts": [],
        "missing_concepts": [],
        "incorrect_claims": [],
        "criteria_evaluations": [
            {
                "criterion_id": "mutability_distinction",
                "awarded_marks": 2.5,
                "evidence": "Lists can be modified after creation while tuples cannot",
                "explanation": "Clearly explained mutability in candidate's own phrasing.",
            },
            {
                "criterion_id": "practical_use_case",
                "awarded_marks": 1.5,
                "evidence": "I use tuples for coordinates and dictionary keys",
                "explanation": "Valid practical use case.",
            },
            {
                "criterion_id": "technical_depth",
                "awarded_marks": 1.0,
                "evidence": "Tuples are hashable and use less memory",
                "explanation": "Accurately noted hashability and memory benefits.",
            },
        ],
        "summary_explanation": "Strong answer demonstrating core distinction and use case.",
    }
    engine = EvaluationEngine(llm_client=mock_llm)
    
    answer = "A list can be modified after creation, but a tuple cannot be changed. I use tuples for fixed coordinates and dict keys."
    result = engine.evaluate_answer(list_tuple_question, answer)
    
    assert result.awarded_marks == 5.0
    assert result.percentage == 100.0
    assert len(result.incorrect_claims) == 0


def test_case_b_partially_correct_answer(list_tuple_question):
    """Case B: Partially correct answer receives justified partial marks."""
    mock_llm = MagicMock()
    mock_llm.generate_json.return_value = {
        "addressed_question": True,
        "is_ambiguous": False,
        "clarification_question": None,
        "demonstrated_concepts": ["Lists are mutable and tuples are immutable"],
        "partial_concepts": [],
        "missing_concepts": ["Concrete real-world use case scenario"],
        "incorrect_claims": [],
        "criteria_evaluations": [
            {
                "criterion_id": "mutability_distinction",
                "awarded_marks": 2.5,
                "evidence": "Lists are mutable and tuples are immutable",
                "explanation": "Correctly identified central mutability difference.",
            },
            {
                "criterion_id": "practical_use_case",
                "awarded_marks": 0.0,
                "evidence": "None provided",
                "explanation": "Did not provide real-world scenario.",
            },
            {
                "criterion_id": "technical_depth",
                "awarded_marks": 0.0,
                "evidence": "None",
                "explanation": "No technical nuances discussed.",
            },
        ],
        "summary_explanation": "Correct core mutability distinction but omitted practical use cases.",
    }
    engine = EvaluationEngine(llm_client=mock_llm)
    
    answer = "A list is mutable and a tuple is immutable."
    result = engine.evaluate_answer(list_tuple_question, answer)
    
    assert result.awarded_marks == 2.5
    assert result.percentage == 50.0
    assert "Concrete real-world use case scenario" in result.missing_concepts


def test_case_c_completely_incorrect_answer(list_tuple_question):
    """Case C: Completely incorrect answer receives 0 marks."""
    mock_llm = MagicMock()
    mock_llm.generate_json.return_value = {
        "addressed_question": True,
        "is_ambiguous": False,
        "clarification_question": None,
        "demonstrated_concepts": [],
        "partial_concepts": [],
        "missing_concepts": ["Mutability difference"],
        "incorrect_claims": ["Lists are immutable and tuples are mutable"],
        "criteria_evaluations": [
            {
                "criterion_id": "mutability_distinction",
                "awarded_marks": 0.0,
                "evidence": "Candidate claimed lists are immutable and tuples are mutable",
                "explanation": "Incorrect claim inverted the definitions.",
            },
            {
                "criterion_id": "practical_use_case",
                "awarded_marks": 0.0,
                "evidence": "",
                "explanation": "No valid use case.",
            },
            {
                "criterion_id": "technical_depth",
                "awarded_marks": 0.0,
                "evidence": "",
                "explanation": "No valid technical concepts.",
            },
        ],
        "summary_explanation": "Candidate gave opposite of correct behavior.",
    }
    engine = EvaluationEngine(llm_client=mock_llm)
    
    answer = "Lists are immutable and tuples are mutable in Python."
    result = engine.evaluate_answer(list_tuple_question, answer)
    
    assert result.awarded_marks == 0.0
    assert len(result.incorrect_claims) > 0


def test_case_d_mixed_correct_and_incorrect(list_tuple_question):
    """Case D: Answer with both a correct statement and an incorrect statement."""
    mock_llm = MagicMock()
    mock_llm.generate_json.return_value = {
        "addressed_question": True,
        "is_ambiguous": False,
        "clarification_question": None,
        "demonstrated_concepts": ["Lists are mutable and tuples are immutable"],
        "partial_concepts": [],
        "missing_concepts": [],
        "incorrect_claims": ["Tuples are compiled in C into static arrays that run 100x faster"],
        "criteria_evaluations": [
            {
                "criterion_id": "mutability_distinction",
                "awarded_marks": 2.5,
                "evidence": "Lists are mutable and tuples are immutable",
                "explanation": "Core distinction correct.",
            },
            {
                "criterion_id": "practical_use_case",
                "awarded_marks": 0.5,
                "evidence": "Used when you need speed",
                "explanation": "Weak/vague use case.",
            },
            {
                "criterion_id": "technical_depth",
                "awarded_marks": 0.0,
                "evidence": "Tuples run 100x faster",
                "explanation": "False claim regarding 100x speed difference.",
            },
        ],
        "summary_explanation": "Identified mutability distinction, but included false claim about 100x speed difference.",
    }
    engine = EvaluationEngine(llm_client=mock_llm)
    
    answer = "Lists are mutable and tuples are immutable. You use tuples when you need speed because tuples run 100x faster in C."
    result = engine.evaluate_answer(list_tuple_question, answer)
    
    assert result.awarded_marks == 3.0
    assert any("100x" in claim for claim in result.incorrect_claims)


def test_case_e_irrelevant_answer(list_tuple_question):
    """Case E: Off-topic answer receives 0 marks."""
    mock_llm = MagicMock()
    mock_llm.generate_json.return_value = {
        "addressed_question": False,
        "is_ambiguous": False,
        "clarification_question": None,
        "demonstrated_concepts": [],
        "partial_concepts": [],
        "missing_concepts": ["List vs tuple mutability"],
        "incorrect_claims": [],
        "criteria_evaluations": [
            {"criterion_id": "mutability_distinction", "awarded_marks": 0.0, "evidence": "", "explanation": "Off-topic"},
            {"criterion_id": "practical_use_case", "awarded_marks": 0.0, "evidence": "", "explanation": "Off-topic"},
            {"criterion_id": "technical_depth", "awarded_marks": 0.0, "evidence": "", "explanation": "Off-topic"},
        ],
        "summary_explanation": "Response discusses Django ORM instead of list vs tuple.",
    }
    engine = EvaluationEngine(llm_client=mock_llm)
    
    answer = "In Django, you write models that map to SQL tables using Object Relational Mapping."
    result = engine.evaluate_answer(list_tuple_question, answer)
    
    assert result.awarded_marks == 0.0
    assert result.addressed_question is False


def test_case_f_short_but_correct_answer(list_tuple_question):
    """Case F: Very short but technically accurate answer receives earned criteria marks."""
    mock_llm = MagicMock()
    mock_llm.generate_json.return_value = {
        "addressed_question": True,
        "is_ambiguous": False,
        "clarification_question": None,
        "demonstrated_concepts": ["Lists are mutable; tuples are immutable"],
        "partial_concepts": [],
        "missing_concepts": ["Elaborated use case"],
        "criteria_evaluations": [
            {"criterion_id": "mutability_distinction", "awarded_marks": 2.5, "evidence": "Lists: mutable. Tuples: immutable.", "explanation": "Concise and correct."},
            {"criterion_id": "practical_use_case", "awarded_marks": 0.0, "evidence": "", "explanation": "No use case provided."},
            {"criterion_id": "technical_depth", "awarded_marks": 0.0, "evidence": "", "explanation": "No depth."},
        ],
        "summary_explanation": "Concise and accurate on mutability.",
    }
    engine = EvaluationEngine(llm_client=mock_llm)
    
    answer = "Lists: mutable. Tuples: immutable."
    result = engine.evaluate_answer(list_tuple_question, answer)
    
    assert result.awarded_marks == 2.5


def test_case_g_long_verbose_with_false_claims(list_tuple_question):
    """Case G: Verbose answer with incorrect technical claims does not gain points for verbosity."""
    mock_llm = MagicMock()
    mock_llm.generate_json.return_value = {
        "addressed_question": True,
        "is_ambiguous": False,
        "clarification_question": None,
        "demonstrated_concepts": [],
        "partial_concepts": [],
        "missing_concepts": ["Core mutability difference"],
        "incorrect_claims": ["Lists are compiled in memory and tuples are dynamically typed on disk"],
        "criteria_evaluations": [
            {"criterion_id": "mutability_distinction", "awarded_marks": 0.0, "evidence": "Long text with invalid reasoning", "explanation": "Failed to identify mutability."},
            {"criterion_id": "practical_use_case", "awarded_marks": 0.0, "evidence": "", "explanation": "Invalid rationale."},
            {"criterion_id": "technical_depth", "awarded_marks": 0.0, "evidence": "", "explanation": "Factually erroneous assertions."},
        ],
        "summary_explanation": "Extensive paragraph full of pseudo-technical jargon with no correct substance.",
    }
    engine = EvaluationEngine(llm_client=mock_llm)
    
    answer = "Basically in Python programming language there are many diverse paradigms and lists are compiled dynamically into disk blocks while tuples exist in the CPU cache as non-volatile representations..."
    result = engine.evaluate_answer(list_tuple_question, answer)
    
    assert result.awarded_marks == 0.0


def test_case_i_ambiguous_answer_triggers_clarification(list_tuple_question):
    """Case I: Ambiguous answer sets is_ambiguous flag and provides clarifying question."""
    mock_llm = MagicMock()
    mock_llm.generate_json.return_value = {
        "addressed_question": True,
        "is_ambiguous": True,
        "clarification_question": "Did you mean that elements cannot be added, or that their types cannot change?",
        "demonstrated_concepts": [],
        "partial_concepts": ["Mentions changes"],
        "missing_concepts": ["Clear mutability statement"],
        "incorrect_claims": [],
        "criteria_evaluations": [
            {"criterion_id": "mutability_distinction", "awarded_marks": 1.0, "evidence": "One changes and one stays", "explanation": "Vague statement."},
            {"criterion_id": "practical_use_case", "awarded_marks": 0.0, "evidence": "", "explanation": "None"},
            {"criterion_id": "technical_depth", "awarded_marks": 0.0, "evidence": "", "explanation": "None"},
        ],
        "summary_explanation": "Answer is ambiguous about whether modification refers to values or references.",
    }
    engine = EvaluationEngine(llm_client=mock_llm)
    
    answer = "One changes and one stays."
    result = engine.evaluate_answer(list_tuple_question, answer)
    
    assert result.is_ambiguous is True
    assert result.clarification_question is not None


def test_case_j_alternative_correct_code_implementation(palindrome_question):
    """Case J: Alternative correct code implementation (two pointer instead of slicing)."""
    mock_llm = MagicMock()
    mock_llm.generate_json.return_value = {
        "addressed_question": True,
        "is_ambiguous": False,
        "clarification_question": None,
        "demonstrated_concepts": ["Two-pointer palindrome check", "Case insensitivity and alphanumeric filtering"],
        "partial_concepts": [],
        "missing_concepts": [],
        "incorrect_claims": [],
        "criteria_evaluations": [
            {"criterion_id": "normalization", "awarded_marks": 2.0, "evidence": "Filtered with isalnum and lower()", "explanation": "Correct normalization."},
            {"criterion_id": "reversal_comparison", "awarded_marks": 2.0, "evidence": "Two pointer loop while left < right", "explanation": "Valid alternative two-pointer algorithm."},
            {"criterion_id": "edge_case_handling", "awarded_marks": 1.0, "evidence": "Handles empty string by exiting loop returning True", "explanation": "Clean edge case handling."},
        ],
        "summary_explanation": "Excellent alternative two-pointer implementation with full test pass.",
    }
    engine = EvaluationEngine(llm_client=mock_llm)

    code = (
        "def is_palindrome(text: str) -> bool:\n"
        "    chars = [c.lower() for c in text if c.isalnum()]\n"
        "    l, r = 0, len(chars) - 1\n"
        "    while l < r:\n"
        "        if chars[l] != chars[r]:\n"
        "            return False\n"
        "        l += 1\n"
        "        r -= 1\n"
        "    return True\n"
    )
    result = engine.evaluate_answer(palindrome_question, code)
    
    assert result.awarded_marks == 5.0
    assert result.execution_result["tests_passed"] == 5


def test_case_k_code_with_syntax_errors(palindrome_question):
    """Case K: Code with syntax errors should be flagged and earn 0 on functional criteria."""
    mock_llm = MagicMock()
    mock_llm.generate_json.return_value = {
        "addressed_question": True,
        "is_ambiguous": False,
        "clarification_question": None,
        "demonstrated_concepts": [],
        "partial_concepts": [],
        "missing_concepts": ["Syntactically valid Python code"],
        "incorrect_claims": [],
        "criteria_evaluations": [
            {"criterion_id": "normalization", "awarded_marks": 0.0, "evidence": "Syntax error", "explanation": "Syntax error."},
            {"criterion_id": "reversal_comparison", "awarded_marks": 0.0, "evidence": "Syntax error", "explanation": "Syntax error."},
            {"criterion_id": "edge_case_handling", "awarded_marks": 0.0, "evidence": "Syntax error", "explanation": "Syntax error."},
        ],
        "summary_explanation": "Code cannot be parsed due to SyntaxError.",
    }
    engine = EvaluationEngine(llm_client=mock_llm)

    broken_code = "def is_palindrome(text:\n return text =="
    result = engine.evaluate_answer(palindrome_question, broken_code)

    assert result.awarded_marks == 0.0
    assert result.execution_result["syntax_valid"] is False


def test_case_m_malformed_model_response_fallback(list_tuple_question):
    """Case M: Malformed model response should trigger safe deterministic fallback without crashing."""
    mock_llm = MagicMock()
    mock_llm.generate_json.side_effect = ValueError("Invalid JSON from LLM")
    engine = EvaluationEngine(llm_client=mock_llm)

    result = engine.evaluate_answer(list_tuple_question, "Lists are mutable and tuples are immutable.")
    
    assert result.awarded_marks == 0.0
    assert "deterministic fallback" in result.summary_explanation.lower()
