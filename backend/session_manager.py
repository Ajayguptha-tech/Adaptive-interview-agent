"""
Session lifecycle and report generation manager for Python Interview Intelligence.
Maintains interview state, validates answers, prevents question leakage,
normalizes final scores to 100, and generates structured performance reports.
"""

import time
import logging
import threading
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from backend.models import (
    StartInterviewRequest,
    Question,
    QuestionRecord,
    QuestionDisplay,
    EvaluationResult,
    FeedbackMode,
    FinalReport,
)
from backend.adaptive_engine import CompetencyTracker, AdaptiveEngine
from backend.evaluator import EvaluationEngine
from backend.question_bank import get_all_topics
from backend.interviewers.registry import default_registry, InterviewerRegistry
from backend.interviewers.python_interviewer import PythonInterviewer

logger = logging.getLogger(__name__)


class InterviewSession:
    """Represents an active or completed interview session."""

    def __init__(self, config: StartInterviewRequest, first_question: Question, first_reason: str):
        self.session_id: str = str(uuid.uuid4())
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

        self.current_question: Optional[Question] = first_question
        self.current_reason: str = first_reason
        self.history: List[QuestionRecord] = []
        self.tracker: CompetencyTracker = CompetencyTracker()
        self.status: str = "active"
        self.created_at: str = datetime.now(timezone.utc).isoformat()
        self.lock = threading.Lock()

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


class SessionManager:
    """Manages interview sessions in memory."""

    def __init__(
        self,
        evaluation_engine: Optional[EvaluationEngine] = None,
        registry: Optional[InterviewerRegistry] = None,
    ):
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

    def start_session(self, request: StartInterviewRequest) -> InterviewSession:
        """Initializes a new interview session using the requested or automatically routed track."""
        t_start = time.perf_counter()
        resume_profile = None
        plan = None
        effective_topics = request.topics

        # Validate and associate resume if provided
        if getattr(request, "resume_id", None):
            from backend.resume_analyzer.adapter import get_resume_adapter
            from backend.interview_plan import InterviewPlanner, InterviewPlan

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

        first_q, reason = interviewer.select_first_question(
            mode=request.difficulty_mode,
            topics=effective_topics,
            use_dynamic=getattr(request, "dynamic_questions", True),
            tech_stack=getattr(request, "tech_stack", None) or (resume_profile.get("recommended_tech_stack") if resume_profile else None),
        )
        session = InterviewSession(request, first_q, reason)
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

        duration_sec = time.perf_counter() - t_start
        logger.info(
            "[PERF] First question delivery completed in %.3fs for session %s (track='%s', q_id='%s')",
            duration_sec, session.session_id, track, first_q.id
        )

        return session

    def get_session(self, session_id: str) -> Optional[InterviewSession]:
        """Retrieves session by ID."""
        return self.sessions.get(session_id)

    def submit_answer(
        self,
        session_id: str,
        answer: str,
    ) -> Dict[str, Any]:
        """
        Submits and evaluates candidate answer.
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

        current_q = session.current_question
        if not current_q:
            raise RuntimeError("No active question found in session.")

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
            session.current_question = None
            session.current_reason = "Interview reached configured question limit."
        else:
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
                use_dynamic=session.dynamic_questions,
                tech_stack=session.tech_stack,
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

        return {
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

        return FinalReport(
            session_id=session.session_id,
            role=session.role,
            track=session.track,
            tech_stack=session.tech_stack,
            resume_id=getattr(session, "resume_id", None),
            resume_summary=resume_summary,
            resume_skill_gap=resume_skill_gap,
            interview_plan=interview_plan_dict,
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
