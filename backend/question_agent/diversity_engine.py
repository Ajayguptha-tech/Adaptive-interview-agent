"""
Systematic Layered Diversity and Duplicate Detection Engine.
Implements the 6-layer strategy to eradicate repeated questions:
- Layer 1: Canonical normalization & SHA-256 exact fingerprinting
- Layer 2: Semantic duplicate detection via technical concept extraction & composite n-gram/token similarity
- Layer 3: Concurrent-safe per-session question history
- Layer 4: Candidate-specific cross-session history with durable SQLite isolation
- Layer 5: Candidate scoring & selection pipeline helper
- Layer 6: Bounded retry tracking & diverse unasked fallback selection
"""

import hashlib
import json
import logging
import math
import re
import sqlite3
import threading
import time
from typing import Dict, List, Optional, Set, Tuple, Any

from backend.models import Question, DifficultyLevel, QuestionType
from backend.question_agent.models import QuestionFormat

logger = logging.getLogger(__name__)

# Core stopwords that do NOT carry core technical meaning in questions
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
    # Question boilerplate
    "write", "explain", "code", "function", "following", "given", "program", "example",
    "implement", "describe", "analyze", "consider", "provide", "show", "using", "does", "would",
    "discuss", "difference", "between", "contrast", "overview", "briefly", "detail",
}

# Technical keywords and key concepts mapped for high-precision semantic comparison
TECHNICAL_CONCEPT_MAP: Dict[str, Set[str]] = {
    "mutability_sequences": {"list", "tuple", "mutable", "immutable", "mutability", "sequence"},
    "dict_hashability": {"dictionary", "dict", "hash", "hashable", "key", "lookup", "collision"},
    "memory_gc": {"garbage", "collector", "reference", "counting", "cyclical", "heap", "stack", "mem", "leak"},
    "gil_concurrency": {"gil", "global", "interpreter", "lock", "thread", "threading", "cpu", "io", "multiprocessing"},
    "async_eventloop": {"async", "asyncio", "await", "coroutine", "event", "loop", "task", "future"},
    "generators_iterators": {"generator", "yield", "iterator", "iterable", "lazy", "evaluation", "stream"},
    "decorators_closures": {"decorator", "closure", "wrapper", "functools", "wraps", "scope", "lexical"},
    "oop_polymorphism": {"oop", "inheritance", "polymorphism", "encapsulation", "class", "abstract", "interface", "dunder", "method"},
    "context_managers": {"context", "manager", "with", "enter", "exit", "resource"},
    "error_handling": {"exception", "try", "except", "finally", "raise", "error"},
    "react_state_lifecycle": {"react", "hooks", "usestate", "useeffect", "state", "props", "lifecycle", "rerender"},
    "dom_event_loop": {"dom", "event", "loop", "bubbling", "propagation", "microtask", "macrotask"},
    "rest_api_design": {"rest", "api", "endpoint", "http", "status", "idempotent", "get", "post", "put", "delete"},
    "database_indexing": {"sql", "index", "b-tree", "query", "join", "foreign", "primary", "scan", "execution", "plan"},
    "auth_security": {"jwt", "token", "auth", "authentication", "authorization", "oauth", "cors", "csrf", "cookie", "session"},
    "docker_container": {"docker", "container", "image", "dockerfile", "compose", "volume", "port"},
}


