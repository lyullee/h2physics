"""Original finite-inventory/analytic checks, not biological calibration data."""

from __future__ import annotations

import os
import subprocess
import sys
from importlib.util import find_spec
from math import exp
from pathlib import Path

import numpy as np
import pytest

from h2physics.adapters.biological import (
    Adm1Geometry,
    BiologicalAudit,
    BiologicalAuditError,
    BiologicalEvidence,
    QsdSanNative,
)
from scripts.check_biological import make_case


@pytest.fixture(scope="module")
def native():
    if find_spec("qsdsan") is None:
        pytest.skip("separately installed reviewed native biological engine is optional")
    return QsdSanNative.from_installed()


@pytest.fixture(scope="module")
def reactive(native):
    digester = make_case(native)
    result = digester.run(start_time_s=864000., end_time_s=872640., sample_count=12801,
                          max_step_s=300)
    return digester, result


@pytest.mark.parametrize("temperature", [25, 279, 331, float("nan")])
def test_warm_liquid_phase_boundary_is_explicit(temperature):
    with pytest.raises(ValueError):
        Adm1Geometry(.01, .005, 1e-9, 101325, temperature)


def test_signed_or_nonfinite_geometry_is_not_clipped():
    with pytest.raises(ValueError):
        Adm1Geometry(.01, .005, -1e-9, 101325, 308.15)
    with pytest.raises(ValueError):
        BiologicalAudit(0, 1e-8, 5e5)


def test_missing_source_and_clock_support_are_not_inferred():
    with pytest.raises(ValueError):
        BiologicalEvidence("", "p", "i", "f", "T", "b", "clock", 0, 1)
    with pytest.raises(ValueError):
        BiologicalEvidence("s", "p", "i", "f", "T", "b", "clock", 1, 1)


def test_actual_native_finite_objects_and_exact_initial_state(reactive):
    digester, run = reactive
    assert run.native_system is digester.native_system
    assert run.native_reactor is digester.native_reactor
    assert run.native_model is digester.native_model
    assert run.native_components is digester.native_components
    assert run.native_solution is run.native_system.scope.sol
    np.testing.assert_array_equal(run.native_solution.y[:, 0], run.native_initial_state)
    assert len(run.native_solution.t) < len(run.points)
    assert run.native_solution.t[0] == 10.0
    assert run.native_solution.t[-1] == 10.1
    assert run.points[0].time_s == 864000
    assert not run.native_reactor.algebraic_h2
    assert not run.native_reactor.fixed_headspace_P
    assert run.points[0].headspace_hydrogen_kg == pytest.approx(.005 * 1e-6 * .00201588)
    assert run.native_reactor.state["S_su"] == pytest.approx(run.points[-1].native_state[0])
    assert run.energy_balance_available is False
    assert run.native_threshold_zeroing_kg_m3_or_kmol_m3 == 1e-16


def test_actual_hydrogen_generation_consumption_and_biomass_balance(reactive):
    digester, run = reactive
    assert run.points[-1].native_state[0] < .9
    biomass = digester._ids.index("X_su")
    assert run.points[-1].native_state[biomass] > run.points[0].native_state[biomass]
    balance = run.balance
    assert balance.hydrogen_formed_kg > balance.hydrogen_consumed_kg > 0
    assert balance.exported_hydrogen_kg > 0
    assert balance.exported_dry_hydrogen_mole_fraction < .01
    assert balance.hydrogen_residual_kg < 1e-10
    h2 = "S_h2"
    actual_mass_factor = digester.native_components.S_h2.i_mass
    delta_h2 = (run.points[-1].liquid_hydrogen_kg + run.points[-1].headspace_hydrogen_kg
                - run.points[0].liquid_hydrogen_kg - run.points[0].headspace_hydrogen_kg)
    expected = ((balance.inlet_measured_kg[h2] - balance.liquid_outlet_measured_kg[h2])
                * actual_mass_factor + balance.hydrogen_formed_kg - balance.hydrogen_consumed_kg
                - balance.exported_hydrogen_kg)
    assert abs(delta_h2 - expected) < 1e-10


def test_independent_cod_carbon_nitrogen_native_stoichiometric_nullspaces(reactive):
    digester, run = reactive
    for name, weights in (("COD", digester.native_components.i_COD),
                          ("C", digester.native_components.i_C),
                          ("N", digester.native_components.i_N)):
        assert np.max(np.abs(digester._matrix[:-3] @ weights)) < 1e-12
        assert run.balance.invariant_residuals_kg[name] < 5e-9
    assert max(run.balance.component_residuals_kg.values()) < 5e-9


def test_inert_limit_matches_independent_analytic_cstr(native):
    digester = make_case(native, zero_rates=True, gas_pipe=0)
    run = digester.run(start_time_s=864000, end_time_s=907200, sample_count=129,
                       max_step_s=900, rtol=1e-12, atol=1e-14)
    decay = exp(-digester.feed_volume_flow_m3_s * 43200 / .01)
    assert run.points[-1].native_state[0] == pytest.approx(.5 + .5 * decay, abs=1e-10)
    index = digester._ids.index("X_su")
    assert run.points[-1].native_state[index] == pytest.approx(.1 * decay, abs=1e-10)
    for point in run.points:
        assert point.headspace_hydrogen_kg == run.points[0].headspace_hydrogen_kg
        assert point.gas_outflow_m3_s == 0
    assert run.balance.hydrogen_formed_kg == 0
    assert run.balance.hydrogen_consumed_kg == 0
    assert run.balance.exported_dry_hydrogen_mole_fraction is None


