"""
tests/web/test_zip_emitter.py — coverage for web/adapters/zip_emitter.py (M1 S1.3).

7 test cases:
    1. test_emit_returns_bytes              — basic smoke
    2. test_emit_preserves_directory_structure — subdirs preserved with slug prefix
    3. test_emit_excludes_default_patterns  — .git/__pycache__/*.pyc/.DS_Store excluded
    4. test_emit_respects_custom_exclude_patterns — custom tuple replaces defaults
    5. test_emit_raises_on_missing_directory — FileNotFoundError
    6. test_emit_raises_on_file_instead_of_directory — NotADirectoryError
    7. test_emit_produces_deterministic_output — byte-identical on repeated calls
"""
from __future__ import annotations

import io
import zipfile

import pytest

from web.adapters.zip_emitter import emit, DEFAULT_EXCLUDES


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _zip_names(result: bytes) -> list[str]:
    """Return sorted list of archive member names."""
    with zipfile.ZipFile(io.BytesIO(result)) as zf:
        return sorted(zf.namelist())


# ---------------------------------------------------------------------------
# 1. Basic smoke
# ---------------------------------------------------------------------------

def test_emit_returns_bytes(tmp_path):
    """emit() should return bytes that constitute a valid ZIP archive."""
    slug_dir = tmp_path / "acme"
    slug_dir.mkdir()
    (slug_dir / "hello.txt").write_text("hello")

    result = emit(slug_dir)

    assert isinstance(result, bytes)
    assert len(result) > 0
    # verify it is actually a valid zip
    assert zipfile.is_zipfile(io.BytesIO(result))


# ---------------------------------------------------------------------------
# 2. Directory structure preserved
# ---------------------------------------------------------------------------

def test_emit_preserves_directory_structure(tmp_path):
    """Files appear under <slug>/ prefix with full relative path."""
    slug_dir = tmp_path / "acme"
    (slug_dir / "1-skill").mkdir(parents=True)
    (slug_dir / "2-ddl").mkdir(parents=True)
    (slug_dir / "1-skill" / "x.md").write_text("# skill")
    (slug_dir / "2-ddl" / "y.sql").write_text("CREATE TABLE t (id INT);")

    result = emit(slug_dir)
    names = _zip_names(result)

    assert "acme/1-skill/x.md" in names
    assert "acme/2-ddl/y.sql" in names


# ---------------------------------------------------------------------------
# 3. Default exclusions
# ---------------------------------------------------------------------------

def test_emit_excludes_default_patterns(tmp_path):
    """Default patterns strip .git, __pycache__, *.pyc, .DS_Store."""
    slug_dir = tmp_path / "x"
    (slug_dir / "__pycache__").mkdir(parents=True)
    (slug_dir / ".git").mkdir(parents=True)
    (slug_dir / "__pycache__" / "foo.pyc").write_bytes(b"bytecode")
    (slug_dir / ".git" / "HEAD").write_text("ref: refs/heads/main")
    (slug_dir / ".DS_Store").write_bytes(b"\x00")
    (slug_dir / "regular.txt").write_text("keep me")

    result = emit(slug_dir)
    names = _zip_names(result)

    assert "x/regular.txt" in names
    # none of the excluded paths should appear
    assert not any("__pycache__" in n for n in names)
    assert not any(".git" in n for n in names)
    assert not any(".DS_Store" in n for n in names)
    assert not any(".pyc" in n for n in names)


# ---------------------------------------------------------------------------
# 4. Custom exclude patterns replace defaults
# ---------------------------------------------------------------------------

def test_emit_respects_custom_exclude_patterns(tmp_path):
    """When exclude_patterns is supplied, it REPLACES defaults entirely.

    Consequence: passing only ("*.log",) will exclude .log files but
    __pycache__, .pyc etc. will NO LONGER be excluded.
    """
    slug_dir = tmp_path / "proj"
    (slug_dir / "__pycache__").mkdir(parents=True)
    (slug_dir / "__pycache__" / "mod.pyc").write_bytes(b"bytecode")
    (slug_dir / "app.log").write_text("log line")
    (slug_dir / "app.py").write_text("print('hi')")

    result = emit(slug_dir, exclude_patterns=("*.log",))
    names = _zip_names(result)

    # .log is excluded by custom pattern
    assert not any(".log" in n for n in names)
    # app.py is kept
    assert "proj/app.py" in names
    # __pycache__/mod.pyc is NOT excluded — defaults are replaced
    assert "proj/__pycache__/mod.pyc" in names


# ---------------------------------------------------------------------------
# 5. Missing directory raises FileNotFoundError
# ---------------------------------------------------------------------------

def test_emit_raises_on_missing_directory(tmp_path):
    """emit() must raise FileNotFoundError when out_dir does not exist."""
    missing = tmp_path / "does_not_exist"
    with pytest.raises(FileNotFoundError, match="out_dir not found"):
        emit(missing)


# ---------------------------------------------------------------------------
# 6. File path raises NotADirectoryError
# ---------------------------------------------------------------------------

def test_emit_raises_on_file_instead_of_directory(tmp_path):
    """emit() must raise NotADirectoryError when out_dir is a file."""
    a_file = tmp_path / "not_a_dir.txt"
    a_file.write_text("I am a file")
    with pytest.raises(NotADirectoryError, match="not a directory"):
        emit(a_file)


# ---------------------------------------------------------------------------
# 7. Deterministic output
# ---------------------------------------------------------------------------

def test_emit_produces_deterministic_output(tmp_path):
    """Two calls on the same input must return byte-identical archives."""
    slug_dir = tmp_path / "stable"
    (slug_dir / "a").mkdir(parents=True)
    (slug_dir / "b").mkdir(parents=True)
    (slug_dir / "a" / "first.txt").write_text("aaa")
    (slug_dir / "b" / "second.txt").write_text("bbb")
    (slug_dir / "root.md").write_text("# root")

    result1 = emit(slug_dir)
    result2 = emit(slug_dir)

    assert result1 == result2
