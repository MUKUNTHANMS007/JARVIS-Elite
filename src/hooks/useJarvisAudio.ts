import { useRef, useCallback, useState, useEffect } from "react";

const resampleAudio = (samples: Float32Array, fromRate: number, toRate: number): Float32Array => {
  if (fromRate === toRate) return samples;
  const ratio = fromRate / toRate;
  const newLength = Math.round(samples.length / ratio);
  const result = new Float32Array(newLength);
  for (let i = 0; i < newLength; i++) {
    const pos = i * ratio;
    const index = Math.floor(pos);
    const fraction = pos - index;
    const nextIndex = index + 1 < samples.length ? index + 1 : index;
    result[i] = samples[index] * (1 - fraction) + samples[nextIndex] * fraction;
  }
  return result;
};

export interface UseJarvisAudioReturn {
  isSpeaking: boolean;
  playRawChunk: (arrayBuffer: ArrayBuffer) => Promise<boolean>;
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
      const ctx = new (window.AudioContext || (window as any).webkitAudioContext)();
      
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

  const postToWorklet = useCallback((float32: Float32Array) => {
    workletNode.current?.port.postMessage(float32);
  }, []);

  const playRawChunk = useCallback(async (arrayBuffer: ArrayBuffer) => {
    if (!arrayBuffer.byteLength) return false;
    if (!audioCtx.current) await initAudio();
    
    const ctx = audioCtx.current;
    if (!ctx || !workletNode.current) {
        console.warn("[Neural Audio] Playback requested before initialization.");
        return false;
    }

    if (ctx.state === 'suspended') {
        await ctx.resume();
        console.log("[Neural Audio] AudioContext resumed for playback.");
    }

    const header = new Uint8Array(arrayBuffer, 0, Math.min(12, arrayBuffer.byteLength));
    const isWav = header[0] === 0x52 && header[1] === 0x49 && header[2] === 0x46 && header[3] === 0x46; // RIFF
    const isMp3 = header[0] === 0xff && (header[1] & 0xe0) === 0xe0;
    const isId3 = header[0] === 0x49 && header[1] === 0x44 && header[2] === 0x33; // ID3 tag
    const isMp4 = header[4] === 0x66 && header[5] === 0x74 && header[6] === 0x79 && header[7] === 0x70; // ftyp

    if (isWav || isMp3 || isId3 || isMp4) {
        try {
            const decoded = await ctx.decodeAudioData(arrayBuffer.slice(0));
            postToWorklet(decoded.getChannelData(0));
            return true;
        } catch (e) {
            console.warn("[Neural Audio] Encoded audio decode failed; skipping chunk:", e);
            return false;
        }
    }

    // RAW PCM_16 from Groq pipeline (must be even byte length)
    if (arrayBuffer.byteLength % 2 !== 0) {
        console.warn("[Neural Audio] Skipping odd-length binary chunk.");
        return false;
    }

    const int16Array = new Int16Array(arrayBuffer);
    const float32Array = new Float32Array(int16Array.length);
    for (let i = 0; i < int16Array.length; i++) {
      float32Array[i] = int16Array[i] / 32768.0;
    }
    const resampled = resampleAudio(float32Array, 24000, ctx.sampleRate);
    postToWorklet(resampled);
    return true;
  }, [initAudio, postToWorklet]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      audioCtx.current?.close();
    };
  }, []);

  return { isSpeaking, playRawChunk, initAudio };
}
