import { useEffect, useState } from 'react'
import { FlaskConical, Loader2, Microscope, Route } from 'lucide-react'
import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { chat, getConfig } from '../services/api'
import type { ChatResponse, ConfigResponse, RegionScores } from '../types/cognitiveState'
import StatTile from '../components/common/StatTile'
import { PATHWAY_COLORS } from '../utils/colors'

const REGION_LABELS: Record<keyof RegionScores, string> = {
  language: 'Language',
  memory: 'Memory',
  reasoning: 'Reasoning',
  uncertainty: 'Uncertainty',
  verification: 'Verification',
}
const REGION_ORDER: (keyof RegionScores)[] = ['language', 'memory', 'reasoning', 'uncertainty', 'verification']

/**
 * Question Lab (spec section 14): enter a question, see the predicted
 * (pre-generation, text-only) vs measured (post-generation, activation-
 * derived) cognitive profile side by side, the probe's category prediction,
 * and which pathway the executive controller chose and why. This is the
 * page that actually operationalizes H1 ("do activations predict cognitive
 * requirements") by making the two profiles directly comparable rather than
 * only showing one blended number.
 */
export default function QuestionLab() {
  const [query, setQuery] = useState('')
  const [model, setModel] = useState('mock')
  const [models, setModels] = useState<string[]>(['mock'])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<ChatResponse | null>(null)

  useEffect(() => {
    let cancelled = false
    getConfig()
      .then((cfg: ConfigResponse) => {
        if (cancelled) return
        setModels(cfg.available_models.length ? cfg.available_models : ['mock'])
        setModel(cfg.available_models.includes('local_hf') ? 'local_hf' : cfg.default_model)
      })
      .catch(() => {})
    return () => {
      cancelled = true
    }
  }, [])

  async function handleAnalyze() {
    if (!query.trim()) {
      setError('Enter a question to analyze.')
      return
    }
    setLoading(true)
    setError(null)
    try {
      const res = await chat({ query, model, uncertainty_mode: true, num_samples: 4, research_mode: true })
      setResult(res)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Analysis failed.')
      setResult(null)
    } finally {
      setLoading(false)
    }
  }

  const regions = result?.cognitive_state.brain_regions
  const chartData = regions
    ? REGION_ORDER.map((key) => ({
        label: REGION_LABELS[key],
        Predicted: regions.predicted[key],
        Measured: regions.measured ? regions.measured[key] : null,
      }))
    : []

  const probe = result?.research?.probe_prediction

  return (
    <div className="flex flex-col gap-6">
      <div className="glass-panel p-6">
        <div className="mb-4 flex items-center gap-2">
          <FlaskConical size={18} strokeWidth={1.75} className="text-cyan-accent" />
          <h1 className="text-lg font-semibold text-ink-primary">Question Lab</h1>
        </div>
        <p className="mb-5 text-sm text-ink-secondary">
          Enter a question to see its <strong className="text-ink-primary">predicted</strong> cognitive profile
          (text heuristics, before generation) against its <strong className="text-ink-primary">measured</strong>{' '}
          profile (real activation statistics, after generation) - select the local model to populate the measured
          side and the category probe.
        </p>

        <label className="section-label mb-1.5 block">Question</label>
        <textarea
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          rows={3}
          placeholder="e.g. If A is greater than B, and B is greater than C, is A greater than C?"
          className="w-full resize-none rounded-lg border border-panel-border bg-panel-light px-3 py-2 text-sm text-ink-primary outline-none placeholder:text-ink-muted focus:border-cyan-accent/40"
        />

        <div className="mt-4 flex flex-wrap items-end gap-4">
          <div>
            <label className="section-label mb-1.5 block">Model</label>
            <select
              value={model}
              onChange={(e) => setModel(e.target.value)}
              className="rounded-lg border border-panel-border bg-panel-light px-3 py-2 text-sm text-ink-primary outline-none focus:border-cyan-accent/40"
            >
              {models.map((m) => (
                <option key={m} value={m}>
                  {m}
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
            {loading ? <Loader2 size={15} className="animate-spin" /> : <FlaskConical size={15} />}
            Analyze
          </button>
        </div>

        {error ? <p className="mt-3 text-sm text-status-warning">{error}</p> : null}
      </div>

      {result ? (
        <>
          <div className="glass-panel p-6">
            <div className="mb-4 flex items-center justify-between">
              <div className="section-label">Predicted vs. Measured Cognitive Profile</div>
              <span
                className="badge"
                style={{
                  borderColor: `${PATHWAY_COLORS[result.pathway]}40`,
                  backgroundColor: `${PATHWAY_COLORS[result.pathway]}14`,
                  color: PATHWAY_COLORS[result.pathway],
                }}
              >
                <Route size={12} className="mr-1 inline" strokeWidth={1.75} />
                {result.pathway}
              </span>
            </div>
            {!regions?.measured ? (
              <p className="mb-3 text-xs text-status-caution">
                No measured profile available - select the local model (and Research Mode is implied by this page) to
                populate real activation-derived scores. Currently showing predicted-only.
              </p>
            ) : null}
            <div className="h-64 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={chartData} margin={{ left: 0, right: 12, top: 4, bottom: 4 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.08)" vertical={false} />
                  <XAxis dataKey="label" tickLine={false} axisLine={false} tick={{ fill: '#9aa7b8', fontSize: 11 }} />
                  <YAxis domain={[0, 100]} tickLine={false} axisLine={false} tick={{ fill: '#9aa7b8', fontSize: 11 }} />
                  <Tooltip
                    cursor={{ fill: 'rgba(148,163,184,0.06)' }}
                    contentStyle={{ background: '#10151d', border: '1px solid rgba(148,163,184,0.12)', borderRadius: 8, fontSize: 12 }}
                    labelStyle={{ color: '#e6edf3' }}
                  />
                  <Legend wrapperStyle={{ fontSize: 12 }} />
                  <Bar dataKey="Predicted" fill="#38bdf8" radius={[4, 4, 0, 0]} maxBarSize={28} />
                  <Bar dataKey="Measured" fill="#a78bfa" radius={[4, 4, 0, 0]} maxBarSize={28} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
            <div className="glass-panel p-6">
              <div className="mb-3 flex items-center gap-2">
                <Microscope size={16} strokeWidth={1.75} className="text-violet-accent" />
                <div className="section-label">Category Probe</div>
              </div>
              {probe ? (
                <>
                  <p className="mb-3 text-sm text-ink-secondary">
                    Predicted category: <span className="font-semibold text-ink-primary">{probe.predicted_category}</span>{' '}
                    <span className="font-mono text-xs text-ink-muted">({Math.round(probe.confidence * 100)}% confidence, {probe.probe_type})</span>
                  </p>
                  <div className="flex flex-col gap-1.5">
                    {Object.entries(probe.probabilities)
                      .sort((a, b) => b[1] - a[1])
                      .map(([cat, p]) => (
                        <div key={cat} className="flex items-center gap-2 text-xs">
                          <span className="w-32 shrink-0 text-ink-secondary">{cat.replace(/_/g, ' ')}</span>
                          <div className="meter-track h-1.5 flex-1">
                            <div className="meter-fill bg-violet-accent" style={{ width: `${Math.round(p * 100)}%` }} />
                          </div>
                          <span className="w-10 shrink-0 text-right font-mono text-ink-muted">{Math.round(p * 100)}%</span>
                        </div>
                      ))}
                  </div>
                </>
              ) : (
                <p className="text-sm text-ink-muted">
                  No trained probe available, or the local model wasn't used for this query. Run{' '}
                  <code className="rounded bg-panel-light px-1 py-0.5 font-mono text-[11px]">backend/app/probes/train.py</code> and select
                  the local model.
                </p>
              )}
            </div>

            <div className="glass-panel p-6">
              <div className="mb-3 section-label">Task Analysis (heuristic)</div>
              <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
                {Object.entries(result.task_analysis).map(([key, value]) => (
                  <StatTile key={key} label={key.replace(/_/g, ' ')} value={`${value}%`} />
                ))}
              </div>
            </div>
          </div>

          <div className="glass-panel p-4 text-xs leading-relaxed text-ink-secondary">
            <span className="font-medium text-ink-primary">Routing reason: </span>
            {result.research?.routing_reason ?? 'Research details unavailable for this provider.'}
          </div>
        </>
      ) : null}
    </div>
  )
}
