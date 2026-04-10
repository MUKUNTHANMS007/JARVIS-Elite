// JARVIS Neural Flow: High-Performance PCM AudioWorklet Processor
// Optimized for 24kHz RAW PCM_16 neural voice streams.

class PCMProcessor extends AudioWorkletProcessor {
  constructor() {
    super();
    // Capacity for 3 seconds of audio at 24kHz (24000 * 3)
    this.bufferCapacity = 72000;
    this.buffer = new Float32Array(this.bufferCapacity);
    this.readPointer = 0;
    this.writePointer = 0;
    this.wasSpeaking = false;
    
    this.port.onmessage = (e) => {
      if (e.data instanceof Float32Array) {
        this.appendData(e.data);
      }
    };
  }

  appendData(newData) {
    const availableSpace = this.bufferCapacity - (this.writePointer - this.readPointer);
    
    if (newData.length > availableSpace) {
      // Emergency Reset: If buffer overflows, clear half and sync
      console.warn("[Neural Audio] Buffer overflow. Resynching pointers.");
      this.readPointer = 0;
      this.writePointer = 0;
    }

    // Wrap-around logic simplified by using a large linear buffer that we periodicially reset
    // In this implementation, we just append linearly. If we near the end, we shift left.
    if (this.writePointer + newData.length > this.bufferCapacity) {
      const remainingSamples = this.writePointer - this.readPointer;
      this.buffer.copyWithin(0, this.readPointer, this.writePointer);
      this.readPointer = 0;
      this.writePointer = remainingSamples;
    }

    this.buffer.set(newData, this.writePointer);
    this.writePointer += newData.length;
  }

  process(inputs, outputs, parameters) {
    const output = outputs[0];
    const channel = output[0];
    
    let hasData = false;
    
    for (let i = 0; i < channel.length; i++) {
        if (this.readPointer < this.writePointer) {
            channel[i] = this.buffer[this.readPointer++];
            hasData = true;
        } else {
            channel[i] = 0;
            // Buffer empty: Reset pointers to avoid large offsets
            this.readPointer = 0;
            this.writePointer = 0;
        }
    }

    // Report state changes back to React for UI synchronization
    if (hasData && !this.wasSpeaking) {
        this.port.postMessage({ type: 'state', speaking: true });
        this.wasSpeaking = true;
    } else if (!hasData && this.wasSpeaking) {
        this.port.postMessage({ type: 'state', speaking: false });
        this.wasSpeaking = false;
    }

    return true; // Keep processor alive
  }
}

registerProcessor('pcm-processor', PCMProcessor);
