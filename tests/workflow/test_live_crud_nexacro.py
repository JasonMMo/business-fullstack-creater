"""Tests for live_crud_nexacro — envelope CRUD round-trip + envelope builders."""
from __future__ import annotations
import re
import urllib.error

import pytest

from scripts.workflow import live_crud_nexacro


# ---------- _FakeResp (urllib mocking shim) ----------

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


def _make_sequencer(responses):
    """Returns (fake_urlopen, captured) that pops responses[0] each call."""
    pending = list(responses)
    captured = []

    def fake_urlopen(req, timeout=None):
        captured.append({
            "url": req.full_url,
            "method": req.get_method(),
            "data": req.data,
            "headers": dict(req.headers),
        })
        body, status = pending.pop(0)
        return _FakeResp(body, status=status)

    return fake_urlopen, captured


def _ok_select_body(row_count: int) -> bytes:
    """Build a fake select-response with given row count and ErrorCode=0."""
    rows = "".join("<Row><Col id=\"id\">{}</Col></Row>".format(i) for i in range(row_count))
    return (
        '<?xml version="1.0" encoding="utf-8"?>'
        '<Root xmlns="http://www.nexacroplatform.com/platform/dataset">'
        '<Parameters><Parameter id="ErrorCode" type="INT">0</Parameter></Parameters>'
        f'<Dataset id="dsAccount"><Rows>{rows}</Rows></Dataset>'
        '</Root>'
    ).encode("utf-8")


def _ok_save_body() -> bytes:
    return (
        '<?xml version="1.0" encoding="utf-8"?>'
        '<Root xmlns="http://www.nexacroplatform.com/platform/dataset">'
        '<Parameters><Parameter id="ErrorCode" type="INT">0</Parameter></Parameters>'
        '</Root>'
    ).encode("utf-8")


def _err_save_body(code: int = -1) -> bytes:
    return (
        '<?xml version="1.0" encoding="utf-8"?>'
        '<Root xmlns="http://www.nexacroplatform.com/platform/dataset">'
        f'<Parameters><Parameter id="ErrorCode" type="INT">{code}</Parameter></Parameters>'
        '</Root>'
    ).encode("utf-8")


# ---------- CrudResult defaults ----------

def test_crud_result_defaults():
    r = live_crud_nexacro.CrudResult()
    assert r.baseline_count == -1
    assert r.after_insert_count == -1
    assert r.after_delete_count == -1
    assert r.insert_status == 0
    assert r.insert_error_code == -999
    assert r.delete_status == 0
    assert r.delete_error_code == -999
    assert r.ok is False
    assert r.reason == ""


# ---------- nexacro_dataset_id ----------

def test_dataset_id_snake_case():
    assert live_crud_nexacro.nexacro_dataset_id("account") == "dsAccount"


def test_dataset_id_multi_segment():
    assert live_crud_nexacro.nexacro_dataset_id("order_item") == "dsOrderItem"
    assert live_crud_nexacro.nexacro_dataset_id("shipping_address") == "dsShippingAddress"


def test_dataset_id_single_segment_already_lowercase():
    assert live_crud_nexacro.nexacro_dataset_id("lead") == "dsLead"


# ---------- nexacro_save_url ----------

def test_save_url_shape():
    assert live_crud_nexacro.nexacro_save_url(8080, "account") == \
        "http://localhost:8080/uiadapter/account/save_datalist_map.do"


def test_save_url_distinct_from_select():
    # select URL is owned by lane_runner_map.lane_probe_url; this just
    # documents the wire-protocol delta between the two endpoints.
    assert "save_datalist_map.do" in live_crud_nexacro.nexacro_save_url(8080, "x")


# ---------- build_select_envelope ----------

def test_build_select_envelope_has_dssearch_and_namespace():
    env = live_crud_nexacro.build_select_envelope()
    assert 'xmlns="http://www.nexacroplatform.com/platform/dataset"' in env
    assert '<Dataset id="dsSearch">' in env
    assert "<ColumnInfo>" in env


# ---------- build_save_envelope ----------

def test_save_envelope_insert_row_has_type_attr():
    env = live_crud_nexacro.build_save_envelope(
        "dsAccount", insert_rows=[{"id": 999001, "code": "X"}]
    )
    assert '<Dataset id="dsAccount">' in env
    assert '<Row Type="insert">' in env
    assert '<Col id="id">999001</Col>' in env
    assert '<Col id="code">X</Col>' in env
    assert '<Column id="id"' in env
    assert '<Column id="code"' in env


def test_save_envelope_delete_row_has_type_attr():
    env = live_crud_nexacro.build_save_envelope(
        "dsAccount", delete_rows=[{"id": 999001}]
    )
    assert '<Row Type="delete">' in env
    assert '<Col id="id">999001</Col>' in env


