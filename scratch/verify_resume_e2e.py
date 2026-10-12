"""
End-to-end verification script for ResumeAnalyzerAgent integration.
Tests live endpoints, Python and Full-Stack tracks with and without resumes,
and verifies evidence-based skill gap analysis.
"""
import io
import json
import sys
import os
sys.path.insert(0, os.path.abspath("."))
from fastapi.testclient import TestClient
from backend.main import app

def run_e2e_verification():
    client = TestClient(app)
    results = {}

    print("=" * 60)
    print("STEP 1: Verify Resume Upload and Parsing through FastAPI Endpoint")
    print("=" * 60)
    sample_resume = """
    Alex Mercer - Senior Software Engineer
    alex.mercer@example.com | San Francisco, CA

    Professional Summary:
    Full-stack and Python engineer with 6 years of experience building scalable systems,
    REST APIs, React applications, and PostgreSQL databases.

    Technical Skills:
    - Programming Languages: Python, JavaScript, TypeScript, SQL
    - Frameworks & Libraries: FastAPI, Django, React, Express, Node.js
    - Databases: PostgreSQL, Redis, SQLite
    - Tools & Platforms: Docker, Git, Linux, AWS

    Experience:
    Senior Software Engineer | TechCorp Inc. (2021 - Present)
    - Architected Python backend services using FastAPI and PostgreSQL handling 5M daily requests.
    - Built responsive frontend modules using React and TypeScript.
    - Implemented asynchronous background tasks with Redis and Celery.
    """

    resume_file = io.BytesIO(sample_resume.encode("utf-8"))
    upload_res = client.post(
        "/api/resume/upload",
        files={"file": ("alex_mercer_resume.txt", resume_file, "text/plain")},
        data={
            "job_title": "Senior Python & Full-Stack Engineer",
            "company": "Apex Systems",
            "job_description": "We are looking for a Python and Full-Stack engineer with experience in FastAPI, React, SQL, and system design.",
            "track": "python"
        }
    )
    assert upload_res.status_code == 200, f"Upload failed: {upload_res.text}"
    upload_data = upload_res.json()
    resume_id = upload_data["resume_id"]
    profile = upload_data["profile"]

    print(f"  [OK] Upload Successful. Resume ID: {resume_id}")
    print(f"  [OK] Extracted Candidate Name: {profile.get('candidate_name')}")
    print(f"  [OK] Integrity Status: {profile.get('integrity_status')}")
    print(f"  [OK] ATS Compatibility Score: {profile.get('ats_score')}%")
    print(f"  [OK] Extracted Skills ({len(profile.get('claimed_skills', []))}): {profile.get('claimed_skills')[:6]}...")
    assert len(profile.get("claimed_skills", [])) >= 3
    results["resume_upload"] = "PASSED"

    print("\n" + "=" * 60)
    print("STEP 2: Python Track Interview with Resume Integration")
    print("=" * 60)
    py_start_res = client.post("/api/interview/start", json={
        "role": "Python Developer",
        "track": "python",
        "resume_id": resume_id,
        "max_questions": 2,
        "difficulty_mode": "intermediate",
        "dynamic_questions": False,
    })
    assert py_start_res.status_code == 200
    py_session = py_start_res.json()
    py_sid = py_session["session_id"]
    print(f"  [OK] Python Session Created: {py_sid}")
    print(f"  [OK] Q1: {py_session['topic']} - {py_session['text'][:70]}...")
    print(f"  [OK] Selection Reason (Informed by Resume): {py_session.get('reason')}")

    # Answer Q1 (Demonstrated competence)
    py_ans1_res = client.post(f"/api/interview/{py_sid}/answer", json={
        "answer": "Python uses reference counting and a generational cyclic garbage collector. Variables are references to objects."
    })
    assert py_ans1_res.status_code == 200
    py_q2 = py_ans1_res.json()
    print(f"  [OK] Q1 Answer Evaluated. Awarded: {py_q2.get('feedback', {}).get('earned_marks')} marks.")

    # Answer Q2 (Show gap / flawed answer)
    py_ans2_res = client.post(f"/api/interview/{py_sid}/answer", json={
        "answer": "I do not know how this works in Python."
    })
    assert py_ans2_res.status_code == 200

    # Get final report with skill gap
    py_rep_res = client.get(f"/api/interview/{py_sid}/report")
    assert py_rep_res.status_code == 200
    py_rep = py_rep_res.json()
    assert py_rep["resume_skill_gap"] is not None
    py_gap = py_rep["resume_skill_gap"]
    print("  [OK] Final Report Retrieved with Resume Skill-Gap Intelligence:")
    print(f"    - Total Skills Tracked: {py_gap['total_skills_tracked']}")
    print(f"    - Demonstrated Count: {py_gap['demonstrated_count']} ({py_gap['demonstrated_skills']})")
    print(f"    - Claimed Unvalidated Count: {py_gap['claimed_unvalidated_count']}")
    print(f"    - Summary Verdict: {py_gap['summary_verdict']}")
    assert py_gap["total_skills_tracked"] > 0
    results["python_with_resume"] = "PASSED"

    print("\n" + "=" * 60)
    print("STEP 3: Full-Stack Track Interview with Resume Integration")
    print("=" * 60)
    fs_start_res = client.post("/api/interview/start", json={
        "role": "Full-Stack Developer",
        "track": "fullstack",
        "tech_stack": "React + Node.js + Express + SQL",
        "resume_id": resume_id,
        "max_questions": 2,
        "difficulty_mode": "intermediate",
        "dynamic_questions": False,
    })
    assert fs_start_res.status_code == 200
    fs_session = fs_start_res.json()
    fs_sid = fs_session["session_id"]
    print(f"  [OK] Full-Stack Session Created: {fs_sid}")
    print(f"  [OK] Q1: {fs_session['topic']} - {fs_session['text'][:70]}...")

    # Answer Q1
    fs_ans1 = client.post(f"/api/interview/{fs_sid}/answer", json={
        "answer": "React uses the Virtual DOM for reconciliation, diffing elements, and batching DOM updates efficiently."
    })
    assert fs_ans1.status_code == 200

    # Answer Q2
    fs_ans2 = client.post(f"/api/interview/{fs_sid}/answer", json={
        "answer": "REST APIs use standard HTTP verbs (GET, POST, PUT, DELETE) and status codes for stateless client-server communication."
    })
    assert fs_ans2.status_code == 200

    fs_rep_res = client.get(f"/api/interview/{fs_sid}/report")
    assert fs_rep_res.status_code == 200
    fs_rep = fs_rep_res.json()
    assert fs_rep["resume_skill_gap"] is not None
    fs_gap = fs_rep["resume_skill_gap"]
    print("  [OK] Full-Stack Final Report with Skill Gap:")
    print(f"    - Demonstrated Skills: {fs_gap['demonstrated_skills']}")
    print(f"    - Claimed Unvalidated: {fs_gap['claimed_unvalidated_skills']}")
    print(f"    - Summary Verdict: {fs_gap['summary_verdict']}")
    results["fullstack_with_resume"] = "PASSED"

    print("\n" + "=" * 60)
    print("STEP 4: Verify Python & Full-Stack Operate Without Resume (Optionality)")
    print("=" * 60)
    # Python without resume
    py_no_res = client.post("/api/interview/start", json={
        "role": "Python Developer",
        "track": "python",
        "resume_id": None,
        "max_questions": 1,
        "difficulty_mode": "beginner",
        "dynamic_questions": False,
    })
    assert py_no_res.status_code == 200
    no_sid = py_no_res.json()["session_id"]
    client.post(f"/api/interview/{no_sid}/answer", json={"answer": "A list is mutable whereas a tuple is immutable."})
    no_rep = client.get(f"/api/interview/{no_sid}/report").json()
    assert no_rep["resume_id"] is None
    assert no_rep["resume_skill_gap"] is None
    print("  [OK] Python interview without resume succeeded cleanly (resume_skill_gap is None).")

    # Full-Stack without resume
    fs_no_res = client.post("/api/interview/start", json={
        "role": "Full-Stack Developer",
        "track": "fullstack",
        "resume_id": None,
        "max_questions": 1,
        "difficulty_mode": "beginner",
        "dynamic_questions": False,
    })
    assert fs_no_res.status_code == 200
    fs_no_sid = fs_no_res.json()["session_id"]
    client.post(f"/api/interview/{fs_no_sid}/answer", json={"answer": "const and let are block-scoped."})
    fs_no_rep = client.get(f"/api/interview/{fs_no_sid}/report").json()
    assert fs_no_rep["resume_id"] is None
    assert fs_no_rep["resume_skill_gap"] is None
    print("  [OK] Full-Stack interview without resume succeeded cleanly (resume_skill_gap is None).")
    results["sessions_without_resume"] = "PASSED"

    print("\n" + "=" * 60)
    print("E2E VERIFICATION COMPLETE: ALL CHECKS PASSED")
    print("=" * 60)
    for test, status in results.items():
        print(f"  {test.ljust(30)}: {status}")

if __name__ == "__main__":
    run_e2e_verification()
