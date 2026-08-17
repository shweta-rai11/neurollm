"""Deterministic, offline mock LLM provider.

Works with zero API keys and is fully reproducible: randomness is seeded
from a stable hash of the query text (never from unseeded `random`), so the
same query always produces the same candidates across runs -- this matters
for tests and demo consistency.

Response variation is deliberately shaped by task category so that the
downstream uncertainty engine (app/cognitive_state/uncertainty.py) sees
realistic signal:

    - coding / math queries: candidates are near-identical in substance
      (only the wrapping phrasing is paraphrased) -> low semantic
      uncertainty when clustered.
    - predictive / open "who will win" / "best treatment" style queries:
      candidates give meaningfully different, hedged, non-committal, and
      mutually disagreeing answers -> high semantic uncertainty when
      clustered. This is intentional: the mock provider must never present
      a single confident answer to a genuinely unresolved question.
    - creative queries: candidates are diverse (different ideas/phrasings)
      but not framed as disagreeing with each other.
    - everything else (factual/planning/generic): mild paraphrase
      variation, similar in spirit to coding/math but with different
      wrapper text.
"""
from __future__ import annotations

import hashlib
import random

from app.llm.provider import LLMProvider

_CODE_KEYWORDS = [
    "function", "algorithm", "python", "javascript", "typescript", "code",
    "program", "class ", "def ", "implement", "compile", "debug", "regex",
    "sql", "api", "recursion", "linked list", "array", "sort", "loop",
]

_MATH_KEYWORDS = [
    "equation", "derivative", "integral", "matrix", "probability", "theorem",
    "proof", "calculate", "solve for", "differential", "algebra", "geometry",
    "statistics", "vector", "eigenvalue", "sum of",
]

_CREATIVE_KEYWORDS = [
    "brainstorm", "creative", "idea", "ideas", "poem", "story", "invent",
    "imagine", "design a", "novel", "startup idea", "name for", "slogan",
    "write a song", "metaphor", "fictional", "generate five", "generate 5",
]

_PLANNING_KEYWORDS = [
    "plan", "roadmap", "step 1", "steps to", "strategy", "milestones",
    "timeline", "workflow", "outline", "phases", "break down",
]

_FACTUAL_KEYWORDS = [
    "who", "when", "what year", "how many", "where is", "capital of",
    "discovered", "invented", "founded", "population of", "born in",
]

# Genuinely ambiguous / open / predictive queries -- the mock provider must
# NOT answer these as settled fact. Candidates should disagree with each
# other so the uncertainty engine correctly reports high disagreement.
_PREDICTIVE_KEYWORDS = [
    "will win", "who will", "predict", "best treatment", "best cure",
    "going to happen", "next president", "future of", "will happen",
    "who will be", "what will", "should i invest", "best stock",
]


def _detect_category(query: str) -> str:
    lowered = query.lower()
    if any(kw in lowered for kw in _PREDICTIVE_KEYWORDS):
        return "predictive"
    if any(kw in lowered for kw in _CODE_KEYWORDS):
        return "coding"
    if any(kw in lowered for kw in _MATH_KEYWORDS):
        return "math"
    if any(kw in lowered for kw in _CREATIVE_KEYWORDS):
        return "creative"
    if any(kw in lowered for kw in _PLANNING_KEYWORDS):
        return "planning"
    if any(kw in lowered for kw in _FACTUAL_KEYWORDS):
        return "factual"
    return "generic"


def _snippet(query: str, max_len: int = 60) -> str:
    q = query.strip().replace("\n", " ")
    if len(q) <= max_len:
        return q
    return q[:max_len].rstrip() + "..."


def _seed_for(query: str) -> int:
    digest = hashlib.sha256(query.encode("utf-8")).hexdigest()
    return int(digest[:16], 16)


