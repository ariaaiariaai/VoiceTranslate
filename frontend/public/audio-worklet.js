// AudioWorklet processor — runs in a separate audio thread.
// Resamples from native rate to 16 kHz mono Float32, computes RMS-based VAD,
// and posts buffers back to the main thread.

const TARGET_SR = 16000

class ResamplerWorklet extends AudioWorkletProcessor {
  constructor() {
    super()
    this._ratio = sampleRate / TARGET_SR
    this._buffer = []
    this._bufferSamples = 0
    this._frameSamples = TARGET_SR / 10 // 100 ms frames
    this._rmsAccum = 0
    this._rmsCount = 0
    this._threshold = -50 // dB
    this._enabled = true
  }

  process(inputs) {
    const input = inputs[0]
    if (!input || input.length === 0) return true
    const ch = input[0]
    if (!ch) return true
    // Resample: simple linear interpolation downsampler.
    const out = new Float32Array(Math.ceil(ch.length / this._ratio))
    let pos = 0
    for (let i = 0; i < out.length; i++) {
      const srcIdx = i * this._ratio
      const i0 = Math.floor(srcIdx)
      const i1 = Math.min(i0 + 1, ch.length - 1)
      const frac = srcIdx - i0
      out[i] = ch[i0] * (1 - frac) + ch[i1] * frac
      pos = i1
    }
    // RMS
    let sumSq = 0
    for (let i = 0; i < out.length; i++) sumSq += out[i] * out[i]
    const rms = Math.sqrt(sumSq / out.length)
    const db = 20 * Math.log10(Math.max(rms, 1e-9))
    const isSpeech = db > this._threshold

    this.port.postMessage(
      {
        type: 'frame',
        samples: out,
        db,
        isSpeech,
        sr: TARGET_SR,
      },
      [out.buffer]
    )
    return true
  }
}

registerProcessor('resampler-worklet', ResamplerWorklet)
