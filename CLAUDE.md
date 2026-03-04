# VoiceBridge - Live Translation App

## Project Overview

Real-time bidirectional speech translation app for PTSC Vietnam (oil & gas).
Primary use case: Vietnamese <-> Russian live conversation translation.
Built for a director who needs to communicate across language barriers.

## Tech Stack

### Frontend
- React 18+ with TypeScript
- Vite build tool
- Tailwind CSS + shadcn/ui components
- Web Audio API for mic capture
- WebSocket for real-time streaming
- framer-motion for transitions

### Backend
- Python 3.11+
- FastAPI with WebSocket support
- uvicorn ASGI server

### External APIs (POC Phase)
- **STT:** Deepgram Nova-3 (streaming WebSocket, ~150ms latency)
- **Translation:** DeepL API (best quality for Vi<->Ru)
- **TTS:** Google Cloud TTS (good Vietnamese + Russian voices)

### Future Self-Hosted (Post-POC)
- STT: Whisper / faster-whisper
- Translation: NLLB-200 / Opus-MT
- TTS: Qwen3-TTS (voice cloning capable)
- Voice cloning: OpenVoice / Qwen3-TTS

## Architecture

Cascaded pipeline: STT -> Translation -> TTS
Each stage is independently swappable. All communication via WebSocket streaming.

```
Frontend (React) <--WebSocket--> Backend (FastAPI)
                                    |
                                    ├── Deepgram STT (streaming)
                                    ├── DeepL Translation
                                    └── Google Cloud TTS
```

## Project Structure

```
voice-agent/
├── CLAUDE.md
├── frontend/              # React Vite app
│   ├── src/
│   │   ├── components/
│   │   │   ├── ui/        # shadcn/ui components
│   │   │   ├── layout/    # Header, StatusBar
│   │   │   └── translation/  # SpeakerPanel, TranscriptView
│   │   ├── hooks/         # useAudioCapture, useWebSocket, useTranslation
│   │   ├── lib/           # utils, audio helpers
│   │   ├── pages/         # ConversationPage
│   │   └── styles/        # global CSS, tokens
│   └── ...
├── backend/               # Python FastAPI
│   ├── app/
│   │   ├── main.py        # FastAPI app, WebSocket endpoint
│   │   ├── pipeline/      # STT, translation, TTS orchestration
│   │   │   ├── stt.py     # Deepgram client
│   │   │   ├── translator.py  # DeepL client
│   │   │   └── tts.py     # Google TTS client
│   │   ├── models/        # Pydantic schemas
│   │   └── config.py      # API keys, settings
│   ├── requirements.txt
│   └── ...
├── docs/
│   └── plans/
└── .env                   # API keys (gitignored)
```

## Development Guidelines

- POC first: get the pipeline working end-to-end before optimizing
- Measure latency at every stage - log timestamps for STT, translation, TTS
- Each pipeline stage must be independently testable and swappable
- Use environment variables for all API keys (.env file, never commit)
- WebSocket messages use JSON with a consistent schema:
  - `{ type: "audio_chunk", data: base64, speaker: "a"|"b", language: "vi"|"ru" }`
  - `{ type: "transcript", original: string, translated: string, speaker: "a"|"b" }`
  - `{ type: "audio_response", data: base64, language: "vi"|"ru" }`
  - `{ type: "error", message: string }`
- Frontend audio: capture at 16kHz mono PCM for STT compatibility
- Push-to-talk for POC (simpler than voice activity detection)

## Supported Languages (POC)
- Vietnamese (vi)
- Russian (ru)
- English (en) - useful for testing / fallback

## Iteration Roadmap
1. **POC (current):** Cascaded pipeline, push-to-talk, cloud APIs, single device
2. **V1:** Streaming overlap, voice activity detection, latency optimization, voice cloning
3. **V2:** Multi-device sessions, meeting mode, domain glossary (oil & gas terms)
4. **V3:** Offline fallback, presentation/broadcast mode, self-hosted models

## Commands

```bash
# Frontend
cd frontend && npm install && npm run dev

# Backend
cd backend && pip install -r requirements.txt && uvicorn app.main:app --reload

# Both (from root)
# TODO: add a root script or docker-compose
```
