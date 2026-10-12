"""
Test 4: Complete Interview Workflow TTS/STT Integration Test.
"""

import io
import os
import sys
import time
import wave
import requests
from pathlib import Path

BASE_URL = "http://127.0.0.1:8000"

SAMPLE_RESUME = """
Alex Mercer
alex.mercer@example.com | Seattle, WA
Summary: Python Backend Engineer with 4 years experience in FastAPI, PostgreSQL, and Redis.
Skills: Python, FastAPI, PostgreSQL, Redis, Docker, PyTest, Git
Experience:
Software Engineer at CloudScale Systems (2022 - Present)
- Developed REST APIs in Python using FastAPI and SQLAlchemy.
- Implemented unit testing pipelines using PyTest achieving high test coverage.
"""

audio_reference_path = str(Path("scratch") / "stt_test_reference.wav")

print("=== STEP 1: RESUME UPLOAD & ANALYSIS ===")
t0 = time.perf_counter()
upload_res = requests.post(
    f"{BASE_URL}/api/resume/upload",
    files={"file": ("alex_resume.txt", io.BytesIO(SAMPLE_RESUME.encode("utf-8")), "text/plain")},
    data={"target_role": "Python Developer"},
)
assert upload_res.status_code == 200, f"Upload failed: {upload_res.text}"
profile_data = upload_res.json()
resume_id = profile_data["resume_id"]
routed_track = profile_data["routed_track"]
print(f"Resume ID: {resume_id}")
print(f"Routed track: {routed_track} (confidence: {profile_data['domain_confidence']:.2f})")
print(f"Elapsed: {time.perf_counter() - t0:.3f}s")

print("\n=== STEP 2: PREPARE INTERVIEW AGENDA ===")
t0 = time.perf_counter()
prep_res = requests.post(
    f"{BASE_URL}/api/interview/prepare",
    json={
        "resume_id": resume_id,
        "target_role": "Python Developer",
        "interview_mode": "mock",
        "max_questions": 3,
    },
)
assert prep_res.status_code == 200, f"Prepare failed: {prep_res.text}"
prep_data = prep_res.json()
print(f"Preparation status: {prep_data['status']}")
print(f"Elapsed: {time.perf_counter() - t0:.3f}s")

print("\n=== STEP 3: START INTERVIEW SESSION ===")
t0 = time.perf_counter()
start_res = requests.post(
    f"{BASE_URL}/api/interview/start",
    json={
        "resume_id": resume_id,
        "role": "Python Developer",
        "max_questions": 3,
        "dynamic_questions": False,
    },
)
assert start_res.status_code == 200, f"Start failed: {start_res.text}"
start_data = start_res.json()
session_id = start_data["session_id"]
question_text = start_data["text"]
response_type = start_data.get("response_type", "verbal")
print(f"Session ID: {session_id}")
print(f"Question 1: '{question_text}'")
print(f"Response Type: {response_type}")
print(f"Elapsed: {time.perf_counter() - t0:.3f}s")

print("\n=== STEP 4: TTS QUESTION AUDIO GENERATION (GET /api/interview/{sid}/audio) ===")
t0 = time.perf_counter()
audio_res = requests.get(f"{BASE_URL}/api/interview/{session_id}/audio")
t_audio = time.perf_counter() - t0
assert audio_res.status_code == 200, f"Audio endpoint failed: {audio_res.text}"
assert audio_res.headers.get("content-type") == "audio/wav", f"Expected audio/wav, got {audio_res.headers.get('content-type')}"
audio_bytes = audio_res.content
assert len(audio_bytes) > 0, "Audio stream was empty!"

with wave.open(io.BytesIO(audio_bytes), "rb") as wf:
    channels = wf.getnchannels()
    sampwidth = wf.getsampwidth()
    framerate = wf.getframerate()
    nframes = wf.getnframes()
    duration = nframes / float(framerate)
    print(f"Synthesized Question Audio:")
    print(f"  Size: {len(audio_bytes):,} bytes")
    print(f"  Duration: {duration:.2f} seconds")
    print(f"  Format: {framerate} Hz, {channels} ch, {sampwidth*8}-bit PCM")
    print(f"  Server synthesis time: {t_audio:.3f}s")

print("\n=== STEP 5: TTS HARDWARE PLAYBACK (POST /api/interview/{sid}/speak) ===")
t0 = time.perf_counter()
speak_res = requests.post(
    f"{BASE_URL}/api/interview/{session_id}/speak",
    json={"text": "Question 1: Please explain Python data structures."},
)
t_speak = time.perf_counter() - t0
assert speak_res.status_code == 200, f"Speak failed: {speak_res.text}"
print(f"Speak response: {speak_res.json()}")
print(f"Hardware playback execution time: {t_speak:.3f}s")

print("\n=== STEP 6: STT ANSWER TRANSCRIPTION (POST /api/interview/{sid}/transcribe_upload) ===")
with open(audio_reference_path, "rb") as f:
    t0 = time.perf_counter()
    trans_res = requests.post(
        f"{BASE_URL}/api/interview/{session_id}/transcribe_upload",
        files={"file": ("candidate_answer.wav", f, "audio/wav")},
    )
    t_trans = time.perf_counter() - t0
assert trans_res.status_code == 200, f"Transcribe failed: {trans_res.text}"
trans_data = trans_res.json()
assert trans_data["is_success"] is True
recognized_answer = trans_data["transcript"]
print(f"STT Transcript: '{recognized_answer}'")
print(f"Transcription time: {t_trans:.3f}s")

print("\n=== STEP 7: AUTOMATIC EVALUATION PIPELINE (POST /api/interview/{sid}/answer) ===")
t0 = time.perf_counter()
eval_res = requests.post(
    f"{BASE_URL}/api/interview/{session_id}/answer",
    json={"answer": recognized_answer},
)
t_eval = time.perf_counter() - t0
assert eval_res.status_code == 200, f"Answer evaluation failed: {eval_res.text}"
eval_data = eval_res.json()
evaluation = eval_data["evaluation"]
print(f"Evaluation completed in {t_eval:.2f}s:")
print(f"  Awarded marks: {evaluation['awarded_marks']} / {evaluation['max_marks']} ({evaluation['percentage']}%)")
print(f"  Assessment label: {evaluation['assessment']}")
print(f"  Feedback summary: {evaluation['summary'][:80]}...")
print(f"  Criteria count evaluated: {len(evaluation['criteria'])}")
print(f"  Next question available: {eval_data['next_question'][:60]}...")

print("\n=== STEP 8: FINAL REPORT GENERATION (POST /api/interview/{sid}/end) ===")
t0 = time.perf_counter()
end_res = requests.post(f"{BASE_URL}/api/interview/{session_id}/end", json={"status": "ended_early"})
assert end_res.status_code == 200, f"End failed: {end_res.text}"
rep_data = end_res.json()["report"]
print(f"Final report generated in {time.perf_counter() - t0:.3f}s:")
print(f"  Status: {rep_data['status']}")
print(f"  Questions completed: {rep_data['questions_completed']}")
print(f"  Normalized score: {rep_data['normalized_score']} / 100")
print(f"  Demonstrated skills: {rep_data.get('resume_skill_gap', {}).get('demonstrated_skills', [])}")

print("\n>>> ALL TEST 4 INTERVIEW INTEGRATION STEPS PASSED SUCCESSFULLY! <<<")
