"""Abstract LLM provider interface.

All concrete providers (mock, OpenAI, ...) implement this interface so the
API layer can treat them interchangeably. Providers are responsible for
never leaking secrets (API keys, raw upstream error bodies) into raised
exceptions -- see `LLMProviderError`.
"""
from __future__ import annotations

import abc


class LLMProviderError(Exception):
    """Raised when a provider cannot produce a response.

    The message attached to this exception is expected to be safe to show
    in logs (no API keys, no raw upstream payloads).
    """


class LLMProvider(abc.ABC):
    """Common interface implemented by every LLM backend."""

    @abc.abstractmethod
    async def generate(self, query: str) -> str:
        """Return a single answer for `query`."""
        raise NotImplementedError

    @abc.abstractmethod
    async def generate_multiple(self, query: str, n: int) -> list[str]:
        """Return `n` candidate answers for `query`, used for uncertainty sampling."""
        raise NotImplementedError

    @abc.abstractmethod
    def get_model_info(self) -> dict:
        """Return `{"name": ..., "provider": ..., "description": ...}`."""
        raise NotImplementedError
