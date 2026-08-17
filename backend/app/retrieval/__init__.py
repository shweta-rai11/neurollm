"""Real, external retrieval for the VERIFY pathway's fact-check step.

This is what upgrades verification from "the model checking its own prior
candidates" (self-critique -- known to be an unreliable signal, see
app.brain.executive_controller's original self-verifier) to "the model
checking a real, externally retrieved source" -- still not ground truth, but
a materially different and stronger signal. Best-effort throughout: no
retrieval-related failure (missing key, network error, malformed response)
is allowed to break the chat pipeline; the caller always gets a clean
"unavailable" signal (`None`/`[]`) instead of an exception.
"""
