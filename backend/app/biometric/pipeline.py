"""Top-level orchestration: uploaded image bytes -> feature vector template.

This is the pipeline referenced in the product spec:

    Fingerprint image -> Preprocessing -> Segmentation -> Ridge enhancement
    -> Skeletonization -> Minutiae extraction -> Feature vector

The single entry point, `extract_fingerprint`, is the only function
`app.profile.service.ProfileService` calls into this package with.
"""
from __future__ import annotations

from dataclasses import dataclass

from app.biometric.enhancement import binarize, enhance
from app.biometric.feature_vector import FeatureVector, build_feature_vector
from app.biometric.image_io import decode_image_bytes
from app.biometric.minutiae import MinutiaeResult, extract_minutiae
from app.biometric.preprocessing import normalize, segment_foreground
from app.biometric.quality import QualityAssessment, assess_quality
from app.biometric.ridge_features import compute_ridge_fields, ridge_continuity, ridge_curvature, ridge_density
from app.biometric.singularities import SingularityResult, analyze_singularities
from app.biometric.skeletonize import zhang_suen_thin


@dataclass
class FingerprintExtractionResult:
    quality: QualityAssessment
    minutiae: MinutiaeResult
    singularities: SingularityResult
    feature_vector: FeatureVector
    continuity: float
    image_width: int
    image_height: int


def extract_fingerprint(image_bytes: bytes) -> FingerprintExtractionResult:
    gray = decode_image_bytes(image_bytes)
    segmentation = segment_foreground(gray)
    normalized = normalize(gray)

    fields = compute_ridge_fields(normalized)
    density = ridge_density(fields, segmentation.block_mask)
    curvature = ridge_curvature(fields, segmentation.block_mask)
    continuity = ridge_continuity(segmentation.mask)

    enhanced = enhance(normalized, fields, segmentation.block_mask)
    binary = binarize(enhanced, segmentation.mask)
    skeleton = zhang_suen_thin(binary)

    minutiae_result = extract_minutiae(skeleton, segmentation.mask, fields)
    singularity_result = analyze_singularities(fields.orientation, segmentation.block_mask, fields.coherence)

    quality = assess_quality(gray, segmentation, fields, len(minutiae_result.minutiae))

    feature_vector = build_feature_vector(
        fields=fields,
        block_mask=segmentation.block_mask,
        minutiae=minutiae_result,
        singularities=singularity_result,
        ridge_density=density,
        ridge_curvature=curvature,
        quality=quality,
    )

    height, width = gray.shape
    return FingerprintExtractionResult(
        quality=quality,
        minutiae=minutiae_result,
        singularities=singularity_result,
        feature_vector=feature_vector,
        continuity=continuity,
        image_width=width,
        image_height=height,
    )
