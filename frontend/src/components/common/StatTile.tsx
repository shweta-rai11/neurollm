import type { ReactNode } from 'react'

interface StatTileProps {
  label: string
  value: ReactNode
  hint?: string
}

/** Compact label/value figure per the dataviz "stat tile" contract. */
export default function StatTile({ label, value, hint }: StatTileProps) {
  return (
    <div className="rounded-lg border border-panel-border bg-panel-light/60 px-3 py-2.5">
      <div className="section-label">{label}</div>
      <div className="mt-1 font-mono text-xl font-semibold text-ink-primary">{value}</div>
      {hint ? <div className="mt-0.5 text-[11px] text-ink-muted">{hint}</div> : null}
    </div>
  )
}
