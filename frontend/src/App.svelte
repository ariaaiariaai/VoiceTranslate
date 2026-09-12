<script lang="ts">
  import { onMount } from 'svelte'
  import StartButton from './components/StartButton.svelte'
  import TranscriptList from './components/TranscriptList.svelte'
  import ModeToggle from './components/ModeToggle.svelte'
  import StatusBar from './components/StatusBar.svelte'
  import SettingsPanel from './components/SettingsPanel.svelte'
  import {
    backendUrl,
    connection,
    mode,
    transcripts,
    lastLatency,
    ttsEngine,
  } from './lib/stores'
  import { startCapture, type AudioCaptureHandle } from './lib/audio/capture'
  import { WSClient } from './lib/net/ws-client'
  import { playTTSBlob, stopTTS } from './lib/audio-playback/player'
  import { requestWakeLock, releaseWakeLock } from './lib/wake-lock'
  import { initPWA } from './lib/pwa'
  import type { TranscriptLine } from './lib/stores'

  let capture: AudioCaptureHandle | null = null
  let ws: WSClient | null = null
  let pendingAudioSeq = 0

  onMount(() => {
    initPWA()
    // Auto-detect backend URL:
    // 1. Use VITE_BACKEND_URL env var baked at build time, OR
    // 2. Use current origin (works when frontend and backend share Cloudflare Tunnel hostname)
    const fromEnv = import.meta.env.VITE_BACKEND_URL as string | undefined
    if (fromEnv) {
      backendUrl.set(fromEnv)
    } else if (typeof window !== 'undefined') {
      backendUrl.set(window.location.origin)
    }
  })

  function wsUrl(): string {
    const base = $backendUrl || window.location.origin
    return base.replace(/^http/, 'ws') + '/ws'
  }

  async function startSession() {
    await requestWakeLock()
    transcripts.set([])
    pendingAudioSeq = 0

    connection.set('connecting')

    ws = new WSClient({
      url: wsUrl(),
      onOpen: () => {
        connection.set('connected')
        ws!.sendJSON({
          type: 'hello',
          mode: $mode,
          tts_engine: $ttsEngine,
          sample_rate: 16000,
        })
      },
      onClose: () => {
        connection.set('reconnecting')
      },
      onError: () => {
        // reconnect logic in WSClient
      },
      onText: (msg) => handleServerText(msg),
      onBinary: (data) => handleServerBinary(data),
    })
    ws.connect()

    try {
      capture = await startCapture(
        (pcm16, vad) => {
          ws?.sendBinary(pcm16)
        },
        (err) => {
          console.error('mic error', err)
          alert('無法取得麥克風權限：' + err.message)
          stopSession()
        }
      )
    } catch (e: any) {
      console.error('start failed', e)
      alert('啟動失敗：' + e.message)
      stopSession()
    }
  }

  function handleServerText(msg: any) {
    if (msg.type === 'ready') return
    if (msg.type === 'transcript') {
      const seg = msg.segment
      lastLatency.set(seg.latency_ms)
      transcripts.update((arr) => {
        // Replace any partial placeholder for this id
        const filtered = arr.filter((l) => l.id !== seg.id)
        const line: TranscriptLine = {
          id: seg.id,
          ja: seg.ja,
          zh: seg.zh,
          latency_ms: seg.latency_ms,
          timestamp: Date.now(),
        }
        const next = [...filtered, line]
        return next.slice(-200) // keep last 200
      })
      pendingAudioSeq = msg.audio_seq ?? 0
    } else if (msg.type === 'partial') {
      transcripts.update((arr) => {
        const filtered = arr.filter((l) => l.id !== msg.id)
        const line: TranscriptLine = {
          id: msg.id,
          ja: msg.ja || '…',
          zh: msg.zh || '…',
          latency_ms: 0,
          timestamp: Date.now(),
          partial: true,
        }
        return [...filtered, line].slice(-200)
      })
    } else if (msg.type === 'error') {
      console.error('server error', msg)
      alert(`[${msg.code}] ${msg.message}`)
    }
  }

  function handleServerBinary(data: ArrayBuffer) {
    // Server sends WAV/MP3 paired with the most recent transcript (audio_seq).
    // We just play it. Order is guaranteed (text frame precedes binary frame).
    const blob = new Blob([data], { type: 'audio/wav' })
    playTTSBlob(blob).catch((e) => console.warn('tts play failed', e))
  }

  function onModeChange() {
    ws?.sendJSON({ type: 'mode', mode: $mode })
  }

  function onTtsEngineChange() {
    ws?.sendJSON({ type: 'tts_engine', tts_engine: $ttsEngine })
  }

  async function stopSession() {
    await capture?.stop()
    capture = null
    ws?.close()
    ws = null
    stopTTS()
    await releaseWakeLock()
    connection.set('idle')
  }
</script>

<main>
  <header>
    <h1>VoiceTranslate</h1>
    <p class="subtitle">日文 → 繁體中文 即時翻譯</p>
  </header>

  <SettingsPanel />

  <TranscriptList />

  <ModeToggle onChange={() => { onModeChange(); onTtsEngineChange() }} />

  <div class="footer">
    <StatusBar />
    <StartButton onStart={startSession} onStop={stopSession} />
  </div>
</main>

<style>
  :global(html, body) {
    margin: 0;
    padding: 0;
    height: 100%;
    background: #0b0b0b;
    color: white;
    font-family:
      -apple-system,
      BlinkMacSystemFont,
      'PingFang HK',
      'PingFang TC',
      'Microsoft JhengHei',
      'Hiragino Sans',
      sans-serif;
    overscroll-behavior: none;
    -webkit-font-smoothing: antialiased;
  }
  :global(*) {
    box-sizing: border-box;
  }
  main {
    display: flex;
    flex-direction: column;
    height: 100vh;
    height: 100dvh;
    position: relative;
    /* iPhone notch / Dynamic Island safe-area */
    padding-top: env(safe-area-inset-top);
    padding-bottom: env(safe-area-inset-bottom);
    padding-left: env(safe-area-inset-left);
    padding-right: env(safe-area-inset-right);
  }
  header {
    padding: 0.75rem 1rem 0.5rem;
    text-align: center;
  }
  h1 {
    margin: 0;
    font-size: 1.1rem;
    font-weight: 600;
    letter-spacing: 0.5px;
  }
  .subtitle {
    margin: 0.25rem 0 0;
    font-size: 0.75rem;
    color: rgba(255, 255, 255, 0.5);
  }
  .footer {
    padding: 0.75rem 1rem 1rem;
    background: rgba(0, 0, 0, 0.4);
    border-top: 1px solid rgba(255, 255, 255, 0.06);
  }
</style>
