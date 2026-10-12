"""
Adaptive Interview Intelligence - FastAPI Backend
Provides skill-adaptive Python interview orchestration, fair rubric-based
answer evaluation, deterministic scoring normalized to 100, and comprehensive reporting.
"""

import asyncio
import logging
import tempfile
import time
from pathlib import Path
from typing import Optional, Dict, Any
from fastapi import FastAPI, HTTPException, Request, UploadFile, File, Form
from fastapi.responses import HTMLResponse, FileResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from backend.models import (
    StartInterviewRequest,
    PrepareInterviewRequest,
    AnswerRequest,
    EndInterviewRequest,
    InterviewMode,
    FeedbackMode,
)

logger = logging.getLogger(__name__)
from backend.session_manager import SessionManager
from backend.llm_client import default_llm_client
from backend.speech_bridge import speech_bridge
from backend.question_bank import get_all_topics, get_all_competencies, get_all_questions
from backend.interviewers.registry import default_registry
from backend.fullstack.question_bank import (
    get_all_fullstack_topics,
    get_all_fullstack_competencies,
    get_all_fullstack_questions,
    TECH_STACK_CONFIGS,
)


class SpeakRequest(BaseModel):
    text: Optional[str] = None


class ListenRequest(BaseModel):
    timeout: float = Field(default=8.0, ge=1.0, le=30.0)
    phrase_time_limit: float = Field(default=30.0, ge=2.0, le=90.0)
    language: str = "en-US"

app = FastAPI(
    title="Adaptive Interview Intelligence API",
    version="3.1.0",
    description="Adaptive technical interview engine supporting Python and Full-Stack tracks with deterministic rubric evaluation",
)

# Enable CORS for web interfaces
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory session manager
session_manager = SessionManager()

# Static directory path
STATIC_DIR = Path(__file__).parent / "static"
if not STATIC_DIR.exists():
    STATIC_DIR.mkdir(parents=True, exist_ok=True)

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/")
def home(request: Request):
    """
    Serves the modern interview web application UI.
    If JSON is explicitly requested, returns API service status.
    """
    accept = request.headers.get("accept", "")
    if "text/html" in accept or "*/*" in accept:
        index_file = STATIC_DIR / "index.html"
        if index_file.exists():
            return FileResponse(str(index_file))

    return {
        "message": "Adaptive Python Interviewer API is running",
        "version": "3.1.0",
        "model": default_llm_client.model_name,
        "tracks": ["python", "fullstack"],
        "docs": "/docs",
        "ui": "/",
    }


@app.get("/api/health")
def health():
    """Health check for API and Ollama service."""
    ollama_status = default_llm_client.check_health()
    return {
        "api": "running",
        "ollama": "connected" if ollama_status["available"] else "disconnected",
        "required_model_available": ollama_status["has_required_model"],
        "models": ollama_status.get("models", []),
    }


@app.get("/api/tracks")
def get_interview_tracks():
    """Returns all registered interviewer tracks and metadata."""
    tracks = default_registry.list_tracks()
    return {
        "tracks": tracks,
        "default_track": "python",
    }


@app.get("/api/topics")
def get_available_topics(track: str = "python"):
    """
    Returns available topics and competencies for the given interviewer track.
    Defaults to 'python' for backwards compatibility.
    """
    try:
        interviewer = default_registry.get(track)
        info = interviewer.get_topics_and_competencies()
        if isinstance(info, dict):
            topics = info.get("topics", [])
            competencies = info.get("competencies", [])
        else:
            topics, competencies = info

        tech_stacks = []
        total_questions = 0
        if track == "fullstack":
            tech_stacks = list(TECH_STACK_CONFIGS.keys())
            total_questions = len(get_all_fullstack_questions())
        else:
            total_questions = len(get_all_questions())

        return {
            "track": track,
            "topics": topics,
            "competencies": competencies,
            "tech_stacks": tech_stacks,
            "total_questions": total_questions,
        }
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to fetch topics: {exc}")


