import pytest
from unittest.mock import AsyncMock, MagicMock
from app.pipeline.orchestrator import TranslationPipeline


@pytest.fixture
def mock_pipeline():
    stt = MagicMock()
    stt.transcribe = AsyncMock(return_value="xin chào")

    translator = MagicMock()
    translator.translate = AsyncMock(return_value="Привет")

    tts = MagicMock()
    tts.synthesize = AsyncMock(return_value="base64_audio_data")

    return TranslationPipeline(stt=stt, translator=translator, tts=tts)


@pytest.mark.asyncio
async def test_full_pipeline(mock_pipeline):
    result = await mock_pipeline.process(
        audio_base64="fake_audio",
        source_lang="vi",
        target_lang="ru",
    )
    assert result.original_text == "xin chào"
    assert result.translated_text == "Привет"
    assert result.audio_base64 == "base64_audio_data"
    assert result.latency_ms > 0


@pytest.mark.asyncio
async def test_pipeline_empty_transcription(mock_pipeline):
    mock_pipeline.stt.transcribe = AsyncMock(return_value="")
    result = await mock_pipeline.process(
        audio_base64="fake_audio",
        source_lang="vi",
        target_lang="ru",
    )
    assert result.original_text == ""
    assert result.translated_text == ""
    assert result.audio_base64 == ""
    mock_pipeline.translator.translate.assert_not_called()
    mock_pipeline.tts.synthesize.assert_not_called()
