"""
web/routes/ops.py — Growth-75 (M3 Slice c) ops-pack-only download route.

`GET /domain/{run_id}/ops.zip` streams only the four artifacts emitted by
`scripts/emit_ops_pack.py` (Growth-71) — Dockerfile, docker-compose.yml,
.env.example, DEPLOY-SOP.md — so the IT-담당자 페르소나 can grab the deploy
bundle without pulling the entire scaffold tree.

Pipeline assumption: Growth-74 auto-call writes `<out_dir>/shell/ops/` during
Stage 5 PASS. This route does NOT re-emit; if the directory is absent (Stage 5
skipped, shell/pom.xml missing, emit failed) the response is 409 with a hint.
"""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from web import run_registry
from web.adapters import zip_emitter

router = APIRouter(prefix="/domain")


@router.get("/{run_id}/ops.zip")
async def domain_ops_download(run_id: str) -> Response:
    """Stream only the ops pack (4 artifacts) for *run_id* as a zip."""
    result = run_registry.get(run_id)
    if result is None:
        raise HTTPException(status_code=404, detail="해당 실행 결과를 찾을 수 없습니다.")

    ops_dir = Path(result.out_dir) / "shell" / "ops"
    if not ops_dir.is_dir():
        raise HTTPException(
            status_code=409,
            detail=(
                "ops pack 산출물이 없습니다. Stage 5 가 건너뛰어졌거나 "
                "shell/pom.xml 부재로 emit_ops_pack 가 실행되지 않았습니다."
            ),
        )

    zip_bytes = zip_emitter.emit(ops_dir)

    return Response(
        content=zip_bytes,
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="{result.slug}-ops.zip"'
        },
    )
