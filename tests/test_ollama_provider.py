"""
Mocked unit tests for Ollama AI provider integration, verifying:
- Ollama connectivity and model detection via /api/tags
- Ollama unreachable and connection error handling
- Missing model detection with actionable install command
- Safe parsing of JSON, markdown fences, and embedded JSON
- Timeout handling and bounded retries
- Strict provider selection (ollama vs gemini vs invalid)
- Health endpoint accuracy for Ollama and Gemini
- Question generation and answer evaluation through Ollama
- Safe preservation of answers when AI service is unavailable without fake score
"""

import json
import os
from unittest.mock import MagicMock, patch
import pytest
import requests
from fastapi.testclient import TestClient

from backend.llm_client import LLMClient, _extract_json_object
from backend.main import app
from backend.evaluator import EvaluationEngine
from backend.question_generator import QuestionGenerator
from backend.models import Question, RubricCriterion, DifficultyLevel, QuestionType


# ---------------------------------------------------------------------------
# 1. Ollama Reachability & Model Detection Tests
# ---------------------------------------------------------------------------

def test_ollama_reachable_and_model_present():
    client = LLMClient(provider="ollama", model_name="llama3.2:1b")
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "models": [
            {"name": "llama3.2:1b", "model": "llama3.2:1b"},
            {"name": "qwen2.5:7b", "model": "qwen2.5:7b"}
        ]
    }
    with patch("requests.get", return_value=mock_resp):
        health = client._check_ollama_health()
        assert health["available"] is True
        assert health["has_required_model"] is True
        assert health["provider"] == "ollama"
        assert "llama3.2:1b" in health["models"]


def test_ollama_server_unreachable():
    client = LLMClient(provider="ollama", model_name="llama3.2:1b")
    with patch("requests.get", side_effect=requests.ConnectionError("Connection refused to 127.0.0.1:11434")):
        health = client._check_ollama_health()
        assert health["available"] is False
        assert health["has_required_model"] is False
        assert health["provider"] == "ollama"
        assert "Ollama connection error" in health["error"]
        assert "Ensure Ollama is running" in health["error"]


def test_ollama_model_missing_gives_clear_instruction():
    client = LLMClient(provider="ollama", model_name="deepseek-r1:8b")
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "models": [
            {"name": "llama3.2:1b", "model": "llama3.2:1b"}
        ]
    }
    with patch("requests.get", return_value=mock_resp):
        health = client._check_ollama_health()
        assert health["available"] is True
        assert health["has_required_model"] is False
        assert "ollama pull deepseek-r1:8b" in health["error"]
        assert "llama3.2:1b" in health["error"]


def test_ollama_health_timeout():
    client = LLMClient(provider="ollama", model_name="llama3.2:1b")
    with patch("requests.get", side_effect=requests.Timeout("Tags timed out")):
        health = client._check_ollama_health()
        assert health["available"] is False
        assert health["has_required_model"] is False
        assert "timed out after 5s" in health["error"]


# ---------------------------------------------------------------------------
# 2. JSON Extraction and Response Parsing Tests
# ---------------------------------------------------------------------------

def test_extract_json_direct():
    data = {"status": "success", "score": 90}
    assert _extract_json_object(json.dumps(data)) == data


def test_extract_json_markdown_wrapped():
    raw = "```json\n{\"summary\": \"Well done\", \"percentage\": 85.0}\n```"
    result = _extract_json_object(raw)
    assert result["summary"] == "Well done"
    assert result["percentage"] == 85.0


def test_extract_json_with_surrounding_conversational_text():
    raw = (
        "Here is the evaluation of the candidate's answer:\n"
        "{\"summary\": \"Solid understanding\", \"awarded_marks\": 4.0}\n"
        "Let me know if you need more details!"
    )
    result = _extract_json_object(raw)
    assert result["summary"] == "Solid understanding"
    assert result["awarded_marks"] == 4.0


def test_extract_json_invalid_raises_value_error():
    with pytest.raises(ValueError) as excinfo:
        _extract_json_object("This contains no JSON whatsoever.")
    assert "Could not parse valid JSON object" in str(excinfo.value)


# ---------------------------------------------------------------------------
# 3. Ollama Generation & Error Handling Tests
# ---------------------------------------------------------------------------

