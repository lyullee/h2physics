"""Deferred native checks for finite wall coupling on a moving cylinder."""

from hashlib import sha256
from pathlib import Path

from h2physics.cluster_validation import ValidationCase, ValidationOutcome

LIMITS = (
    "Cantera 3.2 owns reacting gas, moving-volume, flow-device and ReactorNet equations.",
    "Wall UA, capacity and external heat are synthetic caller inputs in these contract cases.",
    "The wall is one lumped state; no cylinder-wall correlation or engine qualification is inferred.",
)


def cases():
    parameters = {
        # Use the mechanism supplied by the separately installed Cantera package.
        # Do not copy or redistribute its YAML into this repository.
        "mechanism_yaml_path": "h2o2.yaml",
        "phase_name": "ohmech",
        "license_id": "Cantera-distributed h2o2.yaml; upstream mechanism terms not asserted",
        "source_reference": "https://www.cantera.org/3.2/examples/input/h2o2.html",
        "minimum_temperature_k": 200.0,
        "maximum_temperature_k": 3500.0,
        "minimum_pressure_pa": 1.0e4,
        "maximum_pressure_pa": 1.0e8,
        # The accepted closure diagnostic is established on the execution host
        # by a documented 3-grid refinement probe, not a guessed joule budget.
        "samples_per_revolution": 144,
    }
    return (
        ValidationCase(
            identifier="hydrogen-engine-wall-gas-coupling-energy-ledger",
            profile="hydrogen-engine",
            entrypoint=__name__ + ":validate_wall_energy",
            parameters=parameters,
            invariants=("native-reactor-wall-temperature-state",
                        "equal-and-opposite-gas-wall-transfer",
                        "total-gas-wall-boundary-energy-closure",
                        "trace-currentness-retains-wall-inputs",
                        "sampled-energy-residual-refines-at-72-144-288"),
        ),
        ValidationCase(
            identifier="hydrogen-engine-wall-zero-UA-reduction",
            profile="hydrogen-engine",
            entrypoint=__name__ + ":validate_zero_ua",
            parameters=parameters,
            invariants=("zero-UA-wall-does-not-perturb-cylinder-gas-history",
                        "finite-wall-state-remains-at-initial-temperature"),
        ),
        ValidationCase(
            identifier="hydrogen-engine-wall-external-boundary-ledger",
            profile="hydrogen-engine",
            entrypoint=__name__ + ":validate_external_boundary",
            parameters=parameters,
            invariants=("signed-external-wall-heat-is-integrated-by-native-state",
                        "external-heat-enters-combined-system-energy-once",
                        "gas-wall-transfer-cancels-in-combined-ledger",
                        "callback-closure-mutation-invalidates-wall-trace",
                        "sampled-energy-residual-refines-at-72-144-288"),
        ),
    )


