# Growth-16 SHELL Pattern Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** karpathy-rdb-nexacro 에 8번째 패턴 SHELL (kind: shell, applies_to: project) 을 도입하고, business-fullstack-creater 에 `nexacro-shell` UI overlay adapter 를 추가하여 standalone nexacro WAR 빌드 경로를 연다. 기존 `nexacro` merge adapter, nexacroN-fullstack 정책, 7 entity 패턴 회귀 모두 0.

**Architecture:** SHELL 은 `karpathy-rdb-nexacro/.claude/skills/karpathy-rdb-nexacro/patterns/SHELL/` 디렉터리 (manifest.yaml + frame_*.xfdl.j2). `pattern_loader.resolve_shell(variant)` 신규 함수로 entity 패턴과 구분. `business-fullstack-creater/scripts/nexacro_shell_overlay.py` 가 v0.5 H4 registry 에 `nexacro-shell` 로 등록 — 기존 `nexacro` adapter 와 dispatch 분리. CLI `--ui nexacro-shell --shell-mode MDI` 로 진입. blueprint.yaml 의 선택적 `shell:` 블록이 메뉴/typedef/login/frame_overrides 를 선언; 미지정 시 합리적 기본 추론.

**Tech Stack:** Python 3.10+, Jinja2, PyYAML, pytest, PowerShell (Windows). 변경 레포: `andrej-karpathy-rdb-nexacro` (P1, P5), `business-fullstack-creater` (P2~P4, P6), `andrej-karpathy-rdb-skill` (P6 spec). `nexacroN-fullstack` 변경 0 (정책 §7 보존).

**Spec:** `docs/superpowers/specs/2026-05-20-growth-16-shell-pattern-design.md`

**Baseline tags (freeze):** business-fullstack-creater v0.6.0, rdb-nexacro v0.5.0, rdb-mybatis v0.5.2, rdb-ddl v0.5.1, rdb-skill v0.4.0.

---

## File Structure

**andrej-karpathy-rdb-nexacro** (Stage 4 패턴 카탈로그):
- Create: `.claude/skills/karpathy-rdb-nexacro/patterns/SHELL/manifest.yaml`
- Create: `.claude/skills/karpathy-rdb-nexacro/patterns/SHELL/frame_main.xfdl.j2`
- Create: `.claude/skills/karpathy-rdb-nexacro/patterns/SHELL/frame_mdi.xfdl.j2`
- Create: `.claude/skills/karpathy-rdb-nexacro/patterns/SHELL/frame_sdi.xfdl.j2`
- Create: `.claude/skills/karpathy-rdb-nexacro/patterns/SHELL/frame_left.xfdl.j2`
- Create: `.claude/skills/karpathy-rdb-nexacro/patterns/SHELL/frame_top.xfdl.j2`
- Create: `.claude/skills/karpathy-rdb-nexacro/patterns/SHELL/frame_login.xfdl.j2`
- Create: `.claude/skills/karpathy-rdb-nexacro/patterns/SHELL/typedefinition.xml.j2`
- Create: `.claude/skills/karpathy-rdb-nexacro/patterns/SHELL/packageN.xadl.j2`
- Create: `.claude/skills/karpathy-rdb-nexacro/patterns/SHELL/README.md`
- Modify: `scripts/pattern_loader.py` (add `resolve_shell`)
- Create: `tests/test_resolve_shell.py`

**business-fullstack-creater** (Stage 5 오케스트레이션):
- Create: `scripts/nexacro_shell_overlay.py`
- Modify: `scripts/scaffold_orchestrator.py` (--shell-mode pass-through)
- Modify: `scripts/scaffold_cli.py` (--shell-mode / --nexacrolib-from flags)
- Create: `tests/test_nexacro_shell_overlay.py`
- Create: `tests/test_cli_shell_mode.py`
- Create: `tests/fixtures/shell-shipping/blueprint.yaml`
- Create: `tests/fixtures/shell-shipping/golden/` (xfdl/typedef/xadl golden)
- Modify: `USER-GUIDE.md` (Growth-16 §)

**andrej-karpathy-rdb-skill** (Stage 1 spec):
- Modify: `.claude/skills/karpathy-rdb/references/blueprint-spec.md` (shell: 블록)

---

## Task 1: SHELL manifest + MDI frame templates (P1-a)

**Files:**
- Create: `D:\AI\workspace\andrej-karpathy-rdb-nexacro\.claude\skills\karpathy-rdb-nexacro\patterns\SHELL\manifest.yaml`
- Create: `D:\AI\workspace\andrej-karpathy-rdb-nexacro\.claude\skills\karpathy-rdb-nexacro\patterns\SHELL\README.md`
- Create: 6 MDI frame `.xfdl.j2` + `typedefinition.xml.j2` + `packageN.xadl.j2`

- [ ] **Step 1: Write manifest.yaml**

```yaml
name: SHELL
pattern: SHELL
kind: shell
applies_to: project
extensible: true
description: "Project-level nexacro shell (frame composition + menu + typedef) for standalone WAR builds"
variants:
  - id: MDI
    display: Multi-Document Interface
    frames: [frame_main, frame_mdi, frame_left, frame_top, frame_login]
    builtin: true
  - id: SDI
    display: Single-Document Interface
    frames: [frame_main, frame_sdi, frame_left, frame_top, frame_login]
    builtin: true
inputs:
  required: [blueprint.entities, blueprint.shell.menu]
  optional: [blueprint.shell.login, blueprint.shell.branding, blueprint.shell.frame_overrides]
outputs:
  - nxui/packageN/frame/*.xfdl
  - nxui/packageN/typedefinition.xml
  - nxui/packageN/packageN.xadl
version: 1
migration:
  policy: "blueprint.shell.manifest_version 명시 시 그 버전 강제, 미지정 시 최신"
  v1_to_v2_breaking: []
```

- [ ] **Step 2: Write README.md**

