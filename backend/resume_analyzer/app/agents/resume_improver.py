"""Agent 5: Resume Improvement Agent.
Orchestrates generative improvements via Gemini or deterministic rule-based improvements.
"""
from typing import List, Optional
from ..schemas.resume import ResumeParsedData
from ..schemas.job_description import JobDescriptionParsed
from ..schemas.analysis import (
    SkillsAnalysisResult,
    ScoringBreakdown,
    ResumeImprovementResult,
    BulletRewrite,
)
from ..services.gemini_service import GeminiService


WEAK_OPENERS = [
    ("responsible for", "Spearheaded and executed"),
    ("worked on", "Engineered and delivered"),
    ("helped with", "Collaborated cross-functionally to drive"),
    ("assisted with", "Co-engineered and accelerated"),
    ("handled", "Managed and optimized"),
    ("involved in", "Contributed to high-impact development of"),
    ("duties included", "Successfully executed"),
]


class ResumeImproverAgent:
    """Agent 5: Generates grounded resume recommendations and bullet rewrites."""

    def __init__(self, gemini_service: Optional[GeminiService] = None):
        self.gemini_service = gemini_service or GeminiService()

    def generate_improvements(
        self,
        resume: ResumeParsedData,
        jd: JobDescriptionParsed,
        skills: SkillsAnalysisResult,
        scoring: ScoringBreakdown,
    ) -> ResumeImprovementResult:
        # Try Gemini if configured
        if self.gemini_service.is_configured():
            ai_data = self.gemini_service.generate_improvements(
                resume_text=resume.normalized_text,
                job_title=jd.title,
                job_description=jd.normalized_text,
                matched_skills=skills.exact_matches,
                missing_skills=skills.missing_required + skills.missing_preferred,
            )

            if ai_data and isinstance(ai_data, dict):
                bullet_rewrites = []
                for b in ai_data.get("bullet_rewrites", []):
                    if isinstance(b, dict) and b.get("original_bullet") and b.get("rewritten_bullet"):
                        bullet_rewrites.append(
                            BulletRewrite(
                                original_bullet=b["original_bullet"],
                                rewritten_bullet=b["rewritten_bullet"],
                                reasoning=b.get("reasoning", "Optimized for clarity and ATS keyword density."),
                                target_role_or_project=b.get("target_role_or_project", "Experience"),
                            )
                        )

                return ResumeImprovementResult(
                    strengths=ai_data.get("strengths", self._extract_deterministic_strengths(resume, skills, scoring)),
                    critical_improvements=ai_data.get(
                        "critical_improvements", self._extract_deterministic_improvements(skills, scoring)
                    ),
                    bullet_rewrites=bullet_rewrites or self._generate_rule_based_rewrites(resume, jd, skills),
                    recruiter_summary=ai_data.get("recruiter_summary", self._generate_rule_based_recruiter_summary(resume, jd, scoring)),
                    tailored_summary_draft=ai_data.get(
                        "tailored_summary_draft", self._generate_rule_based_summary_draft(resume, jd, skills)
                    ),
                    action_plan=ai_data.get("action_plan", self._generate_rule_based_action_plan(skills)),
                    is_ai_generated=True,
                    ai_model_used=self.gemini_service.model_name,
                )

        # Deterministic Rule-Based Fallback
        return self._generate_deterministic_improvements(resume, jd, skills, scoring)

    def _generate_deterministic_improvements(
        self,
        resume: ResumeParsedData,
        jd: JobDescriptionParsed,
        skills: SkillsAnalysisResult,
        scoring: ScoringBreakdown,
    ) -> ResumeImprovementResult:
        strengths = self._extract_deterministic_strengths(resume, skills, scoring)
        critical_improvements = self._extract_deterministic_improvements(skills, scoring)
        bullet_rewrites = self._generate_rule_based_rewrites(resume, jd, skills)
        recruiter_summary = self._generate_rule_based_recruiter_summary(resume, jd, scoring)
        summary_draft = self._generate_rule_based_summary_draft(resume, jd, skills)
        action_plan = self._generate_rule_based_action_plan(skills)

        return ResumeImprovementResult(
            strengths=strengths,
            critical_improvements=critical_improvements,
            bullet_rewrites=bullet_rewrites,
            recruiter_summary=recruiter_summary,
            tailored_summary_draft=summary_draft,
            action_plan=action_plan,
            is_ai_generated=False,
            ai_model_used=None,
        )

    def _extract_deterministic_strengths(
        self,
        resume: ResumeParsedData,
        skills: SkillsAnalysisResult,
        scoring: ScoringBreakdown,
    ) -> List[str]:
        strengths = []
        if skills.required_match_percentage >= 70:
            strengths.append(f"Strong required skill alignment ({int(skills.required_match_percentage)}% of mandatory skills demonstrated).")
        if skills.exact_matches:
            top_matches = ", ".join(skills.exact_matches[:4])
            strengths.append(f"Demonstrates core technical competencies: {top_matches}.")
        if len(resume.experience) >= 2:
            strengths.append(f"Established career trajectory with {len(resume.experience)} documented professional engagements.")
        if resume.education:
            strengths.append(f"Verified educational background: {resume.education[0].degree or 'Degree documented'}.")
        if scoring.categories.get("completeness_and_readability", {}).raw_score >= 80:
            strengths.append("Clean, ATS-parseable structure with standard heading hierarchy and contact visibility.")
        if not strengths:
            strengths.append("Foundational technical background with clear capacity for domain adaptation.")
        return strengths

    def _extract_deterministic_improvements(
        self,
        skills: SkillsAnalysisResult,
        scoring: ScoringBreakdown,
    ) -> List[str]:
        improvements = []
        if skills.missing_required:
            missing_str = ", ".join(skills.missing_required[:3])
            improvements.append(f"Integrate missing mandatory competencies: {missing_str} into project or role descriptions.")
        if skills.missing_preferred:
            pref_str = ", ".join(skills.missing_preferred[:3])
            improvements.append(f"Demonstrate familiarity with preferred bonus tools: {pref_str}.")
        
        exp_score = scoring.categories.get("relevant_experience")
        if exp_score and exp_score.raw_score < 75:
            improvements.append("Increase density of quantified metrics (percentages, scale, dollar impact) in experience bullets.")

        read_score = scoring.categories.get("completeness_and_readability")
        if read_score and read_score.raw_score < 70:
            improvements.append("Review contact details and ensure all standard sections (Summary, Experience, Education, Skills) are present.")

        return improvements or ["Review wording to maximize alignment with target job title keywords."]

    def _generate_rule_based_rewrites(
        self,
        resume: ResumeParsedData,
        jd: JobDescriptionParsed,
        skills: SkillsAnalysisResult,
    ) -> List[BulletRewrite]:
        rewrites: List[BulletRewrite] = []
        candidates_to_rewrite = []

        # Gather bullets from experience
        for exp in resume.experience:
            for bullet in exp.responsibilities:
                candidates_to_rewrite.append((bullet, exp.job_title or "Role"))

        # Check weak phrasing
        for original, role in candidates_to_rewrite:
            low_b = original.lower()
            for weak, strong in WEAK_OPENERS:
                if weak in low_b:
                    # Construct improved draft
                    # Replace weak phrase with strong action verb
                    idx = low_b.find(weak)
                    after_weak = original[idx + len(weak):].strip()
                    rewritten = f"{strong} {after_weak} to enhance performance and deliver measurable outcomes."
                    rewrites.append(
                        BulletRewrite(
                            original_bullet=original,
                            rewritten_bullet=rewritten,
                            reasoning=f"Replaced passive phrasing '{weak}' with decisive action verb '{strong}' and outcome orientation.",
                            target_role_or_project=role,
                        )
                    )
                    break
            if len(rewrites) >= 3:
                break

        # If no weak openers were found, pick the shortest bullet and enhance it
        if not rewrites and candidates_to_rewrite:
            orig, role = candidates_to_rewrite[0]
            matched_kw = skills.exact_matches[0] if skills.exact_matches else "key technologies"
            rewritten = f"Architected and implemented {orig}, leveraging {matched_kw} to optimize execution and workflow reliability."
            rewrites.append(
                BulletRewrite(
                    original_bullet=orig,
                    rewritten_bullet=rewritten,
                    reasoning="Enhanced bullet with strong action verb, specific tooling context, and delivery focus.",
                    target_role_or_project=role,
                )
            )

        return rewrites

    def _generate_rule_based_recruiter_summary(
        self,
        resume: ResumeParsedData,
        jd: JobDescriptionParsed,
        scoring: ScoringBreakdown,
    ) -> str:
        score_val = scoring.overall_score
        tier = "strong candidate" if score_val >= 75 else ("promising candidate with addressable skill gaps" if score_val >= 60 else "developing candidate")
        role_title = jd.title
        skills_summary = ", ".join(resume.skills[:4]) if resume.skills else "technical competencies"

        return (
            f"The candidate presents as a {tier} for the {role_title} role (Overall Compatibility: {score_val}/100). "
            f"Key demonstrated strengths include hands-on experience in {skills_summary}. "
            f"Addressing identified keyword and qualification gaps will significantly maximize ATS pass-through and recruiter screening interest."
        )

    def _generate_rule_based_summary_draft(
        self,
        resume: ResumeParsedData,
        jd: JobDescriptionParsed,
        skills: SkillsAnalysisResult,
    ) -> str:
        target_role = jd.title
        top_skills = ", ".join(skills.exact_matches[:4]) if skills.exact_matches else "modern software engineering"
        exp_count = len(resume.experience)
        exp_phrase = f"with experience across {exp_count} progressive roles" if exp_count > 0 else "with a strong technical foundation"

        return (
            f"Results-oriented {target_role} {exp_phrase}, specializing in {top_skills}. "
            f"Demonstrated track record of delivering reliable systems and driving cross-functional technical solutions. "
            f"Eager to contribute high-impact engineering discipline to {jd.company or 'the organization'}."
        )

    def _generate_rule_based_action_plan(self, skills: SkillsAnalysisResult) -> List[str]:
        plan = []
        if skills.missing_required:
            plan.append(f"Priority 1: Audit projects to incorporate missing required skills ({', '.join(skills.missing_required[:3])}).")
        else:
            plan.append("Priority 1: Maintain 100% required skill visibility in both skills list and bullet points.")

        if skills.missing_preferred:
            plan.append(f"Priority 2: Add certifications or coursework for bonus skills ({', '.join(skills.missing_preferred[:2])}).")

        plan.append("Priority 3: Ensure each work experience bullet adheres to the Action Verb + Context + Measurable Result formula.")
        plan.append("Priority 4: Verify contact details, LinkedIn URL, and portfolio links are clickable and up to date.")
        return plan
