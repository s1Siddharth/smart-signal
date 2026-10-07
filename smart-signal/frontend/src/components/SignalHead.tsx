// components/SignalHead.tsx — Big circular traffic signal light
interface SignalHeadProps {
  state: 'GREEN' | 'RED' | 'YELLOW' | 'OFF'
  road: string
  size?: 'sm' | 'md' | 'lg'
}

const STATE_COLORS = {
  GREEN:  { bg: '#2EE59D', glow: '0 0 20px 6px rgba(46,229,157,0.6)',  cls: 'animate-glow-green' },
  RED:    { bg: '#FF4D5E', glow: '0 0 20px 6px rgba(255,77,94,0.6)',    cls: 'animate-glow-red' },
  YELLOW: { bg: '#FFB020', glow: '0 0 20px 6px rgba(255,176,32,0.6)',   cls: 'animate-pulse-amber' },
  OFF:    { bg: '#1E2736', glow: 'none',                                 cls: '' },
}

const SIZES = {
  sm: { outer: 'w-10 h-10', inner: 'w-7 h-7', label: 'text-xs' },
  md: { outer: 'w-16 h-16', inner: 'w-11 h-11', label: 'text-sm' },
  lg: { outer: 'w-24 h-24', inner: 'w-16 h-16', label: 'text-base' },
}

export function SignalHead({ state, road, size = 'md' }: SignalHeadProps) {
  const { bg, glow, cls } = STATE_COLORS[state] ?? STATE_COLORS.OFF
  const sz = SIZES[size]

  return (
    <div className="flex flex-col items-center gap-1">
      {/* Housing */}
      <div
        className={`${sz.outer} rounded-full bg-panel border border-border flex items-center justify-center relative`}
      >
        {/* Light */}
        <div
          className={`${sz.inner} rounded-full transition-all duration-150 ${cls}`}
          style={{ background: bg, boxShadow: glow }}
          role="img"
          aria-label={`Road ${road}: ${state}`}
        />
      </div>
      {/* Text label — never color-only */}
      <span
        className={`font-mono font-medium tracking-wider ${sz.label}`}
        style={{ color: bg }}
      >
        {state}
      </span>
      <span className="text-text-secondary text-xs font-sans">Road {road}</span>
    </div>
  )
}
