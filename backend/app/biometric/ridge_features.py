"""Ridge orientation, frequency, density, curvature, continuity.

Orientation: gradient structure tensor per block (Hong, Wan & Jain 1998
eq. 5-6; also Bazen & Gerez, "Systematic methods for the computation of the
directional fields and singular points of fingerprints", IEEE TPAMI 2002).
Frequency: x-signature projection along the ridge-perpendicular direction
(Hong, Wan & Jain 1998 section III-C). Both are real per-block measurements
of the actual image, not fabricated numbers.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy import ndimage

from app.biometric.preprocessing import BLOCK_SIZE, largest_component_fraction

_MIN_RIDGE_PERIOD = 3.0
_MAX_RIDGE_PERIOD = 25.0


@dataclass
class RidgeFields:
    orientation: np.ndarray  # radians in [0, pi), one value per block
    coherence: np.ndarray  # [0, 1] per block -- how consistent the local gradient direction is
    frequency: np.ndarray  # ridges per pixel, one value per block (0 where unmeasurable)
    block_size: int


def compute_orientation_field(gray: np.ndarray, block_size: int = BLOCK_SIZE) -> tuple[np.ndarray, np.ndarray]:
    """Per-block ridge orientation and coherence via the gradient structure
    tensor. Ridge orientation is perpendicular to the dominant gradient
    direction, and doubling the angle (the standard trick for a
    pi-periodic quantity) lets per-block tensors be smoothed by simple
    averaging before halving the angle back."""
    gy, gx = np.gradient(gray)

    gxx = gx * gx
    gyy = gy * gy
    gxy = gx * gy

    h, w = gray.shape
    pad_h = (-h) % block_size
    pad_w = (-w) % block_size
    gxx_p = np.pad(gxx, ((0, pad_h), (0, pad_w)))
    gyy_p = np.pad(gyy, ((0, pad_h), (0, pad_w)))
    gxy_p = np.pad(gxy, ((0, pad_h), (0, pad_w)))
    ph, pw = gxx_p.shape

    def block_sum(a: np.ndarray) -> np.ndarray:
        return a.reshape(ph // block_size, block_size, pw // block_size, block_size).sum(axis=(1, 3))

    vxx = block_sum(gxx_p) - block_sum(gyy_p)
    vxy = 2.0 * block_sum(gxy_p)

    # Smooth the doubled-angle vector field so orientation is a coherent
    # local estimate rather than pixel-noise-sensitive.
    vxx = ndimage.uniform_filter(vxx, size=3, mode="nearest")
    vxy = ndimage.uniform_filter(vxy, size=3, mode="nearest")

    orientation = 0.5 * np.arctan2(vxy, vxx) + (np.pi / 2.0)
    orientation = np.mod(orientation, np.pi)

    magnitude = np.sqrt(vxx**2 + vxy**2)
    energy = block_sum(gxx_p) + block_sum(gyy_p)
    coherence = np.divide(magnitude, energy, out=np.zeros_like(magnitude), where=energy > 1e-9)
    coherence = np.clip(coherence, 0.0, 1.0)

    return orientation, coherence


def _x_signature_period(strip: np.ndarray) -> float | None:
    """Ridge period from one strip of pixels sampled perpendicular to ridge
    orientation: average spacing between successive local maxima of the
    smoothed intensity profile (the "x-signature", Hong et al. 1998)."""
    if strip.size < 6:
        return None
    smoothed = ndimage.uniform_filter1d(strip, size=3, mode="nearest")
    peaks = []
    for i in range(1, len(smoothed) - 1):
        if smoothed[i] > smoothed[i - 1] and smoothed[i] >= smoothed[i + 1]:
            peaks.append(i)
    if len(peaks) < 2:
        return None
    spacings = np.diff(peaks)
    return float(np.mean(spacings))


def compute_frequency_field(
    gray: np.ndarray, orientation: np.ndarray, block_size: int = BLOCK_SIZE, window: int = 24
) -> np.ndarray:
    """Per-block ridge frequency (ridges/pixel) from the x-signature method:
    for each block, sample a `window`-long strip of pixels running
    perpendicular to the block's ridge orientation and measure the spacing
    between intensity peaks."""
    h, w = gray.shape
    n_rows, n_cols = orientation.shape
    frequency = np.zeros_like(orientation)

    half = window // 2
    for by in range(n_rows):
        for bx in range(n_cols):
            cy = min(h - 1, int((by + 0.5) * block_size))
            cx = min(w - 1, int((bx + 0.5) * block_size))
            theta = orientation[by, bx]
            # Direction perpendicular to ridge orientation, i.e. along the
            # ridge-to-valley alternation.
            dy, dx = np.cos(theta), -np.sin(theta)

            ts = np.arange(-half, half + 1)
            ys = np.clip(np.round(cy + ts * dy).astype(int), 0, h - 1)
            xs = np.clip(np.round(cx + ts * dx).astype(int), 0, w - 1)
            strip = gray[ys, xs]

            period = _x_signature_period(strip)
            if period is not None and _MIN_RIDGE_PERIOD <= period <= _MAX_RIDGE_PERIOD:
                frequency[by, bx] = 1.0 / period
            # else leave at 0 -- unmeasurable block, not a fabricated guess.

    return frequency


def compute_ridge_fields(gray: np.ndarray, block_size: int = BLOCK_SIZE) -> RidgeFields:
    orientation, coherence = compute_orientation_field(gray, block_size)
    frequency = compute_frequency_field(gray, orientation, block_size)
    return RidgeFields(orientation=orientation, coherence=coherence, frequency=frequency, block_size=block_size)


def ridge_density(fields: RidgeFields, block_mask: np.ndarray) -> float:
    """Mean ridge frequency over foreground blocks with a measurable
    period -- ridges per pixel, a direct real-valued density statistic."""
    valid = block_mask & (fields.frequency > 0)
    if not valid.any():
        return 0.0
    return float(fields.frequency[valid].mean())


def ridge_curvature(fields: RidgeFields, block_mask: np.ndarray) -> float:
    """Local orientation-field variability, in radians -- how much ridge
    direction changes block-to-block within the foreground (arches/whorls
    curve more than plain loops/parallel ridges)."""
    valid = block_mask & (fields.coherence > 0.1)
    if valid.sum() < 2:
        return 0.0
    # Circular variance on the doubled angle (orientation is pi-periodic).
    doubled = 2.0 * fields.orientation[valid]
    mean_vec = np.hypot(np.cos(doubled).mean(), np.sin(doubled).mean())
    return float(1.0 - mean_vec)


def ridge_continuity(mask: np.ndarray) -> float:
    return largest_component_fraction(mask)
