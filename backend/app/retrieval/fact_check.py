"""Retrieval-grounded fact-check: asks the model to judge a candidate answer
against real search snippets, instead of only against its own other
candidates. Mirrors the parsing style of the existing self-verifier
(CONSISTENT/INCONSISTENT) in `app.brain.executive_controller` so both
signals are combined the same documented way in `app.brain.hallucination`.
"""
from __future__ import annotations

from app.llm.provider import LLMProvider
from app.retrieval.brave_search import SearchResult, search

_FACT_CHECK_PROMPT_TEMPLATE = """You are fact-checking a candidate answer against search results.

Question: {query}

Candidate answer: {answer}

Search results:
{snippets}

Does the candidate answer agree with the search results? Reply with exactly one word first -- \
SUPPORTED, CONTRADICTED, or UNCLEAR (if the search results don't address the claim either way) \
-- then a one-sentence explanation."""


def _format_snippets(results: list[SearchResult]) -> str:
    if not results:
        return "(no results)"
    return "\n".join(f"{i + 1}. {r.title}: {r.snippet}" for i, r in enumerate(results))


async def fact_check(provider: LLMProvider, query: str, answer: str) -> tuple[float | None, str, list[SearchResult]]:
    """Returns (retrieval_disagreement in [0,1] or None if retrieval produced
    no evidence, the raw model judgement text, the search results used).
    `None` (not 0.0) signals "no external evidence available" so the caller
    can tell that apart from "evidence agreed with the answer"."""
    results = await search(query)
    if not results:
        return None, "", []

    prompt = _FACT_CHECK_PROMPT_TEMPLATE.format(query=query, answer=answer, snippets=_format_snippets(results))
    try:
        raw_text = await provider.generate(prompt)
    except Exception:  # noqa: BLE001 -- fact-check is best-effort, must never break the pipeline
        return None, "", results

    normalized = raw_text.strip().upper()
    if normalized.startswith("CONTRADICTED"):
        disagreement = 0.9
    elif normalized.startswith("SUPPORTED"):
        disagreement = 0.1
    else:
        # UNCLEAR, or the model didn't follow the format -- treat as
        # genuinely ambiguous rather than guessing a direction.
        disagreement = 0.5

    return disagreement, raw_text, results
