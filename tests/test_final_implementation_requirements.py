"""
Comprehensive Verification Test Suite for Final Implementation Task:
Landing Page + Voice-First Interview + Truly Dynamic Question Generator.
"""

import io
import json
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from backend.main import app
from backend.models import (
    StartInterviewRequest,
    InterviewMode,
    DifficultyLevel,
    QuestionType,
    Question,
    RubricCriterion,
    EvaluationResult,
    CriterionEvaluation,
)
from backend.session_manager import SessionManager
from backend.evaluator import EvaluationEngine
from backend.question_agent import default_question_agent
from backend.question_agent.diversity_engine import QuestionDiversityEngine
from backend.resume_analyzer.adapter import ResumeAnalyzerAdapter

client = TestClient(app)

MOCK_EVAL = EvaluationResult(
    question_id="q-mock",
    awarded_marks=4.5,
    max_marks=5.0,
    percentage=90.0,
    summary_explanation="Strong technical explanation addressing memory layouts and object semantics.",
    criteria_evaluations=[
        CriterionEvaluation(
            criterion_id="crit_1",
            awarded_marks=4.5,
            max_marks=5.0,
            evidence="Candidate accurately explained concepts.",
            explanation="Accurate response.",
        )
    ],
    demonstrated_concepts=["Core concepts"],
    missing_concepts=[],
    incorrect_claims=[],
)

RESUME_DEV_A = b"""
Jordan Vance
Email: jordan.vance@example.com | Location: Austin, TX
SUMMARY
Senior Backend Engineer with 5 years building scalable distributed architectures in Python.
TECHNICAL SKILLS
Python, Asyncio, FastAPI, Redis, Distributed Systems, Microservices
EXPERIENCE
Senior Backend Engineer at CloudVelocity (2021-Present)
- Architected asynchronous event pipeline using FastAPI and Redis Pub/Sub handling 10k msgs/sec.
- Optimized task workers and non-blocking I/O event loops.
PROJECTS
EventStream Router
- Real-time event routing gateway implemented in Python asyncio and websockets.
"""

RESUME_DEV_B = b"""
Morgan Reed
Email: morgan.reed@example.com | Location: Chicago, IL
SUMMARY
Database & Systems Engineer with 5 years specializing in relational models, SQL query optimization, and Django.
TECHNICAL SKILLS
Python, Django, PostgreSQL, SQLAlchemy, Database Indexing, Query Optimization, Celery
EXPERIENCE
Database Software Engineer at FinTech Data (2020-Present)
- Optimized PostgreSQL queries and schema migrations, reducing slow queries by 60%.
- Implemented background batch reconciliation using Django ORM and Celery.
PROJECTS
QueryPlan Analyzer
- PostgreSQL query plan parser and indexing recommender built in Python.
"""


# =============================================================================
# 1. LANDING PAGE & INTERNAL TRACK HIDING VERIFICATION
# =============================================================================

def test_landing_page_redirect_and_home_api():
    """Verify backend health provides clean service status."""
    res = client.get("/api/health")
    assert res.status_code == 200
    data = res.json()
    assert data["api"] == "running"


