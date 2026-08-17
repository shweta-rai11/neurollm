"""Deterministic task-characterization heuristics.

This module estimates task characteristics (complexity, reasoning demand,
creativity, planning, context-dependence, verification/factuality needs,
risk, and ambiguity) directly from the text of a user query.

Design intent (see README section "Scientific Integrity"):
    - The scoring here is a deterministic, reproducible heuristic layer.
      It is NOT a claim about what the downstream LLM is "thinking."
    - An optional lightweight LLM classifier can be layered on top later
      (see `llm_assist` hook) but the deterministic layer must always be
      able to produce a result on its own so the app is reproducible and
      works without any API key.

The heuristics are intentionally simple (keyword / structural signals,
normalized into 0-100 bands) rather than a trained classifier. They are a
starting point for a rule-based cognitive simulation (see roadmap V1) and
are documented as such -- not presented as validated psychometrics.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.models.schemas import TaskAnalysis

_CODE_KEYWORDS = [
    "function", "algorithm", "python", "javascript", "typescript", "code",
    "program", "class ", "def ", "implement", "compile", "debug", "regex",
    "sql", "api", "recursion", "linked list", "array", "sort", "loop",
    "variable", "syntax", "compiler", "runtime", "big-o", "complexity of",
]

_MATH_KEYWORDS = [
    "equation", "derivative", "integral", "matrix", "probability", "theorem",
    "proof", "calculate", "solve for", "differential", "algebra", "geometry",
    "statistics", "vector", "eigenvalue", "sum of", "optimi",
]

_STRUCTURED_REASONING_KEYWORDS = [
    "step by step", "step-by-step", "explain why", "logically", "prove",
    "analyze", "compare and contrast", "evaluate", "reasoning", "because",
    "therefore", "if...then", "cause of",
]

_CREATIVITY_KEYWORDS = [
    "brainstorm", "creative", "idea", "ideas", "poem", "story", "invent",
    "imagine", "design a", "novel", "startup idea", "name for", "slogan",
    "write a song", "metaphor", "fictional", "generate five", "generate 5",
    "alternative", "concept for",
]

_PLANNING_KEYWORDS = [
    "plan", "roadmap", "step 1", "steps to", "strategy", "milestones",
    "timeline", "workflow", "outline", "phases", "how do i approach",
    "break down", "project plan",
]

_CONTEXT_KEYWORDS = [
    "this document", "the paper", "attached", "above", "previous message",
    "earlier you said", "based on the following", "given the context",
    "this conversation", "the file", "as discussed",
]

_VERIFICATION_KEYWORDS = [
    "is it true", "fact check", "source", "cite", "citation", "evidence",
    "accurate", "who discovered", "when did", "what year", "statistics show",
    "according to", "verify", "reference",
]

_RISK_KEYWORDS = [
    "medical", "diagnos", "treatment", "legal advice", "invest", "financial",
    "dosage", "medication", "suicide", "self-harm", "weapon", "hack",
    "exploit", "vulnerability", "election", "vote for", "who will win",
    "predict the future", "should i buy", "surgery",
]

_AMBIGUITY_KEYWORDS = [
    "best", "better", "should i", "which one", "recommend", "optimal",
    "the right", "correct way", "ideal", "what's the best",
]

_FACTUALITY_KEYWORDS = [
    "who", "when", "what year", "how many", "where is", "capital of",
    "discovered", "invented", "founded", "population of", "born in",
    "fact", "history of",
]


def _keyword_score(text: str, keywords: list[str]) -> float:
    """Fraction-based keyword hit score in [0, 1]."""
    lowered = text.lower()
    hits = sum(1 for kw in keywords if kw in lowered)
    if hits == 0:
        return 0.0
    # Diminishing returns: 1 hit -> 0.45, 2 -> 0.7, 3 -> 0.85, 4+ -> ~0.95+
    return min(1.0, 1 - (0.55 ** hits))


def _length_signal(text: str) -> float:
    """Longer, multi-sentence queries tend to carry more complexity/planning."""
    n_words = len(text.split())
    n_sentences = max(1, len(re.split(r"[.!?]+", text.strip())) - 1) or 1
    word_signal = min(1.0, n_words / 120.0)
    sentence_signal = min(1.0, n_sentences / 6.0)
    return 0.6 * word_signal + 0.4 * sentence_signal


def _step_count_signal(text: str) -> float:
    """Detects enumerations / multi-step structure ("1.", "first, then, finally")."""
    numbered = len(re.findall(r"(?m)^\s*\d+[\.\)]", text))
    sequence_words = len(re.findall(r"\b(first|then|next|after that|finally|second|third)\b", text.lower()))
    raw = numbered + sequence_words
    return min(1.0, raw / 4.0)


def _to_100(x: float) -> int:
    return int(round(max(0.0, min(1.0, x)) * 100))


@dataclass
class _RawSignals:
    logical_reasoning: float = 0.0
    creativity: float = 0.0
    planning: float = 0.0
    context_dependency: float = 0.0
    verification_requirement: float = 0.0
    risk: float = 0.0
    ambiguity: float = 0.0
    factuality_requirement: float = 0.0
    complexity: float = 0.0
    details: dict = field(default_factory=dict)


def _compute_raw_signals(query: str) -> _RawSignals:
    coding = _keyword_score(query, _CODE_KEYWORDS)
    math_ = _keyword_score(query, _MATH_KEYWORDS)
    structured = _keyword_score(query, _STRUCTURED_REASONING_KEYWORDS)
    logical_reasoning = max(coding, math_, structured) * 0.6 + (coding + math_ + structured) / 3 * 0.4

    creativity = _keyword_score(query, _CREATIVITY_KEYWORDS)

    planning_kw = _keyword_score(query, _PLANNING_KEYWORDS)
    step_signal = _step_count_signal(query)
    planning = max(planning_kw, step_signal * 0.8)

    context_dependency = _keyword_score(query, _CONTEXT_KEYWORDS)

    verification_kw = _keyword_score(query, _VERIFICATION_KEYWORDS)
    factuality = _keyword_score(query, _FACTUALITY_KEYWORDS)
    verification_requirement = max(verification_kw, factuality * 0.7)

    risk = _keyword_score(query, _RISK_KEYWORDS)
    ambiguity = _keyword_score(query, _AMBIGUITY_KEYWORDS)

    length_signal = _length_signal(query)
    complexity = (
        0.30 * logical_reasoning
        + 0.20 * planning
        + 0.15 * length_signal
        + 0.15 * step_signal
        + 0.10 * context_dependency
        + 0.10 * max(coding, math_)
    )

    return _RawSignals(
        logical_reasoning=logical_reasoning,
        creativity=creativity,
        planning=planning,
        context_dependency=context_dependency,
        verification_requirement=verification_requirement,
        risk=risk,
        ambiguity=ambiguity,
        factuality_requirement=factuality,
        complexity=complexity,
        details={
            "coding_score": coding,
            "mathematical_score": math_,
            "structured_reasoning_score": structured,
            "length_signal": length_signal,
            "step_signal": step_signal,
        },
    )


def analyze_task(query: str) -> TaskAnalysis:
    """Deterministically characterize a query into 0-100 task-signal scores.

    This is the reproducible baseline layer described in the product spec
    (section 7). It does not call any LLM and always returns a result.
    """
    if not query or not query.strip():
        return TaskAnalysis(
            complexity=0, logical_reasoning=0, creativity=0, planning=0,
            context_dependency=0, verification_requirement=0, risk=0,
            ambiguity=0, factuality_requirement=0,
        )

    raw = _compute_raw_signals(query)

    return TaskAnalysis(
        complexity=_to_100(raw.complexity),
        logical_reasoning=_to_100(raw.logical_reasoning),
        creativity=_to_100(raw.creativity),
        planning=_to_100(raw.planning),
        context_dependency=_to_100(raw.context_dependency),
        verification_requirement=_to_100(raw.verification_requirement),
        risk=_to_100(raw.risk),
        ambiguity=_to_100(raw.ambiguity),
        factuality_requirement=_to_100(raw.factuality_requirement),
    )
