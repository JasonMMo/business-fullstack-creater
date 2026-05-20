# tests/golden/test_growth21a_auth_mode.py
"""Growth-21a-2/21a-3 — SHELL Spring Security + Nexacro auth bundle emission.

Asserts the auth_files block in the SHELL manifest plus the 21a-3
살붙임 (pom dependencies, application.yml security blocks, frame_login
real /login POST + OAuth2 provider buttons):
  - auth_mode="none"    → no auth/config files (Growth-16~20 contract)
  - auth_mode="session" → 10 files + spring-boot-starter-security
  - auth_mode="jwt"     → 11 files + jjwt deps + JWT yaml block + STATELESS
  - auth_mode="oauth2"  → 12 files (+ OAuth2LoginSuccessHandler) +
                          oauth2-client starter + OAuth2 yaml block +
                          provider buttons in frameLogin

Skipped when any sibling stage repo is missing.
"""
import pathlib
import sys

import pytest

CREATOR = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(CREATOR / "scripts"))

SIBLINGS = {
    "stage1": CREATOR.parent / "andrej-karpathy-rdb-skill",
    "stage2": CREATOR.parent / "andrej-karpathy-rdb-ddl",
    "stage3": CREATOR.parent / "andrej-karpathy-rdb-mybatis",
    "stage4": CREATOR.parent / "andrej-karpathy-rdb-nexacro",
}

_MISSING = [k for k, p in SIBLINGS.items() if not p.exists()]
pytestmark = pytest.mark.skipif(
    bool(_MISSING),
    reason=f"sibling stage repo(s) not found: {', '.join(_MISSING)}",
)


def _build_args(tmp_path, target, *, auth_mode="none"):
    from scaffold_orchestrator import ScaffoldArgs  # noqa: PLC0415

    return ScaffoldArgs(
        domain="권한관리",
        domain_slug="auth",
        wiki_mode="preset",
        preset="권한관리",
        wiki_path=None,
        lane="nexacro",
        default_pattern="D2",
        package="com.example.auth",
        out_dir=tmp_path / "scaffold-out",
        creator_root=CREATOR,
        stop_after_stage=5,
        dialect="hsqldb",
        service_name="Auth",
        target_project=target,
        overlay_force=False,
        ui="nexacro",
        shell_mode="MDI",
        auth_mode=auth_mode,
    )


def _auth_root(target):
    return target / "src" / "main" / "java" / "com" / "nexacro" / "uiadapter" / "auth" / "auth"


def _config_root(target):
    return target / "src" / "main" / "java" / "com" / "nexacro" / "uiadapter" / "auth" / "config"


def _run(args):
    from scaffold_orchestrator import run_scaffold, StageFailure  # noqa: PLC0415

    try:
        run_scaffold(args)
    except StageFailure as exc:
        pytest.fail(f"StageFailure during auth_mode run: {exc}")


def test_auth_mode_none_emits_no_auth_files(tmp_path):
    """Default contract: auth_mode='none' must NOT create auth/ or config/
    directories — Growth-16~20 goldens depend on the exact file inventory.
    """
    target = tmp_path / "newproj"
    target.mkdir()

    args = _build_args(tmp_path, target, auth_mode="none")
    _run(args)

    assert not _auth_root(target).exists(), \
        "auth_mode=none must NOT emit auth/ directory"
    assert not _config_root(target).exists(), \
        "auth_mode=none must NOT emit config/ directory"


def test_auth_mode_session_emits_10_files(tmp_path):
    target = tmp_path / "newproj"
    target.mkdir()

    args = _build_args(tmp_path, target, auth_mode="session")
    _run(args)

    auth_dir = _auth_root(target)
    cfg_dir = _config_root(target)

    expected_auth = {
        "NexacroAuthenticationToken.java",
        "NexacroAuthenticationDetailSource.java",
        "NexacroAuthenticationFilter.java",
        "NexacroAuthenticationProvider.java",
        "NexacroAuthenticationEntryPoint.java",
        "NexacroAccessDeniedHandler.java",
        "NexacroAuthenticationFailureHandler.java",
        "NexacroAuthenticationSuccessHandler.java",
        "NexacroUserDetailsService.java",
    }
    actual_auth = {p.name for p in auth_dir.glob("*.java")}
    assert actual_auth == expected_auth, (
        f"auth_mode=session expected {expected_auth}, got {actual_auth}"
    )
    # JwtTokenProvider must NOT be present in session mode
    assert not (auth_dir / "JwtTokenProvider.java").exists()
    # SecurityConfig always present when auth_mode != none
    assert (cfg_dir / "SecurityConfig.java").exists()


def test_auth_mode_jwt_emits_11_files_with_bearer(tmp_path):
    target = tmp_path / "newproj"
    target.mkdir()

    args = _build_args(tmp_path, target, auth_mode="jwt")
    _run(args)

    auth_dir = _auth_root(target)
    cfg_dir = _config_root(target)

    # 10 auth files + 1 config file = 11 total
    assert (auth_dir / "JwtTokenProvider.java").exists(), \
        "auth_mode=jwt must emit JwtTokenProvider"
    assert (cfg_dir / "SecurityConfig.java").exists()

    # SuccessHandler must reference Bearer token in jwt mode
    success = (auth_dir / "NexacroAuthenticationSuccessHandler.java").read_text(
        encoding="utf-8"
    )
    assert "Bearer" in success, \
        "auth_mode=jwt SuccessHandler must emit Bearer header"
    assert "jwtTokenProvider" in success, \
        "auth_mode=jwt SuccessHandler must use JwtTokenProvider"

    # SecurityConfig must be STATELESS in jwt mode
    sec = (cfg_dir / "SecurityConfig.java").read_text(encoding="utf-8")
    assert "STATELESS" in sec, \
        "auth_mode=jwt SecurityConfig must use SessionCreationPolicy.STATELESS"


