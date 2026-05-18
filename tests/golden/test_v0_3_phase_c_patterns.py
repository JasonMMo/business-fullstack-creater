import os
import pathlib
import subprocess
import sys

ROOT   = pathlib.Path(__file__).resolve().parent / "v0.3-phase-c-patterns"
STAGE1 = pathlib.Path(r"D:\AI\workspace\andrej-karpathy-rdb-skill")
STAGE2 = pathlib.Path(r"D:\AI\workspace\andrej-karpathy-rdb-ddl")
STAGE4 = pathlib.Path(r"D:\AI\workspace\andrej-karpathy-rdb-nexacro")


def test_e2e_three_patterns(tmp_path):
    # Stage 1 — compile wiki → _blueprint.yaml
    r1 = subprocess.run(
        [sys.executable, str(STAGE1 / "scripts" / "rdb_index.py"), "compile", str(ROOT)],
        capture_output=True, text=True,
    )
    assert r1.returncode == 0, f"Stage 1 failed:\nSTDOUT:{r1.stdout}\nSTDERR:{r1.stderr}"

    bp = ROOT / "_blueprint.yaml"
    assert bp.exists(), "Blueprint file was not created by Stage 1"

    bp_text = bp.read_text(encoding="utf-8")
    assert "pattern: D2" in bp_text, f"D2 pattern not found in blueprint:\n{bp_text}"
    assert "pattern: F1" in bp_text, f"F1 pattern not found in blueprint:\n{bp_text}"
    assert "pattern: C1" in bp_text, f"C1 pattern not found in blueprint:\n{bp_text}"

    # Stage 2 — DDL compile
    db = tmp_path / "db"
    r2 = subprocess.run(
        [sys.executable, str(STAGE2 / "scripts" / "ddl_compile.py"),
         str(bp), "--out", str(db), "--dialect", "postgres"],
        capture_output=True, text=True,
    )
    assert r2.returncode == 0, f"Stage 2 failed:\nSTDOUT:{r2.stdout}\nSTDERR:{r2.stderr}"

    # Stage 4 — form_gen compile
    nexacro = tmp_path / "nexacro"
    env = os.environ.copy()
    env["PYTHONPATH"] = str(STAGE4 / "scripts")
    r4 = subprocess.run(
        [sys.executable, str(STAGE4 / "scripts" / "form_gen.py"), "compile",
         "--blueprint", str(bp),
         "--infer-endpoints",
         "--out", str(nexacro)],
        capture_output=True, text=True, env=env,
    )
    assert r4.returncode == 0, f"Stage 4 failed:\nSTDOUT:{r4.stdout}\nSTDERR:{r4.stderr}"

    form_dir = nexacro / "nxui" / "_form_"

    # order_header — D2: Grid present, btn_save present
    xfdl_order_header = (form_dir / "order_header.xfdl").read_text(encoding="utf-8")
    assert "<Grid" in xfdl_order_header, \
        f"D2 (order_header): expected <Grid but not found:\n{xfdl_order_header[:2000]}"
    assert "btn_save" in xfdl_order_header, \
        f"D2 (order_header): expected btn_save but not found:\n{xfdl_order_header[:2000]}"

    # order_detail — F1: no Grid, btn_save present
    xfdl_order_detail = (form_dir / "order_detail.xfdl").read_text(encoding="utf-8")
    assert "<Grid" not in xfdl_order_detail, \
        f"F1 (order_detail): expected NO <Grid but found one:\n{xfdl_order_detail[:2000]}"
    assert "btn_save" in xfdl_order_detail, \
        f"F1 (order_detail): expected btn_save but not found:\n{xfdl_order_detail[:2000]}"

    # code_master — C1: Grid present, btn_save absent, btn_select present
    xfdl_code_master = (form_dir / "code_master.xfdl").read_text(encoding="utf-8")
    assert "<Grid" in xfdl_code_master, \
        f"C1 (code_master): expected <Grid but not found:\n{xfdl_code_master[:2000]}"
    assert "btn_save" not in xfdl_code_master, \
        f"C1 (code_master): expected NO btn_save but found one:\n{xfdl_code_master[:2000]}"
    assert "btn_select" in xfdl_code_master, \
        f"C1 (code_master): expected btn_select but not found:\n{xfdl_code_master[:2000]}"
