import { useEffect, useState } from 'react'
import { History as HistoryIcon, Loader2, TriangleAlert } from 'lucide-react'
import { Link } from 'react-router-dom'
import { getHistory } from '../services/api'
import type { HistoryItem } from '../types/cognitiveState'
import { truncate, formatTimestamp } from '../utils/format'
import { directSeverity, inverseSeverity, SEVERITY_TEXT_CLASS } from '../utils/colors'

function Badge({ value, invert }: { value: number; invert?: boolean }) {
  const severity = invert ? inverseSeverity(value) : directSeverity(value)
  return <span className={`font-mono text-sm font-semibold ${SEVERITY_TEXT_CLASS[severity]}`}>{value}%</span>
}

export default function History() {
  const [items, setItems] = useState<HistoryItem[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    getHistory()
      .then((res) => {
        if (!cancelled) setItems(res.items)
      })
      .catch((err) => {
        if (!cancelled) setError(err instanceof Error ? err.message : 'Failed to load history.')
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [])

  return (
    <div className="glass-panel p-6">
      <div className="mb-5 flex items-center gap-2">
        <HistoryIcon size={18} strokeWidth={1.75} className="text-cyan-accent" />
        <h1 className="text-lg font-semibold text-ink-primary">History</h1>
      </div>

      {loading ? (
        <div className="flex items-center gap-2 text-sm text-ink-muted">
          <Loader2 size={15} className="animate-spin" />
          Loading past analyses…
        </div>
      ) : error ? (
        <div className="flex items-center gap-2 text-sm text-status-warning">
          <TriangleAlert size={15} strokeWidth={1.75} />
          {error}
        </div>
      ) : !items || items.length === 0 ? (
        <p className="text-sm text-ink-muted">
          No analyses yet —{' '}
          <Link to="/" className="text-cyan-accent hover:underline">
            try the Dashboard
          </Link>
          .
        </p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full min-w-[860px] border-collapse text-sm">
            <thead>
              <tr className="border-b border-panel-border text-left text-xs uppercase tracking-wide text-ink-muted">
                <th className="py-2 pr-4 font-medium">Query</th>
                <th className="py-2 pr-4 font-medium">Model</th>
                <th className="py-2 pr-4 font-medium">Pathway</th>
                <th className="py-2 pr-4 font-medium">Timestamp</th>
                <th className="py-2 pr-4 font-medium">Confidence</th>
                <th className="py-2 pr-4 font-medium">Uncertainty</th>
                <th className="py-2 pr-4 font-medium">Difficulty</th>
                <th className="py-2 pr-4 font-medium">Hallucination risk</th>
              </tr>
            </thead>
            <tbody>
              {items.map((item) => (
                <tr key={item.id} className="border-b border-panel-border/60 last:border-0">
                  <td className="py-2.5 pr-4 text-ink-primary">{truncate(item.query, 70)}</td>
                  <td className="py-2.5 pr-4 font-mono text-xs text-ink-secondary">{item.model}</td>
                  <td className="py-2.5 pr-4 font-mono text-xs text-ink-secondary">{item.pathway}</td>
                  <td className="py-2.5 pr-4 whitespace-nowrap text-xs text-ink-muted">
                    {formatTimestamp(item.timestamp)}
                  </td>
                  <td className="py-2.5 pr-4">
                    <Badge value={item.confidence} />
                  </td>
                  <td className="py-2.5 pr-4">
                    <Badge value={item.uncertainty} invert />
                  </td>
                  <td className="py-2.5 pr-4">
                    <Badge value={item.difficulty} invert />
                  </td>
                  <td className="py-2.5 pr-4">
                    <Badge value={Math.round(item.hallucination_risk * 100)} invert />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
