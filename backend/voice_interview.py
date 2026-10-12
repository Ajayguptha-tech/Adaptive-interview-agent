
import sys
from pathlib import Path

import requests

# Existing standalone agents: do not copy or modify their source.
STT_PATH = Path.home() / "Desktop" / "speech Agent" / "Reusable-Speech-to-Text-Agent"
TTS_PATH = Path.home() / "Desktop" / "TTS-Integration-Test"

sys.path.insert(0, str(STT_PATH))
sys.path.insert(0, str(TTS_PATH))

from speech_to_text import SpeechToTextAssistant
from tts_assistant import TextToSpeechAssistant


API = "http://127.0.0.1:8000"
ROLE = "Python Developer"
MAX_QUESTIONS = 5


def main():
    print("\n=== Adaptive Interview Intelligence ===")
    print("Initializing STT and TTS agents...")

    stt = SpeechToTextAssistant()
    tts = TextToSpeechAssistant()

    # Start an interview using the existing FastAPI backend.
    response = requests.post(
        f"{API}/api/interview/start",
        json={
            "role": ROLE,
            "job_description": (
                "Python fundamentals, data structures and problem solving"
            ),
            "resume_summary": "",
            "competencies": [
                "Python fundamentals",
                "Data structures",
                "Problem solving",
                "Technical communication",
            ],
            "max_questions": MAX_QUESTIONS,
        },
        timeout=180,
    )
    response.raise_for_status()
    interview = response.json()

    session_id = interview["session_id"]
    question = interview["question"]

    print(f"\nInterview started. Session: {session_id}")

    try:
        while True:
            print("\nInterviewer:", question)
            print("Speaking question...")

            tts.speak(question)

            input(
                "\nPress ENTER when you are ready to answer "
                "using your microphone..."
            )

            print("Listening... Speak clearly after the prompt.")

            result = stt.listen(
                timeout=10,
                phrase_time_limit=30,
                language="en-US",
            )

            if not result.is_success or not result.text.strip():
                print("\nSpeech was not transcribed.")
                print("Details:", result.error_message or "No speech detected.")
                print("Please try answering again.")
                continue

            answer = result.text.strip()
            print("\nRecognized answer:", answer)

            response = requests.post(
                f"{API}/api/interview/{session_id}/answer",
                json={"answer": answer},
                timeout=180,
            )
            response.raise_for_status()
            result_data = response.json()

            evaluation = result_data["evaluation"]
            print("\n--- Answer Evaluation ---")
            print("Competency:", evaluation["competency"])
            print("Assessment:", evaluation["assessment"])
            print("Evidence:", evaluation["evidence_from_answer"])
            print("Missing knowledge:", evaluation["missing_knowledge"])

            if result_data["is_complete"]:
                print("\nInterview completed!")
                break

            question = result_data["next_question"]

            if not question:
                print("No next question was returned. Stopping safely.")
                break

    except KeyboardInterrupt:
        print("\nInterview interrupted by user.")

    except requests.RequestException as exc:
        print("\nAPI connection error:", exc)

    finally:
        try:
            report_response = requests.get(
                f"{API}/api/interview/{session_id}/report",
                timeout=30,
            )
            if report_response.ok:
                report = report_response.json()
                print("\n=== Interview Report ===")
                print("Status:", report["status"])
                print("Answers evaluated:", report["answers_evaluated"])
                print("Competencies:")
                for competency, records in report["competency_report"].items():
                    print(f"\n{competency}:")
                    for record in records:
                        print("  Assessment:", record["assessment"])
                        print("  Evidence:", record["evidence"])
                        print("  Missing:", record["missing_knowledge"])
        except Exception as exc:
            print("Could not retrieve final report:", exc)


if __name__ == "__main__":
    main()
