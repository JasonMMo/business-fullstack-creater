"""
web/settings.py — env-based configuration for the FastAPI web layer.

SaaS-readiness note: all paths are scoped via env vars so a future
multi-tenant deployment can inject TENANT_ID/USER_ID namespacing at
the infrastructure layer without changing application code.
No global mutable state — create a new Settings instance per call if needed.
"""
import os
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent


class Settings:
    """Lightweight env-var wrapper. No external deps (pydantic-settings deferred to M4)."""

    def __init__(self) -> None:
        self.web_host: str = os.environ.get("WEB_HOST", "127.0.0.1")
        self.web_port: int = int(os.environ.get("WEB_PORT", "8000"))
        self.scaffold_out_dir: str = os.environ.get("SCAFFOLD_OUT_DIR", "out/")
        self.scaffold_cli_path: str = os.environ.get(
            "SCAFFOLD_CLI_PATH", "scripts/scaffold_cli.py"
        )
        self.creater_root: str = os.environ.get("CREATER_ROOT", str(_REPO_ROOT))


def get_settings() -> Settings:
    """Factory function — call this instead of importing a singleton."""
    return Settings()
