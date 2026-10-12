"""Agent 3: Skills Matching Agent.
Performs case-insensitive matching, handles aliasing/synonyms, and differentiates
exact matches, aliases, missing required, and missing preferred skills.
Tracks whether matched skills were explicitly listed or inferred from project/work experience.
"""
import re
from typing import List, Dict, Set, Tuple, Optional
from ..schemas.resume import ResumeParsedData, SkillEvidenceItem
from ..schemas.job_description import JobDescriptionParsed
from ..schemas.analysis import SkillsAnalysisResult, SkillMatchItem


SKILL_ALIASES: Dict[str, Set[str]] = {
    "javascript": {"js", "ecmascript", "vanilla js"},
    "typescript": {"ts"},
    "python": {"py", "python3"},
    "react": {"react.js", "reactjs"},
    "vue": {"vue.js", "vuejs"},
    "angular": {"angular.js", "angularjs"},
    "node.js": {"node", "nodejs"},
    "next.js": {"nextjs", "next"},
    "postgresql": {"postgres", "psql"},
    "mongodb": {"mongo"},
    "kubernetes": {"k8s"},
    "docker": {"containers", "containerization"},
    "aws": {"amazon web services", "amazon ec2", "aws lambda", "s3"},
    "gcp": {"google cloud", "google cloud platform"},
    "azure": {"microsoft azure"},
    "rest api": {"rest", "restful", "restful api", "restful apis", "web apis"},
    "graphql": {"gql"},
    "ci/cd": {"continuous integration", "continuous deployment", "github actions", "gitlab ci", "jenkins"},
    "machine learning": {"ml"},
    "artificial intelligence": {"ai", "genai"},
    "deep learning": {"dl", "neural networks"},
    "go": {"golang"},
    "c++": {"cpp"},
    "c#": {"csharp", "c-sharp", ".net", "dotnet"},
    "fastapi": {"fast-api"},
    "html": {"html5"},
    "css": {"css3", "tailwind", "sass", "scss"},
    "git": {"github", "gitlab", "version control"},
    "sql": {"relational database", "rdbms"},
    "nosql": {"non-relational database"},
}

# Reverse mapping: alias -> canonical key
ALIAS_TO_CANONICAL: Dict[str, str] = {}
for canonical, aliases in SKILL_ALIASES.items():
    ALIAS_TO_CANONICAL[canonical.lower()] = canonical.lower()
    for alias in aliases:
        ALIAS_TO_CANONICAL[alias.lower()] = canonical.lower()


