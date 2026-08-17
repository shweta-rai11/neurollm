"""Executive Controller: decides which reasoning pathway to engage next
(spec sections 4F / 12, MVP subset).

`select_pathway()` is a pure, synchronous decision function -- easy to unit
test without any model call. The actual VERIFY pathway (self-consistency +
a self-verifier LLM call + abstention framing) necessarily talks to a real
provider, so it lives here as the async `run_verification_pathway()` rather
than being pushed up into the route handler, since routing the *next* step
is exactly the executive controller's job per the spec.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from app.brain.hallucination import HallucinationRisk, refine_with_verifier
from app.brain.neuromodulation import NeuromodulatorSignals
from app.brain.regions import RegionScores
from app.cognitive_state.uncertainty import UncertaintyResult
from app.llm.provider import LLMProvider
from app.models.schemas import TaskAnalysis
from app.profile.params import ComputationalProfileParams
from app.retrieval.brave_search import SearchResult, is_available as retrieval_is_available
from app.retrieval.fact_check import fact_check

# Calibrated against real local-model runs on the benchmark's
# hallucination_prone items (see data/benchmark.json) -- 0.45 reliably
# triggers VERIFY on genuinely obscure questions without also catching
# ordinary factual ones. A designed/tunable threshold, not a learned value.
_BASE_HRS_THRESHOLD = 0.45
_MIN_HRS_THRESHOLD = 0.25
_MAX_HRS_THRESHOLD = 0.75
_ABSTAIN_THRESHOLD = 0.65
_REASONING_THRESHOLD = 65
_CREATIVITY_THRESHOLD = 65


class Pathway(str, Enum):
    DIRECT = "DIRECT"
    ANALYTICAL = "ANALYTICAL"
    CREATIVE = "CREATIVE"
    VERIFY = "VERIFY"


@dataclass
class RoutingDecision:
    pathway: Pathway
    reason: str
    hrs_threshold_used: float
    thresholds: dict[str, float] = field(default_factory=dict)


def _effective_hrs_threshold(
    neuromod: NeuromodulatorSignals, profile: ComputationalProfileParams | None = None
) -> float:
    """Neuromodulation feedback into routing (spec section 5): a higher
    norepinephrine-like (alertness/unexpectedness) signal or a lower
    serotonin-like (stability) signal both make the system more cautious --
    i.e. they lower the bar for triggering verification.

    When an Individual Computational Profile is supplied, its learned
    `verification_strength` (never fingerprint-derived -- see
    `app.profile.learning`) applies the same kind of bounded (+-0.075)
    cautiousness shift, on top of the neuromodulation terms above."""
    threshold = _BASE_HRS_THRESHOLD
    threshold -= (neuromod.norepinephrine_like / 100.0) * 0.15
    threshold -= max(0.0, (50.0 - neuromod.serotonin_like) / 100.0) * 0.10
    if profile is not None:
        threshold -= (profile.verification_strength - 0.5) * 0.15
    return max(_MIN_HRS_THRESHOLD, min(_MAX_HRS_THRESHOLD, threshold))


def select_pathway(
    task: TaskAnalysis,
    region_profile: RegionScores,
    initial_hrs: HallucinationRisk,
    neuromod: NeuromodulatorSignals,
    profile: ComputationalProfileParams | None = None,
) -> RoutingDecision:
    hrs_threshold = _effective_hrs_threshold(neuromod, profile)

    if initial_hrs.score >= hrs_threshold:
        return RoutingDecision(
            pathway=Pathway.VERIFY,
            reason=f"hallucination risk {initial_hrs.score:.2f} >= threshold {hrs_threshold:.2f} "
                   f"(base {_BASE_HRS_THRESHOLD:.2f}, adjusted by neuromodulation)",
            hrs_threshold_used=hrs_threshold,
            thresholds={"hrs": hrs_threshold},
        )

    if task.creativity >= _CREATIVITY_THRESHOLD and task.creativity >= task.logical_reasoning:
        return RoutingDecision(
            pathway=Pathway.CREATIVE,
            reason=f"creativity score {task.creativity} >= threshold {_CREATIVITY_THRESHOLD}",
            hrs_threshold_used=hrs_threshold,
            thresholds={"creativity": _CREATIVITY_THRESHOLD},
        )

    if region_profile.reasoning >= _REASONING_THRESHOLD or task.logical_reasoning >= _REASONING_THRESHOLD:
        return RoutingDecision(
            pathway=Pathway.ANALYTICAL,
            reason=f"reasoning activation {region_profile.reasoning} or task.logical_reasoning "
                   f"{task.logical_reasoning} >= threshold {_REASONING_THRESHOLD}",
            hrs_threshold_used=hrs_threshold,
            thresholds={"reasoning": _REASONING_THRESHOLD},
        )

    return RoutingDecision(
        pathway=Pathway.DIRECT,
        reason="no elevated hallucination risk, reasoning, or creativity signal",
        hrs_threshold_used=hrs_threshold,
        thresholds={},
    )


_VERIFIER_PROMPT_TEMPLATE = """You are checking your own earlier answers for consistency.

