// components/TrafficSimulation.tsx
// Top-view 2D canvas simulation of the intersection.
// Vehicles move, queue, stop at red, cross on green.
// Driven entirely by live backend simulation state.

import { useEffect, useRef, useCallback } from 'react'

// ── Types ────────────────────────────────────────────────────────

export interface VehicleData {
  vid: number
  road: string
  dist: number   // distance from intersection center (normalized 0–1)
  speed: number
  state: 'approaching' | 'stopped' | 'crossing' | 'exiting'
  color: string
}

export interface SimSnapshot {
  A?: VehicleData[]
  B?: VehicleData[]
  C?: VehicleData[]
  D?: VehicleData[]
}

interface TrafficSimulationProps {
  lights: Record<string, string>   // A/B/C/D -> GREEN|YELLOW|RED
  simulation: SimSnapshot          // per-road vehicle arrays from backend
  signalState: string              // GREEN|YELLOW|ALL_RED|EMERGENCY
  phase: string                    // P1|P2
  elapsedS: number
  maxS: number
}

// ── Canvas constants ─────────────────────────────────────────────

const W = 640
const H = 640
const CX = W / 2
const CY = H / 2

const ROAD_W = 85
const BOX = ROAD_W
const STOP_PX = 135
const VEH_W = 26
const VEH_H = 44
const SIG_R = 14

const ROAD_COLOR    = '#1A2236'
const GRASS_COLOR   = '#0D1B0D'
const MARKING_COLOR = '#FFFFFF'
const BORDER_COLOR  = '#C8A600'
const BOX_COLOR     = '#253045'

const SIGNAL_COLORS: Record<string, string> = {
  GREEN:  '#2EE59D',
  YELLOW: '#FFB020',
  RED:    '#FF4D5E',
  OFF:    '#1E2736',
}

const GLOW_COLORS: Record<string, string> = {
  GREEN:  'rgba(46, 229, 157, 0.5)',
  YELLOW: 'rgba(255, 176, 32, 0.5)',
  RED:    'rgba(255, 77, 94, 0.5)',
}

// ── Coordinate helpers ────────────────────────────────────────────

function vehicleXY(road: string, distNorm: number): [number, number] {
  const distPx = distNorm * 260
  const offset = ROAD_W / 2 - 12
  switch (road) {
    case 'A': return [CX - distPx, CY - offset]
    case 'B': return [CX - offset, CY - distPx]
    case 'C': return [CX + distPx, CY + offset]
    case 'D': return [CX + offset, CY + distPx]
    default:  return [CX, CY]
  }
}

function vehicleAngle(road: string): number {
  switch (road) {
    case 'A': return Math.PI / 2
    case 'B': return Math.PI
    case 'C': return -Math.PI / 2
    case 'D': return 0
    default:  return 0
  }
}

// ── Drawing functions ─────────────────────────────────────────────

function drawRoads(ctx: CanvasRenderingContext2D) {
  ctx.fillStyle = GRASS_COLOR
  ctx.fillRect(0, 0, W, H)

  ctx.fillStyle = BORDER_COLOR
  ctx.fillRect(CX - ROAD_W - 4, 0, (ROAD_W + 4) * 2, H)
  ctx.fillRect(0, CY - ROAD_W - 4, W, (ROAD_W + 4) * 2)

  ctx.fillStyle = ROAD_COLOR
  ctx.fillRect(CX - ROAD_W, 0, ROAD_W * 2, H)
  ctx.fillRect(0, CY - ROAD_W, W, ROAD_W * 2)

  ctx.fillStyle = BOX_COLOR
  ctx.fillRect(CX - BOX, CY - BOX, BOX * 2, BOX * 2)

  ctx.strokeStyle = MARKING_COLOR
  ctx.lineWidth = 2
  ctx.setLineDash([18, 14])

  ctx.beginPath(); ctx.moveTo(CX, 0); ctx.lineTo(CX, CY - BOX); ctx.stroke()
  ctx.beginPath(); ctx.moveTo(CX, CY + BOX); ctx.lineTo(CX, H); ctx.stroke()
  ctx.beginPath(); ctx.moveTo(0, CY); ctx.lineTo(CX - BOX, CY); ctx.stroke()
  ctx.beginPath(); ctx.moveTo(CX + BOX, CY); ctx.lineTo(W, CY); ctx.stroke()

  ctx.setLineDash([])
  ctx.lineWidth = 3

  // Stop lines
  ctx.beginPath(); ctx.moveTo(CX - ROAD_W + 4, CY - STOP_PX); ctx.lineTo(CX + ROAD_W - 4, CY - STOP_PX); ctx.stroke()
  ctx.beginPath(); ctx.moveTo(CX - ROAD_W + 4, CY + STOP_PX); ctx.lineTo(CX + ROAD_W - 4, CY + STOP_PX); ctx.stroke()
  ctx.beginPath(); ctx.moveTo(CX + STOP_PX, CY - ROAD_W + 4); ctx.lineTo(CX + STOP_PX, CY + ROAD_W - 4); ctx.stroke()
  ctx.beginPath(); ctx.moveTo(CX - STOP_PX, CY - ROAD_W + 4); ctx.lineTo(CX - STOP_PX, CY + ROAD_W - 4); ctx.stroke()
}

