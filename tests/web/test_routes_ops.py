"""
tests/web/test_routes_ops.py — Growth-75 (M3 Slice c) /domain/{run_id}/ops.zip 라우트.

검증 항목:
  1. 404 — run_id 미등록
  2. 409 — out_dir/shell/ops/ 부재 (Stage 5 skipped / emit_ops_pack 미실행)
  3. 200 — ops/ 존재 시 zip 응답, Content-Type 및 Content-Disposition 정상
  4. zip 내용 — 4 산출물 (Dockerfile/docker-compose.yml/.env.example/DEPLOY-SOP.md) 포함
  5. preview — ops_pack_available=true 시 Ops Pack 버튼 표시
  6. preview — ops_pack_available=false 시 Ops Pack 버튼 미표시
"""
from __future__ import annotations

import io
import zipfile

import pytest

from web.adapters.scaffold_runner import ScaffoldResult
from web import run_registry


_OPS_FILES = ("Dockerfile", "docker-compose.yml", ".env.example", "DEPLOY-SOP.md")


def _seed_run(tmp_path, *, slug: str = "acme-customer", with_ops: bool = True) -> str:
    """Register a ScaffoldResult and optionally seed ops/ artifacts."""
    out_dir = tmp_path / slug
    (out_dir / "shell").mkdir(parents=True)
    if with_ops:
        ops = out_dir / "shell" / "ops"
        ops.mkdir()
        for name in _OPS_FILES:
            (ops / name).write_text(f"# {name}\n", encoding="utf-8")

    result = ScaffoldResult(
        success=True,
        slug=slug,
        out_dir=str(out_dir),
        stages=[],
        stdout="",
        stderr="",
        returncode=0,
    )
    return run_registry.register(result)


@pytest.fixture(autouse=True)
def _clear_registry():
    run_registry.clear()
    yield
    run_registry.clear()


# ---------------------------------------------------------------------------
# 1. 404 — unknown run_id
# ---------------------------------------------------------------------------

def test_ops_download_returns_404_for_unknown_run(client):
    resp = client.get("/domain/deadbeef/ops.zip")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# 2. 409 — ops/ absent
# ---------------------------------------------------------------------------

def test_ops_download_returns_409_when_ops_dir_missing(client, tmp_path):
    run_id = _seed_run(tmp_path, with_ops=False)
    resp = client.get(f"/domain/{run_id}/ops.zip")
    assert resp.status_code == 409
    assert "ops pack" in resp.json()["detail"]


# ---------------------------------------------------------------------------
# 3. 200 — zip response headers
# ---------------------------------------------------------------------------

def test_ops_download_returns_zip_with_correct_headers(client, tmp_path):
    run_id = _seed_run(tmp_path, slug="acme-customer", with_ops=True)
    resp = client.get(f"/domain/{run_id}/ops.zip")

    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/zip"
    assert 'filename="acme-customer-ops.zip"' in resp.headers["content-disposition"]


# ---------------------------------------------------------------------------
# 4. zip 내용 — 4 산출물 포함
# ---------------------------------------------------------------------------

def test_ops_download_zip_contains_four_artifacts(client, tmp_path):
    run_id = _seed_run(tmp_path, with_ops=True)
    resp = client.get(f"/domain/{run_id}/ops.zip")
    assert resp.status_code == 200

    with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
        names = zf.namelist()

    # zip_emitter 가 archive root 로 ops/ 디렉터리 basename(=ops) 을 prefix 함
    basenames = {n.split("/", 1)[-1] for n in names}
    for fname in _OPS_FILES:
        assert fname in basenames, f"missing in zip: {fname}"


# ---------------------------------------------------------------------------
# 5. preview UI — ops_pack_available=true → 버튼 표시
# ---------------------------------------------------------------------------

def test_preview_shows_ops_pack_button_when_available(client, tmp_path):
    run_id = _seed_run(tmp_path, with_ops=True)
    resp = client.get(f"/domain/{run_id}/preview")
    assert resp.status_code == 200
    assert "Ops Pack 다운로드" in resp.text
    assert f'/domain/{run_id}/ops.zip' in resp.text


# ---------------------------------------------------------------------------
# 6. preview UI — ops_pack_available=false → 버튼 미표시
# ---------------------------------------------------------------------------

def test_preview_hides_ops_pack_button_when_absent(client, tmp_path):
    run_id = _seed_run(tmp_path, with_ops=False)
    resp = client.get(f"/domain/{run_id}/preview")
    assert resp.status_code == 200
    assert "Ops Pack 다운로드" not in resp.text
