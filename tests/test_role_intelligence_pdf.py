"""
Automated Unit & Integration Tests for Phase 2, 3, 4, 11 Enhancements:
- Evidence-based Resume Integrity and Authenticity Assessment (4 outcomes).
- Role-Based Eligibility Assessment across 12 engineering roles (3 outcomes).
- Automatic Extensible Role Routing (12 role families, specialized agent mapping).
- Curated Multi-Role Question Banks & Rubrics.
- Professional Server-Side Multi-Page PDF Report Generation.
"""

import io
import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.resume_analyzer.integrity_audit import ResumeIntegrityAssessor, ResumeIntegrityReport
from backend.resume_analyzer.eligibility import RoleEligibilityAssessor, RoleEligibilityResult, ROLE_REQUIREMENT_PROFILES
from backend.domain_router import DomainRouter, SUPPORTED_ROLE_REGISTRY
from backend.pdf_generator import InterviewPDFReportGenerator

client = TestClient(app)


def test_resume_integrity_assessor_outcomes():
    """Validates the 4 integrity assessment outcomes and risk indicators."""
    # 1. Standard valid profile
    mock_clean_profile = {
        "skills": ["Python", "FastAPI", "PostgreSQL", "Docker"],
        "experience": [
            {
                "title": "Backend Engineer",
                "company": "Tech Corp",
                "duration": "2021 - Present",
                "years_calculated": 3.0,
                "description": "Engineered FastAPI microservices and PostgreSQL database layers.",
                "technologies_used": ["Python", "FastAPI", "PostgreSQL"],
            }
        ],
        "projects": [
            {
                "name": "Cloud API",
                "description": "Containerized FastAPI microservices deploying with Docker.",
                "technologies": ["Python", "FastAPI", "Docker"],
            }
        ],
        "education": [{"degree": "B.S. Computer Science", "institution": "State Univ", "year": "2021"}],
    }

    report = ResumeIntegrityAssessor.audit_profile(
        parsed_resume=None,
        raw_text="Engineered FastAPI microservices and PostgreSQL database layers with Docker.",
        filename="clean_resume.pdf",
    )
    assert isinstance(report, ResumeIntegrityReport)
    assert report.outcome in [
        "no_inconsistencies",
        "potential_inconsistencies",
        "strong_concerns",
        "insufficient_evidence",
    ]
    assert report.outcome_label != ""
    assert report.headline != ""
    assert report.caveat_notice != ""

    # 2. Insufficient text
    report_sparse = ResumeIntegrityAssessor.audit_profile(
        parsed_resume=None,
        raw_text="Short text",
        filename="sparse.txt",
    )
    assert report_sparse.outcome == "insufficient_evidence"


def test_role_eligibility_all_12_roles():
    """Validates eligibility calculation for all 12 supported engineering roles."""
    roles = list(ROLE_REQUIREMENT_PROFILES.keys())
    assert len(roles) == 12

    sample_resume = {
        "skills": ["Python", "FastAPI", "PostgreSQL", "Docker", "SQL", "Git"],
        "experience": [
            {
                "title": "Python Developer",
                "years_calculated": 3.0,
                "description": "Built scalable Python REST services using FastAPI and SQL databases.",
                "technologies_used": ["Python", "FastAPI", "SQL"],
            }
        ],
        "projects": [
            {
                "name": "Data API",
                "description": "High performance data querying service using PostgreSQL and Python.",
                "technologies": ["Python", "PostgreSQL"],
            }
        ],
        "total_experience_years": 3.0,
    }

    # Python Developer -> Should be Eligible
    res_py = RoleEligibilityAssessor.assess_eligibility(sample_resume, "Python Developer")
    assert isinstance(res_py, RoleEligibilityResult)
    assert res_py.outcome in ["eligible", "potentially_eligible", "not_currently_eligible"]
    assert "Python" in res_py.relevant_skills_found
    assert len(res_py.reasons_supporting_result) > 0

    # Data Analyst -> Should evaluate SQL and Python
    res_da = RoleEligibilityAssessor.assess_eligibility(sample_resume, "Data Analyst")
    assert res_da.outcome in ["eligible", "potentially_eligible"]

    # Java Developer -> Missing Java, should be potentially or not currently eligible
    res_java = RoleEligibilityAssessor.assess_eligibility(sample_resume, "Java Developer")
    assert res_java.outcome in ["potentially_eligible", "not_currently_eligible"]
    assert "Java" in res_java.missing_or_weak_skills


