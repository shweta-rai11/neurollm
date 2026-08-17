"""Central orchestration: query -> task analysis -> generation (+ activation
capture when possible) -> uncertainty sampling -> brain regions ->
neuromodulation -> hallucination risk -> pathway selection -> (optionally)
verification -> assembled CognitiveState.

This is the one place that talks to a live provider, so `routes_chat.py`,
`routes_experiments.py`, and `probes` benchmark scoring all share it rather
than re-implementing the flow.
"""
from __future__ import annotations

from dataclasses import dataclass

from app.activations.extractor import ActivationCapture
from app.activations.features import ActivationSummary, summarize
from app.brain.executive_controller import Pathway, RoutingDecision, run_verification_pathway, select_pathway
from app.brain.hallucination import HallucinationRisk, compute_initial_risk
from app.brain.neuromodulation import NeuromodulatorSignals, compute_neuromodulation
from app.brain.regions import BrainRegions, compute_brain_regions
from app.brain.state_engine import build_cognitive_state
from app.cognitive_state.task_analyzer import analyze_task
from app.cognitive_state.uncertainty import estimate_uncertainty
from app.llm import LLMProviderError, MockProvider, get_provider
from app.models.schemas import CognitiveState, ProbePrediction, TaskAnalysis, UncertaintyResult
from app.profile.explain import Explanation, build_explanation
from app.profile.params import ComputationalProfileParams
from app.profile.task_classifier import TaskCategoryResult, classify_task_category
from app.retrieval.brave_search import SearchResult


@dataclass
class PipelineResult:
    answer: str
    pathway: str
    routing_reason: str
    hallucination_risk: HallucinationRisk
    task: TaskAnalysis
    region_profile: BrainRegions
    neuromod: NeuromodulatorSignals
    uncertainty: UncertaintyResult | None
    cognitive_state: CognitiveState
    provider_label: str
    activation_capture: ActivationCapture | None
    activation_summary: ActivationSummary | None
    verifier_raw_text: str | None
    retrieval_raw_text: str | None
    retrieval_results: list[SearchResult]
    probe_prediction: ProbePrediction | None
    task_category: TaskCategoryResult
    profile_applied: bool
    explanation: Explanation


async def run_pipeline(
    query: str,
    model: str,
    uncertainty_mode: bool,
    num_samples: int,
    research_mode: bool = False,
    profile: ComputationalProfileParams | None = None,
) -> PipelineResult:
    task = analyze_task(query)
    task_category = classify_task_category(query, task)
    provider = get_provider(model)
    provider_label = provider.get_model_info().get("provider", model)

    activation_capture: ActivationCapture | None = None
    activation_summary: ActivationSummary | None = None
    answer: str

    try:
        # Duck-typed rather than an isinstance(..., LocalHFProvider) check so
        # tests can substitute a fake provider exposing the same
        # get_activation_extractor() hook without loading the real model.
        if hasattr(provider, "get_activation_extractor"):
            extractor = provider.get_activation_extractor()
            answer, activation_capture = extractor.capture(query)
            activation_summary = summarize(activation_capture)
        else:
            answer = await provider.generate(query)
    except LLMProviderError:
        provider = MockProvider()
        provider_label = f"mock (fallback: {model} unavailable)"
        answer = await provider.generate(query)

    uncertainty: UncertaintyResult | None = None
    if uncertainty_mode:
        try:
            candidates = await provider.generate_multiple(query, num_samples)
            uncertainty = estimate_uncertainty(candidates)
        except Exception:  # noqa: BLE001 -- uncertainty sampling is optional
            uncertainty = None

    region_profile = compute_brain_regions(query, task, activation_summary, uncertainty, profile)
    neuromod = compute_neuromodulation(task, activation_summary, uncertainty, profile)

    if activation_summary is not None:
        token_entropy_component = activation_summary.token_entropy_normalized
        activation_uncertainty_component = activation_summary.late_layer_attention_entropy
    else:
        # No real activations available for this provider (mock/OpenAI) --
        # fall back to the text-heuristic proxies rather than fabricating an
        # activation number. This keeps HRS meaningful for every provider,
        # not just the local one.
        token_entropy_component = task.ambiguity / 100.0
        activation_uncertainty_component = task.risk / 100.0
    answer_variability = (
        uncertainty.semantic_uncertainty_score / 100.0 if uncertainty is not None else task.ambiguity / 100.0
    )

    initial_hrs = compute_initial_risk(token_entropy_component, activation_uncertainty_component, answer_variability)

    active_profile = region_profile.measured or region_profile.predicted
    decision: RoutingDecision = select_pathway(task, active_profile, initial_hrs, neuromod, profile)

    final_hrs = initial_hrs
    verifier_raw_text: str | None = None
    retrieval_raw_text: str | None = None
    retrieval_results: list[SearchResult] = []
    if decision.pathway == Pathway.VERIFY and uncertainty is not None and uncertainty.candidate_count >= 2:
        answer, final_hrs, verifier_raw_text, retrieval_raw_text, retrieval_results = await run_verification_pathway(
            provider, query, uncertainty, initial_hrs
        )

    cognitive_state = build_cognitive_state(task, region_profile, neuromod, final_hrs, uncertainty, decision.pathway.value)

    probe_prediction: ProbePrediction | None = None
    if research_mode and activation_summary is not None:
        from app.probes.infer import predict_category

        probe_prediction = predict_category(task, activation_summary)

    explanation = build_explanation(
        task_category=task_category,
        region_profile=active_profile,
        neuromod=neuromod,
        hrs=final_hrs,
        pathway=decision.pathway.value,
        profile_applied=profile is not None,
    )

    return PipelineResult(
        answer=answer,
        pathway=decision.pathway.value,
        routing_reason=decision.reason,
        hallucination_risk=final_hrs,
        task=task,
        region_profile=region_profile,
        neuromod=neuromod,
        uncertainty=uncertainty,
        cognitive_state=cognitive_state,
        provider_label=provider_label,
        activation_capture=activation_capture,
        activation_summary=activation_summary,
        verifier_raw_text=verifier_raw_text,
        retrieval_raw_text=retrieval_raw_text,
        retrieval_results=retrieval_results,
        probe_prediction=probe_prediction,
        task_category=task_category,
        profile_applied=profile is not None,
        explanation=explanation,
    )
