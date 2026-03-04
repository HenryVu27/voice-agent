# VoiceBridge POC Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a working proof-of-concept web app that translates live speech between Vietnamese and Russian in real-time using a cascaded STT → Translation → TTS pipeline.

**Architecture:** React frontend captures mic audio, streams to a FastAPI backend via WebSocket. Backend orchestrates Deepgram (STT), DeepL (translation), and Google Cloud TTS in sequence. Translated audio + transcripts stream back to the frontend.

**Tech Stack:** React 18 + TypeScript + Vite + Tailwind + shadcn/ui | Python 3.11 + FastAPI + uvicorn | Deepgram + DeepL + Google Cloud TTS APIs

---

## Task 1: Backend Scaffolding

**Files:**
- Create: `backend/app/__init__.py`
- Create: `backend/app/main.py`
- Create: `backend/app/config.py`
- Create: `backend/app/models/__init__.py`
- Create: `backend/app/models/schemas.py`
- Create: `backend/app/pipeline/__init__.py`
- Create: `backend/requirements.txt`
- Create: `backend/.env.example`
- Create: `.env`

**Step 1: Create requirements.txt**

```txt
fastapi==0.115.6
uvicorn[standard]==0.34.0
websockets==14.2
python-dotenv==1.0.1
deepgram-sdk==3.10.1
deepl==1.21.0
google-cloud-texttospeech==2.24.0
pydantic==2.10.4
httpx==0.28.1
pytest==8.3.4
pytest-asyncio==0.25.2
```

**Step 2: Create config.py**

```python
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    deepgram_api_key: str = ""
    deepl_api_key: str = ""
    google_application_credentials: str = ""

    host: str = "0.0.0.0"
    port: int = 8000
    cors_origins: list[str] = ["http://localhost:5173"]

    class Config:
        env_file = ".env"


@lru_cache
def get_settings() -> Settings:
    return Settings()
```

**Step 3: Create Pydantic schemas for WebSocket messages**

```python
# backend/app/models/schemas.py
from pydantic import BaseModel
from typing import Literal
from enum import Enum


class Speaker(str, Enum):
    A = "a"
    B = "b"


class Language(str, Enum):
    VI = "vi"
    RU = "ru"
    EN = "en"


# Client -> Server
class AudioChunkMessage(BaseModel):
    type: Literal["audio_chunk"] = "audio_chunk"
    data: str  # base64 encoded audio
    speaker: Speaker
    language: Language


class StartSpeakingMessage(BaseModel):
    type: Literal["start_speaking"] = "start_speaking"
    speaker: Speaker


class StopSpeakingMessage(BaseModel):
    type: Literal["stop_speaking"] = "stop_speaking"
    speaker: Speaker


# Server -> Client
class TranscriptMessage(BaseModel):
    type: Literal["transcript"] = "transcript"
    original: str
    translated: str
    speaker: Speaker


class AudioResponseMessage(BaseModel):
    type: Literal["audio_response"] = "audio_response"
    data: str  # base64 encoded audio
    language: Language


class StatusMessage(BaseModel):
    type: Literal["status"] = "status"
    latency_ms: float


class ErrorMessage(BaseModel):
    type: Literal["error"] = "error"
    message: str
```

**Step 4: Create minimal main.py with health check**

```python
# backend/app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import get_settings

settings = get_settings()

app = FastAPI(title="VoiceBridge", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    return {"status": "ok", "version": "0.1.0"}
```

**Step 5: Create .env.example and .env**

```bash
# .env.example (committed)
DEEPGRAM_API_KEY=your_key_here
DEEPL_API_KEY=your_key_here
GOOGLE_APPLICATION_CREDENTIALS=path/to/service-account.json

# .env (gitignored) - copy from .env.example and fill in real keys
```

**Step 6: Create __init__.py files**

Empty `__init__.py` in `backend/app/`, `backend/app/models/`, `backend/app/pipeline/`.

**Step 7: Install dependencies and verify server starts**

```bash
cd backend
python -m venv .venv
source .venv/Scripts/activate  # Windows Git Bash
pip install -r requirements.txt
uvicorn app.main:app --reload
# Expected: INFO: Uvicorn running on http://0.0.0.0:8000
# Visit http://localhost:8000/health -> {"status":"ok","version":"0.1.0"}
```

**Step 8: Commit**

```bash
git add backend/ .env.example .gitignore
git commit -m "feat: scaffold backend with FastAPI, config, and message schemas"
```

---

## Task 2: STT Module (Deepgram)

**Files:**
- Create: `backend/app/pipeline/stt.py`
- Create: `backend/tests/__init__.py`
- Create: `backend/tests/test_stt.py`

**Step 1: Write the test**

