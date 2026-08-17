import { useState } from 'react'
import { ShieldAlert } from 'lucide-react'
import type { Pathway, RegionScores } from '../../types/cognitiveState'
import { REGION_META } from './regionMeta'
import BrainRegionShape from './BrainRegionShape'
import RegionTooltip from './RegionTooltip'
import { PATHWAY_COLORS } from '../../utils/colors'

const VIEW_W = 560
const VIEW_H = 380

// A lateral (side-profile) brain silhouette, hand-drawn as three anatomical
// pieces (cerebrum, temporal lobe, cerebellum) plus a brainstem stub -- the
// classic "brain diagram" side view, not a photographic or anatomically
// precise reference. This is still an illustrative shape (see the disclaimer
// below the diagram and the About page), but it is drawn to actually read as
// a brain at a glance, with the lobe boundary (sylvian-fissure-style notch)
// and cerebellum/brainstem included for visual legibility.
const CEREBRUM =
  'M95,110 C70,85 100,55 150,50 C210,42 260,40 300,55 C345,68 375,100 385,150 ' +
  'C393,190 385,225 360,250 C330,268 295,262 270,245 C240,225 190,215 150,210 ' +
  'C120,207 100,195 85,175 C72,158 70,135 95,110 Z'

const TEMPORAL_LOBE =
  'M110,195 C95,210 85,235 95,255 C102,272 120,282 145,278 C168,274 180,258 178,240 ' +
  'C176,222 165,208 150,200 C138,196 122,193 110,195 Z'

const CEREBELLUM =
  'M260,235 C250,255 255,278 280,285 C300,292 320,285 330,268 C340,250 335,230 315,222 ' +
  'C298,216 275,220 260,235 Z'

const BRAINSTEM =
  'M235,255 C232,270 230,290 238,308 C244,312 252,310 252,300 C254,285 250,268 248,255 Z'

// Decorative gyri/sulci texture -- short wavy strokes across the cerebrum
// surface. Purely cosmetic (no data), included because a smooth blob does
// not read as "brain" the way a few folds do.
const GYRI_LINES = [
  'M132,78 C152,88 172,82 192,90',
  'M204,66 C226,76 249,70 269,80',
  'M114,116 C134,126 154,120 172,128',
  'M226,104 C248,114 268,108 288,116',
  'M162,146 C182,154 202,148 218,154',
  'M270,180 C288,190 306,186 322,192',
]

interface BrainVisualizationProps {
  regions: RegionScores
  /** Which profile `regions` represents -- shown as a small badge so it's
   * never ambiguous whether the diagram is showing a pre-generation
   * prediction or a post-generation, activation-derived measurement. */
  mode?: 'predicted' | 'measured'
  pathway?: Pathway
  hallucinationRisk?: number
}

