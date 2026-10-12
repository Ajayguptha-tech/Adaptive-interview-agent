"""
Test script for live STT endpoint and physical microphone capture probe.
"""

import os
import sys
import time
import requests
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from backend.speech_bridge import speech_bridge

audio_file = str(Path("scratch") / "stt_test_reference.wav")

print("=== 1. TESTING LIVE HTTP API: POST /api/interview/{sid}/transcribe_upload ===")
# Start a temporary session
start_res = requests.post(
    "http://127.0.0.1:8000/api/interview/start",
    json={"track": "python", "max_questions": 2, "dynamic_questions": False},
)
assert start_res.status_code == 200, f"Failed to start session: {start_res.text}"
session_id = start_res.json()["session_id"]
print(f"Temporary session created: {session_id}")

# Upload the reference WAV file
with open(audio_file, "rb") as f:
    files = {"file": ("test_answer.wav", f, "audio/wav")}
    t0 = time.perf_counter()
    trans_res = requests.post(
        f"http://127.0.0.1:8000/api/interview/{session_id}/transcribe_upload",
        files=files,
    )
    t_api = time.perf_counter() - t0

print(f"API HTTP Status: {trans_res.status_code}")
print(f"API Call Duration: {t_api:.3f}s")
api_data = trans_res.json()
print(f"API Response Body: {api_data}")
assert api_data["is_success"] is True
assert len(api_data["transcript"]) > 0

print("\n=== 2. PROBING PHYSICAL MICROPHONE CAPTURE: POST /api/interview/{sid}/listen ===")
print("Initiating hardware microphone probe (timeout=3.0s, limit=3.0s)...")
t0 = time.perf_counter()
mic_res = requests.post(
    f"http://127.0.0.1:8000/api/interview/{session_id}/listen",
    json={"timeout": 3.0, "phrase_time_limit": 3.0, "language": "en-US"},
)
t_mic = time.perf_counter() - t0

print(f"Mic probe HTTP Status: {mic_res.status_code}")
print(f"Mic probe Duration: {t_mic:.3f}s")
mic_data = mic_res.json()
print(f"Mic probe Response: {mic_data}")

# Clean up session
requests.post(f"http://127.0.0.1:8000/api/interview/{session_id}/end", json={"status": "ended_early"})
print(f"Cleaned up session {session_id}.")
