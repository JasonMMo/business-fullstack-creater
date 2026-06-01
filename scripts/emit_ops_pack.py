"""Growth-71 (M3 Ops Pack) — emit self-host deployment artifacts.

Reads a scaffold output directory (`out/<slug>/shell/`) and writes a
self-contained `ops/` folder so an IT-담당자 persona can deploy without
a developer environment:

    <out-dir>/shell/ops/
        Dockerfile              # multi-stage maven → tomcat/jre runtime
        docker-compose.yml      # app + dialect-matched db service
        .env.example            # env-var contract (DB creds, ports)
        DEPLOY-SOP.md           # Korean step-by-step runbook

Growth-76 (M3 Slice d) opt-in `--vault` adds Vault Agent sidecar overlay
for enterprise key-management environments — IT-담당자가 사내 Vault 에
DB 자격증명을 위임할 수 있도록 추가 3 산출물:

    <out-dir>/shell/ops/
        docker-compose.vault.yml  # vault-agent sidecar overlay (compose -f stack)
        vault-agent.hcl           # Vault Agent config (AppRole + template)
        env.tmpl                  # consul-template — Vault KV → .env

Growth-77 (M3 Slice e) opt-in `--sso` adds Keycloak/OIDC sidecar overlay
— IT-담당자가 사내 SSO 로 인증을 위임할 수 있도록 추가 3 산출물:

    <out-dir>/shell/ops/
        docker-compose.sso.yml    # keycloak sidecar overlay (compose -f stack)
        keycloak-realm.json       # realm import (1 realm + 1 OIDC client)
        .env.sso.example          # OIDC env contract (issuer-uri/client-id/secret)

CLI
---

    python scripts/emit_ops_pack.py <out-dir>
        [--profile profiles/<slug>.yaml]   # customer profile override
        [--force]                           # overwrite existing ops/
        [--shell-subdir shell]              # name of the war/jar subdir
        [--vault]                           # emit Vault Agent sidecar overlay
        [--sso]                             # emit Keycloak/OIDC sidecar overlay

Inputs detected from the scaffold itself:
- packaging (`war` vs `jar`)  → runtime image
- jakarta vs javax (deps grep) → Tomcat 10 vs 9
- artifactId / version         → final jar/war name

Customer profile (optional) supplies dialect override + ${ENV} placeholder
prefix; otherwise the dialect is inferred from pom.xml dependency hints
(postgresql / mysql-connector-j / hsqldb). Profile may also opt-in to
Vault via `overlay.vault_agent: true`.
"""
from __future__ import annotations

import argparse
import pathlib
import re
import sys
import xml.etree.ElementTree as ET
from typing import Any, Dict, Optional

import yaml

_MVN_NS = {"m": "http://maven.apache.org/POM/4.0.0"}


# ---------------------------------------------------------------------------
# Scaffold introspection
# ---------------------------------------------------------------------------

def _pom_text(root: ET.Element, *paths: str) -> Optional[str]:
    for path in paths:
        for ns_path in (path, "./" + "/".join(f"m:{p}" for p in path.split("/"))):
            node = root.find(ns_path, _MVN_NS) if ":" in ns_path else root.find(ns_path)
            if node is not None and node.text:
                return node.text.strip()
    return None


def inspect_scaffold(shell_dir: pathlib.Path) -> Dict[str, Any]:
    """Return {artifact_id, version, packaging, lane, dialect}."""
    pom = shell_dir / "pom.xml"
    if not pom.exists():
        raise FileNotFoundError(
            f"pom.xml not found at {pom} — pass <out-dir> pointing to the "
            f"scaffold root (parent of shell/) or use --shell-subdir."
        )
    raw = pom.read_text(encoding="utf-8", errors="replace")
    tree = ET.fromstring(raw)
    artifact_id = _pom_text(tree, "artifactId") or "app"
    version = _pom_text(tree, "version") or "1.0.0-SNAPSHOT"
    packaging = (_pom_text(tree, "packaging") or "jar").lower()
    lane = "jakarta" if (
        "jakarta.servlet" in raw
        or "mybatis-spring-boot-starter-jakarta" in raw
        or "jakarta.servlet.jsp" in raw
    ) else "javax"
    if "postgresql" in raw:
        dialect = "postgres"
    elif "mysql-connector" in raw or "mysql-connector-j" in raw:
        dialect = "mysql"
    elif "hsqldb" in raw:
        dialect = "hsqldb"
    else:
        dialect = "postgres"  # safe default — overridable via profile
    return {
        "artifact_id": artifact_id,
        "version": version,
        "packaging": packaging,
        "lane": lane,
        "dialect": dialect,
    }


# ---------------------------------------------------------------------------
# Profile helpers
# ---------------------------------------------------------------------------

