"""Tests for live_crud — REST CRUD round-trip + data.sql template auto-discovery."""
from __future__ import annotations
import json
import urllib.error
from pathlib import Path

import pytest

from scripts.workflow import live_crud


# ---------- _FakeResp (urllib mocking shim, same pattern as test_live_probe) ----------

class _FakeResp:
    def __init__(self, body: bytes, status: int = 200):
        self._body = body
        self.status = status

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


# ---------- CrudResult dataclass defaults ----------

def test_crud_result_defaults():
    r = live_crud.CrudResult()
    assert r.baseline_count == -1
    assert r.after_insert_count == -1
    assert r.after_delete_count == -1
    assert r.insert_status == 0
    assert r.delete_status == 0
    assert r.ok is False
    assert r.reason == ""


# ---------- crud_roundtrip_rest happy path ----------

def _make_sequencer(responses):
    """Returns a fake_urlopen that pops responses[0] each call."""
    pending = list(responses)
    captured = []

    def fake_urlopen(req, timeout=None):
        captured.append({
            "url": req.full_url,
            "method": req.get_method(),
            "data": req.data,
        })
        body, status = pending.pop(0)
        return _FakeResp(body, status=status)

    return fake_urlopen, captured


def test_crud_roundtrip_happy_path(monkeypatch):
    """baseline=3 → insert (+1=4) → delete (back to 3) → ok=True."""
    fake, captured = _make_sequencer([
        (b'[{"id":1},{"id":2},{"id":3}]', 200),     # baseline GET
        (b'1', 200),                                  # insert POST
        (b'[{"id":1},{"id":2},{"id":3},{"id":999001}]', 200),  # verify GET
        (b'1', 200),                                  # delete POST
        (b'[{"id":1},{"id":2},{"id":3}]', 200),     # final GET
    ])
    monkeypatch.setattr(live_crud.urllib_request, "urlopen", fake)

    r = live_crud.crud_roundtrip_rest(
        "http://localhost:8080/api/lead",
        insert_row={"id": 999001, "code": "X"},
        pk_column="id",
        pk_value=999001,
    )
    assert r.ok is True
    assert r.baseline_count == 3
    assert r.after_insert_count == 4
    assert r.after_delete_count == 3
    assert r.insert_status == 200 and r.insert_rows == 1
    assert r.delete_status == 200 and r.delete_rows == 1

    # Verify the 5 calls happened in expected order
    assert [c["method"] for c in captured] == ["GET", "POST", "GET", "POST", "GET"]

    # Insert body carries _rowType=I
    insert_body = json.loads(captured[1]["data"].decode("utf-8"))
    assert insert_body == [{"id": 999001, "code": "X", "_rowType": "I"}]

    # Delete body carries _rowType=D
    delete_body = json.loads(captured[3]["data"].decode("utf-8"))
    assert delete_body == [{"id": 999001, "_rowType": "D"}]


def test_crud_roundtrip_baseline_get_fails(monkeypatch):
    def boom(req, timeout=None):
        raise OSError("connection refused")
    monkeypatch.setattr(live_crud.urllib_request, "urlopen", boom)

    r = live_crud.crud_roundtrip_rest(
        "http://localhost:8080/api/lead",
        insert_row={"id": 999001},
        pk_column="id",
        pk_value=999001,
    )
    assert r.ok is False
    assert "baseline" in r.reason.lower()


def test_crud_roundtrip_insert_fails(monkeypatch):
    fake, _ = _make_sequencer([
        (b'[{"id":1}]', 200),  # baseline GET ok
        (b'0', 200),            # insert returns 0 rows — fail
    ])
    monkeypatch.setattr(live_crud.urllib_request, "urlopen", fake)

    r = live_crud.crud_roundtrip_rest(
        "http://localhost:8080/api/lead",
        insert_row={"id": 999001},
        pk_column="id",
        pk_value=999001,
    )
    assert r.ok is False
    assert r.insert_rows == 0
    assert "insert failed" in r.reason


