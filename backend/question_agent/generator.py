"""
Dynamic Question Generator and Multi-Candidate Selection Engine.
Generates candidate-specific, grounded, non-repetitive interview questions using Ollama (qwen2.5:7b):
- Supports all 12 specialized question formats
- Grounds questions in candidate resume evidence (projects, tech stacks, claims)
- Layer 5: Generates and evaluates candidate questions, selecting optimal candidates
- Layer 6: Bounded retries with rejected context, graceful fallback to QuestionCatalog
- Measures generation latency and token throughput
"""

import json
import logging
import random
import re
import time
import uuid
from typing import Dict, Any, List, Optional, Set, Tuple

from backend.llm_client import LLMClient, default_llm_client
from backend.models import (
    DifficultyLevel,
    Question,
    QuestionType,
    RubricCriterion,
)
from backend.question_agent.models import (
    QuestionFormat,
    QuestionCandidate,
    ResumeIntelligenceProfile,
    InterviewBlueprint,
    FORMAT_TO_QUESTION_TYPE,
)
from backend.question_agent.diversity_engine import QuestionDiversityEngine
from backend.question_agent.question_validator import QuestionQualityValidator
from backend.question_agent.catalog import QuestionCatalog

logger = logging.getLogger(__name__)

MAX_RETRIES = 3


