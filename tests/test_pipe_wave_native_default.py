"""The production pipe-wave default owns native fluid properties explicitly."""

import builtins

import numpy as np
import pytest

from h2physics.isothermal_pipe_waves import (
    IdealHydrogenIsothermalEOS,
    IsothermalPipeWaveModel,
)
from h2physics.thermo.isothermal_eos import CoolPropIsothermalEOS


def _model(**kwargs):
    return IsothermalPipeWaveModel(
        length_m=10., internal_diameter_m=.1, cell_count=4,
        temperature_k=300., **kwargs,
    )


def test_default_trace_uses_direct_native_high_pressure_density():
    cp = pytest.importorskip("CoolProp.CoolProp")
    model = _model()
    assert isinstance(model.eos, CoolPropIsothermalEOS)
    pressure = 70.e6
    expected = cp.PropsSI("Dmass", "P", pressure, "T", 300., "HEOS::Hydrogen")
    trace = model.simulate(
        initial_pressure_pa=np.full(4, pressure),
        initial_velocity_m_s=np.zeros(4), time_samples_s=(0., 1.e-5),
    )
    np.testing.assert_allclose(trace.density_kg_m3, expected, rtol=1.e-12)
    assert trace.eos_closure_id == model.eos.identity
    ideal = IdealHydrogenIsothermalEOS().density_pt(pressure, 300.)
    assert abs(expected - ideal) / expected > .01


def test_missing_coolprop_raises_without_ideal_fallback(monkeypatch):
    original_import = builtins.__import__

    def without_coolprop(name, *args, **kwargs):
        if name == "CoolProp" or name.startswith("CoolProp."):
            raise ImportError("simulated missing optional dependency")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", without_coolprop)
    with pytest.raises(ImportError, match="h2physics\\[thermo\\]"):
        _model()
    reference = IdealHydrogenIsothermalEOS()
    assert _model(eos=reference).eos is reference


def test_default_model_propagates_native_liquid_phase_rejection():
    cp = pytest.importorskip("CoolProp.CoolProp")
    pressure, temperature = 1.e6, 20.
    assert cp.PhaseSI("P", pressure, "T", temperature, "HEOS::Hydrogen") == "liquid"
    model = IsothermalPipeWaveModel(
        length_m=10., internal_diameter_m=.1, cell_count=4,
        temperature_k=temperature,
    )
    with pytest.raises(ValueError, match="homogeneous gas/supercritical"):
        model.simulate(
            initial_pressure_pa=np.full(4, pressure),
            initial_velocity_m_s=np.zeros(4), time_samples_s=(0., 1.e-5),
        )
