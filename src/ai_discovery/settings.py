"""Runtime configuration (env-driven, pydantic-settings)."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """All values can be overridden with AI_DISCOVERY_* env vars (see .env.example)."""

    model_config = SettingsConfigDict(env_prefix="AI_DISCOVERY_", env_file=".env", extra="ignore")

    database_url: str = (
        "postgresql+psycopg://ai_discovery:ai_discovery@localhost:55432/ai_discovery"
    )
    sources_config: Path = REPO_ROOT / "config" / "sources.yaml"
    # Raw HTML snapshots are private: they stay on local disk, never in the API.
    snapshot_dir: Path = REPO_ROOT / "var" / "snapshots"
    # Identifies the project repo only (no personal/work contact address).
    user_agent: str = (
        "ai-discovery-intelligence/0.1 (+https://github.com/Rajeev-SG/ai-discovery-intelligence)"
    )
    request_timeout_seconds: float = 25.0
    # Politeness: per-host minimum delay between requests (seconds).
    per_host_delay_seconds: float = 2.0
    max_concurrency: int = 4
    api_cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.api_cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
