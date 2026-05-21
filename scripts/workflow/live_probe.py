"""Live probe — POST a nexacro envelope to the runner, parse verdict.

The full-test L4 layer needs three signals from the live WAS:
  1. HTTP 200 (transport-level ok)
  2. ErrorCode=0 in the nexacro Parameters block (handler-level ok)
  3. At least one Row in the response Dataset (seed data actually loaded)

All three must hold for `ok=True`. Two of three → partial WAS verdict (the
caller can map this onto the "라이브 WAS 부분검증" label).
"""
from __future__ import annotations
import re
import urllib.error
import urllib.request as urllib_request
from dataclasses import dataclass
from typing import Optional


_NEXACRO_NS = "http://www.nexacroplatform.com/platform/dataset"

_ERROR_CODE_RE = re.compile(
    r'<Parameter[^>]*\bid="ErrorCode"[^>]*>([^<]+)</Parameter>'
)
_ROW_RE = re.compile(r'<Row(?:\s|>)')


def build_envelope(
    operation: str = "select_datalist_map",
    search_params: Optional[dict] = None,
) -> str:
    """Build a minimal nexacro dsSearch envelope (default: empty search)."""
    sp = search_params or {}
    if sp:
        columns = "".join(
            f'<Column id="{k}" type="STRING" size="40"/>' for k in sp
        )
        cols = "".join(f'<Col id="{k}">{v}</Col>' for k, v in sp.items())
        rows = f"<Row>{cols}</Row>"
    else:
        columns = '<Column id="dummy" type="STRING" size="1"/>'
        rows = ""
    return (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        f'<Root xmlns="{_NEXACRO_NS}">\n'
        '  <Parameters/>\n'
        '  <Dataset id="dsSearch">\n'
        f'    <ColumnInfo>{columns}</ColumnInfo>\n'
        f'    <Rows>{rows}</Rows>\n'
        '  </Dataset>\n'
        '</Root>\n'
    )


@dataclass
class ProbeResult:
    http_status: int
    error_code: int = -999
    row_count: int = 0
    ok: bool = False
    raw: str = ""


def parse_response(xml_text: str, http_status: int) -> ProbeResult:
    """HTTP 200 + ErrorCode=0 + >=1 Row → ok=True."""
    if http_status != 200:
        return ProbeResult(http_status=http_status, raw=xml_text)
    m = _ERROR_CODE_RE.search(xml_text)
    try:
        error_code = int(m.group(1).strip()) if m else -999
    except ValueError:
        error_code = -999
    row_count = len(_ROW_RE.findall(xml_text))
    ok = (error_code == 0 and row_count >= 1)
    return ProbeResult(
        http_status=http_status,
        error_code=error_code,
        row_count=row_count,
        ok=ok,
        raw=xml_text,
    )


def probe_endpoint(
    url: str,
    envelope: Optional[str] = None,
    timeout_sec: float = 30.0,
) -> ProbeResult:
    """POST nexacro envelope to URL, return parsed verdict.

    Connection errors collapse to http_status=0 (caller treats as L4 FAIL).
    HTTP-level errors (4xx/5xx) preserve the status code and attempt to parse
    any response body — useful for inspecting ErrorCode in 500 responses.
    """
    body = (envelope or build_envelope()).encode("utf-8")
    req = urllib_request.Request(
        url,
        data=body,
        headers={
            "Content-Type": "text/xml;charset=utf-8",
            "User-Agent": "live-probe/0.1",
        },
        method="POST",
    )
    try:
        with urllib_request.urlopen(req, timeout=timeout_sec) as resp:
            status = getattr(resp, "status", 200)
            text = resp.read().decode("utf-8", errors="replace")
            return parse_response(text, http_status=status)
    except urllib.error.HTTPError as e:
        text = ""
        try:
            text = e.read().decode("utf-8", errors="replace") if e.fp else ""
        except Exception:
            pass
        return parse_response(text, http_status=e.code)
    except Exception as e:
        return ProbeResult(http_status=0, raw=str(e))
