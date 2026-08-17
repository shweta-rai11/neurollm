import { useState } from 'react'
import { HelpCircle, ChevronDown } from 'lucide-react'
import type { ProfileInfluence } from '../../types/profile'

/** The "Why this brain state?" panel (product spec section 11) — collapsed
 * by default behind an Explain button, matching the spec's click-to-reveal
 * interaction rather than always-on clutter. */
export default function ExplainPanel({ influence }: { influence: ProfileInfluence }) {
  const [open, setOpen] = useState(false)

  return (
    <div className="glass-panel p-6">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center justify-between gap-2 text-left"
      >
        <span className="flex items-center gap-2">
          <HelpCircle size={16} strokeWidth={1.75} className="text-cyan-accent" />
          <h2 className="section-label">Explain</h2>
        </span>
        <ChevronDown size={16} className={`text-ink-muted transition-transform ${open ? 'rotate-180' : ''}`} />
      </button>

      {open ? (
        <div className="mt-4 flex flex-col gap-4">
          {influence.explanation.map((entry) => (
            <div key={entry.question}>
              <p className="text-sm font-medium text-ink-primary">{entry.question}</p>
              <p className="mt-1 text-xs leading-relaxed text-ink-secondary">{entry.answer}</p>
            </div>
          ))}
          <div className="rounded-lg border border-status-warning/25 bg-status-warning/10 px-3 py-2 text-[11px] font-medium leading-relaxed text-status-warning">
            {influence.disclaimer}
          </div>
        </div>
      ) : null}
    </div>
  )
}
