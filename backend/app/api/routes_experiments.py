"""POST /experiment -- A/B compare two queries' cognitive states.
POST /experiment/benchmark -- spec section 10's condition comparison: for
each benchmark item, run Condition 1 (direct, no routing) vs Condition 4
(virtual-brain routing and verification) and score real accuracy where the
item has a checkable `expected_answer`.
"""
from __future__ import annotations

import asyncio
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.brain.pipeline import run_pipeline
from app.database.database import get_db
from app.database.models import AnalysisRecord
from app.llm import LLMProviderError, MockProvider, get_provider
from app.models.schemas import (
    BenchmarkCategorySummary,
    BenchmarkItemResult,
    BenchmarkRequest,
    BenchmarkResponse,
    ExperimentRequest,
    ExperimentResponse,
    ExperimentSide,
    HallucinationRiskOut,
)
from app.cognitive_state.uncertainty import estimate_uncertainty

router = APIRouter()

_DATA_DIR = Path(__file__).resolve().parents[3] / "data"
_DATA_PATH = _DATA_DIR / "benchmark.json"
_PUBLIC_DATA_PATH = _DATA_DIR / "benchmark_public.json"


async def _run_side(query: str, model: str, num_samples: int) -> ExperimentSide:
    result = await run_pipeline(query=query, model=model, uncertainty_mode=True, num_samples=num_samples)
    return ExperimentSide(
        query=query,
        answer=result.answer,
        pathway=result.pathway,
        hallucination_risk=HallucinationRiskOut(score=result.hallucination_risk.score, components=result.hallucination_risk.components),
        task_analysis=result.task,
        cognitive_state=result.cognitive_state,
        uncertainty=result.uncertainty,
    )


def _persist(db: Session, side: ExperimentSide, model: str) -> None:
    record = AnalysisRecord(
        timestamp=datetime.now(timezone.utc).isoformat(),
        kind="experiment_side",
        query=side.query,
        model=model,
        provider=model,
        answer=side.answer,
        pathway=side.pathway,
        hallucination_risk=side.hallucination_risk.score,
        task_analysis_json=side.task_analysis.model_dump_json(),
        cognitive_state_json=side.cognitive_state.model_dump_json(),
        uncertainty_json=side.uncertainty.model_dump_json() if side.uncertainty else None,
        duration_ms=0,
    )
    db.add(record)


@router.post("/experiment", response_model=ExperimentResponse)
async def experiment(req: ExperimentRequest, db: Session = Depends(get_db)) -> ExperimentResponse:
    side_a, side_b = await asyncio.gather(
        _run_side(req.query_a, req.model, req.num_samples),
        _run_side(req.query_b, req.model, req.num_samples),
    )

    _persist(db, side_a, req.model)
    _persist(db, side_b, req.model)
    db.commit()

    # Reuse the same similarity/clustering machinery as the uncertainty
    # engine to score agreement between the two sides' answers -- this is a
    # lightweight reuse (2-candidate comparison), not a new method.
    cross_comparison = estimate_uncertainty([side_a.answer, side_b.answer])

    return ExperimentResponse(
        side_a=side_a,
        side_b=side_b,
        response_agreement_between_sides=float(cross_comparison.response_agreement),
    )


def _load_benchmark_items(categories: list[str] | None, limit_per_category: int) -> list[dict]:
    data = json.loads(_DATA_PATH.read_text())
    items = list(data["items"])
    # Public, real-dataset-sourced items (TruthfulQA/SimpleQA -- see
    # data/build_benchmark.py and data/README.md) live in a separate file so
    # the hand-authored 54-item set stays intact and clearly
    # provenance-labeled; both are just "the benchmark" to this endpoint.
    if _PUBLIC_DATA_PATH.exists():
        public_data = json.loads(_PUBLIC_DATA_PATH.read_text())
        items.extend(public_data["items"])
    if categories:
        wanted = set(categories)
        items = [it for it in items if it["category"] in wanted]

    by_category: dict[str, list[dict]] = {}
    for item in items:
        by_category.setdefault(item["category"], []).append(item)

    selected: list[dict] = []
    for cat_items in by_category.values():
        selected.extend(cat_items[:limit_per_category])
    return selected


