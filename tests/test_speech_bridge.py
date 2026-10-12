"""
Automated unit and integration test suite for SpeechBridge and Speech Endpoints.
Covers:
- TTS initialization success & failure
- STT success, empty transcript, recognition failure, timeout
- Thread lock preventing concurrent recording & playback
- FastAPI /api/speech/status, /speak, /audio, /listen, /transcribe_upload
- Retry without question penalty / consumption
- API compatibility with voice_interview.py
"""

import io
import os
import tempfile
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from backend.main import app, session_manager
from backend.speech_bridge import SpeechBridge, speech_bridge


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def mock_recognition_result():
    def _create(is_success=True, text="Lists are mutable while tuples are immutable", error_message=None):
        mock = MagicMock()
        mock.is_success = is_success
        mock.text = text
        mock.error_message = error_message
        mock.engine = "mock_stt"
        mock.confidence = 0.98
        mock.diagnostics = {"device": "Mock Microphone"}
        return mock
    return _create


# =============================================================================
# SPEECH BRIDGE UNIT TESTS
# =============================================================================

def test_speech_bridge_status_structure():
    """Verify that SpeechBridge status returns complete diagnostic metadata."""
    status = speech_bridge.get_status()
    assert "tts" in status
    assert "stt" in status
    assert "state" in status
    assert "available" in status["tts"]
    assert "available" in status["stt"]
    assert "is_speaking" in status["state"]
    assert "is_recording" in status["state"]


def test_tts_speak_success_mocked():
    """Verify TTS speak returns success when speech assistant executes without errors."""
    mock_tts = MagicMock()
    bridge = SpeechBridge(tts_instance=mock_tts)

    res = bridge.speak("Hello candidate, explain list comprehensions.")
    assert res["success"] is True
    assert res["error"] is None
    mock_tts.speak.assert_called_once_with("Hello candidate, explain list comprehensions.")


def test_tts_speak_empty_text():
    """Verify TTS speak rejects empty or whitespace-only input."""
    bridge = SpeechBridge()
    res = bridge.speak("   ")
    assert res["success"] is False
    assert "Empty text" in res["error"]


def test_tts_speak_exception_handling():
    """Verify TTS speak safely catches runtime exceptions without crashing."""
    mock_tts = MagicMock()
    mock_tts.speak.side_effect = RuntimeError("Audio device busy or unavailable")
    bridge = SpeechBridge(tts_instance=mock_tts)

    res = bridge.speak("Sample test question")
    assert res["success"] is False
    assert "Audio device busy" in res["error"]


def test_stt_listen_success_mocked(mock_recognition_result):
    """Verify STT listen extracts valid transcript text upon recognition success."""
    mock_stt = MagicMock()
    mock_stt.listen.return_value = mock_recognition_result(
        is_success=True,
        text="A generator uses yield and evaluates lazily."
    )
    bridge = SpeechBridge(stt_instance=mock_stt)

    result = bridge.listen_and_transcribe(timeout=5.0, phrase_time_limit=10.0)
    assert result["is_success"] is True
    assert result["text"] == "A generator uses yield and evaluates lazily."
    assert result["error_message"] is None


def test_stt_listen_empty_transcript(mock_recognition_result):
    """Verify STT listen rejects empty/silent transcripts with clear error message."""
    mock_stt = MagicMock()
    mock_stt.listen.return_value = mock_recognition_result(
        is_success=True,
        text="   "  # Silent audio transcribed to empty text
    )
    bridge = SpeechBridge(stt_instance=mock_stt)

    result = bridge.listen_and_transcribe()
    assert result["is_success"] is False
    assert result["text"] == ""
    assert "silent audio" in result["error_message"].lower()


def test_stt_listen_timeout_or_failure(mock_recognition_result):
    """Verify STT listen handles timeout/speech recognition failure gracefully."""
    mock_stt = MagicMock()
    mock_stt.listen.return_value = mock_recognition_result(
        is_success=False,
        text="",
        error_message="Listening timed out after 8 seconds (no speech detected)."
    )
    bridge = SpeechBridge(stt_instance=mock_stt)

    result = bridge.listen_and_transcribe()
    assert result["is_success"] is False
    assert "timed out" in result["error_message"]


