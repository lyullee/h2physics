"""Deferred HyRAM radiation to lumped thermal-target coupling."""

from h2physics.cluster_validation import ValidationCase, ValidationOutcome


def cases():
    return (ValidationCase(
        identifier="hyram-radiation-lumped-thermal-target-handoff",
        profile="jet-fire-conservation",
        entrypoint=__name__ + ":validate_handoff",
        invariants=(
            "accepted HyRAM observer irradiance remains incident W/m2 on its exact steady interval",
            "observer-to-target surface and irradiance projection are caller-evidenced",
            "original source, receptor, frame, clock and interval survive into the target input",
            "surface, irradiance-projection and history-mapping evidence identifiers remain sealed and current",
            "target temperature/energy response uses the existing lumped thermal solver and supplied properties",
            "no view factor, target absorptivity, transient fire, injury, or equipment failure is inferred",
        ),
    ),)


def validate_handoff(*, work_directory, **parameters):
    del work_directory
    from examples.jet_fire_conservation import build_source
    from h2physics.adapters.hyram_thermal_target import incident_heat_history_from_hyram_radiation
    from h2physics.adapters.thermal_target import (
        LumpedThermalTarget, ThermalTargetTolerances, run_thermal_target,
    )
    from h2physics.core import Origin

    source = build_source(
        native_packages=parameters.get("native_packages"),
        upstream_temperature_k=parameters.get("upstream_temperature_k", 300.),
        ambient_temperature_k=parameters.get("ambient_temperature_k", 293.15),
    )
    radiation = source.irradiance(
        [[0., 3., 2.], [1., 3., 2.]], relative_humidity=.5,
        minimum_source_distance_m=.1,
    )
    binding = incident_heat_history_from_hyram_radiation(
        radiation, observer_index=1, start_s=source.window.start_s,
        end_s=source.window.end_s, receptor_id="authored-thermal-target-receptor",
        basis_id="incident-hyram-scalar-irradiance-w-m2",
        surface_mapping_evidence_id="authored-observer-to-target-surface-mapping",
        irradiance_projection_evidence_id="authored-plane-projection-already-applied",
        history_mapping_evidence_id="authored-steady-window-left-hold",
    )
    target = LumpedThermalTarget(
        area_m2=.01, heat_capacity_j_k=1e4, initial_temperature_k=293.15,
        absorptivity=.5, emissivity=.8, convective_coefficient_w_m2_k=5.,
        ambient_temperature_k=293.15, radiant_surroundings_temperature_k=293.15,
        minimum_temperature_k=250., maximum_temperature_k=1500.,
        material_evidence_id="authored-target-heat-capacity-and-optical-data",
        geometry_evidence_id="authored-target-area-and-location",
        convection_evidence_id="authored-convection-boundary",
        radiation_evidence_id="authored-target-emissivity-and-surroundings",
        origin=Origin.SYNTHETIC,
    )
    tolerances = ThermalTargetTolerances(energy_j=1e-4, relative_energy=1e-8, clock_s=1e-9)
    trace = run_thermal_target(binding.history, target, tolerances,
                               maximum_step_s=max((source.window.end_s-source.window.start_s)/20., 1e-6))
    binding.require_current()
    trace.require_current()
    assert trace.history is binding.history
    assert trace.history.source_owner is binding.source_guard
    assert trace.history.incident_flux_w_m2[0] == radiation.irradiance_w_m2[1]
    return ValidationOutcome(True, {
        "incident_flux_w_m2": float(trace.history.incident_flux_w_m2[0]),
        "target_maximum_temperature_k": trace.maximum_temperature_k,
        "absorbed_incident_energy_j": float(trace.absorbed_incident_j[-1]),
        "maximum_energy_residual_j": float(max(abs(v) for v in trace.energy_residual_j)),
        "receptor_id": trace.history.source_owner.receptor_id if hasattr(trace.history.source_owner, "receptor_id") else binding.exposure.receptor.receptor_id,
    }, ("Synthetic thermal-target interface check only; it does not qualify a real target or fire exposure.",))
