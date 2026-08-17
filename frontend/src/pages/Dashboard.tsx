import { useEffect, useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { Loader2, Send, TriangleAlert, Info, Microscope } from 'lucide-react'
import BrainVisualization from '../components/BrainVisualization'
import CognitiveState from '../components/CognitiveState'
import NeuromodulationPanel from '../components/NeuromodulationPanel'
import ResponsePanel from '../components/ResponsePanel'
import RecommendationPanel from '../components/RecommendationPanel'
import { chat, getConfig } from '../services/api'
import type { ChatResponse, ConfigResponse, RegionScores } from '../types/cognitiveState'

const DEFAULT_REGIONS: RegionScores = {
  language: 0,
  memory: 0,
  reasoning: 0,
  uncertainty: 0,
  verification: 0,
}

// Spec section 20/23's three-question demonstration: a simple factual
// question expected to route DIRECT, a multi-step reasoning question
// expected to route ANALYTICAL, and an obscure/hallucination-prone question
// expected to trigger VERIFY (and possibly an explicit abstention).
const DEMO_QUESTIONS = [
  { label: 'Q1 · Simple factual', query: 'What is the capital of Japan?' },
  {
    label: 'Q2 · Multi-step reasoning',
    query: 'A train travels 60 mph for 2 hours, then 40 mph for 1 hour. What is the average speed for the whole trip?',
  },
  {
    label: 'Q3 · Obscure factual',
    query: "What was the exact attendance figure at the 1987 Wimbledon Gentlemen's Singles final?",
  },
]

export default function Dashboard() {
  const [config, setConfig] = useState<ConfigResponse | null>(null)
  const [query, setQuery] = useState('')
  const [model, setModel] = useState<string>('mock')
  const [numSamples, setNumSamples] = useState(5)
  const [uncertaintyMode, setUncertaintyMode] = useState(true)
  const [researchMode, setResearchMode] = useState(false)

  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<ChatResponse | null>(null)

  useEffect(() => {
    getConfig()
      .then((cfg) => {
        setConfig(cfg)
        setModel(cfg.default_model)
        setNumSamples(cfg.default_num_samples)
      })
      .catch(() => {
        // Backend may not be running yet - the model selector just falls
        // back to the "mock" default and the form still submits.
      })
  }, [])

  async function runQuery(q: string) {
    if (!q.trim() || loading) return
    setLoading(true)
    setError(null)
    try {
      const response = await chat({
        query: q.trim(),
        model,
        uncertainty_mode: uncertaintyMode,
        num_samples: numSamples,
        research_mode: researchMode,
      })
      setResult(response)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'AI model unavailable.')
      setResult(null)
    } finally {
      setLoading(false)
    }
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    await runQuery(query)
  }

  const isLocalModel = model === 'local_hf'
  const regionProfile = result?.cognitive_state.brain_regions
  const displayedRegions = regionProfile?.measured ?? regionProfile?.predicted ?? DEFAULT_REGIONS
  const maxSamples = config?.max_num_samples ?? 10

  return (
    <div className="flex flex-col gap-6">
      {/* What this page does, up front - not just discoverable via hover/About */}
      <div className="glass-panel flex items-start gap-3 border-cyan-accent/20 p-4">
        <Info size={18} className="mt-0.5 shrink-0 text-cyan-accent" />
        <p className="text-xs leading-relaxed text-ink-secondary">
          <span className="font-medium text-ink-primary">How this works:</span> type a question below and submit it.
          NeuroLLM scores the question, generates an answer, and routes it through a virtual brain that estimates
          cognitive demand and hallucination risk - shown below as region activations, a neuromodulation readout
          (computational metaphors, not biology), state meters, and a recommendation. Select the local model and
          enable Research Mode to see real activation statistics rather than text-only heuristics. See{' '}
          <Link to="/about" className="text-cyan-accent underline decoration-cyan-accent/30 underline-offset-2 hover:decoration-cyan-accent">
            About
          </Link>{' '}
          for the full explanation and its limitations.
        </p>
      </div>

      {/* Demo presets - spec's three-question demonstration */}
      <div className="glass-panel flex flex-wrap items-center gap-2 p-4">
        <span className="section-label mr-1">Demo questions:</span>
        {DEMO_QUESTIONS.map((d) => (
          <button
            key={d.label}
            type="button"
            onClick={() => {
              setQuery(d.query)
              void runQuery(d.query)
            }}
            className="rounded-full border border-panel-border bg-panel-light px-3 py-1.5 text-xs text-ink-secondary transition-colors hover:border-cyan-accent/30 hover:text-cyan-accent"
          >
            {d.label}
          </button>
        ))}
      </div>

      {/* Query bar */}
      <form onSubmit={handleSubmit} className="glass-panel flex flex-col gap-4 p-5">
        <div className="flex flex-col gap-2">
          <label htmlFor="query" className="section-label">
            Query
          </label>
          <textarea
            id="query"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Ask NeuroLLM something and watch its virtual brain respond…"
            rows={3}
            className="w-full resize-none rounded-lg border border-panel-border bg-panel-light/60 px-3 py-2 text-sm text-ink-primary placeholder:text-ink-muted focus:border-cyan-accent/50 focus:outline-none focus:ring-1 focus:ring-cyan-accent/30"
          />
        </div>

        <div className="flex flex-wrap items-end gap-4">
          <div className="flex flex-col gap-1">
            <label htmlFor="model" className="text-xs text-ink-secondary">
              Model
            </label>
            <select
              id="model"
              value={model}
              onChange={(e) => setModel(e.target.value)}
              className="rounded-lg border border-panel-border bg-panel-light/60 px-2.5 py-1.5 text-sm text-ink-primary focus:border-cyan-accent/50 focus:outline-none"
            >
              {(config?.available_models ?? ['mock']).map((m) => (
                <option key={m} value={m}>
                  {m === 'local_hf' ? `local_hf (${config?.local_model_name ?? 'Qwen2.5-1.5B-Instruct'})` : m}
                </option>
              ))}
            </select>
          </div>

          <div className="flex flex-col gap-1">
            <label htmlFor="num-samples" className="text-xs text-ink-secondary">
              Samples ({numSamples})
            </label>
            <input
              id="num-samples"
              type="range"
              min={1}
              max={maxSamples}
              value={numSamples}
              onChange={(e) => setNumSamples(Number(e.target.value))}
              className="h-1.5 w-32 accent-cyan-accent"
            />
          </div>

          <label className="flex items-center gap-2 pb-1.5 text-xs text-ink-secondary">
            <input
              type="checkbox"
              checked={uncertaintyMode}
              onChange={(e) => setUncertaintyMode(e.target.checked)}
              className="h-3.5 w-3.5 accent-cyan-accent"
            />
            Uncertainty mode
          </label>

          <label
            className={`flex items-center gap-2 pb-1.5 text-xs ${isLocalModel ? 'text-ink-secondary' : 'text-ink-muted opacity-50'}`}
            title={isLocalModel ? undefined : 'Select the local_hf model to enable Research Mode'}
          >
            <input
              type="checkbox"
              checked={researchMode}
              disabled={!isLocalModel}
              onChange={(e) => setResearchMode(e.target.checked)}
              className="h-3.5 w-3.5 accent-violet-accent"
            />
            <Microscope size={13} strokeWidth={1.75} />
            Research mode
          </label>

          <button
            type="submit"
            disabled={loading || !query.trim()}
            className="ml-auto flex items-center gap-2 rounded-lg border border-cyan-accent/40 bg-cyan-faint px-4 py-2 text-sm font-medium text-cyan-accent transition-colors hover:bg-cyan-accent/20 disabled:cursor-not-allowed disabled:opacity-40"
          >
            {loading ? <Loader2 size={15} className="animate-spin" /> : <Send size={15} />}
            {loading ? 'Thinking…' : 'Submit'}
          </button>
        </div>
      </form>

      {error && (
        <div className="glass-panel flex items-center gap-3 border-status-warning/30 p-4 text-sm text-status-warning">
          <TriangleAlert size={18} className="shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Three-column layout */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <BrainVisualization
          regions={displayedRegions}
          mode={regionProfile?.measured ? 'measured' : regionProfile ? 'predicted' : undefined}
          pathway={result?.pathway}
          hallucinationRisk={result?.hallucination_risk.score}
        />

        {result ? (
          <CognitiveState state={result.cognitive_state} taskAnalysis={result.task_analysis} />
        ) : (
          <EmptyPanel label="Global Cognitive State" hint="Submit a query to populate cognitive-state meters." />
        )}

        {result ? (
          <NeuromodulationPanel signals={result.cognitive_state.neuromodulation} />
        ) : (
          <EmptyPanel label="Virtual Neuromodulation Layer" hint="Submit a query to populate neuromodulation signals." />
        )}
      </div>

      {/* Bottom: response and explainability and recommendations */}
      <AnimatePresence mode="wait">
        {result && (
          <motion.div
            key={result.answer.slice(0, 24)}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.3 }}
            className="grid grid-cols-1 gap-6 lg:grid-cols-3"
          >
            <div className="lg:col-span-2 flex flex-col gap-4">
              <ResponsePanel answer={result.answer} />
              {result.research ? (
                <div className="glass-panel p-4 text-xs text-ink-secondary">
                  <span className="font-medium text-ink-primary">Routing reason: </span>
                  {result.research.routing_reason}
                  {result.research.verifier_raw_text ? (
                    <div className="mt-2 rounded-lg border border-panel-border bg-panel-light/50 p-3">
                      <div className="section-label mb-1">Self-verifier output (model self-critique, not ground truth)</div>
                      <p className="whitespace-pre-wrap text-ink-secondary">{result.research.verifier_raw_text}</p>
                    </div>
                  ) : null}
                  {result.research.retrieval_sources.length > 0 ? (
                    <div className="mt-2 rounded-lg border border-violet-accent/20 bg-violet-faint p-3">
                      <div className="section-label mb-1 text-violet-accent">
                        Retrieval-grounded fact-check (real search evidence, not ground truth)
                      </div>
                      {result.research.retrieval_raw_text ? (
                        <p className="mb-2 whitespace-pre-wrap text-ink-secondary">{result.research.retrieval_raw_text}</p>
                      ) : null}
                      <div className="flex flex-col gap-1.5">
                        {result.research.retrieval_sources.map((s, i) => (
                          <a
                            key={i}
                            href={s.url}
                            target="_blank"
                            rel="noreferrer"
                            className="text-cyan-accent underline decoration-cyan-accent/30 underline-offset-2 hover:decoration-cyan-accent"
                          >
                            {s.title || s.url}
                          </a>
                        ))}
                      </div>
                    </div>
                  ) : null}
                  <div className="mt-2">
                    See{' '}
                    <Link to="/activation-explorer" className="text-cyan-accent underline decoration-cyan-accent/30 underline-offset-2">
                      Activation Explorer
                    </Link>{' '}
                    for layer-by-layer detail.
                  </div>
                </div>
              ) : null}
            </div>
            <RecommendationPanel recommendations={result.recommendations} />
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

function EmptyPanel({ label, hint }: { label: string; hint: string }) {
  return (
    <div className="glass-panel flex flex-col items-center justify-center gap-2 p-5 text-center">
      <h2 className="section-label">{label}</h2>
      <p className="text-xs text-ink-muted">{hint}</p>
    </div>
  )
}
