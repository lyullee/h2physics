"""Metadata stays lightweight while root-level model exports keep identity."""

import os
import subprocess
import sys
from pathlib import Path

import pytest


def test_metadata_imports_need_no_numerical_or_optional_engines(tmp_path):
    environment = os.environ.copy()
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    source = Path(__file__).resolve().parents[1] / "src"
    environment["PYTHONPATH"] = str(source) + os.pathsep + environment.get("PYTHONPATH", "")
    code = """
import builtins,sys
blocked = {'numpy', 'scipy', 'CoolProp', 'cantera'}
assert not blocked.intersection(sys.modules)
original = builtins.__import__
def guarded(name,*args,**kwargs):
    if name.split('.')[0] in blocked:
        raise RuntimeError('Metadata unexpectedly imported numerical engine: '+name)
    return original(name,*args,**kwargs)
builtins.__import__ = guarded
import h2physics
import h2physics.catalog
import h2physics.cluster_validation
assert not blocked.intersection(sys.modules)
assert h2physics.__version__ == '0.1.0.dev0'
"""
    result = subprocess.run(
        [sys.executable, "-c", code], cwd=tmp_path, env=environment,
        capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120,
    )
    assert result.returncode == 0, result.stderr[-6000:]


def test_public_exports_keep_actual_native_objects_and_cache():
    import h2physics
    from h2physics.caloric_pipe_waves import CaloricPipeWaveModel
    from h2physics.mixtures import GasComposition
    from h2physics.scenarios import OperationalScenario
    from h2physics.thermo.isothermal_eos import CoolPropIsothermalEOS

    assert len(h2physics.__all__) == 81
    assert h2physics.CaloricPipeWaveModel is CaloricPipeWaveModel
    assert h2physics.GasComposition is GasComposition
    assert h2physics.OperationalScenario is OperationalScenario
    assert h2physics.CoolPropIsothermalEOS is CoolPropIsothermalEOS
    assert all(getattr(h2physics, name) is not None for name in h2physics.__all__)
    assert set(h2physics.__all__).issubset(dir(h2physics))
    assert h2physics.mixtures.GasComposition is GasComposition
    with pytest.raises(AttributeError, match="has no attribute"):
        getattr(h2physics, "an_unregistered_physical_model")
