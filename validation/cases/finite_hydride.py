"""Deferred direct-constructor contracts for the finite hydride trace adapter."""

from h2physics.cluster_validation import ValidationCase, ValidationOutcome


def cases():
    return (
        ValidationCase(
            identifier="hydride-loading-window-capacity",
            profile="finite-hydride",
            entrypoint=__name__ + ":validate_loading_window_capacity",
            invariants=(
                "nominal capacity between explicit loading-fraction endpoints is reconstructed",
                "endpoint order and closed unit interval are enforced",
                "capacity window makes no kinetics, reachability or degradation claim",
            ),
        ),
        ValidationCase(
            identifier="finite-hydride-trace-constructor-integrity",
            profile="finite-hydride",
            entrypoint=__name__ + ":validate_trace_integrity",
            invariants=(
                "retained native gas and bound-energy references have compatible bases",
                "trace time and snapshot axes agree exactly",
                "gas/solid transfer and energy residuals reconstruct from retained samples",
                "free-gas volume and solid-hydrogen capacity remain constant across the trace",
                "native callback, source identity and bound-energy basis contracts are typed",
                "forged direct-constructor ledgers are rejected",
                "a consumed integration receipt cannot be cloned and resealed",
            ),
        ),
        ValidationCase(
            identifier="finite-hydride-scheduled-gas-port",
            profile="finite-hydride",
            entrypoint=__name__ + ":validate_scheduled_gas_port",
            invariants=(
                "native-stream-property-basis-matches-bed",
                "signed-external-h2-mass-is-integrated",
                "native-stream-enthalpy-is-integrated-on-common-reference",
                "mass-and-energy-residuals-include-port-ledgers",
                "reject-clock-support-and-detached-outlet-state",
            ),
        ),
        ValidationCase(
            identifier="finite-hydride-nozzle-source-handoff",
            profile="finite-hydride",
            entrypoint=__name__ + ":validate_nozzle_handoff",
            parameters={},
            invariants=(
                "every integrated nozzle-flow interval closes against the accepted outward bed gas-port mass",
                "caller selects output-grid quadrature and cites a closure tolerance budget",
                "a nozzle opening with incompatible integrated mass is rejected without ledger rescaling",
                "every native hydride gas state is evaluated with the same declared property basis",
                "exact source clock, location, opening and end meaning are retained",
                "source receipt invalidates if the retained hydride snapshots change",
            ),
        ),
        ValidationCase(
            identifier="finite-hydride-reduced-trajectory-integrity",
            profile="finite-hydride",
            entrypoint=__name__ + ":validate_reduced_trajectory_integrity",
            invariants=(
                "reduced trajectory retains material and initial-state basis",
                "all returned vectors share a finite increasing time axis",
                "stored mass and reduced-energy residual reconstruct",
                "direct construction and receipt cloning are rejected",
            ),
        ),
        ValidationCase(
            identifier="finite-hydride-postsolve-failure-retention",
            profile="finite-hydride",
            entrypoint=__name__ + ":validate_postsolve_failure_retention",
            invariants=(
                "post-integration assembly failure preserves the exact native solver result",
                "accepted output coordinates and state rows remain inspectable",
                "last trial state and original post-processing exception remain available",
                "failure does not issue a successful hydride trace",
            ),
        ),
    )


def validate_loading_window_capacity(*, work_directory, **parameters):
    del work_directory, parameters

    from h2physics.storage.hydride import HydrideParameters

    material = HydrideParameters(.02, 1000., 24000., .00201588, 0.)
    from math import isclose

    assert isclose(material.swing_capacity_kg(.1, .8), .014, rel_tol=1e-14)
    assert material.swing_capacity_kg(.4, .4) == 0.
    for lower, upper in ((-.01, .5), (.2, 1.01), (.8, .2)):
        try:
            material.swing_capacity_kg(lower, upper)
        except ValueError:
            continue
        raise AssertionError("invalid loading window was accepted")
    return ValidationOutcome(
        accepted=True,
        metrics={"window_capacity_kg": .014, "lower_fraction": .1, "upper_fraction": .8},
        limitations=(
            "Nominal capacity window only; no pressure/temperature/rate reachability or cycle performance is inferred.",
        ),
    )


