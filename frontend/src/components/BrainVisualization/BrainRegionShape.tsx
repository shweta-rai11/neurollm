import { motion } from 'framer-motion'
import type { RegionMeta } from './regionMeta'

interface Props {
  meta: RegionMeta
  activation: number
  isHovered: boolean
  onHoverStart: () => void
  onHoverEnd: () => void
}

/**
 * A single illuminated brain region. Fill opacity and glow intensity scale
 * with the 0-100 activation value; regions above ~70 get a slow, subtle
 * pulse. All transitions are interpolated by framer-motion so activation
 * changes animate smoothly rather than snapping.
 */
export default function BrainRegionShape({ meta, activation, isHovered, onHoverStart, onHoverEnd }: Props) {
  const clamped = Math.max(0, Math.min(100, activation))
  const t = clamped / 100
  const fillOpacity = 0.1 + t * 0.5
  const glowOpacity = 0.06 + t * 0.32
  const strokeOpacity = 0.25 + t * 0.5
  const isHighActivation = clamped > 70

  return (
    <g
      onMouseEnter={onHoverStart}
      onMouseLeave={onHoverEnd}
      onFocus={onHoverStart}
      onBlur={onHoverEnd}
      tabIndex={0}
      role="img"
      aria-label={`${meta.label}: activation ${Math.round(clamped)} percent`}
      style={{ cursor: 'pointer', outline: 'none' }}
    >
      {/* soft glow layer */}
      <motion.ellipse
        cx={meta.cx}
        cy={meta.cy}
        rx={meta.rx}
        ry={meta.ry}
        fill={meta.color}
        filter="url(#brain-region-glow)"
        style={{ transformOrigin: `${meta.cx}px ${meta.cy}px` }}
        initial={false}
        animate={{
          opacity: isHovered ? glowOpacity + 0.12 : glowOpacity,
          scale: isHighActivation ? [1, 1.035, 1] : 1,
        }}
        transition={{
          opacity: { duration: 0.5, ease: 'easeOut' },
          scale: isHighActivation
            ? { duration: 2.6, repeat: Infinity, ease: 'easeInOut' }
            : { duration: 0.5 },
        }}
      />

      {/* region body */}
      <motion.ellipse
        cx={meta.cx}
        cy={meta.cy}
        rx={meta.rx}
        ry={meta.ry}
        fill={meta.color}
        stroke={meta.color}
        initial={false}
        animate={{
          fillOpacity: isHovered ? fillOpacity + 0.15 : fillOpacity,
          strokeOpacity: isHovered ? 0.95 : strokeOpacity,
          strokeWidth: isHovered ? 1.5 : 1,
        }}
        transition={{ duration: 0.45, ease: 'easeOut' }}
      />

      {isHovered && (
        <ellipse
          cx={meta.cx}
          cy={meta.cy}
          rx={meta.rx + 4}
          ry={meta.ry + 4}
          fill="none"
          stroke={meta.color}
          strokeWidth={1}
          strokeOpacity={0.45}
          strokeDasharray="2 4"
        />
      )}
    </g>
  )
}
