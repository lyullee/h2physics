"""Replay actual native multibed PSA, startup/refinement, CSS and conserved exports."""

import argparse
import hashlib
import sys
import time
from pathlib import Path

import numpy as np

from h2physics.adapters.psa_cycle import PsaCycleEvidence, PsaCycleNative, PsaDynaCycle
from h2physics.adsorption import AdsorptionBasis, AdsorptionDomain
from h2physics.core import Origin

ROOT = Path(__file__).resolve().parents[1]
SOURCES = ("src/h2physics/adapters/psa_cycle.py", "tests/test_psa_cycle.py", "scripts/check_psa_cycle.py",
           "src/h2physics/adapters/psa.py", "src/h2physics/adsorption.py")


def authored_case(*, step=.1, cycles=2, closed=False, css=False):
    material = {"name": "authored-warm-H2-N2", "end_fraction": 1., "a1": [[.3], [.8]],
        "b0_per_bar": [[.02], [.08]], "binding_energy_j_mol": [[2000.], [3000.]], "ldf_per_s": [.2, .1]}
    return {"schema": "dynamic-psa-case/v1", "case_id": "authored-multibed-cycle",
        "species": [{"name": "H2", "mw_kg_mol": .00201588, "cp_j_mol_k": 29.},
                    {"name": "N2", "mw_kg_mol": .0280134, "cp_j_mol_k": 29.}],
        "bed": {"n_cells": 3, "diameter_m": .03, "length_m": .15, "void_fraction": .4,
            "particle_diameter_m": .002, "bulk_density_kg_m3": 500., "solid_cp_j_kg_k": 700.,
            "ambient_k": 300., "materials": [material], "wall_thickness_m": .003,
            "wall_density_kg_m3": 7800., "wall_cp_j_kg_k": 500., "wall_k_w_m_k": 10.,
            "bed_k_w_m_k": .25, "h_bed_wall_w_m2_k": 10., "h_ambient_w_m2_k": 1.,
            "wall_model": "dynamic_lumped", "energy_mode": "internal_energy", "kinetics": "loading_ldf"},
        "feed": {"mole_fractions": [.8, .2], "temperature_k": 300., "pressure_bar": 3., "molar_flow_mol_s": .001},
        "high_pressure_bar": 3., "low_pressure_bar": 1., "product_pressure_bar": 1.5,
        "initial_pressure_bar": 1.2, "initial_mole_fractions": [.8, .2],
        "purge_to_feed_ratio": .1, "purge_gain_mol_s_bar": .001,
        "valves": {name: {"gain_mol_s_bar": 0. if closed else .001}
                   for name in ("feed", "product", "tail", "equalization")},
        "schedule": {"name": "skarstrom_4step", "pressurization_s": 1., "adsorption_s": 2.},
        "solver": {"rtol": 1e-7 if css else 1e-8, "max_step_s": step,
            "maximum_cycles": cycles, "minimum_cycles": 4 if css else 2,
            "css_tolerance": 1e-4 if css else 1e-5, "css_consecutive_cycles": 3 if css else 2,
            "mass_balance_tolerance": 1e-7, "energy_balance_tolerance": 1e-7,
            "jacobian_method": "complex_step" if css else "scipy_fd",
            "ledger_integration": "augmented", "negative_tolerance": 0.,
            "record_trace": True, "trace_interval_s": .5, "maximum_step_wall_s": 30.},
        "provenance": {"origin": "authored-synthetic-not-adsorbent-calibration"},
        "claim": "Authored native cycle conservation and finite-inventory verification only"}


def model(native, parameters):
    basis = AdsorptionBasis("authored-warm-H2-N2", ("H2", "N2"), "mol/kg-dry-solid:absolute",
        native.source_id, "authored-cycle-parameters", ("https://patents.google.com/patent/US2944627A/en",),
        loading_definition="absolute")
    return PsaDynaCycle(native, parameters, basis=basis, domain=AdsorptionDomain(290., 350., 5e5, 5e4),
        evidence=PsaCycleEvidence("authored-native-cycle",
            "native-gas-CvT0/stream-CpT0/solid-wall298.15K/negative-binding;H2-spin-unresolved",
            "warm-ideal-gas-no-condensation", Origin.SYNTHETIC), temporary_workspace=ROOT/"artifacts")


