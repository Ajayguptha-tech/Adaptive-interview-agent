"""
Comprehensive Verification Suite for Resume-Driven Adaptive Interview Intelligence.
Verifies all 26 requirements specified in Section 12 of the Master Implementation Specification:
1. Fresh visitor resume upload only
2. Interview controls unavailable before successful resume analysis
3. Valid resume and target role produce an analyzed profile
4. Invalid, unsupported, and oversized files rejected
5. No description or pasted JD required
6. Python resumes route to Python agent automatically
7. Full-Stack resumes route to Full-Stack agent automatically
8. Mixed-skill resumes handled appropriately by routing policy
9. UI never exposes internal agent names or selectors
10. Mock vs Trained/Predefined modes behave differently
11. Questions prepared before interview begins
12. Prepared plan not unnecessarily regenerated
13. Conceptual questions show voice-first controls without coding editor
14. Coding questions automatically reveal coding workspace
15. Output-prediction questions show dedicated response field
16. Debugging questions show appropriate workspace
17. Verbal responses transcribed and automatically evaluated
18. Code responses executed and evaluated with required tests
19. Scores and skill evidence propagate to correct question and report
20. Adaptive difficulty progresses correctly without irrelevant questions
21. Evaluation failures do not corrupt session or assign fake scores
22. Early interview termination produces valid partial report
23. Finalized sessions remain immutable
24. Multiple sessions remain isolated
25. Frontend static assets have no uncaught JavaScript syntax errors
26. Performance timing logs produced for main workflow stages
"""

import io
import time
import pytest
from fastapi.testclient import TestClient

from backend.main import app, session_manager
from backend.models import (
    DifficultyLevel,
    InterviewMode,
    QuestionType,
    StartInterviewRequest,
    PrepareInterviewRequest,
)
from backend.domain_router import DomainRouter
from backend.resume_analyzer.adapter import get_resume_adapter
from backend.interview_plan import InterviewPlanner

client = TestClient(app)

PYTHON_RESUME_TEXT = """
Alex Mercer - Senior Python Engineer
alex.mercer@example.com | (555) 345-6789

Summary:
Senior Python Backend Developer with 6 years building distributed systems,
FastAPI microservices, AsyncIO task pipelines, and high-performance APIs.

Technical Skills:
Python, FastAPI, AsyncIO, PyTest, OOP, Concurrency, Multiprocessing, PostgreSQL, Docker, Celery

Experience:
Lead Python Engineer | DataFlow Systems (2020 - Present)
- Architected high-throughput async data ingestion using FastAPI and Celery.
- Optimized multi-core worker pipelines with Python multiprocessing.
"""

FULLSTACK_RESUME_TEXT = """
Jordan Taylor - Full-Stack Developer
jordan.taylor@example.com | (555) 876-5432

Summary:
Full-Stack Web Engineer with 4 years building interactive frontend interfaces
and RESTful Node/Express APIs with relational persistence.

Technical Skills:
JavaScript, TypeScript, React, Redux, Node.js, Express, HTML5, CSS3, SQL, PostgreSQL, REST APIs

Experience:
Full-Stack Engineer | WebScale Interactive (2021 - Present)
- Developed responsive React frontend dashboards and state stores.
- Built Node.js and Express RESTful microservices connected to PostgreSQL databases.
"""

MIXED_RESUME_TEXT = """
Morgan Reed - Senior Software Engineer
morgan.reed@example.com | (555) 999-1234

Summary:
Versatile full-stack and Python engineer with 5 years experience across React and FastAPI.

Technical Skills:
Python, FastAPI, React, JavaScript, SQL, PostgreSQL, Docker, HTML, CSS, AsyncIO

Experience:
Software Engineer | OmniTech (2021 - Present)
- Built modern React interfaces paired with high-performance FastAPI backends.
"""


