# profiles/ — Customer Profile (6th Axis)

`profiles/<slug>.yaml` 한 장으로 **고객 고유 관습**(패키지, URL, dialect, lane, shell branding, datasource 등)을 묶어둔다. `/scaffold --customer-profile <slug>` 호출로 Stage 1–5 전체에 일관 적용된다.

2번째 도메인부터 손댈 곳 없음 = 복리식 누적의 6번째 축. 5축 (skill / ddl / mybatis / nexacro / creater) 의 형제 축이다.

## 파일명 규칙

- ASCII slug 만 사용 (`acme.yaml`, `foo-bank.yaml`). 한글 파일명 금지 — Growth-51 ASCII slug 원칙 일치.
- 파일명 stem 과 yaml 내부 `customer.slug` 가 동일해야 함.

## 스키마 (version: 1)

```yaml
version: 1                              # 필수. preset-catalog / blueprint 컨벤션 일치.
customer:
  slug: acme                            # ASCII; 파일명 stem 과 일치.
  display: ACME 코퍼레이션               # 한글 표시명 (G-61 dual-name 패턴).
  status: active                        # draft / active / deprecated.
  contact: aj@acme.example              # 옵셔널.

# ── Stage 2 (ddl) ───────────────────────────────────
ddl:
  dialect: postgres                     # postgres / hsqldb / mysql.

# ── Stage 3 (mybatis) ───────────────────────────────
mybatis:
  base_package: com.acme                # compile.py --package.
  project_root_pkg: com.acme.uiadapter  # compile.py --project-root-pkg.
  uia_namespace: jakarta                # jakarta / spring.

# ── Stage 4 (nexacro) ───────────────────────────────
nexacro:
  default_pattern: D2                   # D2 / F1 / C1.

# ── Stage 5 (overlay) ───────────────────────────────
overlay:
  target_pkg_prefix: com.acme.uiadapter
  shell_app_id: acme-portal
  sso_keycloak: true                    # emit Keycloak sidecar (Growth-77).
  sso_clients:                          # Growth-80: multi-client realm. omit = single {slug}-app.
    - id: acme-app                      # required. clientId in Keycloak.
      redirect_uris: [...]              # optional. defaults to localhost:8080 oauth2 callback.
      web_origins: ["+"]               # optional. defaults to ["+"].
      public_client: false              # optional. defaults to false.
  sso_ldap: true                        # Growth-80: enable LDAP federation component.

# ── LDAP federation (Growth-80) ─────────────────────
ldap:
  host: ldap.acme.internal              # required. LDAP server hostname.
  port: 389                             # optional. default 389.
  bind_dn: "cn=admin,dc=acme,dc=..."   # required. service account DN.
  bind_credential: "${ACME_LDAP_PW}"   # required. use ${VAR} placeholder; never plain text.
  users_dn: "ou=people,dc=acme,dc=..."  # required. search base for users.
  username_attr: uid                    # optional. default uid.
  rdn_attr: uid                         # optional. default uid.
  uuid_attr: entryUUID                  # optional. default entryUUID.
  user_object_classes: "inetOrgPerson, organizationalPerson"  # optional.

# ── Auth ────────────────────────────────────────────
auth:
  mode: session                         # none / session / jwt / oauth2.
  lane: jakarta                         # jakarta / javax.

# ── Lane / UI 기본값 ────────────────────────────────
defaults:
  lane: jakarta                         # CLI --lane 누락 시 적용.
  ui: nexacro                           # CLI --ui 누락 시 적용.

# ── 운영 메타 (자동 누적) ───────────────────────────
domains_seen: []                        # Stage 5 PASS 시 orchestrator 가 ASCII slug append.
```

## 머지 우선순위

```
명시적 CLI 인자  >  profile 값  >  ScaffoldArgs 기본값
```

같은 키에 대해 CLI 가 항상 이긴다. profile 은 "이 고객에게는 이게 기본" 을 선언할 뿐, 일회성 override 는 그대로 가능.

## 비밀값 (placeholder)

JDBC 비밀번호 같은 secret 은 `${ENV_VAR}` 형태 placeholder 만 둔다. 실제 값은 `.env` 또는 운영 secret store 에 분리. 로더가 환경변수로 치환한다.

```yaml
datasource:
  username: ${ACME_DB_USER}
  password: ${ACME_DB_PASS}
```

## 누적 효과

| n번째 도메인 | profile 효과 |
|---|---|
| 1st | profile 작성 비용 발생; CLI 결과는 베이스라인과 동일. |
| 2nd | 패키지·URL·dialect·shell-id 자동 적용 — 손 댈 곳 없음. |
| 3rd+ | `domains_seen` 누적; 트랩 가드 customer-tagged. |

## 운영 원칙 위반 신호

- "이번만 직접 CLI 로 넣자" → profile 에 환류 후 다시 실행.
- "고객 한 명이라 profile 필요 없음" → 2번째 도메인에서 손이 가는 순간 위반 발생. 처음부터 profile.

## 참조

- 스키마 작성 동기 + 트랩 분석: `learn-log.md` §6 Growth-63
- 운영 원칙: `CLAUDE.md` — 6축 표
- 가드: `/diagnose` G-62 (`--customer-profile` wiring + `version: 1` enforcement)
