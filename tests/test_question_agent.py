"""
Comprehensive Unit & Integration Test Suite for Resume Intelligence & Adaptive Question Generation Agent.
Tests all 17 core requirements:
1. Resume skills extracted and passed into question generation
2. Questions are relevant to selected role
3. Resume project details influence question selection
4. Exact duplicate questions are rejected (Layer 1)
5. Semantically repetitive questions are rejected (Layer 2)
6. New question candidates are selected when duplicates are rejected (Layer 5)
7. Different sessions maintain isolated state (Layer 3)
8. Recent question history influences later interviews (Layer 4)
9. Concurrent sessions do not corrupt each other's history
10. Python and Full Stack questions remain correctly separated
11. Mock and Main interview modes retain intended behavior
12. 5–10 question limit is strictly enforced
13. Malformed model output is handled safely
14. Model timeouts and unavailable Ollama trigger bounded fallback behavior (Layer 6)
15. Adaptive follow-ups reflect previous answer and evaluation
16. Final reports remain accurate
17. Integration with FastAPI test client
"""

import json
import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

from backend.main import app
from backend.models import (
    DifficultyLevel,
    Question,
    QuestionType,
    EvaluationResult,
    RubricCriterion,
)
from backend.question_agent.models import (
    QuestionFormat,
    InterviewBlueprint,
    ResumeIntelligenceProfile,
    ProjectEvidence,
    ValidationResult,
)
from backend.question_agent.resume_intelligence import ResumeIntelligenceEngine
from backend.question_agent.diversity_engine import (
    QuestionDiversityEngine,
    CandidateQuestionHistoryStore,
)
from backend.question_agent.question_validator import QuestionQualityValidator
from backend.question_agent.catalog import QuestionCatalog
from backend.question_agent.generator import QuestionGeneratorEngine
from backend.question_agent.agent import ResumeAdaptiveQuestionAgent, default_question_agent

client = TestClient(app)


# =============================================================================
# TEST 1: RESUME SKILLS ARE EXTRACTED AND PASSED INTO BLUEPRINT
# =============================================================================

def test_resume_skills_extracted_and_passed_into_blueprint():
    sample_resume = {
        "candidate_name": "Sarah Connor",
        "total_experience_years": 3.5,
        "skills": ["Python", "FastAPI", "PostgreSQL", "Docker", "AsyncIO", "Redis"],
        "claimed_skills": ["Python", "FastAPI", "PostgreSQL", "Docker", "AsyncIO", "Redis"],
        "skill_evidence": [
            {"skill": "FastAPI", "confidence": 0.9, "evidence_snippet": "Built REST APIs with FastAPI microservices."},
            {"skill": "PostgreSQL", "confidence": 0.85, "evidence_snippet": "Designed PostgreSQL relational schemas with indexed queries."},
        ],
        "projects": [
            {
                "title": "Real-Time Telemetry Pipeline",
                "description": "High throughput telemetry pipeline handling 10k events/sec with FastAPI and Redis.",
                "technologies": ["Python", "FastAPI", "Redis", "Docker"],
            }
        ],
    }

    profile = ResumeIntelligenceEngine.extract_intelligence(sample_resume)
    assert profile.candidate_name == "Sarah Connor"
    assert "Python" in profile.programming_languages
    assert "FastAPI" in profile.frameworks
    assert "Docker" in profile.tools_platforms
    assert len(profile.projects) == 1
    assert profile.projects[0].title == "Real-Time Telemetry Pipeline"

    # Blueprint creation reflects extracted skills
    agent = ResumeAdaptiveQuestionAgent()
    blueprint = agent.create_blueprint(
        resume_profile=sample_resume,
        target_role="Python Developer",
        interview_mode="mock",
        max_questions=5,
    )
    assert blueprint.max_questions == 5
    assert len(blueprint.planned_topics) == 5
    assert blueprint.resume_profile is not None
    assert "FastAPI" in blueprint.resume_profile.frameworks


# =============================================================================
# TEST 2: QUESTIONS ARE RELEVANT TO THE SELECTED ROLE
# =============================================================================

