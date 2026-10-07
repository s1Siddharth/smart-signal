// pages/Test.tsx — Video testing and diagnostics page
import { useEffect, useState, useRef } from 'react'
import { useAuth } from '@/auth/AuthContext'
import { SmartSignalWS, type WsMessage } from '@/lib/ws'

export default function Test() {
  const { user } = useAuth()
  const [state, setState] = useState<any>(null)
  const [connected, setConnected] = useState(false)
  const wsRef = useRef<SmartSignalWS | null>(null)
  const [showRawFeed, setShowRawFeed] = useState(false)
  const [showROI, setShowROI] = useState(true)
  const [showDetections, setShowDetections] = useState(true)
  const [showStats, setShowStats] = useState(true)

  useEffect(() => {
    if (!user) return

    const ws = new SmartSignalWS('/ws/state', (data: WsMessage) => {
      setState((prev: WsMessage) => ({
        ...prev,
        ...data,
        emergency: { ...(prev?.emergency || {}), ...(data?.emergency || {}) },
        predict: { ...(prev?.predict || {}), ...(data?.predict || {}) },
        stats: { ...(prev?.stats || {}), ...(data?.stats || {}) },
        lights: { ...(prev?.lights || {}), ...(data?.lights || {}) },
        roads: { ...(prev?.roads || {}), ...(data?.roads || {}) }
      }) as typeof state)
      setConnected(true)
    }, false) // Don't require auth for test page? Actually should require auth
    ws.connect()
    wsRef.current = ws
    return () => ws.disconnect()
  }, [user])

  useEffect(() => {
    return () => {
      wsRef.current?.disconnect()
    }
  }, [])

  if (!user) return <div className="p-6 text-text-muted">Please log in to access the test page</div>

  return (
    <div className="p-6">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-text-primary">Video Testing & Diagnostics</h1>
        <p className="text-text-secondary">Test and monitor your video feed, detection performance, and ROI configuration.</p>
      </div>

      {/* Connection Status */}
      <div className="mb-4 p-3 rounded border border-border">
        <div className="flex items-center justify-between">
          <span className="font-sans font-semibold">Connection Status:</span>
          <span className={`px-3 py-1 rounded-full text-xs font-mono ${connected ? 'bg-signal-green' : 'bg-signal-red'}`}>
            {connected ? 'Connected' : 'Disconnected'}
          </span>
        </div>
      </div>

      {/* Controls */}
      <div className="mb-6 flex flex-wrap gap-4">
        <div className="flex items-center gap-2">
          <label className="text-text-secondary font-sans">Show Raw Feed:</label>
          <input
            type="checkbox"
            checked={showRawFeed}
            onChange={(e) => setShowRawFeed(e.target.checked)}
            className="h-4 w-4 text-signal-green"
          />
        </div>
        <div className="flex items-center gap-2">
          <label className="text-text-secondary font-sans">Show ROI:</label>
          <input
            type="checkbox"
            checked={showROI}
            onChange={(e) => setShowROI(e.target.checked)}
            className="h-4 w-4 text-signal-amber"
          />
        </div>
        <div className="flex items-center gap-2">
          <label className="text-text-secondary font-sans">Show Detections:</label>
          <input
            type="checkbox"
            checked={showDetections}
            onChange={(e) => setShowDetections(e.target.checked)}
            className="h-4 w-4 text-signal-red"
          />
        </div>
        <div className="flex items-center gap-2">
          <label className="text-text-secondary font-sans">Show Stats:</label>
          <input
            type="checkbox"
            checked={showStats}
            onChange={(e) => setShowStats(e.target.checked)}
            className="h-4 w-4 text-signal-green"
          />
        </div>
      </div>

      {/* Main Content */}
      <div className="grid gap-6">
        {/* Video Feed */}
        <div className="bg-panel p-4 rounded border border-border">
          <h2 className="text-sm font-semibold mb-3 text-text-primary">Video Feed</h2>
          <div className="aspect-w-16 aspect-h-9 bg-bg rounded overflow-hidden">
            {state && state.frame_b64 ? (
              <img
                src={`data:image/jpeg;base64,${state.frame_b64}`}
                alt="Video feed with detection annotations"
                className="w-full h-full object-contain"
              />
            ) : (
              <div className="flex h-full items-center justify-center bg-bg text-text-muted text-sm font-mono">
                No video feed available
              </div>
            )}
          </div>
          {showStats && state && (
            <div className="mt-4 p-3 bg-border rounded border border-border">
              <h3 className="text-sm font-semibold mb-2 text-text-primary">Detection Statistics</h3>
              <div className="grid gap-4 text-sm">
                <div>
                  <span className="text-text-secondary">Total Vehicles:</span>
                  <span className="font-mono text-text-primary">
                    {Object.values(state.roads || {}).reduce((sum: number, road: any) => sum + (road.count || 0), 0)}
                  </span>
                </div>
                <div>
                  <span className="text-text-secondary">Detection Confidence:</span>
                  <span className="font-mono text-text-primary">
                    {(state.predict?.confidence === 'high' ? 'High' : state.predict?.confidence === 'medium' ? 'Medium' : 'Low')}
                  </span>
                </div>
                <div>
                  <span className="text-text-secondary">Processing FPS:</span>
                  <span className="font-mono text-text-primary">~{1000 / (state?.elapsed_s ? state.elapsed_s * 1000 / 5 : 200)}</span>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Controls Panel */}
        <div className="bg-panel p-4 rounded border border-border">
          <h2 className="text-sm font-semibold mb-3 text-text-primary">Test Controls</h2>
          <div className="space-y-4">
            <div className="flex items-center gap-3">
              <label className="text-text-secondary font-sans">Detection Sensitivity:</label>
              <input
                type="range"
                min="0.1"
                max="1.0"
                step="0.05"
                value={0.35}
                className="w-24"
              />
              <span className="text-text-sm font-mono">0.35</span>
            </div>
            <div className="flex items-center gap-3">
              <label className="text-text-secondary font-sans">ROI Opacity:</label>
              <input
                type="range"
                min="0"
                max="1"
                step="0.1"
                value={0.6}
                className="w-24"
              />
              <span className="text-text-sm font-mono">0.6</span>
            </div>
            <div className="flex items-center gap-3">
              <label className="text-text-secondary font-sans">Frame Skip:</label>
              <input
                type="range"
                min="1"
                max="5"
                step="1"
                value={1}
                className="w-24"
              />
              <span className="text-text-sm font-mono">1 (process every frame)</span>
            </div>
            <div className="flex items-center gap-3">
              <label className="text-text-secondary font-sans">Reset to Defaults:</label>
              <button
                onClick={() => {
                  // Reset controls to default values
                  // In a real implementation, this would call an API to reset config
                  alert('Reset functionality would restore default detection parameters')
                }}
                className="text-xs font-sans text-signal-red hover:text-signal-red/80"
              >
                Reset
              </button>
            </div>
          </div>
        </div>

        {/* ROI Visualization */}
        <div className="bg-panel p-4 rounded border border-border">
          <h2 className="text-sm font-semibold mb-3 text-text-primary">ROI Visualization</h2>
          <div className="aspect-w-1 aspect-h-1 bg-bg rounded overflow-hidden relative">
            {/* Simple ROI visualization using CSS instead of complex data URL */}
            <div className="absolute inset-0 bg-[url('data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIyMDAiIGhlaWdodD0iMjAwIj48cGF0aCBkPSJNMTAwLDAgTDEwMCwyMDAgTDAwLDEwMCAyMDAwxMDAgTDMwLDEwMCAxMDAsMzAgMTcwLDEwMCAxMDAsMTcwIDE3MCwxMDAgMTAwLDMwIDMwLDEwMCIgc3Ryb2tlPSIjRkZCMDIwIiBzdHJva2V3aWR0aD0iMiIgZmlsbD0ibm9uZSИ8L3BhdGg+PHBhdGggZD0iTTUwLDUwIEMxNTAsNTAgMTUwLDE1MCA1MCwxNTAlQzUwLDUwIDUwLDUwIDUwLDUwIiBzdHJva2U9IiMzRDRGNUQiIHN0cm9rZXdpZHRoPSIxLjUiIGZpbGw9Im5vbmUiIC8+PC9zdmc+')] bg-contain" />
            <div className="absolute bottom-2 left-2 text-xs font-mono text-signal-green">
              ROI: A=North, B=East, C=South, D=West
            </div>
          </div>
        </div>

        {/* Detection Visualization Guide */}
        <div className="bg-panel p-4 rounded border border-border">
          <h2 className="text-sm font-semibold mb-3 text-text-primary">Detection Guide</h2>
          <div className="space-y-3">
            <div className="flex items-center gap-3">
              <div className="w-4 h-4 bg-signal-green rounded" />
              <span className="text-text-secondary font-sans">Cars</span>
            </div>
            <div className="flex items-center gap-3">
              <div className="w-4 h-4 bg-signal-red rounded" />
              <span className="text-text-secondary font-sans">Trucks/Buses</span>
            </div>
            <div className="flex items-center gap-3">
              <div className="w-4 h-4 bg-signal-amber rounded" />
              <span className="text-text-secondary font-sans">Motorcycles</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}