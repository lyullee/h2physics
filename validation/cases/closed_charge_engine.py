"""Deferred Nurion geometry and native closed-charge engine contracts."""

from h2physics.cluster_validation import ValidationCase, ValidationOutcome

LIMITS = (
    "Cantera 3.2 owns homogeneous ideal-gas chemistry and integration.",
    "The moving-wall pressure-volume work and first-law residual are sampled diagnostics.",
    "No spark, injection, valve, calibrated heat transfer, full-cycle or engine qualification is implied.",
)


def cases():
    return (
        ValidationCase(
            identifier="hydrogen-engine-slider-crank-geometry",
            profile="hydrogen-engine",
            entrypoint=__name__ + ":validate_geometry",
            invariants=("positive-clearance-volume", "dead-center-extrema", "volume-rate-zero-at-dead-centers"),
        ),
        ValidationCase(
            identifier="hydrogen-engine-input-admission",
            profile="hydrogen-engine",
            entrypoint=__name__ + ":validate_input_admission",
            invariants=("reject-connecting-rod-shorter-than-crank-radius", "reject-unit-compression-ratio", "reject-text-and-boolean-crank-angle-arrays"),
        ),
        ValidationCase(
            identifier="hydrogen-engine-boundary-schedule-contract",
            profile="hydrogen-engine",
            entrypoint=__name__ + ":validate_boundary_schedule",
            invariants=("schedule-source-and-units-required", "absolute-clock-support-retained", "linear-interpolation", "reject-extrapolation", "immutable-array-backing", "reject-mutated-schedule-metadata"),
        ),
        ValidationCase(
            identifier="hydrogen-engine-crank-schedule-conversion",
            profile="hydrogen-engine",
            entrypoint=__name__ + ":validate_crank_schedule_conversion",
            invariants=("constant-speed-crank-to-absolute-time-map", "time-origin-retained",
                        "schedule-support-matches-crank-window", "reject-nonmonotone-or-out-of-window-angle"),
        ),
        ValidationCase(
            identifier="hydrogen-engine-native-closed-charge",
            profile="hydrogen-engine",
            entrypoint=__name__ + ":validate_native_trace",
            parameters={"mechanism_yaml_path": "REPLACE_WITH_REVIEWED_MECHANISM_PATH"},
            invariants=("native-reacting-h2-charge", "closed-mass", "slider-crank-volume", "finite-pressure-work", "sampled-energy-residual-reported", "reject-forged-direct-trace-clocks-native-owners-and-summaries", "reject-cloned-trace-resealing", "reject-native-state-advanced-after-trace-issuance"),
        ),
        ValidationCase(
            identifier="hydrogen-engine-piston-heat-flux-schedule",
            profile="hydrogen-engine",
            entrypoint=__name__ + ":validate_piston_heat_flux",
            parameters={"mechanism_yaml_path": "REPLACE_WITH_REVIEWED_MECHANISM_PATH"},
            invariants=("caller-owned-absolute-time-heat-flux-schedule",
                        "native-moving-wall-applies-signed-flux-into-cylinder",
                        "piston-face-area-converts-flux-to-energy",
                        "heat-knots-retained-on-output-clock",
                        "first-law-residual-includes-prescribed-wall-energy",
                        "native-wall-terminal-heat-rate-remains-bound"),
        ),
        ValidationCase(
            identifier="hydrogen-engine-failure-prefix",
            profile="hydrogen-engine",
            entrypoint=__name__ + ":validate_failure_prefix",
            parameters={"mechanism_yaml_path": "REPLACE_WITH_REVIEWED_MECHANISM_PATH"},
            invariants=("retain-native-reactor-network-and-wall", "retain-completed-sample-prefix",
                        "report-failed-target-and-last-accepted-time", "preserve-original-cause"),
        ),
    )


