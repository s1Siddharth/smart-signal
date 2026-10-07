// pages/Dashboard.tsx — Main control room dashboard with 2D simulation
import { useEffect, useRef, useState } from 'react'
import { AlertBanner } from '@/components/AlertBanner'
import { DecisionLog } from '@/components/DecisionLog'
import { TrafficSimulation, type SimSnapshot } from '@/components/TrafficSimulation'
import { RoadCard } from '@/components/RoadCard'
import { SignalHead } from '@/components/SignalHead'
import { TimerRing } from '@/components/TimerRing'
import { SmartSignalWS, type WsMessage } from '@/lib/ws'
import { api } from '@/lib/api'
import { useAuth } from '@/auth/AuthContext'
import { useNavigate } from 'react-router-dom'

const DEFAULT_STATE = {
  ts: 0, phase: 'P1', state: 'GREEN', elapsed_s: 0, max_s: 120, reason_last: '',
  lights: { A: 'RED', B: 'RED', C: 'RED', D: 'RED' },
  roads: {
    A: { count: 0, density: 0, waiting_s: 0, adaptive_green_s: 10 },
    B: { count: 0, density: 0, waiting_s: 0, adaptive_green_s: 10 },
    C: { count: 0, density: 0, waiting_s: 0, adaptive_green_s: 10 },
    D: { count: 0, density: 0, waiting_s: 0, adaptive_green_s: 10 },
  },
  predict: { clear_s: 0, confidence: 'high' },
  emergency: { active: false, road: null as string | null },
  stats: { saved_green_s: 0, fixed_wasted_s: 0, adaptive_wasted_s: 0, fixed_wait_vehicle_s: 0, adaptive_wait_vehicle_s: 0 },
  notifications: [] as { id: number; level: string; text: string }[],
  decision_log: [] as { t: string; text: string }[],
  frame_b64: '',
  simulation: {} as SimSnapshot,
}

