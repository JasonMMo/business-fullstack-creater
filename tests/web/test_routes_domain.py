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
