import { useState } from 'react'
import { Microscope, Loader2, Play } from 'lucide-react'
import { runResearchCompare } from '../../services/api'
import { useProfileId } from '../../hooks/useProfileId'
import type { ResearchCompareResponse } from '../../types/profile'

const CATEGORIES = ['factual', 'mathematical', 'logical', 'causal', 'creative']

export default function Research() {
  const { profileId } = useProfileId()
  const [categories, setCategories] = useState<string[]>(['factual', 'mathematical', 'logical'])
  const [limitPerCategory, setLimitPerCategory] = useState(2)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<ResearchCompareResponse | null>(null)

  function toggleCategory(cat: string) {
    setCategories((cs) => (cs.includes(cat) ? cs.filter((c) => c !== cat) : [...cs, cat]))
  }

  async function run() {
    setLoading(true)
    setError(null)
    try {
      const res = await runResearchCompare({
        profile_id: profileId,
        model: 'mock',
        categories,
        limit_per_category: limitPerCategory,
      })
      setResult(res)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Research run failed.')
      setResult(null)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="glass-panel p-6">
        <div className="mb-1 flex items-center gap-2">
          <Microscope size={18} strokeWidth={1.75} className="text-violet-accent" />
          <h1 className="text-lg font-semibold text-ink-primary">Research Mode</h1>
        </div>
        <p className="mb-5 text-sm text-ink-secondary">
          Does a fingerprint-linked computational profile provide any predictive value beyond behavioral history
          alone? Compares <strong className="text-ink-primary">Condition A</strong> (LLM only),{' '}
          <strong className="text-ink-primary">Condition B</strong> (virtual brain, anonymous/default profile), and{' '}
          <strong className="text-ink-primary">Condition C</strong> (virtual brain, your fingerprint-linked profile)
          over a small benchmark. If C shows no benefit, this reports that honestly.
        </p>

        {!profileId ? (
          <p className="mb-4 rounded-lg border border-status-caution/30 bg-status-caution/10 px-3 py-2 text-xs text-status-caution">
            No profile loaded - Condition C will be identical to Condition B by construction. Scan a fingerprint
            first for a meaningful comparison.
          </p>
        ) : null}

        <div className="mb-4 flex flex-wrap gap-2">
          {CATEGORIES.map((cat) => (
            <button
              key={cat}
              type="button"
              onClick={() => toggleCategory(cat)}
              className={`rounded-full border px-3 py-1.5 text-xs transition-colors ${
                categories.includes(cat)
                  ? 'border-cyan-accent/40 bg-cyan-faint text-cyan-accent'
                  : 'border-panel-border bg-panel-light text-ink-secondary hover:text-ink-primary'
              }`}
            >
              {cat}
            </button>
          ))}
        </div>

        <div className="mb-5 flex items-center gap-3">
          <label className="text-xs text-ink-secondary">Items per category ({limitPerCategory})</label>
          <input
            type="range"
            min={1}
            max={6}
            value={limitPerCategory}
            onChange={(e) => setLimitPerCategory(Number(e.target.value))}
            className="h-1.5 w-32 accent-violet-accent"
          />
        </div>

        <button
          type="button"
          onClick={run}
          disabled={loading || categories.length === 0}
          className="flex items-center gap-2 rounded-lg border border-violet-accent/40 bg-violet-faint px-4 py-2 text-sm font-medium text-violet-accent transition-colors hover:bg-violet-accent/20 disabled:cursor-not-allowed disabled:opacity-40"
        >
          {loading ? <Loader2 size={15} className="animate-spin" /> : <Play size={15} />}
          Run comparison
        </button>
        {error ? <p className="mt-3 text-sm text-status-warning">{error}</p> : null}
      </div>

      {result ? (
        <>
          <div className="glass-panel overflow-x-auto p-6">
            <table className="w-full min-w-[520px] text-left text-sm">
              <thead>
                <tr className="border-b border-panel-border text-xs text-ink-muted">
                  <th className="py-2 pr-4 font-medium">Condition</th>
                  <th className="py-2 pr-4 font-medium">n</th>
                  <th className="py-2 pr-4 font-medium">Accuracy</th>
                  <th className="py-2 pr-4 font-medium">Mean hallucination risk</th>
                  <th className="py-2 pr-4 font-medium">Abstention rate</th>
                </tr>
              </thead>
              <tbody>
                {result.conditions.map((c) => (
                  <tr key={c.condition} className="border-b border-panel-border/50">
                    <td className="py-2 pr-4">
                      <span className="font-mono font-semibold text-ink-primary">{c.condition}</span>{' '}
                      <span className="text-xs text-ink-muted">{c.label}</span>
                    </td>
                    <td className="py-2 pr-4 text-ink-secondary">{c.n}</td>
                    <td className="py-2 pr-4 text-ink-secondary">{c.accuracy != null ? `${Math.round(c.accuracy * 100)}%` : '-'}</td>
                    <td className="py-2 pr-4 text-ink-secondary">{c.mean_hallucination_risk.toFixed(2)}</td>
                    <td className="py-2 pr-4 text-ink-secondary">{Math.round(c.abstention_rate * 100)}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="glass-panel border-cyan-accent/20 p-5 text-sm leading-relaxed text-ink-secondary">
            <span className="font-medium text-ink-primary">Honest summary: </span>
            {result.honest_summary}
          </div>
        </>
      ) : null}
    </div>
  )
}