def test_questions_role_relevance():
    python_q = Question(
        id="py-test-01",
        topic="Concurrency & GIL",
        competency="Python Concurrency",
        difficulty=DifficultyLevel.INTERMEDIATE,
        question_type=QuestionType.CONCEPTUAL,
        text="Explain how the Global Interpreter Lock (GIL) affects multithreaded CPU bound programs in CPython.",
        rubric=[
            RubricCriterion(id="c1", description="GIL mechanics", max_marks=2.5, evidence_guide="Mentions single thread bytecode execution"),
            RubricCriterion(id="c2", description="CPU vs IO", max_marks=2.5, evidence_guide="Contrasts CPU vs IO bound concurrency"),
        ],
        expected_concepts=["GIL allows one thread to execute Python bytecode at a time."],
    )

    # Valid Python question
    val_py = QuestionQualityValidator.validate_question(
        question=python_q,
        expected_format=QuestionFormat.CONCEPTUAL_EXPLANATION,
        role="Python Developer",
        track="python",
    )
    assert val_py.is_valid is True
    assert val_py.role_relevant is True

    # Leaked Frontend question in Python track should be rejected
    leaked_q = Question(
        id="leaked-01",
        topic="Frontend Layout",
        competency="CSS",
        difficulty=DifficultyLevel.BEGINNER,
        question_type=QuestionType.CONCEPTUAL,
        text="Explain how a React component re-renders when using JSX with Tailwind CSS.",
        rubric=[
            RubricCriterion(id="c1", description="JSX", max_marks=2.5, evidence_guide="Describes JSX rendering"),
            RubricCriterion(id="c2", description="CSS", max_marks=2.5, evidence_guide="Mentions Tailwind classes"),
        ],
        expected_concepts=["React component virtual DOM diffing."],
    )
    val_leaked = QuestionQualityValidator.validate_question(
        question=leaked_q,
        expected_format=QuestionFormat.CONCEPTUAL_EXPLANATION,
        role="Python Developer",
        track="python",
    )
    assert val_leaked.is_valid is False
    assert val_leaked.role_relevant is False


# =============================================================================
# TEST 3: RESUME PROJECT DETAILS INFLUENCE QUESTION SELECTION
# =============================================================================

def test_resume_project_details_influence_question_selection():
    sample_resume = {
        "candidate_name": "Dev",
        "skills": ["Python", "FastAPI", "Docker"],
        "projects": [
            {
                "title": "Cloud Image Converter",
                "description": "Distributed converter worker utilizing Celery, Redis, and FastAPI.",
                "technologies": ["FastAPI", "Celery", "Redis"],
            }
        ],
    }

    mock_llm = MagicMock()
    mock_llm.generate_json.return_value = {
        "topic": "System Integration",
        "competency": "Architecture",
        "difficulty": "intermediate",
        "question_type": "scenario",
        "text": "In your 'Cloud Image Converter' project, how did you handle asynchronous task timeouts with Celery and Redis?",
        "expected_concepts": ["Celery time_limit and soft_time_limit configurations."],
        "rubric": [
            {"id": "c1", "description": "Celery timeout config", "max_marks": 2.5, "evidence_guide": "Mentions soft_time_limit"},
            {"id": "c2", "description": "Redis broker behavior", "max_marks": 2.5, "evidence_guide": "Explains dead letter queues"},
        ],
    }

    agent = ResumeAdaptiveQuestionAgent(llm_client=mock_llm)
    blueprint = agent.create_blueprint(resume_profile=sample_resume, max_questions=5)

    # Slot 3 is programmed as PROJECT_DEEP_DIVE
    q, reason = agent.select_or_generate_question(
        blueprint=blueprint,
        topic="Asyncio & Coroutines",
        competency="Python Concurrency",
        difficulty=DifficultyLevel.INTERMEDIATE,
        question_number=3,
        session_asked_texts=[],
        use_dynamic=True,
    )

    assert "Cloud Image Converter" in q.text
    # Verify prompt received project grounding
    called_prompt = mock_llm.generate_json.call_args[1]["prompt"]
    assert "Cloud Image Converter" in called_prompt
    assert "Celery" in called_prompt


# =============================================================================
# TEST 4: EXACT DUPLICATE QUESTIONS ARE REJECTED (LAYER 1)
# =============================================================================

def test_exact_duplicate_rejected():
    q_original = "What is the difference between a list and a tuple in Python regarding mutability?"
    # Formatted with varying whitespace, uppercase, and punctuation
    q_duplicate = "   WHAT IS THE DIFFERENCE BETWEEN A LIST AND A TUPLE IN PYTHON REGARDING MUTABILITY???   \n"

    is_dup, reason, sim = QuestionDiversityEngine.check_duplicate(
        candidate_text=q_duplicate,
        session_asked_texts=[q_original],
    )

    assert is_dup is True
    assert "Exact duplicate" in reason or sim == 1.0


# =============================================================================
# TEST 5: SEMANTICALLY REPETITIVE QUESTIONS ARE REJECTED (LAYER 2)
# =============================================================================

