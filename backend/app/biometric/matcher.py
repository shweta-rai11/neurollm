"""Demo-grade 1:N template matching -- answers "does this new fingerprint
scan belong to an already-enrolled profile?" via cosine similarity between
`FeatureVector` templates.

IMPORTANT: this is explicitly NOT a forensic-grade AFIS (Automated
Fingerprint Identification System). Real fingerprint matchers align
minutiae constellations under rotation/translation with tolerance for
partial prints; this compares fixed-length global feature summaries. It is
adequate for this app's actual job -- "which locally-created computational
profile does this repeat scan personalize?" -- and is documented as such
everywhere it's surfaced (see `app.profile.service.ProfileService.enroll`).
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

MATCH_THRESHOLD = 0.90


@dataclass
class MatchResult:
    matched_profile_id: str | None
    best_similarity: float


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    denom = float(np.linalg.norm(a) * np.linalg.norm(b))
    if denom < 1e-9:
        return 0.0
    return float(np.dot(a, b) / denom)


def find_match(candidate: np.ndarray, enrolled: list[tuple[str, np.ndarray]]) -> MatchResult:
    """`enrolled` is a list of (profile_id, template_vector) pairs already
    on file. Returns the best-matching profile_id if its similarity clears
    `MATCH_THRESHOLD`, else None (meaning: treat this as a new enrollment)."""
    best_profile_id: str | None = None
    best_similarity = 0.0

    for profile_id, template in enrolled:
        similarity = cosine_similarity(candidate, template)
        if similarity > best_similarity:
            best_similarity = similarity
            best_profile_id = profile_id

    if best_similarity >= MATCH_THRESHOLD:
        return MatchResult(matched_profile_id=best_profile_id, best_similarity=best_similarity)
    return MatchResult(matched_profile_id=None, best_similarity=best_similarity)
