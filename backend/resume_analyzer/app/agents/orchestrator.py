"""Workflow orchestrator coordinating Agents for end-to-end resume analysis."""
import uuid
import datetime
from typing import Dict, Any, Optional
from .resume_parser import ResumeParserAgent
from .job_description_analyzer import JobDescriptionAnalyzerAgent
from .skills_matcher import SkillsMatcherAgent
from .ats_scorer import ATSScorerAgent
from .resume_improver import ResumeImproverAgent
from .integrity_detector import ResumeIntegrityAgent
from ..services.gemini_service import GeminiService
from ..schemas.job_description import JobDescriptionInput
from ..schemas.analysis import AnalysisDetailResponse
from ..database.db import save_analysis


class ResumeAnalyzerOrchestrator:
    """Orchestrates the multi-agent pipeline deterministically with optional Gemini enhancements."""

    def __init__(self, gemini_service: Optional[GeminiService] = None):
        self.gemini_service = gemini_service or GeminiService()
        self.resume_parser = ResumeParserAgent()
        self.integrity_detector = ResumeIntegrityAgent()
        self.jd_analyzer = JobDescriptionAnalyzerAgent()
        self.skills_matcher = SkillsMatcherAgent()
        self.ats_scorer = ATSScorerAgent()
        self.resume_improver = ResumeImproverAgent(self.gemini_service)

    def run_analysis(
        self,
        resume_text: str,
        job_input: JobDescriptionInput,
        file_name: str = "Uploaded_Resume.pdf",
        is_scanned: bool = False,
        warning: str = "",
    ) -> AnalysisDetailResponse:
        analysis_id = str(uuid.uuid4())

        # Step 1: Agent 1 - Parse Resume & Extract Understanding
        resume_data = self.resume_parser.parse(
            text=resume_text,
            file_name=file_name,
            is_scanned=is_scanned,
            warning=warning,
        )

        # Step 2: Agent - Completeness & Integrity Audit
        integrity_audit = self.integrity_detector.audit(
            resume=resume_data,
            raw_text=resume_text,
            file_name=file_name,
            is_scanned=is_scanned,
            warning=warning,
        )

        # Step 3: Agent 2 - Analyze Job Description
        jd_data = self.jd_analyzer.analyze(job_input)

        # Step 4: Agent 3 - Match Skills & Aliases (Explicit & Inferred)
        skills_data = self.skills_matcher.match_skills(resume_data, jd_data)

        # Step 5: Agent 4 - ATS Scoring
        scoring_data = self.ats_scorer.calculate_score(resume_data, jd_data, skills_data)

        # Step 6: Agent 5 - Recommendations & Rewrites
        improvements_data = self.resume_improver.generate_improvements(
            resume=resume_data,
            jd=jd_data,
            skills=skills_data,
            scoring=scoring_data,
        )

        # Step 7: Persist in SQLite
        save_analysis(
            analysis_id=analysis_id,
            file_name=file_name,
            job_title=jd_data.title,
            company=jd_data.company,
            overall_score=scoring_data.overall_score,
            resume_data=resume_data.model_dump(),
            job_description=jd_data.model_dump(),
            skills_analysis=skills_data.model_dump(),
            scoring_breakdown=scoring_data.model_dump(),
            improvements=improvements_data.model_dump(),
            is_ai_powered=improvements_data.is_ai_generated,
            integrity_audit=integrity_audit.model_dump(),
        )

        created_at_str = datetime.datetime.now(datetime.timezone.utc).isoformat()

        return AnalysisDetailResponse(
            id=analysis_id,
            created_at=created_at_str,
            file_name=file_name,
            overall_score=scoring_data.overall_score,
            resume_data=resume_data,
            job_description=jd_data,
            skills_analysis=skills_data,
            scoring_breakdown=scoring_data,
            improvements=improvements_data,
            integrity_audit=integrity_audit,
        )
