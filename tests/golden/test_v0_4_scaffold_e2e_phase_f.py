# tests/golden/test_v0_4_scaffold_e2e_phase_f.py
"""Phase F golden E2E: Stage 5 overlay — target project integration.

Six cases covering:
  1. No target → stage5 SKIPPED label in report
  2. Fixture base-scaffold overlay (java/resources/xfdl/menu/typedef)
  3. Idempotent re-run with overlay_force=True
  4. Conflict without overlay_force raises StageFailure
  5. frameLogin schema mismatch — other steps continue, menu skipped
  6. Real target overlay (skipped when D:\\AI\\testspace\\nexa-boot-jdk17 absent)

Skipped automatically when any sibling stage repo is absent.
Uses the '주문관리' preset with package=com.example.order / service_name=Order.
"""
import os
import pathlib
import re
import shutil
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
_SKIP_REASON = (
    f"sibling stage repo(s) not found: {', '.join(_MISSING)} "
    f"(expected at {CREATOR.parent})"
    if _MISSING
    else ""
)

pytestmark = pytest.mark.skipif(bool(_MISSING), reason=_SKIP_REASON)

# ---------------------------------------------------------------------------
# Fixture paths
# ---------------------------------------------------------------------------

_FIXTURE_BASE = CREATOR / "tests" / "golden" / "fixtures" / "base_scaffold"
_REAL_TARGET = pathlib.Path(r"D:\AI\testspace\nexa-boot-jdk17")


# ---------------------------------------------------------------------------
# Helper: build a fresh ScaffoldArgs pointing at tmp_path
# ---------------------------------------------------------------------------

def _build_args(tmp_path: pathlib.Path, target_dir=None, overlay_force: bool = False):
    from scaffold_orchestrator import ScaffoldArgs  # noqa: PLC0415

    return ScaffoldArgs(
        domain="주문관리",
        domain_slug="order",
        wiki_mode="preset",
        preset="주문관리",
        wiki_path=None,
        lane="nexacro",
        default_pattern="D2",
        package="com.example.order",
        out_dir=tmp_path / "scaffold-out",
        creator_root=CREATOR,
        stop_after_stage=5,
        dialect="hsqldb",
        service_name="Order",
        target_project=target_dir,
        overlay_force=overlay_force,
    )


# ---------------------------------------------------------------------------
# Case 1: No target → stage5 SKIPPED
# ---------------------------------------------------------------------------

def test_no_target_skips_stage5(tmp_path):
    """When target_project is None, stage5 must be marked SKIPPED in report."""
    from scaffold_orchestrator import run_scaffold, StageFailure  # noqa: PLC0415

    args = _build_args(tmp_path, target_dir=None)

    try:
        run_scaffold(args)
    except StageFailure as exc:
        pytest.fail(f"StageFailure during no-target run: {exc}")

    report_md = (args.out_dir / "scaffold-report.md").read_text(encoding="utf-8")
    assert "stage5: SKIPPED" in report_md, (
        f"Expected 'stage5: SKIPPED' in scaffold-report.md; got:\n{report_md}"
    )

    # Smoke: Phase-E-equivalent output still present
    data_sql = args.out_dir / "3-mybatis" / "src" / "main" / "resources" / "data.sql"
    assert data_sql.exists(), f"data.sql missing at {data_sql}"

    patch = (args.out_dir / "4-nexacro" / "patches" / "typedefinition.patch.xml").read_text(
        encoding="utf-8"
    )
    assert 'id="SvcOrder"' in patch, "SvcOrder not in typedef patch"


# ---------------------------------------------------------------------------
# Case 2: Overlay onto fixture base scaffold
# ---------------------------------------------------------------------------

