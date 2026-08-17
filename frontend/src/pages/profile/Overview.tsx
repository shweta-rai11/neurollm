import { useEffect, useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { Loader2, Send, ShieldCheck, UserCircle2, Fingerprint } from 'lucide-react'
import { chat, getConfig } from '../../services/api'
import { useProfileId } from '../../hooks/useProfileId'
import ResponsePanel from '../../components/ResponsePanel'
import NeuromodulationPanel from '../../components/NeuromodulationPanel'
import ActivatedSystemsPanel from '../../components/profile/ActivatedSystemsPanel'
import EndocrinePanel from '../../components/profile/EndocrinePanel'
import ExplainPanel from '../../components/profile/ExplainPanel'
import PipelineDiagram from '../../components/profile/PipelineDiagram'
import type { ChatResponse, ConfigResponse } from '../../types/cognitiveState'

export default function Overview() {
  const { profileId } = useProfileId()
  const [model, setModel] = useState('mock')
  const [models, setModels] = useState<string[]>(['mock'])
  const [query, setQuery] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<ChatResponse | null>(null)

  useEffect(() => {
    getConfig()
      .then((cfg: ConfigResponse) => setModels(cfg.available_models.length ? cfg.available_models : ['mock']))
      .catch(() => {})
  }, [])

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    if (!query.trim() || !profileId) return
    setLoading(true)
    setError(null)
    try {
      const res = await chat({ query: query.trim(), model, uncertainty_mode: true, num_samples: 4, profile_id: profileId })
      setResult(res)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Request failed.')
      setResult(null)
    } finally {
      setLoading(false)
    }
  }

  if (!profileId) {
    return (
      <div className="glass-panel flex flex-col items-center gap-4 p-10 text-center">
        <Fingerprint size={32} className="text-ink-muted" />
        <p className="text-sm text-ink-secondary">No Individual Computational Profile loaded yet.</p>
        <Link
          to="/profile/enroll"
          className="rounded-lg border border-cyan-accent/40 bg-cyan-faint px-4 py-2 text-sm font-medium text-cyan-accent hover:bg-cyan-accent/20"
        >
          Scan fingerprint
        </Link>
      </div>
    )
  }

  const influence = result?.profile_influence ?? null

  return (
    <div className="flex flex-col gap-6">
      <div className="glass-panel flex flex-wrap items-center gap-6 p-5">
        <span className="flex items-center gap-2 text-sm">
          <ShieldCheck size={16} className="text-status-good" />
          Biometric identity <span className="font-semibold text-status-good">Verified</span>
        </span>
        <span className="flex items-center gap-2 text-sm">
          <UserCircle2 size={16} className="text-status-good" />
          Computational profile <span className="font-semibold text-status-good">Loaded</span>
        </span>
        <span className="ml-auto font-mono text-[11px] text-ink-muted">profile_id: {profileId.slice(0, 8)}…</span>
      </div>

      <form onSubmit={handleSubmit} className="glass-panel flex flex-col gap-4 p-5">
        <label className="section-label" htmlFor="overview-query">
          Current task
        </label>
        <textarea
          id="overview-query"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          rows={3}
          placeholder="Ask a question — your profile personalizes how it's routed…"
          className="w-full resize-none rounded-lg border border-panel-border bg-panel-light/60 px-3 py-2 text-sm text-ink-primary placeholder:text-ink-muted focus:border-cyan-accent/50 focus:outline-none"
        />
        <div className="flex items-end gap-4">
          <div>
            <label className="text-xs text-ink-secondary">Model</label>
            <select
              value={model}
              onChange={(e) => setModel(e.target.value)}
              className="mt-1 block rounded-lg border border-panel-border bg-panel-light/60 px-2.5 py-1.5 text-sm text-ink-primary focus:border-cyan-accent/50 focus:outline-none"
            >
              {models.map((m) => (
                <option key={m} value={m}>
                  {m}
                </option>
              ))}
            </select>
          </div>
          <button
            type="submit"
            disabled={loading || !query.trim()}
            className="ml-auto flex items-center gap-2 rounded-lg border border-cyan-accent/40 bg-cyan-faint px-4 py-2 text-sm font-medium text-cyan-accent transition-colors hover:bg-cyan-accent/20 disabled:cursor-not-allowed disabled:opacity-40"
          >
            {loading ? <Loader2 size={15} className="animate-spin" /> : <Send size={15} />}
            Ask
          </button>
        </div>
        {error ? <p className="text-sm text-status-warning">{error}</p> : null}
      </form>

      {result ? (
        <>
          <ResponsePanel answer={result.answer} />
          <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
            <ActivatedSystemsPanel
              regions={result.cognitive_state.brain_regions.measured ?? result.cognitive_state.brain_regions.predicted}
              taskCategory={influence?.task_category ?? 'ambiguous'}
              candidateSystems={influence?.candidate_systems ?? []}
            />
            <div className="flex flex-col gap-6">
              <NeuromodulationPanel signals={result.cognitive_state.neuromodulation} />
              <EndocrinePanel neuromodulation={result.cognitive_state.neuromodulation} taskCategory={influence?.task_category ?? 'ambiguous'} />
            </div>
          </div>
          {influence ? <ExplainPanel influence={influence} /> : null}
        </>
      ) : null}

      <PipelineDiagram />
    </div>
  )
}
