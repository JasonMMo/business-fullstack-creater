"""
web/adapters/fulltest_runner.py — Adapter: FastAPI web layer → full_test CLI subprocess.
# Growth-83

Critical: MUST NOT re-implement full-test logic.
Calls `python -m scripts.workflow.full_test <lane> [domain] --json`.
"""
from __future__ import annotations
import json
import os
import subprocess
import sys
from dataclasses import dataclass, field
from web.settings import get_settings


@dataclass
class FullTestJobResult:
    label: str
    lane: str
    layers: dict = field(default_factory=dict)
    next_hint: str | None = None
    scaffold: str | None = None
    error: str | None = None
    returncode: int = -1

    @property
    def green(self) -> bool:
        return self.layers.get("L4_full", False)

    def to_dict(self) -> dict:
        return {
            "label": self.label,
            "lane": self.lane,
            "layers": self.layers,
            "next_hint": self.next_hint,
            "scaffold": self.scaffold,
            "error": self.error,
            "returncode": self.returncode,
            "green": self.green,
        }


def run(lane: str, scaffold_dir: str, *, timeout_sec: int = 600) -> FullTestJobResult:
    """Spawn full_test CLI with --json and parse result.
    Sets FULLTEST_NO_LEARNLOG=1 to prevent learn-log mutation from web context.
    """
    settings = get_settings()
    env = {**os.environ, "FULLTEST_NO_LEARNLOG": "1"}
    argv = [
        sys.executable, "-m", "scripts.workflow.full_test",
        lane, scaffold_dir, "--json",
    ]
    try:
        proc = subprocess.run(
            argv,
            capture_output=True,
            text=True,
            timeout=timeout_sec,
            env=env,
            cwd=settings.creater_root,
        )
        data = json.loads(proc.stdout)
        return FullTestJobResult(
            label=data.get("label", ""),
            lane=data.get("lane", lane),
            layers=data.get("layers", {}),
            next_hint=data.get("next_hint"),
            scaffold=data.get("scaffold"),
            returncode=proc.returncode,
        )
    except subprocess.TimeoutExpired:
        return FullTestJobResult(label="타임아웃", lane=lane, error="full-test timeout (600s)", returncode=-2)
    except Exception as exc:
        return FullTestJobResult(label="오류", lane=lane, error=str(exc), returncode=-1)
