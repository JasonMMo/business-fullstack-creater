# tests/test_react_overlay.py
"""Tests for scripts/react_overlay.py — v0.5 H4 skeleton."""
import json
import pathlib

import pytest

import react_overlay
import stage5_overlay  # ensures the registry is wired


def _make_out_dir(tmp: pathlib.Path) -> pathlib.Path:
    """Build a fake out_dir with a Stage 3 endpoints.json for two entities."""
    out = tmp / "out"
    mybatis = out / "3-mybatis"
    mybatis.mkdir(parents=True)
    endpoints = {
        "version": "0.1.4",
        "endpoints": {
            "customer": {
                "select_datalist_map": {
                    "method": "POST",
                    "path": "/api/customer/select_datalist_map",
                },
                "save_datalist_map": {
                    "method": "POST",
                    "path": "/api/customer/save_datalist_map",
                },
            },
            "address": {
                "select_datalist_map": {
                    "method": "POST",
                    "path": "/api/address/select_datalist_map",
                },
                "save_datalist_map": {
                    "method": "POST",
                    "path": "/api/address/save_datalist_map",
                },
            },
        },
    }
    (mybatis / "endpoints.json").write_text(
        json.dumps(endpoints), encoding="utf-8"
    )
    return out


def _entities():
    return [{"name": "customer"}, {"name": "address"}]


def test_emits_one_module_per_entity(tmp_path):
    out = _make_out_dir(tmp_path)
    target = tmp_path / "target"

    report = react_overlay.run(
        out_dir=out,
        target_dir=target,
        domain_slug="orders",
        domain_label="주문",
        service_pascal="Order",
        blueprint_entities=_entities(),
    )

    written = report["react_api_written"]
    assert len(written) == 2
    customer = target / "frontend" / "src" / "api" / "customer.ts"
    address = target / "frontend" / "src" / "api" / "address.ts"
    assert customer.exists()
    assert address.exists()


def test_emitted_module_contains_endpoint_paths(tmp_path):
    out = _make_out_dir(tmp_path)
    target = tmp_path / "target"
    react_overlay.run(
        out_dir=out,
        target_dir=target,
        domain_slug="orders",
        domain_label="주문",
        service_pascal="Order",
        blueprint_entities=_entities(),
    )
    body = (target / "frontend" / "src" / "api" / "customer.ts").read_text(
        encoding="utf-8"
    )
    assert "/api/customer/select_datalist_map" in body
    assert "/api/customer/save_datalist_map" in body
    assert "export async function selectDataListMap" in body
    assert "export async function saveDataListMap" in body


def test_conflict_scan_aborts_without_force(tmp_path):
    out = _make_out_dir(tmp_path)
    target = tmp_path / "target"
    # Pre-populate the target file
    api = target / "frontend" / "src" / "api"
    api.mkdir(parents=True)
    (api / "customer.ts").write_text("// existing user content\n", encoding="utf-8")

    with pytest.raises(RuntimeError) as exc:
        react_overlay.run(
            out_dir=out,
            target_dir=target,
            domain_slug="orders",
            domain_label="주문",
            service_pascal="Order",
            blueprint_entities=_entities(),
        )
    assert "would overwrite" in str(exc.value)
    # File must remain untouched
    assert (api / "customer.ts").read_text(encoding="utf-8") == (
        "// existing user content\n"
    )


def test_overlay_force_creates_bak_once(tmp_path):
    out = _make_out_dir(tmp_path)
    target = tmp_path / "target"
    api = target / "frontend" / "src" / "api"
    api.mkdir(parents=True)
    (api / "customer.ts").write_text("// original\n", encoding="utf-8")

    report1 = react_overlay.run(
        out_dir=out,
        target_dir=target,
        domain_slug="orders",
        domain_label="주문",
        service_pascal="Order",
        blueprint_entities=_entities(),
        overlay_force=True,
    )
    bak = api / "customer.ts.bak"
    assert bak.exists()
    assert bak.read_text(encoding="utf-8") == "// original\n"
    assert any(p.endswith("customer.ts.bak") for p in report1["backed_up"])

    # Re-run: .bak must NOT become customer.ts.bak.bak (idempotent backup)
    report2 = react_overlay.run(
        out_dir=out,
        target_dir=target,
        domain_slug="orders",
        domain_label="주문",
        service_pascal="Order",
        blueprint_entities=_entities(),
        overlay_force=True,
    )
    assert not (api / "customer.ts.bak.bak").exists()
    # Second run reports no new backup for customer.ts (already exists)
    assert not any(p.endswith("customer.ts.bak") for p in report2["backed_up"])


