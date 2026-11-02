import numpy as np
import pytest

from h2physics.materials import HydrogenCarrier, PowerLawSolubility, SurfaceCondition
from h2physics.storage.finite_hydride import HydrideGasThermodynamics
from h2physics.storage.microsphere import MicrosphereDomain, MicrosphereStorage


@pytest.fixture
def gas():
    pytest.importorskip("CoolProp")
    return HydrideGasThermodynamics.coolprop("Hydrogen")


def model(gas, cells=12, *, coefficient=1e-5):
    carrier = HydrogenCarrier("molecular_hydrogen", gas.molar_mass_kg_mol)
    return MicrosphereStorage(inner_radius_m=1e-5, outer_radius_m=1.1e-5, cells=cells,
        diffusivity_m2_s=lambda t: 1e-14, solubility=PowerLawSolubility(
            carrier, lambda t: coefficient, 1.), gas=gas,
        domain=MicrosphereDomain(200., 600., 1., 1e7, 1e-20),
        parameter_evidence="authored-numerical-material-not-a-glass-fit")


def amount(storage, pressure=1e5, temperature=300.):
    return storage.gas.state_pt(pressure, temperature).density_kg_m3*storage.cavity_volume_m3/storage.gas.molar_mass_kg_mol


def run(storage, external, *, initial_wall=None, temperature=lambda t: 300., duration=100.):
    return storage.simulate(np.linspace(0., duration, 31), amount(storage),
        np.zeros(len(storage.mesh.cell_centers_m)) if initial_wall is None else initial_wall,
        temperature_k=temperature, external_hydrogen_fugacity_pa=lambda t: external,
        clock_id="authored-prescribed-clock", boundary_evidence="authored-bath-and-external-H2",
        maximum_step_s=2.)


def test_native_real_gas_release_and_total_inventory_accounting(gas):
    storage = model(gas)
    result = run(storage, 0.)
    assert result.gas_inventory_mol[-1] < result.gas_inventory_mol[0]
    assert result.gas_states[-1].pressure_pa < result.gas_states[0].pressure_pa
    assert result.transport.right_integrated_mol[-1] > 0
    scale = result.gas_inventory_mol[0]
    assert np.max(abs(result.gas_transfer_residual_mol))/scale < 1e-12
    assert np.max(abs(result.transport.total_residual_mol))/scale < 1e-10
    # Reconstruct the cavity independently through a second actual EOS object.
    import CoolProp.CoolProp as cp
    native = cp.AbstractState("HEOS", "Hydrogen")
    for n, state in zip(result.gas_inventory_mol, result.gas_states, strict=True):
        native.update(cp.DmolarT_INPUTS, n/storage.cavity_volume_m3, 300.)
        assert state.pressure_pa == pytest.approx(native.p(), rel=1e-10)
        assert storage.gas.fugacity_pa(state) == pytest.approx(native.fugacity(0), rel=1e-10)
    assert not result.gas_fugacity_pa.flags.writeable


def test_external_charge_and_uniform_equilibrium_use_fugacity_not_pressure(gas):
    storage = model(gas)
    charged = run(storage, 2e5, duration=300.)
    assert charged.gas_inventory_mol[-1] > charged.gas_inventory_mol[0]
    assert charged.transport.right_integrated_mol[-1] < 0
    state = gas.state_pt(1e5, 300.)
    fugacity = gas.fugacity_pa(state)
    wall = np.full(12, storage.solubility.concentration_mol_m3(fugacity, 300.))
    equilibrium = run(storage, fugacity, initial_wall=wall)
    np.testing.assert_allclose(equilibrium.gas_inventory_mol, equilibrium.gas_inventory_mol[0], rtol=1e-12)
    np.testing.assert_allclose(equilibrium.transport.mobile_mol_m3, wall[None, :]+np.zeros((31, 12)), rtol=1e-10)


def test_prescribed_heating_uses_same_native_fixed_spin_eos_without_energy_claim(gas):
    storage = model(gas, coefficient=0.)
    result = run(storage, 0., temperature=lambda t: 300.+t, duration=20.)
    np.testing.assert_allclose(result.gas_inventory_mol, result.gas_inventory_mol[0], rtol=1e-14)
    assert result.gas_states[-1].pressure_pa > result.gas_states[0].pressure_pa
    assert result.gas_states[-1].temperature_k == 320.
    assert result.gas_states[-1].basis.spin_composition == "normal"
    assert not hasattr(result, "energy_residual_j")


def test_mesh_refinement_reduces_finite_gas_wall_release_error(gas):
    outputs = [run(model(gas, cells=n), 0.).gas_inventory_mol[-1] for n in (8, 16, 32)]
    assert abs(outputs[0]-outputs[1])/abs(outputs[1]-outputs[2]) > 3.


def test_sealed_outer_wall_stores_hydrogen_without_losing_total_inventory(gas):
    storage = model(gas)
    result = storage.simulate([0., 20., 100.], amount(storage), np.zeros(12),
        temperature_k=lambda t: 300., external_wall_condition=lambda t, temp:
            SurfaceCondition("flux", 0.), clock_id="authored-sealed-clock",
        boundary_evidence="authored-impermeable-outer-coating", maximum_step_s=2.)
    assert result.transport.wall_inventory_mol[-1] > 0.
    assert result.gas_inventory_mol[-1] < result.gas_inventory_mol[0]
    assert result.transport.right_integrated_mol[-1] == 0.
    np.testing.assert_allclose(result.total_hydrogen_mass_kg,
        result.total_hydrogen_mass_kg[0], rtol=1e-10, atol=0.)


def test_carrier_identity_native_domain_and_missing_evidence_rejected(gas):
    storage = model(gas)
    with pytest.raises(ValueError, match="temperature"):
        storage.gas_state(amount(storage), 700.)
    with pytest.raises(ValueError, match="floor"):
        storage.gas_state(1e-22, 300.)
    with pytest.raises(ValueError, match="gas-like"):
        cold = MicrosphereStorage(inner_radius_m=1e-5, outer_radius_m=1.1e-5, cells=4,
            diffusivity_m2_s=lambda t: 1e-14, solubility=storage.solubility, gas=gas,
            domain=MicrosphereDomain(15., 100., 1., 1e8, 1e-20), parameter_evidence="authored")
        liquid = gas.state_pt(1e5, 18.)
        cold.gas_state(liquid.density_kg_m3*cold.cavity_volume_m3/gas.molar_mass_kg_mol, 18.)
    with pytest.raises(ValueError, match="clock"):
        storage.simulate([0, 1], amount(storage), np.zeros(12), temperature_k=lambda t: 300.,
            external_hydrogen_fugacity_pa=lambda t: 0., clock_id="", boundary_evidence="test")
    with pytest.raises(ValueError, match="mobile-entity"):
        MicrosphereStorage(inner_radius_m=1e-5, outer_radius_m=1.1e-5, cells=4,
            diffusivity_m2_s=lambda t: 1e-14, solubility=PowerLawSolubility(
                HydrogenCarrier("atomic_hydrogen", .001), lambda t: 1., .5), gas=gas,
            domain=storage.domain, parameter_evidence="authored")
