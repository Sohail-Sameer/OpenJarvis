"""Tests for Groq Whisper API speech backend."""

from unittest.mock import MagicMock, patch

import pytest

from openjarvis.core.registry import SpeechRegistry
from openjarvis.speech._stubs import TranscriptionResult
from openjarvis.speech.groq_whisper import GroqWhisperBackend


@pytest.fixture(autouse=True)
def _register_groq_whisper():
    """Re-register after any registry clear."""
    if not SpeechRegistry.contains("groq"):
        SpeechRegistry.register_value("groq", GroqWhisperBackend)


def test_groq_whisper_registers():
    assert SpeechRegistry.contains("groq")


def test_groq_whisper_uses_groq_base_url_by_default():
    with patch("openjarvis.speech.groq_whisper.OpenAI") as mock_openai:
        GroqWhisperBackend(api_key="test-key")

        mock_openai.assert_called_once_with(
            api_key="test-key", base_url="https://api.groq.com/openai/v1"
        )


def test_groq_whisper_transcribe():
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = "Hello from Groq"
    mock_response.language = "en"
    mock_response.duration = 1.5
    mock_client.audio.transcriptions.create.return_value = mock_response

    with patch("openjarvis.speech.groq_whisper.OpenAI", return_value=mock_client):
        backend = GroqWhisperBackend(api_key="test-key")
        result = backend.transcribe(b"fake audio", format="webm")

        assert isinstance(result, TranscriptionResult)
        assert result.text == "Hello from Groq"
        assert result.language == "en"
        call_kwargs = mock_client.audio.transcriptions.create.call_args.kwargs
        assert call_kwargs["model"] == "whisper-large-v3-turbo"


def test_groq_whisper_health():
    with patch("openjarvis.speech.groq_whisper.OpenAI"):
        backend = GroqWhisperBackend(api_key="test-key")
        assert backend.health() is True


def test_groq_whisper_health_no_key():
    with patch("openjarvis.speech.groq_whisper.OpenAI"):
        backend = GroqWhisperBackend.__new__(GroqWhisperBackend)
        backend._client = None
        backend._api_key = ""
        assert backend.health() is False
