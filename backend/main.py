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
from fastapi import FastAPI, HTTPException, Request, UploadFile, File, Form, Header, Query
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
    IntegrityEventCreateRequest,
    IntegrityEventUpdateRequest,
    CandidateDecisionUpdateRequest,
    CandidateComparisonRequest,
)

logger = logging.getLogger(__name__)


def verify_session_access(
    session: Any,
    x_candidate_id: Optional[str] = None,
    x_session_token: Optional[str] = None,
    candidate_id: Optional[str] = None,
    token: Optional[str] = None,
) -> None:
    """
    Enforces multi-user security and data isolation.
    Validates that client has ownership of the session if identity headers or tokens are supplied.
    """
    provided_cand = x_candidate_id or candidate_id
    provided_token = x_session_token or token

    if provided_cand and getattr(session, "candidate_id", None) and provided_cand != session.candidate_id:
        logger.warning(
            "[AUTH_DENIED] Candidate ID mismatch for session %s (claimed='%s', owner='%s')",
            session.session_id, provided_cand, session.candidate_id
        )
        raise HTTPException(
            status_code=403,
            detail="Forbidden: You do not have authorization to access this interview session.",
        )

    if provided_token and getattr(session, "session_token", None) and provided_token != session.session_token:
        logger.warning(
            "[AUTH_DENIED] Session token mismatch for session %s",
            session.session_id
        )
        raise HTTPException(
            status_code=403,
            detail="Forbidden: Invalid session authorization token.",
        )


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

from fastapi.responses import HTMLResponse, FileResponse, Response, RedirectResponse

# Static directory path
STATIC_DIR = Path(__file__).parent / "static"
if not STATIC_DIR.exists():
    STATIC_DIR.mkdir(parents=True, exist_ok=True)

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/")
def home(request: Request):
    """
    FastAPI Backend API Root.
    Redirects web browsers to the primary frontend at http://localhost:5173.
    Returns service metadata for programmatic API clients.
    """
    accept = request.headers.get("accept", "")
    if "text/html" in accept:
        return RedirectResponse(url="http://localhost:5173", status_code=307)

    return {
        "message": "Adaptive Python Interviewer API is running",
        "service": "Adaptive Interview Intelligence API",
        "status": "running",
        "version": "3.1.0",
        "model": default_llm_client.model_name,
        "tracks": ["python", "fullstack"],
        "frontend_url": "http://localhost:5173",
        "docs": "/docs",
        "health": "/api/health",
    }


@app.get("/api/health")
def health():
    """Health check for API and AI service."""
    ai_status = default_llm_client.check_health()
    provider = ai_status.get("provider", getattr(default_llm_client, "provider", "ollama"))
    is_available = bool(ai_status.get("available", False) and ai_status.get("has_required_model", False))
    connection_status = "connected" if is_available else "disconnected"

    response = {
        "api": "running",
        "provider": provider,
        "status": connection_status,
        "ollama": ai_status.get("ollama", connection_status if provider == "ollama" else "disconnected"),
        "required_model_available": bool(ai_status.get("has_required_model", False)),
        "models": ai_status.get("models", []),
    }
    if "gemini" in ai_status:
        response["gemini"] = ai_status["gemini"]
    elif provider == "gemini":
        response["gemini"] = connection_status
    if "installed_ollama_models" in ai_status:
        response["installed_ollama_models"] = ai_status["installed_ollama_models"]
    if "error" in ai_status and not is_available:
        response["error"] = ai_status["error"]
    return response


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
    from backend.role_validator import RoleValidator

    raw_user_role = (target_role or job_title or "").strip()
    if raw_user_role:
        is_valid, norm_role, role_err = RoleValidator.validate_role(raw_user_role, is_required=True)
        if not is_valid:
            logger.warning("[ROLE_REJECT] Rejected invalid role input '%s': %s", raw_user_role, role_err)
            raise HTTPException(status_code=422, detail=role_err)
        effective_role = norm_role
    else:
        effective_role = None

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

    final_role = effective_role or result.get("target_role") or "Software Engineer"

    # Safely initiate blueprint & Question 1 pre-warming in background after resume analysis
    try:
        from backend.session_manager import prewarm_first_question
        prewarm_first_question(
            resume_id=result.get("resume_id"),
            resume_profile=result,
            target_role=final_role,
            track=result.get("routed_track") or "python",
            difficulty_mode="adaptive",
            tech_stack=result.get("recommended_tech_stack"),
            max_questions=5,
        )
    except Exception as exc:
        logger.warning("[PREWARM_TRIGGER_FAILED] %s", exc)

    skills_list = result.get("skills") or result.get("extracted_skills") or []
    exp_years = result.get("total_experience_years") or result.get("experience_years") or 0.0
    routed_track = result.get("routed_track") or "python"

    return {
        **result,
        "skills": skills_list,
        "extracted_skills": skills_list,
        "experience_years": exp_years,
        "total_experience_years": exp_years,
        "routed_track": routed_track,
        "candidate_name": result.get("candidate_name") or "Technical Candidate",
        "target_role": final_role,
        "profile": result,
    }


