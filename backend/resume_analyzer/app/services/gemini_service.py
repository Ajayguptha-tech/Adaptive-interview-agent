"""Dedicated service interface for Google Gemini API via official google-genai SDK."""
import os
import json
import logging
from typing import Optional, Dict, Any, List

logger = logging.getLogger("resumeiq.gemini")


class GeminiService:
    """Manages hosted AI interactions using the official google-genai SDK.
    Gracefully handles missing keys, quota limits, timeouts, and malformed outputs.
    """

    def __init__(self):
        self.api_key = os.environ.get("GEMINI_API_KEY", "").strip()
        self.model_name = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash").strip()
        self._client = None

        if self.api_key:
            try:
                from google import genai
                self._client = genai.Client(api_key=self.api_key)
                logger.info(f"Gemini client initialized with model '{self.model_name}'")
            except Exception as e:
                logger.warning(f"Failed to initialize Gemini client: {e}")
                self._client = None

    def is_configured(self) -> bool:
        return bool(self.api_key and self._client)

    def generate_improvements(
        self,
        resume_text: str,
        job_title: str,
        job_description: str,
        matched_skills: List[str],
        missing_skills: List[str],
    ) -> Optional[Dict[str, Any]]:
        """Generate structured resume improvements and bullet rewrites.
        Returns parsed JSON dict or None on failure.
        """
        if not self.is_configured():
            return None

        prompt = f"""
You are an expert executive resume coach and ATS optimization specialist.
Analyze this resume against the target job description and generate targeted improvements.

CRITICAL CONSTRAINTS:
1. Ground all feedback strictly in the candidate's existing experience and the target job description.
2. DO NOT invent fake metrics, unverified qualifications, imaginary past companies, or claims the candidate didn't make.
3. For bullet rewrites, transform existing weak bullets into high-impact STAR/Action-Context-Result format, highlighting relevant keywords while keeping facts accurate.
4. Output MUST be valid JSON with no markdown wrapping or code fences.

Target Job: {job_title}
Job Description:
{job_description[:2000]}

Candidate Matched Skills: {', '.join(matched_skills[:15])}
Missing Required/Preferred Skills: {', '.join(missing_skills[:15])}

Candidate Resume Text:
{resume_text[:3000]}

Respond ONLY with a JSON object in this exact schema:
{{
  "strengths": ["string", "string", "string"],
  "critical_improvements": ["string", "string", "string"],
  "bullet_rewrites": [
    {{
      "original_bullet": "exact or paraphrased weak bullet from resume",
      "rewritten_bullet": "impactful rewrite highlighting relevant skills",
      "reasoning": "why this improves ATS parseability and recruiter interest",
      "target_role_or_project": "associated role or project name"
    }}
  ],
  "recruiter_summary": "2-3 sentence executive summary of candidate fit from a recruiter lens",
  "tailored_summary_draft": "Suggested 3-4 sentence professional summary to place at the top of the resume",
  "action_plan": ["step 1", "step 2", "step 3"]
}}
"""

        try:
            response = self._client.models.generate_content(
                model=self.model_name,
                contents=prompt,
            )

            if not response or not response.text:
                return None

            raw_text = response.text.strip()
            # Clean possible markdown json fences
            if raw_text.startswith("```json"):
                raw_text = raw_text[7:]
            elif raw_text.startswith("```"):
                raw_text = raw_text[3:]
            if raw_text.endswith("```"):
                raw_text = raw_text[:-3]
            raw_text = raw_text.strip()

            parsed = json.loads(raw_text)
            return parsed
        except Exception as e:
            logger.error(f"Gemini API error during improvement generation: {e}")
            return None

    def generate_chat_reply(
        self,
        analysis_context: Dict[str, Any],
        chat_history: List[Dict[str, str]],
        user_message: str,
    ) -> Optional[str]:
        """Generate conversational answer grounded in resume and job description."""
        if not self.is_configured():
            return None

        # Format history
        history_snippet = "\n".join(
            [f"{msg.get('sender', 'user').capitalize()}: {msg.get('content', '')}" for msg in chat_history[-6:]]
        )

        prompt = f"""
You are the ResumeIQ Improvement Assistant. You are coaching a candidate to tailor their resume for a specific job.

CONTEXT:
Target Job Title: {analysis_context.get('job_title', 'Target Role')}
Company: {analysis_context.get('company', 'Target Company')}
Overall ATS Score: {analysis_context.get('overall_score', 'N/A')}/100
Matched Skills: {analysis_context.get('matched_skills', [])}
Missing Skills: {analysis_context.get('missing_skills', [])}

CANDIDATE RESUME EXCERPT:
{analysis_context.get('resume_excerpt', '')[:2500]}

RECENT CHAT HISTORY:
{history_snippet}

USER QUESTION:
{user_message}

RULES:
- Answer directly, practically, and professionally.
- Ground advice strictly in the provided resume and job requirements.
- Never invent experience or fabricate achievements.
- If the user asks for a bullet rewrite, provide a draft and remind them to verify facts/numbers.
- If information is missing, ask clarifying questions instead of hallucinating.
- Keep the response concise (1-3 paragraphs or bullet points).
"""

        try:
            response = self._client.models.generate_content(
                model=self.model_name,
                contents=prompt,
            )
            if response and response.text:
                return response.text.strip()
            return None
        except Exception as e:
            logger.error(f"Gemini API chat generation error: {e}")
            return None
