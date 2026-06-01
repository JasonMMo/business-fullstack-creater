"""
web/routes/domain.py — /domain routes for M1 S1.4 + S1.5.

GET  /domain/new                — Render empty scaffold form.
POST /domain/new                — Validate, run scaffold, register result, redirect to preview.
GET  /domain/{run_id}/preview   — Display scaffold results for a completed run.
"""
from __future__ import annotations

import re
from typing import List, Optional

from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response

from web.adapters import scaffold_runner, zip_emitter
from web.adapters.scaffold_runner import ScaffoldRequest
from web import run_registry

router = APIRouter(prefix="/domain")

_SLUG_RE = re.compile(r"^[a-z][a-z0-9_-]*$")

_DIALECT_CHOICES = ["hsqldb", "postgres", "mysql"]
_LANE_CHOICES = ["jakarta", "javax", "nexacro", "vanilla"]
_PATTERN_CHOICES = ["D2", "D3"]
_WIKI_MODE_CHOICES = ["preset", "wiki"]
_SHELL_MODE_CHOICES = ["none", "MDI", "SDI"]  # Growth-86


# ---------------------------------------------------------------------------
# GET /domain/new
# ---------------------------------------------------------------------------

@router.get("/new", response_class=HTMLResponse)
async def domain_form_get(request: Request) -> HTMLResponse:
    """Render the blank domain-definition form."""
    templates = request.app.state.templates
    return templates.TemplateResponse(
        request,
        "domain_form.html",
        {
            "errors": [],
            "form": {},
        },
    )


# ---------------------------------------------------------------------------
# POST /domain/new
# ---------------------------------------------------------------------------

@router.post("/new", response_model=None)
async def domain_form_post(
    request: Request,
    domain: str = Form(default=""),
    slug: str = Form(default=""),
    dialect: str = Form(default="hsqldb"),
    lane: str = Form(default="jakarta"),
    default_pattern: str = Form(default="D2"),
    wiki_mode: str = Form(default="preset"),
    preset: str = Form(default=""),
    customer_profile: str = Form(default=""),
    package: str = Form(default=""),  # Growth-85: Java 패키지명
    shell_mode: str = Form(default="none"),  # Growth-86: none|MDI|SDI — !=none 이면 ops pack 생성
) -> Response:
    """Validate form, run scaffold, register result, redirect to preview."""
    # Growth-85
    templates = request.app.state.templates

    # Normalise
    domain = domain.strip()
    slug = slug.strip()
    preset_val: Optional[str] = preset.strip() or None
    customer_profile_val: Optional[str] = customer_profile.strip() or None
    package = package.strip()
    shell_mode = shell_mode.strip() or "none"  # Growth-86

    # Preserve raw form input for re-render on error
    form_data = {
        "domain": domain,
        "slug": slug,
        "dialect": dialect,
        "lane": lane,
        "default_pattern": default_pattern,
        "wiki_mode": wiki_mode,
        "preset": preset,
        "customer_profile": customer_profile,
        "package": package,  # Growth-85
        "shell_mode": shell_mode,  # Growth-86
    }

    errors: List[str] = []

    if not domain:
        errors.append("도메인명을 입력해 주세요.")
    if not slug:
        errors.append("슬러그를 입력해 주세요.")
    elif not _SLUG_RE.match(slug):
        errors.append(
            "슬러그는 소문자 알파벳으로 시작하고 소문자·숫자·하이픈·언더스코어만 허용됩니다."
        )

    # B2 Growth-85: wiki_mode=preset 인데 preset 이 비어있으면 명확한 에러
    if wiki_mode == "preset" and not preset_val:
        errors.append(
            "프리셋 모드에서는 프리셋 이름이 필요합니다. 예: 고객관리 (또는 '직접 정의' 모드를 선택하세요)."
        )

    # Growth-86: shell-mode 화이트리스트 검증 (none/MDI/SDI 외 거부)
    if shell_mode not in _SHELL_MODE_CHOICES:
        errors.append(
            "shell-mode 는 none / MDI / SDI 중 하나여야 합니다."
        )

    if errors:
        return templates.TemplateResponse(
            request,
            "domain_form.html",
            {"errors": errors, "form": form_data},
            status_code=422,
        )

    # B1 Growth-85: customer_profile 도 없고 package 도 비면 자동 기본값 설정
    # (비전문 사용자가 Java 패키지명을 몰라도 scaffold 가 동작하도록)
    if not package and not customer_profile_val:
        package = f"com.example.{slug}"

    # Build ScaffoldRequest and call runner
    scaffold_req = ScaffoldRequest(
        domain=domain,
        slug=slug,
        dialect=dialect,
        lane=lane,
        default_pattern=default_pattern,
        wiki_mode=wiki_mode,
        preset=preset_val,
        customer_profile=customer_profile_val,
        package=package,  # Growth-85
        shell_mode=shell_mode,  # Growth-86
    )

    result = scaffold_runner.run(scaffold_req)

    # Register result regardless of success/failure — preview shows both
    run_id = run_registry.register(result)

    return RedirectResponse(
        url=f"/domain/{run_id}/preview",
        status_code=303,
    )


# ---------------------------------------------------------------------------
# GET /domain/{run_id}/preview
# ---------------------------------------------------------------------------

@router.get("/{run_id}/preview", response_class=HTMLResponse)
async def domain_preview(request: Request, run_id: str) -> HTMLResponse:
    """Display the scaffold results for *run_id*."""
    from pathlib import Path  # local import — preview-only filesystem probe

    templates = request.app.state.templates

    result = run_registry.get(run_id)
    if result is None:
        raise HTTPException(status_code=404, detail="해당 실행 결과를 찾을 수 없습니다.")

    stage_count = len(result.stages)
    ok_count = sum(1 for s in result.stages if s.status == "OK")
    fail_count = sum(1 for s in result.stages if s.status == "FAIL")

    # Growth-75 (M3 Slice c): ops pack 가용 여부 — emit_ops_pack 가 Growth-74
    # auto-call 로 out_dir/shell/ops/ 에 emit 했는지 확인.
    ops_pack_available = (Path(result.out_dir) / "shell" / "ops").is_dir()

    return templates.TemplateResponse(
        request,
        "domain_preview.html",
        {
            "run_id": run_id,
            "result": result,
            "ok_count": ok_count,
            "fail_count": fail_count,
            "stage_count": stage_count,
            "ops_pack_available": ops_pack_available,
        },
    )


# ---------------------------------------------------------------------------
# GET /domain/{run_id}/download
# ---------------------------------------------------------------------------

@router.get("/{run_id}/download")
async def domain_download(run_id: str) -> Response:
    """Stream the scaffold artifacts for *run_id* as a ZIP file."""
    result = run_registry.get(run_id)
    if result is None:
        raise HTTPException(status_code=404, detail="해당 실행 결과를 찾을 수 없습니다.")

    try:
        zip_bytes = zip_emitter.emit(result.out_dir)
    except (FileNotFoundError, NotADirectoryError):
        raise HTTPException(status_code=409, detail="산출물이 존재하지 않습니다.")

    return Response(
        content=zip_bytes,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{result.slug}.zip"'},
    )