```markdown
# SHELL Pattern (Growth-16)

Project-level nexacro shell — entity 패턴 (D2/F1/C1/L2/MD/TR/RO) 과 달리 `applies_to: project`.

**Variants:** MDI (default), SDI. `extensible: true` — 사용자 등록 variant 허용.

**렌더 우선순위 (frame_overrides):** project local > skill local > global catalog.

상세: `docs/superpowers/specs/2026-05-20-growth-16-shell-pattern-design.md`
```

- [ ] **Step 3: Write frame_main.xfdl.j2 (entry frame, MDI/SDI 공통 shell)**

최소 frame 정의: `<Form id="frameMain">` + 3분할 영역 (frame_top / frame_left / work).
변수: `{{ title }}`, `{{ has_login }}`.

```xml
<?xml version="1.0" encoding="UTF-8"?>
<FDL version="2.0">
  <Form id="frameMain" left="0" top="0" width="1280" height="800" titletext="{{ title }}">
    <Layouts>
      <Layout>
        <FrameSet id="rootFrame" rows="32, *" cols="220, *">
          <Frame id="topFrame" formurl="frame::frame_top.xfdl" colspan="2"/>
          <Frame id="leftFrame" formurl="frame::frame_left.xfdl"/>
          <Frame id="workFrame" formurl=""/>
        </FrameSet>
      </Layout>
    </Layouts>
  </Form>
</FDL>
```

- [ ] **Step 4: Write frame_mdi.xfdl.j2 (MDI workspace tabbed container)**

```xml
<?xml version="1.0" encoding="UTF-8"?>
<FDL version="2.0">
  <Form id="frameMDI" left="0" top="0" width="1060" height="768" titletext="MDI Workspace">
    <Layouts>
      <Layout>
        <Tab id="tabWork" left="0" top="0" right="0" bottom="0" tabindex="0"/>
      </Layout>
    </Layouts>
    <Script type="xscript5.1"><![CDATA[
      this.openEntity = function(entityId, formUrl) {
        var idx = this.tabWork.insertTabpage(entityId, this.tabWork.tabpages.length, entityId);
        this.tabWork.tabpages[idx].url = formUrl;
      };
    ]]></Script>
  </Form>
</FDL>
```

- [ ] **Step 5: Write frame_left.xfdl.j2 (menu tree, domain→entity grouping)**

```xml
<?xml version="1.0" encoding="UTF-8"?>
<FDL version="2.0">
  <Form id="frameLeft" left="0" top="0" width="220" height="768" titletext="{{ menu.root_label }}">
    <Objects>
      <Dataset id="dsMenu">
        <ColumnInfo><Column id="id" type="STRING"/><Column id="label" type="STRING"/><Column id="parent" type="STRING"/><Column id="target" type="STRING"/><Column id="sort" type="INT"/></ColumnInfo>
        <Rows>
          {% for d in menu.domains %}<Row><Col id="id">{{ d.id }}</Col><Col id="label">{{ d.label }}</Col><Col id="parent"></Col><Col id="sort">{{ d.sort | default(100) }}</Col></Row>
          {% for e in d.entities %}<Row><Col id="id">{{ d.id }}.{{ e }}</Col><Col id="label">{{ e }}</Col><Col id="parent">{{ d.id }}</Col><Col id="target">{{ d.id }}::{{ e }}.xfdl</Col></Row>
          {% endfor %}{% endfor %}
          {% for ext in menu.extensions %}<Row><Col id="id">{{ ext.id }}</Col><Col id="label">{{ ext.label }}</Col><Col id="parent"></Col><Col id="target">{{ ext.target }}</Col><Col id="sort">{{ ext.sort | default(999) }}</Col></Row>
          {% endfor %}
        </Rows>
      </Dataset>
    </Objects>
    <Layouts>
      <Layout>
        <Grid id="gridMenu" left="0" top="0" right="0" bottom="0" binddataset="dsMenu"/>
      </Layout>
    </Layouts>
  </Form>
</FDL>
```

- [ ] **Step 6: Write frame_top.xfdl.j2 (header)**

```xml
<?xml version="1.0" encoding="UTF-8"?>
<FDL version="2.0">
  <Form id="frameTop" left="0" top="0" width="1280" height="32" titletext="{{ branding.header_text | default(title) }}">
    <Layouts>
      <Layout>
        <Static id="stHeader" left="8" top="4" width="600" height="24" text="{{ branding.header_text | default(title) }}"/>
        <Button id="btnLogout" right="8" top="4" width="80" height="24" text="Logout"/>
      </Layout>
    </Layouts>
  </Form>
</FDL>
```

- [ ] **Step 7: Write frame_login.xfdl.j2 (minimal /uiadapter/login.do call)**

```xml
<?xml version="1.0" encoding="UTF-8"?>
<FDL version="2.0">
  <Form id="frameLogin" left="0" top="0" width="400" height="240" titletext="Login">
    <Layouts>
      <Layout>
        <Edit id="edtUser" left="80" top="60" width="240" height="28"/>
        <Edit id="edtPass" left="80" top="100" width="240" height="28" passwordchar="*"/>
        <Button id="btnLogin" left="80" top="150" width="240" height="32" text="Login"/>
      </Layout>
    </Layouts>
    <Script type="xscript5.1"><![CDATA[
      this.btnLogin_onclick = function() {
        this.transaction("login", "uiadapter::login.do", "", "", "userId=edtUser.value passWd=edtPass.value", "fnCallback");
      };
    ]]></Script>
  </Form>
</FDL>
```

- [ ] **Step 8: Write typedefinition.xml.j2 (entity 컬럼 → typedef)**

```xml
<?xml version="1.0" encoding="UTF-8"?>
<TypeDefinition>
  <Services>
    {% for d in menu.domains %}{% for e in d.entities %}
    <Service prefixid="{{ d.id }}_{{ e }}" url="/uiadapter/{{ d.id }}/{{ e }}/"/>
    {% endfor %}{% endfor %}
    {% for svc in typedef.extra_services | default([]) %}
    <Service prefixid="{{ svc.prefixid }}" url="{{ svc.url }}"/>
    {% endfor %}
  </Services>
</TypeDefinition>
```

