import { useRef, useState, useCallback, useEffect } from "react";
import type { ClientMessage, ServerMessage } from "@/lib/types";

interface UseWebSocketOptions {
  url: string;
  onMessage: (message: ServerMessage) => void;
  reconnectInterval?: number;
}

export function useWebSocket({ url, onMessage, reconnectInterval = 3000 }: UseWebSocketOptions) {
  const wsRef = useRef<WebSocket | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    const ws = new WebSocket(url);

    ws.onopen = () => {
      setIsConnected(true);
    };

    ws.onmessage = (event) => {
      const data: ServerMessage = JSON.parse(event.data);
      onMessage(data);
    };

    ws.onclose = () => {
      setIsConnected(false);
      reconnectTimer.current = setTimeout(connect, reconnectInterval);
    };

    ws.onerror = () => {
      ws.close();
    };

    wsRef.current = ws;
  }, [url, onMessage, reconnectInterval]);

  const disconnect = useCallback(() => {
    clearTimeout(reconnectTimer.current);
    wsRef.current?.close();
    wsRef.current = null;
  }, []);

  const send = useCallback((message: ClientMessage) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(message));
    }
  }, []);

  useEffect(() => {
    connect();
    return disconnect;
  }, [connect, disconnect]);

  return { isConnected, send, disconnect };
}
