"""
Unified LLM Client supporting Google Gemini (cloud/hosted) and Ollama (local)
with robust error handling, JSON parsing, timeouts, and metrics tracking.
"""

import json
import logging
import os
import re
import time
from typing import Dict, Any, Optional
import requests

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

logger = logging.getLogger(__name__)

DEFAULT_OLLAMA_URL = os.environ.get("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/")
if not DEFAULT_OLLAMA_URL.endswith("/api/chat"):
    DEFAULT_OLLAMA_URL += "/api/chat"

DEFAULT_MODEL_NAME = os.environ.get("OLLAMA_MODEL", "qwen2.5:7b").strip() or "qwen2.5:7b"
DEFAULT_GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash").strip() or "gemini-2.5-flash"
DEFAULT_TIMEOUT_SECONDS = 180


def _sanitize_error(error_msg: str, api_key: Optional[str] = None) -> str:
    """Removes sensitive API keys and secrets from error strings."""
    msg = str(error_msg)
    if api_key and api_key in msg:
        msg = msg.replace(api_key, "[REDACTED]")
    msg = re.sub(r'AIza[0-9A-Za-z-_]{35}', '[REDACTED]', msg)
    msg = re.sub(r'((?:key|token|api_key)=)[^&\s]+', r'\1[REDACTED]', msg, flags=re.IGNORECASE)
    return msg