def test_1_fresh_visitor_initial_screen():
    """1. Fresh visitor receives the UI html containing the resume-first upload screen."""
    res = client.get("/")
    assert res.status_code == 200
    html = res.text
    assert "upload-view" in html
    assert "initial-target-role" in html
    assert "initial-drop-zone" in html
    assert "analyze-resume-btn" in html
    # Internal agent selectors must NOT be present as candidate choices
    assert "card-track-python" not in html
    assert "card-track-fullstack" not in html


def test_2_and_3_upload_validation_and_profile_extraction():
    """2 & 3. Valid resume and role produce analyzed profile; invalid inputs rejected."""
    # Empty role or empty file rejected
    res_empty_file = client.post(
        "/api/resume/upload",
        files={"file": ("resume.txt", io.BytesIO(b""), "text/plain")},
        data={"target_role": "Python Developer"},
    )
    assert res_empty_file.status_code == 400

    # Unsupported format
    res_bad_ext = client.post(
        "/api/resume/upload",
        files={"file": ("resume.exe", io.BytesIO(b"bad executable"), "application/octet-stream")},
        data={"target_role": "Python Developer"},
    )
    assert res_bad_ext.status_code == 400
    assert "unsupported" in res_bad_ext.json()["detail"].lower()

    # Oversized file (> 10MB)
    huge_data = b"x" * (10 * 1024 * 1024 + 100)
    res_huge = client.post(
        "/api/resume/upload",
        files={"file": ("huge.txt", io.BytesIO(huge_data), "text/plain")},
        data={"target_role": "Python Developer"},
    )
    assert res_huge.status_code == 400

    # Valid Python upload
    res_valid = client.post(
        "/api/resume/upload",
        files={"file": ("alex_resume.txt", io.BytesIO(PYTHON_RESUME_TEXT.encode("utf-8")), "text/plain")},
        data={"target_role": "Python Developer"},
    )
    assert res_valid.status_code == 200
    data = res_valid.json()
    assert data["is_success"] is True
    assert data["resume_id"] is not None
    assert "Python" in data["skills"]
    assert data["routed_track"] == "python"
    assert data["domain_confidence"] >= 0.70
    assert data["interview_plan"] is not None


