import sys, pathlib

_ROOT = pathlib.Path(__file__).parent
# Add scripts/ to sys.path so tests can import scaffold_orchestrator, stage_paths, etc.
sys.path.insert(0, str(_ROOT / "scripts"))
# Add repo root so `web` package is importable as `web.app` etc.
sys.path.insert(0, str(_ROOT))
