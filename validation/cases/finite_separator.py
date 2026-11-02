"""Deferred pure-fluid native phase-selective separator operation."""

from h2physics.cluster_validation import ValidationCase, ValidationOutcome


def cases():
    return (ValidationCase(
        identifier="finite-pure-fluid-separator-selective-ports", profile="finite-transfer",
        entrypoint=__name__ + ":validate_separator",
        invariants=("original native stratified phase inventories and selective withdrawal",
                    "pure-fluid property basis and independent total stored-energy audit",
                    "admitted HEOS provider and low-level state identity stay current",
                    "only the completed native operation can issue a separator trace",
                    "phase inventory floors and caller phase domain gates",
                    "callback code and captured schedules stay fixed through the run",
                    "native exception retains evaluated trials without inventing accepted prefix"),
    ),)


def build_problem():
    from lh2dt.geometry import HorizontalVesselGeometry
    from lh2dt.properties import ThermoState
    from lh2dt.stratified_tank import StratifiedTank, StratifiedTankParameters

    from h2physics.adapters.lh2dt import Lh2dtProperties
    from h2physics.adapters.lh2dt_properties import Lh2dtLowLevelProperties
    from h2physics.thermo import CoolPropProperties

    eos = CoolPropProperties("ParaHydrogen", quality_roundoff_tolerance=1e-8)
    properties = Lh2dtLowLevelProperties(eos, state_factory=ThermoState)
    bridge = Lh2dtProperties(properties, reference_id=eos.basis.reference_id)
    parameters = StratifiedTankParameters(1000., 1000., 0., 0., 0., 0., 0., 0., 0., .15,
                                          minimum_pressure_Pa=10000., maximum_pressure_Pa=1250000.)
    tank = StratifiedTank(HorizontalVesselGeometry(.3, .3, .05), parameters, properties)
    return tank, tank.initialize_saturated(3e5, .5), bridge


def validate_separator(*, work_directory, **parameters):
    del work_directory, parameters
    from math import isclose

    from lh2dt.streams import MassEnergyFlow

    from h2physics.adapters.finite_separator import (
        FiniteSeparatorError,
        run_finite_pure_fluid_separator,
    )

    tank, initial, bridge = build_problem()

    def phase_domain(state):
        assert 10. < state.temperature_k < 100.
        assert 1e4 <= state.pressure_pa <= 1.25e6

    def flows(time, thermo):
        assert 5. <= time <= 5.1+1e-10
        return ((), (MassEnergyFlow(-1e-6, thermo.vapor.specific_enthalpy_J_kg),))

    kwargs = dict(bridge=bridge, material_species_id="H2:para", duration_s=.1,
        maximum_step_s=.01, start_time_s=5., clock_id="authored-separator-clock",
        phase_flows=flows, ambient_temperature_k=30.,
        phase_assignment_evidence_id="authored-native-vapor-port-only",
        phase_domains={"liquid": phase_domain, "vapor": phase_domain},
        mass_tolerance_kg=1e-10, energy_tolerance_j=1e-4,
        minimum_liquid_inventory_kg=1e-10, minimum_vapor_inventory_kg=1e-10)
    import numpy as np

    for rejected in (False, np.bool_(False)):
        try:
            run_finite_pure_fluid_separator(tank, initial, **(kwargs | {
                "phase_domains": {"liquid": lambda state: rejected, "vapor": phase_domain},
            }))
        except FiniteSeparatorError as error:
            assert isinstance(error.cause, ValueError)
        else:
            raise AssertionError("False scalar phase-domain decision was ignored")
    trace = run_finite_pure_fluid_separator(tank, initial, **kwargs)
    assert trace.require_current() is trace
    from dataclasses import replace
    from h2physics.adapters.finite_separator import FiniteSeparatorTrace
    try:
        replace(trace)
    except ValueError:
        pass
    else:
        raise AssertionError("A cloned separator trace reused its consumed native issuer")
    try:
        FiniteSeparatorTrace(
            trace.native_owner, trace.initial_state, trace.clock_id,
            trace.phase_assignment_evidence_id, trace.points, trace.native_rows,
            trace.boundary_evaluations, trace.material_species_id,
            trace.native_provenance, trace.source_guard,
        )
    except ValueError:
        pass
    else:
        raise AssertionError("Direct separator trace construction was accepted")
    assert trace.points[-1].native_step is trace.native_rows[-1]
    assert isclose(trace.points[-1].total_mass_kg-trace.points[0].total_mass_kg,
                   -1e-7, abs_tol=1e-10)
    assert all(abs(point.energy_residual_j) < 1e-4 for point in trace.points)
    mutable_schedule = {"scale": 1.0}

    def mutate_schedule(time, thermo):
        if time > 5.0:
            mutable_schedule["scale"] = 2.0
        return ((), (MassEnergyFlow(-1e-6*mutable_schedule["scale"],
                                    thermo.vapor.specific_enthalpy_J_kg),))

    try:
        run_finite_pure_fluid_separator(tank, initial, **(kwargs | {"phase_flows": mutate_schedule}))
    except FiniteSeparatorError as error:
        assert isinstance(error.cause, ValueError)
        assert "callbacks" in str(error.cause)
    else:
        raise AssertionError("A mutating captured phase-flow schedule changed during an accepted run")
    cause = RuntimeError("authored-phase-port-failure")

    def fail(time, thermo):
        if time > 5.03:
            raise cause
        return flows(time, thermo)

    try:
        run_finite_pure_fluid_separator(tank, initial, **(kwargs | {"phase_flows": fail}))
    except FiniteSeparatorError as error:
        assert error.cause is cause
        assert error.boundary_evaluations
        assert not error.accepted_prefix_available
    else:
        raise AssertionError("Original native phase-flow failure was discarded")

    # Replacing the provider's low-level state after adapter admission must not
    # let the cached fluid/basis identity describe a different EOS state object.
    eos = bridge.native.provider
    eos._state = object()
    try:
        bridge.native.from_pT(3e5, 30.)
    except ValueError:
        pass
    else:
        raise AssertionError("Native property facade accepted a replaced provider state")
    return ValidationOutcome(True, {"native_points": len(trace.points)},
                             ("Pure-fluid phase-selective native vessel; no finite mixture separator claim",))
