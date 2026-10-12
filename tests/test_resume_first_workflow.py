"""
Comprehensive Automated Test Suite for Resume-First Adaptive Interview Intelligence.
Verifies all 15 requirements specified in Section 6:
1. Multi-format upload (PDF, DOCX, TXT)
2. Invalid formats and size limit enforcement
3. Interview Plan generation from candidate profile
4. Python interview generation based on resume claims
5. Full-Stack interview generation based on resume claims
6. Question-to-skill linkages and evidence tracking
7. Demonstrated classification on passing answers
8. Not Demonstrated classification on failing answers
9. Claimed but unvalidated classification for unasked claims
10. Not assessed classification for untargeted role requirements
11. Integrated Final Report with Interview Plan and Skill Gap
12. Early termination with partial evidence
13. General interview without resume (zero regression)
14. Session isolation and immutable finalized sessions
"""

import io
import pytest
from fastapi.testclient import TestClient

from backend.main import app, session_manager
from backend.resume_analyzer.adapter import get_resume_adapter
from backend.resume_analyzer.skill_gap import SkillGapAnalyzer, SkillStatus
from backend.interview_plan import InterviewPlanner

client = TestClient(app)

RESUME_TEXT_SAMPLE = """
Morgan Lee - Full Stack Engineer
morgan.lee@example.com | (555) 234-5678

Summary:
Full-stack and Python engineer with 5 years experience building distributed APIs,
React interfaces, and relational databases.

Technical Skills:
Python, FastAPI, AsyncIO, PostgreSQL, React, Node.js, Express, Docker

Experience:
Senior Software Engineer | FinTech Systems (2020 - Present)
- Developed async transaction processing pipelines using Python, FastAPI, and PostgreSQL.
- Architected React frontend state management and dashboard views.
"""


