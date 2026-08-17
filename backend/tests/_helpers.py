"""Shared test-only builders for TaskAnalysis / UncertaintyResult / synthetic
ActivationSummary fixtures. Kept out of conftest.py since these are plain
factory functions, not pytest fixtures/hooks.
"""
from __future__ import annotations

import io

import numpy as np
from PIL import Image

from app.activations.features import ActivationSummary
from app.models.schemas import TaskAnalysis, UncertaintyResult


def task(**overrides) -> TaskAnalysis:
    base = dict(
        complexity=20,
        logical_reasoning=20,
        creativity=20,
        planning=20,
        context_dependency=20,
        verification_requirement=20,
        risk=20,
        ambiguity=20,
        factuality_requirement=20,
    )
    base.update(overrides)
    return TaskAnalysis(**base)


def uncertainty(score: int, agreement: int | None = None, clusters: int = 3, candidates=None) -> UncertaintyResult:
    return UncertaintyResult(
        semantic_uncertainty_score=score,
        response_agreement=agreement if agreement is not None else max(0, 100 - score),
        candidate_count=5,
        unique_semantic_clusters=clusters,
        mean_embedding_similarity=0.5,
        max_embedding_distance=0.5,
        entropy_raw=1.0,
        entropy_normalized=score / 100.0,
        candidates=candidates or [],
        method="tfidf",
    )


class FakeActivationExtractor:
    """Deterministic stand-in for LocalHFActivationExtractor -- lets API
    integration tests exercise research_mode / the local_hf pathway without
    downloading or loading the real Qwen model."""

    def capture(self, prompt: str, max_new_tokens: int = 200):
        from app.activations.extractor import ActivationCapture

        answer = f"[fake local answer for: {prompt[:40]}]"
        capture = ActivationCapture(
            num_layers=4,
            vocab_size=32000,
            num_prompt_tokens=8,
            num_generated_tokens=5,
            layer_hidden_norms=[1.0, 2.0, 3.0, 4.0, 5.0],
            layer_attention_entropy=[0.7, 0.6, 0.5, 0.4],
            token_entropies=[0.2, 0.3, 0.25, 0.2, 0.3],
            token_prob_margins=[0.6, 0.55, 0.6, 0.65, 0.6],
            token_top1_probs=[0.8, 0.78, 0.8, 0.82, 0.8],
        )
        return answer, capture

    def generate_text(self, prompt: str, max_new_tokens: int = 150, temperature: float = 0.8) -> str:
        return f"[fake local candidate for: {prompt[:40]}]"


class FakeLocalProvider:
    """Test double for LocalHFProvider -- same public shape
    (get_activation_extractor/generate/generate_multiple/get_model_info)
    without any torch/transformers dependency."""

    def __init__(self):
        self._extractor = FakeActivationExtractor()

    def get_activation_extractor(self):
        return self._extractor

    async def generate(self, query: str) -> str:
        answer, _capture = self._extractor.capture(query)
        return answer

    async def generate_multiple(self, query: str, n: int) -> list[str]:
        return [self._extractor.generate_text(query) for _ in range(n)]

    def get_model_info(self) -> dict:
        return {"name": "fake-local", "provider": "local_hf", "description": "test double for LocalHFProvider"}


def synthetic_fingerprint_bytes(seed: int = 0, w: int = 200, h: int = 200) -> bytes:
    """A deterministic, seeded sinusoidal ridge-like pattern (a spiral phase
    field, which produces a real singularity for the pattern classifier to
    find) encoded as a PNG -- a stand-in for a real fingerprint scan so
    `app.biometric` tests don't depend on external image fixtures.

    The same `seed` always reproduces the same bytes. A full spiral phase
    field samples ridge orientation almost uniformly across [0, pi)
    regardless of its rotation/tightness/center, which made early versions
    of this helper produce different-seed images whose orientation
    histograms (a big chunk of the feature vector) were accidentally
    cosine-similar enough to trigger the identity matcher -- so seeds
    alternate between a parallel-ridge pattern (orientation concentrated in
    one histogram bin, angle varied widely per seed) and a spiral pattern,
    which are far more separated in feature space, closer to how distinct
    real fingerprints actually differ.
    """
    rng = np.random.default_rng(seed)
    yy, xx = np.mgrid[0:h, 0:w]

    if seed % 2 == 0:
        angle = rng.uniform(0.0, np.pi)
        freq = rng.uniform(0.15, 0.35)
        projected = xx * np.cos(angle) + yy * np.sin(angle)
        phase = projected * freq
    else:
        freq = rng.uniform(0.10, 0.24)
        spiral_tightness = rng.uniform(0.4, 2.6)
        angle_offset = rng.uniform(0.0, 2 * np.pi)
        cx = w / 2 + rng.uniform(-25, 25)
        cy = h / 2 + rng.uniform(-25, 25)
        dx, dy = xx - cx, yy - cy
        r = np.sqrt(dx**2 + dy**2) + 1e-6
        theta = np.arctan2(dy, dx)
        phase = (r * freq) + theta * spiral_tightness + angle_offset

    img = 0.5 + 0.35 * np.sin(phase)
    img += rng.normal(0, 0.02, size=img.shape)
    img = np.clip(img, 0, 1)
    arr8 = (img * 255).astype(np.uint8)
    buf = io.BytesIO()
    Image.fromarray(arr8, mode="L").save(buf, format="PNG")
    return buf.getvalue()


def activation_summary(**overrides) -> ActivationSummary:
    base = dict(
        early_layer_hidden_norm=10.0,
        mid_layer_hidden_norm=12.0,
        late_layer_hidden_norm=14.0,
        hidden_norm_growth_ratio=0.4,
        early_layer_attention_entropy=0.6,
        late_layer_attention_entropy=0.4,
        mean_attention_entropy=0.5,
        mean_token_entropy=1.5,
        max_token_entropy=3.0,
        token_entropy_normalized=0.2,
        mean_prob_margin=0.5,
        min_prob_margin=0.1,
        num_generated_tokens=40,
    )
    base.update(overrides)
    return ActivationSummary(**base)
