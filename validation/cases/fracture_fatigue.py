"""Deferred cluster cases. No native model/solver runs at import or in cases()."""

import hashlib
import inspect
import json
import math
from dataclasses import replace
from pathlib import Path

from h2physics.cluster_validation import ValidationCase, ValidationOutcome


def cases():
    return (
        ValidationCase(
            identifier="fracture-paris-si-exponential",
            profile="fracture-fatigue",
            entrypoint="validation.cases.fracture_fatigue:validate_baseline",
            parameters={},
            invariants=(
                "actual native HELPR2.1.0 objects",
                "SI versus MPa sqrt(m) conversion",
                "independent m2 exponential finite growth",
                "source bytes unchanged",
            ),
        ),
        ValidationCase(
            identifier="fracture-terminal-events-refinement",
            profile="fracture-fatigue",
            entrypoint="validation.cases.fracture_fatigue:validate_events",
            parameters={},
            invariants=(
                "independent size and Kmax failure cycles",
                "native SciPy event results",
                "cycle/physical clock boundary",
                "step/tolerance refinement",
            ),
        ),
        ValidationCase(
            identifier="fracture-hydrogen-native-constitutive",
            profile="fracture-fatigue",
            entrypoint="validation.cases.fracture_fatigue:validate_hydrogen",
            parameters={},
            invariants=(
                "actual native H2 model",
                "native fugacity reference identified",
                "no air-curve relabel",
                "actual native calls retained",
            ),
        ),
        ValidationCase(
            identifier="fracture-arrest-restart-and-negatives",
            profile="fracture-fatigue",
            entrypoint="validation.cases.fracture_fatigue:validate_failures",
            parameters={},
            invariants=(
                "zero-amplitude arrest and later restart",
                "no missing-clock inference",
                "geometry/native/domain failure retention",
                "no negative-rate repair",
            ),
        ),
        ValidationCase(
            identifier="fracture-block-sample-summary",
            profile="fracture-fatigue",
            entrypoint="validation.cases.fracture_fatigue:validate_block_summary",
            parameters={},
            invariants=(
                "per-block crack changes reconstruct from exact retained endpoints",
                "cycle and physical clocks remain those declared by each load block",
                "summaries contain reached blocks only and preserve terminal sample reasons",
                "no event interpolation or fracture acceptance claim is introduced",
            ),
        ),
    )


def _run_fixture(*, cycles=5000.0, stop_size_m=0.0015, toughness=8e6, step=20.0, tolerance=1e-9):
    from examples.fracture_fatigue import authored_case
    from h2physics.adapters.fracture_fatigue import (
        FractureIntegrationSettings,
        HelprFatigueLaw,
        integrate_fatigue_crack,
    )

    history, geometry, material, conditions, selection = authored_case(
        cycles=cycles, stop_size_m=stop_size_m, toughness_pa_sqrt_m=toughness
    )
    result = integrate_fatigue_crack(
        HelprFatigueLaw(selection),
        history,
        geometry,
        material,
        conditions,
        initial_crack_m=0.0007,
        settings=FractureIntegrationSettings(
            maximum_cycle_step=step, relative_tolerance=tolerance, absolute_tolerance_m=1e-13
        ),
    )
    return result


def _save(work_directory, name, data):
    directory = Path(work_directory)
    directory.mkdir(parents=True, exist_ok=True)
    (directory / (name + ".json")).write_text(
        json.dumps(data, indent=2, allow_nan=False) + "\n", encoding="utf-8", newline="\n"
    )


def validate_block_summary(*, work_directory, **parameters):
    from h2physics.adapters.fracture_fatigue import fracture_block_summaries

    result = _run_fixture()
    summaries = fracture_block_summaries(result)
    if not summaries or len(summaries) != len({point.block_id for point in result.snapshots}):
        raise AssertionError("Summary must include each and only reached block")
    for summary in summaries:
        points = tuple(point for point in result.snapshots if point.block_id == summary.block_id)
        if (summary.start_cycle != points[0].cycle or summary.end_cycle != points[-1].cycle
                or summary.start_crack_m != points[0].crack_size_m
                or summary.end_crack_m != points[-1].crack_size_m
                or summary.snapshot_count != len(points)):
            raise AssertionError("Block summary must retain exact sampled endpoints/count")
        expected = summary.end_crack_m - summary.start_crack_m
        if not math.isclose(summary.sampled_growth_m, expected, rel_tol=2e-13, abs_tol=1e-18):
            raise AssertionError("Block growth must reconstruct only from retained samples")
    _save(work_directory, "fracture_block_summaries", {
        "blocks": [{
            "block_id": row.block_id,
            "start_cycle": row.start_cycle,
            "end_cycle": row.end_cycle,
            "sampled_growth_m": row.sampled_growth_m,
            "sample_count": row.snapshot_count,
            "last_sample_reason": row.last_snapshot_reason,
        } for row in summaries],
    })
    return ValidationOutcome(True, {
        "reached_blocks": len(summaries),
        "total_samples": sum(row.snapshot_count for row in summaries),
        "sampled_growth_m": math.fsum(row.sampled_growth_m for row in summaries),
    }, (
        "The summary is an exact-sample reduction and does not locate hidden event times",
        "Sampled crack growth is not a fracture acceptance criterion or failure probability",
    ))


