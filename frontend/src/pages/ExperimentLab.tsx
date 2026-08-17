import { useEffect, useState } from 'react'
import { FlaskConical, Scale, Loader2 } from 'lucide-react'
import { runExperiment, getConfig } from '../services/api'
import type { ExperimentResponse, RegionScores } from '../types/cognitiveState'
import BrainVisualization from '../components/BrainVisualization'
import ExperimentCard from '../components/ExperimentCard'
import ConditionComparison from '../components/ConditionComparison'

const DEFAULT_REGIONS: RegionScores = { language: 0, memory: 0, reasoning: 0, uncertainty: 0, verification: 0 }

const PRESETS: { label: string; queryA: string; queryB: string }[] = [
  {
    label: 'Creativity vs. Coding',
    queryA: 'Write a poem about Mars.',
    queryB: 'Write a Python function to calculate Mars orbital velocity.',
  },
  {
    label: 'Ambiguous vs. Precise',
    queryA: "What's the best programming language?",
    queryB: 'What is the time complexity of binary search?',
  },
  {
    label: 'High-risk vs. Low-risk',
    queryA: 'What dosage of ibuprofen is safe to take daily?',
    queryB: 'What color is the sky on a clear day?',
  },
]

export default function ExperimentLab() {
  const [queryA, setQueryA] = useState('')
  const [queryB, setQueryB] = useState('')
  const [model, setModel] = useState('mock')
  const [models, setModels] = useState<string[]>(['mock'])
  const [numSamples, setNumSamples] = useState(5)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<ExperimentResponse | null>(null)

  useEffect(() => {
    let cancelled = false
    getConfig()
      .then((cfg) => {
        if (cancelled) return
        setModels(cfg.available_models.length ? cfg.available_models : ['mock'])
        setModel(cfg.default_model)
        setNumSamples(cfg.default_num_samples)
      })
      .catch(() => {
        // Config endpoint unavailable - keep the sane defaults above.
      })
    return () => {
      cancelled = true
    }
  }, [])

  async function handleRun() {
    if (!queryA.trim() || !queryB.trim()) {
      setError('Enter a query for both Side A and Side B.')
      return
    }
    setLoading(true)
    setError(null)
    try {
      const res = await runExperiment({ query_a: queryA, query_b: queryB, model, num_samples: numSamples })
      setResult(res)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Experiment failed.')
      setResult(null)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="glass-panel p-6">
        <div className="mb-4 flex items-center gap-2">
          <FlaskConical size={18} strokeWidth={1.75} className="text-cyan-accent" />
          <h1 className="text-lg font-semibold text-ink-primary">Experiment Lab</h1>
        </div>
        <p className="mb-5 text-sm text-ink-secondary">
          Run two queries side by side and compare their cognitive-state signatures - useful for
          seeing how task type (creative vs. factual, ambiguous vs. precise, risky vs. safe)
          shifts confidence, uncertainty, and brain-region activation.
        </p>

        <div className="mb-5 flex flex-wrap gap-2">
          {PRESETS.map((preset) => (
            <button
              key={preset.label}
              type="button"
              onClick={() => {
                setQueryA(preset.queryA)
                setQueryB(preset.queryB)
              }}
              className="rounded-full border border-panel-border bg-panel-light px-3 py-1.5 text-xs text-ink-secondary transition-colors hover:border-cyan-accent/30 hover:text-cyan-accent"
            >
              {preset.label}
            </button>
          ))}
        </div>

        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          <div>
            <label className="section-label mb-1.5 block">Query A</label>
            <textarea
              value={queryA}
              onChange={(e) => setQueryA(e.target.value)}
              rows={3}
              placeholder="e.g. Write a poem about Mars."
              className="w-full resize-none rounded-lg border border-panel-border bg-panel-light px-3 py-2 text-sm text-ink-primary outline-none placeholder:text-ink-muted focus:border-cyan-accent/40"
            />
          </div>
          <div>
            <label className="section-label mb-1.5 block">Query B</label>
            <textarea
              value={queryB}
              onChange={(e) => setQueryB(e.target.value)}
              rows={3}
              placeholder="e.g. Write a Python function to calculate Mars orbital velocity."
              className="w-full resize-none rounded-lg border border-panel-border bg-panel-light px-3 py-2 text-sm text-ink-primary outline-none placeholder:text-ink-muted focus:border-cyan-accent/40"
            />
          </div>
        </div>

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
          <div>
            <label className="section-label mb-1.5 block">Samples per side</label>
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
            onClick={handleRun}
            disabled={loading}
            className="ml-auto flex items-center gap-2 rounded-lg border border-cyan-accent/30 bg-cyan-faint px-4 py-2 text-sm font-medium text-cyan-accent transition-colors hover:bg-cyan-accent/20 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {loading ? <Loader2 size={15} className="animate-spin" /> : <FlaskConical size={15} />}
            Run Experiment
          </button>
        </div>

        {error ? <p className="mt-3 text-sm text-status-warning">{error}</p> : null}
      </div>

      {result ? (
        <div className="glass-panel flex items-center justify-center gap-3 p-4">
          <Scale size={16} strokeWidth={1.75} className="text-violet-accent" />
          <span className="text-sm text-ink-secondary">Response agreement between sides:</span>
          <span className="font-mono text-lg font-semibold text-violet-accent">
            {Math.round(result.response_agreement_between_sides)}%
          </span>
        </div>
      ) : null}

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <div className="flex flex-col gap-4">
          {(loading || result) && (
            <BrainVisualization
              regions={result?.side_a.cognitive_state.brain_regions.measured ?? result?.side_a.cognitive_state.brain_regions.predicted ?? DEFAULT_REGIONS}
              mode={result?.side_a.cognitive_state.brain_regions.measured ? 'measured' : 'predicted'}
              pathway={result?.side_a.pathway}
              hallucinationRisk={result?.side_a.hallucination_risk.score}
            />
          )}
          <ExperimentCard label="A" query={queryA} response={result?.side_a ?? null} loading={loading} />
        </div>
        <div className="flex flex-col gap-4">
          {(loading || result) && (
            <BrainVisualization
              regions={result?.side_b.cognitive_state.brain_regions.measured ?? result?.side_b.cognitive_state.brain_regions.predicted ?? DEFAULT_REGIONS}
              mode={result?.side_b.cognitive_state.brain_regions.measured ? 'measured' : 'predicted'}
              pathway={result?.side_b.pathway}
              hallucinationRisk={result?.side_b.hallucination_risk.score}
            />
          )}
          <ExperimentCard label="B" query={queryB} response={result?.side_b ?? null} loading={loading} />
        </div>
      </div>

      <ConditionComparison />
    </div>
  )
}
