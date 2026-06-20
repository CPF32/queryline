"""Transcribe short microphone recordings for chat voice input."""

from __future__ import annotations

import base64
import json
import os
import shutil
import subprocess
import urllib.error
import urllib.request


def _normalize_mime_type(mime_type: str, audio_bytes: bytes) -> str:
    cleaned = (mime_type or "").split(";")[0].strip().lower()
    if cleaned and cleaned != "application/octet-stream":
        return cleaned
    if audio_bytes[:4] == b"RIFF":
        return "audio/wav"
    if audio_bytes[:4] == b"\x1aE\xdf\xa3":
        return "audio/webm"
    if len(audio_bytes) >= 8 and audio_bytes[4:8] == b"ftyp":
        return "audio/mp4"
    return "audio/webm"


def _transcribe_gemini(*, audio_bytes: bytes, mime_type: str) -> str:
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not configured.")

    from google import genai
    from google.genai import types

    model = os.environ.get("GEMINI_MODEL", "gemini-2.0-flash-lite")
    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model=model,
        contents=[
            types.Content(
                role="user",
                parts=[
                    types.Part.from_bytes(
                        data=audio_bytes,
                        mime_type=_normalize_mime_type(mime_type, audio_bytes),
                    ),
                    types.Part.from_text(
                        text=(
                            "Transcribe the spoken words in this audio. "
                            "Return only the transcription text with no labels or commentary."
                        ),
                    ),
                ],
            )
        ],
    )
    text = (response.text or "").strip()
    if not text:
        raise RuntimeError("No speech was detected in the recording.")
    return text


def _convert_to_wav(audio_bytes: bytes, mime_type: str) -> bytes:
    normalized = _normalize_mime_type(mime_type, audio_bytes)
    if normalized == "audio/wav" or audio_bytes[:4] == b"RIFF":
        return audio_bytes

    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError(
            "Local voice transcription with Ollama requires ffmpeg to convert browser audio. "
            "Install ffmpeg or add GEMINI_API_KEY for cloud transcription."
        )

    completed = subprocess.run(
        [
            ffmpeg,
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            "pipe:0",
            "-ar",
            "16000",
            "-ac",
            "1",
            "-f",
            "wav",
            "pipe:1",
        ],
        input=audio_bytes,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0 or not completed.stdout:
        detail = completed.stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(
            detail or "Could not convert audio for local transcription."
        )
    return completed.stdout


def _transcribe_ollama(*, audio_bytes: bytes, mime_type: str) -> str:
    base_url = os.environ.get("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/")
    model = os.environ.get("OLLAMA_WHISPER_MODEL", "dimavz/whisper-tiny")
    wav_bytes = _convert_to_wav(audio_bytes, mime_type)
    payload = {
        "model": model,
        "stream": False,
        "messages": [
            {
                "role": "user",
                "content": "transcribe",
                "images": [base64.b64encode(wav_bytes).decode("ascii")],
            }
        ],
    }
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        f"{base_url}/api/chat",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(
            f"Ollama transcription failed ({exc.code}): {detail or exc.reason}"
        ) from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(
            f"Cannot reach Ollama at {base_url}. Run `ollama serve` and pull a Whisper model "
            f"(`ollama pull {model}`)."
        ) from exc

    message = data.get("message") or {}
    text = (message.get("content") or "").strip()
    if not text:
        raise RuntimeError("No speech was detected in the recording.")
    return text


def transcribe_audio(*, audio_bytes: bytes, mime_type: str) -> str:
    """Return spoken text from a short audio clip."""
    if not audio_bytes:
        raise RuntimeError("Recording was empty.")

    gemini_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if gemini_key:
        return _transcribe_gemini(audio_bytes=audio_bytes, mime_type=mime_type)

    provider = os.environ.get("LLM_PROVIDER", "anthropic").strip().lower()
    if provider == "ollama":
        return _transcribe_ollama(audio_bytes=audio_bytes, mime_type=mime_type)

    raise RuntimeError(
        "Voice input is not configured. Add GEMINI_API_KEY to your environment, "
        "or set LLM_PROVIDER=ollama with a Whisper model "
        "(for example: ollama pull dimavz/whisper-tiny)."
    )