def test_report_shape_matches_overlay_contract(tmp_path):
    out = _make_out_dir(tmp_path)
    target = tmp_path / "target"
    report = react_overlay.run(
        out_dir=out,
        target_dir=target,
        domain_slug="orders",
        domain_label="주문",
        service_pascal="Order",
        blueprint_entities=_entities(),
    )
    # Shape parity with nexacro adapter
    for key in (
        "java_copied",
        "resources_copied",
        "xfdl_copied",
        "backed_up",
        "renamed_imports",
        "menu_warning",
        "typedef_added",
        "conflicts",
        "react_api_written",
    ):
        assert key in report, f"missing key: {key}"


def test_module_includes_export_to_csv(tmp_path):
    """Growth-8: each generated module exposes exportToCsv for RO/audit use."""
    out = _make_out_dir(tmp_path)
    target = tmp_path / "target"
    react_overlay.run(
        out_dir=out,
        target_dir=target,
        domain_slug="orders",
        domain_label="주문",
        service_pascal="Order",
        blueprint_entities=_entities(),
    )
    body = (target / "frontend" / "src" / "api" / "customer.ts").read_text(
        encoding="utf-8"
    )
    assert "export async function exportToCsv" in body
    assert "Blob" in body
    assert ".csv" in body


def test_report_records_export_helpers(tmp_path):
    """Growth-8: report exposes react_export_csv_added list."""
    out = _make_out_dir(tmp_path)
    target = tmp_path / "target"
    report = react_overlay.run(
        out_dir=out,
        target_dir=target,
        domain_slug="orders",
        domain_label="주문",
        service_pascal="Order",
        blueprint_entities=_entities(),
    )
    assert "react_export_csv_added" in report
    assert sorted(report["react_export_csv_added"]) == ["address", "customer"]


def test_md_pattern_emits_master_detail_component(tmp_path):
    """Gap 3: entity with pattern: MD generates <Pascal>MDPage.tsx."""
    out = _make_out_dir(tmp_path)
    target = tmp_path / "target"
    entities = [
        {
            "name": "sales_order",
            "pattern": "MD",
            "relations": [
                {"from": "sales_order", "to": "order_item",
                 "cardinality": "1:N", "fk": {"column": "order_id"}}
            ],
        },
        {"name": "order_item"},
    ]
    # endpoints.json must have entries to keep _fetch_module happy
    mybatis = out / "3-mybatis"
    payload = json.loads((mybatis / "endpoints.json").read_text("utf-8"))
    payload["endpoints"]["sales_order"] = {
        "select_datalist_map": {"method": "POST", "path": "/api/sales_order/select_datalist_map"},
        "save_datalist_map": {"method": "POST", "path": "/api/sales_order/save_datalist_map"},
    }
    payload["endpoints"]["order_item"] = {
        "select_datalist_map": {"method": "POST", "path": "/api/order_item/select_datalist_map"},
        "save_datalist_map": {"method": "POST", "path": "/api/order_item/save_datalist_map"},
    }
    (mybatis / "endpoints.json").write_text(json.dumps(payload), "utf-8")

    report = react_overlay.run(
        out_dir=out,
        target_dir=target,
        domain_slug="orders",
        domain_label="주문",
        service_pascal="Order",
        blueprint_entities=entities,
    )

    page = target / "frontend" / "src" / "pages" / "sales_order" / "SalesOrderMDPage.tsx"
    assert page.exists()
    body = page.read_text(encoding="utf-8")
    assert "SalesOrderMDPage" in body
    assert "from '../api/sales_order'" in body
    assert "from '../api/order_item'" in body
    assert "order_id: parentId" in body
    entries = [c for c in report["react_components_written"]
               if c["entity"] == "sales_order"]
    assert entries and entries[0]["pattern"] == "MD"


