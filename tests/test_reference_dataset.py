"""
Reference Evaluation Dataset and Regression Suite.
Maintains a curated dataset of representative candidate responses with
expected criterion-level outcomes, score ranges, and misconception detection.
Used to detect evaluation scoring regressions.
"""

from typing import Dict, Any, List
from unittest.mock import MagicMock
import pytest
from backend.question_bank import get_question_by_id
from backend.evaluator import EvaluationEngine

# Reference dataset of candidate responses with expected outcomes
REFERENCE_DATASET: List[Dict[str, Any]] = [
    {
        "case_id": "REF-001-LIST-TUPLE-STRONG",
        "question_id": "py-beg-001",
        "candidate_answer": (
            "Lists in Python are mutable so elements can be appended or removed. "
            "Tuples are immutable once initialized. I use tuples for geographic coordinates "
            "like (lat, lon) and as keys in dictionaries because they are hashable."
        ),
        "expected_score_min": 4.5,
        "expected_score_max": 5.0,
        "required_criteria_awarded": ["mutability_distinction", "practical_use_case"],
        "expected_misconceptions": [],
        "mock_response": {
            "addressed_question": True,
            "is_ambiguous": False,
            "clarification_question": None,
            "demonstrated_concepts": ["List mutability", "Tuple immutability", "Coordinates use case", "Hashability"],
            "partial_concepts": [],
            "missing_concepts": [],
            "incorrect_claims": [],
            "criteria_evaluations": [
                {"criterion_id": "mutability_distinction", "awarded_marks": 2.5, "evidence": "Lists mutable, tuples immutable", "explanation": "Accurate"},
                {"criterion_id": "practical_use_case", "awarded_marks": 1.5, "evidence": "Geographic coordinates (lat, lon)", "explanation": "Valid"},
                {"criterion_id": "technical_depth", "awarded_marks": 1.0, "evidence": "Hashable as dict keys", "explanation": "Accurate"},
            ],
            "summary_explanation": "Comprehensive answer with valid mutability and hashability distinction.",
        },
    },
    {
        "case_id": "REF-002-DEFAULT-ARG-BUG",
        "question_id": "py-beg-003",
        "candidate_answer": (
            "The default cart list is only created once when the function is defined. "
            "So every call modifies that same list in memory. "
            "You should set cart=None as the default, and inside do: if cart is None: cart = []"
        ),
        "expected_score_min": 4.5,
        "expected_score_max": 5.0,
        "required_criteria_awarded": ["identify_bug_cause", "provide_idiomatic_fix"],
        "expected_misconceptions": [],
        "mock_response": {
            "addressed_question": True,
            "is_ambiguous": False,
            "clarification_question": None,
            "demonstrated_concepts": ["Default arg evaluated at definition time", "Mutable default sharing state", "Default None idiom"],
            "partial_concepts": [],
            "missing_concepts": [],
            "incorrect_claims": [],
            "criteria_evaluations": [
                {"criterion_id": "identify_bug_cause", "awarded_marks": 2.5, "evidence": "default cart list is only created once when function is defined", "explanation": "Clear explanation"},
                {"criterion_id": "provide_idiomatic_fix", "awarded_marks": 2.0, "evidence": "cart=None and if cart is None: cart = []", "explanation": "Idiomatic fix"},
                {"criterion_id": "code_clarity", "awarded_marks": 0.5, "evidence": "every call modifies that same list in memory", "explanation": "Clear"},
            ],
            "summary_explanation": "Accurately diagnosed mutable default parameter bug with idiomatic None fix.",
        },
    },
    {
        "case_id": "REF-003-GIL-CONCURRENCY",
        "question_id": "py-adv-002",
        "candidate_answer": (
            "The GIL is CPython's mutex ensuring only one native thread runs Python bytecode at a time. "
            "For CPU-bound tasks, threading gives no speedup; multiprocessing must be used to bypass the GIL with multiple processes. "
            "For network I/O, asyncio or threading work well because I/O operations release the lock."
        ),
        "expected_score_min": 4.5,
        "expected_score_max": 5.0,
        "required_criteria_awarded": ["gil_definition_and_mechanism", "multiprocessing_vs_threading", "asyncio_event_loop"],
        "expected_misconceptions": [],
        "mock_response": {
            "addressed_question": True,
            "is_ambiguous": False,
            "clarification_question": None,
            "demonstrated_concepts": ["GIL is CPython mutex", "CPU-bound requires multiprocessing", "I/O releases lock", "asyncio/threading for I/O"],
            "partial_concepts": [],
            "missing_concepts": [],
            "incorrect_claims": [],
            "criteria_evaluations": [
                {"criterion_id": "gil_definition_and_mechanism", "awarded_marks": 1.5, "evidence": "GIL is CPython mutex", "explanation": "Accurate definition"},
                {"criterion_id": "multiprocessing_vs_threading", "awarded_marks": 1.5, "evidence": "CPU-bound requires multiprocessing", "explanation": "Clear distinction"},
                {"criterion_id": "asyncio_event_loop", "awarded_marks": 1.5, "evidence": "asyncio or threading for network I/O", "explanation": "Accurate"},
                {"criterion_id": "thread_safety_nuance", "awarded_marks": 0.5, "evidence": "I/O releases lock", "explanation": "Good detail"},
            ],
            "summary_explanation": "Thorough breakdown of GIL, CPU vs I/O bound workloads, and process vs async selection.",
        },
    },
    {
        "case_id": "REF-004-MISCONCEPTION-DETECTION",
        "question_id": "py-beg-001",
        "candidate_answer": (
            "Tuples and lists are identical except tuples are stored on SSD while lists are in RAM. "
            "Also tuples can never contain lists."
        ),
        "expected_score_min": 0.0,
        "expected_score_max": 0.5,
        "required_criteria_awarded": [],
        "expected_misconceptions": ["tuples stored on SSD", "tuples cannot contain lists"],
        "mock_response": {
            "addressed_question": True,
            "is_ambiguous": False,
            "clarification_question": None,
            "demonstrated_concepts": [],
            "partial_concepts": [],
            "missing_concepts": ["Immutability distinction"],
            "incorrect_claims": ["Tuples are stored on SSD while lists are in RAM", "Tuples can never contain lists"],
            "criteria_evaluations": [
                {"criterion_id": "mutability_distinction", "awarded_marks": 0.0, "evidence": "Claimed identical memory difference", "explanation": "Incorrect"},
                {"criterion_id": "practical_use_case", "awarded_marks": 0.0, "evidence": "None", "explanation": "None"},
                {"criterion_id": "technical_depth", "awarded_marks": 0.0, "evidence": "False assertions", "explanation": "Erroneous"},
            ],
            "summary_explanation": "Demonstrates gross misconceptions about storage and nested mutability.",
        },
    },
]