def test_semantic_duplicate_rejected():
    q_gil_1 = "Explain how the Global Interpreter Lock (GIL) impacts CPU-bound multithreaded performance in CPython."
    q_gil_2 = "How does the GIL in Python affect CPU intensive multithreading execution across multiple cores?"

    sim = QuestionDiversityEngine.compute_similarity(q_gil_1, q_gil_2)
    assert sim >= 0.38

    is_dup, reason, _ = QuestionDiversityEngine.check_duplicate(
        candidate_text=q_gil_2,
        session_asked_texts=[q_gil_1],
        threshold=0.38,
    )
    assert is_dup is True
    assert "Semantically redundant" in reason or "Too similar" in reason

    # Completely distinct questions must NOT be marked duplicate
    q_sql = "Explain the difference between an INNER JOIN and a LEFT JOIN in PostgreSQL."
    is_dup_distinct, _, _ = QuestionDiversityEngine.check_duplicate(
        candidate_text=q_sql,
        session_asked_texts=[q_gil_1],
    )
    assert is_dup_distinct is False


# =============================================================================
# TEST 6: NEW CANDIDATE SELECTED WHEN DUPLICATES ARE REJECTED (LAYER 5)
# =============================================================================

def test_new_candidate_selected_on_duplicate_rejection():
    asked_prev = "What is the difference between a list and a tuple in Python?"

    # Attempt 1 returns duplicate
    dup_resp = {
        "topic": "Data Structures & Mutability",
        "competency": "Python",
        "difficulty": "beginner",
        "question_type": "conceptual",
        "text": "Explain the difference between Python list and tuple regarding mutability.",
        "expected_concepts": ["Lists mutable, tuples immutable"],
        "rubric": [
            {"id": "c1", "description": "Mutability", "max_marks": 2.5, "evidence_guide": "Details"},
            {"id": "c2", "description": "Syntax", "max_marks": 2.5, "evidence_guide": "Details"},
        ],
    }

    # Attempt 2 returns fresh unique question
    fresh_resp = {
        "topic": "Data Structures & Mutability",
        "competency": "Python",
        "difficulty": "beginner",
        "question_type": "conceptual",
        "text": "How do Python dictionaries handle hash collisions internally using open addressing?",
        "expected_concepts": ["Hash collision probing with perturb index."],
        "rubric": [
            {"id": "c1", "description": "Hash lookup", "max_marks": 2.5, "evidence_guide": "Details"},
            {"id": "c2", "description": "Perturb resolution", "max_marks": 2.5, "evidence_guide": "Details"},
        ],
    }

    mock_llm = MagicMock()
    mock_llm.generate_json.side_effect = [dup_resp, fresh_resp]

    agent = ResumeAdaptiveQuestionAgent(llm_client=mock_llm)
    blueprint = agent.create_blueprint(max_questions=5)

    q, reason = agent.select_or_generate_question(
        blueprint=blueprint,
        topic="Data Structures & Mutability",
        competency="Python",
        difficulty=DifficultyLevel.BEGINNER,
        question_number=1,
        session_asked_texts=[asked_prev],
        use_dynamic=True,
    )

    # Must pick the fresh dictionary question
    assert "dictionaries handle hash collisions" in q.text
    assert mock_llm.generate_json.call_count == 2


# =============================================================================
# TEST 7: DIFFERENT SESSIONS MAINTAIN ISOLATED STATE (LAYER 3)
# =============================================================================

def test_session_isolation():
    res1 = client.post("/api/interview/start", json={"track": "python", "max_questions": 5, "dynamic_questions": False})
    res2 = client.post("/api/interview/start", json={"track": "python", "max_questions": 5, "dynamic_questions": False})

    sid1 = res1.json()["session_id"]
    sid2 = res2.json()["session_id"]

    assert sid1 != sid2

    # Answer in session 1
    ans_res = client.post(f"/api/interview/{sid1}/answer", json={"answer": "Lists are mutable, tuples are immutable sequence containers."})
    assert ans_res.status_code == 200
    assert ans_res.json()["question_number"] == 1

    # Session 2 must remain at question 1 with empty history
    status2 = client.get(f"/api/interview/{sid2}/status")
    assert status2.status_code == 200
    assert status2.json()["question_number"] == 1


# =============================================================================
# TEST 8: RECENT QUESTION HISTORY INFLUENCES LATER INTERVIEWS (LAYER 4)
# =============================================================================

