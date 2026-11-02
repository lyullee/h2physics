"""Actual native inverse heat against independent direct-EOS forward cases."""

import importlib
import sys
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

from h2physics.adapters.pifira_heat import (
    AxialContactGeometry,
    ClosedHeatDomain,
    ClosedHeatEvidence,
    EffectiveAreaEvidence,
    PifiraClosedVesselHeat,
    contents_equivalent_heat_flux,
    pifira_effective_area,
)
from h2physics.core import Origin, TimeSeries
from h2physics.thermo import CoolPropProperties


def native_api():
    pytest.importorskip("CoolProp")
    target = Path(__file__).resolve().parents[1]/"artifacts/native_fire_packages"
    if target.is_dir() and str(target) not in sys.path:
        sys.path.insert(0, str(target))
    return pytest.importorskip("pifira")


def model(fluid="ParaHydrogen"):
    native = native_api()
    tank = native.TankSpec(volume=.04, fluid="HEOS::"+fluid, fill=.35)
    evidence = ClosedHeatEvidence("authored-heat", "sealed-case", "rigid-case",
        "equilibrium-case", "contents-U-only; wall/work separate", Origin.SYNTHETIC)
    return PifiraClosedVesselHeat(native, tank, CoolPropProperties(fluid), evidence=evidence,
        domain=ClosedHeatDomain(1e5, 8e5))


def pressure(values=(1.5e5, 2e5, 2.5e5), **changes):
    options = dict(time_s=np.array([100., 110., 120.]), values=np.array(values)[:, None],
        channels=("P",), units=("Pa",), valid=np.ones((3, 1), bool), clock_id="heat-clock",
        origin=Origin.SYNTHETIC, source_id="authored-heat", quantities=("pressure",),
        basis_ids=("absolute",))
    options.update(changes)
    return TimeSeries(**options)


def run(m=None, history=None):
    m = model() if m is None else m
    return m.run(pressure() if history is None else history, "P",
        mass_kg=m.derive_initial_mass(1.5e5), mass_evidence_id="native-declared-fill-mass")


def area_evidence(**changes):
    e = EffectiveAreaEvidence("authored-heat", "heat-clock", 100., 110., "centre-geometry",
        "authored-local-Gaussian", "authored-wetted-height", "fourth-power-equivalent", Origin.SYNTHETIC)
    return replace(e, **changes)


def area(*, theta=None, temperature=None, evidence=None, **changes):
    native = native_api()
    theta = np.array([-120., -60., 0., 60., 120.]) if theta is None else np.asarray(theta)
    temperature = ((295.**4+8e10*np.exp(-.5*(theta/32.)**2))**.25
                   if temperature is None else temperature)
    options = dict(angles_deg=theta, wall_temperature_k=temperature,
        ambient_temperature_k=295., diameter_m=.4,
        axial_geometry=AxialContactGeometry(0., .6, 0., .5, "authored-common-axis"),
        evidence=area_evidence() if evidence is None else evidence,
        maximum_normalized_fit_error=1e-5)
    options.update(changes)
    return pifira_effective_area(native, **options)


@pytest.mark.parametrize("fluid", ["Hydrogen", "ParaHydrogen", "OrthoHydrogen"])
def test_actual_native_contents_energy_agrees_with_independent_direct_heos_flash(fluid):
    trace = run(model(fluid))
    assert trace.native_module is importlib.import_module("pifira")
    assert trace.native_tank.fluid == "HEOS::"+fluid
    assert np.max(abs(trace.native_minus_eos_energy_j)) < 1e-6
    assert np.max(abs(trace.interval_energy_residual_j)) < 1e-8
    assert not trace.native_energy_j.flags.writeable
    assert not trace.interval_heat_w.flags.writeable
    assert trace.native_gauge_zero_pa == 101325.


def test_independent_constant_power_forward_eos_is_inverted_without_fitting_pressure():
    m = model()
    mass = m.derive_initial_mass(1.5e5)
    density = mass/m.tank.volume
    initial = m.properties.state_prho(1.5e5, density)
    t = np.linspace(100., 120., 11)
    prescribed_power = 1300.
    states = [m.properties.state_rho_u(density,
        initial.internal_energy_j_kg+prescribed_power*(v-t[0])/mass) for v in t]
    history = pressure([s.pressure_pa for s in states], time_s=t, valid=np.ones((11, 1), bool))
    trace = m.run(history, "P", mass_kg=mass, mass_evidence_id="fixed-initial-fill")
    assert trace.interval_heat_w == pytest.approx(np.full(10, prescribed_power), abs=1e-5)
    assert trace.native_energy_j[-1]-trace.native_energy_j[0] == pytest.approx(26000., abs=1e-4)


def test_signed_cooling_and_zero_heat_remain_contents_energy_rates():
    m = model()
    cooling = run(m, pressure([2.5e5, 2e5, 1.5e5]))
    assert np.all(cooling.interval_heat_w < 0.)
    stationary = run(m, pressure([1.5e5]*3))
    assert np.all(stationary.interval_heat_w == 0.)


