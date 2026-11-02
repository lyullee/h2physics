"""Deferred native contracts for prescribed-flow open-cylinder segments."""

from h2physics.cluster_validation import ValidationCase, ValidationOutcome

LIMITS = (
    "Cantera 3.2 owns reacting ideal-gas states and ReactorNet integration.",
    "Inlets have fixed caller-declared states; their mass rates are scheduled.",
    "Outlets withdraw the instantaneous well-mixed cylinder composition at a prescribed rate.",
    "Optional pressure valves use Cantera's one-way linear pressure-drop law with caller-owned coefficients and opening schedules.",
    "Valve coefficients are not discharge coefficients and imply no compressible-nozzle calibration.",
    "Crank-angle fuel feed is a fixed-state prescribed mass rate, not injector/nozzle/spray physics.",
    "Shared-nozzle inlets retain the existing isentropic/choking gates and use native Cantera only as the MFC adapter.",
    "No nozzle thrust, jet momentum deposition, injector, spray or complete-cycle closure is represented.",
    "No spark, full-cycle closure or experimental qualification is implied.",
)

# The execution host resolves the Cantera-provided mechanism path locally. These
# metadata identify the documented phase and declared computational envelope;
# the license label deliberately does not assert upstream mechanism terms.
_ENGINE_MECHANISM_METADATA = {
    # Resolve the installed Cantera resource on each host instead of embedding
    # or redistributing its mechanism file with this project.
    "mechanism_yaml_path": "h2o2.yaml",
    "phase_name": "ohmech",
    "license_id": "Cantera-distributed h2o2.yaml; upstream mechanism terms not asserted",
    "source_reference": "https://www.cantera.org/3.2/examples/input/h2o2.html",
    "minimum_temperature_k": 200.0,
    "maximum_temperature_k": 3500.0,
    "minimum_pressure_pa": 1.0e4,
    "maximum_pressure_pa": 1.0e8,
}


def cases():
    return (
        ValidationCase(
            identifier="hydrogen-engine-open-control-volume-forced-flow",
            profile="hydrogen-engine",
            entrypoint=__name__ + ":validate_open_cylinder",
            parameters=dict(_ENGINE_MECHANISM_METADATA),
            invariants=("native-moving-volume-reactor", "fixed-source-bound-inlet-states",
                        "scheduled-nonnegative-feed-and-exhaust-rates", "species-resolved-native-inlet-transfer",
                        "native-pressure-responsive-one-way-valve-boundary",
                        "bulk-exhaust-removes-current-cylinder-composition", "retained-mass-and-energy-diagnostics",
                        "reject-forged-trace-and-mutated-source", "failure-prefix-retains-native-owners"),
        ),
        ValidationCase(
            identifier="hydrogen-engine-native-pressure-valve-boundary",
            profile="hydrogen-engine",
            entrypoint=__name__ + ":validate_open_cylinder",
            parameters=dict(_ENGINE_MECHANISM_METADATA),
            invariants=("cantera-native-valve-device", "caller-evidence-tagged-valve-coefficient",
                        "bounded-source-opening-schedule", "forward-flow-only-pressure-response",
                        "outlet-current-mixture-composition", "native-device-retained-in-trace"),
        ),
        ValidationCase(
            identifier="hydrogen-engine-crank-angle-fuel-delivery-native-flow",
            profile="hydrogen-engine",
            entrypoint=__name__ + ":validate_open_cylinder",
            parameters=dict(_ENGINE_MECHANISM_METADATA),
            invariants=("crank-angle-flow-map-uses-declared-constant-speed-geometry",
                        "fuel-feed-is-native-reservoir-mass-flow-controller",
                        "species-source-ledger-retains-fuel-composition",
                        "mass-and-energy-diagnostics-remain-requested-sample-level",
                        "fuel-delivery-is-not-represented-as-injector-physics"),
        ),
        ValidationCase(
            identifier="hydrogen-engine-open-cylinder-shared-nozzle-inlet",
            profile="hydrogen-engine",
            entrypoint=__name__ + ":validate_shared_nozzle_inlet",
            parameters=dict(_ENGINE_MECHANISM_METADATA),
            invariants=("shared-homogeneous-isentropic-nozzle-drives-source-flow",
                        "live-native-cylinder-pressure-is-nozzle-backpressure",
                        "native-mass-flow-controller-only-adapts-nozzle-rate",
                        "choked-subcritical-and-no-forward-pressure-regimes-retained",
                        "source-mass-species-and-stagnation-enthalpy-ledgers-retained",
                        "native-nozzle-results-bound-to-accepted-cylinder-pressure",
                        "failure-prefix-retains-nozzle-boundary-owners"),
        ),
    )


