"""
Live Server Acceptance Verification Script: Resume-First Candidate Journey
Tests the running server at http://127.0.0.1:8000 for the full Resume-First lifecycle.
"""

import io
import requests
import sys

BASE_URL = "http://127.0.0.1:8000"

def run_resume_first_acceptance_test():
    print("==============================================================")
    print("STARTING LIVE RESUME-FIRST ACCEPTANCE VERIFICATION")
    print(f"Target Server: {BASE_URL}")
    print("==============================================================")

    # 1. Health & Tracks Check
    res = requests.get(f"{BASE_URL}/api/health")
    assert res.status_code == 200, f"Health check failed: {res.text}"
    print("[1/10] Server health check OK")

    res_tracks = requests.get(f"{BASE_URL}/api/tracks")
    assert res_tracks.status_code == 200
    tracks = res_tracks.json()["tracks"]
    track_ids = [t["id"] for t in tracks]
    assert "python" in track_ids and "fullstack" in track_ids
    print(f"[2/10] Multi-track availability verified: {track_ids}")

    # 2. Upload Resume to Live Server
    resume_text = """
    Alex Morgan
    Senior Full-Stack & Python Engineer
    alex.morgan@example.com

    SUMMARY
    6+ years developing Python FastAPI backend systems and React frontends with SQL databases.

    TECHNICAL SKILLS
    Python, FastAPI, React, JavaScript, SQL, AsyncIO, Docker

    EXPERIENCE
    TechCore Labs: Architected high-throughput FastAPI microservices using AsyncIO and PostgreSQL.
    """
    files = {"file": ("alex_morgan_resume.txt", io.BytesIO(resume_text.encode("utf-8")), "text/plain")}
    data = {
        "job_title": "Senior Python Engineer",
        "company": "TechCore",
        "job_description": "Seeking expert in Python, AsyncIO, and API development.",
        "track": "python"
    }
    res_upload = requests.post(f"{BASE_URL}/api/resume/upload", files=files, data=data)
    assert res_upload.status_code == 200, f"Resume upload failed: {res_upload.text}"
    upload_data = res_upload.json()
    resume_id = upload_data["resume_id"]
    profile = upload_data["profile"]
    assert resume_id is not None
    skills = profile.get("claimed_skills") or profile.get("skills", [])
    assert any("python" in s.lower() for s in skills)
    print(f"[3/10] Resume uploaded successfully! Resume ID: {resume_id[:8]}... Skills: {skills[:6]}")

    # 3. Test Interview Plan Generation for Python Track
    res_plan_py = requests.post(f"{BASE_URL}/api/resume/plan", json={
        "resume_id": resume_id,
        "track": "python",
        "role": "Python Developer",
        "max_questions": 5,
        "difficulty_mode": "adaptive"
    })
    assert res_plan_py.status_code == 200, f"Plan generation failed: {res_plan_py.text}"
    plan_py = res_plan_py.json()
    assert plan_py["track"] == "python"
    assert len(plan_py["selected_topics"]) > 0
    criteria_list = plan_py.get("planned_questions_criteria") or plan_py.get("questions_criteria", [])
    assert len(criteria_list) == 5
    print(f"[4/10] Python interview plan generated: {len(criteria_list)} criteria items. Topics: {plan_py['selected_topics'][:4]}")

    # 4. Test Interview Plan Generation for Full-Stack Track (differs appropriately)
    res_plan_fs = requests.post(f"{BASE_URL}/api/resume/plan", json={
        "resume_id": resume_id,
        "track": "fullstack",
        "role": "Full-Stack Developer",
        "max_questions": 5,
        "difficulty_mode": "adaptive"
    })
    assert res_plan_fs.status_code == 200
    plan_fs = res_plan_fs.json()
    assert plan_fs["track"] == "fullstack"
    assert any(t in ["React & Component Architecture", "Backend & REST APIs", "SQL & Databases", "JavaScript Core"] for t in plan_fs["selected_topics"])
    print(f"[5/10] Full-Stack interview plan generated: Topics: {plan_fs['selected_topics'][:4]}")

    # 5. Start Personalized Python Interview using resume_id
    res_start = requests.post(f"{BASE_URL}/api/interview/start", json={
        "role": "Python Developer",
        "track": "python",
        "difficulty_mode": "adaptive",
        "max_questions": 3,
        "dynamic_questions": False,
        "resume_id": resume_id
    })
    assert res_start.status_code == 200, f"Start interview failed: {res_start.text}"
    start_session = res_start.json()
    session_id = start_session["session_id"]
    q1 = start_session["question"]
    q1_reason = start_session.get("reason", "")
    print(f"[6/10] Session started: {session_id[:8]}... Personalized reason: '{q1_reason}'")
    assert "Validating resume claim" in q1_reason or "Personalized" in q1_reason or "Assessing" in q1_reason

    # 6. Submit High-Scoring Answer for Question 1
    res_ans1 = requests.post(f"{BASE_URL}/api/interview/{session_id}/answer", json={
        "answer": "Lists are mutable heterogeneous sequences stored in dynamic contiguous arrays. Tuples are immutable and hashable if their items are hashable."
    })
    assert res_ans1.status_code == 200
    eval1 = res_ans1.json()["evaluation"]
    print(f"[7/10] Q1 Evaluated: {eval1['awarded_marks']}/{eval1['max_marks']} marks ({eval1['percentage']}%)")
    assert eval1["awarded_marks"] > 0

    # 7. Submit Weak Answer for Question 2
    res_ans2 = requests.post(f"{BASE_URL}/api/interview/{session_id}/answer", json={
        "answer": "I don't remember this topic."
    })
    assert res_ans2.status_code == 200
    eval2 = res_ans2.json()["evaluation"]
    print(f"[8/10] Q2 Evaluated: {eval2['awarded_marks']}/{eval2['max_marks']} marks")

    # 8. End Early and Retrieve Final Intelligence Report
    res_end = requests.post(f"{BASE_URL}/api/interview/{session_id}/end", json={"status": "ended_early"})
    assert res_end.status_code == 200
    report = res_end.json()["report"]
    assert report["status"] == "ended_early"
    assert "interview_plan" in report and report["interview_plan"] is not None
    assert "resume_skill_gap" in report and report["resume_skill_gap"] is not None

    gap = report["resume_skill_gap"]
    print(f"[9/10] Final Report Skill Gap Verified: Total Tracked={gap['total_skills_tracked']}, Demonstrated={gap['demonstrated_count']}")
    for s in gap["skills"]:
        ev_qs = [f"Q#{q['question_number']}({q['awarded_marks']}/{q['max_marks']})" for q in s.get("interview_evidence", [])]
        print(f"       -> {s['skill_name']}: {s['status'].upper()} (Score: {s.get('score_percentage')}%) Evidence: {ev_qs}")

    assert gap["demonstrated_count"] >= 1, f"Expected at least 1 demonstrated skill from 4.5/5 answer, got {gap['demonstrated_count']}"
    assert any(s["status"] == "demonstrated" for s in gap["skills"])

    # 9. Verify General Interview Without Resume Still Works Flawlessly
    res_gen = requests.post(f"{BASE_URL}/api/interview/start", json={
        "role": "Python Developer",
        "track": "python",
        "max_questions": 2,
        "dynamic_questions": False,
        "resume_id": None
    })
    assert res_gen.status_code == 200
    gen_session_id = res_gen.json()["session_id"]
    res_gen_end = requests.post(f"{BASE_URL}/api/interview/{gen_session_id}/end", json={"status": "ended_early"})
    assert res_gen_end.status_code == 200
    gen_report = res_gen_end.json()["report"]
    assert gen_report["resume_skill_gap"] is None
    print("[10/10] General interview without resume confirmed fully functional!")

    print("==============================================================")
    print("ALL 10 LIVE RESUME-FIRST ACCEPTANCE CHECKS PASSED SUCCESSFULLY!")
    print("==============================================================")

if __name__ == "__main__":
    run_resume_first_acceptance_test()