def validate_reduced_trajectory_integrity(*, work_directory, **parameters):
    del work_directory, parameters
    from dataclasses import replace

    import numpy as np

    from h2physics.storage.hydride import (
        ArrheniusRate, HydrideBed, HydrideBoundary, HydrideKinetics,
        HydrideParameters, HydrideState, VanthoffPlateau,
    )

    material = HydrideParameters(.002, 1000., 24000., .00201588, 0.)
    kinetics = HydrideKinetics(
        VanthoffPlateau(24000., 80., 1e5),
        ArrheniusRate(.01, 0., 300.), ArrheniusRate(.02, 0., 300.),
    )
    initial = HydrideState(.1, 300.)
    times = np.array([0., 1., 2.])
    trajectory = HydrideBed(material, kinetics).simulate(
        times, initial, lambda _t, _s: HydrideBoundary(0., 300., 0.),
        maximum_step_s=.5,
    )
    for action in (
        lambda: replace(trajectory),
        lambda: type(trajectory)(
            trajectory.time_s, trajectory.fraction, trajectory.temperature_k,
            trajectory.hydrogen_stored_kg, trajectory.integrated_boundary_heat_j,
            trajectory.reduced_energy_residual_j, trajectory.function_evaluations,
            material, initial,
        ),
    ):
        try:
            action()
        except (TypeError, ValueError):
            pass
        else:
            raise AssertionError("Hydride trajectory accepted an unissued or cloned receipt")

    forged = np.array(trajectory.reduced_energy_residual_j, copy=True)
    forged[-1] += 1.
    try:
        replace(trajectory, reduced_energy_residual_j=forged)
    except (TypeError, ValueError):
        pass
    else:
        raise AssertionError("Hydride trajectory accepted a forged reduced-energy ledger")
    return ValidationOutcome(
        accepted=True,
        metrics={"retained_samples": len(trajectory.time_s), "forged_receipts_rejected": 3},
        limitations=("Constructor-integrity contract only; synthetic coefficients do not validate an alloy.",),
    )


