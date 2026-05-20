# tests/golden/test_growth21b3_sales_cross_domain.py
"""Growth-21b-3 — 영업관리 × 고객관리 × 권한관리 cross-domain FK 점검.

The orchestrator's `wiki_mode="preset"` path can only expand ONE preset
per scaffold. To exercise cross-domain references this test pre-builds
a combined wiki directory by invoking `_init_wiki_from_preset` three
times into the same destination, then runs the scaffold with
`wiki_mode="wiki"` pointing at the merged tree.

Goals (discovery + locking):
  1. Combined Stage 1 compile produces a single blueprint covering ALL
     three domains (customer/role/user/opportunity/...).
  2. Stage 2 DDL emits CREATE TABLEs for representatives of each domain.
  3. opportunity.customer_id resolves to a real FK against customer.
  4. opportunity.owner_user_id resolves to a real FK against app_user.
  5. The combined scaffold still runs cleanly through Stage 4.

If any assertion fails this becomes the next backlog item (multi-preset
orchestrator support or seed FK declaration gap). Test is intentionally
strict so we surface gaps loudly.

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

PRESETS = ("고객관리", "권한관리", "영업관리")


def _build_combined_wiki(tmp_path):
    """Expand 3 presets into a single wiki directory."""
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
        domain="영업관리+고객관리+권한관리",
        domain_slug="crm_bundle",
        wiki_mode="wiki",
        preset=None,
        wiki_path=wiki_dir,
        lane="nexacro",
        default_pattern="D2",
        package="com.example.crmbundle",
        out_dir=tmp_path / "scaffold-out",
        creator_root=CREATOR,
        stop_after_stage=4,
        dialect="hsqldb",
        service_name="CrmBundle",
    )


def _run(args):
    from scaffold_orchestrator import run_scaffold, StageFailure  # noqa: PLC0415

    try:
        run_scaffold(args)
    except StageFailure as exc:
        pytest.fail(f"StageFailure during cross-domain scaffold: {exc}")


def _combined_ddl(args):
    ddl_dir = args.out_dir / "2-ddl"
    return "\n".join(p.read_text(encoding="utf-8") for p in ddl_dir.rglob("*.sql"))


def test_growth21b3_combined_wiki_compiles_three_domains(tmp_path):
    """All 3 domains' entities must land in the merged blueprint."""
    wiki = _build_combined_wiki(tmp_path)
    args = _build_args(tmp_path, wiki)
    _run(args)

    bp = (args.out_dir / "1-wiki" / "_blueprint.yaml").read_text(encoding="utf-8")
    # One representative entity from each domain
    for entity in ("customer", "app_user", "opportunity"):
        assert entity in bp, (
            f"blueprint missing `{entity}` — combined wiki failed to merge"
        )


def test_growth21b3_stage2_ddl_has_all_three_domains(tmp_path):
    wiki = _build_combined_wiki(tmp_path)
    args = _build_args(tmp_path, wiki)
    _run(args)

    ddl = _combined_ddl(args).lower()
    for table in ("customer", "app_user", "role", "lead", "opportunity",
                  "sales_activity", "contact_person"):
        assert table in ddl, f"DDL missing table `{table}`"


def test_growth21b3_opportunity_customer_fk_resolves(tmp_path):
    """opportunity.customer_id must declare an FK against customer when
    both tables coexist in the same scaffold.
    """
    wiki = _build_combined_wiki(tmp_path)
    args = _build_args(tmp_path, wiki)
    _run(args)

    ddl = _combined_ddl(args).lower()
    assert "customer_id" in ddl
    # Accept any schema-qualified form: "references customer" or
    # "references <schema>.customer". The opportunity FK must point at customer.
    import re
    assert re.search(r"foreign key\s*\(\s*customer_id\s*\)\s*references\s+(\w+\.)?customer\b", ddl), (
        "opportunity.customer_id did not resolve to FK → customer. "
        "Cross-domain concept-derived relation failed to emit constraint."
    )


def test_growth21b3_opportunity_owner_fk_resolves(tmp_path):
    """opportunity.owner_user_id must declare an FK against app_user."""
    wiki = _build_combined_wiki(tmp_path)
    args = _build_args(tmp_path, wiki)
    _run(args)

    ddl = _combined_ddl(args).lower()
    assert "owner_user_id" in ddl
    import re
    assert re.search(r"foreign key\s*\(\s*owner_user_id\s*\)\s*references\s+(\w+\.)?app_user\b", ddl), (
        "opportunity.owner_user_id did not resolve to FK → app_user. "
        "RBAC ownership guard will not work at the DB layer."
    )


def test_growth21b3_combined_scaffold_runs_through_stage4(tmp_path):
    """End-to-end smoke: combined wiki survives Stages 1-4."""
    wiki = _build_combined_wiki(tmp_path)
    args = _build_args(tmp_path, wiki)
    _run(args)

    report = (args.out_dir / "scaffold-report.md").read_text(encoding="utf-8")
    for stage in ("stage1", "stage2", "stage3", "stage4"):
        assert stage in report, f"{stage} missing from scaffold-report"
