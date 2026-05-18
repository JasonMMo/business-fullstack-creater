"""tests/test_scaffold_cli.py — Tests for scaffold_cli.py."""
import subprocess
import sys
import pathlib

import pytest

# Path to the CLI script (absolute, works regardless of cwd)
SCAFFOLD_CLI = pathlib.Path(__file__).resolve().parents[1] / "scripts" / "scaffold_cli.py"


# ---------------------------------------------------------------------------
# Import the module directly so we can unit-test derive_slug without subprocess
# ---------------------------------------------------------------------------
sys.path.insert(0, str(SCAFFOLD_CLI.parent))
from scaffold_cli import derive_slug


# ---------------------------------------------------------------------------
# Test: --help exits 0 and mentions --domain
# ---------------------------------------------------------------------------
class TestCliHelp:
    def test_cli_help_runs(self):
        result = subprocess.run(
            [sys.executable, str(SCAFFOLD_CLI), "--help"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"--help exited {result.returncode}\n{result.stderr}"
        assert "--domain" in result.stdout, "'--domain' not in --help output"

    def test_cli_help_mentions_wiki_mode(self):
        result = subprocess.run(
            [sys.executable, str(SCAFFOLD_CLI), "--help"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "--wiki-mode" in result.stdout

    def test_cli_help_mentions_package(self):
        result = subprocess.run(
            [sys.executable, str(SCAFFOLD_CLI), "--help"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "--package" in result.stdout


# ---------------------------------------------------------------------------
# Test: derive_slug — top-level function, unit-testable without subprocess
# ---------------------------------------------------------------------------
class TestDeriveSlug:
    def test_ascii_no_spaces(self):
        assert derive_slug("order") == "order"

    def test_spaces_become_hyphens(self):
        assert derive_slug("order management") == "order-management"

    def test_uppercase_lowercased(self):
        assert derive_slug("OrderMgmt") == "ordermgmt"

    def test_korean_drops_to_empty_fallback(self):
        # Korean characters are non-alnum in [a-z0-9], so stripped; fallback = "domain"
        result = derive_slug("주문관리")
        assert result == "domain"

    def test_mixed_ascii_korean(self):
        result = derive_slug("order 주문")
        # "order " → "order-", Korean stripped → "order-" → strip trailing dash → "order"
        assert result == "order"

    def test_special_chars_stripped(self):
        assert derive_slug("hello!@#world") == "helloworld"

    def test_multiple_hyphens_collapsed(self):
        assert derive_slug("foo  bar") == "foo-bar"

    def test_leading_trailing_hyphens_stripped(self):
        # spaces at edges produce leading/trailing hyphens
        result = derive_slug(" foo ")
        assert not result.startswith("-")
        assert not result.endswith("-")

    def test_empty_string_fallback(self):
        assert derive_slug("") == "domain"
