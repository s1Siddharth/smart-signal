// components/RoadCard.tsx — Per-road vehicle count + density + wait time
interface RoadCardProps {
  road: string
  light: string
  count: number
  density: number
  waiting_s: number
}

const LIGHT_COLORS: Record<string, string> = {
  GREEN:  '#2EE59D',
  RED:    '#FF4D5E',
  YELLOW: '#FFB020',
}

export function RoadCard({ road, light, count, density, waiting_s }: RoadCardProps) {
  const color = LIGHT_COLORS[light] ?? '#4A5568'
  const densityPct = Math.min((density / 10) * 100, 100)

  return (
    <div
      className="bg-panel border border-border rounded p-4 flex flex-col gap-2 transition-colors duration-150"
      style={{ borderColor: light === 'GREEN' ? `${color}44` : undefined }}
    >
      <div className="flex items-center justify-between">
        <span className="font-sans font-semibold text-text-primary text-sm">Road {road}</span>
        <span
          className="text-xs font-mono font-medium px-2 py-0.5 rounded"
          style={{ color, background: `${color}22` }}
        >
          {light}
        </span>
      </div>

      {/* Vehicle count */}
      <div className="flex items-baseline gap-1">
        <span className="font-mono text-3xl font-medium text-text-primary">{count}</span>
        <span className="text-text-secondary text-xs">vehicles</span>
      </div>

      {/* Density bar */}
      <div>
        <div className="flex justify-between text-xs text-text-muted mb-1">
          <span>Density</span>
          <span className="font-mono">{density.toFixed(1)}</span>
        </div>
        <div className="h-1.5 bg-border rounded-full overflow-hidden">
          <div
            className="h-full rounded-full transition-all duration-500"
            style={{ width: `${densityPct}%`, background: color }}
          />
        </div>
      </div>

      {/* Wait time */}
      <div className="flex justify-between text-xs">
        <span className="text-text-muted">Wait</span>
        <span className="font-mono text-text-secondary">{Math.ceil(waiting_s)}s</span>
      </div>
    </div>
  )
}