- [ ] **Step 9: Write packageN.xadl.j2 (entry app definition)**

```xml
<?xml version="1.0" encoding="UTF-8"?>
<ADL version="2.0">
  <Application id="packageN" titletext="{{ title }}" mainframe="mainframe"/>
  <MainFrame id="mainframe" left="0" top="0" width="1280" height="800"/>
  <Modules>
    <Module url="frame::frame_main.xfdl"/>
    {% if has_login %}<Module url="frame::frame_login.xfdl"/>{% endif %}
  </Modules>
</ADL>
```

- [ ] **Step 10: Write frame_sdi.xfdl.j2 stub (for P5 completion)**

```xml
<?xml version="1.0" encoding="UTF-8"?>
<FDL version="2.0">
  <Form id="frameSDI" left="0" top="0" width="1060" height="768" titletext="SDI">
    <Layouts><Layout/></Layouts>
    <Script type="xscript5.1"><![CDATA[
      this.openEntity = function(entityId, formUrl) {
        this.set_url(formUrl);
      };
    ]]></Script>
  </Form>
</FDL>
```

- [ ] **Step 11: Commit (per-file)**

```powershell
git -C D:\AI\workspace\andrej-karpathy-rdb-nexacro add .claude/skills/karpathy-rdb-nexacro/patterns/SHELL/manifest.yaml
git -C D:\AI\workspace\andrej-karpathy-rdb-nexacro commit -m @'
feat(patterns): SHELL manifest (8th pattern, kind=shell, MDI+SDI)

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
'@
```

각 frame `.xfdl.j2` / README / typedef / xadl 도 동일한 per-file commit 패턴 반복 (총 10 commits).

---

## Task 2: pattern_loader.resolve_shell (P1-b)

**Files:**
- Modify: `D:\AI\workspace\andrej-karpathy-rdb-nexacro\scripts\pattern_loader.py`
- Create: `D:\AI\workspace\andrej-karpathy-rdb-nexacro\tests\test_resolve_shell.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_resolve_shell.py
import pathlib
import pytest
from pattern_loader import resolve_shell, PatternNotFoundError

BUNDLED = pathlib.Path(__file__).parent.parent / ".claude/skills/karpathy-rdb-nexacro/patterns"


def test_resolve_shell_mdi_returns_5_frames():
    rs = resolve_shell("MDI", bundled_root=BUNDLED)
    assert rs.variant == "MDI"
    assert rs.kind == "shell"
    assert set(rs.frames) == {"frame_main", "frame_mdi", "frame_left", "frame_top", "frame_login"}
    assert rs.manifest["extensible"] is True
    assert rs.source == "bundled"


def test_resolve_shell_sdi():
    rs = resolve_shell("SDI", bundled_root=BUNDLED)
    assert rs.variant == "SDI"
    assert "frame_sdi" in rs.frames


def test_resolve_shell_unknown_variant_raises():
    with pytest.raises(PatternNotFoundError, match="variant 'TAB'"):
        resolve_shell("TAB", bundled_root=BUNDLED)


def test_resolve_shell_no_entity_pattern_regression():
    """entity 패턴 D2 가 resolve_shell 로 호출되지 않음 (kind 검증)."""
    with pytest.raises(PatternNotFoundError):
        resolve_shell("D2", bundled_root=BUNDLED)
```

- [ ] **Step 2: Run test to verify fail**

```powershell
cd D:\AI\workspace\andrej-karpathy-rdb-nexacro; pytest tests/test_resolve_shell.py -v
```

Expected: 4 FAIL (resolve_shell not defined).

- [ ] **Step 3: Implement resolve_shell in pattern_loader.py**

Append to `scripts/pattern_loader.py`:

```python
@dataclass
class ResolvedShell:
    variant: str
    kind: str
    frames: list[str]
    template_dir: pathlib.Path
    manifest: dict
    source: str


def resolve_shell(
    variant: str,
    bundled_root: pathlib.Path | str,
    global_root: pathlib.Path | str | None = None,
) -> ResolvedShell:
    """Resolve a SHELL pattern variant. Priority: bundled → global."""
    for label, root in (("bundled", bundled_root), ("global", global_root)):
        if root is None:
            continue
        shell_dir = pathlib.Path(root) / "SHELL"
        mani_path = shell_dir / "manifest.yaml"
        if not mani_path.exists():
            continue
        manifest = yaml.safe_load(mani_path.read_text(encoding="utf-8")) or {}
        if manifest.get("kind") != "shell":
            continue
        for v in manifest.get("variants", []):
            if v.get("id") == variant:
                return ResolvedShell(
                    variant=variant,
                    kind="shell",
                    frames=list(v.get("frames", [])),
                    template_dir=shell_dir,
                    manifest=manifest,
                    source=label,
                )
    raise PatternNotFoundError(
        f"SHELL variant {variant!r} not found. Searched roots: "
        f"{[str(r) for r in (bundled_root, global_root) if r]}"
    )
```

- [ ] **Step 4: Run test to verify pass**

```powershell
cd D:\AI\workspace\andrej-karpathy-rdb-nexacro; pytest tests/test_resolve_shell.py -v
```

Expected: 4 PASS.

- [ ] **Step 5: Run full regression suite**

```powershell
cd D:\AI\workspace\andrej-karpathy-rdb-nexacro; pytest -q
```

Expected: all prior tests still pass (7 entity-pattern regression 0).

- [ ] **Step 6: Commit**

```powershell
git -C D:\AI\workspace\andrej-karpathy-rdb-nexacro add scripts/pattern_loader.py
git -C D:\AI\workspace\andrej-karpathy-rdb-nexacro commit -m @'
feat(pattern_loader): resolve_shell — variant-aware SHELL resolution

bundled → global priority. kind=shell 검증. variant 미발견 시 PatternNotFoundError.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
'@
git -C D:\AI\workspace\andrej-karpathy-rdb-nexacro add tests/test_resolve_shell.py
git -C D:\AI\workspace\andrej-karpathy-rdb-nexacro commit -m @'
test(resolve_shell): MDI/SDI happy path + unknown variant + entity-pattern guard

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
'@
```

