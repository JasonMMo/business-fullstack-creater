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


# ---------- Growth-36: GET + JSON probe variant (jakarta/javax/vanilla REST lanes) ----------

def test_probe_endpoint_json_ok(monkeypatch):
    captured = {}

    def fake_urlopen(req, timeout=None):
        captured["url"] = req.full_url
        captured["method"] = req.get_method()
        return _FakeResp(b'[{"id":1,"code":"A"},{"id":2,"code":"B"}]', status=200)

    monkeypatch.setattr(live_probe.urllib_request, "urlopen", fake_urlopen)
    r = live_probe.probe_endpoint_json("http://localhost:8080/api/lead")
    assert r.ok is True
    assert r.row_count == 2
    assert r.error_code == 0
    assert captured["method"] == "GET"
    assert captured["url"].endswith("/api/lead")


def test_probe_endpoint_json_zero_rows_not_ok(monkeypatch):
    monkeypatch.setattr(
        live_probe.urllib_request, "urlopen",
        lambda req, timeout=None: _FakeResp(b"[]", status=200),
    )
    r = live_probe.probe_endpoint_json("http://localhost:8080/api/lead")
    assert r.row_count == 0
    assert r.ok is False


def test_probe_endpoint_json_http_500(monkeypatch):
    import urllib.error
    def fake_urlopen(req, timeout=None):
        raise urllib.error.HTTPError(req.full_url, 500, "boom", {}, None)

    monkeypatch.setattr(live_probe.urllib_request, "urlopen", fake_urlopen)
    r = live_probe.probe_endpoint_json("http://localhost:8080/api/lead")
    assert r.http_status == 500
    assert r.ok is False


def test_probe_endpoint_json_non_list_body_not_ok(monkeypatch):
    """Stage 3 controller returns List<Map>; dict response is unexpected."""
    monkeypatch.setattr(
        live_probe.urllib_request, "urlopen",
        lambda req, timeout=None: _FakeResp(b'{"error":"oops"}', status=200),
    )
    r = live_probe.probe_endpoint_json("http://localhost:8080/api/lead")
    assert r.row_count == 0
    assert r.ok is False


# ---------- Growth-38: retry-on-transient-failure ----------

def test_probe_endpoint_retries_on_connection_error_then_succeeds(monkeypatch):
    """First call raises (post-ready transient), second call succeeds — retries=2 covers it."""
    calls = {"n": 0}
    def flaky_urlopen(req, timeout=None):
        calls["n"] += 1
        if calls["n"] == 1:
            raise OSError("connection refused")
        return _FakeResp(OK_RESPONSE.encode("utf-8"), status=200)
    monkeypatch.setattr(live_probe.urllib_request, "urlopen", flaky_urlopen)
    monkeypatch.setattr(live_probe.time, "sleep", lambda s: None)
    r = live_probe.probe_endpoint("http://localhost:8080/x", retries=2, retry_delay_sec=0.0)
    assert r.ok is True
    assert calls["n"] == 2


def test_probe_endpoint_gives_up_after_retries_exhausted(monkeypatch):
    calls = {"n": 0}
    def boom(req, timeout=None):
        calls["n"] += 1
        raise OSError("nope")
    monkeypatch.setattr(live_probe.urllib_request, "urlopen", boom)
    monkeypatch.setattr(live_probe.time, "sleep", lambda s: None)
    r = live_probe.probe_endpoint("http://localhost:8080/x", retries=3, retry_delay_sec=0.0)
    assert r.ok is False
    assert r.http_status == 0
    assert calls["n"] == 4  # initial + 3 retries


def test_probe_endpoint_json_retries_on_transient(monkeypatch):
    calls = {"n": 0}
    def flaky(req, timeout=None):
        calls["n"] += 1
        if calls["n"] < 2:
            raise OSError("not yet")
        return _FakeResp(b'[{"id":1}]', status=200)
    monkeypatch.setattr(live_probe.urllib_request, "urlopen", flaky)
    monkeypatch.setattr(live_probe.time, "sleep", lambda s: None)
    r = live_probe.probe_endpoint_json("http://localhost:8080/api/x", retries=2, retry_delay_sec=0.0)
    assert r.ok is True
    assert calls["n"] == 2


def test_probe_endpoint_no_retry_on_http_error(monkeypatch):
    """HTTPError (4xx/5xx) is a real response — don't retry, surface immediately."""
    import urllib.error
    calls = {"n": 0}
    def fake(req, timeout=None):
        calls["n"] += 1
        raise urllib.error.HTTPError(req.full_url, 500, "boom", {}, None)
    monkeypatch.setattr(live_probe.urllib_request, "urlopen", fake)
    monkeypatch.setattr(live_probe.time, "sleep", lambda s: None)
    r = live_probe.probe_endpoint("http://localhost:8080/x", retries=3, retry_delay_sec=0.0)
    assert r.http_status == 500
    assert calls["n"] == 1
