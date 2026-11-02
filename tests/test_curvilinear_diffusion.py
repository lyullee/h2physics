import numpy as np
import pytest

from h2physics.materials import (
    DiffusionDomain,
    DiffusionMesh,
    FiniteSurfaceInventory,
    HydrogenCarrier,
    SurfaceCondition,
    TransportBoundary,
    TrapPopulation,
)

H2 = HydrogenCarrier("molecular_hydrogen", .002)


def faces(left=1., right=0.):
    return lambda t: TransportBoundary(SurfaceCondition("concentration", left),
                                        SurfaceCondition("concentration", right))


def test_spherical_steady_rate_is_exact_radial_resistance_not_planar_area():
    inner, outer, diffusion = 1., 2., .1
    mesh = DiffusionMesh.spherical_shell(inner, outer, 12)
    c = (1/mesh.cell_centers_m-1/outer)/(1/inner-1/outer)
    run = DiffusionDomain(H2, mesh, lambda t: diffusion).simulate(
        [0, 1], c, boundary=faces(), temperature_k=lambda t: 300.)
    exact_rate = 4*np.pi*diffusion/(1/inner-1/outer)
    np.testing.assert_allclose(run.mobile_mol_m3[-1], c, rtol=0, atol=1e-12)
    assert run.left_integrated_mol[-1] == pytest.approx(exact_rate, rel=1e-11)
    assert run.right_integrated_mol[-1] == pytest.approx(exact_rate, rel=1e-11)
    assert np.max(abs(run.wall_residual_mol)) < 1e-12
    assert run.native_solution.success


def test_spherical_startup_converges_to_independent_separation_of_variables_inventory():
    inner, outer, diffusion, time = 1., 2., .1, 1.
    length = outer-inner
    k = np.arange(1, 101)
    exact = 4*np.pi*inner*(inner*length/2+length**2/6)-8*np.pi*inner*length*np.sum(
        (inner-outer*(-1.)**k)/(k*np.pi)**2*np.exp(-diffusion*(k*np.pi/length)**2*time))
    errors = []
    for cells in (20, 40, 80):
        mesh = DiffusionMesh.spherical_shell(inner, outer, cells)
        run = DiffusionDomain(H2, mesh, lambda t: diffusion).simulate(
            [0, time], np.zeros(cells), boundary=faces(), temperature_k=lambda t: 300.)
        errors.append(abs(run.wall_inventory_mol[-1]-exact))
        assert np.max(abs(run.wall_residual_mol)) < 1e-8
    assert errors[0]/errors[1] > 3.5 and errors[1]/errors[2] > 3.5


def test_finite_both_sides_preserve_total_entity_inventory_with_traps():
    mesh = DiffusionMesh.spherical_shell(1., 2., 10)
    model = DiffusionDomain(H2, mesh, lambda t: .2,
        traps=(TrapPopulation(2., lambda t: 1., lambda t: .5),))
    left = FiniteSurfaceInventory(20., 1e-6,
        lambda t, n: SurfaceCondition("concentration", n/20), "authored-left-volume")
    right = FiniteSurfaceInventory(10., 1e-6,
        lambda t, n: SurfaceCondition("concentration", n/10), "authored-right-volume")
    run = model.simulate([0, 1, 10], np.zeros(10),
        boundary=lambda t: TransportBoundary(None, None), temperature_k=lambda t: 300.,
        left_inventory=left, right_inventory=right)
    total = run.wall_inventory_mol+run.left_inventory_mol+run.right_inventory_mol
    np.testing.assert_allclose(total, total[0], rtol=0, atol=1e-9)
    assert np.max(abs(run.total_residual_mol)) < 1e-9
    assert np.max(abs(run.wall_residual_mol)) < 1e-9
    assert run.trapped_mol_m3[-1].sum() > 0
    assert not run.left_inventory_mol.flags.writeable


def test_imposed_coordinate_flux_scales_each_spherical_face_area():
    mesh = DiffusionMesh.spherical_shell(1., 2., 5)
    run = DiffusionDomain(H2, mesh, lambda t: 1.).simulate(
        [0, .1], np.ones(5), temperature_k=lambda t: 300., boundary=lambda t:
        TransportBoundary(SurfaceCondition("flux", .02), SurfaceCondition("flux", .01)))
    assert run.left_integrated_mol[-1] == pytest.approx(.1*4*np.pi*.02)
    assert run.right_integrated_mol[-1] == pytest.approx(.1*16*np.pi*.01)
    assert np.max(abs(run.total_residual_mol)) < 1e-12


def test_finite_inventory_floor_and_competing_boundary_ownership_are_rejected():
    mesh = DiffusionMesh.planar(1., 4)
    model = DiffusionDomain(H2, mesh, lambda t: 1.)
    store = FiniteSurfaceInventory(.1, .01,
        lambda t, n: SurfaceCondition("flux", 1.), "authored-forced-overdraw")
    with pytest.raises(ValueError, match="both own"):
        model.simulate([0, 1], np.zeros(4), boundary=faces(),
            temperature_k=lambda t: 300., left_inventory=store)
    with pytest.raises(ValueError, match="floor"):
        model.simulate([0, 1], np.zeros(4),
            boundary=lambda t: TransportBoundary(None, SurfaceCondition("flux", 0)),
            temperature_k=lambda t: 300., left_inventory=store)


def test_thin_spherical_shell_recovers_planar_flux_and_geometry_is_guarded():
    inner, length = 1., 1e-5
    exact_sphere = 4*np.pi*inner*(inner+length)/length
    planar = 4*np.pi*inner**2/length
    assert exact_sphere/planar == pytest.approx(1., rel=2e-5)
    mesh = DiffusionMesh.planar(1., 5, area_m2=3.)
    run = DiffusionDomain(H2, mesh, lambda t: 1.).simulate(
        [0, .1], 1-mesh.cell_centers_m, boundary=faces(), temperature_k=lambda t: 300.)
    assert run.left_integrated_mol[-1] == pytest.approx(.3)
    assert not mesh.cell_volumes_m3.flags.writeable
    for inner, outer, cells in ((0., 1., 5), (1., .5, 5), (1., 2., True)):
        with pytest.raises(ValueError):
            DiffusionMesh.spherical_shell(inner, outer, cells)