def test_cross_session_candidate_history(tmp_path):
    db_file = str(tmp_path / "test_history.db")
    store = CandidateQuestionHistoryStore(db_path=db_file)

    candidate_id = "candidate_12345"
    q_text = "Explain the mechanics of Python's memory management and garbage collection."

    store.record_question(
        candidate_id=candidate_id,
        session_id="session_01",
        question_id="py-gc-001",
        question_text=q_text,
        topic="Memory Management",
    )

    # Candidate 12345 has history
    recent = store.get_recent_questions(candidate_id)
    assert len(recent) == 1
    assert recent[0]["question_id"] == "py-gc-001"

    # Other candidate has isolated zero history
    other_recent = store.get_recent_questions("other_candidate_99999")
    assert len(other_recent) == 0


# =============================================================================
# TEST 9: CONCURRENT SESSIONS DO NOT CORRUPT HISTORY
# =============================================================================

def test_concurrent_sessions_thread_safety(tmp_path):
    import concurrent.futures
    db_file = str(tmp_path / "concurrent.db")
    store = CandidateQuestionHistoryStore(db_path=db_file)

    def record_job(idx):
        store.record_question(
            candidate_id=f"cand_{idx % 4}",
            session_id=f"sess_{idx}",
            question_id=f"q_{idx}",
            question_text=f"Sample Question Number {idx} about technical topic",
            topic="Topic",
        )

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        futures = [executor.submit(record_job, i) for i in range(40)]
        for f in concurrent.futures.as_completed(futures):
            f.result()

    # Verify all records stored cleanly without database locks or corruption
    records_cand0 = store.get_recent_questions("cand_0", limit=100)
    assert len(records_cand0) == 10


# =============================================================================
# TEST 10: PYTHON AND FULL STACK QUESTIONS REMAIN SEPARATED
# =============================================================================

def test_python_and_fullstack_track_separation():
    # Python session
    res_py = client.post("/api/interview/start", json={"track": "python", "max_questions": 5, "dynamic_questions": False})
    data_py = res_py.json()
    assert data_py["track"] == "python"
    assert data_py["language"] == "python"

    # Fullstack session
    res_fs = client.post("/api/interview/start", json={"track": "fullstack", "max_questions": 5, "dynamic_questions": False})
    data_fs = res_fs.json()
    assert data_fs["track"] == "fullstack"
    assert data_fs["language"] in ["javascript", "html", "css", "sql"]


# =============================================================================
# TEST 11: MOCK AND MAIN INTERVIEW MODES RETAIN INTENDED BEHAVIOR
# =============================================================================

def test_mock_and_main_modes():
    # Predefined / Main mode sets dynamic_questions=False
    res_pre = client.post("/api/interview/start", json={"mode": "predefined", "max_questions": 5})
    assert res_pre.json()["dynamic_questions"] is False

    # Mock mode sets dynamic_questions=True
    res_mock = client.post("/api/interview/start", json={"mode": "mock", "max_questions": 5})
    assert res_mock.json()["dynamic_questions"] is True


# =============================================================================
# TEST 12: 5 TO 10 QUESTION LIMIT IS STRICTLY ENFORCED
# =============================================================================

def test_enforce_5_to_10_question_limit():
    # Under 5 rejected
    res_low = client.post("/api/interview/prepare", json={"resume_id": "fake", "max_questions": 3})
    assert res_low.status_code == 422

    # Over 10 rejected
    res_high = client.post("/api/interview/prepare", json={"resume_id": "fake", "max_questions": 15})
    assert res_high.status_code == 422

    # Blueprint enforces bounds
    agent = ResumeAdaptiveQuestionAgent()
    bp_low = agent.create_blueprint(max_questions=2)
    assert bp_low.max_questions == 5

    bp_high = agent.create_blueprint(max_questions=25)
    assert bp_high.max_questions == 10


# =============================================================================
# TEST 13: MALFORMED MODEL OUTPUT IS HANDLED SAFELY
# =============================================================================

def test_malformed_model_output_handled_safely():
    mock_llm = MagicMock()
    # Model returns broken dictionary or missing rubric
    mock_llm.generate_json.return_value = {
        "text": "",  # Empty text
    }

    agent = ResumeAdaptiveQuestionAgent(llm_client=mock_llm)
    blueprint = agent.create_blueprint(max_questions=5)

    # Must not crash, should fall back cleanly
    q, reason = agent.select_or_generate_question(
        blueprint=blueprint,
        topic="Asyncio & Coroutines",
        competency="Python",
        difficulty=DifficultyLevel.INTERMEDIATE,
        question_number=1,
        session_asked_texts=[],
        use_dynamic=True,
    )

    assert q is not None
    assert len(q.text) > 20
    assert len(q.rubric) >= 2


# =============================================================================
# TEST 14: MODEL TIMEOUT AND OFFLINE BOUNDED FALLBACK BEHAVIOR (LAYER 6)
# =============================================================================

