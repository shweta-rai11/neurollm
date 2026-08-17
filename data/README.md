# Benchmark dataset

`benchmark.json` is a small, hand-authored benchmark covering the question categories described
in the NeuroLLM spec (factual, mathematical, logical, causal, creative, ambiguous, conflicting,
hallucination-prone, multi-hop, medical/high-stakes). It exists for two purposes:

1. **Probe training** (`backend/app/probes/train.py`) - supervised examples for the
   category-classification probe.
2. **Condition comparison** (`POST /api/experiment/benchmark`) - a real, bounded accuracy
   measurement for the "does virtual-brain routing improve reliability" experiment.

## `expected_answer` / `match_type`

Only **factual**, **mathematical**, and **logical** items (and the two `multi_hop` items whose
first hop resolves to an unambiguous, stable fact) carry an `expected_answer` - these are the
only categories where "correct" has an objective, checkable meaning at the scale of this MVP.
`match_type` is either:

- `"substring"` - case-insensitive substring match against the model's answer.
- `"numeric"` - the first number found in the model's answer must equal `expected_answer`
  (within floating-point tolerance).

Every other category has `expected_answer: null` deliberately, not by omission - open-ended,
ambiguous, conflicting-evidence, and "medical/high-stakes" questions do not have a single correct
string to match, and obscure/hallucination-prone questions are included specifically to observe
*whether the system abstains*, not to grade a specific factual claim (several of them concern
facts we could not verify with confidence ourselves, which is the point: they're designed to be
plausible-sounding but unverifiable/obscure).

## Synthetic, not clinical

The `medical_high_stakes` category exists to test how the system's risk/verification signals
behave on higher-stakes phrasing. These are generic textbook-style prompts for research purposes
only - this project is not a clinical decision tool and none of its output should be treated as
medical advice (see the main README's Limitations section).

## Size

This is intentionally small (~50 items) for an MVP - enough to give the probe and the condition
comparison real signal to work with, not a claim of benchmark-scale coverage. Expanding it is
listed as future work in the main README.
