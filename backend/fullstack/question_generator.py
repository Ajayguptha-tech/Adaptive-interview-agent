"""
Dynamic Full-Stack Question Generator.
Generates authentic Full-Stack technical interview questions with:
- Local Ollama LLM integration (qwen2.5:7b)
- Multi-technology coverage (HTML/CSS, JS, React, Node.js, Express, SQL, APIs, Architecture)
- Semantic duplicate detection using token & bigram fingerprinting
- Cross-session persistent recency cache (.recent_fullstack_questions.json)
- Bounded 3-attempt regeneration loop on duplicates
- Grounded fallback to curated Full-Stack question bank
"""

import json
import logging
import re
import threading
import time
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Set

from backend.models import (
    DifficultyLevel,
    Question,
    QuestionType,
    RubricCriterion,
)
from backend.question_generator import FingerprintEngine
from backend.fullstack.question_bank import (
    FULLSTACK_QUESTION_BANK,
    get_all_fullstack_questions,
)
from backend.llm_client import LLMClient, default_llm_client

logger = logging.getLogger(__name__)

CACHE_FILE_PATH = Path(".recent_fullstack_questions.json")
MAX_RECENT_CACHE = 40
SIMILARITY_DUPLICATE_THRESHOLD = 0.45
MAX_REGENERATION_ATTEMPTS = 3


