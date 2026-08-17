import { Microscope, CircleAlert } from 'lucide-react'
import type { UncertaintyResult } from '../../types/cognitiveState'
import StatTile from '../common/StatTile'
import { clusterColor } from '../../utils/colors'
import { truncate } from '../../utils/format'

interface UncertaintyPanelProps {
  uncertainty: UncertaintyResult | null
}

/**
 * "Evidence from model behavior" — never says "probability"; uses
 * response-consistency / semantic-uncertainty language per the product spec.
 * Gracefully degrades to an empty-state message when uncertainty is null
 * (single-sample mode, or a backend that didn't attach it).
 */
export default function UncertaintyPanel({ uncertainty }: UncertaintyPanelProps) {
  if (!uncertainty) {
    return (
      <div className="glass-panel p-6">
        <div className="mb-2 flex items-center gap-2">
          <Microscope size={16} strokeWidth={1.75} className="text-cyan-accent" />
          <h2 className="section-label">Evidence from Model Behavior</h2>
        </div>
        <p className="text-sm text-ink-muted">Uncertainty estimation unavailable.</p>
      </div>
    )
  }

  const groups = new Map<number, typeof uncertainty.candidates>()
  for (const candidate of uncertainty.candidates) {
    const list = groups.get(candidate.cluster_id) ?? []
    list.push(candidate)
    groups.set(candidate.cluster_id, list)
  }
  const sortedClusters = Array.from(groups.entries()).sort((a, b) => a[0] - b[0])

  const isFallback = uncertainty.method === 'lexical_fallback'

  return (
    <div className="glass-panel p-6">
      <div className="mb-4 flex items-center gap-2">
        <Microscope size={16} strokeWidth={1.75} className="text-cyan-accent" />
        <h2 className="section-label">Evidence from Model Behavior</h2>
      </div>

      <div className="mb-5 grid grid-cols-2 gap-3 sm:grid-cols-4">
        <StatTile label="Candidates sampled" value={uncertainty.candidate_count} />
        <StatTile label="Semantic clusters" value={uncertainty.unique_semantic_clusters} />
        <StatTile label="Response agreement" value={`${uncertainty.response_agreement}%`} />
        <StatTile
          label="Semantic uncertainty estimate"
          value={`${uncertainty.semantic_uncertainty_score}%`}
        />
      </div>

      <div className="mb-5 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-ink-muted">
        <span>
          Mean embedding similarity:{' '}
          <span className="font-mono text-ink-secondary">
            {uncertainty.mean_embedding_similarity.toFixed(3)}
          </span>
        </span>
        <span>
          Max embedding distance:{' '}
          <span className="font-mono text-ink-secondary">
            {uncertainty.max_embedding_distance.toFixed(3)}
          </span>
        </span>
        <span className="inline-flex items-center gap-1">
          Similarity method:{' '}
          <span className={`font-mono ${isFallback ? 'text-status-caution' : 'text-ink-secondary'}`}>
            {isFallback ? 'lexical fallback' : uncertainty.method}
          </span>
          {isFallback ? <CircleAlert size={12} strokeWidth={2} className="text-status-caution" /> : null}
        </span>
      </div>

      <div className="section-label mb-2">Candidates by semantic cluster</div>
      <div className="flex flex-col gap-3">
        {sortedClusters.map(([clusterId, candidates]) => (
          <div key={clusterId}>
            <div className="mb-1.5 flex items-center gap-1.5 text-xs text-ink-muted">
              <span
                className="h-2 w-2 rounded-full"
                style={{ backgroundColor: clusterColor(clusterId) }}
              />
              <span>
                Cluster {clusterId} · {candidates.length}{' '}
                {candidates.length === 1 ? 'response' : 'responses'}
              </span>
            </div>
            <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
              {candidates.map((c, i) => (
                <div
                  key={i}
                  className="rounded-lg border px-3 py-2 text-xs leading-relaxed text-ink-secondary"
                  style={{
                    borderColor: `${clusterColor(clusterId)}40`,
                    backgroundColor: `${clusterColor(clusterId)}0d`,
                  }}
                >
                  {truncate(c.text, 140)}
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
