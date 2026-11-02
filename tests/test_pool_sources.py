from dataclasses import dataclass
from types import SimpleNamespace

import numpy as np
import pytest

from h2physics.adapters.pool import (
    DeclaredGroundInflow,
    NativeDynamicPool,
    PoolCouplingError,
    PoolTolerances,
)
from h2physics.core import Origin, PropertyBasis, ThermoState
from h2physics.release import SourceLocation
from h2physics.sources import IntervalMassSource

BASIS = PropertyBasis("Hydrogen", "authored-test-reference", "normal")
GROUND = SourceLocation("ground", "authored-clock", "authored-frame", (0., 0., 0.), (0., 0., 1.))
VAPOR = SourceLocation("vapor", "authored-clock", "authored-frame", (0., 0., 0.), (0., 0., 1.))


class AuthoredProperties:
    basis = BASIS

    def saturated(self, pressure, quality):
        density, enthalpy = (80., 10.) if quality == 0. else (4., 110.)
        return ThermoState(self.basis, pressure, 20., density, enthalpy,
            enthalpy-pressure/density, 0., "two_phase", vapor_mass_fraction=quality)


@dataclass
class AuthoredInflow:
    times_s: tuple = (0., .37)
    rates_kg_s: tuple = (.02, 0.)

    def rate_at(self, time):
        return self.rates_kg_s[0] if time < self.times_s[1] else self.rates_kg_s[1]


def ground():
    return DeclaredGroundInflow(AuthoredInflow(), GROUND, AuthoredProperties().saturated(1e5, 0.),
        100., 100.6, Origin.SYNTHETIC, "authored-ground-boundary", "isolation")


def authored_runner(config, inflow, *, output_times_s):
    # Authored contract snapshots; this fixture does not solve pool physics.
    rows = []
    for time in output_times_s:
        supplied, evaporated = .02*min(time, .37), .01*time
        rows.append(SimpleNamespace(time_s=time, cumulative_inflow_kg=supplied,
            liquid_mass_kg=supplied-evaporated, cumulative_evaporation_kg=evaporated,
            escaped_domain_mass_kg=0., cumulative_numerical_mass_adjustment_kg=0.,
            unledgered_mass_residual_kg=0., pool_temperature_K=20., liquid_density_kg_m3=80.,
            interval_mean_evaporation_rate_kg_s=.01 if time else 0.,
            last_substep_evaporation_rate_kg_s=.013 if time else 0.,
            reported_radius_m=0., wet_area_m2=.1 if time else 0., source_status="within_declared_scope"))
    return SimpleNamespace(ledger=tuple(rows), mass_balance_residual_kg=0.)


CONFIG = SimpleNamespace(ambient_pressure_Pa=1e5, initial_liquid_mass_kg=0.)
EDGES = (100., 100.2, 100.37, 100.6)


def test_mass_intervals_conserve_nonuniform_bins_and_reject_clock_or_window_invention():
    source = IntervalMassSource(VAPOR, [100., 101., 103.], [.2, .8],
        AuthoredProperties().saturated(1e5, 1.), Origin.SYNTHETIC, "authored", "window_end")
    assert source.mass_between(100.5, 102., clock_id=VAPOR.clock_id) == pytest.approx(.5)
    rebinned = source.rebin([100., 100.5, 102., 103.], clock_id=VAPOR.clock_id)
    assert rebinned.total_mass_kg == pytest.approx(source.total_mass_kg)
    np.testing.assert_allclose(rebinned.mass_kg, [.1, .5, .4])
    assert not source.mean_rates_kg_s.flags.writeable and not source.mass_kg.flags.writeable
    assert source.enthalpy_transfer_j == pytest.approx(110.)
    with pytest.raises(ValueError, match="clock"):
        source.mass_between(100., 101., clock_id="other")
    with pytest.raises(ValueError, match="extrapolate"):
        source.mass_between(99., 101., clock_id=VAPOR.clock_id)
    with pytest.raises(ValueError, match="full ordered"):
        source.rebin([100., 102.], clock_id=VAPOR.clock_id)


def test_actual_native_objects_and_cumulative_evaporation_survive_zero_reported_footprint():
    bridge = NativeDynamicPool(authored_runner, AuthoredProperties(), engine_id="authored-engine")
    flow = ground()
    run = bridge.run(CONFIG, flow, output_times_s=EDGES, vapor_location=VAPOR)
    assert run.config is CONFIG and run.inflow.native is flow.native
    assert run.samples[1].native is run.native.ledger[1]
    assert run.admissible and not run.validation_qualified
    assert run.samples[-1].native.reported_radius_m == 0.
    assert run.samples[-1].native.liquid_mass_kg > 0.
    source = run.evaporation_source()
    assert source.total_mass_kg == pytest.approx(.006)
    assert source.mass_between(100.37, 100.6, clock_id=VAPOR.clock_id) == pytest.approx(.0023)
    assert flow.cumulative_mass_kg(100.6, clock_id=GROUND.clock_id) == pytest.approx(.0074)
    assert source.origin == Origin.PREDICTED
    with pytest.raises(ValueError, match="Stopping liquid"):
        run.evaporation_source(end_reason="isolation")
    with pytest.raises(ValueError, match="zero remaining"):
        run.evaporation_source(end_reason="depleted")