def test_concurrency_lock_prevents_simultaneous_recording_and_playback():
    """Verify lock prevents speaking while recording and vice-versa."""
    mock_tts = MagicMock()
    mock_stt = MagicMock()
    bridge = SpeechBridge(stt_instance=mock_stt, tts_instance=mock_tts)

    # Simulate recording in progress
    bridge._is_recording = True
    speak_res = bridge.speak("Test speech")
    assert speak_res["success"] is False
    assert "Cannot speak while microphone is actively recording" in speak_res["error"]
    bridge._is_recording = False

    # Simulate speaking in progress
    bridge._is_speaking = True
    listen_res = bridge.listen_and_transcribe()
    assert listen_res["is_success"] is False
    assert "Cannot record audio while TTS is actively speaking" in listen_res["error_message"]
    bridge._is_speaking = False


def test_transcribe_audio_file_mocked(mock_recognition_result):
    """Verify transcribing uploaded audio file via STT assistant."""
    mock_stt = MagicMock()
    mock_stt.transcribe_file.return_value = mock_recognition_result(
        is_success=True,
        text="Dictionaries preserve insertion order since Python 3.7."
    )
    bridge = SpeechBridge(stt_instance=mock_stt)

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tf:
        tf.write(b"RIFF\x00\x00\x00\x00WAVE")
        temp_path = tf.name

    try:
        res = bridge.transcribe_audio_file(temp_path, cleanup=True)
        assert res["is_success"] is True
        assert res["text"] == "Dictionaries preserve insertion order since Python 3.7."
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


# =============================================================================
# FASTAPI SPEECH API ENDPOINTS
# =============================================================================

def test_api_speech_status(client):
    """Verify GET /api/speech/status returns valid diagnostics."""
    res = client.get("/api/speech/status")
    assert res.status_code == 200
    data = res.json()
    assert "tts" in data
    assert "stt" in data


def test_api_speak_endpoint_mocked(client):
    """Verify POST /api/interview/{session_id}/speak with active session."""
    # Start interview session
    start_res = client.post("/api/interview/start", json={
        "role": "Python Developer",
        "max_questions": 5,
        "difficulty_mode": "beginner",
        "dynamic_questions": False,
    })
    session_id = start_res.json()["session_id"]

    with patch.object(speech_bridge, "speak", return_value={"success": True, "error": None}) as mock_speak:
        res = client.post(f"/api/interview/{session_id}/speak")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "spoken"
        assert len(data["spoken_text"]) > 0
        mock_speak.assert_called_once()


def test_api_audio_stream_endpoint(client):
    """Verify GET /api/interview/{session_id}/audio returns WAV audio bytes."""
    start_res = client.post("/api/interview/start", json={
        "role": "Python Developer",
        "max_questions": 5,
        "difficulty_mode": "beginner",
        "dynamic_questions": False,
    })
    session_id = start_res.json()["session_id"]

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tf:
        tf.write(b"RIFF....WAVEfmt ....data....")
        temp_path = tf.name

    with patch.object(speech_bridge, "generate_speech_file", return_value=(True, temp_path, None)):
        res = client.get(f"/api/interview/{session_id}/audio")
        assert res.status_code == 200
        assert "audio/wav" in res.headers["content-type"]
        assert len(res.content) > 0


def test_api_listen_endpoint_mocked(client):
    """Verify POST /api/interview/{session_id}/listen records & returns transcript."""
    start_res = client.post("/api/interview/start", json={
        "role": "Python Developer",
        "max_questions": 5,
        "difficulty_mode": "beginner",
        "dynamic_questions": False,
    })
    session_id = start_res.json()["session_id"]

    mock_res = {
        "is_success": True,
        "text": "The GIL ensures only one thread executes Python bytecode at a time.",
        "error_message": None,
        "diagnostics": {"engine": "sounddevice"}
    }

    with patch.object(speech_bridge, "listen_and_transcribe", return_value=mock_res):
        res = client.post(f"/api/interview/{session_id}/listen", json={"timeout": 5.0})
        assert res.status_code == 200
        data = res.json()
        assert data["is_success"] is True
        assert data["transcript"] == mock_res["text"]


