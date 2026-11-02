"""Deferred finite relief-lift cases; discovery performs no model calculation."""

from dataclasses import replace

from h2physics.cluster_validation import ValidationCase, ValidationOutcome

LIMITS = (
    "Component/native integration contracts; no independent device validation.",
    "Accepted-sample linear travel, not hidden-crossing localization or disk mechanics.",
    "Caller phase selection and coefficients require independent evidence.",
)


def _failure_prefix_fixture_factory():
    """Build an actual pinned native tank whose later step rejects its boundary."""
    from pathlib import Path

    import lh2dt
    from lh2dt.properties import ThermoState as NativeState
    from lh2dt.streams import MassEnergyFlow
    from lh2dt.tank import HomogeneousTank, TankGeometry, TankState
    from lh2dt.valve import PressureReliefValve, Valve, ValveResult

    from h2physics.adapters.lh2dt import Lh2dtProperties
    from h2physics.adapters.lh2dt_properties import Lh2dtLowLevelProperties
    from h2physics.adapters.lh2dt_relief import (
        Lh2dtReliefTankDriver,
        ReliefTankBoundary,
        shared_native_relief,
    )
    from h2physics.release import HomogeneousIsentropicNozzle, NozzleOpening
    from h2physics.thermo import CoolPropProperties
    from scripts.check_relief_integration import NATIVE_SOURCE_SHA256, REVISION, native_hash

    if native_hash(Path(lh2dt.__file__).resolve().parent) != NATIVE_SOURCE_SHA256:
        raise ValueError("Failure-prefix fixture requires the reviewed pinned LH2DT source")

    start = 5.0
    step = 0.005
    duration = 0.015
    fail_after = start + step + 1e-12
    properties = CoolPropProperties("Hydrogen")
    facade = Lh2dtLowLevelProperties(properties, state_factory=NativeState)
    bridge = Lh2dtProperties(facade, reference_id=properties.basis.reference_id)
    opening = NozzleOpening("authored-relief-prefix-opening", 1e-6, 1.0,
                            "synthetic-failure-prefix-area")
    protection = shared_native_relief(
        native_valve_type=Valve,
        native_relief_factory=PressureReliefValve,
        result_factory=ValveResult,
        nozzle=HomogeneousIsentropicNozzle(properties),
        bridge=bridge,
        opening=opening,
        set_pressure_pa_absolute=2e5,
        reseat_pressure_pa_absolute=1.8e5,
        native_source_id="LH2DT:" + REVISION,
    )
    tank = HomogeneousTank(TankGeometry(0.01, 100.0, 1.0, 10.0), facade)
    initial_thermo = facade.from_pT(1.9e5, 300.0)
    initial_mass = initial_thermo.density_kg_m3 * tank.geometry.volume_m3
    initial = TankState(
        initial_mass,
        initial_mass * initial_thermo.specific_internal_energy_J_kg,
        300.0,
    )

    def ambient_temperature(absolute_time_s):
        # The first 5 ms are valid and accepted. The native tank's own
        # derivative rejects this invalid second-interval boundary value.
        return 0.0 if absolute_time_s > fail_after else 300.0

    boundary = ReliefTankBoundary(
        "authored-relief-failure-prefix-clock",
        start,
        start + duration,
        properties.state_pt(1e5, 300.0),
        ambient_temperature,
        lambda _time_s, _state, _wall_temperature_k: 0.0,
        "authored-invalid-second-interval-ambient",
    )
    driver = Lh2dtReliefTankDriver(
        tank, protection, flow_factory=MassEnergyFlow, state_factory=NativeState,
    )
    return driver, {
        "initial": initial,
        "duration_s": duration,
        "maximum_step_s": step,
        "start_time_s": start,
        "clock_id": boundary.clock_id,
        "boundary": boundary,
        "minimum_inventory_kg": initial_mass * 0.01,
    }


