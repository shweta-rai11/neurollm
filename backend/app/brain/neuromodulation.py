"""Virtual Neuromodulation Layer.

IMPORTANT: these are computational variables *inspired by* neuromodulation,
not biological hormones or neurochemistry -- every field name below carries
the "-like" suffix deliberately, and the project's UI/API/docs must never
drop it (never "dopamine increased", always "dopamine-like signal
increased"). They exist for two reasons:

  1. A legible, at-a-glance summary of a few underlying computational
     signals (response consistency, prompt/token entropy, task risk).
  2. They actually modulate routing thresholds in `executive_controller.py`
     -- this is a functional layer, not a decorative one (spec section 5:
     "should modify routing thresholds rather than claiming to reproduce
     human neurochemistry").

Mapping used below:
  dopamine_like        <- reward/confidence proxy: token probability margin and cross-sample agreement
  serotonin_like        <- stability: cross-sample agreement and low task ambiguity
  norepinephrine_like    <- alertness/unexpectedness: token entropy and task risk/ambiguity
  acetylcholine_like    <- attention/engagement: context dependency and verification requirement
"""
from __future__ import annotations

from dataclasses import dataclass

from app.activations.features import ActivationSummary
from app.models.schemas import TaskAnalysis, UncertaintyResult
from app.profile.params import ComputationalProfileParams


def _clamp(x: float) -> float:
    return max(0.0, min(100.0, x))


def _profile_delta(param: float) -> float:
    """Same bounded (+-15) personalization nudge as `app.brain.regions`."""
    return (param - 0.5) * 30.0


@dataclass
class NeuromodulatorSignals:
    dopamine_like: float
    serotonin_like: float
    norepinephrine_like: float
    acetylcholine_like: float


def compute_neuromodulation(
    task: TaskAnalysis,
    activation: ActivationSummary | None,
    uncertainty_result: UncertaintyResult | None,
    profile: ComputationalProfileParams | None = None,
) -> NeuromodulatorSignals:
    agreement = float(uncertainty_result.response_agreement) if uncertainty_result is not None else 70.0
    prob_margin_pct = (activation.mean_prob_margin * 100.0) if activation is not None else 50.0
    token_entropy_pct = (activation.token_entropy_normalized * 100.0) if activation is not None else 30.0

    dopamine_like = _clamp(0.6 * prob_margin_pct + 0.4 * agreement)
    serotonin_like = _clamp(0.7 * agreement + 0.3 * (100.0 - task.ambiguity))
    norepinephrine_like = _clamp(0.5 * token_entropy_pct + 0.3 * task.risk + 0.2 * task.ambiguity)
    acetylcholine_like = _clamp(0.6 * task.context_dependency + 0.4 * task.verification_requirement)

    if profile is not None:
        # Individual Computational Profile personalization (product spec
        # section 5) -- same bounded nudge pattern as app.brain.regions.
        dopamine_like = _clamp(dopamine_like + _profile_delta(profile.exploitation))
        acetylcholine_like = _clamp(acetylcholine_like + _profile_delta(profile.attention_baseline))

    return NeuromodulatorSignals(
        dopamine_like=round(dopamine_like, 1),
        serotonin_like=round(serotonin_like, 1),
        norepinephrine_like=round(norepinephrine_like, 1),
        acetylcholine_like=round(acetylcholine_like, 1),
    )