class FullStackQuestionGenerator:
    """Generates and selects dynamic, varied Full-Stack interview questions."""

    def __init__(
        self,
        llm_client: Optional[LLMClient] = None,
        recent_cache_file: Optional[Path] = None,
    ):
        self.llm_client = llm_client or default_llm_client
        self.recent_cache_file = recent_cache_file or CACHE_FILE_PATH
        self._lock = threading.Lock()
        self.recent_records: List[Dict[str, Any]] = self._load_recent_cache()

    @property
    def recent_asked_ids(self) -> Set[str]:
        with self._lock:
            return {r["id"] for r in self.recent_records if "id" in r}

    @property
    def recent_asked_texts(self) -> List[str]:
        with self._lock:
            return [r.get("text", "") for r in self.recent_records if r.get("text")]

    def _load_recent_cache(self) -> List[Dict[str, Any]]:
        try:
            if self.recent_cache_file.exists():
                with open(self.recent_cache_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        records = []
                        for item in data:
                            if isinstance(item, str):
                                records.append({"id": item, "text": "", "topic": ""})
                            elif isinstance(item, dict):
                                records.append(item)
                        return records
        except Exception as exc:
            logger.warning("Could not read recent Full-Stack questions cache: %s", exc)
        return []

    def _save_recent_cache(self):
        try:
            with self._lock:
                records_to_save = self.recent_records[-MAX_RECENT_CACHE:]
            with open(self.recent_cache_file, "w", encoding="utf-8") as f:
                json.dump(records_to_save, f, indent=2)
        except Exception as exc:
            logger.warning("Could not save recent Full-Stack questions cache: %s", exc)

    def record_asked_question(self, question: Question):
        fingerprint = list(FingerprintEngine.extract_tokens(question.text))
        record = {
            "id": question.id,
            "topic": question.topic,
            "difficulty": question.difficulty.value,
            "question_type": question.question_type.value,
            "text": question.text,
            "language": question.language,
            "fingerprint": fingerprint,
            "timestamp": time.time(),
        }
        with self._lock:
            self.recent_records = [r for r in self.recent_records if r.get("id") != question.id]
            self.recent_records.append(record)
        self._save_recent_cache()

    def is_duplicate_or_similar(
        self,
        candidate_text: str,
        session_asked_texts: List[str],
        threshold: float = SIMILARITY_DUPLICATE_THRESHOLD,
    ) -> Tuple[bool, str]:
        # 1. Check against current session
        for prev in session_asked_texts:
            sim = FingerprintEngine.calculate_similarity(candidate_text, prev)
            if sim >= threshold or candidate_text.strip().lower() == prev.strip().lower():
                return True, f"Too similar ({sim:.2f}) to session question: '{prev[:50]}...'"

        # 2. Check against persistent cross-session cache
        with self._lock:
            cached_records = list(self.recent_records)

        for rec in cached_records:
            prev_text = rec.get("text", "")
            if not prev_text:
                continue
            sim = FingerprintEngine.calculate_similarity(candidate_text, prev_text)
            if sim >= threshold:
                return True, f"Too similar ({sim:.2f}) to recent candidate question: '{prev_text[:50]}...'"

        return False, ""

    def generate_or_select_question(
        self,
        topic: str,
        competency: str,
        difficulty: DifficultyLevel,
        question_type: QuestionType,
        session_asked_ids: Set[str],
        session_asked_texts: Optional[List[str]] = None,
        candidate_context: Optional[Dict[str, Any]] = None,
        use_llm: bool = True,
        tech_stack: Optional[str] = None,
    ) -> Tuple[Question, str]:
        session_asked_texts = session_asked_texts or []

        # 1. Attempt dynamic generation if requested
        if use_llm:
            for attempt in range(1, MAX_REGENERATION_ATTEMPTS + 1):
                try:
                    dynamic_q = self._generate_dynamic_question(
                        topic=topic,
                        competency=competency,
                        difficulty=difficulty,
                        question_type=question_type,
                        session_asked_texts=session_asked_texts,
                        candidate_context=candidate_context,
                        attempt=attempt,
                        tech_stack=tech_stack,
                    )
                    if dynamic_q:
                        is_dup, reason = self.is_duplicate_or_similar(dynamic_q.text, session_asked_texts)
                        if is_dup:
                            logger.info("Regenerating Full-Stack question (attempt %d/%d): %s", attempt, MAX_REGENERATION_ATTEMPTS, reason)
                            continue

                        self.record_asked_question(dynamic_q)
                        selection_reason = (
                            f"Dynamically generated fresh Full-Stack {dynamic_q.language.upper()} "
                            f"{question_type.value} question on '{topic}' at {difficulty.value} level."
                        )
                        return dynamic_q, selection_reason

                except Exception as exc:
                    logger.warning("Dynamic Full-Stack question generation attempt %d failed: %s", attempt, exc)

        # 2. Safe Fallback to Curated Question Bank
        bank_q, reason = self._select_from_bank_fallback(
            topic=topic,
            difficulty=difficulty,
            question_type=question_type,
            session_asked_ids=session_asked_ids,
            session_asked_texts=session_asked_texts,
        )
        self.record_asked_question(bank_q)
        return bank_q, reason

    def _select_from_bank_fallback(
        self,
        topic: str,
        difficulty: DifficultyLevel,
        question_type: QuestionType,
        session_asked_ids: Set[str],
        session_asked_texts: List[str],
    ) -> Tuple[Question, str]:
        all_bank = get_all_fullstack_questions()

        # Strict match: topic + difficulty + question_type
        matches = [
            q for q in all_bank
            if q.topic == topic and q.difficulty == difficulty and q.question_type == question_type
            and q.id not in session_asked_ids
        ]

        if not matches:
            # Topic + difficulty
            matches = [
                q for q in all_bank
                if q.topic == topic and q.difficulty == difficulty
                and q.id not in session_asked_ids
            ]

        if not matches:
            # Topic match
            matches = [
                q for q in all_bank
                if q.topic == topic and q.id not in session_asked_ids
            ]

        if not matches:
            # Any unasked
            matches = [q for q in all_bank if q.id not in session_asked_ids]

        if not matches:
            # Exhausted bank: pick question with least session overlap
            matches = all_bank

        # Pick candidate with least similarity to recent history
        best_candidate = matches[0]
        lowest_sim = 1.0

        for candidate in matches:
            max_sim = 0.0
            for prev in session_asked_texts:
                sim = FingerprintEngine.calculate_similarity(candidate.text, prev)
                if sim > max_sim:
                    max_sim = sim
            if max_sim < lowest_sim:
                lowest_sim = max_sim
                best_candidate = candidate

        reason = (
            f"Selected curated Full-Stack question '{best_candidate.id}' on '{best_candidate.topic}' "
            f"({best_candidate.difficulty.value} level, {best_candidate.question_type.value})."
        )
        return best_candidate, reason

    def _generate_dynamic_question(
        self,
        topic: str,
        competency: str,
        difficulty: DifficultyLevel,
        question_type: QuestionType,
        session_asked_texts: List[str],
        candidate_context: Optional[Dict[str, Any]] = None,
        attempt: int = 1,
        tech_stack: Optional[str] = None,
    ) -> Optional[Question]:
        recent_snippets = [t[:70] for t in self.recent_asked_texts[-10:] if t]
        exclude_clause = ""
        if recent_snippets:
            exclude_clause = "CRITICAL: Do NOT generate questions semantically similar to these recent questions:\n" + "\n".join(f"- {s}..." for s in recent_snippets)

        adaptive_steering = ""
        if candidate_context:
            missing = candidate_context.get("missing_concepts", [])
            last_score = candidate_context.get("last_score")
            if missing:
                adaptive_steering += f"CANDIDATE KNOWLEDGE GAP: The candidate struggled with: {', '.join(missing[:3])}. Target or probe these missing concepts.\n"
            if last_score is not None and last_score >= 80.0:
                adaptive_steering += "CANDIDATE PERFORMANCE: Strong performance demonstrated. Test deeper architectural nuances, edge cases, or performance tradeoffs.\n"
            elif last_score is not None and last_score < 40.0:
                adaptive_steering += "CANDIDATE PERFORMANCE: Struggled on previous question. Provide a grounded foundational problem to test core principles.\n"

        target_lang = "javascript"
        if "sql" in topic.lower() or "database" in topic.lower():
            target_lang = "sql"
        elif "html" in topic.lower() or "css" in topic.lower():
            target_lang = "html"

        stack_notice = f"Target Tech Stack: {tech_stack}" if tech_stack else "Target Tech Stack: React, Node.js, Express, SQL, HTML/CSS"

        prompt = f"""Generate an authentic Full-Stack technical interview question.
Target Topic: {topic}
Competency: {competency}
Difficulty: {difficulty.value}
Question Type: {question_type.value}
Target Language: {target_lang}
{stack_notice}

{adaptive_steering}
{exclude_clause}

Respond ONLY with a JSON object strictly matching this schema:
{{
  "topic": "{topic}",
  "competency": "{competency}",
  "difficulty": "{difficulty.value}",
  "question_type": "{question_type.value}",
  "language": "{target_lang}",
  "text": "Detailed question text / prompt",
  "code_snippet": null,
  "starter_code": null,
  "expected_output": null,
  "expected_concepts": ["Core concept 1", "Core concept 2"],
  "common_misconceptions": ["Frequent misconception"],
  "rubric": [
    {{
      "id": "crit_1",
      "description": "First criterion description",
      "max_marks": 2.5,
      "evidence_guide": "Concrete criteria for full marks"
    }},
    {{
      "id": "crit_2",
      "description": "Second criterion description",
      "max_marks": 2.5,
      "evidence_guide": "Concrete criteria for full marks"
    }}
  ],
  "reference_answer": "Authoritative reference answer / solution"
}}
Ensure the rubric criteria max_marks sum up to exactly 5.0.
"""

        system_prompt = (
            "You are a principal Full-Stack engineering interviewer and assessment architect. "
            "You create authentic, rigorous Full-Stack interview questions across frontend, backend, APIs, and databases. "
            "Always return strictly valid JSON matching the requested schema without markdown wrapper."
        )

        raw = self.llm_client.generate_json(prompt=prompt, system_prompt=system_prompt, temperature=0.7)
        return self._validate_and_build_question(raw, fallback_topic=topic, fallback_difficulty=difficulty, default_lang=target_lang)

    def _validate_and_build_question(
        self,
        raw: Dict[str, Any],
        fallback_topic: str,
        fallback_difficulty: DifficultyLevel,
        default_lang: str = "javascript",
    ) -> Optional[Question]:
        if not isinstance(raw, dict):
            return None

        text = raw.get("text", "").strip()
        if not text or len(text) < 15:
            return None

        # Difficulty
        raw_diff = str(raw.get("difficulty", "")).lower()
        diff = {
            "beginner": DifficultyLevel.BEGINNER,
            "intermediate": DifficultyLevel.INTERMEDIATE,
            "advanced": DifficultyLevel.ADVANCED,
        }.get(raw_diff, fallback_difficulty)

        # Question type
        raw_type = str(raw.get("question_type", "")).lower()
        q_type = {
            "conceptual": QuestionType.CONCEPTUAL,
            "code_writing": QuestionType.CODE_WRITING,
            "code_output": QuestionType.CODE_OUTPUT,
            "debugging": QuestionType.DEBUGGING,
            "scenario": QuestionType.SCENARIO,
            "practical": QuestionType.PRACTICAL,
        }.get(raw_type, QuestionType.CONCEPTUAL)

        # Code snippet requirements
        code_snippet = raw.get("code_snippet")
        if q_type in (QuestionType.CODE_OUTPUT, QuestionType.DEBUGGING) and not code_snippet:
            return None

        # Build rubric
        raw_rubric = raw.get("rubric", [])
        criteria: List[RubricCriterion] = []
        if isinstance(raw_rubric, list):
            for i, c in enumerate(raw_rubric):
                if isinstance(c, dict) and "description" in c:
                    crit_id = c.get("id") or f"crit_{i+1}"
                    max_m = float(c.get("max_marks", 2.5))
                    desc = str(c.get("description", ""))
                    guide = str(c.get("evidence_guide", ""))
                    criteria.append(RubricCriterion(id=crit_id, description=desc, max_marks=max_m, evidence_guide=guide))

        if not criteria:
            criteria = [
                RubricCriterion(id="correctness", description="Demonstrates full technical correctness", max_marks=5.0)
            ]

        # Normalize rubric to exactly 5.0 marks
        total_m = sum(c.max_marks for c in criteria)
        if total_m > 0 and abs(total_m - 5.0) > 0.05:
            scale = 5.0 / total_m
            for c in criteria:
                c.max_marks = round(c.max_marks * scale, 2)
            cur_sum = sum(c.max_marks for c in criteria)
            diff_adj = round(5.0 - cur_sum, 2)
            if diff_adj != 0.0:
                criteria[0].max_marks = round(criteria[0].max_marks + diff_adj, 2)

        unique_id = f"fs-dyn-{int(time.time()*1000) % 1000000}"
        language = raw.get("language") or default_lang

        return Question(
            id=unique_id,
            topic=raw.get("topic") or fallback_topic,
            competency=raw.get("competency") or "Full-Stack Engineering",
            difficulty=diff,
            question_type=q_type,
            text=text,
            code_snippet=code_snippet,
            starter_code=raw.get("starter_code"),
            expected_output=raw.get("expected_output"),
            expected_concepts=raw.get("expected_concepts") or [],
            common_misconceptions=raw.get("common_misconceptions") or [],
            rubric=criteria,
            reference_answer=raw.get("reference_answer", ""),
            track="fullstack",
            language=language,
        )


default_fullstack_generator = FullStackQuestionGenerator()
