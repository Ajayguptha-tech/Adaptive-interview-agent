"""
LLM Client for Ollama Qwen2.5-7B with robust error handling, JSON parsing,
timeouts, and testing hooks.
"""

import json
import logging
from typing import Dict, Any, Optional
import requests

logger = logging.getLogger(__name__)

DEFAULT_OLLAMA_URL = "http://127.0.0.1:11434/api/chat"
DEFAULT_MODEL_NAME = "qwen2.5:7b"
DEFAULT_TIMEOUT_SECONDS = 180


class LLMClient:
    """Handles communication with the local Ollama instance."""

    def __init__(
        self,
        endpoint_url: str = DEFAULT_OLLAMA_URL,
        model_name: str = DEFAULT_MODEL_NAME,
        timeout: int = DEFAULT_TIMEOUT_SECONDS,
    ):
        self.endpoint_url = endpoint_url
        self.model_name = model_name
        self.timeout = timeout

    def check_health(self) -> Dict[str, Any]:
        """Checks if Ollama service is reachable and has the required model."""
        base_url = self.endpoint_url.replace("/api/chat", "")
        tags_url = f"{base_url}/api/tags"
        try:
            resp = requests.get(tags_url, timeout=5)
            resp.raise_for_status()
            data = resp.json()
            models = data.get("models", [])
            has_model = any(
                m.get("name", "").startswith(self.model_name.split(":")[0])
                for m in models
            )
            return {
                "available": True,
                "has_required_model": has_model,
                "models": [m.get("name") for m in models],
            }
        except Exception as e:
            logger.warning(f"Ollama health check failed: {e}")
            return {
                "available": False,
                "has_required_model": False,
                "error": str(e),
            }

    def generate_json(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.1,
    ) -> Dict[str, Any]:
        """
        Sends a request to Ollama expecting structured JSON.
        Validates and parses the JSON response.
        """
        if system_prompt is None:
            system_prompt = (
                "You are an expert, objective, evidence-based technical interviewer and evaluator. "
                "Evaluate the candidate's answer strictly against the provided scoring rubric. "
                "Always return valid, well-formed JSON matching the requested schema. "
                "Never invent candidate evidence or award unearned marks."
            )

        payload = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            "format": "json",
            "stream": False,
            "options": {"temperature": temperature},
        }

        try:
            resp = requests.post(self.endpoint_url, json=payload, timeout=self.timeout)
            resp.raise_for_status()
            body = resp.json()
            content = body.get("message", {}).get("content", "")
            if not content:
                raise ValueError("LLM returned empty content.")

            parsed = json.loads(content)
            if not isinstance(parsed, dict):
                raise ValueError(f"Expected JSON object, got {type(parsed).__name__}")
            return parsed

        except requests.ConnectionError as exc:
            raise RuntimeError(f"Ollama connection error: Is Ollama running on {self.endpoint_url}? ({exc})")
        except requests.Timeout as exc:
            raise TimeoutError(f"Ollama request timed out after {self.timeout}s: ({exc})")
        except json.JSONDecodeError as exc:
            raise ValueError(f"LLM returned invalid JSON: {exc}. Content was: {content[:200] if 'content' in locals() else 'None'}")
        except Exception as exc:
            raise RuntimeError(f"LLM generation failed: {exc}")


# Default global instance
default_llm_client = LLMClient()