def _run_arguments(parameters, *, wall, external_heat=None):
    import cantera as ct
    import numpy as np

    from h2physics.adapters.cantera import MechanismBasis, ReactiveState
    from h2physics.combustion import (
        CylinderWallThermal,
        EngineBoundarySchedule,
        OpenCylinderBoundary,
        OpenCylinderInlet,
        OpenCylinderOutlet,
        SliderCrank,
    )

    required = ("mechanism_yaml_path", "license_id", "source_reference",
                "minimum_temperature_k", "maximum_temperature_k",
                "minimum_pressure_pa", "maximum_pressure_pa")
    missing = [name for name in required if name not in parameters]
    if missing:
        raise ValueError("Native cylinder-wall case requires reviewed mechanism metadata: "
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
    phase_name = str(parameters.get("phase_name", "ohmech"))
    basis = MechanismBasis(
        identifier=f"nurion-cylinder-wall:{phase_name}", source_sha256=sha256(raw).hexdigest(),
        license_id=str(parameters["license_id"]), references=(str(parameters["source_reference"]),),
        minimum_temperature_k=float(parameters["minimum_temperature_k"]),
        maximum_temperature_k=float(parameters["maximum_temperature_k"]),
        minimum_pressure_pa=float(parameters["minimum_pressure_pa"]),
        maximum_pressure_pa=float(parameters["maximum_pressure_pa"]),
    )

    def phase_factory():
        return ct.Solution(yaml=raw.decode("utf-8"), name=phase_name)

    origin = 100.
    geometry = SliderCrank(.08, .10, .17, 10., 1200.)
    crank_start, crank_end = np.pi, np.pi + np.pi / 4
    omega = 2 * np.pi * geometry.speed_rpm / 60
    end_time = origin + (crank_end-crank_start)/omega
    times = np.linspace(origin, end_time, 4)

    def schedule(identifier, values):
        return EngineBoundarySchedule("mass_flow", "kg/s", f"synthetic:{identifier}",
            origin, times, np.asarray(values, dtype=float))

    feed_h2 = OpenCylinderInlet("wall-case-h2",
        ReactiveState(350., 2.e5, {"H2": 1.}),
        schedule("wall-h2-feed", (.001, .0012, .0011, .001)),
        "synthetic:wall-h2-feed", "mechanism:wall-case-reference")
    feed_air = OpenCylinderInlet("wall-case-air",
        ReactiveState(350., 2.e5, {"O2": .21, "N2": .79}),
        schedule("wall-air-feed", (.006, .0065, .0062, .006)),
        "synthetic:wall-air-feed", "mechanism:wall-case-reference")
    exhaust = OpenCylinderOutlet("wall-case-exhaust",
        schedule("wall-exhaust", (.002, .003, .004, .005)), "synthetic:wall-exhaust")
    boundary = OpenCylinderBoundary((feed_h2, feed_air), (exhaust,))
    wall_model = None
    if wall:
        wall_model = CylinderWallThermal(
            heat_capacity_j_k=1200., reference_temperature_k=298.15,
            initial_temperature_k=500., conductance_ua_w_k=150.,
            energy_reference_id="mechanism:wall-case-reference",
            property_evidence_id="synthetic:wall-capacity",
            boundary_evidence_id="synthetic:wall-external-boundary",
            external_heat_into_wall=external_heat,
        )
    return dict(
        phase_factory=phase_factory, mechanism_basis=basis,
        initial=ReactiveState(900., 1.2e6, {"H2": .25, "O2": .18, "N2": .57}),
        geometry=geometry, boundary=boundary,
        absolute_clock_origin_s=origin, crank_start_rad=crank_start,
        crank_end_rad=crank_end,
        samples_per_revolution=int(parameters.get("samples_per_revolution", 144)),
        wall_thermal=wall_model,
    )


def validate_wall_energy(*, work_directory, **parameters):
    del work_directory
    import numpy as np

    from h2physics.combustion import run_open_cylinder_segment

    trace = run_open_cylinder_segment(**_run_arguments(parameters, wall=True))
    trace.require_current()
    assert trace.wall_thermal is not None
    assert np.any(np.abs(trace.wall_temperature_k-trace.wall_temperature_k[0]) > 1e-9)
    assert np.allclose(np.diff(trace.wall_internal_energy_j),
        -np.diff(trace.gas_wall_heat_into_gas_j)+np.diff(trace.wall_boundary_heat_j),
        rtol=1e-8, atol=1e-7)
    refinement = _refinement_probe(parameters, wall=True)
    maximum = refinement[-1]
    return ValidationOutcome(True, {"wall_temperature_change_k":
        float(trace.wall_temperature_k[-1]-trace.wall_temperature_k[0]),
        "max_combined_energy_residual_j": maximum,
        "refinement_residuals_j": refinement,
        "refinement_tolerance_candidate_j": maximum,
        "refinement_contract": "finite, strictly decreasing residual at 72/144/288 samples per revolution"}, LIMITS)


def validate_zero_ua(*, work_directory, **parameters):
    del work_directory
    import numpy as np

    from dataclasses import replace
    from h2physics.combustion import CylinderWallThermal, run_open_cylinder_segment

    with_wall = _run_arguments(parameters, wall=True)
    wall_model = replace(with_wall["wall_thermal"], conductance_ua_w_k=0.,
                         external_heat_into_wall=None)
    with_wall["wall_thermal"] = wall_model
    without_wall = _run_arguments(parameters, wall=False)
    first = run_open_cylinder_segment(**with_wall)
    second = run_open_cylinder_segment(**without_wall)
    assert isinstance(first.wall_thermal, CylinderWallThermal)
    assert np.array_equal(first.time_s, second.time_s)
    for name in ("pressure_pa", "temperature_k", "mass_kg", "internal_energy_j", "mass_fractions"):
        a, b = getattr(first, name), getattr(second, name)
        assert np.allclose(a, b, rtol=1e-7, atol=1e-8), name
    assert np.allclose(first.wall_temperature_k, wall_model.initial_temperature_k)
    return ValidationOutcome(True, {"gas_history_max_difference": max(
        float(np.max(np.abs(getattr(first, name)-getattr(second, name))))
        for name in ("pressure_pa", "temperature_k", "mass_kg", "internal_energy_j"))}, LIMITS)


def validate_external_boundary(*, work_directory, **parameters):
    del work_directory
    import numpy as np

    from h2physics.combustion import run_open_cylinder_segment

    callback_state = {"heat_w": -75.}

    def external_heat(time_s, gas_k, wall_k):
        return callback_state["heat_w"]

    trace = run_open_cylinder_segment(**_run_arguments(
        parameters, wall=True, external_heat=external_heat))
    trace.require_current()
    boundary = trace.wall_boundary_heat_j
    assert boundary[-1] < 0.
    assert np.allclose(np.diff(trace.wall_internal_energy_j),
        -np.diff(trace.gas_wall_heat_into_gas_j)+np.diff(boundary),
        rtol=1e-8, atol=1e-7)
    refinement = _refinement_probe(parameters, wall=True, external_heat=external_heat)
    maximum = refinement[-1]
    callback_state["heat_w"] = -50.
    try:
        trace.require_current()
    except ValueError:
        pass
    else:
        raise AssertionError("Mutating external-heat callback closure retained a current trace")
    callback_state["heat_w"] = -75.
    trace.require_current()
    return ValidationOutcome(True, {"external_wall_heat_j": float(boundary[-1]),
        "max_combined_energy_residual_j": maximum,
        "refinement_residuals_j": refinement,
        "refinement_tolerance_candidate_j": maximum,
        "refinement_contract": "finite, strictly decreasing residual at 72/144/288 samples per revolution"}, LIMITS)


def _refinement_probe(parameters, *, wall, external_heat=None):
    """Measure closure at three nested output grids; report, do not assume, a budget.

    The finest observed residual is a candidate acceptance scale for a later
    calibrated contract. Passing here means the output-grid residual converged
    monotonically over these levels; it is not a universal energy tolerance or
    evidence of physical validation.
    """
    import numpy as np

    from h2physics.combustion import run_open_cylinder_segment

    residuals = []
    for samples in (72, 144, 288):
        case_parameters = dict(parameters, samples_per_revolution=samples)
        trace = run_open_cylinder_segment(**_run_arguments(
            case_parameters, wall=wall, external_heat=external_heat))
        trace.require_current()
        value = float(np.max(np.abs(trace.sampled_first_law_residual_j)))
        if not np.isfinite(value):
            raise AssertionError(f"Non-finite energy residual at {samples} samples/revolution")
        residuals.append(value)
    if not (residuals[0] > residuals[1] > residuals[2]):
        raise AssertionError(
            "Energy residual did not decrease strictly across the declared "
            f"72/144/288 refinement levels: {residuals!r}"
        )
    return tuple(residuals)
