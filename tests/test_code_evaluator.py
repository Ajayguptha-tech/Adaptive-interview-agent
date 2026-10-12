"""
Tests for CodeEvaluator: static AST analysis, unsafe construct detection,
isolated subprocess execution, and timeout safety.
"""

import pytest
from backend.code_evaluator import CodeEvaluator


def test_static_analysis_valid_code():
    code = (
        "def add(a: int, b: int) -> int:\n"
        "    return a + b\n"
    )
    result = CodeEvaluator.analyze_static(code)
    assert result["valid_syntax"] is True
    assert "add" in result["functions"]
    assert result["error"] is None
    assert len(result["unsafe_flags"]) == 0


def test_static_analysis_syntax_error():
    code = "def broken(\n   return 42"
    result = CodeEvaluator.analyze_static(code)
    assert result["valid_syntax"] is False
    assert "SyntaxError" in result["error"]


def test_static_analysis_detects_unsafe_constructs():
    code = (
        "import os\n"
        "def delete_all():\n"
        "    os.system('rm -rf /')\n"
    )
    result = CodeEvaluator.analyze_static(code)
    assert result["valid_syntax"] is True
    assert any("restricted module 'os'" in flag for flag in result["unsafe_flags"])


def test_static_analysis_detects_eval_call():
    code = (
        "def run_dynamic(code_str):\n"
        "    return eval(code_str)\n"
    )
    result = CodeEvaluator.analyze_static(code)
    assert result["valid_syntax"] is True
    assert any("restricted built-in 'eval'" in flag for flag in result["unsafe_flags"])


def test_isolated_execution_passes_all_tests():
    code = (
        "def is_palindrome(text: str) -> bool:\n"
        "    cleaned = ''.join(c.lower() for c in text if c.isalnum())\n"
        "    return cleaned == cleaned[::-1]\n"
    )
    test_cases = [
        {"input": "racecar", "expected": True},
        {"input": "A man, a plan, a canal: Panama!", "expected": True},
        {"input": "python", "expected": False},
    ]
    result = CodeEvaluator.evaluate_code(
        candidate_code=code,
        test_cases=test_cases,
        function_name="is_palindrome",
    )
    assert result["executed"] is True
    assert result["syntax_valid"] is True
    assert result["tests_passed"] == 3
    assert result["tests_total"] == 3
    assert result["execution_error"] is None


def test_isolated_execution_partial_tests_fail():
    code = (
        "def is_palindrome(text: str) -> bool:\n"
        "    # Bug: fails to handle uppercase or punctuation\n"
        "    return text == text[::-1]\n"
    )
    test_cases = [
        {"input": "racecar", "expected": True},
        {"input": "Racecar", "expected": True},  # will fail due to case
    ]
    result = CodeEvaluator.evaluate_code(
        candidate_code=code,
        test_cases=test_cases,
        function_name="is_palindrome",
    )
    assert result["executed"] is True
    assert result["tests_passed"] == 1
    assert result["tests_total"] == 2


def test_isolated_execution_timeout_prevention():
    code = (
        "def infinite_loop(x):\n"
        "    while True:\n"
        "        pass\n"
    )
    test_cases = [{"input": 1, "expected": 2}]
    result = CodeEvaluator.evaluate_code(
        candidate_code=code,
        test_cases=test_cases,
        timeout_seconds=0.5,
    )
    assert result["executed"] is True
    assert result["tests_passed"] == 0
    assert "timed out" in result["execution_error"]
