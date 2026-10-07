// components/TimerRing.tsx — Circular 120 s countdown ring with 35 s tick mark
interface TimerRingProps {
  elapsed: number    // seconds elapsed
  max: number        // max green seconds (usually 120)
  cutoff?: number    // early-switch tick mark (usually 35)
}

export function TimerRing({ elapsed, max, cutoff = 35 }: TimerRingProps) {
  const R = 52
  const stroke = 6
  const size = (R + stroke) * 2
  const circ = 2 * Math.PI * R
  const progress = Math.min(elapsed / max, 1)
  const dashoffset = circ * (1 - progress)

  // Tick mark angle for cutoff
  const cutoffAngle = (cutoff / max) * 360 - 90  // -90 to start from top
  const tickRad = (cutoffAngle * Math.PI) / 180
  const cx = size / 2, cy = size / 2
  const tx = cx + (R - 4) * Math.cos(tickRad)
  const ty = cy + (R - 4) * Math.sin(tickRad)
  const tx2 = cx + (R + 4) * Math.cos(tickRad)
  const ty2 = cy + (R + 4) * Math.sin(tickRad)

  const remaining = Math.max(0, max - elapsed)
  const color = progress > 0.85 ? '#FF4D5E' : progress > 0.6 ? '#FFB020' : '#2EE59D'

  return (
    <div className="flex flex-col items-center gap-2">
      <svg width={size} height={size} className="rotate-[-90deg]">
        {/* Track */}
        <circle cx={cx} cy={cy} r={R} fill="none" stroke="#1E2736" strokeWidth={stroke} />
        {/* Progress arc */}
        <circle
          cx={cx} cy={cy} r={R}
          fill="none"
          stroke={color}
          strokeWidth={stroke}
          strokeLinecap="round"
          strokeDasharray={circ}
          strokeDashoffset={dashoffset}
          style={{ transition: 'stroke-dashoffset 0.3s linear, stroke 0.3s ease' }}
        />
        {/* Cutoff tick mark */}
        <line x1={tx} y1={ty} x2={tx2} y2={ty2} stroke="#FFB020" strokeWidth={2} />
      </svg>
      <div className="absolute flex flex-col items-center justify-center" style={{ marginTop: -size / 2 - 12 }}>
        <span className="font-mono text-2xl font-medium text-text-primary" style={{ color }}>
          {Math.ceil(remaining)}s
        </span>
        <span className="text-text-secondary text-xs">of {max}s</span>
      </div>
    </div>
  )
}
