"""
tests/web/test_routes_domain.py — Domain form route coverage for M1 S1.4.

All 10 required test cases + helpers. scaffold_runner.run() is always
monkeypatched so no subprocess is spawned.
"""
from __future__ import annotations

from typing import List

import pytest
from fastapi.testclient import TestClient

from web.adapters.scaffold_runner import ScaffoldRequest, ScaffoldResult


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------

def _make_result(req: ScaffoldRequest, *, success: bool = True) -> ScaffoldResult:
    return ScaffoldResult(
        success=success,
        slug=req.slug,
        out_dir="/tmp/x",
        stages=[],
        stdout="",
        stderr="",
        returncode=0,
    )


def _valid_form(**overrides) -> dict:
    base = {
        "domain": "고객관리",
        "slug": "customer",
        "dialect": "hsqldb",
        "lane": "jakarta",
        "default_pattern": "D2",
        "wiki_mode": "preset",
        "preset": "",
        "customer_profile": "",
    }
    base.update(overrides)
    return base


@pytest.fixture(autouse=True)
def _clear_registry():
    """Ensure run_registry is clean before and after each test."""
    import web.run_registry as rr
    rr.clear()
    yield
    rr.clear()


@pytest.fixture
def fake_run(monkeypatch):
    """Patch scaffold_runner.run with a fast in-process stub; returns captured list."""
    captured: List[ScaffoldRequest] = []

    def _fake(req: ScaffoldRequest, *, timeout_sec: int = 300) -> ScaffoldResult:
        captured.append(req)
        return _make_result(req)

    monkeypatch.setattr("web.routes.domain.scaffold_runner.run", _fake)
    return captured


@pytest.fixture
def fake_run_failure(monkeypatch):
    """Like fake_run but always returns success=False."""
    captured: List[ScaffoldRequest] = []

    def _fake(req: ScaffoldRequest, *, timeout_sec: int = 300) -> ScaffoldResult:
        captured.append(req)
        return _make_result(req, success=False)

    monkeypatch.setattr("web.routes.domain.scaffold_runner.run", _fake)
    return captured


# ---------------------------------------------------------------------------
# Test 1 — GET /domain/new → 200 with Korean label
# ---------------------------------------------------------------------------

def test_get_domain_new_returns_200(client: TestClient) -> None:
    response = client.get("/domain/new")
    assert response.status_code == 200


def test_get_domain_new_contains_domain_label(client: TestClient) -> None:
    response = client.get("/domain/new")
    assert "도메인" in response.text


# ---------------------------------------------------------------------------
# Test 2 — POST valid → 303 redirect to /domain/{id}/preview
# ---------------------------------------------------------------------------

