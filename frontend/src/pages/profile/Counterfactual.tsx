import { useState } from 'react'
import { SlidersHorizontal, Loader2, Play } from 'lucide-react'
import { runCounterfactual } from '../../services/api'
import { useProfileId } from '../../hooks/useProfileId'
import { PROFILE_PARAM_NAMES } from '../../types/profile'
import type { CounterfactualOverrides, CounterfactualResponse } from '../../types/profile'
import { PROFILE_PARAM_COLORS } from '../../utils/colors'
import StatTile from '../../components/common/StatTile'

function paramLabel(name: string): string {
  return name.replace(/_/g, ' ')
}

const DEFAULT_OVERRIDES: CounterfactualOverrides = Object.fromEntries(
  PROFILE_PARAM_NAMES.map((name) => [name, 0.5]),
) as CounterfactualOverrides

export default function Counterfactual() {
  const { profileId } = useProfileId()
  const [query, setQuery] = useState('')
  const [overrides, setOverrides] = useState<CounterfactualOverrides>(DEFAULT_OVERRIDES)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<CounterfactualResponse | null>(null)

  async function run() {
    if (!query.trim() || loading) return
    setLoading(true)
    setError(null)
    try {
      const res = await runCounterfactual({ query: query.trim(), model: 'mock', profile_id: profileId, overrides })
      setResult(res)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Counterfactual run failed.')
      setResult(null)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="glass-panel p-6">
        <div className="mb-1 flex items-center gap-2">
          <SlidersHorizontal size={18} strokeWidth={1.75} className="text-cyan-accent" />
          <h1 className="text-lg font-semibold text-ink-primary">What if?</h1>
        </div>
        <p className="mb-5 text-sm text-ink-secondary">
          Override your profile's parameters and compare the resulting virtual-brain state against your current
          profile (or a neutral baseline if no profile is loaded). This is a computational experiment, not a
          prediction about your real cognition.
        </p>

        <label className="section-label mb-1.5 block">Question</label>
        <textarea
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          rows={2}
          placeholder="Ask a question to compare under different simulated parameters…"
          className="mb-5 w-full resize-none rounded-lg border border-panel-border bg-panel-light/60 px-3 py-2 text-sm text-ink-primary placeholder:text-ink-muted focus:border-cyan-accent/50 focus:outline-none"
        />

        <div className="grid grid-cols-1 gap-x-8 gap-y-4 sm:grid-cols-2">
          {PROFILE_PARAM_NAMES.map((name) => (
            <div key={name}>
              <div className="mb-1 flex items-center justify-between text-xs">
                <span className="text-ink-secondary">{paramLabel(name)}</span>
                <span className="font-mono tabular-nums text-ink-muted">{overrides[name]?.toFixed(2)}</span>
              </div>
              <input
                type="range"
                min={0}
                max={1}
                step={0.05}
                value={overrides[name] ?? 0.5}
                onChange={(e) => setOverrides((o) => ({ ...o, [name]: Number(e.target.value) }))}
                className="h-1.5 w-full accent-cyan-accent"
                style={{ accentColor: PROFILE_PARAM_COLORS[name] }}
              />
            </div>
          ))}
        </div>

        <button
          type="button"
          onClick={run}
          disabled={loading || !query.trim()}
          className="mt-6 flex items-center gap-2 rounded-lg border border-cyan-accent/40 bg-cyan-faint px-4 py-2 text-sm font-medium text-cyan-accent transition-colors hover:bg-cyan-accent/20 disabled:cursor-not-allowed disabled:opacity-40"
        >
          {loading ? <Loader2 size={15} className="animate-spin" /> : <Play size={15} />}
          Run counterfactual
        </button>
        {error ? <p className="mt-3 text-sm text-status-warning">{error}</p> : null}
      </div>

      {result ? (
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          <div className="glass-panel p-6">
            <div className="section-label mb-4">Current profile</div>
            <p className="mb-3 whitespace-pre-wrap text-sm text-ink-primary">{result.baseline.answer}</p>
            <div className="grid grid-cols-2 gap-2">
              <StatTile label="Pathway" value={result.baseline.pathway} />
              <StatTile label="Confidence" value={`${result.baseline.confidence}%`} />
              <StatTile label="Hallucination risk" value={result.baseline.hallucination_risk.toFixed(2)} />
              <StatTile
                label="Agreement"
                value={result.baseline.uncertainty_agreement != null ? `${Math.round(result.baseline.uncertainty_agreement)}%` : '-'}
              />
            </div>
          </div>

          <div className="glass-panel border-violet-accent/20 p-6">
            <div className="section-label mb-4">Counterfactual profile</div>
            <p className="mb-3 whitespace-pre-wrap text-sm text-ink-primary">{result.counterfactual.answer}</p>
            <div className="grid grid-cols-2 gap-2">
              <StatTile label="Pathway" value={result.counterfactual.pathway} />
              <StatTile label="Confidence" value={`${result.counterfactual.confidence}%`} />
              <StatTile label="Hallucination risk" value={result.counterfactual.hallucination_risk.toFixed(2)} />
              <StatTile
                label="Agreement"
                value={result.counterfactual.uncertainty_agreement != null ? `${Math.round(result.counterfactual.uncertainty_agreement)}%` : '-'}
              />
            </div>
          </div>

          <div className="glass-panel p-4 text-sm text-ink-secondary lg:col-span-2">
            <p>
              Confidence delta:{' '}
              <span className={result.confidence_delta >= 0 ? 'text-status-good' : 'text-status-warning'}>
                {result.confidence_delta >= 0 ? '+' : ''}
                {result.confidence_delta}%
              </span>{' '}
              · Hallucination-risk delta:{' '}
              <span className={result.hallucination_risk_delta <= 0 ? 'text-status-good' : 'text-status-warning'}>
                {result.hallucination_risk_delta >= 0 ? '+' : ''}
                {result.hallucination_risk_delta.toFixed(2)}
              </span>{' '}
              · Pathway changed:{' '}
              <span className="text-ink-primary">{result.pathway_changed ? 'yes' : 'no'}</span>
            </p>
            <p className="mt-2 text-xs text-ink-muted">{result.note}</p>
          </div>
        </div>
      ) : null}
    </div>
  )
}
