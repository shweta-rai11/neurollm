"""Unit tests for app.retrieval.fact_check -- uses a fake provider and
monkeypatches app.retrieval.fact_check.search directly, so no real network
or model calls happen."""
from __future__ import annotations

import pytest

from app.retrieval import fact_check as fact_check_module
from app.retrieval.brave_search import SearchResult


class _FakeProvider:
    def __init__(self, response_text: str):
        self._response_text = response_text

    async def generate(self, query: str) -> str:
        return self._response_text

    async def generate_multiple(self, query: str, n: int) -> list[str]:
        return [self._response_text] * n

    def get_model_info(self) -> dict:
        return {"name": "fake", "provider": "fake", "description": "test double"}


class _RaisingProvider:
    async def generate(self, query: str) -> str:
        raise RuntimeError("provider unavailable")

    async def generate_multiple(self, query: str, n: int) -> list[str]:
        raise RuntimeError("provider unavailable")

    def get_model_info(self) -> dict:
        return {"name": "raising", "provider": "raising", "description": "test double"}


_SAMPLE_RESULTS = [SearchResult(title="T1", snippet="S1", url="https://example.com/1")]


def _install_search(monkeypatch, results):
    async def _fake_search(query, count=3):
        return results

    monkeypatch.setattr(fact_check_module, "search", _fake_search)


@pytest.mark.asyncio
async def test_no_search_results_yields_none_disagreement(monkeypatch):
    _install_search(monkeypatch, [])
    provider = _FakeProvider("SUPPORTED. Looks fine.")

    disagreement, raw_text, results = await fact_check_module.fact_check(provider, "q", "answer")

    assert disagreement is None
    assert raw_text == ""
    assert results == []


@pytest.mark.asyncio
async def test_supported_yields_low_disagreement(monkeypatch):
    _install_search(monkeypatch, _SAMPLE_RESULTS)
    provider = _FakeProvider("SUPPORTED. The search results confirm this.")

    disagreement, raw_text, results = await fact_check_module.fact_check(provider, "q", "answer")

    assert disagreement == 0.1
    assert "SUPPORTED" in raw_text.upper()
    assert results == _SAMPLE_RESULTS


@pytest.mark.asyncio
async def test_contradicted_yields_high_disagreement(monkeypatch):
    _install_search(monkeypatch, _SAMPLE_RESULTS)
    provider = _FakeProvider("CONTRADICTED. The search results disagree.")

    disagreement, _raw_text, _results = await fact_check_module.fact_check(provider, "q", "answer")

    assert disagreement == 0.9


@pytest.mark.asyncio
async def test_unclear_yields_mid_disagreement(monkeypatch):
    _install_search(monkeypatch, _SAMPLE_RESULTS)
    provider = _FakeProvider("UNCLEAR. Not addressed.")

    disagreement, _raw_text, _results = await fact_check_module.fact_check(provider, "q", "answer")

    assert disagreement == 0.5


@pytest.mark.asyncio
async def test_unparsed_response_yields_mid_disagreement(monkeypatch):
    _install_search(monkeypatch, _SAMPLE_RESULTS)
    provider = _FakeProvider("I'm not sure how to answer that.")

    disagreement, _raw_text, _results = await fact_check_module.fact_check(provider, "q", "answer")

    assert disagreement == 0.5


@pytest.mark.asyncio
async def test_provider_failure_degrades_to_none_disagreement(monkeypatch):
    _install_search(monkeypatch, _SAMPLE_RESULTS)
    provider = _RaisingProvider()

    disagreement, raw_text, results = await fact_check_module.fact_check(provider, "q", "answer")

    assert disagreement is None
    assert raw_text == ""
    assert results == _SAMPLE_RESULTS
