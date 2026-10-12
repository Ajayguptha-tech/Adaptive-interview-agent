"""
Test suite for ResumeAnalyzerAgent integration and Resume-to-Interview Skill-Gap Intelligence.
Covers all 10 verification scenarios required by Section 9:
1. Successful resume parsing using a synthetic test resume.
2. Skill extraction and structured output.
3. Job-description matching and ATS scoring.
4. Unsupported file formats and malformed documents.
5. Resume analysis without starting an interview.
6. Python interview integration with resume-informed questions.
7. Full-Stack interview integration with resume-informed questions.
8. Correct classification of claimed, demonstrated, unvalidated, and unassessed skills.
9. Evidence references in the final report.
10. Interview operation when resume analysis is skipped or unavailable.
"""

import io
import pytest
from fastapi.testclient import TestClient

from backend.main import app, session_manager
from backend.resume_analyzer.adapter import get_resume_adapter
from backend.resume_analyzer.skill_gap import SkillGapAnalyzer, SkillStatus
from backend.models import StartInterviewRequest, InterviewMode

client = TestClient(app)

SYNTHETIC_PYTHON_RESUME = """
Jordan Smith
Seattle, WA | jordan.smith@example.com | (206) 555-0199 | linkedin.com/in/jordansmith

SUMMARY
Experienced Full-Stack and Python Engineer with 4 years of experience architecting cloud services with Python, FastAPI, and PostgreSQL.

SKILLS
Python, FastAPI, Docker, PostgreSQL, Redis, AsyncIO, Git

EXPERIENCE
Senior Software Engineer - CloudTech Labs | 2021 - 2024
- Spearheaded development of 10+ microservices in Python and FastAPI.
- Architected PostgreSQL data pipelines and improved cache efficiency by 30% using Redis.
- Implemented high-concurrency event-driven processing using Python AsyncIO.

EDUCATION
B.S. in Computer Science - University of Washington | 2020
"""

SYNTHETIC_FULLSTACK_RESUME = """
Taylor Reed
San Francisco, CA | taylor.reed@example.com | (415) 555-0144

SUMMARY
Full-Stack Web Developer with 3 years of experience building modern web applications using React, Node.js, Express, and SQL.

SKILLS
JavaScript, TypeScript, React, Node.js, Express, SQL, HTML, CSS

EXPERIENCE
Full-Stack Developer - Nova Apps | 2021 - 2024
- Built responsive UI components with React and TypeScript.
- Designed RESTful API endpoints using Node.js and Express with SQL database integration.

EDUCATION
B.S. in Software Engineering - San Jose State University | 2021
"""


# =============================================================================
# 1 & 2: Resume Parsing & Skill Extraction
# =============================================================================

def test_resume_parsing_and_skill_extraction():
    """Verify that synthetic resume is parsed with structured contact info and extracted skills."""
    adapter = get_resume_adapter()
    result = adapter.analyze_resume(
        filename="jordan_resume.txt",
        file_bytes=SYNTHETIC_PYTHON_RESUME.encode("utf-8"),
    )

    assert result["is_success"] is True
    assert result["resume_id"] is not None
    assert result["candidate_name"] == "Jordan Smith"
    assert result["contact_info"]["email"] == "jordan.smith@example.com"
    assert "Python" in result["skills"]
    assert "FastAPI" in result["skills"]
    assert result["integrity_audit"]["integrity_status"] in ("passed", "advisory", "attention_needed")
    assert len(result["experience"]) >= 1


# =============================================================================
# 3: Job Description Matching and ATS Scoring
# =============================================================================

def test_job_description_matching_and_ats_scoring():
    """Verify ATS score calculation and exact/missing skills extraction against target JD."""
    adapter = get_resume_adapter()
    result = adapter.analyze_resume(
        filename="jordan_resume.txt",
        file_bytes=SYNTHETIC_PYTHON_RESUME.encode("utf-8"),
        job_title="Senior Python Backend Engineer",
        job_description="We need a Senior Python Engineer with experience in Python, FastAPI, Docker, and Kubernetes.",
        required_skills=["Python", "FastAPI", "Docker", "Kubernetes"],
        preferred_skills=["AWS", "Redis"],
    )

    assert result["is_success"] is True
    assert result["job_matching"] is not None
    assert result["ats_score"] is not None
    assert result["ats_score"] > 50.0  # High match on Python, FastAPI, Docker
    assert "Python" in result["matched_skills"]
    assert "FastAPI" in result["matched_skills"]
    assert "Kubernetes" in result["missing_skills"]


# =============================================================================
# 4: Unsupported File Formats and Malformed Documents
# =============================================================================

