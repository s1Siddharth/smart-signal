// components/DecisionLog.tsx — Terminal-style decision log
interface LogEntry {
  t: string
  text: string
}

interface DecisionLogProps {
  entries: LogEntry[]
}

export function DecisionLog({ entries }: DecisionLogProps) {
  return (
    <div className="bg-panel border border-border rounded p-3 font-mono text-xs text-text-secondary overflow-y-auto max-h-48">
      <div className="text-accent text-xs mb-2 font-sans font-semibold tracking-wider uppercase">
        Decision Log
      </div>
      {entries.length === 0 ? (
        <span className="text-text-muted">No transitions yet.</span>
      ) : (
        [...entries].reverse().map((e, i) => (
          <div key={i} className="flex gap-2 py-0.5 border-b border-border last:border-0 animate-fade-in">
            <span className="text-text-muted shrink-0">{e.t}</span>
            <span className="text-text-secondary">&gt;</span>
            <span>{e.text}</span>
          </div>
        ))
      )}
    </div>
  )
}
