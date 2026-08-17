import { Activity, Gauge, Sparkles, ShieldCheck, BookOpen, Layers } from 'lucide-react'
import type { CognitiveState as CognitiveStateT, TaskAnalysis } from '../../types/cognitiveState'
import Meter from '../common/Meter'
import { directSeverity, inverseSeverity, SEVERITY_BAR_CLASS } from '../../utils/colors'

interface CognitiveStateProps {
  state: CognitiveStateT
  /** Optional: unlocks two extra meters (Creativity, Context Dependence). */
  taskAnalysis?: TaskAnalysis
}

/**
 * Renders the four GlobalState meters as animated horizontal progress bars
 * (per the dashboard mockup: "Confidence 81%" style labeled meters), plus the
 * StateInterpretation block (mode pills, status heading, plain-language
 * interpretation sentence).
 */
export default function CognitiveState({ state, taskAnalysis }: CognitiveStateProps) {
  const { global_state: gs, interpretation } = state

  return (
    <div className="glass-panel p-6">
      <div className="mb-5 flex items-center justify-between">
        <h2 className="section-label">Cognitive State</h2>
      </div>

      <div className="grid grid-cols-1 gap-5 sm:grid-cols-2">
        <Meter
          label="Confidence"
          value={gs.confidence}
          icon={<ShieldCheck size={14} strokeWidth={1.75} className="text-ink-muted" />}
          fillClassName={SEVERITY_BAR_CLASS[directSeverity(gs.confidence)]}
        />
        <Meter
          label="Uncertainty"
          value={gs.uncertainty}
          icon={<Gauge size={14} strokeWidth={1.75} className="text-ink-muted" />}
          fillClassName={SEVERITY_BAR_CLASS[inverseSeverity(gs.uncertainty)]}
        />
        <Meter
          label="Complexity"
          value={gs.difficulty}
          icon={<Layers size={14} strokeWidth={1.75} className="text-ink-muted" />}
          fillClassName="bg-violet-accent"
        />
        <Meter
          label="Verification Need"
          value={gs.verification_need}
          icon={<Activity size={14} strokeWidth={1.75} className="text-ink-muted" />}
          fillClassName={SEVERITY_BAR_CLASS[inverseSeverity(gs.verification_need)]}
        />
        {taskAnalysis ? (
          <>
            <Meter
              label="Creativity"
              value={taskAnalysis.creativity}
              icon={<Sparkles size={14} strokeWidth={1.75} className="text-ink-muted" />}
              fillClassName="bg-violet-accent"
            />
            <Meter
              label="Context Dependence"
              value={taskAnalysis.context_dependency}
              icon={<BookOpen size={14} strokeWidth={1.75} className="text-ink-muted" />}
              fillClassName="bg-[#2dd4bf]"
            />
          </>
        ) : null}
      </div>

      <div className="my-6 h-px bg-panel-border" />

      <div>
        <div className="mb-2 flex flex-wrap gap-1.5">
          {interpretation.modes.map((mode) => (
            <span
              key={mode}
              className="badge border-cyan-accent/25 bg-cyan-faint text-cyan-accent"
            >
              {mode}
            </span>
          ))}
        </div>
        <h3 className="text-lg font-semibold tracking-tight text-ink-primary">
          {interpretation.status}
        </h3>
        <p className="mt-1.5 text-sm leading-relaxed text-ink-secondary">
          {interpretation.interpretation}
        </p>

        {Object.keys(interpretation.contributing_signals).length > 0 ? (
          <div className="mt-3 flex flex-wrap gap-1.5">
            {Object.entries(interpretation.contributing_signals).map(([key, val]) => (
              <span
                key={key}
                className="badge border-panel-border bg-panel-light text-ink-secondary"
              >
                <span className="text-ink-muted">{key.replace(/_/g, ' ')}:</span> {val}
              </span>
            ))}
          </div>
        ) : null}
      </div>
    </div>
  )
}
