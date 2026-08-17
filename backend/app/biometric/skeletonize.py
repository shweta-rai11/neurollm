"""Zhang-Suen thinning (Zhang & Suen, "A fast parallel algorithm for
thinning digital patterns", Communications of the ACM 27(3), 1984),
implemented directly in numpy (no scikit-image dependency) so the ridge
binary image can be reduced to single-pixel-wide ridge lines before
crossing-number minutiae extraction.
"""
from __future__ import annotations

import numpy as np

_MAX_ITERATIONS = 40


def _neighbors(padded: np.ndarray) -> list[np.ndarray]:
    """8-neighbors P2..P9 in clockwise order starting from directly above,
    each the same shape as the unpadded image."""
    p2 = padded[0:-2, 1:-1]
    p3 = padded[0:-2, 2:]
    p4 = padded[1:-1, 2:]
    p5 = padded[2:, 2:]
    p6 = padded[2:, 1:-1]
    p7 = padded[2:, 0:-2]
    p8 = padded[1:-1, 0:-2]
    p9 = padded[0:-2, 0:-2]
    return [p2, p3, p4, p5, p6, p7, p8, p9]


def zhang_suen_thin(binary: np.ndarray) -> np.ndarray:
    """`binary` is a uint8/bool array where 1 = ridge pixel. Returns a
    same-shape uint8 array reduced to a 1-pixel-wide skeleton."""
    img = (binary > 0).astype(np.uint8)

    for _ in range(_MAX_ITERATIONS):
        changed = False

        for substep in (1, 2):
            padded = np.pad(img, 1, mode="constant", constant_values=0)
            p2, p3, p4, p5, p6, p7, p8, p9 = _neighbors(padded)
            seq = [p2, p3, p4, p5, p6, p7, p8, p9, p2]

            b = p2 + p3 + p4 + p5 + p6 + p7 + p8 + p9
            a = np.zeros_like(img, dtype=np.int32)
            for i in range(8):
                a += ((seq[i] == 0) & (seq[i + 1] == 1)).astype(np.int32)

            cond_common = (img == 1) & (b >= 2) & (b <= 6) & (a == 1)
            if substep == 1:
                cond = cond_common & ((p2 * p4 * p6) == 0) & ((p4 * p6 * p8) == 0)
            else:
                cond = cond_common & ((p2 * p4 * p8) == 0) & ((p2 * p6 * p8) == 0)

            if cond.any():
                img[cond] = 0
                changed = True

        if not changed:
            break

    return img
