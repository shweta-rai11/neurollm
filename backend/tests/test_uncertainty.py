"""Unit tests for app.cognitive_state.uncertainty.estimate_uncertainty."""
from __future__ import annotations

from app.cognitive_state.uncertainty import estimate_uncertainty

_VALID_METHODS = {"tfidf", "lexical_fallback"}


def test_identical_candidates_have_zero_uncertainty_and_full_agreement():
    candidates = ["The answer is 42."] * 5
    result = estimate_uncertainty(candidates)

    assert result.semantic_uncertainty_score == 0
    assert result.response_agreement == 100
    assert result.unique_semantic_clusters == 1


def test_wildly_different_candidates_have_high_uncertainty():
    candidates = [
        "The mitochondria is the powerhouse of the cell.",
        "Paris is the capital of France.",
        "def quicksort(arr):\n    return sorted(arr)",
        "The stock market fell sharply today due to inflation fears.",
        "Photosynthesis converts sunlight into chemical energy in plants.",
    ]
    result = estimate_uncertainty(candidates)

    assert result.semantic_uncertainty_score > 50
    assert result.unique_semantic_clusters > 1


def test_empty_candidate_list_returns_valid_zero_result_without_raising():
    result = estimate_uncertainty([])

    assert result.candidate_count == 0
    assert result.semantic_uncertainty_score == 0
    assert result.response_agreement == 100
    assert result.unique_semantic_clusters == 0
    assert result.candidates == []
    # Per the documented code path: n == 0 short-circuits before any
    # TF-IDF attempt and hardcodes the lexical fallback method.
    assert result.method == "lexical_fallback"


def test_entropy_and_score_stay_within_bounds_across_varied_inputs():
    candidate_sets = [
        ["only one candidate"],
        ["same text", "same text"],
        ["completely different topic one", "an entirely unrelated statement about weather"],
        [
            "def add(a, b): return a + b",
            "def add(a, b):\n    return a + b",
            "The weather today is sunny with a chance of rain.",
            "Quantum entanglement links particle states across distance.",
            "def add(a, b): return a + b  # sum two numbers",
        ],
        ["", "", ""],
        ["repeat"] * 10,
    ]
    for candidates in candidate_sets:
        result = estimate_uncertainty(candidates)
        assert 0 <= result.semantic_uncertainty_score <= 100
        assert 0 <= result.response_agreement <= 100
        assert 0.0 <= result.entropy_normalized <= 1.0
        assert result.method in _VALID_METHODS


def test_method_field_is_always_a_known_backend():
    for candidates in (
        ["a"],
        ["a", "b"],
        ["hello world", "goodbye world", "totally different sentence here"],
        [],
    ):
        result = estimate_uncertainty(candidates)
        assert result.method in _VALID_METHODS