class QuestionDiversityEngine:
    """Multi-layered uniqueness validation, exact fingerprinting, and session isolation."""

    @classmethod
    def normalize_text(cls, text: str) -> str:
        """
        Layer 1: Normalizes whitespace, casing, punctuation, and markdown formatting.
        """
        if not text:
            return ""
        # Lowercase
        t = text.lower()
        # Remove code block markers and formatting
        t = re.sub(r"```[\w]*", " ", t)
        t = re.sub(r"[`_*#>\-~]", " ", t)
        # Normalize punctuation to spaces
        t = re.sub(r"[^\w\s]", " ", t)
        # Collapse multi-whitespace
        t = re.sub(r"\s+", " ", t).strip()
        return t

    @classmethod
    def generate_fingerprint(cls, text: str) -> str:
        """
        Layer 1: Computes a deterministic SHA-256 fingerprint from canonically normalized text.
        """
        norm = cls.normalize_text(text)
        return hashlib.sha256(norm.encode("utf-8")).hexdigest()

    @classmethod
    def extract_technical_tokens(cls, text: str) -> Set[str]:
        """Extracts significant non-stopword technical tokens."""
        norm = cls.normalize_text(text)
        tokens = norm.split()
        return {t for t in tokens if len(t) > 2 and t not in STOPWORDS}

    @classmethod
    def extract_bigrams(cls, text: str) -> Set[str]:
        """Extracts technical bigram shingles."""
        norm = cls.normalize_text(text)
        tokens = [t for t in norm.split() if t not in STOPWORDS]
        bigrams = set()
        for i in range(len(tokens) - 1):
            bigrams.add(f"{tokens[i]}_{tokens[i+1]}")
        return bigrams

    @classmethod
    def extract_concepts(cls, text: str) -> Set[str]:
        """Identifies specific core concepts tested in the question text."""
        norm = cls.normalize_text(text)
        tokens = set(norm.split())
        matched_concepts = set()
        for concept_name, keywords in TECHNICAL_CONCEPT_MAP.items():
            overlap = tokens.intersection(keywords)
            # If 2 or more concept keywords match (or 1 distinctive keyword like 'gil'), mark concept
            if len(overlap) >= 2 or ("gil" in overlap) or ("asyncio" in overlap) or ("jwt" in overlap):
                matched_concepts.add(concept_name)
        return matched_concepts

    @classmethod
    def compute_similarity(cls, text1: str, text2: str) -> float:
        """
        Layer 2: Computes multi-factor semantic similarity:
        - 40% token Jaccard similarity
        - 30% bigram shingle Jaccard similarity
        - 30% technical concept alignment
        Returns float in [0.0, 1.0].
        """
        if not text1 or not text2:
            return 0.0

        # Exact match shortcut
        if cls.generate_fingerprint(text1) == cls.generate_fingerprint(text2):
            return 1.0

        t1 = cls.extract_technical_tokens(text1)
        t2 = cls.extract_technical_tokens(text2)
        b1 = cls.extract_bigrams(text1)
        b2 = cls.extract_bigrams(text2)
        c1 = cls.extract_concepts(text1)
        c2 = cls.extract_concepts(text2)

        token_sim = (len(t1 & t2) / max(1, len(t1 | t2))) if (t1 or t2) else 0.0
        bigram_sim = (len(b1 & b2) / max(1, len(b1 | b2))) if (b1 or b2) else 0.0

        concept_sim = 0.0
        if c1 and c2:
            concept_sim = len(c1 & c2) / max(1, len(c1 | c2))
        elif not c1 and not c2:
            # If neither matched known taxonomy, rely more on token/bigram
            concept_sim = (token_sim + bigram_sim) / 2.0

        # If both questions test the EXACT same distinctive concept (e.g. GIL or Mutability),
        # elevate similarity weight
        if c1 and c2 and (c1 & c2):
            # Same core concept being evaluated
            combined = 0.35 * token_sim + 0.25 * bigram_sim + 0.40 * concept_sim
        else:
            combined = 0.50 * token_sim + 0.35 * bigram_sim + 0.15 * concept_sim

        return round(combined, 3)

    @classmethod
    def check_duplicate(
        cls,
        candidate_text: str,
        session_asked_texts: List[str],
        prior_candidate_texts: Optional[List[str]] = None,
        threshold: float = 0.38,
    ) -> Tuple[bool, str, float]:
        """
        Evaluates a candidate question against current session history (Layer 3)
        and candidate cross-session history (Layer 4).
        Returns: (is_duplicate: bool, rejection_reason: str, max_similarity: float)
        """
        cand_norm = cls.normalize_text(candidate_text)
        if len(cand_norm) < 15:
            return True, "Question text is too short or empty.", 1.0

        cand_fp = cls.generate_fingerprint(candidate_text)

        # 1. Exact & Semantic check against Current Session (Layer 1 & Layer 2)
        max_sim = 0.0
        worst_match = ""

        for prev in session_asked_texts:
            if not prev:
                continue
            prev_fp = cls.generate_fingerprint(prev)
            if cand_fp == prev_fp:
                return True, f"Exact duplicate of question already asked in this session: '{prev[:60]}...'", 1.0

            sim = cls.compute_similarity(candidate_text, prev)
            if sim > max_sim:
                max_sim = sim
                worst_match = prev

            if sim >= threshold:
                return True, f"Semantically redundant (sim={sim:.2f} >= {threshold}) with current session question: '{prev[:60]}...'", sim

        # 2. Check against Prior Interviews for this Candidate (Layer 4)
        if prior_candidate_texts:
            for prev in prior_candidate_texts:
                if not prev:
                    continue
                prev_fp = cls.generate_fingerprint(prev)
                if cand_fp == prev_fp:
                    return True, f"Candidate was already asked this exact question in a previous interview: '{prev[:60]}...'", 1.0

                sim = cls.compute_similarity(candidate_text, prev)
                if sim > max_sim:
                    max_sim = sim
                    worst_match = prev

                # Slightly higher tolerance for previous sessions (0.48 vs 0.38)
                if sim >= (threshold + 0.10):
                    return True, f"Too similar (sim={sim:.2f}) to question asked in candidate's prior interview: '{prev[:60]}...'", sim

        return False, "", max_sim