def test_ollama_generate_json_success():
    client = LLMClient(provider="ollama", model_name="llama3.2:1b")
    mock_post = MagicMock()
    mock_post.status_code = 200
    mock_post.json.return_value = {
        "message": {"content": json.dumps({"verdict": "pass", "marks": 5.0})},
        "total_duration": 500000000,
        "eval_duration": 400000000,
        "eval_count": 25,
        "prompt_eval_count": 40,
    }
    with patch("requests.post", return_value=mock_post):
        res = client.generate_json(prompt="Test prompt", system_prompt="Test sys")
        assert res["verdict"] == "pass"
        assert res["marks"] == 5.0
        assert client.last_perf_stats["eval_count"] == 25
        assert client.last_perf_stats["total_duration_ms"] == 500.0


def test_ollama_generate_json_model_not_found_404():
    client = LLMClient(provider="ollama", model_name="nonexistent:model")
    mock_post = MagicMock()
    mock_post.status_code = 404
    with patch("requests.post", return_value=mock_post):
        with pytest.raises(RuntimeError) as excinfo:
            client.generate_json(prompt="Hello")
        assert "ollama pull nonexistent:model" in str(excinfo.value)


def test_ollama_generate_json_timeout_raises_timeout_error():
    client = LLMClient(provider="ollama", model_name="llama3.2:1b", timeout=5)
    with patch("requests.post", side_effect=requests.Timeout("Read timed out")):
        with pytest.raises(TimeoutError) as excinfo:
            client.generate_json(prompt="Evaluate this answer", max_retries=0)
        assert "timed out after 5s" in str(excinfo.value)


def test_ollama_generate_json_transient_retry():
    client = LLMClient(provider="ollama", model_name="llama3.2:1b", timeout=5)
    mock_post_ok = MagicMock()
    mock_post_ok.status_code = 200
    mock_post_ok.json.return_value = {
        "message": {"content": json.dumps({"status": "ok"})},
        "total_duration": 1000000,
        "eval_duration": 500000,
        "eval_count": 5,
        "prompt_eval_count": 10,
    }
    # Fail once with connection error, then succeed on attempt 2
    with patch("requests.post", side_effect=[requests.ConnectionError("Temporary blip"), mock_post_ok]):
        with patch("time.sleep", return_value=None):
            result = client.generate_json(prompt="Hello", max_retries=1)
            assert result["status"] == "ok"


# ---------------------------------------------------------------------------
# 4. Provider Selection & Invalid Value Tests
# ---------------------------------------------------------------------------

def test_explicit_provider_selection():
    with patch.dict(os.environ, {"LLM_PROVIDER": "ollama", "GEMINI_API_KEY": "AIzaSySecret"}, clear=True):
        client = LLMClient()
        assert client.provider == "ollama"

    with patch.dict(os.environ, {"LLM_PROVIDER": "gemini", "GEMINI_API_KEY": "AIzaSySecret"}, clear=True):
        client = LLMClient()
        assert client.provider == "gemini"


def test_invalid_provider_selection_raises_error():
    with patch.dict(os.environ, {"LLM_PROVIDER": "claude"}, clear=True):
        with pytest.raises(ValueError) as excinfo:
            LLMClient()
        assert "Invalid LLM_PROVIDER 'claude'" in str(excinfo.value)


# ---------------------------------------------------------------------------
# 5. FastAPI /api/health with Ollama
# ---------------------------------------------------------------------------

def test_api_health_with_ollama_connected():
    from backend.main import default_llm_client
    with patch.object(default_llm_client, "check_health") as mock_health:
        mock_health.return_value = {
            "available": True,
            "has_required_model": True,
            "provider": "ollama",
            "status": "connected",
            "ollama": "connected",
            "gemini": "not_configured",
            "models": ["llama3.2:1b"],
            "installed_ollama_models": ["llama3.2:1b"],
        }
        test_client = TestClient(app)
        res = test_client.get("/api/health")
        assert res.status_code == 200
        data = res.json()
        assert data["api"] == "running"
        assert data["provider"] == "ollama"
        assert data["status"] == "connected"
        assert data["ollama"] == "connected"
        assert data["required_model_available"] is True
        assert "llama3.2:1b" in data["models"]


def test_api_health_with_ollama_disconnected():
    from backend.main import default_llm_client
    with patch.object(default_llm_client, "check_health") as mock_health:
        mock_health.return_value = {
            "available": False,
            "has_required_model": False,
            "provider": "ollama",
            "status": "disconnected",
            "ollama": "disconnected",
            "models": [],
            "error": "Ollama connection error: Service not reachable at http://127.0.0.1:11434.",
        }
        test_client = TestClient(app)
        res = test_client.get("/api/health")
        assert res.status_code == 200
        data = res.json()
        assert data["api"] == "running"
        assert data["provider"] == "ollama"
        assert data["status"] == "disconnected"
        assert data["ollama"] == "disconnected"
        assert data["required_model_available"] is False
        assert "Ollama connection error" in data["error"]