class LLMClient:
    """Unified LLM client supporting Google Gemini and local Ollama instances."""

    def __init__(
        self,
        endpoint_url: Optional[str] = None,
        model_name: Optional[str] = None,
        timeout: int = DEFAULT_TIMEOUT_SECONDS,
        api_key: Optional[str] = None,
        provider: Optional[str] = None,
    ):
        self.timeout = timeout
        self.last_perf_stats: Dict[str, Any] = {}

        # Determine API key
        self.api_key = (api_key or os.environ.get("GEMINI_API_KEY", "")).strip()

        # Determine provider: explicit > LLM_PROVIDER env > GEMINI_API_KEY presence > ollama
        env_provider = os.environ.get("LLM_PROVIDER", "").strip().lower()
        if provider:
            self.provider = provider.lower()
        elif env_provider:
            self.provider = env_provider
        elif self.api_key:
            self.provider = "gemini"
        else:
            self.provider = "ollama"

        # Determine model name
        if model_name:
            self.model_name = model_name
        elif self.provider == "gemini":
            self.model_name = os.environ.get("GEMINI_MODEL", DEFAULT_GEMINI_MODEL).strip() or DEFAULT_GEMINI_MODEL
        else:
            self.model_name = os.environ.get("OLLAMA_MODEL", DEFAULT_MODEL_NAME).strip() or DEFAULT_MODEL_NAME

        # Determine endpoint URL for Ollama
        if endpoint_url:
            self.endpoint_url = endpoint_url
        else:
            self.endpoint_url = DEFAULT_OLLAMA_URL

        # Initialize Gemini client if applicable
        self._gemini_client = None
        if self.provider == "gemini" and self.api_key:
            try:
                from google import genai
                self._gemini_client = genai.Client(api_key=self.api_key)
            except Exception as e:
                logger.warning(f"Failed to initialize Gemini client: {_sanitize_error(str(e), self.api_key)}")
                self._gemini_client = None

    def check_health(self) -> Dict[str, Any]:
        """Checks if the configured LLM service (Gemini or Ollama) is reachable and ready."""
        if self.provider == "gemini":
            return self._check_gemini_health()
        return self._check_ollama_health()

    def _check_gemini_health(self) -> Dict[str, Any]:
        """Performs a real reachability check against Google Gemini API."""
        if not self.api_key:
            return {
                "available": False,
                "has_required_model": False,
                "provider": "gemini",
                "error": "GEMINI_API_KEY is not configured.",
                "models": [],
            }
        try:
            from google import genai
            from google.genai import types
        except ImportError:
            return {
                "available": False,
                "has_required_model": False,
                "provider": "gemini",
                "error": "The 'google-genai' package is not installed.",
                "models": [],
            }

        client = self._gemini_client
        if client is None:
            try:
                client = genai.Client(api_key=self.api_key)
                self._gemini_client = client
            except Exception as e:
                safe_err = _sanitize_error(str(e), self.api_key)
                return {
                    "available": False,
                    "has_required_model": False,
                    "provider": "gemini",
                    "error": safe_err,
                    "models": [],
                }

        try:
            cfg = types.GetModelConfig(http_options=types.HttpOptions(timeout=5000))
            client.models.get(model=self.model_name, config=cfg)
            return {
                "available": True,
                "has_required_model": True,
                "provider": "gemini",
                "models": [self.model_name],
            }
        except Exception as e:
            safe_err = _sanitize_error(str(e), self.api_key)
            logger.warning(f"Gemini health check failed: {safe_err}")
            return {
                "available": False,
                "has_required_model": False,
                "provider": "gemini",
                "error": safe_err,
                "models": [],
            }

    def _check_ollama_health(self) -> Dict[str, Any]:
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
                "provider": "ollama",
                "models": [m.get("name") for m in models],
            }
        except Exception as e:
            logger.warning(f"Ollama health check failed: {e}")
            return {
                "available": False,
                "has_required_model": False,
                "provider": "ollama",
                "error": str(e),
                "models": [],
            }

    def generate_json(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.1,
        options: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Sends a request expecting structured JSON.
        Validates, parses the JSON response, and records latency & token metrics.
        """
        if self.provider == "gemini":
            return self._generate_gemini_json(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=temperature,
                options=options,
            )
        return self._generate_ollama_json(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=temperature,
            options=options,
        )

    def _generate_gemini_json(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.1,
        options: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        if not self.api_key:
            raise RuntimeError("Gemini API key is not configured. Please set GEMINI_API_KEY.")

        try:
            from google import genai
            from google.genai import types
        except ImportError:
            raise RuntimeError("The 'google-genai' package is required for Gemini integration but is not installed.")

        client = self._gemini_client
        if client is None:
            try:
                client = genai.Client(api_key=self.api_key)
                self._gemini_client = client
            except Exception as e:
                raise RuntimeError(f"Failed to initialize Gemini client: {_sanitize_error(str(e), self.api_key)}")

        if system_prompt is None:
            system_prompt = (
                "You are an expert, objective, evidence-based technical interviewer and evaluator. "
                "Evaluate the candidate's answer strictly against the provided scoring rubric. "
                "Always return valid, well-formed JSON matching the requested schema. "
                "Never invent candidate evidence or award unearned marks."
            )

        config_kwargs: Dict[str, Any] = {
            "system_instruction": system_prompt,
            "temperature": temperature,
            "response_mime_type": "application/json",
            "http_options": types.HttpOptions(timeout=int(self.timeout * 1000)),
        }
        if options and "num_predict" in options:
            config_kwargs["max_output_tokens"] = options["num_predict"]

        config = types.GenerateContentConfig(**config_kwargs)

        t_start = time.perf_counter()
        content = ""
        try:
            response = client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=config,
            )
            elapsed_ms = round((time.perf_counter() - t_start) * 1000.0, 2)

            usage = getattr(response, "usage_metadata", None)
            prompt_tokens = getattr(usage, "prompt_token_count", 0) or 0
            candidate_tokens = getattr(usage, "candidates_token_count", 0) or 0
            tps = round(candidate_tokens / (elapsed_ms / 1000.0), 2) if elapsed_ms > 0 else 0.0

            self.last_perf_stats = {
                "total_duration_ms": elapsed_ms,
                "prompt_eval_duration_ms": 0.0,
                "eval_duration_ms": elapsed_ms,
                "prompt_eval_count": prompt_tokens,
                "eval_count": candidate_tokens,
                "tokens_per_second": tps,
            }

            content = getattr(response, "text", "") or ""
            if not content.strip():
                raise ValueError("LLM returned empty content.")

            cleaned = content.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            elif cleaned.startswith("```"):
                cleaned = cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            cleaned = cleaned.strip()

            parsed = json.loads(cleaned)
            if not isinstance(parsed, dict):
                raise ValueError(f"Expected JSON object, got {type(parsed).__name__}")
            return parsed

        except json.JSONDecodeError as exc:
            safe_snippet = _sanitize_error(content[:200] if content else 'None', self.api_key)
            raise ValueError(f"LLM returned invalid JSON: {exc}. Content was: {safe_snippet}")
        except Exception as exc:
            if isinstance(exc, ValueError):
                raise
            err_str = str(exc)
            if "timeout" in err_str.lower() or "timed out" in err_str.lower() or isinstance(exc, TimeoutError):
                safe_err = _sanitize_error(err_str, self.api_key)
                raise TimeoutError(f"Gemini request timed out after {self.timeout}s: ({safe_err})")
            safe_err = _sanitize_error(err_str, self.api_key)
            raise RuntimeError(f"Gemini generation failed: {safe_err}")

    def _generate_ollama_json(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.1,
        options: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Sends a request to Ollama expecting structured JSON.
        Validates, parses the JSON response, and records latency & token metrics.
        """
        if system_prompt is None:
            system_prompt = (
                "You are an expert, objective, evidence-based technical interviewer and evaluator. "
                "Evaluate the candidate's answer strictly against the provided scoring rubric. "
                "Always return valid, well-formed JSON matching the requested schema. "
                "Never invent candidate evidence or award unearned marks."
            )

        merged_options = {
            "temperature": temperature,
            "num_ctx": 2048,
            "num_predict": 550,
        }
        if options:
            merged_options.update(options)

        payload = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            "format": "json",
            "stream": False,
            "keep_alive": "15m",
            "options": merged_options,
        }

        try:
            resp = requests.post(self.endpoint_url, json=payload, timeout=self.timeout)
            resp.raise_for_status()
            body = resp.json()

            # Instrument Ollama performance metrics
            total_ns = body.get("total_duration", 0)
            p_eval_ns = body.get("prompt_eval_duration", 0)
            eval_ns = body.get("eval_duration", 0)
            eval_count = body.get("eval_count", 0)
            p_eval_count = body.get("prompt_eval_count", 0)

            tps = (eval_count / (eval_ns / 1e9)) if eval_ns > 0 else 0.0

            self.last_perf_stats = {
                "total_duration_ms": round(total_ns / 1e6, 2),
                "prompt_eval_duration_ms": round(p_eval_ns / 1e6, 2),
                "eval_duration_ms": round(eval_ns / 1e6, 2),
                "prompt_eval_count": p_eval_count,
                "eval_count": eval_count,
                "tokens_per_second": round(tps, 2),
            }

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