class SkillsMatcherAgent:
    """Agent 3: Deterministic, alias-aware skills comparison with explicit vs inferred attribution."""

    def __init__(self):
        pass

    def match_skills(self, resume: ResumeParsedData, jd: JobDescriptionParsed) -> SkillsAnalysisResult:
        # Build candidate resume skills pool (from structured skills + text mentions)
        resume_raw_skills = set(resume.skills)
        resume_full_text = resume.normalized_text.lower()

        # Build lookup for evidence and explicit status
        evidence_lookup: Dict[str, SkillEvidenceItem] = {}
        for item in resume.all_skills_detailed:
            evidence_lookup[item.name.lower()] = item

        explicit_set = {s.lower() for s in resume.explicit_skills}

        # Canonicalize resume skills
        candidate_canonical_map: Dict[str, str] = {}  # canonical -> actual resume term
        for s in resume_raw_skills:
            norm_s = s.strip().lower()
            canonical = ALIAS_TO_CANONICAL.get(norm_s, norm_s)
            candidate_canonical_map[canonical] = s

        matched_required: List[str] = []
        alias_matches: List[Dict[str, str]] = []
        missing_required: List[str] = []
        inferred_matches: List[str] = []
        all_items: List[SkillMatchItem] = []

        # 1. Evaluate Required Skills
        for req_skill in jd.required_skills:
            req_norm = req_skill.strip().lower()
            req_canonical = ALIAS_TO_CANONICAL.get(req_norm, req_norm)

            found, matched_term, match_kind = self._check_skill_presence(
                req_norm, req_canonical, candidate_canonical_map, resume_full_text
            )

            if found and matched_term:
                matched_required.append(req_skill)
                # Check if it was explicit or inferred
                term_low = matched_term.lower()
                evidence_item = evidence_lookup.get(term_low)
                is_explicit = term_low in explicit_set or (evidence_item and evidence_item.is_explicit)
                source = "explicit" if is_explicit else (evidence_item.source if evidence_item else "experience")
                snippet = evidence_item.evidence_snippet if evidence_item else f"Matched in resume: '{matched_term}'"

                if not is_explicit:
                    inferred_matches.append(req_skill)

                if match_kind == "exact":
                    all_items.append(
                        SkillMatchItem(
                            skill=req_skill,
                            match_type="exact",
                            matched_resume_term=matched_term,
                            confidence=1.0,
                            category="Required",
                            source=source,
                            evidence_snippet=snippet,
                        )
                    )
                else:  # alias
                    alias_matches.append({"requested": req_skill, "found": matched_term})
                    all_items.append(
                        SkillMatchItem(
                            skill=req_skill,
                            match_type="alias",
                            matched_resume_term=matched_term,
                            confidence=0.9,
                            category="Required",
                            source=source,
                            evidence_snippet=snippet,
                        )
                    )
            else:
                missing_required.append(req_skill)
                all_items.append(
                    SkillMatchItem(
                        skill=req_skill,
                        match_type="missing_required",
                        matched_resume_term=None,
                        confidence=0.0,
                        category="Required",
                        source="missing",
                        evidence_snippet=None,
                    )
                )

        # 2. Evaluate Preferred Skills
        matched_preferred: List[str] = []
        missing_preferred: List[str] = []
        for pref_skill in jd.preferred_skills:
            pref_norm = pref_skill.strip().lower()
            pref_canonical = ALIAS_TO_CANONICAL.get(pref_norm, pref_norm)

            found, matched_term, match_kind = self._check_skill_presence(
                pref_norm, pref_canonical, candidate_canonical_map, resume_full_text
            )

            if found and matched_term:
                matched_preferred.append(pref_skill)
                term_low = matched_term.lower()
                evidence_item = evidence_lookup.get(term_low)
                is_explicit = term_low in explicit_set or (evidence_item and evidence_item.is_explicit)
                source = "explicit" if is_explicit else (evidence_item.source if evidence_item else "experience")
                snippet = evidence_item.evidence_snippet if evidence_item else f"Matched in resume: '{matched_term}'"

                if not is_explicit:
                    inferred_matches.append(pref_skill)

                if match_kind == "alias":
                    alias_matches.append({"requested": pref_skill, "found": matched_term})

                all_items.append(
                    SkillMatchItem(
                        skill=pref_skill,
                        match_type="exact" if match_kind == "exact" else "alias",
                        matched_resume_term=matched_term,
                        confidence=1.0 if match_kind == "exact" else 0.9,
                        category="Preferred",
                        source=source,
                        evidence_snippet=snippet,
                    )
                )
            else:
                missing_preferred.append(pref_skill)
                all_items.append(
                    SkillMatchItem(
                        skill=pref_skill,
                        match_type="missing_preferred",
                        matched_resume_term=None,
                        confidence=0.0,
                        category="Preferred",
                        source="missing",
                        evidence_snippet=None,
                    )
                )

        # 3. Candidate Extra Skills (skills candidate has that weren't in JD)
        matched_canonical_set = {
            ALIAS_TO_CANONICAL.get(s.lower(), s.lower()) for s in (matched_required + matched_preferred)
        }
        candidate_extra: List[str] = []
        for skill in resume_raw_skills:
            s_can = ALIAS_TO_CANONICAL.get(skill.lower(), skill.lower())
            if s_can not in matched_canonical_set:
                candidate_extra.append(skill)
                ev_item = evidence_lookup.get(skill.lower())
                all_items.append(
                    SkillMatchItem(
                        skill=skill,
                        match_type="candidate_extra",
                        matched_resume_term=skill,
                        confidence=1.0,
                        category="Extra Candidate Skill",
                        source=ev_item.source if ev_item else "explicit",
                        evidence_snippet=ev_item.evidence_snippet if ev_item else f"Possessed: '{skill}'",
                    )
                )

        # Calculate match percentages
        tot_req = len(jd.required_skills)
        req_pct = round((len(matched_required) / tot_req * 100), 1) if tot_req > 0 else 100.0

        tot_pref = len(jd.preferred_skills)
        pref_pct = round((len(matched_preferred) / tot_pref * 100), 1) if tot_pref > 0 else 100.0

        return SkillsAnalysisResult(
            total_required=tot_req,
            total_preferred=tot_pref,
            matched_required_count=len(matched_required),
            matched_preferred_count=len(matched_preferred),
            required_match_percentage=req_pct,
            preferred_match_percentage=pref_pct,
            exact_matches=sorted(list(set(matched_required))),
            alias_matches=alias_matches,
            missing_required=sorted(missing_required),
            missing_preferred=sorted(missing_preferred),
            candidate_extra_skills=sorted(candidate_extra),
            inferred_matches=sorted(list(set(inferred_matches))),
            all_match_items=all_items,
        )

    def _check_skill_presence(
        self,
        skill_norm: str,
        skill_canonical: str,
        candidate_canonical_map: Dict[str, str],
        resume_full_text: str,
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """Check if skill is present in candidate skills or text, differentiating exact vs alias."""
        # 1. Exact match in candidate extracted skills
        if skill_norm in candidate_canonical_map:
            return True, candidate_canonical_map[skill_norm], "exact"

        # 2. Canonical alias match in candidate extracted skills
        if skill_canonical in candidate_canonical_map:
            return True, candidate_canonical_map[skill_canonical], "alias"

        # 3. Exact word boundary match in resume full text
        pattern = r"\b" + re.escape(skill_norm) + r"\b"
        if re.search(pattern, resume_full_text):
            return True, skill_norm, "exact"

        # 4. Check known aliases in resume full text
        aliases = SKILL_ALIASES.get(skill_canonical, set())
        for alias in aliases:
            a_pat = r"\b" + re.escape(alias.lower()) + r"\b"
            if re.search(a_pat, resume_full_text):
                return True, alias, "alias"

        return False, None, None
