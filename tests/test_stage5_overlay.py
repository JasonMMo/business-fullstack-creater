# tests/test_stage5_overlay.py
"""TDD tests for scripts/stage5_overlay.py — Phase F Task 4."""
import pathlib
import shutil

import pytest

# scripts/ is on sys.path via root conftest.py
from stage5_overlay import run_overlay

GOLDEN_SCAFFOLD = (
    pathlib.Path(__file__).parent / "golden" / "fixtures" / "base_scaffold"
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_out_dir(tmp: pathlib.Path) -> pathlib.Path:
    """Build a minimal fake out_dir with 3-mybatis and 4-nexacro outputs."""
    out = tmp / "out"

    # --- Java source ---
    java_pkg = out / "3-mybatis" / "src" / "main" / "java" / "com" / "example" / "order" / "controller"
    java_pkg.mkdir(parents=True)
    (java_pkg / "OrderController.java").write_text(
        "package com.example.order.controller;\n\n"
        "import com.example.order.domain.Order;\n\n"
        "public class OrderController {}\n",
        encoding="utf-8",
    )

    # --- Resources: mybatis mapper xml ---
    mapper_dir = out / "3-mybatis" / "src" / "main" / "resources" / "mybatis" / "mapper"
    mapper_dir.mkdir(parents=True)
    (mapper_dir / "OrderMapper.xml").write_text(
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<!DOCTYPE mapper PUBLIC "-//mybatis.org//DTD Mapper 3.0//EN"\n'
        '  "http://mybatis.org/dtd/mybatis-3-mapper.dtd">\n'
        '<mapper namespace="com.example.order.mapper.OrderMapper">\n'
        '  <select id="selectAll" resultType="com.example.order.domain.Order">\n'
        "    SELECT * FROM orders\n"
        "  </select>\n"
        "</mapper>\n",
        encoding="utf-8",
    )

    # --- Resources: schema.sql and data.sql ---
    res_dir = out / "3-mybatis" / "src" / "main" / "resources"
    (res_dir / "schema.sql").write_text(
        "CREATE TABLE IF NOT EXISTS orders (id BIGINT PRIMARY KEY);\n",
        encoding="utf-8",
    )
    (res_dir / "data.sql").write_text(
        "-- seed data\n",
        encoding="utf-8",
    )

    # --- Nexacro xfdl ---
    form_dir = out / "4-nexacro" / "nxui" / "_form_"
    form_dir.mkdir(parents=True)
    (form_dir / "order.xfdl").write_text(
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<FDL version="1.7"><Form id="order"/></FDL>\n',
        encoding="utf-8",
    )

    return out


def _make_target_dir(tmp: pathlib.Path) -> pathlib.Path:
    """Copy the golden base_scaffold fixture into a fresh tmp target_dir."""
    target = tmp / "target"
    shutil.copytree(GOLDEN_SCAFFOLD, target)
    return target


# ---------------------------------------------------------------------------
# Test 1: Happy path
# ---------------------------------------------------------------------------

def test_overlay_creates_renamed_java_and_xfdl_and_menu_and_typedef(tmp_path):
    out_dir = _make_out_dir(tmp_path)
    target_dir = _make_target_dir(tmp_path)

    report = run_overlay(
        out_dir=out_dir,
        target_dir=target_dir,
        domain_slug="order",
        domain_label="주문관리",
        service_pascal="Order",
        blueprint_entities=[
            {"name": "order", "label_ko": "주문"},
            {"name": "order_item", "label_ko": "주문상품"},
        ],
    )

    # --- Java file exists and has renamed package/import ---
    java_file = (
        target_dir
        / "src" / "main" / "java" / "com" / "nexacro" / "uiadapter"
        / "order" / "controller" / "OrderController.java"
    )
    assert java_file.exists(), "Renamed java file not found"
    java_text = java_file.read_text(encoding="utf-8")
    assert "package com.nexacro.uiadapter.order.controller;" in java_text
    assert "import com.nexacro.uiadapter.order.domain.Order;" in java_text
    assert "com.example.order" not in java_text, "old package still present"

    # --- Mapper xml renamed ---
    mapper_file = (
        target_dir
        / "src" / "main" / "resources" / "mybatis" / "mapper" / "OrderMapper.xml"
    )
    assert mapper_file.exists()
    xml_text = mapper_file.read_text(encoding="utf-8")
    assert 'namespace="com.nexacro.uiadapter.order.mapper.OrderMapper"' in xml_text
    assert 'resultType="com.nexacro.uiadapter.order.domain.Order"' in xml_text

    # --- schema.sql written (base scaffold had none, just .gitkeep in resources) ---
    schema_sql = target_dir / "src" / "main" / "resources" / "schema.sql"
    assert schema_sql.exists()
    # Since base scaffold had no schema.sql, no .scaffold.bak should exist
    scaffold_bak = target_dir / "src" / "main" / "resources" / "schema.sql.scaffold.bak"
    assert not scaffold_bak.exists(), ".scaffold.bak should not exist when no prior schema.sql"

    # --- xfdl copied to domain sub-dir ---
    xfdl_file = target_dir / "nxui" / "packageN" / "order" / "order.xfdl"
    assert xfdl_file.exists(), "xfdl not copied to domain dir"

    # --- menu injection ---
    frame_login = target_dir / "nxui" / "packageN" / "frame" / "frameLogin.xfdl"
    frame_text = frame_login.read_text(encoding="utf-8")
    assert '<Col id="menuId">BIZ_ORDER</Col>' in frame_text, "domain group row missing"
    assert '<Col id="menuId">BIZ_ORDER_ORDER</Col>' in frame_text, "order entity row missing"
    assert '<Col id="menuId">BIZ_ORDER_ORDER_ITEM</Col>' in frame_text, "order_item entity row missing"

    # --- frameLogin.xfdl.bak created ---
    assert (target_dir / "nxui" / "packageN" / "frame" / "frameLogin.xfdl.bak").exists()

    # --- typedefinition updated ---
    typedef_file = target_dir / "nxui" / "packageN" / "typedefinition.xml"
    typedef_text = typedef_file.read_text(encoding="utf-8")
    assert 'prefixid="order"' in typedef_text
    assert 'url="./order/"' in typedef_text

    # --- typedefinition.xml.bak created ---
    assert (target_dir / "nxui" / "packageN" / "typedefinition.xml.bak").exists()

    # --- Report fields ---
    assert len(report["java_copied"]) >= 1
    assert report["typedef_added"] is True
    assert report["menu_warning"] is None
    assert report["renamed_imports"] >= 1


# ---------------------------------------------------------------------------
# Test 2: Idempotent — second overlay is safe
# ---------------------------------------------------------------------------

def test_idempotent_second_overlay_is_safe(tmp_path):
    out_dir = _make_out_dir(tmp_path)
    target_dir = _make_target_dir(tmp_path)

    _kwargs = dict(
        out_dir=out_dir,
        target_dir=target_dir,
        domain_slug="order",
        domain_label="주문관리",
        service_pascal="Order",
        blueprint_entities=[
            {"name": "order", "label_ko": "주문"},
            {"name": "order_item", "label_ko": "주문상품"},
        ],
        overlay_force=True,  # force so second run doesn't raise conflict
    )

    run_overlay(**_kwargs)

    # Snapshot key files after first run
    frame_login = target_dir / "nxui" / "packageN" / "frame" / "frameLogin.xfdl"
    typedef_file = target_dir / "nxui" / "packageN" / "typedefinition.xml"
    frame_bak = target_dir / "nxui" / "packageN" / "frame" / "frameLogin.xfdl.bak"
    typedef_bak = target_dir / "nxui" / "packageN" / "typedefinition.xml.bak"

    snap_frame = frame_login.read_bytes()
    snap_typedef = typedef_file.read_bytes()
    snap_frame_bak = frame_bak.read_bytes()
    snap_typedef_bak = typedef_bak.read_bytes()

    # Second run
    run_overlay(**_kwargs)

    assert frame_login.read_bytes() == snap_frame, "frameLogin.xfdl mutated on second run"
    assert typedef_file.read_bytes() == snap_typedef, "typedefinition.xml mutated on second run"
    assert frame_bak.read_bytes() == snap_frame_bak, "frameLogin.xfdl.bak overwritten on second run"
    assert typedef_bak.read_bytes() == snap_typedef_bak, "typedefinition.xml.bak overwritten on second run"


# ---------------------------------------------------------------------------
# Test 3: Conflict without force raises listing files
# ---------------------------------------------------------------------------

def test_conflict_without_force_raises_listing_files(tmp_path):
    out_dir = _make_out_dir(tmp_path)
    target_dir = _make_target_dir(tmp_path)

    # Pre-create a conflicting java file
    conflict_java = (
        target_dir
        / "src" / "main" / "java" / "com" / "nexacro" / "uiadapter"
        / "order" / "controller" / "OrderController.java"
    )
    conflict_java.parent.mkdir(parents=True, exist_ok=True)
    conflict_java.write_text("// placeholder\n", encoding="utf-8")

    with pytest.raises(RuntimeError) as exc_info:
        run_overlay(
            out_dir=out_dir,
            target_dir=target_dir,
            domain_slug="order",
            domain_label="주문관리",
            service_pascal="Order",
            blueprint_entities=[{"name": "order", "label_ko": "주문"}],
        )

    msg = str(exc_info.value)
    assert msg.startswith("Stage 5 overlay would overwrite"), f"unexpected message: {msg}"
    # Must list the conflict path
    assert "OrderController.java" in msg, "conflict path not listed in error"


# ---------------------------------------------------------------------------
# Test 4: Conflict with force creates .bak and overwrites
# ---------------------------------------------------------------------------

def test_conflict_with_force_creates_bak_and_overwrites(tmp_path):
    out_dir = _make_out_dir(tmp_path)
    target_dir = _make_target_dir(tmp_path)

    conflict_java = (
        target_dir
        / "src" / "main" / "java" / "com" / "nexacro" / "uiadapter"
        / "order" / "controller" / "OrderController.java"
    )
    conflict_java.parent.mkdir(parents=True, exist_ok=True)
    old_content = "// placeholder old content\n"
    conflict_java.write_text(old_content, encoding="utf-8")

    run_overlay(
        out_dir=out_dir,
        target_dir=target_dir,
        domain_slug="order",
        domain_label="주문관리",
        service_pascal="Order",
        blueprint_entities=[{"name": "order", "label_ko": "주문"}],
        overlay_force=True,
    )

    bak_file = conflict_java.with_suffix(".java.bak")
    assert bak_file.exists(), ".bak file not created"
    assert bak_file.read_text(encoding="utf-8") == old_content, ".bak has wrong content"

    new_content = conflict_java.read_text(encoding="utf-8")
    assert "com.nexacro.uiadapter.order.controller" in new_content, "new package rename not applied"
    assert old_content not in new_content, "old content still present"


# ---------------------------------------------------------------------------
# Test 5: Schema mismatch skips menu only, other steps continue
# ---------------------------------------------------------------------------

def test_schema_mismatch_skips_menu_only(tmp_path):
    out_dir = _make_out_dir(tmp_path)
    target_dir = _make_target_dir(tmp_path)

    # Remove the 'auth' column from frameLogin.xfdl to trigger SchemaMismatch
    frame_login = target_dir / "nxui" / "packageN" / "frame" / "frameLogin.xfdl"
    original = frame_login.read_text(encoding="utf-8")
    stripped = original.replace(
        '          <Column id="auth" type="STRING" size="256"/>\n', ""
    )
    frame_login.write_text(stripped, encoding="utf-8")
    # Verify auth is gone
    assert "auth" not in frame_login.read_text(encoding="utf-8")

    # Should NOT raise
    report = run_overlay(
        out_dir=out_dir,
        target_dir=target_dir,
        domain_slug="order",
        domain_label="주문관리",
        service_pascal="Order",
        blueprint_entities=[
            {"name": "order", "label_ko": "주문"},
            {"name": "order_item", "label_ko": "주문상품"},
        ],
    )

    # menu_warning must describe schema mismatch
    assert report["menu_warning"] is not None, "menu_warning should be set"
    warning = report["menu_warning"]
    assert "schema mismatch" in warning.lower() or "mismatch" in warning, f"expected 'mismatch' in warning: {warning}"
    assert "auth" in warning, f"'auth' missing from warning: {warning}"
    assert "target ColumnInfo" in warning, f"'target ColumnInfo' missing: {warning}"

    # typedef step still ran
    assert report["typedef_added"] is True, "typedef step should have run"

    # Java file was created
    java_file = (
        target_dir
        / "src" / "main" / "java" / "com" / "nexacro" / "uiadapter"
        / "order" / "controller" / "OrderController.java"
    )
    assert java_file.exists(), "Java file should exist even when menu injection fails"

    # frameLogin was NOT modified — still missing 'auth', no new menuId rows
    frame_text = frame_login.read_text(encoding="utf-8")
    assert "auth" not in frame_text, "auth column should still be absent"
    assert "BIZ_ORDER" not in frame_text, "menu rows should not have been injected"


# ---------------------------------------------------------------------------
# Test 6: Custom package prefixes (v0.4.2 G1) — non-default source + target
# ---------------------------------------------------------------------------

def _make_out_dir_custom_source(tmp: pathlib.Path) -> pathlib.Path:
    """Same as _make_out_dir but Stage 3 java tree is rooted at io/foo/bar/shop."""
    out = tmp / "out"
    java_pkg = (
        out / "3-mybatis" / "src" / "main" / "java"
        / "io" / "foo" / "bar" / "shop" / "controller"
    )
    java_pkg.mkdir(parents=True)
    (java_pkg / "ShopController.java").write_text(
        "package io.foo.bar.shop.controller;\n\n"
        "import io.foo.bar.shop.domain.Shop;\n\n"
        "public class ShopController {}\n",
        encoding="utf-8",
    )
    mapper_dir = out / "3-mybatis" / "src" / "main" / "resources" / "mybatis" / "mapper"
    mapper_dir.mkdir(parents=True)
    (mapper_dir / "ShopMapper.xml").write_text(
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<mapper namespace="io.foo.bar.shop.mapper.ShopMapper">\n'
        '  <select id="selectAll" resultType="io.foo.bar.shop.domain.Shop">\n'
        "    SELECT * FROM shops\n"
        "  </select>\n"
        "</mapper>\n",
        encoding="utf-8",
    )
    res_dir = out / "3-mybatis" / "src" / "main" / "resources"
    (res_dir / "schema.sql").write_text("CREATE TABLE shops (id BIGINT);\n", encoding="utf-8")
    (res_dir / "data.sql").write_text("-- seed\n", encoding="utf-8")
    form_dir = out / "4-nexacro" / "nxui" / "_form_"
    form_dir.mkdir(parents=True)
    (form_dir / "shop.xfdl").write_text(
        '<?xml version="1.0" encoding="utf-8"?>\n<FDL/>\n', encoding="utf-8"
    )
    return out


def test_custom_prefixes_route_java_to_target_path(tmp_path):
    """v0.4.2: source_pkg_prefix + target_pkg_prefix must route java files
    from io.foo.bar.<slug> → io.acme.uiadapter.<slug>."""
    out_dir = _make_out_dir_custom_source(tmp_path)
    target_dir = _make_target_dir(tmp_path)

    report = run_overlay(
        out_dir=out_dir,
        target_dir=target_dir,
        domain_slug="shop",
        domain_label="쇼핑몰",
        service_pascal="Shop",
        blueprint_entities=[{"name": "shop", "label_ko": "쇼핑몰"}],
        source_pkg_prefix="io.foo.bar",
        target_pkg_prefix="io.acme.uiadapter",
    )

    # Java lands at io/acme/uiadapter/shop/...
    java_file = (
        target_dir
        / "src" / "main" / "java"
        / "io" / "acme" / "uiadapter" / "shop" / "controller" / "ShopController.java"
    )
    assert java_file.exists(), f"Java not at custom target path: {java_file}"
    java_text = java_file.read_text(encoding="utf-8")
    assert "package io.acme.uiadapter.shop.controller;" in java_text
    assert "import io.acme.uiadapter.shop.domain.Shop;" in java_text
    assert "io.foo.bar.shop" not in java_text, "old custom source prefix still present"

    # Mapper xml rewritten too
    mapper_file = (
        target_dir / "src" / "main" / "resources" / "mybatis" / "mapper" / "ShopMapper.xml"
    )
    xml_text = mapper_file.read_text(encoding="utf-8")
    assert 'namespace="io.acme.uiadapter.shop.mapper.ShopMapper"' in xml_text
    assert 'resultType="io.acme.uiadapter.shop.domain.Shop"' in xml_text

    # No shop slug-subdir under the default com.nexacro.uiadapter prefix
    # (fixture base scaffold pre-includes com/nexacro/uiadapter/ infrastructure dirs,
    # so we check specifically that our slug 'shop' didn't leak there)
    default_shop = target_dir / "src" / "main" / "java" / "com" / "nexacro" / "uiadapter" / "shop"
    assert not default_shop.exists(), (
        f"shop slug leaked under default prefix: {default_shop}"
    )

    assert report["renamed_imports"] >= 1
    assert report["typedef_added"] is True


# ---------------------------------------------------------------------------
# Growth-8: fn_export_dataset adapter — Nexacro xjs helper for RO patterns
# ---------------------------------------------------------------------------

def test_ro_pattern_emits_export_xjs(tmp_path):
    """When any entity has pattern: RO, an Export.xjs helper is emitted."""
    out_dir = _make_out_dir(tmp_path)
    target_dir = _make_target_dir(tmp_path)

    report = run_overlay(
        out_dir=out_dir,
        target_dir=target_dir,
        domain_slug="order",
        domain_label="주문관리",
        service_pascal="Order",
        blueprint_entities=[
            {"name": "order", "label_ko": "주문"},
            {"name": "order_status_history", "label_ko": "주문상태이력", "pattern": "RO"},
        ],
    )

    export_xjs = target_dir / "nxui" / "packageN" / "order" / "Export.xjs"
    assert export_xjs.exists(), "Export.xjs should be emitted when an RO entity exists"
    body = export_xjs.read_text(encoding="utf-8")
    assert "fn_export_dataset" in body
    assert "saveCSV" in body
    assert report.get("nexacro_export_emitted") == "nxui/packageN/order/Export.xjs"


def test_no_ro_pattern_skips_export_xjs(tmp_path):
    """Without any RO entity, no Export.xjs is emitted."""
    out_dir = _make_out_dir(tmp_path)
    target_dir = _make_target_dir(tmp_path)

    report = run_overlay(
        out_dir=out_dir,
        target_dir=target_dir,
        domain_slug="order",
        domain_label="주문관리",
        service_pascal="Order",
        blueprint_entities=[{"name": "order", "label_ko": "주문"}],
    )

    export_xjs = target_dir / "nxui" / "packageN" / "order" / "Export.xjs"
    assert not export_xjs.exists(), "Export.xjs must not be emitted without RO entities"
    assert report.get("nexacro_export_emitted") is None