def test_crud_roundtrip_insert_verify_wrong_count(monkeypatch):
    fake, _ = _make_sequencer([
        (b'[{"id":1}]', 200),       # baseline = 1
        (b'1', 200),                 # insert ok
        (b'[{"id":1}]', 200),       # but count still 1 (insert silently lost)
    ])
    monkeypatch.setattr(live_crud.urllib_request, "urlopen", fake)

    r = live_crud.crud_roundtrip_rest(
        "http://localhost:8080/api/lead",
        insert_row={"id": 999001},
        pk_column="id",
        pk_value=999001,
    )
    assert r.ok is False
    assert "verify" in r.reason.lower()
    assert r.after_insert_count == 1


def test_crud_roundtrip_delete_fails(monkeypatch):
    fake, _ = _make_sequencer([
        (b'[{"id":1}]', 200),                          # baseline = 1
        (b'1', 200),                                    # insert ok
        (b'[{"id":1},{"id":999001}]', 200),            # +1 verify ok
        (b'0', 200),                                    # delete returns 0
        (b'[{"id":1},{"id":999001}]', 200),            # still 2 — fail
    ])
    monkeypatch.setattr(live_crud.urllib_request, "urlopen", fake)

    r = live_crud.crud_roundtrip_rest(
        "http://localhost:8080/api/lead",
        insert_row={"id": 999001},
        pk_column="id",
        pk_value=999001,
    )
    assert r.ok is False
    assert r.delete_rows == 0
    assert "delete" in r.reason.lower()


def test_crud_roundtrip_http_error_on_post(monkeypatch):
    calls = {"n": 0}

    def fake_urlopen(req, timeout=None):
        calls["n"] += 1
        if calls["n"] == 1:
            return _FakeResp(b'[]', status=200)  # baseline = 0
        raise urllib.error.HTTPError(req.full_url, 500, "boom", {}, None)

    monkeypatch.setattr(live_crud.urllib_request, "urlopen", fake_urlopen)
    r = live_crud.crud_roundtrip_rest(
        "http://localhost:8080/api/lead",
        insert_row={"id": 999001},
        pk_column="id",
        pk_value=999001,
    )
    assert r.ok is False
    assert r.insert_status == 500


# ---------- _split_csv_depth0 ----------

def test_split_csv_depth0_basic():
    assert live_crud._split_csv_depth0("1, 'a', 2") == ["1", "'a'", "2"]


def test_split_csv_depth0_respects_parens():
    assert live_crud._split_csv_depth0("1, foo(2, 3), 4") == ["1", "foo(2, 3)", "4"]


def test_split_csv_depth0_respects_quoted_comma():
    assert live_crud._split_csv_depth0("1, 'a, b', 2") == ["1", "'a, b'", "2"]


def test_split_csv_depth0_escaped_single_quote():
    # SQL escapes single-quote by doubling: 'O''Brien' → O'Brien
    parts = live_crud._split_csv_depth0("1, 'O''Brien', 2")
    assert parts == ["1", "'O''Brien'", "2"]


# ---------- _coerce_value ----------

def test_coerce_value_int():
    assert live_crud._coerce_value("42") == 42


def test_coerce_value_float():
    assert live_crud._coerce_value("3.14") == 3.14


def test_coerce_value_string_literal():
    assert live_crud._coerce_value("'hello'") == "hello"


def test_coerce_value_escaped_quote():
    assert live_crud._coerce_value("'O''Brien'") == "O'Brien"


def test_coerce_value_current_timestamp():
    assert live_crud._coerce_value("CURRENT_TIMESTAMP") == "2026-05-21T12:00:00"


def test_coerce_value_current_date():
    assert live_crud._coerce_value("CURRENT_DATE") == "2026-05-21"


