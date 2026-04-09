import { useState, useEffect, useRef, useCallback } from 'react';
import { supabase } from '../utils/supabaseClient';
import { NeuralPacket } from '../types/neural_protocol';
import * as protobuf from 'protobufjs';

const PROTO_SCHEMA = `
syntax = "proto3";
package jarvis.protocol;

message Telemetry {
    float cpu_percent = 1;
    float ram_percent = 2;
    float mood_score = 3;
    bool is_online = 4;
}

message DashboardMetrics {
    int32 unread_mail = 1;
    string spotify_track = 2;
    int32 reminder_count = 3;
    string leetcode_status_json = 4;
    string github_pulse_json = 5;
}

message ProactiveAlert {
    string id = 1;
    string type = 2;
    string title = 3;
    string message = 4;
    double timestamp = 5;
    string priority = 6;
}

enum AgentState {
    IDLE = 0;
    THINKING = 1;
    SPEAKING = 2;
    LISTENING = 3;
    TOOL_EXECUTING = 4;
}

message NeuralPacket {
    string type = 1;
    double timestamp = 2;
    AgentState state = 3;
    Telemetry telemetry = 4;
    DashboardMetrics dashboard = 5;
    string active_tool = 6;
    ProactiveAlert alert = 7;
}
`;

/**
 * JARVIS Unified System Socket Hook (Sentinel Edition) - Advanced Protocol Support
 */
export function useSystemSocket(url: string) {
  const [data, setData] = useState<NeuralPacket | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const socketRef = useRef<WebSocket | null>(null);
  const protoRootRef = useRef<protobuf.Root | null>(null);
  const retryCountRef = useRef(0);
  const maxRetries = 5;
  const RECONNECT_INTERVAL = 3000;

  // --- 0. NEURAL PROTOCOL INITIALIZATION ---
  useEffect(() => {
    try {
      const root = protobuf.parse(PROTO_SCHEMA).root;
      protoRootRef.current = root;
      console.log("[Neural Protocol] Binary decoder initialized.");
    } catch (e) {
      console.error("[Neural Protocol] Shader/Proto initialization drift:", e);
    }
  }, []);

  // --- SENTINEL CLOUD MIRROR (Initial Mirror Sync) ---
  useEffect(() => {
    async function fetchLastKnownState() {
      try {
        const { data: sentinel, error } = await supabase
          .from('neural_sentinel')
          .select('state_json')
          .eq('user_id', 'JARVIS_ADMIN')
          .single();

        if (sentinel && sentinel.state_json && !isConnected) {
          setData(sentinel.state_json as NeuralPacket);
          console.log("[Neural Sentinel] Initial mirror sync established from Cloud.");
        }
      } catch (err) {
        console.warn("[Neural Sentinel] Cloud mirror unavailable:", err);
      }
    }

    if (!isConnected) {
      fetchLastKnownState();
    }
  }, [isConnected]);

  const connect = useCallback(() => {
    if (socketRef.current && (socketRef.current.readyState === WebSocket.OPEN || socketRef.current.readyState === WebSocket.CONNECTING)) {
        return;
    }

    console.log(`[Neural Hub] Attempting connection... (Retry: ${retryCountRef.current})`);
    const ws = new WebSocket(url);
    ws.binaryType = "arraybuffer"; // Support binary packets
    socketRef.current = ws;

    ws.onopen = () => {
      setIsConnected(true);
      retryCountRef.current = 0;
      console.log("[Neural Hub] Unified telemetry link established.");

      const heartbeat = setInterval(() => {
        if (ws.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify({ type: 'PING' }));
        }
      }, 10000);
      (ws as any)._heartbeat = heartbeat;
    };

    ws.onmessage = (event) => {
      try {
        let parsed: any;
        
        if (event.data instanceof ArrayBuffer) {
          // --- BINARY DECODING (Protobuf) ---
          if (!protoRootRef.current) return;
          const NeuralPacketProto = protoRootRef.current.lookupType("jarvis.protocol.NeuralPacket");
          const buffer = new Uint8Array(event.data);
          const decoded = NeuralPacketProto.decode(buffer);
          const rawObject = NeuralPacketProto.toObject(decoded, {
              enums: String,
              longs: Number,
              defaults: true
          }) as any;

          // --- NEURAL TRANSFORMATION (Mapping Proto -> UI Schema) ---
          parsed = {
            ...rawObject,
            dashboard: rawObject.dashboard ? {
              ...rawObject.dashboard,
              leetcode_status: rawObject.dashboard.leetcode_status_json ? JSON.parse(rawObject.dashboard.leetcode_status_json) : null,
              github_pulse: rawObject.dashboard.github_pulse_json ? JSON.parse(rawObject.dashboard.github_pulse_json) : null
            } : undefined
          };
        } else {
          // --- JSON FALLBACK ---
          parsed = JSON.parse(event.data);
        }

        if (parsed.type === "PONG") return;
        
        if (["NEURAL_PULSE", "AGENT_STATE_CHANGE", "PROACTIVE_ALERT"].includes(parsed.type)) {
          setData(parsed as NeuralPacket);
        }
      } catch (e) {
        console.error("[Neural Hub] Parse error:", e);
      }
    };

    ws.onclose = (e) => {
      setIsConnected(false);
      if ((ws as any)._heartbeat) clearInterval((ws as any)._heartbeat);
      
      // Detach self for clean retry
      ws.onclose = null;
      
      if (e.code !== 1000 && retryCountRef.current < maxRetries) {
        const delay = Math.min(RECONNECT_INTERVAL * 2 ** retryCountRef.current, 30000);
        retryCountRef.current++;
        console.warn(`[Neural Hub] Link severed. Retrying in ${delay}ms...`);
        setTimeout(connect, delay);
      }
    };

    ws.onerror = () => {
      if (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING) {
          ws.close();
      }
    };
  }, [url]);

  useEffect(() => {
    connect();
    return () => {
      if (socketRef.current) {
        const ws = socketRef.current;
        // Detach listeners to prevent unexpected reconnection logic
        ws.onopen = null; ws.onmessage = null; ws.onerror = null; ws.onclose = null;
        
        if ((ws as any)._heartbeat) clearInterval((ws as any)._heartbeat);

        if (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING) {
          ws.close(1000, "Unmount");
        }
        socketRef.current = null;
      }
    };
  }, [connect]);

  return { data, isConnected };
}
