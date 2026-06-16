// JARVIS Neural Flow: High-Performance PCM AudioWorklet Processor
// Optimized for 24kHz RAW PCM_16 neural voice streams.

class PCMProcessor extends AudioWorkletProcessor {
  constructor() {
    super();
    // Capacity for 3 seconds of audio at 24kHz (24000 * 3)
    this.bufferCapacity = 72000;
    this.buffer = new Float32Array(this.bufferCapacity);
    this.writePointer = 0;
    this.readPointer = 0;
    this.primeThreshold = 4096; // ~170ms at 24kHz
    this.wasSpeaking = false;
    
    this.port.onmessage = (e) => {
      if (e.data instanceof Float32Array) {
        this.appendData(e.data);
      }
    };
  }

  appendData(newData) {
    const samplesQueued = this.writePointer - this.readPointer;
    
    // In-place shift: If we are nearing the end of the buffer, move existing data to the front
    if (this.writePointer + newData.length > this.bufferCapacity) {
      if (samplesQueued > 0) {
        this.buffer.copyWithin(0, this.readPointer, this.writePointer);
      }
      this.readPointer = 0;
      this.writePointer = samplesQueued;
    }

    // Safety: If it still doesn't fit after shifting, the buffer is truly full
    if (this.writePointer + newData.length <= this.bufferCapacity) {
      this.buffer.set(newData, this.writePointer);
      this.writePointer += newData.length;
    } else {
      console.warn("[Neural Audio] Buffer overflow even after shift. Dropping oldest samples.");
      this.readPointer = 0;
      this.writePointer = 0;
      this.buffer.set(newData, 0);
      this.writePointer = newData.length;
    }
  }

  process(inputs, outputs, parameters) {
    const output = outputs[0];
    const channel = output[0];
    
    const samplesQueued = this.writePointer - this.readPointer;
    
    // SAFETY: Wait for 4096 samples (~170ms) before starting the first time
    // This creates a "cushion" that prevents stuttering.
    if (samplesQueued < this.primeThreshold && !this.wasSpeaking) {
        channel.fill(0);
        return true;
    }

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
    } else {
        channel.fill(0);
        if (this.wasSpeaking) {
            this.port.postMessage({ type: 'state', speaking: false });
            this.wasSpeaking = false;
        }
    }

    return true;
  }
}

registerProcessor('pcm-processor', PCMProcessor);