- [ ] **Step 7: P1 mini 5축 자체 리뷰**

| 축 | 점수 | 근거 |
|---|---|---|
| 1. 반복 데이터 효율 | 3 | 신규 manifest, 아직 blueprint 와 미연결 |
| 2. 도메인·엔티티 누적 | 3 | 패턴 디렉터리 등록 |
| 3. 풍부한 Seeds | 5 | 8번째 패턴 디렉터리 자체가 신규 자산 |
| 4. 완성도 높은 WAR | 2 | 아직 emit 안 함 |
| 5. Karpathy 정신 | 5 | 파일+manifest |

평균 3.6 ≥ 3 → PASS, P2 진행.

---

## Task 3: nexacro_shell_overlay adapter (P2-a)

**Files:**
- Create: `D:\AI\workspace\business-fullstack-creater\scripts\nexacro_shell_overlay.py`
- Create: `D:\AI\workspace\business-fullstack-creater\tests\test_nexacro_shell_overlay.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_nexacro_shell_overlay.py
import pathlib
import pytest
import sys
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / "scripts"))

import ui_overlay_registry
import nexacro_shell_overlay  # noqa  triggers registration


def test_registered_as_nexacro_shell():
    assert "nexacro-shell" in ui_overlay_registry.registered()


def test_empty_target_dir_emits_5_frame_files(tmp_path):
    target = tmp_path / "out"
    target.mkdir()
    out = tmp_path / "scaffold-out"
    (out / "3-mybatis").mkdir(parents=True)
    (out / "4-nexacro" / "nxui" / "_form_").mkdir(parents=True)

    report = ui_overlay_registry.dispatch(
        "nexacro-shell",
        out_dir=out,
        target_dir=target,
        domain_slug="배송관리",
        domain_label="배송 관리",
        service_pascal="DeliveryService",
        blueprint_entities=[{"name": "delivery", "domain": "배송관리"}],
        shell_mode="MDI",
        shell_title="배송관리 시스템",
        shell_login_enabled=True,
        menu_domains=[{"id": "배송관리", "label": "배송 관리", "sort": 10, "entities": ["delivery"]}],
        nexacrolib_from=None,
    )
    frame_dir = target / "nxui" / "packageN" / "frame"
    assert (frame_dir / "frame_main.xfdl").exists()
    assert (frame_dir / "frame_mdi.xfdl").exists()
    assert (frame_dir / "frame_left.xfdl").exists()
    assert (frame_dir / "frame_top.xfdl").exists()
    assert (frame_dir / "frame_login.xfdl").exists()
    assert (target / "nxui" / "packageN" / "typedefinition.xml").exists()
    assert (target / "nxui" / "packageN" / "packageN.xadl").exists()
    assert report.get("shell_emitted") is True
    assert report.get("shell_variant") == "MDI"


def test_login_disabled_omits_frame_login(tmp_path):
    target = tmp_path / "out"; target.mkdir()
    out = tmp_path / "sc"; (out / "3-mybatis").mkdir(parents=True); (out / "4-nexacro" / "nxui" / "_form_").mkdir(parents=True)
    ui_overlay_registry.dispatch(
        "nexacro-shell",
        out_dir=out, target_dir=target, domain_slug="d", domain_label="D",
        service_pascal="X", blueprint_entities=[], shell_mode="MDI",
        shell_title="T", shell_login_enabled=False,
        menu_domains=[{"id": "d", "label": "D", "sort": 1, "entities": []}],
        nexacrolib_from=None,
    )
    assert not (target / "nxui" / "packageN" / "frame" / "frame_login.xfdl").exists()


def test_nexacro_adapter_unchanged():
    """기존 nexacro adapter 가 여전히 등록되어 있어야 함 (회귀)."""
    import stage5_overlay  # noqa
    assert "nexacro" in ui_overlay_registry.registered()
```

- [ ] **Step 2: Run test to verify fail**

```powershell
cd D:\AI\workspace\business-fullstack-creater; pytest tests/test_nexacro_shell_overlay.py -v
```

Expected: import error / 4 FAIL.

- [ ] **Step 3: Implement nexacro_shell_overlay.py**