def validate_baseline(*, work_directory, **parameters):
    """Remote-only analytic oracle, authored independently of native implementation."""
    source = Path(__file__).resolve().parents[2]
    names = (
        "src/h2physics/adapters/fracture_fatigue.py",
        "examples/fracture_fatigue.py",
        "validation/cases/fracture_fatigue.py",
    )
    before = {n: hashlib.sha256((source / n).read_bytes()).hexdigest() for n in names}
    result = _run_fixture()
    # m=2 and Y=1 give an exponential in cycles. This is an oracle only.
    exponent = 2e-20 * math.pi * (42e6 - 12e6) ** 2
    expected = 0.0007 * math.exp(exponent * 5000.0)
    actual = result.snapshots[-1].crack_size_m
    error = abs(actual / expected - 1.0)
    assert result.termination == "history_exhausted" and error < 2e-7
    assert result.native_owners[0].growth.__class__.__module__ == "helpr.physics.crack_growth"
    assert result.native_solutions[0].success and result.native_calls
    assert result.snapshots[-1].physical_time_s == 11000.0
    assert all(
        c.native_delta_k_mpa_sqrt_m == c.stress_intensity.range_pa_sqrt_m / 1e6
        for c in result.native_calls
    )
    after = {n: hashlib.sha256((source / n).read_bytes()).hexdigest() for n in names}
    assert before == after
    metrics = {
        "relative_size_error": error,
        "final_size_m": actual,
        "final_cycle": result.snapshots[-1].cycle,
        "actual_native_calls": len(result.native_calls),
    }
    _save(
        work_directory,
        "fracture_baseline",
        {
            "metrics": metrics,
            "begin_sha256": before,
            "end_sha256": after,
            "native_source_sha256": dict(result.source_sha256),
        },
    )
    return ValidationOutcome(
        accepted=True,
        metrics=metrics,
        limitations=(
            "Synthetic supplied curve and infinite-plate geometry; no measured H2 validation.",
        ),
    )


def validate_events(*, work_directory, **parameters):
    coefficient = 2e-20 * math.pi * (42e6 - 12e6) ** 2
    size_limit = 0.001
    expected_cycle = math.log(size_limit / 0.0007) / coefficient
    coarse = _run_fixture(cycles=10000.0, stop_size_m=size_limit, step=80.0, tolerance=1e-7)
    fine = _run_fixture(cycles=10000.0, stop_size_m=size_limit, step=10.0, tolerance=1e-10)
    size_error = abs(fine.snapshots[-1].cycle - expected_cycle)
    assert fine.termination == "crack_size_limit" and size_error < 0.01
    assert abs(fine.snapshots[-1].crack_size_m - size_limit) < 1e-9
    assert size_error <= abs(coarse.snapshots[-1].cycle - expected_cycle) + 1e-7
    critical = 2.5e6
    expected_size = (critical / (42e6 * math.sqrt(math.pi))) ** 2
    expected_failure = math.log(expected_size / 0.0007) / coefficient
    fracture = _run_fixture(cycles=15000.0, stop_size_m=0.0015, toughness=critical, step=10.0)
    failure_error = abs(fracture.snapshots[-1].cycle - expected_failure)
    assert fracture.termination == "peak_mode_I_fracture_criterion" and failure_error < 0.02
    assert any(len(t) for t in fracture.native_solutions[-1].t_events)
    metrics = {
        "size_event_cycle_error": size_error,
        "fracture_event_cycle_error": failure_error,
        "fracture_size_m": fracture.snapshots[-1].crack_size_m,
    }
    _save(work_directory, "fracture_events", metrics)
    return ValidationOutcome(
        accepted=True,
        metrics=metrics,
        limitations=(
            "Numerical terminal events require the explicitly admitted SIF trial extension.",
        ),
    )


