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
                source_lang, target_lang = LANGUAGE_CONFIG.get(speaker, ("en", "en"))

                result = await pipeline.process(
                    audio_base64=data["data"],
                    source_lang=source_lang,
                    target_lang=target_lang,
                )

                if result.original_text:
                    await websocket.send_json({
                        "type": "transcript",
                        "original": result.original_text,
                        "translated": result.translated_text,
                        "speaker": speaker,
                    })

                    if result.audio_base64:
                        await websocket.send_json({
                            "type": "audio_response",
                            "data": result.audio_base64,
                            "language": target_lang,
                        })

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
