"""Minutiae extraction via the crossing-number method (standard fingerprint
literature, e.g. Maltoni, Maio, Jain & Prabhakar, "Handbook of Fingerprint
Recognition", 2nd ed., section 4.4): on the 1-pixel-wide skeleton, a ridge
pixel's crossing number over its 8-neighborhood classifies it as a ridge
ending (CN=1) or bifurcation (CN=3).
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from app.biometric.ridge_features import RidgeFields

_BORDER_MARGIN = 10  # px -- skeleton artifacts near image edges aren't real minutiae
_MIN_SEPARATION = 6  # px -- suppress duplicate detections from the same ridge feature
_GRID_SIZE = 4  # spatial distribution histogram is _GRID_SIZE x _GRID_SIZE


@dataclass
class Minutia:
    x: int
    y: int
    kind: str  # "ending" | "bifurcation"
    orientation_rad: float


@dataclass
class MinutiaeResult:
    minutiae: list[Minutia]
    n_endings: int
    n_bifurcations: int
    distribution_grid: np.ndarray  # _GRID_SIZE x _GRID_SIZE, fraction of minutiae per cell


def _crossing_numbers(skeleton: np.ndarray) -> np.ndarray:
    padded = np.pad(skeleton.astype(np.int32), 1, mode="constant", constant_values=0)
    p2 = padded[0:-2, 1:-1]
    p3 = padded[0:-2, 2:]
    p4 = padded[1:-1, 2:]
    p5 = padded[2:, 2:]
    p6 = padded[2:, 1:-1]
    p7 = padded[2:, 0:-2]
    p8 = padded[1:-1, 0:-2]
    p9 = padded[0:-2, 0:-2]
    seq = [p2, p3, p4, p5, p6, p7, p8, p9, p2]

    cn = np.zeros(skeleton.shape, dtype=np.float64)
    for i in range(8):
        cn += np.abs(seq[i] - seq[i + 1])
    return cn / 2.0


def _orientation_at(fields: RidgeFields, x: int, y: int) -> float:
    by = min(fields.orientation.shape[0] - 1, y // fields.block_size)
    bx = min(fields.orientation.shape[1] - 1, x // fields.block_size)
    return float(fields.orientation[by, bx])


def _suppress_close_duplicates(points: list[tuple[int, int, str]], min_separation: int) -> list[tuple[int, int, str]]:
    kept: list[tuple[int, int, str]] = []
    for x, y, kind in points:
        if all((x - kx) ** 2 + (y - ky) ** 2 >= min_separation**2 for kx, ky, _ in kept):
            kept.append((x, y, kind))
    return kept


def extract_minutiae(skeleton: np.ndarray, mask: np.ndarray, fields: RidgeFields) -> MinutiaeResult:
    h, w = skeleton.shape
    cn = _crossing_numbers(skeleton)

    valid = np.zeros_like(mask)
    valid[_BORDER_MARGIN : h - _BORDER_MARGIN, _BORDER_MARGIN : w - _BORDER_MARGIN] = True
    valid &= mask

    ys_e, xs_e = np.nonzero((skeleton == 1) & valid & (np.isclose(cn, 1.0)))
    ys_b, xs_b = np.nonzero((skeleton == 1) & valid & (np.isclose(cn, 3.0)))

    candidates: list[tuple[int, int, str]] = [(int(x), int(y), "ending") for y, x in zip(ys_e, xs_e)]
    candidates += [(int(x), int(y), "bifurcation") for y, x in zip(ys_b, xs_b)]

    kept = _suppress_close_duplicates(candidates, _MIN_SEPARATION)

    minutiae = [Minutia(x=x, y=y, kind=kind, orientation_rad=_orientation_at(fields, x, y)) for x, y, kind in kept]

    grid = np.zeros((_GRID_SIZE, _GRID_SIZE), dtype=np.float64)
    for m in minutiae:
        gy = min(_GRID_SIZE - 1, int(m.y / max(1, h) * _GRID_SIZE))
        gx = min(_GRID_SIZE - 1, int(m.x / max(1, w) * _GRID_SIZE))
        grid[gy, gx] += 1.0
    if minutiae:
        grid /= len(minutiae)

    return MinutiaeResult(
        minutiae=minutiae,
        n_endings=sum(1 for m in minutiae if m.kind == "ending"),
        n_bifurcations=sum(1 for m in minutiae if m.kind == "bifurcation"),
        distribution_grid=grid,
    )
