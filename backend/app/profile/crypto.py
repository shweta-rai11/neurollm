"""Encryption for biometric templates at rest (product spec section 17).

Only the derived numeric `FeatureVector` template is ever encrypted/stored
here -- raw fingerprint image bytes are never written to disk or database
anywhere in this app (see `app.biometric.image_io`, `app.profile.service`).
"""
from __future__ import annotations

import numpy as np
from cryptography.fernet import Fernet, InvalidToken

from app.config import settings


class TemplateDecryptionError(ValueError):
    pass


def _fernet() -> Fernet:
    return Fernet(settings.biometric_encryption_key.encode())


def encrypt_template(vector: np.ndarray) -> bytes:
    raw = vector.astype(np.float32).tobytes()
    return _fernet().encrypt(raw)


def decrypt_template(blob: bytes) -> np.ndarray:
    try:
        raw = _fernet().decrypt(blob)
    except InvalidToken as exc:
        raise TemplateDecryptionError("stored biometric template could not be decrypted") from exc
    return np.frombuffer(raw, dtype=np.float32)
