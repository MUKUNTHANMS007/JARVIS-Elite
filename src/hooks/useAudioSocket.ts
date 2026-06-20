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
  const audioReceivedThisTurn = useRef(false);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const mediaStreamRef = useRef<MediaStream | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const pendingImageRef = useRef<string | null>(null);
  const shouldReconnect = useRef(true);

  const speakWithBrowserTTS = useCallback((text: string) => {
    if (!text.trim() || !("speechSynthesis" in window)) return;
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.rate = 1.0;
    utterance.pitch = 0.95;
    const voices = window.speechSynthesis.getVoices();
    const preferred = voices.find(v =>
      v.lang.startsWith("en-GB") || v.name.toLowerCase().includes("ryan") || v.name.toLowerCase().includes("daniel")
    ) ?? voices.find(v => v.lang.startsWith("en"));
    if (preferred) utterance.voice = preferred;
    window.speechSynthesis.speak(utterance);
  }, []);

  const [messages, setMessages] = useState<JarvisMessage[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [isThinking, setIsThinking] = useState(false);
  const [mood, setMood] = useState("normal");

  const { isSpeaking, playRawChunk, initAudio } = useJarvisAudio();

  // Serialize binary audio chunk handling. WebSocket.onmessage fires in
  // arrival order, but since the handler is async, a slow chunk (e.g. an
  // MP3 fallback chunk going through decodeAudioData) can resolve AFTER a
  // later, faster PCM chunk - causing audio to be posted to the worklet
  // out of order (garbled/stuttering playback). This chain guarantees
  // strictly in-order processing no matter how long each chunk takes.
  const audioChainRef = useRef<Promise<void>>(Promise.resolve());

  const MAX_RETRIES = 8;

  const blobToBase64 = useCallback((blob: Blob) => {
    return new Promise<string>((resolve, reject) => {
      const reader = new FileReader();
      reader.onloadend = () => {
        const result = typeof reader.result === "string" ? reader.result : "";
        resolve(result.split(",", 2)[1] || "");
      };
      reader.onerror = () => reject(reader.error ?? new Error("Failed to encode audio blob."));
      reader.readAsDataURL(blob);
    });
  }, []);

  const stopMediaStream = useCallback(() => {
    mediaStreamRef.current?.getTracks().forEach((track) => track.stop());
    mediaStreamRef.current = null;
  }, []);

  const connect = useCallback(() => {
    if (ws.current?.readyState === WebSocket.OPEN || ws.current?.readyState === WebSocket.CONNECTING) return;

    const socket = new WebSocket(url);
    socket.binaryType = 'arraybuffer';
    ws.current = socket;

    socket.onopen = async () => {
      if (ws.current !== socket) {
        socket.close();
        return;
      }
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
      if (ws.current !== socket) {
        socket.close();
        return;
      }
      if (typeof event.data === 'string') {
        let msg: { type?: MessageType; [key: string]: any };
        try {
          msg = JSON.parse(event.data);
        } catch (error) {
          console.warn("[Jarvis] Ignoring malformed WebSocket message:", error);
          return;
        }

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
            audioReceivedThisTurn.current = false;
            // Drop any chunks still draining from a previous (interrupted) turn.
            audioChainRef.current = Promise.resolve();
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
            if (!audioReceivedThisTurn.current && currentAssistantMsg.current.trim()) {
              speakWithBrowserTTS(currentAssistantMsg.current);
            }
            currentAssistantMsg.current = "";
            break;

          case "ERROR":
            console.error("[Jarvis] Agent error:", msg.message);
            setIsThinking(false);
            break;
        }
      } else {
        if (event.data instanceof ArrayBuffer && event.data.byteLength > 0) {
          const buffer = event.data;
          // Chain onto the previous chunk's promise so chunks are always
          // played in the order they arrived, even if an earlier chunk's
          // decode (e.g. MP3 fallback) takes longer than a later one's.
          audioChainRef.current = audioChainRef.current
            .then(async () => {
              const played = await playRawChunk(buffer);
              audioReceivedThisTurn.current = audioReceivedThisTurn.current || played;
            })
            .catch((error) => {
              console.warn("[Jarvis] Audio chunk playback failed:", error);
            });
        }
      }
    };

    socket.onclose = (e) => {
      if (ws.current === socket) {
        setIsConnected(false);
        clearInterval(pingTimer.current);
        console.warn(`[Jarvis] Disconnected. Code: ${e.code}`);

        if (e.code === 4401) {
          console.error("[Jarvis] Connection rejected: Unauthorized (Code 4401). Please verify that VITE_WS_AUTH_TOKEN in your frontend matches WS_AUTH_TOKEN on your backend.");
          shouldReconnect.current = false;
          return;
        }

        if (shouldReconnect.current && retryCount.current < MAX_RETRIES) {
          const delay = Math.min(1000 * 2 ** retryCount.current, 30000);
          retryCount.current++;
          console.log(`[Jarvis] Reconnecting in ${delay}ms (attempt ${retryCount.current})`);
          retryTimer.current = window.setTimeout(connect, delay);
        }
      } else {
        console.log("[Jarvis] Stale socket onclose ignored.");
      }
    };

    // P2 fix: log URL and full event object so voice socket failures are diagnosable.
    socket.onerror = (event) => {
      console.error(`[Jarvis] Voice socket error (url=${url}):`, event);
      socket.close();
    };
  }, [url, playRawChunk, speakWithBrowserTTS]);

  const startRecording = useCallback(async (imageFrame: string | null = null) => {
    if (isRecording || mediaRecorderRef.current?.state === "recording") return;
    if (!navigator.mediaDevices?.getUserMedia || typeof MediaRecorder === "undefined") {
      console.warn("[Jarvis] MediaRecorder is not supported in this browser.");
      return;
    }

    try {
      pendingImageRef.current = imageFrame;
      await initAudio();

      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      mediaStreamRef.current = stream;

      const mimeCandidates = [
        "audio/webm;codecs=opus",
        "audio/webm",
        "audio/ogg;codecs=opus",
        "audio/mp4",
      ];
      const supportedMime = mimeCandidates.find((candidate) => MediaRecorder.isTypeSupported(candidate));
      const recorder = supportedMime ? new MediaRecorder(stream, { mimeType: supportedMime }) : new MediaRecorder(stream);

      audioChunksRef.current = [];
      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };
      recorder.onerror = (event) => {
        console.error("[Jarvis] Recording error:", event);
        setIsRecording(false);
        stopMediaStream();
      };
      recorder.onstop = async () => {
        try {
          const chunkType = audioChunksRef.current[0]?.type;
          const mimeType = recorder.mimeType || chunkType || supportedMime || "audio/webm";
          const blob = new Blob(audioChunksRef.current, { type: mimeType });
          const base64Audio = await blobToBase64(blob);

          if (base64Audio && ws.current?.readyState === WebSocket.OPEN) {
            ws.current.send(JSON.stringify({
              type: "audio_input",
              data: base64Audio,
              mime_type: mimeType,
              file_name: mimeType.includes("mp4") ? "browser-recording.m4a" : "browser-recording.webm",
              image: pendingImageRef.current,
            }));
          }
        } catch (error) {
          console.error("[Jarvis] Failed to send recorded audio:", error);
        } finally {
          audioChunksRef.current = [];
          pendingImageRef.current = null;
          mediaRecorderRef.current = null;
          stopMediaStream();
          setIsRecording(false);
        }
      };

      mediaRecorderRef.current = recorder;
      recorder.start();
      setIsRecording(true);
    } catch (error) {
      console.error("[Jarvis] Failed to start recording:", error);
      pendingImageRef.current = null;
      setIsRecording(false);
      stopMediaStream();
    }
  }, [blobToBase64, initAudio, isRecording, stopMediaStream]);

  const stopRecording = useCallback(() => {
    const recorder = mediaRecorderRef.current;
    if (!recorder || recorder.state === "inactive") return;
    recorder.stop();
  }, []);

  const sendTextMessage = useCallback(async (text: string, image: string | null = null) => {
    const trimmed = text.trim();
    if (!trimmed) return;
    await initAudio();
    if (!ws.current || ws.current.readyState !== WebSocket.OPEN) {
      console.warn("[Jarvis] Cannot send message while neural link is offline.");
      return;
    }
    setMessages(prev => [...prev, {
      role: "user",
      content: trimmed,
      timestamp: Date.now()
    }]);
    ws.current.send(JSON.stringify({ type: "text_input", text: trimmed, image }));
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
      if (mediaRecorderRef.current?.state === "recording") {
        mediaRecorderRef.current.stop();
      }
      stopMediaStream();
      ws.current?.close(1000);
    };
  }, [connect, stopMediaStream]);

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
