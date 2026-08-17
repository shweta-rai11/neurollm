import { useEffect, useState } from 'react'
import { Activity, Loader2, Waves } from 'lucide-react'
import { Line, LineChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { chat, getConfig } from '../services/api'
import type { ChatResponse, ConfigResponse } from '../types/cognitiveState'
import StatTile from '../components/common/StatTile'

const CHART_TOOLTIP_STYLE = { background: '#10151d', border: '1px solid rgba(148,163,184,0.12)', borderRadius: 8, fontSize: 12 }
const AXIS_TICK = { fill: '#9aa7b8', fontSize: 11 }

function LayerChart({
  data,
  dataKey,
  color,
  yLabel,
  xLabel = 'Layer',
}: {
  data: { layer: number; value: number }[]
  dataKey: string
  color: string
  yLabel: string
  xLabel?: string
}) {
  return (
    <div className="h-56 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data} margin={{ left: 4, right: 12, top: 8, bottom: 4 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.08)" vertical={false} />
          <XAxis
            dataKey="layer"
            tickLine={false}
            axisLine={false}
            tick={AXIS_TICK}
            interval={Math.max(0, Math.ceil(data.length / 15) - 1)}
            label={{ value: xLabel, position: 'insideBottom', offset: -2, fill: '#9aa7b8', fontSize: 11 }}
          />
          <YAxis tickLine={false} axisLine={false} tick={AXIS_TICK} label={{ value: yLabel, angle: -90, position: 'insideLeft', fill: '#9aa7b8', fontSize: 11 }} />
          <Tooltip contentStyle={CHART_TOOLTIP_STYLE} labelStyle={{ color: '#e6edf3' }} />
          <Line type="monotone" dataKey="value" name={dataKey} stroke={color} strokeWidth={2} dot={{ r: 2 }} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}

/**
 * Activation Explorer (spec section 14/19): layer-by-layer real activation
 * detail for the last research-mode query. Only the local model exposes
 * this -- if `research` comes back null the page says so explicitly rather
 * than rendering an empty/fake chart (see backend README, "no fabricated
 * numbers").
 */
export default function ActivationExplorer() {
  const [query, setQuery] = useState('')
  const [model, setModel] = useState('local_hf')
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

  async function handleRun() {
    if (!query.trim()) {
      setError('Enter a query to inspect.')
      return
    }
    setLoading(true)
    setError(null)
    try {
      const res = await chat({ query, model, uncertainty_mode: false, num_samples: 1, research_mode: true })
      setResult(res)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Request failed.')
      setResult(null)
    } finally {
      setLoading(false)
    }
  }

  const research = result?.research

  const hiddenNormData = research ? research.layer_hidden_norms.map((value, layer) => ({ layer, value })) : []
  const attentionEntropyData = research ? research.layer_attention_entropy.map((value, layer) => ({ layer, value })) : []
  const tokenEntropyData = research ? research.token_entropies.map((value, i) => ({ layer: i, value })) : []
  const probMarginData = research ? research.token_prob_margins.map((value, i) => ({ layer: i, value })) : []

  return (
    <div className="flex flex-col gap-6">
      <div className="glass-panel p-6">
        <div className="mb-4 flex items-center gap-2">
          <Activity size={18} strokeWidth={1.75} className="text-cyan-accent" />
          <h1 className="text-lg font-semibold text-ink-primary">Activation Explorer</h1>
        </div>
        <p className="mb-5 text-sm text-ink-secondary">
          Real, layer-by-layer hidden-state and attention statistics captured from a live forward
          pass through the local model - not simulated. Requires the local model (research mode is
          implied by this page).
        </p>

        <label className="section-label mb-1.5 block">Query</label>
        <textarea
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          rows={2}
          placeholder="e.g. Explain why the sky is blue."
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
            onClick={handleRun}
            disabled={loading}
            className="ml-auto flex items-center gap-2 rounded-lg border border-cyan-accent/30 bg-cyan-faint px-4 py-2 text-sm font-medium text-cyan-accent transition-colors hover:bg-cyan-accent/20 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {loading ? <Loader2 size={15} className="animate-spin" /> : <Waves size={15} />}
            Capture Activations
          </button>
        </div>

        {error ? <p className="mt-3 text-sm text-status-warning">{error}</p> : null}
      </div>

      {result && !research ? (
        <div className="glass-panel p-6 text-sm text-status-caution">
          No activation data available for this response - Activation Explorer only works with the
          local model (<code className="font-mono text-xs">local_hf</code>), which was not used for this
          request. Select it above and try again.
        </div>
      ) : null}

      {research ? (
        <>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            <StatTile label="Layers" value={research.num_layers} />
            <StatTile label="Generated tokens" value={research.token_entropies.length} />
            <StatTile label="Mean token entropy" value={research.activation_features.mean_token_entropy?.toFixed(3) ?? 'n/a'} />
            <StatTile label="Mean prob. margin" value={research.activation_features.mean_prob_margin?.toFixed(3) ?? 'n/a'} />
          </div>

          <div className="glass-panel p-6">
            <div className="section-label mb-3">Hidden-state activation magnitude by layer</div>
            <LayerChart data={hiddenNormData} dataKey="L2 norm" color="#38bdf8" yLabel="Mean L2 norm" />
          </div>

          <div className="glass-panel p-6">
            <div className="section-label mb-3">Attention entropy by layer (position-normalized)</div>
            <LayerChart data={attentionEntropyData} dataKey="Entropy" color="#a78bfa" yLabel="Normalized entropy" />
          </div>

          <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
            <div className="glass-panel p-6">
              <div className="section-label mb-3">Per-token entropy (generated answer)</div>
              <LayerChart data={tokenEntropyData} dataKey="Entropy" color="#f5a524" yLabel="Entropy (nats)" xLabel="Token index" />
            </div>
            <div className="glass-panel p-6">
              <div className="section-label mb-3">Per-token probability margin (top1 − top2)</div>
              <LayerChart data={probMarginData} dataKey="Margin" color="#2dd4bf" yLabel="Margin" xLabel="Token index" />
            </div>
          </div>
        </>
      ) : null}
    </div>
  )
}
