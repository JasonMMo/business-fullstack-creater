# tests/golden/test_growth22b_scm_cross_domain.py
"""Growth-22b — 공급망 × 재고관리 × 권한관리 cross-domain FK 점검.

Validates Growth-21b-4 concept-only FK fallback on the new 공급망 seed:
  1. Combined wiki blueprint covers all three domains.
  2. purchase_order_item.sku_id resolves to FK → 재고관리.sku.
  3. purchase_order.deliver_warehouse_id resolves to FK → 재고관리.warehouse.
  4. purchase_order.requester_user_id resolves to FK → 권한관리.app_user.
  5. goods_receipt_item.sku_id resolves to FK → 재고관리.sku.

Skipped when any sibling stage repo is missing.
"""
import pathlib
import re
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

PRESETS = ("재고관리", "권한관리", "공급망")


def _build_combined_wiki(tmp_path):
    from scaffold_orchestrator import _init_wiki_from_preset  # noqa: PLC0415

    combined = tmp_path / "combined-wiki"
    combined.mkdir(parents=True, exist_ok=True)
    s1 = SIBLINGS["stage1"]
    for preset in PRESETS:
        _init_wiki_from_preset(preset, s1, combined)
    return combined


def _build_args(tmp_path, wiki_dir):
    from scaffold_orchestrator import ScaffoldArgs  # noqa: PLC0415

    return ScaffoldArgs(
        domain="공급망+재고관리+권한관리",
        domain_slug="scm_bundle",
        wiki_mode="wiki",
        preset=None,
        wiki_path=wiki_dir,
        lane="nexacro",
        default_pattern="D2",
        package="com.example.scmbundle",
        out_dir=tmp_path / "scaffold-out",
        creator_root=CREATOR,
        stop_after_stage=4,
        dialect="hsqldb",
        service_name="ScmBundle",
    )


def _run(args):
    from scaffold_orchestrator import run_scaffold, StageFailure  # noqa: PLC0415

    try:
        run_scaffold(args)
    except StageFailure as exc:
        pytest.fail(f"StageFailure during cross-domain SCM scaffold: {exc}")


def _combined_ddl(args):
    ddl_dir = args.out_dir / "2-ddl"
    return "\n".join(p.read_text(encoding="utf-8") for p in ddl_dir.rglob("*.sql"))


def test_growth22b_combined_wiki_compiles_three_domains(tmp_path):
    wiki = _build_combined_wiki(tmp_path)
    args = _build_args(tmp_path, wiki)
    _run(args)

    bp = (args.out_dir / "1-wiki" / "_blueprint.yaml").read_text(encoding="utf-8")
    for entity in ("sku", "warehouse", "app_user", "purchase_order", "goods_receipt"):
        assert entity in bp, (
            f"blueprint missing `{entity}` — combined wiki failed to merge"
        )


def test_growth22b_purchase_order_item_sku_fk(tmp_path):
    """purchase_order_item.sku_id must declare an FK against sku."""
    wiki = _build_combined_wiki(tmp_path)
    args = _build_args(tmp_path, wiki)
    _run(args)

    ddl = _combined_ddl(args).lower()
    assert re.search(
        r"foreign key\s*\(\s*sku_id\s*\)\s*references\s+(\w+\.)?sku\b", ddl
    ), "purchase_order_item.sku_id did not resolve to FK → sku"


def test_growth22b_purchase_order_warehouse_fk(tmp_path):
    """purchase_order.deliver_warehouse_id must declare an FK against warehouse."""
    wiki = _build_combined_wiki(tmp_path)
    args = _build_args(tmp_path, wiki)
    _run(args)

    ddl = _combined_ddl(args).lower()
    assert re.search(
        r"foreign key\s*\(\s*deliver_warehouse_id\s*\)\s*references\s+(\w+\.)?warehouse\b",
        ddl,
    ), "purchase_order.deliver_warehouse_id did not resolve to FK → warehouse"


def test_growth22b_purchase_order_requester_fk(tmp_path):
    """purchase_order.requester_user_id must declare an FK against app_user."""
    wiki = _build_combined_wiki(tmp_path)
    args = _build_args(tmp_path, wiki)
    _run(args)

    ddl = _combined_ddl(args).lower()
    assert re.search(
        r"foreign key\s*\(\s*requester_user_id\s*\)\s*references\s+(\w+\.)?app_user\b",
        ddl,
    ), "purchase_order.requester_user_id did not resolve to FK → app_user"


def test_growth22b_goods_receipt_warehouse_fk(tmp_path):
    """goods_receipt.warehouse_id must declare an FK against warehouse."""
    wiki = _build_combined_wiki(tmp_path)
    args = _build_args(tmp_path, wiki)
    _run(args)

    ddl = _combined_ddl(args).lower()
    assert re.search(
        r"foreign key\s*\(\s*warehouse_id\s*\)\s*references\s+(\w+\.)?warehouse\b",
        ddl,
    ), "goods_receipt.warehouse_id did not resolve to FK → warehouse"


def test_growth22b_combined_scaffold_runs_through_stage4(tmp_path):
    wiki = _build_combined_wiki(tmp_path)
    args = _build_args(tmp_path, wiki)
    _run(args)

    report = (args.out_dir / "scaffold-report.md").read_text(encoding="utf-8")
    for stage in ("stage1", "stage2", "stage3", "stage4"):
        assert stage in report, f"{stage} missing from scaffold-report"
