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
