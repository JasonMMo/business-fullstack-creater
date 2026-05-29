"""
web/fulltest_registry.py — In-memory full-test job registry with single-flight lock.
# Growth-83
"""
from __future__ import annotations
import threading
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Optional

from web.adapters.fulltest_runner import FullTestJobResult


class JobStatus(str, Enum):
    RUNNING = "running"
    DONE = "done"
    ERROR = "error"


@dataclass
class FullTestJob:
    job_id: str
    run_id: str   # scaffold run_id from run_registry
    lane: str
    status: JobStatus = JobStatus.RUNNING
    result: Optional[FullTestJobResult] = None


_jobs: Dict[str, FullTestJob] = {}
_lock = threading.Lock()
_running_run_id: Optional[str] = None   # single-flight: only one run at a time


def start(run_id: str, lane: str, scaffold_dir: str) -> tuple[str, bool]:
    """Start a background full-test job.

    Returns (job_id, started). started=False means a job for this run_id
    is already running (caller should 409).
    """
    global _running_run_id
    with _lock:
        if _running_run_id is not None:
            return "", False
        job_id = uuid.uuid4().hex
        job = FullTestJob(job_id=job_id, run_id=run_id, lane=lane)
        _jobs[job_id] = job
        _running_run_id = run_id

    def _worker():
        global _running_run_id
        from web.adapters import fulltest_runner
        result = fulltest_runner.run(lane, scaffold_dir)
        with _lock:
            job.result = result
            job.status = JobStatus.DONE if not result.error else JobStatus.ERROR
            _running_run_id = None

    t = threading.Thread(target=_worker, daemon=True)
    t.start()
    return job_id, True


def get_by_run_id(run_id: str) -> Optional[FullTestJob]:
    """Return the most recent job for this run_id, or None."""
    matches = [j for j in _jobs.values() if j.run_id == run_id]
    return matches[-1] if matches else None


def clear() -> None:
    """Test isolation helper."""
    global _running_run_id
    _jobs.clear()
    _running_run_id = None
