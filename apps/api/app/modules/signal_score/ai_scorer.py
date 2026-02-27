"""AI Scorer: evaluates document quality via AI Gateway."""

import json
import time

import httpx
import structlog

from app.core.config import settings

logger = structlog.get_logger()

DEFAULT_ASSESSMENT = {
    "score": 0,
    "reasoning": "No evaluation available",
    "strengths": [],
    "weaknesses": [],
    "recommendation": "Upload relevant documentation",
}


class AIScorer:
    """Sync client for AI Gateway document quality evaluation."""

    def __init__(self) -> None:
        self.gateway_url = settings.AI_GATEWAY_URL
        self.api_key = settings.AI_GATEWAY_API_KEY
        self.timeout = 60.0

    def evaluate_document_quality(
        self,
        document_text: str,
        criterion_name: str,
        criterion_description: str,
        project_context: dict,
    ) -> dict:
        """Evaluate document quality against a criterion via AI Gateway.

        Args:
            document_text: Extracted text from relevant documents (max 8000 chars used).
            criterion_name: Name of the criterion being evaluated.
            criterion_description: Description of what a good score looks like.
            project_context: Dict with project_type, stage, country.

        Returns:
            Dict with score (0-100), reasoning, strengths, weaknesses, recommendation.
        """
        if not document_text or not document_text.strip():
            return DEFAULT_ASSESSMENT.copy()

        if not self.api_key:
            logger.warning("ai_gateway_key_not_set", criterion=criterion_name)
            return DEFAULT_ASSESSMENT.copy()

        prompt = self._build_prompt(
            document_text[:8000],
            criterion_name,
            criterion_description,
            project_context,
        )

        for attempt in range(2):
            try:
                return self._call_gateway(prompt, project_context)
            except Exception as e:
                logger.warning(
                    "ai_scorer_attempt_failed",
                    attempt=attempt + 1,
                    criterion=criterion_name,
                    error=str(e),
                )
                if attempt == 1:
                    logger.error(
                        "ai_scorer_failed",
                        criterion=criterion_name,
                        error=str(e),
                    )
                    return DEFAULT_ASSESSMENT.copy()

        return DEFAULT_ASSESSMENT.copy()

    def _build_prompt(
        self,
        text: str,
        criterion_name: str,
        criterion_description: str,
        project_context: dict,
    ) -> str:
        project_type = project_context.get("project_type", "alternative investment")
        stage = project_context.get("stage", "development")
        country = project_context.get("country", "unknown")

        return f"""You are evaluating documentation for a {project_type} asset in {country} (stage: {stage}).

Criterion: {criterion_name}
Expected: {criterion_description}

Score the document quality from 0-100 based on:
- Completeness: Does it cover all expected sections for this criterion?
- Specificity: Are numbers, dates, and details concrete rather than vague?
- Credibility: Are sources cited? Is the methodology sound?
- Recency: Is the information current and relevant?

Document text:
{text}

Respond ONLY with valid JSON (no markdown, no extra text):
{{
    "score": <integer 0-100>,
    "reasoning": "<2-3 sentence assessment>",
    "strengths": ["<strength1>", "<strength2>"],
    "weaknesses": ["<weakness1>", "<weakness2>"],
    "recommendation": "<specific action to improve this criterion>"
}}"""

    def _call_gateway(self, prompt: str, project_context: dict) -> dict:
        """Make sync HTTP call to AI Gateway."""
        start = time.time()
        response = httpx.post(
            f"{self.gateway_url}/v1/completions",
            json={
                "messages": [{"role": "user", "content": prompt}],
                "task_type": "analysis",
                "temperature": 0.3,
                "max_tokens": 1024,
                "org_id": project_context.get("org_id", "system"),
                "user_id": project_context.get("user_id", "system"),
            },
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            timeout=self.timeout,
        )
        response.raise_for_status()
        elapsed_ms = int((time.time() - start) * 1000)

        data = response.json()
        content = data.get("content", "")

        # Parse JSON from response
        try:
            result = json.loads(content)
        except json.JSONDecodeError:
            # Try to extract JSON from markdown code blocks
            if "```" in content:
                json_str = content.split("```")[1]
                if json_str.startswith("json"):
                    json_str = json_str[4:]
                result = json.loads(json_str.strip())
            else:
                raise

        # Validate and normalize
        return {
            "score": max(0, min(100, int(result.get("score", 0)))),
            "reasoning": str(result.get("reasoning", "")),
            "strengths": list(result.get("strengths", [])),
            "weaknesses": list(result.get("weaknesses", [])),
            "recommendation": str(result.get("recommendation", "")),
            "model_used": data.get("model_used", "unknown"),
            "tokens_used": data.get("usage", {}).get("total_tokens", 0),
            "processing_time_ms": elapsed_ms,
        }
