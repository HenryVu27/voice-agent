"""
Manual E2E smoke test. Run with real API keys.
Verifies the full pipeline: audio -> STT -> translate -> TTS -> audio.

Usage: RUN_E2E_TESTS=1 python -m pytest tests/test_e2e.py -v -s
"""
import pytest
import base64
import os

pytestmark = pytest.mark.skipif(
    not os.getenv("RUN_E2E_TESTS"), reason="Set RUN_E2E_TESTS=1 to run"
)


@pytest.mark.asyncio
async def test_full_pipeline_with_real_apis():
    """Smoke test: send a short audio clip through the full pipeline."""
    from app.config import get_settings
    from app.pipeline.stt import SpeechToText
    from app.pipeline.translator import Translator
    from app.pipeline.tts import TextToSpeech
    from app.pipeline.orchestrator import TranslationPipeline

    settings = get_settings()
    pipeline = TranslationPipeline(
        stt=SpeechToText(api_key=settings.deepgram_api_key),
        translator=Translator(api_key=settings.deepl_api_key),
        tts=TextToSpeech(),
    )

    test_audio_path = os.path.join(os.path.dirname(__file__), "fixtures", "test_audio.wav")
    if not os.path.exists(test_audio_path):
        pytest.skip("No test audio fixture at tests/fixtures/test_audio.wav")

    with open(test_audio_path, "rb") as f:
        audio_b64 = base64.b64encode(f.read()).decode()

    result = await pipeline.process(
        audio_base64=audio_b64,
        source_lang="vi",
        target_lang="ru",
    )

    print(f"\nOriginal: {result.original_text}")
    print(f"Translated: {result.translated_text}")
    print(f"Audio length: {len(result.audio_base64)} chars")
    print(f"Total latency: {result.latency_ms:.0f}ms")
    print(f"  STT: {result.stt_ms:.0f}ms")
    print(f"  Translation: {result.translation_ms:.0f}ms")
    print(f"  TTS: {result.tts_ms:.0f}ms")

    assert result.original_text, "STT should produce text"
    assert result.translated_text, "Translation should produce text"
    assert result.audio_base64, "TTS should produce audio"
    assert result.latency_ms < 5000, "Pipeline should complete under 5s"
