from unittest.mock import AsyncMock, patch

import pytest

from app.pipeline.tts import TextToSpeech


@pytest.fixture
def tts():
    with patch("app.pipeline.tts.texttospeech.TextToSpeechClient"):
        return TextToSpeech()


@pytest.mark.asyncio
async def test_synthesize_returns_base64_audio(tts):
    """Mock _synthesize_google to return 'base64_audio_data', verify synthesize() returns it."""
    with patch.object(tts, "_synthesize_google", new_callable=AsyncMock) as mock_synth:
        mock_synth.return_value = "base64_audio_data"
        result = await tts.synthesize("Xin chào", "vi")

    assert result == "base64_audio_data"
    mock_synth.assert_awaited_once_with("Xin chào", "vi")


@pytest.mark.asyncio
async def test_synthesize_empty_text_returns_empty(tts):
    """Verify empty text returns empty string without calling Google."""
    result = await tts.synthesize("", "vi")
    assert result == ""
