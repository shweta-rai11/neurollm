"""Gabor-filter ridge enhancement and binarization (Hong, Wan & Jain 1998,
section III-D): each block is convolved with a Gabor kernel tuned to that
block's own measured orientation/frequency, which sharpens ridge/valley
contrast enough for reliable skeletonization and minutiae extraction.
"""
from __future__ import annotations

import numpy as np
from scipy import ndimage

from app.biometric.preprocessing import BLOCK_SIZE
from app.biometric.ridge_features import RidgeFields

_KERNEL_SIZE = 11  # odd, in pixels
_SIGMA = 4.0
_DEFAULT_FREQUENCY = 1.0 / 10.0  # used where a block's frequency is unmeasurable


def _gabor_kernel(frequency: float, orientation: float, size: int = _KERNEL_SIZE, sigma: float = _SIGMA) -> np.ndarray:
    half = size // 2
    y, x = np.mgrid[-half : half + 1, -half : half + 1]
    # Rotate coordinates into the ridge-aligned frame: x' along the ridge,
    # y' across it (the sinusoidal carrier runs along y').
    x_theta = x * np.cos(orientation) + y * np.sin(orientation)
    y_theta = -x * np.sin(orientation) + y * np.cos(orientation)
    gaussian = np.exp(-0.5 * (x_theta**2 + y_theta**2) / sigma**2)
    carrier = np.cos(2.0 * np.pi * frequency * y_theta)
    kernel = gaussian * carrier
    kernel -= kernel.mean()  # zero-DC so uniform regions aren't biased
    return kernel


def enhance(gray: np.ndarray, fields: RidgeFields, block_mask: np.ndarray) -> np.ndarray:
    """Block-wise Gabor filtering: each block of the (padded) image is
    convolved with a kernel matched to that block's orientation/frequency."""
    block_size = fields.block_size
    h, w = gray.shape
    pad = _KERNEL_SIZE // 2
    padded = np.pad(gray, pad, mode="reflect")
    out = np.zeros_like(gray)

    n_rows, n_cols = fields.orientation.shape
    for by in range(n_rows):
        for bx in range(n_cols):
            y0, x0 = by * block_size, bx * block_size
            y1, x1 = min(h, y0 + block_size), min(w, x0 + block_size)
            if y0 >= h or x0 >= w:
                continue

            frequency = fields.frequency[by, bx]
            if frequency <= 0:
                frequency = _DEFAULT_FREQUENCY
            kernel = _gabor_kernel(frequency, fields.orientation[by, bx])

            region = padded[y0 : y1 + 2 * pad, x0 : x1 + 2 * pad]
            filtered = ndimage.convolve(region, kernel, mode="nearest")
            out[y0:y1, x0:x1] = filtered[pad : pad + (y1 - y0), pad : pad + (x1 - x0)]

    return out


def binarize(enhanced: np.ndarray, mask: np.ndarray) -> np.ndarray:
    """Local-mean thresholding within the foreground mask: a pixel is ridge
    (1) if it's darker than the mean of its neighborhood -- standard for
    Gabor-enhanced fingerprint images, which have near-zero DC per block."""
    local_mean = ndimage.uniform_filter(enhanced, size=BLOCK_SIZE)
    binary = (enhanced < local_mean).astype(np.uint8)
    binary[~mask] = 0
    return binary
