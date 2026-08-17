"""The five MVP virtual brain regions: Language, Memory, Reasoning,
Uncertainty, Verification (spec section 22).

Each region reports two scores:
  - `predicted`  -- estimated from the query text alone, before generation,
    using deterministic heuristics (`task_analyzer.py` scores plus a small
    text-only language-surface heuristic defined below). This is the "what
    kind of computation should this need" prediction.
  - `measured`   -- estimated after generation from real activation
    statistics (`app.activations.features.ActivationSummary`) and, where
    available, the behavioral multi-sample uncertainty result. This is what
    actually happened, read off the model.

Keeping both, rather than only exposing one blended number, is what lets the
system test H1 ("do activations predict cognitive requirements") instead of
just asserting it -- see Question Lab in the frontend.

Layer-position heuristic: Language leans on early/mid-layer activation
magnitude and Reasoning leans on late-layer magnitude/growth, per the
documented (not validated-for-this-model) design heuristic in
`app.activations.features`. Memory's `measured` score is intentionally a
passthrough of `predicted` -- there is no retrieval/embedding-memory
pathway in this MVP to observe, so there is nothing new to measure (see
README Limitations) rather than a number invented to look different.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from app.activations.features import ActivationSummary
from app.models.schemas import TaskAnalysis, UncertaintyResult
from app.profile.params import ComputationalProfileParams

_CLAUSE_MARKERS = re.compile(r"\b(which|that|because|although|while|since|who|whom|whereas)\b", re.IGNORECASE)


def _clamp100(x: float) -> int:
    return int(round(max(0.0, min(100.0, x))))


def _profile_delta(param: float) -> float:
    """Bounded Individual Computational Profile personalization nudge
    (product spec section 5): a neutral (0.5) param contributes 0; the
    extremes contribute at most +-15 percentage points. This is a designed,
    documented heuristic identical in spirit to this module's other
    weighted-sum blends -- never a claim that the profile "measures" the
    region it nudges."""
    return (param - 0.5) * 30.0


@dataclass
class RegionScores:
    language: int
    memory: int
    reasoning: int
    uncertainty: int
    verification: int


@dataclass
class BrainRegions:
    predicted: RegionScores
    measured: RegionScores | None  # None when no activation capture is available (e.g. mock provider)


def _predicted_language(query: str) -> float:
    """Text-surface heuristic (length, lexical diversity, clause structure)
    -- deliberately independent of task_analyzer's coding/math keyword
    scores, since "linguistic processing demand" is closer to prose
    complexity than to task category."""
    words = query.split()
    n_words = len(words)
    if n_words == 0:
        return 0.0

    stripped = [w.strip(".,!?;:\"'()").lower() for w in words]
    unique_ratio = len({w for w in stripped if w}) / n_words
    avg_word_len = sum(len(w) for w in stripped) / n_words
    n_sentences = max(1, len(re.split(r"[.!?]+", query.strip())) - 1) or 1
    clause_hits = len(_CLAUSE_MARKERS.findall(query))

    length_component = min(1.0, n_words / 60.0)
    lexical_component = min(1.0, unique_ratio * (avg_word_len / 6.0))
    structure_component = min(1.0, (n_sentences - 1) / 3.0 + clause_hits / 4.0)

    return 100.0 * (0.35 * length_component + 0.35 * lexical_component + 0.30 * structure_component)


def predicted_profile(
    query: str, task: TaskAnalysis, profile: ComputationalProfileParams | None = None
) -> RegionScores:
    language = _predicted_language(query)
    memory = 0.55 * task.context_dependency + 0.45 * task.factuality_requirement
    reasoning = 0.5 * task.logical_reasoning + 0.3 * task.complexity + 0.2 * task.planning
    uncertainty = 0.6 * task.ambiguity + 0.4 * task.risk
    verification = 0.55 * task.verification_requirement + 0.45 * task.factuality_requirement

    if profile is not None:
        reasoning += 0.5 * (_profile_delta(profile.attention_baseline) + _profile_delta(profile.working_memory_baseline))
        verification += _profile_delta(profile.verification_strength)
        memory += _profile_delta(profile.memory_retrieval)
        uncertainty += _profile_delta(profile.uncertainty_sensitivity)

    return RegionScores(
        language=_clamp100(language),
        memory=_clamp100(memory),
        reasoning=_clamp100(reasoning),
        uncertainty=_clamp100(uncertainty),
        verification=_clamp100(verification),
    )


def measured_profile(
    predicted: RegionScores,
    activation: ActivationSummary,
    uncertainty_result: UncertaintyResult | None,
) -> RegionScores:
    early = activation.early_layer_hidden_norm
    mid = activation.mid_layer_hidden_norm
    late = activation.late_layer_hidden_norm
    total_norm = early + mid + late

    lexical_share = (early + mid) / total_norm if total_norm > 1e-6 else 0.5
    late_share = late / total_norm if total_norm > 1e-6 else 0.5

    language = 100.0 * (0.5 * lexical_share + 0.5 * (1.0 - activation.token_entropy_normalized))

    # No retrieval pathway to observe in this MVP -- inherit the prediction
    # rather than inventing a "measured" number with nothing new behind it.
    memory = float(predicted.memory)

    growth_component = min(1.0, max(0.0, activation.hidden_norm_growth_ratio))
    reasoning = 100.0 * (0.4 * late_share + 0.3 * growth_component + 0.3 * activation.late_layer_attention_entropy)

    activation_uncertainty = 0.5 * activation.token_entropy_normalized + 0.5 * (1.0 - activation.mean_prob_margin)
    if uncertainty_result is not None:
        uncertainty = 100.0 * (0.5 * activation_uncertainty + 0.5 * (uncertainty_result.semantic_uncertainty_score / 100.0))
    else:
        uncertainty = 100.0 * activation_uncertainty

    verification = 0.5 * predicted.verification + 0.5 * uncertainty

    return RegionScores(
        language=_clamp100(language),
        memory=_clamp100(memory),
        reasoning=_clamp100(reasoning),
        uncertainty=_clamp100(uncertainty),
        verification=_clamp100(verification),
    )


def compute_brain_regions(
    query: str,
    task: TaskAnalysis,
    activation: ActivationSummary | None,
    uncertainty_result: UncertaintyResult | None,
    profile: ComputationalProfileParams | None = None,
) -> BrainRegions:
    predicted = predicted_profile(query, task, profile)
    measured = measured_profile(predicted, activation, uncertainty_result) if activation is not None else None
    return BrainRegions(predicted=predicted, measured=measured)