def _score(answer: str, expected: str | None, match_type: str | None) -> bool | None:
    if expected is None or match_type is None:
        return None
    if match_type == "substring":
        return expected.strip().lower() in answer.lower()
    if match_type == "any_substring":
        # `expected` is a "|||"-joined list of acceptable phrasings (real
        # datasets like TruthfulQA give multiple correct answers per
        # question) -- correct if ANY of them appears in the response.
        # Lenient by design: checks for an accepted phrasing, doesn't
        # penalize extra unrelated content (see data/README.md).
        candidates = [c.strip().lower() for c in expected.split("|||") if c.strip()]
        answer_lower = answer.lower()
        return any(c in answer_lower for c in candidates) if candidates else None
    if match_type == "numeric":
        match = re.search(r"-?\d+(?:\.\d+)?", answer.replace(",", ""))
        if not match:
            return False
        try:
            return abs(float(match.group()) - float(expected)) < 1e-6
        except ValueError:
            return False
    return None


async def _run_normal_condition(query: str, model: str) -> tuple[str, float]:
    """Condition 1: direct generation, no uncertainty sampling, no routing."""
    provider = get_provider(model)
    start = time.perf_counter()
    try:
        answer = await provider.generate(query)
    except LLMProviderError:
        provider = MockProvider()
        answer = await provider.generate(query)
    latency_ms = (time.perf_counter() - start) * 1000
    return answer, latency_ms


@router.post("/experiment/benchmark", response_model=BenchmarkResponse)
async def experiment_benchmark(req: BenchmarkRequest) -> BenchmarkResponse:
    items = _load_benchmark_items(req.categories, req.limit_per_category)

    results: list[BenchmarkItemResult] = []
    normal_latencies: list[float] = []
    routed_latencies: list[float] = []

    for item in items:
        normal_answer, normal_latency = await _run_normal_condition(item["query"], req.model)
        normal_latencies.append(normal_latency)

        routed_start = time.perf_counter()
        routed = await run_pipeline(query=item["query"], model=req.model, uncertainty_mode=True, num_samples=4)
        routed_latencies.append((time.perf_counter() - routed_start) * 1000)

        expected = item.get("expected_answer")
        match_type = item.get("match_type")

        results.append(
            BenchmarkItemResult(
                id=item["id"],
                category=item["category"],
                query=item["query"],
                expected_answer=expected,
                condition_normal_answer=normal_answer,
                condition_normal_correct=_score(normal_answer, expected, match_type),
                condition_routed_answer=routed.answer,
                condition_routed_correct=_score(routed.answer, expected, match_type),
                condition_routed_pathway=routed.pathway,
                condition_routed_abstained=routed.pathway == "VERIFY" and "don't have strong evidence" in routed.answer,
                hallucination_risk=routed.hallucination_risk.score,
            )
        )

    category_summaries: list[BenchmarkCategorySummary] = []
    by_category: dict[str, list[BenchmarkItemResult]] = {}
    for r in results:
        by_category.setdefault(r.category, []).append(r)

    for category, rows in by_category.items():
        normal_scored = [r.condition_normal_correct for r in rows if r.condition_normal_correct is not None]
        routed_scored = [r.condition_routed_correct for r in rows if r.condition_routed_correct is not None]
        abstained = sum(1 for r in rows if r.condition_routed_abstained)
        category_summaries.append(
            BenchmarkCategorySummary(
                category=category,
                n=len(rows),
                normal_accuracy=(sum(normal_scored) / len(normal_scored)) if normal_scored else None,
                routed_accuracy=(sum(routed_scored) / len(routed_scored)) if routed_scored else None,
                routed_abstention_rate=abstained / len(rows) if rows else 0.0,
                mean_hallucination_risk=sum(r.hallucination_risk for r in rows) / len(rows) if rows else 0.0,
            )
        )

    return BenchmarkResponse(
        model=req.model,
        items=results,
        category_summaries=category_summaries,
        normal_mean_latency_ms=sum(normal_latencies) / len(normal_latencies) if normal_latencies else 0.0,
        routed_mean_latency_ms=sum(routed_latencies) / len(routed_latencies) if routed_latencies else 0.0,
    )
