# tests/test_nexacro_shell_overlay.py
"""Tests for nexacro_shell_overlay (Growth-16 P2)."""
import os
import pathlib
import pytest

import ui_overlay_registry
import stage5_overlay  # noqa: F401 — registers nexacro-shell via import chain


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
NEXACRO_SKILL = (
    REPO_ROOT.parent
    / "andrej-karpathy-rdb-nexacro"
    / ".claude" / "skills" / "karpathy-rdb-nexacro" / "patterns"
)


pytestmark = pytest.mark.skipif(
    not NEXACRO_SKILL.exists(),
    reason="nexacro skill sibling repo not present",
)


def _common_kwargs(target_dir: pathlib.Path) -> dict:
    return dict(
        out_dir=str(target_dir / "out"),
        target_dir=str(target_dir),
        domain_slug="shipping",
        domain_label="배송관리",
        service_pascal="Shipping",
        blueprint_entities=[
            {"name": "delivery", "label_ko": "배송"},
            {"name": "courier", "label_ko": "택배사"},
        ],
        nexacro_skill_root=str(NEXACRO_SKILL),
        shell_variant="MDI",
        shell_branding={"app_title": "Shipping App", "brand_text": "배송"},
        shell_login={"title": "Login"},
    )


def test_shell_adapter_is_registered():
    assert "nexacro-shell" in ui_overlay_registry.registered()


def test_shell_overlay_writes_5_frames_typedef_xadl(tmp_path):
    report = ui_overlay_registry.dispatch(
        "nexacro-shell", **_common_kwargs(tmp_path)
    )
    assert report["shell_variant"] == "MDI"
    pkg = tmp_path / "nxui" / "packageN"
    frames = pkg / "frame"
    for name in ("frameMain.xfdl", "frameMDI.xfdl", "frameLeft.xfdl", "frameTop.xfdl", "frameLogin.xfdl"):
        assert (frames / name).exists(), f"missing {name}"
    assert (pkg / "typedefinition.xml").exists()
    assert (pkg / "packageN.xadl").exists()
    assert len(report["frames_rendered"]) == 5
    assert report["menu_entries"] == 2


def test_shell_overlay_renders_menu_from_entities(tmp_path):
    ui_overlay_registry.dispatch("nexacro-shell", **_common_kwargs(tmp_path))
    left = (tmp_path / "nxui" / "packageN" / "frame" / "frameLeft.xfdl").read_text(
        encoding="utf-8"
    )
    # Entities flow into ds_menu rows when shell_menu is empty
    assert "<Col id=\"menuId\">delivery</Col>" in left
    assert "<Col id=\"label\">배송</Col>" in left
    assert "shipping::delivery.xfdl" in left


def test_shell_overlay_conflict_aborts_without_force(tmp_path):
    kwargs = _common_kwargs(tmp_path)
    ui_overlay_registry.dispatch("nexacro-shell", **kwargs)
    with pytest.raises(RuntimeError) as exc:
        ui_overlay_registry.dispatch("nexacro-shell", **kwargs)
    assert "would overwrite" in str(exc.value)


def test_shell_overlay_sdi_variant_uses_frame_sdi(tmp_path):
    kwargs = _common_kwargs(tmp_path)
    kwargs["shell_variant"] = "SDI"
    report = ui_overlay_registry.dispatch("nexacro-shell", **kwargs)
    assert report["shell_variant"] == "SDI"
    sdi = tmp_path / "nxui" / "packageN" / "frame" / "frameSDI.xfdl"
    assert sdi.exists()
    body = sdi.read_text(encoding="utf-8")
    assert "frameSDI" in body
    assert "divWork" in body
    # MDI frame must NOT have been rendered for SDI variant
    assert not (tmp_path / "nxui" / "packageN" / "frame" / "frameMDI.xfdl").exists()


def test_shell_overlay_frame_filenames_are_case_exact(tmp_path):
    """Regression: Windows filesystem is case-insensitive, so ``Path.exists``
    happily resolves ``frameMdi.xfdl`` when the runtime looks up
    ``frameMDI.xfdl``. Linux WAR deployment is case-sensitive — a mismatch
    breaks the workFrame reference inside frameMain.xfdl.

    Enumerate the directory via ``os.listdir`` (case-preserving) and assert
    every produced filename matches the expected casing exactly, AND that
    frameMain.xfdl's ``work_frame`` value names a real file in the dir.
    """
    ui_overlay_registry.dispatch("nexacro-shell", **_common_kwargs(tmp_path))
    frame_dir = tmp_path / "nxui" / "packageN" / "frame"
    actual = set(os.listdir(frame_dir))
    expected_mdi = {
        "frameMain.xfdl", "frameMDI.xfdl",
        "frameLeft.xfdl", "frameTop.xfdl", "frameLogin.xfdl",
    }
    assert expected_mdi.issubset(actual), (
        f"case-exact mismatch — expected {expected_mdi}, got {actual}"
    )
    # The buggy past output "frameMdi.xfdl" must NOT exist
    assert "frameMdi.xfdl" not in actual, (
        "frame template key 'frame_mdi' must render as 'frameMDI.xfdl' "
        "(variant acronym preserved), not 'frameMdi.xfdl'"
    )

    # And frameMain.xfdl's workFrame must reference a real on-disk file
    main_text = (frame_dir / "frameMain.xfdl").read_text(encoding="utf-8")
    assert "frameMDI.xfdl" in main_text, "frameMain must reference frameMDI.xfdl"
    # Cross-check: the referenced name resolves case-exactly
    assert "frameMDI.xfdl" in actual