```python
# backend/tests/test_stt.py
import pytest
import base64
from unittest.mock import AsyncMock, MagicMock, patch
from app.pipeline.stt import SpeechToText


@pytest.fixture
def stt():
    return SpeechToText(api_key="test_key")


@pytest.mark.asyncio
async def test_transcribe_returns_text(stt):
    """STT should accept base64 audio and return transcribed text."""
    fake_audio = base64.b64encode(b"fake_audio_data").decode()

    with patch.object(stt, '_transcribe_with_deepgram', new_callable=AsyncMock) as mock:
        mock.return_value = "xin chao"
        result = await stt.transcribe(fake_audio, language="vi")

    assert result == "xin chao"
    mock.assert_called_once()


@pytest.mark.asyncio
async def test_transcribe_empty_audio_returns_empty(stt):
    """STT should return empty string for silence / no speech."""
    fake_audio = base64.b64encode(b"").decode()

    with patch.object(stt, '_transcribe_with_deepgram', new_callable=AsyncMock) as mock:
        mock.return_value = ""
        result = await stt.transcribe(fake_audio, language="vi")

    assert result == ""
```

**Step 2: Run test to verify it fails**

```bash
cd backend
python -m pytest tests/test_stt.py -v
# Expected: FAIL - ModuleNotFoundError: No module named 'app.pipeline.stt'
```

**Step 3: Implement STT module**

```python
# backend/app/pipeline/stt.py
import base64
import time
import logging
from deepgram import DeepgramClient, PrerecordedOptions

logger = logging.getLogger(__name__)

LANGUAGE_MAP = {
    "vi": "vi",
    "ru": "ru",
    "en": "en-US",
}


class SpeechToText:
    def __init__(self, api_key: str):
        self.client = DeepgramClient(api_key)

    async def transcribe(self, audio_base64: str, language: str) -> str:
        """Transcribe base64-encoded audio to text.

        Args:
            audio_base64: Base64 encoded audio data (16kHz mono PCM/WAV)
            language: Language code ("vi", "ru", "en")

        Returns:
            Transcribed text string, or empty string if no speech detected.
        """
        if not audio_base64:
            return ""

        start = time.time()
        text = await self._transcribe_with_deepgram(audio_base64, language)
        elapsed_ms = (time.time() - start) * 1000
        logger.info(f"STT completed in {elapsed_ms:.0f}ms: '{text[:50]}...' ({language})")
        return text

    async def _transcribe_with_deepgram(self, audio_base64: str, language: str) -> str:
        audio_bytes = base64.b64decode(audio_base64)
        if len(audio_bytes) == 0:
            return ""

        options = PrerecordedOptions(
            model="nova-3",
            language=LANGUAGE_MAP.get(language, language),
            smart_format=True,
        )

        source = {"buffer": audio_bytes, "mimetype": "audio/wav"}
        response = await self.client.listen.asyncrest.v("1").transcribe_file(source, options)

        transcript = (
            response.results.channels[0].alternatives[0].transcript
            if response.results.channels
            else ""
        )
        return transcript.strip()
```

**Step 4: Run tests**

```bash
python -m pytest tests/test_stt.py -v
# Expected: 2 passed
```

**Step 5: Commit**

```bash
git add backend/app/pipeline/stt.py backend/tests/
git commit -m "feat: add Deepgram STT module with tests"
```

---

## Task 3: Translation Module (DeepL)

**Files:**
- Create: `backend/app/pipeline/translator.py`
- Create: `backend/tests/test_translator.py`

**Step 1: Write the test**

```python
# backend/tests/test_translator.py
import pytest
from unittest.mock import MagicMock, patch
from app.pipeline.translator import Translator


@pytest.fixture
def translator():
    return Translator(api_key="test_key")


@pytest.mark.asyncio
async def test_translate_vi_to_ru(translator):
    """Should translate Vietnamese text to Russian."""
    mock_result = MagicMock()
    mock_result.text = "Привет"

    with patch.object(translator, '_client') as mock_client:
        mock_client.translate_text.return_value = mock_result
        result = await translator.translate("Xin chào", source_lang="vi", target_lang="ru")

    assert result == "Привет"


@pytest.mark.asyncio
async def test_translate_empty_text(translator):
    """Should return empty string for empty input."""
    result = await translator.translate("", source_lang="vi", target_lang="ru")
    assert result == ""
```

**Step 2: Run test to verify it fails**

```bash
python -m pytest tests/test_translator.py -v
# Expected: FAIL
```

**Step 3: Implement translator module**

```python
# backend/app/pipeline/translator.py
import time
import logging
import deepl

logger = logging.getLogger(__name__)

# DeepL uses uppercase language codes and specific variants
DEEPL_LANG_MAP = {
    "vi": None,       # DeepL does not support Vietnamese natively
    "ru": "RU",
    "en": "EN-US",
}

# For languages DeepL doesn't support, we route through English as pivot
# Vietnamese is not supported by DeepL - we'll use Google Translate as fallback
# For POC: we use googletrans or httpx to Google Translate API


class Translator:
    def __init__(self, api_key: str):
        self._client = deepl.Translator(api_key)

    async def translate(self, text: str, source_lang: str, target_lang: str) -> str:
        """Translate text between languages.

        Args:
            text: Source text to translate
            source_lang: Source language code ("vi", "ru", "en")
            target_lang: Target language code ("vi", "ru", "en")

        Returns:
            Translated text string.
        """
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

        # DeepL doesn't support Vietnamese - use pivot through English
        if source_lang == "vi" or target_lang == "vi":
            return await self._translate_with_pivot(text, source_lang, target_lang)

        result = self._client.translate_text(
            text,
            source_lang=source_code,
            target_lang=target_code,
        )
        return result.text

    async def _translate_with_pivot(self, text: str, source_lang: str, target_lang: str) -> str:
        """For unsupported language pairs, pivot through English.

        Vietnamese -> English -> Russian (or reverse).
        In production, replace with Google Translate API which supports Vi directly.
        """
        # TODO: Replace with direct Google Translate API call for Vi support
        # For now, this is a placeholder that documents the limitation
        import httpx

        # Using MyMemory free translation API as POC fallback
        async with httpx.AsyncClient() as client:
            langpair = f"{source_lang}|{target_lang}"
            resp = await client.get(
                "https://api.mymemory.translated.net/get",
                params={"q": text, "langpair": langpair},
            )
            data = resp.json()
            return data.get("responseData", {}).get("translatedText", text)
```

