"""Deferred finite-LH2 separator to vessel-failure history contract."""

from h2physics.cluster_validation import ValidationCase, ValidationOutcome


def cases():
    return (ValidationCase(
        identifier="finite-separator-vessel-failure-history-handoff",
        profile="finite-transfer",
        entrypoint=__name__ + ":validate_handoff",
        invariants=(
            "accepted liquid/vapor thermodynamic rows provide one exact absolute internal pressure per accepted time",
            "pure-H2 property basis, native owner and clock remain bound through HELPR history use",
            "caller supplies one shell-wall temperature and external absolute pressure per exact sample",
            "pressure basis, shell region and geometry mapping are explicit and checked",
            "liquid/vapor temperature is never used as vessel wall temperature",
            "HELPR remains the only failure criterion; no rupture or release law is added",
        ),
    ),)


def validate_handoff(*, work_directory, **parameters):
    del work_directory, parameters
    from h2physics.adapters.finite_separator import run_finite_pure_fluid_separator
    from h2physics.adapters.finite_separator_vessel_failure import history_from_finite_separator
    from h2physics.adapters.vessel_failure import VesselFailureContext
    from h2physics.core import Origin
    from validation.cases.finite_separator import build_problem

    tank, initial, bridge = build_problem()
    clock = "authored-separator-vessel-common-clock"

    def phase_domain(state):
        assert 10. < state.temperature_k < 100.
        assert 1e4 <= state.pressure_pa <= 1.25e6

    trace = run_finite_pure_fluid_separator(
        tank, initial, bridge=bridge, material_species_id="H2:para",
        duration_s=0.1, maximum_step_s=0.05, start_time_s=100.,
        clock_id=clock, phase_flows=lambda _time, _thermo: ((), ()),
        ambient_temperature_k=30., phase_assignment_evidence_id="authored-no-flow-phase-assignment",
        phase_domains={"liquid": phase_domain, "vapor": phase_domain},
        mass_tolerance_kg=1e-9, energy_tolerance_j=1e-3,
        minimum_liquid_inventory_kg=1e-10, minimum_vapor_inventory_kg=1e-10,
    )
    basis = trace.points[0].liquid.basis
    source_id = (f"finite-separator:{trace.material_species_id}:"
                 f"{basis.reference_id}:{trace.native_provenance.package_sha256}")
    context = VesselFailureContext(
        "authored-LH2-vessel", "authored-LH2-shell-region", "authored-facility-frame",
        clock, source_id, basis, 1.0, "authored-pure-hydrogen-service",
        "authored-independent-shell-temperature-mapping",
        "authored-shell-geometry-mapping", Origin.SYNTHETIC,
    )
    walls = tuple(30.0 for _ in trace.points)
    history = history_from_finite_separator(
        trace, context=context, wall_temperature_k=walls,
        external_pressure_pa_absolute=lambda _time: 101325.0,
        shell_id=context.wall_region_id,
        wall_mapping_evidence_id=context.wall_temperature_evidence_id,
        geometry_mapping_evidence_id=context.geometry_binding_evidence_id,
        pressure_basis_id="Pa_absolute",
        pressure_basis_evidence_id="authored-absolute-pressure-mapping",
        external_pressure_evidence_id="authored-ambient-pressure-history",
        reconstruction_evidence_id="authored-HELPR-history-reconstruction",
    )
    assert len(history.samples) == len(trace.points)
    assert all(sample.internal_pressure_pa_absolute == point.liquid.pressure_pa
               and sample.time_s == point.time_s
               for sample, point in zip(history.samples, trace.points, strict=True))
    assert tuple(sample.wall_temperature_k for sample in history.samples) == walls
    assert history.native_trace is trace
    assert history.require_current() is history
    return ValidationOutcome(True, {
        "accepted_samples": len(history.samples),
        "absolute_pressure_pa_first": history.samples[0].internal_pressure_pa_absolute,
        "clock_id": history.context.clock_id,
        "source_id": history.context.source_id,
    }, ("Synthetic history-interface contract only; no HELPR prediction, failure probability or release consequence is implied.",))
