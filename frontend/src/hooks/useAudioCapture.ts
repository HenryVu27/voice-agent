import { useRef, useState, useCallback } from "react";

interface UseAudioCaptureOptions {
  onAudioChunk: (base64Audio: string) => void;
  sampleRate?: number;
}

export function useAudioCapture({ onAudioChunk, sampleRate = 16000 }: UseAudioCaptureOptions) {
  const [isRecording, setIsRecording] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);

  const startRecording = useCallback(async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          sampleRate,
          channelCount: 1,
          echoCancellation: true,
          noiseSuppression: true,
        },
      });

      const mediaRecorder = new MediaRecorder(stream, {
        mimeType: "audio/webm;codecs=opus",
      });

      chunksRef.current = [];

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          chunksRef.current.push(event.data);
        }
      };

      mediaRecorder.start(100);
      mediaRecorderRef.current = mediaRecorder;
      setIsRecording(true);
      setError(null);
    } catch (err) {
      setError(
        err instanceof DOMException && err.name === "NotAllowedError"
          ? "Microphone permission denied. Please allow microphone access."
          : "Failed to access microphone."
      );
    }
  }, [sampleRate]);

  const stopRecording = useCallback((): Promise<string> => {
    return new Promise((resolve) => {
      const mediaRecorder = mediaRecorderRef.current;
      if (!mediaRecorder || mediaRecorder.state === "inactive") {
        resolve("");
        return;
      }

      mediaRecorder.onstop = async () => {
        const blob = new Blob(chunksRef.current, { type: "audio/webm" });
        const buffer = await blob.arrayBuffer();
        const base64 = btoa(
          new Uint8Array(buffer).reduce(
            (data, byte) => data + String.fromCharCode(byte),
            ""
          )
        );

        mediaRecorder.stream.getTracks().forEach((track) => track.stop());
        setIsRecording(false);
        onAudioChunk(base64);
        resolve(base64);
      };

      mediaRecorder.stop();
    });
  }, [onAudioChunk]);

  return { isRecording, startRecording, stopRecording, error };
}