@app.get("/api/role/validate")
def validate_role_api(role: str = Query(..., min_length=1)):
    """
    Validates job role input. Returns is_valid, normalized role, and actionable error message.
    Rejects meaningless, random, or arbitrary text (e.g. asdfghjkl, qwerty, hello, 123456).
    """
    from backend.role_validator import RoleValidator
    is_valid, normalized, err = RoleValidator.validate_role(role, is_required=True)
    return {
        "is_valid": is_valid,
        "role": normalized if is_valid else None,
        "normalized_role": normalized if is_valid else None,
        "error_message": err,
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
    try:
        from backend.session_manager import prewarm_first_question
        diff_str = data.difficulty_mode.value if hasattr(data.difficulty_mode, "value") else str(data.difficulty_mode)
        prewarm_first_question(
            resume_id=data.resume_id,
            resume_profile=profile,
            target_role=data.target_role or profile.get("target_role") or "Software Engineer",
            track=target_track,
            difficulty_mode=diff_str,
            tech_stack=data.tech_stack or profile.get("recommended_tech_stack"),
            max_questions=data.max_questions or 5,
        )
    except Exception as exc:
        logger.warning("[PREWARM_TRIGGER_FAILED] %s", exc)
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

    if data.max_questions < 5 or data.max_questions > 10:
        raise HTTPException(
            status_code=422,
            detail="Configured interview length must be strictly between 5 and 10 questions inclusive."
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

    # Pre-warm Question 1 based on prepared configuration before interview begins
    try:
        from backend.session_manager import prewarm_first_question
        prewarm_first_question(
            resume_id=data.resume_id,
            resume_profile=profile,
            target_role=target_role,
            track=track,
            difficulty_mode=diff_mode,
            tech_stack=tech_stack,
            max_questions=data.max_questions,
        )
    except Exception as exc:
        logger.warning("[PREWARM_TRIGGER_FAILED] %s", exc)

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


@app.get("/api/interview/{session_id}/blueprint")
def get_interview_blueprint(session_id: str):
    """Returns candidate's active interview blueprint if available."""
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Interview session not found.")
    blueprint = getattr(session, "blueprint", None)
    if not blueprint:
        from backend.question_agent import default_question_agent
        diff_str = session.difficulty_mode.value if hasattr(session.difficulty_mode, "value") else str(session.difficulty_mode)
        blueprint = default_question_agent.create_blueprint(
            resume_profile=session.resume_profile,
            target_role=session.role,
            interview_mode="mock" if session.dynamic_questions else "predefined",
            difficulty_mode=diff_str,
            target_track=session.track,
            tech_stack=session.tech_stack,
            max_questions=session.max_questions,
            candidate_id=session.candidate_id,
        )
        session.blueprint = blueprint
    return blueprint.model_dump()


@app.get("/api/question_agent/stats")
def get_question_agent_stats():
    """Returns Question Catalog statistics and generation latency metrics."""
    from backend.question_agent import default_question_agent
    return {
        "catalog_size": default_question_agent.catalog.get_total_count(),
        "total_generations": default_question_agent.generator.total_generations,
        "fallback_count": default_question_agent.generator.fallback_count,
        "last_latency_ms": default_question_agent.generator.last_latency_ms,
        "status": "active",
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
            "candidate_id": session.candidate_id,
            "session_token": session.session_token,
            "status": "active",
            "role": session.role,
            "track": session.track,
            "tech_stack": session.tech_stack,
            "question_number": 1,
            "question_id": current_display.id,
            "question": current_display.text,
            "text": current_display.text,
            "question_details": {
                "question_id": current_display.id,
                "id": current_display.id,
                "question_number": 1,
                "text": current_display.text,
                "code_snippet": current_display.code_snippet,
                "topic": current_display.topic,
                "competency": current_display.competency,
                "difficulty": current_display.difficulty.value,
                "question_type": current_display.question_type.value,
                "type": current_display.question_type.value,
                "max_marks": current_display.max_marks,
                "selection_reason": current_display.selection_reason,
            },
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
def submit_answer(
    session_id: str,
    data: AnswerRequest,
    x_candidate_id: Optional[str] = Header(None),
    x_session_token: Optional[str] = Header(None),
):
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
    verify_session_access(session, x_candidate_id=x_candidate_id, x_session_token=x_session_token)

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
            question_id=getattr(data, "question_id", None),
            question_number=getattr(data, "question_number", None),
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
            "marks_awarded": eval_result.awarded_marks,
            "max_marks": eval_result.max_marks,
            "percentage": eval_result.percentage,
            "feedback": eval_result.summary_explanation,
            "misconceptions": eval_result.missing_concepts,
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
def end_interview_early(
    session_id: str,
    data: Optional[EndInterviewRequest] = None,
    x_candidate_id: Optional[str] = Header(None),
    x_session_token: Optional[str] = Header(None),
):
    """
    Allows ending an interview early or cancelling at any point,
    halting pending timers and generating the final report immediately.
    """
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")
    verify_session_access(session, x_candidate_id=x_candidate_id, x_session_token=x_session_token)

    target_status = data.status if (data and data.status) else "ended_early"
    if target_status not in ("ended_early", "cancelled", "completed"):
        target_status = "ended_early"

    with session.lock:
        session.status = target_status
        session.is_cancelled = True
        session.pregenerated_question = None
        session.current_question = None

    session_manager.persistence.save_session(session)

    report_obj = session_manager.generate_report(session_id)
    return {
        "message": f"Interview {target_status}.",
        "session_id": session_id,
        "status": session.status,
        "report": report_obj.model_dump(),
    }


@app.get("/api/interview/{session_id}")
def get_interview(
    session_id: str,
    x_candidate_id: Optional[str] = Header(None),
    x_session_token: Optional[str] = Header(None),
):
    """Returns current state and history of an interview session."""
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")
    verify_session_access(session, x_candidate_id=x_candidate_id, x_session_token=x_session_token)

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
        "question_number": len(session.history) + 1,
        "max_questions": session.max_questions,
        "difficulty_mode": session.difficulty_mode.value,
        "feedback_mode": session.feedback_mode.value,
        "current_question": curr_display,
        "history_count": len(session.history),
    }


@app.get("/api/interview/{session_id}/status")
def get_interview_status(
    session_id: str,
    x_candidate_id: Optional[str] = Header(None),
    x_session_token: Optional[str] = Header(None),
):
    """Returns question progress and status for an active interview."""
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Interview session not found.")
    return {
        "session_id": session.session_id,
        "status": session.status,
        "question_number": len(session.history) + 1,
        "max_questions": session.max_questions,
        "questions_answered": len(session.history),
    }


@app.get("/api/interview/{session_id}/report")
def interview_report(
    session_id: str,
    x_candidate_id: Optional[str] = Header(None),
    x_session_token: Optional[str] = Header(None),
):
    """
    Returns the comprehensive interview performance report.
    Includes backward-compatible fields for voice_interview.py
    and normalized score out of 100.
    """
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")
    verify_session_access(session, x_candidate_id=x_candidate_id, x_session_token=x_session_token)

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
def download_interview_pdf(
    session_id: str,
    x_candidate_id: Optional[str] = Header(None),
    x_session_token: Optional[str] = Header(None),
    candidate_id: Optional[str] = Query(None),
    token: Optional[str] = Query(None),
):
    """
    Generates and downloads the comprehensive technical assessment report
    as an enterprise-grade multi-page PDF document.
    """
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")
    verify_session_access(
        session,
        x_candidate_id=x_candidate_id,
        x_session_token=x_session_token,
        candidate_id=candidate_id,
        token=token,
    )

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


# =========================================================================
# MODULE 3: INTERVIEW INTEGRITY TELEMETRY & AUDIT APIS
# =========================================================================

@app.post("/api/interview/{session_id}/integrity_event")
async def record_integrity_event(
    session_id: str,
    event_data: IntegrityEventCreateRequest,
    x_candidate_id: Optional[str] = Header(None),
):
    """
    Records an observed sensor or browser telemetry event (window blur, focus transition, audio fluctuation).
    Entries are non-accusatory raw sensory logs meant for human recruiter context.
    """
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")

    record = session_manager.log_integrity_event(
        session_id=session_id,
        event_data=event_data,
        candidate_id=x_candidate_id or getattr(session, "candidate_id", None),
    )
    return {
        "status": "success",
        "event": record.model_dump(),
    }


@app.get("/api/interview/{session_id}/integrity_events")
async def list_integrity_events(session_id: str):
    """
    Retrieves chronological sensor and browser telemetry stream for an interview session.
    """
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")

    events = session_manager.get_integrity_events(session_id)
    return {
        "session_id": session_id,
        "count": len(events),
        "events": [e.model_dump() for e in events],
    }


@app.patch("/api/interview/{session_id}/integrity_event/{event_id}")
async def update_integrity_event_triage(
    session_id: str,
    event_id: str,
    update_data: IntegrityEventUpdateRequest,
):
    """
    Allows recruiter to annotate or resolve an integrity observation
    (e.g., 'verified_benign', 'verified_technical', 'requires_followup').
    """
    success = session_manager.update_integrity_event_status(
        event_id=event_id,
        status=update_data.status,
        notes=update_data.notes,
    )
    if not success:
        raise HTTPException(status_code=404, detail="Integrity event not found or update failed.")

    return {
        "status": "updated",
        "event_id": event_id,
        "recruiter_status": update_data.status,
    }


@app.get("/api/interview/{session_id}/integrity_summary")
async def get_integrity_summary(session_id: str):
    """
    Aggregates session sensor events into a recruiter-visible integrity summary with ethical protocols.
    """
    summary = session_manager.get_integrity_summary(session_id)
    return summary.model_dump()


# =========================================================================
# MODULE 5: CANDIDATE DECISION INTELLIGENCE & RECRUITER APIS
# =========================================================================

@app.get("/api/recruiter/candidates")
async def list_recruiter_candidates(role: Optional[str] = Query(None)):
    """
    Returns candidate decision records for recruiter pipeline dashboard.
    If database records exist, returns them; also includes active sessions.
    """
    records = session_manager.list_candidate_decisions(target_role=role)
    # Also discover active sessions not yet finalized
    active_ids = session_manager.persistence.list_sessions()
    existing_sids = {r.session_id for r in records}

    candidates = [r.model_dump() for r in records]
    for sid in active_ids[:20]:
        if sid not in existing_sids:
            try:
                dec = session_manager.get_candidate_decision(sid)
                if dec:
                    candidates.append(dec.model_dump())
            except Exception:
                pass

    return {
        "count": len(candidates),
        "candidates": candidates,
    }


@app.get("/api/recruiter/candidate/{session_id}")
async def get_recruiter_candidate_details(session_id: str):
    """
    Retrieves full candidate evaluation, decision recommendation, and rubric breakdown.
    """
    decision = session_manager.get_candidate_decision(session_id)
    if not decision:
        raise HTTPException(status_code=404, detail="Candidate assessment record not found.")

    report = None
    try:
        report = session_manager.generate_report(session_id).model_dump()
    except Exception:
        pass

    return {
        "decision": decision.model_dump(),
        "report": report,
    }


@app.patch("/api/recruiter/decision/{session_id}")
async def update_recruiter_decision(
    session_id: str,
    update: CandidateDecisionUpdateRequest,
):
    """
    Allows human recruiter to record an outcome override (e.g., 'proceed_to_human_review', 'request_follow_up')
    along with contextual hiring panel notes.
    """
    success = session_manager.update_candidate_decision(
        session_id=session_id,
        outcome=update.outcome,
        notes=update.notes,
    )
    if not success:
        raise HTTPException(status_code=404, detail="Candidate decision record not found.")

    return {
        "status": "updated",
        "session_id": session_id,
        "outcome": update.outcome,
        "notes": update.notes,
    }


@app.post("/api/recruiter/compare")
async def compare_candidates(request: CandidateComparisonRequest):
    """
    Provides explainable side-by-side comparison across multiple candidate assessments
    under the same role family, normalizing scores and mapping competency matrices.
    """
    if not request.session_ids:
        raise HTTPException(status_code=400, detail="session_ids list must not be empty.")

    result = session_manager.compare_candidates(request.session_ids)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])

    return result





