"""Growth-70 — tests for scripts/extract_target_profile.py."""
from __future__ import annotations

import os
import pathlib
import textwrap

import pytest

from scripts import extract_target_profile as etp
from scripts.scaffold_cli import load_customer_profile


# ---------------------------------------------------------------------------
# Fixture builders
# ---------------------------------------------------------------------------

def _write_pom(
    project: pathlib.Path,
    *,
    group_id: str,
    artifact_id: str,
    version: str = "0.1.0-SNAPSHOT",
    name: str | None = None,
    extra_deps: str = "",
) -> None:
    name_block = f"<name>{name}</name>" if name else ""
    pom = textwrap.dedent(
        f"""\
        <?xml version="1.0" encoding="UTF-8"?>
        <project xmlns="http://maven.apache.org/POM/4.0.0">
          <modelVersion>4.0.0</modelVersion>
          <groupId>{group_id}</groupId>
          <artifactId>{artifact_id}</artifactId>
          <version>{version}</version>
          {name_block}
          <dependencies>
            {extra_deps}
          </dependencies>
        </project>
        """
    )
    (project / "pom.xml").write_text(pom, encoding="utf-8")


def _write_app_yml(project: pathlib.Path, body: str) -> None:
    resources = project / "src" / "main" / "resources"
    resources.mkdir(parents=True, exist_ok=True)
    (resources / "application.yml").write_text(body, encoding="utf-8")


# ---------------------------------------------------------------------------
# Slug derivation
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "artifact, expected",
    [
        ("shipping-shell", "shipping"),
        ("acme-portal", "acme"),
        ("orders-shell-mdi", "orders"),
        ("plain-app", "plain"),
        ("billing-uiadapter", "billing"),
        ("standalone", "standalone"),
    ],
)
def test_derive_slug(artifact, expected):
    assert etp.derive_slug(artifact) == expected


# ---------------------------------------------------------------------------
# Dialect detection
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "url, expected",
    [
        ("jdbc:postgresql://localhost:5432/db", "postgres"),
        ("jdbc:mysql://db.local:3306/app", "mysql"),
        ("jdbc:hsqldb:mem:test", "hsqldb"),
        ("jdbc:h2:mem:test", "h2"),
        ("jdbc:oracle:thin:@host:1521:xe", "oracle"),
        ("jdbc:sqlserver://host:1433;databaseName=db", "mssql"),
        (None, "postgres"),  # safe default
        ("", "postgres"),
    ],
)
def test_detect_dialect(url, expected):
    assert etp.detect_dialect(url) == expected


# ---------------------------------------------------------------------------
# Full build_profile cases — fixture-based
# ---------------------------------------------------------------------------

def test_build_profile_jakarta_postgres(tmp_path):
    proj = tmp_path / "shipping-shell"
    proj.mkdir()
    _write_pom(
        proj,
        group_id="com.nexacro.uiadapter",
        artifact_id="shipping-shell",
        name="shipping-shell",
        extra_deps="<dependency><groupId>jakarta.servlet</groupId><artifactId>jakarta.servlet-api</artifactId></dependency>",
    )
    _write_app_yml(
        proj,
        textwrap.dedent(
            """\
            spring:
              datasource:
                url: jdbc:postgresql://db.acme.internal:5432/shipping
                username: postgres
                password: postgres
            mybatis:
              type-aliases-package: com.nexacro.uiadapter.shipping.domain
            """
        ),
    )

    profile = etp.build_profile(proj)

    assert profile["version"] == 1
    assert profile["customer"]["slug"] == "shipping"
    assert profile["customer"]["status"] == "draft"
    assert profile["ddl"]["dialect"] == "postgres"
    assert profile["mybatis"]["uia_namespace"] == "jakarta"
    assert profile["mybatis"]["project_root_pkg"] == "com.nexacro.uiadapter"
    assert profile["defaults"]["lane"] == "jakarta"
    assert profile["overlay"]["maven"]["group_id"] == "com.nexacro.uiadapter"
    assert profile["overlay"]["maven"]["version"] == "0.1.0-SNAPSHOT"
    # Env placeholders use uppercased slug
    assert profile["datasource"]["username"] == "${SHIPPING_DB_USER}"
    assert profile["datasource"]["host"] == "db.acme.internal"
    assert profile["datasource"]["port"] == 5432
    assert profile["datasource"]["db"] == "shipping"


