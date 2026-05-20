# tests/golden/test_growth21a_auth_mode.py
"""Growth-21a-2 — SHELL Spring Security + Nexacro auth bundle emission.

Asserts the auth_files block in the SHELL manifest:
  - auth_mode="none"    → no auth/config files (Growth-16~20 contract)
  - auth_mode="session" → 10 files (8 auth + UserDetailsService + SecurityConfig)
  - auth_mode="jwt"     → 11 files (session + JwtTokenProvider)
  - auth_mode="oauth2"  → 11 files (same set as jwt; OAuth2 deps land in 21a-3)

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
    """oauth2 mode includes the same files as jwt (deps land in 21a-3)."""
    target = tmp_path / "newproj"
    target.mkdir()

    args = _build_args(tmp_path, target, auth_mode="oauth2")
    _run(args)

    assert (_auth_root(target) / "JwtTokenProvider.java").exists()
    assert (_config_root(target) / "SecurityConfig.java").exists()