def test_coerce_value_true_false_null():
    assert live_crud._coerce_value("TRUE") is True
    assert live_crud._coerce_value("FALSE") is False
    assert live_crud._coerce_value("NULL") is None


# ---------- parse_merge_into ----------

SAMPLE_MERGE = """
-- Stage 2 emitted seed
MERGE INTO lead USING (VALUES(1, 'L-001', 'Acme Corp', CURRENT_TIMESTAMP))
  AS s(id, code, name, created_at) ON lead.id = s.id
  WHEN NOT MATCHED THEN INSERT (id, code, name, created_at)
  VALUES (s.id, s.code, s.name, s.created_at);

MERGE INTO lead USING (VALUES(2, 'L-002', 'Beta Inc', CURRENT_TIMESTAMP))
  AS s(id, code, name, created_at) ON lead.id = s.id
  WHEN NOT MATCHED THEN INSERT (id, code, name, created_at)
  VALUES (s.id, s.code, s.name, s.created_at);

MERGE INTO account USING (VALUES(10, 'A-001'))
  AS s(id, code) ON account.id = s.id
  WHEN NOT MATCHED THEN INSERT (id, code) VALUES (s.id, s.code);
"""


def test_parse_merge_into_lead():
    result = live_crud.parse_merge_into(SAMPLE_MERGE, "lead")
    assert result is not None
    cols, vals = result
    assert cols == ["id", "code", "name", "created_at"]
    assert vals == [1, "L-001", "Acme Corp", "2026-05-21T12:00:00"]


def test_parse_merge_into_account():
    result = live_crud.parse_merge_into(SAMPLE_MERGE, "account")
    assert result is not None
    cols, vals = result
    assert cols == ["id", "code"]
    assert vals == [10, "A-001"]


def test_parse_merge_into_unknown_returns_none():
    assert live_crud.parse_merge_into(SAMPLE_MERGE, "missing_entity") is None


def test_parse_merge_into_case_insensitive():
    text = "merge into Lead using (VALUES(1, 'x')) as s(id, code) on Lead.id = s.id"
    # Loose form — just verify regex tolerates case
    result = live_crud.parse_merge_into(text, "lead")
    assert result is not None
    cols, vals = result
    assert cols == ["id", "code"]
    assert vals == [1, "x"]


# ---------- build_insert_template ----------

def test_build_insert_template_swaps_pk(tmp_path: Path):
    sql = tmp_path / "data.sql"
    sql.write_text(SAMPLE_MERGE, encoding="utf-8")

    result = live_crud.build_insert_template(sql, "lead")
    assert result is not None
    row, pk_value = result
    assert pk_value == 999001
    assert row["id"] == 999001              # PK swapped
    assert row["code"] == "L-001"           # other fields mirror seed
    assert row["name"] == "Acme Corp"
    assert row["created_at"] == "2026-05-21T12:00:00"


def test_build_insert_template_custom_sentinel(tmp_path: Path):
    sql = tmp_path / "data.sql"
    sql.write_text(SAMPLE_MERGE, encoding="utf-8")

    result = live_crud.build_insert_template(sql, "lead", sentinel_pk=42424242)
    assert result is not None
    row, pk_value = result
    assert pk_value == 42424242
    assert row["id"] == 42424242


def test_build_insert_template_missing_file(tmp_path: Path):
    assert live_crud.build_insert_template(tmp_path / "nope.sql", "lead") is None


def test_build_insert_template_unknown_entity(tmp_path: Path):
    sql = tmp_path / "data.sql"
    sql.write_text(SAMPLE_MERGE, encoding="utf-8")
    assert live_crud.build_insert_template(sql, "ghost") is None


def test_build_insert_template_pk_column_not_in_cols(tmp_path: Path):
    sql = tmp_path / "data.sql"
    sql.write_text(SAMPLE_MERGE, encoding="utf-8")
    # lead has 'id' but not 'uuid' — function must bail
    assert live_crud.build_insert_template(sql, "lead", pk_column="uuid") is None
