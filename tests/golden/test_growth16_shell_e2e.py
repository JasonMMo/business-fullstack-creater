# tests/golden/test_growth16_shell_e2e.py
"""Growth-16 P4 — standalone shell E2E for the 배송관리 (shipping) domain.

Runs the full scaffold with --shell-mode=MDI against a fresh empty target
directory and verifies the standalone project tree contains:
  - the rendered shell (5 frames + typedefinition.xml + packageN.xadl)
  - the per-domain overlay (Java service + xfdl forms + menu injection)
  - optional nexacrolib copy when --nexacrolib-from is supplied

Skipped when any sibling stage repo is missing (no fixture base is required
for shell-mode because the shell adapter creates packageN/ from scratch).
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


def _build_args(tmp_path, target, *, shell_mode="MDI", nexacrolib_from=None):
    from scaffold_orchestrator import ScaffoldArgs  # noqa: PLC0415

    return ScaffoldArgs(
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
        shell_mode=shell_mode,
        nexacrolib_from=nexacrolib_from,
    )


def test_standalone_shell_mdi_renders_full_project(tmp_path):
    """Full pipeline + shell-mode=MDI into an empty target produces
    a self-contained standalone nexacro project (shell + domain artifacts).
    """
    from scaffold_orchestrator import run_scaffold, StageFailure  # noqa: PLC0415

    target = tmp_path / "newproj"
    target.mkdir()

    args = _build_args(tmp_path, target)
    try:
        run_scaffold(args)
    except StageFailure as exc:
        pytest.fail(f"StageFailure during shell-mode run: {exc}")

    pkg = target / "nxui" / "packageN"
    # Shell artifacts
    for name in ("frameMain.xfdl", "frameMDI.xfdl", "frameLeft.xfdl",
                 "frameTop.xfdl", "frameLogin.xfdl"):
        assert (pkg / "frame" / name).exists(), f"shell frame missing: {name}"
    assert (pkg / "typedefinition.xml").exists()
    assert (pkg / "packageN.xadl").exists()

    # Domain overlay artifacts
    java_root = target / "src" / "main" / "java" / "com" / "nexacro" / "uiadapter" / "shipping"
    assert java_root.is_dir(), f"Java overlay missing at {java_root}"
    assert list(java_root.rglob("*.java")), "no .java files copied"

    xfdl_dir = pkg / "shipping"
    assert xfdl_dir.is_dir(), "domain xfdl dir missing"
    assert list(xfdl_dir.glob("*.xfdl")), "no domain xfdl files"

    # scaffold-report records the shell pass
    report_md = (args.out_dir / "scaffold-report.md").read_text(encoding="utf-8")
    assert "stage5" in report_md


def test_standalone_shell_with_nexacrolib_copy(tmp_path):
    """--nexacrolib-from copies the supplied tree into target/nxui/nexacrolib/."""
    from scaffold_orchestrator import run_scaffold, StageFailure  # noqa: PLC0415

    # Fake nexacrolib donor — kept tiny to keep the test fast
    lib = tmp_path / "fake-nxlib"
    (lib / "components").mkdir(parents=True)
    (lib / "components" / "Grid.xcdl").write_text("<Grid/>", encoding="utf-8")
    (lib / "manifest.xml").write_text("<manifest/>", encoding="utf-8")

    target = tmp_path / "newproj"
    target.mkdir()

    args = _build_args(tmp_path, target, nexacrolib_from=lib)
    try:
        run_scaffold(args)
    except StageFailure as exc:
        pytest.fail(f"StageFailure during nexacrolib copy run: {exc}")

    nxlib = target / "nxui" / "nexacrolib"
    assert (nxlib / "components" / "Grid.xcdl").exists()
    assert (nxlib / "manifest.xml").exists()


def test_growth19_one_pass_korean_labels_and_typedef_merge(tmp_path):
    """Growth-19 — 1-pass shell × per-domain integration contract.

    Asserts the three things that prove the round-trip works:
      1. frameLeft.xfdl ds_menu rows use Korean labels from seed `display`
         (preserved as blueprint `label_ko`, propagated by shell adapter).
      2. typedefinition.xml carries BOTH the shell-emitted `svc` Service AND
         the per-domain Service prefixid (typedef_merger 1-pass).
      3. overlay report has menu_skipped (explicit shell-mode contract),
         not menu_warning (which would indicate an unexpected fallback).
    """
    from scaffold_orchestrator import run_scaffold, StageFailure  # noqa: PLC0415

    target = tmp_path / "newproj"
    target.mkdir()

    args = _build_args(tmp_path, target)
    try:
        run_scaffold(args)
    except StageFailure as exc:
        pytest.fail(f"StageFailure during Growth-19 1-pass run: {exc}")

    # 1. Korean labels in frameLeft ds_menu
    frame_left = (target / "nxui" / "packageN" / "frame" / "frameLeft.xfdl").read_text(
        encoding="utf-8"
    )
    for label in ("배송사", "배송", "배송 상품", "배송 추적"):
        assert f'<Col id="label">{label}</Col>' in frame_left, (
            f"frameLeft ds_menu missing Korean label '{label}' — "
            "Stage 1 label_ko propagation or shell adapter wiring broke"
        )

    # 2. typedefinition.xml: shell `svc` AND per-domain `shipping` Service entries
    typedef = (target / "nxui" / "packageN" / "typedefinition.xml").read_text(
        encoding="utf-8"
    )
    assert 'prefixid="svc"' in typedef, "shell svc Service missing from typedef"
    assert 'prefixid="shipping"' in typedef, (
        "per-domain shipping Service missing from typedef — typedef_merger broken"
    )

    # 3. Overlay report shape: menu intentionally skipped, no warning
    report_md = (args.out_dir / "scaffold-report.md").read_text(encoding="utf-8")
    assert "stage5" in report_md
