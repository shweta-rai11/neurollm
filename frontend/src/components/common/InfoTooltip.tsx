import { useState } from 'react'
import { Info } from 'lucide-react'

/**
 * Small info-icon affordance that reveals an explanatory tooltip on hover
 * (desktop) or tap (touch/keyboard). Used to attach the mandatory
 * "this is not a biological measurement" disclaimer to every hormone meter.
 */
export default function InfoTooltip({ text }: { text: string }) {
  const [open, setOpen] = useState(false)
  return (
    <span
      className="group relative inline-flex items-center"
      onMouseEnter={() => setOpen(true)}
      onMouseLeave={() => setOpen(false)}
    >
      <button
        type="button"
        aria-label="More information"
        onClick={() => setOpen((v) => !v)}
        className="flex h-4 w-4 items-center justify-center rounded-full text-ink-muted transition-colors hover:text-cyan-accent focus:outline-none focus-visible:text-cyan-accent"
      >
        <Info size={13} strokeWidth={1.75} />
      </button>
      {open ? (
        <span
          role="tooltip"
          className="absolute bottom-full left-1/2 z-50 mb-2 w-56 -translate-x-1/2 rounded-lg border border-panel-border bg-panel-light p-2.5 text-xs font-normal leading-snug text-ink-secondary shadow-glass"
        >
          {text}
          <span className="absolute left-1/2 top-full h-2 w-2 -translate-x-1/2 -translate-y-1/2 rotate-45 border-b border-r border-panel-border bg-panel-light" />
        </span>
      ) : null}
    </span>
  )
}
