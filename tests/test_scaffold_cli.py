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


# R1 (서비스 리뷰 2026-05-26): resolve_slug — explicit > derived > package-fallback
class TestResolveSlug:
    def test_explicit_slug_wins_over_domain(self):
        from scaffold_cli import resolve_slug
        slug, src = resolve_slug("주문관리", explicit_slug="order", package_fallback="other")
        assert (slug, src) == ("order", "explicit")

    def test_ascii_domain_derives(self):
        from scaffold_cli import resolve_slug
        slug, src = resolve_slug("OrderMgmt", explicit_slug=None, package_fallback="anything")
        assert (slug, src) == ("ordermgmt", "derived")

    def test_korean_falls_back_to_package_last_segment(self):
        from scaffold_cli import resolve_slug
        slug, src = resolve_slug("주문관리", explicit_slug=None, package_fallback="order")
        assert (slug, src) == ("order", "package-fallback")

    def test_korean_without_fallback_raises(self):
        from scaffold_cli import resolve_slug
        import pytest as _pytest
        with _pytest.raises(ValueError, match="cannot derive slug"):
            resolve_slug("주문관리", explicit_slug=None, package_fallback=None)

    def test_explicit_slug_empty_after_sanitize_raises(self):
        from scaffold_cli import resolve_slug
        import pytest as _pytest
        with _pytest.raises(ValueError, match="sanitizes to empty"):
            resolve_slug("ignored", explicit_slug="!@#$", package_fallback="ok")

    def test_explicit_slug_sanitized(self):
        from scaffold_cli import resolve_slug
        # explicit slug also passes through ASCII sanitization
        slug, src = resolve_slug("anything", explicit_slug="Order Mgmt!", package_fallback=None)
        assert (slug, src) == ("order-mgmt", "explicit")


# Growth-59 (2026-05-26): lane-aware --ui default
class TestResolveUiDefault:
    def test_vanilla_lane_defaults_to_react(self):
        from scaffold_cli import resolve_ui_default
        assert resolve_ui_default(None, "vanilla") == "react"

    def test_nexacro_lane_defaults_to_nexacro(self):
        from scaffold_cli import resolve_ui_default
        assert resolve_ui_default(None, "nexacro") == "nexacro"

    def test_jakarta_lane_defaults_to_nexacro(self):
        from scaffold_cli import resolve_ui_default
        assert resolve_ui_default(None, "jakarta") == "nexacro"

    def test_javax_lane_defaults_to_nexacro(self):
        from scaffold_cli import resolve_ui_default
        assert resolve_ui_default(None, "javax") == "nexacro"

    def test_explicit_nexacro_overrides_vanilla_default(self):
        from scaffold_cli import resolve_ui_default
        # User may force nexacro overlay even on vanilla lane
        assert resolve_ui_default("nexacro", "vanilla") == "nexacro"

    def test_explicit_react_overrides_nexacro_default(self):
        from scaffold_cli import resolve_ui_default
        # User may force react overlay on a nexacro lane
        assert resolve_ui_default("react", "nexacro") == "react"


