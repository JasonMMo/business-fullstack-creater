"""Live CRUD round-trip via the nexacro envelope (insert + delete over save_datalist_map.do).

Counterpart to `live_crud` (REST). Same 5-step proof — baseline list → insert →
verify +1 → delete → verify back-to-baseline — but speaks the nexacro XML wire
protocol the jakarta-for-nexacro lane actually serves.

Endpoints (per nexacro middle lane convention):
  POST /uiadapter/<entity>/select_datalist_map.do   (read; same envelope as live_probe)
  POST /uiadapter/<entity>/save_datalist_map.do     (insert/update/delete; Row Type attr)

A successful round-trip proves the controller → NexacroResult deserializer →
service → mapper → DB → NexacroResult serializer stack is intact for writes,
which the read-only L4 probe alone cannot establish.
"""
from __future__ import annotations
import re
import time
import urllib.error
import urllib.request as urllib_request
from dataclasses import dataclass
from typing import Optional


_NEXACRO_NS = "http://www.nexacroplatform.com/platform/dataset"

# Reuse live_probe's parse signals — these are the wire-protocol contract.
_ERROR_CODE_RE = re.compile(
    r'<Parameter[^>]*\bid="ErrorCode"[^>]*>([^<]+)</Parameter>'
)
_ROW_RE = re.compile(r'<Row(?:\s|>)')


@dataclass
class CrudResult:
    baseline_count: int = -1
    after_insert_count: int = -1
    after_delete_count: int = -1
    insert_status: int = 0
    insert_error_code: int = -999
    delete_status: int = 0
    delete_error_code: int = -999
    ok: bool = False
    reason: str = ""


# ---------- envelope builders ----------

def _column_info(columns: list[str]) -> str:
    return "".join(
        f'<Column id="{c}" type="STRING" size="255"/>' for c in columns
    )


def _row_cols(row: dict) -> str:
    parts = []
    for k, v in row.items():
        if v is None:
            parts.append(f'<Col id="{k}"/>')
            continue
        if isinstance(v, bool):
            text = "true" if v else "false"
        else:
            text = str(v)
        # Minimal XML escape for &, <, >
        text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        parts.append(f'<Col id="{k}">{text}</Col>')
    return "".join(parts)


def build_select_envelope() -> str:
    """Same shape as live_probe.build_envelope — empty dsSearch.

    Kept locally so this module has no circular import on live_probe.
    """
    return (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        f'<Root xmlns="{_NEXACRO_NS}">\n'
        '  <Parameters/>\n'
        '  <Dataset id="dsSearch">\n'
        '    <ColumnInfo><Column id="dummy" type="STRING" size="1"/></ColumnInfo>\n'
        '    <Rows></Rows>\n'
        '  </Dataset>\n'
        '</Root>\n'
    )


def build_save_envelope(
    dataset_id: str,
    insert_rows: Optional[list[dict]] = None,
    delete_rows: Optional[list[dict]] = None,
) -> str:
    """Build a save envelope with Row Type="insert"/"delete" entries.

    `dataset_id` is the runtime dataset name the controller binds (e.g., `dsAccount`).
    `insert_rows` / `delete_rows` are column→value dicts. The combined column set
    determines `<ColumnInfo>`; a missing column on a given row renders as `<Col/>`.
    """
    ins = insert_rows or []
    dels = delete_rows or []
    all_cols: list[str] = []
    seen = set()
    for r in [*ins, *dels]:
        for k in r:
            if k not in seen:
                seen.add(k)
                all_cols.append(k)
    rows_xml_parts = []
    for r in ins:
        rows_xml_parts.append(f'<Row Type="insert">{_row_cols(r)}</Row>')
    for r in dels:
        rows_xml_parts.append(f'<Row Type="delete">{_row_cols(r)}</Row>')
    rows_xml = "".join(rows_xml_parts)
    return (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        f'<Root xmlns="{_NEXACRO_NS}">\n'
        '  <Parameters/>\n'
        f'  <Dataset id="{dataset_id}">\n'
        f'    <ColumnInfo>{_column_info(all_cols)}</ColumnInfo>\n'
        f'    <Rows>{rows_xml}</Rows>\n'
        '  </Dataset>\n'
        '</Root>\n'
    )


# ---------- transport ----------

def _post_envelope(url: str, body: str, timeout_sec: float) -> tuple[int, str]:
    req = urllib_request.Request(
        url,
        data=body.encode("utf-8"),
        headers={
            "Content-Type": "text/xml;charset=utf-8",
            "User-Agent": "live-crud-nexacro/0.1",
        },
        method="POST",
    )
    try:
        with urllib_request.urlopen(req, timeout=timeout_sec) as resp:
            status = getattr(resp, "status", 200)
            text = resp.read().decode("utf-8", errors="replace")
            return (status, text)
    except urllib.error.HTTPError as e:
        try:
            text = e.read().decode("utf-8", errors="replace") if e.fp else ""
        except Exception:
            text = ""
        return (e.code, text)
    except Exception:
        return (0, "")


