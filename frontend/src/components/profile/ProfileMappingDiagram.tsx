import { Fingerprint, ArrowRight, BrainCircuit } from 'lucide-react'

/**
 * Fingerprint -> "Personalization mapping" -> Virtual brain. The arrow label
 * is deliberately NOT "biological brain mapping" -- the fingerprint personalizes
 * computational parameters, it does not map to biology (see product spec
 * section 12 / README Positioning).
 */
export default function ProfileMappingDiagram() {
  return (
    <div className="glass-panel flex flex-col items-center gap-4 p-6 sm:flex-row sm:justify-center sm:gap-6">
      <div className="flex flex-col items-center gap-2 rounded-xl border border-panel-border bg-panel-light/60 px-6 py-5">
        <Fingerprint size={32} strokeWidth={1.5} className="text-cyan-accent" />
        <span className="section-label">Fingerprint</span>
        <span className="text-[11px] text-ink-muted">biometric representation</span>
      </div>

      <div className="flex flex-col items-center gap-1 text-ink-muted">
        <ArrowRight size={20} strokeWidth={1.75} className="rotate-90 sm:rotate-0" />
        <span className="text-center text-[10px] font-medium uppercase tracking-wide text-cyan-accent">
          Personalization
          <br />
          mapping
        </span>
      </div>

      <div className="flex flex-col items-center gap-2 rounded-xl border border-panel-border bg-panel-light/60 px-6 py-5">
        <BrainCircuit size={32} strokeWidth={1.5} className="text-violet-accent" />
        <span className="section-label">Virtual Brain</span>
        <span className="text-[11px] text-ink-muted">computational state</span>
      </div>
    </div>
  )
}
