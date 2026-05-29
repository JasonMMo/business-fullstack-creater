"""Growth-71 — tests for scripts/emit_ops_pack.py."""
from __future__ import annotations

import pathlib
import textwrap

import pytest

from scripts import emit_ops_pack as eop


# ---------------------------------------------------------------------------
# Fixture builder — minimal scaffold output (just enough pom.xml to inspect)
# ---------------------------------------------------------------------------

def _write_scaffold(
    out: pathlib.Path,
    *,
    artifact_id: str = "shipping-shell",
    version: str = "0.1.0-SNAPSHOT",
    packaging: str = "war",
    lane: str = "jakarta",
    dialect: str = "postgres",
) -> pathlib.Path:
    shell = out / "shell"
    shell.mkdir(parents=True)
    (shell / "src").mkdir()
    lane_dep = (
        "<dependency><groupId>jakarta.servlet</groupId><artifactId>x</artifactId></dependency>"
        if lane == "jakarta"
        else "<dependency><groupId>javax.servlet</groupId><artifactId>x</artifactId></dependency>"
    )
    dialect_dep = {
        "postgres": "<dependency><groupId>org.postgresql</groupId><artifactId>postgresql</artifactId></dependency>",
        "mysql": "<dependency><groupId>com.mysql</groupId><artifactId>mysql-connector-j</artifactId></dependency>",
        "hsqldb": "<dependency><groupId>org.hsqldb</groupId><artifactId>hsqldb</artifactId></dependency>",
    }[dialect]
    (shell / "pom.xml").write_text(
        textwrap.dedent(
            f"""\
            <?xml version="1.0" encoding="UTF-8"?>
            <project xmlns="http://maven.apache.org/POM/4.0.0">
              <modelVersion>4.0.0</modelVersion>
              <groupId>com.example</groupId>
              <artifactId>{artifact_id}</artifactId>
              <version>{version}</version>
              <packaging>{packaging}</packaging>
              <dependencies>
                {lane_dep}
                {dialect_dep}
              </dependencies>
            </project>
            """
        ),
        encoding="utf-8",
    )
    return shell


# ---------------------------------------------------------------------------
# Inspection
# ---------------------------------------------------------------------------

def test_inspect_jakarta_postgres_war(tmp_path):
    _write_scaffold(tmp_path)
    info = eop.inspect_scaffold(tmp_path / "shell")
    assert info["artifact_id"] == "shipping-shell"
    assert info["packaging"] == "war"
    assert info["lane"] == "jakarta"
    assert info["dialect"] == "postgres"


def test_inspect_javax_mysql_jar(tmp_path):
    _write_scaffold(tmp_path, packaging="jar", lane="javax", dialect="mysql")
    info = eop.inspect_scaffold(tmp_path / "shell")
    assert info["packaging"] == "jar"
    assert info["lane"] == "javax"
    assert info["dialect"] == "mysql"


def test_inspect_missing_pom_raises(tmp_path):
    (tmp_path / "shell").mkdir()
    with pytest.raises(FileNotFoundError, match="pom.xml"):
        eop.inspect_scaffold(tmp_path / "shell")


# ---------------------------------------------------------------------------
# Dockerfile rendering
# ---------------------------------------------------------------------------

def test_dockerfile_war_jakarta_uses_tomcat10(tmp_path):
    _write_scaffold(tmp_path, packaging="war", lane="jakarta")
    info = eop.inspect_scaffold(tmp_path / "shell")
    dockerfile = eop.render_dockerfile(info)
    assert "FROM tomcat:10.1" in dockerfile
    assert "FROM maven:3.9-eclipse-temurin-17 AS builder" in dockerfile
    assert "shipping-shell-0.1.0-SNAPSHOT.war" in dockerfile
    assert "uiadapter.war" in dockerfile


