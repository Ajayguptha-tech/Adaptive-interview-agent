"""
Unit and integration tests for LLMClient supporting Google Gemini and Ollama providers,
verifying provider selection, health checking, JSON generation, error sanitization,
API security, and caller compatibility.
"""

import os
import json
from unittest.mock import MagicMock, patch
import pytest
from fastapi.testclient import TestClient

from backend.llm_client import LLMClient, _sanitize_error
from backend.main import app
from backend.evaluator import EvaluationEngine
from backend.question_generator import QuestionGenerator
from backend.question_agent.generator import QuestionGeneratorEngine
from backend.question_agent.catalog import QuestionCatalog
from backend.models import Question, RubricCriterion, DifficultyLevel


# ---------------------------------------------------------------------------
# 1. API Key Sanitization Tests
# ---------------------------------------------------------------------------

def test_sanitize_error_masks_key():
    fake_key = "AIzaSyDummySecretKey1234567890123456"
    raw_error = f"403 Forbidden: Request failed with key {fake_key} on https://generativelanguage.googleapis.com"
    sanitized = _sanitize_error(raw_error, api_key=fake_key)
    assert fake_key not in sanitized
    assert "[REDACTED]" in sanitized


def test_sanitize_error_masks_query_param():
    raw_error = "Error connecting to https://api.google.com?key=some_secret_token_abc123&test=1"
    sanitized = _sanitize_error(raw_error)
    assert "some_secret_token_abc123" not in sanitized
    assert "key=[REDACTED]" in sanitized


# ---------------------------------------------------------------------------
# 2. Provider Selection Tests
# ---------------------------------------------------------------------------

def test_provider_defaults_to_ollama_when_no_gemini_key():
    with patch.dict(os.environ, {}, clear=True):
        client = LLMClient()
        assert client.provider == "ollama"
        assert client.model_name == "qwen2.5:7b"
        assert "11434" in client.endpoint_url


def test_provider_selects_gemini_when_api_key_configured():
    with patch.dict(os.environ, {"GEMINI_API_KEY": "AIzaSyFakeTestKey12345", "GEMINI_MODEL": "gemini-2.5-flash"}, clear=True):
        client = LLMClient()
        assert client.provider == "gemini"
        assert client.model_name == "gemini-2.5-flash"


def test_provider_explicit_override():
    with patch.dict(os.environ, {"GEMINI_API_KEY": "AIzaSyFakeTestKey12345", "LLM_PROVIDER": "ollama"}, clear=True):
        client = LLMClient()
        assert client.provider == "ollama"


# ---------------------------------------------------------------------------
# 3. Health Check Tests
# ---------------------------------------------------------------------------

def test_gemini_health_check_missing_key():
    client = LLMClient(provider="gemini", api_key="")
    health = client.check_health()
    assert health["available"] is False
    assert health["has_required_model"] is False
    assert health["provider"] == "gemini"
    assert "error" in health


def test_gemini_health_check_success():
    client = LLMClient(provider="gemini", api_key="AIzaSyFakeKey")
    mock_genai_client = MagicMock()
    mock_model = MagicMock()
    mock_model.name = "models/gemini-2.5-flash"
    mock_genai_client.models.get.return_value = mock_model
    client._gemini_client = mock_genai_client

    health = client.check_health()
    assert health["available"] is True
    assert health["has_required_model"] is True
    assert health["provider"] == "gemini"
    assert "gemini-2.5-flash" in health["models"]


def test_gemini_health_check_api_error_sanitized():
    secret_key = "AIzaSySecretApiKeyToMask"
    client = LLMClient(provider="gemini", api_key=secret_key)
    mock_genai_client = MagicMock()
    mock_genai_client.models.get.side_effect = Exception(f"API quota exceeded for key={secret_key}")
    client._gemini_client = mock_genai_client

    health = client.check_health()
    assert health["available"] is False
    assert health["has_required_model"] is False
    assert secret_key not in health["error"]
    assert "[REDACTED]" in health["error"]


# ---------------------------------------------------------------------------
# 4. JSON Generation Tests with Gemini
# ---------------------------------------------------------------------------

