"""Voice input API router — transcription + AI project data extraction."""

from __future__ import annotations

from typing import Any

import structlog
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_permission
from app.core.database import get_db
from app.modules.voice_input import service
from app.schemas.auth import CurrentUser

logger = structlog.get_logger()

router = APIRouter(prefix="/voice", tags=["voice-input"])

_ALLOWED_AUDIO_TYPES = {
    "audio/mpeg", "audio/mp3", "audio/wav", "audio/x-wav",
    "audio/mp4", "audio/m4a", "audio/x-m4a", "audio/ogg", "audio/webm",
}
_MAX_BYTES = 25 * 1024 * 1024  # 25 MB (Whisper limit)


class TranscriptRequest(BaseModel):
    transcript: str


@router.post("/transcribe")
async def transcribe(
    file: UploadFile = File(...),
    current_user: CurrentUser = Depends(require_permission("view", "project")),
) -> dict[str, str]:
    if file.content_type not in _ALLOWED_AUDIO_TYPES:
        raise HTTPException(status_code=415, detail=f"Unsupported audio type: {file.content_type}")

    audio_bytes = await file.read()
    if len(audio_bytes) > _MAX_BYTES:
        raise HTTPException(status_code=413, detail="Audio file exceeds 25 MB limit")

    try:
        transcript = await service.transcribe_audio(audio_bytes, file.filename or "audio.mp3", file.content_type)
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    return {"transcript": transcript}


@router.post("/extract")
async def extract(
    body: TranscriptRequest,
    current_user: CurrentUser = Depends(require_permission("view", "project")),
) -> dict[str, Any]:
    try:
        extracted = await service.extract_project_data(body.transcript)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc))
    return {"extracted": extracted}


@router.post("/process")
async def process(
    file: UploadFile = File(...),
    current_user: CurrentUser = Depends(require_permission("view", "project")),
) -> dict[str, Any]:
    if file.content_type not in _ALLOWED_AUDIO_TYPES:
        raise HTTPException(status_code=415, detail=f"Unsupported audio type: {file.content_type}")

    audio_bytes = await file.read()
    if len(audio_bytes) > _MAX_BYTES:
        raise HTTPException(status_code=413, detail="Audio file exceeds 25 MB limit")

    try:
        result = await service.process_audio(audio_bytes, file.filename or "audio.mp3", file.content_type)
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    return result
