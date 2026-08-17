import { NavLink, Outlet } from 'react-router-dom'
import { Fingerprint, LayoutDashboard, TrendingUp, SlidersHorizontal, Microscope, ShieldCheck } from 'lucide-react'

const TABS = [
  { to: '/profile/enroll', label: 'Enroll', icon: Fingerprint },
  { to: '/profile', label: 'Overview', icon: LayoutDashboard, end: true },
  { to: '/profile/evolution', label: 'Evolution', icon: TrendingUp },
  { to: '/profile/counterfactual', label: 'Counterfactual', icon: SlidersHorizontal },
  { to: '/profile/research', label: 'Research', icon: Microscope },
  { to: '/profile/privacy', label: 'Privacy', icon: ShieldCheck },
]

/** Local tab bar for the /profile/* hub — kept off the main top nav (see
 * Header.tsx) so the primary navigation doesn't overflow with 5 sub-pages. */
export default function ProfileLayout() {
  return (
    <div className="flex flex-col gap-6">
      <div className="glass-panel flex items-start gap-3 border-cyan-accent/20 p-4">
        <Fingerprint size={18} className="mt-0.5 shrink-0 text-cyan-accent" />
        <p className="text-xs leading-relaxed text-ink-secondary">
          <span className="font-medium text-ink-primary">Individual Computational Profile:</span> a fingerprint
          establishes a personalization key; a separately-learned set of computational parameters (never inferred
          from ridge morphology) personalizes the virtual brain's routing. See{' '}
          <NavLink to="/profile/privacy" className="text-cyan-accent underline decoration-cyan-accent/30 underline-offset-2">
            Privacy
          </NavLink>{' '}
          for how your data is handled.
        </p>
      </div>

      <nav className="flex flex-wrap gap-1 border-b border-panel-border pb-1">
        {TABS.map(({ to, label, icon: Icon, end }) => (
          <NavLink
            key={to}
            to={to}
            end={end}
            className={({ isActive }) =>
              [
                'flex items-center gap-1.5 rounded-t-lg border-b-2 px-3 py-2 text-sm transition-colors',
                isActive
                  ? 'border-cyan-accent text-cyan-accent'
                  : 'border-transparent text-ink-secondary hover:text-ink-primary',
              ].join(' ')
            }
          >
            <Icon size={14} strokeWidth={1.75} />
            {label}
          </NavLink>
        ))}
      </nav>

      <Outlet />
    </div>
  )
}
