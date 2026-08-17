"""Image-quality metrics computed from the actual uploaded image -- this is
what backs the spec's "Fingerprint detected / Image quality: Good / Ridge
visibility: 94% / Minutiae detected: 42 / Orientation confidence: 91%"
readout. Every number here is derived from a real measurement made
elsewhere in this package (orientation coherence, segmentation, contrast,
sharpness, minutiae count) -- nothing is a placeholder constant.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy import ndimage

from app.biometric.preprocessing import Segmentation, largest_component_fraction
from app.biometric.ridge_features import RidgeFields


def _clamp01(x: float) -> float:
    return float(max(0.0, min(1.0, x)))


@dataclass
class QualityAssessment:
    quality_label: str  # "Good" | "Fair" | "Poor"
    overall_quality: float  # 0-1
    ridge_visibility_pct: float  # 0-100
    orientation_confidence_pct: float  # 0-100
    contrast_score: float  # 0-1
    sharpness_score: float  # 0-1
    segmentation_quality: float  # 0-1
    continuity: float  # 0-1
    minutiae_detected: int


def _contrast_score(gray: np.ndarray, mask: np.ndarray) -> float:
    values = gray[mask] if mask.any() else gray
    std = float(values.std())
    # Well-exposed ridge/valley images typically have std in the ~0.08-0.30
    # range at this normalization; scale so that range maps to ~[0.3, 1.0].
    return _clamp01(std / 0.30)


def _sharpness_score(gray: np.ndarray, mask: np.ndarray) -> float:
    laplacian = ndimage.laplace(gray)
    values = laplacian[mask] if mask.any() else laplacian
    variance = float(values.var())
    return _clamp01(variance / 0.02)


def _segmentation_quality(segmentation: Segmentation) -> float:
    fraction = segmentation.foreground_fraction
    # Penalize segmentations that are implausibly small (mostly background)
    # or implausibly total (segmentation likely failed to separate anything).
    if fraction <= 0.0:
        coverage_score = 0.0
    elif fraction < 0.15:
        coverage_score = fraction / 0.15
    elif fraction > 0.95:
        coverage_score = 1.0 - (fraction - 0.95) / 0.05
    else:
        coverage_score = 1.0
    continuity = largest_component_fraction(segmentation.mask)
    return _clamp01(0.5 * coverage_score + 0.5 * continuity)


def assess_quality(
    gray: np.ndarray,
    segmentation: Segmentation,
    fields: RidgeFields,
    minutiae_count: int,
) -> QualityAssessment:
    valid_blocks = segmentation.block_mask & (fields.coherence > 0)
    orientation_confidence = float(fields.coherence[valid_blocks].mean()) if valid_blocks.any() else 0.0

    contrast = _contrast_score(gray, segmentation.mask)
    sharpness = _sharpness_score(gray, segmentation.mask)
    seg_quality = _segmentation_quality(segmentation)
    continuity = largest_component_fraction(segmentation.mask)

    # Ridge visibility: how distinctly ridge structure stands out, combining
    # orientation coherence (are ridges locally well-defined?), contrast, and
    # segmentation continuity.
    ridge_visibility = _clamp01(0.5 * orientation_confidence + 0.3 * contrast + 0.2 * continuity)

    overall = _clamp01(
        0.30 * orientation_confidence + 0.25 * ridge_visibility + 0.20 * seg_quality
        + 0.15 * contrast + 0.10 * sharpness
    )

    if overall >= 0.70:
        label = "Good"
    elif overall >= 0.45:
        label = "Fair"
    else:
        label = "Poor"

    return QualityAssessment(
        quality_label=label,
        overall_quality=overall,
        ridge_visibility_pct=round(ridge_visibility * 100.0, 1),
        orientation_confidence_pct=round(orientation_confidence * 100.0, 1),
        contrast_score=round(contrast, 3),
        sharpness_score=round(sharpness, 3),
        segmentation_quality=round(seg_quality, 3),
        continuity=round(continuity, 3),
        minutiae_detected=minutiae_count,
    )
