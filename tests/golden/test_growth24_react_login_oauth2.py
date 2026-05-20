# tests/golden/test_growth24_react_login_oauth2.py
"""Growth-24 — React overlay OAuth2 LoginPage emission.

Validates that scripts/react_overlay.py emits
`frontend/src/pages/auth/LoginPage.tsx` only when `auth_mode == "oauth2"`,
and that the page is a faithful React mirror of the Nexacro frame_login
provider-button flow from Growth-21a-3:

  - kicks the browser at `/oauth2/authorization/{providerId}` (matches
    Spring's OAuth2 client filter wired by SecurityConfig.oauth2Login()).
  - on mount, reads the `X-Auth-Bearer` cookie left by
    OAuth2LoginSuccessHandler (Growth-21a-2 jakarta / Growth-23 javax)
    and stashes it under `localStorage["auth.bearer"]`.
  - keeps a password-form fallback so session/jwt modes can reuse the
    same screen without re-rendering the providers list.

This test is self-contained (does not require sibling-stage repos) — it
invokes scripts/react_overlay.py directly.
"""
import json
import pathlib
import sys

import pytest

CREATOR = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(CREATOR / "scripts"))


@pytest.fixture
def overlay_env(tmp_path):
    """Fake out_dir with a minimal Stage 3 endpoints.json + target dir."""
    out = tmp_path / "out"
    (out / "3-mybatis").mkdir(parents=True)
    (out / "3-mybatis" / "endpoints.json").write_text(
        json.dumps({"version": "0.1.4", "endpoints": {}}),
        encoding="utf-8",
    )
    target = tmp_path / "target"
    target.mkdir()
    return out, target


def _login_path(target: pathlib.Path) -> pathlib.Path:
    return target / "frontend" / "src" / "pages" / "auth" / "LoginPage.tsx"


def test_no_login_emitted_when_auth_mode_none(overlay_env):
    out, target = overlay_env
    import react_overlay  # noqa: PLC0415

    report = react_overlay.run(
        out_dir=out,
        target_dir=target,
        domain_slug="auth",
        domain_label="권한관리",
        service_pascal="Auth",
        blueprint_entities=[{"name": "app_user"}],
        auth_mode="none",
    )
    assert report["react_login_emitted"] is None
    assert not _login_path(target).exists()


def test_no_login_emitted_when_auth_mode_session_or_jwt(overlay_env):
    out, target = overlay_env
    import react_overlay  # noqa: PLC0415

    for mode in ("session", "jwt"):
        # Fresh target subdir per mode so we don't carry state across loops.
        sub_target = target / mode
        sub_target.mkdir()
        report = react_overlay.run(
            out_dir=out,
            target_dir=sub_target,
            domain_slug="auth",
            domain_label="권한관리",
            service_pascal="Auth",
            blueprint_entities=[{"name": "app_user"}],
            auth_mode=mode,
        )
        assert report["react_login_emitted"] is None, \
            f"auth_mode={mode} must not emit LoginPage.tsx"
        assert not _login_path(sub_target).exists()


def test_oauth2_emits_login_page_with_provider_buttons_and_cookie_pickup(overlay_env):
    out, target = overlay_env
    import react_overlay  # noqa: PLC0415

    report = react_overlay.run(
        out_dir=out,
        target_dir=target,
        domain_slug="auth",
        domain_label="권한관리",
        service_pascal="Auth",
        blueprint_entities=[{"name": "app_user"}],
        auth_mode="oauth2",
    )

    login = _login_path(target)
    assert login.exists(), "OAuth2 mode must emit LoginPage.tsx"
    assert report["react_login_emitted"] == "frontend/src/pages/auth/LoginPage.tsx"

    src = login.read_text(encoding="utf-8")

    # Spring's OAuth2 client filter contract — must use the exact prefix.
    assert "/oauth2/authorization/${providerId}" in src, \
        "LoginPage must redirect to Spring's OAuth2 authorization endpoint"

    # Cookie pickup contract — must read X-Auth-Bearer set by
    # OAuth2LoginSuccessHandler and stash it under localStorage.
    assert "X-Auth-Bearer" in src
    assert "localStorage.setItem(STORAGE_KEY" in src
    assert "auth.bearer" in src

    # Provider list — at minimum Google + GitHub (mirrors frame_login).
    assert "'google'" in src
    assert "'github'" in src

    # Password-form fallback so session/jwt can reuse the screen.
    assert "onPasswordSubmit" in src
    assert "/login" in src

    # Growth-24 header marker so future regressions are easy to spot.
    assert "Growth-24" in src


def test_oauth2_login_page_overwrite_requires_overlay_force(overlay_env):
    out, target = overlay_env
    import react_overlay  # noqa: PLC0415

    # First emit — succeeds.
    react_overlay.run(
        out_dir=out,
        target_dir=target,
        domain_slug="auth",
        domain_label="권한관리",
        service_pascal="Auth",
        blueprint_entities=[{"name": "app_user"}],
        auth_mode="oauth2",
    )
    assert _login_path(target).exists()

    # Second emit without overlay_force — must abort.
    with pytest.raises(RuntimeError, match="LoginPage"):
        react_overlay.run(
            out_dir=out,
            target_dir=target,
            domain_slug="auth",
            domain_label="권한관리",
            service_pascal="Auth",
            blueprint_entities=[{"name": "app_user"}],
            auth_mode="oauth2",
        )

    # With overlay_force — backs up and rewrites.
    report = react_overlay.run(
        out_dir=out,
        target_dir=target,
        domain_slug="auth",
        domain_label="권한관리",
        service_pascal="Auth",
        blueprint_entities=[{"name": "app_user"}],
        auth_mode="oauth2",
        overlay_force=True,
    )
    bak = pathlib.Path(str(_login_path(target)) + ".bak")
    assert bak.exists()
    assert report["react_login_emitted"] == "frontend/src/pages/auth/LoginPage.tsx"
