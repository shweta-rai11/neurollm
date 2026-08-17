"""OpenAI-backed LLM provider.

Wraps the `openai` package's AsyncOpenAI client. All upstream failures
(auth, rate limit, network, timeout, malformed response) are caught and
re-raised as `LLMProviderError` with a safe, generic message -- raw
exception text, API keys, and response bodies from the OpenAI SDK are never
propagated to callers or logs.
"""
from __future__ import annotations

import asyncio

from app.config import settings
from app.llm.provider import LLMProvider, LLMProviderError

_DEFAULT_TEMPERATURE = 0.9
_MAX_OUTPUT_TOKENS = 800


class OpenAIProvider(LLMProvider):
    def __init__(self) -> None:
        try:
            from openai import AsyncOpenAI
        except ImportError as exc:  # pragma: no cover - dependency always declared
            raise LLMProviderError("OpenAI client library is not available.") from exc

        if not settings.has_openai_key:
            raise LLMProviderError("OpenAI API key is not configured.")

        self._client = AsyncOpenAI(api_key=settings.openai_api_key)
        self._model = settings.openai_model

    async def generate(self, query: str) -> str:
        results = await self.generate_multiple(query, 1)
        return results[0]

    async def generate_multiple(self, query: str, n: int) -> list[str]:
        try:
            response = await self._client.chat.completions.create(
                model=self._model,
                messages=[{"role": "user", "content": query}],
                n=n,
                temperature=_DEFAULT_TEMPERATURE,
                max_tokens=_MAX_OUTPUT_TOKENS,
            )
        except Exception as exc:  # noqa: BLE001 - normalize all SDK errors
            raise LLMProviderError(
                f"OpenAI request failed ({type(exc).__name__}); see server logs for detail."
            ) from exc

        try:
            texts = [choice.message.content or "" for choice in response.choices]
        except (AttributeError, IndexError) as exc:
            raise LLMProviderError("OpenAI response was malformed.") from exc

        if not texts:
            raise LLMProviderError("OpenAI returned no candidate responses.")

        # Some models/providers ignore `n` and only return one choice; pad
        # by requesting additional single completions concurrently so the
        # caller always gets the requested count.
        if len(texts) < n:
            missing = n - len(texts)
            extra = await asyncio.gather(
                *[self._single_completion(query) for _ in range(missing)],
                return_exceptions=True,
            )
            for item in extra:
                if isinstance(item, str):
                    texts.append(item)
        return texts[:n] if len(texts) >= n else texts

    async def _single_completion(self, query: str) -> str:
        try:
            response = await self._client.chat.completions.create(
                model=self._model,
                messages=[{"role": "user", "content": query}],
                temperature=_DEFAULT_TEMPERATURE,
                max_tokens=_MAX_OUTPUT_TOKENS,
            )
            return response.choices[0].message.content or ""
        except Exception as exc:  # noqa: BLE001
            raise LLMProviderError(
                f"OpenAI request failed ({type(exc).__name__}); see server logs for detail."
            ) from exc

    def get_model_info(self) -> dict:
        return {
            "name": self._model,
            "provider": "openai",
            "description": f"OpenAI chat completion model ({self._model}).",
        }
