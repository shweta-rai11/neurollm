import { Droplet } from 'lucide-react'
import InfoTooltip from '../common/InfoTooltip'
import type { NeuromodulatorSignals } from '../../types/cognitiveState'

interface EndocrinePanelProps {
  neuromodulation: NeuromodulatorSignals
  taskCategory: string
}

type Level = 'BASELINE' | 'MODERATE' | 'ELEVATED'

function levelFor(value: number): Level {
  if (value >= 65) return 'ELEVATED'
  if (value >= 35) return 'MODERATE'
  return 'BASELINE'
}

const LEVEL_CLASS: Record<Level | 'NOT TASK-PRIMARY', string> = {
  BASELINE: 'text-status-good',
  MODERATE: 'text-status-caution',
  ELEVATED: 'text-status-warning',
  'NOT TASK-PRIMARY': 'text-ink-muted',
}

/**
 * Qualitative, simulated endocrine-style readout (product spec section 10).
 * "Stress/cortisol" is derived from the norepinephrine-like alertness signal
 * already computed by the backend (app/brain/neuromodulation.py); there is
 * no computed "oxytocin-like" backend signal at all -- it reads
 * "NOT TASK-PRIMARY" unless the task was classified as social reasoning,
 * which is the honest thing to show rather than inventing a number.
 */
export default function EndocrinePanel({ neuromodulation, taskCategory }: EndocrinePanelProps) {
  const stressLevel = levelFor(neuromodulation.norepinephrine_like)
  const isSocial = taskCategory === 'social_reasoning'
  const oxytocinLevel: Level | 'NOT TASK-PRIMARY' = isSocial ? levelFor(neuromodulation.acetylcholine_like) : 'NOT TASK-PRIMARY'

  return (
    <div className="glass-panel p-6">
      <div className="mb-4 flex items-center gap-2">
        <Droplet size={16} strokeWidth={1.75} className="text-status-caution" />
        <h2 className="section-label">Simulated Endocrine State</h2>
      </div>

      <div className="mb-5 rounded-lg border border-status-caution/20 bg-status-caution/10 px-3 py-2 text-xs leading-relaxed text-ink-secondary">
        The simulator maintains an endocrine-style state because stress-related systems are hypothesized to influence
        cognitive-state models - these are qualitative, computed labels, not a measurement of this user's hormones.
      </div>

      <div className="flex flex-col gap-4">
        <Row label="Stress / cortisol-like" level={stressLevel} tooltip="Derived from the norepinephrine-like alertness signal (token entropy, task risk)." />
        <Row label="Oxytocin-like" level={oxytocinLevel} tooltip="Only estimated when the task was classified as social reasoning; otherwise not task-primary rather than a fabricated number." />
      </div>
    </div>
  )
}

function Row({ label, level, tooltip }: { label: string; level: Level | 'NOT TASK-PRIMARY'; tooltip: string }) {
  return (
    <div className="flex items-center justify-between gap-3">
      <span className="inline-flex items-center gap-1.5 text-sm text-ink-primary">
        {label}
        <InfoTooltip text={tooltip} />
      </span>
      <span className={`font-mono text-xs font-semibold tracking-wide ${LEVEL_CLASS[level]}`}>{level}</span>
    </div>
  )
}