# A handful of well-known problems get a real, working reference
# implementation instead of the generic placeholder below -- several of
# these are the exact demo/example questions used throughout the product
# spec (reverse a linked list, sort a list, anomaly detection, orbital
# velocity), so the mock provider should look substantive for them without
# pretending to be a general-purpose code generator for arbitrary queries.
_CANONICAL_CODE_SOLUTIONS: list[tuple[list[str], str]] = [
    (
        ["reverse", "linked list"],
        "```python\n"
        "class Node:\n"
        "    def __init__(self, value, next=None):\n"
        "        self.value = value\n"
        "        self.next = next\n\n"
        "def reverse_linked_list(head):\n"
        "    previous = None\n"
        "    current = head\n"
        "    while current is not None:\n"
        "        next_node = current.next\n"
        "        current.next = previous\n"
        "        previous = current\n"
        "        current = next_node\n"
        "    return previous  # new head\n"
        "```\n"
        "This walks the list once, reversing each `next` pointer as it "
        "goes. Time complexity is O(n), space complexity is O(1)."
    ),
    (
        ["sort", "list"],
        "```python\n"
        "def sort_list(items):\n"
        "    if len(items) <= 1:\n"
        "        return items\n"
        "    mid = len(items) // 2\n"
        "    left = sort_list(items[:mid])\n"
        "    right = sort_list(items[mid:])\n"
        "    merged = []\n"
        "    i = j = 0\n"
        "    while i < len(left) and j < len(right):\n"
        "        if left[i] <= right[j]:\n"
        "            merged.append(left[i]); i += 1\n"
        "        else:\n"
        "            merged.append(right[j]); j += 1\n"
        "    merged.extend(left[i:])\n"
        "    merged.extend(right[j:])\n"
        "    return merged\n"
        "```\n"
        "A standard merge sort: O(n log n) time, stable, and doesn't rely "
        "on the built-in `sorted()` so the mechanics are visible."
    ),
    (
        ["anomaly", "genomic"],
        "```python\n"
        "import statistics\n\n"
        "def detect_anomalies(values, z_threshold=3.0):\n"
        "    mean = statistics.mean(values)\n"
        "    stdev = statistics.pstdev(values) or 1e-9\n"
        "    anomalies = []\n"
        "    for i, v in enumerate(values):\n"
        "        z = (v - mean) / stdev\n"
        "        if abs(z) > z_threshold:\n"
        "            anomalies.append((i, v, round(z, 2)))\n"
        "    return anomalies\n"
        "```\n"
        "A simple z-score outlier detector over per-sample values (e.g. "
        "read depth or expression level per locus). Real genomic anomaly "
        "detection pipelines typically add position-aware smoothing and "
        "domain-specific normalization on top of this kind of baseline."
    ),
    (
        ["orbital velocity"],
        "```python\n"
        "import math\n\n"
        "def orbital_velocity(gravitational_parameter, orbital_radius):\n"
        "    \"\"\"Circular orbital speed: v = sqrt(GM / r).\"\"\"\n"
        "    return math.sqrt(gravitational_parameter / orbital_radius)\n\n"
        "MARS_MU = 4.282837e13  # m^3/s^2\n"
        "MARS_RADIUS_PLUS_ALT = 3_389_500 + 400_000  # m, low orbit example\n"
        "print(orbital_velocity(MARS_MU, MARS_RADIUS_PLUS_ALT))\n"
        "```\n"
        "Uses the standard circular-orbit relation v = sqrt(GM / r) with "
        "Mars's gravitational parameter; swap in the desired orbital radius."
    ),
    (
        ["fibonacci"],
        "```python\n"
        "def fibonacci(n):\n"
        "    a, b = 0, 1\n"
        "    for _ in range(n):\n"
        "        a, b = b, a + b\n"
        "    return a\n"
        "```\n"
        "Iterative O(n) time, O(1) space -- avoids the exponential blowup "
        "of a naive recursive implementation."
    ),
    (
        ["binary search"],
        "```python\n"
        "def binary_search(sorted_items, target):\n"
        "    lo, hi = 0, len(sorted_items) - 1\n"
        "    while lo <= hi:\n"
        "        mid = (lo + hi) // 2\n"
        "        if sorted_items[mid] == target:\n"
        "            return mid\n"
        "        if sorted_items[mid] < target:\n"
        "            lo = mid + 1\n"
        "        else:\n"
        "            hi = mid - 1\n"
        "    return -1\n"
        "```\n"
        "O(log n) time. Requires `sorted_items` to already be sorted."
    ),
]


def _canonical_solution(query: str) -> str | None:
    lowered = query.lower()
    for keywords, solution in _CANONICAL_CODE_SOLUTIONS:
        if all(kw in lowered for kw in keywords):
            return solution
    return None


def _coding_pool(query: str) -> list[str]:
    snippet = _snippet(query)
    canonical = _canonical_solution(query)
    core = canonical or (
        "```python\n"
        "def solve(*args, **kwargs):\n"
        f"    # Addresses: {snippet}\n"
        "    result = None\n"
        "    # validate input, then process the relevant structure\n"
        "    return result\n"
        "```\n"
        "The approach validates the input, processes the relevant data "
        "structure, and returns the computed result. Typical time "
        "complexity is O(n) for inputs of this shape."
    )
    openers = [
        "Here's one way to do it:",
        "Sure, here's an approach:",
        "You can solve this as follows:",
        "Here's a working solution:",
        "This should work:",
        "Try this implementation:",
        "Here's a straightforward approach:",
        "One clean way to implement this:",
        "Here's a solution that handles the common case:",
        "This implementation should get you there:",
    ]
    return [f"{opener}\n\n{core}" for opener in openers]


