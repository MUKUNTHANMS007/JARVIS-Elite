import { useState, useEffect, useRef } from 'react';

/**
 * JARVIS Neural Pulse Hook
 * Unified telemetry listener for consolidated System + Dashboard push.
 * Replaces high-frequency HTTP polling.
 */
export function usePulse(url: string) {
  const [pulseData, setPulseData] = useState<any>(null);
  const [isConnected, setIsConnected] = useState(false);
  const socketRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    const connect = () => {
      const ws = new WebSocket(url);
      socketRef.current = ws;

      ws.onopen = () => {
        setIsConnected(true);
        console.log("[Neural Pulse] Telemetry Link Established.");
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.type === "SYSTEM_PULSE") {
            setPulseData(data);
          }
        } catch (e) {
          console.error("[Neural Pulse] Telemetry Parse Error:", e);
        }
      };

      ws.onclose = () => {
        setIsConnected(false);
        // Exponential backoff or simple retry
        setTimeout(connect, 3000);
      };

      ws.onerror = () => ws.close();
    };

    connect();
    return () => socketRef.current?.close();
  }, [url]);

  return { pulseData, isConnected };
}
