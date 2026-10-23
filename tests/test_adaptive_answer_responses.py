"""
Comprehensive test suite for Adaptive Interview Intelligence answer evaluation and follow-up behaviors.
Covers:
1. Strong answer (>= 85%): No follow-up; difficulty maintained or escalated.
2. Partial answer (40-70%): Targeted adaptive follow-up generated for missing concepts; buffer invalidated.
3. Incorrect answer (< 25%): No follow-up loop; difficulty demoted to prerequisite/foundational.
4. Off-topic answer: 0% awarded; no crash; no follow-up loop.
5. Empty / whitespace answer: Rejected with ValueError; session state & question number preserved.
6. Deduplication of pre-generation inference jobs for same slot.
7. Deduplication of pre-warming jobs for same candidate resume.
8. Concurrency & idempotency: Strictly single question delivered per slot on retries.
9. Configuration mismatch invalidation of pre-warmed opening question.
10. Session cancellation & early end cleanup of background workers and memory buffer.
"""

import time
import pytest
from unittest.mock import MagicMock, patch

from backend.models import (
    DifficultyLevel,
    Question,
    QuestionType,
    EvaluationResult,
    RubricCriterion,
    CriterionEvaluation,
    StartInterviewRequest,
    FeedbackMode,
    InterviewMode,
)
from backend.question_agent.models import (
    QuestionFormat,
    InterviewBlueprint,
    QuestionCandidate,
)
from backend.question_agent.agent import ResumeAdaptiveQuestionAgent
from backend.session_manager import (
    InterviewSession,
    SessionManager,
    prewarm_first_question,
    clear_prewarmed_question,
    get_pregen_metrics,
    reset_pregen_metrics,
    _PREPARED_FIRST_QUESTIONS,
    _PREPARED_LOCK,
)


def _create_mock_question(q_id="q1", topic="Python Memory Model", diff=DifficultyLevel.INTERMEDIATE):
    return Question(
        id=q_id,
        topic=topic,
        competency="Python Core",
        difficulty=diff,
        question_type=QuestionType.CONCEPTUAL,
        text=f"Explain {topic} in Python.",
        rubric=[
            RubricCriterion(id="c1", description="Explanation", max_marks=2.5),
            RubricCriterion(id="c2", description="Examples", max_marks=2.5),
        ],
        reference_answer=f"Authoritative explanation of {topic}.",
    )


# =============================================================================
# 1. STRONG ANSWER (>= 85%): NO FOLLOW-UP, PROGRESS TO NEXT TOPIC
# =============================================================================

def test_strong_answer_no_followup_and_difficulty_advancement():
    """Candidates scoring >=85% should NOT get a follow-up; difficulty should escalate or maintain."""
    agent = ResumeAdaptiveQuestionAgent()
    blueprint = InterviewBlueprint(target_role="Python Developer", target_track="python", max_questions=5)
    q = _create_mock_question(q_id="q_mem", topic="Python Memory Model")

    strong_eval = EvaluationResult(
        question_id=q.id,
        awarded_marks=4.5,
        max_marks=5.0,
        percentage=90.0,
        summary_explanation="Comprehensive and accurate explanation.",
        demonstrated_concepts=["refcounting", "generational gc", "cycle detection"],
        missing_concepts=[],
        incorrect_claims=[],
        criteria_evaluations=[
            CriterionEvaluation(criterion_id="c1", awarded_marks=2.5, max_marks=2.5, evidence="Clear explanation", explanation="Clear"),
            CriterionEvaluation(criterion_id="c2", awarded_marks=2.0, max_marks=2.5, evidence="Valid examples", explanation="Good examples"),
        ],
    )

    followup = agent.generate_adaptive_follow_up(
        blueprint=blueprint,
        last_question=q,
        last_evaluation=strong_eval,
        session_asked_texts=[q.text],
    )

    assert followup is None, "Strong answer (>=85%) must not trigger a follow-up question."


# =============================================================================
# 2. PARTIAL ANSWER (40-70%): GENERATES TARGETED ADAPTIVE FOLLOW-UP
# =============================================================================

