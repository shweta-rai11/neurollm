"""Decode an uploaded image into a bounded grayscale numpy array.

This is the only place in the app that touches the raw uploaded bytes --
`app.biometric.pipeline.extract_fingerprint` reads them into memory here and
they are discarded once this function returns; nothing downstream persists
them (see `app.profile.service.ProfileService.enroll`, which stores only the
derived `FeatureVector` template).
"""
from __future__ import annotations

import io

import numpy as np
from PIL import Image, UnidentifiedImageError

# Bounded so a very large upload can't make the (CPU-only, per-request)
# ridge/Gabor/thinning pipeline below unreasonably slow. 320px is generous
# for the block-based (16px block) algorithms used throughout this package.
_MAX_DIMENSION = 320
_MIN_DIMENSION = 64


class InvalidImageError(ValueError):
    """Raised when the uploaded bytes can't be decoded as an image."""


def decode_image_bytes(data: bytes) -> np.ndarray:
    """Decode `data` to a grayscale float64 array in [0, 1], resized so its
    longer side is at most `_MAX_DIMENSION` px (aspect ratio preserved) and
    its shorter side is at least `_MIN_DIMENSION` px (upscaled if needed so
    tiny images still have enough pixels for block-based analysis)."""
    try:
        image = Image.open(io.BytesIO(data))
        image.load()
    except (UnidentifiedImageError, OSError) as exc:
        raise InvalidImageError(f"could not decode image: {exc}") from exc

    gray = image.convert("L")

    width, height = gray.size
    if width == 0 or height == 0:
        raise InvalidImageError("image has zero width or height")

    longer = max(width, height)
    shorter = min(width, height)
    scale = 1.0
    if longer > _MAX_DIMENSION:
        scale = _MAX_DIMENSION / longer
    elif shorter < _MIN_DIMENSION:
        scale = _MIN_DIMENSION / shorter

    if scale != 1.0:
        new_size = (max(1, round(width * scale)), max(1, round(height * scale)))
        gray = gray.resize(new_size, Image.BILINEAR)

    array = np.asarray(gray, dtype=np.float64) / 255.0
    return array
