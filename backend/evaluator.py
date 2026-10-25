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
        Evaluates candidate response deterministically against rubrics and expected concepts.
        Awards fair partial credit and never falsely reports 0/5 for correct concepts.
        """
        return evaluate_deterministically(
            question=question,
            candidate_answer=candidate_answer,
            execution_result=execution_result,
            error_reason=error_reason,
        )


# =============================================================================
# DETERMINISTIC FALLBACK EVALUATOR
# =============================================================================

DETERMINISTIC_STOP_WORDS = {
    'a', 'about', 'above', 'after', 'again', 'against', 'all', 'am', 'an', 'and', 'any', 'are', 'aren',
    'as', 'at', 'be', 'because', 'been', 'before', 'being', 'below', 'between', 'both', 'but', 'by',
    'can', 'could', 'did', 'do', 'does', 'doing', 'down', 'during', 'each', 'few', 'for', 'from',
    'further', 'had', 'has', 'have', 'having', 'he', 'her', 'here', 'hers', 'herself', 'him',
    'himself', 'his', 'how', 'i', 'if', 'in', 'into', 'is', 'it', 'its', 'itself', 'just', 'll', 'm',
    'me', 'might', 'more', 'most', 'must', 'my', 'myself', 'no', 'nor', 'not', 'now', 'o', 'of',
    'off', 'on', 'once', 'only', 'or', 'other', 'our', 'ours', 'ourselves', 'out', 'over', 'own',
    're', 's', 'same', 'she', 'should', 'so', 'some', 'such', 't', 'than', 'that', 'the', 'their',
    'theirs', 'them', 'themselves', 'then', 'there', 'these', 'they', 'this', 'those', 'through',
    'to', 'too', 'under', 'until', 'up', 've', 'very', 'was', 'we', 'were', 'what', 'when', 'where',
    'which', 'while', 'who', 'whom', 'why', 'will', 'with', 'won', 'would', 'y', 'you', 'your',
    'yours', 'yourself', 'yourselves', 'explain', 'explains', 'explaining', 'explanation', 'clearly',
    'provides', 'providing', 'mentions', 'mentioning', 'accurately', 'state', 'states', 'stating',
    'describe', 'describes', 'example', 'examples', 'e.g', 'eg', 'etc', 'answer', 'candidate',
    'python', 'code', 'function', 'class', 'method', 'variable', 'object', 'program', 'system', 'use', 'using', 'used'
}


def _extract_deterministic_tokens(text: str) -> Set[str]:
    """Extracts normalized words and special technical symbols for rubric matching."""
    words = re.findall(r'[a-zA-Z0-9_\-]+|<[a-zA-Z0-9_\-]+>|\[\]|\(\)|\{\}', text.lower())
    res = set()
    for w in words:
        if w not in DETERMINISTIC_STOP_WORDS and len(w) > 1:
            res.add(w)
        elif w in ('[]', '()', '{}'):
            res.add(w)
    return res


def _find_evidence_sentence(candidate_answer: str, target_terms: Set[str]) -> str:
    """Finds the sentence in candidate_answer that best demonstrates the target terms."""
    raw_sentences = re.split(r'(?<=[.!?\n])\s+', candidate_answer.strip())
    sentences = [s.strip() for s in raw_sentences if s.strip()]
    if not sentences:
        return candidate_answer[:200] if candidate_answer else "Not addressed."

    best_sent = ""
    max_hits = 0
    for s in sentences:
        s_tokens = _extract_deterministic_tokens(s)
        hits = len(s_tokens.intersection(target_terms))
        if hits > max_hits:
            max_hits = hits
            best_sent = s

    return best_sent if best_sent else (sentences[0] if sentences else "Not addressed.")


def evaluate_deterministically(
    question: Question,
    candidate_answer: str,
    execution_result: Optional[Dict[str, Any]] = None,
    error_reason: str = "",
) -> EvaluationResult:
    """
    Evaluates candidate response strictly and deterministically using question rubrics,
    expected concepts, and code execution results when the AI LLM service is unavailable.
    Awards fair partial credit and never assigns a false 0/5 when correct concepts are demonstrated.
    """
    trimmed = candidate_answer.strip()
    norm_answer = re.sub(r'[\r\n\t]+', ' ', trimmed.lower())
    ans_tokens = _extract_deterministic_tokens(norm_answer)

    # 1. Check for empty submission
    if not trimmed:
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
            execution_result=execution_result,
            evaluation_status="completed",
        )

    # 2. Check for explicit refusal or "don't know"
    refusal_patterns = [
        r"\b(?:i\s+)?don'?t\s+know\b", r"\bno\s+idea\b", r"\bidk\b",
        r"\bpass\b", r"\bunclear\b", r"\bnot\s+sure\b"
    ]
    if any(re.search(p, norm_answer) for p in refusal_patterns) and len(trimmed.split()) <= 6:
        zero_criteria = [
            CriterionEvaluation(
                criterion_id=c.id,
                awarded_marks=0.0,
                max_marks=c.max_marks,
                evidence=trimmed,
                explanation="Candidate indicated they do not know the answer.",
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
            summary_explanation="Candidate indicated they do not know the answer. Zero marks awarded.",
            addressed_question=True,
            is_ambiguous=False,
            clarification_question=None,
            execution_result=execution_result,
            evaluation_status="completed",
        )

    # 3. Check for Output Prediction questions
    is_code_output = (question.question_type == QuestionType.CODE_OUTPUT)
    expected_out = (question.expected_output or OutputPredictionEvaluator.get_expected_output(question) or "").strip()
    output_matches = False
    if is_code_output and expected_out:
        output_matches = OutputPredictionEvaluator.verify_prediction(expected_out, trimmed)

    # 4. Check for code-writing / debugging with test cases
    tests_passed = execution_result.get("tests_passed", 0) if execution_result else 0
    tests_total = execution_result.get("tests_total", 0) if execution_result else 0
    syntax_valid = execution_result.get("syntax_valid", False) if execution_result else False
    is_code_writing = (question.question_type == QuestionType.CODE_WRITING or (question.question_type == QuestionType.DEBUGGING and question.test_cases))

    # 5. Evaluate each criterion
    validated_evals: List[CriterionEvaluation] = []
    total_awarded = 0.0
    demonstrated_concepts: List[str] = []
    missing_concepts: List[str] = []
    detected_misconceptions: List[str] = []

    # Check for specific verifiable misconceptions in answer
    tuple_mod_claim = bool(
        re.search(r'\btuples?\s+(?:can\s+be\s+modified|can\s+change|support\s+append|\.append)', norm_answer)
        or re.search(r'\bappend\s+(?:to|into)\s+tuples?\b', norm_answer)
    )
    if tuple_mod_claim:
        detected_misconceptions.append("Claiming tuples can be modified using methods like append()")

    for crit in question.rubric:
        crit_id_lower = crit.id.lower()
        crit_desc_lower = crit.description.lower()
        crit_text = f"{crit.id} {crit.description} {crit.evidence_guide}"
        crit_tokens = _extract_deterministic_tokens(crit_text)

        awarded = 0.0
        evidence = "Not addressed."
        explanation = ""

        # A. If code-writing or debugging question with execution result
        if is_code_writing:
            if execution_result:
                if not execution_result.get("syntax_valid", True):
                    awarded = 0.0
                    evidence = str(execution_result.get("syntax_error", "Syntax error in candidate code."))
                    explanation = f"Syntax error detected: {execution_result.get('syntax_error')}. Solution receives 0 marks."
                elif execution_result.get("execution_error"):
                    awarded = 0.0
                    evidence = str(execution_result.get("execution_error", "Runtime error in candidate code."))
                    explanation = f"Execution runtime error: {execution_result.get('execution_error')}. Solution receives 0 marks."
                elif tests_total > 0:
                    pass_ratio = tests_passed / tests_total
                    awarded = round(crit.max_marks * pass_ratio, 2)
                    evidence = f"Automated test runner: {tests_passed}/{tests_total} test cases passed."
                    explanation = f"Deterministic code test verification: {tests_passed}/{tests_total} tests passed."
                else:
                    awarded = 0.0
                    evidence = "No tests executed."
                    explanation = "Code execution was not possible."
            else:
                awarded = 0.0
                evidence = "No code execution result available."
                explanation = "Code solution could not be evaluated without execution result."

        # B. Output prediction criterion
        elif is_code_output and any(k in crit_id_lower or k in crit_desc_lower for k in ("output", "predict", "result")):
            if output_matches:
                awarded = crit.max_marks
                evidence = _find_evidence_sentence(trimmed, {expected_out.lower(), "output", "print", "printed"})
                explanation = f"Correct output predicted: '{expected_out}'."
                demonstrated_concepts.append(f"Predicted expected output '{expected_out}'")
            else:
                awarded = 0.0
                evidence = _find_evidence_sentence(trimmed, {"output", "print", "printed"})
                explanation = f"Incorrect output predicted (expected: '{expected_out}')."
                missing_concepts.append(f"Expected output '{expected_out}'")

        # C. Mutability distinction criterion (e.g. lists vs tuples)
        elif "mutab" in crit_id_lower or "mutability" in crit_desc_lower:
            inverted = bool(
                re.search(r'\blists?\s+(?:are|is|can\'t|cannot)\s+(?:not\s+mutable|immutable)', norm_answer)
                or re.search(r'\btuples?\s+(?:are|is|can\s+be)\s+(?:mutable|modified|changed)', norm_answer)
                or re.search(r'\blists?\s+are\s+immutable', norm_answer)
                or re.search(r'\btuples?\s+are\s+mutable', norm_answer)
            )
            if inverted:
                awarded = 0.0
                evidence = _find_evidence_sentence(trimmed, {"mutable", "immutable", "list", "tuple"})
                explanation = "Candidate incorrectly claimed that lists are immutable or tuples are mutable."
                detected_misconceptions.append("Confusing mutability: lists are mutable, tuples are immutable.")
                missing_concepts.append("Mutability distinction between lists and tuples")
            else:
                has_mutable = bool(
                    re.search(r'\bmutab(?:le|ility)?\b', norm_answer)
                    or "can be modified" in norm_answer
                    or "change in place" in norm_answer
                    or "can change" in norm_answer
                    or "modify in place" in norm_answer
                )
                has_immutable = bool(
                    re.search(r'\bimmutab(?:le|ility)?\b', norm_answer)
                    or "cannot be modified" in norm_answer
                    or "cannot change" in norm_answer
                    or "can't change" in norm_answer
                    or "fixed collection" in norm_answer
                    or "cannot be altered" in norm_answer
                )
                target_evidence_terms = {"mutable", "immutable", "mutability", "immutability", "list", "tuple", "lists", "tuples"}
                evidence = _find_evidence_sentence(trimmed, target_evidence_terms)

                if has_mutable and has_immutable:
                    awarded = crit.max_marks
                    explanation = "Candidate clearly demonstrated the mutability distinction (lists are mutable, tuples are immutable)."
                    demonstrated_concepts.append("Lists are mutable while tuples are immutable")
                elif has_mutable or has_immutable:
                    awarded = round(crit.max_marks * 0.5, 2)
                    explanation = "Candidate partially demonstrated mutability (explained one side of the distinction)."
                    demonstrated_concepts.append("Partial mutability distinction demonstrated")
                else:
                    awarded = 0.0
                    explanation = "Candidate response did not demonstrate the mutability distinction."
                    missing_concepts.append("Mutability distinction between lists and tuples")

        # D. Practical use-case / real-world scenario criterion
        elif any(k in crit_id_lower or k in crit_desc_lower for k in ("use_case", "scenario", "practical", "when you would choose")):
            use_case_patterns = [
                r'\bcoordinates?\b', r'\bdict(?:ionary)?\s+keys?\b', r'\bkeys?\b',
                r'\brecords?\b', r'\bconstant(?:s)?\b', r'\bdata\s+integrity\b',
                r'\bgps\b', r'\blatitude\b', r'\blongitude\b',
                r'\bpoints?\b', r'\bdatabase\b', r'\bfixed\s+collection\b'
            ]
            matched_cases = [p for p in use_case_patterns if re.search(p, norm_answer)]
            target_evidence_terms = {"coordinate", "coordinates", "dictionary", "dict", "key", "keys", "record", "records", "constant"}

            if matched_cases:
                awarded = crit.max_marks
                evidence = _find_evidence_sentence(trimmed, target_evidence_terms)
                explanation = "Candidate provided a valid practical real-world scenario for using tuples."
                demonstrated_concepts.append("Valid practical scenario / use case demonstrated")
            else:
                awarded = 0.0
                evidence = "No practical scenario or real-world use case was provided in the answer."
                explanation = "Did not provide a practical real-world scenario (e.g. coordinates, dictionary keys, constant records) where a tuple is preferred."
                missing_concepts.append("Practical real-world use case for tuples")

        # E. Technical depth / syntax / nuances
        elif any(k in crit_id_lower or k in crit_desc_lower for k in ("technical_depth", "syntax", "nuance", "performance", "memory")):
            depth_terms = [
                r'\bhash(?:able|ability)?\b', r'\bparenthes(?:es|is)?\b', r'\bbrackets?\b',
                r'\[\]', r'\(\)', r'\bmemor(?:y)?\b', r'\boverhead\b', r'\bperform(?:ance)?\b',
                r'\bfaster\b', r'\bsyntax\b', r'\bheterogeneous\b', r'\bhomogeneous\b'
            ]
            matched_depth = [p for p in depth_terms if re.search(p, norm_answer)]
            target_evidence_terms = {"hashable", "parentheses", "brackets", "syntax", "memory", "performance", "overhead", "[]", "()"}

            if len(matched_depth) >= 2:
                awarded = crit.max_marks
                evidence = _find_evidence_sentence(trimmed, target_evidence_terms)
                explanation = "Candidate demonstrated accurate technical depth (syntax, memory, or hashability nuances)."
                demonstrated_concepts.append("Technical depth (syntax, memory, or hashability)")
            elif len(matched_depth) == 1:
                awarded = round(crit.max_marks * 0.5, 2)
                evidence = _find_evidence_sentence(trimmed, target_evidence_terms)
                explanation = "Candidate partially demonstrated technical depth."
                demonstrated_concepts.append("Partial technical depth demonstrated")
            else:
                awarded = 0.0
                evidence = "Technical syntax, memory, or hashability nuances not mentioned."
                explanation = "Did not mention syntax differences, hashability, or memory/performance nuances."
                missing_concepts.append("Technical depth (syntax, memory, or hashability)")

        # F. General criterion scoring based on expected concepts & token overlap
        else:
            examples = re.findall(r'\((?:e\.g\.,?\s*|such as\s*)(.*?)\)', crit.description, re.IGNORECASE)
            example_tokens = set()
            for ex in examples:
                example_tokens.update(_extract_deterministic_tokens(ex))

            matched_crit_tokens = crit_tokens.intersection(ans_tokens)
            matched_example_tokens = example_tokens.intersection(ans_tokens) if example_tokens else set()

            evidence = _find_evidence_sentence(trimmed, crit_tokens)

            related_concepts = [
                concept for concept in question.expected_concepts
                if len(_extract_deterministic_tokens(concept).intersection(crit_tokens)) >= 1
            ]

            matched_concept_count = 0
            for concept in related_concepts:
                c_tokens = _extract_deterministic_tokens(concept)
                if c_tokens and len(c_tokens.intersection(ans_tokens)) >= max(1, int(len(c_tokens) * 0.4)):
                    matched_concept_count += 1
                    if concept not in demonstrated_concepts:
                        demonstrated_concepts.append(concept)
                else:
                    if concept not in missing_concepts:
                        missing_concepts.append(concept)

            if related_concepts and matched_concept_count == len(related_concepts):
                awarded = crit.max_marks
                explanation = f"Candidate demonstrated all expected technical concepts for '{crit.description}'."
            elif related_concepts and matched_concept_count > 0:
                ratio = matched_concept_count / len(related_concepts)
                awarded = round(crit.max_marks * ratio, 2)
                explanation = f"Candidate demonstrated partial technical concepts for '{crit.description}'."
            elif len(matched_crit_tokens) >= 3 or (example_tokens and len(matched_example_tokens) >= 1):
                ratio = len(matched_crit_tokens) / max(3, len(crit_tokens))
                awarded = round(crit.max_marks * min(1.0, max(0.5, ratio)), 2)
                explanation = f"Candidate demonstrated key technical aspects of '{crit.description}'."
            elif len(matched_crit_tokens) >= 2:
                ratio = len(matched_crit_tokens) / max(3, len(crit_tokens))
                awarded = round(crit.max_marks * min(1.0, max(0.35, ratio)), 2)
                explanation = f"Candidate partially mentioned concepts related to '{crit.description}'."
            else:
                awarded = 0.0
                explanation = f"Candidate response did not demonstrate the concepts required for '{crit.description}'."

        total_awarded += awarded
        validated_evals.append(
            CriterionEvaluation(
                criterion_id=crit.id,
                awarded_marks=awarded,
                max_marks=crit.max_marks,
                evidence=evidence,
                explanation=explanation,
            )
        )

    # 6. Check for detected misconceptions penalty
    if detected_misconceptions and total_awarded > 0:
        penalty = min(total_awarded * 0.25, 1.0)
        total_awarded = max(0.0, total_awarded - penalty)

    max_marks = question.total_marks
    total_awarded = round(min(total_awarded, max_marks), 2)
    percentage = round((total_awarded / max_marks) * 100.0, 2) if max_marks > 0 else 0.0

    # Ensure missing concepts contains all unfulfilled concepts
    for concept in question.expected_concepts:
        if concept not in demonstrated_concepts and concept not in missing_concepts:
            missing_concepts.append(concept)

    # Determine status and summary
    safe_reason = re.sub(r'AIza[0-9A-Za-z-_]{35}', '[REDACTED]', error_reason)
    if "429" in safe_reason or "resource_exhausted" in safe_reason.lower():
        service_note = "AI service rate limit / HTTP 429"
    elif "timeout" in safe_reason.lower():
        service_note = "AI service timeout"
    elif "connection" in safe_reason.lower():
        service_note = "AI service offline"
    else:
        service_note = "AI service fallback"

    # Requirement 5: If a reliable score cannot be calculated (e.g. substantive answer, no criteria or zero confidence),
    # mark as pending/unavailable instead of falsely reporting 0.
    eval_status = "fallback"
    syntax_failed = bool(execution_result and not execution_result.get("syntax_valid", True))
    exec_error = bool(execution_result and execution_result.get("execution_error"))
    tests_failed = bool(execution_result and tests_total > 0 and tests_passed == 0)
    is_code_failure = syntax_failed or exec_error or tests_failed

    if (
        total_awarded == 0.0
        and len(trimmed.split()) >= 15
        and not detected_misconceptions
        and not is_code_output
        and not is_code_failure
    ):
        eval_status = "pending"
        summary_explanation = (
            f"Evaluation pending ({service_note}). Your answer has been safely recorded. "
            "Automated rubric matching found insufficient criteria match; marks are not penalized with zero."
        )
    elif total_awarded > 0.0:
        summary_explanation = (
            f"Evaluation completed via deterministic fallback ({service_note}). "
            f"Candidate demonstrated verified technical concepts (awarded {total_awarded}/{max_marks} marks, {percentage}%)."
        )
    else:
        summary_explanation = (
            f"Evaluation completed via deterministic fallback ({service_note}). "
            f"Candidate response did not demonstrate the required technical concepts for this question (0.0/{max_marks} marks)."
        )

    return EvaluationResult(
        question_id=question.id,
        awarded_marks=total_awarded,
        max_marks=max_marks,
        percentage=percentage,
        criteria_evaluations=validated_evals,
        demonstrated_concepts=demonstrated_concepts,
        partial_concepts=[],
        missing_concepts=missing_concepts,
        incorrect_claims=detected_misconceptions,
        summary_explanation=summary_explanation,
        addressed_question=True,
        is_ambiguous=False,
        clarification_question=None,
        execution_result=execution_result,
        evaluation_status=eval_status,
    )


def json_list(items: List[str]) -> str:
    """Helper to format list as clean bullet points for prompts."""
    if not items:
        return "- (None listed)"
    return "\n".join(f"- {item}" for item in items)
