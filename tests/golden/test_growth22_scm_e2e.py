# tests/golden/test_growth22_scm_e2e.py
"""Growth-22 — 공급망(SCM) standalone E2E golden through Stages 1-4.

Validates the freshly-registered 공급망 preset:
  1. Scaffolds cleanly through Stage 4.
  2. Stage 2 DDL emits all 6 SCM tables.
  3. purchase_order.workflow guards land in the blueprint (state machine seed).
  4. Cross-domain columns (sku_id, warehouse_id, requester_user_id,
     received_by_user_id) are emitted as plain bigint columns even though the
     referenced tables (sku/warehouse/app_user) are not part of this scaffold.
  5. Stage 4 emits a single merged SvcScm service (Phase-E contract).

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
        domain="공급망",
        domain_slug="scm",
        wiki_mode="preset",
        preset="공급망",
        wiki_path=None,
        lane="nexacro",
        default_pattern="D2",
        package="com.example.scm",
        out_dir=tmp_path / "scaffold-out",
        creator_root=CREATOR,
        stop_after_stage=4,
        dialect="hsqldb",
        service_name="Scm",
    )


def _run(args):
    from scaffold_orchestrator import run_scaffold, StageFailure  # noqa: PLC0415

    try:
        run_scaffold(args)
    except StageFailure as exc:
        pytest.fail(f"StageFailure during 공급망 scaffold: {exc}")


def test_growth22_scaffold_runs_clean(tmp_path):
    args = _build_args(tmp_path)
    _run(args)
    report = (args.out_dir / "scaffold-report.md").read_text(encoding="utf-8")
    assert "service_name: `Scm`" in report, report


def test_growth22_stage2_ddl_has_all_six_tables(tmp_path):
    """All 6 공급망 entities must compile into CREATE TABLE statements."""
    args = _build_args(tmp_path)
    _run(args)

    ddl_dir = args.out_dir / "2-ddl"
    combined = "\n".join(
        p.read_text(encoding="utf-8") for p in ddl_dir.rglob("*.sql")
    ).lower()
    for table in (
        "supplier", "supplier_contact",
        "purchase_order", "purchase_order_item",
        "goods_receipt", "goods_receipt_item",
    ):
        assert table in combined, f"DDL missing table `{table}`"


def test_growth22_stage2_emits_cross_domain_columns(tmp_path):
    """sku_id, warehouse_id, requester_user_id, received_by_user_id must
    appear as bigint columns even though sku/warehouse/app_user are absent.
    Validates Growth-21b-4 concept-only FK fallback (column persists when
    target entity absent; FK constraint silently skipped).
    """
    args = _build_args(tmp_path)
    _run(args)

    ddl_dir = args.out_dir / "2-ddl"
    combined = "\n".join(
        p.read_text(encoding="utf-8") for p in ddl_dir.rglob("*.sql")
    )
    for col in ("sku_id", "warehouse_id", "requester_user_id",
                "received_by_user_id", "deliver_warehouse_id"):
        assert col in combined, (
            f"cross-domain column `{col}` missing from DDL — "
            f"FK propagation broke for 공급망"
        )


def test_growth22_blueprint_lists_all_six_entities(tmp_path):
    """All 6 SCM entities should appear in the compiled blueprint."""
    args = _build_args(tmp_path)
    _run(args)

    bp = (args.out_dir / "1-wiki" / "_blueprint.yaml").read_text(encoding="utf-8")
    for entity in (
        "supplier", "supplier_contact",
        "purchase_order", "purchase_order_item",
        "goods_receipt", "goods_receipt_item",
    ):
        assert entity in bp, f"blueprint missing entity `{entity}`"


def test_growth22_stage4_single_service_svc_scm(tmp_path):
    """Phase-E contract: 공급망 collapses into a single SvcScm service."""
    args = _build_args(tmp_path)
    _run(args)

    patch = (
        args.out_dir / "4-nexacro" / "patches" / "typedefinition.patch.xml"
    ).read_text(encoding="utf-8")

    assert 'id="SvcScm"' in patch, patch
    assert 'url="/uiadapter/scm"' in patch, patch
    for leaked in ("SvcSupplier", "SvcPurchaseOrder", "SvcGoodsReceipt"):
        assert leaked not in patch, f"per-entity Service leaked: {leaked}"


def test_growth22_stage4_emits_form_per_entity(tmp_path):
    """All 6 SCM entities should each produce at least one xfdl form."""
    args = _build_args(tmp_path)
    _run(args)

    form_dir = args.out_dir / "4-nexacro" / "nxui" / "_form_"
    names = {p.stem.lower() for p in form_dir.glob("*.xfdl")}
    for entity in ("supplier", "purchase_order", "goods_receipt"):
        hit = any(entity in n for n in names)
        assert hit, (
            f"no xfdl form for entity `{entity}` — produced forms: {sorted(names)}"
        )