def validate_open_cylinder(*, work_directory, **parameters):
    del work_directory
    from dataclasses import replace
    from hashlib import sha256
    from pathlib import Path

    import cantera as ct
    import numpy as np

    from h2physics.adapters.cantera import MechanismBasis, ReactiveState
    from h2physics.combustion import (
        EngineBoundarySchedule,
        OpenCylinderInlet,
        OpenCylinderBoundary,
        OpenCylinderOutlet,
        OpenCylinderValveOutlet,
        SliderCrank,
        open_cylinder_inlet_from_crank_angle,
        run_open_cylinder_segment,
    )

    required = ("mechanism_yaml_path", "phase_name", "license_id", "source_reference",
                "minimum_temperature_k", "maximum_temperature_k", "minimum_pressure_pa",
                "maximum_pressure_pa")
    missing = [name for name in required if name not in parameters]
    if missing:
        raise ValueError("Native engine case requires reviewed mechanism metadata: " + ", ".join(missing))
    mechanism_path = Path(parameters["mechanism_yaml_path"])
    if not mechanism_path.is_file() and not mechanism_path.is_absolute():
        mechanism_path = next((Path(directory) / mechanism_path
                               for directory in ct.get_data_directories()
                               if (Path(directory) / mechanism_path).is_file()), mechanism_path)
    if not mechanism_path.is_file():
        raise FileNotFoundError(
            f"Cantera mechanism resource {parameters['mechanism_yaml_path']!r} "
            "was not found in the configured Cantera data directories"
        )
    raw = mechanism_path.read_bytes()
    digest = sha256(raw).hexdigest()
    phase_name = str(parameters["phase_name"])
    basis = MechanismBasis(
        identifier=f"nurion-open-engine:{phase_name}", source_sha256=digest,
        license_id=str(parameters["license_id"]), references=(str(parameters["source_reference"]),),
        minimum_temperature_k=float(parameters["minimum_temperature_k"]),
        maximum_temperature_k=float(parameters["maximum_temperature_k"]),
        minimum_pressure_pa=float(parameters["minimum_pressure_pa"]),
        maximum_pressure_pa=float(parameters["maximum_pressure_pa"]),
    )

    def factory():
        return ct.Solution(yaml=raw.decode("utf-8"), name=phase_name)

    origin = 100.
    geometry = SliderCrank(.08, .10, .17, 10., 1200.)
    start, end = np.pi, np.pi + np.pi / 4
    omega = 2 * np.pi * geometry.speed_rpm / 60
    stop = origin + (end - start) / omega
    schedule_times = np.array([origin, origin + (stop-origin)/3,
                               origin + 2*(stop-origin)/3, stop])

    def flow_schedule(identifier, values):
        return EngineBoundarySchedule(
            quantity="mass_flow", units="kg/s", source_id=f"caller:{identifier}:v1",
            clock_origin_s=origin, time_s=schedule_times, values=np.asarray(values, dtype=float),
        )

    def opening_schedule(identifier, values):
        return EngineBoundarySchedule(
            quantity="valve_open_fraction", units="1", source_id=f"caller:{identifier}:v1",
            clock_origin_s=origin, time_s=schedule_times, values=np.asarray(values, dtype=float),
        )

    initial = ReactiveState(900., 1.2e6, {"H2": .25, "O2": .18, "N2": .57})
    hydrogen_feed = open_cylinder_inlet_from_crank_angle(
        identifier="hydrogen-feed", state=ReactiveState(350., 2e5, {"H2": 1.}),
        crank_angle_rad=start + omega*(schedule_times-origin),
        mass_flow_kg_s=[.001, .002, .0015, .001], geometry=geometry,
        crank_start_rad=start, absolute_clock_origin_s=origin,
        schedule_source_id="caller:engine-hydrogen-flow-v1",
        source_reference="caller:engine-h2-feed-v1",
        enthalpy_reference="mechanism:declared-native-reference-v1",
    )
    oxidizer_feed = OpenCylinderInlet(
        identifier="oxidizer-feed", state=ReactiveState(350., 2e5, {"O2": .21, "N2": .79}),
        mass_flow=flow_schedule("oxidizer-flow", [.008, .009, .009, .008]),
        source_reference="caller:engine-oxidizer-feed-v1", enthalpy_reference="mechanism:declared-native-reference-v1",
    )
    exhaust = OpenCylinderOutlet(
        identifier="prescribed-exhaust", mass_flow=flow_schedule("exhaust-flow", [.004, .006, .008, .009]),
        source_reference="caller:engine-exhaust-rate-v1",
    )
    pressure_exhaust = OpenCylinderValveOutlet(
        identifier="pressure-responsive-exhaust",
        opening=opening_schedule("exhaust-opening", [0., .35, .8, 1.]),
        coefficient_kg_s_pa=1.e-9,
        coefficient_reference="synthetic-caller:linear-valve-coefficient-v1",
        source_reference="synthetic-caller:valve-port-pressure-order-v1",
    )
    boundary = OpenCylinderBoundary((hydrogen_feed, oxidizer_feed), (exhaust,),
                                    valve_outlets=(pressure_exhaust,))
    trace = run_open_cylinder_segment(
        factory, basis, initial, geometry, boundary,
        absolute_clock_origin_s=origin, crank_start_rad=start, crank_end_rad=end,
        samples_per_revolution=int(parameters.get("samples_per_revolution", 720)),
    )
    assert trace.require_current() is trace
    assert np.allclose(hydrogen_feed.mass_flow.time_s, schedule_times, rtol=1e-12, atol=1e-12)
    assert np.array_equal(hydrogen_feed.mass_flow.values, [.001, .002, .0015, .001])
    assert type(trace.native_flow_devices[0]).__name__ == "MassFlowController"
    h2_index = trace.species_names.index("H2")
    assert abs(trace.species_transfer_kg[-1, h2_index]) > 0.
    assert np.allclose(trace.volume_m3, geometry.volume_m3(trace.crank_angle_rad), rtol=1e-9, atol=1e-12)
    assert trace.mass_fractions.shape == (len(trace.time_s), len(trace.species_names))
    assert trace.species_transfer_kg.shape == trace.mass_fractions.shape
    assert np.all(np.isfinite(trace.mass_balance_residual_kg))
    assert np.all(np.isfinite(trace.sampled_first_law_residual_j))
    assert len(trace.native_flow_devices) == 4
    assert type(trace.native_flow_devices[-1]).__name__ == "Valve"

    rejected = 0
    try:
        trace.time_s.setflags(write=True)
    except ValueError:
        rejected += 1
    object.__setattr__(hydrogen_feed.mass_flow, "source_id", "forged:source")
    try:
        try:
            trace.require_current()
        except ValueError:
            rejected += 1
    finally:
        object.__setattr__(hydrogen_feed.mass_flow, "source_id", f"caller:hydrogen-flow:v1")
    assert rejected == 2
    try:
        replace(trace)
    except TypeError:
        rejected += 1
    assert rejected == 3
    return ValidationOutcome(
        True,
        {"sample_count": len(trace.time_s), "initial_mass_kg": trace.mass_kg[0],
         "final_mass_kg": trace.mass_kg[-1],
         "maximum_abs_mass_residual_kg": float(np.max(np.abs(trace.mass_balance_residual_kg))),
         "maximum_abs_sampled_energy_residual_j": float(np.max(np.abs(trace.sampled_first_law_residual_j))),
         "rejected_mutation_or_clone_paths": rejected},
        LIMITS,
    )