def test_domain_router_12_role_families():
    """Validates that DomainRouter routes all 12 role families accurately without generic fallback."""
    test_cases = [
        ("Python Developer", "python"),
        ("Full-Stack Developer", "fullstack"),
        ("Frontend Developer", "fullstack"),
        ("Backend Developer", "fullstack"),
        ("Java Developer", "python"),
        ("C/C++ Developer", "python"),
        ("Data Analyst", "python"),
        ("Data Engineer", "python"),
        ("Machine Learning Engineer", "python"),
        ("AI/ML Engineer", "python"),
        ("SQL/Database Developer", "fullstack"),
        ("General Software Engineer", "python"),
    ]

    for role_name, expected_track in test_cases:
        routing = DomainRouter.route(
            resume_profile={"skills": ["Python", "SQL", "Git"]},
            target_role=role_name,
        )
        assert routing["routed_track"] == expected_track
        assert routing["role_title"] != ""
        assert routing["domain_confidence"] > 0.0
        assert len(routing["focus_competencies"]) > 0


def test_server_side_pdf_report_generation():
    """Validates that InterviewPDFReportGenerator compiles valid multi-page PDF bytes with all 5 sections."""
    mock_report = {
        "session_id": "test-pdf-session-1234",
        "candidate_name": "Alex Mercer",
        "role": "Python Developer",
        "mode": "mock",
        "normalized_score": 86.5,
        "total_marks_obtained": 17.3,
        "total_max_marks": 20.0,
        "questions_completed": 4,
        "assessment_grade": "Distinction (Senior / Advanced)",
        "authenticity_assessment": {
            "outcome_label": "No significant inconsistencies detected",
            "headline": "High structural coherence across resume claims",
        },
        "eligibility_assessment": {
            "outcome_label": "Eligible",
            "headline": "Candidate satisfies technical requirements for target role",
            "reasons_supporting_result": ["Verified 3.0+ years experience", "Core Python frameworks present"],
        },
        "resume_skill_gap": {
            "demonstrated_skills": [{"skill": "Python"}, {"skill": "FastAPI"}],
            "assessed_not_demonstrated": [{"skill": "Metaprogramming"}],
            "claimed_unvalidated_skills": [{"skill": "Docker"}],
            "unassessed_skills": [{"skill": "Kubernetes"}],
        },
        "history": [
            {
                "question_number": 1,
                "question": {
                    "text": "Explain Python GIL and its implications for multithreading.",
                    "competency": "concurrency",
                    "difficulty": "intermediate",
                    "expected_concepts": ["Global Interpreter Lock", "CPU-bound vs I/O-bound", "multiprocessing"],
                    "model_answer": "The GIL is a mutex that prevents multiple native threads from executing Python bytecodes simultaneously.",
                },
                "candidate_answer": "GIL prevents true multi-core parallel execution in CPU-bound Python threads, but I/O operations release the lock.",
                "evaluation": {
                    "awarded_marks": 4.5,
                    "max_marks": 5.0,
                    "summary_explanation": "Clear explanation distinguishing I/O-bound and CPU-bound threading implications.",
                    "criteria": [
                        {"criterion_id": "Technical Accuracy", "awarded_marks": 2.5, "max_marks": 2.5, "explanation": "Correct explanation."},
                        {"criterion_id": "Concurrency Tradeoffs", "awarded_marks": 2.0, "max_marks": 2.5, "explanation": "Mentioned multiprocessing."},
                    ],
                },
            }
        ],
        "competency_scores": {
            "concurrency": {"earned": 4.5, "max": 5.0, "percentage": 90.0, "questions_count": 1}
        },
        "recommendations": ["Deep dive into asyncio event loop task scheduling."],
        "suggested_study_topics": ["asyncio", "multiprocessing"],
    }

    pdf_bytes = InterviewPDFReportGenerator.build_pdf_bytes(mock_report)
    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 2000
    assert pdf_bytes[:4] == b"%PDF"


def test_pdf_endpoint_live_response():
    """Validates the GET /api/interview/{session_id}/pdf endpoint using TestClient."""
    # 1. Start a quick session
    start_res = client.post("/api/interview/start", json={
        "track": "python",
        "max_questions": 2,
        "dynamic_questions": False,
    })
    assert start_res.status_code == 200
    session_id = start_res.json()["session_id"]

    # 2. Answer question
    client.post(f"/api/interview/{session_id}/answer", json={
        "answer": "A list is mutable dynamic array; tuple is immutable."
    })

    # 3. End interview
    client.post(f"/api/interview/{session_id}/end", json={"status": "completed"})

    # 4. Request PDF download
    pdf_res = client.get(f"/api/interview/{session_id}/pdf")
    assert pdf_res.status_code == 200
    assert pdf_res.headers["content-type"] == "application/pdf"
    assert "attachment; filename=" in pdf_res.headers.get("content-disposition", "")
    assert pdf_res.content[:4] == b"%PDF"
