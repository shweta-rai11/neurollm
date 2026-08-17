"""Unit tests for app.cognitive_state.task_analyzer.analyze_task."""
from __future__ import annotations

from app.cognitive_state.task_analyzer import analyze_task
from app.models.schemas import TaskAnalysis

_FIELDS = [
    "complexity",
    "logical_reasoning",
    "creativity",
    "planning",
    "context_dependency",
    "verification_requirement",
    "risk",
    "ambiguity",
    "factuality_requirement",
]


def _assert_in_range(task: TaskAnalysis) -> None:
    for field in _FIELDS:
        value = getattr(task, field)
        assert 0 <= value <= 100, f"{field}={value} out of [0, 100]"


def test_coding_query_scores_high_logical_low_creativity():
    query = (
        "Write a Python function to implement binary search on a sorted "
        "array, and explain the algorithm's time complexity."
    )
    task = analyze_task(query)
    assert task.logical_reasoning > 50
    assert task.complexity > 30
    assert task.creativity < 20
    _assert_in_range(task)


def test_creative_query_scores_high_creativity():
    query = "Brainstorm five creative startup ideas and imagine a fictional story around them."
    task = analyze_task(query)
    assert task.creativity > 50
    _assert_in_range(task)


def test_empty_string_returns_all_zero_without_raising():
    task = analyze_task("")
    for field in _FIELDS:
        assert getattr(task, field) == 0


def test_whitespace_only_string_returns_all_zero_without_raising():
    task = analyze_task("   \n\t  ")
    for field in _FIELDS:
        assert getattr(task, field) == 0


def test_numbered_steps_query_scores_higher_planning_than_one_liner():
    step_query = (
        "1. First gather the requirements. 2. Then design the system. "
        "3. Next implement the modules. 4. Finally test everything end to end."
    )
    plain_query = "What is the capital of France?"

    step_task = analyze_task(step_query)
    plain_task = analyze_task(plain_query)

    assert step_task.planning > plain_task.planning


def test_medical_risk_query_scores_higher_risk_than_neutral_query():
    risk_query = "What is the recommended dosage for this medication, and what are the surgery risks?"
    neutral_query = "What's a good recipe for pancakes?"

    risk_task = analyze_task(risk_query)
    neutral_task = analyze_task(neutral_query)

    assert risk_task.risk > neutral_task.risk


def test_all_fields_within_bounds_across_sample_queries():
    sample_queries = [
        "Reverse a linked list in Python.",
        "Brainstorm ten wild ideas for a birthday party.",
        "Should I invest in this stock? What's the best treatment for a headache?",
        "Based on the attached document, summarize the key findings.",
        "Who discovered penicillin and when was it discovered?",
        "Plan a step-by-step roadmap for launching a new product.",
        "",
        "a",
        "x" * 500,
        "Is it true that the earth is flat? Cite your sources.",
    ]
    for query in sample_queries:
        task = analyze_task(query)
        _assert_in_range(task)
