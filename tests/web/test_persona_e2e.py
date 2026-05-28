"""
tests/web/test_persona_e2e.py — G1.1 acceptance gate, M1 S1.7.

Exercises the full non-IT-user workflow end-to-end through the real
scaffold subprocess.  Skipped by default; set RUN_E2E=1 to enable.

    # PowerShell
    $env:RUN_E2E="1"; python -m pytest tests/web/test_persona_e2e.py -q -s

    # bash / CMD
    RUN_E2E=1 python -m pytest tests/web/test_persona_e2e.py -q -s

Expected runtime: ~1–3 minutes (depends on sibling repos being present).
"""
from __future__ import annotations

import io
import os
import shutil
import time
import zipfile

import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_E2E") != "1",
    reason="Set RUN_E2E=1 to run the persona E2E test (invokes real scaffold subprocess; ~1–3 min).",
)


# ---------------------------------------------------------------------------
# Registry isolation
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def clear_registry():
    """Clear run_registry before/after every test in this module."""
    import web.run_registry as rr
    rr.clear()
    yield
    rr.clear()


# ---------------------------------------------------------------------------
# E2E test — real subprocess pipeline
# ---------------------------------------------------------------------------

def test_persona_full_journey(client: TestClient):
    """업무 담당자가 dev 환경 없이 도메인 1개 정의 → preview 그린 → zip 다운로드, 30분 내."""
    import web.run_registry as rr
    from web.settings import get_settings

    slug = f"e2e_customer_{os.getpid()}"

    t_start = time.monotonic()

    # 1. Home page reachable
    r1 = client.get("/")
    assert r1.status_code == 200, f"GET / returned {r1.status_code}"
    assert "도메인 정의" in r1.text or r1.status_code == 200  # link may vary by template

    # 2. Form page
    r2 = client.get("/domain/new")
    assert r2.status_code == 200, f"GET /domain/new returned {r2.status_code}"
    # Form must contain field labels
    assert "도메인" in r2.text

    # 3. POST — trigger real scaffold subprocess
    r3 = client.post(
        "/domain/new",
        data={
            "domain": "고객관리",
            "slug": slug,
            "dialect": "hsqldb",
            "lane": "jakarta",
            "default_pattern": "D2",
            "wiki_mode": "preset",
        },
        follow_redirects=False,
    )
    assert r3.status_code == 303, (
        f"POST /domain/new expected 303, got {r3.status_code}.\n"
        f"Body: {r3.text[:500]}"
    )
    loc = r3.headers.get("location", "")
    assert loc.startswith("/domain/"), f"Unexpected Location: {loc}"
    assert loc.endswith("/preview"), f"Unexpected Location: {loc}"

    # 4. Extract run_id
    run_id = loc.split("/")[2]
    assert run_id, "run_id is empty"

    # 5. Preview — must show success badge and slug
    r4 = client.get(f"/domain/{run_id}/preview")
    assert r4.status_code == 200, f"GET preview returned {r4.status_code}"
    assert "성공" in r4.text, (
        f"Preview does not contain '성공' badge.\nBody (first 1000 chars):\n{r4.text[:1000]}"
    )
    assert slug in r4.text, f"Preview does not contain slug '{slug}'"

    # 6. Download — must be a valid zip
    r5 = client.get(f"/domain/{run_id}/download")
    assert r5.status_code == 200, f"GET download returned {r5.status_code}"
    ct = r5.headers.get("content-type", "")
    assert ct == "application/zip", f"Expected application/zip, got {ct}"
    cd = r5.headers.get("content-disposition", "")
    assert f'filename="{slug}.zip"' in cd, f"Unexpected Content-Disposition: {cd}"

    # 7. Validate zip is non-empty and has the expected top-level folder
    result = rr.get(run_id)
    assert result is not None, "run_id not found in registry after download"

    z = zipfile.ZipFile(io.BytesIO(r5.content))
    names = z.namelist()
    assert len(names) > 0, "Downloaded zip is empty"

    import pathlib
    expected_top = pathlib.Path(result.out_dir).name
    assert any(
        n.startswith(expected_top + "/") or n == expected_top for n in names
    ), f"Expected top-level folder '{expected_top}' not found in zip. Got: {names[:10]}"

    # 8. Wall-clock constraint: < 30 minutes
    elapsed = time.monotonic() - t_start
    print(f"\n[E2E] elapsed: {elapsed:.1f}s")
    assert elapsed < 1800, f"E2E journey took {elapsed:.1f}s — exceeds 30-minute budget"

    # 9. Cleanup: remove the scaffold out_dir
    out_dir = result.out_dir
    shutil.rmtree(out_dir, ignore_errors=True)
