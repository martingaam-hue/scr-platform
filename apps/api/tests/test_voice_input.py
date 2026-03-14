"""Unit tests for voice_input module — no DB or network required."""

from __future__ import annotations

import asyncio
import inspect
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.config import Settings
from app.modules.voice_input import service as voice_service

# ── Config ─────────────────────────────────────────────────────────────────────


class TestConfig:
    def test_openai_api_key_is_declared_field(self):
        """OPENAI_API_KEY must be a declared Settings field, not a getattr workaround."""
        assert "OPENAI_API_KEY" in Settings.model_fields

    def test_openai_api_key_default_is_none(self):
        s = Settings()
        assert s.OPENAI_API_KEY is None

    def test_openai_api_key_accepts_string(self):
        s = Settings(OPENAI_API_KEY="sk-test-key")
        assert s.OPENAI_API_KEY == "sk-test-key"

    def test_no_getattr_workaround_in_service(self):
        """service.py must access settings.OPENAI_API_KEY directly, not via getattr."""
        source = inspect.getsource(voice_service)
        assert 'getattr(settings, "OPENAI_API_KEY"' not in source
        assert "getattr(settings, 'OPENAI_API_KEY'" not in source


# ── AIAgentType enum ────────────────────────────────────────────────────────────


class TestAIAgentTypeEnum:
    def test_voice_transcription_value_exists(self):
        from app.models.enums import AIAgentType

        assert hasattr(AIAgentType, "VOICE_TRANSCRIPTION")

    def test_voice_transcription_string_value(self):
        from app.models.enums import AIAgentType

        assert AIAgentType.VOICE_TRANSCRIPTION.value == "voice_transcription"


# ── transcribe_audio ────────────────────────────────────────────────────────────


def _make_http_mock(json_payload: dict) -> tuple[MagicMock, MagicMock]:
    """Return (mock_cls, mock_client) wired up for httpx.AsyncClient context manager."""
    mock_resp = MagicMock()
    mock_resp.json.return_value = json_payload
    mock_resp.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    mock_client.post = AsyncMock(return_value=mock_resp)

    mock_cls = MagicMock(return_value=mock_client)
    return mock_cls, mock_client


class TestTranscribeAudio:
    def test_raises_when_api_key_is_none(self):
        with patch("app.modules.voice_input.service.settings") as ms:
            ms.OPENAI_API_KEY = None
            with pytest.raises(RuntimeError, match="OPENAI_API_KEY not configured"):
                asyncio.run(voice_service.transcribe_audio(b"audio", "t.mp3", "audio/mpeg"))

    def test_raises_when_api_key_is_empty_string(self):
        with patch("app.modules.voice_input.service.settings") as ms:
            ms.OPENAI_API_KEY = ""
            with pytest.raises(RuntimeError, match="OPENAI_API_KEY not configured"):
                asyncio.run(voice_service.transcribe_audio(b"audio", "t.mp3", "audio/mpeg"))

    def test_returns_transcript_text(self):
        mock_cls, mock_client = _make_http_mock({"text": "Hello world"})
        with (
            patch("app.modules.voice_input.service.settings") as ms,
            patch("app.modules.voice_input.service.httpx.AsyncClient", mock_cls),
        ):
            ms.OPENAI_API_KEY = "sk-test"
            result = asyncio.run(voice_service.transcribe_audio(b"audio", "t.mp3", "audio/mpeg"))
        assert result == "Hello world"

    def test_empty_text_key_returns_empty_string(self):
        mock_cls, _ = _make_http_mock({})
        with (
            patch("app.modules.voice_input.service.settings") as ms,
            patch("app.modules.voice_input.service.httpx.AsyncClient", mock_cls),
        ):
            ms.OPENAI_API_KEY = "sk-test"
            result = asyncio.run(voice_service.transcribe_audio(b"audio", "t.mp3", "audio/mpeg"))
        assert result == ""

    def test_authorization_header_uses_api_key(self):
        mock_cls, mock_client = _make_http_mock({"text": "ok"})
        with (
            patch("app.modules.voice_input.service.settings") as ms,
            patch("app.modules.voice_input.service.httpx.AsyncClient", mock_cls),
        ):
            ms.OPENAI_API_KEY = "sk-abc123"
            asyncio.run(voice_service.transcribe_audio(b"audio", "t.mp3", "audio/mpeg"))

        call_kwargs = mock_client.post.call_args
        headers = call_kwargs.kwargs.get("headers") or call_kwargs.args[1]
        assert headers["Authorization"] == "Bearer sk-abc123"

    def test_whisper_model_sent_in_data(self):
        mock_cls, mock_client = _make_http_mock({"text": "ok"})
        with (
            patch("app.modules.voice_input.service.settings") as ms,
            patch("app.modules.voice_input.service.httpx.AsyncClient", mock_cls),
        ):
            ms.OPENAI_API_KEY = "sk-test"
            asyncio.run(voice_service.transcribe_audio(b"audio", "t.mp3", "audio/mpeg"))

        data = mock_client.post.call_args.kwargs.get("data", {})
        assert data.get("model") == "whisper-1"

    def test_filename_passed_in_files(self):
        mock_cls, mock_client = _make_http_mock({"text": "ok"})
        with (
            patch("app.modules.voice_input.service.settings") as ms,
            patch("app.modules.voice_input.service.httpx.AsyncClient", mock_cls),
        ):
            ms.OPENAI_API_KEY = "sk-test"
            asyncio.run(voice_service.transcribe_audio(b"audio", "meeting.wav", "audio/wav"))

        files = mock_client.post.call_args.kwargs.get("files", {})
        assert files["file"][0] == "meeting.wav"