def test_overlay_to_fixture_base_scaffold(tmp_path):
    """Full overlay onto the fixture scaffold: java/resources/xfdl/menu/typedef."""
    from scaffold_orchestrator import run_scaffold, StageFailure  # noqa: PLC0415

    # Copy fixture so it stays clean
    target = tmp_path / "target"
    shutil.copytree(_FIXTURE_BASE, target)

    args = _build_args(tmp_path, target_dir=target)

    try:
        run_scaffold(args)
    except StageFailure as exc:
        pytest.fail(f"StageFailure during overlay run: {exc}")

    # Java files placed under the uiadapter tree
    java_root = target / "src" / "main" / "java" / "com" / "nexacro" / "uiadapter" / "order"
    assert java_root.is_dir(), f"Java root dir missing: {java_root}"
    java_files = list(java_root.rglob("*.java"))
    assert java_files, f"No .java files under {java_root}"

    # Package declaration rewritten
    sample_java = java_files[0].read_text(encoding="utf-8")
    assert sample_java.startswith("package com.nexacro.uiadapter.order"), (
        f"Package not rewritten in {java_files[0].name}:\n{sample_java[:200]}"
    )

    # schema.sql written; scaffold.bak NOT present (base had none to back up)
    schema_sql = target / "src" / "main" / "resources" / "schema.sql"
    assert schema_sql.exists(), f"schema.sql not written to {schema_sql}"
    assert not (schema_sql.parent / "schema.sql.scaffold.bak").exists(), (
        "scaffold.bak should not exist — base fixture had no prior schema.sql"
    )

    # xfdl forms placed
    xfdl_dir = target / "nxui" / "packageN" / "order"
    assert xfdl_dir.is_dir(), f"xfdl order dir missing: {xfdl_dir}"
    assert list(xfdl_dir.glob("*.xfdl")), f"No xfdl files under {xfdl_dir}"

    # frameLogin.xfdl contains BIZ_ORDER group row
    frame_login = target / "nxui" / "packageN" / "frame" / "frameLogin.xfdl"
    frame_text = frame_login.read_text(encoding="utf-8")
    assert '<Col id="menuId">BIZ_ORDER</Col>' in frame_text, (
        f"BIZ_ORDER group row not injected into frameLogin.xfdl"
    )

    # typedefinition.xml contains prefixid="order"
    typedef_text = (target / "nxui" / "packageN" / "typedefinition.xml").read_text(
        encoding="utf-8"
    )
    assert 'prefixid="order"' in typedef_text, (
        "prefixid='order' not inserted into typedefinition.xml"
    )

    # One-shot backups created
    assert (target / "nxui" / "packageN" / "frame" / "frameLogin.xfdl.bak").exists(), (
        "frameLogin.xfdl.bak not created"
    )
    assert (target / "nxui" / "packageN" / "typedefinition.xml.bak").exists(), (
        "typedefinition.xml.bak not created"
    )


# ---------------------------------------------------------------------------
# Case 3: Idempotency — second overlay doesn't duplicate rows or overwrite .bak
# ---------------------------------------------------------------------------

