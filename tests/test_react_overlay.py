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
