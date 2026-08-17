"""Tests for app.biometric -- the real fingerprint feature-extraction
pipeline. Verifies determinism, discriminability, and that every
quality/minutiae/pattern field is actually computed (present, in-range)
rather than a fabricated placeholder.
"""
from __future__ import annotations

import numpy as np

from app.biometric.image_io import InvalidImageError, decode_image_bytes
from app.biometric.pipeline import extract_fingerprint
from tests._helpers import synthetic_fingerprint_bytes


def test_decode_rejects_garbage_bytes():
    try:
        decode_image_bytes(b"not an image")
        assert False, "expected InvalidImageError"
    except InvalidImageError:
        pass


def test_extraction_is_deterministic():
    data = synthetic_fingerprint_bytes(seed=1)
    r1 = extract_fingerprint(data)
    r2 = extract_fingerprint(data)
    assert np.array_equal(r1.feature_vector.to_vector(), r2.feature_vector.to_vector())


def test_different_images_produce_different_templates():
    r1 = extract_fingerprint(synthetic_fingerprint_bytes(seed=1))
    r2 = extract_fingerprint(synthetic_fingerprint_bytes(seed=99))
    assert not np.array_equal(r1.feature_vector.to_vector(), r2.feature_vector.to_vector())


def test_quality_fields_are_computed_and_in_range():
    # Seed 5 lands on the spiral-pattern branch (see synthetic_fingerprint_bytes),
    # which reliably produces ridge endings/bifurcations to detect -- a purely
    # parallel-ridge pattern (even seeds) can legitimately have zero minutiae.
    result = extract_fingerprint(synthetic_fingerprint_bytes(seed=5))
    q = result.quality
    assert q.quality_label in {"Good", "Fair", "Poor"}
    assert 0.0 <= q.overall_quality <= 1.0
    assert 0.0 <= q.ridge_visibility_pct <= 100.0
    assert 0.0 <= q.orientation_confidence_pct <= 100.0
    assert q.minutiae_detected >= 0
    # A real ridge-like pattern should not be flagged as "no structure at all".
    assert q.minutiae_detected > 0


def test_pattern_classification_is_one_of_the_three_classes():
    result = extract_fingerprint(synthetic_fingerprint_bytes(seed=3))
    assert result.singularities.pattern in {"arch", "loop", "whorl"}
    assert 0.0 <= result.singularities.pattern_confidence <= 1.0


def test_blank_image_is_flagged_low_quality_not_fabricated_minutiae():
    blank = np.full((80, 80), 128, dtype=np.uint8)
    import io as _io

    from PIL import Image

    buf = _io.BytesIO()
    Image.fromarray(blank, mode="L").save(buf, format="PNG")

    result = extract_fingerprint(buf.getvalue())
    assert result.quality.quality_label == "Poor"
    assert result.quality.minutiae_detected == 0


def test_feature_vector_length_matches_declared_constant():
    from app.biometric.feature_vector import VECTOR_LENGTH

    result = extract_fingerprint(synthetic_fingerprint_bytes(seed=4))
    assert result.feature_vector.to_vector().shape[0] == VECTOR_LENGTH
