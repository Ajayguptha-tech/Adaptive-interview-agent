"""
Dynamic Question Generation and Selection Strategy for Python Interviews.
Generates fresh, non-repeating Python questions using local Ollama (qwen2.5:7b)
with strict schema validation, rubric normalization, semantic fingerprinting,
regeneration for duplicates, candidate-specific adaptive steering, and safe fallback.
"""

import json
import logging
import os
import random
import re
import string
import threading
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from backend.llm_client import LLMClient, default_llm_client
from backend.models import (
    DifficultyLevel,
    InterviewMode,
    Question,
    QuestionType,
    RubricCriterion,
)
from backend.question_bank import (
    QUESTION_BANK,
    get_all_questions,
    get_all_topics,
)

logger = logging.getLogger(__name__)

CACHE_FILE_PATH = Path(__file__).parent.parent / ".recent_questions.json"
MAX_RECENT_CACHE = 100
SIMILARITY_DUPLICATE_THRESHOLD = 0.45
MAX_REGENERATION_ATTEMPTS = 3

# Common stopwords to exclude from semantic fingerprint
STOPWORDS = {
    "a", "about", "above", "after", "again", "against", "all", "am", "an", "and", "any", "are",
    "as", "at", "be", "because", "been", "before", "being", "below", "between", "both", "but", "by",
    "can", "could", "did", "do", "does", "doing", "down", "during", "each", "few", "for", "from",
    "further", "had", "has", "have", "having", "he", "her", "here", "him", "his", "how", "i", "if",
    "in", "into", "is", "it", "its", "itself", "just", "me", "more", "most", "my", "myself", "no",
    "nor", "not", "now", "of", "off", "on", "once", "only", "or", "other", "our", "ours", "out",
    "over", "own", "same", "she", "should", "so", "some", "such", "than", "that", "the", "their",
    "theirs", "them", "then", "there", "these", "they", "this", "those", "through", "to", "too",
    "under", "until", "up", "very", "was", "we", "were", "what", "when", "where", "which", "while",
    "who", "whom", "why", "with", "you", "your", "yours", "yourself", "yourselves",
    # Generic question boilerplate
    "write", "explain", "code", "python", "function", "following", "given", "program", "example",
    "implement", "describe", "analyze", "consider", "provide", "show", "using", "what", "does",
}


class FingerprintEngine:
    """Computes normalized technical tokens and n-gram shingles for duplicate detection."""

    @classmethod
    def extract_tokens(cls, text: str) -> Set[str]:
        cleaned = re.sub(r"[^\w\s]", " ", text.lower())
        tokens = cleaned.split()
        return {t for t in tokens if len(t) > 2 and t not in STOPWORDS}

    @classmethod
    def extract_bigrams(cls, text: str) -> Set[str]:
        cleaned = re.sub(r"[^\w\s]", " ", text.lower())
        tokens = [t for t in cleaned.split() if t not in STOPWORDS]
        bigrams = set()
        for i in range(len(tokens) - 1):
            bigrams.add(f"{tokens[i]}_{tokens[i+1]}")
        return bigrams

    @classmethod
    def calculate_similarity(cls, text1: str, text2: str) -> float:
        """
        Calculates composite Jaccard similarity across technical tokens and bigrams.
        Returns float in [0.0, 1.0].
        """
        t1, t2 = cls.extract_tokens(text1), cls.extract_tokens(text2)
        b1, b2 = cls.extract_bigrams(text1), cls.extract_bigrams(text2)

        token_sim = (len(t1 & t2) / max(1, len(t1 | t2))) if (t1 or t2) else 0.0
        bigram_sim = (len(b1 & b2) / max(1, len(b1 | b2))) if (b1 or b2) else 0.0

        # Weighted combination: bigrams indicate specific algorithmic or semantic matches
        return round(0.5 * token_sim + 0.5 * bigram_sim, 3)

    @classmethod
    def are_semantically_similar(cls, text1: str, text2: str, threshold: float = 0.45) -> bool:
        """Convenience method returning True if similarity meets or exceeds threshold."""
        return cls.calculate_similarity(text1, text2) >= threshold


