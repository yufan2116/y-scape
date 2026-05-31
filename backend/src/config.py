"""Application configuration."""

from __future__ import annotations

import os
from pathlib import Path

from pydantic import AliasChoices, Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

_BACKEND_ROOT = Path(__file__).resolve().parents[1]
_ENV_FILE = _BACKEND_ROOT / ".env"


class Settings(BaseSettings):
    runs_dir: Path = Path("runs_active")
    workspace_root: Path = Path("workspace")
    artifact_root: Path = Path("tool_artifacts")
    max_artifact_size_mb: int = 50
    default_output_dir: Path = Path("tool_output")
    dry_run_default: bool = True
    status_polling_interval_ms: int = 2000
    model_provider: str = "demo"
    model_name: str = "deepseek-v4-flash"
    demo_mode: bool = False
    deepseek_api_key: SecretStr = Field(
        default=SecretStr(""),
        validation_alias=AliasChoices("DEEPSEEK_API_KEY", "YSCAPE_DEEPSEEK_API_KEY"),
    )
    deepseek_api_base: str = "https://api.deepseek.com"
    deepseek_thinking: bool = False
    stale_threshold_seconds: int = 120
    snapshot_flush_delay_seconds: float = 0.3
    max_iterations: int = 8
    planner_timeout_seconds: int = 20
    llm_timeout_seconds: int = 90
    tool_timeout_seconds: int = 30
    agent_loop_timeout_seconds: int = 600
    event_buffer_size: int = 200
    sse_heartbeat_seconds: int = 15
    max_quality_failures: int = 3
    min_research_report_chars: int = 800

    model_config = SettingsConfigDict(
        env_prefix="YSCAPE_",
        env_file=_ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        if os.getenv("DEMO_MODE", "").lower() in {"1", "true", "yes"}:
            self.demo_mode = True

    @property
    def api_key_configured(self) -> bool:
        return bool(self.deepseek_api_key.get_secret_value().strip())

    def deepseek_chat_completions_url(self) -> str:
        base = self.deepseek_api_base.rstrip("/")
        if base.endswith("/v1"):
            return f"{base}/chat/completions"
        return f"{base}/v1/chat/completions"


settings = Settings()