def cases():
    definitions = (
        ("relief-lift-travel", "validate_travel", ("native set/reseat identity", "bounded opening/closing travel")),
        ("relief-lift-leakage", "validate_leakage", ("declared seat leakage", "shared-nozzle effective area")),
        ("relief-lift-phase", "validate_phase", ("explicit phase owner", "wrong phase/basis/native state reject")),
        ("relief-lift-inventory", "validate_inventory", ("finite selectable phase mass", "no clipping or fallback")),
        ("relief-lift-clock", "validate_clock", ("accepted monotone clock", "maximum step and sampled crossing limits")),
        ("relief-lift-binding", "validate_binding", ("original owner-issued result", "native/law/opening mutation reject")),
        ("relief-lift-failure-prefix", "validate_failure_prefix", (
            "native tank rejects an invalid later boundary after a valid interval and retains the accepted prefix",
            "failed candidate is not represented as accepted output",
            "native state, protection owner, trial count and original cause remain available",
        )),
        ("relief-withdrawal-accepted-edge-ledger", "validate_withdrawal_ledger", (
            "adjacent owner-issued endpoints and explicit phase/clock identity",
            "linear-endpoint mass and signed enthalpy quadrature",
            "finite phase inventory closes with caller-declared other transfer",
        )),
        ("relief-withdrawal-finite-source-handoff", "validate_finite_source_handoff", (
            "inventory-closing relief withdrawals retain exact interval masses and clock",
            "representative state requires same basis/phase and closes cumulative enthalpy",
            "source receipt rejects stale native owner or changed ledger")),
        ("relief-withdrawal-invalid-edge-rejection", "validate_withdrawal_rejection", (
            "phase switch, relief set/reseat transition, nonadjacent clock or stock mismatch rejects",
            "no silent clipping or synthetic owner result is admitted",
        )),
    )
    return tuple(ValidationCase(identifier=name, profile="finite-relief-lift",
        entrypoint=__name__ + ":" + entry,
        parameters=({"failure_fixture_factory": _failure_prefix_fixture_factory}
                    if name == "relief-lift-failure-prefix" else {}),
        invariants=invariants)
        for name, entry, invariants in definitions)


def _fixture(**parameters):
    """Use injected owners or the package's reviewed-native authored fixture."""
    factory = parameters.get("fixture_factory")
    if factory is not None:
        if not callable(factory):
            raise TypeError("fixture_factory must be callable when supplied")
        return factory()
    from examples.finite_relief_lift import build_native_fixture

    return build_native_fixture()


def _accepted_withdrawal_fixture():
    """Build adjacent native endpoints with an explicit synthetic phase balance."""
    owner, points, downstream = _fixture()
    first = owner.initialize(time_s=0., clock_id="withdrawal-ledger-clock",
        native_tank_state=points[0], downstream=downstream)
    left = owner.advance(first, time_s=.05, native_tank_state=points[1],
        downstream=downstream)
    right = owner.advance(left, time_s=.10, native_tank_state=points[2],
        downstream=downstream)
    dt = right.state.time_s - left.state.time_s
    expected_mass = .5 * (left.mass_flow_kg_s + right.mass_flow_kg_s) * dt
    expected_energy = .5 * (left.enthalpy_flow_w + right.enthalpy_flow_w) * dt
    return owner, left, right, expected_mass, expected_mass, expected_energy


def _nonadjacent_withdrawal_fixture():
    """Build same-phase native results separated by one accepted sample."""
    owner, points, downstream = _fixture()
    first = owner.initialize(time_s=0., clock_id="withdrawal-rejection-clock",
        native_tank_state=points[0], downstream=downstream)
    left = owner.advance(first, time_s=.05, native_tank_state=points[1],
        downstream=downstream)
    middle = owner.advance(left, time_s=.10, native_tank_state=points[2],
        downstream=downstream)
    right = owner.advance(middle, time_s=.15, native_tank_state=points[1],
        downstream=downstream)
    return owner, left, right, 0.0


def validate_travel(*, work_directory, **parameters):
    model, points, downstream = _fixture(**parameters)
    first = model.initialize(time_s=0., clock_id="relief-lift-clock",
        native_tank_state=points[0], downstream=downstream)
    opened = model.advance(first, time_s=.05, native_tank_state=points[1], downstream=downstream)
    held = model.advance(opened, time_s=.10, native_tank_state=points[2], downstream=downstream)
    closed = model.advance(held, time_s=.15, native_tank_state=points[3], downstream=downstream)
    assert opened.state.demanded_open and opened.state.lift_fraction > first.state.lift_fraction
    assert held.state.demanded_open and closed.state.lift_fraction < held.state.lift_fraction
    return ValidationOutcome(True, {"peak_lift": held.state.lift_fraction}, LIMITS)


