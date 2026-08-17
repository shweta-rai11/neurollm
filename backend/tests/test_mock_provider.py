"""Unit tests for app.llm.mock_provider.MockProvider.

These test functions are `async def` and exercised via pytest-asyncio in
"auto" mode (see backend/pytest.ini: `asyncio_mode = auto`), so no explicit
`@pytest.mark.asyncio` decorators are needed -- every async test in this
suite follows that same convention.
"""
from __future__ import annotations

from app.llm.mock_provider import MockProvider


async def test_generate_is_deterministic_for_the_same_query():
    provider = MockProvider()
    query = "Write a function to reverse a linked list"

    first = await provider.generate(query)
    second = await provider.generate(query)

    assert first == second


async def test_generate_multiple_returns_exactly_n_items():
    provider = MockProvider()
    query = "Write a function to reverse a linked list"

    for n in (1, 3, 5, 10):
        candidates = await provider.generate_multiple(query, n)
        assert len(candidates) == n


async def test_coding_candidates_are_lexically_similar_structural():
    provider = MockProvider()
    query = "Write a function to reverse a linked list"

    candidates = await provider.generate_multiple(query, 5)

    assert all(("def " in c) or ("```" in c) for c in candidates)


async def test_predictive_candidates_meaningfully_differ():
    provider = MockProvider()
    query = "Who will win the election next year?"

    candidates = await provider.generate_multiple(query, 5)

    # The mock provider must never answer a genuinely unresolved/predictive
    # question with a single confident, repeated answer.
    assert len(set(candidates)) > 1


async def test_get_model_info_returns_expected_keys():
    provider = MockProvider()
    info = provider.get_model_info()

    assert set(("name", "provider", "description")).issubset(info.keys())
    assert info["provider"] == "mock"
    assert isinstance(info["name"], str) and info["name"]
    assert isinstance(info["description"], str) and info["description"]


async def test_empty_query_does_not_raise_and_returns_n_placeholders():
    provider = MockProvider()
    candidates = await provider.generate_multiple("   ", 3)
    assert len(candidates) == 3
