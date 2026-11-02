import numpy as np
import pytest

from h2physics.materials import (
    DiffusionSlab,
    HydrogenCarrier,
    PowerLawSolubility,
    SlabBoundary,
    SurfaceCondition,
    TrapPopulation,
    steady_permeation,
)

H = HydrogenCarrier("atomic_hydrogen", .001)


def test_steady_carrier_basis_and_reverse_pressure_gradient():
    solubility = PowerLawSolubility(H, lambda t: 2., .5)
    result = steady_permeation(solubility, diffusivity_m2_s=3., thickness_m=2.,
                               upstream_fugacity_pa=9., downstream_fugacity_pa=1., temperature_k=300.)
    assert result.mobile_entity_flux_mol_m2_s == 6.
    assert result.h2_equivalent_flux_mol_m2_s == 3.
    assert result.hydrogen_mass_flux_kg_m2_s == .006
    reverse = steady_permeation(solubility, diffusivity_m2_s=3., thickness_m=2.,
                                upstream_fugacity_pa=1., downstream_fugacity_pa=9., temperature_k=300.)
    assert reverse.mobile_entity_flux_mol_m2_s == -6.


def test_linear_steady_profile_and_independent_boundary_quadrature_close():
    n = 12
    x = (np.arange(n)+.5)/n
    model = DiffusionSlab(H, 1., n, lambda t: .1)
    result = model.simulate([0, .5, 1.], 1-x,
                            boundary=lambda t: SlabBoundary(SurfaceCondition("concentration", 1),
                                                             SurfaceCondition("concentration", 0)),
                            temperature_k=lambda t: 300.)
    np.testing.assert_allclose(result.mobile_mol_m3[-1], 1-x, atol=1e-10)
    assert result.left_integrated_flux_mol_m2[-1] == pytest.approx(.1)
    assert np.max(abs(result.inventory_residual_mol_m2)) < 1e-10


def test_startup_inventory_converges_to_independent_fourier_series():
    errors = []
    diffusion, final_time = .1, 1.
    odd = np.arange(1, 100, 2)
    exact = .5 - 4/np.pi**2 * np.sum(np.exp(-odd**2*np.pi**2*diffusion*final_time)/odd**2)
    for n in (20, 40, 80):
        model = DiffusionSlab(H, 1., n, lambda t: diffusion)
        result = model.simulate([0, final_time], np.zeros(n),
                                boundary=lambda t: SlabBoundary(SurfaceCondition("concentration", 1),
                                                                 SurfaceCondition("concentration", 0)),
                                temperature_k=lambda t: 300.)
        numerical = np.mean(result.mobile_mol_m3[-1])
        errors.append(abs(numerical-exact))
        assert np.max(abs(result.inventory_residual_mol_m2)) < 1e-8
    assert errors[0]/errors[1] > 3.5 and errors[1]/errors[2] > 3.5
    assert errors[-1] < 1e-4


def test_closed_trapping_conserves_mobile_plus_trapped_and_reaches_equilibrium():
    model = DiffusionSlab(H, 1., 5, lambda t: 1.,
                          traps=(TrapPopulation(2., lambda t: 1., lambda t: .5),))
    result = model.simulate([0, 5, 20], np.ones(5),
                            boundary=lambda t: SlabBoundary(SurfaceCondition("flux", 0),
                                                             SurfaceCondition("flux", 0)),
                            temperature_k=lambda t: 300.)
    mobile, trapped = result.mobile_mol_m3[-1], result.trapped_mol_m3[-1, 0]
    np.testing.assert_allclose(mobile+trapped, 1, atol=1e-9)
    np.testing.assert_allclose(trapped, 2*mobile/(mobile+.5), atol=1e-7)
    assert np.max(abs(result.inventory_residual_mol_m2)) < 1e-9
    assert not result.trapped_mol_m3.flags.writeable