def test_unsupported_file_format_rejection():
    """Verify that unsupported extensions (e.g. .exe, .doc) are rejected cleanly."""
    adapter = get_resume_adapter()
    result = adapter.analyze_resume(
        filename="malicious_payload.exe",
        file_bytes=b"MZ\x90\x00\x03\x00\x00\x00",
    )
    assert result["is_success"] is False
    assert "Unsupported file format" in result["error_message"]

    # Test empty document
    res_empty = adapter.analyze_resume(
        filename="empty.txt",
        file_bytes=b"   ",
    )
    assert res_empty["is_success"] is False


# =============================================================================
# 5: Resume Analysis Without Starting an Interview
# =============================================================================

def test_standalone_resume_upload_endpoint():
    """Verify POST /api/resume/upload and GET /api/resume/{id} operate independently."""
    file_content = SYNTHETIC_PYTHON_RESUME.encode("utf-8")
    response = client.post(
        "/api/resume/upload",
        files={"file": ("candidate_cv.txt", io.BytesIO(file_content), "text/plain")},
        data={"job_title": "Python Developer", "required_skills": "Python,FastAPI,Docker"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["is_success"] is True
    resume_id = data["resume_id"]
    assert resume_id is not None
    assert "Python" in data["skills"]

    # Retrieve via GET endpoint
    get_res = client.get(f"/api/resume/{resume_id}")
    assert get_res.status_code == 200
    retrieved = get_res.json()
    assert retrieved["resume_id"] == resume_id
    assert retrieved["candidate_name"] == "Jordan Smith"


# =============================================================================
# 6: Python Interview Integration with Resume-Informed Questions
# =============================================================================

def test_python_interview_with_resume_id():
    """Verify that starting a Python interview with resume_id links resume to session."""
    # 1. Upload resume
    upload_res = client.post(
        "/api/resume/upload",
        files={"file": ("jordan.txt", io.BytesIO(SYNTHETIC_PYTHON_RESUME.encode("utf-8")), "text/plain")},
    )
    assert upload_res.status_code == 200
    resume_id = upload_res.json()["resume_id"]

    # 2. Start Python interview attached to resume
    start_res = client.post(
        "/api/interview/start",
        json={
            "track": "python",
            "max_questions": 2,
            "dynamic_questions": False,
            "resume_id": resume_id,
        },
    )
    assert start_res.status_code == 200
    session_data = start_res.json()
    session_id = session_data["session_id"]
    assert "resume" in session_data["selection_reason"].lower() or "cross-referencing" in session_data["selection_reason"].lower()

    # 3. Answer Question 1
    ans_res = client.post(
        f"/api/interview/{session_id}/answer",
        json={"answer": "Lists are mutable and stored contiguously while tuples are immutable."},
    )
    assert ans_res.status_code == 200

    # 4. Check intermediate skill gap
    gap_res = client.get(f"/api/interview/{session_id}/skill_gap")
    assert gap_res.status_code == 200
    gap_data = gap_res.json()
    assert gap_data["has_resume"] is True
    assert gap_data["resume_id"] == resume_id


# =============================================================================
# 7: Full-Stack Interview Integration with Resume-Informed Questions
# =============================================================================

def test_fullstack_interview_with_resume_id():
    """Verify that starting a Full-Stack interview links Full-Stack resume profile."""
    # 1. Upload fullstack resume
    upload_res = client.post(
        "/api/resume/upload",
        files={"file": ("taylor.txt", io.BytesIO(SYNTHETIC_FULLSTACK_RESUME.encode("utf-8")), "text/plain")},
    )
    assert upload_res.status_code == 200
    resume_id = upload_res.json()["resume_id"]

    # 2. Start Full-Stack interview
    start_res = client.post(
        "/api/interview/start",
        json={
            "track": "fullstack",
            "tech_stack": "React + Node.js + Express + SQL",
            "max_questions": 2,
            "dynamic_questions": False,
            "resume_id": resume_id,
        },
    )
    assert start_res.status_code == 200
    session_id = start_res.json()["session_id"]
    assert start_res.json()["track"] == "fullstack"


# =============================================================================
# 8 & 9: Skill Gap Classification & Evidence References in Final Report
# =============================================================================

def test_skill_gap_classification_and_evidence():
    """
    Verify precise classification:
    - Demonstrated (Passed interview question)
    - Claimed but Unvalidated (On resume, but not asked)
    - Not Demonstrated (Assessed but failed/unsatisfactory)
    - Not Assessed (In target JD, but not on resume and not asked)
    """
    resume_profile = {
        "candidate_name": "Alex Candidate",
        "filename": "alex_cv.pdf",
        "skills": ["Python", "FastAPI", "Docker", "PostgreSQL"],
        "skill_evidence": [
            {"skill": "Python", "source": "experience", "evidence_snippet": "Built APIs in Python", "confidence": 1.0},
            {"skill": "Docker", "source": "skills_list", "evidence_snippet": "Listed under skills", "confidence": 1.0},
        ],
        "job_matching": {
            "missing_required": ["Kubernetes"],  # In JD, but candidate lacks it
        },
    }

    interview_history = [
        {
            "question_number": 1,
            "topic": "Python Core",
            "question_text": "Explain Python GIL and memory management",
            "competency": "Python fundamentals",
            "awarded_marks": 4.5,
            "max_marks": 5.0,
            "percentage": 90.0,
            "summary": "Demonstrated comprehensive understanding of Python internals.",
            "correctness_status": "correct",
        },
        {
            "question_number": 2,
            "topic": "SQL & Databases",
            "question_text": "Write a query to aggregate users",
            "competency": "Database design",
            "awarded_marks": 1.0,
            "max_marks": 5.0,
            "percentage": 20.0,
            "summary": "Failed required SQL syntax and aggregate logic.",
            "correctness_status": "incorrect",
        },
    ]

    report = SkillGapAnalyzer.analyze_skill_gap(
        resume_profile=resume_profile,
        interview_history=interview_history,
        track="python",
    )

    # 1. Python was assessed with 90% -> Demonstrated
    assert "Python" in report.demonstrated_skills
    py_item = next(i for i in report.skills if i.skill_name == "Python")
    assert py_item.status == SkillStatus.DEMONSTRATED
    assert len(py_item.interview_evidence) == 1
    assert py_item.interview_evidence[0]["awarded_marks"] == 4.5

    # 2. Docker was claimed on resume but never asked -> Claimed Unvalidated
    assert "Docker" in report.claimed_unvalidated_skills
    docker_item = next(i for i in report.skills if i.skill_name == "Docker")
    assert docker_item.status == SkillStatus.CLAIMED_UNVALIDATED
    assert len(docker_item.resume_claims) >= 1

    # 3. SQL / PostgreSQL was assessed with 20% -> Not Demonstrated
    assert any(s in report.not_demonstrated_skills for s in ("PostgreSQL", "SQL"))

    # 4. Kubernetes was required by JD, not on resume and not asked -> Not Assessed
    assert "Kubernetes" in report.not_assessed_skills
    k8s_item = next(i for i in report.skills if i.skill_name == "Kubernetes")
    assert k8s_item.status == SkillStatus.NOT_ASSESSED


def test_final_report_contains_skill_gap():
    """Verify that end-to-end session finalization embeds resume_skill_gap in FinalReport."""
    # 1. Upload resume
    upload_res = client.post(
        "/api/resume/upload",
        files={"file": ("jordan.txt", io.BytesIO(SYNTHETIC_PYTHON_RESUME.encode("utf-8")), "text/plain")},
    )
    resume_id = upload_res.json()["resume_id"]

    # 2. Start session
    start_res = client.post(
        "/api/interview/start",
        json={"track": "python", "max_questions": 2, "dynamic_questions": False, "resume_id": resume_id},
    )
    session_id = start_res.json()["session_id"]

    # 3. Answer 1 question
    client.post(
        f"/api/interview/{session_id}/answer",
        json={"answer": "Lists are mutable and tuples are immutable."},
    )

    # 4. End interview
    end_res = client.post(f"/api/interview/{session_id}/end", json={"status": "completed"})
    assert end_res.status_code == 200
    report = end_res.json()["report"]

    assert report["resume_id"] == resume_id
    assert report["resume_summary"] is not None
    assert report["resume_summary"]["candidate_name"] == "Jordan Smith"
    assert report["resume_skill_gap"] is not None
    assert "demonstrated_skills" in report["resume_skill_gap"]
    assert "claimed_unvalidated_skills" in report["resume_skill_gap"]


# =============================================================================
# 10: Operation When Resume Analysis is Skipped
# =============================================================================

def test_interview_operates_without_resume():
    """Verify that starting an interview without resume_id works identically to baseline."""
    start_res = client.post(
        "/api/interview/start",
        json={"track": "python", "max_questions": 1, "dynamic_questions": False},
    )
    assert start_res.status_code == 200
    session_id = start_res.json()["session_id"]

    client.post(
        f"/api/interview/{session_id}/answer",
        json={"answer": "A list is mutable while a tuple is immutable."},
    )

    end_res = client.post(f"/api/interview/{session_id}/end", json={"status": "completed"})
    assert end_res.status_code == 200
    report = end_res.json()["report"]

    assert report["resume_id"] is None
    assert report["resume_summary"] is None
    assert report["resume_skill_gap"] is None
    assert report["normalized_score"] > 0.0
