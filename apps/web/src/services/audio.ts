export class AudioCaptureService {
  private audioContext: AudioContext | null = null;
  private mediaStream: MediaStream | null = null;
  private workletNode: AudioWorkletNode | null = null;
  private scriptProcessor: ScriptProcessorNode | null = null;
  private onDataCallback: ((buffer: ArrayBuffer) => void) | null = null;
  private isCapturing = false;

  constructor() {}

  async start(onData: (buffer: ArrayBuffer) => void) {
    if (this.isCapturing) return;
    this.onDataCallback = onData;

    try {
      this.mediaStream = await navigator.mediaDevices.getUserMedia({
        audio: {
          channelCount: 1,
          sampleRate: { ideal: 16000 },
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        },
        video: false,
      });

      this.audioContext = new (window.AudioContext || (window as any).webkitAudioContext)({
        sampleRate: 16000,
      });

      if (this.audioContext.state === 'suspended') {
        await this.audioContext.resume();
      }

      const source = this.audioContext.createMediaStreamSource(this.mediaStream);

      // Try AudioWorklet first
      try {
        await this.audioContext.audioWorklet.addModule('/pcm-recorder-processor.js');
        this.workletNode = new AudioWorkletNode(this.audioContext, 'pcm-recorder-processor');
        this.workletNode.port.onmessage = (event) => {
          if (this.onDataCallback && this.isCapturing) {
            this.onDataCallback(event.data);
          }
        };
        source.connect(this.workletNode);
        this.workletNode.connect(this.audioContext.destination);
      } catch (workletError) {
        console.warn('AudioWorklet module failed, falling back to ScriptProcessor:', workletError);
        // Fallback: ScriptProcessorNode
        this.scriptProcessor = this.audioContext.createScriptProcessor(2048, 1, 1);
        this.scriptProcessor.onaudioprocess = (e) => {
          if (!this.isCapturing || !this.onDataCallback) return;
          const input = e.inputBuffer.getChannelData(0);
          const sampleCount = input.length;
          const payload = new ArrayBuffer(8 + sampleCount * 2);
          const f64 = new Float64Array(payload, 0, 1);
          f64[0] = Date.now() / 1000.0;
          const pcm16 = new Int16Array(payload, 8, sampleCount);
          for (let i = 0; i < sampleCount; i++) {
            let s = Math.max(-1, Math.min(1, input[i]));
            pcm16[i] = s < 0 ? s * 0x8000 : s * 0x7fff;
          }
          this.onDataCallback(payload);
        };
        source.connect(this.scriptProcessor);
        this.scriptProcessor.connect(this.audioContext.destination);
      }

      this.isCapturing = true;
    } catch (err) {
      console.error('Failed to access microphone:', err);
      throw err;
    }
  }

  stop() {
    this.isCapturing = false;
    if (this.workletNode) {
      this.workletNode.disconnect();
      this.workletNode = null;
    }
    if (this.scriptProcessor) {
      this.scriptProcessor.disconnect();
      this.scriptProcessor = null;
    }
    if (this.mediaStream) {
      this.mediaStream.getTracks().forEach((track) => track.stop());
      this.mediaStream = null;
    }
    if (this.audioContext) {
      this.audioContext.close();
      this.audioContext = null;
    }
  }

  isActive(): boolean {
    return this.isCapturing;
  }
}

export const audioCapture = new AudioCaptureService();
