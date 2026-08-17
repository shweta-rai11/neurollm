"""One-off, large-scale run of Condition 1 (direct generation) vs Condition 4
(virtual-brain routing + verification) -- the real, larger-sample test of
whether routing/verification actually reduces hallucinations, using
`data/benchmark.json` (54 hand-authored items) plus a slice of the real
TruthfulQA/SimpleQA items fetched by `data/build_benchmark.py`.

This reuses the *exact* scoring and pipeline functions `POST
/api/experiment/benchmark` uses (`_run_normal_condition`, `_score`,
`run_pipeline`) -- it does not duplicate that logic, and it does not change
that endpoint or loosen its request-level `limit_per_category<=20` cap
(which exists to bound accidental large runs triggered from the browser).
This script exists specifically to run a deliberate, large, offline batch
that cap doesn't fit.

No Brave Search API key was configured for this run, so the VERIFY pathway
used self-critique-only verification (see app.retrieval) -- this run
measures the pre-retrieval system, honestly labeled as such in the output.

Run as: `.venv/bin/python -m app.experiments.run_large_benchmark` from `backend/`.
"""
from __future__ import annotations

import asyncio
import json
import time
from datetime import datetime, timezone
from pathlib import Path

from app.api.routes_experiments import _run_normal_condition, _score
from app.brain.pipeline import run_pipeline
from app.retrieval.brave_search import is_available as retrieval_is_available

MODEL = "local_hf"
N_TRUTHFULQA = 60
N_SIMPLEQA = 60
NUM_SAMPLES = 4

_DATA_DIR = Path(__file__).resolve().parents[3] / "data"
_OUTPUT_PATH = _DATA_DIR / "large_benchmark_results.json"


def _load_items() -> list[dict]:
    hand_items = json.loads((_DATA_DIR / "benchmark.json").read_text())["items"]
    public_items = json.loads((_DATA_DIR / "benchmark_public.json").read_text())["items"]
    truthfulqa_items = [i for i in public_items if i["category"] == "truthfulqa"][:N_TRUTHFULQA]
    simpleqa_items = [i for i in public_items if i["category"] == "simpleqa"][:N_SIMPLEQA]
    return [*hand_items, *truthfulqa_items, *simpleqa_items]


async def _run_one(item: dict) -> dict:
    normal_answer, normal_latency = await _run_normal_condition(item["query"], MODEL)

    routed_start = time.perf_counter()
    routed = await run_pipeline(query=item["query"], model=MODEL, uncertainty_mode=True, num_samples=NUM_SAMPLES)
    routed_latency = (time.perf_counter() - routed_start) * 1000

    expected = item.get("expected_answer")
    match_type = item.get("match_type")

    return {
        "id": item["id"],
        "category": item["category"],
        "query": item["query"],
        "expected_answer": expected,
        "normal_answer": normal_answer,
        "normal_correct": _score(normal_answer, expected, match_type),
        "normal_latency_ms": normal_latency,
        "routed_answer": routed.answer,
        "routed_correct": _score(routed.answer, expected, match_type),
        "routed_pathway": routed.pathway,
        "routed_abstained": routed.pathway == "VERIFY" and "don't have strong evidence" in routed.answer,
        "routed_hallucination_risk": routed.hallucination_risk.score,
        "routed_latency_ms": routed_latency,
    }


def _summarize(results: list[dict]) -> dict:
    by_category: dict[str, list[dict]] = {}
    for r in results:
        by_category.setdefault(r["category"], []).append(r)

    category_summaries = {}
    for category, rows in by_category.items():
        normal_scored = [r["normal_correct"] for r in rows if r["normal_correct"] is not None]
        routed_scored = [r["routed_correct"] for r in rows if r["routed_correct"] is not None]
        abstained = sum(1 for r in rows if r["routed_abstained"])
        category_summaries[category] = {
            "n": len(rows),
            "normal_accuracy": (sum(normal_scored) / len(normal_scored)) if normal_scored else None,
            "routed_accuracy": (sum(routed_scored) / len(routed_scored)) if routed_scored else None,
            "routed_abstention_rate": abstained / len(rows) if rows else 0.0,
            "mean_hallucination_risk": sum(r["routed_hallucination_risk"] for r in rows) / len(rows) if rows else 0.0,
        }

    all_normal_scored = [r["normal_correct"] for r in results if r["normal_correct"] is not None]
    all_routed_scored = [r["routed_correct"] for r in results if r["routed_correct"] is not None]
    return {
        "category_summaries": category_summaries,
        "overall_normal_accuracy": (sum(all_normal_scored) / len(all_normal_scored)) if all_normal_scored else None,
        "overall_routed_accuracy": (sum(all_routed_scored) / len(all_routed_scored)) if all_routed_scored else None,
        "overall_n_scored": len(all_normal_scored),
    }


async def main() -> None:
    items = _load_items()
    print(f"Loaded {len(items)} items ({sum(1 for i in items if i['category']=='truthfulqa')} truthfulqa, "
          f"{sum(1 for i in items if i['category']=='simpleqa')} simpleqa, "
          f"{sum(1 for i in items if i['category'] not in ('truthfulqa','simpleqa'))} hand-authored)")
    print(f"Retrieval available for this run: {retrieval_is_available()} (self-critique-only if False)")

    results: list[dict] = []
    start = time.perf_counter()
    for i, item in enumerate(items):
        try:
            result = await _run_one(item)
        except Exception as exc:  # noqa: BLE001 -- one bad item must not abort the whole run
            print(f"[{i + 1}/{len(items)}] ERROR on {item['id']}: {type(exc).__name__}: {exc}")
            continue
        results.append(result)
        elapsed = time.perf_counter() - start
        eta = (elapsed / (i + 1)) * (len(items) - i - 1)
        print(
            f"[{i + 1}/{len(items)}] {item['category']:12s} normal={result['normal_correct']} "
            f"routed={result['routed_correct']} pathway={result['routed_pathway']} "
            f"hrs={result['routed_hallucination_risk']:.2f} | elapsed={elapsed / 60:.1f}m eta={eta / 60:.1f}m"
        )

    summary = _summarize(results)
    output = {
        "run_at": datetime.now(timezone.utc).isoformat(),
        "model": MODEL,
        "num_samples": NUM_SAMPLES,
        "retrieval_available": retrieval_is_available(),
        "n_items_attempted": len(items),
        "n_items_completed": len(results),
        "summary": summary,
        "items": results,
    }
    _OUTPUT_PATH.write_text(json.dumps(output, indent=2))

    print("\n=== SUMMARY ===")
    print(f"Retrieval available: {retrieval_is_available()}")
    print(f"Overall: normal_accuracy={summary['overall_normal_accuracy']}, routed_accuracy={summary['overall_routed_accuracy']}, n={summary['overall_n_scored']}")
    for category, s in sorted(summary["category_summaries"].items()):
        print(f"  {category:12s} n={s['n']:3d} normal={s['normal_accuracy']} routed={s['routed_accuracy']} "
              f"abstain={s['routed_abstention_rate']:.2f} mean_hrs={s['mean_hallucination_risk']:.3f}")
    print(f"\nWrote {len(results)} results to {_OUTPUT_PATH}")


if __name__ == "__main__":
    asyncio.run(main())
