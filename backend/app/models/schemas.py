"""Pydantic request/response schemas for the AI-Brain / NeuroLLM API.

All numeric "scores" in this module are 0-100 (or 0-1 for hallucination
risk) computational signals -- some from deterministic text heuristics, some
from real model activation statistics where noted. See `app.brain` for what
each one is actually computed from; nothing here is a claim about biological
brain structure, hormones, or consciousness (see README).
"""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field

from app.models.profile_schemas import ProfileInfluence


# ---------------------------------------------------------------------------
# Task analysis (predicted, text-only, pre-generation)
# ---------------------------------------------------------------------------


class TaskAnalysis(BaseModel):
    complexity: int = Field(..., ge=0, le=100)
    logical_reasoning: int = Field(..., ge=0, le=100)
    creativity: int = Field(..., ge=0, le=100)
    planning: int = Field(..., ge=0, le=100)
    context_dependency: int = Field(..., ge=0, le=100)
    verification_requirement: int = Field(..., ge=0, le=100)
    risk: int = Field(..., ge=0, le=100)
    ambiguity: int = Field(..., ge=0, le=100)
    factuality_requirement: int = Field(..., ge=0, le=100)


# ---------------------------------------------------------------------------
# Uncertainty (behavioral: multi-sample response consistency)
# ---------------------------------------------------------------------------


class CandidateResponse(BaseModel):
    text: str
    cluster_id: int


class UncertaintyResult(BaseModel):
    semantic_uncertainty_score: int = Field(..., ge=0, le=100, description="0=fully consistent, 100=maximally disagreeing")
    response_agreement: int = Field(..., ge=0, le=100)
    candidate_count: int
    unique_semantic_clusters: int
    mean_embedding_similarity: float
    max_embedding_distance: float
    entropy_raw: float
    entropy_normalized: float
    candidates: list[CandidateResponse]
    method: str = Field(..., description="Similarity backend actually used: 'tfidf' or 'lexical_fallback'")


# ---------------------------------------------------------------------------
# Virtual brain: regions, neuromodulation, hallucination risk, pathway
# ---------------------------------------------------------------------------


class RegionScores(BaseModel):
    """The five MVP virtual brain regions (spec section 22)."""
    language: int = Field(..., ge=0, le=100)
    memory: int = Field(..., ge=0, le=100)
    reasoning: int = Field(..., ge=0, le=100)
    uncertainty: int = Field(..., ge=0, le=100)
    verification: int = Field(..., ge=0, le=100)


class BrainRegions(BaseModel):
    predicted: RegionScores = Field(..., description="Estimated from the query text alone, before generation.")
    measured: Optional[RegionScores] = Field(
        None, description="Estimated from real model activations after generation. Null when no activation capture is available (e.g. mock provider)."
    )


class NeuromodulatorSignals(BaseModel):
    """Virtual Neuromodulation Layer -- computational analogies, not biological
    hormones. See app/brain/neuromodulation.py."""
    dopamine_like: float = Field(..., ge=0, le=100)
    serotonin_like: float = Field(..., ge=0, le=100)
    norepinephrine_like: float = Field(..., ge=0, le=100)
    acetylcholine_like: float = Field(..., ge=0, le=100)


class HallucinationRiskOut(BaseModel):
    score: float = Field(..., ge=0, le=1, description="0=low risk, 1=high risk")
    components: dict[str, float]


class GlobalState(BaseModel):
    confidence: int
    uncertainty: int
    difficulty: int
    verification_need: int


class StateInterpretation(BaseModel):
    modes: list[str]
    status: str
    contributing_signals: dict[str, str]
    interpretation: str


class Recommendation(BaseModel):
    title: str
    detail: str
    icon: str
    severity: str = Field(..., description="info | caution | warning")


class ProbePrediction(BaseModel):
    predicted_category: str
    confidence: float = Field(..., ge=0, le=1)
    probabilities: dict[str, float]
    probe_type: str


class RetrievalSource(BaseModel):
    title: str
    snippet: str
    url: str


class ResearchDetails(BaseModel):
    """Only populated when `research_mode=true` AND the provider is
    `local_hf` -- absent (not zero-filled) otherwise, so the UI never
    displays fabricated research data for a provider with no inspectable
    internals."""
    num_layers: int
    layer_hidden_norms: list[float]
    layer_attention_entropy: list[float]
    token_entropies: list[float]
    token_prob_margins: list[float]
    activation_features: dict[str, float]
    probe_prediction: Optional[ProbePrediction] = None
    verifier_raw_text: Optional[str] = None
    retrieval_raw_text: Optional[str] = None
    retrieval_sources: list[RetrievalSource] = Field(default_factory=list)
    routing_reason: str


