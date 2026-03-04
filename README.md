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
   source .venv/Scripts/activate  # or .venv\Scripts\activate on Windows CMD
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
                                   +-- Deepgram STT (speech-to-text)
                                   +-- DeepL / MyMemory (translation)
                                   +-- Google Cloud TTS (text-to-speech)
```

## Translation Pipeline

1. Speaker presses "Hold to Speak" and talks
2. Audio is captured and sent to backend via WebSocket
3. Backend runs: STT -> Translation -> TTS
4. Translated audio + transcript sent back to frontend
5. Other speaker hears the translation and sees the transcript

## Development

```bash
# Run backend tests
cd backend && python -m pytest tests/ -v

# Build frontend
cd frontend && npm run build

# Run E2E test (requires API keys in .env)
cd backend && RUN_E2E_TESTS=1 python -m pytest tests/test_e2e.py -v -s
```

## Supported Languages

- Vietnamese (vi)
- Russian (ru)
- English (en)
