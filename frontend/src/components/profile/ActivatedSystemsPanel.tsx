import { Network } from 'lucide-react'
import Meter from '../common/Meter'
import InfoTooltip from '../common/InfoTooltip'
import { REGION_COLORS } from '../../utils/colors'
import type { RegionScores } from '../../types/cognitiveState'

interface ActivatedSystemsPanelProps {
  regions: RegionScores
  taskCategory: string
  candidateSystems: string[]
}

const REGION_LABELS: Record<keyof RegionScores, string> = {
  language: 'Language processing',
  memory: 'Memory retrieval',
  reasoning: 'Reasoning / working memory',
  uncertainty: 'Uncertainty monitoring',
  verification: 'Verification',
}

/**
 * The five region meters below are the app's actual computed signals
 * (app/brain/regions.py). `candidateSystems` are the task-classifier's
 * named illustrative virtual systems (spec section 8/14) -- shown as labels,
 * not given fabricated individual percentages, since no per-named-system
 * magnitude is actually computed anywhere in the backend.
 */
export default function ActivatedSystemsPanel({ regions, taskCategory, candidateSystems }: ActivatedSystemsPanelProps) {
  return (
    <div className="glass-panel p-6">
      <div className="mb-1 flex items-center gap-2">
        <Network size={16} strokeWidth={1.75} className="text-cyan-accent" />
        <h2 className="section-label">Activated Virtual Systems</h2>
      </div>
      <p className="mb-4 text-xs text-ink-muted">
        Task classified as <span className="text-ink-secondary">{taskCategory.replace(/_/g, ' ')}</span>
      </p>

      <div className="mb-5 flex flex-col gap-4">
        {(Object.keys(REGION_LABELS) as (keyof RegionScores)[]).map((key) => (
          <Meter key={key} label={REGION_LABELS[key]} value={regions[key]} fillColor={REGION_COLORS[key]} />
        ))}
      </div>

      <div>
        <div className="mb-2 flex items-center gap-1.5 section-label">
          Candidate systems for this task
          <InfoTooltip text="A fixed, designed mapping from task category to illustrative virtual-system names (spec section 8) - categorical, not individually quantified. Named after real neuroanatomy as a metaphor, not a claim that this software activates those regions." />
        </div>
        <div className="flex flex-wrap gap-1.5">
          {candidateSystems.map((system) => (
            <span
              key={system}
              className="rounded-full border border-panel-border bg-panel-light px-2.5 py-1 text-[11px] text-ink-secondary"
            >
              {system}
            </span>
          ))}
        </div>
      </div>
    </div>
  )
}