def _load_profile(profile_path: Optional[pathlib.Path]) -> Optional[Dict[str, Any]]:
    if profile_path is None:
        return None
    if not profile_path.exists():
        raise FileNotFoundError(f"profile not found: {profile_path}")
    data = yaml.safe_load(profile_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("version") != 1:
        raise ValueError(
            f"profile {profile_path} must be a v1 customer profile (version: 1)"
        )
    return data


def _profile_slug(profile: Optional[Dict[str, Any]], fallback: str) -> str:
    if profile and isinstance(profile.get("customer"), dict):
        slug = profile["customer"].get("slug")
        if isinstance(slug, str) and slug:
            return slug
    return fallback


def _env_prefix(slug: str) -> str:
    return re.sub(r"[^A-Z0-9]+", "_", slug.upper()).strip("_") or "APP"


# ---------------------------------------------------------------------------
# Render templates
# ---------------------------------------------------------------------------

_DOCKERFILE_TPL = """\
# Auto-generated by scripts/emit_ops_pack.py (Growth-71).
# Multi-stage build: Maven compiles the {packaging}, runtime image serves it.

FROM maven:3.9-eclipse-temurin-17 AS builder
WORKDIR /build
COPY pom.xml ./
COPY src ./src
RUN mvn -q -DskipTests -B package

{runtime_stage}
"""

_RUNTIME_WAR_JAKARTA = """\
FROM tomcat:10.1-jdk17-temurin
LABEL maintainer="ops@example.com"
# Remove default ROOT webapp so the scaffold WAR maps to /uiadapter cleanly.
RUN rm -rf /usr/local/tomcat/webapps/ROOT
COPY --from=builder /build/target/{artifact_id}-{version}.war \\
    /usr/local/tomcat/webapps/uiadapter.war
EXPOSE 8080
CMD ["catalina.sh", "run"]
"""

_RUNTIME_WAR_JAVAX = """\
FROM tomcat:9.0-jdk17-temurin
LABEL maintainer="ops@example.com"
RUN rm -rf /usr/local/tomcat/webapps/ROOT
COPY --from=builder /build/target/{artifact_id}-{version}.war \\
    /usr/local/tomcat/webapps/uiadapter.war
EXPOSE 8080
CMD ["catalina.sh", "run"]
"""

_RUNTIME_JAR = """\
FROM eclipse-temurin:17-jre
LABEL maintainer="ops@example.com"
WORKDIR /app
COPY --from=builder /build/target/{artifact_id}-{version}.jar /app/app.jar
EXPOSE 8080
ENTRYPOINT ["java", "-jar", "/app/app.jar"]
"""


def render_dockerfile(info: Dict[str, Any]) -> str:
    if info["packaging"] == "war":
        runtime = (
            _RUNTIME_WAR_JAKARTA if info["lane"] == "jakarta" else _RUNTIME_WAR_JAVAX
        )
    else:
        runtime = _RUNTIME_JAR
    runtime_stage = runtime.format(
        artifact_id=info["artifact_id"], version=info["version"]
    )
    return _DOCKERFILE_TPL.format(packaging=info["packaging"], runtime_stage=runtime_stage)


# --- docker-compose ---------------------------------------------------------

_DB_SERVICE_POSTGRES = """\
  db:
    image: postgres:16-alpine
    restart: unless-stopped
    environment:
      POSTGRES_USER: ${{{prefix}_DB_USER}}
      POSTGRES_PASSWORD: ${{{prefix}_DB_PASS}}
      POSTGRES_DB: ${{{prefix}_DB_NAME}}
    ports:
      - "${{{prefix}_DB_PORT:-5432}}:5432"
    volumes:
      - db-data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U $${{{prefix}_DB_USER}}"]
      interval: 10s
      timeout: 5s
      retries: 5
"""

_DB_SERVICE_MYSQL = """\
  db:
    image: mysql:8.0
    restart: unless-stopped
    environment:
      MYSQL_USER: ${{{prefix}_DB_USER}}
      MYSQL_PASSWORD: ${{{prefix}_DB_PASS}}
      MYSQL_DATABASE: ${{{prefix}_DB_NAME}}
      MYSQL_RANDOM_ROOT_PASSWORD: "yes"
    ports:
      - "${{{prefix}_DB_PORT:-3306}}:3306"
    volumes:
      - db-data:/var/lib/mysql
    healthcheck:
      test: ["CMD", "mysqladmin", "ping", "-h", "localhost"]
      interval: 10s
      timeout: 5s
      retries: 5
"""

_COMPOSE_TPL = """\
# Auto-generated by scripts/emit_ops_pack.py (Growth-71).
# Self-host deploy contract — see DEPLOY-SOP.md for step-by-step.
services:
  app:
    build:
      context: ..
      dockerfile: ops/Dockerfile
    restart: unless-stopped
    env_file:
      - .env
    ports:
      - "${{APP_PORT:-8080}}:8080"
{depends_on}{db_service}{volumes}"""

_DEPENDS_BLOCK = """\
    depends_on:
      db:
        condition: service_healthy
"""

_VOLUMES_BLOCK = """
volumes:
  db-data:
"""


def render_compose(info: Dict[str, Any], slug: str) -> str:
    prefix = _env_prefix(slug)
    if info["dialect"] == "postgres":
        db_service = _DB_SERVICE_POSTGRES.format(prefix=prefix)
        depends = _DEPENDS_BLOCK
        volumes = _VOLUMES_BLOCK
    elif info["dialect"] == "mysql":
        db_service = _DB_SERVICE_MYSQL.format(prefix=prefix)
        depends = _DEPENDS_BLOCK
        volumes = _VOLUMES_BLOCK
    else:  # hsqldb, h2 — embedded; no db service
        db_service = ""
        depends = ""
        volumes = ""
    return _COMPOSE_TPL.format(
        depends_on=depends, db_service=db_service, volumes=volumes
    )


# --- .env.example -----------------------------------------------------------

_ENV_TPL = """\
# Auto-generated by scripts/emit_ops_pack.py (Growth-71).
# Copy to `.env` and fill in real values before `docker compose up`.
# Never commit the populated `.env` to source control.

APP_PORT=8080

{db_block}"""

_ENV_DB_POSTGRES = """\
{prefix}_DB_HOST=db
{prefix}_DB_PORT=5432
{prefix}_DB_NAME=appdb
{prefix}_DB_USER=app
{prefix}_DB_PASS=change-me-please
"""

_ENV_DB_MYSQL = """\
{prefix}_DB_HOST=db
{prefix}_DB_PORT=3306
{prefix}_DB_NAME=appdb
{prefix}_DB_USER=app
{prefix}_DB_PASS=change-me-please
"""

_ENV_DB_EMBEDDED = """\
# dialect={dialect} — embedded, no separate DB container needed.
# Override JDBC URL via Spring property override in /etc/<app>/application.yml.
"""


def render_env_example(info: Dict[str, Any], slug: str) -> str:
    prefix = _env_prefix(slug)
    if info["dialect"] == "postgres":
        db = _ENV_DB_POSTGRES.format(prefix=prefix)
    elif info["dialect"] == "mysql":
        db = _ENV_DB_MYSQL.format(prefix=prefix)
    else:
        db = _ENV_DB_EMBEDDED.format(dialect=info["dialect"])
    return _ENV_TPL.format(db_block=db)


# --- DEPLOY-SOP.md ----------------------------------------------------------

_SOP_TPL = """\
# 배포 SOP — {slug}

> Auto-generated by `scripts/emit_ops_pack.py` (Growth-71).
> IT 담당자 페르소나 (M-Ops): 산출물 zip 을 받아 사내 WAS/DB/SSO 에
> 1시간 안에 올린다.

## 0. 사전 준비

- Docker Engine 20.10+ (또는 Docker Desktop)
- 외부에서 접근할 포트 1개 (기본 8080)
- DB 자격증명 (사내 정책에 맞는 `app` 사용자)

## 1. 압축 해제

받은 zip 을 배포 호스트의 적절한 경로에 푼다 (예: `/opt/{slug}/`).

```bash
unzip {slug}.zip -d /opt/
cd /opt/{slug}/shell
```

## 2. 환경변수 설정

`ops/.env.example` 을 `ops/.env` 로 복사하고 실제 값을 채운다.

```bash
cp ops/.env.example ops/.env
${{EDITOR:-vi}} ops/.env
```

필수 값:
- `APP_PORT` — 외부 노출 포트
{env_required}

## 3. 컨테이너 기동

```bash
cd ops
docker compose up -d --build
```

빌드 단계: Maven 이 `pom.xml` 을 읽고 `{packaging}` 산출물을 생성한다.
초회 약 3~5분 소요 (의존성 다운로드 포함).

## 4. 헬스체크

```bash
# 컨테이너 상태
docker compose ps

# 애플리케이션 로그
docker compose logs -f app | head -40

# HTTP 응답
curl -i http://localhost:${{APP_PORT:-8080}}/uiadapter/
```

기대: `HTTP/1.1 200` 또는 인증 요구 시 `302/401`. 5xx 가 나오면
§6 트러블슈팅 참조.

## 5. SSO/Reverse-Proxy (옵션)

사내 SSO(예: SAML/OIDC) 또는 nginx/Apache 리버스 프록시 뒤에 배치할
때:

1. nginx upstream 으로 `http://localhost:${{APP_PORT}}` 지정
2. `X-Forwarded-For`, `X-Forwarded-Proto` 헤더 전달
3. SSO 모듈은 application.yml 의 `security.*` 절을 사내 정책에 맞게
   덮어쓰기 (스캐폴드는 기본 `session` 모드).

## 6. 트러블슈팅

| 증상 | 원인 후보 | 조치 |
|---|---|---|
| `app` 컨테이너가 즉시 종료 | DB 연결 실패 | `docker compose logs db` 로 DB healthy 확인 |
| `500 Internal Server Error` | schema 미적용 | `docker compose exec db psql/mysql` 로 schema.sql 수동 실행 |
| `Connection refused` | 포트 충돌 | `.env` 의 `APP_PORT` 변경 후 `docker compose up -d` 재기동 |
| Maven 빌드 실패 | 사내 proxy/mirror | `~/.m2/settings.xml` 를 Dockerfile 빌더 단계에 마운트 |
| `mvn package` 가 nexacro/uiadapter 의존성 해석 실패 | nexacro 1차 jar(`uiadapter*-jakarta-*`, `nexacro*-xapi/xeni`)은 사내 nexus(예: tobesoft) 전용 — 공개 Maven Central 에 없음 | 사내 nexus 접근(VPN/인증) 보장, 또는 빌드 호스트 `~/.m2/repository` 를 빌더 단계에 마운트(`docker compose build` 시 `-v $HOME/.m2:/root/.m2`). 비-nexacro(vanilla) 레인은 공개 의존성만으로 빌드 가능 |

## 7. 백업 / 업그레이드

- DB 볼륨: `docker compose down` 후 `docker volume inspect ops_db-data`
- 새 zip 수령 시: `docker compose down` → unzip 덮어쓰기 → `docker compose up -d --build`
- 데이터 보존을 원하면 `down` 대신 `stop` 후 빌드.

## 8. 비밀값 (Vault 후크)

현재는 `.env` 파일 기반. 사내 Vault/Secret Manager 사용 시 `.env` 를
런타임에 동적 생성하는 entrypoint 스크립트로 교체 (Slice b 예정).
"""


def render_sop(info: Dict[str, Any], slug: str) -> str:
    prefix = _env_prefix(slug)
    if info["dialect"] in ("postgres", "mysql"):
        env_required = (
            f"- `{prefix}_DB_USER` / `{prefix}_DB_PASS` / `{prefix}_DB_NAME` / "
            f"`{prefix}_DB_HOST` / `{prefix}_DB_PORT` — DB 자격증명"
        )
    else:
        env_required = (
            f"- (embedded {info['dialect']} 사용 — 별도 DB 자격증명 불필요)"
        )
    return _SOP_TPL.format(
        slug=slug,
        packaging=info["packaging"],
        env_required=env_required,
    )


# ---------------------------------------------------------------------------
# Growth-76 — Vault Agent sidecar overlay
# ---------------------------------------------------------------------------

_VAULT_HCL_TPL = """\
# Auto-generated by scripts/emit_ops_pack.py --vault (Growth-76).
# Vault Agent config — AppRole auth + KV template -> /vault/secrets/.env
# IT-담당자가 채워야 할 것:
#   - vault-auth/role-id, vault-auth/secret-id (AppRole 자격증명 파일)
#   - VAULT_ADDR 환경변수 (Vault 서버 주소)

pid_file = "/vault/pid"

vault {
  address = "{{ env "VAULT_ADDR" }}"
}

auto_auth {
  method "approle" {
    config = {
      role_id_file_path = "/vault/role-id"
      secret_id_file_path = "/vault/secret-id"
      remove_secret_id_file_after_reading = false
    }
  }
  sink "file" {
    config = {
      path = "/vault/token"
    }
  }
}

template {
  source      = "/vault/templates/env.tmpl"
  destination = "/vault/secrets/.env"
  perms       = "0644"
}
"""

_VAULT_ENV_TMPL_TPL_DB = """\
# Auto-generated by scripts/emit_ops_pack.py --vault (Growth-76).
# consul-template syntax — Vault Agent renders this to /vault/secrets/.env
# Vault KV path: secret/data/{slug}/db (KV v2)

APP_PORT=8080

{{{{ with secret "secret/data/{slug}/db" }}}}
{prefix}_DB_HOST={{{{ .Data.data.host }}}}
{prefix}_DB_PORT={{{{ .Data.data.port }}}}
{prefix}_DB_NAME={{{{ .Data.data.name }}}}
{prefix}_DB_USER={{{{ .Data.data.user }}}}
{prefix}_DB_PASS={{{{ .Data.data.pass }}}}
{{{{ end }}}}
"""

_VAULT_ENV_TMPL_TPL_EMBEDDED = """\
# Auto-generated by scripts/emit_ops_pack.py --vault (Growth-76).
# dialect={dialect} — embedded DB, no Vault KV needed for credentials.

APP_PORT=8080
"""

_VAULT_COMPOSE_TPL = """\
# Auto-generated by scripts/emit_ops_pack.py --vault (Growth-76).
# Vault Agent sidecar overlay — usage:
#   docker compose -f docker-compose.yml -f docker-compose.vault.yml up -d
# Renders /vault/secrets/.env from Vault KV; app reads it via env_file.
services:
  vault-agent:
    image: hashicorp/vault:1.15
    restart: unless-stopped
    command: ["agent", "-config=/vault/config/vault-agent.hcl"]
    environment:
      VAULT_ADDR: ${VAULT_ADDR:-http://vault.internal:8200}
    volumes:
      - ./vault-agent.hcl:/vault/config/vault-agent.hcl:ro
      - ./env.tmpl:/vault/templates/env.tmpl:ro
      - vault-secrets:/vault/secrets
      - ${VAULT_AUTH_DIR:-./vault-auth}:/vault:ro
  app:
    env_file:
      - vault-secrets/.env
    depends_on:
      vault-agent:
        condition: service_started
    volumes:
      - vault-secrets:/vault/secrets:ro

volumes:
  vault-secrets:
"""


def render_vault_hcl(info: Dict[str, Any], slug: str) -> str:
    return _VAULT_HCL_TPL


def render_vault_env_tmpl(info: Dict[str, Any], slug: str) -> str:
    prefix = _env_prefix(slug)
    if info["dialect"] in ("postgres", "mysql"):
        return _VAULT_ENV_TMPL_TPL_DB.format(slug=slug, prefix=prefix)
    return _VAULT_ENV_TMPL_TPL_EMBEDDED.format(dialect=info["dialect"])


def render_vault_compose(info: Dict[str, Any], slug: str) -> str:
    return _VAULT_COMPOSE_TPL


_VAULT_SOP_SECTION = """\

## 9. Vault Agent sidecar (Growth-76)

본 ops pack 은 `--vault` 옵션으로 emit 되어, 사내 HashiCorp Vault 에서
DB 자격증명을 런타임에 위임받는 sidecar 구성이 동봉되어 있다.

### 9.1 사전 준비

1. Vault 서버에 KV v2 secret 경로 작성:
   ```
   vault kv put secret/{slug}/db host=db port=5432 name=appdb user=app pass=<실제값>
   ```
2. AppRole 인증 활성화 + role 발급:
   ```
   vault auth enable approle
   vault write auth/approle/role/{slug}-role policies=read-{slug}-db
   vault read -field=role_id auth/approle/role/{slug}-role/role-id > ./vault-auth/role-id
   vault write -f -field=secret_id auth/approle/role/{slug}-role/secret-id > ./vault-auth/secret-id
   ```
3. `VAULT_ADDR` 환경변수 export (예: `https://vault.acme.internal`).

### 9.2 기동

```bash
docker compose -f docker-compose.yml -f docker-compose.vault.yml up -d
```

순서: `vault-agent` 가 KV 를 읽어 `/vault/secrets/.env` 를 렌더하고,
`app` 컨테이너가 그 파일을 `env_file` 로 읽는다. .env.example 의
정적 값은 **사용되지 않는다** (vault-agent 가 동적으로 덮어쓴다).

### 9.3 비밀값 회전

Vault KV 값 갱신 후 `docker compose restart app` 만으로 새 자격증명 반영.
vault-agent 는 template TTL 에 따라 자동 재렌더(consul-template 표준 동작).
"""


# ---------------------------------------------------------------------------
# Growth-77 (M3 Slice e) — Keycloak/OIDC SSO sidecar opt-in
# ---------------------------------------------------------------------------

_SSO_COMPOSE_TPL = """\
# Auto-generated by scripts/emit_ops_pack.py --sso (Growth-77).
# Keycloak sidecar overlay — usage:
#   docker compose -f docker-compose.yml -f docker-compose.sso.yml up -d
# Keycloak imports keycloak-realm.json on first start; app reads OIDC env
# vars from .env.sso.example (copy to .env.sso and fill secrets).
services:
  keycloak:
    image: quay.io/keycloak/keycloak:24.0
    restart: unless-stopped
    command: ["start-dev", "--import-realm"]
    environment:
      KEYCLOAK_ADMIN: ${{KEYCLOAK_ADMIN:-admin}}
      KEYCLOAK_ADMIN_PASSWORD: ${{KEYCLOAK_ADMIN_PASSWORD:-admin}}
    volumes:
      - ./keycloak-realm.json:/opt/keycloak/data/import/realm.json:ro
    ports:
      - "${{KEYCLOAK_PORT:-8180}}:8080"
  app:
    env_file:
      - .env.sso
    environment:
      OIDC_ISSUER_URI: ${{OIDC_ISSUER_URI:-http://keycloak:8080/realms/{slug}}}
      OIDC_CLIENT_ID: ${{OIDC_CLIENT_ID:-{slug}-app}}
      OIDC_CLIENT_SECRET: ${{OIDC_CLIENT_SECRET}}
      OIDC_REDIRECT_URI: ${{OIDC_REDIRECT_URI:-http://localhost:8080/login/oauth2/code/keycloak}}
    depends_on:
      keycloak:
        condition: service_started
"""

_SSO_REALM_JSON_TPL = """\
{{
  "realm": "{slug}",
  "enabled": true,
  "displayName": "{slug} realm (Growth-77)",
  "registrationAllowed": false,
  "resetPasswordAllowed": true,
  "rememberMe": true,
  "clients": [
    {{
      "clientId": "{slug}-app",
      "enabled": true,
      "protocol": "openid-connect",
      "publicClient": false,
      "standardFlowEnabled": true,
      "directAccessGrantsEnabled": false,
      "redirectUris": [
        "http://localhost:8080/login/oauth2/code/keycloak",
        "http://localhost:8080/*"
      ],
      "webOrigins": ["+"],
      "attributes": {{
        "post.logout.redirect.uris": "http://localhost:8080/*"
      }}
    }}
  ]
}}
"""

# Growth-80 marker: LDAP federation component template for Keycloak realm JSON.
# Uses simple string-replace substitution (not str.format) so ${VAR} placeholders
# in bind_credential survive verbatim into the emitted JSON.
_SSO_LDAP_COMPONENT_TPL = (
    '  "components": {\n'
    '    "org.keycloak.storage.UserStorageProvider": [\n'
    '      {\n'
    '        "name": "__LDAP_NAME__",\n'
    '        "providerId": "ldap",\n'
    '        "subComponents": {},\n'
    '        "config": {\n'
    '          "enabled": ["true"],\n'
    '          "priority": ["0"],\n'
    '          "vendor": ["other"],\n'
    '          "connectionUrl": ["__LDAP_URL__"],\n'
    '          "usersDn": ["__LDAP_USERS_DN__"],\n'
    '          "bindDn": ["__LDAP_BIND_DN__"],\n'
    '          "bindCredential": ["__LDAP_BIND_CREDENTIAL__"],\n'
    '          "authType": ["simple"],\n'
    '          "editMode": ["READ_ONLY"],\n'
    '          "usernameLDAPAttribute": ["__LDAP_USERNAME_ATTR__"],\n'
    '          "rdnLDAPAttribute": ["__LDAP_RDN_ATTR__"],\n'
    '          "uuidLDAPAttribute": ["__LDAP_UUID_ATTR__"],\n'
    '          "userObjectClasses": ["__LDAP_USER_OBJECT_CLASSES__"],\n'
    '          "searchScope": ["1"],\n'
    '          "connectionPooling": ["true"],\n'
    '          "pagination": ["true"],\n'
    '          "syncRegistrations": ["false"]\n'
    '        }\n'
    '      }\n'
    '    ]\n'
    '  }'
)

_SSO_LDAP_ENV_EXAMPLE_TPL = """\
# Auto-generated by scripts/emit_ops_pack.py --sso --sso-ldap (Growth-80).
# LDAP federation credentials — copy to .env.ldap and fill the values:

LDAP_BIND_DN=
LDAP_BIND_CREDENTIAL=
LDAP_USERS_DN=
"""

_SSO_LDAP_SOP_SECTION = """

### 10.4 LDAP federation (Growth-80)

LDAP federation 활성 — `.env.ldap.example` 의 `LDAP_BIND_CREDENTIAL` 을
실제 LDAP 서비스 계정 비밀번호로 채운 후 `.env.ldap` 으로 복사.
Keycloak realm 에 `org.keycloak.storage.UserStorageProvider` 컴포넌트가
자동 import 되므로, Keycloak 재기동 시 LDAP 사용자가 조회된다.
운영 전환 시 `editMode` 를 `READ_ONLY` -> `WRITABLE` 로 변경 가능
(Keycloak admin console -> User Federation -> ldap 항목).
"""

_SSO_ENV_EXAMPLE_TPL = """\
# Auto-generated by scripts/emit_ops_pack.py --sso (Growth-77).
# OIDC client contract — copy to .env.sso and fill OIDC_CLIENT_SECRET
# with the value from Keycloak admin console after first start:
#   Realm "{slug}" → Clients → "{slug}-app" → Credentials → "Client secret".

OIDC_ISSUER_URI=http://keycloak:8080/realms/{slug}
OIDC_CLIENT_ID={slug}-app
OIDC_CLIENT_SECRET=
OIDC_REDIRECT_URI=http://localhost:8080/login/oauth2/code/keycloak
"""

_SSO_SOP_SECTION = """\

## 10. Keycloak/OIDC SSO sidecar (Growth-77)

본 ops pack 은 `--sso` 옵션으로 emit 되어, 사내 SSO 없이도 즉시
Keycloak 사이드카로 OIDC 로그인이 동작하는 구성이 동봉되어 있다.
운영에서는 사내 SSO provider 로 `OIDC_ISSUER_URI` 만 교체.

### 10.1 사전 준비

1. 첫 기동: `keycloak-realm.json` 이 `/opt/keycloak/data/import/realm.json`
   으로 마운트되어 realm `{slug}` + client `{slug}-app` 가 자동 import.
2. `.env.sso.example` → `.env.sso` 로 복사. `OIDC_CLIENT_SECRET` 만 채우면
   된다 (Keycloak admin console → 해당 client → Credentials 탭).
3. 사내 SSO 전환 시: `OIDC_ISSUER_URI` 를 사내 IdP URL 로 교체,
   `docker-compose.sso.yml` 의 `keycloak` 서비스 블록 제거.

### 10.2 기동

```bash
docker compose -f docker-compose.yml -f docker-compose.sso.yml up -d
```

순서: `keycloak` 이 realm import 완료 후 `app` 이 OIDC 발견(discovery)
엔드포인트(`${{OIDC_ISSUER_URI}}/.well-known/openid-configuration`) 를
조회해 로그인 플로우 활성화.

### 10.3 인증 검증

```bash
curl -sS http://localhost:8080/login | grep -i keycloak
# 정상이면 Keycloak 로그인 페이지로 redirect 되는 HTML 응답.
```

admin/admin 으로 admin console 접근 가능 (운영 전 반드시 변경:
`KEYCLOAK_ADMIN_PASSWORD` 환경변수 override).
"""


def render_sso_compose(info: Dict[str, Any], slug: str) -> str:
    return _SSO_COMPOSE_TPL.format(slug=slug)


def _render_client_json(client: dict) -> str:
    """Return a single Keycloak client JSON object string (Growth-80 multi-client)."""
    import json as _json_mod
    redirect_uris = client.get(
        "redirect_uris",
        ["http://localhost:8080/login/oauth2/code/keycloak", "http://localhost:8080/*"],
    )
    web_origins = client.get("web_origins", ["+"])
    public_client = client.get("public_client", False)
    obj = {
        "clientId": client["id"],
        "enabled": True,
        "protocol": "openid-connect",
        "publicClient": public_client,
        "standardFlowEnabled": True,
        "directAccessGrantsEnabled": False,
        "redirectUris": redirect_uris,
        "webOrigins": web_origins,
        "attributes": {"post.logout.redirect.uris": "http://localhost:8080/*"},
    }
    return _json_mod.dumps(obj, indent=6)


def _render_ldap_component(slug: str, ldap: dict) -> str:
    """Return the LDAP federation components JSON block (Growth-80)."""
    host = ldap["host"]
    port = str(ldap.get("port", 389))
    users_dn = ldap["users_dn"]
    bind_dn = ldap["bind_dn"]
    bind_credential = ldap["bind_credential"]
    username_attr = ldap.get("username_attr", "uid")
    rdn_attr = ldap.get("rdn_attr", "uid")
    uuid_attr = ldap.get("uuid_attr", "entryUUID")
    user_object_classes = ldap.get("user_object_classes", "inetOrgPerson, organizationalPerson")

    result = _SSO_LDAP_COMPONENT_TPL
    result = result.replace("__LDAP_NAME__", f"ldap-{slug}")
    result = result.replace("__LDAP_URL__", f"ldap://{host}:{port}")
    result = result.replace("__LDAP_USERS_DN__", users_dn)
    result = result.replace("__LDAP_BIND_DN__", bind_dn)
    result = result.replace("__LDAP_BIND_CREDENTIAL__", bind_credential)
    result = result.replace("__LDAP_USERNAME_ATTR__", username_attr)
    result = result.replace("__LDAP_RDN_ATTR__", rdn_attr)
    result = result.replace("__LDAP_UUID_ATTR__", uuid_attr)
    result = result.replace("__LDAP_USER_OBJECT_CLASSES__", user_object_classes)
    return result


def render_sso_realm(info: Dict[str, Any], slug: str, *, clients=None, ldap=None) -> str:
    """Render Keycloak realm JSON.

    Growth-80: if ``clients`` list provided, render multi-client array via
    ``_render_client_json``; otherwise fall back to single hardcoded client
    (Growth-77 backcompat). If ``ldap`` dict provided, inject LDAP federation
    ``components`` block.
    """
    import json as _json_mod
    if clients:
        clients_json = ",\n    ".join(_render_client_json(c) for c in clients)
        clients_block = f"[\n    {clients_json}\n  ]"
    else:
        # Growth-77 backcompat: single hardcoded client
        single = {
            "clientId": f"{slug}-app",
            "enabled": True,
            "protocol": "openid-connect",
            "publicClient": False,
            "standardFlowEnabled": True,
            "directAccessGrantsEnabled": False,
            "redirectUris": [
                "http://localhost:8080/login/oauth2/code/keycloak",
                "http://localhost:8080/*",
            ],
            "webOrigins": ["+"],
            "attributes": {"post.logout.redirect.uris": "http://localhost:8080/*"},
        }
        clients_block = _json_mod.dumps([single], indent=4)

    realm_obj: Dict[str, Any] = {
        "realm": slug,
        "enabled": True,
        "displayName": f"{slug} realm (Growth-77)",
        "registrationAllowed": False,
        "resetPasswordAllowed": True,
        "rememberMe": True,
    }
    # Build as string to inject clients block (already formatted JSON)
    realm_base = _json_mod.dumps(realm_obj, indent=2)
    # Insert clients array before closing brace
    realm_base = realm_base.rstrip("}")
    realm_base = realm_base.rstrip() + ",\n"
    realm_base += f'  "clients": {clients_block}'
    if ldap:
        ldap_block = _render_ldap_component(slug, ldap)
        realm_base += ",\n" + ldap_block
    realm_base += "\n}"
    return realm_base


def render_sso_env_example(info: Dict[str, Any], slug: str) -> str:
    return _SSO_ENV_EXAMPLE_TPL.format(slug=slug)


# ---------------------------------------------------------------------------
# Emit driver
# ---------------------------------------------------------------------------

def emit(
    out_dir: pathlib.Path,
    *,
    profile: Optional[Dict[str, Any]] = None,
    shell_subdir: str = "shell",
    force: bool = False,
    vault: bool = False,
    sso: bool = False,
    sso_ldap: bool = False,
) -> pathlib.Path:
    """Emit ops/ folder. Returns the ops directory path."""
    shell_dir = out_dir / shell_subdir
    if not shell_dir.exists():
        # Tolerate callers passing the shell dir directly.
        if (out_dir / "pom.xml").exists():
            shell_dir = out_dir
        else:
            raise FileNotFoundError(
                f"shell directory not found: {shell_dir} (and {out_dir}/pom.xml missing)"
            )
    info = inspect_scaffold(shell_dir)
    slug = _profile_slug(profile, info["artifact_id"])
    if profile and isinstance(profile.get("ddl"), dict):
        d = profile["ddl"].get("dialect")
        if d in ("postgres", "mysql", "hsqldb", "h2"):
            info["dialect"] = d

    vault_opt = vault
    if not vault_opt and profile and isinstance(profile.get("overlay"), dict):
        vault_opt = bool(profile["overlay"].get("vault_agent"))

    sso_opt = sso
    if not sso_opt and profile and isinstance(profile.get("overlay"), dict):
        sso_opt = bool(profile["overlay"].get("sso_keycloak"))

    # Growth-80: sso_ldap opt-in via CLI flag or profile overlay.sso_ldap
    sso_ldap_opt = sso_ldap
    if not sso_ldap_opt and profile and isinstance(profile.get("overlay"), dict):
        sso_ldap_opt = bool(profile["overlay"].get("sso_ldap"))

    # Growth-80: multi-client list from profile overlay.sso_clients
    _overlay = profile.get("overlay") if profile and isinstance(profile.get("overlay"), dict) else {}
    clients = _overlay.get("sso_clients") if _overlay else None

    # Growth-80: ldap config from profile top-level ldap section
    ldap_cfg = profile.get("ldap") if (profile and sso_ldap_opt) else None

    ops = shell_dir / "ops"
    if ops.exists() and not force:
        raise FileExistsError(
            f"{ops} already exists — pass --force to overwrite."
        )
    ops.mkdir(parents=True, exist_ok=True)

    (ops / "Dockerfile").write_text(render_dockerfile(info), encoding="utf-8")
    (ops / "docker-compose.yml").write_text(
        render_compose(info, slug), encoding="utf-8"
    )
    (ops / ".env.example").write_text(
        render_env_example(info, slug), encoding="utf-8"
    )
    sop_text = render_sop(info, slug)
    if vault_opt:
        sop_text = sop_text + _VAULT_SOP_SECTION.format(slug=slug)
        (ops / "docker-compose.vault.yml").write_text(
            render_vault_compose(info, slug), encoding="utf-8"
        )
        (ops / "vault-agent.hcl").write_text(
            render_vault_hcl(info, slug), encoding="utf-8"
        )
        (ops / "env.tmpl").write_text(
            render_vault_env_tmpl(info, slug), encoding="utf-8"
        )
    if sso_opt:
        sop_text = sop_text + _SSO_SOP_SECTION.format(slug=slug)
        if sso_ldap_opt and ldap_cfg:
            sop_text = sop_text + _SSO_LDAP_SOP_SECTION
        (ops / "docker-compose.sso.yml").write_text(
            render_sso_compose(info, slug), encoding="utf-8"
        )
        (ops / "keycloak-realm.json").write_text(
            render_sso_realm(info, slug, clients=clients, ldap=ldap_cfg), encoding="utf-8"
        )
        (ops / ".env.sso.example").write_text(
            render_sso_env_example(info, slug), encoding="utf-8"
        )
        if sso_ldap_opt and ldap_cfg:
            (ops / ".env.ldap.example").write_text(
                _SSO_LDAP_ENV_EXAMPLE_TPL, encoding="utf-8"
            )
    (ops / "DEPLOY-SOP.md").write_text(sop_text, encoding="utf-8")
    return ops


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv: Optional[list[str]] = None) -> int:
    p = argparse.ArgumentParser(
        prog="emit_ops_pack",
        description="Emit self-host ops/ artifacts for a scaffold output (Growth-71).",
    )
    p.add_argument("out_dir", help="scaffold output directory (parent of shell/)")
    p.add_argument(
        "--profile", default=None, help="path to profiles/<slug>.yaml override"
    )
    p.add_argument(
        "--shell-subdir", default="shell", help="name of war/jar subdir (default: shell)"
    )
    p.add_argument("--force", action="store_true", help="overwrite existing ops/")
    p.add_argument(
        "--vault",
        action="store_true",
        help="emit Vault Agent sidecar overlay (Growth-76)",
    )
    p.add_argument(
        "--sso",
        action="store_true",
        help="emit Keycloak/OIDC sidecar overlay (Growth-77)",
    )
    p.add_argument(
        "--sso-ldap",
        action="store_true",
        help="Growth-80: enable Keycloak LDAP federation component (requires --sso)",
    )
    args = p.parse_args(argv)

    out_dir = pathlib.Path(args.out_dir).resolve()
    if not out_dir.is_dir():
        print(f"ERROR: not a directory: {out_dir}", file=sys.stderr)
        return 2

    try:
        profile = _load_profile(
            pathlib.Path(args.profile) if args.profile else None
        )
        ops = emit(
            out_dir,
            profile=profile,
            shell_subdir=args.shell_subdir,
            force=args.force,
            vault=args.vault,
            sso=args.sso,
            sso_ldap=args.sso_ldap,
        )
    except (FileNotFoundError, FileExistsError, ValueError) as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1 if isinstance(e, FileExistsError) else 2

    print(f"wrote {ops}/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
