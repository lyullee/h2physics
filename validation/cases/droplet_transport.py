"""Deferred native parcel checks. Import and cases() perform no calculations."""

from h2physics.cluster_validation import ValidationCase, ValidationOutcome


def cases():
    cases = []
    cases.append(ValidationCase(
        identifier="parcel-vapor-interval-source-handoff",
        profile="droplet-transport",
        entrypoint="validation.cases.droplet_transport:validate_reference",
        parameters={"mode": "vapor-source-handoff"},
        invariants=(
            "accepted native cumulative evaporation becomes exact interval vapor mass",
            "original parcel issuer, exact vapor ThermoState, clock and coordinate frame are retained",
            "caller supplies evidence for collapsing a moving trajectory into a fixed source location",
            "mutation of a source bin invalidates the handoff seal",
            "no gas dispersion or parcel-to-cloud momentum transfer is inferred",
        ),
    ))
    for mode in ("constant-heat", "ground-crossing"):
        cases.append(ValidationCase(
            identifier="parcel-"+mode, profile="droplet-transport",
            entrypoint="validation.cases.droplet_transport:validate_reference",
            parameters={"mode": mode}, invariants=(
                "native CoolProp saturation and retained SciPy result",
                "ParcelTrace is issued only by the completed native flight and rejects direct construction/clone replay",
                "post-issuance edits to native arrays or conservation summaries invalidate population/impact consumers",
                "independent constant-heat mass loss", "mass/energy/momentum closure",
                "positive terminal residual; incident is not deposited liquid")))
    cases.append(ValidationCase(
        identifier="parcel-initial-flash", profile="droplet-transport",
        entrypoint="validation.cases.droplet_transport:validate_reference",
        parameters={"mode": "initial-flash"}, invariants=(
            "native PH flash remains within a resolved two-phase state",
            "finite flash partitions total mass between saturated endpoints",
            "weighted endpoint enthalpy closes the isenthalpic partition",
            "remaining liquid mass is exposed as the parcel-flight initial inventory",
            "single-phase expansion and missing phase evidence are rejected")))
    return tuple(cases)


