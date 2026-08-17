import { FlaskConical } from 'lucide-react'
import type { NeuromodulatorSignals } from '../../types/cognitiveState'
import Meter from '../common/Meter'
import InfoTooltip from '../common/InfoTooltip'
import { NEUROMOD_COLORS } from '../../utils/colors'

interface NeuromodulationPanelProps {
  signals: NeuromodulatorSignals
}

/**
 * Every value here is a "-like" computational variable derived from real
 * signals (response consistency, token/attention entropy, task heuristics)
 * — NEVER a biological hormone measurement. These also feed back into
 * routing thresholds in the executive controller (see backend
 * app/brain/neuromodulation.py + executive_controller.py) rather than being
 * purely decorative.
 */
const NEUROMOD_META: { key: keyof NeuromodulatorSignals; name: string; meaning: string }[] = [
  { key: 'dopamine_like', name: 'Dopamine-like', meaning: 'reward / confidence proxy (token probability margin, cross-sample agreement)' },
  { key: 'serotonin_like', name: 'Serotonin-like', meaning: 'stability (cross-sample agreement, low ambiguity)' },
  { key: 'norepinephrine_like', name: 'Norepinephrine-like', meaning: 'alertness / unexpectedness (token entropy, task risk) — raises verification sensitivity' },
  { key: 'acetylcholine_like', name: 'Acetylcholine-like', meaning: 'attention / engagement (context dependency, verification requirement)' },
]

function tooltipText(meaning: string): string {
  return `Computational variable inspired by neuromodulation, representing ${meaning}. Not a biological hormone measurement.`
}

export default function NeuromodulationPanel({ signals }: NeuromodulationPanelProps) {
  return (
    <div className="glass-panel p-6">
      <div className="mb-4 flex items-center gap-2">
        <FlaskConical size={16} strokeWidth={1.75} className="text-violet-accent" />
        <h2 className="section-label">Virtual Neuromodulation Layer</h2>
      </div>

      <div className="mb-5 rounded-lg border border-violet-accent/20 bg-violet-faint px-3 py-2 text-xs leading-relaxed text-ink-secondary">
        Computational variables inspired by neuromodulation — not biological hormone data. These
        also adjust routing thresholds in the executive controller (see About).
      </div>

      <div className="grid grid-cols-1 gap-5 sm:grid-cols-2">
        {NEUROMOD_META.map(({ key, name, meaning }) => (
          <Meter
            key={key}
            label={
              <span className="inline-flex items-center gap-1.5">
                <span>{name}</span>
                <InfoTooltip text={tooltipText(meaning)} />
              </span>
            }
            value={signals[key]}
            fillColor={NEUROMOD_COLORS[key]}
          />
        ))}
      </div>
    </div>
  )
}
