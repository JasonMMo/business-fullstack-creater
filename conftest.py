import sys, pathlib

# Add scripts/ to sys.path so tests can import scaffold_orchestrator, stage_paths, etc.
sys.path.insert(0, str(pathlib.Path(__file__).parent / "scripts"))
