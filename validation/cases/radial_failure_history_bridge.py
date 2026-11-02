"""Deferred Nurion checks for radial wall-temperature-to-failure history binding."""

from dataclasses import replace

import numpy as np

from h2physics.cluster_validation import ValidationCase, ValidationOutcome


def cases():
    return (
        ValidationCase(
            identifier="radial-vessel-callback-integrity-signature",
            profile="fracture-fatigue",
            entrypoint=__name__ + ":validate_callback_integrity",
            invariants=(
                "callable source fingerprints include Python code, defaults and nested closure state",
                "bound-method fingerprints remain stable while capturing receiver configuration",
                "changed callback configuration changes its retained source signature",
            ),
        ),
        ValidationCase(
            identifier="radial-wall-temperature-vessel-failure-binding",
            profile="fracture-fatigue",
            entrypoint=__name__ + ":validate_binding",
            invariants=(
                "actual computed radial heat field retained with HELPR loading history",
                "crack-location temperature sampled from cell and surface values",
                "pressure and thermal histories require identical times and clock identity",
                "pressure-plus-thermal stress binds the exact thermal/mechanical/pressure histories and spans the full wall",
                "selected total-stress field joins the original VesselLoading pressure, temperature and clock record",
                "caller SIF callback receives every original total-stress sample on the exact clock",
                "caller-supplied signed and zero SIF values are preserved without absolute-value coercion",
                "exact inclusive SIF windows retain source indices and do not interpolate sample values",
                "off-grid/reversed window bounds and post-selection range edits are rejected",
                "caller-evidenced SIF threshold lookup reports only the first exact sampled hit without event interpolation",
                "post-return SIF maximum summary and exact sample bindings cannot be mutated silently",
                "pressure-only HELPR is not silently used as a radial stress-field solver",
                "thermal-increment convention is rejected to prevent adding pressure twice",
                "field-convention evidence cannot be replaced after binding",
                "thermal and mechanical cylinder surfaces match exactly",
                "out-of-wall sample and evidence mismatch rejected",
                "post-return pressure/thermal/history identities and content are revalidated",
                "post-return service basis, fraction, origin and geometry context remain bound",
                "equivalent replacement context/sample/load objects do not inherit issued identity",
                "HELPR composition errors identify pre/evaluation/post integrity stages and retain causes",
                "sampled radial bridge rejects an unrelated or replaced native trace",
                "guarded result enters the existing native HELPR failure API without rebuilding its history",
            ),
        ),
    )


def validate_callback_integrity(*, work_directory, **parameters):
    from h2physics.adapters.radial_failure_history import _callable_binding

    del work_directory, parameters
    def boundary(*, scale=1.0):
        return scale

    original = _callable_binding(boundary)
    boundary.__kwdefaults__["scale"] = 2.0
    changed = _callable_binding(boundary)
    assert original != changed

    def capture():
        configuration = {"scale": [1.0]}

        def callback():
            return configuration["scale"][0]

        return callback, configuration

    callback, configuration = capture()
    closure_original = _callable_binding(callback)
    configuration["scale"][0] = 2.0
    closure_changed = _callable_binding(callback)
    assert closure_original != closure_changed

    class Receiver:
        def __init__(self):
            self.scale = 1.0

        def callback(self):
            return self.scale

    receiver = Receiver()
    method = receiver.callback
    method_original = _callable_binding(method)
    assert method_original == _callable_binding(receiver.callback)
    receiver.scale = 2.0
    assert method_original != _callable_binding(receiver.callback)

    def code_one():
        return 1

    def code_two():
        return 2

    code_original = _callable_binding(code_one)
    code_one.__code__ = code_two.__code__
    assert code_original != _callable_binding(code_one)
    return ValidationOutcome(True, {"changed_callback_signatures_detected": 4})


