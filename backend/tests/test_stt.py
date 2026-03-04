import base64
from unittest.mock import AsyncMock, patch

import pytest

from app.pipeline.stt import SpeechToText


@pytest.fixture
def stt():
    return SpeechToText(api_key="test-key")


@pytest.mark.asyncio
async def test_transcribe_returns_text(stt):
    """Mock _transcribe_with_deepgram to return 'xin chao', verify transcribe() returns it."""
    audio_b64 = base64.b64encode(b"fake-audio-data").decode()

    with patch.object(stt, "_transcribe_with_deepgram", new_callable=AsyncMock) as mock_dg:
        mock_dg.return_value = "xin chao"
        result = await stt.transcribe(audio_b64, "vi")

    assert result == "xin chao"
    mock_dg.assert_awaited_once_with(audio_b64, "vi")


@pytest.mark.asyncio
async def test_transcribe_empty_audio_returns_empty(stt):
    """Mock _transcribe_with_deepgram to return '', verify empty result."""
    audio_b64 = base64.b64encode(b"fake-audio-data").decode()

    with patch.object(stt, "_transcribe_with_deepgram", new_callable=AsyncMock) as mock_dg:
        mock_dg.return_value = ""
        result = await stt.transcribe(audio_b64, "vi")

    assert result == ""
    mock_dg.assert_awaited_once_with(audio_b64, "vi")