def test_dockerfile_war_javax_uses_tomcat9(tmp_path):
    _write_scaffold(tmp_path, packaging="war", lane="javax")
    info = eop.inspect_scaffold(tmp_path / "shell")
    dockerfile = eop.render_dockerfile(info)
    assert "FROM tomcat:9.0" in dockerfile
    assert "tomcat:10" not in dockerfile


def test_dockerfile_jar_uses_temurin_jre(tmp_path):
    _write_scaffold(tmp_path, packaging="jar")
    info = eop.inspect_scaffold(tmp_path / "shell")
    dockerfile = eop.render_dockerfile(info)
    assert "FROM eclipse-temurin:17-jre" in dockerfile
    assert "ENTRYPOINT" in dockerfile
    assert "app.jar" in dockerfile


# ---------------------------------------------------------------------------
# docker-compose rendering — dialect branching
# ---------------------------------------------------------------------------

def test_compose_postgres_has_db_service_and_volume(tmp_path):
    _write_scaffold(tmp_path, dialect="postgres")
    info = eop.inspect_scaffold(tmp_path / "shell")
    compose = eop.render_compose(info, slug="acme")
    assert "image: postgres:16-alpine" in compose
    assert "ACME_DB_USER" in compose
    assert "depends_on:" in compose
    assert "volumes:" in compose
    assert "pg_isready" in compose


def test_compose_mysql_uses_mysql8(tmp_path):
    _write_scaffold(tmp_path, dialect="mysql")
    info = eop.inspect_scaffold(tmp_path / "shell")
    compose = eop.render_compose(info, slug="legacy")
    assert "image: mysql:8.0" in compose
    assert "LEGACY_DB_USER" in compose
    assert "mysqladmin" in compose


def test_compose_hsqldb_has_no_db_service(tmp_path):
    _write_scaffold(tmp_path, dialect="hsqldb")
    info = eop.inspect_scaffold(tmp_path / "shell")
    compose = eop.render_compose(info, slug="tiny")
    assert "image: postgres" not in compose
    assert "image: mysql" not in compose
    assert "depends_on:" not in compose
    # Still has the app service
    assert "app:" in compose


# ---------------------------------------------------------------------------
# .env rendering
# ---------------------------------------------------------------------------

def test_env_postgres_includes_db_block(tmp_path):
    _write_scaffold(tmp_path, dialect="postgres")
    info = eop.inspect_scaffold(tmp_path / "shell")
    env = eop.render_env_example(info, slug="acme")
    assert "APP_PORT=8080" in env
    assert "ACME_DB_HOST=db" in env
    assert "ACME_DB_PORT=5432" in env


def test_env_mysql_uses_3306(tmp_path):
    _write_scaffold(tmp_path, dialect="mysql")
    info = eop.inspect_scaffold(tmp_path / "shell")
    env = eop.render_env_example(info, slug="legacy")
    assert "LEGACY_DB_PORT=3306" in env


def test_env_hsqldb_skips_db_block(tmp_path):
    _write_scaffold(tmp_path, dialect="hsqldb")
    info = eop.inspect_scaffold(tmp_path / "shell")
    env = eop.render_env_example(info, slug="tiny")
    assert "embedded" in env
    assert "DB_HOST" not in env


# ---------------------------------------------------------------------------
# SOP rendering — Korean runbook
# ---------------------------------------------------------------------------

def test_sop_korean_runbook_present(tmp_path):
    _write_scaffold(tmp_path, dialect="postgres")
    info = eop.inspect_scaffold(tmp_path / "shell")
    sop = eop.render_sop(info, slug="acme")
    assert "배포 SOP — acme" in sop
    assert "docker compose up -d" in sop
    assert "ACME_DB_USER" in sop
    assert "트러블슈팅" in sop


def test_sop_embedded_dialect_skips_db_creds(tmp_path):
    _write_scaffold(tmp_path, dialect="hsqldb")
    info = eop.inspect_scaffold(tmp_path / "shell")
    sop = eop.render_sop(info, slug="tiny")
    assert "embedded" in sop
    assert "TINY_DB_USER" not in sop