```python
# scripts/nexacro_shell_overlay.py
"""nexacro-shell UI overlay adapter (Growth-16).

Emits a standalone nexacro project tree from SHELL pattern templates.
Coexists with the legacy `nexacro` (merge) adapter via ui_overlay_registry.
"""
import pathlib
import shutil
import sys
from typing import Optional

import jinja2
import yaml

import ui_overlay_registry

# Locate karpathy-rdb-nexacro patterns (sibling repo)
_HERE = pathlib.Path(__file__).resolve().parent
_RDB_NEXACRO = _HERE.parent.parent / "andrej-karpathy-rdb-nexacro"
_PATTERNS_ROOT = _RDB_NEXACRO / ".claude" / "skills" / "karpathy-rdb-nexacro" / "patterns"


def _load_shell_manifest(template_dir: pathlib.Path) -> dict:
    return yaml.safe_load((template_dir / "manifest.yaml").read_text(encoding="utf-8")) or {}


def _select_variant_frames(manifest: dict, variant: str) -> list[str]:
    for v in manifest.get("variants", []):
        if v.get("id") == variant:
            return list(v.get("frames", []))
    raise ValueError(f"Unknown SHELL variant: {variant}")


def _render(template_dir: pathlib.Path, name: str, ctx: dict) -> str:
    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(str(template_dir)),
        keep_trailing_newline=True, autoescape=False,
    )
    return env.get_template(f"{name}.xfdl.j2").render(**ctx) if name.startswith("frame_") \
        else env.get_template(f"{name}.j2").render(**ctx)


def _nexacro_shell_overlay_run(
    *,
    out_dir: pathlib.Path,
    target_dir: pathlib.Path,
    domain_slug: str,
    domain_label: str,
    service_pascal: str,
    blueprint_entities: list,
    shell_mode: str = "MDI",
    shell_title: str = "",
    shell_login_enabled: bool = True,
    menu_domains: Optional[list] = None,
    menu_extensions: Optional[list] = None,
    typedef_extra_services: Optional[list] = None,
    frame_overrides: Optional[dict] = None,
    branding: Optional[dict] = None,
    nexacrolib_from: Optional[pathlib.Path] = None,
    overlay_force: bool = False,
    source_pkg_prefix: str = "com.example",
    target_pkg_prefix: str = "com.nexacro.uiadapter",
    patterns_root: Optional[pathlib.Path] = None,
    **_unknown,
) -> dict:
    patterns_root = patterns_root or _PATTERNS_ROOT
    shell_dir = patterns_root / "SHELL"
    if not shell_dir.exists():
        raise FileNotFoundError(f"SHELL pattern dir missing: {shell_dir}")
    manifest = _load_shell_manifest(shell_dir)
    frames = _select_variant_frames(manifest, shell_mode)
    if not shell_login_enabled and "frame_login" in frames:
        frames = [f for f in frames if f != "frame_login"]

    ctx = {
        "title": shell_title or f"{domain_label} 시스템",
        "has_login": shell_login_enabled,
        "menu": {
            "root_label": "업무 메뉴",
            "domains": menu_domains or [],
            "extensions": menu_extensions or [],
        },
        "typedef": {"extra_services": typedef_extra_services or []},
        "branding": branding or {},
        "frame_overrides": frame_overrides or {},
    }

    pkg_dir = target_dir / "nxui" / "packageN"
    frame_out = pkg_dir / "frame"
    frame_out.mkdir(parents=True, exist_ok=True)

    emitted_frames = []
    for fr in frames:
        override = (frame_overrides or {}).get(fr)
        if override and pathlib.Path(override).exists():
            shutil.copy2(override, frame_out / f"{fr}.xfdl")
        else:
            text = jinja2.Environment(
                loader=jinja2.FileSystemLoader(str(shell_dir)),
                keep_trailing_newline=True, autoescape=False,
            ).get_template(f"{fr}.xfdl.j2").render(**ctx)
            (frame_out / f"{fr}.xfdl").write_text(text, encoding="utf-8")
        emitted_frames.append(fr)

    # typedef + xadl
    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(str(shell_dir)),
        keep_trailing_newline=True, autoescape=False,
    )
    (pkg_dir / "typedefinition.xml").write_text(
        env.get_template("typedefinition.xml.j2").render(**ctx), encoding="utf-8")
    (pkg_dir / "packageN.xadl").write_text(
        env.get_template("packageN.xadl.j2").render(**ctx), encoding="utf-8")

    # nexacrolib symlink/copy notice
    nexacrolib_status = "skipped"
    if nexacrolib_from:
        src = pathlib.Path(nexacrolib_from)
        if src.exists():
            dst = pkg_dir / "nexacrolib"
            if dst.exists() and overlay_force:
                shutil.rmtree(dst)
            if not dst.exists():
                shutil.copytree(src, dst)
                nexacrolib_status = "copied"

    return {
        "shell_emitted": True,
        "shell_variant": shell_mode,
        "frames": emitted_frames,
        "nexacrolib": nexacrolib_status,
    }


ui_overlay_registry.register("nexacro-shell", _nexacro_shell_overlay_run)
```

- [ ] **Step 4: Run test to verify pass**

```powershell
cd D:\AI\workspace\business-fullstack-creater; pytest tests/test_nexacro_shell_overlay.py -v
```

Expected: 4 PASS.

- [ ] **Step 5: Run full regression**

```powershell
cd D:\AI\workspace\business-fullstack-creater; pytest -q
```

Expected: all prior pass. nexacro adapter 회귀 0.

- [ ] **Step 6: Commit**

```powershell
git -C D:\AI\workspace\business-fullstack-creater add scripts/nexacro_shell_overlay.py
git -C D:\AI\workspace\business-fullstack-creater commit -m @'
feat(scripts): nexacro-shell UI overlay adapter (Growth-16 P2)

standalone nexacro shell emit. SHELL pattern 의 frame/typedef/xadl 을
target_dir 에 렌더. ui_overlay_registry 에 'nexacro-shell' 로 등록.
기존 'nexacro' merge adapter 와 분리.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
'@
git -C D:\AI\workspace\business-fullstack-creater add tests/test_nexacro_shell_overlay.py
git -C D:\AI\workspace\business-fullstack-creater commit -m @'
test(nexacro_shell_overlay): 5-frame emit + login toggle + nexacro adapter regression

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
'@
```

- [ ] **Step 7: P2 mini 5축 리뷰** → 4·3·4·3·5 평균 3.8 PASS

---

## Task 4: CLI --shell-mode + --nexacrolib-from wiring (P3)

**Files:**
- Modify: `D:\AI\workspace\business-fullstack-creater\scripts\scaffold_orchestrator.py`
- Modify: `D:\AI\workspace\business-fullstack-creater\scripts\scaffold_cli.py`
- Create: `D:\AI\workspace\business-fullstack-creater\tests\test_cli_shell_mode.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_cli_shell_mode.py
import pathlib, subprocess, sys


def test_cli_parses_shell_mode(tmp_path):
    """--ui nexacro-shell --shell-mode SDI 가 인자 파싱 단계에서 거부되지 않음."""
    bp = tmp_path / "blueprint.yaml"
    bp.write_text("version: 1\nentities: []\n", encoding="utf-8")
    out = tmp_path / "out"
    cli = pathlib.Path(__file__).parent.parent / "scripts" / "scaffold_cli.py"
    r = subprocess.run(
        [sys.executable, str(cli), "--blueprint", str(bp), "--ui", "nexacro-shell",
         "--shell-mode", "SDI", "--target", str(out), "--dry-run"],
        capture_output=True, text=True,
    )
    assert "unrecognized arguments" not in r.stderr
    assert "--shell-mode" not in r.stderr.split("error")[-1] if "error" in r.stderr else True


def test_cli_default_nexacro_no_shell_mode(tmp_path):
    """기존 --ui nexacro 호출은 --shell-mode 없이도 정상 (회귀)."""
    bp = tmp_path / "blueprint.yaml"
    bp.write_text("version: 1\nentities: []\n", encoding="utf-8")
    out = tmp_path / "out"
    cli = pathlib.Path(__file__).parent.parent / "scripts" / "scaffold_cli.py"
    r = subprocess.run(
        [sys.executable, str(cli), "--blueprint", str(bp), "--ui", "nexacro",
         "--target", str(out), "--dry-run"],
        capture_output=True, text=True,
    )
    assert "unrecognized" not in r.stderr
```

