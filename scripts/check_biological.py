"""Reproduce native ADM1 finite-inventory checks with explicitly synthetic inputs."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path
from time import perf_counter


def fingerprints() -> dict[str, str]:
    root = Path(__file__).resolve().parents[1]
    files = ("src/h2physics/adapters/biological.py", "tests/test_biological.py",
             "scripts/check_biological.py", "docs/NATIVE_BIOLOGICAL_PROCESS.md",
             "research/biological_dependency.toml")
    result = {f: hashlib.sha256((root / f).read_bytes()).hexdigest()
              for f in files if (root / f).exists()}
    for package in ("qsdsan", "biosteam", "thermosteam"):
        from importlib.util import find_spec
        spec = find_spec(package)
        if spec is not None and spec.origin:
            directory = Path(spec.origin).parent
            digest = hashlib.sha256()
            files = sorted(p for p in directory.rglob("*")
                           if p.is_file() and p.suffix in (".py", ".tsv"))
            for path in files:
                digest.update(path.relative_to(directory).as_posix().encode())
                digest.update(b"\0")
                digest.update(path.read_bytes())
            result["native:" + package] = digest.hexdigest()
    return result


def make_case(native, *, zero_rates=False, gas_pipe=1e-9, feed_flow=.0001/86400,
              max_pressure=500000, absolute_tolerance=1e-7, external_pressure=101325):
    """Original synthetic reactor; no experimental record or fitted coefficients."""
    from qsdsan import process_models as pm

    from h2physics.adapters.biological import (
        Adm1Geometry,
        BiologicalAudit,
        BiologicalEvidence,
        QsdSanAdm1Digester,
    )

    components = pm.create_adm1_cmps()
    changes = {}
    if zero_rates:
        changes = dict.fromkeys(("q_dis", "q_ch_hyd", "q_pr_hyd", "q_li_hyd",
                                 "k_su", "k_aa", "k_fa", "k_c4", "k_pro", "k_ac", "k_h2",
                                 "b_su", "b_aa", "b_fa", "b_c4", "b_pro", "b_ac", "b_h2", "kLa"), 0)
    model = pm.ADM1(components=components, **changes)
    initial = dict.fromkeys(components.IDs, 0.0)
    initial.update(S_su=1.0, S_IC=.1, S_IN=.05, X_su=.1, X_h2=.01, H2O=1000.0)
    if zero_rates:
        initial["S_h2"] = 1e-4
    feed = {k: 0.0 for k in components.IDs if k != "H2O"}
    feed.update(S_su=.5 if zero_rates else 1.0, S_IC=.1, S_IN=.05)
    evidence = BiologicalEvidence("original-synthetic-verification",
                                  "authored-native-zero-rate-limit" if zero_rates else "native-default-not-calibrated",
                                  "authored-initial-inventories", "authored-constant-feed",
                                  "prescribed-isothermal-308.15K", "native-ADM1-measured-COD-C-N",
                                  "absolute-verification-clock", 864000., 950400.)
    return QsdSanAdm1Digester(native, components=components, model=model,
                             geometry=Adm1Geometry(.01, .005, gas_pipe, external_pressure, 308.15),
                             evidence=evidence, feed_volume_flow_m3_s=feed_flow,
                             feed_concentrations_kg_m3=feed,
                             initial_liquid_concentrations_kg_m3=initial,
                             initial_headspace_mol_m3={"S_h2": 1e-6, "S_ch4": 30., "S_IC": 10.},
                             audit=BiologicalAudit(absolute_tolerance, 1e-8, max_pressure, 1e-6))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--native-target", action="append", default=[],
                        help="Explicit optional package path; repeat fixed-core before dependency target")
    parser.add_argument("--probe-only", action="store_true")
    args = parser.parse_args()
    for target in reversed(args.native_target):
        sys.path.insert(0, str(Path(target).resolve()))
    import numpy as np

    from h2physics.adapters.biological import QsdSanNative

    start = perf_counter()
    before = fingerprints()
    native = QsdSanNative.from_installed()
    reactor = make_case(native)
    run = reactor.run(start_time_s=864000., end_time_s=872640., sample_count=12801,
                      max_step_s=300)
    gates = {
        "native_object_retention": run.native_solution is reactor.native_system.scope.sol,
        "native_initial_exact": np.array_equal(run.native_solution.y[:, 0], run.native_initial_state),
        "finite_substrate_and_biomass": run.points[-1].native_state[0] < .9
            and run.points[-1].native_state[reactor._ids.index("X_su")] > .1,
        "hydrogen_formed_consumed_exported": run.balance.hydrogen_formed_kg
            > run.balance.hydrogen_consumed_kg > 0 and run.balance.exported_hydrogen_kg > 0,
        "independent_hydrogen_balance": run.balance.hydrogen_residual_kg < 1e-10,
        "independent_cod_c_n": max(run.balance.invariant_residuals_kg.values()) < 5e-9,
        "prescribed_temperature_no_energy_claim": not run.energy_balance_available,
    }
    extra = {}
    if not args.probe_only:
        from math import exp

        from h2physics.adapters.biological import BiologicalAuditError

        fine = make_case(native).run(start_time_s=864000, end_time_s=872640,
                                     sample_count=25601, max_step_s=150, rtol=2e-9, atol=2e-12)
        endpoint_difference = float(np.max(np.abs(np.array(fine.points[-1].native_state[:27])
                                                  - run.points[-1].native_state[:27])))
        h2_export_difference = abs(fine.balance.exported_hydrogen_kg - run.balance.exported_hydrogen_kg)
        h2_export_relative = h2_export_difference / fine.balance.exported_hydrogen_kg
        gates["native_temporal_refinement"] = endpoint_difference < 1e-7 and h2_export_relative < 1e-4
        gates["sampled_ledger_refinement"] = (max(fine.balance.component_residuals_kg.values())
                                                < max(run.balance.component_residuals_kg.values()))
        extra.update(endpoint_refinement_max_native_liquid_coordinate=endpoint_difference,
                     export_hydrogen_refinement_relative=h2_export_relative,
                     fine_component_defect_kg=max(fine.balance.component_residuals_kg.values()),
                     fine_invariant_defects_kg=dict(fine.balance.invariant_residuals_kg))
        inert_case = make_case(native, zero_rates=True, gas_pipe=0)
        inert = inert_case.run(start_time_s=864000, end_time_s=907200, sample_count=129,
                               max_step_s=900, rtol=1e-12, atol=1e-14)
        analytical = .5 + .5 * exp(-inert_case.feed_volume_flow_m3_s * 43200 / .01)
        inert_error = abs(inert.points[-1].native_state[0] - analytical)
        gates["independent_inert_analytic_limit"] = inert_error < 1e-10
        gates["zero_pipe_no_export"] = inert.balance.exported_hydrogen_kg == 0
        extra["inert_analytic_concentration_error_kg_m3"] = inert_error
        closed_case = make_case(native, gas_pipe=0, feed_flow=0)
        try:
            closed_case.run(start_time_s=864000, end_time_s=872640,
                            sample_count=12801, max_step_s=300)
        except BiologicalAuditError as error:
            gates["native_closed_finalization_failure_retained"] = (
                error.native_solution.success and error.clock_kind == "native-finalization"
                and "empty" in str(error))
            closed_solution = error.native_solution
            extra["closed_native_finalization_error"] = str(error)
        else:
            raise RuntimeError("checked native closed finalization behavior changed")
        first = np.array(list(closed_case._point(864000, closed_solution.y[:, 0]).measured_inventories_kg.values()))
        last = np.array(list(closed_case._point(872640, closed_solution.y[:, -1]).measured_inventories_kg.values()))
        invariant_change = max(abs((last-first) @ weights) for weights in
                               (closed_case.native_components.i_COD, closed_case.native_components.i_C,
                                closed_case.native_components.i_N))
        gates["diagnostic_closed_finite_cod_c_n"] = invariant_change < 1e-10
        extra["closed_invariant_inventory_change_kg"] = float(invariant_change)
        reverse = make_case(native, zero_rates=True, external_pressure=200000).run(
            start_time_s=864000, end_time_s=872640, sample_count=65)
        gates["native_one_way_no_reverse"] = all(p.gas_outflow_m3_s == 0 for p in reverse.points)
        try:
            make_case(native).run(start_time_s=864000, end_time_s=872640,
                                   sample_count=1601, max_step_s=300)
        except BiologicalAuditError as error:
            gates["underresolved_ledger_fails_with_native_trace"] = (
                error.native_solution.success and len(error.audited_points) == 1601
                and "COD boundary" in str(error))
            extra["coarse_rejection"] = str(error)
        else:
            gates["underresolved_ledger_fails_with_native_trace"] = False
        try:
            make_case(native, max_pressure=103000).run(
                start_time_s=864000, end_time_s=872640, sample_count=65)
        except BiologicalAuditError as error:
            gates["pressure_rejection_retains_accepted_state"] = (
                error.native_solution.success and error.clock_kind == "native-accepted"
                and error.time_s == 864000)
        else:
            gates["pressure_rejection_retains_accepted_state"] = False
        constants = reactor.native_model.rate_function._params["rate_constants"]
        saved_constants = constants.copy()
        selected = [run.points[0], run.points[len(run.points)//2], run.points[-1]]
        try:
            constants[0] = np.nan
            reactor._balance(np.array([p.time_s for p in selected]),
                             np.array([p.native_state for p in selected]), selected)
        except ValueError as error:
            gates["actual_native_nonfinite_rate_rejected"] = "nonfinite" in str(error)
        else:
            gates["actual_native_nonfinite_rate_rejected"] = False
        finally:
            constants[:] = saved_constants
    after = fingerprints()
    gates["source_and_native_bytes_unchanged"] = before == after
    gates = {name: bool(passed) for name, passed in gates.items()}
    data = {"native_versions": dict(native.versions),
            "native_accepted_steps": len(run.native_solution.t),
            "hydrogen_formed_kg": run.balance.hydrogen_formed_kg,
            "hydrogen_consumed_kg": run.balance.hydrogen_consumed_kg,
            "exported_hydrogen_kg": run.balance.exported_hydrogen_kg,
            "dry_export_hydrogen_mole_fraction": run.balance.exported_dry_hydrogen_mole_fraction,
            "maximum_component_defect_kg": max(run.balance.component_residuals_kg.values()),
            "invariant_defects_kg": dict(run.balance.invariant_residuals_kg),
            "initial_pressure_pa": run.points[0].pressure_pa,
            "final_pressure_pa": run.points[-1].pressure_pa,
            "initial_substrate_kg_cod_m3": run.points[0].native_state[0],
            "final_substrate_kg_cod_m3": run.points[-1].native_state[0],
            "initial_trajectory_error": float(np.max(np.abs(run.native_solution.y[:, 0]
                                                           - run.native_initial_state))),
            "numba_disable_jit": os.environ.get("NUMBA_DISABLE_JIT", "unset"),
            "seconds": perf_counter() - start, "gates": gates,
            "begin": before, "end": after, **extra}
    print(json.dumps(data, indent=2), flush=True)
    return 0 if all(gates.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
