"""Segmentation and normalization -- standard fingerprint preprocessing
steps (Hong, Wan & Jain, "Fingerprint Image Enhancement: Algorithm and
Performance Evaluation", IEEE TPAMI 1998), reimplemented directly against
numpy/scipy rather than a fingerprint library.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy import ndimage

BLOCK_SIZE = 16


@dataclass
class Segmentation:
    mask: np.ndarray  # bool, one value per pixel: True = ridge foreground
    block_mask: np.ndarray  # bool, one value per BLOCK_SIZE x BLOCK_SIZE block
    foreground_fraction: float


def _block_reduce(image: np.ndarray, block_size: int, func) -> np.ndarray:
    """Reduce `image` to one value per `block_size` x `block_size` block by
    `func` (e.g. np.var, np.mean), padding the trailing edge if needed."""
    h, w = image.shape
    pad_h = (-h) % block_size
    pad_w = (-w) % block_size
    padded = np.pad(image, ((0, pad_h), (0, pad_w)), mode="edge")
    ph, pw = padded.shape
    reshaped = padded.reshape(ph // block_size, block_size, pw // block_size, block_size)
    return func(reshaped, axis=(1, 3))


def segment_foreground(gray: np.ndarray, block_size: int = BLOCK_SIZE) -> Segmentation:
    """Block-variance foreground segmentation: ridge/valley structure has
    measurably higher local variance than blank background/paper, so blocks
    below a variance threshold (fraction of the image's overall block-variance
    range) are classified as background."""
    block_var = _block_reduce(gray, block_size, np.var)
    v_min, v_max = float(block_var.min()), float(block_var.max())
    if v_max - v_min < 1e-9:
        # Perfectly flat image -- nothing looks like ridge structure anywhere.
        block_mask = np.zeros_like(block_var, dtype=bool)
    else:
        threshold = v_min + 0.10 * (v_max - v_min)
        block_mask = block_var > threshold

    mask = np.kron(block_mask, np.ones((block_size, block_size), dtype=bool))
    mask = mask[: gray.shape[0], : gray.shape[1]]

    foreground_fraction = float(block_mask.mean()) if block_mask.size else 0.0
    return Segmentation(mask=mask, block_mask=block_mask, foreground_fraction=foreground_fraction)


def normalize(gray: np.ndarray, target_mean: float = 0.5, target_var: float = 0.02) -> np.ndarray:
    """Hong et al.'s normalization: rescale pixel intensities to a fixed
    mean/variance so downstream orientation/frequency estimation isn't
    sensitive to scanner/camera brightness or contrast differences."""
    mean = float(gray.mean())
    var = float(gray.var())
    if var < 1e-9:
        return np.full_like(gray, target_mean)

    deviation = np.sqrt(target_var * ((gray - mean) ** 2) / var)
    normalized = np.where(gray > mean, target_mean + deviation, target_mean - deviation)
    return np.clip(normalized, 0.0, 1.0)


def largest_component_fraction(mask: np.ndarray) -> float:
    """Fraction of the foreground mask occupied by its single largest
    connected component -- a real measure of ridge-structure continuity
    (fragmented/noisy segmentation produces many small disjoint blobs)."""
    if not mask.any():
        return 0.0
    labeled, n_components = ndimage.label(mask)
    if n_components == 0:
        return 0.0
    sizes = ndimage.sum(mask, labeled, index=range(1, n_components + 1))
    return float(np.max(sizes) / mask.sum())
