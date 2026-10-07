// pages/Commuter.tsx — Public mobile-first page (no login, no video)
import { useEffect, useRef, useState } from 'react'
import { SmartSignalWS, type WsMessage } from '@/lib/ws'

const LIGHT_COLORS: Record<string, string> = {
  GREEN:  '#2EE59D',
  RED:    '#FF4D5E',
  YELLOW: '#FFB020',
}

const DEFAULT = {
  lights: { A: 'RED', B: 'RED', C: 'RED', D: 'RED' },
  predict: { clear_s: 0 },
  emergency: { active: false, road: null as string | null },
  notifications: [] as { id: number; level: string; text: string }[],
}

type State = typeof DEFAULT

export default function Commuter() {
  const [state, setState] = useState<State>(DEFAULT)
  const [notifEnabled, setNotifEnabled] = useState(false)
  const wsRef = useRef<SmartSignalWS | null>(null)

  useEffect(() => {
    const ws = new SmartSignalWS('/ws/public', (data: WsMessage) => {
      setState(prev => ({
        ...prev,
        ...data,
        emergency: { ...prev.emergency, ...(data.emergency as object || {}) },
        predict: { ...prev.predict, ...(data.predict as object || {}) },
        lights: { ...prev.lights, ...(data.lights as object || {}) }
      }) as State)
    }, false)
    ws.connect()
    wsRef.current = ws
    return () => ws.disconnect()
  }, [])

  const enableNotifications = async () => {
    const perm = await Notification.requestPermission()
    setNotifEnabled(perm === 'granted')
  }

  const roads = ['A', 'B', 'C', 'D'] as const

  return (
    <div className="min-h-screen bg-bg text-text-primary px-4 py-6 max-w-md mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="font-sans font-bold text-text-primary text-lg">Traffic Signal</h1>
          <p className="text-text-muted text-xs font-mono">Live status — commuter view</p>
        </div>
        {!notifEnabled && (
          <button
            onClick={enableNotifications}
            id="btn-enable-notifications"
            className="text-xs bg-panel border border-border rounded px-3 py-1.5 text-accent hover:border-accent transition-colors font-sans"
          >
            Enable alerts
          </button>
        )}
      </div>

      {/* Emergency alert */}
      {state.emergency?.active && (
        <div className="mb-4 p-3 rounded border animate-pulse-amber text-signal-amber text-sm font-sans"
          style={{ background: 'rgba(255,176,32,0.1)', borderColor: '#FFB020' }}
          role="alert" aria-live="assertive">
          🚨 Ambulance on Road {state.emergency.road} — priority green active
        </div>
      )}

      {/* Road status cards */}
      <div className="grid grid-cols-2 gap-3 mb-6">
        {roads.map(r => {
          const light = state.lights[r] ?? 'RED'
          const col = LIGHT_COLORS[light] ?? '#4A5568'
          const eta = light !== 'GREEN' ? state.predict?.clear_s : 0
          return (
            <div
              key={r}
              className="bg-panel border border-border rounded p-4 flex flex-col items-center gap-2"
              style={{ borderColor: light === 'GREEN' ? `${col}44` : undefined }}
            >
              {/* Big signal dot */}
              <div
                className={`w-14 h-14 rounded-full flex items-center justify-center ${light === 'GREEN' ? 'animate-glow-green' : ''}`}
                style={{ background: `${col}22`, border: `2px solid ${col}` }}
              >
                <div className="w-8 h-8 rounded-full" style={{ background: col }} />
              </div>
              <span className="font-sans font-semibold text-text-primary">Road {r}</span>
              <span className="font-mono text-xs" style={{ color: col }}>{light}</span>
              {eta > 0 && (
                <span className="text-text-muted text-xs font-mono">green in ~{Math.ceil(eta)}s</span>
              )}
            </div>
          )
        })}
      </div>

      {/* Notification feed */}
      <div className="bg-panel border border-border rounded p-4">
        <h2 className="text-accent text-xs font-sans font-semibold tracking-wider uppercase mb-3">
          Live Alerts
        </h2>
        <div className="flex flex-col gap-2 max-h-64 overflow-y-auto">
          {(state.notifications ?? []).length === 0 ? (
            <p className="text-text-muted text-xs font-mono">All clear — no active alerts.</p>
          ) : (
            [...(state.notifications ?? [])].reverse().map(n => (
              <div
                key={n.id}
                className="text-sm font-sans animate-fade-in py-1 border-b border-border last:border-0"
                style={{ color: n.level === 'alert' ? '#FFB020' : n.level === 'warning' ? '#FF4D5E' : '#94A3B8' }}
              >
                {n.text}
              </div>
            ))
          )}
        </div>
      </div>

      {/* Privacy note */}
      <p className="mt-6 text-center text-text-muted text-xs font-sans">
        This page shows signal status only. No camera feed or personal data is collected.
      </p>
    </div>
  )
}