def test_model_timeout_and_offline_bounded_fallback():
    mock_llm = MagicMock()
    # LLM client raises connection/timeout error
    mock_llm.generate_json.side_effect = TimeoutError("Ollama service timed out after 15000ms")

    agent = ResumeAdaptiveQuestionAgent(llm_client=mock_llm)
    blueprint = agent.create_blueprint(max_questions=5)

    # Must gracefully fall back to QuestionCatalog
    q, reason = agent.select_or_generate_question(
        blueprint=blueprint,
        topic="Data Structures & Mutability",
        competency="Python Fundamentals",
        difficulty=DifficultyLevel.BEGINNER,
        question_number=1,
        session_asked_texts=[],
        use_dynamic=True,
    )

    assert q is not None
    assert "catalog" in reason.lower()
    assert agent.generator.fallback_count >= 1


# =============================================================================
# TEST 15: ADAPTIVE FOLLOW-UPS REFLECT PREVIOUS ANSWER AND EVALUATION
# =============================================================================

def test_adaptive_follow_up_reflects_answer_and_evaluation():
    prev_q = Question(
        id="py-prev-001",
        topic="Asyncio & Coroutines",
        competency="Concurrency",
        difficulty=DifficultyLevel.INTERMEDIATE,
        question_type=QuestionType.CONCEPTUAL,
        text="Explain how Python's event loop coordinates coroutines with async and await.",
        rubric=[RubricCriterion(id="c1", description="Event loop", max_marks=5.0, evidence_guide="Details")],
    )

    from backend.models import CriterionEvaluation
    eval_result = EvaluationResult(
        question_id="py-prev-001",
        awarded_marks=2.5,
        max_marks=5.0,
        percentage=50.0,
        criteria_evaluations=[
            CriterionEvaluation(
                criterion_id="c1",
                awarded_marks=2.5,
                max_marks=5.0,
                evidence="Described async syntax",
                explanation="Missed task scheduling semantics",
            )
        ],
        summary_explanation="Candidate explained async/await syntax but missed task scheduling semantics.",
        missing_concepts=["Event loop task queue and cooperative yield via await"],
        incorrect_claims=[],
        is_ambiguous=False,
    )

    mock_llm = MagicMock()
    mock_llm.generate_json.return_value = {
        "topic": "Asyncio & Coroutines",
        "competency": "Concurrency",
        "difficulty": "intermediate",
        "question_type": "follow_up",
        "text": "Following up on your explanation, what happens inside the event loop when a coroutine yields control during an I/O operation?",
        "expected_concepts": ["Task yields control back to selector/event loop."],
        "rubric": [
            {"id": "c1", "description": "Yielding control", "max_marks": 2.5, "evidence_guide": "Details"},
            {"id": "c2", "description": "Callback registration", "max_marks": 2.5, "evidence_guide": "Details"},
        ],
    }

    agent = ResumeAdaptiveQuestionAgent(llm_client=mock_llm)
    blueprint = agent.create_blueprint(max_questions=5)

    follow_up = agent.generate_adaptive_follow_up(
        blueprint=blueprint,
        last_question=prev_q,
        last_evaluation=eval_result,
        session_asked_texts=[prev_q.text],
    )

    assert follow_up is not None
    q_fu, reason_fu = follow_up
    assert "yields control" in q_fu.text
    assert q_fu.follow_up_to == "py-prev-001"
    assert "Targeted adaptive follow-up" in reason_fu


# =============================================================================
# TEST 16: FINAL REPORT GENERATION ACCURACY
# =============================================================================

def test_final_report_generation_accuracy():
    res = client.post("/api/interview/start", json={"track": "python", "max_questions": 5, "dynamic_questions": False})
    sid = res.json()["session_id"]

    # Submit 1 answer
    client.post(f"/api/interview/{sid}/answer", json={"answer": "Lists are mutable sequences whereas tuples are immutable."})

    # End interview
    end_res = client.post(f"/api/interview/{sid}/end", json={"status": "completed"})
    assert end_res.status_code == 200
    report = end_res.json()["report"]
    assert report["session_id"] == sid
    assert report["questions_completed"] >= 1
    assert "topic_scores" in report


# =============================================================================
# TEST 17: QUESTION AGENT STATS AND BLUEPRINT ENDPOINTS
# =============================================================================

def test_question_agent_endpoints():
    res_stats = client.get("/api/question_agent/stats")
    assert res_stats.status_code == 200
    data = res_stats.json()
    assert "catalog_size" in data
    assert data["catalog_size"] > 0
    assert data["status"] == "active"