**Step 4: Run tests**

```bash
python -m pytest tests/test_translator.py -v
# Expected: 2 passed
```

**Step 5: Commit**

```bash
git add backend/app/pipeline/translator.py backend/tests/test_translator.py
git commit -m "feat: add translation module with DeepL + pivot fallback for Vietnamese"
```

---

## Task 4: TTS Module (Google Cloud TTS)

**Files:**
- Create: `backend/app/pipeline/tts.py`
- Create: `backend/tests/test_tts.py`

**Step 1: Write the test**

```python
# backend/tests/test_tts.py
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.pipeline.tts import TextToSpeech


@pytest.fixture
def tts():
    return TextToSpeech()


@pytest.mark.asyncio
async def test_synthesize_returns_base64_audio(tts):
    """TTS should accept text and return base64-encoded audio."""
    with patch.object(tts, '_synthesize_google', new_callable=AsyncMock) as mock:
        mock.return_value = "base64_audio_data"
        result = await tts.synthesize("Привет", language="ru")

    assert result == "base64_audio_data"
    mock.assert_called_once()


@pytest.mark.asyncio
async def test_synthesize_empty_text_returns_empty(tts):
    """TTS should return empty string for empty input."""
    result = await tts.synthesize("", language="ru")
    assert result == ""
```

**Step 2: Run test to verify it fails**

```bash
python -m pytest tests/test_tts.py -v
# Expected: FAIL
```

**Step 3: Implement TTS module**

```python
# backend/app/pipeline/tts.py
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
        """Convert text to speech audio.

        Args:
            text: Text to synthesize
            language: Target language code ("vi", "ru", "en")

        Returns:
            Base64-encoded MP3 audio string, or empty string if no text.
        """
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
```

**Step 4: Run tests**

```bash
python -m pytest tests/test_tts.py -v
# Expected: 2 passed
```

**Step 5: Commit**

```bash
git add backend/app/pipeline/tts.py backend/tests/test_tts.py
git commit -m "feat: add Google Cloud TTS module with tests"
```

---

## Task 5: Pipeline Orchestrator

**Files:**
- Create: `backend/app/pipeline/orchestrator.py`
- Create: `backend/tests/test_orchestrator.py`

**Step 1: Write the test**

```python
# backend/tests/test_orchestrator.py
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
    """Pipeline should chain STT -> Translation -> TTS and return all results."""
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
    """Pipeline should return early if STT produces no text."""
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
```

**Step 2: Run test to verify it fails**

```bash
python -m pytest tests/test_orchestrator.py -v
# Expected: FAIL
```

**Step 3: Implement orchestrator**

```python
# backend/app/pipeline/orchestrator.py
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

    async def process(
        self, audio_base64: str, source_lang: str, target_lang: str
    ) -> PipelineResult:
        """Run the full STT -> Translation -> TTS pipeline.

        Args:
            audio_base64: Base64 encoded audio from speaker
            source_lang: Speaker's language ("vi", "ru", "en")
            target_lang: Listener's language ("vi", "ru", "en")

        Returns:
            PipelineResult with transcripts, audio, and latency metrics.
        """
        pipeline_start = time.time()

        # Stage 1: Speech to Text
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

        # Stage 3: Text to Speech
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
```

**Step 4: Run tests**

```bash
python -m pytest tests/test_orchestrator.py -v
# Expected: 2 passed
```

**Step 5: Commit**

```bash
git add backend/app/pipeline/orchestrator.py backend/tests/test_orchestrator.py
git commit -m "feat: add translation pipeline orchestrator with latency tracking"
```

---

## Task 6: WebSocket Endpoint

**Files:**
- Modify: `backend/app/main.py`
- Create: `backend/tests/test_websocket.py`

**Step 1: Write the test**

```python
# backend/tests/test_websocket.py
import pytest
import json
import base64
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient
from app.main import app


def test_health_endpoint():
    """Health endpoint should return ok."""
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_websocket_connection():
    """WebSocket should accept connections."""
    client = TestClient(app)
    with client.websocket_connect("/ws/translate") as ws:
        # Send a start_speaking message
        ws.send_json({"type": "start_speaking", "speaker": "a"})
        # Connection should stay open (no error)
```

**Step 2: Run test to verify it fails**

```bash
python -m pytest tests/test_websocket.py -v
# Expected: FAIL on websocket test (endpoint doesn't exist yet)
```