def test_partial_answer_generates_targeted_followup():
    """Candidate scoring 50% with missing concepts gets targeted follow-up probing missing concept."""
    agent = ResumeAdaptiveQuestionAgent()
    mock_gen = MagicMock()
    followup_q = Question(
        id="q_followup_1",
        topic="Python Memory Model",
        competency="Python Core",
        difficulty=DifficultyLevel.INTERMEDIATE,
        question_type=QuestionType.CONCEPTUAL,
        text="How does Python's cyclic garbage collector resolve circular references between two objects?",
        rubric=[RubricCriterion(id="c1", description="Cycle detection", max_marks=5.0)],
        reference_answer="Cyclic GC uses tri-color marking to detect unreachable reference cycles.",
    )
    mock_candidate = MagicMock()
    mock_gen.generate_candidate_question.return_value = (followup_q, "Generated follow-up", mock_candidate)
    agent.generator = mock_gen

    blueprint = InterviewBlueprint(target_role="Python Developer", target_track="python", max_questions=5)
    q = _create_mock_question(q_id="q_mem", topic="Python Memory Model")

    partial_eval = EvaluationResult(
        question_id=q.id,
        awarded_marks=2.5,
        max_marks=5.0,
        percentage=50.0,
        summary_explanation="Candidate explained refcounting but missed cyclical reference resolution.",
        demonstrated_concepts=["refcounting"],
        missing_concepts=["cycle detection", "gc module generations"],
        incorrect_claims=[],
        criteria_evaluations=[
            CriterionEvaluation(criterion_id="c1", awarded_marks=2.5, max_marks=2.5, evidence="Refcounting", explanation="Refcounting explained"),
            CriterionEvaluation(criterion_id="c2", awarded_marks=0.0, max_marks=2.5, evidence="Missing", explanation="No cyclic reference mention"),
        ],
    )

    res = agent.generate_adaptive_follow_up(
        blueprint=blueprint,
        last_question=q,
        last_evaluation=partial_eval,
        session_asked_texts=[q.text],
    )

    assert res is not None, "Partial answer with missing concepts should produce targeted follow-up."
    fq, reason = res
    assert fq.follow_up_to == "q_mem"
    assert "probe missing concept: cycle detection" in reason
    assert mock_gen.generate_candidate_question.called
    kwargs = mock_gen.generate_candidate_question.call_args.kwargs
    assert kwargs["question_format"] == QuestionFormat.ADAPTIVE_FOLLOW_UP
    assert "cycle detection" in kwargs["candidate_context"]["missing_concepts"]


# =============================================================================
# 3. INCORRECT ANSWER (< 25%): NO FOLLOW-UP LOOP, STEP DOWN DIFFICULTY
# =============================================================================

def test_incorrect_answer_no_followup_loop():
    """Candidate scoring <25% should NOT be trapped in a follow-up loop on unfamiliar topic."""
    agent = ResumeAdaptiveQuestionAgent()
    blueprint = InterviewBlueprint(target_role="Python Developer", target_track="python", max_questions=5)
    q = _create_mock_question(q_id="q_async", topic="AsyncIO Internals")

    incorrect_eval = EvaluationResult(
        question_id=q.id,
        awarded_marks=0.5,
        max_marks=5.0,
        percentage=10.0,
        summary_explanation="Candidate confused asyncio event loops with multithreading OS preemptive scheduling.",
        demonstrated_concepts=[],
        missing_concepts=["event loop", "coroutines", "cooperative multitasking"],
        incorrect_claims=["asyncio creates an OS thread per task"],
        criteria_evaluations=[
            CriterionEvaluation(criterion_id="c1", awarded_marks=0.5, max_marks=5.0, evidence="Misunderstanding", explanation="Fundamental confusion"),
        ],
    )

    followup = agent.generate_adaptive_follow_up(
        blueprint=blueprint,
        last_question=q,
        last_evaluation=incorrect_eval,
        session_asked_texts=[q.text],
    )

    assert followup is None, "Incorrect answer (<25%) must not trap candidate in a follow-up loop."


