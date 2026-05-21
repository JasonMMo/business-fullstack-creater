"""Live CRUD round-trip — INSERT and DELETE through the runner's bulk-save endpoint.

REST controllers (jakarta/javax/vanilla) expose:
  GET  /api/<entity>          → List<Map>            (read all)
  POST /api/<entity>          → int (rows affected)  (bulk save; body = List<Map>; _rowType ∈ {I,U,D})

A successful round-trip proves the full controller→service→mapper→DB→serializer
stack works end-to-end for writes — not just reads (which L4 probe already covers).

Growth-40 ships the round-trip primitive plus a best-effort template auto-discovery
that mines `data.sql` MERGE statements for column/value shape, then swaps in a
high-number sentinel PK so the probe row never collides with seed rows.
"""
from __future__ import annotations
import json
import re
import urllib.error
import urllib.request as urllib_request
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class CrudResult:
    baseline_count: int = -1
    after_insert_count: int = -1
    after_delete_count: int = -1
    insert_status: int = 0
    insert_rows: int = 0
    delete_status: int = 0
    delete_rows: int = 0
    ok: bool = False
    reason: str = ""


def _get_count(url: str, timeout_sec: float) -> tuple[int, int]:
    req = urllib_request.Request(
        url, headers={"Accept": "application/json", "User-Agent": "live-crud/0.1"}, method="GET",
    )
    try:
        with urllib_request.urlopen(req, timeout=timeout_sec) as resp:
            status = getattr(resp, "status", 200)
            body = resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        return (e.code, -1)
    except Exception:
        return (0, -1)
    try:
        payload = json.loads(body)
    except (ValueError, TypeError):
        return (status, -1)
    return (status, len(payload) if isinstance(payload, list) else -1)


def _post_rows(url: str, rows: list[dict], timeout_sec: float) -> tuple[int, int]:
    body = json.dumps(rows).encode("utf-8")
    req = urllib_request.Request(
        url,
        data=body,
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "live-crud/0.1",
        },
        method="POST",
    )
    try:
        with urllib_request.urlopen(req, timeout=timeout_sec) as resp:
            status = getattr(resp, "status", 200)
            text = resp.read().decode("utf-8", errors="replace").strip()
    except urllib.error.HTTPError as e:
        return (e.code, -1)
    except Exception:
        return (0, -1)
    try:
        affected = int(text)
    except (ValueError, TypeError):
        affected = -1
    return (status, affected)


def crud_roundtrip_rest(
    base_url: str,
    insert_row: dict,
    pk_column: str,
    pk_value,
    timeout_sec: float = 30.0,
) -> CrudResult:
    """Run baseline → insert → verify +1 → delete → verify back-to-baseline → ok.

    `insert_row` is a column→value dict for required NOT NULL fields (without _rowType).
    The function injects `_rowType="I"` for the insert and builds a `{pk_column: pk_value,
    "_rowType": "D"}` payload for the delete.

    ok=True only if all 5 steps return HTTP 200, both POSTs report ≥1 row affected,
    and counts move +1 then back to baseline.
    """
    s, baseline = _get_count(base_url, timeout_sec)
    if s != 200 or baseline < 0:
        return CrudResult(baseline_count=baseline, reason=f"baseline GET failed (status={s})")

    insert_payload = [{**insert_row, "_rowType": "I"}]
    s_ins, n_ins = _post_rows(base_url, insert_payload, timeout_sec)
    if s_ins != 200 or n_ins < 1:
        return CrudResult(
            baseline_count=baseline,
            insert_status=s_ins, insert_rows=n_ins,
            reason=f"insert failed (status={s_ins}, affected={n_ins})",
        )

    s_a, after_ins = _get_count(base_url, timeout_sec)
    if s_a != 200 or after_ins != baseline + 1:
        return CrudResult(
            baseline_count=baseline, after_insert_count=after_ins,
            insert_status=s_ins, insert_rows=n_ins,
            reason=f"insert verify failed (expected {baseline+1}, got {after_ins})",
        )

    delete_payload = [{pk_column: pk_value, "_rowType": "D"}]
    s_del, n_del = _post_rows(base_url, delete_payload, timeout_sec)
    s_a2, after_del = _get_count(base_url, timeout_sec)
    ok = (s_del == 200 and n_del >= 1 and s_a2 == 200 and after_del == baseline)
    reason = "" if ok else (
        f"delete/verify failed (del_status={s_del}, del_affected={n_del}, "
        f"final={after_del}, expected {baseline})"
    )
    return CrudResult(
        baseline_count=baseline,
        after_insert_count=after_ins,
        after_delete_count=after_del,
        insert_status=s_ins, insert_rows=n_ins,
        delete_status=s_del, delete_rows=n_del,
        ok=ok,
        reason=reason,
    )


