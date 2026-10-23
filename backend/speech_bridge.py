"""
Speech Bridge Module for Adaptive Interview Intelligence.
Integrates existing standalone STT and TTS agents without duplicating code.
Manages thread-safe audio synthesis, microphone recording, audio transcription,
and error classification (timeouts, empty input, hardware errors).
"""

import logging
import os
import sys
import tempfile
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("SpeechBridge")
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter("[%(asctime)s] [%(levelname)s] [SpeechBridge] %(message)s", datefmt="%H:%M:%S")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

# Register external agent locations in sys.path
STT_DIR = Path.home() / "Desktop" / "speech Agent" / "Reusable-Speech-to-Text-Agent"
TTS_DIR = Path.home() / "Desktop" / "TTS-Integration-Test"

for agent_path in (STT_DIR, TTS_DIR):
    if agent_path.exists() and str(agent_path) not in sys.path:
        sys.path.insert(0, str(agent_path))

# Lazy imports placeholders
_STT_CLASS = None
_TTS_CLASS = None


class BuiltinSpeechAssistant:
    """
    Self-contained in-tree Speech-to-Text assistant utilizing SpeechRecognition.
    Operates portably on Render/Linux, Windows, and macOS without requiring external directories.
    """

    def __init__(self):
        self._sr = None
        self._sf = None

    def _get_sr(self):
        if self._sr is None:
            import speech_recognition as sr
            self._sr = sr
        return self._sr

    def _get_sf(self):
        if self._sf is None:
            import soundfile as sf
            self._sf = sf
        return self._sf

    def list_audio_devices(self) -> List[Dict[str, Any]]:
        return []

    def transcribe_file(self, audio_path: str, language: str = "en-US") -> Any:
        class Result:
            def __init__(self, is_success: bool, text: str = "", error_message: Optional[str] = None, engine: str = "google_cloud"):
                self.is_success = is_success
                self.text = text
                self.error_message = error_message
                self.engine = engine

        if not os.path.exists(audio_path):
            return Result(False, "", "Audio file not found.")

        try:
            sr = self._get_sr()
        except ImportError as exc:
            return Result(False, "", f"SpeechRecognition library not available: {exc}")

        wav_path = audio_path
        converted = False
        try:
            sf = self._get_sf()
            data, samplerate = sf.read(audio_path)
            if len(data.shape) > 1 and data.shape[1] > 1:
                data = data.mean(axis=1)

            temp_wav = tempfile.NamedTemporaryFile(suffix="_pcm.wav", delete=False)
            wav_path = temp_wav.name
            temp_wav.close()
            sf.write(wav_path, data, samplerate, format="WAV", subtype="PCM_16")
            converted = True
        except Exception as conv_err:
            logger.info(f"Direct WAV processing without soundfile conversion: {conv_err}")

        recognizer = sr.Recognizer()
        try:
            with sr.AudioFile(wav_path) as source:
                audio = recognizer.record(source)
            text = recognizer.recognize_google(audio, language=language)
            return Result(True, text=text.strip(), engine="google_cloud_stt")
        except sr.UnknownValueError:
            return Result(False, "", "Audio file contained no recognizable speech.")
        except sr.RequestError as exc:
            return Result(False, "", f"Speech recognition service unavailable: {exc}")
        except Exception as exc:
            return Result(False, "", f"Transcription failed: {exc}")
        finally:
            if converted and os.path.exists(wav_path):
                try:
                    os.remove(wav_path)
                except Exception:
                    pass


def _get_stt_class():
    global _STT_CLASS
    if _STT_CLASS is None:
        try:
            from speech_to_text import SpeechToTextAssistant
            _STT_CLASS = SpeechToTextAssistant
        except ImportError as exc:
            logger.info(f"External SpeechToTextAssistant not found ({exc}). Using BuiltinSpeechAssistant.")
            _STT_CLASS = BuiltinSpeechAssistant
    return _STT_CLASS


