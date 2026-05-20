# tests/golden/test_growth16_shell_sdi_e2e.py
"""Growth-16 P5 — SDI variant standalone E2E.

Mirrors the MDI E2E but exercises the SHELL pattern's three-tier frame
fallback: only ``frame_sdi.xfdl.j2`` ships under ``variants/SDI/``, and
the other four frames + ``typedefinition.xml`` + ``packageN.xadl`` are
resolved from the shared MDI variant directory.
"""
import pathlib
import sys

import pytest

CREATOR = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(CREATOR / "scripts"))

SIBLINGS = {
    "stage1": CREATOR.parent / "andrej-karpathy-rdb-skill",
    "stage2": CREATOR.parent / "andrej-karpathy-rdb-ddl",
    "stage3": CREATOR.parent / "andrej-karpathy-rdb-mybatis",
    "stage4": CREATOR.parent / "andrej-karpathy-rdb-nexacro",
}

_MISSING = [k for k, p in SIBLINGS.items() if not p.exists()]
pytestmark = pytest.mark.skipif(
    bool(_MISSING),
    reason=f"sibling stage repo(s) not found: {', '.join(_MISSING)}",
)


def test_standalone_shell_sdi_uses_fallback_frames(tmp_path):
    """--shell-mode=SDI must produce frameSDI.xfdl AND the shared MDI frames
    (Main/Left/Top/Login) via 3-tier resolver fallback.
    """
    from scaffold_orchestrator import (  # noqa: PLC0415
        ScaffoldArgs,
        run_scaffold,
        StageFailure,
    )

    target = tmp_path / "newproj"
    target.mkdir()

    args = ScaffoldArgs(
        domain="배송관리",
        domain_slug="shipping",
        wiki_mode="preset",
        preset="배송관리",
        wiki_path=None,
        lane="nexacro",
        default_pattern="D2",
        package="com.example.shipping",
        out_dir=tmp_path / "scaffold-out",
        creator_root=CREATOR,
        stop_after_stage=5,
        dialect="hsqldb",
        service_name="Shipping",
        target_project=target,
        overlay_force=False,
        ui="nexacro",
        shell_mode="SDI",
    )

    try:
        run_scaffold(args)
    except StageFailure as exc:
        pytest.fail(f"StageFailure during SDI shell-mode run: {exc}")

    pkg = target / "nxui" / "packageN"
    frame_dir = pkg / "frame"

    # SDI-specific frame must exist
    sdi_frame = frame_dir / "frameSDI.xfdl"
    assert sdi_frame.exists(), "frameSDI.xfdl missing"

    # The shared frames (resolved from MDI fallback) must also exist
    for shared in ("frameMain.xfdl", "frameLeft.xfdl",
                   "frameTop.xfdl", "frameLogin.xfdl"):
        assert (frame_dir / shared).exists(), f"shared frame missing: {shared}"

    # MDI's per-variant frame must NOT be rendered when SDI is selected
    assert not (frame_dir / "frameMDI.xfdl").exists(), \
        "frameMDI.xfdl should not exist under SDI variant"

    # Auxiliary templates fall back from MDI dir
    assert (pkg / "typedefinition.xml").exists()
    assert (pkg / "packageN.xadl").exists()

    # frameMain.xfdl wires its workFrame to frameSDI under SDI variant
    main_text = (frame_dir / "frameMain.xfdl").read_text(encoding="utf-8")
    assert "frameSDI.xfdl" in main_text, \
        "frameMain.xfdl should wire workFrame to frameSDI.xfdl under SDI"
    assert "frameMDI.xfdl" not in main_text, \
        "frameMain.xfdl should not reference frameMDI.xfdl under SDI"
