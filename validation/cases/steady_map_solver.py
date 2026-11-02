"""Deferred multi-start contracts for the bounded Brayton map solver."""

from dataclasses import replace

from h2physics.cluster_validation import ValidationCase, ValidationOutcome

LIMITS = (
    "The synthetic maps and callbacks exercise solver contracts only.",
    "Cantera owns every trial Brayton thermodynamic/equilibrium calculation.",
    "The three unknowns and all correction, speed-link, loss and target inputs are explicit.",
    "A unique algebraic root does not qualify an actual engine or close omitted plant boundaries.",
)


def cases():
    return (
        ValidationCase(
            identifier="hydrogen-brayton-bounded-map-operating-point-solve",
            profile="hydrogen-engine",
            entrypoint=__name__ + ":validate_steady_map_solve",
            invariants=("three-declared-unknowns-and-three-physical-residuals",
                        "native-brayton-cycle-reused-per-trial",
                        "explicit-speed-link-and-flow-conversion-evidence",
                        "compressor-and-turbine-map-bounds-no-extrapolation",
                        "shaft-loss-and-target-included-in-residual",
                        "multiple-seeds-and-distinct-root-reporting",
                        "ambiguous-results-do-not-select-a-root-silently"),
        ),
        ValidationCase(
            identifier="hydrogen-brayton-operating-point-incomplete-seed-search",
            profile="hydrogen-engine",
            entrypoint=__name__ + ":validate_steady_map_solve",
            parameters={"scenario": "invalid-speed-link"},
            invariants=("out-of-map-seed-callback-is-retained-as-failed-attempt",
                        "partial-root-search-is-not-reported-as-unique",
                        "unique-candidate-rejects-incomplete-search"),
        ),
    )


