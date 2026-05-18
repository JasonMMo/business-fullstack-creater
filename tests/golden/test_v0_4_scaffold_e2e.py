# tests/golden/test_v0_4_scaffold_e2e.py
"""Golden E2E test: real 4-stage scaffold using sibling stage repositories.

Skipped automatically when any sibling repo is absent from the expected path.
Uses the '고객관리' preset (confirmed present in rdb-skill presets/).
"""
import pathlib
import sys

import pytest

# ---------------------------------------------------------------------------
# Resolve paths
# ---------------------------------------------------------------------------
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


# ---------------------------------------------------------------------------
# Test
# ---------------------------------------------------------------------------
@pytest.mark.skipif(bool(_MISSING), reason=_SKIP_REASON)
def test_scaffold_e2e_preset_고객관리_D2(tmp_path):
    """Full 4-stage scaffold with the '고객관리' preset, lane=nexacro, pattern=D2."""
    from scaffold_orchestrator import ScaffoldArgs, run_scaffold, StageFailure  # noqa: PLC0415

    out = tmp_path / "scaffold-out"

    args = ScaffoldArgs(
        domain="고객관리",
        domain_slug="customer",
        wiki_mode="preset",
        preset="고객관리",
        wiki_path=None,
        lane="nexacro",
        default_pattern="D2",
        package="com.test.scaffold",
        out_dir=out,
        creator_root=CREATOR,
        stop_after_stage=4,
    )

    try:
        report = run_scaffold(args)
    except StageFailure as exc:
        # Print the full error so CI logs show what went wrong
        pytest.fail(f"StageFailure: {exc}")

    # -----------------------------------------------------------------------
    # 1. All 4 stages completed
    # -----------------------------------------------------------------------
    assert report.stages_run == ["stage1", "stage2", "stage3", "stage4"], (
        f"Unexpected stages_run: {report.stages_run}"
    )

    # -----------------------------------------------------------------------
    # 2. scaffold-report.md exists and contains OK markers for all stages
    # -----------------------------------------------------------------------
    report_md = out / "scaffold-report.md"
    assert report_md.exists(), "scaffold-report.md not written"
    report_content = report_md.read_text(encoding="utf-8")
    for stage in ("stage1", "stage2", "stage3", "stage4"):
        assert stage in report_content, (
            f"{stage} not found in scaffold-report.md"
        )
        assert f"- {stage}: OK" in report_content, (
            f"'- {stage}: OK' marker missing in scaffold-report.md"
        )

    # -----------------------------------------------------------------------
    # 3. Stage 1: _blueprint.yaml produced
    # -----------------------------------------------------------------------
    blueprint = out / "1-wiki" / "_blueprint.yaml"
    assert blueprint.exists(), f"_blueprint.yaml not found at {blueprint}"

    # -----------------------------------------------------------------------
    # 4. Stage 2: DDL directory contains at least one .sql file
    # -----------------------------------------------------------------------
    ddl_dir = out / "2-ddl"
    assert ddl_dir.is_dir(), f"2-ddl directory not found at {ddl_dir}"
    # Stage 2 (ddl_gen) places SQL files inside a migrations/ subdirectory
    sql_files = list(ddl_dir.rglob("*.sql"))
    assert len(sql_files) >= 1, (
        f"No .sql files found under {ddl_dir}; contents: {list(ddl_dir.rglob('*'))}"
    )

    # -----------------------------------------------------------------------
    # 5. Stage 3: MyBatis output directory exists and has content
    # -----------------------------------------------------------------------
    mybatis_dir = out / "3-mybatis"
    assert mybatis_dir.is_dir(), f"3-mybatis directory not found at {mybatis_dir}"
    mybatis_files = list(mybatis_dir.rglob("*"))
    assert len(mybatis_files) >= 1, (
        f"3-mybatis directory is empty; expected mapper/java output"
    )

    # -----------------------------------------------------------------------
    # 6. Stage 4: Nexacro .xfdl forms produced
    # -----------------------------------------------------------------------
    nexacro_dir = out / "4-nexacro"
    assert nexacro_dir.is_dir(), f"4-nexacro directory not found at {nexacro_dir}"
    xfdl_files = list((nexacro_dir / "nxui" / "_form_").glob("*.xfdl"))
    assert len(xfdl_files) >= 1, (
        f"No .xfdl files found in {nexacro_dir / 'nxui' / '_form_'}; "
        f"nexacro_dir contents: {list(nexacro_dir.rglob('*'))}"
    )