**Step 3: Add WebSocket endpoint to main.py**

```python
# backend/app/main.py
import json
import logging
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from app.config import get_settings
from app.pipeline.stt import SpeechToText
from app.pipeline.translator import Translator
from app.pipeline.tts import TextToSpeech
from app.pipeline.orchestrator import TranslationPipeline

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

settings = get_settings()

app = FastAPI(title="VoiceBridge", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Language pair config: speaker -> (source_lang, target_lang)
LANGUAGE_CONFIG = {
    "a": ("vi", "ru"),
    "b": ("ru", "vi"),
}


def create_pipeline() -> TranslationPipeline:
    return TranslationPipeline(
        stt=SpeechToText(api_key=settings.deepgram_api_key),
        translator=Translator(api_key=settings.deepl_api_key),
        tts=TextToSpeech(),
    )


@app.get("/health")
async def health():
    return {"status": "ok", "version": "0.1.0"}


@app.websocket("/ws/translate")
async def websocket_translate(websocket: WebSocket):
    await websocket.accept()
    pipeline = create_pipeline()
    logger.info("WebSocket client connected")

    try:
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type")

            if msg_type == "start_speaking":
                logger.info(f"Speaker {data['speaker']} started speaking")

            elif msg_type == "stop_speaking":
                logger.info(f"Speaker {data['speaker']} stopped speaking")

            elif msg_type == "audio_chunk":
                speaker = data["speaker"]
                source_lang, target_lang = LANGUAGE_CONFIG.get(
                    speaker, ("en", "en")
                )

                result = await pipeline.process(
                    audio_base64=data["data"],
                    source_lang=source_lang,
                    target_lang=target_lang,
                )

                if result.original_text:
                    # Send transcript
                    await websocket.send_json({
                        "type": "transcript",
                        "original": result.original_text,
                        "translated": result.translated_text,
                        "speaker": speaker,
                    })

                    # Send translated audio
                    if result.audio_base64:
                        await websocket.send_json({
                            "type": "audio_response",
                            "data": result.audio_base64,
                            "language": target_lang,
                        })

                    # Send latency stats
                    await websocket.send_json({
                        "type": "status",
                        "latency_ms": result.latency_ms,
                    })

    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        try:
            await websocket.send_json({
                "type": "error",
                "message": str(e),
            })
        except Exception:
            pass
```

**Step 4: Run tests**

```bash
python -m pytest tests/test_websocket.py -v
# Expected: 2 passed
```

**Step 5: Commit**

```bash
git add backend/app/main.py backend/tests/test_websocket.py
git commit -m "feat: add WebSocket endpoint for real-time translation"
```

---

## Task 7: Frontend Scaffolding

**Files:**
- Create: `frontend/` (entire Vite + React + Tailwind project)

**Step 1: Scaffold Vite React TypeScript project**

```bash
cd C:/Personal/voice-agent
npm create vite@latest frontend -- --template react-ts
cd frontend
npm install
```

**Step 2: Install Tailwind CSS**

```bash
npm install -D tailwindcss @tailwindcss/vite
```

Add Tailwind to `vite.config.ts`:
```typescript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    proxy: {
      '/ws': {
        target: 'http://localhost:8000',
        ws: true,
      },
    },
  },
})
```

Replace `src/index.css` with:
```css
@import "tailwindcss";

:root {
  --background: oklch(0.985 0 0);
  --foreground: oklch(0.145 0 0);
  --primary: oklch(0.55 0.2 250);
  --primary-foreground: oklch(0.985 0 0);
  --secondary: oklch(0.97 0.005 250);
  --muted: oklch(0.97 0 0);
  --muted-foreground: oklch(0.556 0 0);
  --accent: oklch(0.97 0.005 250);
  --destructive: oklch(0.577 0.245 27.325);
  --border: oklch(0.922 0 0);
  --ring: oklch(0.708 0 0);
  --radius: 0.625rem;

  --speaker-a: oklch(0.55 0.15 160);
  --speaker-b: oklch(0.55 0.15 30);
}

body {
  background-color: var(--background);
  color: var(--foreground);
  font-family: "DM Sans", system-ui, sans-serif;
}
```

**Step 3: Install project dependencies**

```bash
npm install framer-motion lucide-react sonner
npm install -D @types/node
```

**Step 4: Add path alias to tsconfig**

Update `tsconfig.app.json` to add path alias:
```json
{
  "compilerOptions": {
    "baseUrl": ".",
    "paths": { "@/*": ["./src/*"] }
  }
}
```

**Step 5: Create utility file**

```typescript
// frontend/src/lib/utils.ts
import { type ClassValue, clsx } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}
```

```bash
npm install clsx tailwind-merge
```

**Step 6: Verify dev server starts**

```bash
npm run dev
# Expected: Local: http://localhost:5173/
```

**Step 7: Commit**

```bash
cd C:/Personal/voice-agent
git add frontend/
git commit -m "feat: scaffold frontend with React, TypeScript, Vite, Tailwind"
```

---

## Task 8: Frontend WebSocket Hook

**Files:**
- Create: `frontend/src/hooks/useWebSocket.ts`
- Create: `frontend/src/lib/types.ts`