class CognitiveState(BaseModel):
    brain_regions: BrainRegions
    neuromodulation: NeuromodulatorSignals
    global_state: GlobalState
    interpretation: StateInterpretation
    recommendations: list[Recommendation]


# ---------------------------------------------------------------------------
# Chat / analysis API
# ---------------------------------------------------------------------------


class ChatRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=8000)
    model: str = Field(default="mock")
    uncertainty_mode: bool = Field(default=True)
    num_samples: int = Field(default=5, ge=1, le=10)
    research_mode: bool = Field(default=False, description="Requests layer-by-layer activation detail; only honored for provider='local_hf'.")
    profile_id: Optional[str] = Field(
        default=None,
        description="Individual Computational Profile id (see /api/biometric/enroll). When set, the profile's "
        "learned parameters personalize routing and a `profile_influence` block is attached to the response.",
    )


class ChatMetadata(BaseModel):
    model: str
    duration_ms: int
    input_tokens: int
    output_tokens: int
    provider: str


class ChatResponse(BaseModel):
    answer: str
    pathway: str
    hallucination_risk: HallucinationRiskOut
    cognitive_state: CognitiveState
    uncertainty: Optional[UncertaintyResult] = None
    task_analysis: TaskAnalysis
    recommendations: list[Recommendation]
    metadata: ChatMetadata
    research: Optional[ResearchDetails] = None
    profile_influence: Optional[ProfileInfluence] = None


class AnalyzeRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=8000)


class AnalyzeResponse(BaseModel):
    task_analysis: TaskAnalysis


class UncertaintyRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=8000)
    model: str = Field(default="mock")
    num_samples: int = Field(default=5, ge=1, le=10)


class UncertaintyResponse(BaseModel):
    uncertainty: UncertaintyResult


class ExperimentRequest(BaseModel):
    query_a: str = Field(..., min_length=1, max_length=8000)
    query_b: str = Field(..., min_length=1, max_length=8000)
    model: str = Field(default="mock")
    num_samples: int = Field(default=5, ge=1, le=10)


class ExperimentSide(BaseModel):
    query: str
    answer: str
    pathway: str
    hallucination_risk: HallucinationRiskOut
    task_analysis: TaskAnalysis
    cognitive_state: CognitiveState
    uncertainty: Optional[UncertaintyResult] = None


class ExperimentResponse(BaseModel):
    side_a: ExperimentSide
    side_b: ExperimentSide
    response_agreement_between_sides: float


class HistoryItem(BaseModel):
    id: int
    timestamp: str
    query: str
    model: str
    pathway: str
    uncertainty: int
    confidence: int
    difficulty: int
    verification_need: int
    hallucination_risk: float


class HistoryResponse(BaseModel):
    items: list[HistoryItem]


class HealthResponse(BaseModel):
    status: str
    version: str


class ConfigResponse(BaseModel):
    available_models: list[str]
    default_model: str
    default_num_samples: int
    max_num_samples: int
    has_openai_key: bool
    local_model_name: Optional[str] = None


# ---------------------------------------------------------------------------
# Condition comparison / benchmark (spec section 10)
# ---------------------------------------------------------------------------


class BenchmarkRequest(BaseModel):
    model: str = Field(default="mock")
    categories: Optional[list[str]] = Field(None, description="Subset of benchmark.json categories to run; all categories if omitted.")
    limit_per_category: int = Field(default=4, ge=1, le=20)


class BenchmarkItemResult(BaseModel):
    id: str
    category: str
    query: str
    expected_answer: Optional[str]
    condition_normal_answer: str
    condition_normal_correct: Optional[bool]
    condition_routed_answer: str
    condition_routed_correct: Optional[bool]
    condition_routed_pathway: str
    condition_routed_abstained: bool
    hallucination_risk: float


class BenchmarkCategorySummary(BaseModel):
    category: str
    n: int
    normal_accuracy: Optional[float]
    routed_accuracy: Optional[float]
    routed_abstention_rate: float
    mean_hallucination_risk: float


class BenchmarkResponse(BaseModel):
    model: str
    items: list[BenchmarkItemResult]
    category_summaries: list[BenchmarkCategorySummary]
    normal_mean_latency_ms: float
    routed_mean_latency_ms: float


# ---------------------------------------------------------------------------
# Probes
# ---------------------------------------------------------------------------


class ProbeInfoResponse(BaseModel):
    trained: bool
    probe_type: Optional[str] = None
    test_accuracy: Optional[float] = None
    n_train: Optional[int] = None
    n_test: Optional[int] = None
    categories: list[str] = Field(default_factory=list)
    trained_at: Optional[str] = None
