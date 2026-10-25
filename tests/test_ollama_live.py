"""
Live integration test with the local Ollama Qwen2.5-7B instance.
Checks actual end-to-end evaluation against the running model.
Skipped automatically if Ollama is not running.
"""

import pytest
from backend.llm_client import LLMClient
from backend.evaluator import EvaluationEngine
from backend.question_bank import get_question_by_id


@pytest.fixture(scope="module")
def ollama_client():
    client = LLMClient(provider="ollama", timeout=180)
    health = client.check_health()
    if not health.get("available") and health.get("ollama") != "connected":
        pytest.skip(f"Local Ollama instance is not reachable on {client.base_url}")
    if not health.get("has_required_model"):
        pytest.skip(f"Ollama is reachable, but configured model '{client.model_name}' is not loaded. Installed: {health.get('models', [])}")
    return client


def test_ollama_live_evaluation(ollama_client):
    """Executes a real live semantic evaluation through Ollama Qwen2.5-7B."""
    q = get_question_by_id("py-beg-001")
    assert q is not None

    engine = EvaluationEngine(llm_client=ollama_client)
    candidate_answer = (
        "Lists are mutable in Python so you can add or remove elements in place. "
        "Tuples are immutable once created. I use tuples for geographic coordinates (x, y) "
        "and as dictionary keys because they are hashable."
    )

    result = engine.evaluate_answer(q, candidate_answer)

    # Sanity checks on live response
    assert result.awarded_marks > 0.0, f"Expected marks awarded by live model, got {result.awarded_marks}"
    assert result.max_marks == 5.0
    assert result.addressed_question is True
    assert len(result.criteria_evaluations) == len(q.rubric)
    # Check that deterministic bounds were preserved
    assert 0.0 <= result.awarded_marks <= 5.0