def validate_hydrogen(*, work_directory, **parameters):
    from helpr.physics.environment import EnvironmentSpecification

    from h2physics.adapters.fracture_fatigue import (
        HelprFatigueLaw,
        HelprLawSelection,
        HydrogenCrackEnvironment,
    )
    from h2physics.core import Origin

    # Select the reviewed native reference explicitly, without copying its
    # coefficient/reference table into the host's public source.
    reference = inspect.signature(EnvironmentSpecification).parameters["reference_pressure"].default
    native_env = EnvironmentSpecification(8.0, 4.0, 298.0, 0.75, reference_pressure=reference)
    env = HydrogenCrackEnvironment(
        8e6,
        4e6,
        298.0,
        0.75,
        float(native_env.fugacity) * 1e6,
        "HELPR-native-Abel-Noble",
        "native-evaluated-authored-boundary",
        Origin.SYNTHETIC,
    )
    rates = {}
    for model in ("code_case_2938", "g_202006"):
        law = HelprFatigueLaw(
            HelprLawSelection(
                model,
                "explicit-native-model-selection",
                reference_pressure_pa=float(reference) * 1e6,
            )
        )
        owner = law.make_native(env)
        raw = owner.growth.calc_change_in_crack_size(
            delta_n=1.0, delta_k=7.0, r_ratio=0.3, cycle_index=0
        )
        assert math.isfinite(raw) and raw > 0 and owner.environment is not None
        doubled = owner.growth.calc_change_in_crack_size(
            delta_n=2.0, delta_k=7.0, r_ratio=0.3, cycle_index=0
        )
        assert math.isclose(float(doubled), 2 * float(raw), rel_tol=1e-12)
        law.require_definition(owner)
        rates[model + "_native_m_per_cycle"] = float(raw)
    rates["native_fugacity_pa"] = env.hydrogen_fugacity_pa
    _save(work_directory, "fracture_native_hydrogen", rates)
    return ValidationOutcome(
        accepted=True,
        metrics=rates,
        limitations=(
            "Native conditional point evaluation is not independent material/correlation validation.",
            "The native Abel-Noble fugacity basis is explicit and is not a CoolProp conversion.",
        ),
    )


def validate_failures(*, work_directory, **parameters):
    from examples.fracture_fatigue import authored_case
    from h2physics.adapters.fracture_fatigue import (
        FractureGrowthError,
        HelprFatigueLaw,
        LoadCycleHistory,
        integrate_fatigue_crack,
    )

    history, geometry, material, conditions, selection = authored_case(cycles=1000.0)
    first = history.blocks[0]
    hold = replace(
        first,
        block_id="hold",
        end_cycle=500.0,
        end_time_s=2000.0,
        maximum_stress_pa=first.minimum_stress_pa,
    )
    growth = replace(
        first, block_id="restart", start_cycle=500.0, start_time_s=2000.0, end_time_s=3000.0
    )
    ordered = replace(history, blocks=(hold, growth))
    result = integrate_fatigue_crack(
        HelprFatigueLaw(selection), ordered, geometry, material, conditions, initial_crack_m=0.0007
    )
    hold_points = [s for s in result.snapshots if s.block_id == "hold"]
    assert all(s.crack_size_m == 0.0007 and s.native_call is None for s in hold_points)
    assert result.snapshots[-1].crack_size_m > 0.0007
    retained = 0
    for broken, invalid_material in (
        (geometry, replace(material, stress_intensity_ratio=(0.7, 0.9))),
        (replace(geometry, stress_intensity=lambda a, b: None), material),
    ):
        try:
            integrate_fatigue_crack(
                HelprFatigueLaw(selection),
                history,
                broken,
                invalid_material,
                conditions,
                initial_crack_m=0.0007,
            )
        except FractureGrowthError as error:
            assert error.__cause__ is not None and error.history is not None
            assert error.native_owners
            retained += 1
    try:
        LoadCycleHistory(
            (
                first,
                replace(
                    first,
                    block_id="gap",
                    start_cycle=1500.0,
                    end_cycle=2000.0,
                    start_time_s=4000.0,
                    end_time_s=5000.0,
                ),
            ),
            history.cycle_clock_id,
            history.physical_clock_id,
            history.stress_basis_id,
            history.ordering_evidence_id,
            history.source_id,
            history.origin,
        )
    except ValueError:
        retained += 1
    assert retained == 3
    metrics = {
        "retained_negative_cases": retained,
        "arrest_then_restart_final_m": result.snapshots[-1].crack_size_m,
    }
    _save(work_directory, "fracture_failures", metrics)
    return ValidationOutcome(
        accepted=True,
        metrics=metrics,
        limitations=(
            "These cases have not been run locally; acceptance exists only after this remote handler executes.",
            "No local/native performance or measured validation is claimed.",
        ),
    )
