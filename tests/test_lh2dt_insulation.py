"""Boundary/ledger contract tests with authored native-interface doubles.

Actual native heat equations and tank integration are exercised separately by
scripts/check_insulation_integration.py, using the pinned optional package.
"""

from dataclasses import replace
from types import SimpleNamespace

import pytest

from h2physics.adapters.lh2dt_insulation import (
    InsulationClosureError,
    InsulationEvidence,
    Lh2dtVacuumInsulation,
    WallHeatAllocation,
    layered_inventory_reader,
)
from h2physics.core import Origin, PropertyBasis
from h2physics.dynamics import InventoryBalance, InventoryTolerances


def evidence(**changes):
    result = InsulationEvidence("authored-drawing", "authored-construction-closures", "helium",
        "authored-absolute-annulus-pressure", ("authored-test",), Origin.SYNTHETIC)
    return replace(result, **changes)


class NativeDouble:
    def __init__(self):
        self.parameters = SimpleNamespace(area_m2=2., maximum_valid_vacuum_pressure_Pa=.1,
                                           localized_heat_paths=(SimpleNamespace(path_id="neck"),))
        self.result = SimpleNamespace(total_heat_into_cold_W=10., radiation_heat_W=2.,
            mli_solid_heat_W=3., support_heat_W=1., residual_gas_heat_W=0.,
            localized_heat_W=4., vacuum_pressure_Pa=.01)
        self.zone_result = (2., 8.)
        self.calls = []

    def evaluate(self, warm, cold, pressure):
        self.calls.append((warm, cold, pressure))
        return self.result

    def layered_wall_heat_distribution(self, warm, cold, pressure, **kwargs):
        self.calls.append((warm, cold, pressure, kwargs))
        return self.zone_result


def allocation(**changes):
    result = WallHeatAllocation(("lower", "upper"), (.4, .6), {"neck": (0., 1.)},
                                "authored-surface-and-penetration-map")
    return replace(result, **changes)


def test_actual_native_object_signed_boundary_and_provenance_are_retained():
    raw = NativeDouble()
    bridge = Lh2dtVacuumInsulation(raw, evidence=evidence())
    result = bridge.evaluate(280., 30., .01)
    assert result.native is raw.result and bridge.native is raw
    assert result.power.heat_w == 10. and result.power.shaft_work_w == 0.
    assert result.heat_residual_w == 0. and dict(result.path_heat_w)["localized"] == 4.
    assert result.evidence.origin == Origin.SYNTHETIC and bridge.area_m2 == 2.
    for field in ("total_heat_into_cold_W", "radiation_heat_W", "mli_solid_heat_W",
                  "support_heat_W", "localized_heat_W"):
        setattr(raw.result, field, -getattr(raw.result, field))
    reversed_heat = bridge.evaluate(20., 30., .01)
    assert reversed_heat.power.heat_w == -10.


@pytest.mark.parametrize("fault", ["sum", "sign", "zero", "pressure", "nonfinite"])
def test_failed_native_heat_retains_original_result_without_an_accepted_power(fault):
    raw = NativeDouble()
    bridge = Lh2dtVacuumInsulation(raw, evidence=evidence())
    warm, cold = 280., 30.
    if fault == "sum":
        raw.result.total_heat_into_cold_W = 11.
    elif fault == "sign":
        raw.result.radiation_heat_W = -2.
        raw.result.total_heat_into_cold_W = 6.
    elif fault == "zero":
        warm = cold
    elif fault == "pressure":
        raw.result.vacuum_pressure_Pa = .02
    else:
        raw.result.total_heat_into_cold_W = float("nan")
    with pytest.raises(InsulationClosureError) as error:
        bridge.evaluate(warm, cold, .01)
    assert error.value.native is raw.result


def test_absolute_vacuum_domain_and_parameter_change_are_explicit_gates():
    raw = NativeDouble()
    bridge = Lh2dtVacuumInsulation(raw, evidence=evidence())
    for pressure in (-.001, .1001, float("nan")):
        with pytest.raises(ValueError):
            bridge.evaluate(280., 30., pressure)
    for warm, cold in ((0., 30.), (280., -1.), (True, 30.)):
        with pytest.raises(ValueError):
            bridge.evaluate(warm, cold, .01)
    assert not raw.calls
    raw.parameters = SimpleNamespace(area_m2=3.)
    with pytest.raises(ValueError, match="changed"):
        bridge.evaluate(280., 30., .01)


