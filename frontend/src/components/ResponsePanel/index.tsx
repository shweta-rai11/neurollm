import { MessageSquareText } from 'lucide-react'

interface ResponsePanelProps {
  answer: string
}

/** Clean readable block for the model's final answer text. */
export default function ResponsePanel({ answer }: ResponsePanelProps) {
  const hasAnswer = typeof answer === 'string' && answer.trim().length > 0

  return (
    <div className="glass-panel p-6">
      <div className="mb-4 flex items-center gap-2">
        <MessageSquareText size={16} strokeWidth={1.75} className="text-cyan-accent" />
        <h2 className="section-label">AI Response</h2>
      </div>
      {hasAnswer ? (
        <p className="whitespace-pre-wrap break-words text-[15px] leading-relaxed text-ink-primary">
          {answer}
        </p>
      ) : (
        <p className="text-sm text-ink-muted">No response text available.</p>
      )}
    </div>
  )
}