def test_shell_overlay_sdi_frame_filename_is_case_exact(tmp_path):
    """Same regression for SDI variant — frame_sdi → frameSDI.xfdl."""
    kwargs = _common_kwargs(tmp_path)
    kwargs["shell_variant"] = "SDI"
    ui_overlay_registry.dispatch("nexacro-shell", **kwargs)
    frame_dir = tmp_path / "nxui" / "packageN" / "frame"
    actual = set(os.listdir(frame_dir))
    assert "frameSDI.xfdl" in actual, f"missing frameSDI.xfdl in {actual}"
    assert "frameSdi.xfdl" not in actual, "frame_sdi must render as frameSDI.xfdl"


def test_shell_overlay_emits_buildable_maven_project(tmp_path):
    """Growth-17b: the standalone shell must scaffold pom.xml,
    Application.java, and application.yml so `mvn package` produces a
    Spring Boot fat-jar that bundles the rendered nxui/packageN as a static
    resource (BACKEND_URL → /uiadapter/, same-origin uiadapter REST).
    """
    kwargs = _common_kwargs(tmp_path)
    kwargs["target_pkg_prefix"] = "com.acme.shipping"
    kwargs["maven_group_id"] = "com.acme"
    kwargs["maven_artifact_id"] = "shipping-shell"
    kwargs["maven_version"] = "0.2.0-SNAPSHOT"
    report = ui_overlay_registry.dispatch("nexacro-shell", **kwargs)

    pom = tmp_path / "pom.xml"
    app = tmp_path / "src" / "main" / "java" / "com" / "acme" / "shipping" / "Application.java"
    yml = tmp_path / "src" / "main" / "resources" / "application.yml"
    assert pom.exists(), "pom.xml missing"
    assert app.exists(), f"Application.java missing at {app}"
    assert yml.exists(), "application.yml missing"

    pom_text = pom.read_text(encoding="utf-8")
    assert "<groupId>com.acme</groupId>" in pom_text
    assert "<artifactId>shipping-shell</artifactId>" in pom_text
    assert "<version>0.2.0-SNAPSHOT</version>" in pom_text
    assert "com.acme.shipping.Application" in pom_text  # mainClass
    # Jinja must have escaped the Maven {{*}} delimiter and {{BACKEND_URL}}
    assert "{{*}}" in pom_text
    assert "{{BACKEND_URL}}" in pom_text
    # nxui bundled as Boot static resource
    assert "nxui/packageN" in pom_text
    assert "static/packageN" in pom_text

    app_text = app.read_text(encoding="utf-8")
    assert "package com.acme.shipping;" in app_text
    assert "@SpringBootApplication" in app_text
    assert "@MapperScan(\"com.acme.shipping.shipping.mapper\")" in app_text

    yml_text = yml.read_text(encoding="utf-8")
    assert "context-path: /uiadapter" in yml_text
    assert "type-aliases-package: com.acme.shipping.shipping.domain" in yml_text
    assert "mapper-locations: classpath:mybatis/mapper/**/*.xml" in yml_text

    # Growth-17c: NexacroBase POJO required by Stage 3 nexacro-lane entities
    nb = tmp_path / "src" / "main" / "java" / "com" / "acme" / "shipping" / "shipping" / "domain" / "NexacroBase.java"
    assert nb.exists(), f"NexacroBase.java missing at {nb}"
    nb_text = nb.read_text(encoding="utf-8")
    assert "package com.acme.shipping.shipping.domain;" in nb_text
    assert "implements DataSetRowTypeAccessor" in nb_text

    # Report keys (4 build files now: pom, Application, application.yml, NexacroBase)
    assert len(report["build_files_rendered"]) == 4
    assert any(p.endswith("pom.xml") for p in report["build_files_rendered"])
    assert any(p.endswith("Application.java") for p in report["build_files_rendered"])
    assert any(p.endswith("application.yml") for p in report["build_files_rendered"])
    assert any(p.endswith("NexacroBase.java") for p in report["build_files_rendered"])


