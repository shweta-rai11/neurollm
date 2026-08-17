import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { TrendingUp, Fingerprint, Loader2 } from 'lucide-react'
import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { getProfileEvolution } from '../../services/api'
import { useProfileId } from '../../hooks/useProfileId'
import { PROFILE_PARAM_NAMES } from '../../types/profile'
import type { EvolutionResponse } from '../../types/profile'

function paramLabel(name: string): string {
  return name.replace(/_/g, ' ')
}

export default function Evolution() {
  const { profileId } = useProfileId()
  const [data, setData] = useState<EvolutionResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!profileId) return
    setLoading(true)
    getProfileEvolution(profileId)
      .then(setData)
      .catch((err) => setError(err instanceof Error ? err.message : 'Failed to load evolution history.'))
      .finally(() => setLoading(false))
  }, [profileId])

  if (!profileId) {
    return (
      <div className="glass-panel flex flex-col items-center gap-4 p-10 text-center">
        <Fingerprint size={32} className="text-ink-muted" />
        <p className="text-sm text-ink-secondary">No Individual Computational Profile loaded yet.</p>
        <Link to="/profile/enroll" className="rounded-lg border border-cyan-accent/40 bg-cyan-faint px-4 py-2 text-sm font-medium text-cyan-accent hover:bg-cyan-accent/20">
          Scan fingerprint
        </Link>
      </div>
    )
  }

  const chartData = data
    ? PROFILE_PARAM_NAMES.map((name) => ({
        label: paramLabel(name),
        Initial: Math.round(data.initial[name] * 100),
        Current: Math.round(data.current[name] * 100),
      }))
    : []

  return (
    <div className="flex flex-col gap-6">
      <div className="glass-panel p-6">
        <div className="mb-1 flex items-center gap-2">
          <TrendingUp size={18} strokeWidth={1.75} className="text-cyan-accent" />
          <h1 className="text-lg font-semibold text-ink-primary">Profile Evolution</h1>
        </div>
        <p className="text-sm text-ink-secondary">
          {data ? `${data.n_interactions} recorded interaction${data.n_interactions === 1 ? '' : 's'}. ` : ''}
          {data?.note}
        </p>
      </div>

      {loading ? (
        <div className="glass-panel flex items-center justify-center gap-2 p-10 text-sm text-ink-muted">
          <Loader2 size={16} className="animate-spin" /> Loading…
        </div>
      ) : error ? (
        <p className="text-sm text-status-warning">{error}</p>
      ) : data ? (
        <>
          <div className="glass-panel p-6">
            <div className="section-label mb-4">Initial vs. Current</div>
            <div className="h-72 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={chartData} margin={{ left: 0, right: 12, top: 4, bottom: 4 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.08)" vertical={false} />
                  <XAxis dataKey="label" tickLine={false} axisLine={false} tick={{ fill: '#9aa7b8', fontSize: 10 }} interval={0} angle={-20} textAnchor="end" height={60} />
                  <YAxis domain={[0, 100]} tickLine={false} axisLine={false} tick={{ fill: '#9aa7b8', fontSize: 11 }} />
                  <Tooltip
                    cursor={{ fill: 'rgba(148,163,184,0.06)' }}
                    contentStyle={{ background: '#10151d', border: '1px solid rgba(148,163,184,0.12)', borderRadius: 8, fontSize: 12 }}
                    labelStyle={{ color: '#e6edf3' }}
                  />
                  <Legend wrapperStyle={{ fontSize: 12 }} />
                  <Bar dataKey="Initial" fill="#38bdf8" radius={[4, 4, 0, 0]} maxBarSize={22} />
                  <Bar dataKey="Current" fill="#a78bfa" radius={[4, 4, 0, 0]} maxBarSize={22} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          {Object.keys(data.task_profiles).length > 0 ? (
            <div className="glass-panel overflow-x-auto p-6">
              <div className="section-label mb-4">Task-specific profiles</div>
              <table className="w-full min-w-[640px] text-left text-xs">
                <thead>
                  <tr className="border-b border-panel-border text-ink-muted">
                    <th className="py-2 pr-4 font-medium">Category</th>
                    {PROFILE_PARAM_NAMES.map((name) => (
                      <th key={name} className="py-2 pr-4 font-medium">
                        {paramLabel(name)}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(data.task_profiles).map(([category, params]) => (
                    <tr key={category} className="border-b border-panel-border/50">
                      <td className="py-2 pr-4 text-ink-primary">{category.replace(/_/g, ' ')}</td>
                      {PROFILE_PARAM_NAMES.map((name) => (
                        <td key={name} className="py-2 pr-4 font-mono text-ink-secondary">
                          {params[name].toFixed(2)}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="text-sm text-ink-muted">No task-specific profiles yet - ask a few questions from the Overview tab.</p>
          )}
        </>
      ) : null}
    </div>
  )
}
