"""ORM models.

For the MVP, a single `AnalysisRecord` table pragmatically consolidates
what would otherwise be a conceptual requests/responses/cognitive_states/
experiments split. Each row stores everything needed to reconstruct a past
analysis: the query, model/provider used, the raw answer, the uncertainty
result (when computed), and the full cognitive state (brain/hormone
signals, confidence, difficulty, verification need) as JSON. No API keys
or other secrets are ever stored here.
"""
from __future__ import annotations

import uuid

from sqlalchemy import Float, ForeignKey, Integer, LargeBinary, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.database import Base


class AnalysisRecord(Base):
    __tablename__ = "analysis_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    timestamp: Mapped[str] = mapped_column(String, nullable=False)
    kind: Mapped[str] = mapped_column(String, nullable=False)  # "chat" | "experiment_side"
    query: Mapped[str] = mapped_column(Text, nullable=False)
    model: Mapped[str] = mapped_column(String, nullable=False)
    provider: Mapped[str] = mapped_column(String, nullable=False)
    answer: Mapped[str] = mapped_column(Text, nullable=False)
    pathway: Mapped[str] = mapped_column(String, nullable=False, default="DIRECT")
    hallucination_risk: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    task_analysis_json: Mapped[str] = mapped_column(Text, nullable=False)
    cognitive_state_json: Mapped[str] = mapped_column(Text, nullable=False)
    uncertainty_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    duration_ms: Mapped[int] = mapped_column(Integer, nullable=False)


def _new_uuid() -> str:
    return str(uuid.uuid4())


class ComputationalProfile(Base):
    """The Individual Computational Profile itself (product spec section 5).

    `virtual_brain_parameters_json` stores the overall `ComputationalProfileParams`;
    `task_profiles_json` stores the same shape per task category (spec
    section 14). Both start at neutral (0.5) defaults on creation and only
    move via `app.profile.learning` -- never from biometric features.
    """

    __tablename__ = "computational_profiles"

    profile_id: Mapped[str] = mapped_column(String, primary_key=True, default=_new_uuid)
    consent_given: Mapped[bool] = mapped_column(nullable=False, default=False)
    consent_at: Mapped[str | None] = mapped_column(String, nullable=True)
    virtual_brain_parameters_json: Mapped[str] = mapped_column(Text, nullable=False)
    task_profiles_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    evidence_status: Mapped[str] = mapped_column(String, nullable=False, default="computational_model")
    created_at: Mapped[str] = mapped_column(String, nullable=False)
    updated_at: Mapped[str] = mapped_column(String, nullable=False)


class BiometricTemplate(Base):
    """A single enrolled fingerprint template. `encrypted_template` is a
    Fernet-encrypted serialized `FeatureVector` (see app/profile/crypto.py)
    -- the raw image is never persisted anywhere in this app."""

    __tablename__ = "biometric_templates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    profile_id: Mapped[str] = mapped_column(String, ForeignKey("computational_profiles.profile_id"), nullable=False)
    finger_label: Mapped[str] = mapped_column(String, nullable=False)
    encrypted_template: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    quality_json: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[str] = mapped_column(String, nullable=False)


class ProfileInteraction(Base):
    """One recorded interaction used as a behavioral-learning data point
    (product spec section 6) -- also the raw material for the Profile
    Evolution view's before/after chart."""

    __tablename__ = "profile_interactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    profile_id: Mapped[str] = mapped_column(String, ForeignKey("computational_profiles.profile_id"), nullable=False)
    timestamp: Mapped[str] = mapped_column(String, nullable=False)
    query: Mapped[str] = mapped_column(Text, nullable=False)
    task_category: Mapped[str] = mapped_column(String, nullable=False)
    pathway: Mapped[str] = mapped_column(String, nullable=False)
    hallucination_risk: Mapped[float] = mapped_column(Float, nullable=False)
    uncertainty_agreement: Mapped[float | None] = mapped_column(Float, nullable=True)
    feedback_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    params_snapshot_json: Mapped[str] = mapped_column(Text, nullable=False)