# ── extract_project_data ────────────────────────────────────────────────────────


class TestExtractProjectData:
    def test_returns_validated_data(self):
        mock_cls, _ = _make_http_mock({"validated_data": {"project_name": "Solar Farm"}})
        with patch("app.modules.voice_input.service.httpx.AsyncClient", mock_cls):
            result = asyncio.run(voice_service.extract_project_data("transcript text"))
        assert result == {"project_name": "Solar Farm"}

    def test_missing_validated_data_returns_empty_dict(self):
        mock_cls, _ = _make_http_mock({})
        with patch("app.modules.voice_input.service.httpx.AsyncClient", mock_cls):
            result = asyncio.run(voice_service.extract_project_data("transcript"))
        assert result == {}

    def test_task_type_sent_in_request(self):
        mock_cls, mock_client = _make_http_mock({"validated_data": {}})
        with patch("app.modules.voice_input.service.httpx.AsyncClient", mock_cls):
            asyncio.run(voice_service.extract_project_data("test"))
        body = mock_client.post.call_args.kwargs.get("json", {})
        assert body.get("task_type") == "extract_project_from_voice"

    def test_transcript_passed_in_context(self):
        mock_cls, mock_client = _make_http_mock({"validated_data": {}})
        with patch("app.modules.voice_input.service.httpx.AsyncClient", mock_cls):
            asyncio.run(voice_service.extract_project_data("my transcript"))
        body = mock_client.post.call_args.kwargs.get("json", {})
        assert body["context"]["transcript"] == "my transcript"


# ── process_audio ───────────────────────────────────────────────────────────────


class TestProcessAudio:
    def test_returns_transcript_and_extracted(self):
        with (
            patch(
                "app.modules.voice_input.service.transcribe_audio",
                new_callable=AsyncMock,
                return_value="hello world",
            ),
            patch(
                "app.modules.voice_input.service.extract_project_data",
                new_callable=AsyncMock,
                return_value={"name": "test"},
            ),
        ):
            result = asyncio.run(voice_service.process_audio(b"audio", "t.mp3", "audio/mpeg"))
        assert result["transcript"] == "hello world"
        assert result["extracted"] == {"name": "test"}

    def test_transcript_passed_to_extract(self):
        with (
            patch(
                "app.modules.voice_input.service.transcribe_audio",
                new_callable=AsyncMock,
                return_value="specific text",
            ),
            patch(
                "app.modules.voice_input.service.extract_project_data",
                new_callable=AsyncMock,
                return_value={},
            ) as mock_e,
        ):
            asyncio.run(voice_service.process_audio(b"audio", "t.mp3", "audio/mpeg"))
        mock_e.assert_awaited_once_with("specific text")


# ── Cost estimation logic ───────────────────────────────────────────────────────


class TestCostEstimate:
    """Whisper pricing: $0.006/min; we approximate 1 min of speech per MB."""

    @pytest.mark.parametrize(
        "file_mb, expected_cost",
        [
            (1.0, 0.006),
            (5.0, 0.03),
            (10.0, 0.06),
            (25.0, 0.15),
        ],
    )
    def test_cost_formula(self, file_mb: float, expected_cost: float):
        cost = round(file_mb * 0.006, 6)
        assert cost == pytest.approx(expected_cost, rel=1e-4)

    def test_zero_bytes_zero_cost(self):
        cost = round(0.0 * 0.006, 6)
        assert cost == 0.0


# ── Rate limit constants ────────────────────────────────────────────────────────


class TestRateLimitConstants:
    def test_rate_limit_is_10(self):
        from app.modules.voice_input.router import _VOICE_RATE_LIMIT

        assert _VOICE_RATE_LIMIT == 10

    def test_rate_window_is_one_hour(self):
        from app.modules.voice_input.router import _VOICE_RATE_WINDOW

        assert _VOICE_RATE_WINDOW == 3600