def test_post_valid_redirects_303(client: TestClient, fake_run) -> None:
    response = client.post(
        "/domain/new",
        data=_valid_form(),
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert response.headers["location"].startswith("/domain/")
    assert response.headers["location"].endswith("/preview")


# ---------------------------------------------------------------------------
# Test 3 — POST valid → result stored in run_registry
# ---------------------------------------------------------------------------

def test_post_valid_registers_result(client: TestClient, fake_run) -> None:
    import web.run_registry as rr

    response = client.post(
        "/domain/new",
        data=_valid_form(),
        follow_redirects=False,
    )
    assert response.status_code == 303
    location = response.headers["location"]
    # location = /domain/<run_id>/preview
    run_id = location.split("/")[2]
    result = rr.get(run_id)
    assert result is not None
    assert result.slug == "customer"


# ---------------------------------------------------------------------------
# Test 4 — POST with empty domain → 422 + "도메인" in error text
# ---------------------------------------------------------------------------

def test_post_empty_domain_returns_422(client: TestClient, fake_run) -> None:
    response = client.post(
        "/domain/new",
        data=_valid_form(domain=""),
        follow_redirects=False,
    )
    assert response.status_code == 422
    assert "도메인" in response.text


# ---------------------------------------------------------------------------
# Test 5 — POST with empty slug → 422 + "슬러그" in error text
# ---------------------------------------------------------------------------

def test_post_empty_slug_returns_422(client: TestClient, fake_run) -> None:
    response = client.post(
        "/domain/new",
        data=_valid_form(slug=""),
        follow_redirects=False,
    )
    assert response.status_code == 422
    assert "슬러그" in response.text


# ---------------------------------------------------------------------------
# Test 6 — POST with slug containing uppercase → 422
# ---------------------------------------------------------------------------

def test_post_slug_with_uppercase_returns_422(client: TestClient, fake_run) -> None:
    response = client.post(
        "/domain/new",
        data=_valid_form(slug="Bad_Slug"),
        follow_redirects=False,
    )
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# Test 7 — POST with slug starting with digit → 422
# ---------------------------------------------------------------------------

def test_post_slug_starting_with_digit_returns_422(client: TestClient, fake_run) -> None:
    response = client.post(
        "/domain/new",
        data=_valid_form(slug="1abc"),
        follow_redirects=False,
    )
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# Test 8 — POST with empty preset → ScaffoldRequest.preset is None
# ---------------------------------------------------------------------------

def test_post_empty_preset_becomes_none(client: TestClient, fake_run) -> None:
    client.post(
        "/domain/new",
        data=_valid_form(preset=""),
        follow_redirects=False,
    )
    assert len(fake_run) == 1
    assert fake_run[0].preset is None


# ---------------------------------------------------------------------------
# Test 9 — POST validation failure → user input preserved in re-rendered form
# ---------------------------------------------------------------------------

def test_post_validation_preserves_user_input(client: TestClient, fake_run) -> None:
    response = client.post(
        "/domain/new",
        data=_valid_form(domain="고객관리", slug=""),  # slug missing → 422
        follow_redirects=False,
    )
    assert response.status_code == 422
    assert "고객관리" in response.text


# ---------------------------------------------------------------------------
# Test 10 — POST with scaffold_runner returning success=False → still redirects
# ---------------------------------------------------------------------------

def test_post_scaffold_failure_still_redirects(
    client: TestClient, fake_run_failure
) -> None:
    response = client.post(
        "/domain/new",
        data=_valid_form(),
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert response.headers["location"].startswith("/domain/")
    assert response.headers["location"].endswith("/preview")


# ---------------------------------------------------------------------------
# Preview tests (S1.5)
# ---------------------------------------------------------------------------

from web.adapters.scaffold_runner import StageResult  # noqa: E402


def _make_preview_result(
    success: bool = True,
    slug: str = "cust",
    stages: list | None = None,
    **kw,
) -> ScaffoldResult:
    return ScaffoldResult(
        success=success,
        slug=slug,
        out_dir=f"/tmp/out/{slug}",
        stages=stages if stages is not None else [
            StageResult(name="stage1", status="OK", duration_ms=120),
        ],
        stdout="hello stdout",
        stderr="",
        returncode=0 if success else 1,
        **kw,
    )


# Preview test 1 — success=True → 200, contains "성공" + slug
def test_preview_success_200(client: TestClient) -> None:
    import web.run_registry as rr

    result = _make_preview_result(success=True, slug="myslug")
    run_id = rr.register(result)

    response = client.get(f"/domain/{run_id}/preview")
    assert response.status_code == 200
    assert "성공" in response.text
    assert "myslug" in response.text


# Preview test 2 — success=False → 200, contains "실패" (not 422)
def test_preview_failure_200(client: TestClient) -> None:
    import web.run_registry as rr

    result = _make_preview_result(success=False, slug="failslug")
    run_id = rr.register(result)

    response = client.get(f"/domain/{run_id}/preview")
    assert response.status_code == 200
    assert "실패" in response.text


# Preview test 3 — unknown run_id → 404 + "찾을 수 없습니다" in detail
def test_preview_unknown_run_id_404(client: TestClient) -> None:
    response = client.get("/domain/doesnotexist/preview")
    assert response.status_code == 404
    data = response.json()
    assert "찾을 수 없습니다" in data["detail"]


# Preview test 4 — all stage rows from result.stages appear in the page
def test_preview_shows_all_stage_rows(client: TestClient) -> None:
    import web.run_registry as rr

    stages = [
        StageResult(name="stage1", status="OK", duration_ms=100),
        StageResult(name="stage2", status="SKIPPED", duration_ms=None),
        StageResult(name="stage3", status="FAIL", duration_ms=50, note="error!"),
    ]
    result = _make_preview_result(success=False, slug="multistage", stages=stages)
    run_id = rr.register(result)

    response = client.get(f"/domain/{run_id}/preview")
    assert response.status_code == 200
    assert "stage1" in response.text
    assert "stage2" in response.text
    assert "stage3" in response.text
    assert "SKIPPED" in response.text
    assert "FAIL" in response.text


# Preview test 5 — download CTA link is present
def test_preview_contains_download_link(client: TestClient) -> None:
    import web.run_registry as rr

    result = _make_preview_result(slug="dlslug")
    run_id = rr.register(result)

    response = client.get(f"/domain/{run_id}/preview")
    assert response.status_code == 200
    assert f"/domain/{run_id}/download" in response.text


# Preview test 6 — stdout content is shown on page
def test_preview_shows_stdout(client: TestClient) -> None:
    import web.run_registry as rr

    result = _make_preview_result(slug="stdoutslug")
    run_id = rr.register(result)

    response = client.get(f"/domain/{run_id}/preview")
    assert response.status_code == 200
    assert "hello stdout" in response.text


# Preview test 7 — raw_report=None → no raw_report <details> block
def test_preview_omits_raw_report_when_none(client: TestClient) -> None:
    import web.run_registry as rr

    result = _make_preview_result(slug="noreport", raw_report=None)
    run_id = rr.register(result)

    response = client.get(f"/domain/{run_id}/preview")
    assert response.status_code == 200
    assert "scaffold-report.md" not in response.text


# Preview test 8 — end-to-end: POST → follow redirect → preview rendered
def test_preview_end_to_end(client: TestClient, fake_run) -> None:
    response = client.post(
        "/domain/new",
        data=_valid_form(),
        follow_redirects=True,
    )
    assert response.status_code == 200
    # After following the redirect the preview page must render the slug
    assert "customer" in response.text


# ---------------------------------------------------------------------------
# Download tests (S1.6)
# ---------------------------------------------------------------------------

import io       # noqa: E402
import zipfile  # noqa: E402


def _make_download_result(out_dir: str, slug: str = "customer") -> ScaffoldResult:
    return ScaffoldResult(
        success=True,
        slug=slug,
        out_dir=out_dir,
        stages=[StageResult(name="stage1", status="OK")],
        stdout="",
        stderr="",
        returncode=0,
    )


def _make_out_dir(tmp_path):
    """Create a realistic scaffold output directory for zip tests."""
    out_dir = tmp_path / "myout"
    out_dir.mkdir()
    (out_dir / "README.md").write_text("hello")
    (out_dir / "sub").mkdir()
    (out_dir / "sub" / "file.txt").write_text("data")
    return out_dir


# Download test 1 — unknown run_id → 404 + "찾을 수 없습니다" in detail
def test_download_unknown_run_id_404(client: TestClient) -> None:
    response = client.get("/domain/doesnotexist/download")
    assert response.status_code == 404
    data = response.json()
    assert "찾을 수 없습니다" in data["detail"]


# Download test 2 — non-existent out_dir → 409 + "존재하지 않습니다" in detail
def test_download_missing_out_dir_409(client: TestClient, tmp_path) -> None:
    import web.run_registry as rr

    result = _make_download_result(str(tmp_path / "missing"), slug="gone")
    run_id = rr.register(result)

    response = client.get(f"/domain/{run_id}/download")
    assert response.status_code == 409
    data = response.json()
    assert "존재하지 않습니다" in data["detail"]


# Download test 3 — valid out_dir → 200 with application/zip content-type
def test_download_valid_returns_200_zip(client: TestClient, tmp_path) -> None:
    import web.run_registry as rr

    out_dir = _make_out_dir(tmp_path)
    result = _make_download_result(str(out_dir), slug="customer")
    run_id = rr.register(result)

    response = client.get(f"/domain/{run_id}/download")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/zip"


# Download test 4 — Content-Disposition uses slug as filename
def test_download_content_disposition_uses_slug(client: TestClient, tmp_path) -> None:
    import web.run_registry as rr

    out_dir = _make_out_dir(tmp_path)
    result = _make_download_result(str(out_dir), slug="myslug")
    run_id = rr.register(result)

    response = client.get(f"/domain/{run_id}/download")
    assert response.status_code == 200
    disposition = response.headers["content-disposition"]
    assert 'filename="myslug.zip"' in disposition


# Download test 5 — returned bytes are a valid zip containing the files
def test_download_bytes_are_valid_zip(client: TestClient, tmp_path) -> None:
    import web.run_registry as rr

    out_dir = _make_out_dir(tmp_path)
    result = _make_download_result(str(out_dir), slug="customer")
    run_id = rr.register(result)

    response = client.get(f"/domain/{run_id}/download")
    assert response.status_code == 200

    zf = zipfile.ZipFile(io.BytesIO(response.content))
    names = zf.namelist()
    assert any("README.md" in n for n in names)
    assert any("file.txt" in n for n in names)


# Download test 6 — top-level folder in zip matches basename of out_dir
def test_download_zip_top_level_folder_matches_out_dir_basename(
    client: TestClient, tmp_path
) -> None:
    import web.run_registry as rr

    out_dir = _make_out_dir(tmp_path)
    result = _make_download_result(str(out_dir), slug="customer")
    run_id = rr.register(result)

    response = client.get(f"/domain/{run_id}/download")
    assert response.status_code == 200

    zf = zipfile.ZipFile(io.BytesIO(response.content))
    names = sorted(zf.namelist())
    expected_prefix = out_dir.name + "/"
    assert all(n.startswith(expected_prefix) for n in names)
