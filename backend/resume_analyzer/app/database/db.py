"""SQLite persistence for ResumeIQ analyses and chat history."""
import os
import json
import sqlite3
import datetime
from typing import List, Optional, Dict, Any

DB_FILE = os.environ.get("DATABASE_PATH", "resumeiq.db")


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_connection()
    try:
        with conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS analyses (
                    id TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    file_name TEXT NOT NULL,
                    job_title TEXT NOT NULL,
                    company TEXT,
                    overall_score REAL NOT NULL,
                    resume_data_json TEXT NOT NULL,
                    job_description_json TEXT NOT NULL,
                    skills_analysis_json TEXT NOT NULL,
                    scoring_breakdown_json TEXT NOT NULL,
                    improvements_json TEXT NOT NULL,
                    is_ai_powered INTEGER DEFAULT 0,
                    integrity_audit_json TEXT
                )
            """)

            # Auto-migrate for existing tables
            try:
                conn.execute("ALTER TABLE analyses ADD COLUMN integrity_audit_json TEXT")
            except sqlite3.OperationalError:
                pass

            conn.execute("""
                CREATE TABLE IF NOT EXISTS chat_history (
                    id TEXT PRIMARY KEY,
                    analysis_id TEXT NOT NULL,
                    sender TEXT NOT NULL,
                    content TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    FOREIGN KEY (analysis_id) REFERENCES analyses(id) ON DELETE CASCADE
                )
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_analyses_created_at ON analyses(created_at DESC)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_chat_analysis_id ON chat_history(analysis_id)
            """)
    finally:
        conn.close()


def save_analysis(
    analysis_id: str,
    file_name: str,
    job_title: str,
    company: Optional[str],
    overall_score: float,
    resume_data: Dict[str, Any],
    job_description: Dict[str, Any],
    skills_analysis: Dict[str, Any],
    scoring_breakdown: Dict[str, Any],
    improvements: Dict[str, Any],
    is_ai_powered: bool = False,
    integrity_audit: Optional[Dict[str, Any]] = None,
) -> str:
    conn = get_connection()
    created_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
    try:
        with conn:
            conn.execute(
                """
                INSERT INTO analyses (
                    id, created_at, file_name, job_title, company,
                    overall_score, resume_data_json, job_description_json,
                    skills_analysis_json, scoring_breakdown_json, improvements_json,
                    is_ai_powered, integrity_audit_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    analysis_id,
                    created_at,
                    file_name,
                    job_title,
                    company or "",
                    float(overall_score),
                    json.dumps(resume_data),
                    json.dumps(job_description),
                    json.dumps(skills_analysis),
                    json.dumps(scoring_breakdown),
                    json.dumps(improvements),
                    1 if is_ai_powered else 0,
                    json.dumps(integrity_audit) if integrity_audit else None,
                ),
            )
        return analysis_id
    finally:
        conn.close()


def get_analysis(analysis_id: str) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM analyses WHERE id = ?", (analysis_id,))
        row = cur.fetchone()
        if not row:
            return None
        
        row_keys = row.keys()
        integrity_audit_val = None
        if "integrity_audit_json" in row_keys and row["integrity_audit_json"]:
            try:
                integrity_audit_val = json.loads(row["integrity_audit_json"])
            except Exception:
                integrity_audit_val = None

        return {
            "id": row["id"],
            "created_at": row["created_at"],
            "file_name": row["file_name"],
            "job_title": row["job_title"],
            "company": row["company"],
            "overall_score": row["overall_score"],
            "resume_data": json.loads(row["resume_data_json"]),
            "job_description": json.loads(row["job_description_json"]),
            "skills_analysis": json.loads(row["skills_analysis_json"]),
            "scoring_breakdown": json.loads(row["scoring_breakdown_json"]),
            "improvements": json.loads(row["improvements_json"]),
            "is_ai_powered": bool(row["is_ai_powered"]),
            "integrity_audit": integrity_audit_val,
        }
    finally:
        conn.close()


def list_analyses(limit: int = 50) -> List[Dict[str, Any]]:
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT id, created_at, file_name, job_title, company, overall_score,
                   skills_analysis_json, is_ai_powered
            FROM analyses
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (limit,),
        )
        rows = cur.fetchall()
        results = []
        for r in rows:
            skills = json.loads(r["skills_analysis_json"])
            results.append({
                "id": r["id"],
                "created_at": r["created_at"],
                "file_name": r["file_name"],
                "job_title": r["job_title"],
                "company": r["company"],
                "overall_score": r["overall_score"],
                "matched_skills_count": skills.get("matched_required_count", 0) + skills.get("matched_preferred_count", 0),
                "missing_required_count": len(skills.get("missing_required", [])),
                "is_ai_powered": bool(r["is_ai_powered"]),
            })
        return results
    finally:
        conn.close()


def delete_analysis(analysis_id: str) -> bool:
    conn = get_connection()
    try:
        with conn:
            cur = conn.execute("DELETE FROM analyses WHERE id = ?", (analysis_id,))
            return cur.rowcount > 0
    finally:
        conn.close()


def clear_all_analyses() -> int:
    conn = get_connection()
    try:
        with conn:
            cur = conn.execute("DELETE FROM analyses")
            return cur.rowcount
    finally:
        conn.close()


def save_chat_message(analysis_id: str, message_id: str, sender: str, content: str) -> None:
    conn = get_connection()
    timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
    try:
        with conn:
            conn.execute(
                """
                INSERT INTO chat_history (id, analysis_id, sender, content, timestamp)
                VALUES (?, ?, ?, ?, ?)
                """,
                (message_id, analysis_id, sender, content, timestamp),
            )
    finally:
        conn.close()


def get_chat_history(analysis_id: str) -> List[Dict[str, Any]]:
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT id, sender, content, timestamp
            FROM chat_history
            WHERE analysis_id = ?
            ORDER BY timestamp ASC
            """,
            (analysis_id,),
        )
        return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


def get_dashboard_stats() -> Dict[str, Any]:
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) as total_count, AVG(overall_score) as avg_score FROM analyses")
        row = cur.fetchone()
        total_count = row["total_count"] or 0
        avg_score = round(float(row["avg_score"] or 0), 1)

        # High score count (>= 75)
        cur.execute("SELECT COUNT(*) as high_count FROM analyses WHERE overall_score >= 75")
        high_count = cur.fetchone()["high_count"] or 0

        # Needs attention count (< 60)
        cur.execute("SELECT COUNT(*) as low_count FROM analyses WHERE overall_score < 60")
        low_count = cur.fetchone()["low_count"] or 0

        return {
            "total_analyses": total_count,
            "average_score": avg_score,
            "strong_matches": high_count,
            "needs_improvement": low_count,
        }
    finally:
        conn.close()