# =============================================================================
# RESUME ANALYZER AGENT INTEGRATION ENDPOINTS
# =============================================================================

@app.post("/api/resume/upload")
async def upload_resume(
    file: UploadFile = File(...),
    job_title: Optional[str] = Form(None),
    job_description: Optional[str] = Form(None),
    company: Optional[str] = Form(None),
    required_skills: Optional[str] = Form(None),
    preferred_skills: Optional[str] = Form(None),
    target_role: Optional[str] = Form(None),
):
    """
    Uploads and analyzes a resume (PDF, DOCX, TXT) via the integrated ResumeAnalyzerAgent pipeline.
    Extracts contact info, skills, experience, and integrity audit; deterministically routes candidate.
    """
    from backend.resume_analyzer.adapter import get_resume_adapter

    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename cannot be empty.")

    contents = await file.read()
    if not contents:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    req_skills_list = [s.strip() for s in required_skills.split(",") if s.strip()] if required_skills else None
    pref_skills_list = [s.strip() for s in preferred_skills.split(",") if s.strip()] if preferred_skills else None

    effective_role = target_role or job_title or "Software Engineer"
    adapter = get_resume_adapter()

    # Offload parsing and AI analysis to thread to avoid blocking event loop
    result = await asyncio.to_thread(
        adapter.analyze_resume,
        filename=file.filename,
        file_bytes=contents,
        job_title=job_title,
        job_description=job_description,
        company=company,
        required_skills=req_skills_list,
        preferred_skills=pref_skills_list,
        target_role=effective_role,
    )

    if not result.get("is_success", False):
        raise HTTPException(
            status_code=400,
            detail=result.get("error_message", "Failed to analyze resume."),
        )

    return {
        **result,
        "profile": result,
    }


@app.get("/api/resume/{resume_id}")
def get_resume_analysis(resume_id: str):
    """Retrieves parsed resume profile by ID."""
    from backend.resume_analyzer.adapter import get_resume_adapter
    profile = get_resume_adapter().get_resume_profile(resume_id)
    if not profile:
        raise HTTPException(status_code=404, detail=f"Resume profile '{resume_id}' not found.")
    return profile


@app.get("/api/resume/{resume_id}/eligibility")
def get_resume_eligibility(resume_id: str, target_role: Optional[str] = None):
    """Retrieves or evaluates role readiness assessment for candidate."""
    from backend.resume_analyzer.adapter import get_resume_adapter
    from backend.resume_analyzer.eligibility import RoleEligibilityAssessor

    profile = get_resume_adapter().get_resume_profile(resume_id)
    if not profile:
        raise HTTPException(status_code=404, detail=f"Resume profile '{resume_id}' not found.")

    effective_role = target_role or profile.get("target_role") or "Software Engineer"
    eligibility_res = RoleEligibilityAssessor.assess_eligibility(
        resume_profile=profile,
        target_role=effective_role,
        integrity_status=profile.get("authenticity_outcome", "passed"),
    )
    return eligibility_res.model_dump()


class GeneratePlanRequest(BaseModel):
    resume_id: str
    track: Optional[str] = None
    max_questions: int = 5
    difficulty_mode: str = "adaptive"
    tech_stack: Optional[str] = None
    target_role: Optional[str] = None
    job_description: Optional[str] = None
    company: Optional[str] = None


@app.post("/api/resume/plan")
def generate_interview_plan_endpoint(data: GeneratePlanRequest):
    """
    Generates a tailored interview plan for a parsed resume profile and track.
    Provides candidate with clear transparency on topics, initial difficulty,
    and claimed skills requiring verification prior to interview launch.
    """
    from backend.resume_analyzer.adapter import get_resume_adapter
    from backend.interview_plan import InterviewPlanner

    profile = get_resume_adapter().get_resume_profile(data.resume_id)
    if not profile:
        raise HTTPException(status_code=404, detail=f"Resume profile '{data.resume_id}' not found.")

    target_track = data.track or profile.get("routed_track") or "python"

    plan = InterviewPlanner.create_plan(
        resume_profile=profile,
        track=target_track,
        max_questions=data.max_questions,
        difficulty_mode=data.difficulty_mode,
        tech_stack=data.tech_stack or profile.get("recommended_tech_stack"),
        target_role=data.target_role or profile.get("target_role"),
        job_description=data.job_description,
        company=data.company,
    )
    profile["interview_plan"] = plan.model_dump()
    return plan.model_dump()


