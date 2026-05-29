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
    with pytest.raises(FileNotFoundError, match="No pom.xml or build.gradle"):
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


# ---------------------------------------------------------------------------
# Growth-78 (M5 Slice C-b) — Gradle input
# ---------------------------------------------------------------------------

def _write_gradle_groovy(
    project: pathlib.Path,
    *,
    group: str,
    version: str = "1.0.0-SNAPSHOT",
    root_name: str | None = None,
    extra_deps: str = "",
) -> None:
    body = textwrap.dedent(
        f"""\
        plugins {{
            id 'org.springframework.boot' version '3.1.0'
            id 'java'
        }}
        group = '{group}'
        version = '{version}'
        dependencies {{
            implementation 'org.springframework.boot:spring-boot-starter-web'
            {extra_deps}
        }}
        """
    )
    (project / "build.gradle").write_text(body, encoding="utf-8")
    if root_name:
        (project / "settings.gradle").write_text(
            f"rootProject.name = '{root_name}'\n", encoding="utf-8"
        )


def _write_gradle_kts(
    project: pathlib.Path,
    *,
    group: str,
    version: str = "1.0.0-SNAPSHOT",
    root_name: str | None = None,
    extra_deps: str = "",
) -> None:
    body = textwrap.dedent(
        f"""\
        plugins {{
            id("org.springframework.boot") version "3.1.0"
            java
        }}
        group = "{group}"
        version = "{version}"
        dependencies {{
            implementation("org.springframework.boot:spring-boot-starter-web")
            {extra_deps}
        }}
        """
    )
    (project / "build.gradle.kts").write_text(body, encoding="utf-8")
    if root_name:
        (project / "settings.gradle.kts").write_text(
            f"rootProject.name = \"{root_name}\"\n", encoding="utf-8"
        )


def test_gradle_groovy_jakarta_postgres(tmp_path):
    proj = tmp_path / "shipping-shell"
    proj.mkdir()
    _write_gradle_groovy(
        proj,
        group="com.acme.uiadapter",
        root_name="shipping-shell",
        extra_deps="implementation 'jakarta.servlet:jakarta.servlet-api'",
    )
    _write_app_yml(
        proj,
        textwrap.dedent(
            """\
            spring:
              datasource:
                url: jdbc:postgresql://db.acme.internal:5432/shipping
            mybatis:
              type-aliases-package: com.acme.uiadapter.shipping.domain
            """
        ),
    )
    profile = etp.build_profile(proj)
    assert profile["customer"]["slug"] == "shipping"
    assert profile["ddl"]["dialect"] == "postgres"
    assert profile["defaults"]["lane"] == "jakarta"
    assert profile["overlay"]["maven"]["group_id"] == "com.acme.uiadapter"
    assert profile["overlay"]["maven"]["version"] == "1.0.0-SNAPSHOT"
    assert profile["overlay"]["shell_app_id"] == "shipping-shell"


def test_gradle_kts_jakarta_mysql(tmp_path):
    proj = tmp_path / "billing-portal"
    proj.mkdir()
    _write_gradle_kts(
        proj,
        group="com.bill.uiadapter",
        root_name="billing-portal",
        extra_deps="implementation(\"jakarta.servlet:jakarta.servlet-api\")",
    )
    _write_app_yml(
        proj,
        "spring:\n  datasource:\n    url: jdbc:mysql://db.local:3306/billing\n",
    )
    profile = etp.build_profile(proj)
    assert profile["customer"]["slug"] == "billing"
    assert profile["ddl"]["dialect"] == "mysql"
    assert profile["defaults"]["lane"] == "jakarta"


def test_gradle_groovy_javax_no_settings_uses_dir_name(tmp_path):
    proj = tmp_path / "legacy-app"
    proj.mkdir()
    # No settings.gradle, no jakarta dep — should pick javax + dir name
    body = textwrap.dedent(
        """\
        plugins {
            id 'org.springframework.boot' version '2.7.18'
            id 'java'
        }
        group = 'com.legacy'
        version = '0.5.0'
        dependencies {
            implementation 'javax.servlet:servlet-api'
        }
        """
    )
    (proj / "build.gradle").write_text(body, encoding="utf-8")
    profile = etp.build_profile(proj)
    assert profile["customer"]["slug"] == "legacy"
    assert profile["defaults"]["lane"] == "javax"
    assert profile["overlay"]["shell_app_id"] == "legacy-app"
    assert profile["overlay"]["maven"]["version"] == "0.5.0"


def test_gradle_kts_takes_precedence_over_groovy(tmp_path):
    """If both build.gradle.kts and build.gradle exist, KTS wins."""
    proj = tmp_path / "dual-app"
    proj.mkdir()
    (proj / "build.gradle").write_text(
        "group = 'com.groovy.wrong'\nversion = '0.0.1'\n", encoding="utf-8"
    )
    (proj / "build.gradle.kts").write_text(
        'group = "com.kts.right"\nversion = "9.9.9"\n', encoding="utf-8"
    )
    profile = etp.build_profile(proj)
    assert profile["overlay"]["maven"]["group_id"] == "com.kts.right"
    assert profile["overlay"]["maven"]["version"] == "9.9.9"