@pytest.mark.parametrize("changes", [{"pressure_basis": "gauge"}, {"geometry_id": ""},
    {"source_ids": ()}, {"residual_gas_id": ""}, {"closure_id": ""}])
def test_missing_or_inconsistent_parameter_evidence_is_rejected(changes):
    with pytest.raises(ValueError):
        evidence(**changes)


def test_zone_and_localized_path_allocations_remain_distinct_and_immutable():
    raw = NativeDouble()
    bridge = Lh2dtVacuumInsulation(raw, evidence=evidence())
    mapping = {"neck": [0., 1.]}
    allocated = allocation(localized_path_fractions=mapping)
    mapping["neck"][0] = .5
    result = bridge.partition(280., (25., 35.), .01, allocation=allocated)
    assert result.native is raw.zone_result and result.zone_heat_w == (2., 8.)
    assert result.power.heat_w == 10.
    assert raw.calls[-1][3]["area_fractions"] == (.4, .6)
    assert raw.calls[-1][3]["localized_path_fractions"]["neck"] == (0., 1.)
    with pytest.raises(TypeError):
        allocated.localized_path_fractions["neck"] = (.5, .5)
    with pytest.raises(ValueError, match="every native localized"):
        bridge.partition(280., (25., 35.), .01, allocation=allocation(localized_path_fractions={}))


@pytest.mark.parametrize("changes", [{"zone_ids": ("wall", "wall")},
    {"area_fractions": (.3, .3)}, {"area_fractions": (-.1, 1.1)},
    {"localized_path_fractions": {"neck": (.1, .1)}}, {"evidence_id": ""}])
def test_invalid_geometry_is_not_normalized_or_inferred(changes):
    with pytest.raises(ValueError):
        allocation(**changes)


def test_native_partition_fault_is_retained():
    raw = NativeDouble()
    bridge = Lh2dtVacuumInsulation(raw, evidence=evidence())
    raw.zone_result = (-2., 8.)
    with pytest.raises(InsulationClosureError) as error:
        bridge.partition(280., (25., 35.), .01, allocation=allocation())
    assert error.value.native is raw.zone_result


def test_state_dependent_wall_boundary_receives_actual_thermo_and_absolute_clock():
    raw = NativeDouble()
    bridge = Lh2dtVacuumInsulation(raw, evidence=evidence())
    thermo = SimpleNamespace(wall_temperatures_K=(25., 35.))
    calls, observations = [], []

    def warm(time, state):
        calls.append((time, state))
        return 270. + time

    callback = bridge.layered_wall_callback(allocation(), warm_temperature_k=warm,
        vacuum_pressure_pa_abs=lambda time, state: .01 * state.wall_temperatures_K[0] / 25.,
        clock_id="authored-absolute-operation", start_time_s=10.,
        observer=lambda time, result: observations.append((time, result)))
    assert callback(.25, thermo) == (2., 8.)
    assert calls == [(10.25, thermo)] and raw.calls[-1][:3] == (280.25, (25., 35.), .01)
    assert observations[0][0] == 10.25 and observations[0][1].power.heat_w == 10.
    with pytest.raises(ValueError, match="clock"):
        bridge.layered_wall_callback(allocation(), warm_temperature_k=280.,
                                     vacuum_pressure_pa_abs=.01, clock_id="")


def test_independent_layered_inventory_and_signed_existing_heat_ledger():
    basis = PropertyBasis("ParaHydrogen", "authored-property-reference", "para")
    read = layered_inventory_reader(rigid_volume_m3=.01, wall_heat_capacities_j_k=(2., 3.), basis=basis)
    initial_state = SimpleNamespace(liquid_masses_kg=(1.,), vapor_masses_kg=(.1,),
        liquid_specific_enthalpies_J_kg=(1000.,), vapor_specific_enthalpies_J_kg=(3000.,),
        pressure_Pa=100_000., wall_temperatures_K=(20., 30.))
    initial = read(initial_state)
    assert initial.fluid_internal_energy_j == 300.
    assert initial.solid_internal_energy_j == 130. and initial.mass_kg == 1.1
    final = read(SimpleNamespace(**(vars(initial_state) | {"wall_temperatures_K": (19., 29.)})))
    balance = InventoryBalance(initial, final, 0., -5., 0., -5.)
    assert balance.mass_residual_kg == balance.energy_residual_j == 0.
    assert not balance.violations(InventoryTolerances())
    with pytest.raises(ValueError, match="capacities"):
        read(SimpleNamespace(**(vars(initial_state) | {"wall_temperatures_K": (20.,)})))
