"""
Resume Analyzer Integration Adapter.
Provides a clean, stable interface bridging Adaptive Interview Intelligence
with the copied ResumeAnalyzerAgent multi-agent pipeline.
"""

import os
import io
import re
import uuid
import hashlib
import logging
from typing import Dict, Any, Optional, List, Tuple

from backend.resume_analyzer.app.services.extractor import extract_resume_text
from backend.resume_analyzer.app.agents.resume_parser import ResumeParserAgent
from backend.resume_analyzer.app.agents.job_description_analyzer import JobDescriptionAnalyzerAgent
from backend.resume_analyzer.app.agents.skills_matcher import SkillsMatcherAgent
from backend.resume_analyzer.app.agents.ats_scorer import ATSScorerAgent
from backend.resume_analyzer.app.agents.integrity_detector import ResumeIntegrityAgent
from backend.resume_analyzer.app.agents.resume_improver import ResumeImproverAgent
from backend.resume_analyzer.app.schemas.job_description import JobDescriptionInput
from backend.resume_analyzer.app.schemas.resume import ResumeParsedData

logger = logging.getLogger("adaptive_interview.resume_adapter")

# Max upload size: 10MB
MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024
ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt"}


class ResumeAnalyzerAdapter:
    """Stable integration layer wrapping the ResumeAnalyzerAgent multi-agent suite."""

    def __init__(self):
        self.parser = ResumeParserAgent()
        self.integrity_detector = ResumeIntegrityAgent()
        self.jd_analyzer = JobDescriptionAnalyzerAgent()
        self.skills_matcher = SkillsMatcherAgent()
        self.ats_scorer = ATSScorerAgent()
        self.improver = ResumeImproverAgent()

        # In-memory store for analyzed resumes during active sessions
        self._store: Dict[str, Dict[str, Any]] = {}
        self._hash_cache: Dict[str, Dict[str, Any]] = {}

    def validate_file(self, filename: str, file_bytes: bytes) -> Tuple[bool, Optional[str]]:
        """Validates file extension and size constraints."""
        if not filename or not file_bytes:
            return False, "File name or file content is empty."

        ext = os.path.splitext(filename.lower())[1]
        if ext not in ALLOWED_EXTENSIONS:
            return (
                False,
                f"Unsupported file format '{ext}'. Allowed formats: {', '.join(sorted(ALLOWED_EXTENSIONS))}.",
            )

        if len(file_bytes) > MAX_FILE_SIZE_BYTES:
            mb_size = round(len(file_bytes) / (1024 * 1024), 2)
            return False, f"File size ({mb_size}MB) exceeds maximum limit of 10MB."

        return True, None

    def extract_text(self, filename: str, file_bytes: bytes) -> Dict[str, Any]:
        """Extracts text from PDF, DOCX, or plain text."""
        ext = os.path.splitext(filename.lower())[1]

        if ext in (".pdf", ".docx"):
            return extract_resume_text(file_bytes, filename)
        elif ext == ".txt":
            try:
                text = file_bytes.decode("utf-8")
            except UnicodeDecodeError:
                text = file_bytes.decode("latin-1", errors="replace")

            clean_text = text.strip()
            word_count = len(clean_text.split()) if clean_text else 0
            return {
                "text": clean_text,
                "is_scanned": False,
                "warning": "" if clean_text else "Text file is empty.",
                "file_type": "txt",
                "word_count": word_count,
                "char_count": len(clean_text),
            }
        else:
            raise ValueError(f"Unsupported file extension: {ext}")

    def analyze_resume(
        self,
        filename: str,
        file_bytes: bytes,
        job_title: Optional[str] = None,
        job_description: Optional[str] = None,
        company: Optional[str] = None,
        required_skills: Optional[List[str]] = None,
        preferred_skills: Optional[List[str]] = None,
        target_role: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Parses resume, audits integrity, executes domain routing, and pre-generates interview plan.
        Returns a normalized dictionary structure suitable for the interview intelligence app.
        """
        import time
        t_start = time.perf_counter()
        # 1. Validation
        is_valid, err = self.validate_file(filename, file_bytes)
        if not is_valid:
            return {
                "is_success": False,
                "error_message": err,
                "resume_id": None,
            }

        file_hash = hashlib.sha256(file_bytes).hexdigest()
        cache_key = f"{file_hash}_{target_role or job_title or 'default'}"
        if cache_key in self._hash_cache:
            cached_data = dict(self._hash_cache[cache_key])
            fresh_id = str(uuid.uuid4())
            cached_data["resume_id"] = fresh_id
            self._store[fresh_id] = cached_data
            logger.info("[PERF] Returning cached resume profile for key %s (duration <0.001s)", cache_key)
            return cached_data

        # 2. Text Extraction
        try:
            extracted = self.extract_text(filename, file_bytes)
        except Exception as e:
            return {
                "is_success": False,
                "error_message": f"Text extraction failed: {str(e)}",
                "resume_id": None,
            }

        raw_text = extracted.get("text", "")
        if not raw_text or len(raw_text.strip()) < 20:
            return {
                "is_success": False,
                "error_message": extracted.get("warning") or "Insufficient text extracted from resume.",
                "resume_id": None,
            }

        # 3. Agent 1: Parse Resume Structure & Extract Understanding
        try:
            parsed_resume: ResumeParsedData = self.parser.parse(
                text=raw_text,
                file_name=filename,
                is_scanned=extracted.get("is_scanned", False),
                warning=extracted.get("warning", ""),
            )
        except Exception as e:
            return {
                "is_success": False,
                "error_message": f"Resume parsing agent encountered an error: {str(e)}",
                "resume_id": None,
            }

        # 4. Agent 2: Integrity & Completeness Audit
        try:
            audit = self.integrity_detector.audit(
                resume=parsed_resume,
                raw_text=raw_text,
                file_name=filename,
                is_scanned=extracted.get("is_scanned", False),
                warning=extracted.get("warning", ""),
            )
            integrity_dict = audit.model_dump()
        except Exception as e:
            logger.warning(f"Integrity audit warning: {e}")
            integrity_dict = {
                "overall_status": "passed",
                "issues": [],
                "completeness_score": 80.0,
            }

        # Evidence-Based Authenticity and Integrity Assessment
        try:
            from backend.resume_analyzer.integrity_audit import ResumeIntegrityAssessor
            authenticity_report = ResumeIntegrityAssessor.audit_profile(
                parsed_resume=parsed_resume,
                raw_text=raw_text,
                filename=filename,
            )
            authenticity_dict = authenticity_report.model_dump()
        except Exception as auth_err:
            logger.warning(f"Authenticity audit error: {auth_err}")
            authenticity_dict = {
                "outcome": "no_inconsistencies",
                "outcome_label": "No significant inconsistencies detected",
                "headline": "Standard structural coherence",
                "summary_explanation": "Resume parsed with baseline consistency.",
                "risk_score": 0.0,
                "indicators": [],
                "section_consistency": {},
                "clarification_topics": [],
            }

        # 5. Optional Agent 3-5: Job Description Matching, ATS Scoring, and Improvements
        jd_match_result: Optional[Dict[str, Any]] = None
        ats_score: Optional[float] = None
        matched_skills: List[str] = []
        missing_skills: List[str] = []
        improvements_summary: Optional[Dict[str, Any]] = None

        if job_title and (job_description or required_skills):
            try:
                jd_input = JobDescriptionInput(
                    title=job_title.strip(),
                    company=company.strip() if company else None,
                    description=job_description.strip() if job_description else f"Target role for {job_title}",
                    required_skills=required_skills or [],
                    preferred_skills=preferred_skills or [],
                )
                parsed_jd = self.jd_analyzer.analyze(jd_input)
                skills_data = self.skills_matcher.match_skills(parsed_resume, parsed_jd)
                scoring_data = self.ats_scorer.calculate_score(parsed_resume, parsed_jd, skills_data)
                improvements_data = self.improver.generate_improvements(
                    resume=parsed_resume,
                    jd=parsed_jd,
                    skills=skills_data,
                    scoring=scoring_data,
                )

                jd_match_result = {
                    "job_title": parsed_jd.title,
                    "company": parsed_jd.company,
                    "required_match_percentage": skills_data.required_match_percentage,
                    "preferred_match_percentage": skills_data.preferred_match_percentage,
                    "exact_matches": skills_data.exact_matches,
                    "missing_required": skills_data.missing_required,
                    "missing_preferred": skills_data.missing_preferred,
                }
                ats_score = scoring_data.overall_score
                matched_skills = skills_data.exact_matches
                missing_skills = skills_data.missing_required
                improvements_summary = {
                    "strengths": improvements_data.strengths,
                    "critical_improvements": improvements_data.critical_improvements,
                    "recruiter_summary": improvements_data.recruiter_summary,
                    "action_plan": improvements_data.action_plan,
                }
            except Exception as e:
                logger.warning(f"Job description matching encountered error: {e}")

        # 6. Normalize skill evidence items
        skill_evidence_list: List[Dict[str, Any]] = []
        for se in getattr(parsed_resume, "all_skills_detailed", []):
            skill_evidence_list.append({
                "skill": se.name,
                "category": se.category,
                "source": se.source,
                "is_explicit": se.is_explicit,
                "evidence_snippet": se.evidence_snippet,
                "confidence": se.confidence,
            })

        # Experience entries
        experience_list = [exp.model_dump() for exp in parsed_resume.experience]
        education_list = [edu.model_dump() for edu in parsed_resume.education]
        projects_list = [proj.model_dump() for proj in parsed_resume.projects]

        total_exp_years = sum(float(exp.years_calculated or 0.0) for exp in parsed_resume.experience)

        resume_id = str(uuid.uuid4())
        normalized_profile = {
            "is_success": True,
            "resume_id": resume_id,
            "filename": filename,
            "candidate_name": parsed_resume.contact_info.name or "Candidate",
            "contact_info": parsed_resume.contact_info.model_dump(),
            "summary": parsed_resume.summary,
            "skills": sorted(list(set(parsed_resume.skills))),
            "claimed_skills": sorted(list(set(parsed_resume.skills))),
            "skill_evidence": skill_evidence_list,
            "experience": experience_list,
            "education": education_list,
            "projects": projects_list,
            "total_experience_years": round(total_exp_years, 1),
            "integrity_audit": integrity_dict,
            "integrity_status": integrity_dict.get("overall_status", "passed"),
            "authenticity_assessment": authenticity_dict,
            "authenticity_outcome": authenticity_dict.get("outcome", "no_inconsistencies"),
            "authenticity_headline": authenticity_dict.get("headline", ""),
            "job_matching": jd_match_result,
            "ats_score": ats_score,
            "matched_skills": matched_skills,
            "missing_skills": missing_skills,
            "improvements": improvements_summary,
            "raw_text_length": len(raw_text),
            "file_hash": hashlib.sha256(file_bytes).hexdigest(),
        }

        # 7. Automatic Domain Routing, Role Eligibility & Initial Plan Generation
        try:
            from backend.domain_router import DomainRouter
            from backend.interview_plan import InterviewPlanner
            from backend.resume_analyzer.eligibility import RoleEligibilityAssessor

            effective_role = target_role or job_title or "Software Engineer"
            routing = DomainRouter.route(normalized_profile, target_role=effective_role)

            normalized_profile["target_role"] = effective_role
            normalized_profile["routed_track"] = routing["routed_track"]
            normalized_profile["role_family"] = routing.get("role_family", "python")
            normalized_profile["role_title"] = routing.get("role_title", effective_role)
            normalized_profile["coverage_level"] = routing.get("coverage_level", "Specialized Agent")
            normalized_profile["specialization_mode"] = routing.get("specialization_mode", "core")
            normalized_profile["domain_confidence"] = routing["domain_confidence"]
            normalized_profile["routing_reason"] = routing["routing_reason"]
            normalized_profile["recommended_tech_stack"] = routing.get("recommended_tech_stack")
            normalized_profile["is_mixed_profile"] = routing.get("is_mixed_profile", False)
            normalized_profile["focus_competencies"] = routing.get("focus_competencies", [])
            normalized_profile["focus_topics"] = routing.get("focus_topics", [])

            # Role-Based Eligibility Assessment
            eligibility_res = RoleEligibilityAssessor.assess_eligibility(
                resume_profile=normalized_profile,
                target_role=effective_role,
                integrity_status=authenticity_dict.get("outcome", "no_inconsistencies"),
            )
            eligibility_dict = eligibility_res.model_dump()
            normalized_profile["eligibility_assessment"] = eligibility_dict
            normalized_profile["eligibility_status"] = eligibility_dict.get("outcome", "eligible")
            normalized_profile["eligibility_headline"] = eligibility_dict.get("headline", "")
            normalized_profile["eligibility_reasons"] = eligibility_dict.get("reasons_supporting_result", [])

            # Pre-generate interview plan for instant start
            initial_plan = InterviewPlanner.create_plan(
                resume_profile=normalized_profile,
                track=routing["routed_track"],
                max_questions=5,
                difficulty_mode="adaptive",
                tech_stack=routing.get("recommended_tech_stack"),
                target_role=effective_role,
                job_description=job_description,
                company=company,
            )
            normalized_profile["interview_plan"] = initial_plan.model_dump()
        except Exception as route_err:
            logger.warning("[ROUTING_ERROR] Could not auto-route resume: %s", route_err)
            normalized_profile["routed_track"] = "python"
            normalized_profile["role_family"] = "python"
            normalized_profile["role_title"] = "Python Developer"
            normalized_profile["domain_confidence"] = 0.70
            normalized_profile["routing_reason"] = "Defaulted to Python track."

        duration_sec = time.perf_counter() - t_start
        logger.info(
            "[PERF] Resume analysis completed in %.3fs for file '%s' (routed to %s, conf=%.2f)",
            duration_sec, filename, normalized_profile.get("routed_track"), normalized_profile.get("domain_confidence", 0.0)
        )

        # Store in cache
        self._store[resume_id] = normalized_profile
        self._hash_cache[cache_key] = dict(normalized_profile)
        return normalized_profile

    def get_resume_profile(self, resume_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves stored resume profile by ID."""
        return self._store.get(resume_id)


_GLOBAL_ADAPTER = ResumeAnalyzerAdapter()


def get_resume_adapter() -> ResumeAnalyzerAdapter:
    """Returns the singleton adapter instance."""
    return _GLOBAL_ADAPTER