def test_gemini_generate_json_success():
    client = LLMClient(provider="gemini", api_key="AIzaSyFakeKey")
    mock_genai_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = json.dumps({"score": 95, "feedback": "Excellent answer"})
    mock_usage = MagicMock()
    mock_usage.prompt_token_count = 120
    mock_usage.candidates_token_count = 45
    mock_response.usage_metadata = mock_usage

    mock_genai_client.models.generate_content.return_value = mock_response
    client._gemini_client = mock_genai_client

    result = client.generate_json(prompt="Test prompt", system_prompt="Test sys")
    assert isinstance(result, dict)
    assert result["score"] == 95
    assert result["feedback"] == "Excellent answer"

    # Verify performance stats
    assert client.last_perf_stats["prompt_eval_count"] == 120
    assert client.last_perf_stats["eval_count"] == 45
    assert client.last_perf_stats["total_duration_ms"] >= 0.0


def test_gemini_generate_json_markdown_wrapped():
    client = LLMClient(provider="gemini", api_key="AIzaSyFakeKey")
    mock_genai_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = "```json\n{\"rubric_score\": 4.5, \"verbatim_quote\": \"generator expression\"}\n```"
    mock_response.usage_metadata = None
    mock_genai_client.models.generate_content.return_value = mock_response
    client._gemini_client = mock_genai_client

    result = client.generate_json(prompt="Evaluate answer")
    assert result["rubric_score"] == 4.5
    assert result["verbatim_quote"] == "generator expression"


def test_gemini_generate_json_invalid_json():
    client = LLMClient(provider="gemini", api_key="AIzaSyFakeKey")
    mock_genai_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = "This is not valid JSON content"
    mock_response.usage_metadata = None
    mock_genai_client.models.generate_content.return_value = mock_response
    client._gemini_client = mock_genai_client

    with pytest.raises(ValueError) as excinfo:
        client.generate_json(prompt="Test")
    assert "LLM returned invalid JSON" in str(excinfo.value)


def test_gemini_generate_json_timeout_handling():
    client = LLMClient(provider="gemini", api_key="AIzaSyFakeKey", timeout=10)
    mock_genai_client = MagicMock()
    mock_genai_client.models.generate_content.side_effect = TimeoutError("Request timed out after 10000ms")
    client._gemini_client = mock_genai_client

    with pytest.raises(TimeoutError) as excinfo:
        client.generate_json(prompt="Test timeout")
    assert "timed out after 10s" in str(excinfo.value)


# ---------------------------------------------------------------------------
# 5. FastAPI /api/health Endpoint Integration
# ---------------------------------------------------------------------------

def test_api_health_with_gemini_mocked():
    from backend.main import default_llm_client

    with patch.object(default_llm_client, "check_health") as mock_health:
        mock_health.return_value = {
            "available": True,
            "has_required_model": True,
            "provider": "gemini",
            "models": ["gemini-2.5-flash"],
        }
        test_client = TestClient(app)
        res = test_client.get("/api/health")
        assert res.status_code == 200
        data = res.json()
        assert data["api"] == "running"
        assert data["provider"] == "gemini"
        assert data["status"] == "connected"
        assert data["gemini"] == "connected"
        assert "ollama" in data
        assert data["required_model_available"] is True
        assert "gemini-2.5-flash" in data["models"]


# ---------------------------------------------------------------------------
# 6. Existing Caller Compatibility (EvaluationEngine, QuestionGenerator, QuestionGeneratorEngine)
# ---------------------------------------------------------------------------

def test_evaluator_engine_with_gemini_client():
    from backend.question_bank import get_question_by_id

    mock_gemini_client = MagicMock(spec=LLMClient)
    mock_gemini_client.provider = "gemini"
    mock_gemini_client.model_name = "gemini-2.5-flash"
    mock_gemini_client.generate_json.return_value = {
        "addressed_question": True,
        "criteria_evaluations": [
            {
                "criterion_name": "Core explanation",
                "awarded_marks": 3.0,
                "reasoning": "Accurately explained mutable vs immutable.",
                "verbatim_quote": "lists are mutable and tuples are immutable",
                "confidence_score": 0.95,
            }
        ],
        "strengths": ["Clear explanation"],
        "weaknesses_or_misconceptions": [],
        "overall_feedback": "Solid answer.",
    }

    engine = EvaluationEngine(llm_client=mock_gemini_client)
    q = get_question_by_id("py-beg-001")
    assert q is not None
    result = engine.evaluate_answer(q, "Lists are mutable and tuples are immutable.")
    assert result.addressed_question is True
    assert result.awarded_marks >= 0.0
    mock_gemini_client.generate_json.assert_called_once()