# ---------------------------------------------------------------------------
# Profile override
# ---------------------------------------------------------------------------

def test_profile_overrides_slug_and_dialect(tmp_path):
    _write_scaffold(tmp_path, dialect="postgres", artifact_id="shipping-shell")
    profile = {
        "version": 1,
        "customer": {"slug": "acme"},
        "ddl": {"dialect": "mysql"},
    }
    ops = eop.emit(tmp_path, profile=profile, force=True)
    compose = (ops / "docker-compose.yml").read_text(encoding="utf-8")
    env = (ops / ".env.example").read_text(encoding="utf-8")
    sop = (ops / "DEPLOY-SOP.md").read_text(encoding="utf-8")
    # MySQL took effect even though pom signaled postgres
    assert "image: mysql:8.0" in compose
    # ACME slug → env prefix
    assert "ACME_DB_USER" in compose
    assert "ACME_DB_USER" in env
    assert "배포 SOP — acme" in sop


# ---------------------------------------------------------------------------
# emit() driver — all-4-artifact contract + idempotency
# ---------------------------------------------------------------------------

def test_emit_writes_all_four_artifacts(tmp_path):
    _write_scaffold(tmp_path)
    ops = eop.emit(tmp_path)
    assert (ops / "Dockerfile").exists()
    assert (ops / "docker-compose.yml").exists()
    assert (ops / ".env.example").exists()
    assert (ops / "DEPLOY-SOP.md").exists()


def test_emit_refuses_to_clobber_without_force(tmp_path):
    _write_scaffold(tmp_path)
    eop.emit(tmp_path)
    with pytest.raises(FileExistsError, match="--force"):
        eop.emit(tmp_path)
    # --force overwrites
    eop.emit(tmp_path, force=True)


def test_emit_accepts_shell_dir_directly(tmp_path):
    shell = _write_scaffold(tmp_path)
    ops = eop.emit(shell)  # callers may pass the shell/ itself
    assert (ops / "Dockerfile").exists()


# ---------------------------------------------------------------------------
# Profile loader contract
# ---------------------------------------------------------------------------

def test_load_profile_rejects_v2(tmp_path):
    p = tmp_path / "bad.yaml"
    p.write_text("version: 2\ncustomer: {slug: x}\n", encoding="utf-8")
    with pytest.raises(ValueError, match="version: 1"):
        eop._load_profile(p)


def test_load_profile_returns_none_when_path_is_none():
    assert eop._load_profile(None) is None


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def test_cli_writes_ops_dir(tmp_path, capsys):
    _write_scaffold(tmp_path)
    rc = eop.main([str(tmp_path)])
    assert rc == 0
    assert "wrote" in capsys.readouterr().out
    assert (tmp_path / "shell" / "ops" / "Dockerfile").exists()


def test_cli_force_overwrite(tmp_path):
    _write_scaffold(tmp_path)
    assert eop.main([str(tmp_path)]) == 0
    assert eop.main([str(tmp_path)]) == 1  # existing ops/, no --force
    assert eop.main([str(tmp_path), "--force"]) == 0


def test_cli_rejects_missing_out_dir(tmp_path, capsys):
    rc = eop.main([str(tmp_path / "nope")])
    assert rc == 2
    assert "not a directory" in capsys.readouterr().err


# ---------------------------------------------------------------------------
# Growth-76 — Vault Agent sidecar overlay
# ---------------------------------------------------------------------------

def test_vault_off_by_default_emits_only_four_artifacts(tmp_path):
    _write_scaffold(tmp_path)
    ops = eop.emit(tmp_path)
    assert not (ops / "docker-compose.vault.yml").exists()
    assert not (ops / "vault-agent.hcl").exists()
    assert not (ops / "env.tmpl").exists()
    # Original 4 still present
    assert (ops / "Dockerfile").exists()
    assert (ops / "docker-compose.yml").exists()