def _parse_error_code(text: str) -> int:
    m = _ERROR_CODE_RE.search(text)
    if not m:
        return -999
    try:
        return int(m.group(1).strip())
    except ValueError:
        return -999


def _count_rows(text: str) -> int:
    return len(_ROW_RE.findall(text))


def _get_count(select_url: str, timeout_sec: float) -> tuple[int, int, int]:
    """Return (http_status, error_code, row_count) for the select envelope."""
    status, text = _post_envelope(select_url, build_select_envelope(), timeout_sec)
    if status != 200:
        return (status, -999, -1)
    err = _parse_error_code(text)
    if err != 0:
        return (status, err, -1)
    return (status, err, _count_rows(text))


# ---------- 5-step round-trip ----------

def crud_roundtrip_envelope(
    select_url: str,
    save_url: str,
    dataset_id: str,
    insert_row: dict,
    pk_column: str,
    pk_value,
    timeout_sec: float = 30.0,
) -> CrudResult:
    """baseline → insert → verify +1 → delete → verify back-to-baseline.

    `dataset_id` is the nexacro runtime dataset id (e.g., `dsAccount` for entity
    `account`). The controller deserializes the envelope's `<Dataset id="...">`
    block by that name.

    `insert_row` is a column→value dict (without `_rowType`). The function emits
    `<Row Type="insert">` for it. The delete payload is built as
    `<Row Type="delete">` containing only `{pk_column: pk_value}`.

    ok=True only if all 5 calls return HTTP 200 + ErrorCode=0 and the row count
    moves +1 then back to baseline.
    """
    s, err, baseline = _get_count(select_url, timeout_sec)
    if s != 200 or err != 0 or baseline < 0:
        return CrudResult(
            baseline_count=baseline,
            reason=f"baseline select failed (status={s}, errcode={err})",
        )

    ins_env = build_save_envelope(dataset_id, insert_rows=[insert_row])
    s_ins, ins_text = _post_envelope(save_url, ins_env, timeout_sec)
    ins_err = _parse_error_code(ins_text) if s_ins == 200 else -999
    if s_ins != 200 or ins_err != 0:
        return CrudResult(
            baseline_count=baseline,
            insert_status=s_ins, insert_error_code=ins_err,
            reason=f"insert save failed (status={s_ins}, errcode={ins_err})",
        )

    s_a, err_a, after_ins = _get_count(select_url, timeout_sec)
    if s_a != 200 or err_a != 0 or after_ins != baseline + 1:
        return CrudResult(
            baseline_count=baseline, after_insert_count=after_ins,
            insert_status=s_ins, insert_error_code=ins_err,
            reason=f"insert verify failed (expected {baseline+1}, got {after_ins}; errcode={err_a})",
        )

    del_env = build_save_envelope(dataset_id, delete_rows=[{pk_column: pk_value}])
    s_del, del_text = _post_envelope(save_url, del_env, timeout_sec)
    del_err = _parse_error_code(del_text) if s_del == 200 else -999

    s_a2, err_a2, after_del = _get_count(select_url, timeout_sec)
    ok = (
        s_del == 200 and del_err == 0
        and s_a2 == 200 and err_a2 == 0
        and after_del == baseline
    )
    reason = "" if ok else (
        f"delete/verify failed (del_status={s_del}, del_errcode={del_err}, "
        f"final={after_del}, final_errcode={err_a2}, expected {baseline})"
    )
    return CrudResult(
        baseline_count=baseline,
        after_insert_count=after_ins,
        after_delete_count=after_del,
        insert_status=s_ins, insert_error_code=ins_err,
        delete_status=s_del, delete_error_code=del_err,
        ok=ok, reason=reason,
    )


# ---------- helpers callers will want ----------

def nexacro_dataset_id(entity: str) -> str:
    """Return the server-side dataset id the scaffold controller binds for save.

    Scaffold-generated controllers declare
        @ParamDataSet(name = "dataList") List<Map<String, Object>> dataList
    so the envelope must ship `<Dataset id="dataList">`. The form-side `ds<Pascal>`
    convention only applies inside the XFDL Transaction's string map
    (e.g. `dsCustomer=dataList:U`) — the wire dataset id is always `dataList`.

    `entity` is accepted (and ignored) so a future per-entity binding override
    can land without rewiring callers.
    """
    return "dataList"


def nexacro_save_url(port: int, entity: str) -> str:
    """Build the save endpoint URL parallel to lane_runner_map.lane_probe_url (which targets select)."""
    return f"http://localhost:{port}/uiadapter/{entity}/save_datalist_map.do"
