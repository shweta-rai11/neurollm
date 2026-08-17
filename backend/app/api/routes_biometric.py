"""Biometric identity lifecycle: scan preview, enrollment, and the privacy
controls required for handling fingerprint data (product spec section 17).

Every fingerprint image is processed in-memory for the duration of one
request and discarded -- only the derived, encrypted feature-vector
template (never the raw image) is persisted. See `app.biometric.pipeline`
for the extraction algorithms and `app.profile.service.ProfileService` for
what's actually stored.
"""
from __future__ import annotations

import json

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.biometric.image_io import InvalidImageError
from app.biometric.pipeline import FingerprintExtractionResult
from app.database.database import get_db
from app.models.profile_schemas import (
    ComputationalProfileOut,
    DeleteProfileResponse,
    EnrollResponse,
    ExportProfileResponse,
    FingerprintQuality,
    FingerprintScanSummary,
    QualityCheckResponse,
    ResetBiometricResponse,
)
from app.profile.service import ConsentRequiredError, ProfileNotFoundError, ProfileService

router = APIRouter(prefix="/biometric", tags=["biometric"])

_MAX_UPLOAD_BYTES = 8 * 1024 * 1024


async def _read_upload(file: UploadFile) -> bytes:
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="empty file upload")
    if len(data) > _MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="fingerprint image too large")
    return data


def _scan_summary(extraction: FingerprintExtractionResult) -> FingerprintScanSummary:
    q = extraction.quality
    return FingerprintScanSummary(
        quality=FingerprintQuality(
            quality_label=q.quality_label,
            overall_quality=q.overall_quality,
            ridge_visibility_pct=q.ridge_visibility_pct,
            orientation_confidence_pct=q.orientation_confidence_pct,
            contrast_score=q.contrast_score,
            sharpness_score=q.sharpness_score,
            segmentation_quality=q.segmentation_quality,
            continuity=q.continuity,
            minutiae_detected=q.minutiae_detected,
        ),
        pattern=extraction.singularities.pattern,
        pattern_confidence=extraction.singularities.pattern_confidence,
        n_cores=extraction.singularities.n_cores,
        n_deltas=extraction.singularities.n_deltas,
        n_endings=extraction.minutiae.n_endings,
        n_bifurcations=extraction.minutiae.n_bifurcations,
        image_width=extraction.image_width,
        image_height=extraction.image_height,
    )


@router.post("/quality-check", response_model=QualityCheckResponse)
async def quality_check(file: UploadFile = File(...), db: Session = Depends(get_db)) -> QualityCheckResponse:
    data = await _read_upload(file)
    service = ProfileService(db)
    try:
        extraction = service.preview_quality(data)
    except InvalidImageError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return QualityCheckResponse(scan=_scan_summary(extraction))


@router.post("/enroll", response_model=EnrollResponse)
async def enroll(
    file: UploadFile = File(...),
    finger_label: str = Form(...),
    consent: bool = Form(...),
    db: Session = Depends(get_db),
) -> EnrollResponse:
    data = await _read_upload(file)
    service = ProfileService(db)
    try:
        result = service.enroll(data, finger_label=finger_label, consent=consent)
    except ConsentRequiredError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except InvalidImageError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    return EnrollResponse(
        profile_id=result.profile_id,
        matched_existing_profile=result.matched_existing_profile,
        match_similarity=result.match_similarity,
        scan=_scan_summary(result.extraction),
        virtual_brain_parameters=result.params.to_dict(),
    )


@router.get("/profile/{profile_id}", response_model=ComputationalProfileOut)
async def get_profile(profile_id: str, db: Session = Depends(get_db)) -> ComputationalProfileOut:
    service = ProfileService(db)
    try:
        row = service.get_profile_row(profile_id)
    except ProfileNotFoundError:
        raise HTTPException(status_code=404, detail=f"profile {profile_id} not found")

    return ComputationalProfileOut(
        profile_id=row.profile_id,
        consent_given=row.consent_given,
        created_at=row.created_at,
        updated_at=row.updated_at,
        evidence_status=row.evidence_status,
        virtual_brain_parameters=json.loads(row.virtual_brain_parameters_json),
        task_profiles=json.loads(row.task_profiles_json or "{}"),
        enrolled_finger_count=len(service.enrolled_fingers(profile_id)),
    )


@router.delete("/profile/{profile_id}", response_model=DeleteProfileResponse)
async def delete_profile(profile_id: str, db: Session = Depends(get_db)) -> DeleteProfileResponse:
    service = ProfileService(db)
    try:
        service.delete_profile(profile_id)
    except ProfileNotFoundError:
        raise HTTPException(status_code=404, detail=f"profile {profile_id} not found")
    return DeleteProfileResponse(deleted=True)


@router.get("/profile/{profile_id}/export", response_model=ExportProfileResponse)
async def export_profile(profile_id: str, db: Session = Depends(get_db)) -> ExportProfileResponse:
    service = ProfileService(db)
    try:
        export = service.export_profile(profile_id)
    except ProfileNotFoundError:
        raise HTTPException(status_code=404, detail=f"profile {profile_id} not found")
    return ExportProfileResponse(export=export)


@router.post("/profile/{profile_id}/reset", response_model=ResetBiometricResponse)
async def reset_biometric(profile_id: str, db: Session = Depends(get_db)) -> ResetBiometricResponse:
    service = ProfileService(db)
    try:
        service.reset_biometric(profile_id)
    except ProfileNotFoundError:
        raise HTTPException(status_code=404, detail=f"profile {profile_id} not found")
    return ResetBiometricResponse(reset=True)
