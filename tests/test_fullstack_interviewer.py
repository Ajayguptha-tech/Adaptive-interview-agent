"""
Unit and integration tests for the Independent Full-Stack Interviewer Model.
Verifies track registry, question bank domains, multi-language safe code evaluator
(Node.js JavaScript & SQLite), strict rubric evaluation, adaptive engine,
session lifecycle, and final reporting.
"""

import pytest
from unittest.mock import MagicMock
from fastapi.testclient import TestClient

from backend.main import app, session_manager
from backend.interviewers.registry import InterviewerRegistry
from backend.interviewers.python_interviewer import PythonInterviewer
from backend.interviewers.fullstack_interviewer import FullStackInterviewer
from backend.fullstack.question_bank import (
    get_all_fullstack_questions,
    get_all_fullstack_topics,
    get_all_fullstack_competencies,
    get_fullstack_question_by_id,
    TECH_STACK_CONFIGS,
)
from backend.fullstack.code_evaluator import FullStackCodeEvaluator
from backend.fullstack.evaluator import FullStackEvaluationEngine
from backend.fullstack.adaptive_engine import FullStackAdaptiveEngine, FullStackCompetencyTracker
from backend.models import (
    StartInterviewRequest,
    InterviewMode,
    DifficultyLevel,
    QuestionType,
    EvaluationResult,
)

client = TestClient(app)


# =============================================================================
# 1. TRACK REGISTRY & ISOLATION TESTS
# =============================================================================

def test_registry_track_retrieval_and_rejection():
    """Verify registry returns correct adapters and rejects unknown tracks without fallback."""
    registry = InterviewerRegistry()
    
    py_interviewer = registry.get("python")
    assert isinstance(py_interviewer, PythonInterviewer)
    
    fs_interviewer = registry.get("fullstack")
    assert isinstance(fs_interviewer, FullStackInterviewer)
    
    # Must reject unknown track and NEVER silently fall back
    with pytest.raises(ValueError, match="Unknown interviewer track"):
        registry.get("golang")

    with pytest.raises(ValueError, match="Unknown interviewer track"):
        registry.get("java")


def test_api_tracks_endpoint():
    """GET /api/tracks should return all registered tracks."""
    response = client.get("/api/tracks")
    assert response.status_code == 200
    data = response.json()
    assert "tracks" in data
    track_ids = [t["id"] for t in data["tracks"]]
    assert "python" in track_ids
    assert "fullstack" in track_ids


def test_api_topics_fullstack_endpoint():
    """GET /api/topics?track=fullstack should return Full-Stack topics and tech stacks."""
    response = client.get("/api/topics?track=fullstack")
    assert response.status_code == 200
    data = response.json()
    assert data["track"] == "fullstack"
    assert len(data["topics"]) >= 5
    assert "JavaScript Core" in data["topics"]
    assert "SQL & Databases" in data["topics"]
    assert len(data["tech_stacks"]) >= 3


def test_api_topics_unknown_track_returns_400():
    """GET /api/topics with unknown track should return 400 Bad Request."""
    response = client.get("/api/topics?track=unknown_lang")
    assert response.status_code == 400
    assert "Unknown interviewer track" in response.json()["detail"]


# =============================================================================
# 2. FULL-STACK QUESTION BANK TESTS
# =============================================================================

def test_fullstack_question_bank_coverage():
    """Verify curated question bank covers all mandatory web tiers and difficulties."""
    questions = get_all_fullstack_questions()
    assert len(questions) >= 12, "Curated bank must contain sufficient quality questions"
    
    difficulties = {q.difficulty for q in questions}
    assert DifficultyLevel.BEGINNER in difficulties
    assert DifficultyLevel.INTERMEDIATE in difficulties
    assert DifficultyLevel.ADVANCED in difficulties

    topics = get_all_fullstack_topics()
    assert "HTML & Semantic Web" in topics
    assert "CSS Layout & Box Model" in topics
    assert "JavaScript Core" in topics
    assert "React & Component Architecture" in topics
    assert "Backend & REST APIs" in topics
    assert "SQL & Databases" in topics
    assert "Full-Stack Integration & Architecture" in topics

    # Check question types
    types = {q.question_type for q in questions}
    assert QuestionType.CONCEPTUAL in types
    assert QuestionType.CODE_WRITING in types
    assert QuestionType.CODE_OUTPUT in types
    assert QuestionType.DEBUGGING in types


