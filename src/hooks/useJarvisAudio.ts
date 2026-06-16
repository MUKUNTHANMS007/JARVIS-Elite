import { useRef, useCallback, useState, useEffect } from "react";

export interface UseJarvisAudioReturn {
  isSpeaking: boolean;
  playRawChunk: (arrayBuffer: ArrayBuffer) => Promise<void>;
  initAudio: () => Promise<void>;
}

export function useJarvisAudio(): UseJarvisAudioReturn {
  const audioCtx = useRef<AudioContext | null>(null);
  const workletNode = useRef<AudioWorkletNode | null>(null);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const textDecoder = useRef(new TextDecoder());

  const initAudio = useCallback(async () => {
    if (audioCtx.current) {
      if (audioCtx.current.state === "suspended") {
        try {
          await audioCtx.current.resume();
          console.log("[Neural Audio] Resumed suspended AudioContext on user interaction.");
        } catch (e) {
          console.error("[Neural Audio] Failed to resume AudioContext:", e);
        }
      }
      return;
    }

    try {
      // 24kHz is the native sample rate of Kokoro-82M
      const ctx = new (window.AudioContext || (window as any).webkitAudioContext)({ sampleRate: 24000 });
      
      // Load the Neural Flow processor
      await ctx.audioWorklet.addModule('/worklets/pcm-processor.js');
      
      const node = new AudioWorkletNode(ctx, 'pcm-processor');
      
      // Listen for state changes from the high-priority thread
      node.port.onmessage = (e) => {
        if (e.data.type === 'state') {
          setIsSpeaking(e.data.speaking);
        }
      };

      node.connect(ctx.destination);
      
      audioCtx.current = ctx;
      workletNode.current = node;
      console.log("[Neural Audio] Worklet thread initialized successfully.");
      
      if (ctx.state === "suspended") {
        await ctx.resume();
        console.log("[Neural Audio] Resumed immediately after init.");
      }
    } catch (err) {
      console.error("[Neural Audio] Worklet failed to initialize:", err);
    }
  }, []);

  const playRawChunk = useCallback(async (arrayBuffer: ArrayBuffer) => {
    if (!audioCtx.current) await initAudio();
    
    const ctx = audioCtx.current;
    if (!ctx || !workletNode.current) {
        console.warn("[Neural Audio] Playback requested before initialization.");
        return;
    }

    if (ctx.state === 'suspended') {
        await ctx.resume();
        console.log("[Neural Audio] AudioContext resumed for playback.");
    }

    // Check if it's a legacy WAV (rare now, but robust)
    const header = new Uint8Array(arrayBuffer, 0, 4);
    const isWav = header[0] === 82 && header[1] === 73 && header[2] === 70 && header[3] === 70; // "RIFF"

    if (isWav) {
        // Fallback for WAV: manual decoding (blocks main thread slightly)
        const decoded = await ctx.decodeAudioData(arrayBuffer);
        const float32 = decoded.getChannelData(0);
        workletNode.current.port.postMessage(float32);
    } else {
        // PRIMARY PATH: RAW PCM_16 to Float32 conversion
        const int16Array = new Int16Array(arrayBuffer);
        const float32Array = new Float32Array(int16Array.length);
        
        for (let i = 0; i < int16Array.length; i++) {
          float32Array[i] = int16Array[i] / 32768.0;
        }

        // Send to AudioWorklet thread
        workletNode.current.port.postMessage(float32Array);
    }
  }, [initAudio]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      audioCtx.current?.close();
    };
  }, []);

  return { isSpeaking, playRawChunk, initAudio };
}
