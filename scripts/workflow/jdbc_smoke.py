"""L2 JDBC smoke runner — apply schema + data to in-memory HSQLDB.

Resolves hsqldb jar via env var `HSQLDB_JAR` first, then a small fallback list
of known-good locations on this dev environment. Subprocesses to the sibling
`_jdbc_smoke.java` single-file launcher (JDK 11+ source-mode).

Verdict: PASS iff exit code 0. Missing jar → SKIPPED (caller decides how to
label — current full_test treats SKIPPED as PASS to avoid blocking L3/L4 on
infra absence, with a stderr warning).
"""
from __future__ import annotations
import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

_FALLBACK_JAR_PATHS = [
    Path(r"D:\2025\08\코리안리\resources\hsqldb-2.5.2.jar"),
    Path(r"D:\devpro\repository\org\hsqldb\hsqldb\2.7.2\hsqldb-2.7.2.jar"),
    Path(r"D:\devpro\repository\org\hsqldb\hsqldb\2.5.2\hsqldb-2.5.2.jar"),
]

_LAUNCHER = Path(__file__).parent / "_jdbc_smoke.java"


@dataclass
class SmokeResult:
    ok: bool
    skipped: bool = False
    reason: str = ""
    stdout: str = ""
    stderr: str = ""


def find_hsqldb_jar() -> Optional[Path]:
    """Resolve hsqldb jar. Env var wins; otherwise probe known dev paths."""
    env = os.environ.get("HSQLDB_JAR")
    if env:
        p = Path(env)
        if p.exists():
            return p
    for cand in _FALLBACK_JAR_PATHS:
        if cand.exists():
            return cand
    return None


def run_smoke(
    schema_sql: Path,
    data_sql: Path,
    invariant: Optional[str] = None,
    *,
    hsqldb_jar: Optional[Path] = None,
    java_exe: str = "java",
    timeout_sec: int = 60,
) -> SmokeResult:
    """Run HSQLDB schema+data smoke. Optional invariant: 'SELECT ...=<int>'."""
    jar = hsqldb_jar or find_hsqldb_jar()
    if jar is None:
        return SmokeResult(ok=True, skipped=True, reason="no HSQLDB_JAR — L2 skipped")
    if shutil.which(java_exe) is None:
        return SmokeResult(ok=True, skipped=True, reason=f"no {java_exe} on PATH — L2 skipped")
    if not _LAUNCHER.exists():
        return SmokeResult(ok=False, reason=f"missing launcher {_LAUNCHER}")
    if not schema_sql.exists():
        return SmokeResult(ok=False, reason=f"schema missing: {schema_sql}")
    if not data_sql.exists():
        return SmokeResult(ok=False, reason=f"data missing: {data_sql}")

    cmd = [
        java_exe, "-cp", str(jar), str(_LAUNCHER),
        "--schema", str(schema_sql),
        "--data", str(data_sql),
    ]
    if invariant:
        cmd += ["--invariant", invariant]
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout_sec)
    except subprocess.TimeoutExpired:
        return SmokeResult(ok=False, reason=f"L2 timed out after {timeout_sec}s")
    return SmokeResult(
        ok=(p.returncode == 0),
        stdout=p.stdout,
        stderr=p.stderr,
        reason="" if p.returncode == 0 else f"exit {p.returncode}",
    )


def discover_sql(scaffold_dir: Path) -> tuple[Optional[Path], Optional[Path]]:
    """Resolve schema.sql + data.sql under scaffold (Stage 3 first, then 2-ddl)."""
    for sub in (
        scaffold_dir / "3-mybatis" / "src" / "main" / "resources",
        scaffold_dir / "2-ddl",
    ):
        schema = sub / "schema.sql"
        data = sub / "data.sql"
        if schema.exists() and data.exists():
            return schema, data
    return None, None
