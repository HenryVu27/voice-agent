import base64
import time
import logging

from deepgram import AsyncDeepgramClient

logger = logging.getLogger(__name__)

LANGUAGE_MAP = {
    "vi": "vi",
    "ru": "ru",
    "en": "en-US",
}


class SpeechToText:
    def __init__(self, api_key: str):
        self.client = AsyncDeepgramClient(api_key=api_key)

    async def transcribe(self, audio_base64: str, language: str) -> str:
        if not audio_base64:
            return ""
        start = time.time()
        text = await self._transcribe_with_deepgram(audio_base64, language)
        elapsed_ms = (time.time() - start) * 1000
        logger.info(f"STT completed in {elapsed_ms:.0f}ms: '{text[:50]}' ({language})")
        return text

    async def _transcribe_with_deepgram(self, audio_base64: str, language: str) -> str:
        audio_bytes = base64.b64decode(audio_base64)
        if len(audio_bytes) == 0:
            return ""

        response = await self.client.listen.v1.media.transcribe_file(
            request=audio_bytes,
            model="nova-3",
            language=LANGUAGE_MAP.get(language, language),
            smart_format=True,
        )

        channels = response.results.channels if response.results else []
        if not channels:
            return ""

        alternatives = channels[0].alternatives
        if not alternatives:
            return ""

        transcript = alternatives[0].transcript or ""
        return transcript.strip()