def test_vault_flag_emits_three_additional_artifacts(tmp_path):
    _write_scaffold(tmp_path, dialect="postgres")
    ops = eop.emit(tmp_path, vault=True)
    assert (ops / "docker-compose.vault.yml").exists()
    assert (ops / "vault-agent.hcl").exists()
    assert (ops / "env.tmpl").exists()


def test_vault_compose_overlay_contains_sidecar_service(tmp_path):
    _write_scaffold(tmp_path)
    ops = eop.emit(tmp_path, vault=True)
    compose = (ops / "docker-compose.vault.yml").read_text(encoding="utf-8")
    assert "vault-agent:" in compose
    assert "hashicorp/vault" in compose
    assert "env_file:" in compose
    assert "vault-secrets/.env" in compose


def test_vault_hcl_uses_approle_and_template(tmp_path):
    _write_scaffold(tmp_path)
    ops = eop.emit(tmp_path, vault=True)
    hcl = (ops / "vault-agent.hcl").read_text(encoding="utf-8")
    assert 'method "approle"' in hcl
    assert "template {" in hcl
    assert "/vault/secrets/.env" in hcl
    assert 'env "VAULT_ADDR"' in hcl


def test_vault_env_tmpl_renders_db_block_for_postgres(tmp_path):
    _write_scaffold(tmp_path, dialect="postgres")
    profile = {"version": 1, "customer": {"slug": "acme"}}
    ops = eop.emit(tmp_path, profile=profile, vault=True)
    tmpl = (ops / "env.tmpl").read_text(encoding="utf-8")
    assert 'secret "secret/data/acme/db"' in tmpl
    assert "ACME_DB_HOST=" in tmpl
    assert ".Data.data.host" in tmpl


def test_vault_env_tmpl_skips_db_for_embedded_dialect(tmp_path):
    _write_scaffold(tmp_path, dialect="hsqldb")
    ops = eop.emit(tmp_path, vault=True)
    tmpl = (ops / "env.tmpl").read_text(encoding="utf-8")
    assert "DB_HOST" not in tmpl
    assert "embedded" in tmpl


def test_vault_sop_appends_section_9(tmp_path):
    _write_scaffold(tmp_path, dialect="postgres")
    profile = {"version": 1, "customer": {"slug": "acme"}}
    ops = eop.emit(tmp_path, profile=profile, vault=True)
    sop = (ops / "DEPLOY-SOP.md").read_text(encoding="utf-8")
    assert "## 9. Vault Agent sidecar" in sop
    assert "vault kv put secret/acme/db" in sop
    assert "docker-compose.vault.yml" in sop


def test_vault_sop_omitted_when_vault_off(tmp_path):
    _write_scaffold(tmp_path)
    ops = eop.emit(tmp_path)
    sop = (ops / "DEPLOY-SOP.md").read_text(encoding="utf-8")
    assert "## 9. Vault Agent sidecar" not in sop


def test_vault_opt_in_via_profile(tmp_path):
    _write_scaffold(tmp_path)
    profile = {
        "version": 1,
        "customer": {"slug": "acme"},
        "overlay": {"vault_agent": True},
    }
    ops = eop.emit(tmp_path, profile=profile)  # vault=False by default
    assert (ops / "vault-agent.hcl").exists()
    assert (ops / "docker-compose.vault.yml").exists()


def test_cli_vault_flag_wires_through(tmp_path):
    _write_scaffold(tmp_path)
    rc = eop.main([str(tmp_path), "--vault"])
    assert rc == 0
    ops = tmp_path / "shell" / "ops"
    assert (ops / "vault-agent.hcl").exists()
    assert (ops / "docker-compose.vault.yml").exists()
    assert (ops / "env.tmpl").exists()


# ---------------------------------------------------------------------------
# Growth-77 — Keycloak/OIDC SSO sidecar overlay
# ---------------------------------------------------------------------------

