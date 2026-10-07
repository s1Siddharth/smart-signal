// components/AlertBanner.tsx — Ambulance / emergency alert banner
interface AlertBannerProps {
  active: boolean
  road: string | null
}

export function AlertBanner({ active, road }: AlertBannerProps) {
  if (!active || !road) return null

  return (
    <div
      className="flex items-center gap-3 px-4 py-3 rounded border animate-pulse-amber"
      style={{
        background: 'rgba(255,176,32,0.1)',
        borderColor: '#FFB020',
      }}
      role="alert"
      aria-live="assertive"
    >
      <div className="w-3 h-3 rounded-full bg-signal-amber shrink-0" />
      <span className="font-sans font-semibold text-signal-amber text-sm">
        EMERGENCY — Ambulance on Road {road}. Priority green active.
      </span>
    </div>
  )
}
