"""Voice input API router — transcription + AI project data extraction."""

from __future__ import annotations

import time
from typing import Any

import redis.asyncio as aioredis
import structlog
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_permission
from app.core.database import get_db
from app.models.ai import AITaskLog
from app.models.enums import AIAgentType, AITaskStatus
from app.modules.voice_input import service
from app.schemas.auth import CurrentUser
from app.services.ai_budget import enforce_ai_budget
from app.services.response_cache import get_redis

logger = structlog.get_logger()

router = APIRouter(prefix="/voice", tags=["voice-input"])

_ALLOWED_AUDIO_TYPES = {
    "audio/mpeg",
    "audio/mp3",
    "audio/wav",
    "audio/x-wav",
    "audio/mp4",
    "audio/m4a",
    "audio/x-m4a",
    "audio/ogg",
    "audio/webm",
}
_MAX_BYTES = 25 * 1024 * 1024  # 25 MB (Whisper limit)
_VOICE_RATE_LIMIT = 10  # max transcriptions per org per hour
_VOICE_RATE_WINDOW = 3600  # 1 hour sliding window


class TranscriptRequest(BaseModel):
    transcript: str


async def _check_voice_rate_limit(
    current_user: CurrentUser = Depends(require_permission("view", "project")),
) -> CurrentUser:
    """Enforce 10 Whisper calls per hour per org. Fails open on Redis errors."""
    try:
        r: aioredis.Redis = await get_redis()
        key = f"voice_rl:{current_user.org_id}"
        now = time.time()
        pipe = r.pipeline()
        pipe.zadd(key, {str(now): now})
        pipe.zremrangebyscore(key, 0, now - _VOICE_RATE_WINDOW)
        pipe.zcard(key)
        pipe.expire(key, _VOICE_RATE_WINDOW + 1)
        results = await pipe.execute()
        count: int = results[2]
        if count > _VOICE_RATE_LIMIT:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Voice transcription rate limit: 10 per hour per organisation.",
            )
    except HTTPException:
        raise
    except Exception:
        pass  # fail open on Redis errors
    return current_user


@router.post("/transcribe")
async def transcribe(
    file: UploadFile = File(...),
    current_user: CurrentUser = Depends(_check_voice_rate_limit),
    _: None = Depends(enforce_ai_budget),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    if file.content_type not in _ALLOWED_AUDIO_TYPES:
        raise HTTPException(status_code=415, detail=f"Unsupported audio type: {file.content_type}")

    audio_bytes = await file.read()
    if len(audio_bytes) > _MAX_BYTES:
        raise HTTPException(status_code=413, detail="Audio file exceeds 25 MB limit")

    t0 = time.monotonic()
    try:
        transcript = await service.transcribe_audio(
            audio_bytes, file.filename or "audio.mp3", file.content_type
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    duration_ms = round((time.monotonic() - t0) * 1000)

    # Rough cost: $0.006/min; estimate ~1 min of audio per MB
    file_mb = len(audio_bytes) / (1024 * 1024)
    cost_usd = round(file_mb * 0.006, 6)

    log = AITaskLog(
        org_id=current_user.org_id,
        agent_type=AIAgentType.VOICE_TRANSCRIPTION,
        entity_type="voice_input",
        status=AITaskStatus.COMPLETED,
        model_used="whisper-1",
        tokens_input=0,
        tokens_output=len(transcript),
        cost_usd=cost_usd,
        triggered_by=current_user.user_id,
        output_data={"transcript": transcript, "duration_ms": duration_ms},
    )
    db.add(log)
    await db.commit()
    await db.refresh(log)

    logger.info("voice.transcribed_and_logged", result_id=str(log.id), duration_ms=duration_ms)
    return {"transcript": transcript, "result_id": str(log.id)}


@router.post("/extract")
async def extract(
    body: TranscriptRequest,
    current_user: CurrentUser = Depends(require_permission("view", "project")),
    _: None = Depends(enforce_ai_budget),
) -> dict[str, Any]:
    try:
        extracted = await service.extract_project_data(body.transcript)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return {"extracted": extracted}


@router.post("/process")
async def process(
    file: UploadFile = File(...),
    current_user: CurrentUser = Depends(_check_voice_rate_limit),
    _: None = Depends(enforce_ai_budget),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    if file.content_type not in _ALLOWED_AUDIO_TYPES:
        raise HTTPException(status_code=415, detail=f"Unsupported audio type: {file.content_type}")

    audio_bytes = await file.read()
    if len(audio_bytes) > _MAX_BYTES:
        raise HTTPException(status_code=413, detail="Audio file exceeds 25 MB limit")

    t0 = time.monotonic()
    try:
        result = await service.process_audio(
            audio_bytes, file.filename or "audio.mp3", file.content_type
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    duration_ms = round((time.monotonic() - t0) * 1000)

    file_mb = len(audio_bytes) / (1024 * 1024)
    cost_usd = round(file_mb * 0.006, 6)

    log = AITaskLog(
        org_id=current_user.org_id,
        agent_type=AIAgentType.VOICE_TRANSCRIPTION,
        entity_type="voice_input",
        status=AITaskStatus.COMPLETED,
        model_used="whisper-1",
        tokens_input=0,
        tokens_output=len(result.get("transcript", "")),
        cost_usd=cost_usd,
        triggered_by=current_user.user_id,
        output_data={**result, "duration_ms": duration_ms},
    )
    db.add(log)
    await db.commit()
    await db.refresh(log)

    return {**result, "result_id": str(log.id)}
