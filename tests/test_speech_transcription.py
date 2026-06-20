"""Tests for speech transcription service and API."""

from __future__ import annotations

import io
from unittest.mock import MagicMock, patch

import pytest


def test_transcribe_endpoint_requires_audio(client):
    response = client.post("/api/v1/chat/transcribe")
    assert response.status_code == 422
    body = response.get_json()
    assert body["error"]["code"] == "validation_error"


def test_transcribe_endpoint_rejects_empty_file(client):
    data = {"audio": (io.BytesIO(b""), "recording.webm")}
    response = client.post(
        "/api/v1/chat/transcribe",
        data=data,
        content_type="multipart/form-data",
    )
    assert response.status_code == 422
    body = response.get_json()
    assert body["error"]["code"] == "validation_error"


@patch("app.services.speech_transcription_service.transcribe_audio", return_value="hello world")
def test_transcribe_endpoint_returns_text(mock_transcribe, client):
    data = {"audio": (io.BytesIO(b"fake-audio"), "recording.webm")}
    response = client.post(
        "/api/v1/chat/transcribe",
        data=data,
        content_type="multipart/form-data",
    )
    assert response.status_code == 200
    body = response.get_json()
    assert body["data"]["text"] == "hello world"
    mock_transcribe.assert_called_once()


def test_transcribe_audio_uses_gemini_when_key_configured(monkeypatch: pytest.MonkeyPatch):
    from app.services import speech_transcription_service

    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setenv("LLM_PROVIDER", "anthropic")

    with patch.object(
        speech_transcription_service,
        "_transcribe_gemini",
        return_value="from gemini",
    ) as mock_gemini:
        text = speech_transcription_service.transcribe_audio(
            audio_bytes=b"audio",
            mime_type="audio/webm",
        )

    assert text == "from gemini"
    mock_gemini.assert_called_once_with(audio_bytes=b"audio", mime_type="audio/webm")


def test_transcribe_audio_requires_configuration(monkeypatch: pytest.MonkeyPatch):
    from app.services import speech_transcription_service

    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setenv("LLM_PROVIDER", "anthropic")

    with pytest.raises(RuntimeError, match="Voice input is not configured"):
        speech_transcription_service.transcribe_audio(
            audio_bytes=b"audio",
            mime_type="audio/webm",
        )


def test_normalize_mime_type_detects_webm():
    from app.services.speech_transcription_service import _normalize_mime_type

    assert _normalize_mime_type("application/octet-stream", b"\x1aE\xdf\xa3") == "audio/webm"
