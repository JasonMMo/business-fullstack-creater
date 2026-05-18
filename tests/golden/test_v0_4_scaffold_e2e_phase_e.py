# tests/golden/test_v0_4_scaffold_e2e_phase_e.py
"""Phase E golden E2E: hsqldb dialect + data.sql wiring + single Service.

Skipped automatically when any sibling repo is absent.
Uses the '고객관리' preset (confirmed present in rdb-skill presets/).
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
_SKIP_REASON = (
    f"sibling stage repo(s) not found: {', '.join(_MISSING)} "
    f"(expected at {CREATOR.parent})"
    if _MISSING
    else ""
)


@pytest.mark.skipif(bool(_MISSING), reason=_SKIP_REASON)
def test_scaffold_e2e_hsqldb_seed_single_service(tmp_path):
    """Phase E: dialect=hsqldb, seed.sql wired to Stage 3, single SvcOrder service."""
    from scaffold_orchestrator import ScaffoldArgs, run_scaffold, StageFailure  # noqa: PLC0415

    out = tmp_path / "scaffold-out"

    args = ScaffoldArgs(
        domain="주문관리",
        domain_slug="order",
        wiki_mode="preset",
        preset="주문관리",
        wiki_path=None,
        lane="nexacro",
        default_pattern="D2",
        package="com.test.order",
        out_dir=out,
        creator_root=CREATOR,
        stop_after_stage=4,
        dialect="hsqldb",
        service_name="Order",
    )

    try:
        run_scaffold(args)
    except StageFailure as exc:
        pytest.fail(f"StageFailure: {exc}")

    # 1. scaffold-report.md mentions dialect + service_name
    report_md = (out / "scaffold-report.md").read_text(encoding="utf-8")
    assert "dialect: `hsqldb`" in report_md, report_md
    assert "service_name: `Order`" in report_md, report_md

    # 2. Stage 2 emitted seed/ directory with at least one .sql file
    seed_dir = out / "2-ddl" / "seed"
    assert seed_dir.is_dir(), f"seed dir missing at {seed_dir}"
    seed_files = list(seed_dir.glob("*.sql"))
    assert len(seed_files) >= 1, f"no seed .sql files in {seed_dir}"

    # 3. Stage 3 has data.sql under src/main/resources/ (Spring auto-loads it)
    data_sql = out / "3-mybatis" / "src" / "main" / "resources" / "data.sql"
    assert data_sql.exists(), (
        f"data.sql not produced at {data_sql}. "
        f"resources dir contents: "
        f"{list((out / '3-mybatis' / 'src' / 'main' / 'resources').rglob('*')) if (out / '3-mybatis' / 'src' / 'main' / 'resources').exists() else 'MISSING'}"
    )
    data_sql_text = data_sql.read_text(encoding="utf-8")
    assert data_sql_text.strip(), "data.sql is empty"

    # 4. Stage 4 typedefinition.patch.xml has a single Service id="SvcOrder"
    patch = (out / "4-nexacro" / "patches" / "typedefinition.patch.xml").read_text(encoding="utf-8")
    assert 'id="SvcOrder"' in patch, patch
    assert 'url="/uiadapter/order"' in patch, patch
    # confirm no per-entity services leaked through
    assert 'SvcOrderItem' not in patch, "per-entity Service leaked: SvcOrderItem"
    assert 'SvcPayment' not in patch, "per-entity Service leaked: SvcPayment"
    assert 'SvcSalesOrder' not in patch, "per-entity Service leaked: SvcSalesOrder"

    # 5. xfdl forms reference SvcOrder (not the per-entity ids)
    form_dir = out / "4-nexacro" / "nxui" / "_form_"
    xfdl_files = list(form_dir.glob("*.xfdl"))
    assert xfdl_files, f"no xfdl forms in {form_dir}"
    for xfdl in xfdl_files:
        text = xfdl.read_text(encoding="utf-8")
        assert "SvcOrder::" in text, (
            f"{xfdl.name} does not reference SvcOrder::"
        )
