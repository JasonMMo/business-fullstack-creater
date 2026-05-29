"""
web/routes/status.py — Growth-84 (M2) Exec 라이브 대시보드.

GET /status        → 누적 자산 대시보드 HTML (CEO 30초 회독)
GET /status.json   → 동일 데이터 JSON (auto-refresh / 프로그래매틱 소비)

데이터 단일소스: scripts/workflow/status_board.compute() 재사용.
메트릭 계산을 재구현하지 않는다 (복리 누적 원칙).
"""
from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse

router = APIRouter()


def _compute_green_rate(verification) -> dict:
    """검증 매트릭스에서 풀테스트 그린율 파생.

    verified lane / total lane. partial/pending 은 미그린 취급.
    Returns {"verified": int, "total": int, "percent": int}.
    """
    total = len(verification)
    verified = sum(1 for v in verification if v.status == "verified")
    percent = round(verified / total * 100) if total else 0
    return {"verified": verified, "total": total, "percent": percent}


@router.get("/status", response_class=HTMLResponse)
async def status_dashboard(request: Request) -> HTMLResponse:
    """누적 자산 대시보드를 렌더한다."""
    from scripts.workflow import status_board  # noqa: PLC0415

    templates = request.app.state.templates
    try:
        board = status_board.compute()
        green_rate = _compute_green_rate(board.verification)
        error = None
    except Exception as exc:  # 데이터 집계 실패 시 친절 폴백 (500 회피)
        board = None
        green_rate = {"verified": 0, "total": 0, "percent": 0}
        error = f"자산 데이터를 집계하지 못했습니다: {exc}"

    return templates.TemplateResponse(
        request,
        "status.html",
        {
            "board": board,
            "green_rate": green_rate,
            "error": error,
        },
    )


@router.get("/status.json")
async def status_json(request: Request) -> JSONResponse:
    """대시보드 데이터를 JSON 으로 반환한다."""
    from scripts.workflow import status_board  # noqa: PLC0415

    try:
        board = status_board.compute()
        payload = status_board.to_dict(board)
        payload["green_rate"] = _compute_green_rate(board.verification)
    except Exception as exc:
        return JSONResponse(
            status_code=500,
            content={"error": f"자산 데이터를 집계하지 못했습니다: {exc}"},
        )
    return JSONResponse(content=payload)