def validate_geometry(*, work_directory, **parameters):
    del work_directory, parameters
    import numpy as np

    from h2physics.combustion import SliderCrank

    geometry = SliderCrank(.08, .10, .17, 10., 1200.)
    dead_centers = geometry.volume_m3(np.array([0., np.pi, 2*np.pi, 3*np.pi, 4*np.pi]))
    assert np.allclose(dead_centers[[0, 2, 4]], geometry.clearance_volume_m3)
    assert np.allclose(dead_centers[[1, 3]], geometry.clearance_volume_m3 + geometry.piston_area_m2*geometry.stroke_m)
    assert np.allclose(geometry.volume_rate_m3_s(np.array([0., np.pi, 2*np.pi])), 0.)
    return ValidationOutcome(True, {"clearance_volume_m3": geometry.clearance_volume_m3,
                                    "swept_volume_m3": geometry.piston_area_m2*geometry.stroke_m}, LIMITS)


def validate_input_admission(*, work_directory, **parameters):
    del work_directory, parameters
    from h2physics.combustion import SliderCrank

    invalid = 0
    for kwargs in (
        dict(bore_m=.08, stroke_m=.10, connecting_rod_m=.04, compression_ratio=10., speed_rpm=1200.),
        dict(bore_m=.08, stroke_m=.10, connecting_rod_m=.17, compression_ratio=1., speed_rpm=1200.),
    ):
        try:
            SliderCrank(**kwargs)
        except ValueError:
            invalid += 1
    assert invalid == 2
    geometry = SliderCrank(.08, .10, .17, 10., 1200.)
    rejected_angles = 0
    for angles in ("0", [True], [object()]):
        try:
            geometry.volume_m3(angles)
        except (TypeError, ValueError):
            rejected_angles += 1
    assert rejected_angles == 3
    return ValidationOutcome(True, {"rejected_invalid_geometries": invalid,
                                    "rejected_non_numeric_angle_arrays": rejected_angles}, LIMITS)


def validate_boundary_schedule(*, work_directory, **parameters):
    del work_directory, parameters
    from dataclasses import replace

    import numpy as np

    from h2physics.combustion import EngineBoundarySchedule

    schedule = EngineBoundarySchedule(
        quantity="intake_boundary_pressure", units="Pa", source_id="caller:engine-boundary-v1",
        clock_origin_s=100., time_s=np.array([100., 101., 103.]),
        values=np.array([1.0e5, 1.2e5, 1.4e5]),
    )
    assert schedule.support_s == (100., 103.)
    assert np.allclose(schedule.at(np.array([100., 102., 103.])), [1.0e5, 1.3e5, 1.4e5])
    rejected_write_enable = False
    try:
        schedule.values.setflags(write=True)
    except ValueError:
        rejected_write_enable = True
    assert rejected_write_enable
    assert schedule.require_current() is schedule
    original_source_id = schedule.source_id
    object.__setattr__(schedule, "source_id", "forged:engine-boundary")
    rejected_relabel = False
    try:
        schedule.require_current()
    except ValueError:
        rejected_relabel = True
    finally:
        object.__setattr__(schedule, "source_id", original_source_id)
    assert rejected_relabel and schedule.require_current() is schedule
    rejected = 0
    for changed in (
        {"source_id": ""},
        {"time_s": np.array([100., 100., 103.])},
        {"time_s": np.array([99., 101., 103.])},
        {"values": np.array([1.0e5, 1.2e5, np.nan])},
    ):
        try:
            replace(schedule, **changed)
        except ValueError:
            rejected += 1
    try:
        schedule.at(99.)
    except ValueError:
        rejected += 1
    assert rejected == 5
    return ValidationOutcome(True, {"schedule_support_s": schedule.support_s,
                                    "rejected_invalid_schedule_requests": rejected,
                                    "schedule_write_enable_rejected": rejected_write_enable,
                                    "schedule_relabel_rejected": rejected_relabel}, LIMITS)


