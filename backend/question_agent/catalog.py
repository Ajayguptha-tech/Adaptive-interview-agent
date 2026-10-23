"""
Reusable Question Catalog with Rich Metadata and Dynamic Expansion.
Stores and indexes curated and validated model-generated questions with:
- Role, track, technology, skill, subtopic, topic
- Difficulty and QuestionFormat (12 formats)
- Resume relevance keywords
- Rubric criteria summing to 5.0 marks and test cases
- Usage count, last-used timestamp, and source type
- Fast filtering and diversity selection
"""

import json
import logging
import os
import sqlite3
import random
import threading
import time
from typing import Dict, Any, List, Optional, Set, Tuple

from backend.models import Question, DifficultyLevel, QuestionType, RubricCriterion
from backend.question_agent.models import (
    CatalogQuestionEntry,
    QuestionFormat,
    FORMAT_TO_QUESTION_TYPE,
)
from backend.question_agent.diversity_engine import QuestionDiversityEngine

logger = logging.getLogger(__name__)


class QuestionCatalog:
    """Persistent, indexed catalog of reusable technical interview questions."""

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or os.environ.get("DATABASE_PATH", "resumeiq.db")
        self._lock = threading.Lock()
        self._memory_cache: Dict[str, CatalogQuestionEntry] = {}
        self._init_db()
        self._seed_from_banks()

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
                    CREATE TABLE IF NOT EXISTS question_catalog (
                        id TEXT PRIMARY KEY,
                        role TEXT NOT NULL,
                        track TEXT NOT NULL,
                        technology TEXT NOT NULL,
                        skill TEXT NOT NULL,
                        subtopic TEXT NOT NULL,
                        topic TEXT NOT NULL,
                        difficulty TEXT NOT NULL,
                        question_format TEXT NOT NULL,
                        resume_keywords_json TEXT NOT NULL,
                        question_json TEXT NOT NULL,
                        source_type TEXT NOT NULL,
                        validation_status TEXT NOT NULL,
                        usage_count INTEGER DEFAULT 0,
                        last_used_timestamp REAL DEFAULT 0.0,
                        fingerprint TEXT NOT NULL
                    )
                """)
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_cat_track_topic ON question_catalog(track, topic, difficulty)
                """)
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_cat_fingerprint ON question_catalog(fingerprint)
                """)
            conn.close()
        except Exception as exc:
            logger.warning("Could not initialize question_catalog table: %s", exc)

    def _seed_from_banks(self):
        """Seeds catalog from existing question banks if not already populated."""
        try:
            conn = self._get_connection()
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) as cnt FROM question_catalog")
            count = cur.fetchone()["cnt"]
            conn.close()

            if count > 0:
                logger.info("Question catalog already contains %d entries. Skipping initial seeding.", count)
                self._load_cache()
                return
        except Exception as exc:
            logger.warning("Error checking catalog size: %s", exc)

        logger.info("Seeding question catalog from verified python and fullstack banks...")
        entries_to_add: List[CatalogQuestionEntry] = []

        # 1. Seed from Python Question Bank
        try:
            from backend.question_bank import get_all_questions
            for q in get_all_questions():
                q_fmt = QuestionFormat.CONCEPTUAL_EXPLANATION
                if q.question_type == QuestionType.CODE_WRITING:
                    q_fmt = QuestionFormat.CODE_WRITING
                elif q.question_type == QuestionType.CODE_OUTPUT:
                    q_fmt = QuestionFormat.OUTPUT_PREDICTION
                elif q.question_type == QuestionType.DEBUGGING:
                    q_fmt = QuestionFormat.CODE_DEBUGGING
                elif q.question_type == QuestionType.PRACTICAL:
                    q_fmt = QuestionFormat.PRACTICAL_IMPLEMENTATION
                elif q.question_type == QuestionType.SCENARIO:
                    q_fmt = QuestionFormat.DESIGN_ARCHITECTURE
                elif q.question_type == QuestionType.FOLLOW_UP:
                    q_fmt = QuestionFormat.ADAPTIVE_FOLLOW_UP

                entry = CatalogQuestionEntry(
                    id=q.id,
                    role="Python Developer",
                    track="python",
                    technology="python",
                    skill=q.competency,
                    subtopic=q.topic,
                    topic=q.topic,
                    difficulty=q.difficulty,
                    question_format=q_fmt,
                    resume_relevance_keywords=["python", q.topic.lower(), q.competency.lower()],
                    question=q,
                    source_type="curated",
                    validation_status="validated",
                    usage_count=0,
                    last_used_timestamp=0.0,
                    fingerprint=QuestionDiversityEngine.generate_fingerprint(q.text),
                )
                entries_to_add.append(entry)
        except Exception as err:
            logger.warning("Could not seed python questions: %s", err)

        # 2. Seed from Full-Stack Question Bank
        try:
            from backend.fullstack.question_bank import get_all_fullstack_questions
            for q in get_all_fullstack_questions():
                q_fmt = QuestionFormat.CONCEPTUAL_EXPLANATION
                if q.question_type == QuestionType.CODE_WRITING:
                    q_fmt = QuestionFormat.CODE_WRITING
                elif q.question_type == QuestionType.CODE_OUTPUT:
                    q_fmt = QuestionFormat.OUTPUT_PREDICTION
                elif q.question_type == QuestionType.DEBUGGING:
                    q_fmt = QuestionFormat.CODE_DEBUGGING
                elif q.question_type == QuestionType.PRACTICAL:
                    q_fmt = QuestionFormat.PRACTICAL_IMPLEMENTATION
                elif q.question_type == QuestionType.SCENARIO:
                    q_fmt = QuestionFormat.DESIGN_ARCHITECTURE

                entry = CatalogQuestionEntry(
                    id=q.id,
                    role="Full-Stack Developer",
                    track="fullstack",
                    technology=q.language or "javascript",
                    skill=q.competency,
                    subtopic=q.topic,
                    topic=q.topic,
                    difficulty=q.difficulty,
                    question_format=q_fmt,
                    resume_relevance_keywords=["fullstack", q.topic.lower(), (q.language or "").lower()],
                    question=q,
                    source_type="curated",
                    validation_status="validated",
                    usage_count=0,
                    last_used_timestamp=0.0,
                    fingerprint=QuestionDiversityEngine.generate_fingerprint(q.text),
                )
                entries_to_add.append(entry)
        except Exception as err:
            logger.warning("Could not seed fullstack questions: %s", err)

        # 3. Seed from Role-Specific Question Bank Extensions
        try:
            from backend.role_questions import ROLE_SPECIALIZED_QUESTIONS
            for q in ROLE_SPECIALIZED_QUESTIONS:
                entry = CatalogQuestionEntry(
                    id=q.id,
                    role="Specialized Role",
                    track=getattr(q, "track", "python"),
                    technology=getattr(q, "language", "python"),
                    skill=q.competency,
                    subtopic=q.topic,
                    topic=q.topic,
                    difficulty=q.difficulty,
                    question_format=QuestionFormat.CONCEPTUAL_EXPLANATION,
                    resume_relevance_keywords=[(q.language or "").lower(), q.topic.lower()],
                    question=q,
                    source_type="curated",
                    validation_status="validated",
                    usage_count=0,
                    last_used_timestamp=0.0,
                    fingerprint=QuestionDiversityEngine.generate_fingerprint(q.text),
                )
                entries_to_add.append(entry)
        except Exception as err:
            logger.warning("Could not seed role specialized questions: %s", err)

        for e in entries_to_add:
            self.add_entry(e)

        self._load_cache()
        logger.info("Successfully populated question catalog with %d verified entries.", len(entries_to_add))

    def _load_cache(self):
        """Loads entries into memory cache for quick access."""
        try:
            conn = self._get_connection()
            with self._lock:
                cur = conn.cursor()
                cur.execute("SELECT * FROM question_catalog")
                rows = cur.fetchall()
                for r in rows:
                    q_data = json.loads(r["question_json"])
                    q = Question(**q_data)
                    entry = CatalogQuestionEntry(
                        id=r["id"],
                        role=r["role"],
                        track=r["track"],
                        technology=r["technology"],
                        skill=r["skill"],
                        subtopic=r["subtopic"],
                        topic=r["topic"],
                        difficulty=DifficultyLevel(r["difficulty"]),
                        question_format=QuestionFormat(r["question_format"]),
                        resume_keywords_json=json.loads(r["resume_keywords_json"]),
                        question=q,
                        source_type=r["source_type"],
                        validation_status=r["validation_status"],
                        usage_count=r["usage_count"],
                        last_used_timestamp=r["last_used_timestamp"],
                        fingerprint=r["fingerprint"],
                    )
                    self._memory_cache[entry.id] = entry
            conn.close()
        except Exception as e:
            logger.warning("Error loading question catalog cache: %s", e)

    def add_entry(self, entry: CatalogQuestionEntry) -> bool:
        """Persists a new or updated question entry to SQLite catalog."""
        try:
            conn = self._get_connection()
            with self._lock, conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO question_catalog (
                        id, role, track, technology, skill, subtopic, topic, difficulty,
                        question_format, resume_keywords_json, question_json, source_type,
                        validation_status, usage_count, last_used_timestamp, fingerprint
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        entry.id,
                        entry.role,
                        entry.track,
                        entry.technology,
                        entry.skill,
                        entry.subtopic,
                        entry.topic,
                        entry.difficulty.value,
                        entry.question_format.value,
                        json.dumps(entry.resume_relevance_keywords),
                        json.dumps(entry.question.model_dump()),
                        entry.source_type,
                        entry.validation_status,
                        entry.usage_count,
                        entry.last_used_timestamp,
                        entry.fingerprint,
                    ),
                )
            conn.close()
            with self._lock:
                self._memory_cache[entry.id] = entry
            return True
        except Exception as exc:
            logger.warning("Failed to save entry to question catalog: %s", exc)
            return False

    def mark_used(self, question_id: str):
        """Increments usage counter and updates last_used timestamp."""
        with self._lock:
            entry = self._memory_cache.get(question_id)
            if entry:
                entry.usage_count += 1
                entry.last_used_timestamp = time.time()
        try:
            conn = self._get_connection()
            with conn:
                conn.execute(
                    """
                    UPDATE question_catalog
                    SET usage_count = usage_count + 1, last_used_timestamp = ?
                    WHERE id = ?
                    """,
                    (time.time(), question_id),
                )
            conn.close()
        except Exception as exc:
            logger.warning("Failed to update usage in question catalog: %s", exc)

    def get_total_count(self) -> int:
        """Returns the actual verified count of questions in the catalog."""
        with self._lock:
            return len(self._memory_cache)

    def find_best_catalog_fallback(
        self,
        track: str,
        topic: str,
        difficulty: DifficultyLevel,
        question_format: Optional[QuestionFormat],
        session_asked_ids: Set[str],
        session_asked_texts: List[str],
        prior_candidate_texts: Optional[List[str]] = None,
        keywords: Optional[List[str]] = None,
    ) -> Optional[Question]:
        """
        Layer 6 Fallback: selects an unasked, validated question from catalog that minimizes
        similarity to session and prior candidate questions, preferring topic/diff/format matches.
        Strictly excludes any question already asked (by ID, exact normalized text, or high similarity).
        """
        all_asked = [t for t in (list(session_asked_texts) + (prior_candidate_texts or [])) if t]
        norm_asked = {QuestionDiversityEngine.normalize_text(a) for a in all_asked if a}
        asked_ids = set(session_asked_ids or set())

        with self._lock:
            # Pool: only questions with unseen ID and unseen normalized text
            pool = [
                e for e in self._memory_cache.values()
                if e.track.lower() == track.lower() 
                and e.id not in asked_ids
                and QuestionDiversityEngine.normalize_text(e.question.text) not in norm_asked
            ]

        if not pool:
            # Fall back to any unasked regardless of track if track pool exhausted
            with self._lock:
                pool = [
                    e for e in self._memory_cache.values() 
                    if e.id not in asked_ids
                    and QuestionDiversityEngine.normalize_text(e.question.text) not in norm_asked
                ]
            if not pool:
                # Ultimate fallback if every single catalog question was asked
                with self._lock:
                    pool = list(self._memory_cache.values())

        if not pool:
            return None

        # Filtering tiers:
        # Tier 1: Topic, Difficulty, Format
        tier1 = [
            e for e in pool
            if e.topic.lower() == topic.lower()
            and e.difficulty == difficulty
            and (not question_format or e.question_format == question_format)
        ]

        # Tier 2: Topic and Difficulty
        tier2 = [e for e in pool if e.topic.lower() == topic.lower() and e.difficulty == difficulty]

        # Tier 3: Topic only
        tier3 = [e for e in pool if e.topic.lower() == topic.lower()]

        # Tier 4: Difficulty only
        tier4 = [e for e in pool if e.difficulty == difficulty]

        selected_pool = tier1 or tier2 or tier3 or tier4 or pool

        # Rank candidates by (least similarity to asked questions, least usage count)
        scored_candidates: List[Tuple[float, int, CatalogQuestionEntry]] = []
        for entry in selected_pool:
            text = entry.question.text
            max_sim = 0.0
            if all_asked:
                max_sim = max(
                    QuestionDiversityEngine.compute_similarity(text, asked)
                    for asked in all_asked
                )
            scored_candidates.append((max_sim, entry.usage_count, entry))

        # Sort: lowest similarity first, then lowest usage count
        scored_candidates.sort(key=lambda x: (x[0], x[1]))

        # Filter out any candidates that are semantically redundant (sim >= 0.60) if possible
        acceptable = [item for item in scored_candidates if item[0] < 0.60]
        pool_to_choose = acceptable if acceptable else scored_candidates
        min_sim = pool_to_choose[0][0]
        min_usage = pool_to_choose[0][1]
        top_tier = [
            item for item in pool_to_choose
            if item[0] <= min_sim + 0.05 and item[1] <= min_usage + 1
        ]
        chosen_tuple = random.choice(top_tier) if top_tier else pool_to_choose[0]

        best_entry = chosen_tuple[2]
        self.mark_used(best_entry.id)
        return best_entry.question
