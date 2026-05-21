"""Tests for live_probe — nexacro envelope POST + response verdict."""
from __future__ import annotations
import pytest

from scripts.workflow import live_probe


# ---------- envelope builder ----------

def test_build_envelope_has_root_xmlns_and_dssearch():
    xml = live_probe.build_envelope()
    assert "<Root" in xml
    assert 'xmlns="http://www.nexacroplatform.com/platform/dataset"' in xml
    assert 'id="dsSearch"' in xml


def test_build_envelope_with_search_params_emits_row():
    xml = live_probe.build_envelope(search_params={"id": "1"})
    assert '<Column id="id"' in xml
    assert '<Col id="id">1</Col>' in xml


# ---------- parse_response ----------

OK_RESPONSE = """<?xml version="1.0" encoding="utf-8"?>
<Root xmlns="http://www.nexacroplatform.com/platform/dataset">
  <Parameters>
    <Parameter id="ErrorCode" type="int">0</Parameter>
    <Parameter id="ErrorMsg" type="string">success</Parameter>
  </Parameters>
  <Dataset id="dsList">
    <ColumnInfo><Column id="id" type="STRING" size="40"/></ColumnInfo>
    <Rows>
      <Row><Col id="id">1</Col></Row>
      <Row><Col id="id">2</Col></Row>
    </Rows>
  </Dataset>
</Root>
"""


def test_parse_response_ok():
    r = live_probe.parse_response(OK_RESPONSE, http_status=200)
    assert r.http_status == 200
    assert r.error_code == 0
    assert r.row_count == 2
    assert r.ok is True


def test_parse_response_error_code_nonzero():
    xml = (
        '<Root xmlns="http://www.nexacroplatform.com/platform/dataset">'
        '<Parameters><Parameter id="ErrorCode" type="int">-1</Parameter></Parameters>'
        '</Root>'
    )
    r = live_probe.parse_response(xml, http_status=200)
    assert r.error_code == -1
    assert r.ok is False


def test_parse_response_http_error():
    r = live_probe.parse_response("", http_status=500)
    assert r.http_status == 500
    assert r.ok is False


def test_parse_response_zero_rows_is_not_ok():
    """ErrorCode=0 but empty Rows means seeds didn't load — not ok."""
    xml = (
        '<Root xmlns="http://www.nexacroplatform.com/platform/dataset">'
        '<Parameters><Parameter id="ErrorCode" type="int">0</Parameter></Parameters>'
        '<Dataset id="dsList"><Rows></Rows></Dataset>'
        '</Root>'
    )
    r = live_probe.parse_response(xml, http_status=200)
    assert r.error_code == 0
    assert r.row_count == 0
    assert r.ok is False


# ---------- probe_endpoint (urllib mocked) ----------

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


def test_probe_endpoint_posts_envelope_and_parses(monkeypatch):
    captured = {}

    def fake_urlopen(req, timeout=None):
        captured["url"] = req.full_url
        captured["data"] = req.data
        captured["method"] = req.get_method()
        return _FakeResp(OK_RESPONSE.encode("utf-8"), status=200)

    monkeypatch.setattr(live_probe.urllib_request, "urlopen", fake_urlopen)
    r = live_probe.probe_endpoint(
        "http://localhost:8080/uiadapter/account/select_datalist_map.do"
    )
    assert r.ok is True
    assert r.row_count == 2
    assert captured["method"] == "POST"
    assert "uiadapter/account" in captured["url"]
    assert captured["data"].startswith(b"<?xml") or captured["data"].startswith(b"<Root")


def test_probe_endpoint_returns_failure_on_connection_error(monkeypatch):
    def boom(req, timeout=None):
        raise OSError("connection refused")

    monkeypatch.setattr(live_probe.urllib_request, "urlopen", boom)
    r = live_probe.probe_endpoint("http://localhost:9999/nope")
    assert r.ok is False
    assert r.http_status == 0