def test_question_metadata_integrity():
    """Verify each question has complete rubrics and expected concepts."""
    for q in get_all_fullstack_questions():
        assert q.track == "fullstack"
        assert q.total_marks > 0
        assert len(q.rubric) > 0
        assert sum(r.max_marks for r in q.rubric) == pytest.approx(q.total_marks)
        if q.question_type == QuestionType.CODE_WRITING:
            assert q.language in ("javascript", "sql", "html", "python")


# =============================================================================
# 3. FUNCTIONAL MULTI-LANGUAGE CODE EVALUATOR TESTS
# =============================================================================

def test_javascript_passing_execution():
    """Functional verification: valid JS implementation passes test assertions in Node.js."""
    code = """
function groupBy(items, key) {
    return items.reduce((acc, item) => {
        const val = item[key];
        (acc[val] = acc[val] || []).push(item);
        return acc;
    }, {});
}
"""
    test_cases = [
        {
            "input": [[{"id": 1, "g": "a"}, {"id": 2, "g": "b"}, {"id": 3, "g": "a"}], "g"],
            "expected": {"a": [{"id": 1, "g": "a"}, {"id": 3, "g": "a"}], "b": [{"id": 2, "g": "b"}]},
        }
    ]
    res = FullStackCodeEvaluator.evaluate_javascript(
        candidate_code=code,
        test_cases=test_cases,
        function_name="groupBy",
    )
    assert res["executed"] is True
    assert res["syntax_valid"] is True
    assert res["tests_passed"] == 1
    assert res["tests_total"] == 1


def test_javascript_failing_logic_returns_zero():
    """Functional verification: syntactically valid but incorrect JS fails tests."""
    wrong_code = """
function groupBy(items, key) {
    return {};
}
"""
    test_cases = [
        {
            "input": [[{"id": 1, "g": "a"}], "g"],
            "expected": {"a": [{"id": 1, "g": "a"}]},
        }
    ]
    res = FullStackCodeEvaluator.evaluate_javascript(
        candidate_code=wrong_code,
        test_cases=test_cases,
        function_name="groupBy",
    )
    assert res["executed"] is True
    assert res["syntax_valid"] is True
    assert res["tests_passed"] == 0
    assert res["tests_total"] == 1


def test_javascript_syntax_error_handled_cleanly():
    """Functional verification: syntax error produces 0 passed tests and captures error."""
    broken_code = "function groupBy(items, key) { const x = ; return x; }"
    res = FullStackCodeEvaluator.evaluate_javascript(
        candidate_code=broken_code,
        test_cases=[{"input": [], "expected": {}}],
        function_name="groupBy",
    )
    assert res["syntax_valid"] is False
    assert res["tests_passed"] == 0


def test_sql_in_memory_sqlite_execution_success():
    """Functional verification: SQL query executes in sandbox and compares output rows."""
    schema = """
CREATE TABLE departments (id INTEGER PRIMARY KEY, name TEXT);
CREATE TABLE employees (id INTEGER PRIMARY KEY, name TEXT, salary INTEGER, dept_id INTEGER);
INSERT INTO departments VALUES (1, 'Engineering'), (2, 'Marketing');
INSERT INTO employees VALUES (1, 'Alice', 95000, 1), (2, 'Bob', 110000, 1), (3, 'Charlie', 70000, 2);
"""
    query = "SELECT name, salary FROM employees WHERE dept_id = 1 ORDER BY salary DESC;"
    expected_rows = [{"name": "Bob", "salary": 110000}, {"name": "Alice", "salary": 95000}]

    res = FullStackCodeEvaluator.evaluate_sql(
        candidate_sql=query,
        db_schema=schema,
        expected_rows=expected_rows,
    )
    assert res["executed"] is True
    assert res["syntax_valid"] is True
    assert res["tests_passed"] == 1


