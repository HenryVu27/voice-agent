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
