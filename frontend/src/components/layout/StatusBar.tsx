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