def validate_reference(*, work_directory, mode):
    import json
    from pathlib import Path

    from h2physics.adapters.droplet_transport import (
        BoilingHeat,
        ParcelBoundary,
        ParcelTrace,
        SaturatedParcelFlight,
    )
    from h2physics.thermo.coolprop import CoolPropProperties

    if mode == "vapor-source-handoff":
        from h2physics.adapters.parcel_vapor_source import vapor_source_from_parcel_trace
        from h2physics.core import Origin
        from h2physics.release import SourceLocation

        boundary = ParcelBoundary("authored-clock", "inertial-z-up", "authored-reference-only",
            .01, 1e-5, (0., 0., 0.), (0., 0., 0.), 1e5, 1., .002, .01)
        owner = SaturatedParcelFlight(CoolPropProperties(), 101325., boundary,
            lambda state: BoilingHeat(1e-4, "authored-constant-heat-verification"),
            force_approximation_evidence_id="authored-zero-relative-velocity/reference")
        trace = owner.run(start_s=0., end_s=2., position_m=(0., 0., 1.),
            velocity_m_s=(0., 0., 0.), mass_kg=1e-6, residual_mass_floor_kg=1e-8,
            maximum_step_s=.01, relative_tolerance=1e-9,
            absolute_tolerances=(1e-11,)*17)
        location = SourceLocation("parcel-cloud-projection", boundary.clock_id,
            boundary.frame_id, (0., 0., 1.), (0., 0., -1.))
        handoff = vapor_source_from_parcel_trace(trace, location=location,
            origin=Origin.PREDICTED, evidence_id="authored-vapor-source-contract",
            location_projection_evidence_id="authored-fixed-location-projection")
        handoff.require_current()
        total = float(handoff.source.mass_kg.sum())
        assert abs(total-trace.evaporated_mass_kg) <= max(1e-15, trace.evaporated_mass_kg*1e-12)
        original = handoff.source.mass_kg
        altered = original.copy()
        altered[0] += 1e-12
        object.__setattr__(handoff.source, "mass_kg", altered)
        try:
            handoff.require_current()
        except ValueError:
            pass
        else:
            raise AssertionError("Changed interval vapor mass remained current")
        object.__setattr__(handoff.source, "mass_kg", original)
        handoff.source.require_current()
        metrics = {"evaporated_mass_kg": trace.evaporated_mass_kg,
                   "source_total_mass_kg": total,
                   "interval_count": len(handoff.source.mass_kg)}
        destination = Path(work_directory)
        destination.mkdir(parents=True, exist_ok=True)
        (destination/"parcel_vapor_source.json").write_text(
            json.dumps(metrics, allow_nan=False)+"\n", encoding="utf-8")
        return ValidationOutcome(True, metrics, (
            "Authored constant-heat handoff contract only; no experimental evaporation validation",
            "A fixed source location is a caller-declared projection of a moving parcel",
            "No external vapor cloud dispersion is represented",
        ))

    if mode == "initial-flash":
        from h2physics.adapters.droplet_transport import flash_initial_liquid_release

        properties = CoolPropProperties()
        upstream = properties.saturated(0.8e6, 0.)
        flash = flash_initial_liquid_release(
            properties, upstream, downstream_pressure_pa=101325.,
            total_release_mass_kg=0.01,
            phase_equilibrium_evidence_id="authored-equilibrium-throttling-reference",
        )
        assert flash.downstream_equilibrium_state.phase == "two_phase"
        assert 0. < flash.vapor_mass_fraction < 1.
        assert abs(flash.mass_residual_kg) < 1e-15
        assert abs(flash.enthalpy_residual_j) < 1e-6
        assert flash.launch_liquid_mass_kg == flash.liquid_mass_kg > 0.
        from dataclasses import replace

        for pressure in (upstream.pressure_pa, upstream.pressure_pa*1.1):
            try:
                flash_initial_liquid_release(
                    properties, upstream, downstream_pressure_pa=pressure,
                    total_release_mass_kg=0.01,
                    phase_equilibrium_evidence_id="authored-pressure-admission",
                )
            except ValueError:
                pass
            else:
                raise AssertionError("Nondecreasing pressure admitted as a liquid expansion")
        try:
            replace(flash, downstream_equilibrium_state=replace(
                flash.downstream_equilibrium_state,
                enthalpy_j_kg=flash.upstream_state.enthalpy_j_kg+100.,
            ))
        except ValueError:
            pass
        else:
            raise AssertionError("Non-isenthalpic PH result admitted as initial flash")
        vapor_upstream = properties.saturated(0.8e6, 1.)
        try:
            flash_initial_liquid_release(
                properties, vapor_upstream, downstream_pressure_pa=101325.,
                total_release_mass_kg=0.01,
                phase_equilibrium_evidence_id="authored-single-phase-rejection",
            )
        except ValueError:
            pass
        else:
            raise AssertionError("Single-phase expansion was admitted as a flashing liquid parcel")
        try:
            flash_initial_liquid_release(
                properties, upstream, downstream_pressure_pa=101325.,
                total_release_mass_kg=0.01, phase_equilibrium_evidence_id="",
            )
        except ValueError:
            pass
        else:
            raise AssertionError("Initial flashing was admitted without phase-evidence identity")
        metrics = {
            "vapor_mass_fraction": flash.vapor_mass_fraction,
            "flash_vapor_mass_kg": flash.flashed_vapor_mass_kg,
            "parcel_launch_liquid_mass_kg": flash.launch_liquid_mass_kg,
            "mass_residual_kg": flash.mass_residual_kg,
            "enthalpy_residual_j": flash.enthalpy_residual_j,
        }
        destination = Path(work_directory)
        destination.mkdir(parents=True, exist_ok=True)
        (destination/"parcel_initial_flash.json").write_text(
            json.dumps(metrics, allow_nan=False)+"\n", encoding="utf-8",
        )
        return ValidationOutcome(True, metrics, (
            "Authored pure-fluid equilibrium-throttle reference only",
            "Flash vapor momentum and flashing-jet dynamics are not modelled",
            "No flashing experiment, aerosol-size or droplet-yield validation is established",
        ))

    boundary = ParcelBoundary("authored-clock", "inertial-z-up", "authored-reference-only",
        .01, 1e-5, (0., 0., 0.), (0., 0., 0.), 1e5, 1., .002, .01)
    heat = 1e-4
    owner = SaturatedParcelFlight(CoolPropProperties(), 101325., boundary,
        lambda state: BoilingHeat(heat, "authored-constant-heat-verification"),
        force_approximation_evidence_id="authored-zero-relative-velocity/reference")
    # For impact, choose carrier velocity equal to the incident velocity: drag=0.
    if mode == "ground-crossing":
        from dataclasses import replace
        boundary = replace(boundary, carrier_velocity_m_s=(0., 0., -1.))
        owner.boundary = boundary
    velocity = (0., 0., -1.) if mode == "ground-crossing" else (0., 0., 0.)
    result = owner.run(start_s=0., end_s=2., position_m=(0., 0., 1.),
        velocity_m_s=velocity, mass_kg=1e-6, residual_mass_floor_kg=1e-8,
        maximum_step_s=.01, relative_tolerance=1e-9,
        absolute_tolerances=(1e-11,)*17,
        ground_z_m=0. if mode == "ground-crossing" else None)
    from dataclasses import replace
    try:
        replace(result)
    except ValueError:
        pass
    else:
        raise AssertionError("ParcelTrace accepted replay of its consumed native issuer")
    try:
        ParcelTrace(result.boundary, result.native_result, result.trials, result.states,
                    result.end_reason, result.evaporated_mass_kg, result.heat_into_liquid_j,
                    result.drag_work_j, result.vapor_total_energy_out_j,
                    result.vapor_momentum_out_kg_m_s, result.ambient_pressure_work_into_j,
                    result.mass_residual_kg, result.total_energy_residual_j,
                    result.momentum_residual_kg_m_s)
    except ValueError:
        pass
    else:
        raise AssertionError("ParcelTrace accepted direct construction without its native-run issuer")
    original_evaporated = result.evaporated_mass_kg
    object.__setattr__(result, "evaporated_mass_kg", original_evaporated+1e-6)
    try:
        result.require_current()
    except ValueError:
        pass
    else:
        raise AssertionError("ParcelTrace retained currentness after summary mutation")
    object.__setattr__(result, "evaporated_mass_kg", original_evaporated)
    assert result.require_current() is result
    elapsed = result.states[-1].time_s-result.states[0].time_s
    expected = heat*elapsed/owner.latent_heat_j_kg
    assert abs(result.evaporated_mass_kg-expected) < 1e-13
    assert abs(result.mass_residual_kg) < 1e-13
    assert abs(result.total_energy_residual_j) < 1e-8
    assert max(abs(x) for x in result.momentum_residual_kg_m_s) < 1e-12
    assert result.states[-1].mass_kg > 0
    expected_pressure_work = owner.pressure_pa*result.evaporated_mass_kg/owner.liquid.density_kg_m3
    assert abs(result.ambient_pressure_work_into_j-expected_pressure_work) < 1e-10
    if mode == "ground-crossing":
        assert result.end_reason == "incident_ground_crossing"
        assert abs(elapsed-1.) < 1e-8
    metrics = {"elapsed_s": elapsed, "mass_residual_kg": result.mass_residual_kg,
               "energy_residual_j": result.total_energy_residual_j,
               "ambient_pressure_work_into_j": result.ambient_pressure_work_into_j,
               "mass_loss_error_kg": result.evaporated_mass_kg-expected}
    destination = Path(work_directory)
    destination.mkdir(parents=True, exist_ok=True)
    (destination/"parcel.json").write_text(json.dumps(metrics, allow_nan=False)+"\n",
                                          encoding="utf-8")
    return ValidationOutcome(True, metrics, (
        "Authored reference only; heat-transfer/air condensation unqualified",
        "No deposited fraction, breakup, flashing or coupled gas response"))
