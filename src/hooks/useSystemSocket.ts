import { useEffect, useMemo, useRef, useState, useCallback } from "react";
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
  const candidateIndex = useRef(0);
  const shouldReconnect = useRef(true);
  const MAX_RETRIES = 10;

  const [packet, setPacket] = useState<SystemPacket | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [latency, setLatency] = useState<number>(0);

  const urlCandidates = useMemo(() => {
    const candidates = [url];
    try {
      const parsed = new URL(url);
      if (parsed.hostname === "localhost") {
        parsed.hostname = "127.0.0.1";
        candidates.push(parsed.toString());
      }
    } catch {
      // Keep the original URL if parsing fails.
    }
    return Array.from(new Set(candidates));
  }, [url]);

  const syncUrlCandidates = useMemo(() => {
    return urlCandidates.map((candidate) => {
      try {
        const parsed = new URL(candidate);
        parsed.protocol = parsed.protocol === "wss:" ? "https:" : "http:";
        parsed.pathname = "/api/sync";
        parsed.search = "";
        parsed.hash = "";
        return parsed.toString();
      } catch {
        return "";
      }
    }).filter(Boolean);
  }, [urlCandidates]);

  const applyPacket = useCallback((data: any) => {
    if (data.ts) {
      setLatency(Math.max(0, Math.round((Date.now() / 1000 - data.ts) * 1000)));
      data.timestamp = data.ts;
    }

    if (data.type === "SYSTEM_PULSE") data.type = "NEURAL_PULSE";
    data.state = data.state || "IDLE";
    setPacket(data as SystemPacket);
  }, []);

  const applySyncData = useCallback((syncData: any) => {
    if (!syncData) return;
    const intel = syncData.intelligence || {};
    applyPacket({
      type: "NEURAL_PULSE",
      dashboard: {
        unread_mail: intel.gmail_unread ?? 0,
        briefing: intel.gmail_briefing ?? intel.intelligence_briefing ?? "",
        leetcode: intel.leetcode ?? {},
        github: intel.github ?? {},
        spotify_track: intel.spotify_track ?? "Standby",
        spotify_image: intel.spotify_image ?? null,
        is_batman_mode: intel.batman_mode ?? false,
        last_synced: intel.last_synced ?? "",
        proactive_trigger: null,
      },
      status: syncData.system ?? {},
      focus: syncData.focus ?? null,
      ts: Date.now() / 1000,
    });
  }, [applyPacket]);

  const connect = useCallback(() => {
    if (ws.current?.readyState === WebSocket.OPEN || ws.current?.readyState === WebSocket.CONNECTING) {
      console.log("[System WS] Already open or connecting, skipping connect.");
      return;
    }

    const candidateUrl = urlCandidates[candidateIndex.current % urlCandidates.length] || url;
    console.log("[System WS] Connecting to:", candidateUrl);
    const socket = new WebSocket(candidateUrl);
    let opened = false;
    ws.current = socket;

    socket.onopen = () => {
      if (ws.current === socket) {
        opened = true;
        console.log("[System WS] Connected successfully.");
        setIsConnected(true);
        retryCount.current = 0;
      } else {
        console.log("[System WS] onopen ignored - socket replaced.");
        socket.close();
      }
    };

    socket.onmessage = (event) => {
      if (ws.current !== socket) {
        socket.close();
        return;
      }
      try {
        const data: any = JSON.parse(event.data);
        applyPacket(data);
      } catch (err) {
        console.error("[System WS] Error parsing message:", err);
      }
    };

    socket.onclose = (e) => {
      const logClose = opened ? console.warn : console.debug;
      logClose(`[System WS] Closed. URL: ${candidateUrl}, Code: ${e.code}, Reason: ${e.reason || "none"}`);
      if (ws.current === socket) {
        setIsConnected(false);
        if (e.code === 4401) {
          console.error("[System WS] Connection rejected: Unauthorized (Code 4401).");
          shouldReconnect.current = false;
          return;
        }
        if (shouldReconnect.current && retryCount.current < MAX_RETRIES) {
          if (!opened && urlCandidates.length > 1) {
            candidateIndex.current = (candidateIndex.current + 1) % urlCandidates.length;
          }
          const delay = Math.min(1000 * 2 ** retryCount.current, 30000);
          retryCount.current++;
          console.log(`[System WS] Scheduling reconnect in ${delay}ms`);
          retryTimer.current = window.setTimeout(connect, delay);
        }
      } else {
        console.log("[System WS] Stale close event ignored.");
      }
    };

    socket.onerror = () => {
      console.debug(`[System WS] Socket error on ${candidateUrl}; reconnect fallback will handle it.`);
      socket.close();
    };
  }, [applyPacket, url, urlCandidates]);

  useEffect(() => {
    shouldReconnect.current = true;
    connect();
    return () => {
      shouldReconnect.current = false;
      clearTimeout(retryTimer.current);
      ws.current?.close(1000);
    };
  }, [connect]);

  useEffect(() => {
    const pollSync = async () => {
      if (ws.current?.readyState === WebSocket.OPEN) return;

      for (const syncUrl of syncUrlCandidates) {
        try {
          const response = await fetch(syncUrl);
          if (!response.ok) continue;
          applySyncData(await response.json());
          return;
        } catch {
          // Try the next loopback candidate.
        }
      }
    };

    const interval = window.setInterval(pollSync, 5000);
    pollSync();
    return () => window.clearInterval(interval);
  }, [applySyncData, syncUrlCandidates]);

  return { data: packet, isConnected, latency };
}
