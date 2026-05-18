# tests/test_menu_injector.py
"""TDD tests for scripts/menu_injector.py — Phase F Task 2."""
import pathlib
import shutil

import pytest

# scripts/ is on sys.path via root conftest.py
from menu_injector import REQUIRED_COLUMNS, SchemaMismatch, inject_menu_rows

FIXTURE = pathlib.Path(__file__).parent / "fixtures" / "frameLogin_min.xfdl"


# ---------------------------------------------------------------------------
# Test 1: rows appended before </Rows>
# ---------------------------------------------------------------------------

def test_inject_appends_rows_before_rows_close(tmp_path):
    dst = tmp_path / "frameLogin.xfdl"
    shutil.copy(FIXTURE, dst)

    inject_menu_rows(
        dst,
        domain_id="BIZ_ORDER",
        domain_label="주문관리",
        domain_sort=10,
        entries=[
            ("order",      "주문",     "order::order.xfdl"),
            ("order_item", "주문상품", "order::order_item.xfdl"),
        ],
    )
    text = dst.read_text(encoding="utf-8")

    # group row added
    assert '<Col id="menuId">BIZ_ORDER</Col>' in text, "group row menuId missing"
    # entity rows added
    assert '<Col id="menuId">BIZ_ORDER_ORDER</Col>' in text, "entity row ORDER missing"
    assert '<Col id="menuUrl">order::order.xfdl</Col>' in text, "entity url missing"
    # slug uppercased
    assert '<Col id="menuId">BIZ_ORDER_ORDER_ITEM</Col>' in text, "entity row ORDER_ITEM missing"
    # original sample row not destroyed
    assert '<Col id="menuId">SA00000005</Col>' in text, "original row destroyed"
    # inserted rows appear BEFORE </Rows>
    assert text.index("BIZ_ORDER_ORDER") < text.index("</Rows>"), "rows not before </Rows>"


# ---------------------------------------------------------------------------
# Test 2: idempotent — second call is a no-op
# ---------------------------------------------------------------------------

def test_idempotent_second_call_is_noop(tmp_path):
    dst = tmp_path / "frameLogin.xfdl"
    shutil.copy(FIXTURE, dst)

    kwargs = dict(
        domain_id="BIZ_ORDER",
        domain_label="주문관리",
        domain_sort=10,
        entries=[
            ("order",      "주문",     "order::order.xfdl"),
            ("order_item", "주문상품", "order::order_item.xfdl"),
        ],
    )

    inject_menu_rows(dst, **kwargs)
    snapshot = dst.read_bytes()

    inject_menu_rows(dst, **kwargs)
    assert dst.read_bytes() == snapshot, "second call mutated the file"


# ---------------------------------------------------------------------------
# Test 3: SchemaMismatch raised when a required column is absent
# ---------------------------------------------------------------------------

def test_schema_mismatch_raises_with_both_lists(tmp_path):
    # Build a variant fixture without the 'auth' column
    original = FIXTURE.read_text(encoding="utf-8")
    stripped = original.replace(
        '          <Column id="auth" type="STRING" size="256"/>\n', ""
    )
    dst = tmp_path / "frameLogin_no_auth.xfdl"
    dst.write_text(stripped, encoding="utf-8")

    with pytest.raises(SchemaMismatch) as exc_info:
        inject_menu_rows(
            dst,
            domain_id="BIZ_ORDER",
            domain_label="주문관리",
            domain_sort=10,
            entries=[("order", "주문", "order::order.xfdl")],
        )

    exc = exc_info.value
    # target_cols should be the 8-column list (no 'auth')
    assert "auth" not in exc.target_cols, "auth should be absent from target_cols"
    assert len(exc.target_cols) == 8, f"expected 8 cols, got {exc.target_cols}"
    # required should match REQUIRED_COLUMNS exactly
    assert exc.required == REQUIRED_COLUMNS, "required attribute mismatch"
    # message must contain expected phrases
    msg = str(exc)
    assert "target ColumnInfo" in msg, "'target ColumnInfo' missing from message"
    assert "required by tool" in msg, "'required by tool' missing from message"
    assert "missing" in msg, "'missing' missing from message"
    assert "auth" in msg, "'auth' missing from message"


# ---------------------------------------------------------------------------
# Test 4: RuntimeError when dsSample Dataset not found
# ---------------------------------------------------------------------------

def test_missing_dataset_raises_runtime_error(tmp_path):
    tiny = tmp_path / "no_dataset.xfdl"
    tiny.write_text(
        '<?xml version="1.0" encoding="utf-8"?>\n<FDL version="1.7">\n</FDL>\n',
        encoding="utf-8",
    )

    with pytest.raises(RuntimeError) as exc_info:
        inject_menu_rows(
            tiny,
            domain_id="BIZ_ORDER",
            domain_label="주문관리",
            domain_sort=10,
            entries=[],
        )

    assert "dsSample" in str(exc_info.value), "RuntimeError should mention 'dsSample'"