def test_pom_takes_precedence_over_gradle(tmp_path):
    """If both pom.xml and build.gradle exist, pom wins (Maven-first contract)."""
    proj = tmp_path / "mixed-app"
    proj.mkdir()
    _write_pom(proj, group_id="com.maven", artifact_id="mixed-app")
    _write_gradle_groovy(proj, group="com.gradle.ignored", root_name="should-not-win")
    profile = etp.build_profile(proj)
    assert profile["overlay"]["maven"]["group_id"] == "com.maven"
    assert profile["customer"]["slug"] == "mixed"


def test_gradle_roundtrips_through_loader(tmp_path, monkeypatch):
    """Gradle-extracted profile must satisfy load_customer_profile v1 contract."""
    proj = tmp_path / "round-shell"
    proj.mkdir()
    _write_gradle_kts(
        proj,
        group="com.round.uiadapter",
        root_name="round-shell",
        extra_deps='implementation("jakarta.servlet:jakarta.servlet-api")',
    )
    _write_app_yml(proj, "spring:\n  datasource:\n    url: jdbc:postgresql://h:5432/r\n")
    profiles_dir = tmp_path / "profiles"
    profiles_dir.mkdir()
    profile = etp.build_profile(proj)
    (profiles_dir / "round.yaml").write_text(etp.dump_profile(profile), encoding="utf-8")
    loaded = load_customer_profile("round", profiles_root=profiles_dir)
    assert loaded["version"] == 1
    assert loaded["mybatis"]["uia_namespace"] == "jakarta"
    monkeypatch.delenv("ROUND_DB_USER", raising=False)
    assert loaded["datasource"]["username"] == "${ROUND_DB_USER}"


# ---------------------------------------------------------------------------
# Growth-81 (M5 Slice C-d) — Gradle multi-module include parsing
# ---------------------------------------------------------------------------

def test_parse_includes_groovy_single_line():
    """include 'svc:api', 'svc:web' on one line → both captured."""
    text = "include 'svc:api', 'svc:web'\n"
    assert etp._parse_includes(text) == ["svc:api", "svc:web"]


def test_parse_includes_groovy_multiple_lines():
    """Two separate include lines → both captured, order preserved."""
    text = "include 'alpha:core'\ninclude 'alpha:web'\n"
    result = etp._parse_includes(text)
    assert "alpha:core" in result
    assert "alpha:web" in result
    assert len(result) == 2


def test_parse_includes_kotlin_dsl():
    """include(\":svc:api\", \":svc:web\") Kotlin form → colon-prefix stripped."""
    text = 'include(":svc:api", ":svc:web")\n'
    assert etp._parse_includes(text) == ["svc:api", "svc:web"]


def test_parse_gradle_no_includes_omits_modules_key(tmp_path):
    """Single-module project without include → 'modules' key absent (backcompat)."""
    proj = tmp_path / "single-app"
    proj.mkdir()
    _write_gradle_groovy(proj, group="com.single", root_name="single-app")
    build = proj / "build.gradle"
    result = etp.parse_gradle(build)
    assert "modules" not in result


def test_extract_modules_reads_submodule_group(tmp_path):
    """Sub-module build.gradle with group → base_package populated."""
    proj = tmp_path / "multi-root"
    proj.mkdir()
    # settings.gradle with include
    (proj / "settings.gradle").write_text(
        "rootProject.name = 'multi-root'\ninclude 'svc:api'\n",
        encoding="utf-8",
    )
    # root build.gradle
    (proj / "build.gradle").write_text(
        "group = 'com.acme'\nversion = '1.0.0'\n",
        encoding="utf-8",
    )
    # sub-module directory + build.gradle
    sub_dir = proj / "svc" / "api"
    sub_dir.mkdir(parents=True)
    (sub_dir / "build.gradle").write_text(
        "group = 'com.acme.api'\nversion = '1.0.0'\n",
        encoding="utf-8",
    )
    modules = etp._extract_modules(proj)
    assert len(modules) == 1
    assert modules[0]["slug"] == "api"
    assert modules[0]["gradle_path"] == "svc:api"
    assert modules[0]["base_package"] == "com.acme.api"


def test_build_profile_attaches_modules_for_multimodule_gradle(tmp_path):
    """Full build_profile() on multi-module fixture → profile['modules'] present."""
    proj = tmp_path / "mm-root"
    proj.mkdir()
    (proj / "settings.gradle").write_text(
        "rootProject.name = 'mm-root'\ninclude 'svc:api', 'svc:web'\n",
        encoding="utf-8",
    )
    (proj / "build.gradle").write_text(
        "group = 'com.mm'\nversion = '1.0.0'\n",
        encoding="utf-8",
    )
    for seg in ("api", "web"):
        sub = proj / "svc" / seg
        sub.mkdir(parents=True)
        (sub / "build.gradle").write_text(
            f"group = 'com.mm.{seg}'\n",
            encoding="utf-8",
        )
    profile = etp.build_profile(proj)
    assert "modules" in profile
    slugs = [m["slug"] for m in profile["modules"]]
    assert "api" in slugs
    assert "web" in slugs
    paths = [m["gradle_path"] for m in profile["modules"]]
    assert "svc:api" in paths
    assert "svc:web" in paths
