import { useEffect, useRef, useState, useCallback } from "react";
import { useJarvisAudio } from "./useJarvisAudio";

type MessageType = "TRANSCRIPTION" | "TEXT_CHUNK" | "TURN_START" | "TURN_COMPLETE" | "ERROR" | "PING";

interface JarvisMessage {
  role: "user" | "assistant";
  content: string;
  timestamp: number;
}

interface UseJarvisSocketReturn {
  messages: JarvisMessage[];
  isConnected: boolean;
  isRecording: boolean;
  isThinking: boolean;
  isSpeaking: boolean;
  mood: string;
  setIsThinking: (val: boolean) => void;
  startRecording: (imageFrame?: string | null) => Promise<void>;
  stopRecording: () => void;
  sendTextMessage: (text: string, image?: string | null) => void;
  reconnect: () => void;
  clearMessages: () => void;
}

export function useAudioSocket(url: string): UseJarvisSocketReturn {
  const ws = useRef<WebSocket | null>(null);
  const retryCount = useRef(0);
  const retryTimer = useRef<number | undefined>(undefined);
  const pingTimer = useRef<number | undefined>(undefined);
  const currentAssistantMsg = useRef<string>("");
  const shouldReconnect = useRef(true);

  const [messages, setMessages] = useState<JarvisMessage[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const [isThinking, setIsThinking] = useState(false);
  const [mood, setMood] = useState("normal");

  const { isSpeaking, playRawChunk, initAudio } = useJarvisAudio();

  const MAX_RETRIES = 8;

  const connect = useCallback(() => {
    if (ws.current?.readyState === WebSocket.OPEN || ws.current?.readyState === WebSocket.CONNECTING) return;

    const socket = new WebSocket(url);
    socket.binaryType = 'arraybuffer';
    ws.current = socket;

    socket.onopen = async () => {
      setIsConnected(true);
      retryCount.current = 0;
      console.log("[Jarvis] Neural link established.");

      // Heartbeat — pong backend pings
      pingTimer.current = window.setInterval(() => {
        if (socket.readyState === WebSocket.OPEN) {
          socket.send(JSON.stringify({ type: "PONG" }));
        }
      }, 25000);
    };

    socket.onmessage = async (event) => {
      if (typeof event.data === 'string') {
        const msg = JSON.parse(event.data);

        switch (msg.type as MessageType) {
          case "PING":
            socket.send(JSON.stringify({ type: "PONG" }));
            break;

          case "TRANSCRIPTION":
            setMessages(prev => [...prev, {
              role: "user",
              content: msg.text,
              timestamp: Date.now()
            }]);
            break;

          case "TURN_START":
            setIsThinking(true);
            if (msg.mood) setMood(msg.mood);
            currentAssistantMsg.current = "";
            break;

          case "TEXT_CHUNK":
            currentAssistantMsg.current += msg.text;
            setMessages(prev => {
              const last = prev[prev.length - 1];
              if (last?.role === "assistant") {
                return [...prev.slice(0, -1), {
                  ...last,
                  content: currentAssistantMsg.current
                }];
              }
              return [...prev, {
                role: "assistant",
                content: currentAssistantMsg.current,
                timestamp: Date.now()
              }];
            });
            break;

          case "TURN_COMPLETE":
            setIsThinking(false);
            currentAssistantMsg.current = "";
            break;

          case "ERROR":
            console.error("[Jarvis] Agent error:", msg.message);
            setIsThinking(false);
            break;
        }
      } else {
        if (event.data instanceof ArrayBuffer) {
          await playRawChunk(event.data);
        }
      }
    };

    socket.onclose = (e) => {
      setIsConnected(false);
      clearInterval(pingTimer.current);
      console.warn(`[Jarvis] Disconnected. Code: ${e.code}`);

      if (shouldReconnect.current && retryCount.current < MAX_RETRIES) {
        const delay = Math.min(1000 * 2 ** retryCount.current, 30000);
        retryCount.current++;
        console.log(`[Jarvis] Reconnecting in ${delay}ms (attempt ${retryCount.current})`);
        retryTimer.current = window.setTimeout(connect, delay);
      }
    };

    socket.onerror = () => socket.close();
  }, [url, playRawChunk]);

  const startRecording = useCallback(async (imageFrame: string | null = null) => {
    // Voice control disabled
  }, []);

  const stopRecording = useCallback(() => {
    // Voice control disabled
  }, []);

  const sendTextMessage = useCallback(async (text: string, image: string | null = null) => {
    await initAudio();
    if (!ws.current || ws.current.readyState !== WebSocket.OPEN) return;
    ws.current.send(JSON.stringify({ type: "text_input", text, image }));
  }, [initAudio]);

  const reconnect = useCallback(() => {
    clearTimeout(retryTimer.current);
    retryCount.current = 0;
    ws.current?.close(1000);
    connect();
  }, [connect]);

  const clearMessages = useCallback(() => setMessages([]), []);

  useEffect(() => {
    shouldReconnect.current = true;
    connect();
    return () => {
      shouldReconnect.current = false;
      clearTimeout(retryTimer.current);
      clearInterval(pingTimer.current);
      ws.current?.close(1000);
    };
  }, [connect]);

  return {
    messages,
    isConnected,
    isRecording: false,
    isThinking,
    isSpeaking,
    mood,
    setIsThinking,
    startRecording,
    stopRecording,
    sendTextMessage,
    reconnect,
    clearMessages
  };
}
