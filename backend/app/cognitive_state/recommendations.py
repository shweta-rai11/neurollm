"""Recommendation engine: translates cognitive state into user-facing guidance.

Rule of thumb enforced throughout this module (see product spec section 13):
    Consistency across candidate answers is never presented as proof of
    correctness. High agreement lowers estimated uncertainty, but the
    recommendation text always keeps that caveat explicit.
"""
from __future__ import annotations

from app.models.schemas import (
    GlobalState,
    Recommendation,
    TaskAnalysis,
    UncertaintyResult,
)


def build_recommendations(
    task: TaskAnalysis,
    global_state: GlobalState,
    pathway: str,
    uncertainty: UncertaintyResult | None,
) -> list[Recommendation]:
    recs: list[Recommendation] = []

    if pathway == "VERIFY":
        recs.append(Recommendation(
            title="Do not treat this as a confident answer",
            detail="Hallucination-risk signals were high enough to trigger the verification pathway: self-consistency and self-verification did not resolve them. Independently verify before relying on this answer.",
            icon="shield-alert",
            severity="warning",
        ))

    if global_state.uncertainty > 65:
        recs.append(Recommendation(
            title="Verify before trusting",
            detail="Ask for sources or independently verify the answer. Candidate responses showed meaningful disagreement or the task carries high ambiguity.",
            icon="search",
            severity="warning",
        ))

    if task.creativity > 60:
        recs.append(Recommendation(
            title="Explore multiple alternatives",
            detail="This is an open-ended task. Generate multiple alternatives before selecting one rather than anchoring on the first answer.",
            icon="sparkles",
            severity="info",
        ))

    if task.complexity > 70:
        recs.append(Recommendation(
            title="Break the task into steps",
            detail="Break the task into smaller, independently verifiable steps rather than accepting one large answer at face value.",
            icon="list-tree",
            severity="caution",
        ))

    if task.context_dependency > 60:
        recs.append(Recommendation(
            title="Provide more context",
            detail="This task depends heavily on context the model may not have. Provide additional context or source documents for a more reliable answer.",
            icon="book-open",
            severity="caution",
        ))

    if task.risk > 55:
        recs.append(Recommendation(
            title="Use human review",
            detail="This task touches a high-stakes or sensitive domain. Use human review before acting on the output.",
            icon="shield-alert",
            severity="warning",
        ))

    if uncertainty is not None and uncertainty.response_agreement > 80:
        recs.append(Recommendation(
            title="High agreement — verify anyway",
            detail="Candidate responses are highly consistent, but consistency does not guarantee correctness. Agreement reduces estimated uncertainty; it is not proof of truth.",
            icon="check-circle",
            severity="info",
        ))

    if not recs:
        recs.append(Recommendation(
            title="Standard confidence",
            detail="No elevated risk, ambiguity, or disagreement signals were detected. Ordinary review is sufficient.",
            icon="check-circle",
            severity="info",
        ))

    return recs
