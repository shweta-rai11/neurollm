"""Assembles a fixed-length numeric template from the ridge/minutiae/
singularity/quality features computed elsewhere in this package. This
template -- never the raw image -- is what `app.profile` stores and matches
against (see `app.biometric.matcher`, `app.profile.crypto`).
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from app.biometric.minutiae import MinutiaeResult
from app.biometric.quality import QualityAssessment
from app.biometric.ridge_features import RidgeFields
from app.biometric.singularities import SingularityResult

N_ORIENTATION_BINS = 8
N_FREQUENCY_BINS = 6
_FREQ_MIN, _FREQ_MAX = 1.0 / 25.0, 1.0 / 3.0
PATTERN_CLASSES = ("arch", "loop", "whorl")

VECTOR_LENGTH = N_ORIENTATION_BINS + N_FREQUENCY_BINS + 16 + len(PATTERN_CLASSES) + 8


@dataclass
class FeatureVector:
    orientation_histogram: list[float]
    frequency_histogram: list[float]
    minutiae_distribution_grid: list[float]  # flattened 4x4
    pattern: str
    pattern_confidence: float
    n_cores: int
    n_deltas: int
    n_endings: int
    n_bifurcations: int
    ridge_density: float
    ridge_curvature: float
    orientation_confidence: float  # 0-1
    ridge_visibility: float  # 0-1
    contrast_score: float  # 0-1
    overall_quality: float  # 0-1
    _vector: np.ndarray = field(repr=False)

    def to_vector(self) -> np.ndarray:
        return self._vector

    def to_dict(self) -> dict:
        return {
            "orientation_histogram": self.orientation_histogram,
            "frequency_histogram": self.frequency_histogram,
            "minutiae_distribution_grid": self.minutiae_distribution_grid,
            "pattern": self.pattern,
            "pattern_confidence": self.pattern_confidence,
            "n_cores": self.n_cores,
            "n_deltas": self.n_deltas,
            "n_endings": self.n_endings,
            "n_bifurcations": self.n_bifurcations,
            "ridge_density": self.ridge_density,
            "ridge_curvature": self.ridge_curvature,
        }


def _histogram(values: np.ndarray, weights: np.ndarray, n_bins: int, value_range: tuple[float, float]) -> list[float]:
    if values.size == 0 or weights.sum() <= 0:
        return [0.0] * n_bins
    hist, _ = np.histogram(values, bins=n_bins, range=value_range, weights=weights)
    total = hist.sum()
    if total <= 0:
        return [0.0] * n_bins
    return (hist / total).tolist()


def build_feature_vector(
    fields: RidgeFields,
    block_mask: np.ndarray,
    minutiae: MinutiaeResult,
    singularities: SingularityResult,
    ridge_density: float,
    ridge_curvature: float,
    quality: QualityAssessment,
) -> FeatureVector:
    valid = block_mask & (fields.coherence > 0.1)
    orientation_hist = _histogram(fields.orientation[valid], fields.coherence[valid], N_ORIENTATION_BINS, (0.0, np.pi))

    freq_valid = block_mask & (fields.frequency > 0)
    frequency_hist = _histogram(
        fields.frequency[freq_valid], np.ones(int(freq_valid.sum())), N_FREQUENCY_BINS, (_FREQ_MIN, _FREQ_MAX)
    )

    distribution_grid = minutiae.distribution_grid.flatten().tolist()

    pattern_onehot = [1.0 if singularities.pattern == p else 0.0 for p in PATTERN_CLASSES]

    scalar_block = [
        min(1.0, singularities.n_cores / 4.0),
        min(1.0, singularities.n_deltas / 4.0),
        min(1.0, minutiae.n_endings / 60.0),
        min(1.0, minutiae.n_bifurcations / 60.0),
        min(1.0, ridge_density / 0.3),
        min(1.0, ridge_curvature / 1.0),
        quality.orientation_confidence_pct / 100.0,
        quality.contrast_score,
    ]

    vector = np.array(
        orientation_hist + frequency_hist + distribution_grid + pattern_onehot + scalar_block,
        dtype=np.float32,
    )
    assert vector.shape[0] == VECTOR_LENGTH

    return FeatureVector(
        orientation_histogram=orientation_hist,
        frequency_histogram=frequency_hist,
        minutiae_distribution_grid=distribution_grid,
        pattern=singularities.pattern,
        pattern_confidence=singularities.pattern_confidence,
        n_cores=singularities.n_cores,
        n_deltas=singularities.n_deltas,
        n_endings=minutiae.n_endings,
        n_bifurcations=minutiae.n_bifurcations,
        ridge_density=round(ridge_density, 4),
        ridge_curvature=round(ridge_curvature, 4),
        orientation_confidence=quality.orientation_confidence_pct / 100.0,
        ridge_visibility=quality.ridge_visibility_pct / 100.0,
        contrast_score=quality.contrast_score,
        overall_quality=quality.overall_quality,
        _vector=vector,
    )