import json as _json


def test_sso_off_by_default_emits_no_sso_artifacts(tmp_path):
    _write_scaffold(tmp_path)
    ops = eop.emit(tmp_path)
    assert not (ops / "docker-compose.sso.yml").exists()
    assert not (ops / "keycloak-realm.json").exists()
    assert not (ops / ".env.sso.example").exists()


def test_sso_flag_emits_three_additional_artifacts(tmp_path):
    _write_scaffold(tmp_path)
    ops = eop.emit(tmp_path, sso=True)
    assert (ops / "docker-compose.sso.yml").exists()
    assert (ops / "keycloak-realm.json").exists()
    assert (ops / ".env.sso.example").exists()


def test_sso_compose_overlay_contains_keycloak_service(tmp_path):
    _write_scaffold(tmp_path)
    ops = eop.emit(tmp_path, sso=True)
    compose = (ops / "docker-compose.sso.yml").read_text(encoding="utf-8")
    assert "keycloak:" in compose
    assert "quay.io/keycloak/keycloak" in compose
    assert "start-dev" in compose
    assert "OIDC_ISSUER_URI" in compose
    assert "depends_on:" in compose


def test_sso_realm_json_is_valid_with_one_client(tmp_path):
    _write_scaffold(tmp_path)
    profile = {"version": 1, "customer": {"slug": "acme"}}
    ops = eop.emit(tmp_path, profile=profile, sso=True)
    realm = _json.loads((ops / "keycloak-realm.json").read_text(encoding="utf-8"))
    assert realm["realm"] == "acme"
    assert realm["enabled"] is True
    assert len(realm["clients"]) == 1
    client = realm["clients"][0]
    assert client["clientId"] == "acme-app"
    assert client["protocol"] == "openid-connect"
    assert "redirectUris" in client


def test_sso_env_example_contract(tmp_path):
    _write_scaffold(tmp_path)
    profile = {"version": 1, "customer": {"slug": "acme"}}
    ops = eop.emit(tmp_path, profile=profile, sso=True)
    env = (ops / ".env.sso.example").read_text(encoding="utf-8")
    assert "OIDC_ISSUER_URI=http://keycloak:8080/realms/acme" in env
    assert "OIDC_CLIENT_ID=acme-app" in env
    assert "OIDC_CLIENT_SECRET=" in env  # left blank for IT-담당자
    assert "OIDC_REDIRECT_URI=" in env


def test_sso_sop_appends_section_10(tmp_path):
    _write_scaffold(tmp_path)
    profile = {"version": 1, "customer": {"slug": "acme"}}
    ops = eop.emit(tmp_path, profile=profile, sso=True)
    sop = (ops / "DEPLOY-SOP.md").read_text(encoding="utf-8")
    assert "## 10. Keycloak/OIDC SSO sidecar" in sop
    assert "docker-compose.sso.yml" in sop
    assert 'realm "acme"' in sop or 'realm `acme`' in sop or "realm `acme-shell`" in sop or "acme" in sop


def test_sso_sop_omitted_when_sso_off(tmp_path):
    _write_scaffold(tmp_path)
    ops = eop.emit(tmp_path)
    sop = (ops / "DEPLOY-SOP.md").read_text(encoding="utf-8")
    assert "## 10. Keycloak/OIDC SSO sidecar" not in sop


def test_sso_opt_in_via_profile(tmp_path):
    _write_scaffold(tmp_path)
    profile = {
        "version": 1,
        "customer": {"slug": "acme"},
        "overlay": {"sso_keycloak": True},
    }
    ops = eop.emit(tmp_path, profile=profile)  # sso=False by default
    assert (ops / "docker-compose.sso.yml").exists()
    assert (ops / "keycloak-realm.json").exists()