def test_api_transcribe_upload_endpoint(client):
    """Verify POST /api/interview/{session_id}/transcribe_upload accepts audio upload."""
    start_res = client.post("/api/interview/start", json={
        "role": "Python Developer",
        "max_questions": 5,
        "difficulty_mode": "beginner",
        "dynamic_questions": False,
    })
    session_id = start_res.json()["session_id"]

    mock_res = {
        "is_success": True,
        "text": "Decorators are callables that take a function and return an extended function.",
        "error_message": None
    }

    with patch.object(speech_bridge, "transcribe_audio_file", return_value=mock_res):
        fake_wav = io.BytesIO(b"RIFF....WAVEfakeaudio")
        res = client.post(
            f"/api/interview/{session_id}/transcribe_upload",
            files={"file": ("candidate.wav", fake_wav, "audio/wav")}
        )
        assert res.status_code == 200
        data = res.json()
        assert data["is_success"] is True
        assert data["transcript"] == mock_res["text"]


def test_failed_recognition_does_not_consume_question_or_award_marks(client):
    """
    CRITICAL REQUIREMENT: When recognition fails or is empty,
    it must NOT advance the question, must NOT award marks,
    and the candidate must be able to retry.
    """
    start_res = client.post("/api/interview/start", json={
        "role": "Python Developer",
        "max_questions": 5,
        "difficulty_mode": "beginner",
        "dynamic_questions": False,
    })
    session_id = start_res.json()["session_id"]
    initial_q_text = start_res.json()["question"]

    # STT fails
    mock_failed_res = {
        "is_success": False,
        "text": "",
        "error_message": "Audio was recorded but no spoken words were transcribed (silent audio)."
    }

    with patch.object(speech_bridge, "listen_and_transcribe", return_value=mock_failed_res):
        listen_res = client.post(f"/api/interview/{session_id}/listen")
        assert listen_res.status_code == 200
        assert listen_res.json()["is_success"] is False

    # Check session state: question must NOT have advanced!
    session_res = client.get(f"/api/interview/{session_id}")
    session_data = session_res.json()
    assert session_data["current_question"]["text"] == initial_q_text
    assert session_data["history_count"] == 0  # No question was consumed

    # Empty answer submission is rejected by API
    empty_sub = client.post(f"/api/interview/{session_id}/answer", json={"answer": "   "})
    assert empty_sub.status_code == 400

    # History count remains 0
    session_res = client.get(f"/api/interview/{session_id}")
    assert session_res.json()["history_count"] == 0

    # Candidate retries with valid answer
    from backend.models import EvaluationResult, CriterionEvaluation
    mock_eval = EvaluationResult(
        question_id="py-beg-001",
        awarded_marks=4.5,
        max_marks=5.0,
        percentage=90.0,
        criteria_evaluations=[
            CriterionEvaluation(
                criterion_id="mutability_distinction",
                awarded_marks=2.5,
                max_marks=2.5,
                evidence="Lists mutable",
                explanation="Good",
            )
        ],
        demonstrated_concepts=["Mutability difference"],
        missing_concepts=[],
        incorrect_claims=[],
        summary_explanation="Good response",
    )
    with patch("backend.session_manager.EvaluationEngine.evaluate_answer", return_value=mock_eval):
        valid_sub = client.post(f"/api/interview/{session_id}/answer", json={
            "answer": "Lists are mutable sequences whereas tuples are immutable and hashable."
        })
        assert valid_sub.status_code == 200
        assert valid_sub.json()["evaluation"]["awarded_marks"] > 0
        assert valid_sub.json()["question_number"] == 1
