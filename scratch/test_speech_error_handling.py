"""
Test 5: Speech Error Handling and Session Integrity Verification.
"""

import io
import os
import sys
import time
import requests
from pathlib import Path

BASE_URL = "http://127.0.0.1:8000"

project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from backend.speech_bridge import speech_bridge

print("=== 1. EMPTY / WHITESPACE TEXT TTS ERROR HANDLING ===")
ok, path, err = speech_bridge.generate_speech_file("")
print(f"Empty text generate_speech_file -> success={ok}, error='{err}'")
assert ok is False
assert "empty" in err.lower()

speak_empty = speech_bridge.speak("   ")
print(f"Whitespace speak() -> success={speak_empty['success']}, error='{speak_empty.get('error')}'")
assert speak_empty["success"] is False

print("\n=== 2. CORRUPT AUDIO FILE STT ERROR HANDLING ===")
start_res = requests.post(
    f"{BASE_URL}/api/interview/start",
    json={"track": "python", "max_questions": 3, "dynamic_questions": False},
)
assert start_res.status_code == 200
session_id = start_res.json()["session_id"]
initial_question_text = start_res.json().get("question") or start_res.json().get("text")
print(f"Test session: {session_id}, Question: {initial_question_text[:50]}...")

# Upload corrupt file
corrupt_bytes = b"CORRUPTED_NON_AUDIO_DATA_12345"
corrupt_res = requests.post(
    f"{BASE_URL}/api/interview/{session_id}/transcribe_upload",
    files={"file": ("corrupt.wav", io.BytesIO(corrupt_bytes), "audio/wav")},
)
print(f"Corrupt audio upload status: {corrupt_res.status_code}")
corrupt_data = corrupt_res.json()
print(f"Corrupt audio upload response: {corrupt_data}")
assert corrupt_data["is_success"] is False
assert "error" in corrupt_data["error_message"].lower() or "fail" in corrupt_data["error_message"].lower() or "could not be read" in corrupt_data["error_message"].lower()

print("\n=== 3. EMPTY ZERO-BYTE AUDIO FILE ERROR HANDLING ===")
empty_res = requests.post(
    f"{BASE_URL}/api/interview/{session_id}/transcribe_upload",
    files={"file": ("empty.wav", io.BytesIO(b""), "audio/wav")},
)
print(f"Empty audio upload status: {empty_res.status_code}")
empty_data = empty_res.json()
print(f"Empty audio upload response: {empty_data}")
assert empty_data["is_success"] is False

print("\n=== 4. SESSION INTEGRITY VERIFICATION AFTER SPEECH FAILURES ===")
# Verify session did not advance or corrupt
sess_check = requests.get(f"{BASE_URL}/api/interview/{session_id}").json()
print(f"Session status after speech errors: {sess_check['status']}")
print(f"Questions answered count: {sess_check['question_count']}")
print(f"Current question: {sess_check['current_question']['text'][:50]}...")
assert sess_check["status"] == "active"
assert sess_check["question_count"] == 0  # No bogus submission made
assert sess_check["current_question"]["text"] == initial_question_text

print("\n=== 5. SPEECH BRIDGE CONCURRENCY LOCK TEST ===")
# Lock speech bridge in recording state and attempt speak
with speech_bridge._lock:
    speech_bridge._is_recording = True

speak_blocked = speech_bridge.speak("Hello while recording")
print(f"Speak during recording -> success={speak_blocked['success']}, error='{speak_blocked.get('error')}'")
assert speak_blocked["success"] is False
assert "recording" in speak_blocked["error"].lower()

with speech_bridge._lock:
    speech_bridge._is_recording = False
    speech_bridge._is_speaking = True

listen_blocked = speech_bridge.listen_and_transcribe(timeout=1.0)
print(f"Listen during speaking -> success={listen_blocked['is_success']}, error='{listen_blocked.get('error_message')}'")
assert listen_blocked["is_success"] is False
assert "speaking" in listen_blocked["error_message"].lower()

with speech_bridge._lock:
    speech_bridge._is_speaking = False

# Clean up session
requests.post(f"{BASE_URL}/api/interview/{session_id}/end", json={"status": "ended_early"})
print(f"Cleaned up session {session_id}.")

print("\n>>> ALL TEST 5 ERROR HANDLING & SESSION INTEGRITY CHECKS PASSED! <<<")
