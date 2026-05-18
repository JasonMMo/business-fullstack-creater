# tests/test_typedef_merger.py
"""TDD tests for scripts/typedef_merger.py — Phase F Task 3."""
import pathlib
import shutil

import pytest

# scripts/ is on sys.path via root conftest.py
from typedef_merger import merge_service

FIXTURE = pathlib.Path(__file__).parent / "fixtures" / "typedefinition_min.xml"


# ---------------------------------------------------------------------------
# Test 1: new <Service> entry appended before </Services>
# ---------------------------------------------------------------------------

def test_merge_appends_service_before_services_close(tmp_path):
    dst = tmp_path / "typedefinition.xml"
    shutil.copy(FIXTURE, dst)

    merge_service(dst, prefixid="order", url="./order/")
    text = dst.read_text(encoding="utf-8")

    assert '<Service prefixid="order" type="form" url="./order/"' in text
    assert 'cachelevel="session"' in text
    assert text.index('prefixid="order"') < text.index("</Services>")
    # pre-existing entry not destroyed
    assert '<Service prefixid="frame"' in text


# ---------------------------------------------------------------------------
# Test 2: idempotent — second call with same prefixid is a no-op
# ---------------------------------------------------------------------------

def test_idempotent_same_prefixid_is_noop(tmp_path):
    dst = tmp_path / "typedefinition.xml"
    shutil.copy(FIXTURE, dst)

    merge_service(dst, prefixid="order", url="./order/")
    snapshot = dst.read_bytes()

    merge_service(dst, prefixid="order", url="./order/")
    assert dst.read_bytes() == snapshot, "second call mutated the file"


# ---------------------------------------------------------------------------
# Test 3: different prefixid appends a second entry
# ---------------------------------------------------------------------------

def test_different_prefixid_appends_second_entry(tmp_path):
    dst = tmp_path / "typedefinition.xml"
    shutil.copy(FIXTURE, dst)

    merge_service(dst, prefixid="order", url="./order/")
    merge_service(dst, prefixid="customer", url="./customer/")
    text = dst.read_text(encoding="utf-8")

    assert 'prefixid="order"' in text
    assert 'prefixid="customer"' in text
    close_idx = text.index("</Services>")
    assert text.index('prefixid="order"') < close_idx
    assert text.index('prefixid="customer"') < close_idx


# ---------------------------------------------------------------------------
# Test 4: missing </Services> raises RuntimeError
# ---------------------------------------------------------------------------

def test_missing_services_close_raises(tmp_path):
    broken = tmp_path / "typedefinition_broken.xml"
    broken.write_text(
        '<?xml version="1.0" encoding="utf-8"?>\n<TypeDefinition version="3.0">\n</TypeDefinition>\n',
        encoding="utf-8",
    )

    with pytest.raises(RuntimeError) as exc_info:
        merge_service(broken, prefixid="order", url="./order/")

    assert "</Services>" in str(exc_info.value)


# ---------------------------------------------------------------------------
# Test 5: custom cachelevel is written correctly
# ---------------------------------------------------------------------------

def test_custom_cachelevel(tmp_path):
    dst = tmp_path / "typedefinition.xml"
    shutil.copy(FIXTURE, dst)

    merge_service(dst, prefixid="order", url="./order/", cachelevel="none")
    text = dst.read_text(encoding="utf-8")

    assert 'cachelevel="none"' in text
