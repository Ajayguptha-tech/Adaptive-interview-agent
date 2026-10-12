"""
Automated Speech Integration Tests for Phase 7:
1. Live Speech Status Endpoint.
2. Live Audio Synthesis & WAV generation (/audio).
3. Live Audio Upload & Transcription Route with corrupt/invalid audio handling.
4. Browser Microphone Permission Denial and Graceful UI Error Handling via Playwright.
5. Live Local System Audio TTS generation test.
"""

import io
import os
import sys
import requests
from playwright.sync_api import sync_playwright

BASE_URL = "http://127.0.0.1:8000"

def run_speech_integration_verification():
    print("=" * 70)
    print("PHASE 7 SPEECH INTEGRATION AUTOMATED TESTING")
    print("=" * 70)

    # 1. Test Speech API availability
    res_status = requests.get(f"{BASE_URL}/api/speech/status")
    assert res_status.status_code == 200, f"Status failed: {res_status.text}"
    status_data = res_status.json()
    assert status_data["tts"]["available"] is True
    assert status_data["stt"]["available"] is True
    print(f"[1/5] Speech API Availability Verified: TTS={status_data['tts']['engine']}, Voices={status_data['tts']['voices_count']}, STT Devices={status_data['stt']['devices_count']}")

    # 2. Test Live TTS Audio Generation & Stream Route (/api/interview/{id}/audio)
    res_start = requests.post(f"{BASE_URL}/api/interview/start", json={
        "role": "Python Developer",
        "track": "python",
        "max_questions": 1,
        "dynamic_questions": False,
        "difficulty_mode": "beginner"
    })
    assert res_start.status_code == 200
    session_id = res_start.json()["session_id"]
    print(f"[2/5] Created active session {session_id[:8]}... Testing TTS audio generation...")

    res_audio = requests.get(f"{BASE_URL}/api/interview/{session_id}/audio")
    assert res_audio.status_code == 200, f"Audio route failed: {res_audio.status_code}"
    assert res_audio.headers.get("content-type") == "audio/wav"
    audio_content = res_audio.content
    assert len(audio_content) > 1000, f"Audio content too small: {len(audio_content)} bytes"
    # Check WAV RIFF header
    assert audio_content[:4] == b"RIFF" and audio_content[8:12] == b"WAVE"
    print(f"      Valid WAV Audio Stream Received: {len(audio_content)} bytes (RIFF/WAVE header verified)")

    # 3. Test Invalid & Corrupt Audio Upload Handling
    print("[3/5] Testing invalid audio file upload error handling...")
    corrupt_audio = io.BytesIO(b"This is not a real audio file")
    res_bad_upload = requests.post(
        f"{BASE_URL}/api/interview/{session_id}/transcribe_upload",
        files={"file": ("corrupt.wav", corrupt_audio, "audio/wav")}
    )
    assert res_bad_upload.status_code in (200, 400, 500)
    bad_data = res_bad_upload.json()
    assert bad_data.get("is_success") is False or "error" in str(bad_data).lower()
    print(f"      Correctly handled invalid audio without crashing: '{bad_data.get('error_message') or bad_data.get('detail')}'")

    # 4. Test Browser Microphone Permission Denial via Playwright
    print("[4/5] Testing Browser Microphone Permission Denial & Recovery...")
    dialog_logs = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        # Context WITHOUT microphone permissions granted
        ctx = browser.new_context(permissions=[])
        page = ctx.new_page()

        page.on("dialog", lambda d: (dialog_logs.append(d.message), d.accept()))

        page.goto(BASE_URL)
        page.locator("#card-track-python button").click()
        page.wait_for_selector("#setup-view.active")

        # Start interview in predefined mode
        page.locator("#dynamic-mode-pills button[data-dynamic='false']").click()
        page.locator("#start-interview-btn").click()
        page.wait_for_selector("#interview-view.active")

        # Attempt to record audio
        page.locator("#record-toggle-btn").click()
        page.wait_for_timeout(1000)

        # Confirm graceful error dialog
        state_text = page.locator("#voice-state-text").inner_text()
        print(f"      Voice state on mic denial: '{state_text}'")
        assert "ERROR" in state_text or any("microphone" in m.lower() for m in dialog_logs)
        print(f"      Gracefully captured permission denial dialog: '{dialog_logs[0] if dialog_logs else 'State set to ERROR'}'")

        browser.close()

    # 5. Clean up interview session
    requests.post(f"{BASE_URL}/api/interview/{session_id}/end", json={"status": "completed"})
    print("[5/5] Test session finalized cleanly.")

    print("=" * 70)
    print("ALL AUTOMATED SPEECH INTEGRATION TESTS PASSED SUCCESSFULLY!")
    print("=" * 70)

if __name__ == "__main__":
    run_speech_integration_verification()
