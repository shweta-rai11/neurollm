"""Brave Search API client.

Best-effort by design (see package docstring): a missing key, network
error, timeout, or malformed response all resolve to an empty result list
rather than raising. Callers (see `fact_check.py`) treat an empty list as
"no external evidence available" and degrade gracefully, exactly the way
`executive_controller.py`'s self-verifier already tolerates a parse failure.
"""
from __future__ import annotations

from dataclasses import dataclass

import httpx

from app.config import settings

_ENDPOINT = "https://api.search.brave.com/res/v1/web/search"
_TIMEOUT_SECONDS = 8.0


@dataclass
class SearchResult:
    title: str
    snippet: str
    url: str


def is_available() -> bool:
    return bool(settings.brave_search_api_key)


async def search(query: str, count: int = 3) -> list[SearchResult]:
    if not settings.brave_search_api_key:
        return []

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT_SECONDS) as client:
            response = await client.get(
                _ENDPOINT,
                params={"q": query, "count": count},
                headers={
                    "Accept": "application/json",
                    "X-Subscription-Token": settings.brave_search_api_key,
                },
            )
            response.raise_for_status()
            data = response.json()
    except Exception:  # noqa: BLE001 -- retrieval is best-effort, must never break the pipeline
        return []

    raw_results = (data.get("web") or {}).get("results") or []
    results: list[SearchResult] = []
    for item in raw_results[:count]:
        if not isinstance(item, dict):
            continue
        results.append(
            SearchResult(
                title=str(item.get("title", "")),
                snippet=str(item.get("description", "")),
                url=str(item.get("url", "")),
            )
        )
    return results
