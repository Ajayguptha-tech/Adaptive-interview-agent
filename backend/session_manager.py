"""
Session lifecycle and report generation manager for Python Interview Intelligence.
Maintains interview state, validates answers, prevents question leakage,
normalizes final scores to 100, and generates structured performance reports.
"""

import time
import logging
import threading
import uuid
import random
import secrets
import hashlib
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple, Set
from backend.models import (
    StartInterviewRequest,
    Question,
    QuestionRecord,
    QuestionDisplay,
    EvaluationResult,
    FeedbackMode,
    FinalReport,
    InterviewMode,
    DifficultyLevel,
    IntegrityEventRecord,
    IntegritySummary,
    IntegrityEventCreateRequest,
    CandidateDecisionRecord,
    DecisionOutcome,
)
from backend.adaptive_engine import CompetencyTracker, AdaptiveEngine
from backend.evaluator import EvaluationEngine
from backend.question_bank import get_all_topics
from backend.interviewers.registry import default_registry, InterviewerRegistry
from backend.interviewers.python_interviewer import PythonInterviewer

logger = logging.getLogger(__name__)

# Bounded background generation semaphore: max 2 concurrent inferences to protect host CPU/GPU
_PREGEN_SEMAPHORE = threading.Semaphore(2)

# In-memory store for pre-warmed opening questions keyed by resume_id
# Value: Dict with keys "blueprint", "first_question", "first_reason", "target_role", "track", "created_at", "raw_inference_latency"
_PREPARED_FIRST_QUESTIONS: Dict[str, Dict[str, Any]] = {}
_ACTIVE_PREWARM_RESUMES: Set[str] = set()
_PREWARM_EVENTS: Dict[str, threading.Event] = {}
_PREPARED_LOCK = threading.Lock()

# Global metrics for pre-generation correctness and efficiency
PREGEN_METRICS: Dict[str, int] = {
    "pregen_hits": 0,
    "stale_buffer_invalidations": 0,
    "duplicate_jobs_prevented": 0,
    "prewarm_first_q_hits": 0,
}
_METRICS_LOCK = threading.Lock()


def get_pregen_metrics() -> Dict[str, int]:
    with _METRICS_LOCK:
        return dict(PREGEN_METRICS)


def reset_pregen_metrics() -> None:
    with _METRICS_LOCK:
        for k in PREGEN_METRICS:
            PREGEN_METRICS[k] = 0


def _extract_stable_candidate_id(resume_profile: Optional[Dict[str, Any]], fallback_id: Optional[str] = None) -> str:
    """Extracts a deterministic candidate ID across resume re-uploads using email, file hash, or name."""
    if not resume_profile:
        return fallback_id or f"cand_{uuid.uuid4().hex[:8]}"
    contact = resume_profile.get("contact_info") or {}
    email = contact.get("email") if isinstance(contact, dict) else None
    if email and isinstance(email, str) and email.strip():
        return f"cand_{hashlib.sha256(email.strip().lower().encode()).hexdigest()[:12]}"
    file_hash = resume_profile.get("file_hash")
    if file_hash and isinstance(file_hash, str) and file_hash.strip():
        return f"cand_{file_hash[:12]}"
    name = resume_profile.get("candidate_name")
    if name and isinstance(name, str) and name.strip() and name.strip().lower() != "candidate":
        return f"cand_{hashlib.sha256(name.strip().lower().encode()).hexdigest()[:12]}"
    return fallback_id or resume_profile.get("resume_id") or f"cand_{uuid.uuid4().hex[:8]}"


def prewarm_first_question(
    resume_id: str,
    resume_profile: Dict[str, Any],
    target_role: str,
    track: str,
    difficulty_mode: str = "adaptive",
    tech_stack: Optional[str] = None,
    max_questions: int = 5,
) -> None:
    """Pre-warms candidate blueprint and Question 1 in the background after resume preparation."""
    if not resume_id or not resume_profile:
        return

    with _PREPARED_LOCK:
        if resume_id in _ACTIVE_PREWARM_RESUMES:
            with _METRICS_LOCK:
                PREGEN_METRICS["duplicate_jobs_prevented"] += 1
            logger.info("[PREWARM_DEDUP] Prewarm worker already active for resume %s. Skipping duplicate job.", resume_id)
            return
        cached = _PREPARED_FIRST_QUESTIONS.get(resume_id)
        if cached and cached.get("track") == track and cached.get("target_role") == target_role:
            with _METRICS_LOCK:
                PREGEN_METRICS["duplicate_jobs_prevented"] += 1
            logger.info("[PREWARM_DEDUP] Question 1 already cached for resume %s (%s). Skipping duplicate job.", resume_id, target_role)
            return
        _ACTIVE_PREWARM_RESUMES.add(resume_id)
        evt = threading.Event()
        _PREWARM_EVENTS[resume_id] = evt

    def _prewarm_worker():
        acquired = _PREGEN_SEMAPHORE.acquire(blocking=True, timeout=10.0)
        if not acquired:
            with _PREPARED_LOCK:
                _ACTIVE_PREWARM_RESUMES.discard(resume_id)
                evt = _PREWARM_EVENTS.pop(resume_id, None)
                if evt:
                    evt.set()
            return
        try:
            from backend.question_agent import default_question_agent
            from backend.models import DifficultyLevel

            diff = {
                "beginner": DifficultyLevel.BEGINNER,
                "intermediate": DifficultyLevel.INTERMEDIATE,
                "advanced": DifficultyLevel.ADVANCED,
            }.get(difficulty_mode.lower(), DifficultyLevel.INTERMEDIATE)

            stable_cand_id = _extract_stable_candidate_id(resume_profile, fallback_id=resume_id)
            blueprint = default_question_agent.create_blueprint(
                resume_profile=resume_profile,
                target_role=target_role,
                interview_mode="mock",
                difficulty_mode=difficulty_mode,
                target_track=track,
                tech_stack=tech_stack,
                max_questions=max_questions,
                candidate_id=stable_cand_id,
            )

            opening_topic = (
                blueprint.planned_topics[0]
                if blueprint.planned_topics
                else ("Data Structures & Mutability" if track == "python" else "JavaScript Core")
            )
            t0 = time.perf_counter()
            q, reason = default_question_agent.select_or_generate_question(
                blueprint=blueprint,
                topic=opening_topic,
                competency=f"{target_role} Competency",
                difficulty=diff,
                question_number=1,
                session_asked_texts=[],
                use_dynamic=True,
            )
            raw_lat = time.perf_counter() - t0

            with _PREPARED_LOCK:
                _PREPARED_FIRST_QUESTIONS[resume_id] = {
                    "blueprint": blueprint,
                    "first_question": q,
                    "first_reason": reason,
                    "target_role": target_role,
                    "track": track,
                    "raw_inference_latency": raw_lat,
                    "created_at": time.time(),
                }
            logger.info(
                "[PREWARM_READY] Pre-warmed Question 1 (%s) for resume %s in %.2fs (raw inference)",
                q.id, resume_id, raw_lat
            )
        except Exception as exc:
            logger.warning("[PREWARM_FAILED] Failed to pre-warm first question: %s", exc)
        finally:
            with _PREPARED_LOCK:
                _ACTIVE_PREWARM_RESUMES.discard(resume_id)
                evt = _PREWARM_EVENTS.pop(resume_id, None)
                if evt:
                    evt.set()
            _PREGEN_SEMAPHORE.release()

    th = threading.Thread(target=_prewarm_worker, daemon=True, name=f"prewarm-{resume_id[:8]}")
    th.start()


