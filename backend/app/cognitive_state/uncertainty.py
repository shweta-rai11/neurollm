"""Response-consistency uncertainty estimation.

This module implements a SIMPLIFIED, semantic-entropy-INSPIRED uncertainty
estimator. It is explicitly NOT a reproduction of the method or code from:

    Farquhar, S., Kossen, J., Kuhn, L. & Gal, Y.
    "Detecting hallucinations in large language models using semantic
    entropy." Nature 630, 625-630 (2024).

Differences from the original research:
    - The original paper clusters answers using bidirectional entailment
      checks from a dedicated NLI model. This implementation clusters
      answers using either sentence-embedding cosine similarity (when an
      embedding backend is available) or a TF-IDF vector similarity /
      lexical-overlap fallback. This is a much cruder notion of "semantic
      equivalence."
    - The original paper estimates entropy over the model's token-level
      output distribution combined with clustering. This implementation
      estimates entropy purely from the empirical distribution of how many
      sampled answers fall into each similarity cluster -- a proxy, not a
      probability derived from model logits.
    - No calibration against a labeled hallucination benchmark has been
      performed here. Treat the resulting score as a rough, relative
      signal, not a validated probability of correctness.

Pipeline implemented here (see README):
    N candidate answers -> pairwise similarity matrix -> greedy clustering
    -> cluster distribution -> Shannon entropy -> normalize by log(K)
    -> uncertainty_score in [0, 100]
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from difflib import SequenceMatcher

from app.models.schemas import CandidateResponse, UncertaintyResult

_SIMILARITY_CLUSTER_THRESHOLD = 0.55


def _lexical_similarity(a: str, b: str) -> float:
    """Sequence-matcher ratio in [0, 1]. Always available, no dependencies."""
    if not a and not b:
        return 1.0
    return SequenceMatcher(None, a.lower().strip(), b.lower().strip()).ratio()


def _try_tfidf_similarity_matrix(texts: list[str]) -> list[list[float]] | None:
    """Attempt TF-IDF + cosine similarity. Returns None if sklearn/numpy unavailable
    or the corpus is degenerate (e.g. all-empty), triggering the lexical fallback.
    """
    try:
        import numpy as np
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.metrics.pairwise import cosine_similarity
    except ImportError:
        return None

    try:
        non_empty = [t if t.strip() else "empty response" for t in texts]
        vectorizer = TfidfVectorizer(stop_words="english", min_df=1)
        matrix = vectorizer.fit_transform(non_empty)
        if matrix.shape[1] == 0:
            return None
        sim = cosine_similarity(matrix)
        return sim.tolist()
    except ValueError:
        return None


def _lexical_similarity_matrix(texts: list[str]) -> list[list[float]]:
    n = len(texts)
    sim = [[1.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(i + 1, n):
            s = _lexical_similarity(texts[i], texts[j])
            sim[i][j] = s
            sim[j][i] = s
    return sim


def _cluster_by_similarity(sim: list[list[float]], threshold: float) -> list[int]:
    """Greedy union-find style clustering: two candidates join a cluster if
    their pairwise similarity exceeds `threshold`. This avoids requiring a
    pre-specified K (unlike k-means), which matters because the "true"
    number of semantically distinct answers is unknown in advance.
    """
    n = len(sim)
    parent = list(range(n))

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(x: int, y: int) -> None:
        rx, ry = find(x), find(y)
        if rx != ry:
            parent[ry] = rx

    for i in range(n):
        for j in range(i + 1, n):
            if sim[i][j] >= threshold:
                union(i, j)

    roots = [find(i) for i in range(n)]
    unique_roots = sorted(set(roots))
    remap = {r: idx for idx, r in enumerate(unique_roots)}
    return [remap[r] for r in roots]


def _shannon_entropy(cluster_ids: list[int]) -> tuple[float, float, int]:
    """Returns (raw_entropy, normalized_entropy, num_clusters)."""
    n = len(cluster_ids)
    counts: dict[int, int] = {}
    for c in cluster_ids:
        counts[c] = counts.get(c, 0) + 1

    k = len(counts)
    if n == 0 or k <= 1:
        return 0.0, 0.0, max(k, 1)

    probs = [count / n for count in counts.values()]
    h = -sum(p * math.log(p) for p in probs if p > 0)
    h_max = math.log(k)
    h_normalized = h / h_max if h_max > 0 else 0.0
    return h, h_normalized, k


@dataclass
class _SimilarityStats:
    mean_similarity: float
    max_distance: float


def _similarity_stats(sim: list[list[float]]) -> _SimilarityStats:
    n = len(sim)
    if n < 2:
        return _SimilarityStats(mean_similarity=1.0, max_distance=0.0)
    off_diag = [sim[i][j] for i in range(n) for j in range(n) if i != j]
    mean_sim = sum(off_diag) / len(off_diag) if off_diag else 1.0
    max_dist = 1.0 - min(off_diag) if off_diag else 0.0
    return _SimilarityStats(mean_similarity=round(mean_sim, 4), max_distance=round(max_dist, 4))


def estimate_uncertainty(candidates: list[str]) -> UncertaintyResult:
    """Compute semantic-uncertainty-inspired scores over N candidate answers.

    Falls back to a lexical-similarity backend if TF-IDF vectorization is
    unavailable, per the app's "remain usable if optional components fail"
    requirement (see README, Error Handling).
    """
    n = len(candidates)
    if n == 0:
        return UncertaintyResult(
            semantic_uncertainty_score=0,
            response_agreement=100,
            candidate_count=0,
            unique_semantic_clusters=0,
            mean_embedding_similarity=1.0,
            max_embedding_distance=0.0,
            entropy_raw=0.0,
            entropy_normalized=0.0,
            candidates=[],
            method="lexical_fallback",
        )

    method = "tfidf"
    sim = _try_tfidf_similarity_matrix(candidates)
    if sim is None:
        method = "lexical_fallback"
        sim = _lexical_similarity_matrix(candidates)

    cluster_ids = _cluster_by_similarity(sim, _SIMILARITY_CLUSTER_THRESHOLD)
    h_raw, h_normalized, k = _shannon_entropy(cluster_ids)
    stats = _similarity_stats(sim)

    uncertainty_score = int(round(h_normalized * 100))
    agreement_score = max(0, 100 - uncertainty_score)

    return UncertaintyResult(
        semantic_uncertainty_score=uncertainty_score,
        response_agreement=agreement_score,
        candidate_count=n,
        unique_semantic_clusters=k,
        mean_embedding_similarity=stats.mean_similarity,
        max_embedding_distance=stats.max_distance,
        entropy_raw=round(h_raw, 4),
        entropy_normalized=round(h_normalized, 4),
        candidates=[
            CandidateResponse(text=text, cluster_id=cid)
            for text, cid in zip(candidates, cluster_ids)
        ],
        method=method,
    )
