import { Bar, BarChart, Cell, ResponsiveContainer, XAxis, YAxis, Tooltip } from 'recharts'
import type { ChatResponse, ExperimentSide, RegionScores } from '../../types/cognitiveState'
import { REGION_COLORS, PATHWAY_COLORS, directSeverity, inverseSeverity, SEVERITY_TEXT_CLASS } from '../../utils/colors'
import { truncate } from '../../utils/format'

const REGION_LABELS: Record<keyof RegionScores, string> = {
  language: 'Language',
  memory: 'Memory',
  reasoning: 'Reasoning',
  uncertainty: 'Uncertainty',
  verification: 'Verification',
}

const REGION_ORDER: (keyof RegionScores)[] = ['language', 'memory', 'reasoning', 'uncertainty', 'verification']

/**
 * A ChatResponse and an ExperimentSide (the /experiment endpoint's per-side
 * payload) both carry the fields this card needs — answer, cognitive_state,
 * task_analysis, pathway, hallucination_risk — so either is accepted
 * structurally.
 */
type ExperimentCardResponse = ChatResponse | ExperimentSide

interface ExperimentCardProps {
  label: string
  query: string
  response: ExperimentCardResponse | null
  loading?: boolean
}

function Skeleton() {
  return (
    <div className="animate-pulse space-y-4">
      <div className="h-3 w-2/3 rounded bg-panel-light" />
      <div className="h-32 rounded bg-panel-light" />
      <div className="grid grid-cols-4 gap-2">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="h-12 rounded bg-panel-light" />
        ))}
      </div>
      <div className="h-20 rounded bg-panel-light" />
    </div>
  )
}

export default function ExperimentCard({ label, query, response, loading }: ExperimentCardProps) {
  const regionProfile = response ? response.cognitive_state.brain_regions.measured ?? response.cognitive_state.brain_regions.predicted : null
  const chartData = regionProfile
    ? REGION_ORDER.map((key) => ({
        key,
        label: REGION_LABELS[key],
        value: regionProfile[key],
      }))
    : []

  const gs = response?.cognitive_state.global_state

  return (
    <div className="glass-panel flex h-full flex-col p-6">
      <div className="mb-3 flex items-center justify-between">
        <span className="badge border-cyan-accent/25 bg-cyan-faint text-cyan-accent">
          Side {label}
        </span>
        {response ? (
          <span
            className="badge"
            style={{
              borderColor: `${PATHWAY_COLORS[response.pathway]}40`,
              backgroundColor: `${PATHWAY_COLORS[response.pathway]}14`,
              color: PATHWAY_COLORS[response.pathway],
            }}
          >
            {response.pathway}
          </span>
        ) : null}
      </div>

      <p className="mb-4 text-sm italic leading-snug text-ink-secondary">
        {query ? `"${truncate(query, 140)}"` : 'No query entered yet.'}
      </p>

      {loading ? (
        <Skeleton />
      ) : !response ? (
        <p className="text-sm text-ink-muted">Run the experiment to see results.</p>
      ) : (
        <div className="flex flex-1 flex-col gap-4">
          <div>
            <div className="section-label mb-1.5">
              Brain-region activation {response.cognitive_state.brain_regions.measured ? '(measured)' : '(predicted)'}
            </div>
            <div className="h-40 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={chartData} layout="vertical" margin={{ left: 4, right: 12, top: 2, bottom: 2 }}>
                  <XAxis type="number" domain={[0, 100]} hide />
                  <YAxis
                    type="category"
                    dataKey="label"
                    width={78}
                    tickLine={false}
                    axisLine={false}
                    tick={{ fill: '#9aa7b8', fontSize: 11 }}
                  />
                  <Tooltip
                    cursor={{ fill: 'rgba(148,163,184,0.06)' }}
                    contentStyle={{
                      background: '#10151d',
                      border: '1px solid rgba(148,163,184,0.12)',
                      borderRadius: 8,
                      fontSize: 12,
                    }}
                    labelStyle={{ color: '#e6edf3' }}
                    itemStyle={{ color: '#9aa7b8' }}
                    formatter={(value: number) => [`${value}%`, 'Activation']}
                  />
                  <Bar dataKey="value" radius={[0, 4, 4, 0]} maxBarSize={14}>
                    {chartData.map((entry) => (
                      <Cell key={entry.key} fill={REGION_COLORS[entry.key]} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          {gs ? (
            <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
              <MiniStat label="Confidence" value={gs.confidence} severity={directSeverity(gs.confidence)} />
              <MiniStat label="Uncertainty" value={gs.uncertainty} severity={inverseSeverity(gs.uncertainty)} />
              <MiniStat label="Difficulty" value={gs.difficulty} severity={inverseSeverity(gs.difficulty)} />
              <MiniStat
                label="Hallucination risk"
                value={Math.round(response.hallucination_risk.score * 100)}
                severity={inverseSeverity(response.hallucination_risk.score * 100)}
              />
            </div>
          ) : null}

          <div className="flex-1 rounded-lg border border-panel-border bg-panel-light/50 p-3">
            <div className="section-label mb-1.5">Answer</div>
            <p className="max-h-40 overflow-y-auto whitespace-pre-wrap break-words text-xs leading-relaxed text-ink-secondary">
              {response.answer || 'No response text available.'}
            </p>
          </div>
        </div>
      )}
    </div>
  )
}

function MiniStat({
  label,
  value,
  severity,
}: {
  label: string
  value: number
  severity: keyof typeof SEVERITY_TEXT_CLASS
}) {
  return (
    <div className="rounded-md border border-panel-border bg-panel-light/60 px-2 py-1.5 text-center">
      <div className="text-[10px] uppercase tracking-wide text-ink-muted">{label}</div>
      <div className={`font-mono text-sm font-semibold ${SEVERITY_TEXT_CLASS[severity]}`}>{value}%</div>
    </div>
  )
}