class QuestionGeneratorEngine:
    """Generates, validates, and selects dynamic questions using Ollama with layered diversity."""

    def __init__(
        self,
        llm_client: Optional[LLMClient] = None,
        catalog: Optional[QuestionCatalog] = None,
    ):
        self.llm_client = llm_client or default_llm_client
        self.catalog = catalog or QuestionCatalog()
        self.last_latency_ms: float = 0.0
        self.fallback_count: int = 0
        self.total_generations: int = 0

    def generate_candidate_question(
        self,
        blueprint: InterviewBlueprint,
        topic: str,
        competency: str,
        difficulty: DifficultyLevel,
        question_format: QuestionFormat,
        session_asked_texts: List[str],
        prior_candidate_texts: Optional[List[str]] = None,
        candidate_context: Optional[Dict[str, Any]] = None,
        target_project: Optional[str] = None,
        use_llm: bool = True,
        session_asked_ids: Optional[Set[str]] = None,
    ) -> Tuple[Question, str, QuestionCandidate]:
        """
        Executes candidate generation & selection pipeline (Layers 1-6).
        Returns: (Question, selection_reason, QuestionCandidate)
        """
        self.total_generations += 1
        t_start = time.perf_counter()
        asked_ids = set(session_asked_ids or set())

        # If LLM generation requested, attempt generation with bounded retries
        if use_llm:
            rejected_reasons: List[str] = []
            for attempt in range(1, MAX_RETRIES + 1):
                try:
                    candidate = self._generate_single_candidate(
                        blueprint=blueprint,
                        topic=topic,
                        competency=competency,
                        difficulty=difficulty,
                        question_format=question_format,
                        session_asked_texts=session_asked_texts,
                        prior_candidate_texts=prior_candidate_texts,
                        candidate_context=candidate_context,
                        target_project=target_project,
                        attempt=attempt,
                        rejected_reasons=rejected_reasons,
                    )

                    if candidate and candidate.question:
                        # 1. Structural and quality validation
                        t_val_start = time.perf_counter()
                        validation = QuestionQualityValidator.validate_question(
                            question=candidate.question,
                            expected_format=question_format,
                            role=blueprint.target_role,
                            track=blueprint.target_track,
                            resume_profile=blueprint.resume_profile,
                        )
                        candidate.validation_ms = round((time.perf_counter() - t_val_start) * 1000.0, 2)
                        candidate.validation = validation

                        if not validation.is_valid:
                            logger.info(
                                "[VALIDATION_REJECT] Attempt %d: %s",
                                attempt, "; ".join(validation.issues)
                            )
                            rejected_reasons.append(f"Format/quality issue: {'; '.join(validation.issues[:2])}")
                            continue

                        # 2. Check Layer 1 (Exact) and Layer 2 (Semantic) Duplicates
                        # For adaptive follow-ups, concept alignment with previous question is intended;
                        # only reject if nearly identical wording / exact duplicate.
                        t_dup_start = time.perf_counter()
                        threshold = 0.65 if question_format == QuestionFormat.ADAPTIVE_FOLLOW_UP else 0.38
                        is_dup, dup_reason, sim = QuestionDiversityEngine.check_duplicate(
                            candidate_text=candidate.question.text,
                            session_asked_texts=session_asked_texts,
                            prior_candidate_texts=prior_candidate_texts,
                            threshold=threshold,
                        )
                        candidate.duplicate_check_ms = round((time.perf_counter() - t_dup_start) * 1000.0, 2)

                        if is_dup:
                            logger.info(
                                "[DIVERSITY_REJECT] Attempt %d: %s", attempt, dup_reason
                            )
                            rejected_reasons.append(dup_reason)
                            continue

                        # Candidate is unique, validated, and grounded!
                        dur_ms = round((time.perf_counter() - t_start) * 1000.0, 2)
                        self.last_latency_ms = dur_ms
                        candidate.generation_latency_ms = dur_ms

                        reason = (
                            f"Generated fresh {question_format.value.replace('_', ' ')} question on '{topic}' "
                            f"at {difficulty.value} level."
                        )
                        if target_project:
                            reason += f" Grounded in resume project '{target_project}'."

                        return candidate.question, reason, candidate

                except Exception as exc:
                    logger.warning("[GENERATION_ERROR] Attempt %d failed: %s", attempt, exc)
                    rejected_reasons.append(f"Engine exception: {str(exc)[:60]}")

        # Layer 6 Fallback: select unasked question from catalog
        self.fallback_count += 1
        logger.info(
            "[FALLBACK_TRIGGERED] Falling back to QuestionCatalog for topic '%s' (diff=%s, format=%s). Total fallbacks: %d",
            topic, difficulty.value, question_format.value, self.fallback_count
        )

        fallback_q = self.catalog.find_best_catalog_fallback(
            track=blueprint.target_track,
            topic=topic,
            difficulty=difficulty,
            question_format=question_format,
            session_asked_ids=asked_ids,
            session_asked_texts=session_asked_texts,
            prior_candidate_texts=prior_candidate_texts,
        )

        if not fallback_q:
            # Ultimate emergency fallback to verified question banks with strict deduplication
            from backend.question_bank import get_all_questions
            from backend.fullstack.question_bank import get_all_fullstack_questions
            emergency_bank = get_all_fullstack_questions() if blueprint.target_track == "fullstack" else get_all_questions()
            norm_asked = {QuestionDiversityEngine.normalize_text(t) for t in session_asked_texts if t}
            unasked = [
                q for q in emergency_bank
                if q.id not in asked_ids
                and QuestionDiversityEngine.normalize_text(q.text) not in norm_asked
            ]
            fallback_q = random.choice(unasked) if unasked else (emergency_bank[0] if emergency_bank else None)

        dur_ms = (time.perf_counter() - t_start) * 1000.0
        self.last_latency_ms = dur_ms

        fallback_candidate = QuestionCandidate(
            question=fallback_q,
            format=question_format,
            source_type="catalog_curated",
            generation_latency_ms=dur_ms,
            attempt_number=1,
        )

        reason = (
            f"Selected validated {fallback_q.question_type.value} question on '{fallback_q.topic}' "
            f"at {fallback_q.difficulty.value} level from catalog."
        )
        return fallback_q, reason, fallback_candidate

    def _generate_single_candidate(
        self,
        blueprint: InterviewBlueprint,
        topic: str,
        competency: str,
        difficulty: DifficultyLevel,
        question_format: QuestionFormat,
        session_asked_texts: List[str],
        prior_candidate_texts: Optional[List[str]] = None,
        candidate_context: Optional[Dict[str, Any]] = None,
        target_project: Optional[str] = None,
        attempt: int = 1,
        rejected_reasons: Optional[List[str]] = None,
    ) -> Optional[QuestionCandidate]:
        """Constructs grounded prompt and executes Ollama generation with qwen2.5:7b."""
        t_sub_start = time.perf_counter()

        # Build prompt components
        type_instructions = self._get_format_instructions(question_format, target_project)
        resume_grounding = self._build_resume_grounding_clause(blueprint, target_project)
        exclusion_clause = self._build_exclusion_clause(session_asked_texts, prior_candidate_texts)
        adaptive_steering = self._build_adaptive_steering_clause(candidate_context)

        retry_notice = ""
        if attempt > 1 and rejected_reasons:
            retry_notice = (
                f"ATTEMPT #{attempt} CORRECTION NOTICE:\n"
                f"Previous generation was rejected due to: {'; '.join(rejected_reasons[-2:])}\n"
                "You MUST choose a completely distinct angle, mechanism, or scenario. Do NOT repeat previous ideas.\n"
            )

        tc_schema = '[{"input": "sample_arg", "expected": "result"}]' if question_format == QuestionFormat.CODE_WRITING else "null"
        starter_schema = '"def solution(param):\\n    pass"' if question_format == QuestionFormat.CODE_WRITING else "null"
        func_schema = '"solution"' if question_format == QuestionFormat.CODE_WRITING else "null"
        code_schema = '"# Code snippet\\ndef example(): pass"' if question_format in (QuestionFormat.CODE_DEBUGGING, QuestionFormat.OUTPUT_PREDICTION) else "null"
        exp_schema = '"exact terminal stdout"' if question_format == QuestionFormat.OUTPUT_PREDICTION else "null"

        prompt = f"""Generate a {blueprint.target_role} technical interview question.
Topic: {topic} | Competency: {competency} | Difficulty: {difficulty.value} | Format: {question_format.value} | Track: {blueprint.target_track}

{type_instructions}
{resume_grounding}
{adaptive_steering}
{retry_notice}
{exclusion_clause}

Respond ONLY with a valid JSON object matching this schema:
{{
  "topic": "{topic}",
  "competency": "{competency}",
  "difficulty": "{difficulty.value}",
  "question_type": "{FORMAT_TO_QUESTION_TYPE.get(question_format, QuestionType.CONCEPTUAL).value}",
  "text": "Complete question prompt presented directly to the candidate",
  "code_snippet": {code_schema},
  "starter_code": {starter_schema},
  "function_name": {func_schema},
  "expected_output": {exp_schema},
  "test_cases": {tc_schema},
  "expected_concepts": ["concept 1", "concept 2", "concept 3"],
  "common_misconceptions": ["misconception 1", "misconception 2"],
  "rubric": [
    {{"id": "crit_1", "description": "Specific criterion", "max_marks": 2.5, "evidence_guide": "Concrete evidence required"}},
    {{"id": "crit_2", "description": "Second criterion", "max_marks": 2.5, "evidence_guide": "Concrete evidence required"}}
  ],
  "reference_answer": "Concise authoritative reference solution (under 80 words)"
}}
If code/debugging is required, populate code_snippet or test_cases concisely. Keep reference answer under 80 words. Rubric max_marks must sum to 5.0.
"""

        system_prompt = (
            f"You are a principal technical interviewer and software architect conducting a {blueprint.target_role} interview. "
            "You create authentic, rigorous, non-repetitive interview questions with deterministic evaluation rubrics. "
            "Never invent facts not present in the candidate's resume. "
            "Always return strictly valid JSON matching the requested schema without markdown wrapper."
        )

        # Vary temperature slightly across retries to increase diversity
        temp = 0.70 + (attempt - 1) * 0.08
        raw_json = self.llm_client.generate_json(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=min(0.95, temp),
            options={"num_predict": 550, "num_ctx": 2048},
        )

        t_parse_start = time.perf_counter()
        q = self._build_question_from_raw(raw_json, fallback_topic=topic, fallback_diff=difficulty)
        parse_dur_ms = round((time.perf_counter() - t_parse_start) * 1000.0, 2)
        if not q:
            return None

        perf = getattr(self.llm_client, "last_perf_stats", {}) or {}
        dur_ms = round((time.perf_counter() - t_sub_start) * 1000.0, 2)
        return QuestionCandidate(
            question=q,
            format=question_format,
            target_project=target_project,
            source_type="model_generated",
            generation_latency_ms=dur_ms,
            attempt_number=attempt,
            prompt_eval_ms=perf.get("prompt_eval_duration_ms", 0.0),
            token_gen_ms=perf.get("eval_duration_ms", 0.0),
            output_parse_ms=parse_dur_ms,
            tokens_per_second=perf.get("tokens_per_second", 0.0),
            eval_token_count=perf.get("eval_count", 0),
        )

    def _get_format_instructions(self, fmt: QuestionFormat, target_project: Optional[str]) -> str:
        """Returns targeted formatting instructions for all 12 question formats."""
        if fmt == QuestionFormat.TECHNICAL_FUNDAMENTALS:
            return (
                "FORMAT: TECHNICAL FUNDAMENTALS\n"
                "Focus on language semantics, memory model, execution lifecycle, or core data structure mechanics. "
                "Assess whether the candidate deeply understands internal workings rather than just memorized syntax."
            )
        elif fmt == QuestionFormat.CONCEPTUAL_EXPLANATION:
            return (
                "FORMAT: CONCEPTUAL EXPLANATION\n"
                "Ask candidate to explain how a mechanism operates under the hood, why it was designed that way, "
                "and what happens at runtime. Do not require full code writing."
            )
        elif fmt == QuestionFormat.PRACTICAL_IMPLEMENTATION:
            return (
                "FORMAT: PRACTICAL IMPLEMENTATION\n"
                "Present a concrete engineering requirement and ask candidate how they would implement it cleanly, "
                "including handling of edge cases and concurrency or resource cleanup."
            )
        elif fmt == QuestionFormat.CODE_WRITING:
            return (
                "FORMAT: CODE WRITING\n"
                "Provide an algorithmic or practical problem where candidate writes a function. "
                "Specify function_name, arguments, and return types. Provide starter_code and 3-5 concrete test cases."
            )
        elif fmt == QuestionFormat.CODE_DEBUGGING:
            return (
                "FORMAT: CODE DEBUGGING\n"
                "Provide a 4-10 line code snippet in 'code_snippet' containing a realistic bug (e.g. race condition, "
                "reference cycle, mutability defect, or async pitfall). Ask candidate to identify the defect and provide fix."
            )
        elif fmt == QuestionFormat.OUTPUT_PREDICTION:
            return (
                "FORMAT: OUTPUT PREDICTION\n"
                "Provide a tricky or illustrative 4-8 line code snippet in 'code_snippet'. "
                "Candidate must predict the exact output. Provide exact expected stdout in 'expected_output'."
            )
        elif fmt == QuestionFormat.DESIGN_ARCHITECTURE:
            return (
                "FORMAT: DESIGN & ARCHITECTURE\n"
                "Present a system design challenge (API design, data flow, caching tier, or microservice boundary). "
                "Candidate must address trade-offs, fault tolerance, and data consistency."
            )
        elif fmt == QuestionFormat.PROJECT_DEEP_DIVE:
            proj_str = f"'{target_project}'" if target_project else "one of candidate's actual projects"
            return (
                f"FORMAT: PROJECT DEEP DIVE ({proj_str})\n"
                "Ground the question directly in the candidate's actual project details from their resume. "
                "Inquire about architectural trade-offs, scalability bottlenecks, why specific technologies were chosen, "
                "or how they resolved a critical implementation challenge."
            )
        elif fmt == QuestionFormat.TROUBLESHOOTING_SCENARIO:
            return (
                "FORMAT: TROUBLESHOOTING SCENARIO\n"
                "Present a realistic production outage or performance degradation incident (e.g. connection pool exhaustion, "
                "CPU spike, memory leak, or deadlocks). Candidate must explain their root-cause diagnosis and resolution steps."
            )
        elif fmt == QuestionFormat.TRADEOFF_DECISION:
            return (
                "FORMAT: TRADEOFF & DECISION MAKING\n"
                "Ask candidate to evaluate two competing architectural patterns or tools for a specific workload "
                "(e.g. relational vs document store, sync vs async worker, or polling vs websockets). Focus on justification."
            )
        elif fmt == QuestionFormat.APPLIED_REAL_WORLD:
            return (
                "FORMAT: APPLIED REAL WORLD SCENARIO\n"
                "Explore an applied scenario combining candidate's claimed tech stack (e.g. FastAPI, PostgreSQL, Docker). "
                "Challenge candidate on real-world integration, migration, or deployment concerns."
            )
        elif fmt == QuestionFormat.ADAPTIVE_FOLLOW_UP:
            return (
                "FORMAT: ADAPTIVE FOLLOW-UP\n"
                "Follow up on candidate's previous response to probe a missing concept, resolve ambiguity, "
                "or test an advanced edge case of the same topic. Keep it directly connected to their earlier answer."
            )
        return "Create a rigorous technical question."

    def _build_resume_grounding_clause(
        self, blueprint: InterviewBlueprint, target_project: Optional[str]
    ) -> str:
        """Grounds prompt in candidate's verified skills and projects."""
        profile = blueprint.resume_profile
        if not profile:
            return ""

        parts = ["RESUME GROUNDING EVIDENCE:"]
        if profile.programming_languages:
            parts.append(f"- Languages: {', '.join(profile.programming_languages[:5])}")
        if profile.frameworks:
            parts.append(f"- Frameworks: {', '.join(profile.frameworks[:5])}")
        if profile.tools_platforms:
            parts.append(f"- Tools/Platforms: {', '.join(profile.tools_platforms[:5])}")

        # Highlight target project or candidate projects
        if profile.projects:
            proj_summaries = []
            for p in profile.projects[:3]:
                t_str = f" (Tech: {', '.join(p.technologies)})" if p.technologies else ""
                proj_summaries.append(f"  * {p.title}{t_str}: {p.objectives or p.description or ''}")
            parts.append("- Candidate Projects:\n" + "\n".join(proj_summaries))

        if blueprint.tech_stack:
            parts.append(f"- Configured Tech Stack: {blueprint.tech_stack}")

        parts.append(
            "CRITICAL: Do NOT invent projects, certifications, or skills not listed above. "
            "Ground the question in these actual technologies."
        )
        return "\n".join(parts) + "\n"

    def _build_exclusion_clause(
        self, session_asked_texts: List[str], prior_candidate_texts: Optional[List[str]]
    ) -> str:
        """Builds explicit exclusion clause with previews of previously asked questions."""
        all_exclude = list(session_asked_texts) + (prior_candidate_texts or [])
        if not all_exclude:
            return ""

        previews = [f"- {t[:90]}..." for t in all_exclude[-8:]]
        return (
            "EXCLUDE PREVIOUS QUESTIONS (DO NOT DUPLICATE THESE PROBLEMS OR CONCEPTS):\n"
            + "\n".join(previews) + "\n"
        )

    def _build_adaptive_steering_clause(self, candidate_context: Optional[Dict[str, Any]]) -> str:
        """Translates candidate performance into adaptive steering instructions."""
        if not candidate_context:
            return ""

        missing = candidate_context.get("missing_concepts", [])
        misconceptions = candidate_context.get("misconceptions", [])
        last_score = candidate_context.get("last_score")

        points = []
        if last_score is not None:
            if last_score >= 80.0:
                points.append(f"Candidate scored high ({last_score:.0f}%). Probe advanced edge cases or trade-offs.")
            elif last_score < 40.0:
                points.append(f"Candidate struggled ({last_score:.0f}%). Test core fundamentals or guided diagnostics.")

        if missing:
            points.append(f"Candidate recently missed: {', '.join(missing[:3])}. Assess understanding here.")
        if misconceptions:
            points.append(f"Candidate exhibited misconception: {', '.join(misconceptions[:2])}.")

        if not points:
            return ""
        return "ADAPTIVE STEERING:\n" + "\n".join(f"- {p}" for p in points) + "\n"

    def _build_question_from_raw(
        self, data: Dict[str, Any], fallback_topic: str, fallback_diff: DifficultyLevel
    ) -> Optional[Question]:
        """Parses and validates raw JSON output into a Question model."""
        if not isinstance(data, dict):
            return None

        text = (data.get("text") or "").strip()
        if len(text) < 20:
            return None

        diff_str = str(data.get("difficulty", fallback_diff.value)).lower()
        diff = {
            "beginner": DifficultyLevel.BEGINNER,
            "intermediate": DifficultyLevel.INTERMEDIATE,
            "advanced": DifficultyLevel.ADVANCED,
        }.get(diff_str, fallback_diff)

        type_str = str(data.get("question_type", "conceptual")).lower()
        q_type = {
            "conceptual": QuestionType.CONCEPTUAL,
            "code_writing": QuestionType.CODE_WRITING,
            "code_output": QuestionType.CODE_OUTPUT,
            "debugging": QuestionType.DEBUGGING,
            "practical": QuestionType.PRACTICAL,
            "scenario": QuestionType.SCENARIO,
            "follow_up": QuestionType.FOLLOW_UP,
        }.get(type_str, QuestionType.CONCEPTUAL)

        # Rubric parsing
        rubric_raw = data.get("rubric", [])
        rubric_criteria: List[RubricCriterion] = []
        if isinstance(rubric_raw, list):
            for idx, c in enumerate(rubric_raw):
                if isinstance(c, dict):
                    rubric_criteria.append(
                        RubricCriterion(
                            id=str(c.get("id") or f"crit_{idx+1}"),
                            description=str(c.get("description") or f"Criterion {idx+1}"),
                            max_marks=float(c.get("max_marks", 2.5)),
                            evidence_guide=str(c.get("evidence_guide") or "Evidence required"),
                        )
                    )

        if not rubric_criteria:
            rubric_criteria = [
                RubricCriterion(id="crit_1", description="Technical accuracy and depth", max_marks=2.5, evidence_guide="Accurate technical response"),
                RubricCriterion(id="crit_2", description="Clarity and trade-off justification", max_marks=2.5, evidence_guide="Clear trade-off reasoning"),
            ]

        # Normalize rubric marks to 5.0
        QuestionQualityValidator._normalize_rubric_marks(rubric_criteria)

        expected_raw = data.get("expected_concepts")
        if isinstance(expected_raw, list):
            expected = [str(c).strip() for c in expected_raw if str(c).strip()]
        else:
            expected = []
        if not expected:
            expected = ["Demonstrates clear technical understanding of core principles."]

        misc_raw = data.get("common_misconceptions")
        if isinstance(misc_raw, list):
            misconceptions = [str(m).strip() for m in misc_raw if str(m).strip()]
        else:
            misconceptions = []

        test_cases_raw = data.get("test_cases")
        test_cases = None
        if isinstance(test_cases_raw, list):
            valid_tc = []
            for tc in test_cases_raw:
                if isinstance(tc, dict) and "input" in tc and "expected" in tc:
                    valid_tc.append(tc)
            test_cases = valid_tc if valid_tc else None

        slug = re.sub(r"[^a-z0-9]+", "-", fallback_topic.lower()).strip("-")[:12]
        qid = f"dyn-{slug}-{diff.value[:3]}-{uuid.uuid4().hex[:6]}"

        def _safe_str(val: Any) -> Optional[str]:
            if val is None:
                return None
            if isinstance(val, (dict, list)):
                return json.dumps(val)
            return str(val).strip()

        code_snip = _safe_str(data.get("code_snippet"))
        starter = _safe_str(data.get("starter_code"))
        is_coding = bool(
            q_type == QuestionType.CODE_WRITING
            or (q_type == QuestionType.DEBUGGING and bool(code_snip or starter))
        )
        resp_type = "code_writing" if q_type == QuestionType.CODE_WRITING else ("debugging" if is_coding else "verbal")

        return Question(
            id=qid,
            topic=str(data.get("topic") or fallback_topic),
            competency=str(data.get("competency") or "Technical Competency"),
            difficulty=diff,
            question_type=q_type,
            response_type=resp_type,
            requires_code=is_coding,
            text=text,
            code_snippet=code_snip,
            starter_code=starter,
            function_name=_safe_str(data.get("function_name")),
            expected_output=_safe_str(data.get("expected_output")),
            test_cases=test_cases,
            expected_concepts=expected,
            common_misconceptions=misconceptions,
            rubric=rubric_criteria,
            reference_answer=str(data.get("reference_answer") or ""),
        )
