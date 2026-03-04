from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.pipeline.translator import Translator


@pytest.fixture
def translator():
    return Translator(api_key="test_key")


@pytest.mark.asyncio
async def test_translate_vi_to_ru(translator):
    """Vietnamese goes through the MyMemory pivot path, not DeepL directly."""
    with patch.object(
        translator, "_translate_with_pivot", new_callable=AsyncMock
    ) as mock_pivot:
        mock_pivot.return_value = "Привет"
        result = await translator.translate("Xin chào", source_lang="vi", target_lang="ru")

    assert result == "Привет"
    mock_pivot.assert_awaited_once_with("Xin chào", "vi", "ru")


@pytest.mark.asyncio
async def test_translate_en_to_ru_uses_deepl(translator):
    """Supported language pairs (en->ru) go through the DeepL client."""
    mock_result = MagicMock()
    mock_result.text = "Привет"

    with patch.object(translator, "_client") as mock_client:
        mock_client.translate_text.return_value = mock_result
        result = await translator.translate("Hello", source_lang="en", target_lang="ru")

    assert result == "Привет"
    mock_client.translate_text.assert_called_once_with(
        "Hello",
        source_lang="EN-US",
        target_lang="RU",
    )


@pytest.mark.asyncio
async def test_translate_empty_text(translator):
    result = await translator.translate("", source_lang="vi", target_lang="ru")
    assert result == ""