def _math_pool(query: str) -> list[str]:
    snippet = _snippet(query)
    core = (
        f"Step 1: Identify the given quantities for: {snippet}\n"
        "Step 2: Set up the relevant equation or rule.\n"
        "Step 3: Simplify and solve for the unknown.\n"
        "Step 4: Verify by substituting the result back into the original expression.\n"
        "Final answer: the solution follows directly from the steps above."
    )
    openers = [
        "Let's work through this step by step.",
        "Here's the derivation:",
        "Solving this methodically:",
        "Here's how to approach it:",
        "Walking through the math:",
        "Here's the solution path:",
        "Let's break this down:",
        "Working this out carefully:",
        "Here's a clean derivation:",
        "Step-by-step solution:",
    ]
    return [f"{opener}\n\n{core}" for opener in openers]


def _creative_pool(query: str) -> list[str]:
    snippet = _snippet(query)
    return [
        f"Idea 1: {snippet} reimagined through a nostalgic, retro lens.",
        f"Idea 2: A minimalist take on {snippet}, stripped down to its emotional core.",
        f"Idea 3: A bold, high-energy version of {snippet} aimed at a younger audience.",
        f"Idea 4: An unexpected mashup — combine {snippet} with an unrelated theme for novelty.",
        f"Idea 5: A story-driven approach to {snippet}, built around a small narrative.",
        f"Idea 6: A playful, humorous spin on {snippet}.",
        f"Idea 7: A quiet, understated take on {snippet} that lets the idea breathe.",
        f"Idea 8: A futuristic reinterpretation of {snippet}.",
        f"Idea 9: A hand-crafted, artisanal framing of {snippet}.",
        f"Idea 10: A surreal, dreamlike variation on {snippet}.",
    ]


def _predictive_pool(query: str) -> list[str]:
    # Deliberately conflicting, hedged, non-committal candidates -- this
    # query category must never be answered as settled fact.
    return [
        "This is genuinely uncertain. Based on currently available signals, Option A appears to have a slight edge, but that could easily change.",
        "There's no clear consensus here — some indicators favor Option B, while others point to a close contest.",
        "It's hard to say with confidence. A number of observers lean toward Option C, though this is far from settled.",
        "The outcome is unpredictable. Option A, Option B, or an unexpected alternative could all plausibly happen.",
        "Views are mixed: some evidence points to Option B, other evidence points to Option D, so no single answer is reliable here.",
        "This can't be answered with certainty. Multiple outcomes remain plausible, and any specific prediction should be treated with skepticism.",
        "Opinions diverge sharply — roughly half the relevant signals point one way, half the other, so it's essentially a toss-up.",
        "I would avoid committing to a single answer here; Option A and Option C both have credible paths, among other possibilities.",
        "Forecasts disagree: some models favor Option A, others favor Option D, and the gap between them is narrow.",
        "Nobody can say for sure. This depends on factors that haven't played out yet, so treat any single answer with caution.",
    ]


def _generic_pool(query: str, category: str) -> list[str]:
    snippet = _snippet(query)
    label = {
        "factual": "Based on the available information",
        "planning": "Here's a workable plan",
        "generic": "Here's a direct answer",
    }.get(category, "Here's a direct answer")
    core = (
        f"{label} regarding: {snippet}. The key points are summarized "
        "concisely below, covering the essentials without unnecessary detail."
    )
    openers = [
        "To answer directly:",
        "Here's a concise answer:",
        "In short:",
        "Here's what's relevant:",
        "Summarizing the key points:",
        "Here's the core answer:",
        "To address this directly:",
        "Here's a clear answer:",
        "Getting straight to it:",
        "Here's the relevant information:",
    ]
    return [f"{opener}\n\n{core}" for opener in openers]


def _pool_for(query: str, category: str) -> list[str]:
    if category == "predictive":
        return _predictive_pool(query)
    if category == "coding":
        return _coding_pool(query)
    if category == "math":
        return _math_pool(query)
    if category == "creative":
        return _creative_pool(query)
    return _generic_pool(query, category)


class MockProvider(LLMProvider):
    """Offline, deterministic provider requiring no API key."""

    async def generate(self, query: str) -> str:
        candidates = await self.generate_multiple(query, 1)
        return candidates[0]

    async def generate_multiple(self, query: str, n: int) -> list[str]:
        if not query or not query.strip():
            return ["(empty query)"] * max(1, n)

        category = _detect_category(query)
        pool = _pool_for(query, category)
        rng = random.Random(_seed_for(query))

        if n <= len(pool):
            # Deterministic (seeded) shuffle, then take the first n so the
            # canonical (index 0) answer is stable for a given query.
            shuffled = pool[:]
            rng.shuffle(shuffled)
            return shuffled[:n]

        # n exceeds the pool size (shouldn't happen given max_num_samples
        # is bounded well below pool sizes, but handle it defensively).
        result = pool[:]
        while len(result) < n:
            idx = rng.randrange(len(pool))
            result.append(pool[idx])
        return result[:n]

    def get_model_info(self) -> dict:
        return {
            "name": "mock-v1",
            "provider": "mock",
            "description": "Deterministic offline mock provider; requires no API key and is safe for demos/tests.",
        }