def validate_crank_schedule_conversion(*, work_directory, **parameters):
    del work_directory, parameters
    import numpy as np

    from h2physics.combustion import SliderCrank, engine_schedule_from_crank_angle

    geometry = SliderCrank(.08, .10, .17, 10., 1200.)
    start = np.pi
    clock_origin = 2300.
    angles = np.array([start, start + np.pi / 2, start + np.pi])
    schedule = engine_schedule_from_crank_angle(
        quantity="intake_lift", units="m", source_id="caller:valve-lift-v2",
        clock_origin_s=clock_origin, crank_angle_rad=angles,
        values=np.array([0., .004, 0.]), geometry=geometry,
        crank_start_rad=start,
    )
    expected = clock_origin + (angles - start) / (2 * np.pi * geometry.speed_rpm / 60)
    assert np.array_equal(schedule.time_s, expected)
    assert schedule.clock_origin_s == clock_origin
    assert schedule.at(expected[1]) == .004
    rejected = 0
    for bad_angles in (np.array([start, start, start + 1.]),
                       np.array([start - .01, start + .5])):
        try:
            engine_schedule_from_crank_angle(
                quantity="valve_lift", units="m", source_id="caller:bad",
                clock_origin_s=clock_origin, crank_angle_rad=bad_angles,
                values=np.zeros(2 if len(bad_angles) == 2 else 3),
                geometry=geometry, crank_start_rad=start,
            )
        except ValueError:
            rejected += 1
    assert rejected == 2
    return ValidationOutcome(True, {"absolute_schedule_support_s": schedule.support_s,
                                    "rejected_invalid_angle_schedules": rejected}, LIMITS)


def validate_native_trace(*, work_directory, **parameters):
    del work_directory
    from dataclasses import replace
    from hashlib import sha256
    from pathlib import Path

    import cantera as ct
    import numpy as np

    from h2physics.adapters.cantera import MechanismBasis, ReactiveState
    from h2physics.combustion import SliderCrank, run_closed_charge_engine_segment

    required = ("mechanism_yaml_path", "phase_name", "license_id", "source_reference",
                "minimum_temperature_k", "maximum_temperature_k", "minimum_pressure_pa",
                "maximum_pressure_pa")
    missing = [name for name in required if name not in parameters]
    if missing:
        raise ValueError("Nurion case requires reviewed mechanism metadata: " + ", ".join(missing))
    raw = Path(parameters["mechanism_yaml_path"]).read_bytes()
    source_hash = sha256(raw).hexdigest()
    phase_name = str(parameters["phase_name"])
    basis = MechanismBasis(
        identifier=f"nurion-engine:{phase_name}", source_sha256=source_hash,
        license_id=str(parameters["license_id"]), references=(str(parameters["source_reference"]),),
        minimum_temperature_k=float(parameters["minimum_temperature_k"]),
        maximum_temperature_k=float(parameters["maximum_temperature_k"]),
        minimum_pressure_pa=float(parameters["minimum_pressure_pa"]),
        maximum_pressure_pa=float(parameters["maximum_pressure_pa"]),
    )
    def factory():
        return ct.Solution(yaml=raw.decode("utf-8"), name=phase_name)

    initial = ReactiveState(800., 3e6, {"H2": .30, "O2": .15, "N2": .55})
    geometry = SliderCrank(.08, .10, .17, 10., 1200.)
    trace = run_closed_charge_engine_segment(
        factory, basis, initial, geometry,
        crank_start_rad=float(parameters.get("crank_start_rad", np.pi)),
        crank_end_rad=float(parameters.get("crank_end_rad", 2*np.pi)),
        samples_per_revolution=int(parameters.get("samples_per_revolution", 720)),
    )
    assert trace.require_current() is trace
    assert np.all(np.isfinite(trace.pressure_pa)) and np.all(trace.pressure_pa > 0)
    assert np.allclose(trace.mass_kg, trace.mass_kg[0], rtol=1e-8, atol=1e-12)
    assert np.allclose(trace.volume_m3, geometry.volume_m3(trace.crank_angle_rad), rtol=1e-9, atol=1e-12)
    assert np.isfinite(trace.indicated_boundary_work_j)
    assert np.isfinite(trace.first_law_residual_j)
    rejected_receipts = 0
    reversed_time = trace.time_s.copy()
    reversed_time[1] = reversed_time[0]
    duplicate_species = (trace.species_names[0],) * len(trace.species_names)
    for changes in ({"time_s": reversed_time}, {"species_names": duplicate_species},
                    {"native_network": object()},
                    {"indicated_boundary_work_j": trace.indicated_boundary_work_j + 1.},
                    {"first_law_residual_j": trace.first_law_residual_j + 1.}):
        try:
            replace(trace, **changes)
        except (TypeError, ValueError):
            rejected_receipts += 1
    try:
        replace(trace)
    except TypeError:
        rejected_receipts += 1
    else:
        raise AssertionError("A copied native engine trace reused its consumed run issuer")
    assert rejected_receipts == 6
    return ValidationOutcome(True, {
        "samples": len(trace.time_s),
        "initial_pressure_pa": float(trace.pressure_pa[0]),
        "final_pressure_pa": float(trace.pressure_pa[-1]),
        "indicated_boundary_work_j": trace.indicated_boundary_work_j,
        "sampled_first_law_residual_j": trace.first_law_residual_j,
        "rejected_forged_direct_traces": rejected_receipts,
    }, LIMITS)