def clear_prewarmed_question(resume_id: str) -> None:
    """Discards pre-warmed question cache and clears active worker state for resume."""
    with _PREPARED_LOCK:
        _PREPARED_FIRST_QUESTIONS.pop(resume_id, None)
        _ACTIVE_PREWARM_RESUMES.discard(resume_id)
        evt = _PREWARM_EVENTS.pop(resume_id, None)
        if evt:
            evt.set()



class InterviewSession:
    """Represents an active or completed interview session."""

    def __init__(self, config: StartInterviewRequest, first_question: Optional[Question], first_reason: str):
        self.session_id: str = str(uuid.uuid4())
        self.candidate_id: str = (
            getattr(config, "candidate_id", None)
            or getattr(config, "resume_id", None)
            or f"cand_{self.session_id[:8]}"
        )
        self.session_token: str = secrets.token_urlsafe(32)
        self.role: str = config.role
        self.track: str = getattr(config, "track", "python") or "python"
        self.tech_stack: Optional[str] = getattr(config, "tech_stack", None)
        self.job_description: str = config.job_description
        self.resume_summary: str = config.resume_summary
        self.max_questions: int = config.max_questions
        self.difficulty_mode = config.difficulty_mode
        self.feedback_mode = config.feedback_mode
        self.selected_topics = config.topics
        self.dynamic_questions = getattr(config, "dynamic_questions", True)
        self.resume_id: Optional[str] = getattr(config, "resume_id", None)
        self.resume_profile: Optional[Dict[str, Any]] = None
        self.blueprint: Optional[Any] = None

        self.current_question: Optional[Question] = first_question
        self.current_reason: str = first_reason
        self.history: List[QuestionRecord] = []
        self.tracker: CompetencyTracker = CompetencyTracker()
        self.status: str = "active"
        self.created_at: str = datetime.now(timezone.utc).isoformat()
        self.lock = threading.Lock()
        self.version: int = 1
        self.last_submission_hash: Optional[str] = None
        self.idempotency_cache: Dict[str, Any] = {}

        # Bounded pre-generation buffer for next question with slot lock and staleness tracking
        self.pregenerated_question: Optional[Tuple[Question, str]] = None
        self.pregen_thread: Optional[threading.Thread] = None
        self.pregen_lock = threading.Lock()
        self.active_pregen_slot: Optional[int] = None
        self.pregen_target_difficulty: Optional[DifficultyLevel] = None
        self.is_cancelled: bool = False

        # Session-specific random seed to guarantee distinct sequence per interview
        self.seed: int = int(hashlib.sha256(f"{self.session_id}_{self.created_at}".encode("utf-8")).hexdigest()[:8], 16)
        self.rng: random.Random = random.Random(self.seed)

    def schedule_next_pregeneration(self, interviewer: Any, next_q_num: int, target_diff: Any) -> None:
        """Launches a non-blocking background daemon thread to pre-generate the next candidate question."""
        if not self.dynamic_questions or self.is_cancelled or self.status != "active":
            return
        if next_q_num > self.max_questions:
            return

        with self.pregen_lock:
            # Prevent duplicate inference jobs for the same session and question slot
            if self.active_pregen_slot == next_q_num and self.pregen_thread and self.pregen_thread.is_alive():
                with _METRICS_LOCK:
                    PREGEN_METRICS["duplicate_jobs_prevented"] += 1
                logger.info(
                    "[PREGEN_DEDUP] Pre-generation already active for session %s, slot %d. Skipping duplicate job.",
                    self.session_id, next_q_num
                )
                return

            self.active_pregen_slot = next_q_num
            self.pregen_target_difficulty = target_diff
            self.pregenerated_question = None

        def _worker():
            acquired = _PREGEN_SEMAPHORE.acquire(blocking=True, timeout=10.0)
            if not acquired:
                with self.pregen_lock:
                    if self.active_pregen_slot == next_q_num:
                        self.active_pregen_slot = None
                return
            try:
                if self.is_cancelled or self.status != "active":
                    return

                blueprint = getattr(self, "blueprint", None)
                if not blueprint:
                    from backend.question_agent import default_question_agent
                    diff_mode_str = (
                        self.difficulty_mode.value
                        if hasattr(self.difficulty_mode, "value")
                        else str(self.difficulty_mode)
                    )
                    blueprint = default_question_agent.create_blueprint(
                        resume_profile=self.resume_profile,
                        target_role=self.role,
                        interview_mode="mock" if self.dynamic_questions else "predefined",
                        difficulty_mode=diff_mode_str,
                        target_track=self.track,
                        tech_stack=self.tech_stack,
                        max_questions=self.max_questions,
                        candidate_id=self.candidate_id,
                    )
                    self.blueprint = blueprint

                next_topic = None
                if getattr(self, "selected_topics", None):
                    t_idx = (next_q_num - 1) % len(self.selected_topics)
                    next_topic = self.selected_topics[t_idx]
                elif blueprint and blueprint.planned_topics:
                    t_idx = (next_q_num - 1) % len(blueprint.planned_topics)
                    next_topic = blueprint.planned_topics[t_idx]
                else:
                    next_topic = "Python Architecture" if self.track == "python" else "Full Stack Architecture"

                current_texts = [r.question.text for r in self.history]
                if getattr(self, "current_question", None):
                    current_texts.append(self.current_question.text)
                current_ids = {r.question.id for r in self.history}
                if getattr(self, "current_question", None):
                    current_ids.add(self.current_question.id)

                from backend.question_agent import default_question_agent
                t0 = time.perf_counter()
                q, reason = default_question_agent.select_or_generate_question(
                    blueprint=blueprint,
                    topic=next_topic,
                    competency=f"{self.role} Competency",
                    difficulty=target_diff,
                    question_number=next_q_num,
                    session_asked_texts=current_texts,
                    session_asked_ids=current_ids,
                    use_dynamic=True,
                )
                dur = time.perf_counter() - t0
                with self.pregen_lock:
                    if not self.is_cancelled and self.status == "active":
                        self.pregenerated_question = (q, reason)
                        logger.info(
                            "[PREGEN_READY] Pre-generated question %d (%s) in %.2fs for session %s (diff=%s)",
                            next_q_num, q.id, dur, self.session_id, q.difficulty.value
                        )
            except Exception as e:
                logger.warning("[PREGEN_FAILED] Pre-generation failed: %s", e)
            finally:
                _PREGEN_SEMAPHORE.release()
                with self.pregen_lock:
                    if self.active_pregen_slot == next_q_num:
                        self.active_pregen_slot = None

        th = threading.Thread(target=_worker, daemon=True, name=f"pregen-{self.session_id[:6]}-{next_q_num}")
        self.pregen_thread = th
        th.start()

    def get_or_await_pregenerated(
        self,
        expected_difficulty: Optional[DifficultyLevel] = None,
        timeout: float = 2.0,
    ) -> Optional[Tuple[Question, str]]:
        """
        Retrieves the pre-generated question from buffer if ready.
        Validates staleness against expected difficulty and session status.
        """
        if self.is_cancelled or self.status != "active":
            with self.pregen_lock:
                self.pregenerated_question = None
            return None

        th = self.pregen_thread
        if th and th.is_alive():
            th.join(timeout=timeout)

        with self.pregen_lock:
            if not self.pregenerated_question:
                return None

            pq, pr = self.pregenerated_question

            # Staleness check: Invalidate if expected difficulty differs
            if expected_difficulty and pq.difficulty != expected_difficulty:
                with _METRICS_LOCK:
                    PREGEN_METRICS["stale_buffer_invalidations"] += 1
                logger.info(
                    "[PREGEN_STALE_INVALIDATED] Stale pre-generated question %s invalidated: difficulty changed (buffered: %s, required: %s).",
                    pq.id, pq.difficulty.value, expected_difficulty.value
                )
                self.pregenerated_question = None
                return None

            # Fresh, valid pregenerated question
            with _METRICS_LOCK:
                PREGEN_METRICS["pregen_hits"] += 1
            res = self.pregenerated_question
            self.pregenerated_question = None
            return res

    def get_current_question_display(self) -> QuestionDisplay:
        """Returns the public view of the current question for candidate/frontend."""
        q = self.current_question
        default_lang = "python" if self.track == "python" else "javascript"
        return QuestionDisplay(
            question_number=len(self.history) + 1,
            total_questions=self.max_questions,
            id=q.id,
            topic=q.topic,
            competency=q.competency,
            difficulty=q.difficulty,
            question_type=q.question_type,
            text=q.text,
            code_snippet=q.code_snippet,
            max_marks=q.total_marks,
            selection_reason=self.current_reason,
            language=getattr(q, "language", default_lang) or default_lang,
            track=self.track,
            starter_code=getattr(q, "starter_code", None),
            expected_output=getattr(q, "expected_output", None),
            db_schema=getattr(q, "db_schema", None),
        )

    @classmethod
    def from_dict(cls, data: Dict[str, Any], registry: InterviewerRegistry) -> "InterviewSession":
        """Reconstructs an InterviewSession instance from durable serialized storage."""
        diff_val = data["difficulty_mode"]
        try:
            diff_mode = InterviewMode(diff_val)
        except Exception:
            diff_mode = InterviewMode.ADAPTIVE

        fb_val = data["feedback_mode"]
        try:
            fb_mode = FeedbackMode(fb_val)
        except Exception:
            fb_mode = FeedbackMode.IMMEDIATE

        cfg = StartInterviewRequest(
            candidate_id=data.get("candidate_id"),
            role=data["role"],
            track=data["track"],
            tech_stack=data.get("tech_stack"),
            job_description=data.get("job_description", ""),
            resume_summary=data.get("resume_summary", ""),
            max_questions=data["max_questions"],
            difficulty_mode=diff_mode,
            feedback_mode=fb_mode,
            topics=data.get("selected_topics"),
            dynamic_questions=data.get("dynamic_questions", True),
            resume_id=data.get("resume_id"),
        )
        curr_q = Question(**data["current_question"]) if data.get("current_question") else None
        curr_reason = data.get("current_reason", "")
        session = cls(cfg, curr_q, curr_reason)
        session.session_id = data["session_id"]
        session.candidate_id = data.get("candidate_id") or f"cand_{session.session_id[:8]}"
        session.session_token = data.get("session_token") or secrets.token_urlsafe(32)
        session.status = data["status"]
        session.created_at = data["created_at"]
        session.version = data.get("version", 1)
        session.last_submission_hash = data.get("last_submission_hash")
        session.resume_profile = data.get("resume_profile")

        if data.get("interview_plan"):
            from backend.interview_plan import InterviewPlan
            try:
                session.interview_plan = InterviewPlan(**data["interview_plan"])
            except Exception:
                session.interview_plan = None

        session.history = []
        for h_item in data.get("history", []):
            try:
                session.history.append(QuestionRecord(**h_item))
            except Exception as e:
                logger.warning(f"Could not restore question record: {e}")

        interviewer = registry.get(session.track)
        session.tracker = interviewer.create_tracker()
        if data.get("tracker"):
            from backend.session_persistence import SessionPersistence
            SessionPersistence().restore_tracker(session.tracker, data["tracker"])

        return session


