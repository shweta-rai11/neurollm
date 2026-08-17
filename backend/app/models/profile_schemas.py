"""Pydantic schemas for the Individual Computational Profile (ICP) feature
-- biometric enrollment/identity, the learned computational profile, and the
counterfactual/research-mode endpoints.

Same conventions as `app.models.schemas`: numeric fields are documented
computational signals, never a claim about the user's real biology. See
`app.biometric` (feature extraction) and `app.profile` (profile domain).
"""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field

NOT_A_BIOLOGICAL_MEASUREMENT = (
    "Simulated computational value -- not a biological measurement of this user's brain, hormones, or cognition."
)


# ---------------------------------------------------------------------------
# Biometric scan / enrollment
# ---------------------------------------------------------------------------


class FingerprintQuality(BaseModel):
    quality_label: str = Field(..., description="'Good' | 'Fair' | 'Poor', from the actual uploaded image.")
    overall_quality: float = Field(..., ge=0, le=1)
    ridge_visibility_pct: float = Field(..., ge=0, le=100)
    orientation_confidence_pct: float = Field(..., ge=0, le=100)
    contrast_score: float = Field(..., ge=0, le=1)
    sharpness_score: float = Field(..., ge=0, le=1)
    segmentation_quality: float = Field(..., ge=0, le=1)
    continuity: float = Field(..., ge=0, le=1)
    minutiae_detected: int = Field(..., ge=0)


class FingerprintScanSummary(BaseModel):
    quality: FingerprintQuality
    pattern: str = Field(..., description="'arch' | 'loop' | 'whorl' -- from Poincare-index singularity detection.")
    pattern_confidence: float = Field(..., ge=0, le=1)
    n_cores: int
    n_deltas: int
    n_endings: int
    n_bifurcations: int
    image_width: int
    image_height: int
    measurement_note: str = Field(
        default="All values above are computed from the uploaded image using standard fingerprint image-processing "
        "algorithms (ridge orientation, minutiae, singularities). They describe the image, not this user's biology.",
    )


class QualityCheckResponse(BaseModel):
    scan: FingerprintScanSummary


class EnrollResponse(BaseModel):
    profile_id: str
    matched_existing_profile: bool = Field(
        ..., description="True if this fingerprint matched an already-enrolled profile rather than creating a new one."
    )
    match_similarity: float = Field(..., ge=0, le=1)
    scan: FingerprintScanSummary
    virtual_brain_parameters: dict[str, float]
    evidence_status: str = "computational_model"


# ---------------------------------------------------------------------------
# Computational profile lifecycle
# ---------------------------------------------------------------------------


class ComputationalProfileOut(BaseModel):
    profile_id: str
    consent_given: bool
    created_at: str
    updated_at: str
    evidence_status: str
    virtual_brain_parameters: dict[str, float]
    task_profiles: dict[str, dict[str, float]]
    enrolled_finger_count: int


class DeleteProfileResponse(BaseModel):
    deleted: bool


class ResetBiometricResponse(BaseModel):
    reset: bool
    note: str = "Fingerprint templates were removed. Your learned computational profile was kept."


class ExportProfileResponse(BaseModel):
    export: dict


class EvolutionHistoryEntry(BaseModel):
    timestamp: str
    task_category: str
    pathway: str
    params_snapshot: dict[str, float]


class EvolutionResponse(BaseModel):
    initial: dict[str, float]
    current: dict[str, float]
    task_profiles: dict[str, dict[str, float]]
    n_interactions: int
    history: list[EvolutionHistoryEntry]
    note: str = "Derived from observed task performance and user feedback -- never from fingerprint features."


class FeedbackRequest(BaseModel):
    interaction_id: int
    feedback_score: float = Field(..., ge=0, le=1, description="1 = correct/useful, 0 = incorrect/unhelpful.")


class FeedbackResponse(BaseModel):
    updated_parameters: dict[str, float]


# ---------------------------------------------------------------------------
# Profile influence attached to /api/chat responses
# ---------------------------------------------------------------------------


class ExplanationEntryOut(BaseModel):
    question: str
    answer: str


class ProfileInfluence(BaseModel):
    applied: bool
    task_category: str
    task_category_confidence: float = Field(..., ge=0, le=1)
    candidate_systems: list[str]
    explanation: list[ExplanationEntryOut]
    disclaimer: str


# ---------------------------------------------------------------------------
# Counterfactual simulator ("What if?")
# ---------------------------------------------------------------------------


class CounterfactualOverrides(BaseModel):
    attention_baseline: Optional[float] = Field(None, ge=0, le=1)
    working_memory_baseline: Optional[float] = Field(None, ge=0, le=1)
    cognitive_control: Optional[float] = Field(None, ge=0, le=1)
    exploration: Optional[float] = Field(None, ge=0, le=1)
    exploitation: Optional[float] = Field(None, ge=0, le=1)
    memory_retrieval: Optional[float] = Field(None, ge=0, le=1)
    uncertainty_sensitivity: Optional[float] = Field(None, ge=0, le=1)
    salience_sensitivity: Optional[float] = Field(None, ge=0, le=1)
    verification_strength: Optional[float] = Field(None, ge=0, le=1)


class CounterfactualRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=8000)
    model: str = Field(default="mock")
    profile_id: Optional[str] = Field(None, description="Baseline profile; defaults to neutral if omitted.")
    overrides: CounterfactualOverrides


class CounterfactualSide(BaseModel):
    answer: str
    pathway: str
    hallucination_risk: float
    confidence: int
    uncertainty_agreement: Optional[float] = None
    parameters_used: dict[str, float]


class CounterfactualResponse(BaseModel):
    baseline: CounterfactualSide
    counterfactual: CounterfactualSide
    confidence_delta: int
    hallucination_risk_delta: float
    pathway_changed: bool
    note: str = "Computational experiment result -- not a claim about the user's real cognition."


# ---------------------------------------------------------------------------
# Research mode: Condition A/B/C comparison
# ---------------------------------------------------------------------------


class ResearchCompareRequest(BaseModel):
    profile_id: Optional[str] = Field(
        None, description="Enrolled, fingerprint-linked profile for Condition C. If omitted, C is identical to B."
    )
    model: str = Field(default="mock")
    categories: Optional[list[str]] = None
    limit_per_category: int = Field(default=3, ge=1, le=10)


class ConditionSummary(BaseModel):
    condition: str = Field(..., description="'A' | 'B' | 'C'")
    label: str
    n: int
    accuracy: Optional[float]
    mean_hallucination_risk: float
    abstention_rate: float


class ResearchCompareResponse(BaseModel):
    conditions: list[ConditionSummary]
    honest_summary: str = Field(
        ..., description="Plainly states whether Condition C showed any measurable benefit over B -- including 'no' if true."
    )
