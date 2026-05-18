# scripts/menu_injector.py
"""Inject domain + entity menu rows into frameLogin.xfdl dsSample dataset.

xml.etree is intentionally forbidden — xfdl is non-standard XML (BindItem, etc.)
that etree would reformat and break Nexacro Studio diffs.  Regex + string insertion
preserves the original file byte-for-byte except for the new <Row> blocks.
"""
import re
import pathlib
from typing import Sequence, Tuple

REQUIRED_COLUMNS = [
    "level", "groupId", "menuId", "menuNm", "menuUrl",
    "sortNo", "upMenuId", "useYn", "auth",
]


class SchemaMismatch(Exception):
    """Raised when dsSample <ColumnInfo> is missing one or more required columns."""

    def __init__(self, target_cols: list, required: list, path: pathlib.Path):
        self.target_cols = target_cols
        self.required = required
        self.path = path
        missing = [c for c in required if c not in target_cols]
        super().__init__(
            f"dsSample column schema mismatch in {path}.\n"
            f"  target ColumnInfo: {target_cols}\n"
            f"  required by tool : {required}\n"
            f"  missing          : {missing}\n"
            f"  → Add the missing columns to dsSample <ColumnInfo>, "
            f"or map them via blueprint."
        )


# ---------------------------------------------------------------------------
# Compiled regexes
# ---------------------------------------------------------------------------

# Captures the entire body of <Dataset id="dsSample">...</Dataset>
_DATASET_RE = re.compile(
    r'<Dataset\s+id="dsSample">(?P<body>.*?)</Dataset>',
    re.DOTALL,
)

# Extracts column IDs from <ColumnInfo> block
_COLINFO_RE = re.compile(r'<Column\s+id="([^"]+)"', re.DOTALL)

# Matches </Rows> with optional leading whitespace (capture groups for reassembly)
_ROWS_CLOSE_RE = re.compile(r'(\s*)(</Rows>)')

# Row XML template — one entry per menu row
_ROW_TEMPLATE = (
    "          <Row>\n"
    '            <Col id="level">{level}</Col>\n'
    '            <Col id="groupId">{groupId}</Col>\n'
    '            <Col id="menuId">{menuId}</Col>\n'
    '            <Col id="menuNm">{menuNm}</Col>\n'
    '            <Col id="menuUrl">{menuUrl}</Col>\n'
    '            <Col id="sortNo">{sortNo}</Col>\n'
    '            <Col id="upMenuId">{upMenuId}</Col>\n'
    '            <Col id="useYn">Y</Col>\n'
    '            <Col id="auth">YYYYYY</Col>\n'
    "          </Row>\n"
)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def inject_menu_rows(
    xfdl_path: pathlib.Path,
    *,
    domain_id: str,
    domain_label: str,
    domain_sort: int,
    entries: Sequence[Tuple[str, str, str]],  # (slug, label, url)
) -> None:
    """Append domain group row + entity rows into dsSample <Rows> block.

    Idempotent: rows whose menuId already appears in the body are skipped.

    Raises:
        RuntimeError: if <Dataset id="dsSample"> or </Rows> not found.
        SchemaMismatch: if any REQUIRED_COLUMNS are absent from <ColumnInfo>.
    """
    xfdl_path = pathlib.Path(xfdl_path)
    text = xfdl_path.read_text(encoding="utf-8")

    m = _DATASET_RE.search(text)
    if not m:
        raise RuntimeError(
            f'<Dataset id="dsSample"> not found in {xfdl_path}'
        )

    body = m.group("body")

    # --- Schema validation ---
    target_cols = _COLINFO_RE.findall(body)
    if not all(c in target_cols for c in REQUIRED_COLUMNS):
        raise SchemaMismatch(target_cols, REQUIRED_COLUMNS, xfdl_path)

    # --- Idempotency helper ---
    def _has_menu(mid: str) -> bool:
        return f'<Col id="menuId">{mid}</Col>' in body

    # --- Collect new rows to insert ---
    new_rows: list[str] = []

    # Domain group row (level=0)
    if not _has_menu(domain_id):
        new_rows.append(_ROW_TEMPLATE.format(
            level=0,
            groupId=domain_id,
            menuId=domain_id,
            menuNm=domain_label,
            menuUrl="",
            sortNo=domain_sort,
            upMenuId="(root)",
        ))

    # Entity rows (level=1)
    for i, (slug, label, url) in enumerate(entries, start=1):
        mid = f"{domain_id}_{slug.upper()}"
        if _has_menu(mid):
            continue
        new_rows.append(_ROW_TEMPLATE.format(
            level=1,
            groupId=domain_id,
            menuId=mid,
            menuNm=label,
            menuUrl=url,
            sortNo=i * 10,
            upMenuId=domain_id,
        ))

    if not new_rows:
        return  # fully idempotent — nothing to write

    # --- Insert before </Rows> inside the dsSample body ---
    new_body, n = _ROWS_CLOSE_RE.subn(
        lambda mm: "".join(new_rows) + mm.group(1) + mm.group(2),
        body,
        count=1,
    )
    if n != 1:
        raise RuntimeError(
            f"</Rows> not found inside dsSample of {xfdl_path}"
        )

    # Reconstruct full text, replacing only the captured body span
    new_text = text[: m.start("body")] + new_body + text[m.end("body") :]
    xfdl_path.write_text(new_text, encoding="utf-8")