def test_overlay_is_idempotent(tmp_path):
    """Re-running overlay (overlay_force=True) must not duplicate menu/typedef entries
    and must not touch existing .bak files."""
    from scaffold_orchestrator import run_scaffold, StageFailure  # noqa: PLC0415

    target = tmp_path / "target"
    shutil.copytree(_FIXTURE_BASE, target)

    # --- Run 1 ---
    args = _build_args(tmp_path, target_dir=target)
    try:
        run_scaffold(args)
    except StageFailure as exc:
        pytest.fail(f"Run 1 StageFailure: {exc}")

    frame_login = target / "nxui" / "packageN" / "frame" / "frameLogin.xfdl"
    typedef_path = target / "nxui" / "packageN" / "typedefinition.xml"
    frame_bak = pathlib.Path(str(frame_login) + ".bak")

    frame_text_1 = frame_login.read_text(encoding="utf-8")
    rows_count_1 = frame_text_1.count("<Row>")
    typedef_text_1 = typedef_path.read_text(encoding="utf-8")
    order_count_1 = typedef_text_1.count('prefixid="order"')

    bak_mtime = frame_bak.stat().st_mtime
    bak_size = frame_bak.stat().st_size

    assert order_count_1 == 1, f"Expected 1 prefixid='order' after run 1; got {order_count_1}"

    # --- Run 2 (overlay_force=True to bypass conflict scan on existing java/xfdl) ---
    # Use a fresh out_dir so Stage 4 form_gen.py doesn't see its own prior output
    # and trigger its internal conflict guard.  The *target* directory is reused.
    args2 = _build_args(tmp_path / "run2", target_dir=target, overlay_force=True)
    try:
        run_scaffold(args2)
    except StageFailure as exc:
        pytest.fail(f"Run 2 StageFailure: {exc}")

    frame_text_2 = frame_login.read_text(encoding="utf-8")
    rows_count_2 = frame_text_2.count("<Row>")
    typedef_text_2 = typedef_path.read_text(encoding="utf-8")
    order_count_2 = typedef_text_2.count('prefixid="order"')

    assert rows_count_2 == rows_count_1, (
        f"Menu rows duplicated after idempotent re-run: "
        f"run1={rows_count_1} run2={rows_count_2}"
    )
    assert order_count_2 == 1, (
        f"typedef 'prefixid=order' duplicated: run1={order_count_1} run2={order_count_2}"
    )

    # .bak must be unchanged (one-shot backup semantics)
    bak_stat_2 = frame_bak.stat()
    assert bak_stat_2.st_mtime == bak_mtime, (
        f"frameLogin.xfdl.bak mtime changed on 2nd run — one-shot backup broken"
    )
    assert bak_stat_2.st_size == bak_size, (
        f"frameLogin.xfdl.bak size changed on 2nd run"
    )


# ---------------------------------------------------------------------------
# Case 4: Conflict without overlay_force raises StageFailure
# ---------------------------------------------------------------------------

def test_conflict_without_overlay_force_raises(tmp_path):
    """Pre-existing java file + overlay_force=False must raise StageFailure.
    The pre-existing file must remain untouched (conflict-scan-first guarantees no writes)."""
    from scaffold_orchestrator import run_scaffold, StageFailure  # noqa: PLC0415

    target = tmp_path / "target"
    shutil.copytree(_FIXTURE_BASE, target)

    # Pre-create a conflicting controller file that matches an actual generated name.
    # Stage 3 (mybatis) produces OrderItemController.java → maps to target path below.
    conflict_path = (
        target
        / "src" / "main" / "java"
        / "com" / "nexacro" / "uiadapter" / "order" / "controller"
        / "OrderItemController.java"
    )
    conflict_path.parent.mkdir(parents=True, exist_ok=True)
    _SENTINEL = "// PRE_EXISTING_CONTENT — must remain unchanged\n"
    conflict_path.write_text(_SENTINEL, encoding="utf-8")

    args = _build_args(tmp_path, target_dir=target, overlay_force=False)

    with pytest.raises(StageFailure, match="stage5 conflict"):
        run_scaffold(args)

    # File must be unchanged
    assert conflict_path.read_text(encoding="utf-8") == _SENTINEL, (
        "Conflict-detected file was modified despite conflict-scan-first protection"
    )


# ---------------------------------------------------------------------------
# Case 5: frameLogin schema mismatch → menu skipped, other steps continue
# ---------------------------------------------------------------------------

