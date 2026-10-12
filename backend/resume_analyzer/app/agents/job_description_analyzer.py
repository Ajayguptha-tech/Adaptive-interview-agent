"""Agent 2: Job Description Analyzer.
Extracts required skills, preferred skills, experience years, education, and keywords.
"""
import re
from typing import List, Set, Dict, Tuple
from ..schemas.job_description import JobDescriptionInput, JobDescriptionParsed
from .resume_parser import COMMON_TECH_SKILLS


class JobDescriptionAnalyzerAgent:
    """Agent 2: Parses job descriptions into structured requirements and preferences."""

    def __init__(self):
        pass

    def analyze(self, jd_input: JobDescriptionInput) -> JobDescriptionParsed:
        text = jd_input.description
        lines = [line.strip() for line in text.splitlines() if line.strip()]

        required_skills = set(jd_input.required_skills or [])
        preferred_skills = set(jd_input.preferred_skills or [])

        # Segment JD into sections if present
        req_lines, pref_lines, resp_lines = self._segment_jd_sections(lines)

        # Extract skills from sections
        auto_required = self._extract_skills_from_lines(req_lines, text)
        auto_preferred = self._extract_skills_from_lines(pref_lines, text)

        # If user didn't specify required/preferred explicitly, use auto extracted
        if not required_skills:
            required_skills.update(auto_required)
        else:
            # Augment with any clearly mandatory skills
            required_skills.update([s for s in auto_required if s.lower() not in [p.lower() for p in preferred_skills]])

        if not preferred_skills:
            preferred_skills.update(auto_preferred)

        # If both are still empty, scan full text for tech skills
        if not required_skills and not preferred_skills:
            fallback_skills = self._extract_skills_from_full_text(text)
            # Default first 70% to required, rest to preferred
            if fallback_skills:
                split_idx = max(1, int(len(fallback_skills) * 0.7))
                required_skills.update(fallback_skills[:split_idx])
                preferred_skills.update(fallback_skills[split_idx:])

        # Remove intersection: required takes precedence
        preferred_skills = {p for p in preferred_skills if p.lower() not in {r.lower() for r in required_skills}}

        # Experience years
        min_years = self._extract_experience_years(text)

        # Education requirements
        education_reqs = self._extract_education_requirements(text)

        # Keywords
        keywords = self._extract_keywords(text, list(required_skills | preferred_skills))

        # Responsibilities
        responsibilities = [r.strip("-•* ") for r in resp_lines if len(r) > 15][:8]

        return JobDescriptionParsed(
            title=jd_input.title.strip(),
            company=jd_input.company.strip() if jd_input.company else None,
            experience_level=jd_input.experience_level or "Mid",
            min_years_experience=min_years,
            required_skills=sorted(list(required_skills)),
            preferred_skills=sorted(list(preferred_skills)),
            key_responsibilities=responsibilities,
            education_requirements=education_reqs,
            extracted_keywords=sorted(list(keywords)),
            normalized_text=text,
        )

    def _segment_jd_sections(self, lines: List[str]) -> Tuple[List[str], List[str], List[str]]:
        req_lines = []
        pref_lines = []
        resp_lines = []

        current = "general"
        for line in lines:
            lower = line.lower()
            if any(k in lower for k in ["requirement", "must have", "qualifications", "what you need", "what you'll need", "who you are"]):
                if not any(k in lower for k in ["preferred", "nice to have", "bonus"]):
                    current = "required"
                    continue
            if any(k in lower for k in ["preferred", "nice to have", "bonus", "plus", "desirable"]):
                current = "preferred"
                continue
            if any(k in lower for k in ["responsibilities", "what you will do", "role overview", "what you'll do"]):
                current = "responsibilities"
                continue

            if current == "required":
                req_lines.append(line)
            elif current == "preferred":
                pref_lines.append(line)
            elif current == "responsibilities":
                resp_lines.append(line)

        return req_lines, pref_lines, resp_lines

    def _extract_skills_from_lines(self, lines: List[str], full_text: str) -> Set[str]:
        found = set()
        for line in lines:
            # Bullet items
            bullet_clean = re.sub(r"^[•\-*]\s*", "", line)
            # Scan against common technical skills
            lower_clean = bullet_clean.lower()
            for skill in COMMON_TECH_SKILLS:
                pattern = r"\b" + re.escape(skill) + r"\b"
                if re.search(pattern, lower_clean):
                    found.add(skill.title() if not skill.isupper() else skill)
        return found

    def _extract_skills_from_full_text(self, text: str) -> List[str]:
        found = []
        lower = text.lower()
        for skill in COMMON_TECH_SKILLS:
            pattern = r"\b" + re.escape(skill) + r"\b"
            if re.search(pattern, lower):
                found.append(skill.title() if not skill.isupper() else skill)
        return found

    def _extract_experience_years(self, text: str) -> float:
        # Match patterns like "3+ years", "5-7 years", "at least 4 years of experience"
        patterns = [
            r"(\d+)\+?\s*years?\s*(?:of)?\s*(?:relevant|hands-on|professional)?\s*experience",
            r"(?:at least|minimum of)\s*(\d+)\s*years?",
            r"(\d+)\s*-\s*\d+\s*years?\s*(?:of)?\s*experience",
        ]
        for pat in patterns:
            match = re.search(pat, text, re.IGNORECASE)
            if match:
                try:
                    return float(match.group(1))
                except (ValueError, IndexError):
                    pass
        return 0.0

    def _extract_education_requirements(self, text: str) -> List[str]:
        found = []
        patterns = [
            r"(bachelor(?:'s)?(?:\s+degree)?(?:\s+in\s+[a-zA-Z\s]+)?)",
            r"(master(?:'s)?(?:\s+degree)?(?:\s+in\s+[a-zA-Z\s]+)?)",
            r"(ph\.?d\.?(?:\s+in\s+[a-zA-Z\s]+)?)",
            r"(degree in computer science[a-zA-Z\s]*)",
        ]
        for pat in patterns:
            matches = re.findall(pat, text, re.IGNORECASE)
            for m in matches:
                cleaned = m.strip()
                if len(cleaned) <= 60 and cleaned not in found:
                    found.append(cleaned)
        return found

    def _extract_keywords(self, text: str, known_skills: List[str]) -> Set[str]:
        keywords = set(known_skills)
        additional_domain_terms = [
            "scalability", "architecture", "microservices", "distributed systems",
            "agile", "scrum", "ci/cd", "unit testing", "code review", "system design",
            "cloud native", "security", "performance optimization", "api design",
            "cross-functional", "leadership", "mentorship", "collaboration"
        ]
        lower = text.lower()
        for term in additional_domain_terms:
            if re.search(r"\b" + re.escape(term) + r"\b", lower):
                keywords.add(term.title())
        return keywords