def validate_failure_prefix(*, work_directory, **parameters):
    del work_directory
    from hashlib import sha256
    from pathlib import Path
    from unittest.mock import patch

    import cantera as ct
    import numpy as np

    from h2physics.adapters.cantera import MechanismBasis, ReactiveState
    from h2physics.combustion import (
        ClosedChargeEngineError,
        SliderCrank,
        run_closed_charge_engine_segment,
    )
    from h2physics.combustion import closed_charge_engine as engine_module

    required = ("mechanism_yaml_path", "phase_name", "license_id", "source_reference",
                "minimum_temperature_k", "maximum_temperature_k", "minimum_pressure_pa",
                "maximum_pressure_pa")
    missing = [name for name in required if name not in parameters]
    if missing:
        raise ValueError("Nurion case requires reviewed mechanism metadata: " + ", ".join(missing))
    raw = Path(parameters["mechanism_yaml_path"]).read_bytes()
    phase_name = str(parameters["phase_name"])
    basis = MechanismBasis(
        identifier=f"nurion-engine-failure:{phase_name}", source_sha256=sha256(raw).hexdigest(),
        license_id=str(parameters["license_id"]), references=(str(parameters["source_reference"]),),
        minimum_temperature_k=float(parameters["minimum_temperature_k"]),
        maximum_temperature_k=float(parameters["maximum_temperature_k"]),
        minimum_pressure_pa=float(parameters["minimum_pressure_pa"]),
        maximum_pressure_pa=float(parameters["maximum_pressure_pa"]),
    )

    def factory():
        return ct.Solution(yaml=raw.decode("utf-8"), name=phase_name)

    initial = ReactiveState(800., 3e6, {"H2": .30, "O2": .15, "N2": .55})
    geometry = SliderCrank(.08, .10, .17, 10., 1200.)
    original_advance = engine_module._advance_native
    calls = 0
    injected = RuntimeError("synthetic failure after accepted samples")

    def fail_on_third_advance(network, target_s):
        nonlocal calls
        calls += 1
        if calls == 3:
            raise injected
        return original_advance(network, target_s)

    try:
        with patch.object(engine_module, "_advance_native", fail_on_third_advance):
            run_closed_charge_engine_segment(
                factory, basis, initial, geometry,
                crank_start_rad=float(parameters.get("crank_start_rad", np.pi)),
                crank_end_rad=float(parameters.get("crank_end_rad", 2*np.pi)),
                samples_per_revolution=int(parameters.get("samples_per_revolution", 720)),
            )
    except ClosedChargeEngineError as error:
        assert error.cause is injected and error.__cause__ is injected
        assert isinstance(error.native_reactor, ct.IdealGasReactor)
        assert isinstance(error.native_network, ct.ReactorNet)
        assert error.native_wall is not None
        assert len(error.accepted_time_s) == len(error.accepted_states) >= 2
        assert error.last_accepted_time_s == error.accepted_time_s[-1]
        assert error.failed_target_s > error.last_accepted_time_s
        assert np.all(np.diff(error.accepted_time_s) > 0.)
        assert np.all(np.diff(error.accepted_crank_angle_rad) > 0.)
        return ValidationOutcome(True, {
            "accepted_samples_before_failure": len(error.accepted_time_s),
            "last_accepted_time_s": error.last_accepted_time_s,
            "failed_target_time_s": error.failed_target_s,
            "cause_retained": True,
        }, LIMITS)
    raise AssertionError("Expected the injected native advance failure to retain its accepted prefix")