def test_save_envelope_combined_insert_and_delete():
    env = live_crud_nexacro.build_save_envelope(
        "dsAccount",
        insert_rows=[{"id": 1, "name": "A"}],
        delete_rows=[{"id": 2}],
    )
    assert env.index('<Row Type="insert">') < env.index('<Row Type="delete">')
    # ColumnInfo must include the union (id + name)
    assert '<Column id="id"' in env
    assert '<Column id="name"' in env


def test_save_envelope_null_value_emits_empty_col():
    env = live_crud_nexacro.build_save_envelope(
        "dsAccount", insert_rows=[{"id": 1, "memo": None}]
    )
    assert '<Col id="memo"/>' in env


def test_save_envelope_bool_value_lowercased():
    env = live_crud_nexacro.build_save_envelope(
        "dsAccount", insert_rows=[{"id": 1, "active": True, "deleted": False}]
    )
    assert '<Col id="active">true</Col>' in env
    assert '<Col id="deleted">false</Col>' in env


def test_save_envelope_xml_special_chars_escaped():
    env = live_crud_nexacro.build_save_envelope(
        "dsAccount", insert_rows=[{"id": 1, "name": "A & <B>"}]
    )
    assert '<Col id="name">A &amp; &lt;B&gt;</Col>' in env


def test_save_envelope_empty_when_no_rows():
    env = live_crud_nexacro.build_save_envelope("dsX")
    assert '<Dataset id="dsX">' in env
    assert '<Rows></Rows>' in env


# ---------- crud_roundtrip_envelope happy path ----------

def test_crud_roundtrip_envelope_happy_path(monkeypatch):
    """baseline=3 → insert (+1=4) → delete (back to 3) → ok=True."""
    fake, captured = _make_sequencer([
        (_ok_select_body(3), 200),   # baseline select
        (_ok_save_body(), 200),       # insert save
        (_ok_select_body(4), 200),   # verify +1
        (_ok_save_body(), 200),       # delete save
        (_ok_select_body(3), 200),   # final verify
    ])
    monkeypatch.setattr(live_crud_nexacro.urllib_request, "urlopen", fake)

    r = live_crud_nexacro.crud_roundtrip_envelope(
        select_url="http://localhost:8080/uiadapter/account/select_datalist_map.do",
        save_url="http://localhost:8080/uiadapter/account/save_datalist_map.do",
        dataset_id="dsAccount",
        insert_row={"id": 999001, "code": "X"},
        pk_column="id",
        pk_value=999001,
    )
    assert r.ok is True
    assert r.baseline_count == 3
    assert r.after_insert_count == 4
    assert r.after_delete_count == 3
    assert r.insert_status == 200 and r.insert_error_code == 0
    assert r.delete_status == 200 and r.delete_error_code == 0
    # All 5 calls are POST (envelope protocol)
    assert [c["method"] for c in captured] == ["POST"] * 5
    # The 3 select calls hit select_url, 2 save calls hit save_url
    urls = [c["url"] for c in captured]
    assert urls.count("http://localhost:8080/uiadapter/account/select_datalist_map.do") == 3
    assert urls.count("http://localhost:8080/uiadapter/account/save_datalist_map.do") == 2


def test_crud_roundtrip_envelope_baseline_select_fails(monkeypatch):
    def boom(req, timeout=None):
        raise OSError("connection refused")
    monkeypatch.setattr(live_crud_nexacro.urllib_request, "urlopen", boom)
    r = live_crud_nexacro.crud_roundtrip_envelope(
        select_url="http://localhost:8080/uiadapter/account/select_datalist_map.do",
        save_url="http://localhost:8080/uiadapter/account/save_datalist_map.do",
        dataset_id="dsAccount",
        insert_row={"id": 999001},
        pk_column="id",
        pk_value=999001,
    )
    assert r.ok is False
    assert "baseline" in r.reason.lower()


def test_crud_roundtrip_envelope_insert_errorcode_nonzero(monkeypatch):
    fake, _ = _make_sequencer([
        (_ok_select_body(2), 200),       # baseline
        (_err_save_body(-1), 200),        # insert returns ErrorCode=-1
    ])
    monkeypatch.setattr(live_crud_nexacro.urllib_request, "urlopen", fake)
    r = live_crud_nexacro.crud_roundtrip_envelope(
        select_url="http://x/select_datalist_map.do",
        save_url="http://x/save_datalist_map.do",
        dataset_id="dsAccount",
        insert_row={"id": 999001},
        pk_column="id",
        pk_value=999001,
    )
    assert r.ok is False
    assert r.insert_error_code == -1
    assert "insert" in r.reason.lower()