def test_question_generator_with_gemini_client(tmp_path):
    mock_gemini_client = MagicMock(spec=LLMClient)
    mock_gemini_client.provider = "gemini"
    mock_gemini_client.model_name = "gemini-2.5-flash"
    mock_gemini_client.generate_json.return_value = {
        "text": "How do Python generators optimize memory usage when processing large datasets?",
        "topic": "Python Internals",
        "difficulty": "intermediate",
        "question_type": "conceptual",
        "rubric": [
            {
                "id": "crit-gen-1",
                "description": "Explains yield statement and iterator protocol.",
                "max_marks": 5.0,
                "evidence_guide": "Explains lazy evaluation.",
            }
        ],
        "expected_concepts": ["Yield statement", "Lazy evaluation", "Memory efficiency"],
        "common_misconceptions": ["Generators store entire collection in RAM"],
        "reference_answer": "Generators produce items on demand using yield instead of buffering in memory.",
    }

    from backend.models import QuestionType
    cache_file = tmp_path / "test_recent.json"
    gen = QuestionGenerator(llm_client=mock_gemini_client, recent_cache_file=cache_file)
    q, reason = gen.generate_or_select_question(
        topic="Python fundamentals",
        competency="Memory management",
        difficulty=DifficultyLevel.INTERMEDIATE,
        question_type=QuestionType.CONCEPTUAL,
        session_asked_ids=set(),
        use_llm=True,
    )
    assert q is not None
    assert "generators optimize memory" in q.text.lower()
    assert "dynamically generated" in reason.lower()
    mock_gemini_client.generate_json.assert_called()


def test_api_answer_evaluation_flow_with_gemini():
    from backend.main import default_llm_client

    test_client = TestClient(app)
    start_res = test_client.post(
        "/api/interview/start",
        json={"track": "python", "max_questions": 2, "dynamic_questions": False, "feedback_mode": "immediate"},
    )
    assert start_res.status_code == 200
    session_id = start_res.json()["session_id"]

    mock_gemini_response = {
        "addressed_question": True,
        "is_ambiguous": False,
        "clarification_question": None,
        "demonstrated_concepts": ["Lists mutable, tuples immutable"],
        "partial_concepts": [],
        "missing_concepts": [],
        "incorrect_claims": [],
        "criteria_evaluations": [
            {
                "criterion_id": "mutability_distinction",
                "awarded_marks": 2.5,
                "evidence": "lists are mutable and tuples are immutable",
                "explanation": "Candidate correctly explained that lists can be modified in place whereas tuples cannot.",
            },
            {
                "criterion_id": "practical_use_case",
                "awarded_marks": 1.5,
                "evidence": "tuples for coordinates",
                "explanation": "Candidate mentioned coordinates.",
            },
            {
                "criterion_id": "technical_depth",
                "awarded_marks": 1.0,
                "evidence": "coordinates",
                "explanation": "Valid context.",
            },
        ],
        "summary_explanation": "Excellent comprehensive answer on lists vs tuples.",
    }

    mock_resp_obj = MagicMock()
    mock_resp_obj.text = json.dumps(mock_gemini_response)
    mock_resp_obj.usage_metadata = MagicMock(prompt_token_count=100, candidates_token_count=50)

    # Patch default_llm_client to use Gemini
    with patch.object(default_llm_client, "provider", "gemini"), \
         patch.object(default_llm_client, "api_key", "AIzaSyTestKey"), \
         patch.object(default_llm_client, "_gemini_client") as mock_client:
        mock_client.models.generate_content.return_value = mock_resp_obj

        ans_res = test_client.post(
            f"/api/interview/{session_id}/answer",
            json={"answer": "In Python, lists are mutable and tuples are immutable. We use tuples for coordinates."},
        )
        assert ans_res.status_code == 200
        ans_data = ans_res.json()
        assert ans_data["status"] == "active"
        eval_data = ans_data["evaluation"]
        assert eval_data is not None
        assert eval_data["awarded_marks"] == 5.0
        assert eval_data["percentage"] == 100.0
        mock_client.models.generate_content.assert_called()