**Step 1: Create shared types**

```typescript
// frontend/src/lib/types.ts
export type Speaker = "a" | "b";
export type Language = "vi" | "ru" | "en";

// Client -> Server
export interface AudioChunkMessage {
  type: "audio_chunk";
  data: string; // base64
  speaker: Speaker;
  language: Language;
}

export interface StartSpeakingMessage {
  type: "start_speaking";
  speaker: Speaker;
}

export interface StopSpeakingMessage {
  type: "stop_speaking";
  speaker: Speaker;
}

export type ClientMessage = AudioChunkMessage | StartSpeakingMessage | StopSpeakingMessage;

// Server -> Client
export interface TranscriptMessage {
  type: "transcript";
  original: string;
  translated: string;
  speaker: Speaker;
}

export interface AudioResponseMessage {
  type: "audio_response";
  data: string; // base64
  language: Language;
}

export interface StatusMessage {
  type: "status";
  latency_ms: number;
}

export interface ErrorMessage {
  type: "error";
  message: string;
}

export type ServerMessage = TranscriptMessage | AudioResponseMessage | StatusMessage | ErrorMessage;

export interface TranscriptEntry {
  original: string;
  translated: string;
  speaker: Speaker;
  timestamp: number;
}
```

**Step 2: Create WebSocket hook**

```typescript
// frontend/src/hooks/useWebSocket.ts
import { useRef, useState, useCallback, useEffect } from "react";
import type { ClientMessage, ServerMessage } from "@/lib/types";

interface UseWebSocketOptions {
  url: string;
  onMessage: (message: ServerMessage) => void;
  reconnectInterval?: number;
}

export function useWebSocket({ url, onMessage, reconnectInterval = 3000 }: UseWebSocketOptions) {
  const wsRef = useRef<WebSocket | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const reconnectTimer = useRef<ReturnType<typeof setTimeout>>();

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    const ws = new WebSocket(url);

    ws.onopen = () => {
      setIsConnected(true);
    };

    ws.onmessage = (event) => {
      const data: ServerMessage = JSON.parse(event.data);
      onMessage(data);
    };

    ws.onclose = () => {
      setIsConnected(false);
      reconnectTimer.current = setTimeout(connect, reconnectInterval);
    };

    ws.onerror = () => {
      ws.close();
    };

    wsRef.current = ws;
  }, [url, onMessage, reconnectInterval]);

  const disconnect = useCallback(() => {
    clearTimeout(reconnectTimer.current);
    wsRef.current?.close();
    wsRef.current = null;
  }, []);

  const send = useCallback((message: ClientMessage) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(message));
    }
  }, []);

  useEffect(() => {
    connect();
    return disconnect;
  }, [connect, disconnect]);

  return { isConnected, send, disconnect };
}
```

**Step 3: Commit**

```bash
git add frontend/src/hooks/useWebSocket.ts frontend/src/lib/types.ts
git commit -m "feat: add WebSocket hook and shared message types"
```

---

## Task 9: Frontend Audio Capture Hook

**Files:**
- Create: `frontend/src/hooks/useAudioCapture.ts`

**Step 1: Implement audio capture hook**

```typescript
// frontend/src/hooks/useAudioCapture.ts
import { useRef, useState, useCallback } from "react";

interface UseAudioCaptureOptions {
  onAudioChunk: (base64Audio: string) => void;
  sampleRate?: number;
}

export function useAudioCapture({ onAudioChunk, sampleRate = 16000 }: UseAudioCaptureOptions) {
  const [isRecording, setIsRecording] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);

  const startRecording = useCallback(async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          sampleRate,
          channelCount: 1,
          echoCancellation: true,
          noiseSuppression: true,
        },
      });

      const mediaRecorder = new MediaRecorder(stream, {
        mimeType: "audio/webm;codecs=opus",
      });

      chunksRef.current = [];

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          chunksRef.current.push(event.data);
        }
      };

      mediaRecorder.start(100); // Collect data every 100ms
      mediaRecorderRef.current = mediaRecorder;
      setIsRecording(true);
      setError(null);
    } catch (err) {
      setError(
        err instanceof DOMException && err.name === "NotAllowedError"
          ? "Microphone permission denied. Please allow microphone access."
          : "Failed to access microphone."
      );
    }
  }, [sampleRate]);

  const stopRecording = useCallback(async (): Promise<string> => {
    return new Promise((resolve) => {
      const mediaRecorder = mediaRecorderRef.current;
      if (!mediaRecorder || mediaRecorder.state === "inactive") {
        resolve("");
        return;
      }

      mediaRecorder.onstop = async () => {
        const blob = new Blob(chunksRef.current, { type: "audio/webm" });
        const buffer = await blob.arrayBuffer();
        const base64 = btoa(
          new Uint8Array(buffer).reduce(
            (data, byte) => data + String.fromCharCode(byte),
            ""
          )
        );

        // Stop all tracks
        mediaRecorder.stream.getTracks().forEach((track) => track.stop());

        setIsRecording(false);
        onAudioChunk(base64);
        resolve(base64);
      };

      mediaRecorder.stop();
    });
  }, [onAudioChunk]);

  return { isRecording, startRecording, stopRecording, error };
}
```