- [ ] **Step 2: Run test (fail expected)**

```powershell
cd D:\AI\workspace\business-fullstack-creater; pytest tests/test_cli_shell_mode.py -v
```

- [ ] **Step 3: Modify scaffold_cli.py — add --shell-mode + --nexacrolib-from**

Find argparse section, append:

```python
ap.add_argument(
    "--shell-mode", choices=["MDI", "SDI"], default=None,
    help="SHELL variant when --ui nexacro-shell (default: MDI from blueprint.shell or implicit)",
)
ap.add_argument(
    "--nexacrolib-from", type=pathlib.Path, default=None,
    help="Path to nexacrolib/ to copy into target/nxui/packageN/ (--ui nexacro-shell only)",
)
ap.add_argument("--ui", choices=["nexacro", "nexacro-shell", "react"], default="nexacro")
```

(If `--ui` already exists, only extend `choices` to include `nexacro-shell`.)

Pass-through to orchestrator:

```python
result = scaffold_orchestrator.run(
    ...,
    ui=args.ui,
    shell_mode=args.shell_mode,
    nexacrolib_from=args.nexacrolib_from,
)
```

- [ ] **Step 4: Modify scaffold_orchestrator.py — accept + forward kwargs**

Add to `run()` signature:

```python
def run(
    ...,
    ui: str = "nexacro",
    shell_mode: Optional[str] = None,
    nexacrolib_from: Optional[pathlib.Path] = None,
    **extra,
) -> dict:
    ...
    overlay_kwargs = dict(
        out_dir=out_dir, target_dir=target_dir, domain_slug=domain_slug, ...,
    )
    if ui == "nexacro-shell":
        # blueprint.shell 추론
        sh = blueprint.get("shell", {}) or {}
        overlay_kwargs.update(
            shell_mode=shell_mode or sh.get("variant", "MDI"),
            shell_title=sh.get("title", ""),
            shell_login_enabled=(sh.get("login") or {}).get("enabled", True),
            menu_domains=(sh.get("menu") or {}).get("domains") or _derive_menu_from_entities(blueprint),
            menu_extensions=(sh.get("menu") or {}).get("extensions") or [],
            typedef_extra_services=(sh.get("typedef") or {}).get("extra_services") or [],
            frame_overrides=sh.get("frame_overrides") or {},
            branding=sh.get("branding") or {},
            nexacrolib_from=nexacrolib_from,
        )
    return ui_overlay_registry.dispatch(ui, **overlay_kwargs)
```

Add helper `_derive_menu_from_entities(blueprint)` that groups entities by `.domain`.

- [ ] **Step 5: Run test to verify pass**

```powershell
cd D:\AI\workspace\business-fullstack-creater; pytest tests/test_cli_shell_mode.py -v
```

Expected: 2 PASS.

- [ ] **Step 6: Run full regression**

```powershell
cd D:\AI\workspace\business-fullstack-creater; pytest -q
```

- [ ] **Step 7: Commit (per-file)**

```powershell
git -C D:\AI\workspace\business-fullstack-creater add scripts/scaffold_cli.py
git -C D:\AI\workspace\business-fullstack-creater commit -m @'
feat(scaffold_cli): --shell-mode + --nexacrolib-from + --ui nexacro-shell

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
'@
git -C D:\AI\workspace\business-fullstack-creater add scripts/scaffold_orchestrator.py
git -C D:\AI\workspace\business-fullstack-creater commit -m @'
feat(scaffold_orchestrator): pass shell_mode/nexacrolib_from through to overlay

blueprint.shell 의 menu/login/typedef/frame_overrides 를 nexacro-shell adapter
에 전달. 기존 --ui nexacro 경로 무변경.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
'@
git -C D:\AI\workspace\business-fullstack-creater add tests/test_cli_shell_mode.py
git -C D:\AI\workspace\business-fullstack-creater commit -m @'
test(cli): --shell-mode 인자 파싱 + --ui nexacro 회귀

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
'@
```

- [ ] **Step 8: P3 mini 5축** → 4·3·3·3·5 평균 3.6 PASS

---

## Task 5: 배송관리 standalone E2E golden (P4)

**Files:**
- Create: `D:\AI\workspace\business-fullstack-creater\tests\fixtures\shell-shipping\blueprint.yaml`
- Create: `D:\AI\workspace\business-fullstack-creater\tests\fixtures\shell-shipping\golden\frame_main.xfdl`
- Create: `D:\AI\workspace\business-fullstack-creater\tests\fixtures\shell-shipping\golden\frame_mdi.xfdl`
- Create: `D:\AI\workspace\business-fullstack-creater\tests\fixtures\shell-shipping\golden\typedefinition.xml`
- Create: `D:\AI\workspace\business-fullstack-creater\tests\fixtures\shell-shipping\golden\packageN.xadl`
- Create: `D:\AI\workspace\business-fullstack-creater\tests\test_shell_shipping_e2e.py`

- [ ] **Step 1: Write blueprint.yaml fixture**

