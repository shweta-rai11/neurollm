import {
  Fingerprint,
  ScanLine,
  UserCircle2,
  MessageSquareText,
  Tags,
  BrainCircuit,
  Network,
  FlaskConical,
  Activity,
  ShieldCheck,
  CheckCircle2,
  type LucideIcon,
} from 'lucide-react'

interface Step {
  icon: LucideIcon
  title: string
  detail: string
  branch?: 'identity' | 'task' | 'merge'
}

const STEPS: Step[] = [
  { icon: Fingerprint, title: 'Fingerprint', detail: 'Image upload or camera capture', branch: 'identity' },
  { icon: ScanLine, title: 'Biometric features', detail: 'Ridge/minutiae template — never the raw image', branch: 'identity' },
  { icon: UserCircle2, title: 'Individual Computational Profile', detail: 'Identity lookup + learned parameters', branch: 'identity' },
  { icon: MessageSquareText, title: 'Question', detail: 'What you actually asked', branch: 'task' },
  { icon: Tags, title: 'Task classifier', detail: 'Which cognitive task is this?', branch: 'task' },
  { icon: BrainCircuit, title: 'Virtual brain state generator', detail: 'Profile + task combine here', branch: 'merge' },
  { icon: Network, title: 'Neural pathways', detail: 'Candidate virtual systems activate' },
  { icon: FlaskConical, title: 'Neurotransmitter + hormone layer', detail: 'Simulated neuromodulation/endocrine signals' },
  { icon: Activity, title: 'Cognitive state', detail: 'Assembled state passed to the model' },
  { icon: ShieldCheck, title: 'Verification', detail: 'Self-consistency + self-verification when warranted' },
  { icon: CheckCircle2, title: 'Final answer', detail: 'Delivered with its routing shown, not hidden' },
]

export default function PipelineDiagram() {
  return (
    <div className="glass-panel p-6">
      <h2 className="section-label mb-4">How your profile influences the virtual brain</h2>
      <ol className="relative ml-3 flex flex-col gap-5 border-l border-panel-border pl-6">
        {STEPS.map((step, i) => {
          const Icon = step.icon
          return (
            <li key={step.title} className="relative">
              <span className="absolute -left-[31px] flex h-6 w-6 items-center justify-center rounded-full border border-panel-border bg-panel text-cyan-accent">
                <Icon size={13} strokeWidth={1.75} />
              </span>
              <div className="flex flex-wrap items-baseline gap-2">
                <span className="text-sm font-medium text-ink-primary">{step.title}</span>
                {step.branch === 'merge' && i > 0 ? (
                  <span className="badge border-violet-accent/30 bg-violet-faint text-[10px] text-violet-accent">
                    merge point
                  </span>
                ) : null}
              </div>
              <p className="mt-0.5 text-xs text-ink-muted">{step.detail}</p>
            </li>
          )
        })}
      </ol>
      <p className="mt-5 rounded-lg border border-panel-border bg-panel-light/50 px-3 py-2 text-[11px] leading-relaxed text-ink-muted">
        Two separate inputs (fingerprint-derived identity, and the question's task classification) only combine at the
        "virtual brain state generator" step. The fingerprint never determines which virtual systems activate — the
        question does that; the profile only nudges parameters within them.
      </p>
    </div>
  )
}
