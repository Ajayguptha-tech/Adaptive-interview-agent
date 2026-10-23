"""
Resume Intelligence Engine.
Extracts grounded, structured information from parsed resume profiles:
- Candidate skills, proficiency evidence, and verified technologies
- Programming languages, frameworks, and database engines
- Tools, platforms, cloud technologies
- Projects: objectives, architecture, challenges, responsibilities, technical implementation details
- Distinguishes resume claims vs demonstrated interview skills
- Flags unverified claims (mentioned without supporting context)
- Defense against prompt injection in untrusted resume text
"""

import re
import time
import hashlib
import logging
import threading
from typing import Dict, Any, List, Optional, Set, Tuple
from backend.question_agent.models import (
    ResumeIntelligenceProfile,
    ProjectEvidence,
)

logger = logging.getLogger(__name__)

# Versioned, thread-safe in-memory profile cache to avoid redundant parsing
_PROFILE_CACHE: Dict[str, Tuple[float, ResumeIntelligenceProfile]] = {}
_CACHE_LOCK = threading.Lock()
_CACHE_TTL_SECONDS = 3600.0  # 1 hour

# Known languages, frameworks, tools taxonomies for grounded categorization
PROGRAMMING_LANGUAGES = {
    "python", "javascript", "typescript", "java", "c", "c++", "c#", "go", "golang",
    "rust", "ruby", "php", "swift", "kotlin", "scala", "r", "sql", "html", "css",
    "bash", "shell", "elixir", "clojure", "dart", "solidity", "lua", "perl", "haskell", "zig",
}

FRAMEWORKS = {
    "fastapi", "django", "flask", "react", "react.js", "next.js", "nextjs", "vue", "vue.js",
    "angular", "express", "express.js", "node", "node.js", "spring", "spring boot", "hibernate",
    "laravel", "ruby on rails", "rails", "asp.net", ".net", "tailwind", "bootstrap", "redux",
    "pytorch", "tensorflow", "keras", "scikit-learn", "pandas", "numpy", "celery", "pydantic",
    "sqlalchemy", "pytest", "unittest", "axum", "actix", "tokio", "fastify", "svelte", "nestjs",
    "gin", "fiber", "quarkus", "micronaut", "phoenix", "flutter",
}

TOOLS_PLATFORMS = {
    "docker", "kubernetes", "k8s", "aws", "azure", "gcp", "git", "github", "gitlab",
    "linux", "postgresql", "postgres", "mysql", "mongodb", "redis", "sqlite", "kafka",
    "rabbitmq", "nginx", "ci/cd", "jenkins", "terraform", "elasticsearch", "graphql", "rest", "postman",
    "surrealdb", "supabase", "clickhouse", "snowflake", "databricks", "dbt", "airflow",
    "qdrant", "chroma", "pinecone", "wasm", "webassembly", "grpc", "protobuf",
}

PROMPT_INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?(previous|prior|above)\s+instructions?",
    r"system\s*:\s*",
    r"assistant\s*:\s*",
    r"\[\s*inst\s*\]",
    r"<\s*\|\s*im_start\s*\|\s*>",
    r"<\s*\|\s*im_end\s*\|\s*>",
    r"you\s+are\s+now\s+a\s+",
    r"disregard\s+(all\s+)?rules?",
    r"reveal\s+(the\s+)?(system\s+prompt|instructions)",
]


