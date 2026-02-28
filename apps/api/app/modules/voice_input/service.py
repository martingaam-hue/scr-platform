"""Voice-to-text service — transcription + AI structured extraction."""

from __future__ import annotations

from typing import Any

import httpx
import structlog

from app.core.config import settings

logger = structlog.get_logger()


async def transcribe_audio(audio_bytes: bytes, filename: str, content_type: str) -> str:
    """Transcribe audio via OpenAI Whisper API."""
    if not getattr(settings, "OPENAI_API_KEY", None):
        raise RuntimeError("OPENAI_API_KEY not configured")

    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(
            "https://api.openai.com/v1/audio/transcriptions",
            headers={"Authorization": f"Bearer {settings.OPENAI_API_KEY}"},
            files={"file": (filename, audio_bytes, content_type)},
            data={"model": "whisper-1", "language": "en"},
        )
        resp.raise_for_status()

    transcript = resp.json().get("text", "")
    logger.info("voice.transcribed", chars=len(transcript))
    return transcript


async def extract_project_data(transcript: str) -> dict[str, Any]:
    """Use AI to extract structured project data from a spoken transcript."""
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(
            f"{settings.AI_GATEWAY_URL}/v1/completions",
            headers={"X-API-Key": settings.AI_GATEWAY_API_KEY},
            json={
                "task_type": "extract_project_from_voice",
                "context": {"transcript": transcript},
                "model": "claude-sonnet-4-20250514",
            },
        )
        resp.raise_for_status()
        return resp.json().get("validated_data", {})


async def process_audio(audio_bytes: bytes, filename: str, content_type: str) -> dict[str, Any]:
    """Combined: audio → transcript → structured data."""
    transcript = await transcribe_audio(audio_bytes, filename, content_type)
    extracted = await extract_project_data(transcript)
    return {"transcript": transcript, "extracted": extracted}
