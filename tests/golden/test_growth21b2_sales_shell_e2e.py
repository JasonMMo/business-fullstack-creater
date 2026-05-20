# tests/golden/test_growth21b2_sales_shell_e2e.py
"""Growth-21b-2 — 영업관리 standalone shell × MDI E2E.

Extends Growth-21b-1 (Stage 1-4) by also exercising Stage 5 shell-mode
into a fresh empty target directory. Verifies:
  1. Shell frames rendered (frameMain/MDI/Left/Top/Login + typedef + xadl).
  2. Per-domain Java overlay placed under com/nexacro/uiadapter/sales/.
  3. Domain xfdl forms emitted under nxui/packageN/sales/.
  4. frameLeft ds_menu surfaces the seed Korean labels (display).
  5. typedefinition.xml carries BOTH shell `svc` AND per-domain `sales`
     Service prefixes (typedef_merger 1-pass).

Skipped when any sibling stage repo is missing.
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


def _build_args(tmp_path, target, *, shell_mode="MDI"):
    from scaffold_orchestrator import ScaffoldArgs  # noqa: PLC0415

    return ScaffoldArgs(
        domain="영업관리",
        domain_slug="sales",
        wiki_mode="preset",
        preset="영업관리",
        wiki_path=None,
        lane="nexacro",
        default_pattern="D2",
        package="com.example.sales",
        out_dir=tmp_path / "scaffold-out",
        creator_root=CREATOR,
        stop_after_stage=5,
        dialect="hsqldb",
        service_name="Sales",
        target_project=target,
        overlay_force=False,
        ui="nexacro",
        shell_mode=shell_mode,
    )


def _run(args):
    from scaffold_orchestrator import run_scaffold, StageFailure  # noqa: PLC0415

    try:
        run_scaffold(args)
    except StageFailure as exc:
        pytest.fail(f"StageFailure during 영업관리 shell-mode run: {exc}")


def test_growth21b2_shell_mdi_full_project(tmp_path):
    target = tmp_path / "newproj"
    target.mkdir()
    args = _build_args(tmp_path, target)
    _run(args)

    pkg = target / "nxui" / "packageN"
    for name in ("frameMain.xfdl", "frameMDI.xfdl", "frameLeft.xfdl",
                 "frameTop.xfdl", "frameLogin.xfdl"):
        assert (pkg / "frame" / name).exists(), f"shell frame missing: {name}"
    assert (pkg / "typedefinition.xml").exists()
    assert (pkg / "packageN.xadl").exists()


def test_growth21b2_overlay_emits_java_and_xfdl(tmp_path):
    target = tmp_path / "newproj"
    target.mkdir()
    args = _build_args(tmp_path, target)
    _run(args)

    java_root = (
        target / "src" / "main" / "java" / "com" / "nexacro"
        / "uiadapter" / "sales"
    )
    assert java_root.is_dir(), f"Java overlay missing at {java_root}"
    assert list(java_root.rglob("*.java")), "no .java files copied"

    xfdl_dir = target / "nxui" / "packageN" / "sales"
    assert xfdl_dir.is_dir(), "domain xfdl dir missing"
    assert list(xfdl_dir.glob("*.xfdl")), "no domain xfdl files"


def test_growth21b2_frame_left_carries_korean_labels(tmp_path):
    """seed display values must reach frameLeft ds_menu via label_ko."""
    target = tmp_path / "newproj"
    target.mkdir()
    args = _build_args(tmp_path, target)
    _run(args)

    frame_left = (
        target / "nxui" / "packageN" / "frame" / "frameLeft.xfdl"
    ).read_text(encoding="utf-8")

    for label in ("잠재고객", "영업기회", "영업활동", "거래처담당자"):
        assert f'<Col id="label">{label}</Col>' in frame_left, (
            f"frameLeft ds_menu missing Korean label '{label}' — "
            "seed display → label_ko → shell adapter wiring broke"
        )


def test_growth21b2_typedef_merges_shell_and_sales_services(tmp_path):
    target = tmp_path / "newproj"
    target.mkdir()
    args = _build_args(tmp_path, target)
    _run(args)

    typedef = (
        target / "nxui" / "packageN" / "typedefinition.xml"
    ).read_text(encoding="utf-8")

    assert 'prefixid="svc"' in typedef, "shell svc Service missing from typedef"
    assert 'prefixid="sales"' in typedef, (
        "per-domain sales Service missing from typedef — typedef_merger broken"
    )


def test_growth21b2_scaffold_report_records_stage5(tmp_path):
    target = tmp_path / "newproj"
    target.mkdir()
    args = _build_args(tmp_path, target)
    _run(args)

    report_md = (args.out_dir / "scaffold-report.md").read_text(encoding="utf-8")
    assert "stage5" in report_md