@pytest.mark.parametrize("case", REFERENCE_DATASET, ids=[c["case_id"] for c in REFERENCE_DATASET])
def test_reference_dataset_cases(case):
    """Executes reference dataset regression tests."""
    q = get_question_by_id(case["question_id"])
    assert q is not None, f"Question {case['question_id']} not found."

    mock_llm = MagicMock()
    mock_llm.generate_json.return_value = case["mock_response"]
    engine = EvaluationEngine(llm_client=mock_llm)

    result = engine.evaluate_answer(q, case["candidate_answer"])

    # Score bounds check
    assert case["expected_score_min"] <= result.awarded_marks <= case["expected_score_max"], (
        f"Score {result.awarded_marks} outside expected range "
        f"[{case['expected_score_min']}, {case['expected_score_max']}] for {case['case_id']}"
    )

    # Required criteria awarded
    criteria_awarded_ids = [
        c.criterion_id for c in result.criteria_evaluations if c.awarded_marks > 0
    ]
    for required_crit in case["required_criteria_awarded"]:
        assert required_crit in criteria_awarded_ids, (
            f"Expected criterion '{required_crit}' to receive marks in {case['case_id']}"
        )

    # Misconceptions check
    if case["expected_misconceptions"]:
        assert len(result.incorrect_claims) > 0, (
            f"Expected misconceptions to be flagged for {case['case_id']}"
        )