Question: {query}

Candidate answers you previously generated:
{candidates}

Are these candidate answers consistent with each other in substance (even if worded \
differently)? Reply with exactly one word first -- CONSISTENT or INCONSISTENT -- then a \
one-sentence explanation."""


def _largest_cluster_candidate(uncertainty: UncertaintyResult) -> str:
    counts: dict[int, int] = {}
    for c in uncertainty.candidates:
        counts[c.cluster_id] = counts.get(c.cluster_id, 0) + 1
    if not counts:
        return ""
    largest_cluster = max(counts, key=lambda k: counts[k])
    for c in uncertainty.candidates:
        if c.cluster_id == largest_cluster:
            return c.text
    return uncertainty.candidates[0].text


async def run_verification_pathway(
    provider: LLMProvider,
    query: str,
    uncertainty: UncertaintyResult,
    initial_hrs: HallucinationRisk,
) -> tuple[str, HallucinationRisk, str, str, list[SearchResult]]:
    """Self-consistency + self-verifier check, plus real retrieval-grounded
    fact-checking when a search API key is configured (see app.retrieval).
    Returns (final_answer, refined_hrs, verifier_raw_text, retrieval_raw_text,
    search_results). Both raw texts are surfaced in research mode so neither
    check is a black box. `search_results`/`retrieval_raw_text` are empty/""
    when retrieval wasn't available or found no evidence -- never faked."""
    best_answer = _largest_cluster_candidate(uncertainty)

    numbered = "\n".join(f"{i + 1}. {c.text}" for i, c in enumerate(uncertainty.candidates[:5]))
    verifier_prompt = _VERIFIER_PROMPT_TEMPLATE.format(query=query, candidates=numbered)

    try:
        verifier_text = await provider.generate(verifier_prompt)
    except Exception:  # noqa: BLE001 -- verification is best-effort, must not break the response
        verifier_text = ""

    normalized = verifier_text.strip().upper()
    if normalized.startswith("INCONSISTENT"):
        verifier_disagreement = 0.8
    elif normalized.startswith("CONSISTENT"):
        verifier_disagreement = 0.2
    else:
        # Verifier response didn't parse cleanly -- fall back to the existing
        # behavioral signal rather than guessing (documented, not silent).
        verifier_disagreement = uncertainty.semantic_uncertainty_score / 100.0

    retrieval_disagreement: float | None = None
    retrieval_raw_text = ""
    search_results: list[SearchResult] = []
    if retrieval_is_available():
        retrieval_disagreement, retrieval_raw_text, search_results = await fact_check(provider, query, best_answer)

    refined = refine_with_verifier(initial_hrs, verifier_disagreement, retrieval_disagreement)

    if refined.score >= _ABSTAIN_THRESHOLD:
        evidence_note = (
            "self-verification and retrieved evidence did not resolve it"
            if search_results
            else "self-verification did not resolve it"
        )
        final_answer = (
            "I don't have strong evidence for a confident answer to this question. "
            f"Candidate responses disagreed enough (and {evidence_note}) "
            f"that I'm not treating this as settled. A plausible but unverified answer is:\n\n"
            f"{best_answer}\n\n"
            "Treat this as a low-confidence guess, not a verified fact -- independent "
            "verification is recommended before relying on it."
        )
    else:
        final_answer = best_answer

    return final_answer, refined, verifier_text, retrieval_raw_text, search_results
