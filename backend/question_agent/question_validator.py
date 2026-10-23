"""
Question Quality and Rubric Validation Engine.
Ensures every candidate question is:
- Self-contained, unambiguous, and technically rigorous
- Grounded in candidate resume facts (no hallucinated projects/claims)
- Calibrated to appropriate difficulty and target role
- Bound to deterministic rubrics summing to exactly 5.0 marks
- Fully equipped with code snippets/test cases for implementation modalities
"""

import re
import logging
from typing import Dict, Any, List, Optional, Tuple
from backend.models import Question, QuestionType, RubricCriterion
from backend.question_agent.models import (
    QuestionFormat,
    ValidationResult,
    ResumeIntelligenceProfile,
)

logger = logging.getLogger(__name__)


class QuestionQualityValidator:
    """Validates structural integrity, rubric validity, and grounding."""

    @classmethod
    def validate_question(
        cls,
        question: Question,
        expected_format: QuestionFormat,
        role: str,
        track: str,
        resume_profile: Optional[ResumeIntelligenceProfile] = None,
        allowed_projects: Optional[List[str]] = None,
    ) -> ValidationResult:
        """Runs comprehensive validation checks on a generated question."""
        issues: List[str] = []
        is_valid = True
        rubric_valid = True
        grounding_valid = True
        role_relevant = True

        # 1. Text quality check
        text = (question.text or "").strip()
        if len(text) < 20:
            issues.append("Question text is excessively short or incomplete.")
            is_valid = False

        if len(text) > 1200:
            issues.append("Question text is excessively verbose.")

        # 2. Rubric criteria validation
        rubric = question.rubric or []
        if not rubric:
            issues.append("Rubric is missing criteria.")
            rubric_valid = False
            is_valid = False
        else:
            total_marks = sum(c.max_marks for c in rubric)
            if abs(total_marks - 5.0) > 0.15:
                issues.append(f"Rubric total marks ({total_marks:.1f}) deviate from required 5.0 marks.")
                rubric_valid = False
                # Auto-normalize rubric if possible
                cls._normalize_rubric_marks(rubric)

            for idx, c in enumerate(rubric):
                if not (c.description or "").strip():
                    issues.append(f"Criterion #{idx+1} lacks descriptive explanation.")
                    rubric_valid = False
                if not (c.evidence_guide or "").strip():
                    issues.append(f"Criterion #{idx+1} lacks explicit evidence guide.")
                    rubric_valid = False

        # 3. Expected concepts validation
        expected = question.expected_concepts or []
        if not expected or len(expected) < 1:
            issues.append("Question lacks expected concepts for grading.")
            rubric_valid = False

        # 4. Modality-specific structural checks
        if expected_format == QuestionFormat.CODE_WRITING or question.question_type == QuestionType.CODE_WRITING:
            test_cases = question.test_cases or []
            if not test_cases:
                issues.append("Code writing question lacks required test cases.")
                is_valid = False

        elif expected_format == QuestionFormat.OUTPUT_PREDICTION or question.question_type == QuestionType.CODE_OUTPUT:
            if not (question.code_snippet or "").strip():
                issues.append("Output prediction question lacks code snippet.")
                is_valid = False
            if not (question.expected_output or "").strip():
                issues.append("Output prediction question lacks expected output definition.")
                is_valid = False

        elif expected_format == QuestionFormat.CODE_DEBUGGING or question.question_type == QuestionType.DEBUGGING:
            if not (question.code_snippet or "").strip():
                issues.append("Debugging question lacks buggy code snippet.")
                is_valid = False

        # 5. Role & Track relevance check
        track_lower = (track or "python").lower()
        text_lower = text.lower()
        if track_lower == "python":
            # Guard against obvious fullstack frontend-specific leaks into python track
            unrelated_cues = ["react component", "jsx", "tailwind css", "dom event bubbling", "css grid"]
            if any(cue in text_lower for cue in unrelated_cues):
                issues.append("Question contains unrelated frontend technologies in Python track.")
                role_relevant = False
                is_valid = False
        elif track_lower == "fullstack":
            unrelated_cues = ["cpython gil", "metaclass __prepare__", "django orm vs sqlalchemy"]
            if any(cue in text_lower for cue in unrelated_cues):
                issues.append("Question contains specialized CPython internals in Full-Stack track.")
                role_relevant = False
                is_valid = False

        # 6. Resume grounding check (anti-hallucination)
        if expected_format == QuestionFormat.PROJECT_DEEP_DIVE:
            # Check if mentioned project matches candidate's actual projects
            if resume_profile and resume_profile.projects:
                valid_project_names = [p.title.lower() for p in resume_profile.projects]
                # If specific project is probed, make sure it's grounded
                has_matching_project = any(
                    any(term in text_lower for term in p.title.lower().split() if len(term) > 3)
                    for p in resume_profile.projects
                )
                if not has_matching_project and allowed_projects:
                    has_matching_project = any(p.lower() in text_lower for p in allowed_projects)

                if not has_matching_project:
                    issues.append("Project deep dive question references a project not found in candidate's resume.")
                    grounding_valid = False
                    is_valid = False

        # Calculate composite relevance score
        relevance_score = 1.0
        if not role_relevant:
            relevance_score *= 0.3
        if not grounding_valid:
            relevance_score *= 0.5
        if not rubric_valid:
            relevance_score *= 0.7

        return ValidationResult(
            is_valid=is_valid,
            rubric_valid=rubric_valid,
            grounding_valid=grounding_valid,
            role_relevant=role_relevant,
            uniqueness_score=1.0,
            relevance_score=round(relevance_score, 2),
            issues=issues,
        )

    @classmethod
    def _normalize_rubric_marks(cls, criteria: List[RubricCriterion]):
        """Adjusts criterion marks so they sum up to exactly 5.0."""
        if not criteria:
            return
        current_sum = sum(c.max_marks for c in criteria)
        if current_sum <= 0:
            even = round(5.0 / len(criteria), 1)
            for c in criteria:
                c.max_marks = even
            criteria[0].max_marks = round(5.0 - sum(c.max_marks for c in criteria[1:]), 1)
            return

        scale = 5.0 / current_sum
        for c in criteria:
            c.max_marks = round(c.max_marks * scale, 1)

        diff = round(5.0 - sum(c.max_marks for c in criteria), 1)
        if diff != 0:
            criteria[0].max_marks = max(0.5, round(criteria[0].max_marks + diff, 1))
