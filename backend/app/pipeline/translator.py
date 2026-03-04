import time
import logging

import deepl

logger = logging.getLogger(__name__)

DEEPL_LANG_MAP = {
    "vi": None,       # DeepL does not support Vietnamese natively
    "ru": "RU",
    "en": "EN-US",
}


class Translator:
    def __init__(self, api_key: str):
        self._client = deepl.Translator(api_key)

    async def translate(self, text: str, source_lang: str, target_lang: str) -> str:
        if not text.strip():
            return ""

        start = time.time()
        result = await self._translate_deepl(text, source_lang, target_lang)
        elapsed_ms = (time.time() - start) * 1000
        logger.info(f"Translation completed in {elapsed_ms:.0f}ms: {source_lang}->{target_lang}")
        return result

    async def _translate_deepl(self, text: str, source_lang: str, target_lang: str) -> str:
        target_code = DEEPL_LANG_MAP.get(target_lang, target_lang.upper())
        source_code = DEEPL_LANG_MAP.get(source_lang, source_lang.upper())

        # DeepL doesn't support Vietnamese — use pivot
        if source_lang == "vi" or target_lang == "vi":
            return await self._translate_with_pivot(text, source_lang, target_lang)

        result = self._client.translate_text(
            text,
            source_lang=source_code,
            target_lang=target_code,
        )
        return result.text

    async def _translate_with_pivot(
        self, text: str, source_lang: str, target_lang: str
    ) -> str:
        """For unsupported language pairs, use MyMemory free translation API."""
        import httpx

        async with httpx.AsyncClient() as client:
            langpair = f"{source_lang}|{target_lang}"
            resp = await client.get(
                "https://api.mymemory.translated.net/get",
                params={"q": text, "langpair": langpair},
            )
            data = resp.json()
            return data.get("responseData", {}).get("translatedText", text)
