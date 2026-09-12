// WebSocket client with auto-reconnect and exponential backoff.

export interface WSClientOptions {
  url: string
  onOpen?: () => void
  onClose?: (code: number, reason: string) => void
  onError?: (err: Event) => void
  onBinary?: (data: ArrayBuffer) => void
  onText?: (msg: any) => void
}

export class WSClient {
  private ws: WebSocket | null = null
  private opts: WSClientOptions
  private retries = 0
  private maxRetries = 8
  private closed = false
  private pendingAudio: Int16Array[] = []
  private reconnectTimer: number | null = null

  constructor(opts: WSClientOptions) {
    this.opts = opts
  }

  connect() {
    if (this.closed) return
    this.clearReconnect()
    try {
      this.ws = new WebSocket(this.opts.url)
    } catch (e) {
      this.scheduleReconnect()
      return
    }
    this.ws.binaryType = 'arraybuffer'
    this.ws.onopen = () => {
      this.retries = 0
      // Flush any queued audio
      for (const chunk of this.pendingAudio) {
        this.ws!.send(chunk.buffer)
      }
      this.pendingAudio = []
      this.opts.onOpen?.()
    }
    this.ws.onmessage = (ev) => {
      if (ev.data instanceof ArrayBuffer) {
        this.opts.onBinary?.(ev.data)
      } else {
        try {
          const msg = JSON.parse(ev.data)
          this.opts.onText?.(msg)
        } catch (e) {
          console.warn('[ws] bad json', e)
        }
      }
    }
    this.ws.onerror = (e) => {
      this.opts.onError?.(e)
    }
    this.ws.onclose = (ev) => {
      this.opts.onClose?.(ev.code, ev.reason)
      if (!this.closed) this.scheduleReconnect()
    }
  }

  private scheduleReconnect() {
    const delay = Math.min(8000, 250 * Math.pow(2, this.retries))
    this.retries++
    if (this.retries > this.maxRetries) {
      console.warn('[ws] max retries reached')
      return
    }
    this.reconnectTimer = window.setTimeout(() => this.connect(), delay)
  }

  private clearReconnect() {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer)
      this.reconnectTimer = null
    }
  }

  sendJSON(obj: any) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(obj))
    }
  }

  sendBinary(int16: Int16Array) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(int16.buffer)
    } else {
      // Queue up to 5 s of audio while disconnected
      if (this.pendingAudio.length < 5) {
        this.pendingAudio.push(int16)
      }
    }
  }

  close() {
    this.closed = true
    this.clearReconnect()
    this.ws?.close()
  }
}