def test_cli_sso_flag_wires_through(tmp_path):
    _write_scaffold(tmp_path)
    rc = eop.main([str(tmp_path), "--sso"])
    assert rc == 0
    ops = tmp_path / "shell" / "ops"
    assert (ops / "docker-compose.sso.yml").exists()
    assert (ops / "keycloak-realm.json").exists()
    assert (ops / ".env.sso.example").exists()


def test_sso_and_vault_can_combine(tmp_path):
    _write_scaffold(tmp_path)
    profile = {"version": 1, "customer": {"slug": "acme"}}
    ops = eop.emit(tmp_path, profile=profile, vault=True, sso=True)
    # Both overlays emit
    assert (ops / "docker-compose.vault.yml").exists()
    assert (ops / "docker-compose.sso.yml").exists()
    sop = (ops / "DEPLOY-SOP.md").read_text(encoding="utf-8")
    assert "## 9. Vault Agent sidecar" in sop
    assert "## 10. Keycloak/OIDC SSO sidecar" in sop


# ---------------------------------------------------------------------------
# Growth-80 — Multi-client realm + LDAP federation
# ---------------------------------------------------------------------------


def test_sso_default_single_client_backcompat(tmp_path):
    # Growth-77 backcompat: no overlay.sso_clients -> realm has exactly 1 client named {slug}-app
    _write_scaffold(tmp_path)
    profile = {"version": 1, "customer": {"slug": "acme"}}
    ops = eop.emit(tmp_path, profile=profile, sso=True)
    realm = _json.loads((ops / "keycloak-realm.json").read_text(encoding="utf-8"))
    assert len(realm["clients"]) == 1
    assert realm["clients"][0]["clientId"] == "acme-app"


def test_sso_multi_client_via_profile(tmp_path):
    # Growth-80: overlay.sso_clients list -> realm clients array has both entries
    _write_scaffold(tmp_path)
    profile = {
        "version": 1,
        "customer": {"slug": "acme"},
        "overlay": {
            "sso_clients": [
                {"id": "acme-app"},
                {"id": "acme-admin"},
            ]
        },
    }
    ops = eop.emit(tmp_path, profile=profile, sso=True)
    realm = _json.loads((ops / "keycloak-realm.json").read_text(encoding="utf-8"))
    assert len(realm["clients"]) == 2
    client_ids = {c["clientId"] for c in realm["clients"]}
    assert client_ids == {"acme-app", "acme-admin"}


def test_sso_client_default_web_origins(tmp_path):
    # Client without explicit web_origins -> webOrigins defaults to ["+"]
    _write_scaffold(tmp_path)
    profile = {
        "version": 1,
        "customer": {"slug": "acme"},
        "overlay": {"sso_clients": [{"id": "acme-app"}]},
    }
    ops = eop.emit(tmp_path, profile=profile, sso=True)
    realm = _json.loads((ops / "keycloak-realm.json").read_text(encoding="utf-8"))
    assert realm["clients"][0]["webOrigins"] == ["+"]


def test_sso_client_custom_redirect_uris(tmp_path):
    # Client with custom redirect_uris -> redirectUris matches supplied list
    _write_scaffold(tmp_path)
    custom_uris = ["https://app.acme.example/callback", "https://app.acme.example/*"]
    profile = {
        "version": 1,
        "customer": {"slug": "acme"},
        "overlay": {
            "sso_clients": [{"id": "acme-app", "redirect_uris": custom_uris}]
        },
    }
    ops = eop.emit(tmp_path, profile=profile, sso=True)
    realm = _json.loads((ops / "keycloak-realm.json").read_text(encoding="utf-8"))
    assert realm["clients"][0]["redirectUris"] == custom_uris


def test_sso_off_emits_no_ldap(tmp_path):
    # Neither --sso nor sso_ldap -> no .env.ldap.example, no components block
    _write_scaffold(tmp_path)
    ops = eop.emit(tmp_path)
    assert not (ops / ".env.ldap.example").exists()
    assert not (ops / "keycloak-realm.json").exists()