def test_schema_mismatch_skips_only_menu(tmp_path):
    """Remove 'auth' column from frameLogin <ColumnInfo> → SchemaMismatch;
    overlay must complete and report the warning while java/xfdl/typedef still applied."""
    from scaffold_orchestrator import run_scaffold, StageFailure  # noqa: PLC0415

    target = tmp_path / "target"
    shutil.copytree(_FIXTURE_BASE, target)

    # Remove the <Column id="auth" .../> line from frameLogin.xfdl ColumnInfo
    frame_login = target / "nxui" / "packageN" / "frame" / "frameLogin.xfdl"
    original_text = frame_login.read_text(encoding="utf-8")
    mutated_text = re.sub(
        r'\s*<Column id="auth"[^/]*/>\n?', "", original_text
    )
    assert mutated_text != original_text, (
        "auth column removal had no effect — fixture may have changed"
    )
    frame_login.write_text(mutated_text, encoding="utf-8")

    args = _build_args(tmp_path, target_dir=target)

    # Must NOT raise — schema mismatch is reported, not fatal
    try:
        run_scaffold(args)
    except StageFailure as exc:
        pytest.fail(f"StageFailure raised on schema mismatch (should be non-fatal): {exc}")

    # Report contains schema mismatch info
    report_md = (args.out_dir / "scaffold-report.md").read_text(encoding="utf-8")
    assert "schema mismatch" in report_md.lower(), (
        f"'schema mismatch' not found in scaffold-report.md:\n{report_md}"
    )
    assert "'auth'" in report_md or '"auth"' in report_md or "auth" in report_md, (
        f"Missing column 'auth' not mentioned in scaffold-report.md:\n{report_md}"
    )

    # Java overlay happened
    java_root = target / "src" / "main" / "java" / "com" / "nexacro" / "uiadapter" / "order"
    assert java_root.is_dir() and list(java_root.rglob("*.java")), (
        "Java overlay did not happen despite schema mismatch being non-fatal"
    )

    # Typedef merge happened
    typedef_text = (target / "nxui" / "packageN" / "typedefinition.xml").read_text(
        encoding="utf-8"
    )
    assert 'prefixid="order"' in typedef_text, (
        "Typedef merge did not happen despite schema mismatch being non-fatal"
    )

    # xfdl forms copied
    xfdl_dir = target / "nxui" / "packageN" / "order"
    assert xfdl_dir.is_dir() and list(xfdl_dir.glob("*.xfdl")), (
        "xfdl copy did not happen despite schema mismatch being non-fatal"
    )

    # frameLogin.xfdl must NOT contain BIZ_ORDER (menu step was skipped)
    frame_text_after = frame_login.read_text(encoding="utf-8")
    assert "BIZ_ORDER" not in frame_text_after, (
        "BIZ_ORDER found in frameLogin.xfdl — menu injection should have been skipped"
    )


# ---------------------------------------------------------------------------
# Case 6: Real target overlay (optional)
# ---------------------------------------------------------------------------

@pytest.mark.skipif(
    not _REAL_TARGET.exists(),
    reason=f"real test target not present: {_REAL_TARGET}",
)
def test_real_target_overlay_optional(tmp_path):
    """Overlay onto a copy of the real nexa-boot-jdk17 project.

    The original is never mutated — we copy to tmp_path first.
    Skipped when D:\\AI\\testspace\\nexa-boot-jdk17 is absent.
    """
    from scaffold_orchestrator import run_scaffold, StageFailure  # noqa: PLC0415

    # Copy real target to tmp so original is untouched
    real_copy = tmp_path / "real_target_copy"
    shutil.copytree(_REAL_TARGET, real_copy)

    # Use overlay_force=True in case real target already has some generated files
    args = _build_args(tmp_path, target_dir=real_copy, overlay_force=True)

    try:
        run_scaffold(args)
    except StageFailure as exc:
        pytest.fail(f"StageFailure on real target overlay: {exc}")

    # typedef updated
    typedef_path = real_copy / "nxui" / "packageN" / "typedefinition.xml"
    if typedef_path.exists():
        assert 'prefixid="order"' in typedef_path.read_text(encoding="utf-8"), (
            "prefixid='order' not inserted into real-target typedefinition.xml"
        )

    # frameLogin updated (if schema matched)
    frame_login = real_copy / "nxui" / "packageN" / "frame" / "frameLogin.xfdl"
    if frame_login.exists():
        frame_text = frame_login.read_text(encoding="utf-8")
        # Only assert BIZ_ORDER if no schema mismatch occurred
        report_md = (args.out_dir / "scaffold-report.md").read_text(encoding="utf-8")
        if "schema mismatch" not in report_md.lower():
            assert "BIZ_ORDER" in frame_text, (
                "BIZ_ORDER not injected into real-target frameLogin.xfdl"
            )

    # Java files placed
    java_root = (
        real_copy / "src" / "main" / "java"
        / "com" / "nexacro" / "uiadapter" / "order"
    )
    assert java_root.is_dir() and list(java_root.rglob("*.java")), (
        f"No java files placed under {java_root}"
    )
