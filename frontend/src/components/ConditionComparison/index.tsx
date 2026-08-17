import { useState } from 'react'
import { Beaker, Loader2, ChevronDown, ChevronUp } from 'lucide-react'
import { runBenchmark } from '../../services/api'
import type { BenchmarkResponse } from '../../types/cognitiveState'
import { truncate } from '../../utils/format'

const CATEGORIES = [
  'factual', 'mathematical', 'logical', 'causal', 'creative', 'ambiguous',
  'conflicting', 'hallucination_prone', 'multi_hop', 'medical_high_stakes',
]

function pct(value: number | null): string {
  return value === null ? 'n/a' : `${Math.round(value * 100)}%`
}

/**
 * Spec section 10/22-9: "Normal LLM" (direct generation, no routing) vs
 * "virtual-brain routing + verification", scored for real accuracy on the
 * benchmark's objectively-checkable items (factual/mathematical/logical),
 * plus abstention rate and hallucination risk elsewhere. This is the bounded,
 * honest version of the H3 experiment -- not a claim of benchmark-scale
 * validation (see data/README.md).
 */
export default function ConditionComparison() {
  const [selected, setSelected] = useState<string[]>(['factual', 'mathematical', 'logical'])
  const [limitPerCategory, setLimitPerCategory] = useState(3)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<BenchmarkResponse | null>(null)
  const [expanded, setExpanded] = useState(false)

  function toggleCategory(cat: string) {
    setSelected((prev) => (prev.includes(cat) ? prev.filter((c) => c !== cat) : [...prev, cat]))
  }

  async function handleRun() {
    if (selected.length === 0) {
      setError('Select at least one category.')
      return
    }
    setLoading(true)
    setError(null)
    try {
      const res = await runBenchmark({ model: 'mock', categories: selected, limit_per_category: limitPerCategory })
      setResult(res)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Benchmark run failed.')
      setResult(null)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="glass-panel p-6">
      <div className="mb-2 flex items-center gap-2">
        <Beaker size={17} strokeWidth={1.75} className="text-cyan-accent" />
        <h2 className="text-base font-semibold text-ink-primary">Condition Comparison — Normal vs. Virtual-Brain Routing</h2>
      </div>
      <p className="mb-4 text-xs leading-relaxed text-ink-secondary">
        Runs each selected benchmark item through Condition 1 (direct generation, no routing) and
        Condition 4 (virtual-brain routing + verification), scoring real accuracy where the item has
        a checkable expected answer (factual / mathematical / logical categories). Uses the offline
        mock model by default so this runs without a model download; results with the local model
        will differ (and take longer).
      </p>

      <div className="mb-4 flex flex-wrap gap-1.5">
        {CATEGORIES.map((cat) => (
          <button
            key={cat}
            type="button"
            onClick={() => toggleCategory(cat)}
            className={`rounded-full border px-2.5 py-1 text-[11px] transition-colors ${
              selected.includes(cat)
                ? 'border-cyan-accent/40 bg-cyan-faint text-cyan-accent'
                : 'border-panel-border bg-panel-light text-ink-muted hover:text-ink-secondary'
            }`}
          >
            {cat.replace(/_/g, ' ')}
          </button>
        ))}
      </div>

      <div className="mb-4 flex flex-wrap items-end gap-4">
        <div>
          <label className="section-label mb-1.5 block">Items per category</label>
          <select
            value={limitPerCategory}
            onChange={(e) => setLimitPerCategory(Number(e.target.value))}
            className="rounded-lg border border-panel-border bg-panel-light px-3 py-2 text-sm text-ink-primary outline-none focus:border-cyan-accent/40"
          >
            {[1, 2, 3, 4, 6, 8].map((n) => (
              <option key={n} value={n}>
                {n}
              </option>
            ))}
          </select>
        </div>
        <button
          type="button"
          onClick={handleRun}
          disabled={loading}
          className="ml-auto flex items-center gap-2 rounded-lg border border-cyan-accent/30 bg-cyan-faint px-4 py-2 text-sm font-medium text-cyan-accent transition-colors hover:bg-cyan-accent/20 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {loading ? <Loader2 size={15} className="animate-spin" /> : <Beaker size={15} />}
          Run Benchmark
        </button>
      </div>

      {error ? <p className="mb-3 text-sm text-status-warning">{error}</p> : null}

      {result ? (
        <>
          <div className="overflow-x-auto">
            <table className="w-full min-w-[640px] border-collapse text-sm">
              <thead>
                <tr className="border-b border-panel-border text-left text-xs uppercase tracking-wide text-ink-muted">
                  <th className="py-2 pr-4 font-medium">Category</th>
                  <th className="py-2 pr-4 font-medium">n</th>
                  <th className="py-2 pr-4 font-medium">Normal accuracy</th>
                  <th className="py-2 pr-4 font-medium">Routed accuracy</th>
                  <th className="py-2 pr-4 font-medium">Abstention rate</th>
                  <th className="py-2 pr-4 font-medium">Mean hallucination risk</th>
                </tr>
              </thead>
              <tbody>
                {result.category_summaries.map((s) => (
                  <tr key={s.category} className="border-b border-panel-border/60 last:border-0">
                    <td className="py-2.5 pr-4 text-ink-primary">{s.category.replace(/_/g, ' ')}</td>
                    <td className="py-2.5 pr-4 font-mono text-ink-secondary">{s.n}</td>
                    <td className="py-2.5 pr-4 font-mono text-ink-secondary">{pct(s.normal_accuracy)}</td>
                    <td className="py-2.5 pr-4 font-mono text-ink-secondary">{pct(s.routed_accuracy)}</td>
                    <td className="py-2.5 pr-4 font-mono text-ink-secondary">{Math.round(s.routed_abstention_rate * 100)}%</td>
                    <td className="py-2.5 pr-4 font-mono text-ink-secondary">{s.mean_hallucination_risk.toFixed(2)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="mt-4 flex flex-wrap gap-x-6 gap-y-1 text-xs text-ink-muted">
            <span>
              Mean latency (normal): <span className="font-mono text-ink-secondary">{Math.round(result.normal_mean_latency_ms)}ms</span>
            </span>
            <span>
              Mean latency (routed): <span className="font-mono text-ink-secondary">{Math.round(result.routed_mean_latency_ms)}ms</span>
            </span>
          </div>

          <button
            type="button"
            onClick={() => setExpanded((v) => !v)}
            className="mt-4 flex items-center gap-1.5 text-xs text-cyan-accent hover:underline"
          >
            {expanded ? <ChevronUp size={13} /> : <ChevronDown size={13} />}
            {expanded ? 'Hide per-item detail' : 'Show per-item detail'}
          </button>

          {expanded ? (
            <div className="mt-3 flex max-h-96 flex-col gap-2 overflow-y-auto">
              {result.items.map((item) => (
                <div key={item.id} className="rounded-lg border border-panel-border bg-panel-light/40 p-3 text-xs">
                  <div className="mb-1 flex items-center justify-between">
                    <span className="text-ink-primary">{truncate(item.query, 90)}</span>
                    <span className="text-ink-muted">{item.category.replace(/_/g, ' ')}</span>
                  </div>
                  <div className="grid grid-cols-1 gap-1 text-ink-secondary sm:grid-cols-2">
                    <span>
                      Normal: {truncate(item.condition_normal_answer, 80)}{' '}
                      {item.condition_normal_correct !== null ? (item.condition_normal_correct ? '✓' : '✗') : ''}
                    </span>
                    <span>
                      Routed ({item.condition_routed_pathway}
                      {item.condition_routed_abstained ? ', abstained' : ''}): {truncate(item.condition_routed_answer, 80)}{' '}
                      {item.condition_routed_correct !== null ? (item.condition_routed_correct ? '✓' : '✗') : ''}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          ) : null}
        </>
      ) : null}
    </div>
  )
}