def test_auth_mode_oauth2_includes_jwt_provider(tmp_path):
    """oauth2 mode: jwt bundle + OAuth2LoginSuccessHandler + client deps."""
    target = tmp_path / "newproj"
    target.mkdir()

    args = _build_args(tmp_path, target, auth_mode="oauth2")
    _run(args)

    auth_dir = _auth_root(target)
    cfg_dir = _config_root(target)

    assert (auth_dir / "JwtTokenProvider.java").exists()
    assert (cfg_dir / "SecurityConfig.java").exists()
    assert (auth_dir / "OAuth2LoginSuccessHandler.java").exists(), \
        "auth_mode=oauth2 must emit OAuth2LoginSuccessHandler"

    # SecurityConfig wires the oauth2Login() chain only under oauth2.
    sec = (cfg_dir / "SecurityConfig.java").read_text(encoding="utf-8")
    assert "oauth2Login" in sec, \
        "auth_mode=oauth2 SecurityConfig must enable oauth2Login chain"
    assert "OAuth2LoginSuccessHandler" in sec


# ---------------------------------------------------------------------------
# Growth-21a-3: SHELL 살붙임 — pom.xml, application.yml, frame_login.xfdl
# ---------------------------------------------------------------------------


def _pom(target):
    return (target / "pom.xml").read_text(encoding="utf-8")


def _appyml(target):
    return (target / "src" / "main" / "resources" / "application.yml").read_text(
        encoding="utf-8"
    )


def _login_xfdl(target):
    # nexacro_shell_overlay renders frames into target/nxui/packageN/frame/.
    # The src/main/resources/static/packageN/ path is only populated by Maven
    # at build time via the pom.xml resource filter — not at scaffold time.
    return (
        target / "nxui" / "packageN" / "frame" / "frameLogin.xfdl"
    ).read_text(encoding="utf-8")


def test_growth21a3_none_keeps_pom_clean(tmp_path):
    """Regression guard: auth_mode=none must NOT pull security/jjwt/oauth2."""
    target = tmp_path / "newproj"
    target.mkdir()
    _run(_build_args(tmp_path, target, auth_mode="none"))

    pom = _pom(target)
    assert "spring-boot-starter-security" not in pom
    assert "jjwt-api" not in pom
    assert "spring-boot-starter-oauth2-client" not in pom

    appyml = _appyml(target)
    assert "oauth2:" not in appyml
    assert "app:" not in appyml or "app.security" not in appyml


def test_growth21a3_session_adds_security_starter(tmp_path):
    target = tmp_path / "newproj"
    target.mkdir()
    _run(_build_args(tmp_path, target, auth_mode="session"))

    pom = _pom(target)
    assert "spring-boot-starter-security" in pom, \
        "auth_mode=session must pull spring-boot-starter-security"
    assert "jjwt-api" not in pom, "session mode must NOT pull jjwt"
    assert "spring-boot-starter-oauth2-client" not in pom

    # frameLogin in session+ mode posts a real DataSet to /login.
    login = _login_xfdl(target)
    assert 'transaction(\n    "login"' in login or '"svc::/login"' in login, \
        "session frameLogin must POST to /login via transaction()"


def test_growth21a3_jwt_adds_jjwt_and_app_security_yaml(tmp_path):
    target = tmp_path / "newproj"
    target.mkdir()
    _run(_build_args(tmp_path, target, auth_mode="jwt"))

    pom = _pom(target)
    assert "spring-boot-starter-security" in pom
    assert "jjwt-api" in pom and "jjwt-impl" in pom and "jjwt-jackson" in pom
    assert "spring-boot-starter-oauth2-client" not in pom, \
        "jwt mode must NOT pull oauth2 client"

    appyml = _appyml(target)
    assert "app:" in appyml and "jwt:" in appyml, \
        "jwt mode must emit app.security.jwt block"
    assert "APP_SECURITY_JWT_SECRET" in appyml

    # frameLogin captures Bearer header on successful login in jwt+ mode.
    login = _login_xfdl(target)
    assert "gv_bearerToken" in login


def test_growth21a3_oauth2_full_stack(tmp_path):
    target = tmp_path / "newproj"
    target.mkdir()
    _run(_build_args(tmp_path, target, auth_mode="oauth2"))

    pom = _pom(target)
    assert "spring-boot-starter-security" in pom
    assert "jjwt-api" in pom
    assert "spring-boot-starter-oauth2-client" in pom, \
        "auth_mode=oauth2 must pull spring-boot-starter-oauth2-client"

    appyml = _appyml(target)
    assert "oauth2:" in appyml and "registration:" in appyml, \
        "oauth2 mode must emit spring.security.oauth2.client block"
    assert "google" in appyml and "keycloak" in appyml

    # frameLogin gains provider buttons in oauth2 mode.
    login = _login_xfdl(target)
    assert "btnLoginGoogle" in login and "btnLoginKeycloak" in login, \
        "oauth2 frameLogin must surface Google + Keycloak buttons"
    assert "/oauth2/authorization/google" in login
