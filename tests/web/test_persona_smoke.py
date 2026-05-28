"""
tests/web/test_persona_smoke.py — Fast persona journey smoke test (M1 S1.7).

scaffold_runner.run is monkeypatched so no subprocess is spawned.
Runs unconditionally in CI to catch wiring regressions quickly.
"""
from __future__ import annotations

import io
import zipfile

import pytest
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Registry isolation fixture
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def clear_registry():
    """Clear run_registry before/after every test in this module."""
    import web.run_registry as rr
    rr.clear()
    yield
    rr.clear()


# ---------------------------------------------------------------------------
# Smoke test — full persona journey with monkeypatched scaffold runner
# ---------------------------------------------------------------------------

def test_persona_journey_smoke(client: TestClient, monkeypatch, tmp_path):
    # Fake scaffold_runner.run that creates a real tiny out_dir
    fake_out = tmp_path / "smoke-customer"
    fake_out.mkdir()
    (fake_out / "README.md").write_text("scaffold smoke output")
    (fake_out / "src" / "main").mkdir(parents=True)
    (fake_out / "src" / "main" / "App.java").write_text("class App {}")

    def fake_run(req, *, timeout_sec=300):
        from web.adapters.scaffold_runner import ScaffoldResult, StageResult
        return ScaffoldResult(
            success=True, slug=req.slug,
            out_dir=str(fake_out),
            stages=[
                StageResult(name="stage1", status="OK", duration_ms=100),
                StageResult(name="stage2", status="OK", duration_ms=200),
                StageResult(name="stage3", status="OK", duration_ms=300),
                StageResult(name="stage4", status="OK", duration_ms=400),
                StageResult(name="stage5", status="SKIPPED", note="(no --target-project)"),
            ],
            stdout="ok", stderr="", returncode=0,
        )

    monkeypatch.setattr("web.routes.domain.scaffold_runner.run", fake_run)

    # 1. Home page is reachable
    r1 = client.get("/")
    assert r1.status_code == 200

    # 2. Form renders
    r2 = client.get("/domain/new")
    assert r2.status_code == 200

    # 3. POST valid form → 303 redirect to preview
    r3 = client.post(
        "/domain/new",
        data={
            "domain": "고객관리",
            "slug": "smoke_customer",
            "dialect": "hsqldb",
            "lane": "jakarta",
            "default_pattern": "D2",
            "wiki_mode": "preset",
        },
        follow_redirects=False,
    )
    assert r3.status_code == 303
    loc = r3.headers["location"]
    assert loc.startswith("/domain/") and loc.endswith("/preview")
    run_id = loc.split("/")[2]

    # 4. Preview shows success badge and slug
    r4 = client.get(f"/domain/{run_id}/preview")
    assert r4.status_code == 200
    assert "성공" in r4.text
    assert "smoke_customer" in r4.text

    # 5. Download returns a valid zip
    r5 = client.get(f"/domain/{run_id}/download")
    assert r5.status_code == 200
    assert r5.headers["content-type"] == "application/zip"
    assert 'filename="smoke_customer.zip"' in r5.headers["content-disposition"]

    # Validate zip contents
    z = zipfile.ZipFile(io.BytesIO(r5.content))
    names = z.namelist()
    assert any("README.md" in n for n in names)
    assert any("App.java" in n for n in names)
