export type Speaker = "a" | "b";
export type Language = "vi" | "ru" | "en";

// Client -> Server
export interface AudioChunkMessage {
  type: "audio_chunk";
  data: string;
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
  data: string;
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