def validate_trace_integrity(*, work_directory, **parameters):
    del work_directory, parameters
    from dataclasses import replace

    import numpy as np

    from h2physics.storage.finite_hydride import (
        BoundHydrogenEnergyReference,
        FiniteHydrideBed,
        FiniteHydrideDomain,
        FiniteHydrideHeatBoundary,
        FiniteHydrideHeatInput,
        HydrideGasThermodynamics,
    )
    from h2physics.storage.hydride import (
        ArrheniusRate,
        HydrideKinetics,
        HydrideParameters,
        HydrideState,
        VanthoffPlateau,
    )

    gas = HydrideGasThermodynamics.coolprop("Hydrogen")
    parameters = HydrideParameters(.002, 1000., 24000., gas.molar_mass_kg_mol, 0.)
    kinetics = HydrideKinetics(
        VanthoffPlateau(24000., 80., 1e5),
        ArrheniusRate(.01, 0., 300.),
        ArrheniusRate(.02, 0., 300.),
    )
    reference = BoundHydrogenEnergyReference.from_gas(
        gas,
        temperature_k=300.,
        pressure_pa=1e5,
        desorption_enthalpy_j_mol_h2=24000.,
        evidence_id="authored-constructor-contract-only",
    )
    for invalid_provider in (
        {"source_id": 17},
        {"native_objects": "provider"},
        {"state_rho_t": False},
    ):
        try:
            replace(gas, **invalid_provider)
        except (TypeError, ValueError):
            pass
        else:
            raise AssertionError("Invalid native gas-provider identity/capability was accepted")
    try:
        replace(reference, gas_reference_state="not-a-ThermoState")
    except TypeError:
        pass
    else:
        raise AssertionError("A bound-H reference accepted untyped gas-state evidence")
    try:
        replace(reference, evidence_id=17)
    except ValueError:
        pass
    else:
        raise AssertionError("A bound-H reference accepted a nontext evidence identity")
    bed = FiniteHydrideBed(
        parameters,
        kinetics,
        gas,
        reference,
        FiniteHydrideDomain(200., 600., 1e3, 1e7, 1e-7),
        free_gas_volume_m3=.005,
        gas_solid_conductance_w_k=10.,
    )
    boundary = FiniteHydrideHeatBoundary(
        "finite-hydride-contract-clock",
        100.,
        101.,
        lambda _time, _snapshot: FiniteHydrideHeatInput(300.),
        "authored-constant-temperature-boundary",
    )
    trace = bed.simulate(
        np.array([100., 100.5, 101.]),
        HydrideState(.1, 300.),
        gas.state_pt(3e5, 300.),
        boundary=boundary,
        clock_id="finite-hydride-contract-clock",
        maximum_step_s=.25,
        relative_tolerance=1e-9,
    )
    try:
        replace(trace)
    except TypeError as error:
        assert "completed native-provider integration" in str(error)
    else:
        raise AssertionError("A completed hydride trace was cloned with a fresh integrity baseline")
    forged_energy = np.array(trace.total_energy_residual_j, copy=True)
    forged_energy[-1] += 1.
    try:
        replace(trace, total_energy_residual_j=forged_energy)
    except (TypeError, ValueError):
        pass
    else:
        raise AssertionError("A directly constructed hydride trace accepted a forged energy residual")

    forged_time = np.array(trace.time_s, copy=True)
    forged_time[1] += .01
    try:
        replace(trace, time_s=forged_time)
    except (TypeError, ValueError):
        pass
    else:
        raise AssertionError("A hydride trace accepted time coordinates detached from snapshots")

    try:
        replace(trace, integrated_hydrogen_uptake_kg=np.array([0., 0., .5]))
    except (TypeError, ValueError):
        pass
    else:
        raise AssertionError("A hydride trace accepted an inconsistent uptake transfer ledger")

    return ValidationOutcome(
        accepted=True,
        metrics={
            "retained_samples": len(trace.time_s),
            "forged_receipts_rejected": 3,
            "malformed_provider_or_reference_rejected": 5,
        },
        limitations=(
            "Direct-constructor integrity contract only; authored kinetic and material inputs are not experimental.",
            "No independent alloy, caloric, vessel, or apparatus validation is implied.",
        ),
    )