**Step 2: Commit**

```bash
git add frontend/src/hooks/useAudioCapture.ts
git commit -m "feat: add audio capture hook with mic access and base64 encoding"
```

---

## Task 10: Frontend UI Components

**Files:**
- Create: `frontend/src/components/translation/SpeakerPanel.tsx`
- Create: `frontend/src/components/translation/TranscriptView.tsx`
- Create: `frontend/src/components/layout/StatusBar.tsx`
- Create: `frontend/src/components/layout/Header.tsx`

**Step 1: Create Header component**

```tsx
// frontend/src/components/layout/Header.tsx
import { Languages } from "lucide-react";

interface HeaderProps {
  languagePair: string;
}

export function Header({ languagePair }: HeaderProps) {
  return (
    <header className="flex items-center justify-between px-6 py-4 border-b border-[var(--border)]">
      <div className="flex items-center gap-3">
        <Languages className="w-6 h-6 text-[var(--primary)]" />
        <h1 className="text-xl font-semibold tracking-tight">VoiceBridge</h1>
      </div>
      <div className="px-3 py-1.5 rounded-lg bg-[var(--secondary)] text-sm font-medium">
        {languagePair}
      </div>
    </header>
  );
}
```

**Step 2: Create StatusBar component**

```tsx
// frontend/src/components/layout/StatusBar.tsx
import { Circle } from "lucide-react";

interface StatusBarProps {
  isConnected: boolean;
  latencyMs: number | null;
  sessionSeconds: number;
}

export function StatusBar({ isConnected, latencyMs, sessionSeconds }: StatusBarProps) {
  const minutes = Math.floor(sessionSeconds / 60);
  const seconds = sessionSeconds % 60;
  const timeStr = `${minutes}:${seconds.toString().padStart(2, "0")}`;

  return (
    <footer className="flex items-center justify-center gap-6 px-6 py-3 border-t border-[var(--border)] text-sm text-[var(--muted-foreground)]">
      {latencyMs !== null && (
        <span>Latency: {latencyMs.toFixed(0)}ms</span>
      )}
      <span>Session: {timeStr}</span>
      <span className="flex items-center gap-1.5">
        <Circle
          className={`w-2.5 h-2.5 fill-current ${
            isConnected ? "text-emerald-500" : "text-red-500"
          }`}
        />
        {isConnected ? "Connected" : "Disconnected"}
      </span>
    </footer>
  );
}
```

**Step 3: Create TranscriptView component**

```tsx
// frontend/src/components/translation/TranscriptView.tsx
import type { TranscriptEntry, Speaker } from "@/lib/types";

interface TranscriptViewProps {
  entries: TranscriptEntry[];
  speaker: Speaker;
}

export function TranscriptView({ entries, speaker }: TranscriptViewProps) {
  const speakerEntries = entries.filter((e) => e.speaker === speaker);

  if (speakerEntries.length === 0) {
    return (
      <div className="flex-1 flex items-center justify-center text-[var(--muted-foreground)] text-sm">
        Press and hold to speak...
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto space-y-3 p-4">
      {speakerEntries.map((entry, i) => (
        <div key={i} className="space-y-1">
          <p className="text-sm font-medium leading-relaxed">
            {entry.original}
          </p>
          <p className="text-sm text-[var(--muted-foreground)] leading-relaxed">
            {entry.translated}
          </p>
        </div>
      ))}
    </div>
  );
}
```

**Step 4: Create SpeakerPanel component**

```tsx
// frontend/src/components/translation/SpeakerPanel.tsx
import { Mic, MicOff } from "lucide-react";
import { TranscriptView } from "./TranscriptView";
import type { Speaker, Language, TranscriptEntry } from "@/lib/types";

const LANGUAGE_LABELS: Record<Language, string> = {
  vi: "Vietnamese",
  ru: "Russian",
  en: "English",
};

const LANGUAGE_FLAGS: Record<Language, string> = {
  vi: "\u{1F1FB}\u{1F1F3}",
  ru: "\u{1F1F7}\u{1F1FA}",
  en: "\u{1F1FA}\u{1F1F8}",
};

interface SpeakerPanelProps {
  speaker: Speaker;
  language: Language;
  isRecording: boolean;
  onPressStart: () => void;
  onPressEnd: () => void;
  transcripts: TranscriptEntry[];
  disabled?: boolean;
}

export function SpeakerPanel({
  speaker,
  language,
  isRecording,
  onPressStart,
  onPressEnd,
  transcripts,
  disabled,
}: SpeakerPanelProps) {
  return (
    <div className="flex flex-col flex-1 min-h-0">
      <div className="px-4 py-3 border-b border-[var(--border)]">
        <div className="flex items-center gap-2">
          <span className="text-lg">{LANGUAGE_FLAGS[language]}</span>
          <span className="text-sm font-semibold tracking-tight">
            Speaker {speaker.toUpperCase()}
          </span>
          <span className="text-sm text-[var(--muted-foreground)]">
            {LANGUAGE_LABELS[language]}
          </span>
        </div>
      </div>

      <TranscriptView entries={transcripts} speaker={speaker} />

      <div className="p-4">
        <button
          onMouseDown={onPressStart}
          onMouseUp={onPressEnd}
          onTouchStart={onPressStart}
          onTouchEnd={onPressEnd}
          disabled={disabled}
          className={`
            w-full flex items-center justify-center gap-2 px-4 py-3 rounded-lg
            font-medium text-sm transition-all duration-150
            ${
              isRecording
                ? "bg-red-500 text-white shadow-lg scale-[0.98]"
                : "bg-[var(--primary)] text-[var(--primary-foreground)] hover:opacity-90"
            }
            ${disabled ? "opacity-50 cursor-not-allowed" : "cursor-pointer active:scale-[0.98]"}
          `}
        >
          {isRecording ? (
            <>
              <Mic className="w-4 h-4 animate-pulse" />
              Speaking...
            </>
          ) : (
            <>
              <MicOff className="w-4 h-4" />
              Hold to Speak
            </>
          )}
        </button>
      </div>
    </div>
  );
}
```