function drawSignal(
  ctx: CanvasRenderingContext2D,
  road: string,
  state: string,
  t: number,
) {
  const col = SIGNAL_COLORS[state] ?? SIGNAL_COLORS.OFF
  const glow = GLOW_COLORS[state]

  let sx: number, sy: number
  switch (road) {
    case 'A': sx = CX - STOP_PX - 8; sy = CY - ROAD_W - 24; break
    case 'B': sx = CX - ROAD_W - 24; sy = CY - STOP_PX - 8; break
    case 'C': sx = CX + STOP_PX + 8; sy = CY + ROAD_W + 24; break
    case 'D': sx = CX + ROAD_W + 24; sy = CY + STOP_PX + 8; break
    default:  return
  }

  ctx.fillStyle = '#111723'
  ctx.strokeStyle = '#1E2736'
  ctx.lineWidth = 1
  ctx.beginPath()
  ctx.arc(sx, sy, SIG_R + 4, 0, Math.PI * 2)
  ctx.fill(); ctx.stroke()

  if (glow && state !== 'RED') {
    const pulse = 0.6 + 0.4 * Math.sin(t * 4)
    ctx.shadowBlur = 16 * pulse
    ctx.shadowColor = glow
  }

  ctx.fillStyle = col
  ctx.beginPath()
  ctx.arc(sx, sy, SIG_R, 0, Math.PI * 2)
  ctx.fill()
  ctx.shadowBlur = 0

  ctx.fillStyle = '#94A3B8'
  ctx.font = 'bold 11px "Space Grotesk", sans-serif'
  ctx.textAlign = 'center'
  ctx.textBaseline = 'middle'
  let lx = sx, ly = sy
  switch (road) {
    case 'A': ly = sy - 28; break
    case 'B': lx = sx - 28; break
    case 'C': ly = sy + 28; break
    case 'D': lx = sx + 28; break
  }
  ctx.fillText(road, lx, ly)
}

function drawVehicle(
  ctx: CanvasRenderingContext2D,
  road: string,
  dist: number,
  color: string,
  state: string,
  t: number,
) {
  const [x, y] = vehicleXY(road, dist)
  const angle = vehicleAngle(road)
  const alpha = state === 'exiting' ? Math.max(0, 1 + dist / 0.30) : 1.0

  ctx.save()
  ctx.globalAlpha = alpha
  ctx.translate(x, y)
  ctx.rotate(angle)

  const hw = VEH_W / 2
  const hh = VEH_H / 2

  // Shadow
  ctx.fillStyle = 'rgba(0,0,0,0.5)'
  ctx.fillRect(-hw + 2, -hh + 2, VEH_W, VEH_H)

  // Body
  ctx.fillStyle = color
  ctx.strokeStyle = '#000000'
  ctx.lineWidth = 1
  ctx.beginPath()
  ;(ctx as any).roundRect(-hw, -hh, VEH_W, VEH_H, 3)
  ctx.fill()
  ctx.stroke()

  // Windshield
  ctx.fillStyle = 'rgba(180,220,255,0.5)'
  ctx.fillRect(-hw + 3, -hh + 4, VEH_W - 6, hh - 2)

  // Headlights
  if (state !== 'exiting') {
    ctx.fillStyle = '#FFFDE0'
    ctx.fillRect(-hw + 2, -hh - 1, 4, 2)
    ctx.fillRect(hw - 6, -hh - 1, 4, 2)
  }

  // Brake lights when stopped
  if (state === 'stopped') {
    ctx.shadowBlur = 6 + 4 * Math.abs(Math.sin(t * 2))
    ctx.shadowColor = 'rgba(255,77,94,0.8)'
    ctx.fillStyle = '#FF4D5E'
    ctx.fillRect(-hw + 2, hh - 1, 4, 2)
    ctx.fillRect(hw - 6, hh - 1, 4, 2)
  }

  ctx.shadowBlur = 0
  ctx.restore()
}

