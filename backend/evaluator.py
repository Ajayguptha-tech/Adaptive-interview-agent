"""
Fair Answer Evaluation Engine for Python Interview System.
Combines question rubric, expected concepts, LLM semantic analysis,
safe code execution/static analysis, and strict deterministic score calculation.
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
from backend.code_evaluator import CodeEvaluator
from backend.llm_client import LLMClient, default_llm_client

logger = logging.getLogger(__name__)


class OutputPredictionEvaluator:
    """Deterministically normalizes and verifies predicted code output."""

    @classmethod
    def get_expected_output(cls, question: Question) -> Optional[str]:
        if question.expected_output and question.expected_output.strip():
            return question.expected_output.strip()

        # Try to execute snippet if present
        if question.code_snippet and question.code_snippet.strip():
            actual_stdout = CodeEvaluator.run_isolated_snippet(question.code_snippet)
            if actual_stdout is not None:
                return actual_stdout.strip()

        # Fallback to extracting from reference answer
        match = re.search(r"output(?:\s+is)?:\s*['\"]([^'\"]+)['\"]", question.reference_answer, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        return None

    @classmethod
    def verify_prediction(cls, expected: str, candidate_answer: str) -> bool:
        """
        Normalizes expected and candidate text and checks for matching output tokens/lines.
        """
        norm_exp = " ".join(expected.strip().split())
        norm_cand = " ".join(candidate_answer.strip().split())

        if not norm_exp:
            return False

        # Direct containment of normalized output string
        if norm_exp.lower() in norm_cand.lower():
            return True

        # Check line-by-line or token-by-token sequence
        exp_tokens = [t for t in norm_exp.split() if t]
        cand_tokens = [t for t in norm_cand.split() if t]
        if not exp_tokens:
            return False

        exp_len = len(exp_tokens)
        for i in range(len(cand_tokens) - exp_len + 1):
            if [t.lower() for t in cand_tokens[i : i + exp_len]] == [t.lower() for t in exp_tokens]:
                return True

        return False


class EvaluationEngine:
    """
    Orchestrates the evaluation of candidate answers against rubrics.
    Enforces deterministic scoring rules in Python code.
    """

    def __init__(self, llm_client: Optional[LLMClient] = None):
        self.llm_client = llm_client or default_llm_client

    def evaluate_answer(
        self,
        question: Question,
        candidate_answer: str,
    ) -> EvaluationResult:
        """
        Main entry point for evaluating an answer to a question.
        Returns validated EvaluationResult.
        """
        trimmed_answer = candidate_answer.strip()

        # Handle empty answer directly without wasting LLM call
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

        # Code execution / static analysis if code-writing or debugging question with test cases
        execution_result = None
        if question.question_type == QuestionType.CODE_WRITING or (
            question.question_type == QuestionType.DEBUGGING and question.test_cases
        ):
            execution_result = CodeEvaluator.evaluate_code(
                candidate_code=trimmed_answer,
                test_cases=question.test_cases,
                function_name=question.function_name,
            )

        # Build prompt for LLM semantic analysis
        prompt = self._build_evaluation_prompt(
            question=question,
            candidate_answer=trimmed_answer,
            execution_result=execution_result,
        )

        try:
            raw_response = self.llm_client.generate_json(
                prompt=prompt,
                system_prompt=(
                    "You are a rigorous, fair Python technical evaluator. "
                    "Your role is to assess candidate evidence strictly against the question's rubric. "
                    "Reward genuine technical understanding, alternative correct formulations, and valid examples. "
                    "Do NOT deduct marks for different variable names or formatting. "
                    "Identify incorrect claims, misconceptions, and missing concepts. "
                    "Never hallucinate candidate statements. "
                    "Return valid JSON only matching the schema."
                ),
            )
            return self._process_model_response(
                question=question,
                raw_response=raw_response,
                execution_result=execution_result,
                candidate_answer=trimmed_answer,
            )
        except Exception as exc:
            logger.error(f"Error during LLM evaluation for question {question.id}: {exc}")
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
        rubric_lines = []
        for crit in question.rubric:
            rubric_lines.append(
                f"- ID: '{crit.id}' | Max Marks: {crit.max_marks} | "
                f"Description: {crit.description} | Evidence Guide: {crit.evidence_guide}"
            )
        rubric_text = "\n".join(rubric_lines)

        exec_context = ""
        if execution_result:
            exec_context = (
                f"\n=== AUTOMATED CODE EXECUTION & STATIC ANALYSIS RESULT ===\n"
                f"Syntax Valid: {execution_result.get('syntax_valid')}\n"
                f"Mode: {execution_result.get('mode')}\n"
                f"Tests Passed: {execution_result.get('tests_passed')}/{execution_result.get('tests_total')}\n"
                f"Notes: {execution_result.get('notes')}\n"
            )
            if execution_result.get("execution_error"):
                exec_context += f"Error encountered: {execution_result.get('execution_error')}\n"
            if execution_result.get("static_analysis", {}).get("unsafe_flags"):
                exec_context += f"Security flags: {execution_result.get('static_analysis', {}).get('unsafe_flags')}\n"

        prompt = f"""
