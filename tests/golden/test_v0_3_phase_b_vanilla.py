import json
import os
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent / "v0.3-phase-b-vanilla"
STAGE1 = pathlib.Path(r"D:\AI\workspace\andrej-karpathy-rdb-skill")
STAGE2 = pathlib.Path(r"D:\AI\workspace\andrej-karpathy-rdb-ddl")
STAGE3 = pathlib.Path(r"D:\AI\workspace\andrej-karpathy-rdb-mybatis")


def test_e2e_vanilla_lane(tmp_path):
    # Stage 1
    r1 = subprocess.run(
        [sys.executable, str(STAGE1 / "scripts" / "rdb_index.py"), "compile", str(ROOT)],
        capture_output=True, text=True,
    )
    assert r1.returncode == 0, f"Stage 1 failed:\nSTDOUT:{r1.stdout}\nSTDERR:{r1.stderr}"
    bp = ROOT / "_blueprint.yaml"
    assert bp.exists()

    # Stage 2
    db = tmp_path / "db"
    r2 = subprocess.run(
        [sys.executable, str(STAGE2 / "scripts" / "ddl_compile.py"),
         str(bp), "--out", str(db), "--dialect", "postgres"],
        capture_output=True, text=True,
    )
    assert r2.returncode == 0, f"Stage 2 failed:\nSTDOUT:{r2.stdout}\nSTDERR:{r2.stderr}"

    # Stage 3 vanilla
    backend = tmp_path / "backend"
    env = os.environ.copy()
    env["PYTHONPATH"] = str(STAGE3 / "scripts")
    r3 = subprocess.run(
        [sys.executable, str(STAGE3 / "scripts" / "compile.py"), "compile",
         "--blueprint", str(bp),
         "--ddl-dir", str(db / "migrations"),
         "--seed-dir", str(db / "seed"),
         "--out", str(backend),
         "--lane", "vanilla",
         "--package", "com.example.app",
         "--skip-compile"],
        capture_output=True, text=True, env=env,
    )
    assert r3.returncode == 0, f"Stage 3 failed:\nSTDOUT:{r3.stdout}\nSTDERR:{r3.stderr}"

    pkg = backend / "src" / "main" / "java" / "com" / "example" / "app"
    entity = (pkg / "domain" / "Product.java").read_text(encoding="utf-8")
    assert "extends NexacroBase" not in entity
    assert "package com.example.app.domain" in entity

    controller = (pkg / "controller" / "ProductController.java").read_text(encoding="utf-8")
    assert "@RestController" in controller
    assert "NexacroResult" not in controller
    assert "/api/product" in controller

    payload = json.loads((backend / "endpoints.json").read_text(encoding="utf-8"))
    assert payload["version"] == 2
    assert payload["lane"] == "vanilla"
    assert payload["entities"][0]["endpoint_base"] == "/api/product"
