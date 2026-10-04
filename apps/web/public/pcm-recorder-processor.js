// AudioWorkletProcessor for Hearth
// Captures mic input, downsamples to 16000 Hz mono, and converts to Int16 PCM buffers.

class PCMRecorderProcessor extends AudioWorkletProcessor {
  constructor() {
    super();
    this.targetSampleRate = 16000;
    this.buffer = [];
  }

  process(inputs, outputs, parameters) {
    const input = inputs[0];
    if (!input || !input[0]) return true;

    const channelData = input[0]; // Float32 mono channel
    const sampleRateRatio = sampleRate / this.targetSampleRate;

    // Resample to 16kHz
    if (sampleRateRatio === 1) {
      this._emitChunk(channelData);
    } else {
      // Linear interpolation downsampling
      const outputLength = Math.floor(channelData.length / sampleRateRatio);
      const resampled = new Float32Array(outputLength);
      for (let i = 0; i < outputLength; i++) {
        const originalIndex = i * sampleRateRatio;
        const indexFloor = Math.floor(originalIndex);
        const indexCeil = Math.min(indexFloor + 1, channelData.length - 1);
        const fraction = originalIndex - indexFloor;
        resampled[i] = channelData[indexFloor] * (1 - fraction) + channelData[indexCeil] * fraction;
      }
      this._emitChunk(resampled);
    }

    return true;
  }

  _emitChunk(float32Array) {
    // Convert Float32 [-1.0, 1.0] to Int16 [-32768, 32767]
    const int16Array = new Int16Array(float32Array.length);
    for (let i = 0; i < float32Array.length; i++) {
      let s = Math.max(-1, Math.min(1, float32Array[i]));
      int16Array[i] = s < 0 ? s * 0x8000 : s * 0x7fff;
    }
    this.port.postMessage(int16Array.buffer, [int16Array.buffer]);
  }
}

registerProcessor('pcm-recorder-processor', PCMRecorderProcessor);