def test_sql_incorrect_query_fails():
    """Functional verification: SQL query with wrong order or filter fails."""
    schema = """
CREATE TABLE employees (id INTEGER PRIMARY KEY, salary INTEGER);
INSERT INTO employees VALUES (1, 50000), (2, 80000);
"""
    wrong_query = "SELECT salary FROM employees WHERE salary > 90000;"
    expected_rows = [{"salary": 80000}]

    res = FullStackCodeEvaluator.evaluate_sql(
        candidate_sql=wrong_query,
        db_schema=schema,
        expected_rows=expected_rows,
    )
    assert res["tests_passed"] == 0


# =============================================================================
# 4. FULL-STACK EVALUATION ENGINE STRICT SCORING TESTS
# =============================================================================

def test_fullstack_evaluator_strict_output_prediction():
    """Output prediction must match expected output deterministically; wrong gets 0."""
    engine = FullStackEvaluationEngine()
    q = get_fullstack_question_by_id("fs-beg-js-001")  # JS Event loop output prediction
    assert q is not None

    # Correct output: 1 5 3 4 2
    res_correct = engine.evaluate_answer(q, "1\n5\n3\n4\n2")
    assert res_correct.awarded_marks == pytest.approx(q.total_marks)
    assert res_correct.percentage == 100.0

    # Wrong output: 1 2 3 4
    res_wrong = engine.evaluate_answer(q, "1 2 3 4")
    assert res_wrong.awarded_marks == 0.0
    assert res_wrong.percentage == 0.0


def test_fullstack_evaluator_strict_coding_question():
    """Strict coding question with failed tests must receive 0.0 marks."""
    mock_llm = MagicMock()
    mock_llm.generate_json.return_value = {
        "awarded_marks": 5.0,
        "max_marks": 5.0,
        "percentage": 100.0,
        "summary_explanation": "Clean groupBy implementation",
        "demonstrated_concepts": ["Functional reduction", "Object grouping"],
        "missing_concepts": [],
        "incorrect_claims": [],
        "criteria_evaluations": [
            {"criterion_id": "reducer_logic", "awarded_marks": 2.5, "max_marks": 2.5, "evidence": "Used reduce", "explanation": "Valid"},
            {"criterion_id": "dual_selector_support", "awarded_marks": 2.5, "max_marks": 2.5, "evidence": "All tests pass", "explanation": "Valid"},
        ],
    }
    engine = FullStackEvaluationEngine(llm_client=mock_llm)
    q = get_fullstack_question_by_id("fs-int-js-001")  # Array groupBy coding
    assert q is not None

    # Passing code (handles both property key and selector callback)
    valid_code = """
function groupBy(items, key) {
    const getKey = typeof key === 'function' ? key : (item) => item[key];
    return items.reduce((acc, item) => {
        const k = getKey(item);
        (acc[k] = acc[k] || []).push(item);
        return acc;
    }, {});
}
"""
    res_pass = engine.evaluate_answer(q, valid_code)
    assert res_pass.awarded_marks > 0.0
    assert res_pass.percentage >= 80.0

    # Syntax error code must strictly get 0.0 marks
    bad_code = "function groupBy(items, key) { return items.bad( "
    res_bad = engine.evaluate_answer(q, bad_code)
    assert res_bad.awarded_marks == 0.0
    assert res_bad.percentage == 0.0


def test_fullstack_evaluator_empty_answer_gives_zero():
    """Empty or irrelevant conceptual answers receive 0.0 marks without calling LLM."""
    mock_llm = MagicMock()
    engine = FullStackEvaluationEngine(llm_client=mock_llm)
    q = get_fullstack_question_by_id("fs-beg-html-001")
    assert q is not None

    res = engine.evaluate_answer(q, "   ")
    assert res.awarded_marks == 0.0
    assert res.percentage == 0.0
    assert mock_llm.generate_json.call_count == 0