**Step 5: Commit**

```bash
git add frontend/src/components/
git commit -m "feat: add UI components - Header, StatusBar, SpeakerPanel, TranscriptView"
```

---

## Task 11: Conversation Page (Main Integration)

**Files:**
- Create: `frontend/src/pages/ConversationPage.tsx`
- Modify: `frontend/src/App.tsx`

**Step 1: Create ConversationPage**

```tsx
// frontend/src/pages/ConversationPage.tsx
import { useState, useCallback, useEffect, useRef } from "react";
import { Header } from "@/components/layout/Header";
import { StatusBar } from "@/components/layout/StatusBar";
import { SpeakerPanel } from "@/components/translation/SpeakerPanel";
import { useWebSocket } from "@/hooks/useWebSocket";
import { useAudioCapture } from "@/hooks/useAudioCapture";
import type { Speaker, ServerMessage, TranscriptEntry } from "@/lib/types";

const WS_URL = `ws://${window.location.hostname}:${window.location.port}/ws/translate`;

export function ConversationPage() {
  const [transcripts, setTranscripts] = useState<TranscriptEntry[]>([]);
  const [latencyMs, setLatencyMs] = useState<number | null>(null);
  const [sessionSeconds, setSessionSeconds] = useState(0);
  const [activeSpeaker, setActiveSpeaker] = useState<Speaker | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  // Session timer
  useEffect(() => {
    const interval = setInterval(() => {
      setSessionSeconds((s) => s + 1);
    }, 1000);
    return () => clearInterval(interval);
  }, []);

  const handleServerMessage = useCallback((msg: ServerMessage) => {
    switch (msg.type) {
      case "transcript":
        setTranscripts((prev) => [
          ...prev,
          {
            original: msg.original,
            translated: msg.translated,
            speaker: msg.speaker,
            timestamp: Date.now(),
          },
        ]);
        break;

      case "audio_response":
        // Play translated audio
        const audioSrc = `data:audio/mp3;base64,${msg.data}`;
        if (audioRef.current) {
          audioRef.current.src = audioSrc;
          audioRef.current.play().catch(() => {});
        }
        break;

      case "status":
        setLatencyMs(msg.latency_ms);
        break;

      case "error":
        console.error("Server error:", msg.message);
        break;
    }
  }, []);

  const { isConnected, send } = useWebSocket({
    url: WS_URL,
    onMessage: handleServerMessage,
  });

  const handleAudioChunk = useCallback(
    (base64Audio: string) => {
      if (activeSpeaker) {
        send({
          type: "audio_chunk",
          data: base64Audio,
          speaker: activeSpeaker,
          language: activeSpeaker === "a" ? "vi" : "ru",
        });
      }
    },
    [send, activeSpeaker]
  );

  const { isRecording, startRecording, stopRecording, error } = useAudioCapture({
    onAudioChunk: handleAudioChunk,
  });

  const handlePressStart = useCallback(
    (speaker: Speaker) => {
      setActiveSpeaker(speaker);
      send({ type: "start_speaking", speaker });
      startRecording();
    },
    [send, startRecording]
  );

  const handlePressEnd = useCallback(
    (speaker: Speaker) => {
      send({ type: "stop_speaking", speaker });
      stopRecording();
      setActiveSpeaker(null);
    },
    [send, stopRecording]
  );

  return (
    <div className="flex flex-col h-screen">
      <Header languagePair="Vi \u2194 Ru" />

      {error && (
        <div className="px-6 py-3 bg-red-50 text-red-700 text-sm">{error}</div>
      )}

      <div className="flex flex-1 min-h-0 divide-x divide-[var(--border)]">
        <SpeakerPanel
          speaker="a"
          language="vi"
          isRecording={isRecording && activeSpeaker === "a"}
          onPressStart={() => handlePressStart("a")}
          onPressEnd={() => handlePressEnd("a")}
          transcripts={transcripts}
          disabled={!isConnected || (isRecording && activeSpeaker !== "a")}
        />
        <SpeakerPanel
          speaker="b"
          language="ru"
          isRecording={isRecording && activeSpeaker === "b"}
          onPressStart={() => handlePressStart("b")}
          onPressEnd={() => handlePressEnd("b")}
          transcripts={transcripts}
          disabled={!isConnected || (isRecording && activeSpeaker !== "b")}
        />
      </div>

      <StatusBar
        isConnected={isConnected}
        latencyMs={latencyMs}
        sessionSeconds={sessionSeconds}
      />

      <audio ref={audioRef} className="hidden" />
    </div>
  );
}
```

**Step 2: Update App.tsx**

```tsx
// frontend/src/App.tsx
import { ConversationPage } from "@/pages/ConversationPage";