def test_single_phase_overwithdrawn_inventory_is_rejected_before_native_lever_extrapolation():
    m = model()
    with pytest.raises(ValueError, match="two-phase"):
        m.run(pressure(), "P", mass_kg=.02, mass_evidence_id="invalid-small-mass")


@pytest.mark.parametrize("changes", [dict(units=("bar",)), dict(basis_ids=("reported-gauge",)),
    dict(basis_ids=()), dict(quantities=("reported_pressure",)),
    dict(valid=np.array([[True], [False], [True]])), dict(origin=Origin.UNRESOLVED),
    dict(source_id="another-experiment")])
def test_pressure_quantity_basis_masks_and_source_are_not_repaired(changes):
    with pytest.raises(ValueError):
        run(history=pressure(**changes))


def test_native_definition_and_energy_corruption_cannot_pass(monkeypatch):
    m = model()
    m.tank.fill = .4
    with pytest.raises(ValueError, match="definition changed"):
        run(m)
    m = model()
    original = m.native.internal_energy
    monkeypatch.setattr(m.native, "internal_energy", lambda p, mass, tank: original(p, mass, tank)+100.)
    with pytest.raises(ValueError, match="energy or reference"):
        run(m)


def test_native_heat_interval_corruption_cannot_pass(monkeypatch):
    m = model()
    original = m.native.heat_input
    monkeypatch.setattr(m.native, "heat_input", lambda *a, **kw: original(*a, **kw)*1.01)
    with pytest.raises(ValueError, match="intervals"):
        run(m)


def test_independent_gaussian_area_and_native_kw_to_w_equivalent_flux():
    a = area()
    assert a.native_fit["sigma"] == pytest.approx(32., abs=1e-9)
    expected = np.pi*.4*(np.sqrt(2*np.pi)*32/360)*.5
    assert a.area_m2 == pytest.approx(expected, abs=1e-12)
    assert a.normalized_fit_error < 1e-12
    assert not a.wall_temperature_k.flags.writeable
    t = run()
    flux = contents_equivalent_heat_flux(t, 0, a, allocation_evidence_id="authored-no-wall-or-work")
    assert flux.flux_w_m2 == pytest.approx(t.interval_heat_w[0]/expected)
    assert flux.heat_trace is t and flux.area is a
    assert flux.allocation_evidence_id == "authored-no-wall-or-work"


def test_cooling_equivalent_flux_is_signed():
    t = run(history=pressure([2.5e5, 2e5, 1.5e5]))
    assert contents_equivalent_heat_flux(t, 0, area(), allocation_evidence_id="cooling-reference").flux_w_m2 < 0


def test_offset_axial_intervals_use_their_actual_overlap_and_retain_geometry():
    g = AxialContactGeometry(.3, .9, 0., .5, "common-tank-z")
    a = area(axial_geometry=g)
    assert a.height_m == pytest.approx(.2)
    assert a.area_m2 == pytest.approx(area().area_m2*.4)
    assert a.axial_geometry is g and a.ambient_temperature_k == 295.


def test_disjoint_axial_contact_is_zero_area_without_a_flux_floor():
    a = area(axial_geometry=AxialContactGeometry(.8, 1.4, 0., .5, "common-tank-z"))
    assert a.height_m == 0. and a.area_m2 == 0.
    with pytest.raises(ValueError, match="zero axial overlap"):
        contents_equivalent_heat_flux(run(), 0, a, allocation_evidence_id="disjoint-shape")


@pytest.mark.parametrize("changes", [dict(clock_id="other-clock"), dict(source_id="other-source"),
    dict(start_s=101.), dict(end_s=111.)])
def test_area_heat_pairing_requires_identical_source_clock_and_interval(changes):
    with pytest.raises(ValueError, match="identities"):
        contents_equivalent_heat_flux(run(), 0, area(evidence=area_evidence(**changes)),
            allocation_evidence_id="explicit-allocation")


def test_gaussian_area_rejects_missing_tails_and_miscentred_or_broad_shape():
    with pytest.raises(ValueError, match="tail coverage"):
        area(theta=[-20., -10., 0., 10., 20.])
    with pytest.raises(ValueError):
        area(temperature=np.full(5, 500.))
    theta = np.array([-120., -60., 0., 60., 120.])
    wrong = (295.**4+8e10*np.exp(-.5*((theta-25)/32.)**2))**.25
    with pytest.raises(ValueError, match="residual"):
        area(temperature=wrong)


def test_angular_fit_does_not_assign_unresolved_temperature_statistics():
    with pytest.raises(ValueError, match="mean temperatures"):
        area_evidence(temperature_statistic="arithmetic-mean")
    with pytest.raises(ValueError, match="positive radiation"):
        area(temperature=np.array([290., 320., 500., 320., 300.]))