def validate_leakage(*, work_directory, **parameters):
    model, points, downstream = _fixture(**parameters)
    value = model.initialize(time_s=0., clock_id="relief-lift-clock",
        native_tank_state=points[0], downstream=downstream)
    assert value.state.lift_fraction == 0
    assert value.effective_opening_fraction == model.law.closed_leakage_fraction
    assert value.nozzle.effective_area_m2 == model.opening.effective_area_m2(
        model.law.closed_leakage_fraction)
    return ValidationOutcome(True, {"leakage_fraction": value.effective_opening_fraction}, LIMITS)


def validate_phase(*, work_directory, **parameters):
    model, points, downstream = _fixture(**parameters)
    value = model.initialize(time_s=0., clock_id="relief-lift-clock",
        native_tank_state=points[0], downstream=downstream)
    assert value.pickup.phase_id in model.pickup.admitted_phase_ids
    assert value.pickup.native_tank_state is points[0]
    altered = parameters.get("wrong_phase_state", object())
    try:
        model.initialize(time_s=0., clock_id="relief-lift-clock",
            native_tank_state=altered, downstream=downstream)
    except (TypeError, ValueError):
        wrong_native_state_rejected = True
    else:
        raise AssertionError("Unadmitted pickup phase/native state was accepted")
    return ValidationOutcome(True, {
        "phase_id": value.pickup.phase_id,
        "wrong_native_state_rejected": wrong_native_state_rejected,
    }, LIMITS)


def validate_inventory(*, work_directory, **parameters):
    del work_directory
    factory = parameters.get("depleted_fixture_factory")
    if factory is None:
        from examples.finite_relief_lift import build_native_fixture

        model, points, downstream = build_native_fixture(vapor_mass_kg=0.0)
        depleted = points[1]
    else:
        if not callable(factory):
            raise TypeError("depleted_fixture_factory must be callable when supplied")
        model, points, downstream, depleted = factory()
    first = model.initialize(time_s=0., clock_id="relief-lift-clock",
        native_tank_state=points[0], downstream=downstream)
    try:
        model.advance(first, time_s=.05, native_tank_state=depleted, downstream=downstream)
    except ValueError as exc:
        assert "inventory" in str(exc)
    else:
        raise AssertionError("Finite selectable phase inventory was silently clipped")
    return ValidationOutcome(True, {"rejected": 1}, LIMITS)


def validate_clock(*, work_directory, **parameters):
    model, points, downstream = _fixture(**parameters)
    first = model.initialize(time_s=0., clock_id="relief-lift-clock",
        native_tank_state=points[0], downstream=downstream)
    for bad in (0., model.law.maximum_clock_step_s * 1.01):
        try:
            model.advance(first, time_s=bad, native_tank_state=points[1], downstream=downstream)
        except ValueError:
            pass
        else:
            raise AssertionError("Unsupported accepted clock step was accepted")
    return ValidationOutcome(True, {"maximum_step_s": model.law.maximum_clock_step_s}, LIMITS)


def validate_binding(*, work_directory, **parameters):
    model, points, downstream = _fixture(**parameters)
    first = model.initialize(time_s=0., clock_id="relief-lift-clock",
        native_tank_state=points[0], downstream=downstream)
    model.require_current(first)
    copied = replace(first)
    try:
        model.require_current(copied)
    except ValueError:
        pass
    else:
        raise AssertionError("Copied relief-lift result was accepted as owner-issued")
    return ValidationOutcome(True, {"native_owner_retained": first.native_relief_origin is model.protection.native_origin}, LIMITS)


def validate_failure_prefix(*, work_directory, **parameters):
    """Exercise an injected post-acceptance native failure without fabricating a trace."""
    del work_directory
    factory = parameters.get("failure_fixture_factory")
    if not callable(factory):
        raise ValueError("failure-prefix case requires failure_fixture_factory")
    driver, run_arguments = factory()
    from h2physics.adapters.lh2dt_relief import ReliefIntegrationError

    try:
        driver.run(**run_arguments)
    except ReliefIntegrationError as error:
        assert error.native_tank is driver.native
        assert error.protection is driver.protection
        assert error.cause is error.__cause__
        assert len(error.accepted_intervals) == 1
        assert isinstance(error.cause, ValueError)
        cause_text = str(error.cause).lower().replace("_", " ")
        assert all(term in cause_text for term in ("ambient", "temperature", "positive"))
        assert len(error.output_times) == len(error.accepted_intervals) + 1
        assert error.output_times[-1] == error.accepted_time_s
        assert error.accepted_time_s == run_arguments["start_time_s"] + run_arguments["maximum_step_s"]
        assert error.accepted_intervals[-1].native_step.state is error.accepted_state
        assert error.trial_count >= len(error.accepted_intervals)
        assert len(error.mass_residuals) == len(error.output_times)
        assert len(error.energy_residuals) == len(error.output_times)
        assert len(error.released_mass_history) == len(error.output_times)
        assert len(error.released_energy_history) == len(error.output_times)
        assert len(error.external_heat_history) == len(error.output_times)
        return ValidationOutcome(True, {
            "accepted_intervals_before_failure": len(error.accepted_intervals),
            "native_trials": error.trial_count,
            "accepted_time_s": error.accepted_time_s,
            "original_cause_type": type(error.cause).__name__,
        }, LIMITS)
    raise AssertionError("Failure fixture completed without the declared native relief failure")


