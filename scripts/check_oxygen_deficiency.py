"""Execute native finite-O2 transport, original limits and retained failures."""

import argparse
import hashlib
import importlib.metadata
import json
import math
from dataclasses import replace
from pathlib import Path
from time import perf_counter

import numpy as np

from h2physics.adapters.cantera import MechanismBasis, ReactiveState
from h2physics.adapters.cantera_properties import CanteraFrozenGasProperties
from h2physics.adapters.cantera_volume import GasBoundaryRate, GasHeatBoundary, GasVent
from h2physics.adapters.oxygen_deficiency import (
    CanteraOxygenRoom,
    OxygenCriterion,
    OxygenFeedAdmission,
    OxygenResultVerificationError,
    OxygenRoomError,
    OxygenRoomRegion,
    OxygenRoomSettings,
    evaluate_oxygen_criterion,
    verify_oxygen_room_result,
)
from h2physics.core import Origin
from h2physics.release import HomogeneousIsentropicNozzle, NozzleOpening, SourceLocation
from h2physics.sources import IntervalMassSource


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    import cantera as ct
    import scipy

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--no-report", action="store_true")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    host_names = (
        "src/h2physics/adapters/oxygen_deficiency.py",
        "tests/test_oxygen_deficiency.py",
        "scripts/check_oxygen_deficiency.py",
        "docs/OXYGEN_DEFICIENCY.md",
        "src/h2physics/adapters/cantera_volume.py",
        "src/h2physics/adapters/cantera_properties.py",
        "src/h2physics/adapters/cantera.py",
        "src/h2physics/sources.py",
        "src/h2physics/core.py",
        "src/h2physics/release.py",
    )
    before = {name: sha(root / name) for name in host_names}
    mechanism = Path(ct.__file__).parent / "data/h2o2.yaml"
    raw = mechanism.read_bytes()
    distribution = importlib.metadata.distribution("cantera")
    license_path = next(
        Path(distribution.locate_file(p))
        for p in distribution.files
        if str(p).endswith("licenses/License.txt")
    )
    native_paths = {
        "installed h2o2.yaml": mechanism,
        "Cantera compiled extension": Path(ct._cantera.__file__),
        "Cantera license": license_path,
        "Cantera metadata": Path(distribution.locate_file("cantera-3.2.0.dist-info/METADATA")),
    }
    native_before = {name: sha(path) for name, path in native_paths.items()}
    names = ("H2", "O2", "N2", "H2O")

    def factory():
        species = {s.name: s for s in ct.Species.list_from_yaml(raw.decode(), "species")}
        return ct.Solution(thermo="ideal-gas", species=[species[n] for n in names])

    basis = MechanismBasis(
        "installed-h2o2-frozen-finite-room",
        sha(mechanism),
        "Cantera BSD-3-Clause; upstream installed species provenance",
        ("https://cantera.org/3.2/reference/reactors/ideal-gas-reactor.html",),
        300.0,
        1000.0,
        50000.0,
        500000.0,
    )
    region = OxygenRoomRegion(
        "authored-1m3-room",
        "homogeneous-receptor",
        "authored-xyz",
        "authored-absolute-clock",
        (1.0, 0.0, 1.5),
        0.0,
        1.0,
        "authored-complete-mixing",
        "warm-single-gas-no-condensation",
        "prescribed-boundaries-no-fan-performance",
        Origin.SYNTHETIC,
    )
    initial = ReactiveState(330.0, 101325.0, {"O2": 0.21, "N2": 0.79})

    def feed(masses, edges, *, fractions=None, name="H2", outside=None, end="isolation"):
        phase = factory()
        phase.TPX = 330.0, 200000.0, fractions or {"H2": 1.0}
        properties = CanteraFrozenGasProperties(
            phase,
            basis,
            dict(zip(names, phase.Y, strict=True)),
            composition_sum_tolerance=1e-14,
            composition_correction_id="accepted-native-composition-ulps",
        )
        source = IntervalMassSource(
            SourceLocation(
                name, region.clock_id, region.frame_id, (0.0, 0.0, 0.0), (1.0, 0.0, 0.0)
            ),
            edges,
            masses,
            properties.state_pt(200000.0, 330.0),
            Origin.SYNTHETIC,
            "authored-finite-intervals",
            end,
        )
        return OxygenFeedAdmission(source, properties, "native-reference-preserved", outside)

    def vent(callback):
        return GasVent(
            GasBoundaryRate(
                "exhaust",
                region.clock_id,
                100.0,
                102.0,
                callback,
                Origin.SYNTHETIC,
                "authored-exhaust-closure",
            ),
            initial,
        )

    def solve(
        times=(100.0, 101.0),
        *,
        source=(),
        outlet=(),
        heat=(),
        state=initial,
        settings=OxygenRoomSettings(),
        provider_basis=basis,
    ):
        return CanteraOxygenRoom(factory, provider_basis, region).run(
            state, times, feeds=source, exhausts=outlet, heat_boundaries=heat, settings=settings
        )

    def criterion(quantity="wet_oxygen_mole_fraction"):
        return OxygenCriterion(
            "explicit-authored-0.195-screen",
            quantity,
            0.195,
            "below",
            50000.0,
            500000.0,
            -100.0,
            100.0,
            "authored-check;not-regulatory-compliance",
            "declared-near-sea-level-pressure-range",
        )

    calculation_start = perf_counter()
    sealed = solve()
    pulse = feed((0.0002, 0.0004), (100.0, 100.3, 100.6), outside="declared-isolated-tail")
    pulse_result = solve(np.linspace(100.0, 101.0, 11), source=(pulse,))
    phase = factory()
    phase.TPX = 330.0, 101325.0, dict(initial.mole_fractions)
    total_kmol = phase.density_mole * region.volume_m3
    ndot = 0.2 * total_kmol
    pure = feed((ndot * phase.molecular_weights[phase.species_index("H2")],), (100.0, 101.0))
    molar_exhaust = vent(lambda t, p: ndot * p.mean_molecular_weight)
    coarse = solve(np.linspace(100.0, 101.0, 5), source=(pure,), outlet=(molar_exhaust,))
    fine = solve(
        np.linspace(100.0, 101.0, 33),
        source=(pure,),
        outlet=(molar_exhaust,),
        settings=OxygenRoomSettings(
            maximum_time_step_s=0.025, relative_tolerance=1e-12, absolute_tolerance=1e-16
        ),
    )
    exponential = 0.21 * np.exp(-0.2 * (fine.time_s - 100.0))
    mixing_error = float(np.max(abs(fine.wet_oxygen_mole_fraction - exponential)))
    coarse_report, fine_report = [
        evaluate_oxygen_criterion(
            r, criterion(), interpolation="linear_between_native_output_samples"
        )
        for r in (coarse, fine)
    ]
    crossing = 100.0 + math.log(0.21 / 0.195) / 0.2
    coarse_error = abs(coarse_report.crossings[0].linearly_estimated_time_s - crossing)
    fine_error = abs(fine_report.crossings[0].linearly_estimated_time_s - crossing)
    phase.TPX = 330.0, 200000.0, dict(initial.mole_fractions)
    fresh = feed(
        (ndot * phase.mean_molecular_weight,),
        (100.0, 101.0),
        fractions=dict(initial.mole_fractions),
        name="fresh-air",
    )
    recovery = solve(
        source=(fresh,),
        outlet=(molar_exhaust,),
        state=ReactiveState(330.0, 101325.0, fine.snapshots[-1].mole_fractions),
    )
    expected_recovery = 0.21 + (fine.wet_oxygen_mole_fraction[-1] - 0.21) * math.exp(-0.2)
    simple = feed((0.001,), (100.0, 101.0))
    adiabatic = solve(source=(simple,))
    adiabatic_refined = solve(
        source=(simple,),
        settings=OxygenRoomSettings(
            maximum_time_step_s=0.025, relative_tolerance=1e-12, absolute_tolerance=1e-16
        ),
    )
    before_state = adiabatic_refined.snapshots[0]
    inventory = adiabatic_refined.species_inventory_kg[0].copy()
    inventory[names.index("H2")] += 0.001
    phase.Y = inventory / inventory.sum()
    phase.UV = (
        (before_state.internal_energy_j + 0.001 * simple.source.state.enthalpy_j_kg)
        / inventory.sum(),
        region.volume_m3 / inventory.sum(),
    )
    uv_temperature_error = adiabatic_refined.snapshots[-1].temperature_k - phase.T
    uv_pressure_error = adiabatic_refined.snapshots[-1].pressure_pa - phase.P
    q = 0.001 * (simple.source.state.internal_energy_j_kg - simple.source.state.enthalpy_j_kg)
    wall = GasHeatBoundary(
        "authored-thermostat",
        region.clock_id,
        100.0,
        101.0,
        initial,
        1.0,
        heat_flux_w_m2=lambda t: q,
    )
    thermostat = solve(source=(simple,), heat=(wall,))
    humid = solve(state=ReactiveState(330.0, 101325.0, {"O2": 0.19, "N2": 0.76, "H2O": 0.05}))
    dry_report = evaluate_oxygen_criterion(
        humid,
        criterion("dry_oxygen_mole_fraction"),
        interpolation="linear_between_native_output_samples",
    )
    wet_report = evaluate_oxygen_criterion(
        humid, criterion(), interpolation="linear_between_native_output_samples"
    )

    actual_nozzles, signed_corrections, raw_trial_sums = [], [], []
    kernel = factory()
    opening = NozzleOpening("authored-effective-outlet", 1e-6, 1.0, "supplied-effective-area")

    def nozzle_flow(t, native_phase):
        raw_trial_sums.append(math.fsum(native_phase.Y))
        props = CanteraFrozenGasProperties(
            kernel,
            basis,
            dict(zip(names, native_phase.Y, strict=True)),
            composition_sum_tolerance=1e-7,
            composition_correction_id="caller-declared-native-off-manifold-trial-extension;trial-type-unobservable",
        )
        if props.composition_correction is not None:
            c = props.composition_correction
            signed_corrections.append(
                {
                    "raw_sum": c.raw_sum,
                    "species": c.corrected_species,
                    "signed_mass_fraction_change": c.mass_fraction_change,
                    "correction_id": c.correction_id,
                }
            )
        solved = HomogeneousIsentropicNozzle(props).solve(
            props.state_pt(native_phase.P, native_phase.T),
            back_pressure_pa=100000.0,
            opening=opening,
        )
        actual_nozzles.append(solved)
        return solved.mass_flow_kg_s

    nozzle_source = feed((1e-7,), (100.0, 100.001), name="short-H2")
    coupled = solve(
        (100.0, 100.001),
        source=(nozzle_source,),
        outlet=(vent(nozzle_flow),),
        settings=OxygenRoomSettings(
            maximum_time_step_s=0.0005, relative_tolerance=1e-8, absolute_tolerance=1e-13
        ),
    )
    failures = {}
    for label, admission in (
        (
            "unobserved source tail",
            feed((0.001,), (100.0, 100.5), outside="explicit-zero", end="window_end"),
        ),
        ("missing outside-support evidence", feed((0.001,), (100.0, 100.5))),
        (
            "arbitrary enthalpy zero",
            replace(
                simple,
                source=replace(
                    simple.source,
                    state=replace(
                        simple.source.state, enthalpy_j_kg=simple.source.state.enthalpy_j_kg + 100.0
                    ),
                ),
            ),
        ),
        (
            "para relabel",
            replace(
                simple,
                source=replace(
                    simple.source,
                    state=replace(
                        simple.source.state,
                        basis=replace(simple.source.state.basis, spin_composition="para"),
                    ),
                ),
            ),
        ),
        (
            "cold source outside fit",
            replace(
                simple,
                source=replace(
                    simple.source, state=replace(simple.source.state, temperature_k=20.0)
                ),
            ),
        ),
    ):
        try:
            solve(source=(admission,))
        except OxygenRoomError as error:
            failures[label] = {
                "error": str(error),
                "cause": type(error.__cause__).__name__,
                "actual_source_retained": error.feeds[0] is admission,
            }
    # An actual second native partition exceeds its pressure domain. It is not
    # repaired by imposing saturation, clipping flow or changing the source.
    narrow = replace(basis, maximum_pressure_pa=102000.0)
    props = CanteraFrozenGasProperties(factory(), narrow, {"H2": 1.0})
    large_source = replace(
        simple.source,
        edges_s=np.array([100.0, 100.5, 101.0]),
        mass_kg=np.array([0.0, 1.0]),
        state=props.state_pt(101500.0, 330.0),
    )
    large = OxygenFeedAdmission(large_source, props, "authored-domain-negative")
    try:
        solve(source=(large,), provider_basis=narrow)
    except OxygenRoomError as error:
        failures["native pressure domain"] = {
            "error": str(error),
            "cause": type(error.__cause__).__name__,
            "completed_native_partitions": len(error.completed_traces),
            "actual_network_retained": isinstance(error.failed_native.network, ct.ReactorNet),
            "retained_network_time_s": error.failure_time_s,
            "native_state": error.native_state.tolist(),
        }

    all_results = (
        sealed,
        pulse_result,
        coarse,
        fine,
        recovery,
        adiabatic,
        adiabatic_refined,
        thermostat,
        humid,
        coupled,
    )
    verified_identity = all(verify_oxygen_room_result(r) is r for r in all_results)
    tamper_failures = {}
    for label, changed in (
        (
            "cached wet summary zeros",
            replace(sealed, wet_oxygen_mole_fraction=np.zeros_like(sealed.time_s)),
        ),
        (
            "cached dry summary zeros",
            replace(sealed, dry_oxygen_mole_fraction=np.zeros_like(sealed.time_s)),
        ),
        (
            "cached partialP zeros",
            replace(sealed, oxygen_partial_pressure_pa=np.zeros_like(sealed.time_s)),
        ),
        ("changed output clock", replace(sealed, time_s=sealed.time_s + 10.0)),
        ("changed frame context", replace(sealed, region=replace(region, frame_id="other-frame"))),
        (
            "cloned snapshot object",
            replace(sealed, snapshots=(replace(sealed.snapshots[0]), *sealed.snapshots[1:])),
        ),
        ("absent owner binding", replace(sealed, _binding=None)),
    ):
        try:
            evaluate_oxygen_criterion(
                changed, criterion(), interpolation="linear_between_native_output_samples"
            )
        except OxygenResultVerificationError as error:
            tamper_failures[label] = {
                "error": str(error),
                "supplied_retained": error.supplied is changed,
                "actual_native_trace_retained": error.native_traces is sealed.native_traces,
            }
    invalid_criterion = criterion()
    object.__setattr__(invalid_criterion, "threshold", float("nan"))
    criterion_revalidated = False
    try:
        evaluate_oxygen_criterion(
            sealed, invalid_criterion, interpolation="linear_between_native_output_samples"
        )
    except ValueError:
        criterion_revalidated = True
    mass_error = max(float(np.max(abs(r.mass_residual_kg))) for r in all_results)
    species_error = max(float(np.max(abs(r.species_residual_kg))) for r in all_results)
    oxygen_error = max(
        float(np.max(abs(r.species_residual_kg[:, r.species_names.index("O2")])))
        for r in all_results
    )
    energy_error = max(float(np.max(abs(r.energy_residual_j))) for r in all_results)
    pressure_error = max(float(np.max(abs(r.pressure_identity_residual_pa))) for r in all_results)
    source_error = max(
        float(np.max(abs(r.source_mass_residual_kg))) for r in all_results if r.feeds
    )
    source_h_error = max(float(np.max(abs(r.source_enthalpy_residual_j))) for r in all_results)
    accepted_sum_error = max(
        abs(math.fsum(s.mass_fractions.values()) - 1) for s in coupled.snapshots
    )
    gates = {
        "original computed result verifies without ODE replay": verified_identity,
        "replaced summary clock context and snapshot reject": len(tamper_failures) == 7
        and all(
            f["supplied_retained"] and f["actual_native_trace_retained"]
            for f in tamper_failures.values()
        ),
        "current criterion fields revalidated": criterion_revalidated,
        "actual finite native reactors/networks retained": all(
            isinstance(o.network, ct.ReactorNet) for r in all_results for o in r.native
        ),
        "sealed O2 inventory invariant": abs(
            sealed.oxygen_inventory_kg[-1] - sealed.oxygen_inventory_kg[0]
        )
        < 1e-14,
        "all finite mass ledgers": mass_error < 1e-9,
        "all native species and O2 ledgers": species_error < 1e-9 and oxygen_error < 1e-10,
        "all signed U-H-Q ledgers": energy_error < 0.001,
        "independent native ideal P inventory identity": pressure_error < 1e-5,
        "finite interval source masses": source_error < 1e-11
        and len(pulse_result.native_traces) == 3,
        "source native caloric enthalpy admission": source_h_error < 0.001,
        "independent well-mixed O2 exponential": mixing_error < 1e-8,
        "constant-molar displacement P and T": max(
            abs(s.pressure_pa - 101325.0) for s in fine.snapshots
        )
        < 0.001
        and max(abs(s.temperature_k - 330.0) for s in fine.snapshots) < 1e-6,
        "fresh-air finite purge recovery": abs(
            recovery.wet_oxygen_mole_fraction[-1] - expected_recovery
        )
        < 1e-8,
        "independent summed native UV closure": abs(uv_temperature_error) < 1e-7
        and abs(uv_pressure_error) < 1e-4,
        "sampled crossing refinement and bracket": fine_error < coarse_error
        and fine_report.crossings[0].lower_time_s
        <= crossing
        <= fine_report.crossings[0].upper_time_s,
        "thermostat fraction differs from ambient pO2": thermostat.wet_oxygen_mole_fraction[-1]
        < 0.21
        and abs(
            thermostat.oxygen_partial_pressure_pa[-1] - thermostat.oxygen_partial_pressure_pa[0]
        )
        < 1e-4,
        "wet dry and actual partialP are distinct": wet_report.reconstructed_deficit_duration_s
        == 1.0
        and dry_report.reconstructed_deficit_duration_s == 0.0,
        "actual evolving-composition shared nozzle": len(actual_nozzles) > 0
        and coupled.oxygen_inventory_kg[-1] < coupled.oxygen_inventory_kg[0]
        and max(abs(n.energy_residual_w) for n in actual_nozzles) < 1e-6,
        "sampled composition admitted distinct from trial extension": accepted_sum_error < 1e-10
        and max(abs(s - 1) for s in raw_trial_sums) <= 1e-7,
        "original failed sources and native failure retained": len(failures) == 6
        and failures["native pressure domain"]["completed_native_partitions"] == 1
        and failures["native pressure domain"]["actual_network_retained"],
        "no physiological or cold-injury probability": all(
            r.probability is None for r in all_results
        )
        and fine_report.probability is None,
    }
    elapsed = perf_counter() - calculation_start
    after = {name: sha(root / name) for name in host_names}
    native_after = {name: sha(path) for name, path in native_paths.items()}
    gates["executed host/test/script/docs and native bytes unchanged"] = (
        before == after and native_before == native_after
    )
    gates = {name: bool(value) for name, value in gates.items()}
    data = {
        "versions": {
            "cantera": ct.__version__,
            "scipy": scipy.__version__,
            "numpy": np.__version__,
        },
        "elapsed_s": elapsed,
        "gates": gates,
        "host_begin_sha256": before,
        "host_end_sha256": after,
        "native_begin_sha256": native_before,
        "native_end_sha256": native_after,
        "failures": failures,
        "cached_result_negative_cases": tamper_failures,
        "max_defects": {
            "mass_kg": mass_error,
            "all_species_kg": species_error,
            "O2_kg": oxygen_error,
            "U_H_Q_J": energy_error,
            "pressure_identity_Pa": pressure_error,
            "source_mass_kg": source_error,
            "source_enthalpy_J": source_h_error,
            "analytic_O2_fraction": mixing_error,
            "UV_temperature_K": uv_temperature_error,
            "UV_pressure_Pa": uv_pressure_error,
        },
        "mixing": {
            "final_wet_O2": fine.wet_oxygen_mole_fraction[-1],
            "final_recovery_O2": recovery.wet_oxygen_mole_fraction[-1],
            "analytic_crossing_s": crossing,
            "coarse_crossing_error_s": coarse_error,
            "fine_crossing_error_s": fine_error,
            "fine_linear_duration_s": fine_report.reconstructed_deficit_duration_s,
        },
        "shared_nozzle": {
            "actual_calls": len(actual_nozzles),
            "max_raw_trial_sum_deviation": max(abs(s - 1) for s in raw_trial_sums),
            "max_sampled_accepted_sum_deviation": accepted_sum_error,
            "signed_composition_corrections": signed_corrections,
        },
        "initial_stricter_check": "At default rtol1e-10 adiabatic U error1.00319e-5J narrowly exceeded an authored1e-5J assertion; no common budget changed. The independent UV oracle uses refined rtol1e-12/atol1e-16 above.",
        "scope": "Authored warm homogeneous finite inventory verification; no measured O2/human validation, LH2 condensation or cold-injury model.",
    }
    artifact = root / "artifacts/oxygen_deficiency_replay.json"
    artifact.write_text(
        json.dumps(data, indent=2, allow_nan=False) + "\n", encoding="utf-8", newline="\n"
    )
    lines = [
        "# Native finite oxygen-room replay",
        "",
        data["scope"],
        "",
        f"Versions: {data['versions']}. Actual local calculations: {elapsed:.6g}s.",
        "",
        "| Gate | Passed |",
        "|---|---|",
    ]
    lines.extend(f"| {k} | {v} |" for k, v in gates.items())
    lines.extend(
        [
            "",
            "```text",
            json.dumps(data, indent=2, allow_nan=False),
            "```",
            "",
            "Native failed objects are retained by OxygenRoomError during execution; this report stores diagnostic values, not serialized native engines.",
            "Native trial type and the first hidden failing trial are unobservable through the common owner. Completed command partitions differ from hidden accepted steps.",
            "All signed trial corrections belong only to the explicit shared-nozzle numerical extension; no negative species are clipped. Source/native caloric admission remains strict.",
            "Installed mechanism coefficients, implementation code and outside observations are not copied into host source/distributions.",
            "",
        ]
    )
    if not args.no_report:
        (root / "research/oxygen_deficiency.md").write_text(
            "\n".join(lines), encoding="utf-8", newline="\n"
        )
    print(
        json.dumps(
            {
                "passed": sum(gates.values()),
                "total": len(gates),
                "elapsed_s": elapsed,
                "defects": data["max_defects"],
                "versions": data["versions"],
            },
            indent=2,
        )
    )
    if not all(gates.values()):
        raise SystemExit(
            "Retained failed native oxygen-room gates: "
            + str([k for k, v in gates.items() if not v])
        )


if __name__ == "__main__":
    main()
