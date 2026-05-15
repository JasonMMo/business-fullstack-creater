import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent / "v0.3-phase-a-mn"
STAGE1 = pathlib.Path(r"D:\AI\workspace\andrej-karpathy-rdb-skill")
STAGE2 = pathlib.Path(r"D:\AI\workspace\andrej-karpathy-rdb-ddl")


def test_e2e_mn_junction(tmp_path):
    # 1) Stage 1: compile wiki → _blueprint.yaml + compile-report.md
    r1 = subprocess.run(
        [sys.executable, str(STAGE1 / "scripts" / "rdb_index.py"), "compile", str(ROOT)],
        capture_output=True, text=True,
    )
    assert r1.returncode == 0, f"Stage 1 failed:\nSTDOUT:{r1.stdout}\nSTDERR:{r1.stderr}"
    assert "ERROR: 0" in r1.stdout, r1.stdout
    # V005 junction INFO is emitted into _blueprint.yaml validation.infos
    bp_text = (ROOT / "_blueprint.yaml").read_text(encoding="utf-8")
    report = (ROOT / "compile-report.md").read_text(encoding="utf-8")
    assert "V005" in bp_text or "junction" in bp_text.lower() or "V005" in report or "junction" in report.lower(), \
        f"V005 junction not found in blueprint or report.\nBP:\n{bp_text}\nREPORT:\n{report}"

    # 2) Stage 2: compile blueprint → DDL into tmp_path
    bp = ROOT / "_blueprint.yaml"
    r2 = subprocess.run(
        [sys.executable, str(STAGE2 / "scripts" / "ddl_compile.py"),
         str(bp), "--out", str(tmp_path), "--dialect", "postgres"],
        capture_output=True, text=True,
    )
    assert r2.returncode == 0, f"Stage 2 failed:\nSTDOUT:{r2.stdout}\nSTDERR:{r2.stderr}"

    # 3) Assert composite PK and both FKs in generated SQL
    tables_sql = (tmp_path / "migrations" / "V002__create_tables.sql").read_text(encoding="utf-8")
    assert "PRIMARY KEY (user_id, role_id)" in tables_sql, tables_sql

    fk_sql = (tmp_path / "migrations" / "V004__create_constraints.sql").read_text(encoding="utf-8")
    # Two FK constraints — names follow `fk_<table>__<col>` from _gather_foreign_keys
    assert "fk_user_role__user_id" in fk_sql, fk_sql
    assert "fk_user_role__role_id" in fk_sql, fk_sql
    assert "REFERENCES" in fk_sql and "user(id)" in fk_sql.replace(" ", "")  # parent ref
