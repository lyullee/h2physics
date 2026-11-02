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


def test_physics_adapters_do_not_require_workbook_extra(tmp_path):
    """A genuinely absent workbook dependency must not block unrelated physics."""
    code = '''
import importlib
import importlib.abc
import sys
class NoWorkbook(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] == 'openpyxl':
            raise ModuleNotFoundError('Workbook extra deliberately unavailable')
sys.meta_path.insert(0, NoWorkbook())
for module in (
    'h2physics.adapters.indoor_release', 'h2physics.adapters.par_device',
    'h2physics.adapters.thermal_cycles', 'h2physics.adapters.liquefaction_cycle',
    'h2physics.storage.redox_equilibrium',
):
    importlib.import_module(module)
assert 'openpyxl' not in sys.modules
'''
    environment = os.environ.copy()
    source = Path(__file__).resolve().parents[1] / "src"
    environment["PYTHONPATH"] = str(source) + os.pathsep + environment.get("PYTHONPATH", "")
    result = subprocess.run([sys.executable, "-c", code], cwd=tmp_path, env=environment,
                            capture_output=True, text=True, encoding="utf-8",
                            errors="replace", timeout=120, check=False)
    assert result.returncode == 0, result.stderr[-6000:]
