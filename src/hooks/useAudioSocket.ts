import { useState, useEffect, useRef, useCallback } from 'react';

export function useAudioSocket(url: string) {
  const [messages, setMessages] = useState<{ role: 'user' | 'agent', content: string }[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [isThinking, setIsThinking] = useState(false);
  const [mood, setMood] = useState<'normal' | 'stressed'>('normal');

  const socketRef = useRef<WebSocket | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const activeStreamRef = useRef<MediaStream | null>(null);
  const reconnectCountRef = useRef(0);
  const MAX_RECONNECT_ATTEMPTS = 5;
  const RECONNECT_INTERVAL = 3000;
  const currentAudioRef = useRef<HTMLAudioElement | null>(null);
  
  // Audio Queue States
  const audioQueueRef = useRef<Blob[]>([]);
  const isPlayingRef = useRef(false);

  // --- 1. CLEAN HARDWARE MANAGEMENT ---
  const stopHardware = useCallback(() => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
      try { mediaRecorderRef.current.stop(); } catch (e) {}
    }
    if (activeStreamRef.current) {
        activeStreamRef.current.getTracks().forEach(t => t.stop());
        activeStreamRef.current = null;
    }
    audioQueueRef.current = [];
    isPlayingRef.current = false;
    currentAudioRef.current = null;
    setIsRecording(false);
  }, []);

  // --- 2. GAPLESS ACOUSTIC QUEUE ---
  const processQueue = useCallback(() => {
    if (audioQueueRef.current.length === 0) {
      isPlayingRef.current = false;
      return;
    }

    isPlayingRef.current = true;
    const blob = audioQueueRef.current.shift()!;
    const blobUrl = URL.createObjectURL(blob);
    const audio = new Audio(blobUrl);
    currentAudioRef.current = audio;

    audio.onended = () => {
      URL.revokeObjectURL(blobUrl);
      currentAudioRef.current = null;
      processQueue();
    };

    audio.onerror = () => {
      URL.revokeObjectURL(blobUrl);
      currentAudioRef.current = null;
      processQueue();
    };

    audio.play().catch((e) => {
      console.debug("[Neural Link] Playback skipped:", e.message);
      processQueue();
    });
  }, []);

  const playAudioChunk = useCallback((blob: Blob) => {
    audioQueueRef.current.push(blob);
    if (!isPlayingRef.current) {
      processQueue();
    }
  }, [processQueue]);

  // --- 3. UI FEEDBACK ---
  const updateLastMessage = useCallback((text: string) => {
    setMessages(prev => {
      const lastIdx = prev.length - 1;
      const last = prev[lastIdx];
      if (last && last.role === 'agent') {
        const newMsgs = [...prev];
        newMsgs[lastIdx] = { ...last, content: last.content + text };
        return newMsgs;
      }
      return [...prev, { role: 'agent', content: text }];
    });
  }, []);

  const sendTextMessage = useCallback((text: string, imageData?: string | null) => {
    if (!text.trim()) return;
    const command = text.replace(/jarvis|travis|garvis/gi, "JARVIS").trim();
    if (socketRef.current?.readyState === WebSocket.OPEN) {
        socketRef.current.send(JSON.stringify({ 
          type: 'text_input',
          text: command, 
          image: imageData || null 
        }));
        setMessages(prev => [...prev.filter(m => m.content !== '[Audio Processing...]'), { role: 'user', content: command }]);
        setIsThinking(true);
    }
  }, []);

  // --- 4. CORE WEBSOCKET LOGIC ---
  const connect = useCallback(() => {
    // If we're already connecting or open, don't start another one
    if (socketRef.current && (socketRef.current.readyState === WebSocket.OPEN || socketRef.current.readyState === WebSocket.CONNECTING)) {
        return;
    }
    
    const socket = new WebSocket(url);
    socket.binaryType = 'arraybuffer';
    socketRef.current = socket;

    socket.onopen = () => {
        setIsConnected(true);
        reconnectCountRef.current = 0;
        console.log("[Jarvis Core] Neural Link Established.");
        
        const heartbeat = setInterval(() => {
          if (socket.readyState === WebSocket.OPEN) {
            socket.send(JSON.stringify({ type: 'PING' }));
          }
        }, 10000);
        (socket as any)._heartbeat = heartbeat;
    };

    socket.onclose = (e) => {
        setIsConnected(false);
        if ((socket as any)._heartbeat) clearInterval((socket as any)._heartbeat);
        
        // Only reconnect if the closure wasn't intentional (code 1000)
        if (e.code !== 1000 && reconnectCountRef.current < MAX_RECONNECT_ATTEMPTS) {
            console.log(`[Neural Link] Severed. Retrying (${reconnectCountRef.current + 1}/${MAX_RECONNECT_ATTEMPTS})...`);
            setTimeout(() => {
                reconnectCountRef.current++;
                connect();
            }, RECONNECT_INTERVAL);
        }
    };

    socket.onmessage = async (event) => {
      if (typeof event.data === 'string') {
        const data = JSON.parse(event.data);
        if (data.type === 'TRANSCRIPTION') {
            setMessages(prev => {
                const lastIdx = prev.length - 1;
                if (lastIdx >= 0 && prev[lastIdx].content === '[Audio Processing...]') {
                    const newMsgs = [...prev];
                    newMsgs[lastIdx] = { ...newMsgs[lastIdx], content: data.text };
                    return newMsgs;
                }
                return [...prev, { role: 'user', content: data.text }];
            });
        }
        if (data.type === 'TURN_START') {
            setMood(data.mood || 'normal');
            setIsThinking(true);
        }
        if (data.type === 'TEXT_CHUNK') {
            setIsThinking(false);
            updateLastMessage(data.text);
        }
        if (data.type === 'TURN_COMPLETE') {
            setIsThinking(false);
            setMessages(prev => prev.filter(m => m.content !== '[Audio Processing...]'));
        }
      } else {
        const blob = new Blob([event.data], { type: 'audio/wav' });
        playAudioChunk(blob);
      }
    };
  }, [url, playAudioChunk, updateLastMessage]);

  useEffect(() => {
    connect();
    return () => {
        if (socketRef.current) {
            const ws = socketRef.current;
            // Detach listeners to prevent "onclose" firing the retry logic
            ws.onopen = null; ws.onmessage = null; ws.onerror = null; ws.onclose = null;
            
            // If it's still handshaking, closing it triggers the "before established" warning.
            // There is no clean way to "abort" a handshake in the standard WS API, 
            // but checking state reduces the frequency of the error.
            if (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING) {
                ws.close(1000, "Unmount");
            }
            socketRef.current = null;
        }
        stopHardware();
    };
  }, [connect, stopHardware]);

  const reconnect = useCallback(() => {
    reconnectCountRef.current = 0;
    if (socketRef.current) {
        socketRef.current.onclose = null;
        socketRef.current.close(1000);
    }
    connect();
  }, [connect]);

  // --- 5. RECORDING LOGIC ---
  const startRecording = useCallback(async (imageData?: string | null) => {
    fetch('/api/core/spotify/pause').catch(() => {});
    audioQueueRef.current = [];
    isPlayingRef.current = false;
    if (currentAudioRef.current) {
        currentAudioRef.current.pause();
        currentAudioRef.current = null;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      activeStreamRef.current = stream;
      
      const recorder = new MediaRecorder(stream);
      recorder.ondataavailable = (e) => {
        if (e.data.size > 0 && socketRef.current?.readyState === WebSocket.OPEN) {
          e.data.arrayBuffer().then(buf => socketRef.current?.send(buf));
        }
      };

      if (socketRef.current?.readyState === WebSocket.OPEN) {
          socketRef.current.send(JSON.stringify({ type: 'AUDIO_START', image: imageData || null }));
          setMessages(prev => [...prev, { role: 'user', content: '[Audio Processing...]' }]);
          setIsRecording(true);
          setIsThinking(true);
          recorder.start(250);
          mediaRecorderRef.current = recorder;
      }
    } catch (err) {
      console.error("[Jarvis Core] Neural Link Interface Failure:", err);
    }
  }, []);

  const stopRecording = useCallback(() => {
    if (socketRef.current?.readyState === WebSocket.OPEN) {
        socketRef.current.send(JSON.stringify({ type: 'stop_recording' }));
    }
    stopHardware();
    setIsThinking(true);
  }, [stopHardware]);

  return { 
    messages, isConnected, isRecording, 
    isThinking, setIsThinking,
    mood,
    startRecording, stopRecording,
    sendTextMessage, reconnect
  };
}
