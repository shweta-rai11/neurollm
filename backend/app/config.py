"""Application configuration loaded from environment variables."""
from __future__ import annotations

import os

from dotenv import load_dotenv

load_dotenv()


class Settings:
    app_name: str = "AI-Brain"
    version: str = "0.1.0"

    openai_api_key: str | None = os.getenv("OPENAI_API_KEY") or None
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    # Real external retrieval for the VERIFY pathway's fact-check step (see
    # app/retrieval/). Optional -- when unset, VERIFY falls back to its
    # original self-critique-only behavior rather than failing.
    brave_search_api_key: str | None = os.getenv("BRAVE_SEARCH_API_KEY") or None

    default_model: str = os.getenv("DEFAULT_MODEL", "mock")
    default_num_samples: int = int(os.getenv("DEFAULT_NUM_SAMPLES", "5"))
    max_num_samples: int = int(os.getenv("MAX_NUM_SAMPLES", "10"))

    # Local, activation-inspectable model -- enabled by default for normal
    # runs, but the test suite's conftest.py forces ENABLE_LOCAL_MODEL=0 so
    # CI never accidentally triggers a multi-GB download / slow load just by
    # listing it in /api/config's available_models.
    enable_local_model: bool = os.getenv("ENABLE_LOCAL_MODEL", "1") == "1"

    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./ai_brain.db")

    # capacitor://localhost (iOS) and http(s)://localhost (Android) are the
    # fixed origins Capacitor's native WebView always uses for the bundled
    # app (see frontend/MOBILE.md) -- they identify "the native app shell",
    # not a third-party site, so allowing them by default doesn't broaden
    # the CORS surface the way allowing "*" would.
    cors_origins: list[str] = os.getenv(
        "CORS_ORIGINS",
        "http://localhost:5173,http://localhost:3000,capacitor://localhost,http://localhost,https://localhost",
    ).split(",")

    max_request_body_bytes: int = int(os.getenv("MAX_REQUEST_BODY_BYTES", str(64 * 1024)))
    rate_limit_per_minute: int = int(os.getenv("RATE_LIMIT_PER_MINUTE", "60"))

    # Fingerprint uploads need a much larger cap than the default request
    # body limit above -- checked specifically for /api/biometric/* paths
    # (see app.main.MaxBodySizeMiddleware), leaving every other route's cap
    # unchanged.
    max_fingerprint_image_bytes: int = int(os.getenv("MAX_FINGERPRINT_IMAGE_BYTES", str(8 * 1024 * 1024)))

    # Symmetric key used to encrypt stored biometric templates at rest (see
    # app/profile/crypto.py). The fallback below is a FIXED, publicly-known
    # value -- fine for local development (and for the test suite, which
    # never sets this env var) but NOT secure for any real deployment.
    # Production deployments MUST set BIOMETRIC_ENCRYPTION_KEY to a real
    # secret (e.g. `python -c "from cryptography.fernet import Fernet;
    # print(Fernet.generate_key().decode())"`).
    biometric_encryption_key: str = os.getenv(
        "BIOMETRIC_ENCRYPTION_KEY", "isZmglbzjQFuJYAZI33hkrQ0OrP4WoDO_6DLyWJCtSM="
    )

    @property
    def has_openai_key(self) -> bool:
        return bool(self.openai_api_key)

    @property
    def available_models(self) -> list[str]:
        models = ["mock"]
        if self.enable_local_model:
            models.append("local_hf")
        if self.has_openai_key:
            models.append(self.openai_model)
        return models


settings = Settings()