EVALUATION TASK: Evaluate candidate response against question rubric.

=== QUESTION SPECIFICATION ===
ID: {question.id}
Topic: {question.topic}
Competency: {question.competency}
Difficulty: {question.difficulty.value}
Type: {question.question_type.value}
Question Text:
{question.text}
{"Snippet:" + chr(10) + question.code_snippet if question.code_snippet else ""}

Expected Concepts:
{json_list(question.expected_concepts)}

Optional Supporting Concepts:
{json_list(question.optional_concepts)}

Common Misconceptions:
{json_list(question.common_misconceptions)}

Reference Answer (for conceptual guidance only; do not require exact text match):
{question.reference_answer}

=== SCORING RUBRIC ===
{rubric_text}
{exec_context}
=== CANDIDATE ANSWER ===
{candidate_answer}

=== EVALUATION RULES ===
1. Compare candidate's meaning with expected concepts, NOT exact wording.
2. Accept alternative correct solutions or valid examples.
3. Award marks strictly per criterion. Each criterion score must be between 0.0 and its max marks.
4. If candidate made incorrect claims or demonstrated misconceptions, flag them explicitly.
5. If the answer is completely off-topic or doesn't address the question, award 0.
6. If the answer is ambiguous, set is_ambiguous to true and suggest a clarification question.
7. Return evidence quotes from the answer supporting each awarded mark.

