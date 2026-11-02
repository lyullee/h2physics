import numpy as np
import pytest

from h2physics.adapters.psa import BedFaceTransfers, PsaDynaBed, PsaDynaEquilibrium
from h2physics.adsorption import (
    AdsorptionBasis,
    AdsorptionDomain,
    AdsorptionState,
    loading_working_capacity,
)


def test_native_boundary_converts_pressure_and_derivative_axes_without_solver_copy():
    calls = []

    def native(pressure_bar, temperature, material):
        calls.append((pressure_bar.copy(), temperature))
        return np.array([[material["capacity"]]]), np.array([[[3.]]]), np.array([[4.]])

    basis = AdsorptionBasis("authored", ("H2",), "absolute:dry-adsorbent", "test-native", "parameters-v1", ("test",))
    material = {"capacity": 2., "species_order": ["H2"]}
    adapter = PsaDynaEquilibrium(native, material, basis, AdsorptionDomain(290, 350, 1e6))
    material["capacity"] = 99
    state = adapter.equilibrium([2e5], 300)
    np.testing.assert_allclose(calls[0][0], [2.])
    assert state.site_pressure_derivatives_mol_kg_pa[0, 0, 0] == pytest.approx(3e-5)
    assert state.loadings_mol_kg[0] == 2
    assert not state.site_loadings_mol_kg.flags.writeable
    assert loading_working_capacity(state, state)[0] == 0
    with pytest.raises(ValueError, match="nonnegative"):
        adapter.equilibrium([-1], 300)
    with pytest.raises(ValueError, match="domain"):
        adapter.equilibrium([1e5], 200)


def test_signed_surface_excess_is_distinct_from_nonnegative_absolute_uptake():
    from dataclasses import replace

    basis = AdsorptionBasis("authored", ("H2",), "surface-excess:pore-reference-v1", "test", "v1", ("test",),
                             loading_definition="surface_excess")
    state = AdsorptionState(basis, np.array([1e5]), 300., np.array([[-.1]]))
    assert state.loadings_mol_kg[0] == -.1
    with pytest.raises(ValueError, match="absolute uptake"):
        AdsorptionState(replace(basis, loading_definition="absolute"), np.array([1e5]), 300., np.array([[-.1]]))


def test_native_bed_transfer_energy_and_uptake_basis_guards_precede_rate_call():
    from types import SimpleNamespace

    basis = AdsorptionBasis("authored", ("H2",), "absolute:dry", "test", "v1", ("test",), loading_definition="absolute")
    native = SimpleNamespace(ns=1, n=2, nv=4, size=8, mode="loading_ldf")
    native.fields = lambda state: (np.ones((2, 1)), np.ones((2, 1)), np.full(2, 300.),
                                   np.full(2, 300.), np.ones(2), np.ones((2, 1)))
    native.rates = lambda *args: (_ for _ in ()).throw(AssertionError("Native rate must not be called"))
    adapter = PsaDynaBed(native, basis, AdsorptionDomain(290, 350, 1e6), energy_reference_id="native-reference")
    transfers = BedFaceTransfers(("H2",), np.zeros((3, 1)), np.zeros(3), "incompatible-reference")
    with pytest.raises(ValueError, match="energy reference"):
        adapter.rates(np.ones(8), transfers)
    with pytest.raises(ValueError, match="Negative"):
        adapter.snapshot(-np.ones(8))
