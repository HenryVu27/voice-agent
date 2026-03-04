import base64
import time
import logging

from google.cloud import texttospeech

logger = logging.getLogger(__name__)

VOICE_MAP = {
    "vi": texttospeech.VoiceSelectionParams(
        language_code="vi-VN",
        name="vi-VN-Neural2-A",
    ),
    "ru": texttospeech.VoiceSelectionParams(
        language_code="ru-RU",
        name="ru-RU-Neural2-A",
    ),
    "en": texttospeech.VoiceSelectionParams(
        language_code="en-US",
        name="en-US-Neural2-A",
    ),
}


class TextToSpeech:
    def __init__(self):
        self._client = texttospeech.TextToSpeechClient()
        self._audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3,
            speaking_rate=1.0,
        )

    async def synthesize(self, text: str, language: str) -> str:
        if not text.strip():
            return ""
        start = time.time()
        audio_b64 = await self._synthesize_google(text, language)
        elapsed_ms = (time.time() - start) * 1000
        logger.info(f"TTS completed in {elapsed_ms:.0f}ms ({language})")
        return audio_b64

    async def _synthesize_google(self, text: str, language: str) -> str:
        voice = VOICE_MAP.get(language, VOICE_MAP["en"])
        synthesis_input = texttospeech.SynthesisInput(text=text)
        response = self._client.synthesize_speech(
            input=synthesis_input,
            voice=voice,
            audio_config=self._audio_config,
        )
        return base64.b64encode(response.audio_content).decode("utf-8")
