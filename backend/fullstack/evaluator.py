"""
Full-Stack Evaluation Engine.
Evaluates answers across HTML/CSS, JavaScript, React, Backend/APIs, SQL, and Architecture.
Enforces deterministic scoring rules in Python:
- JavaScript/SQL/Python code errors, syntax issues, or failed test cases receive strictly 0.0 marks.
- Output-prediction questions with incorrect predictions receive strictly 0.0 marks.
- Wholly irrelevant conceptual answers receive strictly 0.0 marks.
- Partial marks awarded only when verifiable evidence matches rubric criteria.
"""

import logging
import re
from typing import Dict, Any, List, Optional, Tuple
from backend.models import (
    Question,
    QuestionType,
    RubricCriterion,
    CriterionEvaluation,
    EvaluationResult,
)
from backend.fullstack.code_evaluator import FullStackCodeEvaluator
from backend.llm_client import LLMClient, default_llm_client
from backend.evaluator import evaluate_deterministically

logger = logging.getLogger(__name__)


class FullStackEvaluationEngine:
    """Orchestrates multi-language Full-Stack answer evaluation against rubrics."""

    def __init__(self, llm_client: Optional[LLMClient] = None):
        self.llm_client = llm_client or default_llm_client

    def evaluate_answer(
        self,
        question: Question,
        candidate_answer: str,
    ) -> EvaluationResult:
        """Main entry point for evaluating a Full-Stack candidate response."""
        trimmed_answer = candidate_answer.strip()

        # 1. Handle empty submission
        if not trimmed_answer:
            zero_criteria = [
                CriterionEvaluation(
                    criterion_id=c.id,
                    awarded_marks=0.0,
                    max_marks=c.max_marks,
                    evidence="No answer was submitted.",
                    explanation=f"No response provided for criterion '{c.description}'.",
                )
                for c in question.rubric
            ]
            return EvaluationResult(
                question_id=question.id,
                awarded_marks=0.0,
                max_marks=question.total_marks,
                percentage=0.0,
                criteria_evaluations=zero_criteria,
                demonstrated_concepts=[],
                partial_concepts=[],
                missing_concepts=list(question.expected_concepts),
                incorrect_claims=[],
                summary_explanation="No answer was provided. Zero marks awarded.",
                addressed_question=False,
                is_ambiguous=False,
                clarification_question=None,
                execution_result=None,
            )

        # 2. Deterministic evaluation for CODE_OUTPUT / Output Prediction
        if question.question_type == QuestionType.CODE_OUTPUT and question.expected_output:
            norm_actual = re.sub(r"\s+", " ", trimmed_answer.strip())
            norm_expected = re.sub(r"\s+", " ", question.expected_output.strip())
            is_match = norm_actual == norm_expected
            awarded = question.total_marks if is_match else 0.0

            criteria_evals = [
                CriterionEvaluation(
                    criterion_id=c.id,
                    awarded_marks=c.max_marks if is_match else 0.0,
                    max_marks=c.max_marks,
                    evidence=trimmed_answer if is_match else f"Output mismatch: got '{trimmed_answer}'",
                    explanation="Output matches expected execution order exactly." if is_match else f"Output does not match expected output '{question.expected_output}'.",
                )
                for c in question.rubric
            ]
            return EvaluationResult(
                question_id=question.id,
                awarded_marks=round(awarded, 2),
                max_marks=question.total_marks,
                percentage=100.0 if is_match else 0.0,
                criteria_evaluations=criteria_evals,
                demonstrated_concepts=["Accurate event loop and task queue output prediction"] if is_match else [],
                partial_concepts=[],
                missing_concepts=[] if is_match else list(question.expected_concepts),
                incorrect_claims=[] if is_match else [f"Predicted output '{trimmed_answer}' instead of '{question.expected_output}'"],
                summary_explanation="Correct predicted output." if is_match else f"Incorrect output. Expected: '{question.expected_output}', Got: '{trimmed_answer}'.",
                addressed_question=True,
                is_ambiguous=False,
                clarification_question=None,
                execution_result=None,
            )

        # 3. Code execution if code-writing or debugging question with test cases
        execution_result = None
        has_tests = bool(question.test_cases and len(question.test_cases) > 0)
        is_code_type = question.question_type in (QuestionType.CODE_WRITING, QuestionType.DEBUGGING)

        if (is_code_type and has_tests) or (question.question_type == QuestionType.CODE_WRITING):
            execution_result = FullStackCodeEvaluator.evaluate_code(
                candidate_code=trimmed_answer,
                language=question.language or "javascript",
                test_cases=question.test_cases,
                function_name=question.function_name,
                db_schema=question.db_schema,
            )

            # Strict scoring rule: syntax error or all tests failing yields strictly 0.0 marks
            if execution_result and not execution_result.get("syntax_valid", True):
                zero_crit = [
                    CriterionEvaluation(
                        criterion_id=c.id,
                        awarded_marks=0.0,
                        max_marks=c.max_marks,
                        evidence=f"Syntax Error: {execution_result.get('syntax_error', 'Invalid syntax')}",
                        explanation="Code cannot be evaluated due to syntax error.",
                    )
                    for c in question.rubric
                ]
                return EvaluationResult(
                    question_id=question.id,
                    awarded_marks=0.0,
                    max_marks=question.total_marks,
                    percentage=0.0,
                    criteria_evaluations=zero_crit,
                    demonstrated_concepts=[],
                    missing_concepts=list(question.expected_concepts),
                    incorrect_claims=[f"Syntax error: {execution_result.get('syntax_error')}"],
                    summary_explanation="Code failed to compile or parse. Zero marks awarded for strict syntax failure.",
                    execution_result=execution_result,
                )

            if execution_result and has_tests and execution_result.get("tests_passed", 0) == 0:
                zero_crit = [
                    CriterionEvaluation(
                        criterion_id=c.id,
                        awarded_marks=0.0,
                        max_marks=c.max_marks,
                        evidence=f"Functional verification failed 0/{execution_result.get('tests_total', 1)} tests passed.",
                        explanation="Failed all required functional assertions.",
                    )
                    for c in question.rubric
                ]
                return EvaluationResult(
                    question_id=question.id,
                    awarded_marks=0.0,
                    max_marks=question.total_marks,
                    percentage=0.0,
                    criteria_evaluations=zero_crit,
                    demonstrated_concepts=[],
                    missing_concepts=list(question.expected_concepts),
                    incorrect_claims=["Failed all functional test cases"],
                    summary_explanation="Candidate code failed functional verification tests. Zero marks awarded.",
                    execution_result=execution_result,
                )

        # 4. LLM semantic analysis prompt
        prompt = self._build_evaluation_prompt(
            question=question,
            candidate_answer=trimmed_answer,
            execution_result=execution_result,
        )

        try:
            raw_response = self.llm_client.generate_json(
                prompt=prompt,
                system_prompt=(
                    "You are a principal Full-Stack engineering interviewer and evaluator. "
                    "Evaluate candidate answers strictly and objectively against the provided scoring rubric. "
                    "Reward genuine technical accuracy across frontend, backend, APIs, and databases. "
                    "Identify misconceptions and missing concepts. Return valid JSON only matching the schema."
                ),
                temperature=0.1,
            )
            return self._process_model_response(
                question=question,
                raw_response=raw_response,
                execution_result=execution_result,
                candidate_answer=trimmed_answer,
            )
        except Exception as exc:
            logger.warning("LLM evaluation failed for question %s: %s. Using deterministic fallback.", question.id, exc)
            return self._create_fallback_evaluation(
                question=question,
                candidate_answer=trimmed_answer,
                error_reason=str(exc),
                execution_result=execution_result,
            )

    def _build_evaluation_prompt(
        self,
        question: Question,
        candidate_answer: str,
        execution_result: Optional[Dict[str, Any]] = None,
    ) -> str:
        rubric_str = "\n".join(
            f"- [{c.id}] (Max {c.max_marks} marks): {c.description}. Guide: {c.evidence_guide}"
            for c in question.rubric
        )

        exec_context = ""
        if execution_result:
            exec_context = f"""
AUTOMATED TEST RUNNER RESULTS:
- Language: {execution_result.get('language')}
- Syntax Valid: {execution_result.get('syntax_valid')}
- Tests Passed: {execution_result.get('tests_passed')}/{execution_result.get('tests_total')}
- Execution Error: {execution_result.get('execution_error')}
"""

        return f"""Evaluate this Full-Stack technical interview response.

QUESTION:
Topic: {question.topic} ({question.competency})
Difficulty: {question.difficulty.value}
Question Type: {question.question_type.value}
Prompt: {question.text}

EXPECTED CONCEPTS:
{chr(10).join(f"- {c}" for c in question.expected_concepts)}

SCORING RUBRIC (Total Max: {question.total_marks}):
{rubric_str}

REFERENCE ANSWER:
{question.reference_answer}
{exec_context}
CANDIDATE ANSWER:
{candidate_answer}

Respond ONLY with valid JSON matching this schema:
{{
  "addressed_question": true,
  "is_ambiguous": false,
  "demonstrated_concepts": ["concept1"],
  "partial_concepts": [],
  "missing_concepts": [],
  "incorrect_claims": [],
  "summary_explanation": "Concise justification of awarded marks",
  "criteria_evaluations": [
    {{
      "criterion_id": "criterion_id_from_rubric",
      "awarded_marks": 2.5,
      "evidence": "Direct quote from answer",
      "explanation": "Why these marks were awarded"
    }}
  ]
}}"""

    def _process_model_response(
        self,
        question: Question,
        raw_response: Dict[str, Any],
        execution_result: Optional[Dict[str, Any]],
        candidate_answer: str,
    ) -> EvaluationResult:
        addressed_question = bool(raw_response.get("addressed_question", True))
        is_ambiguous = bool(raw_response.get("is_ambiguous", False))
        clarification_question = raw_response.get("clarification_question")

        demonstrated = raw_response.get("demonstrated_concepts", []) or []
        partial = raw_response.get("partial_concepts", []) or []
        missing = raw_response.get("missing_concepts", []) or []
        incorrect = raw_response.get("incorrect_claims", []) or []
        summary = str(raw_response.get("summary_explanation", "Evaluated against rubric."))
        raw_criteria = raw_response.get("criteria_evaluations", []) or []

        total_awarded, validated_criteria = self.validate_and_calculate_rubric(
            question=question,
            raw_criteria_evals=raw_criteria,
            execution_result=execution_result,
            candidate_answer=candidate_answer,
            demonstrated_concepts=demonstrated,
        )

        max_marks = question.total_marks
        percentage = round((total_awarded / max_marks) * 100.0, 2) if max_marks > 0 else 0.0

        return EvaluationResult(
            question_id=question.id,
            awarded_marks=round(total_awarded, 2),
            max_marks=max_marks,
            percentage=percentage,
            criteria_evaluations=validated_criteria,
            demonstrated_concepts=[str(d) for d in demonstrated],
            partial_concepts=[str(p) for p in partial],
            missing_concepts=[str(m) for m in missing],
            incorrect_claims=[str(i) for i in incorrect],
            summary_explanation=summary,
            addressed_question=addressed_question,
            is_ambiguous=is_ambiguous,
            clarification_question=str(clarification_question) if clarification_question else None,
            execution_result=execution_result,
        )

    @classmethod
    def validate_and_calculate_rubric(
        cls,
        question: Question,
        raw_criteria_evals: List[Dict[str, Any]],
        execution_result: Optional[Dict[str, Any]] = None,
        candidate_answer: str = "",
        demonstrated_concepts: Optional[List[str]] = None,
    ) -> Tuple[float, List[CriterionEvaluation]]:
        """Enforces strict deterministic scoring in Python."""
        rubric_map: Dict[str, RubricCriterion] = {c.id: c for c in question.rubric}
        seen_ids = set()
        validated: List[CriterionEvaluation] = []
        total_score = 0.0

        for item in raw_criteria_evals:
            if not isinstance(item, dict):
                continue
            crit_id = item.get("criterion_id")
            if not crit_id or crit_id not in rubric_map or crit_id in seen_ids:
                continue
            seen_ids.add(crit_id)
            c_def = rubric_map[crit_id]

            raw_awarded = item.get("awarded_marks", 0.0)
            try:
                score = float(raw_awarded)
            except (ValueError, TypeError):
                score = 0.0

            clamped = max(0.0, min(score, c_def.max_marks))
            clamped = round(clamped, 2)
            total_score += clamped

            validated.append(
                CriterionEvaluation(
                    criterion_id=crit_id,
                    awarded_marks=clamped,
                    max_marks=c_def.max_marks,
                    evidence=str(item.get("evidence", "")),
                    explanation=str(item.get("explanation", "")),
                )
            )

        # Fill missing rubric items with zero
        for c in question.rubric:
            if c.id not in seen_ids:
                validated.append(
                    CriterionEvaluation(
                        criterion_id=c.id,
                        awarded_marks=0.0,
                        max_marks=c.max_marks,
                        evidence="Not demonstrated.",
                        explanation=f"Criterion '{c.description}' was not addressed.",
                    )
                )

        # =====================================================================
        # STRICT OVERRIDES
        # =====================================================================
        # 1. Code Writing & Debugging with Tests: failing code MUST receive strictly 0 marks
        has_tests = bool(question.test_cases and len(question.test_cases) > 0)
        is_code = question.question_type == QuestionType.CODE_WRITING or (
            question.question_type == QuestionType.DEBUGGING and has_tests
        )
        if is_code and execution_result:
            if not execution_result.get("syntax_valid"):
                total_score = 0.0
                for v in validated:
                    v.awarded_marks = 0.0
                    v.explanation = f"Syntax error detected ({execution_result.get('syntax_error')}). Solution receives 0 marks."
            elif execution_result.get("execution_error"):
                total_score = 0.0
                for v in validated:
                    v.awarded_marks = 0.0
                    v.explanation = f"Execution error ({execution_result.get('execution_error')}). Solution receives 0 marks."
            elif execution_result.get("tests_total", 0) > 0 and execution_result.get("tests_passed", 0) < execution_result.get("tests_total", 0):
                total_score = 0.0
                for v in validated:
                    v.awarded_marks = 0.0
                    v.explanation = f"Failed functional test cases ({execution_result.get('tests_passed')}/{execution_result.get('tests_total')} passed). Incorrect solution receives 0 marks."

        # 2. Output Prediction: incorrect predictions receive strictly 0 marks
        elif question.question_type == QuestionType.CODE_OUTPUT and candidate_answer:
            exp_out = question.expected_output
            if exp_out:
                norm_exp = " ".join(exp_out.strip().split()).lower()
                norm_cand = " ".join(candidate_answer.strip().split()).lower()
                if norm_exp not in norm_cand:
                    total_score = 0.0
                    for v in validated:
                        v.awarded_marks = 0.0
                        v.explanation = f"Predicted output is incorrect (expected '{exp_out}'). Solution receives 0 marks."

        # 3. Conceptual & Scenario: zero demonstrated concepts receives strictly 0 marks
        elif question.question_type in (QuestionType.CONCEPTUAL, QuestionType.SCENARIO, QuestionType.PRACTICAL):
            if demonstrated_concepts is not None and len(demonstrated_concepts) == 0:
                total_score = 0.0
                for v in validated:
                    v.awarded_marks = 0.0
                    v.explanation = "Answer demonstrated no required technical concepts. Zero marks awarded."

        return round(total_score, 2), validated

    def _create_fallback_evaluation(
        self,
        question: Question,
        candidate_answer: str,
        error_reason: str,
        execution_result: Optional[Dict[str, Any]],
    ) -> EvaluationResult:
        """
        Deterministic fallback when LLM is unavailable.
        Evaluates candidate response deterministically against rubrics and expected concepts.
        Awards fair partial credit and never falsely reports 0/5 for correct concepts.
        """
        return evaluate_deterministically(
            question=question,
            candidate_answer=candidate_answer,
            execution_result=execution_result,
            error_reason=error_reason,
        )
