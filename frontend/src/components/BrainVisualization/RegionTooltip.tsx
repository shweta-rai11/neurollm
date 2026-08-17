import type { RegionMeta } from './regionMeta'

interface Props {
  meta: RegionMeta
  activation: number
  /** Position as a percentage of the container, 0-100. */
  leftPct: number
  topPct: number
}

export default function RegionTooltip({ meta, activation, leftPct, topPct }: Props) {
  return (
    <div
      className="pointer-events-none absolute z-20 w-56 -translate-x-1/2 -translate-y-[calc(100%+14px)] rounded-lg border border-panel-border bg-[#0b0f16]/95 p-3 shadow-glass backdrop-blur-sm"
      style={{ left: `${leftPct}%`, top: `${topPct}%` }}
    >
      <div className="flex items-center gap-2">
        <span className="h-2 w-2 rounded-full" style={{ backgroundColor: meta.color }} />
        <span className="text-sm font-medium text-ink-primary">{meta.label}</span>
      </div>
      {meta.subtitle && <div className="mt-0.5 text-[11px] text-ink-muted">{meta.subtitle}</div>}
      <div className="mt-2 font-mono text-xs text-ink-secondary">
        Activation: <span className="text-ink-primary">{Math.round(activation)}%</span>
      </div>
      <div className="mt-2 text-[11px] leading-snug text-ink-muted">
        <span className="text-ink-secondary">Driven by:</span> {meta.factors.join(', ')}
      </div>
    </div>
  )
}