def test_sso_on_ldap_off_realm_has_no_components(tmp_path):
    # --sso only, no ldap profile -> realm JSON has no components key
    _write_scaffold(tmp_path)
    profile = {"version": 1, "customer": {"slug": "acme"}}
    ops = eop.emit(tmp_path, profile=profile, sso=True)
    realm = _json.loads((ops / "keycloak-realm.json").read_text(encoding="utf-8"))
    assert "components" not in realm
    assert not (ops / ".env.ldap.example").exists()


def _ldap_profile(extra_ldap=None):
    ldap = {
        "host": "ldap.acme.internal",
        "port": 389,
        "bind_dn": "cn=admin,dc=acme,dc=internal",
        "bind_credential": "secret",
        "users_dn": "ou=people,dc=acme,dc=internal",
    }
    if extra_ldap:
        ldap.update(extra_ldap)
    return {
        "version": 1,
        "customer": {"slug": "acme"},
        "ldap": ldap,
    }


def test_sso_ldap_via_cli_flag(tmp_path):
    # emit(..., sso=True, sso_ldap=True) with profile.ldap -> realm has UserStorageProvider + .env.ldap.example
    _write_scaffold(tmp_path)
    ops = eop.emit(tmp_path, profile=_ldap_profile(), sso=True, sso_ldap=True)
    realm = _json.loads((ops / "keycloak-realm.json").read_text(encoding="utf-8"))
    assert "components" in realm
    assert "org.keycloak.storage.UserStorageProvider" in realm["components"]
    assert (ops / ".env.ldap.example").exists()


def test_sso_ldap_via_profile_opt_in(tmp_path):
    # overlay.sso_ldap: true without CLI flag -> same result as CLI flag
    _write_scaffold(tmp_path)
    profile = _ldap_profile()
    profile["overlay"] = {"sso_ldap": True}
    ops = eop.emit(tmp_path, profile=profile, sso=True)
    realm = _json.loads((ops / "keycloak-realm.json").read_text(encoding="utf-8"))
    assert "components" in realm
    assert "org.keycloak.storage.UserStorageProvider" in realm["components"]
    assert (ops / ".env.ldap.example").exists()


def test_sso_ldap_bind_credential_env_var_preserved(tmp_path):
    # ldap.bind_credential containing ${VAR} -> realm JSON contains literal ${VAR}
    _write_scaffold(tmp_path)
    profile = _ldap_profile({"bind_credential": "${ACME_LDAP_PW}"})
    ops = eop.emit(tmp_path, profile=profile, sso=True, sso_ldap=True)
    realm_text = (ops / "keycloak-realm.json").read_text(encoding="utf-8")
    assert "${ACME_LDAP_PW}" in realm_text
    # Also valid JSON
    realm = _json.loads(realm_text)
    provider = realm["components"]["org.keycloak.storage.UserStorageProvider"][0]
    assert provider["config"]["bindCredential"] == ["${ACME_LDAP_PW}"]


def test_sso_ldap_defaults_applied(tmp_path):
    # ldap config with only required fields -> port defaults to 389, username_attr defaults to "uid"
    _write_scaffold(tmp_path)
    profile = {
        "version": 1,
        "customer": {"slug": "acme"},
        "ldap": {
            "host": "ldap.acme",
            "bind_dn": "cn=admin,dc=acme,dc=internal",
            "bind_credential": "x",
            "users_dn": "ou=people,dc=acme,dc=internal",
        },
    }
    ops = eop.emit(tmp_path, profile=profile, sso=True, sso_ldap=True)
    realm = _json.loads((ops / "keycloak-realm.json").read_text(encoding="utf-8"))
    provider = realm["components"]["org.keycloak.storage.UserStorageProvider"][0]
    assert provider["config"]["connectionUrl"] == ["ldap://ldap.acme:389"]
    assert provider["config"]["usernameLDAPAttribute"] == ["uid"]
