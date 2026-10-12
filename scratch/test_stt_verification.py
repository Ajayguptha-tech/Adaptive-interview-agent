"""
Test script for STT audio file transcription and hardware microphone probe.
"""

import os
import sys
import time
import wave
from pathlib import Path
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from backend.speech_bridge import speech_bridge

test_sentence = "Lists are mutable, while tuples are immutable in Python."
scratch_dir = Path("scratch")
scratch_dir.mkdir(exist_ok=True)
audio_file = str(scratch_dir / "stt_test_reference.wav")

print("=== 1. GENERATING KNOWN-GOOD REFERENCE AUDIO FILE ===")
ok, path, err = speech_bridge.generate_speech_file(test_sentence, output_path=audio_file)
print(f"WAV generated: {ok}, path: {path}, error: {err}")

if ok and os.path.exists(audio_file):
    size = os.path.getsize(audio_file)
    with wave.open(audio_file, "rb") as wf:
        nframes = wf.getnframes()
        framerate = wf.getframerate()
        duration = nframes / float(framerate)
        print(f"Audio stats: size={size:,} bytes, duration={duration:.2f}s, rate={framerate}Hz, channels={wf.getnchannels()}")

    print("\n=== 2. SUBMITTING AUDIO FILE TO STT (FILE-BASED TRANSCRIBE) ===")
    t0 = time.perf_counter()
    res = speech_bridge.transcribe_audio_file(audio_file)
    t_stt = time.perf_counter() - t0
    print(f"Transcription duration: {t_stt:.3f}s")
    print(f"Result dict: {res}")
    print(f"Original sentence: {test_sentence}")
    print(f"Transcribed text:  {res.get('text', '')}")

    orig_clean = test_sentence.lower().replace(".", "").replace(",", "").strip()
    trans_clean = res.get("text", "").lower().replace(".", "").replace(",", "").strip()
    print(f"Normalized comparison:")
    print(f"  Expected:   '{orig_clean}'")
    print(f"  Recognized: '{trans_clean}'")
    is_match = trans_clean == orig_clean
    print(f"Exact normalized match: {is_match}")
else:
    print("Failed to generate reference audio.")
