"""Real activation extraction from a local, inspectable open-weight model.

Nothing in this package is a metaphor -- these are genuine tensors read off
a live forward pass (hidden states, attention weights, next-token logits).
The neuroscience-inspired interpretation of these numbers happens one layer
up, in `app.brain` -- see that package's module docstrings for the
"computational analogy, not biology" framing required by the project's
scientific-language guardrails.
"""
