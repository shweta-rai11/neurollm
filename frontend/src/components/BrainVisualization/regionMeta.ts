import type { RegionScores } from '../../types/cognitiveState'

export interface RegionMeta {
  key: keyof RegionScores
  label: string
  subtitle?: string
  /** One-line, plain-language gloss shown in the always-visible legend
   * (not just on hover) so the diagram is legible without discovery. */
  meaning: string
  /** Plain-language contributing factors, shown in the hover tooltip. */
  factors: string[]
  /** Blob center/radii in the 0-560 x 0-380 viewBox, positioned inside the
   * anatomical silhouette in index.tsx (clipped to it so glows never spill
   * outside the brain outline). */
  cx: number
  cy: number
  rx: number
  ry: number
  /** Hex color used for fill/glow -- mirrors utils/colors.ts REGION_COLORS. */
  color: string
  /** Static caption anchor point and text-anchor, hand-placed to sit in the
   * margin around the silhouette without overlapping it or other labels. */
  labelX: number
  labelY: number
  labelAnchor: 'start' | 'middle' | 'end'
}

export const REGION_META: RegionMeta[] = [
  {
    key: 'language',
    label: 'Language',
    subtitle: '(computational analogy)',
    meaning: 'Linguistic / lexical processing demand',
    factors: ['Text length & lexical diversity', 'Early/mid-layer activation magnitude'],
    cx: 150,
    cy: 95,
    rx: 55,
    ry: 42,
    color: '#38bdf8',
    labelX: 50,
    labelY: 32,
    labelAnchor: 'start',
  },
  {
    key: 'reasoning',
    label: 'Reasoning',
    subtitle: '(computational analogy)',
    meaning: 'Multi-step / logical reasoning demand',
    factors: ['Logical-reasoning & planning score', 'Late-layer activation growth'],
    cx: 262,
    cy: 85,
    rx: 66,
    ry: 40,
    color: '#22d3ee',
    labelX: 262,
    labelY: 22,
    labelAnchor: 'middle',
  },
  {
    key: 'verification',
    label: 'Verification',
    subtitle: '(computational analogy)',
    meaning: 'Factuality & verification requirement',
    factors: ['Factuality / verification requirement', 'Hallucination-risk signal'],
    cx: 305,
    cy: 160,
    rx: 55,
    ry: 35,
    color: '#818cf8',
    labelX: 408,
    labelY: 140,
    labelAnchor: 'start',
  },
  {
    key: 'memory',
    label: 'Memory',
    subtitle: '(computational analogy)',
    meaning: 'Dependence on stored / contextual knowledge',
    factors: ['Context dependency', 'Factual-recall requirement'],
    cx: 150,
    cy: 235,
    rx: 30,
    ry: 20,
    color: '#2dd4bf',
    labelX: 14,
    labelY: 240,
    labelAnchor: 'start',
  },
  {
    key: 'uncertainty',
    label: 'Uncertainty',
    subtitle: '(computational analogy)',
    meaning: 'Ambiguity & model uncertainty',
    factors: ['Ambiguity / risk score', 'Token-entropy & response disagreement'],
    cx: 297,
    cy: 246,
    rx: 36,
    ry: 26,
    color: '#f5a524',
    labelX: 408,
    labelY: 260,
    labelAnchor: 'start',
  },
]