def test_build_profile_javax_mysql(tmp_path):
    proj = tmp_path / "legacy-app"
    proj.mkdir()
    _write_pom(
        proj,
        group_id="com.legacy",
        artifact_id="legacy-app",
        name="legacy-app",
        extra_deps="<dependency><groupId>javax.servlet</groupId><artifactId>servlet-api</artifactId></dependency>",
    )
    _write_app_yml(
        proj,
        textwrap.dedent(
            """\
            spring:
              datasource:
                url: jdbc:mysql://mysql.local:3306/legacy
            """
        ),
    )
    profile = etp.build_profile(proj)
    assert profile["customer"]["slug"] == "legacy"
    assert profile["ddl"]["dialect"] == "mysql"
    assert profile["defaults"]["lane"] == "javax"
    assert profile["auth"]["lane"] == "javax"


def test_build_profile_hsqldb_no_app_yml(tmp_path):
    """No application.yml — still produces valid profile with defaults."""
    proj = tmp_path / "tiny"
    proj.mkdir()
    _write_pom(proj, group_id="com.tiny", artifact_id="tiny")
    profile = etp.build_profile(proj)
    assert profile["customer"]["slug"] == "tiny"
    assert profile["ddl"]["dialect"] == "postgres"  # safe default when URL missing
    assert profile["datasource"]["host"] == "localhost"


def test_build_profile_missing_pom(tmp_path):
    proj = tmp_path / "empty"
    proj.mkdir()
    with pytest.raises(FileNotFoundError, match="pom.xml not found"):
        etp.build_profile(proj)


def test_build_profile_invalid_slug_override(tmp_path):
    proj = tmp_path / "x"
    proj.mkdir()
    _write_pom(proj, group_id="com.x", artifact_id="x")
    with pytest.raises(ValueError, match="not a valid ASCII slug"):
        etp.build_profile(proj, slug_override="고객사")


# ---------------------------------------------------------------------------
# Round-trip through load_customer_profile (G-62/G-63 schema contract)
# ---------------------------------------------------------------------------

def test_output_roundtrips_through_loader(tmp_path, monkeypatch):
    """Extractor output must satisfy `load_customer_profile` v1 contract."""
    proj = tmp_path / "rounded-shell"
    proj.mkdir()
    _write_pom(
        proj,
        group_id="com.rounded.uiadapter",
        artifact_id="rounded-shell",
        name="rounded-shell",
        extra_deps="<dependency><groupId>jakarta.servlet</groupId><artifactId>x</artifactId></dependency>",
    )
    _write_app_yml(
        proj,
        "spring:\n  datasource:\n    url: jdbc:postgresql://h:5432/d\n",
    )

    profiles_dir = tmp_path / "profiles"
    profiles_dir.mkdir()
    # Use --print path then write manually so we exercise dump_profile()
    profile = etp.build_profile(proj)
    out = profiles_dir / "rounded.yaml"
    out.write_text(etp.dump_profile(profile), encoding="utf-8")

    loaded = load_customer_profile("rounded", profiles_root=profiles_dir)
    assert loaded["version"] == 1
    assert loaded["customer"]["slug"] == "rounded"
    assert loaded["ddl"]["dialect"] == "postgres"
    # Env interpolation kept ${...} literal because env not set
    monkeypatch.delenv("ROUNDED_DB_USER", raising=False)
    assert loaded["datasource"]["username"] == "${ROUNDED_DB_USER}"


def test_dump_profile_header_present():
    profile = {"version": 1, "customer": {"slug": "x"}}
    text = etp.dump_profile(profile)
    assert text.startswith("# Auto-extracted")
    assert "Growth-70" in text


# ---------------------------------------------------------------------------
# CLI entry point — --print + --force semantics
# ---------------------------------------------------------------------------

def test_cli_print_writes_to_stdout(tmp_path, capsys):
    proj = tmp_path / "x-shell"
    proj.mkdir()
    _write_pom(proj, group_id="com.x", artifact_id="x-shell")
    rc = etp.main([str(proj), "--print"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "version: 1" in out
    assert "slug: x" in out


def test_cli_refuses_to_clobber(tmp_path, capsys):
    proj = tmp_path / "y-shell"
    proj.mkdir()
    _write_pom(proj, group_id="com.y", artifact_id="y-shell")
    out_path = tmp_path / "y.yaml"
    out_path.write_text("preexisting", encoding="utf-8")
    rc = etp.main([str(proj), "--out", str(out_path)])
    assert rc == 1
    assert "already exists" in capsys.readouterr().err
    # --force overwrites
    rc2 = etp.main([str(proj), "--out", str(out_path), "--force"])
    assert rc2 == 0
    assert out_path.read_text(encoding="utf-8").startswith("# Auto-extracted")


def test_cli_rejects_missing_project(tmp_path, capsys):
    rc = etp.main([str(tmp_path / "does-not-exist"), "--print"])
    assert rc == 2
    assert "not a directory" in capsys.readouterr().err