def _get_tts_class():
    global _TTS_CLASS
    if _TTS_CLASS is None:
        try:
            from tts_assistant import TextToSpeechAssistant
            _TTS_CLASS = TextToSpeechAssistant
        except ImportError as exc:
            logger.warning(f"Could not import TextToSpeechAssistant: {exc}")
    return _TTS_CLASS


class SpeechBridge:
    """
    Thread-safe bridge between the FastAPI interview engine and
    the external STT and TTS assistants.
    """

    def __init__(
        self,
        stt_instance: Optional[Any] = None,
        tts_instance: Optional[Any] = None,
    ):
        self._stt = stt_instance
        self._tts = tts_instance
        self._lock = threading.Lock()
        self._is_recording = False
        self._is_speaking = False

    def get_tts(self) -> Optional[Any]:
        """Lazy-initialize TTS assistant."""
        if self._tts is None:
            tts_cls = _get_tts_class()
            if tts_cls:
                try:
                    self._tts = tts_cls()
                    logger.info("Initialized TextToSpeechAssistant.")
                except Exception as exc:
                    logger.error(f"Failed to initialize TextToSpeechAssistant: {exc}")
        return self._tts

    def get_stt(self) -> Optional[Any]:
        """Lazy-initialize STT assistant."""
        if self._stt is None:
            stt_cls = _get_stt_class()
            if stt_cls:
                try:
                    self._stt = stt_cls()
                    logger.info("Initialized SpeechToTextAssistant.")
                except Exception as exc:
                    logger.error(f"Failed to initialize SpeechToTextAssistant: {exc}")
        return self._stt

    def get_status(self) -> Dict[str, Any]:
        """Returns availability and diagnostics for both TTS and STT agents."""
        tts = self.get_tts()
        stt = self.get_stt()

        tts_available = tts is not None
        tts_voices = []
        if tts:
            try:
                tts_voices = tts.get_available_voices()
            except Exception as exc:
                logger.warning(f"Error querying TTS voices: {exc}")

        stt_available = stt is not None
        stt_devices = []
        if stt:
            try:
                stt_devices = stt.list_audio_devices()
            except Exception as exc:
                logger.warning(f"Error querying STT devices: {exc}")

        return {
            "tts": {
                "available": tts_available,
                "engine": getattr(getattr(tts, "config", None), "engine", "unknown") if tts else None,
                "voices_count": len(tts_voices),
                "voices": tts_voices,
            },
            "stt": {
                "available": stt_available,
                "engine": getattr(getattr(stt, "config", None), "engine", "google_cloud_stt") if stt else None,
                "devices_count": len(stt_devices),
                "devices": stt_devices,
            },
            "state": {
                "is_speaking": self._is_speaking,
                "is_recording": self._is_recording,
            },
        }

    def speak(self, text: str) -> Dict[str, Any]:
        """
        Directly speaks the provided text through the local system audio output.
        Thread-safe; prevents overlapping audio playback or recording.
        """
        if not text or not text.strip():
            return {"success": False, "error": "Empty text provided for speech."}

        tts = self.get_tts()
        if not tts:
            return {
                "success": False,
                "error": "TTS assistant is not available. Please verify pyttsx3 or gTTS installation.",
            }

        with self._lock:
            if self._is_recording:
                return {
                    "success": False,
                    "error": "Cannot speak while microphone is actively recording.",
                }
            self._is_speaking = True

        try:
            tts.speak(text)
            return {"success": True, "error": None}
        except Exception as exc:
            logger.error(f"Error during TTS playback: {exc}")
            return {"success": False, "error": f"TTS playback failed: {str(exc)}"}
        finally:
            with self._lock:
                self._is_speaking = False

    def generate_speech_file(self, text: str, output_path: Optional[str] = None) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Synthesizes speech to an audio file without forced hardware playback.
        Useful for web streaming to the browser.
        Returns: (success, file_path, error_message)
        """
        if not text or not text.strip():
            return False, None, "Text cannot be empty."

        tts = self.get_tts()
        if not tts:
            return False, None, "TTS assistant is not available."

        if not output_path:
            temp_file = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
            output_path = temp_file.name
            temp_file.close()

        with self._lock:
            try:
                tts.save_to_file(text, output_path)
                if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                    return True, output_path, None
                return False, None, "Generated audio file was empty or not created."
            except Exception as exc:
                logger.error(f"Error generating speech file: {exc}")
                return False, None, str(exc)

    def listen_and_transcribe(
        self,
        timeout: float = 8.0,
        phrase_time_limit: float = 30.0,
        language: str = "en-US",
    ) -> Dict[str, Any]:
        """
        Records from the hardware microphone and transcribes candidate speech.
        Handles timeouts, empty transcripts, and hardware errors gracefully.
        """
        stt = self.get_stt()
        if not stt:
            return {
                "is_success": False,
                "text": "",
                "error_message": "Speech-to-Text assistant is not available.",
                "diagnostics": None,
            }

        with self._lock:
            if self._is_speaking:
                return {
                    "is_success": False,
                    "text": "",
                    "error_message": "Cannot record audio while TTS is actively speaking.",
                    "diagnostics": None,
                }
            if self._is_recording:
                return {
                    "is_success": False,
                    "text": "",
                    "error_message": "A microphone recording session is already in progress.",
                    "diagnostics": None,
                }
            self._is_recording = True

        try:
            logger.info("Starting microphone capture (timeout=%.1f, limit=%.1f)...", timeout, phrase_time_limit)
            result = stt.listen(
                timeout=timeout,
                phrase_time_limit=phrase_time_limit,
                language=language,
            )

            # Validate recognition outcome
            if not result.is_success:
                err_msg = result.error_message or "Speech was not recognized."
                return {
                    "is_success": False,
                    "text": "",
                    "error_message": err_msg,
                    "diagnostics": getattr(result, "diagnostics", None),
                }

            transcript = (result.text or "").strip()
            if not transcript:
                return {
                    "is_success": False,
                    "text": "",
                    "error_message": "Audio was recorded but no spoken words were transcribed (silent audio).",
                    "diagnostics": getattr(result, "diagnostics", None),
                }

            return {
                "is_success": True,
                "text": transcript,
                "error_message": None,
                "engine": getattr(result, "engine", "google"),
                "confidence": getattr(result, "confidence", None),
                "diagnostics": getattr(result, "diagnostics", None),
            }

        except Exception as exc:
            logger.error(f"Error during microphone recording: {exc}")
            return {
                "is_success": False,
                "text": "",
                "error_message": f"Microphone capture error: {str(exc)}",
                "diagnostics": None,
            }
        finally:
            with self._lock:
                self._is_recording = False

    def transcribe_audio_file(
        self,
        audio_path: str,
        language: str = "en-US",
        cleanup: bool = False,
    ) -> Dict[str, Any]:
        """
        Transcribes an existing audio file (e.g. uploaded from browser).
        """
        stt = self.get_stt()
        if not stt:
            return {
                "is_success": False,
                "text": "",
                "error_message": "Speech-to-Text assistant is not available.",
            }

        try:
            result = stt.transcribe_file(audio_path, language=language)
            if not result.is_success:
                return {
                    "is_success": False,
                    "text": "",
                    "error_message": result.error_message or "Transcription failed.",
                }

            transcript = (result.text or "").strip()
            if not transcript:
                return {
                    "is_success": False,
                    "text": "",
                    "error_message": "Audio file contained no recognizable speech.",
                }

            return {
                "is_success": True,
                "text": transcript,
                "error_message": None,
                "engine": getattr(result, "engine", "google"),
            }
        except Exception as exc:
            logger.error(f"Error transcribing audio file: {exc}")
            return {
                "is_success": False,
                "text": "",
                "error_message": f"Audio transcription failed: {str(exc)}",
            }
        finally:
            if cleanup and os.path.exists(audio_path):
                try:
                    os.remove(audio_path)
                except Exception:
                    pass


# Default global speech bridge
speech_bridge = SpeechBridge()