@app.post("/api/interview/prepare")
async def prepare_interview_endpoint(data: PrepareInterviewRequest):
    """
    Prepares candidate's personalized interview plan and question sequence
    before the interview begins. Ensures all questions are ready with zero startup lag.
    """
    from backend.resume_analyzer.adapter import get_resume_adapter
    from backend.interview_plan import InterviewPlanner

    profile = get_resume_adapter().get_resume_profile(data.resume_id)
    if not profile:
        raise HTTPException(
            status_code=404,
            detail=f"Resume profile '{data.resume_id}' not found. Please upload resume first."
        )

    track = profile.get("routed_track") or "python"
    target_role = data.target_role or profile.get("target_role") or "Software Engineer"
    tech_stack = data.tech_stack or profile.get("recommended_tech_stack")

    diff_mode = (
        data.difficulty_mode.value
        if hasattr(data.difficulty_mode, "value")
        else str(data.difficulty_mode)
    )

    plan = await asyncio.to_thread(
        InterviewPlanner.create_plan,
        resume_profile=profile,
        track=track,
        max_questions=data.max_questions,
        difficulty_mode=diff_mode,
        tech_stack=tech_stack,
        target_role=target_role,
    )
    profile["interview_plan"] = plan.model_dump()

    return {
        "status": "ready",
        "resume_id": data.resume_id,
        "track": track,
        "interview_mode": data.interview_mode,
        "plan": plan.model_dump(),
        "summary": plan.summary,
        "total_questions": len(plan.planned_questions_criteria),
    }


@app.get("/api/interview/{session_id}/skill_gap")
def get_interview_skill_gap(session_id: str):
    """
    Returns evidence-based skill gap intelligence comparing resume claims with interview evaluations.
    """
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Interview session not found.")

    if not getattr(session, "resume_profile", None):
        return {
            "has_resume": False,
            "message": "No resume was associated with this interview session.",
            "report": None,
        }

    from backend.resume_analyzer.skill_gap import SkillGapAnalyzer
    history_records = [
        {
            "question_number": r.question_number,
            "question_text": r.question.text,
            "topic": r.question.topic,
            "competency": r.question.competency,
            "awarded_marks": r.evaluation.awarded_marks,
            "max_marks": r.evaluation.max_marks,
            "percentage": r.evaluation.percentage,
            "summary": r.evaluation.summary_explanation,
            "correctness_status": (
                "correct" if r.evaluation.percentage >= 75.0
                else "partially_correct" if r.evaluation.percentage >= 40.0
                else "incorrect"
            ),
        }
        for r in session.history
    ]

    gap_report = SkillGapAnalyzer.analyze_skill_gap(
        resume_profile=session.resume_profile,
        interview_history=history_records,
        track=session.track,
    )

    return {
        "has_resume": True,
        "resume_id": session.resume_id,
        "candidate_name": session.resume_profile.get("candidate_name"),
        "report": gap_report.model_dump(),
    }


@app.post("/api/interview/start")
def start_interview(data: StartInterviewRequest):
    """
    Starts an adaptive interview session (Python or Full-Stack).
    Backwards compatible with v2.0 and v3.0 client requests.
    """
    try:
        session = session_manager.start_session(data)
        current_display = session.get_current_question_display()

        return {
            "session_id": session.session_id,
            "status": "active",
            "role": session.role,
            "track": session.track,
            "tech_stack": session.tech_stack,
            "question_number": 1,
            "question": current_display.text,
            "text": current_display.text,
            "code_snippet": current_display.code_snippet,
            "topic": current_display.topic,
            "competency": current_display.competency,
            "difficulty": current_display.difficulty.value,
            "question_type": current_display.question_type.value,
            "max_marks": current_display.max_marks,
            "reason": current_display.selection_reason,
            "selection_reason": current_display.selection_reason,
            "resume_id": session.resume_id,
            "max_questions": session.max_questions,
            "difficulty_mode": session.difficulty_mode.value,
            "feedback_mode": session.feedback_mode.value,
            "dynamic_questions": session.dynamic_questions,
            "language": current_display.language,
            "response_type": current_display.response_type,
            "requires_code": current_display.requires_code,
            "starter_code": current_display.starter_code,
            "expected_output": current_display.expected_output,
            "db_schema": current_display.db_schema,
        }
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to start interview: {exc}")


