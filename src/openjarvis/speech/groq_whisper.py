"""Groq Whisper API speech-to-text backend (cloud).

Groq hosts Whisper behind an OpenAI-compatible ``/v1/audio/transcriptions``
endpoint, so this reuses the ``openai`` Python client pointed at Groq's base
URL rather than hand-rolling a new HTTP client. Groq's inference is
CPU/GPU-hosted and fast, which is the same shape as this project's other
cloud speech backend (``openai_whisper.py``) — see that file for the local
alternative (``faster_whisper.py``).
"""

from __future__ import annotations

import io
import os
from typing import List, Optional

from openjarvis.core.registry import SpeechRegistry
from openjarvis.speech._stubs import SpeechBackend, TranscriptionResult

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None  # type: ignore[assignment, misc]

_DEFAULT_BASE_URL = "https://api.groq.com/openai/v1"
_DEFAULT_MODEL = "whisper-large-v3-turbo"


@SpeechRegistry.register("groq")
class GroqWhisperBackend(SpeechBackend):
    """Cloud speech-to-text using Groq's hosted Whisper API."""

    backend_id = "groq"

    def __init__(
        self,
        api_key: Optional[str] = None,
        *,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
    ) -> None:
        self._api_key = api_key or os.environ.get("GROQ_API_KEY", "")
        self._base_url = (
            base_url or os.environ.get("GROQ_WHISPER_BASE_URL") or _DEFAULT_BASE_URL
        )
        self._model = model or os.environ.get("GROQ_WHISPER_MODEL", _DEFAULT_MODEL)
        self._client: Optional[OpenAI] = None
        if self._api_key and OpenAI is not None:
            self._client = OpenAI(api_key=self._api_key, base_url=self._base_url)

    def transcribe(
        self,
        audio: bytes,
        *,
        format: str = "wav",
        language: Optional[str] = None,
    ) -> TranscriptionResult:
        """Transcribe audio using Groq's Whisper API."""
        if self._client is None:
            raise RuntimeError("Groq client not initialized (missing API key?)")

        ext = format if not format.startswith(".") else format[1:]
        audio_file = io.BytesIO(audio)
        audio_file.name = f"audio.{ext}"

        kwargs: dict = {"model": self._model, "file": audio_file}
        if language:
            kwargs["language"] = language
        kwargs["response_format"] = "verbose_json"

        response = self._client.audio.transcriptions.create(**kwargs)

        return TranscriptionResult(
            text=getattr(response, "text", str(response)),
            language=getattr(response, "language", None),
            confidence=None,
            duration_seconds=getattr(response, "duration", 0.0),
            segments=[],
        )

    def health(self) -> bool:
        return self._client is not None and bool(self._api_key)

    def supported_formats(self) -> List[str]:
        return ["mp3", "mp4", "mpeg", "mpga", "m4a", "wav", "webm"]