def validate_withdrawal_ledger(*, work_directory, **parameters):
    del work_directory
    del parameters
    from h2physics.adapters.relief_withdrawal_ledger import integrate_relief_withdrawal_edge

    owner, left, right, other_change, expected_mass, expected_energy = (
        _accepted_withdrawal_fixture())
    receipt = integrate_relief_withdrawal_edge(owner, left, right,
        other_phase_inventory_change_kg=other_change,
        evidence_id="independent-fixture-ledger")
    assert abs(receipt.mass_withdrawn_kg - expected_mass) <= max(1e-12, 1e-10 * abs(expected_mass))
    assert abs(receipt.enthalpy_withdrawn_j - expected_energy) <= max(1e-9, 1e-10 * abs(expected_energy))
    assert abs(receipt.mass_balance_residual_kg) <= 1e-10
    return ValidationOutcome(True, {
        "withdrawn_mass_kg": receipt.mass_withdrawn_kg,
        "withdrawn_enthalpy_j": receipt.enthalpy_withdrawn_j,
        "balance_residual_kg": receipt.mass_balance_residual_kg,
    }, LIMITS + ("Accepted-edge linear trapezoid is not native solver quadrature.",))


def validate_withdrawal_rejection(*, work_directory, **parameters):
    del work_directory
    del parameters
    from h2physics.adapters.relief_withdrawal_ledger import integrate_relief_withdrawal_edge

    owner, left, right, other_change = _nonadjacent_withdrawal_fixture()
    try:
        integrate_relief_withdrawal_edge(owner, left, right,
            other_phase_inventory_change_kg=other_change,
            evidence_id="independent-rejection-fixture")
    except (TypeError, ValueError):
        return ValidationOutcome(True, {"rejected_invalid_edge": 1}, LIMITS)
    raise AssertionError("Invalid relief-withdrawal edge or inventory balance was accepted")


def validate_finite_source_handoff(*, work_directory, **parameters):
    """Deferred bridge contract; execution belongs to the pinned Hangang run."""
    from h2physics.adapters.relief_finite_source import relief_source_from_accepted_withdrawals
    from h2physics.adapters.relief_withdrawal_ledger import integrate_relief_withdrawal_edge
    from h2physics.core import Origin
    from h2physics.release import SourceLocation

    owner, left, right, other_change, expected_mass, expected_energy = _accepted_withdrawal_fixture()
    receipt = integrate_relief_withdrawal_edge(
        owner, left, right,
        other_phase_inventory_change_kg=other_change,
        evidence_id="authored-finite-relief-source-inventory-closure",
    )
    # This authored fixture has no net non-relief phase addition. Preserve the
    # caller's explicit source boundary and thermodynamic state projection.
    location = SourceLocation(
        "authored-finite-relief-source", left.state.clock_id,
        "facility-local-xyz", (0.0, 0.0, 1.0), (0.0, 0.0, 1.0),
    )
    handoff = relief_source_from_accepted_withdrawals(
        owner, (left, right), (receipt,), location=location,
        representative_state=left.downstream, origin=Origin.SYNTHETIC,
        projection_evidence_id="authored-same-downstream-state-energy-basis",
        enthalpy_tolerance_j=max(1e-3, abs(expected_energy) * 1e-10),
    )
    handoff.require_current()
    assert handoff.source.mass_kg[0] == expected_mass
    assert abs(handoff.enthalpy_residual_j) <= handoff.enthalpy_tolerance_j
    return ValidationOutcome(True, {
        "source_mass_kg": handoff.source.total_mass_kg,
        "relief_energy_residual_j": handoff.enthalpy_residual_j,
    }, LIMITS)