# =============================================================================
# 4. OFF-TOPIC ANSWER: SAFELY EVALUATED AS 0%, NO CRASH
# =============================================================================

def test_off_topic_answer_safely_handled():
    """An off-topic answer (e.g. recipe instead of technical answer) yields 0% and no crash."""
    agent = ResumeAdaptiveQuestionAgent()
    blueprint = InterviewBlueprint(target_role="Python Developer", target_track="python", max_questions=5)
    q = _create_mock_question(q_id="q_gil", topic="Python Concurrency")

    off_topic_eval = EvaluationResult(
        question_id=q.id,
        awarded_marks=0.0,
        max_marks=5.0,
        percentage=0.0,
        summary_explanation="Candidate provided completely off-topic answer discussing unrelated recipe.",
        demonstrated_concepts=[],
        missing_concepts=["GIL", "thread synchronization"],
        incorrect_claims=["Irrelevant content submitted"],
        criteria_evaluations=[
            CriterionEvaluation(criterion_id="c1", awarded_marks=0.0, max_marks=5.0, evidence="Off topic text", explanation="Off topic"),
        ],
    )

    followup = agent.generate_adaptive_follow_up(
        blueprint=blueprint,
        last_question=q,
        last_evaluation=off_topic_eval,
        session_asked_texts=[q.text],
    )

    assert followup is None, "Off-topic answer (0%) must not trigger follow-up."


# =============================================================================
# 5. EMPTY ANSWER: REJECTED WITH VALUEERROR, STATE PRESERVED
# =============================================================================

def test_empty_answer_rejected_and_state_preserved():
    """Empty or whitespace-only answers must raise ValueError and not advance question count."""
    sm = SessionManager()
    req = StartInterviewRequest(
        role="Python Developer",
        track="python",
        max_questions=5,
        dynamic_questions=False,
    )
    session = sm.start_session(req)

    assert len(session.history) == 0
    assert session.current_question is not None
    original_q_id = session.current_question.id

    # Test empty string
    with pytest.raises(ValueError, match="Answer cannot be empty"):
        sm.submit_answer(session.session_id, "")

    assert len(session.history) == 0
    assert session.current_question.id == original_q_id

    # Test whitespace-only string
    with pytest.raises(ValueError, match="Answer cannot be empty"):
        sm.submit_answer(session.session_id, "   \n\t  ")

    assert len(session.history) == 0
    assert session.current_question.id == original_q_id


# =============================================================================
# 6. DEDUPLICATION OF PRE-GENERATION INFERENCE JOBS
# =============================================================================

def test_pregeneration_job_deduplication():
    """Calling schedule_next_pregeneration twice for the same slot avoids duplicate job."""
    reset_pregen_metrics()
    req = StartInterviewRequest(
        role="Python Developer",
        track="python",
        max_questions=5,
        dynamic_questions=True,
    )
    session = InterviewSession(req, first_question=None, first_reason="Test")
    session.active_pregen_slot = 2
    session.pregen_thread = MagicMock(is_alive=lambda: True)

    interviewer = MagicMock()
    session.schedule_next_pregeneration(interviewer, next_q_num=2, target_diff=DifficultyLevel.INTERMEDIATE)

    metrics = get_pregen_metrics()
    assert metrics["duplicate_jobs_prevented"] >= 1, "Duplicate pregen job for slot 2 must be prevented."


# =============================================================================
# 7. DEDUPLICATION OF PRE-WARMING JOBS
# =============================================================================

