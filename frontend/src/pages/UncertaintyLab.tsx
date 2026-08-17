import { useState } from 'react'
import { Gauge, Loader2 } from 'lucide-react'
import { Bar, BarChart, Cell, ResponsiveContainer, XAxis, YAxis, Tooltip } from 'recharts'
import { estimateUncertainty } from '../services/api'
import type { UncertaintyResponse } from '../types/cognitiveState'
import UncertaintyPanel from '../components/UncertaintyPanel'
import StatTile from '../components/common/StatTile'
import { clusterColor } from '../utils/colors'

export default function UncertaintyLab() {
  const [query, setQuery] = useState('')
  const [numSamples, setNumSamples] = useState(5)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<UncertaintyResponse | null>(null)

  async function handleAnalyze() {
    if (!query.trim()) {
      setError('Enter a query to analyze.')
      return
    }
    setLoading(true)
    setError(null)
    try {
      const res = await estimateUncertainty({ query, num_samples: numSamples })
      setResult(res)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Uncertainty estimation failed.')
      setResult(null)
    } finally {
      setLoading(false)
    }
  }

  const clusterCounts = result
    ? Array.from(
        result.uncertainty.candidates.reduce((acc, c) => {
          acc.set(c.cluster_id, (acc.get(c.cluster_id) ?? 0) + 1)
          return acc
        }, new Map<number, number>()),
      )
      .sort((a, b) => a[0] - b[0])
      .map(([clusterId, count]) => ({ clusterId, label: `Cluster ${clusterId}`, count }))
    : []

  return (
    <div className="flex flex-col gap-6">
      <div className="glass-panel p-6">
        <div className="mb-4 flex items-center gap-2">
          <Gauge size={18} strokeWidth={1.75} className="text-cyan-accent" />
          <h1 className="text-lg font-semibold text-ink-primary">Uncertainty Lab</h1>
        </div>
        <p className="mb-5 text-sm text-ink-secondary">
          Sample the model multiple times on the same query and measure how much the answers
          agree - a response-consistency uncertainty estimate, not a claim about correctness.
        </p>

        <label className="section-label mb-1.5 block">Query</label>
        <textarea
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          rows={3}
          placeholder="e.g. What year did the French Revolution begin?"
          className="w-full resize-none rounded-lg border border-panel-border bg-panel-light px-3 py-2 text-sm text-ink-primary outline-none placeholder:text-ink-muted focus:border-cyan-accent/40"
        />

        <div className="mt-4 flex flex-wrap items-end gap-4">
          <div>
            <label className="section-label mb-1.5 block">Number of samples</label>
            <select
              value={numSamples}
              onChange={(e) => setNumSamples(Number(e.target.value))}
              className="rounded-lg border border-panel-border bg-panel-light px-3 py-2 text-sm text-ink-primary outline-none focus:border-cyan-accent/40"
            >
              {[3, 5, 7, 10].map((n) => (
                <option key={n} value={n}>
                  {n}
                </option>
              ))}
            </select>
          </div>
          <button
            type="button"
            onClick={handleAnalyze}
            disabled={loading}
            className="ml-auto flex items-center gap-2 rounded-lg border border-cyan-accent/30 bg-cyan-faint px-4 py-2 text-sm font-medium text-cyan-accent transition-colors hover:bg-cyan-accent/20 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {loading ? <Loader2 size={15} className="animate-spin" /> : <Gauge size={15} />}
            Analyze Uncertainty
          </button>
        </div>

        {error ? <p className="mt-3 text-sm text-status-warning">{error}</p> : null}
      </div>

      {result ? (
        <>
          <div className="glass-panel p-6">
            <div className="section-label mb-3">Cluster size distribution</div>
            <div className="h-48 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={clusterCounts} margin={{ left: 0, right: 12, top: 4, bottom: 4 }}>
                  <XAxis dataKey="label" tickLine={false} axisLine={false} tick={{ fill: '#9aa7b8', fontSize: 11 }} />
                  <YAxis
                    allowDecimals={false}
                    tickLine={false}
                    axisLine={false}
                    tick={{ fill: '#9aa7b8', fontSize: 11 }}
                  />
                  <Tooltip
                    cursor={{ fill: 'rgba(148,163,184,0.06)' }}
                    contentStyle={{
                      background: '#10151d',
                      border: '1px solid rgba(148,163,184,0.12)',
                      borderRadius: 8,
                      fontSize: 12,
                    }}
                    labelStyle={{ color: '#e6edf3' }}
                    itemStyle={{ color: '#9aa7b8' }}
                    formatter={(value: number) => [value, 'Responses']}
                  />
                  <Bar dataKey="count" radius={[4, 4, 0, 0]} maxBarSize={48}>
                    {clusterCounts.map((entry) => (
                      <Cell key={entry.clusterId} fill={clusterColor(entry.clusterId)} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>

            <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-2">
              <StatTile
                label="Mean embedding similarity"
                value={result.uncertainty.mean_embedding_similarity.toFixed(3)}
                hint="Pairwise similarity across candidates (0-1)"
              />
              <StatTile
                label="Max embedding distance"
                value={result.uncertainty.max_embedding_distance.toFixed(3)}
                hint="Furthest-apart candidate pair"
              />
            </div>
          </div>

          <UncertaintyPanel uncertainty={result.uncertainty} />
        </>
      ) : null}

      <p className="text-xs leading-relaxed text-ink-muted">
        <span className="font-semibold text-ink-secondary">Method: </span>
        this is a simplified, semantic-entropy-inspired approximation built from lightweight
        text-similarity clustering - it is not the original published semantic-entropy method
        and should be read as a directional signal, not a calibrated probability. See README for
        methodology and references.
      </p>
    </div>
  )
}