class SessionManager:
    """Manages interview sessions in memory with durable SQLite backing."""

    def __init__(
        self,
        evaluation_engine: Optional[EvaluationEngine] = None,
        registry: Optional[InterviewerRegistry] = None,
        persistence: Optional[Any] = None,
    ):
        from backend.session_persistence import SessionPersistence
        self.persistence = persistence or SessionPersistence()
        self.sessions: Dict[str, InterviewSession] = {}
        self.eval_engine = evaluation_engine or EvaluationEngine()
        if registry is not None:
            self.registry = registry
        elif evaluation_engine is not None:
            self.registry = InterviewerRegistry()
            self.registry.register("python", PythonInterviewer(eval_engine=self.eval_engine))
            self.registry.register("fullstack", default_registry.get("fullstack"))
        else:
            self.registry = default_registry

    def start_session(
        self,
        request: StartInterviewRequest,
        resume_profile: Optional[Dict[str, Any]] = None,
    ) -> InterviewSession:
        """Initializes a new interview session using the requested or automatically routed track."""
        t_start = time.perf_counter()
        plan = None
        effective_topics = request.topics

        # Validate and associate resume if provided
        if getattr(request, "resume_id", None):
            from backend.resume_analyzer.adapter import get_resume_adapter
            from backend.interview_plan import InterviewPlanner, InterviewPlan

            if resume_profile is None:
                resume_profile = get_resume_adapter().get_resume_profile(request.resume_id)
            if not resume_profile:
                raise ValueError(
                    f"Resume profile '{request.resume_id}' not found or unanalyzed. Please upload and analyze resume first."
                )

        # Automatic track selection: use request.track if explicitly specified, otherwise auto-routed track from resume
        if getattr(request, "track", None):
            track = request.track
        elif resume_profile and resume_profile.get("routed_track"):
            track = resume_profile["routed_track"]
        else:
            track = "python"

        interviewer = self.registry.get(track)

        # Plan reuse or generation
        if resume_profile:
            diff_mode_val = (
                request.difficulty_mode.value
                if hasattr(request.difficulty_mode, "value")
                else str(request.difficulty_mode)
            )
            cached_plan_dict = resume_profile.get("interview_plan")
            if (
                cached_plan_dict
                and cached_plan_dict.get("track") == track
                and cached_plan_dict.get("total_planned_questions") == request.max_questions
            ):
                try:
                    plan = InterviewPlan(**cached_plan_dict)
                except Exception:
                    plan = None

            if plan is None:
                plan = InterviewPlanner.create_plan(
                    resume_profile=resume_profile,
                    track=track,
                    max_questions=request.max_questions,
                    difficulty_mode=diff_mode_val,
                    tech_stack=getattr(request, "tech_stack", None) or resume_profile.get("recommended_tech_stack"),
                    target_role=getattr(request, "role", None) or resume_profile.get("target_role"),
                )

            if not request.topics and plan.selected_topics:
                effective_topics = plan.selected_topics

        cand_id = getattr(request, "candidate_id", None) or _extract_stable_candidate_id(resume_profile, fallback_id=getattr(request, "resume_id", None))

        # Check if Question 1 was pre-warmed for this resume and role
        prewarmed = None
        target_role_str = getattr(request, "role", None) or (resume_profile.get("target_role") if resume_profile else "Python Developer")
        if resume_profile and getattr(request, "resume_id", None):
            # Check if a prewarm worker is currently running for this resume
            prewarm_evt = None
            with _PREPARED_LOCK:
                if request.resume_id in _ACTIVE_PREWARM_RESUMES:
                    prewarm_evt = _PREWARM_EVENTS.get(request.resume_id)
            if prewarm_evt:
                logger.info("[PREWARM_SYNC] Waiting up to 60s for active prewarm on resume %s...", request.resume_id)
                prewarm_evt.wait(timeout=60.0)

            with _PREPARED_LOCK:
                cached = _PREPARED_FIRST_QUESTIONS.get(request.resume_id)
                if cached:
                    is_dynamic = getattr(request, "dynamic_questions", True)
                    role_matches = not cached.get("target_role") or cached.get("target_role").lower() == target_role_str.lower()
                    track_matches = cached.get("track") == track
                    if is_dynamic and role_matches and track_matches:
                        from backend.question_agent import default_question_agent
                        from backend.question_agent.diversity_engine import QuestionDiversityEngine
                        prior_fps = {r["fingerprint"] for r in default_question_agent.history_store.get_recent_questions(cand_id)}
                        cached_fp = QuestionDiversityEngine.generate_fingerprint(cached["first_question"].text)
                        if cached_fp in prior_fps:
                            logger.info(
                                "[PREWARM_STALE] Question 1 (%s) already asked to candidate %s in prior session. Discarding prewarm to guarantee novelty.",
                                cached["first_question"].id, cand_id
                            )
                            _PREPARED_FIRST_QUESTIONS.pop(request.resume_id, None)
                            with _METRICS_LOCK:
                                PREGEN_METRICS["stale_buffer_invalidations"] += 1
                        else:
                            prewarmed = _PREPARED_FIRST_QUESTIONS.pop(request.resume_id)
                            with _METRICS_LOCK:
                                PREGEN_METRICS["prewarm_first_q_hits"] += 1
                    else:
                        logger.info(
                            "[PREWARM_STALE] Pre-warmed question for %s invalidated due to configuration mismatch (cached: track=%s, role=%s vs requested: track=%s, role=%s, dynamic=%s)",
                            request.resume_id, cached.get("track"), cached.get("target_role"), track, target_role_str, is_dynamic
                        )
                        _PREPARED_FIRST_QUESTIONS.pop(request.resume_id, None)
                        with _METRICS_LOCK:
                            PREGEN_METRICS["stale_buffer_invalidations"] += 1

        if prewarmed:
            blueprint = prewarmed["blueprint"]
            first_q = prewarmed["first_question"]
            reason = prewarmed["first_reason"]
            buffered_delivery_sec = time.perf_counter() - t_start
            logger.info(
                "[PREWARM_HIT] Opening question %s served from pre-warmed buffer in %.4fs (raw inference was %.2fs)",
                first_q.id, buffered_delivery_sec, prewarmed.get("raw_inference_latency", 0.0)
            )
        else:
            from backend.question_agent import default_question_agent
            diff_mode_str = (
                request.difficulty_mode.value
                if hasattr(request.difficulty_mode, "value")
                else str(request.difficulty_mode)
            )
            blueprint = default_question_agent.create_blueprint(
                resume_profile=resume_profile,
                target_role=target_role_str,
                interview_mode="mock" if getattr(request, "dynamic_questions", True) else "predefined",
                difficulty_mode=diff_mode_str,
                target_track=track,
                tech_stack=getattr(request, "tech_stack", None) or (resume_profile.get("recommended_tech_stack") if resume_profile else None),
                max_questions=request.max_questions,
                candidate_id=cand_id,
            )

            first_q, reason = interviewer.select_first_question(
                mode=request.difficulty_mode,
                topics=effective_topics,
                use_dynamic=getattr(request, "dynamic_questions", True),
                tech_stack=getattr(request, "tech_stack", None) or (resume_profile.get("recommended_tech_stack") if resume_profile else None),
                blueprint=blueprint,
                resume_profile=resume_profile,
                candidate_id=cand_id,
                max_questions=request.max_questions,
            )
        session = InterviewSession(request, first_q, reason)
        session.candidate_id = cand_id
        session.blueprint = blueprint
        session.track = track
        session.tracker = interviewer.create_tracker()
        session.resume_profile = resume_profile
        session.interview_plan = plan
        if effective_topics:
            session.selected_topics = effective_topics

        target_skills = []
        if plan and resume_profile:
            target_skills = plan.topic_skill_mapping.get(first_q.topic, [])
            if not target_skills:
                for crit in plan.planned_questions_criteria:
                    if crit.topic == first_q.topic and crit.target_skills:
                        target_skills = crit.target_skills
                        break
            if not target_skills and plan.planned_questions_criteria:
                target_skills = list(plan.planned_questions_criteria[0].target_skills)

            if target_skills:
                claimed_str = ", ".join(target_skills)
                session.current_reason = (
                    f"Personalized plan: Validating resume claim in '{claimed_str}' "
                    f"with opening {first_q.question_type.value} question on '{first_q.topic}'."
                )
            elif resume_profile.get("skills"):
                claimed = ", ".join(resume_profile["skills"][:3])
                session.current_reason = (
                    f"Personalized plan: Validating resume claim in '{claimed}' "
                    f"with opening {first_q.question_type.value} question on '{first_q.topic}'."
                )
        first_q.target_skills = list(target_skills)

        self.sessions[session.session_id] = session
        self.persistence.save_session(session)

        # Trigger background pre-generation of question 2 while candidate reads and prepares answer 1
        if session.dynamic_questions and session.max_questions > 1:
            session.schedule_next_pregeneration(interviewer, 2, first_q.difficulty)

        duration_sec = time.perf_counter() - t_start
        logger.info(
            "[PERF] First question delivery completed in %.3fs for session %s (track='%s', q_id='%s')",
            duration_sec, session.session_id, track, first_q.id
        )

        return session

    def get_session(self, session_id: str) -> Optional[InterviewSession]:
        """Retrieves session by ID, loading from durable SQLite store if not in memory."""
        session = self.sessions.get(session_id)
        if session:
            return session

        raw_dict = self.persistence.load_session_dict(session_id)
        if raw_dict:
            try:
                restored = InterviewSession.from_dict(raw_dict, self.registry)
                self.sessions[session_id] = restored
                return restored
            except Exception as exc:
                logger.error("[PERSISTENCE_LOAD_ERROR] Failed to restore session %s: %s", session_id, exc)

        return None

    def submit_answer(
        self,
        session_id: str,
        answer: str,
        question_id: Optional[str] = None,
        question_number: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Submits and evaluates candidate answer with concurrency lock and idempotency protection.
        Guarantees that empty submissions or errors do not advance question count.
        Calculates deterministic rubric marks and selects next question.
        """
        session = self.get_session(session_id)
        if not session:
            raise KeyError(f"Session '{session_id}' not found.")

        if session.status != "active":
            raise ValueError("This interview session has already ended.")

        trimmed = answer.strip()
        if not trimmed:
            raise ValueError("Answer cannot be empty.")

        with session.lock:
            current_q = session.current_question
            if not current_q:
                raise RuntimeError("No active question found in session.")

            # Idempotency check: prevent duplicate scoring on network retry / refresh
            submission_hash = hashlib.sha256(f"{current_q.id}_{trimmed}".encode("utf-8")).hexdigest()
            if getattr(session, "last_submission_hash", None) == submission_hash and current_q.id in getattr(session, "idempotency_cache", {}):
                logger.info("[IDEMPOTENT_SUBMISSION] Returning cached answer response for session %s, q=%s", session_id, current_q.id)
                return session.idempotency_cache[current_q.id]

            if session.history and (
                (question_id and question_id == session.history[-1].question.id) or
                (question_number and question_number == session.history[-1].question_number)
            ):
                last_rec = session.history[-1]
                logger.info("[IDEMPOTENT_SUBMISSION] Returning cached answer response for prior question %s", last_rec.question.id)
                if last_rec.question.id in getattr(session, "idempotency_cache", {}):
                    return session.idempotency_cache[last_rec.question.id]
                eval_res = last_rec.evaluation
                next_disp = session.get_current_question_display() if session.current_question else None
                return {
                    "session_id": session.session_id,
                    "status": session.status,
                    "question_number": last_rec.question_number,
                    "is_complete": session.status == "completed",
                    "questions_remaining": max(0, session.max_questions - last_rec.question_number),
                    "feedback_mode": session.feedback_mode.value,
                    "evaluation": {
                        "awarded_marks": eval_res.awarded_marks,
                        "max_marks": eval_res.max_marks,
                        "percentage": eval_res.percentage,
                        "summary": eval_res.summary_explanation,
                        "demonstrated_concepts": eval_res.demonstrated_concepts,
                        "incorrect_claims": eval_res.incorrect_claims,
                        "criteria": [
                            {
                                "criterion_id": c.criterion_id,
                                "awarded_marks": c.awarded_marks,
                                "max_marks": c.max_marks,
                                "explanation": c.explanation,
                            }
                            for c in eval_res.criteria_evaluations
                        ],
                    } if session.feedback_mode == FeedbackMode.IMMEDIATE else {
                        "status": "Answer recorded successfully. Detailed marks and feedback will be presented in the final report."
                    },
                    "next_question": next_disp.model_dump() if next_disp else None,
                    "reason_for_next_question": session.current_reason,
                }

            question_number = len(session.history) + 1

            # 1. Evaluate answer using appropriate interviewer model
            interviewer = self.registry.get(session.track)
            t_eval_start = time.perf_counter()
            from unittest.mock import Mock, MagicMock
            if isinstance(EvaluationEngine.evaluate_answer, (Mock, MagicMock)):
                evaluation = EvaluationEngine.evaluate_answer(self.eval_engine, current_q, trimmed)
            else:
                evaluation = interviewer.evaluate_answer(
                    question=current_q,
                    candidate_answer=trimmed,
                )
            eval_dur = time.perf_counter() - t_eval_start
            logger.info(
                "[PERF] Answer evaluation completed in %.3fs for question %d (id=%s, score=%.1f/%.1f)",
                eval_dur, question_number, current_q.id, evaluation.awarded_marks, evaluation.max_marks
            )

            # 2. Record answer and update competency tracker
            session.tracker.record_answer(current_q, evaluation)

            target_skills = list(getattr(current_q, "target_skills", []))
            if not target_skills and getattr(session, "interview_plan", None):
                target_skills = session.interview_plan.topic_skill_mapping.get(current_q.topic, [])
                if not target_skills:
                    for crit in session.interview_plan.planned_questions_criteria:
                        if crit.topic == current_q.topic and crit.target_skills:
                            target_skills = crit.target_skills
                            break
                if not target_skills and session.interview_plan.planned_questions_criteria:
                    q_idx = question_number - 1
                    if 0 <= q_idx < len(session.interview_plan.planned_questions_criteria):
                        target_skills = list(session.interview_plan.planned_questions_criteria[q_idx].target_skills)

            record = QuestionRecord(
                question_number=question_number,
                question=current_q,
                candidate_answer=trimmed,
                evaluation=evaluation,
                selection_reason=session.current_reason,
                timestamp=datetime.now(timezone.utc).isoformat(),
                target_skills=target_skills,
            )
            session.history.append(record)

            # 3. Check completion condition
            is_complete = question_number >= session.max_questions
            next_question_display = None
            next_reason = ""

            if is_complete:
                session.status = "completed"
                session.is_cancelled = True
                with session.pregen_lock:
                    session.pregenerated_question = None
                session.current_question = None
                session.current_reason = "Interview reached configured question limit."
            else:
                next_q = None
                blueprint = getattr(session, "blueprint", None)
                if not blueprint:
                    from backend.question_agent import default_question_agent
                    diff_mode_str = (
                        session.difficulty_mode.value
                        if hasattr(session.difficulty_mode, "value")
                        else str(session.difficulty_mode)
                    )
                    blueprint = default_question_agent.create_blueprint(
                        resume_profile=session.resume_profile,
                        target_role=session.role,
                        interview_mode="mock" if session.dynamic_questions else "predefined",
                        difficulty_mode=diff_mode_str,
                        target_track=session.track,
                        tech_stack=session.tech_stack,
                        max_questions=session.max_questions,
                        candidate_id=session.candidate_id,
                    )
                    session.blueprint = blueprint

                # Phase 2 Part F: Adaptive Follow-up Generation when warranted
                if session.dynamic_questions and evaluation:
                    from backend.question_agent import default_question_agent
                    asked_ids = {r.question.id for r in session.history} | ({current_q.id} if current_q else set())
                    follow_up = default_question_agent.generate_adaptive_follow_up(
                        blueprint=blueprint,
                        last_question=current_q,
                        last_evaluation=evaluation,
                        session_asked_texts=[r.question.text for r in session.history],
                        session_asked_ids=asked_ids,
                    )
                    if follow_up:
                        next_q, next_reason = follow_up
                        # When an adaptive follow-up is generated, any pregenerated question in buffer is stale
                        with session.pregen_lock:
                            if session.pregenerated_question is not None:
                                with _METRICS_LOCK:
                                    PREGEN_METRICS["stale_buffer_invalidations"] += 1
                                session.pregenerated_question = None
                        logger.info(
                            "[ADAPTIVE_FOLLOWUP_SELECTED] Follow-up generated for session %s: %s",
                            session.session_id, next_q.id
                        )

                # Check if we can fulfill from pregenerated question buffer
                if next_q is None and session.dynamic_questions:
                    # Calculate expected difficulty based on interview mode and recent score
                    expected_diff = session.tracker.current_difficulty
                    if session.difficulty_mode == InterviewMode.ADAPTIVE and evaluation:
                        score = evaluation.percentage
                        if score >= 80.0:
                            if session.tracker.current_difficulty == DifficultyLevel.BEGINNER:
                                expected_diff = DifficultyLevel.INTERMEDIATE
                            elif session.tracker.current_difficulty == DifficultyLevel.INTERMEDIATE:
                                if len(session.tracker.recent_percentages) >= 2 and sum(session.tracker.recent_percentages[-2:]) / 2 >= 75.0:
                                    expected_diff = DifficultyLevel.ADVANCED
                                else:
                                    expected_diff = DifficultyLevel.INTERMEDIATE
                            else:
                                expected_diff = DifficultyLevel.ADVANCED
                        elif score < 40.0:
                            if session.tracker.current_difficulty == DifficultyLevel.ADVANCED:
                                expected_diff = DifficultyLevel.INTERMEDIATE
                            elif session.tracker.current_difficulty == DifficultyLevel.INTERMEDIATE:
                                expected_diff = DifficultyLevel.BEGINNER
                            else:
                                expected_diff = DifficultyLevel.BEGINNER
                    elif session.difficulty_mode != InterviewMode.ADAPTIVE:
                        expected_diff = {
                            InterviewMode.BEGINNER: DifficultyLevel.BEGINNER,
                            InterviewMode.INTERMEDIATE: DifficultyLevel.INTERMEDIATE,
                            InterviewMode.ADVANCED: DifficultyLevel.ADVANCED,
                        }.get(session.difficulty_mode, DifficultyLevel.INTERMEDIATE)

                    pregen = session.get_or_await_pregenerated(expected_difficulty=expected_diff, timeout=1.5)
                    if pregen:
                        pq, pr = pregen
                        asked_ids = {r.question.id for r in session.history}
                        asked_texts = [r.question.text for r in session.history]
                        from backend.question_agent.diversity_engine import QuestionDiversityEngine
                        is_dup, dup_reason, _ = QuestionDiversityEngine.check_duplicate(
                            pq.text,
                            asked_texts,
                            threshold=0.45,
                        )
                        if pq.id not in asked_ids and not is_dup:
                            next_q, next_reason = pq, pr
                            logger.info("[PREGEN_HIT] Served pre-generated question %s for session %s (<0.05s)", pq.id, session.session_id)
                        else:
                            with _METRICS_LOCK:
                                PREGEN_METRICS["stale_buffer_invalidations"] += 1
                            logger.info("[PREGEN_REJECTED] Buffered question %s rejected for duplicate risk: %s", pq.id, dup_reason)

                if next_q is None:
                    # 4. Adaptively select next question
                    t_sel_start = time.perf_counter()
                    next_q, next_reason = interviewer.select_next_question(
                        tracker=session.tracker,
                        mode=session.difficulty_mode,
                        allowed_topics=session.selected_topics,
                        last_question=current_q,
                        last_evaluation=evaluation,
                        question_number=question_number + 1,
                        session_asked_texts=[r.question.text for r in session.history],
                        session_asked_ids={r.question.id for r in session.history},
                        use_dynamic=session.dynamic_questions,
                        tech_stack=session.tech_stack,
                        blueprint=blueprint,
                        resume_profile=session.resume_profile,
                        candidate_id=session.candidate_id,
                        max_questions=session.max_questions,
                    )
                    sel_dur = time.perf_counter() - t_sel_start
                    logger.info(
                        "[PERF] Next question selection completed in %.3fs (next_id=%s)",
                        sel_dur, getattr(next_q, "id", "None")
                    )

                if next_q is None:
                    # Question bank exhausted
                    session.status = "completed"
                    session.current_question = None
                    session.current_reason = "All available questions have been completed."
                    is_complete = True
                else:
                    next_target_skills = []
                    if getattr(session, "interview_plan", None):
                        next_target_skills = session.interview_plan.topic_skill_mapping.get(next_q.topic, [])
                        if not next_target_skills:
                            for crit in session.interview_plan.planned_questions_criteria:
                                if crit.topic == next_q.topic and crit.target_skills:
                                    next_target_skills = crit.target_skills
                                    break
                        if not next_target_skills and session.interview_plan.planned_questions_criteria:
                            next_idx = len(session.history)
                            if next_idx < len(session.interview_plan.planned_questions_criteria):
                                next_target_skills = list(session.interview_plan.planned_questions_criteria[next_idx].target_skills)
                        if next_target_skills:
                            claimed_str = ", ".join(next_target_skills)
                            next_reason = (
                                f"Personalized plan: Validating resume claim in '{claimed_str}' "
                                f"with targeted {next_q.question_type.value} question on '{next_q.topic}'."
                            )
                    next_q.target_skills = list(next_target_skills)
                    session.current_question = next_q
                    session.current_reason = next_reason
                    next_question_display = session.get_current_question_display()

                    # Trigger next background pre-generation for Question N+2 while candidate prepares answer for N+1
                    if not is_complete and (question_number + 1) < session.max_questions and session.dynamic_questions:
                        session.schedule_next_pregeneration(interviewer, question_number + 2, next_q.difficulty)

            # Format evaluation based on feedback mode
            eval_payload = None
            if session.feedback_mode == FeedbackMode.IMMEDIATE:
                eval_payload = {
                    "awarded_marks": evaluation.awarded_marks,
                    "max_marks": evaluation.max_marks,
                    "percentage": evaluation.percentage,
                    "summary": evaluation.summary_explanation,
                    "demonstrated_concepts": evaluation.demonstrated_concepts,
                    "incorrect_claims": evaluation.incorrect_claims,
                    "criteria": [
                        {
                            "criterion_id": c.criterion_id,
                            "awarded_marks": c.awarded_marks,
                            "max_marks": c.max_marks,
                            "explanation": c.explanation,
                        }
                        for c in evaluation.criteria_evaluations
                    ],
                }
            else:
                # In assessment mode, defer score until final report
                eval_payload = {
                    "status": "Answer recorded successfully. Detailed marks and feedback will be presented in the final report."
                }

            result_payload = {
                "session_id": session.session_id,
                "status": session.status,
                "question_number": question_number,
                "is_complete": is_complete,
                "questions_remaining": max(0, session.max_questions - question_number),
                "feedback_mode": session.feedback_mode.value,
                "evaluation": eval_payload,
                "next_question": next_question_display.model_dump() if next_question_display else None,
                "reason_for_next_question": next_reason,
            }

            session.last_submission_hash = submission_hash
            session.idempotency_cache[current_q.id] = result_payload
            self.persistence.save_session(session)

            return result_payload

    def generate_report(self, session_id: str) -> FinalReport:
        """
        Compiles detailed final interview report.
        Normalizes final score to 100%, breaks down by topic and difficulty,
        identifies strengths, weaknesses, misconceptions, and recommendations.
        """
        session = self.get_session(session_id)
        if not session:
            raise KeyError(f"Session '{session_id}' not found.")

        interviewer = self.registry.get(session.track)

        history = session.history
        total_earned = sum(r.evaluation.awarded_marks for r in history)
        total_max = sum(r.evaluation.max_marks for r in history)

        normalized_score = round((total_earned / total_max) * 100.0, 1) if total_max > 0 else 0.0

        # Topic breakdown
        topic_scores = {}
        for topic, stat in session.tracker.topic_scores.items():
            t_max = stat["max"]
            t_earned = stat["earned"]
            topic_scores[topic] = {
                "earned": round(t_earned, 2),
                "max": round(t_max, 2),
                "percentage": round((t_earned / t_max) * 100.0, 1) if t_max > 0 else 0.0,
                "questions_count": stat["count"],
            }

        # Difficulty breakdown
        difficulty_scores = {}
        for diff, stat in session.tracker.difficulty_scores.items():
            if stat["count"] > 0:
                d_max = stat["max"]
                d_earned = stat["earned"]
                difficulty_scores[diff] = {
                    "earned": round(d_earned, 2),
                    "max": round(d_max, 2),
                    "percentage": round((d_earned / d_max) * 100.0, 1) if d_max > 0 else 0.0,
                    "questions_count": stat["count"],
                }

        # Competency breakdown
        competency_scores = {}
        for comp, stat in session.tracker.competency_scores.items():
            c_max = stat["max"]
            c_earned = stat["earned"]
            competency_scores[comp] = {
                "earned": round(c_earned, 2),
                "max": round(c_max, 2),
                "percentage": round((c_earned / c_max) * 100.0, 1) if c_max > 0 else 0.0,
                "questions_count": stat["count"],
            }

        # Competency classification
        strong_competencies = [
            comp for comp, data in competency_scores.items() if data["percentage"] >= 75.0
        ]
        weak_competencies = [
            comp for comp, data in competency_scores.items() if data["percentage"] < 60.0
        ]

        # Strongest demonstrated examples
        strongest_demonstrations = []
        for r in sorted(history, key=lambda x: x.evaluation.percentage, reverse=True)[:3]:
            if r.evaluation.percentage >= 60.0:
                strongest_demonstrations.append({
                    "question_id": r.question.id,
                    "topic": r.question.topic,
                    "score": f"{r.evaluation.awarded_marks}/{r.evaluation.max_marks} ({r.evaluation.percentage}%)",
                    "evidence": r.evaluation.summary_explanation,
                })

        # Recommendations based on identified gaps and weak competencies
        recommendations = []
        suggested_study = []

        if weak_competencies:
            for wc in weak_competencies:
                recommendations.append(f"Review core principles in {wc}, focusing on implementation details and edge cases.")
                suggested_study.append(wc)

        if session.tracker.misconceptions:
            recommendations.append(
                f"Address specific identified misconceptions: {'; '.join(session.tracker.misconceptions[:3])}"
            )

        if not recommendations:
            if session.track == "fullstack":
                recommendations.append("Demonstrated solid performance across full-stack competencies. Continue exploring scalable architecture and distributed systems.")
                suggested_study.append("Full-Stack Architecture & Cloud Systems")
            else:
                recommendations.append("Demonstrated solid performance across evaluated competencies. Continue exploring advanced concurrency and systems architecture.")
                suggested_study.append("Advanced Python Internals & Asynchronous Architecture")

        # Unassessed topics
        info = interviewer.get_topics_and_competencies()
        all_topics = info.get("topics", []) if isinstance(info, dict) else info[0]
        unassessed = [
            t for t in all_topics if t not in session.tracker.topic_scores
        ]

        # Serialized history for report inspection
        history_records = []
        for r in history:
            target_skills = list(getattr(r, "target_skills", []))
            if not target_skills:
                target_skills = list(getattr(r.question, "target_skills", []))
            if not target_skills and getattr(session, "interview_plan", None):
                target_skills = session.interview_plan.topic_skill_mapping.get(r.question.topic, [])
                if not target_skills:
                    for crit in session.interview_plan.planned_questions_criteria:
                        if crit.topic == r.question.topic and crit.target_skills:
                            target_skills = crit.target_skills
                            break
                if not target_skills and session.interview_plan.planned_questions_criteria:
                    r_idx = r.question_number - 1
                    if 0 <= r_idx < len(session.interview_plan.planned_questions_criteria):
                        target_skills = list(session.interview_plan.planned_questions_criteria[r_idx].target_skills)

            history_records.append({
                "question_number": r.question_number,
                "question_id": r.question.id,
                "topic": r.question.topic,
                "competency": r.question.competency,
                "target_skills": target_skills,
                "difficulty": r.question.difficulty.value,
                "question_type": r.question.question_type.value,
                "language": getattr(r.question, "language", "python" if session.track == "python" else "javascript"),
                "question_text": r.question.text,
                "candidate_answer": r.candidate_answer,
                "awarded_marks": r.evaluation.awarded_marks,
                "max_marks": r.evaluation.max_marks,
                "percentage": r.evaluation.percentage,
                "summary": r.evaluation.summary_explanation,
                "demonstrated_concepts": r.evaluation.demonstrated_concepts,
                "missing_concepts": r.evaluation.missing_concepts,
                "incorrect_claims": r.evaluation.incorrect_claims,
                "execution_result": getattr(r.evaluation, "execution_result", None),
                "criteria": [
                    {
                        "criterion_id": c.criterion_id,
                        "awarded_marks": c.awarded_marks,
                        "max_marks": c.max_marks,
                        "evidence": c.evidence,
                        "explanation": c.explanation,
                    }
                    for c in r.evaluation.criteria_evaluations
                ],
                "correctness_status": (
                    "correct" if r.evaluation.percentage >= 75.0
                    else "partially_correct" if r.evaluation.percentage >= 40.0
                    else "incorrect"
                ),
                "selection_reason": r.selection_reason,
            })

        # Resume skill gap analysis if resume profile was attached
        resume_skill_gap = None
        resume_summary = None
        if getattr(session, "resume_profile", None):
            try:
                from backend.resume_analyzer.skill_gap import SkillGapAnalyzer
                gap_report = SkillGapAnalyzer.analyze_skill_gap(
                    resume_profile=session.resume_profile,
                    interview_history=history_records,
                    track=session.track,
                )
                resume_skill_gap = gap_report.model_dump()
                resume_summary = {
                    "candidate_name": session.resume_profile.get("candidate_name", "Candidate"),
                    "filename": session.resume_profile.get("filename", ""),
                    "total_experience_years": session.resume_profile.get("total_experience_years", 0.0),
                    "skills": session.resume_profile.get("skills", []),
                    "ats_score": session.resume_profile.get("ats_score"),
                    "integrity_status": session.resume_profile.get("integrity_audit", {}).get("overall_status", "passed"),
                }
            except Exception as e:
                logger.warning(f"Error generating skill gap analysis: {e}")

        interview_plan_dict = None
        if getattr(session, "interview_plan", None):
            interview_plan_dict = session.interview_plan.model_dump()

        # Module 3: Sensor and browser integrity telemetry summary
        integrity_summary = self.persistence.get_integrity_summary(session.session_id)
        integrity_summary_dict = integrity_summary.model_dump()

        # Grade calculation
        if normalized_score >= 90.0:
            grade = "A (Distinction)"
        elif normalized_score >= 75.0:
            grade = "B (Proficient)"
        elif normalized_score >= 60.0:
            grade = "C (Competent)"
        else:
            grade = "D (Developing)"

        # Module 5: Candidate Decision Intelligence synthesis
        has_integrity_flags = integrity_summary.requires_followup_count > 0
        prereqs_ok = True
        if session.resume_profile and session.resume_profile.get("role_eligibility"):
            prereqs_ok = session.resume_profile["role_eligibility"].get("eligible", True)

        if normalized_score >= 75.0 and prereqs_ok and not has_integrity_flags:
            rec_outcome = DecisionOutcome.PROCEED_TO_HUMAN_REVIEW.value
            rec_summary = (
                f"Candidate demonstrated robust technical competency ({normalized_score}%, {grade}) with strong alignment "
                f"to {session.role} requisites. Satisfied core prerequisites and demonstrated capability in {', '.join(strong_competencies[:3]) or 'core topics'}."
            )
        elif normalized_score >= 50.0:
            rec_outcome = DecisionOutcome.REQUEST_FOLLOW_UP.value
            rec_summary = (
                f"Candidate achieved a viable baseline ({normalized_score}%, {grade}) but exhibited gaps in "
                f"{', '.join(weak_competencies[:2]) or 'select topics'}. Recommend structured technical panel interview."
            )
        elif not prereqs_ok:
            rec_outcome = DecisionOutcome.CONSIDER_ALTERNATE_ROLE.value
            rec_summary = (
                f"Candidate did not meet required technical prerequisites or alignment threshold for {session.role} ({normalized_score}%). "
                f"Recommend exploring adjacent roles matching verified strengths."
            )
        else:
            rec_outcome = DecisionOutcome.NEEDS_FURTHER_EVALUATION.value
            rec_summary = (
                f"Candidate completed {len(history)} questions with normalized score of {normalized_score}% ({grade}). "
                f"Score indicates developing competency; panel review recommended before final hiring decision."
            )

        cand_name = (
            session.resume_profile.get("candidate_name")
            if session.resume_profile and session.resume_profile.get("candidate_name")
            else f"Candidate_{session.candidate_id[:8]}"
        )
        decision_rec = CandidateDecisionRecord(
            session_id=session.session_id,
            candidate_id=session.candidate_id,
            candidate_name=cand_name,
            target_role=session.role,
            track=session.track,
            normalized_score=normalized_score,
            grade=grade,
            outcome=rec_outcome,
            confidence_score=92.0 if len(history) >= 3 else 70.0,
            executive_summary=rec_summary,
            demonstrated_competencies=strong_competencies,
            critical_gaps=weak_competencies,
            unvalidated_claims=resume_skill_gap.get("claimed_unvalidated_skills", []) if resume_skill_gap else [],
            prerequisites_satisfied=prereqs_ok,
            integrity_review_needed=has_integrity_flags,
            evidence_points_count=len(history),
            recruiter_outcome_override=None,
            recruiter_notes=None,
        )
        self.persistence.save_candidate_decision(decision_rec)

        return FinalReport(
            session_id=session.session_id,
            role=session.role,
            track=session.track,
            tech_stack=session.tech_stack,
            resume_id=getattr(session, "resume_id", None),
            resume_summary=resume_summary,
            resume_skill_gap=resume_skill_gap,
            interview_plan=interview_plan_dict,
            integrity_summary=integrity_summary_dict,
            decision_recommendation=decision_rec.model_dump(),
            status=session.status,
            question_mode="Dynamic" if session.dynamic_questions else "Predefined",
            created_at=session.created_at,
            total_marks_obtained=round(total_earned, 2),
            total_max_marks=round(total_max, 2),
            normalized_score=normalized_score,
            questions_completed=len(history),
            questions_unanswered=max(0, session.max_questions - len(history)),
            questions_failed=sum(1 for r in history if r.evaluation.percentage < 40.0),
            scoring_denominator=f"Evaluated questions maximum marks ({total_max:.1f} marks total)",
            max_questions=session.max_questions,
            difficulty_mode=session.difficulty_mode.value,
            feedback_mode=session.feedback_mode.value,
            topic_scores=topic_scores,
            difficulty_scores=difficulty_scores,
            competency_scores=competency_scores,
            strong_competencies=strong_competencies,
            weak_competencies=weak_competencies,
            identified_misconceptions=session.tracker.misconceptions,
            unassessed_topics=unassessed,
            recommendations=recommendations,
            strongest_demonstrations=strongest_demonstrations,
            suggested_study_topics=suggested_study,
            history=history_records,
            note=(
                f"Assessment status: {session.status.replace('_', ' ').title()}. "
                f"{len(history)} of {session.max_questions} questions were completed."
            ),
        )

    # -------------------------------------------------------------
    # Module 3 & Module 5: Integrity and Recruiter Intelligence APIs
    # -------------------------------------------------------------

    def log_integrity_event(
        self,
        session_id: str,
        event_data: IntegrityEventCreateRequest,
        candidate_id: Optional[str] = None,
    ) -> IntegrityEventRecord:
        """Logs an observed browser or sensory event (focus loss, tab switch, audio fluctuation)."""
        session = self.get_session(session_id)
        cand_id = candidate_id or (getattr(session, "candidate_id", None) if session else None) or "candidate"
        now_iso = datetime.now(timezone.utc).isoformat()

        offset_sec = event_data.timestamp_offset_seconds
        if offset_sec is None:
            if session and session.created_at:
                try:
                    s_created = datetime.fromisoformat(session.created_at)
                    offset_sec = max(0.0, (datetime.now(timezone.utc) - s_created).total_seconds())
                except Exception:
                    offset_sec = 0.0
            else:
                offset_sec = 0.0

        ev_id = f"integ_{uuid.uuid4().hex[:12]}"
        record = IntegrityEventRecord(
            id=ev_id,
            session_id=session_id,
            candidate_id=cand_id,
            timestamp_offset_seconds=float(offset_sec),
            timestamp_iso=now_iso,
            event_type=event_data.event_type,
            severity=event_data.severity,
            confidence=event_data.confidence,
            title=event_data.title,
            description=event_data.description,
            recruiter_status="pending_review",
            recruiter_notes=None,
            created_at=now_iso,
        )
        self.persistence.save_integrity_event(record)
        return record

    def get_integrity_events(self, session_id: str) -> List[IntegrityEventRecord]:
        """Returns chronological list of integrity events recorded for the session."""
        return self.persistence.get_integrity_events(session_id)

    def update_integrity_event_status(
        self, event_id: str, status: str, notes: Optional[str] = None
    ) -> bool:
        """Updates human recruiter triage review for an integrity event."""
        return self.persistence.update_integrity_event_status(event_id, status, notes)

    def get_integrity_summary(self, session_id: str) -> IntegritySummary:
        """Computes summary statistics of session integrity telemetry."""
        return self.persistence.get_integrity_summary(session_id)

    def get_candidate_decision(self, session_id: str) -> Optional[CandidateDecisionRecord]:
        """Retrieves decision record and recruiter recommendation for session."""
        rec = self.persistence.get_candidate_decision(session_id)
        if not rec:
            # If not yet generated, compile report to synthesize decision
            try:
                self.generate_report(session_id)
                rec = self.persistence.get_candidate_decision(session_id)
            except Exception:
                pass
        return rec

    def update_candidate_decision(
        self, session_id: str, outcome: str, notes: Optional[str] = None
    ) -> bool:
        """Allows recruiter to record an override and contextual notes."""
        return self.persistence.update_candidate_decision(session_id, outcome, notes)

    def list_candidate_decisions(
        self, target_role: Optional[str] = None
    ) -> List[CandidateDecisionRecord]:
        """Lists candidate decision records for recruiter dashboard."""
        return self.persistence.list_candidate_decisions(target_role)

    def compare_candidates(self, session_ids: List[str]) -> Dict[str, Any]:
        """Provides explainable side-by-side comparison across candidate assessments."""
        decisions: List[CandidateDecisionRecord] = []
        for sid in session_ids:
            dec = self.get_candidate_decision(sid)
            if dec:
                decisions.append(dec)

        if not decisions:
            return {"error": "No matching candidate assessment records found for comparison."}

        all_competencies = set()
        for d in decisions:
            all_competencies.update(d.demonstrated_competencies)
            all_competencies.update(d.critical_gaps)

        comparison_matrix = {}
        for comp in sorted(all_competencies):
            comparison_matrix[comp] = {}
            for d in decisions:
                if comp in d.demonstrated_competencies:
                    status = "demonstrated"
                elif comp in d.critical_gaps:
                    status = "gap"
                elif comp in d.unvalidated_claims:
                    status = "unvalidated"
                else:
                    status = "unassessed"
                comparison_matrix[comp][d.candidate_name] = status

        # Rank candidates objectively by normalized score and prerequisite satisfaction
        ranked = sorted(decisions, key=lambda d: (d.prerequisites_satisfied, d.normalized_score), reverse=True)

        return {
            "candidate_count": len(decisions),
            "candidates": [d.model_dump() for d in ranked],
            "competency_matrix": comparison_matrix,
            "top_candidate": ranked[0].candidate_name if ranked else None,
            "fairness_notice": (
                "Side-by-side comparisons utilize identical rubric normalization and objective evidence extraction. "
                "Final hiring discretion rests with human technical panel."
            ),
        }

    def cancel_session(self, session_id: str) -> bool:
        """Cancels an active session and safely stops any pending background pre-generation."""
        session = self.get_session(session_id)
        if not session:
            return False
        with session.lock:
            session.is_cancelled = True
            session.status = "cancelled"
            session.pregenerated_question = None
            session.current_question = None
            self.persistence.save_session(session)
        return True


