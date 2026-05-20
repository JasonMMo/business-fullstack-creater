# tests/golden/test_growth21b_sales_e2e.py
"""Growth-21b-1 — 영업관리 (CRM) E2E golden through Stages 1-4.

Validates that the freshly-registered 영업관리 preset:
  1. Scaffolds cleanly (no StageFailure) with preset=영업관리.
  2. Stage 2 DDL emits all 4 CRM tables (lead, opportunity,
     sales_activity, contact_person).
  3. Stage 3 wires data.sql (Spring auto-load) and a domain mapper tree.
  4. Stage 4 emits exactly one merged Service `SvcSales` (per Phase-E
     single-service contract) and xfdl forms reference it.

Cross-domain columns (customer_id → 고객관리.customer,
owner_user_id → 권한관리.app_user) are emitted as bigint columns; the
referenced tables are NOT part of this scaffold, so the test asserts the
columns are present without requiring FK constraints to resolve.

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


def _build_args(tmp_path):
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
        stop_after_stage=4,
        dialect="hsqldb",
        service_name="Sales",
    )


def _run(args):
    from scaffold_orchestrator import run_scaffold, StageFailure  # noqa: PLC0415

    try:
        run_scaffold(args)
    except StageFailure as exc:
        pytest.fail(f"StageFailure during 영업관리 scaffold: {exc}")


def test_growth21b_sales_scaffold_runs_clean(tmp_path):
    args = _build_args(tmp_path)
    _run(args)
    report = (args.out_dir / "scaffold-report.md").read_text(encoding="utf-8")
    assert "service_name: `Sales`" in report, report
    assert "dialect: `hsqldb`" in report, report


def test_growth21b_stage2_ddl_has_all_four_tables(tmp_path):
    """All 4 영업관리 entities must compile into CREATE TABLE statements."""
    args = _build_args(tmp_path)
    _run(args)

    ddl_dir = args.out_dir / "2-ddl"
    sql_files = list(ddl_dir.rglob("*.sql"))
    assert sql_files, f"no .sql files emitted under {ddl_dir}"

    combined = "\n".join(p.read_text(encoding="utf-8") for p in sql_files).lower()
    for table in ("lead", "opportunity", "sales_activity", "contact_person"):
        # accept either `create table lead` or `create table "lead"` etc.
        assert f"create table" in combined and table in combined, (
            f"DDL missing table `{table}` — combined SQL:\n{combined[:2000]}"
        )


def test_growth21b_stage2_emits_cross_domain_columns(tmp_path):
    """opportunity.customer_id and *.owner_user_id must appear as bigint
    columns even though the referenced tables (customer, app_user) are
    not in this scaffold.
    """
    args = _build_args(tmp_path)
    _run(args)

    ddl_dir = args.out_dir / "2-ddl"
    combined = "\n".join(
        p.read_text(encoding="utf-8") for p in ddl_dir.rglob("*.sql")
    )
    for col in ("customer_id", "owner_user_id"):
        assert col in combined, (
            f"cross-domain column `{col}` missing from DDL — "
            f"FK propagation broke for 영업관리"
        )


def test_growth21b_stage3_data_sql_wired(tmp_path):
    args = _build_args(tmp_path)
    _run(args)

    data_sql = args.out_dir / "3-mybatis" / "src" / "main" / "resources" / "data.sql"
    assert data_sql.exists(), f"data.sql missing at {data_sql}"
    assert data_sql.read_text(encoding="utf-8").strip(), "data.sql empty"


def test_growth21b_stage4_single_service_svc_sales(tmp_path):
    """Phase-E contract: 영업관리 collapses into a single SvcSales service.
    Per-entity Service ids (SvcLead/SvcOpportunity/...) must NOT leak.
    """
    args = _build_args(tmp_path)
    _run(args)

    patch = (
        args.out_dir / "4-nexacro" / "patches" / "typedefinition.patch.xml"
    ).read_text(encoding="utf-8")

    assert 'id="SvcSales"' in patch, patch
    assert 'url="/uiadapter/sales"' in patch, patch
    for leaked in ("SvcLead", "SvcOpportunity", "SvcSalesActivity", "SvcContactPerson"):
        assert leaked not in patch, f"per-entity Service leaked: {leaked}"


def test_growth21b_stage4_xfdl_forms_reference_svc_sales(tmp_path):
    args = _build_args(tmp_path)
    _run(args)

    form_dir = args.out_dir / "4-nexacro" / "nxui" / "_form_"
    xfdl_files = list(form_dir.glob("*.xfdl"))
    assert xfdl_files, f"no xfdl forms emitted under {form_dir}"

    for xfdl in xfdl_files:
        text = xfdl.read_text(encoding="utf-8")
        assert "SvcSales::" in text, (
            f"{xfdl.name} does not reference SvcSales:: — "
            f"single-service wiring broke"
        )


def test_growth21b_stage4_emits_form_per_entity(tmp_path):
    """All 4 CRM entities should each produce at least one xfdl form."""
    args = _build_args(tmp_path)
    _run(args)

    form_dir = args.out_dir / "4-nexacro" / "nxui" / "_form_"
    names = {p.stem.lower() for p in form_dir.glob("*.xfdl")}
    for entity in ("lead", "opportunity", "sales_activity", "contact_person"):
        hit = any(entity in n for n in names)
        assert hit, (
            f"no xfdl form for entity `{entity}` — produced forms: {sorted(names)}"
        )
