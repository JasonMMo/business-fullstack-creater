"""
web/app.py — FastAPI application factory for the business-fullstack-creater web layer.

This module exposes:
  - create_app() → FastAPI   (for testing and programmatic use)
  - app                      (module-level instance so `uvicorn web.app:app` works)

Scaffold logic lives entirely in scripts/scaffold_cli.py — this layer only
calls that CLI; it does NOT re-implement scaffold logic (compounding-growth guard).
"""
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

_WEB_DIR = Path(__file__).resolve().parent


def create_app() -> FastAPI:
    """Create and configure the FastAPI application instance."""
    application = FastAPI(
        title="고객사 풀스택 생성기",
        description="도메인을 한 줄로 입력하면 SpringBoot + Nexacro + DDL 산출물을 자동 생성합니다.",
        version="0.1.0",
    )

    # Static files
    application.mount(
        "/static",
        StaticFiles(directory=str(_WEB_DIR / "static")),
        name="static",
    )

    # Templates (shared via app state so routes can access)
    application.state.templates = Jinja2Templates(
        directory=str(_WEB_DIR / "templates")
    )

    # Routers
    from web.routes.home import router as home_router  # noqa: PLC0415
    from web.routes.domain import router as domain_router  # noqa: PLC0415
    from web.routes.ops import router as ops_router  # noqa: PLC0415
    from web.routes.target import router as target_router  # noqa: PLC0415

    application.include_router(home_router)
    application.include_router(domain_router)
    application.include_router(ops_router)
    application.include_router(target_router)

    return application


# Module-level instance — `uvicorn web.app:app`
app = create_app()
