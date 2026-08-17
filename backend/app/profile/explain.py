""""Why this brain state?" -- a templated, rule-based explanation of the
turn's routing decisions (product spec section 11). Same style as
`app.cognitive_state.recommendations`: threshold-driven text generation,
not an LLM call, so it's reproducible and auditable.
"""
from __future__ import annotations

from dataclasses import dataclass

from app.brain.hallucination import HallucinationRisk
from app.brain.neuromodulation import NeuromodulatorSignals
from app.brain.regions import RegionScores
from app.profile.task_classifier import TaskCategoryResult

MANDATORY_DISCLAIMER = (
    "These are computational representations produced by a designed heuristic model. "
    "They do not measure this user's actual hormones, neurotransmitters, or brain activity."
)


@dataclass
class ExplanationEntry:
    question: str
    answer: str


@dataclass
class Explanation:
    entries: list[ExplanationEntry]
    disclaimer: str = MANDATORY_DISCLAIMER


def build_explanation(
    task_category: TaskCategoryResult,
    region_profile: RegionScores,
    neuromod: NeuromodulatorSignals,
    hrs: HallucinationRisk,
    pathway: str,
    profile_applied: bool,
) -> Explanation:
    entries: list[ExplanationEntry] = []

    systems = ", ".join(task_category.candidate_systems[:-1])
    last = task_category.candidate_systems[-1] if task_category.candidate_systems else ""
    systems_text = f"{systems} and {last}" if systems else last
    entries.append(
        ExplanationEntry(
            question=f"Why were these virtual systems activated: {systems_text}?",
            answer=(
                f"The question was classified as \"{task_category.category.replace('_', ' ')}\" "
                f"(classification confidence {task_category.confidence:.0%}), and this category's candidate "
                "virtual systems are a fixed, designed mapping (product spec section 8) -- not something the "
                "profile or fingerprint chooses."
            ),
        )
    )

    if region_profile.reasoning >= 60:
        entries.append(
            ExplanationEntry(
                question="Why was the reasoning/working-memory signal emphasized?",
                answer=(
                    f"The reasoning region scored {region_profile.reasoning}/100, driven by this query's logical-"
                    "reasoning and complexity signals -- the task requires maintaining and combining intermediate "
                    "information, which this system's virtual working-memory/reasoning region is designed to reflect."
                ),
            )
        )

    if region_profile.verification >= 55:
        entries.append(
            ExplanationEntry(
                question="Why is verification emphasized?",
                answer=(
                    f"The verification region scored {region_profile.verification}/100 and hallucination risk was "
                    f"{hrs.score:.2f}. Higher factuality/verification demand and elevated risk both raise this "
                    "signal, which lowers the bar for the executive controller to choose the VERIFY pathway."
                ),
            )
        )

    entries.append(
        ExplanationEntry(
            question=f"Why was the \"{pathway}\" pathway chosen?",
            answer={
                "VERIFY": "Hallucination-risk signals crossed the routing threshold, so the executive controller "
                          "ran self-consistency and self-verification before finalizing an answer.",
                "ANALYTICAL": "Reasoning demand crossed the routing threshold, so the executive controller favored "
                              "a step-by-step analytical framing.",
                "CREATIVE": "Creativity demand was the dominant signal for this query, so the executive controller "
                            "favored open-ended generation over strict verification.",
                "DIRECT": "No elevated risk, reasoning, or creativity signal was strong enough to change the "
                          "default routing, so the direct pathway was used.",
            }.get(pathway, "The executive controller's threshold rules selected this pathway for this turn."),
        )
    )

    entries.append(
        ExplanationEntry(
            question="Why does the simulator show neuromodulation and endocrine-style panels?",
            answer=(
                "The simulator maintains a small set of computational variables inspired by neuromodulation and "
                "endocrine feedback because stress- and reward-related systems are hypothesized (not established "
                "here) to influence cognitive-state models. These values are computed from response consistency, "
                "token/attention statistics, and task heuristics -- see the Neuromodulation panel."
            ),
        )
    )

    if profile_applied:
        entries.append(
            ExplanationEntry(
                question="Did your fingerprint change any of this?",
                answer=(
                    "No. Your fingerprint was used only to look up your Individual Computational Profile -- a set "
                    "of parameters learned from your own past interactions (feedback, pathway history, verification "
                    "outcomes). Those learned parameters made small, bounded adjustments to the values above; the "
                    "fingerprint itself was never used to infer any cognitive trait."
                ),
            )
        )

    return Explanation(entries=entries)