def test_shell_overlay_extra_services_appended(tmp_path):
    kwargs = _common_kwargs(tmp_path)
    kwargs["shell_extra_services"] = [
        {"prefixid": "auth", "name": "auth", "url": "./services/auth/"}
    ]
    ui_overlay_registry.dispatch("nexacro-shell", **kwargs)
    td = (tmp_path / "nxui" / "packageN" / "typedefinition.xml").read_text(
        encoding="utf-8"
    )
    assert 'prefixid="auth"' in td
    assert 'url="./services/auth/"' in td


# --- Growth-18: dialect-aware shell scaffolding ---------------------------


def _build_kwargs(tmp_path: pathlib.Path, dialect: str) -> dict:
    kwargs = _common_kwargs(tmp_path)
    kwargs["target_pkg_prefix"] = "com.acme.shipping"
    kwargs["maven_group_id"] = "com.acme"
    kwargs["maven_artifact_id"] = "shipping-shell"
    kwargs["maven_version"] = "0.2.0-SNAPSHOT"
    kwargs["dialect"] = dialect
    return kwargs


def test_shell_overlay_hsqldb_default_keeps_legacy_datasource(tmp_path):
    """No `dialect` kwarg should preserve historical HSQLDB output (back-compat)."""
    kwargs = _common_kwargs(tmp_path)
    kwargs["target_pkg_prefix"] = "com.acme.shipping"
    kwargs["maven_group_id"] = "com.acme"
    kwargs["maven_artifact_id"] = "shipping-shell"
    ui_overlay_registry.dispatch("nexacro-shell", **kwargs)
    yml = (tmp_path / "src" / "main" / "resources" / "application.yml").read_text(encoding="utf-8")
    assert "jdbc:hsqldb:mem:shipping" in yml
    assert "org.hsqldb.jdbc.JDBCDriver" in yml
    assert "mode: always" in yml
    pom = (tmp_path / "pom.xml").read_text(encoding="utf-8")
    assert "<artifactId>hsqldb</artifactId>" in pom
    assert "<groupId>org.hsqldb</groupId>" in pom


def test_shell_overlay_postgres_dialect_emits_postgres_yml_and_pom(tmp_path):
    """The contract bug Growth-18 caught — `--dialect postgres` MUST flow into
    application.yml AND pom.xml. Otherwise the rendered scaffold ships an
    hsqldb-only Spring Boot app even though Stage 2 emitted Postgres DDL."""
    ui_overlay_registry.dispatch("nexacro-shell", **_build_kwargs(tmp_path, "postgres"))
    yml = (tmp_path / "src" / "main" / "resources" / "application.yml").read_text(encoding="utf-8")
    assert "jdbc:postgresql://localhost:5432/shipping" in yml
    assert "org.postgresql.Driver" in yml
    assert "username: postgres" in yml
    # mode: embedded is the safe default for real DBs (user owns migrations)
    assert "mode: embedded" in yml
    # No HSQLDB JDBC residue (comment text about HSQLDB is fine)
    assert "jdbc:hsqldb" not in yml.lower()
    assert "org.hsqldb.jdbc.jdbcdriver" not in yml.lower()

    pom = (tmp_path / "pom.xml").read_text(encoding="utf-8")
    assert "<groupId>org.postgresql</groupId>" in pom
    assert "<artifactId>postgresql</artifactId>" in pom
    assert "<postgresql.version>" in pom
    # No HSQLDB driver dep should be left over
    assert "<artifactId>hsqldb</artifactId>" not in pom


def test_shell_overlay_mysql_dialect_emits_mysql_yml_and_pom(tmp_path):
    ui_overlay_registry.dispatch("nexacro-shell", **_build_kwargs(tmp_path, "mysql"))
    yml = (tmp_path / "src" / "main" / "resources" / "application.yml").read_text(encoding="utf-8")
    assert "jdbc:mysql://localhost:3306/shipping" in yml
    assert "com.mysql.cj.jdbc.Driver" in yml
    assert "mode: embedded" in yml
    assert "jdbc:hsqldb" not in yml.lower()

    pom = (tmp_path / "pom.xml").read_text(encoding="utf-8")
    assert "<groupId>com.mysql</groupId>" in pom
    assert "<artifactId>mysql-connector-j</artifactId>" in pom
    assert "<mysql.connector.version>" in pom
    assert "<artifactId>hsqldb</artifactId>" not in pom


def test_shell_overlay_unknown_dialect_falls_back_to_hsqldb(tmp_path):
    """Defensive: unknown dialect string should not crash — fall back to hsqldb
    (the legacy default). The Stage 2 CLI already constrains choices, so this
    only fires if a programmatic caller passes garbage."""
    ui_overlay_registry.dispatch(
        "nexacro-shell", **_build_kwargs(tmp_path, "snowflake")
    )
    yml = (tmp_path / "src" / "main" / "resources" / "application.yml").read_text(encoding="utf-8")
    assert "jdbc:hsqldb:mem:shipping" in yml
