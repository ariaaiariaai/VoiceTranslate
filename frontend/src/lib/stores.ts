// Svelte 5 runes-based stores for shared app state.
import { writable } from 'svelte/store'

export interface TranscriptLine {
  id: number
  ja: string
  zh: string
  latency_ms: number
  timestamp: number
  partial?: boolean
  quality_score?: number | null
  speaker?: string | null  // "A", "B", "C" — VAD-based speaker rotation
}

export type ConnectionState = 'idle' | 'connecting' | 'connected' | 'reconnecting' | 'error'
export type OutputMode = 'text' | 'audio' | 'both'
export type TtsEngine = 'melo' | 'edge_hk' | 'edge_cn'

export const connection = writable<ConnectionState>('idle')
export const transcripts = writable<TranscriptLine[]>([])
export const lastLatency = writable<number>(0)
export const mode = writable<OutputMode>('both')
export const ttsEngine = writable<TtsEngine>('edge_hk') // Cantonese voice by default
export const backendUrl = writable<string>('')
