"""Orchestrates biometric enrollment/identification and profile lifecycle.
This is the ONLY place `app.biometric` (fingerprint feature extraction) and
`app.profile` (Individual Computational Profile) meet -- and even here, the
fingerprint is used exclusively as a lookup/personalization key, never as an
input to `virtual_brain_parameters` (see `app.profile.learning` for the only
thing that actually changes those numbers).
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.biometric.matcher import MatchResult, find_match
from app.biometric.pipeline import FingerprintExtractionResult, extract_fingerprint
from app.database.models import BiometricTemplate, ComputationalProfile, ProfileInteraction
from app.profile.crypto import decrypt_template, encrypt_template
from app.profile.learning import InteractionOutcome, apply_interaction, apply_interaction_to_category
from app.profile.params import ComputationalProfileParams, neutral_profile

_MAX_HISTORY_ITEMS = 200


class ConsentRequiredError(ValueError):
    pass


class ProfileNotFoundError(ValueError):
    pass


@dataclass
class EnrollResult:
    profile_id: str
    matched_existing_profile: bool
    match_similarity: float
    extraction: FingerprintExtractionResult
    params: ComputationalProfileParams


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_params(profile_row: ComputationalProfile) -> ComputationalProfileParams:
    return ComputationalProfileParams.from_dict(json.loads(profile_row.virtual_brain_parameters_json))


def _load_task_profiles(profile_row: ComputationalProfile) -> dict[str, ComputationalProfileParams]:
    raw = json.loads(profile_row.task_profiles_json or "{}")
    return {category: ComputationalProfileParams.from_dict(values) for category, values in raw.items()}


def _save_task_profiles(task_profiles: dict[str, ComputationalProfileParams]) -> str:
    return json.dumps({category: params.to_dict() for category, params in task_profiles.items()})


class ProfileService:
    def __init__(self, db: Session):
        self.db = db

    # -- Biometric enrollment / identification (Layer A) --------------------

    def preview_quality(self, image_bytes: bytes) -> FingerprintExtractionResult:
        """Scan-preview only -- no persistence, no profile lookup."""
        return extract_fingerprint(image_bytes)

    def enroll(self, image_bytes: bytes, finger_label: str, consent: bool) -> EnrollResult:
        if not consent:
            raise ConsentRequiredError("consent is required to enroll a fingerprint")

        extraction = extract_fingerprint(image_bytes)
        candidate_vector = extraction.feature_vector.to_vector()

        enrolled_templates = self.db.query(BiometricTemplate).all()
        enrolled_pairs = [(t.profile_id, decrypt_template(t.encrypted_template)) for t in enrolled_templates]
        match: MatchResult = find_match(candidate_vector, enrolled_pairs)

        now = _now()
        matched_existing = match.matched_profile_id is not None

        if matched_existing:
            profile_id = match.matched_profile_id
            profile_row = self.db.get(ComputationalProfile, profile_id)
        else:
            profile_row = ComputationalProfile(
                consent_given=True,
                consent_at=now,
                virtual_brain_parameters_json=json.dumps(neutral_profile().to_dict()),
                task_profiles_json="{}",
                evidence_status="computational_model",
                created_at=now,
                updated_at=now,
            )
            self.db.add(profile_row)
            self.db.flush()  # populate profile_row.profile_id (server-side default)
            profile_id = profile_row.profile_id

        template_row = BiometricTemplate(
            profile_id=profile_id,
            finger_label=finger_label,
            encrypted_template=encrypt_template(candidate_vector),
            quality_json=json.dumps(extraction.quality.__dict__),
            created_at=now,
        )
        self.db.add(template_row)
        self.db.commit()
        self.db.refresh(profile_row)

        return EnrollResult(
            profile_id=profile_id,
            matched_existing_profile=matched_existing,
            match_similarity=match.best_similarity,
            extraction=extraction,
            params=_load_params(profile_row),
        )

    # -- Profile lookup -------------------------------------------------------

    def get_profile_row(self, profile_id: str) -> ComputationalProfile:
        row = self.db.get(ComputationalProfile, profile_id)
        if row is None:
            raise ProfileNotFoundError(profile_id)
        return row

    def get_params(self, profile_id: str) -> ComputationalProfileParams:
        return _load_params(self.get_profile_row(profile_id))

    def get_category_params(self, profile_id: str, category: str) -> ComputationalProfileParams:
        task_profiles = _load_task_profiles(self.get_profile_row(profile_id))
        return task_profiles.get(category, neutral_profile())

    def enrolled_fingers(self, profile_id: str) -> list[BiometricTemplate]:
        return self.db.query(BiometricTemplate).filter(BiometricTemplate.profile_id == profile_id).all()

    # -- Behavioral learning (Layer B) -----------------------------------------

    def record_interaction(
        self,
        profile_id: str,
        query: str,
        task_category: str,
        outcome: InteractionOutcome,
    ) -> ComputationalProfileParams:
        profile_row = self.get_profile_row(profile_id)

        overall = _load_params(profile_row)
        updated_overall = apply_interaction(overall, outcome)

        task_profiles = _load_task_profiles(profile_row)
        category_params = task_profiles.get(task_category, neutral_profile())
        task_profiles[task_category] = apply_interaction_to_category(category_params, outcome)

        now = _now()
        profile_row.virtual_brain_parameters_json = json.dumps(updated_overall.to_dict())
        profile_row.task_profiles_json = _save_task_profiles(task_profiles)
        profile_row.updated_at = now

        self.db.add(
            ProfileInteraction(
                profile_id=profile_id,
                timestamp=now,
                query=query,
                task_category=task_category,
                pathway=outcome.pathway,
                hallucination_risk=outcome.hallucination_risk,
                uncertainty_agreement=outcome.uncertainty_agreement,
                feedback_score=outcome.feedback_score,
                params_snapshot_json=json.dumps(updated_overall.to_dict()),
            )
        )
        self.db.commit()
        return updated_overall

    def apply_feedback(self, profile_id: str, interaction_id: int, feedback_score: float) -> ComputationalProfileParams:
        interaction = self.db.get(ProfileInteraction, interaction_id)
        if interaction is None or interaction.profile_id != profile_id:
            raise ProfileNotFoundError(f"interaction {interaction_id} not found for profile {profile_id}")

        outcome = InteractionOutcome(
            pathway=interaction.pathway,
            hallucination_risk=interaction.hallucination_risk,
            task_complexity=0.5,  # not stored per-interaction; feedback re-weighting relies mainly on feedback_score
            uncertainty_agreement=interaction.uncertainty_agreement,
            feedback_score=feedback_score,
        )
        interaction.feedback_score = feedback_score
        updated = self.record_interaction(profile_id, interaction.query, interaction.task_category, outcome)
        self.db.commit()
        return updated

    def evolution_history(self, profile_id: str) -> dict:
        profile_row = self.get_profile_row(profile_id)
        current = _load_params(profile_row)
        task_profiles = _load_task_profiles(profile_row)

        interactions = (
            self.db.query(ProfileInteraction)
            .filter(ProfileInteraction.profile_id == profile_id)
            .order_by(ProfileInteraction.id.asc())
            .limit(_MAX_HISTORY_ITEMS)
            .all()
        )

        return {
            "initial": neutral_profile().to_dict(),
            "current": current.to_dict(),
            "task_profiles": {category: params.to_dict() for category, params in task_profiles.items()},
            "n_interactions": len(interactions),
            "history": [
                {
                    "timestamp": i.timestamp,
                    "task_category": i.task_category,
                    "pathway": i.pathway,
                    "params_snapshot": json.loads(i.params_snapshot_json),
                }
                for i in interactions
            ],
        }

    # -- Privacy controls (product spec section 17) ---------------------------

    def delete_profile(self, profile_id: str) -> None:
        self.get_profile_row(profile_id)  # raises if missing
        self.db.query(ProfileInteraction).filter(ProfileInteraction.profile_id == profile_id).delete()
        self.db.query(BiometricTemplate).filter(BiometricTemplate.profile_id == profile_id).delete()
        self.db.query(ComputationalProfile).filter(ComputationalProfile.profile_id == profile_id).delete()
        self.db.commit()

    def reset_biometric(self, profile_id: str) -> None:
        """Drops enrolled fingerprint templates only -- the learned
        behavioral profile (Layer B) is kept. Re-enrollment is required
        before this profile can be found again by a fingerprint scan."""
        self.get_profile_row(profile_id)  # raises if missing
        self.db.query(BiometricTemplate).filter(BiometricTemplate.profile_id == profile_id).delete()
        self.db.commit()

    def export_profile(self, profile_id: str) -> dict:
        """Full profile export, JSON-serializable. Never includes raw image
        bytes (never stored) or raw template bytes (only quality metadata)."""
        profile_row = self.get_profile_row(profile_id)
        fingers = self.enrolled_fingers(profile_id)
        interactions = (
            self.db.query(ProfileInteraction).filter(ProfileInteraction.profile_id == profile_id).all()
        )

        return {
            "profile_id": profile_id,
            "evidence_status": profile_row.evidence_status,
            "consent_given": profile_row.consent_given,
            "consent_at": profile_row.consent_at,
            "created_at": profile_row.created_at,
            "updated_at": profile_row.updated_at,
            "virtual_brain_parameters": _load_params(profile_row).to_dict(),
            "task_profiles": {k: v.to_dict() for k, v in _load_task_profiles(profile_row).items()},
            "enrolled_fingers": [
                {
                    "finger_label": f.finger_label,
                    "quality": json.loads(f.quality_json),
                    "created_at": f.created_at,
                }
                for f in fingers
            ],
            "interactions": [
                {
                    "timestamp": i.timestamp,
                    "task_category": i.task_category,
                    "pathway": i.pathway,
                    "hallucination_risk": i.hallucination_risk,
                    "uncertainty_agreement": i.uncertainty_agreement,
                    "feedback_score": i.feedback_score,
                }
                for i in interactions
            ],
        }
