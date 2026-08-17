import { NavLink } from 'react-router-dom'
import { Activity, FlaskConical, Gauge, History, Info, BrainCircuit, Microscope, Waves, Fingerprint } from 'lucide-react'

const NAV_ITEMS = [
  { to: '/', label: 'Dashboard', icon: Activity, end: true },
  { to: '/question-lab', label: 'Question Lab', icon: FlaskConical, end: false },
  { to: '/activation-explorer', label: 'Activation Explorer', icon: Waves, end: false },
  { to: '/experiment-lab', label: 'Experiment Lab', icon: Microscope, end: false },
  { to: '/uncertainty-lab', label: 'Uncertainty Lab', icon: Gauge, end: false },
  { to: '/fingerprint-detection', label: 'Fingerprint Detection', icon: Fingerprint, end: false },
  { to: '/profile', label: 'Cognitive Profile', icon: Fingerprint, end: false },
  { to: '/history', label: 'History', icon: History, end: false },
  { to: '/about', label: 'About', icon: Info, end: false },
]

export default function Header() {
  return (
    <header className="sticky top-0 z-40 border-b border-panel-border bg-void/85 backdrop-blur-md">
      <div className="mx-auto flex h-16 max-w-[1600px] items-center justify-between gap-6 px-6">
        <div className="flex items-center gap-3">
          <span className="flex h-9 w-9 items-center justify-center rounded-lg border border-cyan-accent/30 bg-cyan-faint text-cyan-accent">
            <BrainCircuit size={20} strokeWidth={1.75} />
          </span>
          <div className="leading-tight">
            <div className="font-mono text-sm font-semibold tracking-wide text-ink-primary">
              NEUROLLM
            </div>
            <div className="text-[11px] text-ink-muted">Virtual Cognitive Brain</div>
          </div>
        </div>

        <nav className="flex items-center gap-1">
          {NAV_ITEMS.map(({ to, label, icon: Icon, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              className={({ isActive }) =>
                [
                  'flex items-center gap-2 rounded-lg px-3 py-2 text-sm transition-colors',
                  isActive
                    ? 'bg-cyan-faint text-cyan-accent'
                    : 'text-ink-secondary hover:bg-panel-light hover:text-ink-primary',
                ].join(' ')
              }
            >
              <Icon size={15} strokeWidth={1.75} />
              <span className="hidden xl:inline">{label}</span>
            </NavLink>
          ))}
        </nav>
      </div>
    </header>
  )
}
