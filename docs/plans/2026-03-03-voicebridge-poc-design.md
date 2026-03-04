# VoiceBridge POC Design

**Date:** 2026-03-03
**Status:** Approved
**Client:** PTSC Vietnam (Oil & Gas)

## Problem

A director at PTSC Vietnam needs real-time translation between Vietnamese and Russian speakers. No clear format specified - could be meetings, phone calls, or day-to-day communication.

## Solution

A web-based live translation app ("VoiceBridge") with a modular translation engine. The POC targets **Conversation Mode**: two speakers on one device, push-to-talk, bidirectional translation with live transcripts.

## Architecture

### Pipeline: Cascaded STT -> Translation -> TTS

```
Speaker A (Vietnamese)
  └─> Mic capture (Web Audio API, 16kHz mono)
      └─> WebSocket to backend
          └─> Deepgram STT (streaming) -> Vietnamese text
              └─> DeepL API -> Russian text
                  └─> Google Cloud TTS -> Russian audio
                      └─> WebSocket to frontend -> Speaker B hears Russian

Speaker B (Russian) follows the reverse path.
```

Each stage is independent and swappable. Latency budget:
- STT: ~150-300ms
- Translation: ~100-200ms
- TTS: ~100-200ms
- Network/overhead: ~100ms
- **Total target: < 1 second**

### Why Cascaded (not streaming or E2E)

- Simplest to build and debug
- Each component testable in isolation
- Easy to swap providers or move to self-hosted
- Streaming overlap optimization is a clean addition later
- E2E models (SeamlessM4T) have weak Vi<->Ru support

## Tech Stack

### Frontend
- React 18 + TypeScript + Vite
- Tailwind CSS + shadcn/ui
- Web Audio API for mic capture
- WebSocket client for real-time communication
- framer-motion for UI transitions

### Backend
- Python 3.11+ / FastAPI
- WebSocket endpoint for bidirectional audio/text streaming
- Async pipeline orchestration

### External APIs
| Stage | Provider | Why |
|-------|----------|-----|
| STT | Deepgram Nova-3 | Streaming WebSocket, ~150ms, good Vi support |
| Translation | DeepL | Best quality for Vi<->Ru pair |
| TTS | Google Cloud TTS | Reliable Vi + Ru voices, low cost |

## UI Design

Conversation Mode - split screen:

```
┌──────────────────────────────────────────────┐
│  VoiceBridge        [Vi <-> Ru]    [Settings] │
├──────────────────────┬───────────────────────┤
│  SPEAKER A           │  SPEAKER B            │
│  Vietnamese          │  Russian              │
│                      │                       │
│  [Live transcript]   │  [Live transcript]    │
│  Original: ...       │  Original: ...        │
│  Translated: ...     │  Translated: ...      │
│                      │                       │
│  [Push to Talk btn]  │  [Push to Talk btn]   │
├──────────────────────┴───────────────────────┤
│  Latency: 0.6s | Session: 4:32 | Connected   │
└──────────────────────────────────────────────┘
```

- Push-to-talk per speaker side
- Dual transcript (original + translated) on each side
- Status bar with latency measurement
- Mobile responsive (vertical stack on small screens)

## WebSocket Message Schema

```typescript
// Client -> Server
{ type: "audio_chunk", data: string (base64), speaker: "a" | "b", language: "vi" | "ru" }
{ type: "start_speaking", speaker: "a" | "b" }
{ type: "stop_speaking", speaker: "a" | "b" }

// Server -> Client
{ type: "transcript", original: string, translated: string, speaker: "a" | "b" }
{ type: "audio_response", data: string (base64), language: "vi" | "ru" }
{ type: "status", latency_ms: number }
{ type: "error", message: string }
```

## Error Handling

- API timeout: retry once, then show error toast
- WebSocket disconnect: auto-reconnect with exponential backoff
- Mic permission denied: clear instructions prompt
- No speech detected: "No speech detected" message after timeout

## Out of Scope (POC)

- Voice cloning / voice preservation
- Multi-device sessions
- Voice activity detection (using push-to-talk instead)
- Offline mode
- Meeting mode / speaker diarization
- Domain-specific vocabulary
- User accounts / authentication

## Competitive Landscape

- **Google Translate Conversation Mode**: Similar concept but generic, no customization
- **Palabra.ai**: Live translation for events, API available, < 1s latency
- **PolyAI**: Enterprise voice AI for contact centers (not translation), but validates natural voice AI at scale. $86M Series D, 45 languages, excellent voice quality.

## Iteration Plan

1. **POC (this)**: Prove the pipeline works, measure latency, basic UI
2. **V1**: Streaming overlap, VAD, voice cloning, latency optimization
3. **V2**: Multi-device, meeting mode, oil & gas glossary
4. **V3**: Offline fallback, broadcast mode, self-hosted models

## Cost Estimate (API-based)

~$0.04-0.06 per minute of conversation (both directions).
A 1-hour meeting costs ~$2-3 in API fees.
