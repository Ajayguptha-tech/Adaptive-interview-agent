"""Agent 4: ATS Scoring Agent.
Calculates transparent, deterministic scores from 0 to 100 across 5 explainable categories.
Weights are configurable and sum to 100%.
"""
from typing import Dict, List, Optional
from ..schemas.resume import ResumeParsedData
from ..schemas.job_description import JobDescriptionParsed
from ..schemas.analysis import SkillsAnalysisResult, ScoringBreakdown, CategoryScore


DEFAULT_WEIGHTS = {
    "required_skills": 0.35,
    "preferred_skills": 0.15,
    "relevant_experience": 0.25,
    "education_and_certifications": 0.15,
    "completeness_and_readability": 0.10,
}


class ATSScorerAgent:
    """Agent 4: Deterministic, transparent ATS compatibility scoring."""

    def __init__(self, weights: Optional[Dict[str, float]] = None):
        self.weights = weights or dict(DEFAULT_WEIGHTS)
        # Validate weights sum to 1.0 (allow minor float epsilon)
        total_weight = sum(self.weights.values())
        if not (0.99 <= total_weight <= 1.01):
            raise ValueError(f"Category weights must sum to 1.0 (current sum: {total_weight})")

    def calculate_score(
        self,
        resume: ResumeParsedData,
        jd: JobDescriptionParsed,
        skills: SkillsAnalysisResult,
    ) -> ScoringBreakdown:
        categories: Dict[str, CategoryScore] = {}

        # 1. Required Skills Score
        req_score, req_exp, req_ev, req_rec = self._score_required_skills(skills, jd)
        w_req = self.weights["required_skills"]
        categories["required_skills"] = CategoryScore(
            category_key="required_skills",
            category_name="Required Skills Coverage",
            raw_score=req_score,
            weight=w_req,
            weighted_score=round(req_score * w_req, 2),
            explanation=req_exp,
            evidence=req_ev,
            recommendations=req_rec,
        )

        # 2. Preferred Skills Score
        pref_score, pref_exp, pref_ev, pref_rec = self._score_preferred_skills(skills, jd)
        w_pref = self.weights["preferred_skills"]
        categories["preferred_skills"] = CategoryScore(
            category_key="preferred_skills",
            category_name="Preferred Skills & Bonus Qualifications",
            raw_score=pref_score,
            weight=w_pref,
            weighted_score=round(pref_score * w_pref, 2),
            explanation=pref_exp,
            evidence=pref_ev,
            recommendations=pref_rec,
        )

        # 3. Relevant Experience Score
        exp_score, exp_exp, exp_ev, exp_rec = self._score_experience(resume, jd)
        w_exp = self.weights["relevant_experience"]
        categories["relevant_experience"] = CategoryScore(
            category_key="relevant_experience",
            category_name="Relevant Experience & Project Depth",
            raw_score=exp_score,
            weight=w_exp,
            weighted_score=round(exp_score * w_exp, 2),
            explanation=exp_exp,
            evidence=exp_ev,
            recommendations=exp_rec,
        )

        # 4. Education and Certifications Score
        edu_score, edu_exp, edu_ev, edu_rec = self._score_education_and_certs(resume, jd)
        w_edu = self.weights["education_and_certifications"]
        categories["education_and_certifications"] = CategoryScore(
            category_key="education_and_certifications",
            category_name="Education & Certifications",
            raw_score=edu_score,
            weight=w_edu,
            weighted_score=round(edu_score * w_edu, 2),
            explanation=edu_exp,
            evidence=edu_ev,
            recommendations=edu_rec,
        )

        # 5. Completeness and Readability Score
        read_score, read_exp, read_ev, read_rec = self._score_readability_completeness(resume)
        w_read = self.weights["completeness_and_readability"]
        categories["completeness_and_readability"] = CategoryScore(
            category_key="completeness_and_readability",
            category_name="Completeness & ATS Formatting",
            raw_score=read_score,
            weight=w_read,
            weighted_score=round(read_score * w_read, 2),
            explanation=read_exp,
            evidence=read_ev,
            recommendations=read_rec,
        )

        # Overall Score: Sum of weighted scores
        overall = sum(cat.weighted_score for cat in categories.values())
        overall = max(0.0, min(100.0, round(overall, 1)))

        notes = [
            f"Required Skills Weight: {int(w_req * 100)}% (matched {skills.matched_required_count}/{skills.total_required or 1})",
            f"Preferred Skills Weight: {int(w_pref * 100)}% (matched {skills.matched_preferred_count}/{skills.total_preferred or 1})",
            f"Experience Weight: {int(w_exp * 100)}% based on detected work history and project metrics",
            f"Education & Certifications Weight: {int(w_edu * 100)}%",
            f"Completeness & Readability Weight: {int(w_read * 100)}% checking headers, contact info, and parseability",
        ]

        return ScoringBreakdown(
            overall_score=overall,
            categories=categories,
            weights=self.weights,
            methodology_notes=notes,
        )

    def _score_required_skills(self, skills: SkillsAnalysisResult, jd: JobDescriptionParsed):
        total = skills.total_required
        if total == 0:
            return 90.0, "Job description listed no explicit mandatory skills; default baseline awarded.", ["No explicit required skills specified in job listing."], []

        matched = skills.matched_required_count
        ratio = matched / total
        raw = round(ratio * 100.0, 1)

        evidence = [f"Matched '{s}'" for s in skills.exact_matches if s in jd.required_skills]
        for a in skills.alias_matches:
            if a["requested"] in jd.required_skills:
                evidence.append(f"Matched '{a['requested']}' via alias '{a['found']}'")

        missing = skills.missing_required
        recommendations = [f"Add demonstrated experience with '{m}'" for m in missing[:5]]

        explanation = f"Matched {matched} of {total} required skills ({int(ratio * 100)}% coverage)."
        return raw, explanation, evidence, recommendations

    def _score_preferred_skills(self, skills: SkillsAnalysisResult, jd: JobDescriptionParsed):
        total = skills.total_preferred
        if total == 0:
            return 85.0, "No secondary or preferred skills specified; standard baseline applied.", ["No distinct preferred skills detected in job description."], []

        matched = skills.matched_preferred_count
        ratio = matched / total
        raw = round(ratio * 100.0, 1)

        evidence = [f"Demonstrated bonus skill: '{s}'" for s in skills.exact_matches if s in jd.preferred_skills]
        recommendations = [f"Consider highlighting knowledge in '{p}' if you have any experience" for p in skills.missing_preferred[:4]]
        explanation = f"Demonstrated {matched} of {total} preferred skills ({int(ratio * 100)}% coverage)."
        return raw, explanation, evidence, recommendations

    def _score_experience(self, resume: ResumeParsedData, jd: JobDescriptionParsed):
        score = 50.0  # baseline
        evidence = []
        recommendations = []

        # Work experience items
        exp_count = len(resume.experience)
        if exp_count >= 3:
            score += 25.0
            evidence.append(f"Identified {exp_count} documented professional roles.")
        elif exp_count >= 1:
            score += 15.0
            evidence.append(f"Identified {exp_count} professional role.")
        else:
            evidence.append("No clearly partitioned professional roles found in experience section.")
            recommendations.append("Ensure your work history is clearly structured under an 'Experience' or 'Work Experience' header.")

        # Projects
        proj_count = len(resume.projects)
        if proj_count >= 2:
            score += 15.0
            evidence.append(f"Documented {proj_count} relevant technical projects.")
        elif proj_count == 1:
            score += 8.0
            evidence.append("Documented 1 key project.")

        # Bullet points with metrics or strong action verbs
        action_verb_count = 0
        metric_count = 0
        verbs = ["built", "developed", "led", "designed", "architected", "optimized", "increased", "reduced", "implemented", "scaled"]
        for exp in resume.experience:
            for b in exp.responsibilities:
                b_low = b.lower()
                if any(v in b_low for v in verbs):
                    action_verb_count += 1
                if any(c in b for c in ["%", "$", "k ", "m ", "000"]):
                    metric_count += 1

        if action_verb_count >= 3:
            score += 5.0
            evidence.append(f"Strong action verbs detected across {action_verb_count} bullet points.")
        if metric_count >= 2:
            score += 5.0
            evidence.append(f"Quantified business or technical impact found in {metric_count} bullets.")
        else:
            recommendations.append("Include measurable metrics (percentages, latency improvements, scale) in your achievements.")

        score = max(0.0, min(100.0, score))
        explanation = f"Experience score based on {exp_count} roles, {proj_count} projects, and outcome-oriented achievements."
        return score, explanation, evidence, recommendations

    def _score_education_and_certs(self, resume: ResumeParsedData, jd: JobDescriptionParsed):
        score = 40.0
        evidence = []
        recommendations = []

        if resume.education:
            score += 35.0
            for edu in resume.education:
                evidence.append(f"Identified education: {edu.degree or edu.raw_text[:50]}")
        else:
            evidence.append("No explicit Education section detected.")
            recommendations.append("Add an Education section detailing your degree, field of study, and institution.")

        if resume.certifications:
            score += 25.0
            for cert in resume.certifications[:3]:
                evidence.append(f"Verified certification: {cert.name}")
        else:
            # Not having certs isn't a penalty, adjust toward baseline 70 if education is present
            if resume.education:
                score += 10.0
            recommendations.append("Adding industry certifications (AWS, GCP, CKA, PMP) can boost candidate visibility.")

        score = max(0.0, min(100.0, score))
        explanation = f"Evaluated {len(resume.education)} education records and {len(resume.certifications)} certifications."
        return score, explanation, evidence, recommendations

    def _score_readability_completeness(self, resume: ResumeParsedData):
        score = 40.0
        evidence = []
        recommendations = []

        # Contact info completeness
        ci = resume.contact_info
        ci_parts = [p for p in [ci.email, ci.phone, ci.linkedin or ci.github] if p]
        if len(ci_parts) >= 3:
            score += 20.0
            evidence.append("Full contact details detected (email, phone, professional profiles).")
        elif len(ci_parts) >= 1:
            score += 10.0
            evidence.append("Partial contact information detected.")
            recommendations.append("Ensure email, phone number, and LinkedIn/GitHub profiles are clearly visible at top.")
        else:
            recommendations.append("Add clear contact information at the top of the resume.")

        # Core sections detected
        expected_sections = ["experience", "education", "skills"]
        detected = resume.detected_sections
        matched_sections = [s for s in expected_sections if s in detected]
        score += len(matched_sections) * 10.0
        evidence.append(f"Standard sections identified: {', '.join(detected) if detected else 'unstructured'}.")

        # Word count sweet spot (300 - 1000 words)
        wc = resume.word_count
        if 350 <= wc <= 1100:
            score += 10.0
            evidence.append(f"Ideal word count length ({wc} words).")
        elif wc < 200:
            recommendations.append(f"Resume is very concise ({wc} words). Elaborate on key technical contributions.")
        elif wc > 1500:
            recommendations.append(f"Resume is lengthy ({wc} words). Aim for a focused 1-2 page format.")

        score = max(0.0, min(100.0, score))
        explanation = f"Completeness rating based on section clarity, parseability, and contact structure."
        return score, explanation, evidence, recommendations
