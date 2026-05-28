"""
web/adapters/zip_emitter.py — in-memory zip bundler for scaffold output directories.

Usage::

    from web.adapters.zip_emitter import emit

    zip_bytes = emit("out/acme-customer")
    # serve zip_bytes as an HTTP response with Content-Type: application/zip

The archive structure mirrors the source directory with a top-level folder named
after the directory basename, so unzipping produces ``<slug>/...`` rather than
a flat dump.

Included:
    - All regular files under out_dir, preserving relative paths.

Excluded by default:
    - .git (and any sub-path containing a component named .git)
    - __pycache__
    - *.pyc, *.pyo
    - .DS_Store

Symlinks are silently skipped to keep the implementation simple and safe.
The caller may supply a custom ``exclude_patterns`` tuple to replace the defaults
entirely (the passed tuple is used as-is; if you want to extend defaults, include
DEFAULT_EXCLUDES in your tuple).
"""
from __future__ import annotations

import fnmatch
import io
import zipfile
from pathlib import Path
from typing import Iterable

DEFAULT_EXCLUDES: tuple[str, ...] = (
    ".git",
    "__pycache__",
    "*.pyc",
    "*.pyo",
    ".DS_Store",
)


def emit(
    out_dir: str | Path,
    *,
    exclude_patterns: tuple[str, ...] = DEFAULT_EXCLUDES,
) -> bytes:
    """Bundle the directory tree at *out_dir* into an in-memory zip archive.

    Parameters
    ----------
    out_dir:
        Path to the scaffold output directory (e.g. ``out/acme-customer``).
    exclude_patterns:
        A tuple of glob patterns matched against each path component and
        filename.  Any path whose relative components or basename match one
        of these patterns is omitted.  Defaults to :data:`DEFAULT_EXCLUDES`.
        Pass your own tuple to **replace** (not extend) the defaults.

    Returns
    -------
    bytes
        Raw bytes of a ZIP archive.  The archive contains a single top-level
        folder named ``basename(out_dir)/`` so that unzipping produces a
        folder rather than a flat file dump.

    Raises
    ------
    FileNotFoundError
        If *out_dir* does not exist.
    NotADirectoryError
        If *out_dir* exists but is not a directory.
    """
    src = Path(out_dir).resolve()
    if not src.exists():
        raise FileNotFoundError(f"out_dir not found: {src}")
    if not src.is_dir():
        raise NotADirectoryError(f"out_dir is not a directory: {src}")

    buf = io.BytesIO()
    archive_root = src.name  # top-level folder name inside the zip

    with zipfile.ZipFile(buf, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(src.rglob("*")):
            if not path.is_file():
                # skip directories and symlinks
                continue
            if _is_excluded(path, src, exclude_patterns):
                continue
            rel = path.relative_to(src)
            arcname = f"{archive_root}/{rel.as_posix()}"
            zf.write(path, arcname=arcname)

    return buf.getvalue()


def _is_excluded(path: Path, src: Path, patterns: Iterable[str]) -> bool:
    """Return True if *path* should be excluded based on *patterns*.

    Checks every component of the relative path and the filename itself
    against each glob pattern.
    """
    rel = path.relative_to(src)
    parts = rel.parts  # individual path components
    name = path.name
    for pat in patterns:
        if any(fnmatch.fnmatch(p, pat) for p in parts):
            return True
        if fnmatch.fnmatch(name, pat):
            return True
    return False