class QuestionGenerator:
    """
    Generates and selects dynamic, varied Python interview questions.
    Combines local Ollama generation with strict validation, duplicate detection,
    semantic fingerprinting, and grounded question bank fallbacks.
    """

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
        """Loads persistent recent question records from local disk."""
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
            logger.warning("Could not read recent questions cache: %s", exc)
        return []

    def _save_recent_cache(self):
        """Persists recent question records to disk with maximum history limit."""
        try:
            with self._lock:
                records_to_save = self.recent_records[-MAX_RECENT_CACHE:]
            with open(self.recent_cache_file, "w", encoding="utf-8") as f:
                json.dump(records_to_save, f, indent=2)
        except Exception as exc:
            logger.warning("Could not save recent questions cache: %s", exc)

    def record_asked_question(self, question: Question):
        """Records question metadata and fingerprint to prevent future duplication."""
        fingerprint = list(FingerprintEngine.extract_tokens(question.text))
        record = {
            "id": question.id,
            "topic": question.topic,
            "difficulty": question.difficulty.value,
            "question_type": question.question_type.value,
            "text": question.text,
            "fingerprint": fingerprint,
            "timestamp": time.time(),
        }
        with self._lock:
            # Avoid duplicate records in cache
            self.recent_records = [r for r in self.recent_records if r.get("id") != question.id]
            self.recent_records.append(record)
        self._save_recent_cache()

    def is_duplicate_or_similar(
        self,
        candidate_text: str,
        session_asked_texts: List[str],
        threshold: float = SIMILARITY_DUPLICATE_THRESHOLD,
    ) -> Tuple[bool, str]:
        """
        Checks if candidate_text is identical or semantically equivalent to:
        1. Any question asked in the current session.
        2. Any question in the persistent cross-session cache.
        """
        # 1. Check against current session
        for prev in session_asked_texts:
            sim = FingerprintEngine.calculate_similarity(candidate_text, prev)
            if sim >= threshold or candidate_text.strip().lower() == prev.strip().lower():
                return True, f"Too similar ({sim:.2f}) to session question: '{prev[:50]}...'"

        # 2. Check against persistent cross-session history
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
    ) -> Tuple[Question, str]:
        """
        Main entry point for generating or selecting a dynamic, non-repeating question.
        Includes regeneration loop when semantically similar duplicates are detected.
        """
        session_asked_texts = session_asked_texts or []

        # 1. Attempt dynamic generation with local Ollama if requested
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
                    )
                    if dynamic_q:
                        is_dup, reason = self.is_duplicate_or_similar(
                            dynamic_q.text, session_asked_texts
                        )
                        if is_dup:
                            logger.info(
                                "Regenerating dynamic question (attempt %d/%d): %s",
                                attempt,
                                MAX_REGENERATION_ATTEMPTS,
                                reason,
                            )
                            continue

                        # Fresh validated question produced
                        self.record_asked_question(dynamic_q)
                        selection_reason = (
                            f"Dynamically generated fresh {question_type.value} question on '{topic}' "
                            f"at {difficulty.value} level."
                        )
                        return dynamic_q, selection_reason

                except Exception as exc:
                    logger.warning("Dynamic question generation attempt %d failed: %s", attempt, exc)

        # 2. Safe Fallback to Question Bank
        bank_q, reason = self._select_from_bank_fallback(
            topic=topic,
            difficulty=difficulty,
            question_type=question_type,
            session_asked_ids=session_asked_ids,
            session_asked_texts=session_asked_texts,
        )
        self.record_asked_question(bank_q)
        return bank_q, reason

    def _generate_dynamic_question(
        self,
        topic: str,
        competency: str,
        difficulty: DifficultyLevel,
        question_type: QuestionType,
        session_asked_texts: List[str],
        candidate_context: Optional[Dict[str, Any]] = None,
        attempt: int = 1,
    ) -> Optional[Question]:
        """
        Prompts Ollama to generate a structured Python question adhering to strict rubric guidelines,
        incorporating candidate-specific adaptive steering and recent exclusions.
        """
        # Compile recent question previews for exclusion prompt
        with self._lock:
            recent_texts = [r["text"] for r in self.recent_records[-8:] if r.get("text")]
        all_exclude = list(session_asked_texts) + [t for t in recent_texts if t not in session_asked_texts]

        exclude_clause = ""
        if all_exclude:
            previews = [f"- {t[:80]}..." for t in all_exclude[-6:]]
            exclude_clause = (
                "EXCLUDE PREVIOUS QUESTIONS (DO NOT DUPLICATE THESE PROBLEMS OR CONCEPTS):\n"
                + "\n".join(previews) + "\n"
            )

        # Candidate-specific adaptive steering
        adaptive_steering = ""
        if candidate_context:
            missing = candidate_context.get("missing_concepts", [])
            misconceptions = candidate_context.get("misconceptions", [])
            last_score = candidate_context.get("last_score")

            steering_points = []
            if last_score is not None:
                if last_score >= 80.0:
                    steering_points.append(
                        f"Candidate scored high ({last_score:.0f}%) on previous question. "
                        "Advance the challenge: probe deeper edge cases, performance trade-offs, or advanced semantics."
                    )
                elif last_score < 40.0:
                    steering_points.append(
                        f"Candidate struggled ({last_score:.0f}%) on previous question. "
                        "Provide a diagnostic problem testing core foundational principles or prerequisite mechanics."
                    )
            if missing:
                steering_points.append(
                    f"Candidate missed these concepts recently: {', '.join(missing[:3])}. "
                    "Incorporate assessment of these areas if relevant to the topic."
                )
            if misconceptions:
                steering_points.append(
                    f"Candidate demonstrated these misconceptions: {', '.join(misconceptions[:2])}."
                )

            if steering_points:
                adaptive_steering = "CANDIDATE ADAPTIVE STEERING:\n" + "\n".join(f"- {p}" for p in steering_points) + "\n"

        type_instructions = {
            QuestionType.CONCEPTUAL: (
                "Create a deep conceptual technical question testing core Python language mechanics, "
                "data structures, memory model, or runtime trade-offs. Do not require code writing."
            ),
            QuestionType.CODE_WRITING: (
                "Create an algorithmic or practical coding challenge where candidate must write a Python function. "
                "Specify exact function name, arguments, and return types. "
                "Provide starter template in 'starter_code' and 3-5 concrete test cases in 'test_cases'."
            ),
            QuestionType.CODE_OUTPUT: (
                "Create a tricky or illustrative 4-8 line Python code snippet in 'code_snippet'. "
                "Ask candidate to predict the exact output. Provide the exact expected printed output in 'expected_output'."
            ),
            QuestionType.DEBUGGING: (
                "Create a debugging challenge with a realistic logic or runtime bug (4-8 lines) in 'code_snippet'. "
                "Candidate must identify and fix the defect. Provide corrected solution and test cases."
            ),
            QuestionType.PRACTICAL: (
                "Create an applied Python systems/design question exploring real-world architecture or optimization."
            ),
            QuestionType.SCENARIO: (
                "Create a production scenario question involving concurrency, profiling, or reliability."
            ),
        }.get(question_type, "Create an authentic Python technical interview question.")

        retry_notice = ""
        if attempt > 1:
            retry_notice = (
                f"NOTE: Attempt #{attempt}. Previous generated question was rejected as a duplicate. "
                "You MUST choose a completely distinct problem, algorithm, or concept.\n"
            )

        prompt = f"""Generate a Python technical interview question.
Target Topic: {topic}
Competency: {competency}
Difficulty: {difficulty.value}
Question Type: {question_type.value}

{type_instructions}
{retry_notice}
{adaptive_steering}
{exclude_clause}

Respond ONLY with a JSON object strictly matching this schema:
{{
  "topic": "{topic}",
  "competency": "{competency}",
  "difficulty": "{difficulty.value}",
  "question_type": "{question_type.value}",
  "text": "Detailed question prompt presented to candidate",
  "code_snippet": "Python code snippet string, or null if conceptual",
  "starter_code": "Optional starter function signature or template, or null",
  "function_name": "Optional callable function name if code writing, or null",
  "expected_output": "Exact expected stdout string if code output question, or null",
  "test_cases": [
    {{"input": "arg_or_list", "expected": "expected_result"}}
  ],
  "expected_concepts": ["List of 3-5 core technical facts expected in a complete answer"],
  "common_misconceptions": ["List of 2-3 common candidate misunderstandings"],
  "rubric": [
    {{
      "id": "crit_1",
      "description": "What specific understanding this criterion rewards",
      "max_marks": 2.5,
      "evidence_guide": "Concrete criteria for full marks"
    }},
    {{
      "id": "crit_2",
      "description": "Second criterion",
      "max_marks": 2.5,
      "evidence_guide": "Concrete criteria"
    }}
  ],
  "reference_answer": "Complete authoritative reference solution (private for grading)"
}}
Ensure the rubric criteria max_marks sum up to exactly 5.0.
"""

        system_prompt = (
            "You are a principal Python technical interviewer and assessment architect. "
            "You create authentic, rigorous Python interview questions with deterministic evaluation rubrics. "
            "Always return strictly valid JSON matching the requested schema without markdown wrapper."
        )

        raw = self.llm_client.generate_json(prompt=prompt, system_prompt=system_prompt, temperature=0.7)
        return self._validate_and_build_question(raw, fallback_topic=topic, fallback_difficulty=difficulty)

    def _validate_and_build_question(
        self,
        data: Dict[str, Any],
        fallback_topic: str,
        fallback_difficulty: DifficultyLevel,
    ) -> Optional[Question]:
        """Validates raw LLM response and constructs a compliant Question model."""
        if not isinstance(data, dict):
            return None

        text = (data.get("text") or "").strip()
        if len(text) < 15:
            return None

        # Normalize difficulty
        diff_str = str(data.get("difficulty", fallback_difficulty.value)).lower()
        diff = {
            "beginner": DifficultyLevel.BEGINNER,
            "intermediate": DifficultyLevel.INTERMEDIATE,
            "advanced": DifficultyLevel.ADVANCED,
        }.get(diff_str, fallback_difficulty)

        # Normalize question type
        type_str = str(data.get("question_type", "conceptual")).lower()
        q_type = {
            "conceptual": QuestionType.CONCEPTUAL,
            "code_writing": QuestionType.CODE_WRITING,
            "code_output": QuestionType.CODE_OUTPUT,
            "debugging": QuestionType.DEBUGGING,
            "practical": QuestionType.PRACTICAL,
            "scenario": QuestionType.SCENARIO,
            "follow_up": QuestionType.FOLLOW_UP,
        }.get(type_str, QuestionType.CONCEPTUAL)

        code_snippet = data.get("code_snippet")
        if code_snippet:
            code_snippet = str(code_snippet).strip()
            if not code_snippet:
                code_snippet = None

        # Output prediction and debugging MUST have a code snippet
        if q_type in (QuestionType.CODE_OUTPUT, QuestionType.DEBUGGING) and not code_snippet:
            return None

        # Parse test cases
        raw_tests = data.get("test_cases")
        test_cases = []
        if isinstance(raw_tests, list):
            for tc in raw_tests:
                if isinstance(tc, dict) and "expected" in tc:
                    test_cases.append(tc)

        # Parse rubric criteria
        raw_rubric = data.get("rubric") or []
        if not isinstance(raw_rubric, list) or len(raw_rubric) == 0:
            return None

        rubric_criteria: List[RubricCriterion] = []
        for idx, item in enumerate(raw_rubric):
            if not isinstance(item, dict):
                continue
            c_id = str(item.get("id") or f"crit_{idx + 1}").strip()
            desc = str(item.get("description") or f"Criterion {idx + 1}").strip()
            try:
                marks = float(item.get("max_marks", 2.5))
            except (ValueError, TypeError):
                marks = 2.5
            guide = str(item.get("evidence_guide") or desc).strip()
            rubric_criteria.append(
                RubricCriterion(
                    id=c_id,
                    description=desc,
                    max_marks=max(0.5, marks),
                    evidence_guide=guide,
                )
            )

        if not rubric_criteria:
            return None

        # Normalize rubric marks so total is always 5.0
        current_sum = sum(c.max_marks for c in rubric_criteria)
        if current_sum <= 0:
            current_sum = 5.0
            for c in rubric_criteria:
                c.max_marks = 5.0 / len(rubric_criteria)
        else:
            scale = 5.0 / current_sum
            for c in rubric_criteria:
                c.max_marks = round(c.max_marks * scale, 1)

            diff_sum = 5.0 - sum(c.max_marks for c in rubric_criteria)
            rubric_criteria[0].max_marks = max(0.5, round(rubric_criteria[0].max_marks + diff_sum, 1))

        expected = [str(c).strip() for c in data.get("expected_concepts", []) if str(c).strip()]
        if not expected:
            expected = ["Demonstrates understanding of core Python semantics."]

        misconceptions = [str(m).strip() for m in data.get("common_misconceptions", []) if str(m).strip()]

        slug = re.sub(r"[^a-z0-9]+", "-", fallback_topic.lower()).strip("-")[:12]
        qid = f"dyn-{slug}-{diff.value[:3]}-{uuid.uuid4().hex[:6]}"

        return Question(
            id=qid,
            topic=str(data.get("topic") or fallback_topic),
            competency=str(data.get("competency") or "Python Competency"),
            difficulty=diff,
            question_type=q_type,
            text=text,
            code_snippet=code_snippet,
            starter_code=data.get("starter_code"),
            function_name=data.get("function_name"),
            expected_output=data.get("expected_output"),
            test_cases=test_cases if test_cases else None,
            expected_concepts=expected,
            common_misconceptions=misconceptions,
            rubric=rubric_criteria,
            reference_answer=str(data.get("reference_answer") or ""),
        )

    def _select_from_bank_fallback(
        self,
        topic: str,
        difficulty: DifficultyLevel,
        question_type: Optional[QuestionType],
        session_asked_ids: Set[str],
        session_asked_texts: Optional[List[str]] = None,
    ) -> Tuple[Question, str]:
        """
        Selects an unasked question from the question bank with randomization
        and semantic similarity filtering to avoid repetitive static sequences.
        """
        all_q = get_all_questions()
        session_asked_texts = session_asked_texts or []

        # Filter candidates not asked in this session
        unasked = [q for q in all_q if q.id not in session_asked_ids]
        if not unasked:
            unasked = all_q

        # 1. Try matching topic, difficulty, and question_type
        if question_type:
            exact = [
                q for q in unasked
                if q.topic.lower() == topic.lower()
                and q.difficulty == difficulty
                and q.question_type == question_type
            ]
            if exact:
                chosen = self._pick_least_similar(exact, session_asked_texts)
                return chosen, f"Selected {question_type.value} question on '{chosen.topic}' from question bank."

        # 2. Try matching topic and difficulty
        by_topic_diff = [
            q for q in unasked
            if q.topic.lower() == topic.lower() and q.difficulty == difficulty
        ]
        if by_topic_diff:
            chosen = self._pick_least_similar(by_topic_diff, session_asked_texts)
            return chosen, f"Selected {chosen.question_type.value} question on '{chosen.topic}' at {difficulty.value} level."

        # 3. Try matching topic (any difficulty / question type to preserve targeted topic)
        by_topic = [
            q for q in unasked
            if q.topic.lower() == topic.lower()
        ]
        if by_topic:
            chosen = self._pick_least_similar(by_topic, session_asked_texts)
            return chosen, f"Selected {chosen.question_type.value} question on '{chosen.topic}' from question bank."

        # 4. Try matching difficulty
        by_diff = [q for q in unasked if q.difficulty == difficulty]
        if by_diff:
            chosen = self._pick_least_similar(by_diff, session_asked_texts)
            return chosen, f"Selected question on '{chosen.topic}' ({difficulty.value}) from question bank."

        # 5. Fallback to any unasked
        chosen = self._pick_least_similar(unasked, session_asked_texts)
        return chosen, f"Selected question on '{chosen.topic}' from question bank."

    def _pick_least_similar(
        self, candidates: List[Question], session_asked_texts: List[str]
    ) -> Question:
        """
        Picks the candidate question that has the least semantic similarity
        to both current session questions and persistent recent questions.
        """
        recent_ids = self.recent_asked_ids
        not_recent = [q for q in candidates if q.id not in recent_ids]
        pool = not_recent if not_recent else candidates

        if not session_asked_texts:
            return random.choice(pool)

        # Find candidate with minimal similarity to previously asked session texts
        scored = []
        for q in pool:
            max_sim = max(
                (FingerprintEngine.calculate_similarity(q.text, prev) for prev in session_asked_texts),
                default=0.0,
            )
            scored.append((max_sim, q))

        scored.sort(key=lambda x: x[0])
        # Return candidate with lowest maximum similarity
        return scored[0][1]


# Default global question generator
default_question_generator = QuestionGenerator()