def test_crud_roundtrip_envelope_insert_verify_wrong_count(monkeypatch):
    fake, _ = _make_sequencer([
        (_ok_select_body(2), 200),
        (_ok_save_body(), 200),
        (_ok_select_body(2), 200),  # +1 expected but stayed at 2
    ])
    monkeypatch.setattr(live_crud_nexacro.urllib_request, "urlopen", fake)
    r = live_crud_nexacro.crud_roundtrip_envelope(
        select_url="http://x/select_datalist_map.do",
        save_url="http://x/save_datalist_map.do",
        dataset_id="dsAccount",
        insert_row={"id": 999001},
        pk_column="id",
        pk_value=999001,
    )
    assert r.ok is False
    assert "verify" in r.reason.lower()
    assert r.after_insert_count == 2


def test_crud_roundtrip_envelope_delete_errorcode_nonzero(monkeypatch):
    fake, _ = _make_sequencer([
        (_ok_select_body(2), 200),
        (_ok_save_body(), 200),
        (_ok_select_body(3), 200),
        (_err_save_body(-1), 200),     # delete fails
        (_ok_select_body(3), 200),     # still 3
    ])
    monkeypatch.setattr(live_crud_nexacro.urllib_request, "urlopen", fake)
    r = live_crud_nexacro.crud_roundtrip_envelope(
        select_url="http://x/select_datalist_map.do",
        save_url="http://x/save_datalist_map.do",
        dataset_id="dsAccount",
        insert_row={"id": 999001},
        pk_column="id",
        pk_value=999001,
    )
    assert r.ok is False
    assert r.delete_error_code == -1
    assert "delete" in r.reason.lower()


def test_crud_roundtrip_envelope_http_500_on_save(monkeypatch):
    calls = {"n": 0}

    def fake(req, timeout=None):
        calls["n"] += 1
        if calls["n"] == 1:
            return _FakeResp(_ok_select_body(0), status=200)
        raise urllib.error.HTTPError(req.full_url, 500, "boom", {}, None)

    monkeypatch.setattr(live_crud_nexacro.urllib_request, "urlopen", fake)
    r = live_crud_nexacro.crud_roundtrip_envelope(
        select_url="http://x/select_datalist_map.do",
        save_url="http://x/save_datalist_map.do",
        dataset_id="dsAccount",
        insert_row={"id": 999001},
        pk_column="id",
        pk_value=999001,
    )
    assert r.ok is False
    assert r.insert_status == 500


def test_crud_roundtrip_envelope_uses_xml_content_type(monkeypatch):
    fake, captured = _make_sequencer([
        (_ok_select_body(0), 200),
        (_ok_save_body(), 200),
        (_ok_select_body(1), 200),
        (_ok_save_body(), 200),
        (_ok_select_body(0), 200),
    ])
    monkeypatch.setattr(live_crud_nexacro.urllib_request, "urlopen", fake)
    live_crud_nexacro.crud_roundtrip_envelope(
        select_url="http://x/select_datalist_map.do",
        save_url="http://x/save_datalist_map.do",
        dataset_id="dsAccount",
        insert_row={"id": 999001},
        pk_column="id",
        pk_value=999001,
    )
    # Header keys are normalized to title-case by urllib's Request
    assert all(
        c["headers"].get("Content-type", "").startswith("text/xml")
        for c in captured
    )


def test_crud_roundtrip_envelope_insert_body_contains_payload(monkeypatch):
    fake, captured = _make_sequencer([
        (_ok_select_body(0), 200),
        (_ok_save_body(), 200),
        (_ok_select_body(1), 200),
        (_ok_save_body(), 200),
        (_ok_select_body(0), 200),
    ])
    monkeypatch.setattr(live_crud_nexacro.urllib_request, "urlopen", fake)
    live_crud_nexacro.crud_roundtrip_envelope(
        select_url="http://x/select_datalist_map.do",
        save_url="http://x/save_datalist_map.do",
        dataset_id="dsAccount",
        insert_row={"id": 999001, "code": "X"},
        pk_column="id",
        pk_value=999001,
    )
    insert_body = captured[1]["data"].decode("utf-8")
    delete_body = captured[3]["data"].decode("utf-8")
    assert '<Row Type="insert">' in insert_body
    assert '<Col id="id">999001</Col>' in insert_body
    assert '<Col id="code">X</Col>' in insert_body
    assert '<Row Type="delete">' in delete_body
    assert '<Col id="id">999001</Col>' in delete_body


def test_crud_roundtrip_envelope_baseline_errorcode_nonzero(monkeypatch):
    fake, _ = _make_sequencer([(_err_save_body(-9), 200)])
    monkeypatch.setattr(live_crud_nexacro.urllib_request, "urlopen", fake)
    r = live_crud_nexacro.crud_roundtrip_envelope(
        select_url="http://x/select_datalist_map.do",
        save_url="http://x/save_datalist_map.do",
        dataset_id="dsAccount",
        insert_row={"id": 999001},
        pk_column="id",
        pk_value=999001,
    )
    assert r.ok is False
    assert "baseline" in r.reason.lower()