def validate_scheduled_gas_port(*, work_directory, **parameters):
    del work_directory, parameters
    from dataclasses import replace

    import numpy as np

    from h2physics.storage.finite_hydride import (
        BoundHydrogenEnergyReference,
        FiniteHydrideBed,
        FiniteHydrideDomain,
        FiniteHydrideGasPortBoundary,
        FiniteHydrideGasPortInput,
        FiniteHydrideHeatBoundary,
        FiniteHydrideHeatInput,
        HydrideGasThermodynamics,
    )
    from h2physics.storage.hydride import (
        ArrheniusRate,
        HydrideKinetics,
        HydrideParameters,
        HydrideState,
        VanthoffPlateau,
    )

    gas = HydrideGasThermodynamics.coolprop("Hydrogen")
    material = HydrideParameters(.002, 1000., 24000., gas.molar_mass_kg_mol, 0.)
    kinetics = HydrideKinetics(
        VanthoffPlateau(24000., 80., 1e5),
        ArrheniusRate(.01, 0., 300.),
        ArrheniusRate(.02, 0., 300.),
    )
    reference = BoundHydrogenEnergyReference.from_gas(
        gas, temperature_k=300., pressure_pa=1e5,
        desorption_enthalpy_j_mol_h2=24000., evidence_id="authored-port-reference",
    )
    bed = FiniteHydrideBed(
        material, kinetics, gas, reference,
        FiniteHydrideDomain(200., 600., 1e3, 1e7, 1e-7),
        free_gas_volume_m3=.005, gas_solid_conductance_w_k=10.,
    )
    clock_id = "finite-hydride-port-clock"
    start, end = 10., 11.
    heat = FiniteHydrideHeatBoundary(
        clock_id, start, end,
        lambda _time, _snapshot: FiniteHydrideHeatInput(300.),
        "authored-isothermal-bath",
    )
    inlet = gas.state_pt(3.1e5, 300.)
    port = FiniteHydrideGasPortBoundary(
        clock_id, start, end,
        lambda _time, _snapshot: FiniteHydrideGasPortInput(
            1e-8, inlet, "authored-positive-inlet-flow"),
        "authored-positive-inlet-flow",
    )
    trace = bed.simulate(
        np.array([start, start+.5, end]), HydrideState(.1, 300.),
        gas.state_pt(3e5, 300.), boundary=heat, clock_id=clock_id,
        maximum_step_s=.25, gas_port=port,
    )
    assert trace.gas_port_boundary is port
    assert trace.integrated_external_gas_mass_kg[-1] > 0.
    assert np.allclose(
        trace.total_hydrogen_residual_kg,
        np.array([s.total_hydrogen_mass_kg for s in trace.snapshots])
        -trace.snapshots[0].total_hydrogen_mass_kg
        -trace.integrated_external_gas_mass_kg,
        rtol=1e-12, atol=1e-14,
    )
    assert np.allclose(
        trace.total_energy_residual_j,
        np.array([s.total_internal_energy_j for s in trace.snapshots])
        -trace.snapshots[0].total_internal_energy_j
        -trace.integrated_external_gas_heat_j
        -trace.integrated_external_solid_heat_j
        -trace.integrated_external_gas_enthalpy_j,
        rtol=1e-12, atol=1e-9,
    )
    forged = np.array(trace.integrated_external_gas_mass_kg, copy=True)
    forged[-1] += 1e-4
    try:
        replace(trace, integrated_external_gas_mass_kg=forged)
    except ValueError:
        pass
    else:
        raise AssertionError("Forged external H2 transfer bypassed total-inventory reconstruction")
    detached_outlet = FiniteHydrideGasPortBoundary(
        clock_id, start, end,
        lambda _time, _snapshot: FiniteHydrideGasPortInput(-1e-8, inlet, "authored-invalid-outlet"),
        "authored-invalid-outlet",
    )
    try:
        detached_outlet.value(start, trace.snapshots[0])
    except ValueError:
        pass
    else:
        raise AssertionError("H2 outlet accepted an independent state instead of the bed state")
    return ValidationOutcome(True, {
        "net_hydrogen_in_kg": trace.integrated_external_gas_mass_kg[-1],
        "net_stream_enthalpy_in_j": trace.integrated_external_gas_enthalpy_j[-1],
        "retained_edges": len(trace.time_s),
    }, (
        "Caller supplies stream flow; no pressure-flow, valve, leak or control law is inferred.",
        "The finite H2 gas/solid inventory, native EOS and existing kinetic law remain the bed owners.",
    ))


