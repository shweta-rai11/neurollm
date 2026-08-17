"""Unit tests for app.retrieval.brave_search -- no real network calls.
`httpx.AsyncClient` is monkeypatched with a fake context manager so these
run entirely offline, consistent with the rest of this suite."""
from __future__ import annotations

import pytest

from app.retrieval import brave_search


class _FakeResponse:
    def __init__(self, payload=None, status_error: Exception | None = None):
        self._payload = payload or {}
        self._status_error = status_error

    def raise_for_status(self):
        if self._status_error:
            raise self._status_error

    def json(self):
        return self._payload


class _FakeAsyncClient:
    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc_info):
        return False

    async def get(self, *args, **kwargs):
        raise NotImplementedError


def _install_fake_client(monkeypatch, response=None, raise_error: Exception | None = None):
    class Client(_FakeAsyncClient):
        async def get(self, *args, **kwargs):
            if raise_error is not None:
                raise raise_error
            return response

    monkeypatch.setattr(brave_search.httpx, "AsyncClient", Client)


@pytest.fixture(autouse=True)
def _reset_key(monkeypatch):
    monkeypatch.setattr(brave_search.settings, "brave_search_api_key", "test-key-not-real")
    yield


def test_is_available_reflects_configured_key(monkeypatch):
    monkeypatch.setattr(brave_search.settings, "brave_search_api_key", "some-key")
    assert brave_search.is_available() is True
    monkeypatch.setattr(brave_search.settings, "brave_search_api_key", None)
    assert brave_search.is_available() is False


@pytest.mark.asyncio
async def test_search_returns_empty_list_without_key(monkeypatch):
    monkeypatch.setattr(brave_search.settings, "brave_search_api_key", None)
    results = await brave_search.search("some query")
    assert results == []


@pytest.mark.asyncio
async def test_search_parses_well_formed_response(monkeypatch):
    payload = {
        "web": {
            "results": [
                {"title": "Result A", "description": "snippet A", "url": "https://a.example"},
                {"title": "Result B", "description": "snippet B", "url": "https://b.example"},
            ]
        }
    }
    _install_fake_client(monkeypatch, response=_FakeResponse(payload))

    results = await brave_search.search("query", count=3)

    assert len(results) == 2
    assert results[0].title == "Result A"
    assert results[0].snippet == "snippet A"
    assert results[0].url == "https://a.example"


@pytest.mark.asyncio
async def test_search_respects_count_limit(monkeypatch):
    payload = {"web": {"results": [{"title": f"R{i}", "description": "", "url": ""} for i in range(10)]}}
    _install_fake_client(monkeypatch, response=_FakeResponse(payload))

    results = await brave_search.search("query", count=3)
    assert len(results) == 3


@pytest.mark.asyncio
async def test_search_degrades_to_empty_on_network_error(monkeypatch):
    _install_fake_client(monkeypatch, raise_error=ConnectionError("boom"))
    results = await brave_search.search("query")
    assert results == []


@pytest.mark.asyncio
async def test_search_degrades_to_empty_on_http_error(monkeypatch):
    import httpx as real_httpx

    _install_fake_client(monkeypatch, response=_FakeResponse(status_error=real_httpx.HTTPStatusError("nope", request=None, response=None)))
    results = await brave_search.search("query")
    assert results == []


@pytest.mark.asyncio
async def test_search_degrades_to_empty_on_malformed_payload(monkeypatch):
    _install_fake_client(monkeypatch, response=_FakeResponse({"unexpected": "shape"}))
    results = await brave_search.search("query")
    assert results == []


@pytest.mark.asyncio
async def test_search_skips_non_dict_result_entries(monkeypatch):
    payload = {"web": {"results": ["not-a-dict", {"title": "Real", "description": "d", "url": "u"}]}}
    _install_fake_client(monkeypatch, response=_FakeResponse(payload))
    results = await brave_search.search("query")
    assert len(results) == 1
    assert results[0].title == "Real"
