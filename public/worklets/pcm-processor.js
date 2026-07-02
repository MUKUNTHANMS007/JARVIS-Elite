// JARVIS Neural Flow: High-Performance PCM AudioWorklet Processor
// Optimized for 24kHz RAW PCM_16 neural voice streams.

class PCMProcessor extends AudioWorkletProcessor {
  constructor() {
    super();
    // Capacity for 120 seconds of audio based on hardware sample rate.
    // Backend TTS synthesis runs faster than real-time playback, so a
    // multi-sentence reply's audio can arrive well before the speaker has
    // drained the previous sentence. A too-small buffer here forces the
    // overflow safety net below to fire and wipe still-unplayed audio
    // mid-reply — heard as JARVIS only speaking the last sentence.
    const rate = typeof sampleRate !== 'undefined' ? sampleRate : 24000;
    this.bufferCapacity = rate * 120;
    this.buffer = new Float32Array(this.bufferCapacity);
    this.writePointer = 0;
    this.readPointer = 0;
    this.wasSpeaking = false;
    
    this.port.onmessage = (e) => {
      if (e.data instanceof Float32Array) {
        this.appendData(e.data);
      }
    };
  }

  appendData(newData) {
    // Guard: if the incoming chunk is larger than the entire buffer, keep only the
    // most recent bufferCapacity samples so we never attempt an out-of-bounds write.
    if (newData.length > this.bufferCapacity) {
      console.warn('[Neural Audio] Chunk exceeds buffer capacity — trimming to fit.');
      newData = newData.subarray(newData.length - this.bufferCapacity);
    }

    const samplesQueued = this.writePointer - this.readPointer;

    // In-place shift: If we are nearing the end of the buffer, move existing data to the front
    if (this.writePointer + newData.length > this.bufferCapacity) {
      if (samplesQueued > 0) {
        this.buffer.copyWithin(0, this.readPointer, this.writePointer);
      }
      this.readPointer = 0;
      this.writePointer = samplesQueued;
    }

    // Safety: if the queued backlog plus the new chunk still can't fit even
    // after compaction, drop the OLDEST queued samples (not the new ones) —
    // a full reset here would silently discard unplayed audio mid-reply.
    if (this.writePointer + newData.length > this.bufferCapacity) {
      const overflow = (this.writePointer + newData.length) - this.bufferCapacity;
      console.warn('[Neural Audio] Buffer overflow even after shift. Dropping oldest samples.');
      this.readPointer = Math.min(this.readPointer + overflow, this.writePointer);
      this.buffer.copyWithin(0, this.readPointer, this.writePointer);
      this.writePointer -= this.readPointer;
      this.readPointer = 0;
    }

    // Final hard-clamp: should never trigger, but prevents any out-of-bounds write
    const available = this.bufferCapacity - this.writePointer;
    const safeData = newData.length <= available ? newData : newData.subarray(0, available);
    this.buffer.set(safeData, this.writePointer);
    this.writePointer += safeData.length;
  }

  process(inputs, outputs, parameters) {
    const output = outputs[0];
    const channel = output[0];
    
    const samplesQueued = this.writePointer - this.readPointer;

    if (samplesQueued > 0) {
        for (let i = 0; i < channel.length; i++) {
            channel[i] = this.readPointer < this.writePointer 
                ? this.buffer[this.readPointer++] 
                : 0;
        }
        if (!this.wasSpeaking) {
            this.port.postMessage({ type: 'state', speaking: true });
            this.wasSpeaking = true;
        }
        
        // Reset pointers to 0 if we've completely consumed the queue
        if (this.readPointer === this.writePointer) {
            this.readPointer = 0;
            this.writePointer = 0;
        }
    } else {
        channel.fill(0);
        if (this.wasSpeaking) {
            this.port.postMessage({ type: 'state', speaking: false });
            this.wasSpeaking = false;
        }
        this.readPointer = 0;
        this.writePointer = 0;
    }

    return true;
  }
}

registerProcessor('pcm-processor', PCMProcessor);
