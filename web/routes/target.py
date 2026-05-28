"""
web/routes/target.py — Growth-79 (M5 Slice C-c) /target/upload routes.

Exposes `extract_target_profile.py` (Growth-70 + Growth-78) via the web UI so
the IT-담당자 페르소나 can hand in an existing SpringBoot project (Maven or
Gradle) as a zip and receive a `profiles/<slug>.yaml` v1 customer profile —
without a CLI environment.

Routes
------
GET  /target/upload                  — Render the upload form.
POST /target/upload                  — Validate zip, run extractor, render preview.
POST /target/upload?download=1       — Same, but stream YAML as attachment.

Single-source rule (G-79): this module imports
`web.adapters.target_extractor` which in turn imports
`scripts/extract_target_profile.py`. The route MUST NOT re-implement
pom.xml / build.gradle parsing.
"""
from __future__ import annotations

import re
from typing import Optional

from fastapi import APIRouter, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, PlainTextResponse, Response

from web.adapters import target_extractor

router = APIRouter(prefix="/target")

_SLUG_RE = re.compile(r"^[a-z][a-z0-9_-]*$")

# 16 MiB hard cap — SpringBoot source trees with vendored builds can exceed
# this, but for a profile-extraction front-end it's a safe upper bound.
_MAX_UPLOAD_BYTES = 16 * 1024 * 1024


@router.get("/upload", response_class=HTMLResponse)
async def target_upload_get(request: Request) -> HTMLResponse:
    templates = request.app.state.templates
    return templates.TemplateResponse(
        request,
        "target_upload.html",
        {"errors": [], "form": {}, "result": None},
    )


@router.post("/upload", response_model=None)
async def target_upload_post(
    request: Request,
    project_zip: UploadFile = File(...),
    slug: str = Form(default=""),
    download: str = Form(default=""),
) -> Response:
    templates = request.app.state.templates
    slug = slug.strip()
    form_data = {"slug": slug}

    errors = []
    if slug and not _SLUG_RE.match(slug):
        errors.append(
            "슬러그는 소문자 알파벳으로 시작하고 소문자·숫자·하이픈·언더스코어만 허용됩니다."
        )

    payload = await project_zip.read()
    if not payload:
        errors.append("업로드한 zip 파일이 비어있습니다.")
    elif len(payload) > _MAX_UPLOAD_BYTES:
        errors.append(
            f"업로드 크기가 한도({_MAX_UPLOAD_BYTES // (1024 * 1024)} MiB)를 초과합니다."
        )

    if errors:
        return templates.TemplateResponse(
            request,
            "target_upload.html",
            {"errors": errors, "form": form_data, "result": None},
            status_code=422,
        )

    try:
        result = target_extractor.extract_from_zip(
            payload,
            slug_override=slug or None,
        )
    except target_extractor.TargetExtractionError as exc:
        return templates.TemplateResponse(
            request,
            "target_upload.html",
            {"errors": [str(exc)], "form": form_data, "result": None},
            status_code=422,
        )

    if download:
        filename = f"{result.slug}.yaml"
        return PlainTextResponse(
            content=result.yaml_text,
            media_type="application/x-yaml",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    return templates.TemplateResponse(
        request,
        "target_upload.html",
        {
            "errors": [],
            "form": form_data,
            "result": {
                "slug": result.slug,
                "yaml_text": result.yaml_text,
                "source": result.source,
            },
        },
    )