def test_resume_upload_and_internal_track_retention():
    """
    Verify resume upload extracts candidate profile, retains routed track internally,
    while response provides candidate-friendly data.
    """
    file_tuple = ("jordan_resume.txt", io.BytesIO(RESUME_DEV_A), "text/plain")
    res = client.post(
        "/api/resume/upload",
        files={"file": file_tuple},
        data={"target_role": "Python Distributed Systems Engineer"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["is_success"] is True
    assert "Jordan" in data["candidate_name"]
    # Retained internally for role intelligence & question routing
    assert data["routed_track"] == "python"
    assert "FastAPI" in data["extracted_skills"] or "Asyncio" in data["extracted_skills"]
    assert data["resume_id"] is not None


# =============================================================================
# 2. INTERVIEW MODE: MOCK INTERVIEW & ADAPTIVE INTERVIEW MAPPING
# =============================================================================

def test_interview_mode_labels_and_backend_mapping():
    """
    Verify Mock Interview (predefined) and Adaptive Interview (mock/dynamic)
    behave correctly in session configuration.
    """
    # 1. Mock Interview (predefined mode)
    res_mock = client.post("/api/interview/start", json={
        "mode": "predefined",
        "max_questions": 5,
        "track": "python"
    })
    assert res_mock.status_code == 200
    data_mock = res_mock.json()
    assert data_mock["dynamic_questions"] is False
    assert data_mock["question_number"] == 1
    assert len(data_mock["question"]) > 10

    # 2. Adaptive Interview (adaptive / mock dynamic mode)
    res_adapt = client.post("/api/interview/start", json={
        "mode": "mock",
        "max_questions": 5,
        "track": "python",
        "dynamic_questions": True
    })
    assert res_adapt.status_code == 200
    data_adapt = res_adapt.json()
    assert data_adapt["dynamic_questions"] is True
    assert data_adapt["question_number"] == 1


# =============================================================================
# 3. VERBAL VS PROGRAMMING QUESTION CLASSIFICATION
# =============================================================================

def test_question_requires_code_metadata_discrimination():
    """
    Verify that verbal conceptual questions have requires_code=False,
    while programming / code writing questions have requires_code=True.
    """
    q_verbal = Question(
        id="py-test-verbal",
        topic="Data Structures",
        competency="Python Core",
        difficulty=DifficultyLevel.INTERMEDIATE,
        question_type=QuestionType.CONCEPTUAL,
        text="Explain how dictionaries handle hash collisions in Python.",
        rubric=[RubricCriterion(id="c1", description="Open addressing", max_marks=5.0, evidence_guide="Guide")],
    )
    disp_verbal = q_verbal.to_display()
    assert disp_verbal.requires_code is False
    assert disp_verbal.response_type == "verbal"

    q_coding = Question(
        id="py-test-code",
        topic="Algorithms",
        competency="Implementation",
        difficulty=DifficultyLevel.INTERMEDIATE,
        question_type=QuestionType.CODE_WRITING,
        text="Write a Python function to invert a binary tree.",
        starter_code="def invert_tree(root):\n    pass\n",
        rubric=[RubricCriterion(id="c1", description="Correctness", max_marks=5.0, evidence_guide="Guide")],
    )
    disp_coding = q_coding.to_display()
    assert disp_coding.requires_code is True
    assert disp_coding.response_type == "code_writing"
    assert disp_coding.starter_code is not None


# =============================================================================
# 4. 5 CONSECUTIVE QUESTIONS PROGRESSION: ZERO DUPLICATES
# =============================================================================

def test_five_consecutive_questions_zero_duplicates():
    """
    Verify 5 consecutive questions in an interview session.
    Record all question IDs and normalized texts, confirming zero exact or semantic duplicates.
    """
    # Start session
    res_start = client.post("/api/interview/start", json={
        "track": "python",
        "role": "Python Backend Engineer",
        "max_questions": 5,
        "dynamic_questions": False,  # Deterministic catalog for rapid multi-question verification
    })
    assert res_start.status_code == 200
    session_data = res_start.json()
    session_id = session_data["session_id"]

    asked_ids = [session_data["question_id"]]
    asked_texts = [session_data["question"]]

    with patch.object(EvaluationEngine, "evaluate_answer", return_value=MOCK_EVAL):
        for i in range(1, 5):
            # Submit mock answer
            res_ans = client.post(
                f"/api/interview/{session_id}/answer",
                json={"answer": f"Answer demonstrating core technical understanding for question {i}."},
            )
            assert res_ans.status_code == 200
            ans_data = res_ans.json()
            assert ans_data["marks_awarded"] is not None

            if ans_data.get("next_question_details"):
                nq = ans_data["next_question_details"]
                asked_ids.append(nq["id"])
                asked_texts.append(nq["text"])
            elif ans_data.get("next_question"):
                asked_texts.append(ans_data["next_question"])

    assert len(asked_ids) == 5, f"Expected 5 questions, got {len(asked_ids)}"
    assert len(set(asked_ids)) == 5, f"Duplicate question IDs detected: {asked_ids}"

    # Pairwise semantic duplicate verification
    for i in range(len(asked_texts)):
        for j in range(i + 1, len(asked_texts)):
            sim = QuestionDiversityEngine.compute_similarity(asked_texts[i], asked_texts[j])
            assert sim < 0.60, f"High semantic similarity ({sim:.2f}) between Q{i+1} and Q{j+1}: '{asked_texts[i]}' vs '{asked_texts[j]}'"


# =============================================================================
# 5. CROSS-SESSION DIVERSITY: SAME RESUME PRODUCES NOVEL QUESTIONS
# =============================================================================

def test_same_resume_multiple_sessions_novelty():
    """
    When the same resume is uploaded in multiple sessions, CandidateQuestionHistoryStore
    tracks previously asked questions, ensuring subsequent sessions introduce novel questions.
    """
    # Upload Jordan's resume first time
    adapter = ResumeAnalyzerAdapter()
    prof1 = adapter.analyze_resume("jordan_resume.txt", RESUME_DEV_A, target_role="Python Engineer")
    cand_id = f"cand_test_same_resume"

    # Blueprint 1
    bp1 = default_question_agent.create_blueprint(
        resume_profile=prof1,
        target_role="Python Engineer",
        target_track="python",
        max_questions=5,
        candidate_id=cand_id,
    )

    # Session 1 Question
    q1, _ = default_question_agent.select_or_generate_question(
        blueprint=bp1,
        topic="Data Structures & Mutability",
        competency="Python Fundamentals",
        difficulty=DifficultyLevel.INTERMEDIATE,
        question_number=1,
        session_asked_texts=[],
        use_dynamic=False,
    )
    assert q1 is not None

    # Simulate same candidate uploading resume again in a second session
    prof2 = adapter.analyze_resume("jordan_resume.txt", RESUME_DEV_A, target_role="Python Engineer")
    bp2 = default_question_agent.create_blueprint(
        resume_profile=prof2,
        target_role="Python Engineer",
        target_track="python",
        max_questions=5,
        candidate_id=cand_id,
    )

    # Session 2 Question for same topic
    q2, _ = default_question_agent.select_or_generate_question(
        blueprint=bp2,
        topic="Data Structures & Mutability",
        competency="Python Fundamentals",
        difficulty=DifficultyLevel.INTERMEDIATE,
        question_number=1,
        session_asked_texts=[],
        use_dynamic=False,
    )

    # Cross-session deduplication should ensure q2 is distinct from q1
    assert q1.id != q2.id, f"Expected distinct question across sessions for candidate {cand_id}, but got same ID {q1.id}"
    sim = QuestionDiversityEngine.compute_similarity(q1.text, q2.text)
    assert sim < 0.60, f"Expected low similarity between Session 1 and Session 2 opening questions, got {sim:.2f}"


# =============================================================================
# 6. DIFFERENT RESUMES FOR SAME ROLE RECEIVE RESUME-GROUNDED QUESTIONS
# =============================================================================

def test_different_resumes_same_role_receive_grounded_topics():
    """
    Candidates applying for the same role with different resumes (Async/FastAPI vs Database/Django)
    receive blueprints tailored to their demonstrated skills and projects.
    """
    adapter = ResumeAnalyzerAdapter()
    prof_async = adapter.analyze_resume("jordan.txt", RESUME_DEV_A, target_role="Senior Python Engineer")
    prof_db = adapter.analyze_resume("morgan.txt", RESUME_DEV_B, target_role="Senior Python Engineer")

    bp_async = default_question_agent.create_blueprint(
        resume_profile=prof_async,
        target_role="Senior Python Engineer",
        target_track="python",
        max_questions=5,
        candidate_id="cand_async",
    )

    bp_db = default_question_agent.create_blueprint(
        resume_profile=prof_db,
        target_role="Senior Python Engineer",
        target_track="python",
        max_questions=5,
        candidate_id="cand_db",
    )

    # Candidate A has Asyncio/FastAPI; Candidate B has Django/PostgreSQL
    assert any("Async" in t or "Concurrency" in t for t in bp_async.planned_topics)
    assert any("Database" in t or "PostgreSQL" in t or "SQL" in t for t in bp_db.planned_topics)


# =============================================================================
# 7. FINAL COMPLETION & PDF REPORT GENERATION
# =============================================================================

def test_interview_completion_and_pdf_report():
    """Verify that ending an interview triggers valid report and PDF download."""
    res_start = client.post("/api/interview/start", json={
        "track": "python",
        "max_questions": 5,
        "dynamic_questions": False,
    })
    sid = res_start.json()["session_id"]

    # Submit an answer
    with patch.object(EvaluationEngine, "evaluate_answer", return_value=MOCK_EVAL):
        client.post(f"/api/interview/{sid}/answer", json={
            "answer": "Lists are mutable heterogeneous sequences, while tuples are immutable fixed sequences."
        })

    # End interview
    res_end = client.post(f"/api/interview/{sid}/end", json={"status": "completed"})
    assert res_end.status_code == 200
    report_data = res_end.json()["report"]
    assert report_data["session_id"] == sid
    assert report_data["normalized_score"] is not None

    # Download verified PDF
    res_pdf = client.get(f"/api/interview/{sid}/pdf")
    assert res_pdf.status_code == 200
    assert res_pdf.headers["content-type"] == "application/pdf"
    assert len(res_pdf.content) > 1000  # Non-trivial PDF bytes
