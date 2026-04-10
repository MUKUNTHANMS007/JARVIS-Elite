import { useEffect, useRef, useState, useCallback } from "react";
import { NeuralPacket, AgentState } from "../types/neural_protocol";

interface SystemPacket extends Omit<NeuralPacket, 'type' | 'timestamp' | 'telemetry' | 'dashboard'> {
  type: "NEURAL_PULSE" | "AGENT_STATE_CHANGE" | "PROACTIVE_ALERT";
  ts: number;
  timestamp: number;
  state: AgentState;
  dashboard: {
    unread_mail: number;
    briefing: string;
    leetcode: any;
    github: any;
    spotify_track: string;
    spotify_image: string | null;
    is_batman_mode: boolean;
    last_synced: string;
    proactive_trigger?: any;
  };
  status: {
    cpu: number;
    ram: number;
    disk: number;
    energy: number;
    uptime: string;
  };
  telemetry: any;
}

export function useSystemSocket(url: string) {
  const ws = useRef<WebSocket | null>(null);
  const retryCount = useRef(0);
  const retryTimer = useRef<number | undefined>(undefined);
  const MAX_RETRIES = 10;

  const [packet, setPacket] = useState<SystemPacket | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [latency, setLatency] = useState<number>(0);

  const connect = useCallback(() => {
    const socket = new WebSocket(url);
    ws.current = socket;

    socket.onopen = () => {
      setIsConnected(true);
      retryCount.current = 0;
    };

    socket.onmessage = (event) => {
      const data: any = JSON.parse(event.data);
      if (data.ts) {
        setLatency(Math.round((Date.now() / 1000 - data.ts) * 1000));
        data.timestamp = data.ts;
      }
      
      // Normalize type for NeuralCore
      if (data.type === "SYSTEM_PULSE") data.type = "NEURAL_PULSE";
      
      data.state = data.state || "IDLE";
      setPacket(data as SystemPacket);
    };

    socket.onclose = (e) => {
      setIsConnected(false);
      if (e.code !== 1000 && retryCount.current < MAX_RETRIES) {
        const delay = Math.min(1000 * 2 ** retryCount.current, 30000);
        retryCount.current++;
        retryTimer.current = window.setTimeout(connect, delay);
      }
    };

    socket.onerror = () => socket.close();
  }, [url]);

  useEffect(() => {
    connect();
    return () => {
      clearTimeout(retryTimer.current);
      ws.current?.close(1000);
    };
  }, [connect]);

  return { data: packet, isConnected, latency };
}