Return valid JSON strictly matching this schema:
{{
  "addressed_question": true,
  "is_ambiguous": false,
  "clarification_question": null,
  "demonstrated_concepts": ["concept 1", ...],
  "partial_concepts": ["concept 2", ...],
  "missing_concepts": ["concept 3", ...],
  "incorrect_claims": ["claim 1", ...],
  "criteria_evaluations": [
    {{
      "criterion_id": "exact_id_from_rubric",
      "awarded_marks": 2.0,
      "evidence": "Quote or specific evidence from candidate answer",
      "explanation": "Why this score was awarded"
    }}
  ],
  "summary_explanation": "Concise 1-2 sentence evidence-based summary of performance on this question."
}}
"""
        return prompt

    def _process_model_response(
        self,
        question: Question,
        raw_response: Dict[str, Any],
        execution_result: Optional[Dict[str, Any]],
        candidate_answer: str = "",
    ) -> EvaluationResult:
        """
        Validates LLM output deterministically in Python code.
        Enforces bounds, rubric membership, deduplication, and calculates exact score sum.
        """
        addressed_question = bool(raw_response.get("addressed_question", True))
        is_ambiguous = bool(raw_response.get("is_ambiguous", False))
        clarification_question = raw_response.get("clarification_question")

        demonstrated = raw_response.get("demonstrated_concepts", [])
        if not isinstance(demonstrated, list):
            demonstrated = []
        partial = raw_response.get("partial_concepts", [])
        if not isinstance(partial, list):
            partial = []
        missing = raw_response.get("missing_concepts", [])
        if not isinstance(missing, list):
            missing = []
        incorrect = raw_response.get("incorrect_claims", [])
        if not isinstance(incorrect, list):
            incorrect = []

        summary_explanation = str(
            raw_response.get("summary_explanation", "Answer evaluated against rubric.")
        )

        raw_criteria = raw_response.get("criteria_evaluations", [])
        if not isinstance(raw_criteria, list):
            raw_criteria = []

        # Validate rubric evaluations deterministically
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
            summary_explanation=summary_explanation,
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
        """
        Enforces deterministic scoring rules:
        1. Code-writing & debugging: solution receives marks ONLY when it matches required behavior.
           Incorrect solutions, syntax errors, or failing test cases receive strictly 0.0 marks.
        2. Output-prediction: candidate prediction MUST match expected output. Incorrect predictions get 0.0.
        3. Conceptual: award partial marks for demonstrated evidence; irrelevant/empty gets 0.0.
        4. Bounds clamp [0.0, max_marks] and sum calculated in Python.
        """
        rubric_map: Dict[str, RubricCriterion] = {c.id: c for c in question.rubric}
        seen_criterion_ids = set()
        validated_evals: List[CriterionEvaluation] = []
        total_score = 0.0

        # Process received evaluations
        for item in raw_criteria_evals:
            if not isinstance(item, dict):
                continue
            crit_id = item.get("criterion_id")
            if not crit_id or crit_id not in rubric_map:
                continue
            if crit_id in seen_criterion_ids:
                continue

            seen_criterion_ids.add(crit_id)
            criterion_def = rubric_map[crit_id]

            raw_awarded = item.get("awarded_marks", 0.0)
            try:
                numeric_score = float(raw_awarded)
            except (ValueError, TypeError):
                numeric_score = 0.0

            clamped_score = max(0.0, min(numeric_score, criterion_def.max_marks))
            evidence = str(item.get("evidence", "No explicit quote provided."))
            explanation = str(item.get("explanation", ""))

            clamped_score = round(clamped_score, 2)
            total_score += clamped_score

            validated_evals.append(
                CriterionEvaluation(
                    criterion_id=crit_id,
                    awarded_marks=clamped_score,
                    max_marks=criterion_def.max_marks,
                    evidence=evidence,
                    explanation=explanation,
                )
            )

        # Ensure all defined criteria in the rubric exist in result
        for crit in question.rubric:
            if crit.id not in seen_criterion_ids:
                validated_evals.append(
                    CriterionEvaluation(
                        criterion_id=crit.id,
                        awarded_marks=0.0,
                        max_marks=crit.max_marks,
                        evidence="Not addressed.",
                        explanation=f"Criterion '{crit.description}' was not demonstrated in candidate response.",
                    )
                )

        # =========================================================================
        # STRICT SCORING POLICY OVERRIDES (Enforced in Python, cannot be bypassed by LLM)
        # =========================================================================

        # 1. Code-writing & Debugging: incorrect solutions receive strictly 0 marks
        if question.question_type == QuestionType.CODE_WRITING or (
            question.question_type == QuestionType.DEBUGGING and question.test_cases
        ):
            if execution_result:
                if not execution_result.get("syntax_valid"):
                    total_score = 0.0
                    for item in validated_evals:
                        item.awarded_marks = 0.0
                        item.explanation = f"Syntax error detected: {execution_result.get('syntax_error')}. Solution receives 0 marks."
                elif execution_result.get("execution_error"):
                    total_score = 0.0
                    for item in validated_evals:
                        item.awarded_marks = 0.0
                        item.explanation = f"Execution runtime error: {execution_result.get('execution_error')}. Solution receives 0 marks."
                elif execution_result.get("tests_total", 0) > 0 and execution_result.get("tests_passed", 0) < execution_result.get("tests_total", 0):
                    total_score = 0.0
                    for item in validated_evals:
                        item.awarded_marks = 0.0
                        item.explanation = (
                            f"Functional tests failed: passed {execution_result.get('tests_passed')}/{execution_result.get('tests_total')} tests. "
                            "An incorrect solution receives 0 marks under strict assessment policy."
                        )

        # 2. Output-prediction: incorrect predicted output receives strictly 0 marks
        elif question.question_type == QuestionType.CODE_OUTPUT and candidate_answer:
            expected_out = OutputPredictionEvaluator.get_expected_output(question)
            if expected_out:
                matches = OutputPredictionEvaluator.verify_prediction(expected_out, candidate_answer)
                if not matches:
                    total_score = 0.0
                    for item in validated_evals:
                        item.awarded_marks = 0.0
                        item.explanation = (
                            f"Predicted output is incorrect (expected: '{expected_out}'). "
                            "Under output prediction rules, an incorrect output receives 0 marks."
                        )

        # 3. Conceptual & Scenario: if completely off-topic or empty evidence
        elif question.question_type in (QuestionType.CONCEPTUAL, QuestionType.SCENARIO, QuestionType.PRACTICAL):
            if demonstrated_concepts is not None and len(demonstrated_concepts) == 0:
                total_score = 0.0
                for item in validated_evals:
                    item.awarded_marks = 0.0
                    item.explanation = "Answer demonstrated no required technical concepts. Zero marks awarded."

        return round(total_score, 2), validated_evals

    def _create_fallback_evaluation(
        self,
        question: Question,
        candidate_answer: str,
        error_reason: str,
        execution_result: Optional[Dict[str, Any]] = None,
    ) -> EvaluationResult:
        """
        Safe fallback evaluation when the LLM service fails or gives unparseable output.
        Does NOT silently award full marks. Uses static analysis and deterministic rules.
        """
        awarded_total = 0.0
        validated_evals = []

        # If code-writing question and tests actually passed in isolated runner
        tests_passed = execution_result.get("tests_passed", 0) if execution_result else 0
        tests_total = execution_result.get("tests_total", 0) if execution_result else 0

        for crit in question.rubric:
            crit_score = 0.0
            explanation = f"Automated evaluation fallback: {error_reason}"

            if execution_result and tests_total > 0 and execution_result.get("syntax_valid"):
                # Pro-rate score based on verified test cases
                pass_ratio = tests_passed / tests_total
                crit_score = round(crit.max_marks * pass_ratio, 2)
                explanation = f"Deterministic fallback based on automated test results: {tests_passed}/{tests_total} tests passed."

            awarded_total += crit_score
            validated_evals.append(
                CriterionEvaluation(
                    criterion_id=crit.id,
                    awarded_marks=crit_score,
                    max_marks=crit.max_marks,
                    evidence="Fallback analysis.",
                    explanation=explanation,
                )
            )

        max_marks = question.total_marks
        percentage = round((awarded_total / max_marks) * 100.0, 2) if max_marks > 0 else 0.0

        return EvaluationResult(
            question_id=question.id,
            awarded_marks=round(awarded_total, 2),
            max_marks=max_marks,
            percentage=percentage,
            criteria_evaluations=validated_evals,
            demonstrated_concepts=["Syntactically valid code"] if execution_result and execution_result.get("syntax_valid") else [],
            partial_concepts=[],
            missing_concepts=["Complete semantic LLM verification (model connection issue)"],
            incorrect_claims=[],
            summary_explanation=f"Evaluation completed via deterministic fallback. Note: {error_reason}",
            addressed_question=True if len(candidate_answer) > 10 else False,
            is_ambiguous=False,
            clarification_question=None,
            execution_result=execution_result,
        )


def json_list(items: List[str]) -> str:
    """Helper to format list as clean bullet points for prompts."""
    if not items:
        return "- (None listed)"
    return "\n".join(f"- {item}" for item in items)
