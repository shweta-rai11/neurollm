/**
 * Shared color mapping for the feature panels.
 *
 * Follows the dataviz skill's rules applied to this app's design tokens
 * (tailwind.config.js): categorical hues are assigned per fixed entity (never
 * per rank), status colors (status-good/caution/warning, plus the cyan/violet
 * brand accents used as the neutral "info" band) are reserved for state and
 * always paired with a text label — never color alone. Hex values below
 * mirror the BrainVisualization component's region palette so region color
 * coding reads consistently everywhere in the app.
 */
import type { RegionScores, NeuromodulatorSignals, Recommendation, Pathway } from '../types/cognitiveState'
import type { ProfileParamName } from '../types/profile'

/** Fixed per-region hue, consistent with BrainVisualization's regionMeta. */
export const REGION_COLORS: Record<keyof RegionScores, string> = {
  language: '#38bdf8',
  memory: '#2dd4bf',
  reasoning: '#22d3ee',
  uncertainty: '#f5a524',
  verification: '#818cf8',
}

/** Fixed per-signal hue for the Virtual Neuromodulation Layer. */
export const NEUROMOD_COLORS: Record<keyof NeuromodulatorSignals, string> = {
  dopamine_like: '#a78bfa', // reward/confidence proxy
  serotonin_like: '#2dd4bf', // stability
  norepinephrine_like: '#f5a524', // alertness/unexpectedness — reserved caution color
  acetylcholine_like: '#818cf8', // attention/engagement — echoes Verification region
}

export const PATHWAY_COLORS: Record<Pathway, string> = {
  DIRECT: '#2dd4bf',
  ANALYTICAL: '#22d3ee',
  CREATIVE: '#a78bfa',
  VERIFY: '#f5a524',
}

/** Cycling categorical palette for open-ended groupings (e.g. candidate clusters). */
export const CLUSTER_COLORS = ['#22d3ee', '#a78bfa', '#2dd4bf', '#f5a524', '#818cf8', '#fb7185']

export function clusterColor(clusterId: number): string {
  return CLUSTER_COLORS[Math.abs(clusterId) % CLUSTER_COLORS.length]
}

export type SeverityLevel = 'good' | 'info' | 'caution' | 'warning'

/** Higher value = better/safer (e.g. confidence). */
export function directSeverity(value: number): SeverityLevel {
  if (value >= 70) return 'good'
  if (value >= 40) return 'info'
  return 'caution'
}

/** Higher value = more concerning (e.g. uncertainty, verification need). */
export function inverseSeverity(value: number): SeverityLevel {
  if (value >= 70) return 'warning'
  if (value >= 40) return 'caution'
  return 'good'
}

export const SEVERITY_BAR_CLASS: Record<SeverityLevel, string> = {
  good: 'bg-status-good',
  info: 'bg-cyan-accent',
  caution: 'bg-status-caution',
  warning: 'bg-status-warning',
}

export const SEVERITY_TEXT_CLASS: Record<SeverityLevel, string> = {
  good: 'text-status-good',
  info: 'text-cyan-accent',
  caution: 'text-status-caution',
  warning: 'text-status-warning',
}

/** Fixed per-parameter hue for the Individual Computational Profile's 9
 * dimensions -- reused across Overview's activated-systems panel and the
 * Evolution/Counterfactual charts so a given parameter reads consistently. */
export const PROFILE_PARAM_COLORS: Record<ProfileParamName, string> = {
  attention_baseline: '#38bdf8',
  working_memory_baseline: '#2dd4bf',
  cognitive_control: '#22d3ee',
  exploration: '#a78bfa',
  exploitation: '#818cf8',
  memory_retrieval: '#fb7185',
  uncertainty_sensitivity: '#f5a524',
  salience_sensitivity: '#f472b6',
  verification_strength: '#4ade80',
}

/** Card treatment for Recommendation.severity ('info' | 'caution' | 'warning'). */
export const RECOMMENDATION_STYLES: Record<
  Recommendation['severity'],
  { border: string; bg: string; text: string }
> = {
  info: { border: 'border-cyan-accent/25', bg: 'bg-cyan-faint', text: 'text-cyan-accent' },
  caution: {
    border: 'border-status-caution/30',
    bg: 'bg-status-caution/10',
    text: 'text-status-caution',
  },
  warning: {
    border: 'border-status-warning/30',
    bg: 'bg-status-warning/10',
    text: 'text-status-warning',
  },
}
