"""Shared pytest configuration for the AI-Brain backend test suite.

Pytest imports every `conftest.py` in a test directory before it imports any
`test_*.py` module inside that directory, which is exactly the hook this
file needs: `app.config.Settings` reads its values from environment
variables at *import* time, so we must set those variables here -- before
any test module gets a chance to `import app...` and freeze the settings
singleton with the wrong values.

Test isolation choices made here (see test_api_integration.py for how they
are exercised):
  - DATABASE_URL points at a fresh temporary sqlite file so the suite never
    touches the real dev `ai_brain.db` and always starts from an empty
    schema.
  - OPENAI_API_KEY is forced empty so `settings.has_openai_key` is False
    regardless of the developer's real shell environment, meaning
    `get_provider(...)` always resolves to the deterministic, offline
    MockProvider. The whole suite runs with no network access and no real
    API key required.
  - ENABLE_LOCAL_MODEL is forced "0" so /api/config's available_models
    never lists "local_hf" during the default test run either -- no test in
    this suite triggers a real multi-GB model download/load. Tests that
    specifically exercise the local_hf/research_mode pathway do so through
    a fake provider (see tests/_helpers.py FakeLocalProvider), not the real
    one.
  - RATE_LIMIT_PER_MINUTE is raised well above anything a single pytest run
    could generate from one TestClient "IP", so the in-process rate limiter
    in app.main never produces a spurious 429 during the test session.
  - BRAVE_SEARCH_API_KEY is forced empty so `app.retrieval.brave_search.is_available()`
    is always False regardless of the developer's real `.env` -- retrieval-
    augmented behavior is exercised via monkeypatching/fakes (see
    tests/test_retrieval.py, test_fact_check.py), never a real API call.
"""
from __future__ import annotations

import os
import tempfile

_tmp_db_fd, _tmp_db_path = tempfile.mkstemp(prefix="ai_brain_test_", suffix=".db")
os.close(_tmp_db_fd)

os.environ["DATABASE_URL"] = f"sqlite:///{_tmp_db_path}"
os.environ["OPENAI_API_KEY"] = ""
os.environ["ENABLE_LOCAL_MODEL"] = "0"
os.environ["RATE_LIMIT_PER_MINUTE"] = "10000"
os.environ["BRAVE_SEARCH_API_KEY"] = ""