function App() {
  return <ConversationPage />;
}

export default App;
```

**Step 3: Clean up default Vite files**

Delete `src/App.css` and the default Vite assets. Remove the import of `App.css` from `App.tsx`.

**Step 4: Verify frontend compiles**

```bash
cd frontend && npm run build
# Expected: Build successful with no TypeScript errors
```

**Step 5: Commit**

```bash
cd C:/Personal/voice-agent
git add frontend/src/
git commit -m "feat: add ConversationPage with full translation UI integration"
```

---

## Task 12: End-to-End Smoke Test

**Files:**
- Create: `backend/tests/test_e2e.py`
- Modify: `.env` (must have real API keys)

**Step 1: Write E2E test**

```python
# backend/tests/test_e2e.py
"""
Manual E2E smoke test. Run with real API keys.
Verifies the full pipeline: audio -> STT -> translate -> TTS -> audio.

Usage: python -m pytest tests/test_e2e.py -v -s --run-e2e
"""
import pytest
import base64
import os

# Skip unless explicitly opted in
pytestmark = pytest.mark.skipunless(
    os.getenv("RUN_E2E_TESTS"), reason="Set RUN_E2E_TESTS=1 to run"
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

    # For E2E test, you need a real audio file
    # Record a short "xin chao" and save as test_audio.wav
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
```

**Step 2: Create test fixtures directory**

```bash
mkdir -p backend/tests/fixtures
echo "Place a short Vietnamese audio WAV file here as test_audio.wav" > backend/tests/fixtures/README.md
```

**Step 3: Run unit tests (confirm nothing broke)**

```bash
cd backend
python -m pytest tests/ -v --ignore=tests/test_e2e.py
# Expected: All tests pass
```

**Step 4: Commit**

```bash
cd C:/Personal/voice-agent
git add backend/tests/
git commit -m "feat: add E2E smoke test for full translation pipeline"
```

---

## Task 13: Final Verification & README

**Files:**
- Create: `README.md`

**Step 1: Start both servers and verify connection**

```bash
# Terminal 1: Backend
cd backend
source .venv/Scripts/activate
uvicorn app.main:app --reload --port 8000

# Terminal 2: Frontend
cd frontend
npm run dev
```

**Step 2: Open browser and verify**

- Open `http://localhost:5173`
- Confirm: split-screen UI loads
- Confirm: StatusBar shows "Connected"
- Confirm: Push-to-talk buttons are visible
- Confirm: No console errors

**Step 3: Create README**

```markdown
# VoiceBridge

Real-time bidirectional speech translation. POC for Vietnamese <-> Russian.

## Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+
- API keys: Deepgram, DeepL, Google Cloud TTS

### Setup

1. Clone and configure:
   ```bash
   cp .env.example .env
   # Edit .env with your API keys
   ```

2. Backend:
   ```bash
   cd backend
   python -m venv .venv
   source .venv/Scripts/activate  # or .venv\Scripts\activate on Windows
   pip install -r requirements.txt
   uvicorn app.main:app --reload
   ```

3. Frontend:
   ```bash
   cd frontend
   npm install
   npm run dev
   ```

4. Open http://localhost:5173

## Architecture

```
Browser (React) <--WebSocket--> FastAPI Server
                                   |
                                   +-- Deepgram STT
                                   +-- DeepL Translation
                                   +-- Google Cloud TTS
```

## Development

```bash
# Run backend tests
cd backend && python -m pytest tests/ -v

# Build frontend
cd frontend && npm run build
```
```

**Step 4: Final commit**

```bash
git add README.md
git commit -m "docs: add README with setup instructions"
```

---

## Summary

| Task | Description | Dependencies |
|------|-------------|-------------|
| 1 | Backend scaffolding (FastAPI, config, schemas) | None |
| 2 | STT module (Deepgram) | Task 1 |
| 3 | Translation module (DeepL + fallback) | Task 1 |
| 4 | TTS module (Google Cloud) | Task 1 |
| 5 | Pipeline orchestrator | Tasks 2, 3, 4 |
| 6 | WebSocket endpoint | Task 5 |
| 7 | Frontend scaffolding (Vite, React, Tailwind) | None |
| 8 | WebSocket hook + types | Task 7 |
| 9 | Audio capture hook | Task 7 |
| 10 | UI components (SpeakerPanel, TranscriptView, etc.) | Tasks 8, 9 |
| 11 | ConversationPage (integration) | Tasks 8, 9, 10 |
| 12 | E2E smoke test | Tasks 6, 11 |
| 13 | Final verification + README | All |

**Parallelizable:** Tasks 1-4 backend modules can be built independently. Tasks 7-9 can run in parallel with backend work. Task 5 needs 2+3+4. Task 6 needs 5. Tasks 10-11 need 8+9.
