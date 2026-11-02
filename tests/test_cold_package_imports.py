"""Catch cross-package cycles that a warmed scientific process can hide."""

import os
import subprocess
import sys
from pathlib import Path

import pytest


@pytest.mark.parametrize("module", (
    "h2physics.storage",
    "h2physics.storage.porous_reservoir",
    "h2physics.adapters",
    "h2physics.thermo",
))
def test_package_import_from_fresh_interpreter(module, tmp_path):
    source = Path(__file__).resolve().parents[1] / "src"
    environment = os.environ.copy()
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    environment["PYTHONPATH"] = str(source) + os.pathsep + environment.get("PYTHONPATH", "")
    result = subprocess.run(
        [sys.executable, "-c", "import importlib,sys; importlib.import_module(sys.argv[1])", module],
        cwd=tmp_path, env=environment, capture_output=True, text=True,
        encoding="utf-8", errors="replace", timeout=120, check=False,
    )
    assert result.returncode == 0, result.stderr[-6000:]