def validate_steady_map_solve(*, work_directory, scenario="unique", **parameters):
    del work_directory, parameters
    import cantera as ct

    from h2physics.combustion.open_brayton import OpenBraytonInputs, run_open_cycle_brayton
    from h2physics.combustion.compressor_map import (
        CompressorComponentMap,
        interpolate_compressor_map,
    )
    from h2physics.combustion.turbine_map import (
        TurbineComponentMap,
        interpolate_turbine_map,
    )
    from h2physics.combustion.steady_map_solver import (
        MapOperatingSeed,
        SteadyMapSolveInputs,
        solve_steady_map_operating_point,
    )

    speed_grid = (.5, 1.)
    comp_pr_grid = (6., 10.)
    turbine_pr_grid = (7., 8.5)
    true_speed, true_comp_pr, true_air_flow = .75, 8., 1.
    true_turbine_pr = true_comp_pr * .97
    comp_map = CompressorComponentMap(
        map_id="synthetic-compressor-map", evidence_id="synthetic:comp-grid:v1",
        source_uri="urn:h2physics:synthetic:compressor-map", license_id="NOASSERTION",
        source_sha256="0" * 64, speed_unit="synthetic-corrected-speed",
        pressure_ratio_convention="outlet-over-inlet-total-pressure",
        corrected_mass_flow_basis="kg/s synthetic correction reference",
        corrected_speed=speed_grid, compression_pressure_ratio=comp_pr_grid,
        corrected_mass_flow_kg_s=tuple(tuple(
            1. + .2 * (speed - true_speed) + .03 * (ratio - true_comp_pr)
            for ratio in comp_pr_grid) for speed in speed_grid),
        isentropic_efficiency=tuple(tuple(
            .85 + .04 * (speed - true_speed) + .01 * (ratio - true_comp_pr)
            for ratio in comp_pr_grid) for speed in speed_grid),
    )
    turbine_map = TurbineComponentMap(
        map_id="synthetic-turbine-map", evidence_id="synthetic:turbine-grid:v1",
        source_uri="urn:h2physics:synthetic:turbine-map", license_id="NOASSERTION",
        source_sha256="1" * 64, speed_unit="synthetic-corrected-speed",
        pressure_ratio_convention="inlet-over-exit-total-pressure",
        corrected_mass_flow_basis="kg/s synthetic correction reference",
        corrected_speed=speed_grid, expansion_pressure_ratio=turbine_pr_grid,
        corrected_mass_flow_kg_s=tuple(tuple(
            true_air_flow * 1.02 + .1 * (speed - true_speed)
            + .02 * (ratio - true_turbine_pr)
            for ratio in turbine_pr_grid) for speed in speed_grid),
        isentropic_efficiency=tuple(tuple(
            .86 + .04 * (speed - true_speed) + .005 * (ratio - true_turbine_pr)
            for ratio in turbine_pr_grid) for speed in speed_grid),
    )
    cycle_inputs = OpenBraytonInputs(
        mechanism_id="gri30.yaml-synthetic-solver-case",
        process_window_id="synthetic-steady-operating-point",
        air_temperature_k=288.15, air_pressure_pa=101325.,
        air_mole_fractions=(("O2", .21), ("N2", .79)),
        compressor_pressure_ratio=true_comp_pr,
        compressor_isentropic_efficiency=.85,
        combustor_pressure_recovery=.97,
        hydrogen_fuel_to_air_mass_ratio=.02,
        hydrogen_inlet_temperature_k=298.15,
        turbine_exhaust_pressure_pa=101325.,
        turbine_isentropic_efficiency=.86,
        hydrogen_lhv_j_kg=120e6,
        air_state_evidence_id="synthetic:air-v1",
        hydrogen_feed_evidence_id="synthetic:h2-v1",
        machine_parameter_evidence_id="synthetic:map-v1",
        lhv_evidence_id="synthetic:lhv-v1",
    )
    comp_point = interpolate_compressor_map(
        comp_map, corrected_speed=true_speed, compression_pressure_ratio=true_comp_pr)
    turb_point = interpolate_turbine_map(
        turbine_map, corrected_speed=true_speed, expansion_pressure_ratio=true_turbine_pr)
    reference_inputs = replace(
        cycle_inputs, compressor_isentropic_efficiency=comp_point.isentropic_efficiency,
        turbine_isentropic_efficiency=turb_point.isentropic_efficiency,
    )
    reference_cycle = run_open_cycle_brayton(ct.Solution("gri30.yaml"), reference_inputs)
    target_shaft_w = reference_cycle.net_work_j_kg_air * true_air_flow

    def phase_factory():
        return ct.Solution("gri30.yaml")

    problem = SteadyMapSolveInputs(
        cycle_inputs=cycle_inputs, compressor_map=comp_map, turbine_map=turbine_map,
        compressor_speed_bounds=(.65, .85), compressor_pressure_ratio_bounds=(7.5, 8.5),
        air_mass_flow_bounds_kg_s=(.9, 1.1),
        seeds=(MapOperatingSeed(.66, 7.6, .92), MapOperatingSeed(.84, 8.4, 1.08)),
        speed_link=(lambda speed: 100. if scenario == "invalid-speed-link" else speed),
        compressor_corrected_flow=lambda actual, cycle, point: actual,
        turbine_corrected_flow=lambda actual, cycle, point: actual,
        speed_link_evidence_id="synthetic:speed-link:v1",
        compressor_flow_evidence_id="synthetic:compressor-flow-conversion:v1",
        turbine_flow_evidence_id="synthetic:turbine-flow-conversion:v1",
        shaft_loss_evidence_id="synthetic:zero-shaft-loss:v1",
        shaft_target_evidence_id="synthetic:reference-shaft-target:v1",
        shaft_mechanical_loss_w=0., shaft_residual_target_w=target_shaft_w,
        flow_relative_tolerance=1e-3, flow_absolute_tolerance_kg_s=1e-6,
        shaft_absolute_tolerance_w=1., root_merge_tolerance=1e-4,
    )
    result = solve_steady_map_operating_point(phase_factory, problem)
    assert result.require_current() is result
    if scenario == "invalid-speed-link":
        assert result.status == "incomplete_search"
        assert not result.candidates
        assert all(not attempt.converged and attempt.failure for attempt in result.attempts)
        try:
            result.unique_candidate
        except ValueError:
            pass
        else:
            raise AssertionError("An incomplete seed search exposed a unique candidate")
        return ValidationOutcome(
            True,
            {"status": result.status, "distinct_roots": len(result.candidates),
             "seed_count": len(result.attempts), "unique_candidate": "rejected"},
            LIMITS,
        )
    assert result.status == "unique"
    point = result.unique_candidate
    assert len(result.attempts) == 2
    assert all(attempt.converged for attempt in result.attempts)
    assert abs(point.compressor_corrected_speed - true_speed) < 1e-3
    assert abs(point.compressor_pressure_ratio - true_comp_pr) < 1e-3
    assert abs(point.air_mass_flow_kg_s - true_air_flow) < 1e-3
    assert abs(point.shaft_residual_w) <= problem.shaft_absolute_tolerance_w
    assert comp_map.corrected_speed[0] <= point.compressor_corrected_speed <= comp_map.corrected_speed[-1]
    assert turbine_map.corrected_speed[0] <= point.turbine_corrected_speed <= turbine_map.corrected_speed[-1]
    return ValidationOutcome(
        True,
        {"status": result.status, "distinct_roots": len(result.candidates),
         "seed_count": len(result.attempts),
         "compressor_corrected_speed": point.compressor_corrected_speed,
         "compressor_pressure_ratio": point.compressor_pressure_ratio,
         "air_mass_flow_kg_s": point.air_mass_flow_kg_s,
         "shaft_target_residual_w": point.shaft_residual_w},
        LIMITS,
    )
