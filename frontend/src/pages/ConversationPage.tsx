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
  const audioRef = useRef<HTMLAudioElement>(null);

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

      case "audio_response": {
        const audioSrc = `data:audio/mp3;base64,${msg.data}`;
        if (audioRef.current) {
          audioRef.current.src = audioSrc;
          audioRef.current.play().catch(() => {});
        }
        break;
      }

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

  const { isRecording, startRecording, stopRecording, error } =
    useAudioCapture({
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
      <Header languagePair="Vi ↔ Ru" />

      {error && (
        <div className="px-6 py-3 bg-red-50 text-red-700 text-sm">
          {error}
        </div>
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