def test_closed_reactive_total_inventories_are_finite(native):
    digester = make_case(native, gas_pipe=0, feed_flow=0)
    # Native solver completes but native zero-flow stream finalization rejects.
    # A conserved diagnostic trajectory is not an accepted closed-process run.
    with pytest.raises(BiologicalAuditError, match="empty") as failure:
        digester.run(start_time_s=864000, end_time_s=872640, sample_count=12801,
                      max_step_s=300)
    error = failure.value
    assert error.native_solution.success
    assert error.native_state == tuple(error.native_solution.y[:, -1])
    assert error.clock_kind == "native-finalization"
    assert error.time_s == 872640
    assert not error.audited_points
    first = np.array(list(digester._point(864000, error.native_solution.y[:, 0]).measured_inventories_kg.values()))
    last = np.array(list(digester._point(872640, error.native_solution.y[:, -1]).measured_inventories_kg.values()))
    for weights in (digester.native_components.i_COD,
                    digester.native_components.i_C, digester.native_components.i_N):
        assert abs((last - first) @ weights) < 1e-10
    assert digester.native_reactor._q_gas == 0


def test_native_one_way_pressure_law_blocks_reverse_flow(native):
    digester = make_case(native, zero_rates=True, external_pressure=200000)
    run = digester.run(start_time_s=864000, end_time_s=872640, sample_count=65)
    assert all(p.pressure_pa < 200000 and p.gas_outflow_m3_s == 0 for p in run.points)
    assert run.balance.exported_hydrogen_kg == 0


def test_coarse_ledger_rejected_and_full_native_solution_retained(native):
    digester = make_case(native)
    with pytest.raises(BiologicalAuditError, match="COD boundary") as failure:
        digester.run(start_time_s=864000, end_time_s=872640, sample_count=1601,
                      max_step_s=300)
    error = failure.value
    assert error.native_solution.success
    assert error.native_solution is digester.native_system.scope.sol
    assert error.native_system is digester.native_system
    assert len(error.audited_points) == 1601
    assert error.native_state == error.audited_points[-1].native_state
    assert error.time_s == 872640
    assert error.clock_kind == "dense-output-sample"
    assert isinstance(error.__cause__, ValueError)


def test_native_pressure_domain_failure_retains_failing_accepted_state(native):
    digester = make_case(native, max_pressure=103000)
    with pytest.raises(BiologicalAuditError, match="pressure") as failure:
        digester.run(start_time_s=864000, end_time_s=872640, sample_count=65)
    error = failure.value
    assert error.native_solution.success
    assert error.native_state == tuple(error.native_solution.y[:, 0])
    assert error.time_s == 864000
    assert error.clock_kind == "native-accepted"
    assert not error.audited_points


def test_clock_support_is_not_extrapolated(native):
    digester = make_case(native)
    with pytest.raises(ValueError, match="support"):
        digester.run(start_time_s=0, end_time_s=1, sample_count=3)
    with pytest.raises(ValueError, match="sample_count"):
        digester.run(start_time_s=864000, end_time_s=872640, sample_count=True)


def test_published_aliased_solver_revision_is_not_silently_accepted():
    root = Path(__file__).resolve().parents[1]
    dependency_target = root / "artifacts/native_biological_packages"
    if not dependency_target.exists():
        pytest.skip("local rejected PyPI baseline is not installed")
    env = dict(os.environ, PYTHONPATH=str(dependency_target))
    result = subprocess.run([sys.executable, "-X", "utf8", "-c",
                             "from h2physics.adapters.biological import QsdSanNative; "
                             "QsdSanNative.from_installed()"], env=env,
                            capture_output=True, text=True, encoding="utf-8", timeout=30)
    assert result.returncode != 0
    assert "aliased y0" in result.stderr


def test_actual_native_nonfinite_rate_cannot_pass_ledger_gate(reactive):
    digester, run = reactive
    constants = digester.native_model.rate_function._params["rate_constants"]
    saved = constants.copy()
    selected = (run.points[0], run.points[len(run.points)//2], run.points[-1])
    times = np.array([p.time_s for p in selected])
    states = np.array([p.native_state for p in selected])
    try:
        constants[0] = np.nan
        native_rates = digester.native_model.rate_function(np.r_[states[0], 308.15])
        assert not np.all(np.isfinite(native_rates))
        with pytest.raises(ValueError, match="nonfinite"):
            digester._balance(times, states, list(selected))
    finally:
        constants[:] = saved


def test_secondary_native_restoration_fault_preserves_primary_audit_cause(native, monkeypatch):
    # Deliberate API failure injection; this test makes no physical acceptance claim.
    digester = make_case(native)
    primary = ValueError("injected independent audit fault")
    secondary = RuntimeError("injected native endpoint cache fault")

    def fail_restore(*args):
        raise secondary

    def fail_audit(*args):
        monkeypatch.setattr(digester.native_reactor, "f_q_gas_var_P_headspace", fail_restore)
        raise primary

    monkeypatch.setattr(digester, "_balance", fail_audit)
    with pytest.raises(BiologicalAuditError) as failure:
        digester.run(start_time_s=864000, end_time_s=864086.4, sample_count=3,
                      max_step_s=30)
    error = failure.value
    assert error.__cause__ is primary
    assert error.restoration_error is secondary
    assert error.native_solution.success
    assert len(error.audited_points) == 3
    assert error.native_state == error.audited_points[-1].native_state