def validate_piston_heat_flux(*, work_directory, **parameters):
    del work_directory
    from hashlib import sha256
    from pathlib import Path

    import cantera as ct
    import numpy as np

    from h2physics.adapters.cantera import MechanismBasis, ReactiveState
    from h2physics.combustion import (
        EngineBoundarySchedule,
        SliderCrank,
        run_closed_charge_engine_segment,
    )

    required = ("mechanism_yaml_path", "phase_name", "license_id", "source_reference",
                "minimum_temperature_k", "maximum_temperature_k", "minimum_pressure_pa",
                "maximum_pressure_pa")
    missing = [name for name in required if name not in parameters]
    if missing:
        raise ValueError("Piston heat case requires reviewed mechanism metadata: " + ", ".join(missing))
    raw = Path(parameters["mechanism_yaml_path"]).read_bytes()
    phase_name = str(parameters["phase_name"])
    basis = MechanismBasis(
        identifier=f"nurion-engine-piston-heat:{phase_name}", source_sha256=sha256(raw).hexdigest(),
        license_id=str(parameters["license_id"]), references=(str(parameters["source_reference"]),),
        minimum_temperature_k=float(parameters["minimum_temperature_k"]),
        maximum_temperature_k=float(parameters["maximum_temperature_k"]),
        minimum_pressure_pa=float(parameters["minimum_pressure_pa"]),
        maximum_pressure_pa=float(parameters["maximum_pressure_pa"]),
    )

    def factory():
        return ct.Solution(yaml=raw.decode("utf-8"), name=phase_name)

    geometry = SliderCrank(.08, .10, .17, 10., 1200.)
    start, end, origin = np.pi, np.pi + np.pi/4, 500.
    duration = (end-start)/(2*np.pi*geometry.speed_rpm/60)
    schedule_times = origin + np.linspace(0., duration, 4)
    flux = np.array([0., 250., 600., 100.])
    schedule = EngineBoundarySchedule(
        "heat_flux", "W/m2", "synthetic:caller-piston-heat-flux-v1",
        origin, schedule_times, flux,
    )
    trace = run_closed_charge_engine_segment(
        factory, basis, ReactiveState(800., 3.e6, {"H2": .30, "O2": .15, "N2": .55}),
        geometry, crank_start_rad=start, crank_end_rad=end,
        piston_heat_flux_schedule=schedule,
        samples_per_revolution=int(parameters.get("samples_per_revolution", 720)),
    )
    assert trace.require_current() is trace
    expected_heat = geometry.piston_area_m2 * float(np.trapz(flux, schedule_times-origin))
    assert trace.piston_heat_flux_schedule is schedule
    assert trace.piston_heat_area_m2 == geometry.piston_area_m2
    assert trace.piston_heat_input_j[0] == 0.
    assert np.isclose(trace.piston_heat_input_j[-1], expected_heat, rtol=1e-12, atol=1e-12)
    assert np.any(np.isclose(trace.time_s, schedule_times[1]-origin, rtol=0., atol=1e-15))
    assert np.isclose(trace.first_law_residual_j,
        trace.internal_energy_j[-1]-trace.internal_energy_j[0]
        + trace.indicated_boundary_work_j-trace.piston_heat_input_j[-1],
        rtol=1e-12, atol=1e-12)
    return ValidationOutcome(True, {
        "piston_heat_input_j": float(trace.piston_heat_input_j[-1]),
        "piston_face_area_m2": geometry.piston_area_m2,
        "samples_with_heat_knots": len(trace.time_s),
        "sampled_first_law_residual_j": trace.first_law_residual_j,
    }, LIMITS)
