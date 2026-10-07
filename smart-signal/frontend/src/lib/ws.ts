// lib/ws.ts — WebSocket client with token auth (first message)
import { auth } from './firebase'

const API_URL = import.meta.env.VITE_API_URL || ''

function wsUrl(path: string): string {
  if (API_URL) {
    // Convert http(s) → ws(s)
    return API_URL.replace(/^http/, 'ws') + path
  }
  const proto = window.location.protocol === 'https:' ? 'wss' : 'ws'
  return `${proto}://${window.location.host}${path}`
}

export type WsMessage = Record<string, unknown>

export class SmartSignalWS {
  private ws: WebSocket | null = null
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null
  private closed = false

  constructor(
    private readonly path: string,
    private readonly onMessage: (data: WsMessage) => void,
    private readonly requireAuth = true,
  ) {}

  connect(): void {
    this.closed = false
    this._open()
  }

  disconnect(): void {
    this.closed = true
    if (this.reconnectTimer) clearTimeout(this.reconnectTimer)
    this.ws?.close()
  }

  private _open(): void {
    const url = wsUrl(this.path)
    this.ws = new WebSocket(url)

    this.ws.onopen = async () => {
      if (this.requireAuth) {
        const token = await auth.currentUser?.getIdToken()
        this.ws?.send(JSON.stringify({ token: token ?? '' }))
      }
    }

    this.ws.onmessage = (e) => {
      try {
        const data = JSON.parse(e.data) as WsMessage
        this.onMessage(data)
      } catch {
        // ignore malformed
      }
    }

    this.ws.onclose = () => {
      if (!this.closed) {
        this.reconnectTimer = setTimeout(() => this._open(), 2000)
      }
    }
  }
}
