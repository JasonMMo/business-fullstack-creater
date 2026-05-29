"""
web/adapters/target_extractor.py — Growth-79 (M5 Slice C-c) thin adapter between
the FastAPI web layer and `scripts/extract_target_profile.py`.

Critical constraint (G-79): this module MUST NOT re-implement profile-extraction
logic. It imports `extract_target_profile.build_profile` + `dump_profile` and
only handles the web-side concerns: zip → temp dir → call → cleanup.

Compounding-growth guard parallel to G-69 (scaffold_runner subprocess pipeline):
just as the web scaffold path goes through scripts/scaffold_cli.py to preserve
6-axis accumulation, the web target-upload path goes through extract_target_profile
to preserve the v1 customer profile (G-70) + Gradle (G-78) input contracts.
"""
from __future__ import annotations

import io
import pathlib
import re
import shutil
import sys
import tempfile
import zipfile
from dataclasses import dataclass
from typing import Optional

# Make `scripts/` importable from the web layer.
_REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
_SCRIPTS = _REPO_ROOT / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

import extract_target_profile  # noqa: E402 — single source of truth for parsing


class TargetExtractionError(ValueError):
    """Raised when the upload cannot be parsed into a v1 customer profile."""


@dataclass(frozen=True)
class ExtractionResult:
    slug: str
    yaml_text: str
    source: str  # short tag for the UI: "maven" | "gradle"


def _zip_root(zf: zipfile.ZipFile) -> Optional[str]:
    """Detect a single top-level directory in the archive (common case)."""
    names = [n for n in zf.namelist() if n and not n.startswith("/")]
    roots = {n.split("/", 1)[0] for n in names}
    if len(roots) == 1:
        only = next(iter(roots))
        if any(n.startswith(only + "/") for n in names):
            return only
    return None


def _detect_source(project_dir: pathlib.Path) -> str:
    if (project_dir / "pom.xml").exists():
        return "maven"
    for name in ("build.gradle.kts", "build.gradle"):
        if (project_dir / name).exists():
            # Growth-81: distinguish multi-module via settings.gradle include
            for settings_name in ("settings.gradle.kts", "settings.gradle"):
                sp = project_dir / settings_name
                if sp.exists():
                    txt = sp.read_text(encoding="utf-8", errors="replace")
                    if re.search(r"^\s*include\s*[\s(]", txt, re.MULTILINE):
                        return "gradle-multi"
            return "gradle"
    return "unknown"


def extract_from_zip(
    payload: bytes,
    *,
    slug_override: Optional[str] = None,
) -> ExtractionResult:
    """Unzip *payload* to a temp dir, build a v1 profile, return YAML text.

    Raises TargetExtractionError for any user-recoverable failure (bad zip,
    missing pom.xml/build.gradle, derived slug invalid). The temp dir is
    always cleaned up.
    """
    if not payload:
        raise TargetExtractionError("업로드 zip 이 비어있습니다.")

    try:
        zf = zipfile.ZipFile(io.BytesIO(payload))
    except zipfile.BadZipFile as exc:
        raise TargetExtractionError(f"올바른 zip 파일이 아닙니다: {exc}") from exc

    tmp_root = pathlib.Path(tempfile.mkdtemp(prefix="target-upload-"))
    try:
        # Reject zip-slip: any entry escaping tmp_root after normalization.
        for member in zf.infolist():
            dest = (tmp_root / member.filename).resolve()
            if tmp_root.resolve() not in dest.parents and dest != tmp_root.resolve():
                raise TargetExtractionError(
                    f"zip 항목이 디렉터리를 벗어납니다: {member.filename}"
                )
        zf.extractall(tmp_root)

        root_name = _zip_root(zf)
        project_dir = (tmp_root / root_name) if root_name else tmp_root

        try:
            profile = extract_target_profile.build_profile(
                project_dir,
                slug_override=slug_override or None,
            )
        except FileNotFoundError as exc:
            raise TargetExtractionError(str(exc)) from exc
        except ValueError as exc:
            raise TargetExtractionError(str(exc)) from exc

        yaml_text = extract_target_profile.dump_profile(profile)
        return ExtractionResult(
            slug=profile["customer"]["slug"],
            yaml_text=yaml_text,
            source=_detect_source(project_dir),
        )
    finally:
        shutil.rmtree(tmp_root, ignore_errors=True)
        zf.close()
