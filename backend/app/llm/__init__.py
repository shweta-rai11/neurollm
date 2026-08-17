"""LLM provider factory.

`get_provider(model_name)` is the single entry point the API layer should
use to obtain a provider instance -- it hides the mock/OpenAI selection
logic so routes never need to branch on configuration themselves.
"""
from __future__ import annotations

from app.config import settings
from app.llm.local_hf_provider import LocalHFProvider
from app.llm.mock_provider import MockProvider
from app.llm.openai_provider import OpenAIProvider
from app.llm.provider import LLMProvider, LLMProviderError

__all__ = [
    "LLMProvider",
    "LLMProviderError",
    "LocalHFProvider",
    "MockProvider",
    "OpenAIProvider",
    "get_provider",
]


def get_provider(model_name: str) -> LLMProvider:
    """Return an `LLMProvider` for `model_name`.

    "local_hf" selects the local, activation-inspectable Qwen2.5 model (see
    app/llm/local_hf_provider.py) -- this is the only provider Research Mode
    can capture real activations from. Falls back to `MockProvider` whenever
    no OpenAI key is configured and a non-local, non-mock model was
    requested, so the app is always usable without any API key.
    """
    if model_name == "local_hf":
        return LocalHFProvider()
    if model_name == "mock" or not settings.has_openai_key:
        return MockProvider()
    return OpenAIProvider()