# ---------------------------------------------------------------------------
# 6. Question Generation & Evaluation with Ollama Client
# ---------------------------------------------------------------------------

def test_ollama_evaluation_engine_mocked():
    mock_ollama_client = MagicMock(spec=LLMClient)
    mock_ollama_client.provider = "ollama"
    mock_ollama_client.model_name = "llama3.2:1b"
    mock_ollama_client.generate_json.return_value = {
        "addressed_question": True,
        "is_ambiguous": False,
        "clarification_question": None,
        "demonstrated_concepts": ["Lists are mutable, tuples are immutable"],
        "partial_concepts": [],
        "missing_concepts": [],
        "incorrect_claims": [],
        "criteria_evaluations": [
            {
                "criterion_id": "mutability_distinction",
                "awarded_marks": 2.5,
                "evidence": "lists are mutable and tuples immutable",
                "explanation": "Candidate correctly explained that lists are mutable and tuples immutable.",
            },
            {
                "criterion_id": "practical_use_case",
                "awarded_marks": 1.5,
                "evidence": "coordinates",
                "explanation": "Valid scenario provided.",
            },
            {
                "criterion_id": "technical_depth",
                "awarded_marks": 1.0,
                "evidence": "hashability",
                "explanation": "Mentions hashability nuances accurately.",
            },
        ],
        "summary_explanation": "Solid understanding of lists vs tuples.",
    }

    engine = EvaluationEngine(llm_client=mock_ollama_client)
    from backend.question_bank import get_question_by_id
    q = get_question_by_id("py-beg-001")
    assert q is not None
    result = engine.evaluate_answer(q, "Lists are mutable and tuples are immutable in Python.")
    assert result.addressed_question is True
    assert result.awarded_marks == 5.0
    mock_ollama_client.generate_json.assert_called_once()


def test_ollama_question_generation_mocked(tmp_path):
    mock_ollama_client = MagicMock(spec=LLMClient)
    mock_ollama_client.provider = "ollama"
    mock_ollama_client.model_name = "llama3.2:1b"
    mock_ollama_client.generate_json.return_value = {
        "text": "Explain how Python handles variable scoping with LEGB rule in nested functions?",
        "topic": "Python internals",
        "difficulty": "intermediate",
        "question_type": "conceptual",
        "rubric": [
            {
                "id": "crit-legb-1",
                "description": "Defines Local, Enclosing, Global, Built-in namespaces.",
                "max_marks": 5.0,
                "evidence_guide": "Explains resolution order.",
            }
        ],
        "expected_concepts": ["LEGB Rule", "Namespaces", "Enclosing scope"],
        "common_misconceptions": ["Python looks at Global before Enclosing"],
        "reference_answer": "Python resolves variables sequentially through Local, Enclosing, Global, and Built-in.",
    }

    cache_file = tmp_path / "test_recent_ollama.json"
    gen = QuestionGenerator(llm_client=mock_ollama_client, recent_cache_file=cache_file)
    q, reason = gen.generate_or_select_question(
        topic="Python fundamentals",
        competency="Variable scoping",
        difficulty=DifficultyLevel.INTERMEDIATE,
        question_type=QuestionType.CONCEPTUAL,
        session_asked_ids=set(),
        use_llm=True,
    )
    assert q is not None
    assert "legb" in q.text.lower()
    mock_ollama_client.generate_json.assert_called()


def test_both_providers_failing_preserves_answer_without_fabricated_score():
    """
    Verifies that when LLM service is completely unavailable, the evaluation engine
    does NOT award a fabricated passing score. The candidate's answer is recorded,
    marks are 0.0, and the summary clearly notes service unavailability.
    """
    mock_failing_client = MagicMock(spec=LLMClient)
    mock_failing_client.provider = "ollama"
    mock_failing_client.model_name = "llama3.2:1b"
    mock_failing_client.generate_json.side_effect = RuntimeError("Ollama connection error: Service not reachable")

    engine = EvaluationEngine(llm_client=mock_failing_client)
    from backend.question_bank import get_question_by_id
    q = get_question_by_id("py-beg-001")
    assert q is not None

    candidate_text = "I believe lists can be modified but tuples cannot."
    result = engine.evaluate_answer(q, candidate_text)

    # Must NOT fabricate a score
    assert result.awarded_marks == 0.0
    assert result.percentage == 0.0
    assert "fallback" in result.summary_explanation.lower() or "connection" in result.summary_explanation.lower()
    # Criteria must document fallback explanation
    for crit in result.criteria_evaluations:
        assert crit.awarded_marks == 0.0
        assert "fallback" in crit.explanation.lower() or "connection" in crit.explanation.lower()