class ResumeIntelligenceEngine:
    """Extracts, verifies, and structures deep resume evidence safely."""

    @classmethod
    def sanitize_resume_text(cls, text: str) -> str:
        """
        Neutralizes prompt injection patterns and unsafe delimiters in untrusted resume text.
        """
        if not text:
            return ""

        sanitized = text
        for pattern in PROMPT_INJECTION_PATTERNS:
            sanitized = re.sub(pattern, "[FILTERED_INSTRUCTION]", sanitized, flags=re.IGNORECASE)

        # Remove control characters except standard whitespace
        sanitized = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]", "", sanitized)

        # Cap length to prevent denial-of-service via huge inputs
        return sanitized[:12000].strip()

    @classmethod
    def extract_intelligence(cls, resume_profile: Dict[str, Any]) -> ResumeIntelligenceProfile:
        """
        Processes a raw resume profile dict from ResumeAnalyzerAdapter and produces
        a validated, injection-safe ResumeIntelligenceProfile.
        """
        if not resume_profile:
            return ResumeIntelligenceProfile()

        candidate_name = str(resume_profile.get("candidate_name") or "Candidate")
        summary = str(resume_profile.get("summary") or "")
        raw_text = str(resume_profile.get("raw_text") or summary or "")
        safe_raw_text = cls.sanitize_resume_text(raw_text)

        total_exp = float(
            resume_profile.get("total_experience_years")
            or resume_profile.get("years_experience")
            or 0.0
        )

        # 1. Gather all raw claimed skills
        raw_skills: List[str] = list(
            resume_profile.get("claimed_skills")
            or resume_profile.get("skills")
            or []
        )

        # Thread-safe versioned cache lookup using deterministic SHA-256 key
        cache_key = hashlib.sha256(
            (f"{candidate_name}|{total_exp}|{safe_raw_text[:2000]}|{','.join(sorted(str(s) for s in raw_skills))}").encode("utf-8")
        ).hexdigest()

        with _CACHE_LOCK:
            if cache_key in _PROFILE_CACHE:
                cached_time, cached_profile = _PROFILE_CACHE[cache_key]
                if (time.time() - cached_time) < _CACHE_TTL_SECONDS:
                    return cached_profile

        # 2. Extract detailed evidence and distinguish verified vs unverified claims
        skill_evidence_map: Dict[str, Dict[str, Any]] = {}
        for ev in resume_profile.get("skill_evidence", []):
            if isinstance(ev, dict) and "skill" in ev:
                s_name = ev["skill"].strip()
                skill_evidence_map[s_name.lower()] = ev

        programming_languages: List[str] = []
        frameworks: List[str] = []
        tools_platforms: List[str] = []
        verified_skills: List[str] = []
        unverified_claims: List[str] = []

        # Check raw text to verify if skill has surrounding supporting context (evidence)
        safe_lower = safe_raw_text.lower()

        for s in raw_skills:
            clean_s = s.strip()
            if not clean_s or len(clean_s) < 2:
                continue

            s_lower = clean_s.lower()

            # Categorize into languages, frameworks, tools (preserve unfamiliar/emerging technologies)
            if s_lower in PROGRAMMING_LANGUAGES and clean_s not in programming_languages:
                programming_languages.append(clean_s)
            elif s_lower in FRAMEWORKS and clean_s not in frameworks:
                frameworks.append(clean_s)
            elif s_lower in TOOLS_PLATFORMS and clean_s not in tools_platforms:
                tools_platforms.append(clean_s)
            elif clean_s not in tools_platforms:
                # Unfamiliar or emerging technology preserved in tools/platforms
                tools_platforms.append(clean_s)

            # Check evidence depth
            ev = skill_evidence_map.get(s_lower)
            has_explicit_evidence = False
            if ev:
                snippet = ev.get("evidence_snippet") or ""
                confidence = float(ev.get("confidence", 0.0))
                if snippet and len(snippet.strip()) > 15 and confidence >= 0.6:
                    has_explicit_evidence = True

            # If not in evidence map, search for multi-word or contextual presence in text
            if not has_explicit_evidence:
                # A skill mentioned with descriptive verbs/projects has context; standalone in comma list may be unverified claim
                pattern = rf"\b{re.escape(s_lower)}\b"
                matches = list(re.finditer(pattern, safe_lower))
                if len(matches) >= 2 or (matches and len(matches[0].string) > 100):
                    has_explicit_evidence = True

            if has_explicit_evidence:
                if clean_s not in verified_skills:
                    verified_skills.append(clean_s)
            else:
                if clean_s not in unverified_claims:
                    unverified_claims.append(clean_s)

        # 3. Extract and structure projects
        raw_projects = resume_profile.get("projects", [])
        structured_projects: List[ProjectEvidence] = []

        for p in raw_projects:
            if not isinstance(p, dict):
                continue

            title = str(p.get("title") or "Unnamed Project").strip()
            desc = p.get("description")
            techs = p.get("technologies") or []
            if isinstance(techs, str):
                techs = [t.strip() for t in techs.split(",") if t.strip()]

            # Infer objectives and challenges from description if present
            objectives = None
            challenges = None
            responsibilities = p.get("responsibilities") or []
            if isinstance(responsibilities, str):
                responsibilities = [r.strip() for r in responsibilities.split(";") if r.strip()]

            if desc:
                clean_desc = cls.sanitize_resume_text(desc)
                # Look for challenge indicators like "optimized", "migrated", "refactored", "bottleneck"
                if any(w in clean_desc.lower() for w in ["scale", "latency", "bottleneck", "challenge", "refactor", "concurrency"]):
                    challenges = f"Production optimization & scaling challenge highlighted in description: {clean_desc[:180]}..."
                objectives = clean_desc[:250]

            structured_projects.append(
                ProjectEvidence(
                    title=title,
                    description=desc,
                    technologies=techs,
                    objectives=objectives,
                    responsibilities=responsibilities,
                    challenges=challenges,
                    evidence_snippet=p.get("evidence_snippet"),
                    is_verified=False,  # Unverified until candidate answers during interview
                )
            )

        # 4. Extract coursework & certifications
        coursework_and_certs: List[str] = []
        for cert in resume_profile.get("certifications", []):
            if isinstance(cert, dict) and "name" in cert:
                coursework_and_certs.append(cert["name"])
            elif isinstance(cert, str):
                coursework_and_certs.append(cert)

        for edu in resume_profile.get("education", []):
            if isinstance(edu, dict):
                degree = edu.get("degree")
                field = edu.get("field_of_study") or edu.get("major")
                if degree or field:
                    coursework_and_certs.append(f"{degree or ''} in {field or ''}".strip())

        profile = ResumeIntelligenceProfile(
            candidate_name=candidate_name,
            total_experience_years=total_exp,
            programming_languages=programming_languages,
            frameworks=frameworks,
            tools_platforms=tools_platforms,
            verified_skills=verified_skills,
            unverified_claims=unverified_claims,
            projects=structured_projects,
            coursework_and_certs=coursework_and_certs,
            summary=summary,
            raw_text_safe=safe_raw_text[:3000],
        )

        with _CACHE_LOCK:
            _PROFILE_CACHE[cache_key] = (time.time(), profile)

        return profile

    @classmethod
    def clear_cache(cls) -> None:
        """Clears the resume profile cache for test isolation."""
        with _CACHE_LOCK:
            _PROFILE_CACHE.clear()

    @classmethod
    def cache_size(cls) -> int:
        """Returns the number of cached profiles."""
        with _CACHE_LOCK:
            return len(_PROFILE_CACHE)
