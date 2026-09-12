// Audio capture pipeline.
// 1. getUserMedia (mono, echo cancellation, noise suppression)
// 2. AudioContext + AudioWorklet (resampler-worklet.js) → 16 kHz mono Float32 frames
// 3. Main thread: collect 1-second PCM Int16 chunks, pass to onChunk callback

export interface AudioCaptureHandle {
  stop(): Promise<void>
}

export async function startCapture(
  onChunk: (pcm16: Int16Array, vad: { db: number; isSpeech: boolean }) => void,
  onError: (err: Error) => void
): Promise<AudioCaptureHandle> {
  // Request mono audio at any sample rate — we resample in the worklet.
  const stream = await navigator.mediaDevices.getUserMedia({
    audio: {
      echoCancellation: true,
      noiseSuppression: true,
      channelCount: 1,
      // Don't constrain sampleRate — Safari ignores it anyway. Worklet handles resampling.
    },
    video: false,
  })

  const ctx = new AudioContext({ latencyHint: 'interactive' })
  // Some browsers (especially Safari) ignore latencyHint; we just create with default.

  // Add the worklet module from /public
  await ctx.audioWorklet.addModule('/audio-worklet.js')

  const src = ctx.createMediaStreamSource(stream)
  const node = new AudioWorkletNode(ctx, 'resampler-worklet')
  src.connect(node)

  // Accumulate frames into 1 s (16 000 samples) chunks before flushing.
  const CHUNK_SAMPLES = 16000
  let buf = new Int16Array(CHUNK_SAMPLES)
  let filled = 0
  let lastDb = -120
  let lastIsSpeech = false

  node.port.onmessage = (ev) => {
    const { samples, db, isSpeech } = ev.data
    lastDb = db
    lastIsSpeech = isSpeech
    // Convert Float32 [-1,1] → Int16 [-32768, 32767]
    for (let i = 0; i < samples.length; i++) {
      const s = Math.max(-1, Math.min(1, samples[i]))
      const v = s < 0 ? s * 0x8000 : s * 0x7fff
      buf[filled++] = v | 0
      if (filled === CHUNK_SAMPLES) {
        onChunk(buf, { db, isSpeech })
        buf = new Int16Array(CHUNK_SAMPLES)
        filled = 0
      }
    }
  }

  // Flush a partial chunk every 500 ms if we have buffered audio and user is speaking.
  const flushTimer = setInterval(() => {
    if (filled > 1600) {
      // at least 100 ms buffered
      const slice = buf.slice(0, filled)
      onChunk(slice, { db: lastDb, isSpeech: lastIsSpeech })
      buf = new Int16Array(CHUNK_SAMPLES)
      filled = 0
    }
  }, 500)

  return {
    async stop() {
      clearInterval(flushTimer)
      try {
        src.disconnect()
        node.disconnect()
      } catch {
        // ignore
      }
      try {
        await ctx.close()
      } catch {
        // ignore
      }
      for (const t of stream.getTracks()) t.stop()
    },
  }
}