```yaml
version: 1
domain: 배송관리
entities:
  - name: courier
    domain: 배송관리
    pattern: C1
    columns: [{name: id, type: bigserial, pk: true}, {name: code, type: varchar(40)}]
  - name: delivery
    domain: 배송관리
    pattern: MD
    columns: [{name: id, type: bigserial, pk: true}, {name: status, type: varchar(20)}]
  - name: delivery_item
    domain: 배송관리
    pattern: D2
    columns: [{name: id, type: bigserial, pk: true}, {name: delivery_id, type: bigint}]
  - name: delivery_tracking
    domain: 배송관리
    pattern: RO
    columns: [{name: id, type: bigserial, pk: true}, {name: event_type, type: varchar(40)}]
shell:
  kind: SHELL
  variant: MDI
  title: 배송관리 시스템
  login: {enabled: true, template: minimal}
  menu:
    root_label: 업무 메뉴
    domains:
      - id: 배송관리
        label: 배송 관리
        sort: 10
        entities: [delivery, courier, delivery_item, delivery_tracking]
```

- [ ] **Step 2: Write failing E2E test**

```python
# tests/test_shell_shipping_e2e.py
import pathlib, subprocess, sys, shutil

FIX = pathlib.Path(__file__).parent / "fixtures" / "shell-shipping"


def test_shipping_shell_emits_golden(tmp_path):
    out = tmp_path / "out"
    target = tmp_path / "target"
    cli = pathlib.Path(__file__).parent.parent / "scripts" / "scaffold_cli.py"
    r = subprocess.run(
        [sys.executable, str(cli),
         "--blueprint", str(FIX / "blueprint.yaml"),
         "--out", str(out),
         "--target", str(target),
         "--ui", "nexacro-shell"],
        capture_output=True, text=True,
    )
    assert r.returncode == 0, f"stderr: {r.stderr}"

    for fname in ("frame_main.xfdl", "frame_mdi.xfdl", "typedefinition.xml", "packageN.xadl"):
        emitted = (target / "nxui" / "packageN" / ("frame" if fname.startswith("frame_") else "") / fname)
        if not emitted.exists():
            emitted = target / "nxui" / "packageN" / fname
        golden = FIX / "golden" / fname
        assert emitted.read_text(encoding="utf-8").strip() == golden.read_text(encoding="utf-8").strip(), \
            f"{fname} diverges from golden"
```

- [ ] **Step 3: Run E2E once to capture actual output, freeze as golden**

```powershell
cd D:\AI\workspace\business-fullstack-creater; pytest tests/test_shell_shipping_e2e.py -v
# 첫 실행: golden 없음 → fail
# 수동으로 emit 결과 검토 후 golden/ 에 복사
python scripts/scaffold_cli.py --blueprint tests/fixtures/shell-shipping/blueprint.yaml --out /tmp/out --target /tmp/tgt --ui nexacro-shell
# inspect /tmp/tgt 결과, 만족하면 golden/ 으로 복사
```

- [ ] **Step 4: Re-run, expect PASS**

```powershell
pytest tests/test_shell_shipping_e2e.py -v
```

- [ ] **Step 5: Optional mvn package WAR build**

```powershell
# nexacrolib 가 vendor 가능한 경우만:
python scripts/scaffold_cli.py --blueprint tests/fixtures/shell-shipping/blueprint.yaml --out /tmp/out --target /tmp/tgt --ui nexacro-shell --nexacrolib-from <path/to/nexacrolib>
cd /tmp/tgt; mvn package
# WAR 산출 확인 (옵션 — nexacrolib 없으면 skip)
```

- [ ] **Step 6: Commit (per-file)**

```powershell
git -C D:\AI\workspace\business-fullstack-creater add tests/fixtures/shell-shipping/blueprint.yaml
git -C D:\AI\workspace\business-fullstack-creater commit -m @'
test(fixtures): shell-shipping blueprint (4 entity, MDI shell)
Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
'@
# 각 golden 파일 별도 commit
git -C D:\AI\workspace\business-fullstack-creater add tests/fixtures/shell-shipping/golden/frame_main.xfdl
git -C D:\AI\workspace\business-fullstack-creater commit -m "test(fixtures): shell-shipping frame_main.xfdl golden"
# ... 나머지 3개 golden 파일 동일 패턴
git -C D:\AI\workspace\business-fullstack-creater add tests/test_shell_shipping_e2e.py
git -C D:\AI\workspace\business-fullstack-creater commit -m @'
test(e2e): shell-shipping standalone WAR scaffold byte-golden
Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
'@
```

- [ ] **Step 7: P4 mini 5축** → 5·5·4·5·5 평균 4.8 PASS

---

## Task 6: SDI variant golden (P5)

**Files:**
- Create: `D:\AI\workspace\business-fullstack-creater\tests\fixtures\shell-shipping-sdi\blueprint.yaml` (variant: SDI)
- Create: `D:\AI\workspace\business-fullstack-creater\tests\fixtures\shell-shipping-sdi\golden\` (xfdl/xadl)
- Create: `D:\AI\workspace\business-fullstack-creater\tests\test_shell_sdi_e2e.py`

- [ ] **Step 1: Write SDI blueprint variant**

`shell-shipping/blueprint.yaml` 을 카피, `shell.variant: SDI` 만 변경. 메뉴 entity 1개로 축소 권장.

- [ ] **Step 2: Write SDI E2E test** (mirror Task 5 structure with frame_sdi.xfdl 검증)

```python
def test_sdi_emits_frame_sdi_not_mdi(tmp_path):
    ...
    assert (target / "nxui" / "packageN" / "frame" / "frame_sdi.xfdl").exists()
    assert not (target / "nxui" / "packageN" / "frame" / "frame_mdi.xfdl").exists()
