"""
web/routes/fulltest.py — Growth-83 풀테스트 시작/폴링 라우트.

POST /domain/{run_id}/fulltest          → 백그라운드 잡 시작 (202/409)
GET  /domain/{run_id}/fulltest/status   → 잡 상태 폴링 (JSON)
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from web import run_registry, fulltest_registry

router = APIRouter(prefix="/domain")


@router.post("/{run_id}/fulltest", status_code=202)
async def fulltest_start(run_id: str) -> JSONResponse:
    """Start a background full-test for the given scaffold run."""
    result = run_registry.get(run_id)
    if result is None:
        raise HTTPException(status_code=404, detail="해당 실행 결과를 찾을 수 없습니다.")

    lane = getattr(result, "lane", "jakarta")
    scaffold_dir = result.out_dir

    job_id, started = fulltest_registry.start(run_id, lane, scaffold_dir)
    if not started:
        raise HTTPException(
            status_code=409,
            detail="풀테스트가 이미 실행 중입니다. 완료 후 다시 시도해 주세요.",
        )
    return JSONResponse(
        status_code=202,
        content={"job_id": job_id, "status": "running"},
    )


@router.get("/{run_id}/fulltest/status")
async def fulltest_status(run_id: str) -> JSONResponse:
    """Poll the current full-test job status for this run."""
    job = fulltest_registry.get_by_run_id(run_id)
    if job is None:
        raise HTTPException(status_code=404, detail="풀테스트 잡이 없습니다. 먼저 시작해 주세요.")

    payload: dict = {"status": job.status.value, "lane": job.lane}
    if job.result:
        payload.update(job.result.to_dict())
    return JSONResponse(content=payload)
