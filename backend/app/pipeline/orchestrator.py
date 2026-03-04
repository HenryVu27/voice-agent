import time
import logging
from dataclasses import dataclass

from app.pipeline.stt import SpeechToText
from app.pipeline.translator import Translator
from app.pipeline.tts import TextToSpeech

logger = logging.getLogger(__name__)


@dataclass
class PipelineResult:
    original_text: str
    translated_text: str
    audio_base64: str
    latency_ms: float
    stt_ms: float = 0
    translation_ms: float = 0
    tts_ms: float = 0


class TranslationPipeline:
    def __init__(self, stt: SpeechToText, translator: Translator, tts: TextToSpeech):
        self.stt = stt
        self.translator = translator
        self.tts = tts

    async def process(self, audio_base64: str, source_lang: str, target_lang: str) -> PipelineResult:
        pipeline_start = time.time()

        # Stage 1: STT
        stt_start = time.time()
        original_text = await self.stt.transcribe(audio_base64, language=source_lang)
        stt_ms = (time.time() - stt_start) * 1000

        if not original_text:
            return PipelineResult(
                original_text="",
                translated_text="",
                audio_base64="",
                latency_ms=(time.time() - pipeline_start) * 1000,
                stt_ms=stt_ms,
            )

        # Stage 2: Translation
        translate_start = time.time()
        translated_text = await self.translator.translate(
            original_text, source_lang=source_lang, target_lang=target_lang
        )
        translation_ms = (time.time() - translate_start) * 1000

        # Stage 3: TTS
        tts_start = time.time()
        audio_b64 = await self.tts.synthesize(translated_text, language=target_lang)
        tts_ms = (time.time() - tts_start) * 1000

        total_ms = (time.time() - pipeline_start) * 1000
        logger.info(
            f"Pipeline complete in {total_ms:.0f}ms "
            f"(STT: {stt_ms:.0f}ms, MT: {translation_ms:.0f}ms, TTS: {tts_ms:.0f}ms)"
        )

        return PipelineResult(
            original_text=original_text,
            translated_text=translated_text,
            audio_base64=audio_b64,
            latency_ms=total_ms,
            stt_ms=stt_ms,
            translation_ms=translation_ms,
            tts_ms=tts_ms,
        )
