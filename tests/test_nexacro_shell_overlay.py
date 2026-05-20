# tests/test_nexacro_shell_overlay.py
"""Tests for nexacro_shell_overlay (Growth-16 P2)."""
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