def test_tr_pattern_emits_tree_component(tmp_path):
    """Gap 3: entity with pattern: TR generates <Pascal>TreePage.tsx."""
    out = _make_out_dir(tmp_path)
    target = tmp_path / "target"
    entities = [
        {
            "name": "department",
            "pattern": "TR",
            "relations": [
                {"from": "department", "to": "department",
                 "cardinality": "self", "fk": {"column": "parent_dept_id"}}
            ],
        }
    ]
    mybatis = out / "3-mybatis"
    payload = json.loads((mybatis / "endpoints.json").read_text("utf-8"))
    payload["endpoints"]["department"] = {
        "select_datalist_map": {"method": "POST", "path": "/api/department/select_datalist_map"},
        "save_datalist_map": {"method": "POST", "path": "/api/department/save_datalist_map"},
    }
    (mybatis / "endpoints.json").write_text(json.dumps(payload), "utf-8")

    report = react_overlay.run(
        out_dir=out,
        target_dir=target,
        domain_slug="hr",
        domain_label="인사",
        service_pascal="Hr",
        blueprint_entities=entities,
    )

    page = target / "frontend" / "src" / "pages" / "department" / "DepartmentTreePage.tsx"
    assert page.exists()
    body = page.read_text(encoding="utf-8")
    assert "DepartmentTreePage" in body
    assert "buildTree" in body
    assert "parent_dept_id" in body
    assert "TreeNode" in body
    entries = [c for c in report["react_components_written"]
               if c["entity"] == "department"]
    assert entries and entries[0]["pattern"] == "TR"


def test_tr_pattern_without_self_relation_falls_back_to_parent_id(tmp_path):
    out = _make_out_dir(tmp_path)
    target = tmp_path / "target"
    entities = [{"name": "category", "pattern": "TR"}]
    mybatis = out / "3-mybatis"
    payload = json.loads((mybatis / "endpoints.json").read_text("utf-8"))
    payload["endpoints"]["category"] = {
        "select_datalist_map": {"method": "POST", "path": "/api/category/select_datalist_map"},
        "save_datalist_map": {"method": "POST", "path": "/api/category/save_datalist_map"},
    }
    (mybatis / "endpoints.json").write_text(json.dumps(payload), "utf-8")

    react_overlay.run(
        out_dir=out,
        target_dir=target,
        domain_slug="catalog",
        domain_label="카탈로그",
        service_pascal="Catalog",
        blueprint_entities=entities,
    )

    body = (target / "frontend" / "src" / "pages" / "category"
            / "CategoryTreePage.tsx").read_text(encoding="utf-8")
    assert "parent_id" in body


def test_entities_without_md_tr_pattern_skip_component_emission(tmp_path):
    out = _make_out_dir(tmp_path)
    target = tmp_path / "target"
    report = react_overlay.run(
        out_dir=out,
        target_dir=target,
        domain_slug="orders",
        domain_label="주문",
        service_pascal="Order",
        blueprint_entities=_entities(),  # plain entities, no pattern
    )
    assert report["react_components_written"] == []
    assert not (target / "frontend" / "src" / "pages").exists()


def test_md_without_one_to_many_relation_skips_component(tmp_path):
    """If MD entity has no 1:N relation, no component is emitted (graceful skip)."""
    out = _make_out_dir(tmp_path)
    target = tmp_path / "target"
    entities = [{"name": "customer", "pattern": "MD"}]  # no relations
    report = react_overlay.run(
        out_dir=out,
        target_dir=target,
        domain_slug="orders",
        domain_label="주문",
        service_pascal="Order",
        blueprint_entities=entities,
    )
    assert report["react_components_written"] == []


def test_d2_pattern_emits_grid_page(tmp_path):
    """Gap 5: D2 entity emits <Pascal>D2Page.tsx with master grid + save."""
    out = _make_out_dir(tmp_path)
    target = tmp_path / "target"
    entities = [{"name": "customer", "pattern": "D2"}]
    react_overlay.run(
        out_dir=out,
        target_dir=target,
        domain_slug="orders",
        domain_label="주문",
        service_pascal="Order",
        blueprint_entities=entities,
    )
    page = (target / "frontend" / "src" / "pages" / "customer"
            / "CustomerD2Page.tsx")
    assert page.exists()
    body = page.read_text(encoding="utf-8")
    assert "CustomerD2Page" in body
    assert "selectDataListMap" in body
    assert "saveDataListMap" in body


def test_f1_pattern_emits_form_page(tmp_path):
    """Gap 5: F1 entity emits single-record form page."""
    out = _make_out_dir(tmp_path)
    target = tmp_path / "target"
    entities = [{"name": "customer", "pattern": "F1"}]
    react_overlay.run(
        out_dir=out,
        target_dir=target,
        domain_slug="orders",
        domain_label="주문",
        service_pascal="Order",
        blueprint_entities=entities,
    )
    page = (target / "frontend" / "src" / "pages" / "customer"
            / "CustomerF1Page.tsx")
    assert page.exists()
    body = page.read_text(encoding="utf-8")
    assert "CustomerF1Page" in body
    assert "<form" in body