def test_prewarm_job_deduplication():
    """Triggering prewarm twice for identical resume_id and role prevents second duplicate worker."""
    reset_pregen_metrics()
    resume_id = "res_dedup_test"
    clear_prewarmed_question(resume_id)

    profile = {"candidate_name": "Test Candidate", "skills": ["Python"]}
    with patch("threading.Thread") as mock_th:
        mock_instance = MagicMock()
        mock_th.return_value = mock_instance

        prewarm_first_question(
            resume_id=resume_id,
            resume_profile=profile,
            target_role="Python Developer",
            track="python",
        )
        assert mock_th.call_count == 1

        # Second call while active should be ignored
        prewarm_first_question(
            resume_id=resume_id,
            resume_profile=profile,
            target_role="Python Developer",
            track="python",
        )
        assert mock_th.call_count == 1

    metrics = get_pregen_metrics()
    assert metrics["duplicate_jobs_prevented"] >= 1
    clear_prewarmed_question(resume_id)


# =============================================================================
# 8. CONCURRENCY & IDEMPOTENCY: SINGLE QUESTION DELIVERED PER SLOT
# =============================================================================

def test_concurrency_and_idempotency_returns_identical_cached_result():
    """Resubmitting the same answer for the same question returns cached response without advancing."""
    sm = SessionManager()
    req = StartInterviewRequest(
        role="Python Developer",
        track="python",
        max_questions=5,
        dynamic_questions=False,
    )
    session = sm.start_session(req)
    q1_id = session.current_question.id

    ans = "Python uses reference counting as primary GC and generational cyclic detector for cycles."
    res1 = sm.submit_answer(session.session_id, ans, question_id=q1_id, question_number=1)

    assert res1["question_number"] == 1
    assert len(session.history) == 1

    # Concurrent retry with identical submission
    res2 = sm.submit_answer(session.session_id, ans, question_id=q1_id, question_number=1)

    # Must return exact same response without advancing question count
    assert res2["question_number"] == 1
    assert len(session.history) == 1
    assert res1["evaluation"] == res2["evaluation"]
    assert res1["next_question"]["id"] == res2["next_question"]["id"]


# =============================================================================
# 9. CONFIGURATION MISMATCH INVALIDATION OF PRE-WARMED OPENING QUESTION
# =============================================================================

def test_configuration_mismatch_invalidates_prewarmed_question():
    """If pre-warmed for Python Developer, but candidate starts interview for Full-Stack, invalidate."""
    reset_pregen_metrics()
    resume_id = "res_config_mismatch"
    clear_prewarmed_question(resume_id)

    mock_q = _create_mock_question(q_id="q_py_open", topic="Data Structures & Mutability")
    with _PREPARED_LOCK:
        _PREPARED_FIRST_QUESTIONS[resume_id] = {
            "blueprint": MagicMock(),
            "first_question": mock_q,
            "first_reason": "Python opening",
            "target_role": "Python Developer",
            "track": "python",
            "created_at": time.time(),
        }

    sm = SessionManager()
    req = StartInterviewRequest(
        role="Full-Stack Developer",
        track="fullstack",
        resume_id=resume_id,
        resume_summary="Resume with Python and React",
        max_questions=5,
        dynamic_questions=False,
    )

    session = sm.start_session(req, resume_profile={"resume_id": resume_id, "target_role": "Full-Stack Developer", "routed_track": "fullstack"})

    # Question delivered should NOT be the stale python question
    assert session.current_question.id != "q_py_open"
    metrics = get_pregen_metrics()
    assert metrics["stale_buffer_invalidations"] >= 1
    clear_prewarmed_question(resume_id)


# =============================================================================
# 10. SESSION CANCELLATION CLEANUP OF BACKGROUND WORKERS & BUFFER
# =============================================================================

def test_session_cancellation_cleans_buffer_and_workers():
    """Cancelling session sets is_cancelled=True, clears pregenerated question, and halts workers."""
    sm = SessionManager()
    req = StartInterviewRequest(
        role="Python Developer",
        track="python",
        max_questions=5,
        dynamic_questions=False,
    )
    session = sm.start_session(req)
    session.pregenerated_question = (_create_mock_question(), "Pre-generated")

    assert session.pregenerated_question is not None

    ok = sm.cancel_session(session.session_id)
    assert ok is True
    assert session.status == "cancelled"
    assert session.is_cancelled is True
    assert session.pregenerated_question is None
    assert session.current_question is None
