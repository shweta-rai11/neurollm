import type { ReactNode } from 'react'
import { BrainCircuit, FlaskConical, Microscope, ShieldAlert, Compass } from 'lucide-react'

function Section({
  icon: Icon,
  title,
  children,
}: {
  icon: typeof BrainCircuit
  title: string
  children: ReactNode
}) {
  return (
    <section className="glass-panel p-6">
      <div className="mb-3 flex items-center gap-2">
        <Icon size={17} strokeWidth={1.75} className="text-cyan-accent" />
        <h2 className="text-base font-semibold text-ink-primary">{title}</h2>
      </div>
      <div className="space-y-3 text-sm leading-relaxed text-ink-secondary">{children}</div>
    </section>
  )
}

export default function About() {
  return (
    <div className="flex flex-col gap-6">
      <div className="glass-panel p-8">
        <h1 className="text-xl font-semibold tracking-tight text-ink-primary">About NeuroLLM</h1>
        <p className="mt-3 max-w-2xl text-[15px] leading-relaxed text-ink-secondary">
          A neuroscience-inspired computational model that maps functional properties of an LLM's
          internal representations onto a virtual cognitive architecture.
        </p>
        <p className="mt-2 max-w-2xl text-sm leading-relaxed text-ink-muted">
          NeuroLLM inspects real hidden states, attention weights, and token logits from a local,
          open-weight model (Qwen2.5-1.5B-Instruct) while it answers a question, combines them with
          deterministic text heuristics, and routes the question through a small set of reasoning
          pathways - direct answer, analytical, creative, or verify-then-possibly-abstain - based on
          an estimated hallucination-risk score. Everything is visualized as an interactive "virtual
          brain."
        </p>
      </div>

      <Section icon={BrainCircuit} title="The metaphor, made explicit">
        <p>
          Every "region" name and "neuromodulator" name in this app is a{' '}
          <strong className="font-semibold text-ink-primary">functional / computational analogy</strong>, not a
          biological claim.
        </p>
        <p>
          NeuroLLM does <strong className="font-semibold text-ink-primary">not</strong> claim that this language
          model has brain regions, hemispheres, hormones, emotions, or consciousness. There is no
          "Language region" or "dopamine" inside the model - those labels stand in for measurable
          quantities (activation magnitude in a group of layers, token-probability margin, response
          consistency across samples, and so on) chosen because they're easier to read at a glance
          than a table of raw tensors. See the "How the numbers are produced" section below for
          exactly what each label maps to.
        </p>
      </Section>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <div className="rounded-xl border border-status-good/20 bg-status-good/5 p-5">
          <div className="section-label mb-2 text-status-good">Real, measured signals</div>
          <ul className="list-inside list-disc space-y-1.5 text-sm text-ink-secondary">
            <li>Per-layer hidden-state L2 norms and per-layer attention entropy, read from an actual forward pass through the local model.</li>
            <li>Per-token entropy and top1/top2 probability margin, read from the actual logits used to sample each generated token.</li>
            <li>Multi-sample response-consistency uncertainty (semantic-entropy-inspired, see Uncertainty Lab).</li>
            <li>A category probe (logistic regression / random forest / small MLP) trained on real activation features - see Question Lab and <code className="font-mono text-xs">docs/PROBE_RESULTS.md</code> for actual eval numbers, not projected ones.</li>
          </ul>
        </div>
        <div className="rounded-xl border border-cyan-accent/20 bg-cyan-faint p-5">
          <div className="section-label mb-2 text-cyan-accent">Designed metaphor / heuristic</div>
          <ul className="list-inside list-disc space-y-1.5 text-sm text-ink-secondary">
            <li>The five virtual "brain regions" (Language, Memory, Reasoning, Uncertainty, Verification) and their predicted/measured weighting formulas.</li>
            <li>The four "-like" neuromodulator signals (dopamine, serotonin, norepinephrine, acetylcholine) and how they adjust routing thresholds.</li>
            <li>The Hallucination Risk Score's weighting and the executive controller's pathway-selection thresholds.</li>
            <li>The Language ↔ early/mid-layer and Reasoning ↔ late-layer association is a documented design heuristic drawn from general interpretability observations - not a validated, per-layer finding for this specific model.</li>
          </ul>
        </div>
        <div className="rounded-xl border border-violet-accent/20 bg-violet-faint p-5">
          <div className="section-label mb-2 text-violet-accent">Open hypothesis</div>
          <ul className="list-inside list-disc space-y-1.5 text-sm text-ink-secondary">
            <li>Whether activation-informed routing and verification measurably improves reliability over direct generation, beyond this MVP's small benchmark (see Experiment Lab's Condition Comparison).</li>
            <li>Whether the probe's category predictions generalize beyond this project's ~50-item benchmark.</li>
            <li>Whether this style of visualization helps a person calibrate trust in an answer - untested here.</li>
          </ul>
        </div>
      </div>

      <Section icon={Microscope} title="How the numbers are produced">
        <p>
          A query is scored on nine task-analysis dimensions (complexity, ambiguity, risk, and so
          on) using deterministic text heuristics - this produces the <em>predicted</em> cognitive
          profile, before any model call. When the local model is selected, one generation pass
          captures real hidden states, attention weights, and logits; these are reduced to a bounded
          feature summary and combine with the heuristics (and, if enabled, multi-sample uncertainty)
          to produce the <em>measured</em> profile, a Hallucination Risk Score, and four "-like"
          neuromodulation signals. The executive controller compares the hallucination-risk score
          and region activations against a set of thresholds (adjusted by the neuromodulation
          signals) to pick a pathway: DIRECT, ANALYTICAL, CREATIVE, or VERIFY. VERIFY runs a
          self-consistency check plus a self-verification prompt, and - if risk stays high - wraps
          the answer in an explicit low-confidence framing instead of presenting it as settled.
        </p>
      </Section>

      <Section icon={Compass} title="Scope of this prototype">
        <p>
          This is the spec's five-region MVP, not the full research vision. Deliberately out of
          scope for this build (see <code className="font-mono text-xs">README.md</code>'s Future
          Work): a 3D Three.js visualization (this app uses a 2D SVG diagram instead), external
          retrieval/evidence pathways, PostgreSQL/WebSockets, mechanistic-interpretability tooling
          (Captum/TransformerLens/SAE), and the lateralization-index experiment. The Memory region's
          "measured" score currently inherits its "predicted" value verbatim because there is no
          retrieval pathway in this MVP to observe - that's a documented limitation, not a bug.
        </p>
      </Section>

      <Section icon={ShieldAlert} title="Limitations">
        <ul className="list-inside list-disc space-y-1.5">
          <li>
            The heuristic task-scoring and region-weighting formulas are{' '}
            <strong className="font-semibold text-ink-primary">not</strong> validated psychometric or
            neuroscientific instruments - they are hand-designed, documented rules.
          </li>
          <li>
            Consistency across sampled responses is <strong className="font-semibold text-ink-primary">not
            proof of correctness</strong> - a model can be confidently, consistently wrong.
          </li>
          <li>
            The self-verifier (used in the VERIFY pathway) is the same model critiquing its own
            candidates - a useful signal, but <strong className="font-semibold text-ink-primary">not
            ground-truth verification</strong>.
          </li>
          <li>
            The probe is trained on a small (~50-item) hand-authored benchmark - its reported
            accuracy demonstrates the methodology, not a validated classifier.
          </li>
          <li>
            When running against the mock provider, responses are synthetic and{' '}
            <strong className="font-semibold text-ink-primary">not real model outputs</strong>, and no
            "measured" activation profile is available.
          </li>
        </ul>
      </Section>

      <div className="glass-panel flex items-center gap-3 p-5">
        <FlaskConical size={16} strokeWidth={1.75} className="shrink-0 text-ink-muted" />
        <p className="text-xs leading-relaxed text-ink-muted">
          This is a research-lab-style instrument for exploring model behavior, not a clinical or
          safety-certified tool. Treat every signal here as a prompt to look closer, not as a final
          verdict.
        </p>
      </div>
    </div>
  )
}
