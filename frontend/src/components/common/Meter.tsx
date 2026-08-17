import { motion } from 'framer-motion'
import type { ReactNode } from 'react'
import { clampPct } from '../../utils/format'

interface MeterProps {
  label: ReactNode
  value: number
  /** Tailwind background class for the fill (defaults to the app's cyan accent). */
  fillClassName?: string
  /**
   * Raw hex color for the fill, applied as an inline style. Use this instead
   * of fillClassName when the color comes from a runtime lookup (e.g. a
   * per-hormone map) — Tailwind's JIT scanner can't see dynamically
   * interpolated `bg-[...]` class names, only literal ones written in source.
   */
  fillColor?: string
  /** Text shown at the end of the row; defaults to a rounded percentage. */
  valueLabel?: string
  sublabel?: string
  icon?: ReactNode
  size?: 'sm' | 'md'
}

/**
 * Animated horizontal meter: `meter-track`/`meter-fill` (defined in index.css)
 * give the recessive track + accent fill; framer-motion animates the width
 * transition on mount/update per the dataviz "meter" convention (fill carries
 * magnitude, unfilled track is a lighter step of the same ramp).
 */
export default function Meter({
  label,
  value,
  fillClassName = 'bg-cyan-accent',
  fillColor,
  valueLabel,
  sublabel,
  icon,
  size = 'md',
}: MeterProps) {
  const clamped = clampPct(value)
  return (
    <div>
      <div className="mb-1.5 flex items-center justify-between gap-2">
        <div className="flex items-center gap-1.5 text-sm text-ink-primary">
          {icon}
          <span>{label}</span>
        </div>
        <span className="font-mono text-sm tabular-nums text-ink-secondary">
          {valueLabel ?? `${clamped}%`}
        </span>
      </div>
      <div className={size === 'sm' ? 'meter-track h-1' : 'meter-track'}>
        <motion.div
          className={`meter-fill ${fillColor ? '' : fillClassName}`}
          style={fillColor ? { backgroundColor: fillColor } : undefined}
          initial={{ width: 0 }}
          animate={{ width: `${clamped}%` }}
          transition={{ duration: 0.6, ease: 'easeOut' }}
        />
      </div>
      {sublabel ? <p className="mt-1 text-xs text-ink-muted">{sublabel}</p> : null}
    </div>
  )
}