# =============================================================================
# 5. FULL-STACK ADAPTIVE SELECTION TESTS
# =============================================================================

def test_fullstack_adaptive_progression():
    """Adaptive engine increases difficulty on high score and decreases on low score."""
    tracker = FullStackCompetencyTracker()
    tracker.current_difficulty = DifficultyLevel.BEGINNER

    q_beg = get_fullstack_question_by_id("fs-beg-html-001")
    eval_strong = EvaluationResult(
        question_id=q_beg.id,
        awarded_marks=5.0,
        max_marks=5.0,
        percentage=100.0,
        criteria_evaluations=[],
        summary_explanation="Strong",
    )
    tracker.record_answer(q_beg, eval_strong)

    next_q, reason = FullStackAdaptiveEngine.select_next_question(
        tracker=tracker,
        mode=InterviewMode.ADAPTIVE,
        last_question=q_beg,
        last_evaluation=eval_strong,
        use_dynamic=False,
    )
    assert next_q is not None
    assert next_q.difficulty in (DifficultyLevel.INTERMEDIATE, DifficultyLevel.ADVANCED)
    assert next_q.track == "fullstack"


# =============================================================================
# 6. SESSION LIFECYCLE & REPORTING TESTS (FULL-STACK TRACK)
# =============================================================================

def test_fullstack_session_end_to_end_predefined():
    """Complete 2-question Full-Stack session in predefined testing mode."""
    # Mock evaluation engine so test runs deterministically and instantly
    mock_eval = MagicMock()
    mock_eval.evaluate_answer.return_value = EvaluationResult(
        question_id="fs-beg-html-001",
        awarded_marks=4.5,
        max_marks=5.0,
        percentage=90.0,
        criteria_evaluations=[],
        summary_explanation="Solid semantic web explanation",
    )
    fs_interviewer = FullStackInterviewer(eval_engine=mock_eval)
    registry = InterviewerRegistry()
    registry.register("fullstack", fs_interviewer)

    custom_manager = session_manager.__class__(registry=registry)

    req = StartInterviewRequest(
        role="Full-Stack Developer",
        track="fullstack",
        tech_stack="React + Node.js + Express + SQL",
        max_questions=2,
        difficulty_mode=InterviewMode.BEGINNER,
        dynamic_questions=False,
    )
    session = custom_manager.start_session(req)
    assert session.track == "fullstack"
    assert session.current_question.track == "fullstack"

    # Submit Answer 1
    res1 = custom_manager.submit_answer(session.session_id, "Semantic tags provide accessibility landmarks and SEO value.")
    assert res1["question_number"] == 1
    assert res1["is_complete"] is False

    # Submit Answer 2 (final)
    res2 = custom_manager.submit_answer(session.session_id, "1 4 3 2")
    assert res2["question_number"] == 2
    assert res2["is_complete"] is True
    assert session.status == "completed"

    # Generate Report
    report = custom_manager.generate_report(session.session_id)
    assert report.track == "fullstack"
    assert report.tech_stack == "React + Node.js + Express + SQL"
    assert report.questions_completed == 2
    assert report.normalized_score >= 0.0
    assert len(report.topic_scores) > 0


def test_fullstack_early_termination_generates_valid_report():
    """Ending fullstack interview early preserves history and generates report immediately."""
    req = StartInterviewRequest(
        role="Full-Stack Engineer",
        track="fullstack",
        max_questions=5,
        difficulty_mode=InterviewMode.BEGINNER,
        dynamic_questions=False,
    )
    session = session_manager.start_session(req)

    # End early via API
    resp = client.post(f"/api/interview/{session.session_id}/end", json={"status": "ended_early"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ended_early"
    report = data["report"]
    assert report["track"] == "fullstack"
    assert report["questions_completed"] == 0
    assert report["questions_unanswered"] == 5
    assert "Ended Early" in report["note"]