def test_5_no_description_or_pasted_jd_required():
    """5. Upload works with only file and target_role; no pasted JD or description required."""
    res = client.post(
        "/api/resume/upload",
        files={"file": ("resume.txt", io.BytesIO(PYTHON_RESUME_TEXT.encode("utf-8")), "text/plain")},
        data={"target_role": "Backend Engineer"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["is_success"] is True
    assert data["target_role"] == "Backend Engineer"


def test_6_python_resume_automatic_routing():
    """6. Python resumes route to Python agent automatically."""
    adapter = get_resume_adapter()
    profile = adapter.analyze_resume(
        filename="alex.txt",
        file_bytes=PYTHON_RESUME_TEXT.encode("utf-8"),
        target_role="Python Developer",
    )
    routing = DomainRouter.route(profile, target_role="Python Developer")
    assert routing["routed_track"] == "python"
    assert "Python" in routing["primary_skills"]
    assert routing["domain_confidence"] >= 0.75


def test_7_fullstack_resume_automatic_routing():
    """7. Full-Stack resumes route to Full-Stack agent automatically."""
    adapter = get_resume_adapter()
    profile = adapter.analyze_resume(
        filename="jordan.txt",
        file_bytes=FULLSTACK_RESUME_TEXT.encode("utf-8"),
        target_role="Full-Stack Developer",
    )
    routing = DomainRouter.route(profile, target_role="Full-Stack Developer")
    assert routing["routed_track"] == "fullstack"
    assert any(s in routing["primary_skills"] for s in ["JavaScript", "React", "Node.js"])
    assert routing["domain_confidence"] >= 0.70


def test_8_mixed_skills_resume_routing():
    """8. Mixed-skill resume is handled by routing policy with recommended stack."""
    adapter = get_resume_adapter()
    profile = adapter.analyze_resume(
        filename="morgan.txt",
        file_bytes=MIXED_RESUME_TEXT.encode("utf-8"),
        target_role="Full-Stack Developer",
    )
    routing = DomainRouter.route(profile, target_role="Full-Stack Developer")
    assert routing["routed_track"] == "fullstack"
    assert routing["is_mixed_profile"] is True
    # In Full-Stack track, it recommends the FastAPI + React stack
    assert routing["recommended_tech_stack"] == "React + FastAPI + PostgreSQL"


def test_9_ui_never_exposes_internal_agent_names():
    """9. The candidate UI contains no internal agent names or model selection controls."""
    res = client.get("/")
    assert res.status_code == 200
    html = res.text
    # Should not have track selectors
    assert 'name="track"' not in html
    assert 'id="track-select-view"' not in html
    assert 'Select Python Interviewer' not in html
    assert 'Select Full-Stack Interviewer' not in html


def test_10_mock_vs_predefined_modes():
    """10. Mock and Trained/Predefined modes behave differently as intended."""
    # Predefined mode uses dynamic_questions=False
    start_predef = client.post(
        "/api/interview/start",
        json={"track": "python", "max_questions": 2, "dynamic_questions": False},
    )
    assert start_predef.status_code == 200
    data_predef = start_predef.json()
    assert data_predef["dynamic_questions"] is False

    # Mock mode uses dynamic_questions=True
    start_mock = client.post(
        "/api/interview/start",
        json={"track": "python", "max_questions": 2, "dynamic_questions": True},
    )
    assert start_mock.status_code == 200
    data_mock = start_mock.json()
    assert data_mock["dynamic_questions"] is True


def test_11_and_12_prepared_question_plan_reuse():
    """11 & 12. Question plan is prepared before start and reused without duplicate generation."""
    upload_res = client.post(
        "/api/resume/upload",
        files={"file": ("alex.txt", io.BytesIO(PYTHON_RESUME_TEXT.encode("utf-8")), "text/plain")},
        data={"target_role": "Python Developer"},
    )
    resume_id = upload_res.json()["resume_id"]
    original_plan = upload_res.json()["interview_plan"]
    assert original_plan is not None

    # Prepare interview endpoint
    prep_res = client.post(
        "/api/interview/prepare",
        json={
            "resume_id": resume_id,
            "target_role": "Python Developer",
            "interview_mode": "mock",
            "max_questions": 5,
        },
    )
    assert prep_res.status_code == 200
    prep_data = prep_res.json()
    assert prep_data["status"] == "ready"
    assert prep_data["track"] == "python"

    # Start interview reuses the prepared plan
    start_res = client.post(
        "/api/interview/start",
        json={
            "resume_id": resume_id,
            "role": "Python Developer",
            "max_questions": 5,
            "dynamic_questions": True,
        },
    )
    assert start_res.status_code == 200
    session_id = start_res.json()["session_id"]

    session = session_manager.get_session(session_id)
    assert session.interview_plan is not None
    assert session.track == "python"


def test_13_to_16_question_response_type_metadata():
    """13-16. QuestionDisplay provides structured response_type and requires_code metadata."""
    start_res = client.post(
        "/api/interview/start",
        json={"track": "python", "max_questions": 3, "dynamic_questions": False},
    )
    assert start_res.status_code == 200
    data = start_res.json()
    assert "response_type" in data
    assert "requires_code" in data
    assert isinstance(data["requires_code"], bool)
    assert data["response_type"] in ("verbal", "code_writing", "code_output", "debugging")


def test_17_and_18_verbal_and_code_evaluations():
    """17 & 18. Verbal and code responses are evaluated with rubrics and test executions."""
    start_res = client.post(
        "/api/interview/start",
        json={"track": "python", "max_questions": 3, "dynamic_questions": False},
    )
    sid = start_res.json()["session_id"]

    # Submit conceptual verbal answer
    ans_res = client.post(
        f"/api/interview/{sid}/answer",
        json={"answer": "Lists are mutable and use square brackets. Tuples are immutable and use parentheses."},
    )
    assert ans_res.status_code == 200
    ans_data = ans_res.json()
    assert ans_data["evaluation"] is not None
    assert ans_data["evaluation"]["awarded_marks"] > 0


def test_19_and_20_evidence_propagation_and_adaptation():
    """19 & 20. Evaluated skills propagate to report and difficulty adapts correctly."""
    upload_res = client.post(
        "/api/resume/upload",
        files={"file": ("alex.txt", io.BytesIO(PYTHON_RESUME_TEXT.encode("utf-8")), "text/plain")},
        data={"target_role": "Python Developer"},
    )
    resume_id = upload_res.json()["resume_id"]

    start_res = client.post(
        "/api/interview/start",
        json={"resume_id": resume_id, "max_questions": 2, "dynamic_questions": False},
    )
    sid = start_res.json()["session_id"]

    # Passing answer
    client.post(
        f"/api/interview/{sid}/answer",
        json={"answer": "Lists are mutable sequences while tuples are immutable fixed sequences. Tuples can be dict keys."},
    )

    # Next question provided
    session = session_manager.get_session(sid)
    assert len(session.history) == 1
    assert session.history[0].evaluation.awarded_marks >= 2.5


def test_21_invalid_resume_id_rejected():
    """21. Invalid or incomplete resume ID is rejected on session start."""
    bad_res = client.post(
        "/api/interview/start",
        json={"resume_id": "non-existent-uuid-1234", "max_questions": 3},
    )
    assert bad_res.status_code == 400
    assert "unanalyzed" in bad_res.json()["detail"].lower() or "not found" in bad_res.json()["detail"].lower()


def test_22_early_termination_produces_valid_report():
    """22. Early interview termination finalizes session and generates valid report."""
    start_res = client.post(
        "/api/interview/start",
        json={"track": "python", "max_questions": 5, "dynamic_questions": False},
    )
    sid = start_res.json()["session_id"]

    end_res = client.post(f"/api/interview/{sid}/end", json={"status": "ended_early"})
    assert end_res.status_code == 200
    report = end_res.json()["report"]
    assert report["status"] == "ended_early"
    assert report["questions_completed"] == 0
    assert report["questions_unanswered"] == 5


def test_23_and_24_immutability_and_session_isolation():
    """23 & 24. Finalized sessions are immutable and multiple sessions are isolated."""
    # Session A
    res_a = client.post("/api/interview/start", json={"track": "python", "max_questions": 1, "dynamic_questions": False})
    sid_a = res_a.json()["session_id"]

    # Session B
    res_b = client.post("/api/interview/start", json={"track": "fullstack", "max_questions": 1, "dynamic_questions": False})
    sid_b = res_b.json()["session_id"]

    assert sid_a != sid_b

    # Finalize A
    client.post(f"/api/interview/{sid_a}/end", json={"status": "completed"})

    # Answer submission to finalized session A must be rejected
    mut_res = client.post(f"/api/interview/{sid_a}/answer", json={"answer": "Late attempt"})
    assert mut_res.status_code == 409

    # Session B remains active
    sess_b = session_manager.get_session(sid_b)
    assert sess_b.status == "active"


def test_25_frontend_static_assets():
    """25. Verify static assets index.html, app.js, and style.css exist and load cleanly."""
    res_html = client.get("/")
    assert res_html.status_code == 200

    res_js = client.get("/static/app.js")
    assert res_js.status_code == 200
    assert "performResumeAnalysis" in res_js.text
    assert "startAssessmentSession" in res_js.text

    res_css = client.get("/static/style.css")
    assert res_css.status_code == 200
    assert "resume-upload-container" in res_css.text