export default function BrainVisualization({ regions, mode, pathway, hallucinationRisk }: BrainVisualizationProps) {
  const [hoveredKey, setHoveredKey] = useState<keyof RegionScores | null>(null)
  const hovered = REGION_META.find((r) => r.key === hoveredKey) ?? null

  return (
    <div className="glass-panel flex flex-col p-5">
      <div className="mb-1 flex items-center justify-between">
        <h2 className="section-label">Virtual Brain - Region Activation</h2>
        {mode ? (
          <span className="badge border-panel-border bg-panel-light text-ink-muted">
            {mode === 'measured' ? 'Measured (activations)' : 'Predicted (pre-generation)'}
          </span>
        ) : null}
      </div>
      <p className="mb-2 text-[11px] leading-snug text-ink-muted">
        Each region glows in proportion to a computational signal - a functional analogy, not a
        reading of anatomical brain structure. Hover a region for details.
      </p>

      <div className="relative mx-auto w-full max-w-md">
        <svg viewBox={`0 0 ${VIEW_W} ${VIEW_H}`} className="w-full" role="img" aria-label="Virtual brain activation map">
          <defs>
            <filter id="brain-region-glow" x="-60%" y="-60%" width="220%" height="220%">
              <feGaussianBlur stdDeviation="10" result="blur" />
              <feMerge>
                <feMergeNode in="blur" />
              </feMerge>
            </filter>
            <clipPath id="brain-silhouette-clip">
              <path d={CEREBRUM} />
              <path d={TEMPORAL_LOBE} />
              <path d={CEREBELLUM} />
            </clipPath>
          </defs>

          {/* Anatomical outline pieces */}
          <path d={CEREBRUM} fill="rgba(148,163,184,0.04)" stroke="rgba(148,163,184,0.4)" strokeWidth={1.4} strokeLinejoin="round" />
          <path d={TEMPORAL_LOBE} fill="rgba(148,163,184,0.04)" stroke="rgba(148,163,184,0.4)" strokeWidth={1.2} strokeLinejoin="round" />
          <path d={CEREBELLUM} fill="rgba(148,163,184,0.04)" stroke="rgba(148,163,184,0.4)" strokeWidth={1.2} strokeLinejoin="round" />
          <path d={BRAINSTEM} fill="rgba(148,163,184,0.05)" stroke="rgba(148,163,184,0.35)" strokeWidth={1} strokeLinejoin="round" />

          {/* Gyri/sulci texture (decorative only) */}
          <g opacity={0.35}>
            {GYRI_LINES.map((d) => (
              <path key={d} d={d} fill="none" stroke="rgba(148,163,184,0.55)" strokeWidth={0.9} strokeLinecap="round" />
            ))}
          </g>

          {/* Region glows, clipped to the silhouette so nothing spills outside the outline */}
          <g clipPath="url(#brain-silhouette-clip)">
            {REGION_META.map((meta) => (
              <BrainRegionShape
                key={meta.key}
                meta={meta}
                activation={regions[meta.key] ?? 0}
                isHovered={hoveredKey === meta.key}
                onHoverStart={() => setHoveredKey(meta.key)}
                onHoverEnd={() => setHoveredKey((prev) => (prev === meta.key ? null : prev))}
              />
            ))}
          </g>
          {/* Invisible hit-targets matching each region (outside the clip so hover/focus always works even when activation is 0) */}
          {REGION_META.map((meta) => (
            <ellipse
              key={`${meta.key}-hit`}
              cx={meta.cx}
              cy={meta.cy}
              rx={meta.rx}
              ry={meta.ry}
              fill="transparent"
              onMouseEnter={() => setHoveredKey(meta.key)}
              onMouseLeave={() => setHoveredKey((prev) => (prev === meta.key ? null : prev))}
              style={{ cursor: 'pointer' }}
            />
          ))}

          {/* Leader lines from region center to label */}
          {REGION_META.map((meta) => (
            <line
              key={`${meta.key}-leader`}
              x1={meta.cx}
              y1={meta.cy}
              x2={meta.labelX + (meta.labelAnchor === 'end' ? 4 : meta.labelAnchor === 'start' ? -4 : 0)}
              y2={meta.labelY - 4}
              stroke={meta.color}
              strokeWidth={0.75}
              strokeOpacity={0.35}
              strokeDasharray="1 3"
              pointerEvents="none"
            />
          ))}

          {/* Static captions */}
          {REGION_META.map((meta) => (
            <text
              key={`${meta.key}-label`}
              x={meta.labelX}
              y={meta.labelY}
              textAnchor={meta.labelAnchor}
              className="pointer-events-none select-none"
              fontSize={11}
              fontFamily="Inter, system-ui, sans-serif"
              fill="rgba(226,232,240,0.85)"
              letterSpacing={0.2}
            >
              {meta.label}
              {meta.subtitle && (
                <tspan x={meta.labelX} dy={13} fontSize={9} fill="rgba(148,163,184,0.7)">
                  {meta.subtitle}
                </tspan>
              )}
            </text>
          ))}
        </svg>

        {hovered && (
          <RegionTooltip
            meta={hovered}
            activation={regions[hovered.key] ?? 0}
            leftPct={(hovered.cx / VIEW_W) * 100}
            topPct={((hovered.cy - hovered.ry) / VIEW_H) * 100}
          />
        )}
      </div>

      {(pathway || hallucinationRisk !== undefined) && (
        <div className="mt-4 flex flex-wrap items-center gap-3 border-t border-panel-border pt-3">
          {pathway ? (
            <span
              className="badge"
              style={{ borderColor: `${PATHWAY_COLORS[pathway]}40`, backgroundColor: `${PATHWAY_COLORS[pathway]}14`, color: PATHWAY_COLORS[pathway] }}
            >
              Pathway: {pathway}
            </span>
          ) : null}
          {hallucinationRisk !== undefined ? (
            <span className="inline-flex items-center gap-1.5 text-xs text-ink-secondary">
              <ShieldAlert size={13} strokeWidth={1.75} className={hallucinationRisk >= 0.55 ? 'text-status-warning' : 'text-ink-muted'} />
              Hallucination risk:{' '}
              <span className={`font-mono font-semibold ${hallucinationRisk >= 0.55 ? 'text-status-warning' : 'text-ink-primary'}`}>
                {hallucinationRisk.toFixed(2)}
              </span>
            </span>
          ) : null}
        </div>
      )}

      {/* Always-visible legend, not just hover-discoverable */}
      <div className="mt-4 grid grid-cols-1 gap-x-4 gap-y-1.5 border-t border-panel-border pt-3 sm:grid-cols-2">
        {REGION_META.map((meta) => (
          <div key={meta.key} className="flex items-start gap-2">
            <span className="mt-1 h-1.5 w-1.5 shrink-0 rounded-full" style={{ backgroundColor: meta.color }} />
            <span className="text-[11px] leading-snug text-ink-muted">
              <span className="text-ink-secondary">{meta.label}:</span> {meta.meaning}
            </span>
          </div>
        ))}
      </div>

      <p className="mt-3 text-center text-[11px] leading-snug text-ink-muted">
        Computational analogy - not a claim of biological brain structure or activity.
      </p>
    </div>
  )
}
