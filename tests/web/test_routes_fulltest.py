"""
tests/web/test_routes_fulltest.py — Growth-83 풀테스트 라우트 커버리지.

POST /domain/{run_id}/fulltest          → 202 / 404 / 409
GET  /domain/{run_id}/fulltest/status   → running / done-green / 404
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from web.adapters.scaffold_runner import ScaffoldResult, StageResult
from web.adapters.fulltest_runner import FullTestJobResult
import web.run_registry as run_registry
import web.fulltest_registry as fulltest_registry
from web.fulltest_registry import FullTestJob, JobStatus


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_scaffold_result(
    slug: str = "customer",
    lane: str = "jakarta",
    out_dir: str | None = None,
) -> ScaffoldResult:
    return ScaffoldResult(
        success=True,
        slug=slug,
        out_dir=out_dir or f"/tmp/out/{slug}",
        stages=[StageResult(name="stage1", status="OK")],
        stdout="",
        stderr="",
        returncode=0,
        lane=lane,
    )


def _make_fulltest_result(green: bool = True) -> FullTestJobResult:
    return FullTestJobResult(
        label="풀테스트 그린" if green else "단위 테스트 실패 — 검증 중단",
        lane="jakarta",
        layers={"L1": True, "L2": True, "L3": True, "L4_full": green, "L4_partial": False},
        next_hint=None if green else "Next: pytest -q",
        returncode=0 if green else 1,
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _clear_registries():
    """Isolate each test: clear both registries before and after."""
    run_registry.clear()
    fulltest_registry.clear()
    yield
    run_registry.clear()
    fulltest_registry.clear()


@pytest.fixture
def registered_run_id(tmp_path) -> str:
    """Register a scaffold result and return its run_id.

    Growth-85 B3: out_dir 은 실제로 존재해야 fulltest 가드를 통과한다.
    """
    out = tmp_path / "customer"
    out.mkdir()
    result = _make_scaffold_result(out_dir=str(out))
    return run_registry.register(result)


# ---------------------------------------------------------------------------
# POST /domain/{run_id}/fulltest
# ---------------------------------------------------------------------------

def test_fulltest_start_202(client: TestClient, registered_run_id: str, monkeypatch) -> None:
    """Valid run_id with monkeypatched runner → 202 Accepted."""
    def _fake_run(lane, scaffold_dir, *, timeout_sec=600):
        return _make_fulltest_result(green=True)

    monkeypatch.setattr("web.adapters.fulltest_runner.run", _fake_run)

    response = client.post(f"/domain/{registered_run_id}/fulltest")
    assert response.status_code == 202
    data = response.json()
    assert data["status"] == "running"
    assert "job_id" in data


def test_fulltest_start_404(client: TestClient) -> None:
    """Unknown run_id → 404."""
    response = client.post("/domain/nonexistent_run_id/fulltest")
    assert response.status_code == 404
    assert "찾을 수 없습니다" in response.json()["detail"]


def test_fulltest_start_409(client: TestClient, registered_run_id: str, monkeypatch) -> None:
    """Second POST while a job is running → 409."""
    import threading

    barrier = threading.Event()

    def _slow_run(lane, scaffold_dir, *, timeout_sec=600):
        barrier.wait(timeout=5)
        return _make_fulltest_result(green=True)

    monkeypatch.setattr("web.adapters.fulltest_runner.run", _slow_run)

    # Start first job
    r1 = client.post(f"/domain/{registered_run_id}/fulltest")
    assert r1.status_code == 202

    # Attempt second job while first is still running
    r2 = client.post(f"/domain/{registered_run_id}/fulltest")
    assert r2.status_code == 409
    assert "이미 실행 중" in r2.json()["detail"]

    # Unblock the background worker
    barrier.set()


# ---------------------------------------------------------------------------
# GET /domain/{run_id}/fulltest/status
# ---------------------------------------------------------------------------

def test_fulltest_status_running(client: TestClient, registered_run_id: str) -> None:
    """RUNNING job returns status=running."""
    job = FullTestJob(job_id="abc123", run_id=registered_run_id, lane="jakarta")
    # inject directly into registry
    fulltest_registry._jobs["abc123"] = job

    response = client.get(f"/domain/{registered_run_id}/fulltest/status")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "running"
    assert data["lane"] == "jakarta"


def test_fulltest_status_done_green(client: TestClient, registered_run_id: str) -> None:
    """DONE job with L4_full=True returns green=true."""
    result = _make_fulltest_result(green=True)
    job = FullTestJob(
        job_id="done123",
        run_id=registered_run_id,
        lane="jakarta",
        status=JobStatus.DONE,
        result=result,
    )
    fulltest_registry._jobs["done123"] = job

    response = client.get(f"/domain/{registered_run_id}/fulltest/status")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "done"
    assert data["green"] is True
    assert data["label"] == "풀테스트 그린"


def test_fulltest_status_404(client: TestClient) -> None:
    """No job registered for run_id → 404."""
    response = client.get("/domain/no_such_run/fulltest/status")
    assert response.status_code == 404
    assert "풀테스트 잡이 없습니다" in response.json()["detail"]


# ---------------------------------------------------------------------------
# Growth-85 B3: scaffold 실패/산출물 없음 → fulltest 409 가드
# ---------------------------------------------------------------------------

def test_fulltest_409_when_scaffold_failed(client: TestClient) -> None:
    """scaffold success=False 이면 풀테스트 시작 시 409 (B3 Growth-85)."""
    failed_result = ScaffoldResult(
        success=False,
        slug="failslug",
        out_dir="/tmp/out/failslug",   # 존재하지 않는 경로
        stages=[],
        stdout="",
        stderr="scaffold failed",
        returncode=1,
        lane="jakarta",
    )
    run_id = run_registry.register(failed_result)
    response = client.post(f"/domain/{run_id}/fulltest")
    assert response.status_code == 409
    assert "scaffold" in response.json()["detail"]


def test_fulltest_409_when_out_dir_missing(client: TestClient, tmp_path) -> None:
    """scaffold success=True 이지만 out_dir 이 디스크에 없으면 409 (B3 Growth-85)."""
    missing_dir = str(tmp_path / "nonexistent")
    ok_result = ScaffoldResult(
        success=True,
        slug="missingdir",
        out_dir=missing_dir,
        stages=[StageResult(name="stage1", status="OK")],
        stdout="",
        stderr="",
        returncode=0,
        lane="jakarta",
    )
    run_id = run_registry.register(ok_result)
    response = client.post(f"/domain/{run_id}/fulltest")
    assert response.status_code == 409
    assert "scaffold" in response.json()["detail"]