@app.post("/api/interview/{session_id}/answer")
def submit_answer(session_id: str, data: AnswerRequest):
    """
    Submits candidate answer, performs rubric evaluation and isolated code test,
    updates competency tracking, and selects the next question.
    Preserves backwards compatibility with existing voice and text clients.
    """
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(
            status_code=404,
            detail="Interview session not found. Please start a new interview.",
        )

    if session.status != "active":
        raise HTTPException(
            status_code=409,
            detail="This interview has already finished.",
        )

    if not data.answer or not data.answer.strip():
        raise HTTPException(
            status_code=400,
            detail="Answer cannot be empty.",
        )

    try:
        result = session_manager.submit_answer(
            session_id=session_id,
            answer=data.answer,
        )

        # For backwards compatibility with voice_interview.py:
        # voice_interview.py expects:
        # result_data["evaluation"]["competency"]
        # result_data["evaluation"]["assessment"]
        # result_data["evaluation"]["evidence_from_answer"]
        # result_data["evaluation"]["missing_knowledge"]
        # result_data["next_question"] (as str)
        last_record = session.history[-1]
        eval_result = last_record.evaluation

        assessment_label = (
            "strong" if eval_result.percentage >= 75.0
            else "partial" if eval_result.percentage >= 40.0
            else "insufficient"
        )

        compat_evaluation = {
            "competency": last_record.question.competency,
            "assessment": assessment_label,
            "evidence_from_answer": eval_result.demonstrated_concepts or [c.evidence for c in eval_result.criteria_evaluations if c.awarded_marks > 0],
            "missing_knowledge": eval_result.missing_concepts,
            "awarded_marks": eval_result.awarded_marks,
            "max_marks": eval_result.max_marks,
            "percentage": eval_result.percentage,
            "summary": eval_result.summary_explanation,
            "criteria": [
                {
                    "criterion_id": c.criterion_id,
                    "awarded_marks": c.awarded_marks,
                    "max_marks": c.max_marks,
                    "explanation": c.explanation,
                    "evidence": c.evidence,
                }
                for c in eval_result.criteria_evaluations
            ],
            "incorrect_claims": eval_result.incorrect_claims,
            "is_ambiguous": eval_result.is_ambiguous,
            "clarification_question": eval_result.clarification_question,
            "execution_result": eval_result.execution_result,
        }

        next_q_text = ""
        next_competency = ""
        next_q_dict = result.get("next_question")
        if next_q_dict:
            next_q_text = next_q_dict.get("text", "")
            next_competency = next_q_dict.get("competency", "")

        return {
            "session_id": session_id,
            "status": result["status"],
            "question_number": result["question_number"],
            "is_complete": result["is_complete"],
            "questions_remaining": result["questions_remaining"],
            "feedback_mode": result["feedback_mode"],
            "evaluation": compat_evaluation,
            "next_question": next_q_text,
            "next_competency": next_competency,
            "next_question_details": next_q_dict,
            "reason_for_next_question": result["reason_for_next_question"],
        }

    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Error evaluating answer: {exc}")


