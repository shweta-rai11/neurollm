"""Fetches real, public hallucination/factuality benchmark items and writes
them to `data/benchmark_public.json`, kept separate from the hand-authored
`data/benchmark.json` so provenance stays unambiguous (see data/README.md).

Sources (verified live via Hugging Face's datasets-server REST API -- no
`datasets` package dependency, just plain HTTP):
  - TruthfulQA (truthfulqa/truthful_qa, "generation" config, validation
    split, 817 rows): adversarial questions designed to elicit common
    misconceptions. Each has a best_answer plus a list of correct_answers
    (multiple acceptable phrasings) -- mapped to category "truthfulqa",
    match_type "any_substring".
  - SimpleQA (basicv8vc/SimpleQA, default config, test split, 4326 rows):
    short factual questions with a single canonical answer -- mapped to
    category "simpleqa", match_type "substring".

Run as: `.venv/bin/python ../data/build_benchmark.py` from `backend/`, or
`backend/.venv/bin/python data/build_benchmark.py` from the project root.
Requires network access; makes only a handful of requests (one page per
source, since we're pulling well under the 100-rows-per-page limit).
"""
from __future__ import annotations

import json
from pathlib import Path

import httpx

_OUTPUT_PATH = Path(__file__).parent / "benchmark_public.json"

_TRUTHFULQA_URL = (
    "https://datasets-server.huggingface.co/rows"
    "?dataset=truthfulqa%2Ftruthful_qa&config=generation&split=validation&offset=0&length={n}"
)
_SIMPLEQA_URL = (
    "https://datasets-server.huggingface.co/rows"
    "?dataset=basicv8vc%2FSimpleQA&config=default&split=test&offset=0&length={n}"
)

_N_TRUTHFULQA = 90
_N_SIMPLEQA = 90


def _fetch_rows(url: str) -> list[dict]:
    resp = httpx.get(url, timeout=30.0)
    resp.raise_for_status()
    data = resp.json()
    return [r["row"] for r in data["rows"]]


def _build_truthfulqa_items() -> list[dict]:
    rows = _fetch_rows(_TRUTHFULQA_URL.format(n=_N_TRUTHFULQA))
    items = []
    for i, row in enumerate(rows):
        phrasings = [row["best_answer"], *row["correct_answers"]]
        # Dedup while preserving order, drop empties.
        seen: set[str] = set()
        unique_phrasings = []
        for p in phrasings:
            key = p.strip().lower()
            if key and key not in seen:
                seen.add(key)
                unique_phrasings.append(p.strip())
        if not row["question"].strip() or not unique_phrasings:
            continue
        items.append({
            "id": f"truthfulqa-{i}",
            "category": "truthfulqa",
            "query": row["question"].strip(),
            "expected_answer": "|||".join(unique_phrasings),
            "match_type": "any_substring",
            "source": "truthfulqa/truthful_qa (generation, validation) via Hugging Face datasets-server",
        })
    return items


def _build_simpleqa_items() -> list[dict]:
    rows = _fetch_rows(_SIMPLEQA_URL.format(n=_N_SIMPLEQA))
    items = []
    for i, row in enumerate(rows):
        question = (row.get("problem") or "").strip()
        answer = (row.get("answer") or "").strip()
        if not question or not answer:
            continue
        items.append({
            "id": f"simpleqa-{i}",
            "category": "simpleqa",
            "query": question,
            "expected_answer": answer,
            "match_type": "substring",
            "source": "basicv8vc/SimpleQA (default, test) via Hugging Face datasets-server",
        })
    return items


def main() -> None:
    print(f"Fetching {_N_TRUTHFULQA} TruthfulQA items...")
    truthfulqa_items = _build_truthfulqa_items()
    print(f"  got {len(truthfulqa_items)} usable items")

    print(f"Fetching {_N_SIMPLEQA} SimpleQA items...")
    simpleqa_items = _build_simpleqa_items()
    print(f"  got {len(simpleqa_items)} usable items")

    output = {
        "version": "1.0",
        "description": (
            "Real public-dataset-sourced benchmark items (TruthfulQA + SimpleQA), fetched by "
            "data/build_benchmark.py. Kept separate from data/benchmark.json's hand-authored set. "
            "See data/README.md for scoring caveats."
        ),
        "items": [*truthfulqa_items, *simpleqa_items],
    }
    _OUTPUT_PATH.write_text(json.dumps(output, indent=2))
    print(f"Wrote {len(output['items'])} items to {_OUTPUT_PATH}")


if __name__ == "__main__":
    main()