def test_c1_pattern_emits_card_page(tmp_path):
    """Gap 5: C1 entity emits card-grid page."""
    out = _make_out_dir(tmp_path)
    target = tmp_path / "target"
    entities = [{"name": "customer", "pattern": "C1"}]
    react_overlay.run(
        out_dir=out,
        target_dir=target,
        domain_slug="orders",
        domain_label="주문",
        service_pascal="Order",
        blueprint_entities=entities,
    )
    page = (target / "frontend" / "src" / "pages" / "customer"
            / "CustomerC1Page.tsx")
    assert page.exists()
    body = page.read_text(encoding="utf-8")
    assert "CustomerC1Page" in body
    assert "card" in body.lower()


def test_l2_pattern_emits_list_detail_page(tmp_path):
    """Gap 5: L2 entity emits left-list + right-detail page."""
    out = _make_out_dir(tmp_path)
    target = tmp_path / "target"
    entities = [{"name": "customer", "pattern": "L2"}]
    react_overlay.run(
        out_dir=out,
        target_dir=target,
        domain_slug="orders",
        domain_label="주문",
        service_pascal="Order",
        blueprint_entities=entities,
    )
    page = (target / "frontend" / "src" / "pages" / "customer"
            / "CustomerL2Page.tsx")
    assert page.exists()
    body = page.read_text(encoding="utf-8")
    assert "CustomerL2Page" in body
    assert "setSelected" in body
    assert "detail" in body.lower()


def test_ro_pattern_emits_readonly_page_with_csv(tmp_path):
    """Gap 5: RO entity emits read-only page with CSV export button."""
    out = _make_out_dir(tmp_path)
    target = tmp_path / "target"
    entities = [{"name": "customer", "pattern": "RO"}]
    react_overlay.run(
        out_dir=out,
        target_dir=target,
        domain_slug="orders",
        domain_label="주문",
        service_pascal="Order",
        blueprint_entities=entities,
    )
    page = (target / "frontend" / "src" / "pages" / "customer"
            / "CustomerROPage.tsx")
    assert page.exists()
    body = page.read_text(encoding="utf-8")
    assert "CustomerROPage" in body
    assert "exportToCsv" in body
    # RO must NOT expose save button
    assert "saveDataListMap" not in body


def test_all_seven_patterns_reported_in_components_written(tmp_path):
    """Gap 5: report.react_components_written must list all 7 supported patterns."""
    out = _make_out_dir(tmp_path)
    target = tmp_path / "target"
    # Pre-populate endpoints for the entities below
    mybatis = out / "3-mybatis"
    payload = json.loads((mybatis / "endpoints.json").read_text("utf-8"))
    for ename in ("e_d2", "e_f1", "e_c1", "e_l2", "e_ro", "e_md", "e_tr", "e_md_child"):
        payload["endpoints"][ename] = {
            "select_datalist_map": {"method": "POST", "path": f"/api/{ename}/select_datalist_map"},
            "save_datalist_map": {"method": "POST", "path": f"/api/{ename}/save_datalist_map"},
        }
    (mybatis / "endpoints.json").write_text(json.dumps(payload), "utf-8")

    entities = [
        {"name": "e_d2", "pattern": "D2"},
        {"name": "e_f1", "pattern": "F1"},
        {"name": "e_c1", "pattern": "C1"},
        {"name": "e_l2", "pattern": "L2"},
        {"name": "e_ro", "pattern": "RO"},
        {"name": "e_md", "pattern": "MD",
         "relations": [{"from": "e_md", "to": "e_md_child",
                        "cardinality": "1:N", "fk": {"column": "parent_id"}}]},
        {"name": "e_md_child"},
        {"name": "e_tr", "pattern": "TR",
         "relations": [{"from": "e_tr", "to": "e_tr",
                        "cardinality": "self", "fk": {"column": "parent_id"}}]},
    ]
    report = react_overlay.run(
        out_dir=out,
        target_dir=target,
        domain_slug="orders",
        domain_label="주문",
        service_pascal="Order",
        blueprint_entities=entities,
    )
    patterns_seen = sorted({c["pattern"] for c in report["react_components_written"]})
    assert patterns_seen == ["C1", "D2", "F1", "L2", "MD", "RO", "TR"]


def test_dispatch_via_registry(tmp_path):
    out = _make_out_dir(tmp_path)
    target = tmp_path / "target"
    report = stage5_overlay.run_overlay(
        ui="react",
        out_dir=out,
        target_dir=target,
        domain_slug="orders",
        domain_label="주문",
        service_pascal="Order",
        blueprint_entities=_entities(),
    )
    assert len(report["react_api_written"]) == 2
