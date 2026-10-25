"""
Unified LLM Client supporting Google Gemini (cloud/hosted) and Ollama (local)
with robust error handling, JSON parsing, timeouts, metrics tracking, and bounded retries.
"""

import json
import logging
import os
import re
import time
from pathlib import Path
from typing import Dict, Any, Optional
import requests

try:
    from dotenv import load_dotenv
    _env_file = Path(__file__).resolve().parent.parent / ".env"
    if _env_file.exists():
        load_dotenv(dotenv_path=_env_file)
    else:
        load_dotenv()
except ImportError:
    pass

logger = logging.getLogger(__name__)

DEFAULT_OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/")
if DEFAULT_OLLAMA_BASE_URL.endswith("/api/chat"):
    DEFAULT_OLLAMA_BASE_URL = DEFAULT_OLLAMA_BASE_URL[:-9].rstrip("/")

DEFAULT_MODEL_NAME = "qwen2.5:7b"
DEFAULT_GEMINI_MODEL = "gemini-2.5-flash"
DEFAULT_TIMEOUT_SECONDS = 180


def _sanitize_error(error_msg: str, api_key: Optional[str] = None) -> str:
    """Removes sensitive API keys and secrets from error strings."""
    msg = str(error_msg)
    if api_key and api_key in msg:
        msg = msg.replace(api_key, "[REDACTED]")
    msg = re.sub(r'AIza[0-9A-Za-z-_]{35}', '[REDACTED]', msg)
    msg = re.sub(r'((?:key|token|api_key)=)[^&\s]+', r'\1[REDACTED]', msg, flags=re.IGNORECASE)
    return msg


class RateLimitError(RuntimeError):
    """Raised when an AI provider responds with a rate limit or resource exhaustion (e.g. HTTP 429)."""
    def __init__(self, message: str, retry_after: Optional[float] = None):
        super().__init__(message)
        self.retry_after = retry_after


def _is_rate_limit_error(exc: Exception) -> Tuple[bool, Optional[float]]:
    """
    Detects HTTP 429 / RESOURCE_EXHAUSTED from Google Gemini or Ollama.
    Extracts recommended retry delay in seconds if present.
    """
    err_str = str(exc)
    code = getattr(exc, "code", None)
    status_code = getattr(exc, "status_code", None)

    is_429 = (
        code == 429
        or status_code == 429
        or "429" in err_str
        or "resource_exhausted" in err_str.lower()
        or "quota exceeded" in err_str.lower()
        or "rate limit" in err_str.lower()
    )
    if not is_429:
        return False, None

    retry_delay = None
    match = re.search(r'retry\s+(?:in|after)\s+([0-9.]+)\s*(?:s|sec|seconds)?', err_str, re.IGNORECASE)
    if match:
        try:
            retry_delay = float(match.group(1))
        except (ValueError, TypeError):
            pass

    return True, retry_delay