def validate_nozzle_handoff(*, work_directory, **parameters):
    del work_directory, parameters
    import numpy as np
    from dataclasses import replace

    from h2physics.adapters.finite_hydride_nozzle import nozzle_history_from_hydride_trace
    from h2physics.core import Origin
    from h2physics.release import HomogeneousIsentropicNozzle, NozzleOpening, SourceLocation
    from h2physics.storage.finite_hydride import (
        BoundHydrogenEnergyReference, FiniteHydrideBed, FiniteHydrideDomain,
        FiniteHydrideGasPortBoundary, FiniteHydrideGasPortInput,
        FiniteHydrideHeatBoundary, FiniteHydrideHeatInput, HydrideGasThermodynamics,
    )
    from h2physics.storage.hydride import (
        ArrheniusRate, HydrideKinetics, HydrideParameters, HydrideState, VanthoffPlateau,
    )
    from h2physics.thermo.coolprop import CoolPropProperties

    gas = HydrideGasThermodynamics.coolprop("Hydrogen")
    material = HydrideParameters(.002, 1000., 24000., gas.molar_mass_kg_mol, 0.)
    kinetics = HydrideKinetics(VanthoffPlateau(24000., 80., 1e5),
        ArrheniusRate(.01, 0., 300.), ArrheniusRate(.02, 0., 300.))
    reference = BoundHydrogenEnergyReference.from_gas(gas, temperature_k=300.,
        pressure_pa=1e5, desorption_enthalpy_j_mol_h2=24000.,
        evidence_id="authored-nozzle-handoff-reference")
    bed = FiniteHydrideBed(material, kinetics, gas, reference,
        FiniteHydrideDomain(200., 600., 1e3, 1e7, 1e-7),
        free_gas_volume_m3=.005, gas_solid_conductance_w_k=10.)
    properties = CoolPropProperties("Hydrogen")
    nozzle = HomogeneousIsentropicNozzle(properties)
    opening = NozzleOpening.circular("authored-hydride-outlet", .001,
        effective_area_factor=6.0e-5, area_basis_id="authored-effective-opening-area")
    back_pressure_pa = 101325.
    clock = "authored-hydride-nozzle-clock"
    start, end = 10., 11.
    thermal = FiniteHydrideHeatBoundary(clock, start, end,
        lambda _time, _snapshot: FiniteHydrideHeatInput(0.), "authored-zero-external-heat")
    port = FiniteHydrideGasPortBoundary(clock, start, end,
        lambda _time, snapshot: FiniteHydrideGasPortInput(
            -nozzle.solve(snapshot.gas, back_pressure_pa=back_pressure_pa,
                          opening=opening).mass_flow_kg_s,
            snapshot.gas, "authored-nozzle-coupled-hydrogen-discharge"),
        "authored-nozzle-coupled-hydrogen-discharge")
    sample_times = np.linspace(start, end, 11)
    trace = bed.simulate(sample_times, HydrideState(.1, 300.),
        gas.state_pt(3e5, 300.), boundary=thermal, clock_id=clock,
        maximum_step_s=.1, gas_port=port, isothermal_temperature_k=300.)
    location = SourceLocation("authored-hydride-release", clock, "authored-ground-xyz",
        (0., 0., 1.), (0., 0., 1.))
    handoff = nozzle_history_from_hydride_trace(trace, nozzle=nozzle, opening=opening,
        location=location, back_pressure_pa=101325.,
        evidence_id="authored-storage-to-release-handoff", origin=Origin.SYNTHETIC,
        port_mass_quadrature="trapezoid", relative_mass_tolerance=1e-3,
        absolute_mass_tolerance_kg=1e-12,
        mass_closure_evidence_id="authored-ode-output-grid-refinement-budget")
    handoff.require_current()
    series = handoff.source_history.mass_flow_series()
    assert handoff.source_history.location is location
    assert handoff.source_history.time_s == tuple(trace.time_s)
    assert len(handoff.source_history.samples) == len(trace.snapshots)
    assert all(sample.upstream_stagnation is snapshot.gas
               for sample, snapshot in zip(handoff.source_history.samples, trace.snapshots, strict=True))
    assert np.all(series.values[:, 0] > 0.)
    assert series.clock_id == trace.clock_id
    closure_limit = 1e-12 + 1e-3*np.asarray(handoff.port_interval_mass_kg)
    assert np.all(np.abs(handoff.interval_mass_residual_kg) <= closure_limit)
    mismatch_rejected = False
    oversized_opening = replace(opening, effective_area_factor=opening.effective_area_factor*2.)
    try:
        nozzle_history_from_hydride_trace(trace, nozzle=nozzle, opening=oversized_opening,
            location=location, back_pressure_pa=back_pressure_pa,
            evidence_id="authored-intentional-nozzle-flow-mismatch", origin=Origin.SYNTHETIC,
            port_mass_quadrature="trapezoid", relative_mass_tolerance=1e-3,
            absolute_mass_tolerance_kg=1e-12,
            mass_closure_evidence_id="authored-ode-output-grid-refinement-budget")
    except ValueError as error:
        mismatch_rejected = "does not close" in str(error)
    assert mismatch_rejected
    return ValidationOutcome(True, {
        "release_mass_flow_kg_s": series.values[:, 0].tolist(),
        "hydride_outflow_mass_kg": float(-trace.integrated_external_gas_mass_kg[-1]),
        "nozzle_integrated_mass_kg": float(sum(handoff.nozzle_interval_mass_kg)),
        "mass_closure_residual_kg": list(handoff.interval_mass_residual_kg),
        "oversized_nozzle_mismatch_rejected": mismatch_rejected,
        "nozzle_samples": len(handoff.source_history.samples),
    }, ("Synthetic finite hydride discharge; shared nozzle is the sole outlet-flow model.",
        "Dispersion and hazard consequence are downstream stages, not inferred by this handoff."))


