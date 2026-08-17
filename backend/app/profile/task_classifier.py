"""Task/question -> category + candidate virtual systems (product spec
sections 8 and 14).

This is deliberately independent of the fingerprint/profile lookup: the
*question* decides which virtual systems are candidates for this turn, the
same deterministic-keyword-heuristic style as `task_analyzer.py`. The
Individual Computational Profile only adjusts the *parameters* used within
those systems (see `app.brain.regions`/`app.brain.neuromodulation` wiring)
-- it never picks which systems are candidates.

"Candidate virtual systems" are named after real neuroanatomical regions as
an illustrative, application-level metaphor -- exactly like the existing
5-region system in `app.brain.regions` -- not a claim that this software
activates those regions. See README "Positioning".
"""
from __future__ import annotations

from dataclasses import dataclass

from app.models.schemas import TaskAnalysis
from app.profile.params import TASK_CATEGORIES

_MIN_CATEGORY_SCORE = 0.18
_AMBIGUOUS_MARGIN = 0.08  # top two scores this close -> treat as ambiguous


def _keyword_score(text: str, keywords: list[str]) -> float:
    lowered = text.lower()
    hits = sum(1 for kw in keywords if kw in lowered)
    if hits == 0:
        return 0.0
    return min(1.0, 1 - (0.55**hits))


_CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "mathematics": [
        "equation", "derivative", "integral", "matrix", "probability", "theorem",
        "proof", "calculate", "solve for", "algebra", "geometry", "statistics",
        "sum of", "square root", "percent", "how much is", "times", "multiplied",
        "multiply", "divided by", "divide", "plus", "minus", "subtract", "average of",
        "what is the total", "squared", "cubed",
    ],
    "coding": [
        "function", "algorithm", "python", "javascript", "code", "program",
        "class ", "def ", "implement", "debug", "regex", "sql", "api", "compile",
        "syntax", "array", "loop", "variable",
    ],
    "scientific_reasoning": [
        "hypothesis", "experiment", "evidence", "theory", "why does", "what causes",
        "mechanism", "biology", "chemistry", "physics", "scientific", "research shows",
        "caused by", "explain how",
    ],
    "factual_retrieval": [
        "who", "when", "what year", "how many", "where is", "capital of",
        "discovered", "invented", "founded", "population of", "born in", "fact",
    ],
    "creative_generation": [
        "brainstorm", "creative", "poem", "story", "invent", "imagine", "design a",
        "novel", "slogan", "write a song", "metaphor", "fictional", "generate five",
        "name for", "come up with",
    ],
    "decision_making": [
        "should i", "which one", "recommend", "best option", "decide", "trade-off",
        "pros and cons", "worth it", "choose between", "better to",
    ],
    "social_reasoning": [
        "feel", "relationship", "friend", "coworker", "conflict", "empathy",
        "perspective", "social", "conversation with", "how would they react",
        "emotion", "trust",
    ],
    "planning": [
        "plan", "roadmap", "step 1", "steps to", "strategy", "milestones",
        "timeline", "workflow", "outline", "phases", "break down", "schedule",
    ],
}

_CANDIDATE_SYSTEMS: dict[str, list[str]] = {
    "mathematics": [
        "Prefrontal executive network", "Frontoparietal network", "Anterior cingulate",
        "Working-memory systems", "Thalamic routing", "Basal-ganglia cognitive gating",
    ],
    "coding": [
        "Prefrontal executive network", "Frontoparietal network", "Working-memory systems",
        "Basal-ganglia procedural systems", "Error-monitoring network",
    ],
    "scientific_reasoning": [
        "Prefrontal executive network", "Frontoparietal network", "Anterior cingulate",
        "Hippocampal/temporal retrieval", "Verification systems",
    ],
    "factual_retrieval": [
        "Hippocampal system (functional analogue)", "Temporal systems",
        "Prefrontal retrieval control", "Memory networks",
    ],
    "creative_generation": [
        "Association/generative network", "Prefrontal generative control",
        "Semantic and temporal association areas",
    ],
    "decision_making": [
        "Orbitofrontal cortex (OFC)", "Ventromedial prefrontal cortex (vmPFC)",
        "Dorsolateral prefrontal cortex (dlPFC)", "Anterior cingulate", "Striatum",
        "Thalamus", "Limbic systems",
    ],
    "social_reasoning": [
        "Medial prefrontal cortex (mPFC)", "Temporal regions",
        "Temporoparietal junction (TPJ)", "Amygdala (functional analogue)", "Insula",
        "Salience / social-cognition network",
    ],
    "planning": [
        "Prefrontal executive network", "Frontoparietal network",
        "Basal-ganglia sequencing", "Working-memory systems",
    ],
    "ambiguous": [
        "Uncertainty / salience network", "Prefrontal control network",
        "Anterior cingulate (conflict monitoring)",
    ],
}


@dataclass
class TaskCategoryResult:
    category: str
    confidence: float
    scores: dict[str, float]
    candidate_systems: list[str]


def classify_task_category(query: str, task: TaskAnalysis) -> TaskCategoryResult:
    scores: dict[str, float] = {}
    for category in TASK_CATEGORIES:
        if category == "ambiguous":
            continue
        scores[category] = _keyword_score(query, _CATEGORY_KEYWORDS[category])

    # Task-heuristic tie-breakers, mirroring the same signals the rest of the
    # pipeline already trusts (task_analyzer.py), rather than inventing new ones.
    scores["mathematics"] = max(scores["mathematics"], task.logical_reasoning / 100.0 * 0.3)
    scores["creative_generation"] = max(scores["creative_generation"], task.creativity / 100.0 * 0.5)
    scores["planning"] = max(scores["planning"], task.planning / 100.0 * 0.4)
    scores["factual_retrieval"] = max(scores["factual_retrieval"], task.factuality_requirement / 100.0 * 0.4)

    ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
    top_category, top_score = ranked[0]
    second_score = ranked[1][1] if len(ranked) > 1 else 0.0

    if top_score < _MIN_CATEGORY_SCORE or (top_score - second_score) < _AMBIGUOUS_MARGIN:
        category = "ambiguous"
        confidence = 1.0 - top_score  # low separation/low signal -> genuinely ambiguous
    else:
        category = top_category
        confidence = top_score

    scores["ambiguous"] = round(max(0.0, 1.0 - top_score), 3)

    return TaskCategoryResult(
        category=category,
        confidence=round(min(1.0, max(0.0, confidence)), 3),
        scores={k: round(v, 3) for k, v in scores.items()},
        candidate_systems=list(_CANDIDATE_SYSTEMS[category]),
    )