def validate_shared_nozzle_inlet(*, work_directory, **parameters):
    del work_directory
    from hashlib import sha256
    from pathlib import Path

    import cantera as ct
    import numpy as np

    from h2physics.adapters.cantera import MechanismBasis, ReactiveState
    from h2physics.adapters.cantera_properties import CanteraFrozenGasProperties
    from h2physics.combustion import (
        EngineBoundarySchedule,
        OpenCylinderBoundary,
        OpenCylinderNozzleInlet,
        SliderCrank,
        run_open_cylinder_segment,
    )
    from h2physics.release import HomogeneousIsentropicNozzle, NozzleOpening

    required = ("mechanism_yaml_path", "phase_name", "license_id", "source_reference",
                "minimum_temperature_k", "maximum_temperature_k", "minimum_pressure_pa",
                "maximum_pressure_pa")
    missing = [name for name in required if name not in parameters]
    if missing:
        raise ValueError("Shared-nozzle case requires reviewed mechanism metadata: "
                         + ", ".join(missing))
    mechanism_path = Path(parameters["mechanism_yaml_path"])
    if not mechanism_path.is_file() and not mechanism_path.is_absolute():
        mechanism_path = next((Path(directory) / mechanism_path
                               for directory in ct.get_data_directories()
                               if (Path(directory) / mechanism_path).is_file()), mechanism_path)
    if not mechanism_path.is_file():
        raise FileNotFoundError(
            f"Cantera mechanism resource {parameters['mechanism_yaml_path']!r} "
            "was not found in the configured Cantera data directories"
        )
    raw = mechanism_path.read_bytes()
    phase_name = str(parameters["phase_name"])
    basis = MechanismBasis(
        identifier=f"nurion-engine-shared-nozzle:{phase_name}",
        source_sha256=sha256(raw).hexdigest(), license_id=str(parameters["license_id"]),
        references=(str(parameters["source_reference"]),),
        minimum_temperature_k=float(parameters["minimum_temperature_k"]),
        maximum_temperature_k=float(parameters["maximum_temperature_k"]),
        minimum_pressure_pa=float(parameters["minimum_pressure_pa"]),
        maximum_pressure_pa=float(parameters["maximum_pressure_pa"]),
    )

    def factory():
        return ct.Solution(yaml=raw.decode("utf-8"), name=phase_name)

    source_state = ReactiveState(350., 5.e6, {"H2": 1.})
    property_phase = factory()
    property_phase.TPX = source_state.temperature_k, source_state.pressure_pa, dict(source_state.mole_fractions)
    properties = CanteraFrozenGasProperties(property_phase, basis, {"H2": 1.})
    nozzle = HomogeneousIsentropicNozzle(properties)
    opening = NozzleOpening.circular(
        "synthetic:engine-nozzle-port", .002,
        effective_area_factor=.8, area_basis_id="synthetic:effective-port-area-v1",
    )
    upstream = properties.state_pt(source_state.pressure_pa, source_state.temperature_k)
    choked = nozzle.solve(upstream, back_pressure_pa=.5*source_state.pressure_pa, opening=opening)
    subcritical = nozzle.solve(upstream, back_pressure_pa=.8*source_state.pressure_pa, opening=opening)
    no_forward = nozzle.solve(upstream, back_pressure_pa=1.1*source_state.pressure_pa, opening=opening)
    assert choked.regime == "choked"
    assert subcritical.regime == "back_pressure_limited"
    assert no_forward.regime == "no_forward_pressure"

    geometry = SliderCrank(.08, .10, .17, 10., 1200.)
    origin, start, end = 1000., np.pi, np.pi + np.pi/12
    duration = (end-start)/(2*np.pi*geometry.speed_rpm/60)
    schedule_times = origin + np.linspace(0., duration, 4)
    opening_schedule = EngineBoundarySchedule(
        "nozzle_open_fraction", "1", "synthetic:engine-nozzle-opening-v1",
        origin, schedule_times, np.ones(4),
    )
    feed = OpenCylinderNozzleInlet(
        identifier="shared-nozzle-hydrogen-inlet", state=source_state,
        nozzle=nozzle, opening=opening, opening_schedule=opening_schedule,
        source_reference="synthetic:fixed-hydrogen-reservoir-v1",
        enthalpy_reference="mechanism:declared-native-reference-v1",
    )
    trace = run_open_cylinder_segment(
        factory, basis,
        ReactiveState(900., 1.2e6, {"H2": .25, "O2": .18, "N2": .57}),
        geometry, OpenCylinderBoundary((), (), nozzle_inlets=(feed,)),
        absolute_clock_origin_s=origin, crank_start_rad=start, crank_end_rad=end,
        samples_per_revolution=36,
    )
    assert trace.require_current() is trace
    assert len(trace.nozzle_results) == len(trace.time_s)
    assert type(trace.native_flow_devices[0]).__name__ == "MassFlowController"
    assert all(row[0].regime in {"choked", "back_pressure_limited", "closed", "no_forward_pressure"}
               for row in trace.nozzle_results)
    assert all(np.isclose(row[0].back_pressure_pa, pressure, rtol=1e-12, atol=1e-8)
               for row, pressure in zip(trace.nozzle_results, trace.pressure_pa, strict=True))
    assert all(row[0].mass_flow_kg_s >= 0. for row in trace.nozzle_results)
    assert trace.nozzle_results[0][0].mass_flow_kg_s > 0.
    assert abs(trace.inlet_enthalpy_transfer_j[-1]) > 0.
    h2_index = trace.species_names.index("H2")
    assert trace.species_transfer_kg[-1, h2_index] > 0.
    return ValidationOutcome(True, {
        "accepted_samples": len(trace.time_s),
        "initial_nozzle_flow_kg_s": trace.nozzle_results[0][0].mass_flow_kg_s,
        "final_nozzle_regime": trace.nozzle_results[-1][0].regime,
        "native_inlet_enthalpy_j": float(trace.inlet_enthalpy_transfer_j[-1]),
        "shared_nozzle_regimes": (choked.regime, subcritical.regime, no_forward.regime),
    }, LIMITS)