def _extract_json_object(content: str) -> Dict[str, Any]:
    """
    Robustly parses JSON from LLM text output.
    Handles markdown fences (```json ... ```), raw JSON, and text before/after JSON.
    """
    if not content or not content.strip():
        raise ValueError("LLM returned empty content.")

    cleaned = content.strip()
    # Strip markdown code fences
    if cleaned.startswith("```json"):
        cleaned = cleaned[7:]
    elif cleaned.startswith("```"):
        cleaned = cleaned[3:]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
    cleaned = cleaned.strip()

    # Fast path: direct JSON parse
    try:
        parsed = json.loads(cleaned)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass

    # Fallback: find outer-most JSON object {...}
    start_idx = cleaned.find("{")
    end_idx = cleaned.rfind("}")
    if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
        candidate = cleaned[start_idx : end_idx + 1]
        try:
            parsed = json.loads(candidate)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass

    raise ValueError(f"Could not parse valid JSON object from LLM output: {cleaned[:200]}")


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

        # Determine provider: explicit provider > LLM_PROVIDER env > GEMINI_API_KEY presence > ollama
        env_provider = os.environ.get("LLM_PROVIDER", "").strip().lower()
        if provider:
            p = provider.strip().lower()
            if p not in ("gemini", "ollama"):
                raise ValueError(f"Invalid provider '{provider}'. Must be 'ollama' or 'gemini'.")
            self.provider = p
        elif env_provider:
            if env_provider not in ("gemini", "ollama"):
                raise ValueError(f"Invalid LLM_PROVIDER '{env_provider}'. Must be 'ollama' or 'gemini'.")
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

        # Determine base URL and endpoint URL for Ollama
        if endpoint_url:
            raw_url = endpoint_url.rstrip("/")
            if raw_url.endswith("/api/chat"):
                self.base_url = raw_url[:-9].rstrip("/")
                self.endpoint_url = raw_url
            else:
                self.base_url = raw_url
                self.endpoint_url = f"{raw_url}/api/chat"
        else:
            self.base_url = DEFAULT_OLLAMA_BASE_URL
            self.endpoint_url = f"{DEFAULT_OLLAMA_BASE_URL}/api/chat"

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
        """
        Checks active provider health, while also probing availability of alternate provider.
        Accurately reports status for both Ollama and Gemini without misleading claims.
        """
        if self.provider == "gemini":
            gemini_status = self._check_gemini_health()
            ollama_status = self._check_ollama_health()
            ollama_connected = "connected" if (ollama_status.get("available") and ollama_status.get("has_required_model")) else "disconnected"
            gemini_connected = "connected" if gemini_status.get("available") else "disconnected"
            return {
                "available": gemini_status.get("available", False),
                "has_required_model": gemini_status.get("has_required_model", False),
                "provider": "gemini",
                "status": gemini_connected,
                "gemini": gemini_connected,
                "ollama": ollama_connected,
                "models": gemini_status.get("models", []),
                "installed_ollama_models": ollama_status.get("models", []),
                **({"error": gemini_status["error"]} if "error" in gemini_status else {}),
            }
        else:
            ollama_status = self._check_ollama_health()
            ollama_connected = "connected" if (ollama_status.get("available") and ollama_status.get("has_required_model")) else "disconnected"
            gemini_status = self._check_gemini_health() if self.api_key else {"available": False}
            gemini_connected = "connected" if gemini_status.get("available") else ("not_configured" if not self.api_key else "disconnected")
            res: Dict[str, Any] = {
                "available": ollama_status.get("available", False),
                "has_required_model": ollama_status.get("has_required_model", False),
                "provider": "ollama",
                "status": ollama_connected,
                "ollama": ollama_connected,
                "gemini": gemini_connected,
                "models": ollama_status.get("models", []),
                "installed_ollama_models": ollama_status.get("models", []),
            }
            if "error" in ollama_status:
                res["error"] = ollama_status["error"]
            return res

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
            is_rl, _ = _is_rate_limit_error(e)
            if is_rl:
                safe_err = f"Gemini service rate limit reached (HTTP 429 RESOURCE_EXHAUSTED). Details: {safe_err}"
            return {
                "available": False,
                "has_required_model": False,
                "provider": "gemini",
                "error": safe_err,
                "models": [],
            }

    def _check_ollama_health(self) -> Dict[str, Any]:
        """Checks if Ollama service is reachable and has the required model."""
        tags_url = f"{self.base_url}/api/tags"
        try:
            resp = requests.get(tags_url, timeout=5)
            resp.raise_for_status()
            data = resp.json()
            models = data.get("models", [])
            model_names = [m.get("name", "") for m in models]
            target_prefix = self.model_name.split(":")[0]
            has_model = any(
                name == self.model_name or name.startswith(target_prefix + ":") or name == target_prefix
                for name in model_names
            )
            if not has_model:
                installed_str = ", ".join(f"'{n}'" for n in model_names) if model_names else "none"
                error_msg = (
                    f"Configured Ollama model '{self.model_name}' is not installed. "
                    f"Installed models: [{installed_str}]. "
                    f"Run 'ollama pull {self.model_name}' in PowerShell/terminal, "
                    f"or set OLLAMA_MODEL in .env to an installed model."
                )
                return {
                    "available": True,
                    "has_required_model": False,
                    "provider": "ollama",
                    "models": model_names,
                    "error": error_msg,
                }
            return {
                "available": True,
                "has_required_model": True,
                "provider": "ollama",
                "models": model_names,
            }
        except requests.ConnectionError as exc:
            return {
                "available": False,
                "has_required_model": False,
                "provider": "ollama",
                "error": (
                    f"Ollama connection error: Service not reachable at {self.base_url}. "
                    "Ensure Ollama is running (`ollama serve` or open Ollama desktop app)."
                ),
                "models": [],
            }
        except requests.Timeout:
            return {
                "available": False,
                "has_required_model": False,
                "provider": "ollama",
                "error": f"Ollama health check timed out after 5s at {tags_url}.",
                "models": [],
            }
        except Exception as exc:
            return {
                "available": False,
                "has_required_model": False,
                "provider": "ollama",
                "error": f"Ollama health check failed: {exc}",
                "models": [],
            }

    def generate_json(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.1,
        options: Optional[Dict[str, Any]] = None,
        max_retries: int = 1,
    ) -> Dict[str, Any]:
        """
        Sends a request expecting structured JSON.
        Validates, parses the JSON response, and records latency & token metrics.
        Includes bounded retry for transient connection/timeout glitches.
        """
        last_err = None
        for attempt in range(max_retries + 1):
            try:
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
            except RateLimitError as rl_err:
                last_err = rl_err
                if attempt < max_retries and rl_err.retry_after is not None and 0 < rl_err.retry_after <= 2.0:
                    logger.warning(f"Transient rate limit (retry_after={rl_err.retry_after}s). Sleeping before single retry...")
                    time.sleep(rl_err.retry_after)
                else:
                    raise
            except (requests.ConnectionError, ConnectionError, TimeoutError) as exc:
                last_err = exc
                if attempt < max_retries:
                    backoff = 1.0 * (2 ** attempt)
                    logger.warning(f"Transient error on attempt {attempt + 1}, retrying in {backoff}s: {exc}")
                    time.sleep(backoff)
                else:
                    raise
            except Exception:
                raise

        if last_err:
            raise last_err

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
            return _extract_json_object(content)

        except ValueError as exc:
            safe_snippet = _sanitize_error(content[:200] if content else 'None', self.api_key)
            raise ValueError(f"LLM returned invalid JSON: {exc}. Content was: {safe_snippet}")
        except Exception as exc:
            if isinstance(exc, ValueError):
                raise
            err_str = str(exc)
            safe_err = _sanitize_error(err_str, self.api_key)
            is_rl, retry_delay = _is_rate_limit_error(exc)
            if is_rl:
                raise RateLimitError(
                    f"Gemini rate limit exceeded (HTTP 429 RESOURCE_EXHAUSTED): {safe_err}",
                    retry_after=retry_delay,
                )
            if "timeout" in err_str.lower() or "timed out" in err_str.lower() or isinstance(exc, TimeoutError):
                raise TimeoutError(f"Gemini request timed out after {self.timeout}s: ({safe_err})")
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

        t_start = time.perf_counter()
        content = ""
        try:
            resp = requests.post(self.endpoint_url, json=payload, timeout=self.timeout)
            if resp.status_code == 404:
                raise RuntimeError(
                    f"Ollama model '{self.model_name}' not found on server. "
                    f"Run 'ollama pull {self.model_name}' to download it."
                )
            resp.raise_for_status()
            body = resp.json()

            elapsed_ms = round((time.perf_counter() - t_start) * 1000.0, 2)
            total_ns = body.get("total_duration", 0)
            p_eval_ns = body.get("prompt_eval_duration", 0)
            eval_ns = body.get("eval_duration", 0)
            eval_count = body.get("eval_count", 0)
            p_eval_count = body.get("prompt_eval_count", 0)

            tps = (eval_count / (eval_ns / 1e9)) if eval_ns > 0 else 0.0

            self.last_perf_stats = {
                "total_duration_ms": round(total_ns / 1e6, 2) if total_ns else elapsed_ms,
                "prompt_eval_duration_ms": round(p_eval_ns / 1e6, 2),
                "eval_duration_ms": round(eval_ns / 1e6, 2),
                "prompt_eval_count": p_eval_count,
                "eval_count": eval_count,
                "tokens_per_second": round(tps, 2),
            }

            content = body.get("message", {}).get("content", "")
            return _extract_json_object(content)

        except (requests.ConnectionError, ConnectionError) as exc:
            raise ConnectionError(f"Ollama connection error: Is Ollama running on {self.base_url}? ({exc})")
        except requests.Timeout as exc:
            raise TimeoutError(f"Ollama request timed out after {self.timeout}s: ({exc})")
        except ValueError as exc:
            raise ValueError(f"LLM returned invalid JSON: {exc}. Content was: {content[:200] if content else 'None'}")
        except Exception as exc:
            if isinstance(exc, (RuntimeError, TimeoutError, ValueError)):
                raise
            raise RuntimeError(f"Ollama generation failed: {exc}")


# Default global instance
default_llm_client = LLMClient()
