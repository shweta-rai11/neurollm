import {
  Search,
  Sparkles,
  ListTree,
  BookOpen,
  ShieldAlert,
  CheckCircle,
  Lightbulb,
  TriangleAlert,
  type LucideIcon,
} from 'lucide-react'
import type { Recommendation } from '../../types/cognitiveState'
import { RECOMMENDATION_STYLES } from '../../utils/colors'

interface RecommendationPanelProps {
  recommendations: Recommendation[]
}

const ICON_MAP: Record<string, LucideIcon> = {
  search: Search,
  sparkles: Sparkles,
  'list-tree': ListTree,
  'book-open': BookOpen,
  'shield-alert': ShieldAlert,
  'check-circle': CheckCircle,
}

function iconFor(name: string): LucideIcon {
  return ICON_MAP[name] ?? Lightbulb
}

/** Renders CognitiveState.recommendations as severity-colored action cards. */
export default function RecommendationPanel({ recommendations }: RecommendationPanelProps) {
  const hasWarning = recommendations.some((r) => r.severity === 'warning')

  return (
    <div className="glass-panel p-6">
      <div className="mb-4 flex items-center justify-between">
        <h2 className="section-label">Recommended Action</h2>
      </div>

      {hasWarning ? (
        <div className="mb-4 flex items-center gap-2 rounded-lg border border-status-warning/30 bg-status-warning/10 px-3 py-2.5 text-sm font-semibold text-status-warning">
          <TriangleAlert size={16} strokeWidth={2} />
          <span>VERIFY BEFORE TRUSTING</span>
        </div>
      ) : null}

      {recommendations.length === 0 ? (
        <p className="text-sm text-ink-muted">
          No specific recommendations - this response appears nominal.
        </p>
      ) : (
        <div className="flex flex-col gap-3">
          {recommendations.map((rec, i) => {
            const Icon = iconFor(rec.icon)
            const style = RECOMMENDATION_STYLES[rec.severity]
            return (
              <div
                key={`${rec.title}-${i}`}
                className={`flex items-start gap-3 rounded-lg border px-3.5 py-3 ${style.border} ${style.bg}`}
              >
                <span className={`mt-0.5 shrink-0 ${style.text}`}>
                  <Icon size={17} strokeWidth={1.75} />
                </span>
                <div>
                  <div className={`text-sm font-semibold ${style.text}`}>{rec.title}</div>
                  <p className="mt-0.5 text-xs leading-relaxed text-ink-secondary">{rec.detail}</p>
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