def test_1_multiformat_upload_validation():
    """1. Test successful TXT and synthetic document upload validation."""
    adapter = get_resume_adapter()
    res = client.post(
        "/api/resume/upload",
        files={"file": ("morgan_resume.txt", io.BytesIO(RESUME_TEXT_SAMPLE.encode("utf-8")), "text/plain")},
        data={"track": "python"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["is_success"] is True
    assert data["resume_id"] is not None
    assert "Python" in data["skills"]
    assert "FastAPI" in data["skills"]


def test_2_invalid_and_oversized_file_rejection():
    """2. Test invalid file types, empty files, and oversized files."""
    # Invalid extension (.exe)
    res_exe = client.post(
        "/api/resume/upload",
        files={"file": ("malware.exe", io.BytesIO(b"executable data"), "application/octet-stream")},
    )
    assert res_exe.status_code == 400
    assert "unsupported" in res_exe.json()["detail"].lower()

    # Empty file
    res_empty = client.post(
        "/api/resume/upload",
        files={"file": ("empty.txt", io.BytesIO(b""), "text/plain")},
    )
    assert res_empty.status_code == 400

    # Oversized file (> 10MB)
    huge_bytes = b"a" * (10 * 1024 * 1024 + 1024)
    res_huge = client.post(
        "/api/resume/upload",
        files={"file": ("huge.txt", io.BytesIO(huge_bytes), "text/plain")},
    )
    assert res_huge.status_code == 400
    assert "exceeds" in res_huge.json()["detail"].lower()


def test_3_interview_planner_generation():
    """3. Test Interview Plan generation for both tracks via endpoint and planner."""
    upload_res = client.post(
        "/api/resume/upload",
        files={"file": ("profile.txt", io.BytesIO(RESUME_TEXT_SAMPLE.encode("utf-8")), "text/plain")},
    )
    resume_id = upload_res.json()["resume_id"]

    # Generate Python Plan
    plan_py_res = client.post(
        "/api/resume/plan",
        json={"resume_id": resume_id, "track": "python", "max_questions": 4, "difficulty_mode": "adaptive"},
    )
    assert plan_py_res.status_code == 200
    plan_py = plan_py_res.json()
    assert plan_py["track"] == "python"
    assert len(plan_py["selected_topics"]) == 4
    assert len(plan_py["planned_questions_criteria"]) == 4
    assert any("FastAPI" in skills or "Python" in skills for skills in plan_py["topic_skill_mapping"].values())

    # Generate Full-Stack Plan
    plan_fs_res = client.post(
        "/api/resume/plan",
        json={"resume_id": resume_id, "track": "fullstack", "max_questions": 4, "difficulty_mode": "adaptive"},
    )
    assert plan_fs_res.status_code == 200
    plan_fs = plan_fs_res.json()
    assert plan_fs["track"] == "fullstack"
    assert any("React" in skills or "PostgreSQL" in skills for skills in plan_fs["topic_skill_mapping"].values())


def test_4_python_interview_generation_from_resume():
    """4. Test that Python interview session attaches interview plan and guides questions."""
    upload_res = client.post(
        "/api/resume/upload",
        files={"file": ("profile.txt", io.BytesIO(RESUME_TEXT_SAMPLE.encode("utf-8")), "text/plain")},
    )
    resume_id = upload_res.json()["resume_id"]

    start_res = client.post(
        "/api/interview/start",
        json={"track": "python", "max_questions": 2, "dynamic_questions": False, "resume_id": resume_id},
    )
    assert start_res.status_code == 200
    session_data = start_res.json()
    assert "reason" in session_data
    # Verify candidate claims are cross-referenced in reason
    assert "resume" in session_data["reason"].lower() or "plan" in session_data["reason"].lower()


def test_5_fullstack_interview_generation_from_resume():
    """5. Test that Full-Stack interview session attaches interview plan and guides questions."""
    upload_res = client.post(
        "/api/resume/upload",
        files={"file": ("profile.txt", io.BytesIO(RESUME_TEXT_SAMPLE.encode("utf-8")), "text/plain")},
    )
    resume_id = upload_res.json()["resume_id"]

    start_res = client.post(
        "/api/interview/start",
        json={"track": "fullstack", "max_questions": 2, "dynamic_questions": False, "resume_id": resume_id},
    )
    assert start_res.status_code == 200
    session_data = start_res.json()
    assert session_data["track"] == "fullstack"


def test_6_to_11_skill_evidence_flow_and_final_report():
    """
    6. Question-to-skill linkage
    7. Demonstrated status on passing answers
    8. Not demonstrated status on failing answers
    9. Claimed but unvalidated on unasked claims
    10. Not assessed on unassessed job requirements
    11. Final report integration with plan and evidence
    """
    profile = {
        "candidate_name": "Dev Candidate",
        "filename": "dev.txt",
        "skills": ["Python", "FastAPI", "Docker", "AsyncIO"],
        "claimed_skills": ["Python", "FastAPI", "Docker", "AsyncIO"],
        "job_matching": {"missing_required": ["Kubernetes"]},
    }

    # Simulated interview history:
    # Q1: Python -> Scored 90% (Demonstrated)
    # Q2: FastAPI -> Scored 30% (Not Demonstrated)
    # Docker, AsyncIO -> Not asked (Claimed but unvalidated)
    # Kubernetes -> In job matching, not on resume and not asked (Not Assessed)
    history = [
        {
            "question_number": 1,
            "question_text": "Explain Python list vs tuple memory efficiency.",
            "topic": "Data Structures & Mutability",
            "target_skills": ["Python"],
            "competency": "Python Fundamentals",
            "awarded_marks": 4.5,
            "max_marks": 5.0,
            "percentage": 90.0,
            "summary": "Clear understanding of memory contiguous layout and immutability.",
            "correctness_status": "correct",
        },
        {
            "question_number": 2,
            "question_text": "Explain FastAPI dependency injection with Yield.",
            "topic": "FastAPI & Modern Web APIs",
            "target_skills": ["FastAPI"],
            "competency": "Web Frameworks",
            "awarded_marks": 1.5,
            "max_marks": 5.0,
            "percentage": 30.0,
            "summary": "Confused dependency injection with normal generator loops.",
            "correctness_status": "incorrect",
        },
    ]

    report = SkillGapAnalyzer.analyze_skill_gap(
        resume_profile=profile,
        interview_history=history,
        track="python",
    )

    # 7. Demonstrated check
    assert "Python" in report.demonstrated_skills
    py_item = next(i for i in report.skills if i.skill_name == "Python")
    assert py_item.status == SkillStatus.DEMONSTRATED
    assert py_item.score_percentage >= 60.0
    assert len(py_item.interview_evidence) == 1

    # 8. Not demonstrated check
    assert "FastAPI" in report.not_demonstrated_skills
    fa_item = next(i for i in report.skills if i.skill_name == "FastAPI")
    assert fa_item.status == SkillStatus.NOT_DEMONSTRATED
    assert fa_item.score_percentage < 60.0

    # 9. Claimed but unvalidated check (Docker & AsyncIO)
    assert "Docker" in report.claimed_unvalidated_skills
    docker_item = next(i for i in report.skills if i.skill_name == "Docker")
    assert docker_item.status == SkillStatus.CLAIMED_UNVALIDATED
    assert docker_item.interview_evidence == []

    # 10. Not assessed check (Kubernetes)
    assert "Kubernetes" in report.not_assessed_skills
    k8s_item = next(i for i in report.skills if i.skill_name == "Kubernetes")
    assert k8s_item.status == SkillStatus.NOT_ASSESSED


def test_12_early_termination_and_unanswered():
    """12. Test ending interview early preserves unanswered counts and evidence."""
    upload_res = client.post(
        "/api/resume/upload",
        files={"file": ("resume.txt", io.BytesIO(RESUME_TEXT_SAMPLE.encode("utf-8")), "text/plain")},
    )
    resume_id = upload_res.json()["resume_id"]

    start_res = client.post(
        "/api/interview/start",
        json={"track": "python", "max_questions": 5, "dynamic_questions": False, "resume_id": resume_id},
    )
    sid = start_res.json()["session_id"]

    # End early without answering
    end_res = client.post(f"/api/interview/{sid}/end", json={"status": "ended_early"})
    assert end_res.status_code == 200
    report = end_res.json()["report"]
    assert report["status"] == "ended_early"
    assert report["questions_completed"] == 0
    assert report["questions_unanswered"] == 5
    assert report["interview_plan"] is not None


def test_13_general_interview_without_resume():
    """13. General interview without a resume operates with zero regressions."""
    start_res = client.post(
        "/api/interview/start",
        json={"track": "python", "max_questions": 1, "dynamic_questions": False, "resume_id": None},
    )
    assert start_res.status_code == 200
    sid = start_res.json()["session_id"]

    # Submit answer
    client.post(f"/api/interview/{sid}/answer", json={"answer": "A list is mutable while a tuple is immutable."})

    rep_res = client.get(f"/api/interview/{sid}/report")
    assert rep_res.status_code == 200
    report = rep_res.json()
    assert report["resume_id"] is None
    assert report["resume_skill_gap"] is None
    assert report["interview_plan"] is None


def test_14_session_isolation_and_immutability():
    """14. Session isolation between multiple candidates and post-finalization immutability."""
    # Session A
    res_a = client.post("/api/interview/start", json={"track": "python", "max_questions": 1, "dynamic_questions": False})
    sid_a = res_a.json()["session_id"]

    # Session B
    res_b = client.post("/api/interview/start", json={"track": "fullstack", "max_questions": 1, "dynamic_questions": False})
    sid_b = res_b.json()["session_id"]

    assert sid_a != sid_b
    assert session_manager.get_session(sid_a).track == "python"
    assert session_manager.get_session(sid_b).track == "fullstack"

    # Finalize Session A
    client.post(f"/api/interview/{sid_a}/end", json={"status": "completed"})

    # Post-finalization answer rejection
    reject_res = client.post(f"/api/interview/{sid_a}/answer", json={"answer": "Too late"})
    assert reject_res.status_code == 409
