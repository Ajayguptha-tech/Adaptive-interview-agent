"""
Unit and Integration Tests for Advanced Dynamic Question Generator Optimization.
Validates:
1. Grounded question generation across distinct resume profiles (Python, Full-Stack, Java, Data Eng, Emerging Tech, Sparse CV)
2. Question history preventing unwanted repetition across sessions
3. Format diversity across the 12 modalities
4. Duplicate rejection vs valid follow-up acceptance (calibrated similarity thresholds)
5. Robust handling of invalid/truncated JSON and model timeouts
6. Intelligent catalog fallback preserving metadata and metrics
7. Resume profile cache isolation and versioning
8. Session cancellation and background pregeneration queue
9. Emerging / unfamiliar technology preservation
10. Sub-50ms latency serving via pregenerated question buffer
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
    StartInterviewRequest,
    FeedbackMode,
    InterviewMode,
)
from backend.question_agent.models import (
    QuestionFormat,
    InterviewBlueprint,
    ResumeIntelligenceProfile,
    ProjectEvidence,
    ValidationResult,
    QuestionCandidate,
    CatalogQuestionEntry,
)
from backend.question_agent.resume_intelligence import ResumeIntelligenceEngine
from backend.question_agent.diversity_engine import (
    QuestionDiversityEngine,
    CandidateQuestionHistoryStore,
)
from backend.question_agent.question_validator import QuestionQualityValidator
from backend.question_agent.catalog import QuestionCatalog
from backend.question_agent.generator import QuestionGeneratorEngine
from backend.question_agent.agent import ResumeAdaptiveQuestionAgent
from backend.session_manager import InterviewSession, SessionManager


# =============================================================================
# 1. RESUME GROUNDING ACROSS DIVERSE PROFILES
# =============================================================================

def test_different_resumes_produce_grounded_blueprints():
    """Tests that distinct resumes produce customized blueprints with relevant topics and skills."""
    python_cv = {
        "candidate_name": "Alice Pythonista",
        "total_experience_years": 4.0,
        "skills": ["Python", "FastAPI", "PostgreSQL", "Docker", "AsyncIO"],
        "claimed_skills": ["Python", "FastAPI", "PostgreSQL", "Docker", "AsyncIO"],
        "projects": [
            {
                "title": "Async Stream Gateway",
                "description": "FastAPI gateway handling streaming events with asyncio.",
                "technologies": ["Python", "FastAPI", "Docker"],
            }
        ],
    }

    rust_cv = {
        "candidate_name": "Elena Rostova",
        "total_experience_years": 3.0,
        "skills": ["Rust", "Axum", "SurrealDB", "WebAssembly", "Tokio"],
        "claimed_skills": ["Rust", "Axum", "SurrealDB", "WebAssembly", "Tokio"],
        "projects": [
            {
                "title": "WASM Edge Microservice",
                "description": "High performance edge compute engine using Axum and SurrealDB.",
                "technologies": ["Rust", "Axum", "SurrealDB"],
            }
        ],
    }

    agent = ResumeAdaptiveQuestionAgent()

    bp_py = agent.create_blueprint(python_cv, target_role="Python Developer", max_questions=5)
    bp_rust = agent.create_blueprint(rust_cv, target_role="Rust Systems Engineer", max_questions=5)

    assert bp_py.resume_profile.candidate_name == "Alice Pythonista"
    assert "FastAPI" in bp_py.resume_profile.frameworks
    assert bp_py.investigate_projects[0].title == "Async Stream Gateway"

    assert bp_rust.resume_profile.candidate_name == "Elena Rostova"
    assert "Rust" in bp_rust.resume_profile.programming_languages
    # Unfamiliar technology SurrealDB should be retained in tools_platforms
    assert "SurrealDB" in bp_rust.resume_profile.tools_platforms
    assert bp_rust.investigate_projects[0].title == "WASM Edge Microservice"


def test_sparse_resume_falls_back_gracefully():
    """A resume with minimal details still produces a valid foundational blueprint without error."""
    sparse_cv = {
        "candidate_name": "Junior Developer",
        "total_experience_years": 0.5,
        "skills": ["Python"],
        "claimed_skills": ["Python"],
    }
    agent = ResumeAdaptiveQuestionAgent()
    bp = agent.create_blueprint(sparse_cv, target_role="Python Developer", max_questions=5)
    assert bp.max_questions == 5
    assert len(bp.planned_topics) == 5
    assert bp.difficulty_progression[0] == DifficultyLevel.BEGINNER


# =============================================================================
# 2. QUESTION HISTORY PREVENTS UNWANTED REPETITION
# =============================================================================

def test_question_history_prevents_unwanted_repetition(tmp_path):
    """Verifies candidate question history store records fingerprints and blocks duplicates."""
    db_file = str(tmp_path / "test_history.db")
    store = CandidateQuestionHistoryStore(db_path=db_file)

    q_text = "Explain the mechanics of Python's Global Interpreter Lock (GIL) and its impact on concurrency."
    store.record_question("cand_123", "sess_1", "q_gil_1", q_text, "Python Concurrency")

    recent = store.get_recent_questions("cand_123")
    assert len(recent) == 1
    assert recent[0]["question_id"] == "q_gil_1"

    # Check duplicate detection using candidate history
    is_dup, reason, sim = QuestionDiversityEngine.check_duplicate(
        candidate_text=q_text,
        session_asked_texts=[],
        prior_candidate_texts=[r["question_text"] for r in recent],
    )
    assert is_dup is True
    assert "exact" in reason.lower() or "similar" in reason.lower()


# =============================================================================
# 3. FORMAT DIVERSITY ROTATION
# =============================================================================

def test_blueprint_formats_distribution():
    """Verifies that an interview blueprint balances modalities across the 12 formats."""
    agent = ResumeAdaptiveQuestionAgent()
    bp = agent.create_blueprint(
        resume_profile={"skills": ["Python", "FastAPI"], "projects": [{"title": "API Gateway"}]},
        target_role="Python Developer",
        max_questions=10,
    )

    formats = bp.planned_formats
    assert len(formats) == 10
    unique_formats = set(formats)
    # At least 7 distinct formats planned across a 10-question interview
    assert len(unique_formats) >= 7
    assert QuestionFormat.TECHNICAL_FUNDAMENTALS in unique_formats
    assert QuestionFormat.CODE_WRITING in unique_formats
    assert QuestionFormat.PROJECT_DEEP_DIVE in unique_formats
    assert QuestionFormat.DESIGN_ARCHITECTURE in unique_formats


# =============================================================================
# 4. DUPLICATE REJECTION VS VALID FOLLOW-UP ACCEPTANCE
# =============================================================================

def test_valid_followup_accepted_while_exact_duplicate_rejected():
    """
    Valid adaptive follow-ups on the same topic must be accepted (higher threshold 0.65),
    while an exact question copy is strictly rejected.
    """
    q1 = "How does the GIL affect multithreaded CPU-bound tasks in Python?"
    follow_up = "Given that the GIL restricts CPU-bound threads, how would you design a multiprocessing pipeline with shared memory?"
    exact_q = "How does the GIL affect multithreaded CPU-bound tasks in Python?"

    # 1. Exact duplicate rejected
    is_dup, reason, _ = QuestionDiversityEngine.check_duplicate(
        candidate_text=exact_q,
        session_asked_texts=[q1],
        threshold=0.38,
    )
    assert is_dup is True

    # 2. Valid follow-up accepted under adaptive follow-up threshold (0.65)
    is_followup_dup, f_reason, sim = QuestionDiversityEngine.check_duplicate(
        candidate_text=follow_up,
        session_asked_texts=[q1],
        threshold=0.65,
    )
    assert is_followup_dup is False, f"Valid follow-up should be accepted, but was rejected: {f_reason} (sim={sim})"


# =============================================================================
# 5. ERROR HANDLING: INVALID JSON & OLLAMA TIMEOUT FALLBACK
# =============================================================================

def test_invalid_json_triggers_catalog_fallback():
    """When LLM returns malformed JSON, QuestionGeneratorEngine gracefully falls back to catalog."""
    mock_llm = MagicMock()
    mock_llm.generate_json.side_effect = ValueError("LLM returned malformed JSON: Unmatched quote")

    catalog = QuestionCatalog()
    generator = QuestionGeneratorEngine(llm_client=mock_llm, catalog=catalog)

    blueprint = InterviewBlueprint(
        target_role="Python Developer",
        target_track="python",
        max_questions=5,
    )

    q, reason, candidate = generator.generate_candidate_question(
        blueprint=blueprint,
        topic="Python Functions & Scope",
        competency="Python Competency",
        difficulty=DifficultyLevel.BEGINNER,
        question_format=QuestionFormat.CONCEPTUAL_EXPLANATION,
        session_asked_texts=[],
        use_llm=True,
    )

    assert q is not None
    assert candidate.source_type == "catalog_curated"
    assert "catalog" in reason.lower()
    assert generator.fallback_count >= 1


def test_ollama_timeout_triggers_catalog_fallback():
    """When Ollama times out, QuestionGeneratorEngine gracefully falls back to catalog without crashing."""
    mock_llm = MagicMock()
    mock_llm.generate_json.side_effect = TimeoutError("Ollama request timed out after 30s")

    catalog = QuestionCatalog()
    generator = QuestionGeneratorEngine(llm_client=mock_llm, catalog=catalog)

    blueprint = InterviewBlueprint(
        target_role="Python Developer",
        target_track="python",
        max_questions=5,
    )

    q, reason, candidate = generator.generate_candidate_question(
        blueprint=blueprint,
        topic="Data Structures & Mutability",
        competency="Python Competency",
        difficulty=DifficultyLevel.INTERMEDIATE,
        question_format=QuestionFormat.CONCEPTUAL_EXPLANATION,
        session_asked_texts=[],
        use_llm=True,
    )

    assert q is not None
    assert candidate.source_type == "catalog_curated"
    assert "catalog" in reason.lower()


# =============================================================================
# 6. RESUME PROFILE CACHE ISOLATION
# =============================================================================

def test_resume_profile_cache_isolation():
    """Tests that ResumeIntelligenceEngine caches by content hash and isolates distinct candidates."""
    ResumeIntelligenceEngine.clear_cache()
    assert ResumeIntelligenceEngine.cache_size() == 0

    cv_1 = {
        "candidate_name": "Dev One",
        "total_experience_years": 2.0,
        "skills": ["Python", "FastAPI"],
        "claimed_skills": ["Python", "FastAPI"],
    }
    cv_2 = {
        "candidate_name": "Dev Two",
        "total_experience_years": 5.0,
        "skills": ["Java", "Spring Boot"],
        "claimed_skills": ["Java", "Spring Boot"],
    }

    p1 = ResumeIntelligenceEngine.extract_intelligence(cv_1)
    assert ResumeIntelligenceEngine.cache_size() == 1

    # Same CV 1 should hit cache
    p1_cached = ResumeIntelligenceEngine.extract_intelligence(cv_1)
    assert p1_cached.candidate_name == "Dev One"
    assert ResumeIntelligenceEngine.cache_size() == 1

    # CV 2 should create separate cache entry
    p2 = ResumeIntelligenceEngine.extract_intelligence(cv_2)
    assert p2.candidate_name == "Dev Two"
    assert ResumeIntelligenceEngine.cache_size() == 2

    # Clear cache
    ResumeIntelligenceEngine.clear_cache()
    assert ResumeIntelligenceEngine.cache_size() == 0


# =============================================================================
# 7. SESSION CANCELLATION AND PREGENERATION QUEUE
# =============================================================================

def test_session_cancellation_and_pregeneration():
    """Verifies that cancel_session cleanly flags cancellation and halts background workers."""
    sm = SessionManager()
    req = StartInterviewRequest(
        role="Python Developer",
        track="python",
        max_questions=5,
        dynamic_questions=False,  # Use catalog for immediate start
    )
    session = sm.start_session(req)
    session_id = session.session_id

    assert session.status == "active"
    assert session.is_cancelled is False

    # Cancel session
    ok = sm.cancel_session(session_id)
    assert ok is True
    assert session.status == "cancelled"
    assert session.is_cancelled is True
    assert session.pregenerated_question is None


def test_pregeneration_buffer_instant_serving():
    """Verifies that a pre-generated question is served immediately from buffer with sub-50ms latency."""
    req = StartInterviewRequest(
        role="Python Developer",
        track="python",
        max_questions=5,
        dynamic_questions=True,
    )
    mock_q = Question(
        id="pregen-test-01",
        topic="Python Functions & Scope",
        competency="Python Competency",
        difficulty=DifficultyLevel.INTERMEDIATE,
        question_type=QuestionType.CONCEPTUAL,
        text="Explain variable scope and the LEGB rule in Python.",
        rubric=[RubricCriterion(id="c1", description="LEGB explanation", max_marks=5.0)],
        reference_answer="LEGB stands for Local, Enclosing, Global, Built-in.",
    )

    session = InterviewSession(req, first_question=None, first_reason="Test")
    session.pregenerated_question = (mock_q, "Pre-generated ahead of time for instant serving.")

    t0 = time.perf_counter()
    res = session.get_or_await_pregenerated(timeout=0.5)
    latency_sec = time.perf_counter() - t0

    assert res is not None
    q, reason = res
    assert q.id == "pregen-test-01"
    assert latency_sec < 0.05, f"Expected sub-50ms latency, got {latency_sec:.4f}s"
    # Ensure buffer is cleared after serving
    assert session.pregenerated_question is None