# Growth-63 (2026-05-28): customer profile loader (6th axis)
class TestLoadCustomerProfile:
    def _write(self, tmp_path, slug, body):
        (tmp_path / f"{slug}.yaml").write_text(body, encoding="utf-8")
        return tmp_path

    def test_returns_none_when_slug_is_none(self):
        from scaffold_cli import load_customer_profile
        assert load_customer_profile(None) is None

    def test_missing_file_raises_value_error(self, tmp_path):
        from scaffold_cli import load_customer_profile
        with pytest.raises(ValueError, match="not found"):
            load_customer_profile("nope", profiles_root=tmp_path)

    def test_version_other_than_1_rejected(self, tmp_path):
        from scaffold_cli import load_customer_profile
        self._write(tmp_path, "x", "version: 2\ncustomer:\n  slug: x\n")
        with pytest.raises(ValueError, match="unsupported version"):
            load_customer_profile("x", profiles_root=tmp_path)

    def test_missing_version_rejected(self, tmp_path):
        from scaffold_cli import load_customer_profile
        self._write(tmp_path, "x", "customer:\n  slug: x\n")
        with pytest.raises(ValueError, match="unsupported version"):
            load_customer_profile("x", profiles_root=tmp_path)

    def test_slug_mismatch_raises(self, tmp_path):
        from scaffold_cli import load_customer_profile
        self._write(tmp_path, "acme", "version: 1\ncustomer:\n  slug: foo\n")
        with pytest.raises(ValueError, match="does not match filename"):
            load_customer_profile("acme", profiles_root=tmp_path)

    def test_happy_path_returns_dict(self, tmp_path):
        from scaffold_cli import load_customer_profile
        self._write(
            tmp_path,
            "acme",
            "version: 1\ncustomer:\n  slug: acme\n  display: ACME\nmybatis:\n  base_package: com.acme\n",
        )
        data = load_customer_profile("acme", profiles_root=tmp_path)
        assert data["customer"]["display"] == "ACME"
        assert data["mybatis"]["base_package"] == "com.acme"

    def test_env_var_interpolated(self, tmp_path, monkeypatch):
        from scaffold_cli import load_customer_profile
        monkeypatch.setenv("ACME_DB_PASS", "s3cret")
        self._write(
            tmp_path,
            "acme",
            'version: 1\ncustomer:\n  slug: acme\ndatasource:\n  password: ${ACME_DB_PASS}\n',
        )
        data = load_customer_profile("acme", profiles_root=tmp_path)
        assert data["datasource"]["password"] == "s3cret"

    def test_env_var_missing_stays_literal(self, tmp_path, monkeypatch):
        from scaffold_cli import load_customer_profile
        monkeypatch.delenv("ACME_DB_PASS", raising=False)
        self._write(
            tmp_path,
            "acme",
            'version: 1\ncustomer:\n  slug: acme\ndatasource:\n  password: ${ACME_DB_PASS}\n',
        )
        data = load_customer_profile("acme", profiles_root=tmp_path)
        assert data["datasource"]["password"] == "${ACME_DB_PASS}"

    def test_non_mapping_root_rejected(self, tmp_path):
        from scaffold_cli import load_customer_profile
        self._write(tmp_path, "x", "- 1\n- 2\n")
        with pytest.raises(ValueError, match="must be a mapping"):
            load_customer_profile("x", profiles_root=tmp_path)


class TestResolveWithProfile:
    def test_cli_value_wins_over_profile(self):
        from scaffold_cli import resolve_with_profile
        profile = {"ddl": {"dialect": "postgres"}}
        assert resolve_with_profile("hsqldb", profile, "ddl", "dialect", default="mysql") == "hsqldb"

    def test_profile_wins_when_cli_none(self):
        from scaffold_cli import resolve_with_profile
        profile = {"ddl": {"dialect": "postgres"}}
        assert resolve_with_profile(None, profile, "ddl", "dialect", default="mysql") == "postgres"

    def test_default_used_when_both_missing(self):
        from scaffold_cli import resolve_with_profile
        assert resolve_with_profile(None, None, "ddl", "dialect", default="mysql") == "mysql"

    def test_missing_nested_key_returns_default(self):
        from scaffold_cli import resolve_with_profile
        profile = {"ddl": {}}
        assert resolve_with_profile(None, profile, "ddl", "dialect", default="mysql") == "mysql"

    def test_cli_empty_string_still_wins(self):
        # Falsy but non-None CLI value must still override (current contract: only None defers).
        from scaffold_cli import resolve_with_profile
        profile = {"defaults": {"lane": "jakarta"}}
        assert resolve_with_profile("", profile, "defaults", "lane", default="nexacro") == ""
