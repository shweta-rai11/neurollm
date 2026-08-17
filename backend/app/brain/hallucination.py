"""Hallucination Risk Score (HRS), spec section 11.

HRS = w1*token_entropy + w2*activation_uncertainty + w3*answer_variability
      + w4*retrieval_disagreement + w5*verifier_disagreement

The score is computed in two stages because both the self-critique and
real-retrieval signals are only available *after* a verification pass has
actually run (see `executive_controller.py` and `app.retrieval`):
`compute_initial_risk` is what the executive controller uses to decide
whether to trigger the VERIFY pathway in the first place -- at that point
`retrieval_disagreement`'s weight is still fixed at 0 (chicken-and-egg: we
haven't retrieved anything yet), never a fabricated value. `refine_with_verifier`
produces the score actually reported to the user once (and if) VERIFY ran,
and it's where real retrieval evidence (when available) gets real weight.
"""
from __future__ import annotations

from dataclasses import dataclass

_W_TOKEN_ENTROPY = 0.35
_W_ACTIVATION_UNCERTAINTY = 0.25
_W_ANSWER_VARIABILITY = 0.40
_W_RETRIEVAL_DISAGREEMENT = 0.0  # inert in compute_initial_risk -- retrieval only runs *after*
                                 # VERIFY is chosen (see app.retrieval), same chicken-and-egg
                                 # constraint as verifier_disagreement below; real weight is
                                 # applied post-hoc in refine_with_verifier instead.
_W_VERIFIER_DISAGREEMENT = 0.30  # blended in when a self-critique pass ran and no retrieval evidence was available
_W_VERIFIER_WITH_RETRIEVAL = 0.15  # self-critique's weight drops once real evidence exists
_W_RETRIEVAL_REFINE = 0.35  # real external evidence gets the largest single post-hoc weight --
                             # calibrated as "stronger than self-critique, not treated as ground truth"


def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))


@dataclass
class HallucinationRisk:
    score: float  # 0 = low risk, 1 = high risk
    components: dict[str, float]


def compute_initial_risk(
    token_entropy_normalized: float,
    activation_uncertainty: float,
    answer_variability: float,
    retrieval_disagreement: float = 0.0,
) -> HallucinationRisk:
    components = {
        "token_entropy": _clamp01(token_entropy_normalized),
        "activation_uncertainty": _clamp01(activation_uncertainty),
        "answer_variability": _clamp01(answer_variability),
        "retrieval_disagreement": _clamp01(retrieval_disagreement),
    }
    score = (
        _W_TOKEN_ENTROPY * components["token_entropy"]
        + _W_ACTIVATION_UNCERTAINTY * components["activation_uncertainty"]
        + _W_ANSWER_VARIABILITY * components["answer_variability"]
        + _W_RETRIEVAL_DISAGREEMENT * components["retrieval_disagreement"]
    )
    return HallucinationRisk(score=round(_clamp01(score), 4), components=components)


def refine_with_verifier(
    initial: HallucinationRisk,
    verifier_disagreement: float,
    retrieval_disagreement: float | None = None,
) -> HallucinationRisk:
    """Blends post-hoc verification signal(s) into the score once the VERIFY
    pathway has actually run (see executive_controller.py). `verifier_disagreement`
    is a model self-critique signal (checking its own prior candidates) --
    not ground-truth verification. `retrieval_disagreement`, when provided,
    is a real external-evidence signal (see app.retrieval.fact_check) and is
    weighted more heavily than self-critique precisely because it isn't the
    same model checking itself. Passing `retrieval_disagreement=None` (the
    default -- no search results were available) reproduces the original
    self-critique-only blend exactly."""
    verifier_component = _clamp01(verifier_disagreement)

    if retrieval_disagreement is None:
        remaining_weight = 1.0 - _W_VERIFIER_DISAGREEMENT
        score = remaining_weight * initial.score + _W_VERIFIER_DISAGREEMENT * verifier_component
        components = {**initial.components, "verifier_disagreement": verifier_component}
    else:
        retrieval_component = _clamp01(retrieval_disagreement)
        remaining_weight = 1.0 - _W_VERIFIER_WITH_RETRIEVAL - _W_RETRIEVAL_REFINE
        score = (
            remaining_weight * initial.score
            + _W_VERIFIER_WITH_RETRIEVAL * verifier_component
            + _W_RETRIEVAL_REFINE * retrieval_component
        )
        components = {
            **initial.components,
            "verifier_disagreement": verifier_component,
            "retrieval_disagreement": retrieval_component,
        }

    return HallucinationRisk(score=round(_clamp01(score), 4), components=components)
