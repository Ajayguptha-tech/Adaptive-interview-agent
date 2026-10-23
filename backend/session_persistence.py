"""
Durable SQLite-backed persistence for interview sessions.
Enables seamless multi-instance deployment, worker failover, and candidate state persistence.
"""

import os
import json
import sqlite3
import logging
import threading
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

from backend.models import (
    StartInterviewRequest,
    Question,
    QuestionRecord,
    QuestionDisplay,
    EvaluationResult,
    FeedbackMode,
    DifficultyLevel,
    InterviewMode,
    IntegrityEventRecord,
    IntegritySummary,
    CandidateDecisionRecord,
)

logger = logging.getLogger(__name__)

DB_FILE = os.environ.get("DATABASE_PATH", "resumeiq.db")


def get_db_connection() -> sqlite3.Connection:
    """Returns SQLite connection with row factory and WAL mode for high concurrency."""
    conn = sqlite3.connect(DB_FILE, check_same_thread=False, timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA busy_timeout = 5000")
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_session_table():
    """Initializes the durable interview_sessions table and indexes."""
    conn = get_db_connection()
    try:
        with conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS interview_sessions (
                    session_id TEXT PRIMARY KEY,
                    candidate_id TEXT NOT NULL,
                    session_token TEXT NOT NULL,
                    role TEXT NOT NULL,
                    track TEXT NOT NULL,
                    tech_stack TEXT,
                    job_description TEXT,
                    resume_summary TEXT,
                    max_questions INTEGER NOT NULL,
                    difficulty_mode TEXT NOT NULL,
                    feedback_mode TEXT NOT NULL,
                    selected_topics_json TEXT NOT NULL,
                    dynamic_questions INTEGER NOT NULL,
                    resume_id TEXT,
                    resume_profile_json TEXT,
                    interview_plan_json TEXT,
                    current_question_json TEXT,
                    current_reason TEXT,
                    history_json TEXT NOT NULL,
                    tracker_json TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    version INTEGER DEFAULT 1,
                    last_submission_hash TEXT
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_sessions_candidate ON interview_sessions(candidate_id)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_sessions_status ON interview_sessions(status)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_sessions_updated ON interview_sessions(updated_at DESC)
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS interview_integrity_events (
                    id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    candidate_id TEXT,
                    timestamp_offset_seconds REAL NOT NULL,
                    timestamp_iso TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT NOT NULL,
                    recruiter_status TEXT NOT NULL DEFAULT 'pending_review',
                    recruiter_notes TEXT,
                    created_at TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_integrity_session ON interview_integrity_events(session_id)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_integrity_candidate ON interview_integrity_events(candidate_id)
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS candidate_decisions (
                    session_id TEXT PRIMARY KEY,
                    candidate_id TEXT NOT NULL,
                    candidate_name TEXT NOT NULL,
                    target_role TEXT NOT NULL,
                    track TEXT NOT NULL,
                    normalized_score REAL NOT NULL,
                    grade TEXT NOT NULL,
                    outcome TEXT NOT NULL,
                    confidence_score REAL NOT NULL,
                    executive_summary TEXT NOT NULL,
                    demonstrated_competencies_json TEXT NOT NULL,
                    critical_gaps_json TEXT NOT NULL,
                    unvalidated_claims_json TEXT NOT NULL,
                    prerequisites_satisfied INTEGER NOT NULL,
                    integrity_review_needed INTEGER NOT NULL,
                    evidence_points_count INTEGER NOT NULL,
                    recruiter_outcome_override TEXT,
                    recruiter_notes TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_decisions_candidate ON candidate_decisions(candidate_id)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_decisions_role ON candidate_decisions(target_role)
            """)
    finally:
        conn.close()


class SessionPersistence:
    """Manages durable SQLite persistence for InterviewSession instances."""

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or DB_FILE
        self._lock = threading.Lock()
        init_session_table()

    def save_session(self, session: Any) -> bool:
        """
        Saves or updates an InterviewSession in SQLite with optimistic concurrency control.
        Increments session version upon successful update.
        """
        conn = get_db_connection()
        now_iso = datetime.now(timezone.utc).isoformat()
        current_version = getattr(session, "version", 1)
        next_version = current_version + 1

        curr_q_dict = session.current_question.model_dump() if session.current_question else None
        history_list = [r.model_dump() for r in session.history]
        tracker_dict = self._serialize_tracker(session.tracker)

        try:
            with self._lock, conn:
                # Check if session already exists
                cur = conn.cursor()
                cur.execute("SELECT version FROM interview_sessions WHERE session_id = ?", (session.session_id,))
                row = cur.fetchone()

                if row is None:
                    # Insert new session
                    conn.execute(
                        """
                        INSERT INTO interview_sessions (
                            session_id, candidate_id, session_token, role, track,
                            tech_stack, job_description, resume_summary, max_questions,
                            difficulty_mode, feedback_mode, selected_topics_json,
                            dynamic_questions, resume_id, resume_profile_json,
                            interview_plan_json, current_question_json, current_reason,
                            history_json, tracker_json, status, created_at, updated_at,
                            version, last_submission_hash
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            session.session_id,
                            session.candidate_id,
                            session.session_token,
                            session.role,
                            session.track,
                            session.tech_stack,
                            session.job_description,
                            session.resume_summary,
                            session.max_questions,
                            session.difficulty_mode.value if hasattr(session.difficulty_mode, "value") else str(session.difficulty_mode),
                            session.feedback_mode.value if hasattr(session.feedback_mode, "value") else str(session.feedback_mode),
                            json.dumps(session.selected_topics or []),
                            1 if session.dynamic_questions else 0,
                            session.resume_id,
                            json.dumps(session.resume_profile) if session.resume_profile else None,
                            json.dumps(session.interview_plan.model_dump()) if getattr(session, "interview_plan", None) else None,
                            json.dumps(curr_q_dict) if curr_q_dict else None,
                            session.current_reason or "",
                            json.dumps(history_list),
                            json.dumps(tracker_dict),
                            session.status,
                            session.created_at,
                            now_iso,
                            current_version,
                            getattr(session, "last_submission_hash", None),
                        ),
                    )
                else:
                    db_version = row["version"]
                    if db_version > current_version:
                        logger.warning(
                            "[SESSION_CONFLICT] Stale write rejected for session %s (db_v=%d, local_v=%d)",
                            session.session_id, db_version, current_version
                        )
                        return False

                    conn.execute(
                        """
                        UPDATE interview_sessions SET
                            candidate_id = ?,
                            session_token = ?,
                            role = ?,
                            track = ?,
                            tech_stack = ?,
                            job_description = ?,
                            resume_summary = ?,
                            max_questions = ?,
                            difficulty_mode = ?,
                            feedback_mode = ?,
                            selected_topics_json = ?,
                            dynamic_questions = ?,
                            resume_id = ?,
                            resume_profile_json = ?,
                            interview_plan_json = ?,
                            current_question_json = ?,
                            current_reason = ?,
                            history_json = ?,
                            tracker_json = ?,
                            status = ?,
                            updated_at = ?,
                            version = ?,
                            last_submission_hash = ?
                        WHERE session_id = ?
                        """,
                        (
                            session.candidate_id,
                            session.session_token,
                            session.role,
                            session.track,
                            session.tech_stack,
                            session.job_description,
                            session.resume_summary,
                            session.max_questions,
                            session.difficulty_mode.value if hasattr(session.difficulty_mode, "value") else str(session.difficulty_mode),
                            session.feedback_mode.value if hasattr(session.feedback_mode, "value") else str(session.feedback_mode),
                            json.dumps(session.selected_topics or []),
                            1 if session.dynamic_questions else 0,
                            session.resume_id,
                            json.dumps(session.resume_profile) if session.resume_profile else None,
                            json.dumps(session.interview_plan.model_dump()) if getattr(session, "interview_plan", None) else None,
                            json.dumps(curr_q_dict) if curr_q_dict else None,
                            session.current_reason or "",
                            json.dumps(history_list),
                            json.dumps(tracker_dict),
                            session.status,
                            now_iso,
                            next_version,
                            getattr(session, "last_submission_hash", None),
                            session.session_id,
                        ),
                    )
                    session.version = next_version

            return True
        except Exception as exc:
            logger.error("[PERSISTENCE_ERROR] Failed to save session %s: %s", session.session_id, exc)
            return False
        finally:
            conn.close()

    def load_session_dict(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Loads raw serialized session dictionary from SQLite."""
        conn = get_db_connection()
        try:
            cur = conn.cursor()
            cur.execute("SELECT * FROM interview_sessions WHERE session_id = ?", (session_id,))
            row = cur.fetchone()
            if not row:
                return None

            return {
                "session_id": row["session_id"],
                "candidate_id": row["candidate_id"],
                "session_token": row["session_token"],
                "role": row["role"],
                "track": row["track"],
                "tech_stack": row["tech_stack"],
                "job_description": row["job_description"],
                "resume_summary": row["resume_summary"],
                "max_questions": row["max_questions"],
                "difficulty_mode": row["difficulty_mode"],
                "feedback_mode": row["feedback_mode"],
                "selected_topics": json.loads(row["selected_topics_json"]),
                "dynamic_questions": bool(row["dynamic_questions"]),
                "resume_id": row["resume_id"],
                "resume_profile": json.loads(row["resume_profile_json"]) if row["resume_profile_json"] else None,
                "interview_plan": json.loads(row["interview_plan_json"]) if row["interview_plan_json"] else None,
                "current_question": json.loads(row["current_question_json"]) if row["current_question_json"] else None,
                "current_reason": row["current_reason"],
                "history": json.loads(row["history_json"]),
                "tracker": json.loads(row["tracker_json"]),
                "status": row["status"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
                "version": row["version"],
                "last_submission_hash": row["last_submission_hash"],
            }
        finally:
            conn.close()

    def delete_session(self, session_id: str) -> bool:
        """Deletes session record from SQLite."""
        conn = get_db_connection()
        try:
            with conn:
                cur = conn.cursor()
                cur.execute("DELETE FROM interview_sessions WHERE session_id = ?", (session_id,))
                return cur.rowcount > 0
        finally:
            conn.close()

    def list_sessions(self, candidate_id: Optional[str] = None) -> List[str]:
        """Lists session IDs optionally filtered by candidate_id."""
        conn = get_db_connection()
        try:
            cur = conn.cursor()
            if candidate_id:
                cur.execute("SELECT session_id FROM interview_sessions WHERE candidate_id = ? ORDER BY created_at DESC", (candidate_id,))
            else:
                cur.execute("SELECT session_id FROM interview_sessions ORDER BY created_at DESC")
            return [row["session_id"] for row in cur.fetchall()]
        finally:
            conn.close()

    def _serialize_tracker(self, tracker: Any) -> Dict[str, Any]:
        """Serializes CompetencyTracker to plain JSON-compatible dictionary."""
        if tracker is None:
            return {}
        return {
            "asked_question_ids": list(getattr(tracker, "asked_question_ids", set())),
            "topic_scores": getattr(tracker, "topic_scores", {}),
            "competency_scores": getattr(tracker, "competency_scores", {}),
            "difficulty_scores": getattr(tracker, "difficulty_scores", {}),
            "demonstrated_concepts": getattr(tracker, "demonstrated_concepts", []),
            "missing_concepts": getattr(tracker, "missing_concepts", []),
            "misconceptions": getattr(tracker, "misconceptions", []),
            "recent_percentages": getattr(tracker, "recent_percentages", []),
            "current_difficulty": getattr(tracker, "current_difficulty", DifficultyLevel.BEGINNER).value
            if hasattr(getattr(tracker, "current_difficulty", None), "value")
            else str(getattr(tracker, "current_difficulty", "beginner")),
        }

    def restore_tracker(self, tracker: Any, data: Dict[str, Any]) -> None:
        """Restores internal state into an existing CompetencyTracker instance."""
        if not tracker or not data:
            return

        tracker.asked_question_ids = set(data.get("asked_question_ids", []))
        tracker.topic_scores = data.get("topic_scores", {})
        tracker.competency_scores = data.get("competency_scores", {})
        tracker.difficulty_scores = data.get("difficulty_scores", {})
        tracker.demonstrated_concepts = data.get("demonstrated_concepts", [])
        tracker.missing_concepts = data.get("missing_concepts", [])
        tracker.misconceptions = data.get("misconceptions", [])
        tracker.recent_percentages = data.get("recent_percentages", [])

        diff_str = data.get("current_difficulty", "beginner")
        try:
            tracker.current_difficulty = DifficultyLevel(diff_str)
        except Exception:
            tracker.current_difficulty = DifficultyLevel.BEGINNER

    # -------------------------------------------------------------
    # Module 3: Interview Integrity Telemetry & Audit Persistence
    # -------------------------------------------------------------

    def save_integrity_event(self, event: IntegrityEventRecord) -> bool:
        """Persists an observed integrity telemetry event."""
        conn = get_db_connection()
        try:
            with self._lock, conn:
                conn.execute(
                    """
                    INSERT INTO interview_integrity_events (
                        id, session_id, candidate_id, timestamp_offset_seconds, timestamp_iso,
                        event_type, severity, confidence, title, description,
                        recruiter_status, recruiter_notes, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(id) DO UPDATE SET
                        recruiter_status = excluded.recruiter_status,
                        recruiter_notes = excluded.recruiter_notes
                    """,
                    (
                        event.id,
                        event.session_id,
                        event.candidate_id,
                        event.timestamp_offset_seconds,
                        event.timestamp_iso or datetime.now(timezone.utc).isoformat(),
                        event.event_type,
                        event.severity,
                        event.confidence,
                        event.title,
                        event.description,
                        event.recruiter_status,
                        event.recruiter_notes,
                        event.created_at or datetime.now(timezone.utc).isoformat(),
                    ),
                )
            return True
        except Exception as e:
            logger.error("[PERSIST_ERROR] Failed to save integrity event: %s", e)
            return False
        finally:
            conn.close()

    def get_integrity_events(self, session_id: str) -> List[IntegrityEventRecord]:
        """Retrieves chronological integrity events for a session."""
        conn = get_db_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT id, session_id, candidate_id, timestamp_offset_seconds, timestamp_iso,
                       event_type, severity, confidence, title, description,
                       recruiter_status, recruiter_notes, created_at
                FROM interview_integrity_events
                WHERE session_id = ?
                ORDER BY timestamp_offset_seconds ASC, created_at ASC
                """,
                (session_id,),
            )
            records = []
            for row in cur.fetchall():
                records.append(
                    IntegrityEventRecord(
                        id=row["id"],
                        session_id=row["session_id"],
                        candidate_id=row["candidate_id"],
                        timestamp_offset_seconds=float(row["timestamp_offset_seconds"]),
                        timestamp_iso=row["timestamp_iso"],
                        event_type=row["event_type"],
                        severity=row["severity"],
                        confidence=float(row["confidence"]),
                        title=row["title"],
                        description=row["description"],
                        recruiter_status=row["recruiter_status"],
                        recruiter_notes=row["recruiter_notes"],
                        created_at=row["created_at"],
                    )
                )
            return records
        finally:
            conn.close()

    def update_integrity_event_status(
        self, event_id: str, status: str, notes: Optional[str] = None
    ) -> bool:
        """Allows human recruiter to annotate or resolve an integrity event."""
        conn = get_db_connection()
        try:
            with self._lock, conn:
                conn.execute(
                    """
                    UPDATE interview_integrity_events
                    SET recruiter_status = ?, recruiter_notes = coalesce(?, recruiter_notes)
                    WHERE id = ?
                    """,
                    (status, notes, event_id),
                )
            return True
        except Exception as e:
            logger.error("[PERSIST_ERROR] Failed to update integrity event %s: %s", event_id, e)
            return False
        finally:
            conn.close()

    def get_integrity_summary(self, session_id: str) -> IntegritySummary:
        """Aggregates sensor and browser telemetry into non-accusatory integrity summary."""
        events = self.get_integrity_events(session_id)
        focus_loss = sum(1 for e in events if e.event_type in ("focus_loss", "window_blur"))
        tab_switches = sum(1 for e in events if e.event_type == "tab_switch")
        audio_anomalies = sum(1 for e in events if e.event_type == "audio_anomaly")
        stream_interrupts = sum(1 for e in events if e.event_type == "stream_interrupted")
        manual_flags = sum(1 for e in events if e.event_type == "manual_flag")

        pending = sum(1 for e in events if e.recruiter_status == "pending_review")
        benign = sum(1 for e in events if e.recruiter_status in ("verified_benign", "verified_technical"))
        followup = sum(1 for e in events if e.recruiter_status == "requires_followup")

        return IntegritySummary(
            session_id=session_id,
            total_events=len(events),
            focus_loss_count=focus_loss,
            tab_switch_count=tab_switches,
            audio_anomaly_count=audio_anomalies,
            stream_interruption_count=stream_interrupts,
            manual_flags_count=manual_flags,
            pending_review_count=pending,
            verified_benign_count=benign,
            requires_followup_count=followup,
        )

    # -------------------------------------------------------------
    # Module 5: Candidate Decision Intelligence Persistence
    # -------------------------------------------------------------

    def save_candidate_decision(self, decision: CandidateDecisionRecord) -> bool:
        """Persists or updates candidate decision record with rubric synthesis."""
        conn = get_db_connection()
        try:
            with self._lock, conn:
                conn.execute(
                    """
                    INSERT INTO candidate_decisions (
                        session_id, candidate_id, candidate_name, target_role, track,
                        normalized_score, grade, outcome, confidence_score, executive_summary,
                        demonstrated_competencies_json, critical_gaps_json, unvalidated_claims_json,
                        prerequisites_satisfied, integrity_review_needed, evidence_points_count,
                        recruiter_outcome_override, recruiter_notes, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(session_id) DO UPDATE SET
                        outcome = excluded.outcome,
                        normalized_score = excluded.normalized_score,
                        grade = excluded.grade,
                        executive_summary = excluded.executive_summary,
                        demonstrated_competencies_json = excluded.demonstrated_competencies_json,
                        critical_gaps_json = excluded.critical_gaps_json,
                        unvalidated_claims_json = excluded.unvalidated_claims_json,
                        integrity_review_needed = excluded.integrity_review_needed,
                        evidence_points_count = excluded.evidence_points_count,
                        recruiter_outcome_override = coalesce(excluded.recruiter_outcome_override, candidate_decisions.recruiter_outcome_override),
                        recruiter_notes = coalesce(excluded.recruiter_notes, candidate_decisions.recruiter_notes),
                        updated_at = excluded.updated_at
                    """,
                    (
                        decision.session_id,
                        decision.candidate_id,
                        decision.candidate_name,
                        decision.target_role,
                        decision.track,
                        decision.normalized_score,
                        decision.grade,
                        decision.outcome,
                        decision.confidence_score,
                        decision.executive_summary,
                        json.dumps(decision.demonstrated_competencies),
                        json.dumps(decision.critical_gaps),
                        json.dumps(decision.unvalidated_claims),
                        1 if decision.prerequisites_satisfied else 0,
                        1 if decision.integrity_review_needed else 0,
                        decision.evidence_points_count,
                        decision.recruiter_outcome_override,
                        decision.recruiter_notes,
                        decision.created_at or datetime.now(timezone.utc).isoformat(),
                        decision.updated_at or datetime.now(timezone.utc).isoformat(),
                    ),
                )
            return True
        except Exception as e:
            logger.error("[PERSIST_ERROR] Failed to save candidate decision: %s", e)
            return False
        finally:
            conn.close()

    def get_candidate_decision(self, session_id: str) -> Optional[CandidateDecisionRecord]:
        """Retrieves candidate decision record for a session."""
        conn = get_db_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT session_id, candidate_id, candidate_name, target_role, track,
                       normalized_score, grade, outcome, confidence_score, executive_summary,
                       demonstrated_competencies_json, critical_gaps_json, unvalidated_claims_json,
                       prerequisites_satisfied, integrity_review_needed, evidence_points_count,
                       recruiter_outcome_override, recruiter_notes, created_at, updated_at
                FROM candidate_decisions
                WHERE session_id = ?
                """,
                (session_id,),
            )
            row = cur.fetchone()
            if not row:
                return None
            return CandidateDecisionRecord(
                session_id=row["session_id"],
                candidate_id=row["candidate_id"],
                candidate_name=row["candidate_name"],
                target_role=row["target_role"],
                track=row["track"],
                normalized_score=float(row["normalized_score"]),
                grade=row["grade"],
                outcome=row["outcome"],
                confidence_score=float(row["confidence_score"]),
                executive_summary=row["executive_summary"],
                demonstrated_competencies=json.loads(row["demonstrated_competencies_json"] or "[]"),
                critical_gaps=json.loads(row["critical_gaps_json"] or "[]"),
                unvalidated_claims=json.loads(row["unvalidated_claims_json"] or "[]"),
                prerequisites_satisfied=bool(row["prerequisites_satisfied"]),
                integrity_review_needed=bool(row["integrity_review_needed"]),
                evidence_points_count=int(row["evidence_points_count"]),
                recruiter_outcome_override=row["recruiter_outcome_override"],
                recruiter_notes=row["recruiter_notes"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )
        finally:
            conn.close()

    def update_candidate_decision(
        self, session_id: str, outcome: str, notes: Optional[str] = None
    ) -> bool:
        """Updates recruiter outcome override and notes."""
        conn = get_db_connection()
        try:
            with self._lock, conn:
                conn.execute(
                    """
                    UPDATE candidate_decisions
                    SET recruiter_outcome_override = ?,
                        recruiter_notes = coalesce(?, recruiter_notes),
                        updated_at = ?
                    WHERE session_id = ?
                    """,
                    (outcome, notes, datetime.now(timezone.utc).isoformat(), session_id),
                )
            return True
        except Exception as e:
            logger.error("[PERSIST_ERROR] Failed to update candidate decision for %s: %s", session_id, e)
            return False
        finally:
            conn.close()

    def list_candidate_decisions(
        self, target_role: Optional[str] = None
    ) -> List[CandidateDecisionRecord]:
        """Lists candidate decision records for recruiter dashboard comparison."""
        conn = get_db_connection()
        try:
            cur = conn.cursor()
            if target_role:
                cur.execute(
                    """
                    SELECT session_id, candidate_id, candidate_name, target_role, track,
                           normalized_score, grade, outcome, confidence_score, executive_summary,
                           demonstrated_competencies_json, critical_gaps_json, unvalidated_claims_json,
                           prerequisites_satisfied, integrity_review_needed, evidence_points_count,
                           recruiter_outcome_override, recruiter_notes, created_at, updated_at
                    FROM candidate_decisions
                    WHERE target_role = ?
                    ORDER BY updated_at DESC
                    """,
                    (target_role,),
                )
            else:
                cur.execute(
                    """
                    SELECT session_id, candidate_id, candidate_name, target_role, track,
                           normalized_score, grade, outcome, confidence_score, executive_summary,
                           demonstrated_competencies_json, critical_gaps_json, unvalidated_claims_json,
                           prerequisites_satisfied, integrity_review_needed, evidence_points_count,
                           recruiter_outcome_override, recruiter_notes, created_at, updated_at
                    FROM candidate_decisions
                    ORDER BY updated_at DESC
                    """
                )
            results = []
            for row in cur.fetchall():
                results.append(
                    CandidateDecisionRecord(
                        session_id=row["session_id"],
                        candidate_id=row["candidate_id"],
                        candidate_name=row["candidate_name"],
                        target_role=row["target_role"],
                        track=row["track"],
                        normalized_score=float(row["normalized_score"]),
                        grade=row["grade"],
                        outcome=row["outcome"],
                        confidence_score=float(row["confidence_score"]),
                        executive_summary=row["executive_summary"],
                        demonstrated_competencies=json.loads(row["demonstrated_competencies_json"] or "[]"),
                        critical_gaps=json.loads(row["critical_gaps_json"] or "[]"),
                        unvalidated_claims=json.loads(row["unvalidated_claims_json"] or "[]"),
                        prerequisites_satisfied=bool(row["prerequisites_satisfied"]),
                        integrity_review_needed=bool(row["integrity_review_needed"]),
                        evidence_points_count=int(row["evidence_points_count"]),
                        recruiter_outcome_override=row["recruiter_outcome_override"],
                        recruiter_notes=row["recruiter_notes"],
                        created_at=row["created_at"],
                        updated_at=row["updated_at"],
                    )
                )
            return results
        finally:
            conn.close()