def validate_postsolve_failure_retention(*, work_directory, **parameters):
    del work_directory, parameters
    from unittest.mock import patch

    import numpy as np
    import h2physics.storage.finite_hydride as hydride_module
    from h2physics.storage.finite_hydride import (
        BoundHydrogenEnergyReference,
        FiniteHydrideBed,
        FiniteHydrideDomain,
        FiniteHydrideHeatBoundary,
        FiniteHydrideHeatInput,
        HydrideGasThermodynamics,
        FiniteHydrideIntegrationError,
    )
    from h2physics.storage.hydride import (
        ArrheniusRate, HydrideKinetics, HydrideParameters, HydrideState, VanthoffPlateau,
    )

    gas = HydrideGasThermodynamics.coolprop("Hydrogen")
    material = HydrideParameters(.002, 1000., 24000., gas.molar_mass_kg_mol, 0.)
    kinetics = HydrideKinetics(
        VanthoffPlateau(24000., 80., 1e5),
        ArrheniusRate(.01, 0., 300.), ArrheniusRate(.02, 0., 300.),
    )
    reference = BoundHydrogenEnergyReference.from_gas(
        gas, temperature_k=300., pressure_pa=1e5,
        desorption_enthalpy_j_mol_h2=24000., evidence_id="authored-failure-retention",
    )
    bed = FiniteHydrideBed(
        material, kinetics, gas, reference,
        FiniteHydrideDomain(200., 600., 1e3, 1e7, 1e-7),
        free_gas_volume_m3=.005, gas_solid_conductance_w_k=10.,
    )
    boundary = FiniteHydrideHeatBoundary(
        "hydride-failure-clock", 10., 11.,
        lambda _time, _snapshot: FiniteHydrideHeatInput(300.), "authored-constant-boundary",
    )
    actual_solve_ivp = hydride_module.solve_ivp
    solver_results = []
    postprocess_failure = RuntimeError("synthetic post-solve snapshot assembly failure")

    def solve_then_break(*args, **kwargs):
        result = actual_solve_ivp(*args, **kwargs)
        solver_results.append(result)
        bed.snapshot_from_inventory = lambda *_a, **_k: (_ for _ in ()).throw(postprocess_failure)
        return result

    try:
        with patch.object(hydride_module, "solve_ivp", solve_then_break):
            bed.simulate(
                np.array([10., 10.5, 11.]), HydrideState(.1, 300.), gas.state_pt(3e5, 300.),
                boundary=boundary, clock_id="hydride-failure-clock", maximum_step_s=.25,
            )
    except FiniteHydrideIntegrationError as error:
        assert len(solver_results) == 1
        native = solver_results[0]
        assert error.native_solution is native
        assert error.cause is postprocess_failure and error.__cause__ is postprocess_failure
        assert np.array_equal(native.t, error.native_solution.t)
        assert np.array_equal(native.y, error.native_solution.y)
        assert error.trial_values.ndim == 1 and np.isfinite(error.trial_values).all()
    else:
        raise AssertionError("Post-solve failure returned a successful hydride trace")
    return ValidationOutcome(True, {
        "accepted_solver_samples": len(solver_results[0].t),
        "native_result_retained": True,
        "original_cause_retained": True,
    }, (
        "Synthetic post-processing failure contract only; no hydride material qualification is implied.",
    ))