function drawCounterBadge(
  ctx: CanvasRenderingContext2D,
  road: string,
  count: number,
) {
  let bx: number, by: number
  switch (road) {
    case 'A': bx = 36; by = CY + ROAD_W + 36; break
    case 'B': bx = CX - ROAD_W - 36; by = 30; break
    case 'C': bx = W - 36; by = CY - ROAD_W - 36; break
    case 'D': bx = CX + ROAD_W + 36; by = H - 30; break
    default: return
  }
  ctx.fillStyle = 'rgba(17, 23, 35, 0.85)'
  ctx.strokeStyle = '#3DD6F5'
  ctx.lineWidth = 1
  ctx.beginPath()
  ;(ctx as any).roundRect(bx - 20, by - 12, 40, 24, 4)
  ctx.fill(); ctx.stroke()

  ctx.fillStyle = '#3DD6F5'
  ctx.font = 'bold 12px "JetBrains Mono", monospace'
  ctx.textAlign = 'center'
  ctx.textBaseline = 'middle'
  ctx.fillText(String(count), bx, by)
}

// ── Main component ────────────────────────────────────────────────

export function TrafficSimulation({
  lights,
  simulation,
  signalState,
  phase,
  elapsedS,
  maxS,
}: TrafficSimulationProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const animRef   = useRef<number>(0)
  const tRef      = useRef<number>(0)

  const lightsRef  = useRef(lights)
  const simRef     = useRef(simulation)
  const stateRef   = useRef(signalState)
  const elapsedRef = useRef(elapsedS)
  const maxRef     = useRef(maxS)

  lightsRef.current  = lights
  simRef.current     = simulation
  stateRef.current   = signalState
  elapsedRef.current = elapsedS
  maxRef.current     = maxS

  const draw = useCallback(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    if (!ctx) return

    tRef.current += 0.016
    const t   = tRef.current
    const sim = simRef.current
    const lts = lightsRef.current

    drawRoads(ctx)

    const roads = ['A', 'B', 'C', 'D'] as const
    for (const road of roads) {
      const vehs = sim[road] ?? []
      for (const v of vehs) {
        drawVehicle(ctx, road, v.dist, v.color, v.state, t)
      }
    }

    for (const road of roads) {
      drawSignal(ctx, road, lts[road] ?? 'RED', t)
    }

    for (const road of roads) {
      const count = (sim[road] ?? []).length
      drawCounterBadge(ctx, road, count)
    }

    // Countdown ring
    const elapsed   = elapsedRef.current
    const maxSec    = maxRef.current
    const remaining = Math.max(0, maxSec - elapsed)
    const frac      = remaining / Math.max(maxSec, 1)
    const sigState  = stateRef.current

    const ringColor =
      sigState === 'YELLOW'    ? '#FFB020' :
      sigState === 'ALL_RED'   ? '#FF4D5E' :
      sigState === 'EMERGENCY' ? '#FF4D5E' :
      '#2EE59D'

    ctx.beginPath()
    ctx.arc(CX, CY, 38, 0, Math.PI * 2)
    ctx.fillStyle = 'rgba(10,14,20,0.9)'
    ctx.fill()
    ctx.strokeStyle = '#1E2736'
    ctx.lineWidth = 2
    ctx.stroke()

    ctx.beginPath()
    ctx.arc(CX, CY, 38, -Math.PI / 2, -Math.PI / 2 + frac * Math.PI * 2)
    ctx.strokeStyle = ringColor
    ctx.lineWidth = 4
    ctx.stroke()

    ctx.fillStyle = ringColor
    ctx.font = 'bold 16px "JetBrains Mono", monospace'
    ctx.textAlign = 'center'
    ctx.textBaseline = 'middle'
    ctx.fillText(`${Math.ceil(remaining)}`, CX, CY - 4)
    ctx.font = '10px "Space Grotesk", sans-serif'
    ctx.fillStyle = '#4A5568'
    ctx.fillText('sec', CX, CY + 10)
  }, [])

  useEffect(() => {
    const loop = () => {
      draw()
      animRef.current = requestAnimationFrame(loop)
    }
    animRef.current = requestAnimationFrame(loop)
    return () => cancelAnimationFrame(animRef.current)
  }, [draw])

  return (
    <div className="relative w-full" style={{ aspectRatio: '1 / 1', maxWidth: 640 }}>
      <canvas
        ref={canvasRef}
        width={W}
        height={H}
        style={{ width: '100%', height: '100%', display: 'block', borderRadius: 6 }}
        aria-label="2D virtual traffic intersection simulation"
      />
      <div
        className="absolute top-2 right-2 text-xs font-mono px-2 py-1 rounded"
        style={{
          background: 'rgba(10,14,20,0.8)',
          color: signalState === 'GREEN' ? '#2EE59D' :
                 signalState === 'YELLOW' ? '#FFB020' : '#FF4D5E',
          border: '1px solid currentColor',
        }}
      >
        {phase} · {signalState}
      </div>
    </div>
  )
}
