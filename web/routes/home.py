"""
web/routes/home.py — Landing page route.
"""
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def home(request: Request) -> HTMLResponse:
    """Render the landing page."""
    templates = request.app.state.templates
    return templates.TemplateResponse(
        request,
        "home.html",
        {
            "project_name": "고객사 풀스택 생성기",
        },
    )