@app.post("/api/interview/{session_id}/end")
def end_interview_early(session_id: str, data: Optional[EndInterviewRequest] = None):
    """
    Allows ending an interview early or cancelling at any point,
    halting pending timers and generating the final report immediately.
    """
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")

    target_status = data.status if (data and data.status) else "ended_early"
    if target_status not in ("ended_early", "cancelled", "completed"):
        target_status = "ended_early"

    with session.lock:
        session.status = target_status
        session.current_question = None

    report_obj = session_manager.generate_report(session_id)
    return {
        "message": f"Interview {target_status}.",
        "session_id": session_id,
        "status": session.status,
        "report": report_obj.model_dump(),
    }


@app.get("/api/interview/{session_id}")
def get_interview(session_id: str):
    """Returns current state and history of an interview session."""
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")

    curr_display = (
        session.get_current_question_display().model_dump()
        if session.current_question
        else None
    )

    return {
        "session_id": session.session_id,
        "role": session.role,
        "track": session.track,
        "tech_stack": session.tech_stack,
        "status": session.status,
        "question_count": len(session.history),
        "max_questions": session.max_questions,
        "difficulty_mode": session.difficulty_mode.value,
        "feedback_mode": session.feedback_mode.value,
        "current_question": curr_display,
        "history_count": len(session.history),
    }


@app.get("/api/interview/{session_id}/report")
def interview_report(session_id: str):
    """
    Returns the comprehensive interview performance report.
    Includes backward-compatible fields for voice_interview.py
    and normalized score out of 100.
    """
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")

    report_obj = session_manager.generate_report(session_id)

    # Backwards-compatible competency_report structure for voice_interview.py
    compat_competency_report: Dict[str, list] = {}
    for r in session.history:
        name = r.question.competency
        assessment_label = (
            "strong" if r.evaluation.percentage >= 75.0
            else "partial" if r.evaluation.percentage >= 40.0
            else "insufficient"
        )
        compat_competency_report.setdefault(name, []).append({
            "assessment": assessment_label,
            "evidence": r.evaluation.demonstrated_concepts or [c.evidence for c in r.evaluation.criteria_evaluations if c.awarded_marks > 0],
            "missing_knowledge": r.evaluation.missing_concepts,
            "score": f"{r.evaluation.awarded_marks}/{r.evaluation.max_marks}",
        })

    result_dict = report_obj.model_dump()
    result_dict["answers_evaluated"] = len(session.history)
    result_dict["competency_report"] = compat_competency_report
    return result_dict


@app.get("/api/interview/{session_id}/pdf")
def download_interview_pdf(session_id: str):
    """
    Generates and downloads the comprehensive technical assessment report
    as an enterprise-grade multi-page PDF document.
    """
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")

    from backend.resume_analyzer.adapter import get_resume_adapter
    from backend.pdf_generator import InterviewPDFReportGenerator

    report_dict = session_manager.generate_report(session_id).model_dump()
    resume_prof = None
    if session.resume_id:
        resume_prof = get_resume_adapter().get_resume_profile(session.resume_id)

    try:
        pdf_bytes = InterviewPDFReportGenerator.generate_pdf_bytes(
            report_data=report_dict,
            resume_profile=resume_prof,
        )
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="interview_report_{session_id[:8]}.pdf"',
                "Content-Length": str(len(pdf_bytes)),
            },
        )
    except Exception as exc:
        logger.exception("Failed to generate PDF report: %s", exc)
        raise HTTPException(status_code=500, detail=f"Failed to generate PDF report: {exc}")


# =============================================================================
# VOICE & SPEECH AGENT ENDPOINTS
# =============================================================================

@app.get("/api/speech/status")
def speech_status():
    """Returns diagnostics for TTS and STT agents."""
    return speech_bridge.get_status()


@app.post("/api/interview/{session_id}/speak")
async def speak_interview_question(session_id: str, data: Optional[SpeakRequest] = None):
    """
    Speaks the current question (or custom provided text) through local system audio.
    """
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")

    text_to_speak = ""
    if data and data.text and data.text.strip():
        text_to_speak = data.text.strip()
    elif session.current_question:
        text_to_speak = session.current_question.text
    else:
        text_to_speak = "The interview has ended."

    result = await asyncio.to_thread(speech_bridge.speak, text_to_speak)
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error", "TTS playback failed."))

    return {
        "session_id": session_id,
        "spoken_text": text_to_speak,
        "status": "spoken",
    }


