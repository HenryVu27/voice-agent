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
