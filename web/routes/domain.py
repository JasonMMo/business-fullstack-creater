"""
web/routes/domain.py — /domain routes for M1 S1.4.

GET  /domain/new  — Render empty scaffold form.
POST /domain/new  — Validate, run scaffold, register result, redirect to preview.
"""
from __future__ import annotations

import re
from typing import List, Optional

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response

from web.adapters import scaffold_runner
from web.adapters.scaffold_runner import ScaffoldRequest
from web import run_registry

router = APIRouter(prefix="/domain")

_SLUG_RE = re.compile(r"^[a-z][a-z0-9_-]*$")

_DIALECT_CHOICES = ["hsqldb", "postgres", "mysql"]
_LANE_CHOICES = ["jakarta", "javax", "nexacro", "vanilla"]
_PATTERN_CHOICES = ["D2", "D3"]
_WIKI_MODE_CHOICES = ["preset", "wiki"]


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
) -> Response:
    """Validate form, run scaffold, register result, redirect to preview."""
    templates = request.app.state.templates

    # Normalise
    domain = domain.strip()
    slug = slug.strip()
    preset_val: Optional[str] = preset.strip() or None
    customer_profile_val: Optional[str] = customer_profile.strip() or None

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

    if errors:
        return templates.TemplateResponse(
            request,
            "domain_form.html",
            {"errors": errors, "form": form_data},
            status_code=422,
        )

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
    )

    result = scaffold_runner.run(scaffold_req)

    # Register result regardless of success/failure — preview shows both
    run_id = run_registry.register(result)

    return RedirectResponse(
        url=f"/domain/{run_id}/preview",
        status_code=303,
    )