@app.get("/api/interview/{session_id}/audio")
async def get_interview_question_audio(session_id: str):
    """
    Returns synthesized audio of the current question for web browser audio playback.
    """
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")

    if not session.current_question:
        raise HTTPException(status_code=400, detail="No active question in this session.")

    text = session.current_question.text
    t_tts = time.perf_counter()
    success, audio_path, err = await asyncio.to_thread(speech_bridge.generate_speech_file, text)
    if not success or not audio_path:
        raise HTTPException(status_code=500, detail=f"Failed to generate speech audio: {err}")

    logger.info(
        "[PERF] TTS audio generation completed in %.3fs for session %s (chars=%d)",
        time.perf_counter() - t_tts, session_id, len(text)
    )

    try:
        with open(audio_path, "rb") as f:
            audio_bytes = f.read()
        return Response(content=audio_bytes, media_type="audio/wav")
    finally:
        try:
            import os
            if os.path.exists(audio_path):
                os.remove(audio_path)
        except Exception:
            pass


@app.post("/api/interview/{session_id}/listen")
async def record_and_transcribe_answer(session_id: str, data: Optional[ListenRequest] = None):
    """
    Records audio from the local hardware microphone using the STT agent
    and returns the transcribed text.
    Does NOT automatically submit or award marks until candidate confirms.
    """
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")

    if session.status != "active":
        raise HTTPException(status_code=409, detail="This interview has already finished.")

    timeout = data.timeout if data else 8.0
    phrase_limit = data.phrase_time_limit if data else 30.0
    lang = data.language if data else "en-US"

    result = await asyncio.to_thread(
        speech_bridge.listen_and_transcribe,
        timeout=timeout,
        phrase_time_limit=phrase_limit,
        language=lang,
    )

    return {
        "session_id": session_id,
        "is_success": result.get("is_success", False),
        "transcript": result.get("text", ""),
        "error_message": result.get("error_message"),
        "diagnostics": result.get("diagnostics"),
    }


@app.post("/api/interview/{session_id}/transcribe_upload")
async def transcribe_uploaded_audio(session_id: str, file: UploadFile = File(...)):
    """
    Transcribes audio recorded in browser and uploaded as a file.
    Uses the exact same standalone STT agent.
    """
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")

    temp_file = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    temp_path = temp_file.name
    try:
        content = await file.read()
        temp_file.write(content)
        temp_file.close()

        t_stt = time.perf_counter()
        result = await asyncio.to_thread(
            speech_bridge.transcribe_audio_file,
            audio_path=temp_path,
            cleanup=True,
        )
        logger.info(
            "[PERF] STT transcription completed in %.3fs for session %s (success=%s, chars=%d)",
            time.perf_counter() - t_stt, session_id, result.get("is_success"), len(result.get("text", ""))
        )

        return {
            "session_id": session_id,
            "is_success": result.get("is_success", False),
            "transcript": result.get("text", ""),
            "error_message": result.get("error_message"),
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Audio transcription failed: {exc}")
    finally:
        try:
            import os
            if os.path.exists(temp_path):
                os.remove(temp_path)
        except Exception:
            pass


@app.get("/api/interview/{session_id}/pdf")
async def download_interview_pdf_report(session_id: str):
    """
    Generates and returns an enterprise-grade multi-page downloadable PDF report
    conforming strictly to Phase 11 requirements using server-side ReportLab.
    """
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")

    report = session_manager.get_final_report(session_id)
    if not report:
        raise HTTPException(status_code=400, detail="Report could not be generated for this session.")

    try:
        from backend.pdf_generator import InterviewPDFReportGenerator
        pdf_bytes = await asyncio.to_thread(InterviewPDFReportGenerator.build_pdf_bytes, report)
        filename = f"Technical_Assessment_Report_{session_id[:8]}.pdf"
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'}
        )
    except Exception as exc:
        logger.error(f"PDF generation failed for session {session_id}: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to generate PDF report: {exc}")