# ---------- Template auto-discovery from data.sql ----------

# Stage 2 emits MERGE statements of the form:
#   MERGE INTO <entity> USING (VALUES(v1, v2, ...)) AS s(c1, c2, ...) ON ...
# We mine the first matching row for the column list and a value template.
_MERGE_RE = re.compile(
    r"MERGE\s+INTO\s+(?P<entity>\w+)\s+USING\s*\(\s*VALUES\s*\((?P<vals>.+?)\)\s*\)\s+AS\s+\w+\s*\((?P<cols>[^)]+)\)",
    re.IGNORECASE | re.DOTALL,
)

# SQL literals we substitute with deterministic ISO strings — MyBatis JdbcType
# binding handles the coercion. Anything else unrecognized → None (JSON null).
_SQL_LITERAL_SUBS = {
    "CURRENT_TIMESTAMP": "2026-05-21T12:00:00",
    "CURRENT_DATE": "2026-05-21",
    "CURRENT_TIME": "12:00:00",
    "TRUE": True,
    "FALSE": False,
    "NULL": None,
}


def _split_csv_depth0(s: str) -> list[str]:
    """Split on commas at parenthesis depth 0, respecting single-quoted strings."""
    out, buf, depth, in_str = [], [], 0, False
    i = 0
    while i < len(s):
        ch = s[i]
        if ch == "'" and (not in_str or s[i:i+2] != "''"):
            in_str = not in_str
            buf.append(ch)
        elif ch == "'" and in_str and s[i:i+2] == "''":
            buf.append("''"); i += 1
        elif not in_str and ch == "(":
            depth += 1; buf.append(ch)
        elif not in_str and ch == ")":
            depth -= 1; buf.append(ch)
        elif not in_str and ch == "," and depth == 0:
            out.append("".join(buf).strip()); buf = []
        else:
            buf.append(ch)
        i += 1
    if buf:
        out.append("".join(buf).strip())
    return out


def _coerce_value(token: str):
    """Convert a SQL literal token to a JSON-serializable Python value."""
    t = token.strip()
    if not t:
        return None
    if t.startswith("'") and t.endswith("'"):
        return t[1:-1].replace("''", "'")
    upper = t.upper()
    if upper in _SQL_LITERAL_SUBS:
        return _SQL_LITERAL_SUBS[upper]
    try:
        return int(t)
    except ValueError:
        pass
    try:
        return float(t)
    except ValueError:
        pass
    return t  # unknown — pass through as string


def parse_merge_into(data_sql_text: str, entity: str) -> Optional[tuple[list[str], list]]:
    """Find first MERGE INTO <entity>, return (columns, first-row values) or None."""
    for m in _MERGE_RE.finditer(data_sql_text):
        if m.group("entity").lower() != entity.lower():
            continue
        cols = [c.strip() for c in m.group("cols").split(",")]
        vals = [_coerce_value(v) for v in _split_csv_depth0(m.group("vals"))]
        if len(cols) != len(vals):
            continue
        return (cols, vals)
    return None


def build_insert_template(
    data_sql: Path,
    entity: str,
    pk_column: str = "id",
    sentinel_pk: int = 999001,
) -> Optional[tuple[dict, int]]:
    """Mine data.sql for entity's first MERGE, return (insert_row_dict, pk_value) or None.

    The PK column's seed value is replaced with `sentinel_pk` (high number unlikely
    to collide with auto-IDENTITY or existing seed rows). All other column values
    are mirrored from the first seed row, so FK references remain valid.
    """
    if not data_sql.exists():
        return None
    text = data_sql.read_text(encoding="utf-8", errors="replace")
    parsed = parse_merge_into(text, entity)
    if parsed is None:
        return None
    cols, vals = parsed
    if pk_column not in cols:
        return None
    row = dict(zip(cols, vals))
    row[pk_column] = sentinel_pk
    return (row, sentinel_pk)
