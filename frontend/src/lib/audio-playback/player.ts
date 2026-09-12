// TTS audio playback. Decodes a WAV (or MP3) blob and plays it via <audio>.
// Sequential queue — overlapping audio is suppressed by stopping the previous node.

let audioEl: HTMLAudioElement | null = null
let currentToken = 0

export function playTTSBlob(blob: Blob): Promise<void> {
  const myToken = ++currentToken
  return new Promise((resolve) => {
    if (!audioEl) {
      audioEl = new Audio()
      audioEl.preload = 'auto'
    }
    const url = URL.createObjectURL(blob)
    const prev = audioEl.src
    audioEl.src = url
    audioEl.onended = () => {
      URL.revokeObjectURL(url)
      if (prev) URL.revokeObjectURL(prev)
      if (myToken === currentToken) resolve()
    }
    audioEl.onerror = () => {
      URL.revokeObjectURL(url)
      if (myToken === currentToken) resolve()
    }
    audioEl.play().catch((e) => {
      console.warn('[tts] play failed', e)
      URL.revokeObjectURL(url)
      if (myToken === currentToken) resolve()
    })
  })
}

export function stopTTS() {
  currentToken++ // invalidate all pending
  if (audioEl) {
    audioEl.pause()
    audioEl.src = ''
  }
}