```

- [ ] **Step 3: Run, capture golden, commit per-file (blueprint, 3 golden, test 별도)**

- [ ] **Step 4: P5 mini 5축** → 5·5·5·5·5 평균 5.0 PASS

---

## Task 7: blueprint-spec.md + USER-GUIDE + v0.7.0 tag (P6)

**Files:**
- Modify: `D:\AI\workspace\andrej-karpathy-rdb-skill\.claude\skills\karpathy-rdb\references\blueprint-spec.md`
- Modify: `D:\AI\workspace\business-fullstack-creater\USER-GUIDE.md`

- [ ] **Step 1: blueprint-spec.md — add `shell:` optional section**

선택적 최상위 필드. 기존 blueprint 의 호환성 유지 (없을 때 default 추론). spec §3-3 의 YAML 예시를 복붙 + 각 슬롯의 의미 1-2 line.

- [ ] **Step 2: Commit blueprint-spec.md**

```powershell
git -C D:\AI\workspace\andrej-karpathy-rdb-skill add .claude/skills/karpathy-rdb/references/blueprint-spec.md
git -C D:\AI\workspace\andrej-karpathy-rdb-skill commit -m @'
docs(blueprint-spec): shell: 선택 블록 (Growth-16)

variant/login/menu/typedef/frame_overrides 명시. 미지정 시 기본 추론.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
'@
```

- [ ] **Step 3: USER-GUIDE.md — Growth-16 SHELL §**

다음 내용 포함:
- standalone vs merge 의사결정 표 (언제 nexacro-shell vs nexacro)
- CLI 예시 (배송관리 1도메인)
- blueprint.shell 블록 요점
- nexacrolib vendor 안내
- 3축 복리 성장 관점에서의 의미 (Frontend 축의 project-level 자산)

- [ ] **Step 4: Commit USER-GUIDE.md**

- [ ] **Step 5: 전체 pytest sweep (3 레포)**

```powershell
cd D:\AI\workspace\andrej-karpathy-rdb-nexacro; pytest -q
cd D:\AI\workspace\business-fullstack-creater; pytest -q
cd D:\AI\workspace\andrej-karpathy-rdb-skill; pytest -q
```

Expected: all green. 회귀 0.

- [ ] **Step 6: 최종 5축 자체 리뷰 (CLAUDE.md 기준)**

평균 ≥ 4 시 PASS. 산정 결과를 본 plan 의 새 § "최종 5축 결과" 에 기록 (per-file commit).

- [ ] **Step 7: v0.7.0 annotated tag (각 레포)**

```powershell
git -C D:\AI\workspace\andrej-karpathy-rdb-nexacro tag -a v0.6.0 -m @'
Growth-16 SHELL pattern (8번째 패턴, kind=shell, MDI+SDI variants)
'@
git -C D:\AI\workspace\business-fullstack-creater tag -a v0.7.0 -m @'
Growth-16 — standalone nexacro shell scaffold (--ui nexacro-shell)
- patterns/SHELL: MDI/SDI variants + 6 frame templates
- nexacro_shell_overlay adapter + ui_overlay_registry 등록
- CLI --shell-mode / --nexacrolib-from
- 배송관리/SDI golden E2E
- blueprint.shell 선택 블록 (skill v0.4.1)
'@
git -C D:\AI\workspace\andrej-karpathy-rdb-skill tag -a v0.4.1 -m @'
docs(blueprint-spec): shell: 선택 블록 (Growth-16)
'@
```

푸시는 사용자가 수동 (`! git push --tags`).

- [ ] **Step 8: P6 mini 5축** → 5·5·5·4·5 평균 4.8 PASS

---

## Verification

1. **단위**: `pytest tests/test_resolve_shell.py`, `tests/test_nexacro_shell_overlay.py`, `tests/test_cli_shell_mode.py` 모두 PASS
2. **E2E**: `tests/test_shell_shipping_e2e.py` (MDI), `tests/test_shell_sdi_e2e.py` (SDI) byte-golden PASS
3. **회귀 0**: 3 레포 `pytest -q` 모두 prior tests 100% PASS
4. **정책**: `git -C D:\AI\workspace\nexacroN-fullstack diff --stat` empty (변경 0)
5. **5축 평균 ≥ 4** (CLAUDE.md 기준)
6. **3축 복리 성장 등록**:
   - Backend: 변경 없음 (Stage 2 그대로)
   - Middle: 변경 없음 (Stage 3 그대로)
   - Frontend: ✅ `patterns/SHELL/` 신규 자산 + `nexacro_shell_overlay` 신규 adapter
7. **버전**: nexacro v0.6.0, business-fullstack-creater v0.7.0, skill v0.4.1 annotated tag

---

## 위험과 완화 (실행 시 주의)

| 위험 | 신호 | 즉시 대응 |
|---|---|---|
| nexacrolib 없이 mvn 실패 | P4 step 5 에서 빌드 에러 | optional 처리, P4 step 5 skip 후 P5 진행 |
| frame_main.xfdl 의 frameset rows/cols 가 실제 nexacrolib 와 불일치 | 사용자 검증 시 화면 깨짐 | nexacroN-fullstack `frame*.xfdl` 의 구조를 참고 (단, **카피 금지** — 좌표만 학습) |
| 한국어 디렉터리 (배송관리) 골든 인코딩 | byte diff 실패 | `write_text(..., encoding="utf-8")` 일관 사용, CRLF→LF 정규화 |
| _derive_menu_from_entities 가 entity.domain 누락 시 빈 메뉴 | menu 비어있음 | 기본값으로 single-domain 메뉴 + warning 로그 |
| Task 5 golden 캡처 시 비결정성 (timestamp 등) | 재실행 시 diff | 템플릿에 timestamp 사용 금지 |

---

## Execution Handoff

플랜 저장 위치: `D:\AI\workspace\business-fullstack-creater\docs\superpowers\plans\2026-05-20-growth-16-shell-pattern-plan.md`

실행 옵션 (사용자 선택):
1. **Inline (executing-plans)** — 현재 세션에서 P1~P6 순차 실행, Phase Gate 마다 5축 자체 리뷰 보고
2. **Subagent-driven** — Task 단위로 fresh subagent + 2-stage review

(사용자 standing rule: "검증과정을 거치면서 auto mode 로" — 기본은 Inline + Phase Gate 자체 리뷰)