def source_hashes(native):
    root = Path(native.core.__file__).parent
    digest = hashlib.sha256()
    for path in sorted(root.glob("*.py")):
        digest.update(path.name.encode())
        digest.update(path.read_bytes())
    return {"ordered-native-Python": digest.hexdigest(), "native-runner-engine": native.runner.code_hash(),
            **{name: hashlib.sha256((root/name).read_bytes()).hexdigest()
               for name in ("core.py", "runner.py", "schedules.py", "numerics.py", "vectorized.py")}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--native-packages", type=Path, default=ROOT/"artifacts/native_packages")
    args = parser.parse_args()
    sys.path.insert(0, str(args.native_packages.resolve()))
    native = PsaCycleNative.from_installed(source_id="PSA-Dyna:a26a8ef687c90cd4a5c18d38aaa4209ea5c5dcd6")
    before = {p: hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in SOURCES}
    native_before = source_hashes(native)
    started = time.perf_counter()
    other_reporting = authored_case()
    other_reporting["reporting_species"] = "N2"
    try:
        model(native, other_reporting)
    except ValueError as error:
        h2_reporting_guard = "reporting_species='H2'" in str(error)
    else:
        h2_reporting_guard = False
    startup = model(native, authored_case()).run(start_time_s=100., clock_id="authored-operation-clock")
    fine_parameters = authored_case(step=.05)
    fine_parameters["solver"]["rtol"] = 2e-9
    fine = model(native, fine_parameters).run(start_time_s=100., clock_id="authored-operation-clock")
    closed = model(native, authored_case(cycles=1, closed=True)).run(start_time_s=100., clock_id="authored-closed-clock")
    print("actual native startup/refinement and closed-valve limits completed", flush=True)
    css_started = time.perf_counter()
    css = model(native, authored_case(step=.2, cycles=80, css=True)).run(
        start_time_s=100., clock_id="authored-CSS-clock")
    css_seconds = time.perf_counter()-css_started
    runs = (startup, fine, closed, css)
    mass_error = max(float(np.max(abs(p.component_residual_mol))) for r in runs for p in r.points)
    energy_error = max(abs(p.energy_residual_j) for r in runs for p in r.points)
    product_relative_error = float(np.max(abs(fine.totals.product_mol-startup.totals.product_mol)
                                         /fine.totals.product_mol))
    purity_error = abs(fine.final_cycle_totals.hydrogen_product_purity-startup.final_cycle_totals.hydrogen_product_purity)
    pressure_difference = max(float(np.max(abs(a.pressure_pa-b.pressure_pa)))
        for a, b in zip(fine.points[-1].beds, startup.points[-1].beds, strict=True))
    closed_defect = max(float(np.max(abs(p.native_state-closed.points[0].native_state))) for p in closed.points)
    final = css.native_result["final_cycle"]
    latest = css.final_cycle_totals
    prefix_cycle_time = max(p.native_elapsed_s for p in css.points)-css.native_schedule["cycle_time_s"]
    cycle_start = next(p for p in css.points if p.native_elapsed_s == prefix_cycle_time)
    cycle_end = css.points[-1]
    actual_feed = cycle_end.feed_mol-cycle_start.feed_mol
    actual_product = cycle_end.product_mol-cycle_start.product_mol
    actual_tail = cycle_end.tail_mol-cycle_start.tail_mol
    actual_purity = float(actual_product[0]/sum(actual_product))
    actual_ratio = float(actual_product[0]/actual_feed[0])
    after = {p: hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in SOURCES}
    native_after = source_hashes(native)
    gates = {
        "actual native runner/checkpoint/schedule and separate native audit Network retained":
            all(r.native_bindings.runner.run_case is native.runner.run_case and
                isinstance(r.audit_network, native.core.Network) and not r.original_integrator_objects_available
                for r in runs),
        "two physical beds/four global slots with finite pressure/composition changes":
            startup.native_result["number_of_beds"] == 2 and startup.native_result["number_of_cycle_steps"] == 4
            and np.ptp([p.beds[0].pressure_pa.mean() for p in startup.points]) > 5e4,
        "independent global component inventory defects <1e-8mol at every retained slot": mass_error < 1e-8,
        "independent U with signed boundary enthalpy and ambient defects <1e-4J": energy_error < 1e-4,
        "closed-valve native exact stationary limit <1e-9 state units": closed_defect < 1e-9,
        "zero product/feed keeps purity and recovery undefined": closed.totals.hydrogen_product_purity is None
            and closed.totals.hydrogen_product_to_feed_ratio is None,
        "native max-step/rtol refinement product integrals <1e-5relative and purity <1e-6":
            product_relative_error < 1e-5 and purity_error < 1e-6,
        "refined endpoint cell pressures differ <2Pa": pressure_difference < 2.,
        "startup retained without CSS/recovery claim": not startup.native_result["state_css_converged"]
            and startup.final_cycle_totals.css_hydrogen_recovery is None,
        "actual native CSS criteria and three-cycle streak achieved within fixed80cycle limit":
            css.native_result["state_css_converged"] and final["css_streak"] >= 3 and final["state_scaled_max"] <= 1e-4,
        "CSS purity/recovery use final-cycle molar exports only <1e-12":
            abs(latest.hydrogen_product_purity-actual_purity) < 1e-12
            and latest.css_hydrogen_recovery is not None and abs(latest.css_hydrogen_recovery-actual_ratio) < 1e-12,
        "CSS still preserves native closed release/experimental-qualification gate":
            css.native_result["dataset_release_gate"].startswith("closed_")
            and css.native_result["training_eligible"] is False,
        "H2-specific recovery requires actual native H2 reporting; N2 reporting rejected": h2_reporting_guard,
        "actual native and host/test/script begin/end source identities unchanged": before == after and native_before == native_after,
    }
    elapsed = time.perf_counter()-started
    lines = ["# Native warm scheduled multibed PSA", "",
        "Original authored native/software verification. No acquired isotherm, measured apparatus fit or industrial "
        "purification rating is claimed. Native source MIT revisiona26a8ef687c90cd4a5c18d38aaa4209ea5c5dcd6 remains "
        "separately installed. Reproduce: `python scripts/check_psa_cycle.py`.", "",
        f"Four completed native-runner campaigns in{elapsed:.6f}s; native CSS campaign{css_seconds:.6f}s. "
        "Every operation is integrated by the actual native runner/BDF/Jacobian machinery. Host Python objects "
        "are serialized only inside an explicit managed ignored workspace, which is removed after native artifacts "
        "are read and verified. No user JSON/HTTP protocol, copied solver, monkeypatch or alternate bed model is required.", "",
        "Authored2bed/3cell/H2-N2 loading-LDF fixture:0.15m length,0.03m diameter, void0.4,300K; "
        "initial1.2bar(abs), feed3bar/.001mol/s/.8H2-.2N2, product boundary1.5bar, tail1bar. "
        "Linear native valve gains0.001mol/(s bar), requested purge/feed0.1 with native available-product/capacity "
        "limitation. Adsorbent capacities[.3,.8]mol/kg, affinities[.02,.08]/bar, binding[2000,3000]J/mol, "
        "LDF[.2,.1]/s are authored, not source material coefficients. Native six-second Skarstrom schedule "
        "uses four global slots1/2/1/2s. Each bed alternates FP/AD/BD/P with its companion on the same clock.", "",
        "Startup uses2cycles, rtol1e-8/maxstep0.1s/native SciPy-FD Jacobian; fine usesrtol2e-9/0.05s. "
        "CSS usesnative complex-step Jacobian, rtol1e-7/0.2s, fixed maximum80cycles, minimum4cycles, "
        "CSS tolerance1e-4 and3consecutive cycles. All use native augmented species/enthalpy/ambient ledgers "
        "and strict0 accepted negative tolerance. Phase scope is warm ideal-gas without condensation; H2 spin "
        "is unresolved on this native constant-Cp reference. Pressure outputs are Pa absolute; native input "
        "pressure keys are explicitly bar absolute.", "",
        "The gas energy is native Cv*T from0K, transported enthalpy Cp*T from0K, adsorbent/wall sensible "
        "storage is referenced to298.15K and binding storage is negative. This is not CoolProp/Cantera formation "
        "energy. Native vacuum-work diagnostics are utility estimates and are not added again as bed heat. "
        "Internal purge and equalization are not external feed/product streams.", "",
        "| Quantity | Observed |", "|---|---:|",
        f"| Maximum component defect mol | {mass_error:.12g} |",
        f"| Maximum signed total-energy defect J | {energy_error:.12g} |",
        f"| Closed native state defect | {closed_defect:.12g} |",
        f"| Product integral refinement relative | {product_relative_error:.12g} |",
        f"| Final-cycle purity refinement absolute | {purity_error:.12g} |",
        f"| Final cell-pressure refinement Pa | {pressure_difference:.12g} |",
        f"| Startup last-cycle H2 product fraction | {startup.final_cycle_totals.hydrogen_product_purity:.12g} |",
        f"| Native CSS completed cycles | {css.native_result['completed_cycles']} |",
        f"| Native CSS worst scaled state change | {final['state_scaled_max']:.12g} |",
        f"| Native CSS final H2 product fraction | {latest.hydrogen_product_purity:.12g} |",
        f"| Native CSS final H2 export/feed ratio | {latest.css_hydrogen_recovery:.12g} |", "",
        "The authored CSS product can be poorer than the supplied0.8H2 feed. This is retained, not repaired "
        "or optimized into a purification claim. Startup enrichment is not evidence of CSS performance. "
        "The overall startup-window ratio is not feed-origin tracer recovery; initial bed inventory can "
        "contribute to exports. Only the native-verified final CSS cycle is labeled recovery here.", "",
        "| CSS final-cycle ledger | Component mol or energy J |", "|---|---|",
        f"| Feed(H2,N2) | {actual_feed.tolist()} |", f"| Net product(H2,N2) | {actual_product.tolist()} |",
        f"| Tail(H2,N2) | {actual_tail.tolist()} |",
        *(f"| {key} | {final[key]:.12g} |" for key in
          ("feed_enthalpy_j", "product_enthalpy_j", "tail_enthalpy_j", "ambient_heat_j", "vacuum_work_j")), "",
        "| Gate | Pass |", "|---|---|", *(f"| {name} | {passed} |" for name, passed in gates.items()), "",
        "## Actual object and integration limits", "",
        "Pinned runner.run_case accepts file paths only and constructs its Network/OdeResult internally. "
        "No public or private standalone slot-integrator helper was found; the only solve_ivp call is inside "
        "run_case. The host repeatedly uses its publicstep_budget=1/cycle_budget=1/resume interface to retain "
        "the actual hash-checked native checkpoint after each slot. It does not reproduce schedule stepping "
        "or integration. The returned audit_network is a distinct actual native Network for PsaDynaBed "
        "admission/snapshots and inventory audits, not the original integrator instance. "
        "original_integrator_objects_available=False is explicit; native callable, raw return records, "
        "state arrays, schedule and checkpoint metadata are retained. Native-generated temporary source ZIP "
        "is neither loaded nor bundled and is removed with the workspace.", "",
        "Receiving request018 must expose an object-based native runner accepting/returning the actual "
        "Network, state, native solver results and accepted-step/slot callbacks, explicit clock, stream "
        "and conservation contracts. The native mean_stream bridge currently requires CSS plus independent "
        "resolution/source/release qualifications; it is not invoked or bypassed here. Numerical CSS does "
        "not authorize a downstream release stream, manufacturer purity, plant capacity or experimental "
        "validation. Product receivers, PR thermodynamics, partial-pressure pellet states, cryogenic "
        "adsorption, arbitrary source clocks and source-qualified material/process parameters remain outside "
        "this first level. No receiving repository was changed or contacted.", "",
        "Primary context: [Skarstrom original cycle patent](https://patents.google.com/patent/US2944627A/en), "
        "[native PSA-Dyna](https://github.com/lyullee/psa-dyna/tree/a26a8ef687c90cd4a5c18d38aaa4209ea5c5dcd6). "
        "Original composition and verification inputs contain no copied native implementation, published "
        "parameter table or source experimental records.", "",
        "## Begin/end fingerprints", "", "| Native source | Begin SHA256 | End SHA256 |", "|---|---|---|",
        *(f"| {name} | {value} | {native_after[name]} |" for name, value in native_before.items()), "",
        "| Host source/test/replay | Begin SHA256 | End SHA256 |", "|---|---|---|",
        *(f"| {name} | {value} | {after[name]} |" for name, value in before.items()), ""]
    (ROOT/"research/native_psa_cycle.md").write_text("\n".join(lines), encoding="utf-8", newline="\n")
    for name, passed in gates.items():
        print(f"{'PASS' if passed else 'FAIL'} {name}", flush=True)
    if not all(gates.values()):
        raise SystemExit("A native PSA cycle gate failed; report retained")
    print(f"wrote research/native_psa_cycle.md; local calculation{elapsed:.6f}s", flush=True)


if __name__ == "__main__":
    main()