def validate_binding(*, work_directory, **parameters):
    from h2physics.adapters.radial_failure_history import (
        bind_radial_thermal_history_to_vessel,
    )
    from h2physics.adapters.vessel_failure import VesselFailureContext
    from h2physics.core import Origin, PropertyBasis
    from h2physics.materials.elastic_cylinder import (
        CylinderGeometry,
        CylinderPressureLoad,
        lame_stress_samples,
    )
    from h2physics.materials.radial_heat import (
        RadialSolidMaterial,
        RadialThermalBoundary,
        radial_cylinder_heat_history,
    )

    del work_directory, parameters
    clock_id = "radial-failure-shared-clock"
    times = np.array([0.0, 10.0, 20.0])
    thermal = radial_cylinder_heat_history(
        0.05,
        0.10,
        1.0,
        RadialSolidMaterial(
            7800.0,
            lambda temperature: 500.0,
            lambda temperature: 16.0,
            "authored-wall-material",
            "authored-constant-property-boundary",
        ),
        300.0,
        times,
        RadialThermalBoundary("heat_flux", 250.0, "authored-inner-heat"),
        RadialThermalBoundary("adiabatic", 0.0, "authored-outer-adiabatic"),
        cells=12,
        history_id="authored-crack-region-wall-history",
        clock_id=clock_id,
        evidence_id="authored-radial-wall-heat-model",
    )
    geometry = CylinderGeometry(0.05, 0.10, "closed", "authored-failure-cylinder")
    loads = tuple(
        CylinderPressureLoad(
            5e6 + index * 0.1e6,
            0.1e6,
            f"authored-load-{index}",
            Origin.SYNTHETIC,
        )
        for index in range(len(times))
    )
    pressure = lame_stress_samples(
        geometry,
        times,
        loads,
        np.array([0.05, 0.075, 0.10]),
        evidence_id="authored-cylinder-pressure-field",
        clock_id=clock_id,
    )
    context = VesselFailureContext(
        vessel_id="authored-pressure-vessel",
        wall_region_id="authored-inner-flaw-tip-region",
        frame_id="authored-cylinder-frame",
        clock_id=clock_id,
        source_id="authored-pressure-source",
        fluid_basis=PropertyBasis("hydrogen", "authored-property-reference", "normal"),
        hydrogen_mole_fraction=1.0,
        hydrogen_service_evidence_id="authored-hydrogen-service",
        wall_temperature_evidence_id=thermal.evidence_id,
        geometry_binding_evidence_id="authored-flaw-position-map",
        origin=Origin.SYNTHETIC,
    )
    flaw_tip_radius = 0.05 + 0.004
    binding = bind_radial_thermal_history_to_vessel(
        pressure,
        context,
        thermal,
        temperature_radius_m=flaw_tip_radius,
        phase_id="single-gas-phase",
        pressure_source_evidence_id="authored-pressure-source",
        temperature_mapping_evidence_id="authored-flaw-tip-radial-map",
        reconstruction_evidence_id="authored-exact-sample-map",
    )
    from h2physics.adapters.radial_failure_history import (
        bind_radial_thermoelastic_history_to_vessel,
    )
    from h2physics.materials.elastic_cylinder import IsotropicThermoelasticMaterial

    thermoelastic = thermal.thermoelastic_history(
        loads,
        geometry,
        IsotropicThermoelasticMaterial(
            190e9, 0.29, 12e-6, "authored-failure-elastic-material",
            "authored-elastic-property-evidence",
        ),
        np.linspace(0.05, 0.10, 21),
        reference_temperature_k=300.0,
        axial_restraint="free",
        evidence_id="authored-radial-stress-field-equations",
    )
    thermoelastic_binding = bind_radial_thermoelastic_history_to_vessel(
        binding,
        thermoelastic,
        field_convention="total_pressure_plus_thermal",
        field_convention_evidence_id="authored-total-cauchy-stress-convention",
    )
    assert thermoelastic_binding.require_current() is thermoelastic_binding
    assert thermoelastic_binding.total_stress_history is thermoelastic.stress
    joined_sample = thermoelastic_binding.sample_at(1)
    assert joined_sample.require_current() is joined_sample
    assert joined_sample.stress_sample.stress_field is joined_sample.total_stress_field
    assert joined_sample.loading is binding.history.samples[1]
    assert joined_sample.loading.time_s == joined_sample.stress_sample.time_s
    assert joined_sample.loading.internal_pressure_pa_absolute == loads[1].internal_pressure_pa
    assert joined_sample.loading.wall_temperature_k == binding.wall_temperature_k[1]
    from h2physics.adapters.radial_failure_history import (
        evaluate_radial_stress_intensity_samples,
    )
    received = []
    radial_series = evaluate_radial_stress_intensity_samples(
        thermoelastic_binding,
        lambda sample: received.append(sample) or float(
            np.max(np.abs(sample.total_stress_field.radial_stress_pa))),
        calculation_evidence_id="authored-interface-only-synthetic-stress-measure",
    )
    assert len(received) == len(times) == len(radial_series.stress_intensity_values_pa_sqrt_m)
    assert all(sample.loading.time_s == time for sample, time in zip(received, times, strict=True))
    assert radial_series.maximum_sampled_index == int(np.argmax(
        radial_series.stress_intensity_values_pa_sqrt_m))
    assert radial_series.require_current() is radial_series
    exact_window = radial_series.sampled_window(times[1], times[2])
    assert exact_window.sampled_times_s == (times[1], times[2])
    assert exact_window.stress_intensity_values_pa_sqrt_m == (
        radial_series.stress_intensity_values_pa_sqrt_m[1],
        radial_series.stress_intensity_values_pa_sqrt_m[2],
    )
    assert exact_window.duration_s == times[2] - times[1]
    assert exact_window.maximum_source_index == max(
        range(1, 3), key=radial_series.stress_intensity_values_pa_sqrt_m.__getitem__,
    )
    assert exact_window.require_current() is exact_window
    for bounds in ((times[1] + 0.1, times[2]), (times[2], times[1])):
        try:
            radial_series.sampled_window(*bounds)
        except ValueError:
            continue
        raise AssertionError(f"Invalid exact SIF window was admitted: {bounds!r}")
    original_window_end = exact_window.end_index
    object.__setattr__(exact_window, "end_index", exact_window.end_index - 1)
    try:
        exact_window.require_current()
    except ValueError:
        window_mutation_rejected = True
    else:
        raise AssertionError("A changed SIF window retained its original selection receipt")
    object.__setattr__(exact_window, "end_index", original_window_end)
    assert exact_window.require_current() is exact_window
    signed_values = iter((-3.0, 0.0, 2.0))
    signed_series = evaluate_radial_stress_intensity_samples(
        thermoelastic_binding,
        lambda _sample: next(signed_values),
        calculation_evidence_id="authored-signed-mode-I-contract",
    )
    assert signed_series.stress_intensity_values_pa_sqrt_m == (-3.0, 0.0, 2.0)
    assert signed_series.maximum_sampled_sif_pa_sqrt_m == 2.0
    assert signed_series.require_current() is signed_series
    threshold_hit = signed_series.first_sample_at_or_above(
        1.0, threshold_evidence_id="caller-qualified-critical-sif",
    )
    assert threshold_hit.sample_index == 2
    assert threshold_hit.time_s == times[2]
    assert threshold_hit.sampled_sif_pa_sqrt_m == 2.0
    assert threshold_hit.require_current() is threshold_hit
    assert signed_series.first_sample_at_or_above(
        2.1, threshold_evidence_id="caller-qualified-critical-sif",
    ) is None
    try:
        replace(threshold_hit, sample_index=1).require_current()
    except ValueError:
        pass
    else:
        raise AssertionError("Threshold receipt must retain the first exact qualifying sample")
    compressive_values = iter((-3.0, -1.0, -2.0))
    compressive_series = evaluate_radial_stress_intensity_samples(
        thermoelastic_binding,
        lambda _sample: next(compressive_values),
        calculation_evidence_id="authored-negative-mode-I-contract",
    )
    assert compressive_series.maximum_sampled_sif_pa_sqrt_m == -1.0
    assert compressive_series.maximum_sampled_index == 1
    original_maximum_sif = radial_series.maximum_sampled_sif_pa_sqrt_m
    object.__setattr__(radial_series, "maximum_sampled_sif_pa_sqrt_m",
                       original_maximum_sif * 1.01)
    try:
        radial_series.require_current()
    except ValueError as error:
        assert "Maximum SIF summary" in str(error)
    else:
        raise AssertionError("Changed sampled-SIF maximum remained covered by its receipt")
    object.__setattr__(radial_series, "maximum_sampled_sif_pa_sqrt_m",
                       original_maximum_sif)
    assert radial_series.require_current() is radial_series
    for invalid_index, expected_error in ((True, TypeError), (1.0, TypeError), (-1, ValueError), (len(times), ValueError)):
        try:
            thermoelastic_binding.sample_at(invalid_index)
        except expected_error:
            continue
        raise AssertionError(f"Invalid joined vessel/stress sample index was admitted: {invalid_index!r}")
    try:
        replace(joined_sample, loading=replace(joined_sample.loading))
    except ValueError:
        replacement_loading_rejected = True
    else:
        raise AssertionError("An equal-valued replacement loading inherited the joined sample identity")
    assert np.array_equal(thermoelastic.stress.time_s, pressure.time_s)
    assert thermoelastic.stress.geometry is pressure.geometry
    assert np.allclose(
        thermoelastic.stress.radial_stress_pa[:, 0],
        -np.array([load.internal_pressure_pa for load in loads]),
        rtol=2e-6, atol=10.0,
    )
    assert np.allclose(
        thermoelastic.stress.radial_stress_pa[:, -1],
        -np.array([load.external_pressure_pa for load in loads]),
        rtol=2e-6, atol=10.0,
    )
    try:
        bind_radial_thermoelastic_history_to_vessel(
            binding,
            thermoelastic,
            field_convention="thermal_increment",
            field_convention_evidence_id="incorrect-increment-declaration",
        )
    except ValueError:
        thermal_increment_rejected = True
    else:
        raise AssertionError("A total pressure-plus-thermal field was relabeled as an increment")
    changed_convention_evidence = replace(thermoelastic_binding)
    object.__setattr__(
        changed_convention_evidence,
        "field_convention_evidence_id",
        "different-valid-looking-convention-evidence",
    )
    try:
        changed_convention_evidence.require_current()
    except ValueError:
        convention_evidence_change_rejected = True
    else:
        raise AssertionError("A changed field-convention evidence identity was retained")
    radial_nodes = np.r_[thermal.inner_radius_m, thermal.radius_m, thermal.outer_radius_m]
    expected = np.array(
        [
            np.interp(
                flaw_tip_radius,
                radial_nodes,
                np.r_[thermal.inner_surface_temperature_k[i],
                      thermal.temperature_k[i], thermal.outer_surface_temperature_k[i]],
            )
            for i in range(times.size)
        ]
    )
    assert np.array_equal(binding.wall_temperature_k, expected)
    assert tuple(sample.time_s for sample in binding.history.samples) == tuple(times)
    assert tuple(sample.internal_pressure_pa_absolute for sample in binding.history.samples) == tuple(
        load.internal_pressure_pa for load in loads
    )
    assert binding.require_current() is binding
    from examples.vessel_failure import authored_case
    from h2physics.adapters.vessel_failure import HelprVesselFailure

    flaw, material_law, _ = authored_case()
    helpr = HelprVesselFailure(
        flaw,
        material_law,
        criterion="separate_yield_and_toughness",
        criterion_evidence_id="authored-radial-failure-composition-only",
    )
    prediction = binding.predict_failure(
        helpr,
        maximum_reconstruction_step_s=5.0,
    )
    assert prediction.history is binding.history
    assert prediction.termination in {
        "first_resolved_initiation", "no_resolved_initiation_within_support"
    }
    original_fraction = binding.source_binding.history.context.hydrogen_mole_fraction
    object.__setattr__(binding.source_binding.history.context, "hydrogen_mole_fraction", 0.5)
    try:
        binding.predict_failure(helpr, maximum_reconstruction_step_s=5.0)
    except Exception as error:
        from h2physics.adapters.radial_failure_history import RadialThermalVesselFailureError

        if not isinstance(error, RadialThermalVesselFailureError):
            raise
        assert error.stage == "pre_evaluation_integrity"
        assert error.binding is binding
        assert isinstance(error.cause, ValueError)
        changed_context_rejected = True
    else:
        raise AssertionError("Changed context was admitted to the HELPR failure composition")
    finally:
        object.__setattr__(
            binding.source_binding.history.context,
            "hydrogen_mole_fraction",
            original_fraction,
        )
    object.__setattr__(binding.source_binding.history, "native_trace", object())
    try:
        binding.require_current()
    except ValueError:
        unrelated_native_trace_rejected = True
    else:
        raise AssertionError("An unrelated native trace was admitted to exact-sample binding")
    finally:
        object.__setattr__(binding.source_binding.history, "native_trace", None)
    original_context_object = binding.source_binding.history.context
    object.__setattr__(
        binding.source_binding.history,
        "context",
        replace(original_context_object),
    )
    try:
        binding.require_current()
    except ValueError:
        replaced_equal_context_rejected = True
    else:
        raise AssertionError("A new equal-valued context inherited the issued source identity")
    finally:
        object.__setattr__(binding.source_binding.history, "context", original_context_object)
    changed_source_binding = replace(
        binding.source_binding,
        wall_temperature_k=binding.source_binding.wall_temperature_k + 0.5,
    )
    object.__setattr__(binding, "source_binding", changed_source_binding)
    try:
        binding.require_current()
    except ValueError:
        changed_mapping_rejected = True
    else:
        raise AssertionError("A replaced post-return vessel mapping was admitted")

    rejected_clock = False
    try:
        other = radial_cylinder_heat_history(
            0.05,
            0.10,
            1.0,
            thermal.material,
            300.0,
            times,
            RadialThermalBoundary("adiabatic", 0.0, "different-inner-boundary"),
            RadialThermalBoundary("adiabatic", 0.0, "different-outer-boundary"),
            cells=12,
            history_id="authored-other-clock-wall",
            clock_id="different-clock",
            evidence_id=thermal.evidence_id,
        )
        bind_radial_thermal_history_to_vessel(
            pressure, context, other, temperature_radius_m=flaw_tip_radius,
            phase_id="single-gas-phase", pressure_source_evidence_id="authored-pressure-source",
            temperature_mapping_evidence_id="authored-flaw-tip-radial-map",
            reconstruction_evidence_id="authored-exact-sample-map",
        )
    except ValueError:
        rejected_clock = True
    assert rejected_clock

    rejected_radius = False
    try:
        bind_radial_thermal_history_to_vessel(
            pressure, context, thermal, temperature_radius_m=0.049,
            phase_id="single-gas-phase", pressure_source_evidence_id="authored-pressure-source",
            temperature_mapping_evidence_id="authored-flaw-tip-radial-map",
            reconstruction_evidence_id="authored-exact-sample-map",
        )
    except ValueError:
        rejected_radius = True
    assert rejected_radius
    return ValidationOutcome(
        True,
        {
            "mapped_samples": len(binding.history.samples),
            "total_stress_field_samples": len(thermoelastic.stress.time_s),
            "total_stress_field_convention": thermoelastic_binding.field_convention,
            "joined_stress_loading_time_s": joined_sample.stress_sample.time_s,
            "sif_window_duration_s": exact_window.duration_s,
            "sif_window_source_indices": (exact_window.start_index, exact_window.end_index),
            "sif_window_mutation_rejected": window_mutation_rejected,
            "equal_loading_replacement_rejected": replacement_loading_rejected,
            "thermal_increment_convention_rejected": thermal_increment_rejected,
            "changed_convention_evidence_rejected": convention_evidence_change_rejected,
            "mechanical_temperature_radius_m": flaw_tip_radius,
            "maximum_temperature_k": float(np.max(binding.wall_temperature_k)),
            "mismatched_clock_rejected": rejected_clock,
            "out_of_wall_radius_rejected": rejected_radius,
            "changed_post_return_mapping_rejected": changed_mapping_rejected,
            "native_failure_evaluations": len(prediction.evaluations),
            "changed_post_return_service_context_rejected": changed_context_rejected,
            "unrelated_native_trace_rejected": unrelated_native_trace_rejected,
            "replaced_equal_context_rejected": replaced_equal_context_rejected,
        },
        (
            "This case checks a computed-field integration boundary only; it does not qualify a crack location, material law, native FAD criterion or vessel life.",
            "The radial wall solve is still a constant-property axisymmetric model; time interpolation and temperature extrapolation are not performed.",
        ),
    )
