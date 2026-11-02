import hashlib
from pathlib import Path

import numpy as np
import pytest

from h2physics.adapters.cantera import MechanismBasis
from h2physics.adapters.cantera_thermo import CanteraMolarEnthalpy
from h2physics.reactions import StoichiometricReaction, conversion_heat_j, solve_product_temperature


def test_actual_native_thermochemistry_and_fixed_extent_energy():
    ct = pytest.importorskip("cantera")
    raw = (Path(ct.__file__).parent / "data/gri30.yaml").read_bytes()
    basis = MechanismBasis("authored-gri-calorimetry", hashlib.sha256(raw).hexdigest(),
        "BSD-3-Clause; GRI-Mech provenance", ("https://cantera.org/3.2/examples/input/gri30.html",),
        200, 3000, 1e4, 2e6)
    provider = CanteraMolarEnthalpy(lambda: ct.Solution(yaml=raw.decode("utf-8")), basis,
                                   ("CH4", "H2O", "CO", "H2"))
    reaction = StoichiometricReaction("prescribed-steam-reforming", provider.species, (-1, -1, 1, 3))
    converted = reaction.convert({"CH4": 1, "H2O": 3}, .2)
    q = conversion_heat_j(converted, provider, inlet_temperature_k=298.15,
                          outlet_temperature_k=298.15, pressure_pa=101325)
    assert q/.2 == pytest.approx(206000, rel=.01)
    native = provider.native_phase
    native.TPX = 298.15, 101325, {"CH4": 1, "H2O": 3}
    hin = native.enthalpy_mole*4/1000
    native.TPX = 298.15, 101325, dict(converted.final_amounts)
    hout = native.enthalpy_mole*sum(converted.final_mol)/1000
    assert q == pytest.approx(hout-hin, abs=1e-8)
    adiabatic = solve_product_temperature(converted, provider, inlet_temperature_k=1200,
        pressure_pa=101325, supplied_heat_j=0, bracket_k=(400, 1600))
    assert 400 < adiabatic.temperature_k < 1200
    assert abs(adiabatic.energy_residual_j) < 1e-6
    assert provider.native_phase is native
    assert np.all(np.isfinite(provider.enthalpies_j_mol(1200, 101325)))
    with pytest.raises(ValueError, match="domain"):
        provider.enthalpies_j_mol(100, 101325)
