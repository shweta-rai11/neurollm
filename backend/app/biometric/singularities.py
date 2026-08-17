"""Singular points (core/delta) via the Poincare index (Kawagoe & Tojo,
"Fingerprint pattern classification", Pattern Recognition 17(3), 1984), and
pattern classification (arch/loop/whorl) from the resulting core/delta
count -- the standard rule used throughout the fingerprint-classification
literature (see also Maltoni et al., Handbook of Fingerprint Recognition,
section 3.2).
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

_CORE_DELTA_INDEX_THRESHOLD = 0.35  # a clean core/delta scores close to +-0.5
_CLUSTER_MIN_BLOCK_DISTANCE = 2  # suppress duplicate detections of the same singularity


@dataclass
class Singularity:
    block_y: int
    block_x: int
    kind: str  # "core" | "delta"
    index: float


@dataclass
class SingularityResult:
    singularities: list[Singularity]
    n_cores: int
    n_deltas: int
    pattern: str  # "arch" | "loop" | "whorl"
    pattern_confidence: float


def _poincare_index(orientation: np.ndarray, by: int, bx: int) -> float:
    """Sum of consecutive orientation differences around the 8-neighborhood
    of block (by, bx), each wrapped into (-pi/2, pi/2] to account for
    orientation being defined only modulo pi. The total is (up to floating
    point) a multiple of pi; dividing by 2*pi gives the Poincare index."""
    loop = [
        orientation[by - 1, bx],
        orientation[by - 1, bx + 1],
        orientation[by, bx + 1],
        orientation[by + 1, bx + 1],
        orientation[by + 1, bx],
        orientation[by + 1, bx - 1],
        orientation[by, bx - 1],
        orientation[by - 1, bx - 1],
        orientation[by - 1, bx],
    ]
    total = 0.0
    for k in range(8):
        diff = loop[k + 1] - loop[k]
        if diff < -np.pi / 2:
            diff += np.pi
        elif diff > np.pi / 2:
            diff -= np.pi
        total += diff
    return total / (2.0 * np.pi)


def find_singularities(orientation: np.ndarray, block_mask: np.ndarray, coherence: np.ndarray) -> list[Singularity]:
    n_rows, n_cols = orientation.shape
    raw: list[Singularity] = []

    for by in range(1, n_rows - 1):
        for bx in range(1, n_cols - 1):
            if not block_mask[by, bx] or coherence[by, bx] < 0.15:
                continue
            index = _poincare_index(orientation, by, bx)
            if index >= _CORE_DELTA_INDEX_THRESHOLD:
                raw.append(Singularity(block_y=by, block_x=bx, kind="core", index=float(index)))
            elif index <= -_CORE_DELTA_INDEX_THRESHOLD:
                raw.append(Singularity(block_y=by, block_x=bx, kind="delta", index=float(index)))

    # Greedy suppression: a real singularity typically triggers a small
    # cluster of adjacent high-index blocks -- keep the strongest of each
    # cluster rather than counting every block in it separately.
    raw.sort(key=lambda s: abs(s.index), reverse=True)
    kept: list[Singularity] = []
    for s in raw:
        if all(
            (s.block_y - k.block_y) ** 2 + (s.block_x - k.block_x) ** 2 >= _CLUSTER_MIN_BLOCK_DISTANCE**2
            for k in kept
        ):
            kept.append(s)
    return kept


def classify_pattern(singularities: list[Singularity]) -> tuple[str, float]:
    """Standard core/delta-count classification rule. `pattern_confidence`
    reflects how cleanly the singularity count matches a canonical pattern
    (0/0, 1/1, or >=2/>=2) rather than a fabricated certainty."""
    n_cores = sum(1 for s in singularities if s.kind == "core")
    n_deltas = sum(1 for s in singularities if s.kind == "delta")

    if n_cores == 0 and n_deltas == 0:
        return "arch", 0.75
    if n_cores >= 2 and n_deltas >= 2:
        return "whorl", 0.8 if (n_cores == 2 and n_deltas == 2) else 0.55
    if n_cores >= 1 and n_deltas >= 1:
        return "loop", 0.8 if (n_cores == 1 and n_deltas == 1) else 0.55
    # A core with no delta (or vice versa) is an ambiguous/partial capture --
    # report the closer canonical pattern with reduced confidence rather
    # than a confident but unjustified label.
    return ("loop" if (n_cores + n_deltas) > 0 else "arch"), 0.35


def analyze_singularities(orientation: np.ndarray, block_mask: np.ndarray, coherence: np.ndarray) -> SingularityResult:
    singularities = find_singularities(orientation, block_mask, coherence)
    pattern, confidence = classify_pattern(singularities)
    return SingularityResult(
        singularities=singularities,
        n_cores=sum(1 for s in singularities if s.kind == "core"),
        n_deltas=sum(1 for s in singularities if s.kind == "delta"),
        pattern=pattern,
        pattern_confidence=confidence,
    )