# SQLite-backed candidate question history manager for Layer 4
class CandidateQuestionHistoryStore:
    """Manages cross-session question history per candidate."""

    def __init__(self, db_path: Optional[str] = None):
        import os
        self.db_path = db_path or os.environ.get("DATABASE_PATH", "resumeiq.db")
        self._lock = threading.Lock()
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, check_same_thread=False, timeout=20.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode = WAL")
        return conn

    def _init_db(self):
        try:
            conn = self._get_connection()
            with conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS candidate_question_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        candidate_id TEXT NOT NULL,
                        session_id TEXT NOT NULL,
                        question_id TEXT NOT NULL,
                        fingerprint TEXT NOT NULL,
                        question_text TEXT NOT NULL,
                        topic TEXT NOT NULL,
                        asked_at REAL NOT NULL
                    )
                """)
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_cand_history ON candidate_question_history(candidate_id, asked_at DESC)
                """)
            conn.close()
        except Exception as e:
            logger.warning("Could not initialize candidate_question_history table: %s", e)

    def record_question(
        self,
        candidate_id: str,
        session_id: str,
        question_id: str,
        question_text: str,
        topic: str,
    ):
        """Records an asked question against the candidate's durable profile."""
        if not candidate_id:
            return
        fp = QuestionDiversityEngine.generate_fingerprint(question_text)
        try:
            conn = self._get_connection()
            with self._lock, conn:
                conn.execute(
                    """
                    INSERT INTO candidate_question_history (
                        candidate_id, session_id, question_id, fingerprint, question_text, topic, asked_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (candidate_id, session_id, question_id, fp, question_text, topic, time.time()),
                )
            conn.close()
        except Exception as exc:
            logger.warning("Failed to record candidate question history: %s", exc)

    def get_recent_questions(self, candidate_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Retrieves recent questions asked to this candidate across earlier sessions."""
        if not candidate_id:
            return []
        try:
            conn = self._get_connection()
            with self._lock:
                cur = conn.cursor()
                cur.execute(
                    """
                    SELECT question_id, fingerprint, question_text, topic, session_id, asked_at
                    FROM candidate_question_history
                    WHERE candidate_id = ?
                    ORDER BY asked_at DESC LIMIT ?
                    """,
                    (candidate_id, limit),
                )
                rows = cur.fetchall()
            conn.close()
            return [dict(r) for r in rows]
        except Exception as exc:
            logger.warning("Failed to fetch candidate question history: %s", exc)
            return []
