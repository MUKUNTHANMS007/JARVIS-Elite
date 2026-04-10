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
  const mediaRecorder = useRef<MediaRecorder | null>(null);
  const retryCount = useRef(0);
  const retryTimer = useRef<number | undefined>(undefined);
  const pingTimer = useRef<number | undefined>(undefined);
  const currentAssistantMsg = useRef<string>("");

  const [messages, setMessages] = useState<JarvisMessage[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [isThinking, setIsThinking] = useState(false);
  const { playRawChunk, initAudio, isSpeaking: isWorkletSpeaking } = useJarvisAudio();
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [mood, setMood] = useState("normal");

  // Sync isSpeaking with the high-priority thread state
  useEffect(() => {
    setIsSpeaking(isWorkletSpeaking);
  }, [isWorkletSpeaking]);

  const MAX_RETRIES = 8;

  const connect = useCallback(() => {
    if (ws.current?.readyState === WebSocket.OPEN) return;

    const socket = new WebSocket(url);
    socket.binaryType = "arraybuffer";
    ws.current = socket;

    socket.onopen = () => {
      setIsConnected(true);
      retryCount.current = 0;
      console.log("[Jarvis] Neural link established.");

      // Heartbeat — pong backend pings
      pingTimer.current = window.setInterval(() => {
        if (socket.readyState === WebSocket.OPEN) {
          socket.send(JSON.stringify({ type: "PONG" }));
        }
      }, 25000);

      // Warm up the AudioWorklet thread
      initAudio();
    };

    socket.onmessage = (event) => {
      if (event.data instanceof ArrayBuffer) {
        // High-priority audio stream offloaded to Worklet thread
        playRawChunk(event.data);
        return;
      }

      const msg = JSON.parse(event.data as string);

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
    };

    socket.onclose = (e) => {
      setIsConnected(false);
      clearInterval(pingTimer.current);
      console.warn(`[Jarvis] Disconnected. Code: ${e.code}`);

      if (e.code !== 1000 && retryCount.current < MAX_RETRIES) {
        const delay = Math.min(1000 * 2 ** retryCount.current, 30000);
        retryCount.current++;
        console.log(`[Jarvis] Reconnecting in ${delay}ms (attempt ${retryCount.current})`);
        retryTimer.current = window.setTimeout(connect, delay);
      }
    };

    socket.onerror = () => socket.close();
  }, [url, initAudio, playRawChunk]);

  const startRecording = useCallback(async (imageFrame: string | null = null) => {
    if (!ws.current || ws.current.readyState !== WebSocket.OPEN) return;

    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    const recorder = new MediaRecorder(stream, { mimeType: "audio/webm" });
    mediaRecorder.current = recorder;

    ws.current.send(JSON.stringify({ type: "AUDIO_START", image: imageFrame }));
    setIsRecording(true);

    recorder.ondataavailable = (e) => {
      if (e.data.size > 0 && ws.current?.readyState === WebSocket.OPEN) {
        ws.current.send(e.data);
      }
    };

    recorder.start(100); // 100ms chunks for low latency
  }, []);

  const stopRecording = useCallback(() => {
    mediaRecorder.current?.stop();
    mediaRecorder.current?.stream.getTracks().forEach(t => t.stop());
    setIsRecording(false);

    if (ws.current?.readyState === WebSocket.OPEN) {
      ws.current.send(JSON.stringify({ type: "stop_recording" }));
    }
  }, []);

  const sendTextMessage = useCallback((text: string, image: string | null = null) => {
    if (!ws.current || ws.current.readyState !== WebSocket.OPEN) return;
    ws.current.send(JSON.stringify({ type: "text_input", text, image }));
  }, []);

  const reconnect = useCallback(() => {
    clearTimeout(retryTimer.current);
    retryCount.current = 0;
    ws.current?.close(1000);
    connect();
  }, [connect]);

  const clearMessages = useCallback(() => setMessages([]), []);

  useEffect(() => {
    connect();
    return () => {
      clearTimeout(retryTimer.current);
      clearInterval(pingTimer.current);
      ws.current?.close(1000);
    };
  }, [connect]);

  return {
    messages,
    isConnected,
    isRecording,
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