export default function Dashboard() {
  const [state, setState] = useState(DEFAULT_STATE)
  const [connected, setConnected] = useState(false)
  const wsRef = useRef<SmartSignalWS | null>(null)
  const { logout } = useAuth()
  const navigate = useNavigate()

  // WebSocket connection for real-time updates
  useEffect(() => {
    const ws = new SmartSignalWS('/ws/state', (data: WsMessage) => {
      setState(prev => ({
        ...prev,
        ...data,
        emergency: { ...prev.emergency, ...(data.emergency as object || {}) },
        predict: { ...prev.predict, ...(data.predict as object || {}) },
        stats: { ...prev.stats, ...(data.stats as object || {}) },
        lights: { ...prev.lights, ...(data.lights as object || {}) },
        roads: { ...prev.roads, ...(data.roads as object || {}) }
      }) as typeof DEFAULT_STATE)
      setConnected(true)
    })
    ws.connect()
    wsRef.current = ws
    return () => ws.disconnect()
  }, [])

  const roads = ['A', 'B', 'C', 'D'] as const

  return (
    <div className="min-h-screen bg-bg grid-bg text-text-primary">
      {/* Top nav */}
      <nav className="border-b border-border bg-panel px-6 py-3 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <span className="font-mono text-accent font-medium">SMART SIGNAL</span>
          <span className="text-text-muted text-xs font-mono">|</span>
          <span className="text-text-secondary text-xs font-sans">Traffic Control Room</span>
          <span
            className={`ml-2 w-2 h-2 rounded-full ${connected ? 'bg-signal-green animate-glow-green' : 'bg-signal-red'}`}
            title={connected ? 'Connected' : 'Disconnected'}
          />
        </div>
        <div className="flex items-center gap-4">
          <button onClick={() => navigate('/analytics')} className="text-text-secondary text-xs hover:text-accent transition-colors font-sans">Analytics</button>
          <button onClick={() => navigate('/commuter')} className="text-text-secondary text-xs hover:text-accent transition-colors font-sans">Commuter</button>
          <button onClick={() => navigate('/settings')} className="text-text-secondary text-xs hover:text-accent transition-colors font-sans">Settings</button>
          <button onClick={logout} className="text-text-muted text-xs hover:text-signal-red transition-colors font-sans">Logout</button>
        </div>
      </nav>

      {/* Alert banner */}
      {state.emergency.active && (
        <div className="px-6 pt-4">
          <AlertBanner active={state.emergency.active} road={state.emergency.road} />
        </div>
      )}

      {/* Main Container */}
      <div className="p-6 flex flex-col gap-6">
        
        {/* ROW 1: Simulation & Live View (Top Half) */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          
          {/* 2D Simulation */}
          <div className="bg-panel border border-border rounded p-4 flex flex-col h-full min-h-[400px]">
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-accent text-xs font-sans font-semibold tracking-wider uppercase">
                2D Live Simulation
              </h2>
              <span className={`text-xs font-mono px-2 py-0.5 rounded ${
                state.state === 'GREEN' ? 'text-signal-green bg-signal-green/10' :
                state.state === 'YELLOW' ? 'text-amber-400 bg-amber-400/10' :
                'text-signal-red bg-signal-red/10'
              }`}>
                {state.phase} · {state.state}
              </span>
            </div>
            <div className="flex-1 flex items-center justify-center">
              <TrafficSimulation
                lights={state.lights}
                simulation={state.simulation}
                signalState={state.state}
                phase={state.phase}
                elapsedS={state.elapsed_s}
                maxS={state.max_s}
              />
            </div>
          </div>

          {/* Live View */}
          <div className="bg-panel border border-border rounded overflow-hidden flex flex-col h-full corner-ticks min-h-[400px]">
            <div className="px-3 pt-3 pb-1 flex items-center justify-between bg-panel">
              <h2 className="text-accent text-xs font-sans font-semibold tracking-wider uppercase">
                Live View
              </h2>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => api.switchSource('0')}
                  className="bg-panel border border-signal-green text-signal-green px-2 py-0.5 rounded text-[10px] font-bold hover:bg-signal-green hover:text-bg transition-colors font-sans"
                >
                  USE WEBCAM
                </button>
                <label className="bg-panel border border-accent text-accent px-2 py-0.5 rounded text-[10px] font-bold hover:bg-accent hover:text-bg transition-colors font-sans cursor-pointer flex items-center justify-center">
                  UPLOAD VIDEO
                  <input
                    type="file"
                    accept="video/mp4,video/x-m4v,video/*"
                    className="hidden"
                    onChange={async (e) => {
                      const file = e.target.files?.[0];
                      if (file) {
                        try {
                          await api.uploadVideo(file);
                        } catch (e) {
                          alert("Upload failed. Make sure the backend is running.");
                        }
                      }
                    }}
                  />
                </label>
                <button
                  onClick={() => api.switchSource('none')}
                  className="bg-signal-red/10 text-signal-red border border-signal-red/30 px-2 py-0.5 rounded text-[10px] font-bold hover:bg-signal-red hover:text-bg transition-colors font-sans ml-2"
                  title="Clear uploaded video and turn off camera"
                >
                  CLEAR VIDEO
                </button>
                <span className="font-mono text-xs text-text-muted ml-2">{connected ? 'LIVE' : 'NO SIGNAL'}</span>
              </div>
            </div>
            <div className="flex-1 bg-bg relative flex items-center justify-center">
              {state.frame_b64 ? (
                <img
                  src={`data:image/jpeg;base64,${state.frame_b64}`}
                  alt="Live camera feed with vehicle detection"
                  className="w-full h-full object-contain absolute inset-0"
                />
              ) : (
                <div className="w-full h-full flex flex-col items-center justify-center gap-4 text-text-muted text-sm font-mono p-4 absolute inset-0">
                  <span>Waiting for camera feed...</span>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* ROW 2: Bottom half widgets */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          
          {/* Column 1: Phase Timer & Signal Heads */}
          <div className="flex flex-col gap-4">
            {/* Timer ring */}
            <div className="bg-panel border border-border rounded p-4 flex flex-col items-center gap-2">
              <h2 className="text-accent text-xs font-sans font-semibold tracking-wider uppercase self-start">
                Phase {state.phase} Timer
              </h2>
              <div className="relative flex justify-center items-center" style={{ height: 130 }}>
                <TimerRing elapsed={state.elapsed_s} max={state.max_s} cutoff={35} />
                <div className="absolute flex flex-col items-center pointer-events-none">
                  <span className="font-mono text-2xl font-medium text-text-primary">
                    {Math.max(0, Math.ceil(state.max_s - state.elapsed_s))}s
                  </span>
                  <span className="text-text-secondary text-xs">remaining</span>
                </div>
              </div>
              <div className="text-center">
                <span className="text-text-muted text-xs font-mono">Predict clear: </span>
                <span className="text-accent text-xs font-mono font-medium">~{state.predict.clear_s}s</span>
                <span className="text-text-muted text-xs ml-1">({state.predict.confidence})</span>
              </div>
              <div className="text-text-muted text-xs font-mono">Last: {state.reason_last || '—'}</div>
            </div>

            {/* Signal heads */}
            <div className="bg-panel border border-border rounded p-4">
              <h2 className="text-accent text-xs font-sans font-semibold tracking-wider uppercase mb-4">
                Signal Heads
              </h2>
              <div className="grid grid-cols-4 gap-2">
                {roads.map(r => (
                  <SignalHead
                    key={r}
                    road={r}
                    state={(state.lights[r] as 'GREEN' | 'RED' | 'YELLOW' | 'OFF') || 'OFF'}
                    size="sm"
                  />
                ))}
              </div>
            </div>
          </div>

          {/* Column 2: Stats & Decision Log */}
          <div className="flex flex-col gap-4">
            {/* Simplified Stats bar */}
            <div className="bg-panel border border-border rounded p-4 grid grid-cols-3 gap-2 text-center">
              <div>
                <div className="font-mono text-xl font-bold text-signal-green mb-1">
                  {Math.round(state.stats.saved_green_s)}s
                </div>
                <span className="text-text-muted text-[10px] uppercase font-sans tracking-wider">Saved</span>
              </div>
              <div>
                <div className="font-mono text-xl font-bold text-signal-red mb-1">
                  {Math.round(state.stats.fixed_wasted_s)}s
                </div>
                <span className="text-text-muted text-[10px] uppercase font-sans tracking-wider">Fixed Wasted</span>
              </div>
              <div>
                <div className="font-mono text-xl font-bold text-signal-amber mb-1">
                  {Math.round(state.stats.adaptive_wasted_s)}s
                </div>
                <span className="text-text-muted text-[10px] uppercase font-sans tracking-wider">Adaptive Wasted</span>
              </div>
            </div>

            {/* Decision log */}
            <DecisionLog entries={state.decision_log} />
          </div>

          {/* Column 3: Road Cards & Notifications */}
          <div className="flex flex-col gap-4">
            {/* Road cards */}
            <div className="grid grid-cols-2 gap-3">
              {roads.map(r => (
                <RoadCard
                  key={r}
                  road={r}
                  light={state.lights[r] ?? 'RED'}
                  count={state.roads[r]?.count ?? 0}
                  density={state.roads[r]?.density ?? 0}
                  waiting_s={state.roads[r]?.waiting_s ?? 0}
                />
              ))}
            </div>

            {/* Notifications feed */}
            <div className="bg-panel border border-border rounded p-3">
              <div className="text-accent text-xs mb-2 font-sans font-semibold tracking-wider uppercase">
                Notifications
              </div>
              <div className="flex flex-col gap-1 max-h-32 overflow-y-auto">
                {state.notifications.length === 0 ? (
                  <span className="text-text-muted text-xs font-mono">Quiet — no events.</span>
                ) : (
                  [...state.notifications].reverse().map(n => (
                    <div key={n.id} className="text-xs font-mono animate-fade-in" style={{
                      color: n.level === 'alert' ? '#FFB020' : n.level === 'warning' ? '#FF4D5E' : '#94A3B8',
                    }}>
                      {n.text}
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}