@pytest.mark.parametrize("corruption,match", [
    ("mass", "inventory does not close"), ("mean", "interval-mean"),
    ("adjustment", "adjustment exceeds"), ("escape", "escaped"),
    ("property", "property mismatch"), ("nan", "nonfinite"),
])
def test_bad_native_claims_fail_and_preserve_diagnostics(corruption, match):
    def corrupted_runner(*args, **kwargs):
        result = authored_runner(*args, **kwargs)
        row = result.ledger[-1]
        if corruption == "mass":
            row.liquid_mass_kg += .001  # Native reported residual deliberately stays zero.
        elif corruption == "mean":
            row.interval_mean_evaporation_rate_kg_s += .001
        elif corruption == "adjustment":
            row.liquid_mass_kg += .001
            row.cumulative_numerical_mass_adjustment_kg = .001
        elif corruption == "escape":
            row.escaped_domain_mass_kg = .001
            row.liquid_mass_kg -= .001
            row.source_status = "out_of_scope"
        elif corruption == "property":
            row.pool_temperature_K = 21.
        else:
            result.mass_balance_residual_kg = float("nan")
        return result

    bridge = NativeDynamicPool(corrupted_runner, AuthoredProperties(), engine_id="authored")
    with pytest.raises(PoolCouplingError, match=match) as error:
        bridge.run(CONFIG, ground(), output_times_s=EDGES, vapor_location=VAPOR)
    assert error.value.native.ledger and error.value.issues
    if corruption != "nan":
        diagnostic = bridge.run(CONFIG, ground(), output_times_s=EDGES,
                                vapor_location=VAPOR, require_closed=False)
        assert not diagnostic.admissible
        with pytest.raises(PoolCouplingError):
            diagnostic.evaporation_source()


def test_native_fluid_and_reference_are_explicit_and_schedules_cannot_mutate():
    wrong_properties = AuthoredProperties()
    wrong_properties.basis = PropertyBasis("ParaHydrogen", "authored-test-reference", "para")
    with pytest.raises(ValueError, match="normal Hydrogen only"):
        NativeDynamicPool(authored_runner, wrong_properties, engine_id="authored")
    flow = ground()
    flow.native.rates_kg_s = (.03, 0.)
    bridge = NativeDynamicPool(authored_runner, AuthoredProperties(), engine_id="authored")
    with pytest.raises(ValueError, match="schedule changed"):
        bridge.run(CONFIG, flow, output_times_s=EDGES, vapor_location=VAPOR)
    with pytest.raises(ValueError, match="entire ordered"):
        bridge.run(CONFIG, ground(), output_times_s=(100., 100.2), vapor_location=VAPOR)
    with pytest.raises(ValueError, match="finite window"):
        ground().cumulative_mass_kg(101., clock_id=GROUND.clock_id)
    with pytest.raises(ValueError, match="budgets"):
        PoolTolerances(maximum_numerical_adjustment_kg=-1.)


def test_explicit_event_clock_budget_delegates_at_known_knots_and_records_every_change():
    flow = ground()
    near_knot = .37-1e-13
    assert flow.native.rate_at(near_knot) == .02

    def near_knot_runner(config, inflow, *, output_times_s):
        assert inflow.native is flow.native
        assert inflow.rate_at(near_knot) == 0.
        return authored_runner(config, inflow, output_times_s=output_times_s)

    bridge = NativeDynamicPool(near_knot_runner, AuthoredProperties(), engine_id="authored",
                               tolerances=PoolTolerances(event_clock_roundoff_s=1e-10))
    run = bridge.run(CONFIG, flow, output_times_s=EDGES, vapor_location=VAPOR)
    assert run.maximum_input_clock_correction_s == pytest.approx(.37-near_knot)
    assert run.input_clock.corrections_s == [(near_knot, .37)]
    ambiguous = NativeDynamicPool(authored_runner, AuthoredProperties(), engine_id="authored",
                                  tolerances=PoolTolerances(event_clock_roundoff_s=.2))
    with pytest.raises(ValueError, match="unresolved"):
        ambiguous.run(CONFIG, ground(), output_times_s=EDGES, vapor_location=VAPOR)
