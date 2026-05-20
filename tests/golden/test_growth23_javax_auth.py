# tests/golden/test_growth23_javax_auth.py
"""Growth-23 — javax lane (Spring Security 5 + javax.servlet) auth bundle.

Mirrors Growth-21a-2's jakarta lane goldens but pinned to auth_lane="javax":
  - auth_mode="session" + auth_lane="javax" → 9 auth/ files (no JwtTokenProvider)
    using javax.servlet imports + SecurityConfig extends
    WebSecurityConfigurerAdapter (Spring Security 5).
  - auth_mode="jwt" + auth_lane="javax" → adds JwtTokenProvider using
    javax.annotation.PostConstruct; SecurityConfig stays
    WebSecurityConfigurerAdapter with STATELESS sessions.
  - auth_mode="oauth2" + auth_lane="javax" → adds OAuth2LoginSuccessHandler
    on javax.servlet; SecurityConfig wires .oauth2Login() via Spring Security
    5 HttpSecurity chain (no lambda DSL).

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


def _build_args(tmp_path, target, *, auth_mode="session", auth_lane="javax"):
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
        auth_lane=auth_lane,
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
        pytest.fail(f"StageFailure during auth_lane=javax run: {exc}")


def test_javax_session_uses_javax_servlet_imports(tmp_path):
    target = tmp_path / "newproj"
    target.mkdir()
    _run(_build_args(tmp_path, target, auth_mode="session", auth_lane="javax"))

    auth_dir = _auth_root(target)
    cfg_dir = _config_root(target)

    # File inventory identical to jakarta lane session (9 auth files + 1 config).
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
        f"javax session expected {expected_auth}, got {actual_auth}"
    )

    # Every servlet-touching class must use javax.servlet, never jakarta.servlet.
    servlet_users = [
        "NexacroAuthenticationFilter.java",
        "NexacroAuthenticationDetailSource.java",
        "NexacroAuthenticationEntryPoint.java",
        "NexacroAccessDeniedHandler.java",
        "NexacroAuthenticationFailureHandler.java",
        "NexacroAuthenticationSuccessHandler.java",
    ]
    for name in servlet_users:
        src = (auth_dir / name).read_text(encoding="utf-8")
        assert "jakarta.servlet" not in src, \
            f"{name} (javax lane) must not contain jakarta.servlet imports"
        assert "javax.servlet" in src, \
            f"{name} (javax lane) must contain javax.servlet imports"
        assert "auth_lane=javax" in src, \
            f"{name} header must mark Growth-23 javax lane"

    # SecurityConfig must extend WebSecurityConfigurerAdapter (Spring Sec 5).
    sec = (cfg_dir / "SecurityConfig.java").read_text(encoding="utf-8")
    assert "extends WebSecurityConfigurerAdapter" in sec, \
        "javax SecurityConfig must extend WebSecurityConfigurerAdapter"
    assert "requestMatchers(" not in sec, \
        "javax SecurityConfig must use antMatchers(...) (Spring Sec 5), not requestMatchers"
    assert "antMatchers(" in sec, \
        "javax SecurityConfig must use antMatchers(...) (Spring Sec 5)"
    assert "SecurityFilterChain" not in sec, \
        "javax SecurityConfig must not declare SecurityFilterChain bean (Spring Sec 6 idiom)"


def test_javax_jwt_uses_javax_annotation_postconstruct(tmp_path):
    target = tmp_path / "newproj"
    target.mkdir()
    _run(_build_args(tmp_path, target, auth_mode="jwt", auth_lane="javax"))

    auth_dir = _auth_root(target)
    cfg_dir = _config_root(target)

    jwt_src = (auth_dir / "JwtTokenProvider.java").read_text(encoding="utf-8")
    assert "javax.annotation.PostConstruct" in jwt_src, \
        "javax JwtTokenProvider must use javax.annotation.PostConstruct"
    assert "jakarta.annotation.PostConstruct" not in jwt_src

    # STATELESS session policy still applied via Spring Sec 5 chained API.
    sec = (cfg_dir / "SecurityConfig.java").read_text(encoding="utf-8")
    assert "STATELESS" in sec
    assert "extends WebSecurityConfigurerAdapter" in sec


def test_javax_oauth2_emits_javax_handler_and_oauth2_login(tmp_path):
    target = tmp_path / "newproj"
    target.mkdir()
    _run(_build_args(tmp_path, target, auth_mode="oauth2", auth_lane="javax"))

    auth_dir = _auth_root(target)
    cfg_dir = _config_root(target)

    oauth_src = (auth_dir / "OAuth2LoginSuccessHandler.java").read_text(
        encoding="utf-8"
    )
    assert "javax.servlet" in oauth_src
    assert "jakarta.servlet" not in oauth_src

    sec = (cfg_dir / "SecurityConfig.java").read_text(encoding="utf-8")
    assert "oauth2Login()" in sec, \
        "javax oauth2 SecurityConfig must call oauth2Login() (Spring Sec 5 chained API)"
    assert "OAuth2LoginSuccessHandler" in sec


def test_javax_lane_strict_resolution_no_jakarta_fallback(tmp_path):
    """Regression guard: pattern_loader must not silently fall back to jakarta
    sources when auth_lane=javax — any emitted file under auth/ that touches
    the servlet API must use javax.servlet exclusively.
    """
    target = tmp_path / "newproj"
    target.mkdir()
    _run(_build_args(tmp_path, target, auth_mode="oauth2", auth_lane="javax"))

    auth_dir = _auth_root(target)
    for java_file in auth_dir.glob("*.java"):
        src = java_file.read_text(encoding="utf-8")
        if "jakarta.servlet" in src:
            pytest.fail(
                f"{java_file.name} contains jakarta.servlet under auth_lane=javax "
                f"— pattern_loader silently fell back to jakarta sources"
            )
