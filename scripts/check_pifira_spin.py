"""Replay actual pifira rotor thermochemistry and strict natural-conversion contracts."""

import argparse
import hashlib
import importlib
import importlib.metadata
import math
import sys
import tomllib
from pathlib import Path
from time import perf_counter

import numpy as np
from scipy.integrate import solve_ivp

from h2physics.adapters.lh2dt_spin import SpinDomain
from h2physics.adapters.pifira_spin import (
    PifiraSpinBridge,
    RotorCutoffError,
    RotorEnergyReference,
    RotorEvidence,
    SpinMedium,
    SpinPVAssumption,
)
from h2physics.core import Origin
from h2physics.thermo.coolprop import CoolPropProperties


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def tree_sha(root):
    value = hashlib.sha256()
    for path in sorted(root.rglob("*.py")):
        value.update(path.relative_to(root).as_posix().encode())
        value.update(b"\0")
        value.update(path.read_bytes())
        value.update(b"\0")
    return value.hexdigest()


def main():
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pifira-packages", type=Path, default=root/"artifacts/native_fire_packages")
    parser.add_argument("--lh2dt-packages", type=Path, default=root/"artifacts/native_packages")
    args = parser.parse_args()
    sys.path[:0] = [str(args.pifira_packages.resolve()), str(args.lh2dt_packages.resolve())]
    native = importlib.import_module("pifira.lh2.spin")
    states = importlib.import_module("lh2dt.ortho_para")
    package = importlib.import_module("pifira")
    distribution = importlib.metadata.distribution("pifira")
    if distribution.version != "0.3.0":
        raise ValueError("This replay checks separately installed pifira0.3.0")
    source_files = ("src/h2physics/adapters/pifira_spin.py", "tests/test_pifira_spin.py",
        "scripts/check_pifira_spin.py", "docs/NATIVE_SPIN_THERMOCHEMISTRY.md",
        "src/h2physics/adapters/lh2dt_spin.py", "research/pifira_dependency.toml")
    before = {name: sha(root/name) for name in source_files}
    native_files = {"pifira/lh2/spin.py": Path(native.__file__),
        "lh2dt/ortho_para.py": Path(states.__file__),
        "pifira0.3.0/LICENSE": Path(distribution.locate_file("pifira-0.3.0.dist-info/licenses/LICENSE")),
        "pifira0.3.0/METADATA": Path(distribution.locate_file("pifira-0.3.0.dist-info/METADATA"))}
    native_before = {name: sha(path) for name, path in native_files.items()}
    package_root = Path(package.__file__).parent
    tree_before = tree_sha(package_root)
    review = tomllib.loads((root/"research/pifira_dependency.toml").read_text())
    expected = next(row["sha256"] for row in review["installed_source"] if row["path"] == "pifira/lh2/spin.py")
    started = perf_counter()

    def bridge(rotor=None, *, maximum=1000., reference=96, offset=0.):
        return PifiraSpinBridge(native, rotor or native.RigidRotorSpinThermo(),
            native.MilenkoCorrelation(), states.OrthoParaState,
            evidence=RotorEvidence("https://doi.org/10.1016/j.ijhydene.2014.01.205",
                "https://doi.org/10.1007/BF02396837", "prescribed-pure-H2-medium", Origin.PREDICTED),
            domain=SpinDomain(1., maximum, reference, 1e-10, "authored-rotor-convergence-envelope"),
            energy_reference=RotorEnergyReference("common-native-J0-rotor-U", offset))

    model = bridge()
    state, mass = model.state(.3), .02
    temperatures = (1., 10., 20., 40., 80., 100., 300., 1000.)
    points = [model.point(state, t, mass) for t in temperatures]
    finite_differences = []
    for temperature in temperatures[1:]:
        width = temperature*1e-4
        row = [temperature]
        for species in ("para", "ortho"):
            difference = (model.thermo.rotational_energy_J_per_kg(temperature+width, species)
                -model.thermo.rotational_energy_J_per_kg(temperature-width, species))/(2*width)
            analytic = float(model.thermo.rotational_cv_J_per_kgK(temperature, species))
            row.extend((analytic, float(difference), abs(analytic-float(difference))))
        difference = (model.thermo.conversion_energy_J_per_kg(temperature+width)
                      -model.thermo.conversion_energy_J_per_kg(temperature-width))/(2*width)
        analytic = float(model.thermo.d_conversion_energy_dT_J_per_kgK(temperature))
        row.extend((analytic, float(difference), abs(analytic-float(difference))))
        finite_differences.append(row)
    fd = np.asarray(finite_differences)
    low = model.point(state, 10., mass)
    low_expected = 1/(1+9*math.exp(-2*model.thermo.rotational_temperature_K/10))
    high_model = bridge(native.RigidRotorSpinThermo(maximum_J=128), maximum=20000., reference=192)
    high = high_model.point(state, 20000., mass)
    cutoff_failure = None
    try:
        bridge(native.RigidRotorSpinThermo(maximum_J=8)).point(state, 1000., mass)
    except RotorCutoffError as error:
        cutoff_failure = error.point

    properties = CoolPropProperties("Hydrogen")
    media = []
    for pressure, temperature in ((2e5, 17.), (2e5, 20.), (2e6, 26.), (2e6, 32.),
                                  (1e5, 40.), (1e6, 80.), (2e6, 100.), (1e6, 120.)):
        medium = SpinMedium.from_frozen_state(properties.state_pt(pressure, temperature),
            density_evidence_id="authored-normal-H2-HEOS-reference-density",
            phase_evidence_id="actual-single-phase-frozen-reference",
            composition_density_assumption_id="authored-fixed-density-approximation-not-spin-mixture-EOS",
            origin=Origin.SYNTHETIC)
        media.append(medium)
    rates = [(m, c, model.rate(model.state(1-c), m, mass)) for m in media for c in (.62, .7, .75)]
    matched_equilibrium_error = max(abs(p.equilibrium.para_fraction-states.equilibrium_para_fraction(
        p.equilibrium.temperature_k, rotational_temperature_K=model.thermo.rotational_temperature_K,
        maximum_rotational_level=model.thermo.maximum_J)) for p in points)
    liquid = media[1]
    c_eq = float(model.thermo.equilibrium_ortho(liquid.temperature_k))
    balance = model.detailed_balance_probe([0., c_eq/2, c_eq, 1.5*c_eq, 1.], liquid)
    gas_reverse = model.rate(model.state(.38), media[-1], mass)
    density_gap_rejected = False
    try:
        model.rate(state, SpinMedium(20., 91., "liquid", "authored-density-probe",
                                     "published-liquid-branch", Origin.SYNTHETIC), mass)
    except ValueError:
        density_gap_rejected = True
    dilute_ratio = float(model.correlation.forward_rate_per_s(80., 2e-5, "gas")
                        /model.correlation.forward_rate_per_s(80., 1e-5, "gas"))

    # External generic verification driver; no library trajectory solver is added.
    times = np.linspace(100., 10100., 101)
    solutions, fraction_errors, energy_errors = [], [], []
    forward = float(model.correlation.forward_rate_per_s(liquid.temperature_k, liquid.density_kg_m3, "liquid"))
    exact_c = c_eq/(1-(1-c_eq/.7)*np.exp(-forward*c_eq/(1-c_eq)*(times-times[0])))
    first_energy = model.point(state, liquid.temperature_k, mass).mixture_rotational_energy_j
    for step, tolerance in ((1000., 1e-8), (500., 1e-10), (250., 1e-12)):
        def callback(time, values):
            result = model.thermostat_power(model.state(values[0]), liquid, mass, time_s=time,
                clock_id="authored-rotor-thermostat-clock", support_start_s=100., support_end_s=10100.,
                boundary_evidence_id="prescribed-T-rotor-bath-only")
            return result.rate.para_fraction_rate_s, result.external_power.heat_w
        solution = solve_ivp(callback, (times[0], times[-1]), (.3, 0.), t_eval=times,
                             rtol=tolerance, atol=1e-12, max_step=step, method="DOP853")
        solutions.append(solution)
        fraction_errors.append(float(np.max(abs((1-solution.y[0])-exact_c))))
        energy_errors.append(max(abs(model.point(model.state(x), liquid.temperature_k, mass).
            mixture_rotational_energy_j-first_energy-q) for x, q in zip(solution.y[0], solution.y[1], strict=True)))
    lower = model.correlation.primary_ortho_fraction_range[0]
    time_to_lower_boundary = -math.log((1-c_eq/lower)/(1-c_eq/.7))/(forward*c_eq/(1-c_eq))

    terms = model.storage_terms(state, 100., mass)
    tdot, xdot, width = .02, 1e-7, .01
    minus = model.point(model.state(.3-width*xdot), 100.-width*tdot, mass).mixture_rotational_energy_j
    plus = model.point(model.state(.3+width*xdot), 100.+width*tdot, mass).mixture_rotational_energy_j
    chain_error = abs((plus-minus)/(2*width)-terms.energy_rate_w(
        temperature_rate_k_s=tdot, para_fraction_rate_s=xdot))
    shifted = bridge(offset=2.3e7)
    energy_shift_error = abs(shifted.point(state, 100., mass).mixture_rotational_energy_j
        -model.point(state, 100., mass).mixture_rotational_energy_j-mass*2.3e7)
    correction = model.storage_terms(state, 100., mass, baseline_para_fraction=.3,
                                     baseline_evidence_id="authored-identical-frozen-baseline")
    h_rejected = False
    try:
        model.storage_terms(state, 100., mass, energy_kind="rotational_H")
    except ValueError:
        h_rejected = True
    pv = SpinPVAssumption("ideal-gas-no-mole-change", "gas", "authored-dilute-ideal-limit-only")
    h_terms = model.storage_terms(state, 100., mass, energy_kind="rotational_H", pv_assumption=pv)
    after = {name: sha(root/name) for name in source_files}
    native_after = {name: sha(path) for name, path in native_files.items()}
    tree_after = tree_sha(package_root)
    gates = {
        "actual reviewed native rotor/rate and LH2DT state used": native_before["pifira/lh2/spin.py"] == expected
            and native_before["pifira0.3.0/LICENSE"] == review["wheel_license_sha256"]
            and isinstance(state, states.OrthoParaState),
        "low-T two-level equilibrium and common-ground gap": abs(low.equilibrium.para_fraction-low_expected) < 2e-15
            and abs(low.conversion_energy_j_kg-model.thermo.gap_J_per_kg) < 1e-8,
        "mathematical high-T 1:3 equilibrium and Cv to R": abs(high.equilibrium.para_fraction-.25) < 1e-13
            and max(abs(high.para_cv_j_kg_k/model.thermo.gas_constant_J_kgK-1),
                    abs(high.ortho_cv_j_kg_k/model.thermo.gas_constant_J_kgK-1)) < 1e-6,
        "native Cv/gap derivative agree with direct energy differences": all(
            np.all(fd[:, error] <= 2e-5+2e-6*abs(fd[:, analytic])) for analytic, error in ((1, 3), (4, 6), (7, 9))),
        "insufficient cutoff fails with actual point retained": cutoff_failure is not None,
        "existing LH2DT equilibrium agrees on matched theta": matched_equilibrium_error < 2e-15,
        "strict rate points use admitted actual frozen single-phase density": len(rates) == 24
            and all(r.medium is m and r.medium.frozen_density_reference is m.frozen_density_reference
                    for m, _, r in rates),
        "dilute native density-rate limit ratio two": abs(dilute_ratio-2) < 1e-9,
        "balance probe has forward/zero/reverse signs but no admission": balance.native_rates_per_s[1] > 0
            and abs(balance.native_rates_per_s[2]) < 1e-20 and balance.native_rates_per_s[3] < 0,
        "admitted reverse gas rate absorbs rotor energy": gas_reverse.conversion_heat_w < 0,
        "native92 versus primary90 density gap remains rejected": density_gap_rejected,
        "generic constant-T driver matches independent closed form": all(s.success for s in solutions)
            and max(fraction_errors) < 1e-10 and min(1-solutions[-1].y[0]) > lower,
        "rotor thermostat delta-U equals external heat": max(energy_errors) < 1e-9,
        "T/composition energy tangent and common-zero invariance": chain_error < 1e-7 and energy_shift_error < 1e-8,
        "identical frozen baseline correction is zero without duplicating storage": correction.energy_j == 0
            and correction.frozen_capacity_j_k == 0,
        "enthalpy rejected without PV evidence; explicit ideal limit retained": h_rejected
            and h_terms.pv_assumption is pv,
        "host and native begin/end source hashes equal": before == after and native_before == native_after
            and tree_before == tree_after,
        "new host module/test/script/docs LF bytes": all(b"\r" not in (root/name).read_bytes()
            for name in source_files[:4]),
    }
    elapsed = perf_counter()-started
    last = solutions[-1]
    lines = ["# Native pifira spin thermochemistry replay", "",
        "Reproduce: `python scripts/check_pifira_spin.py` with the separately installed native targets.", "",
        f"pifira{distribution.version}; SciPy{importlib.metadata.version('scipy')}; "
        f"CoolProp{importlib.metadata.version('CoolProp')}; elapsed={elapsed:.6g}s. "
        "No native engine/source was modified and no printed correlation coefficients or tables were copied. "
        "All calculations are numerical verification or synthetic assumptions, not an independent measured comparison.", "",
        "The native parity-resolved rotor returns rotational U relative to para J=0 and frozen-species Cv. "
        "The conversion gap is Uortho-Upara and its temperature derivative is Cvortho-Cvpara. "
        "Equal molecular masses allow the existing LH2DT para fraction to map to native c_ortho=1-x_para. "
        "These are partial spectroscopic rotor contributions, not liquid-mixture EOS, density, full fluid U/H or tank pressure. "
        "A single common reference shift applies to both branches. H mapping requires explicit no-mole-change ideal-gas "
        "or caller-evidenced spin-independent PV; no ParaHydrogen/OrthoHydrogen pure-fluid energies are subtracted.", "",
        f"Selected native rotor cutoff={model.thermo.maximum_J}; reference cutoff={model.reference_thermo.maximum_J}; "
        f"theta={model.thermo.rotational_temperature_K:.12g}K. Native parameter fingerprint={model.parameter_fingerprint}. "
        "High20000K/128-versus192-level calculation is a mathematical limit only, outside the kinetic domain "
        "and without a molecular/dense-fluid applicability claim.", "",
        "| T K | Para equilibrium | Upara J/kg | Uortho J/kg | Gap J/kg | Gap derivative J/(kg K) |",
        "|---|---:|---:|---:|---:|---:|",
        *(f"| {p.equilibrium.temperature_k:.12g} | {p.equilibrium.para_fraction:.12g} | {p.para_energy_j_kg:.12g} | "
          f"{p.ortho_energy_j_kg:.12g} | {p.conversion_energy_j_kg:.12g} | {p.conversion_energy_temperature_derivative_j_kg_k:.12g} |" for p in points), "",
        f"High-limit para fraction={high.equilibrium.para_fraction:.12g}; Cvpara/R={high.para_cv_j_kg_k/model.thermo.gas_constant_J_kgK:.12g}; "
        f"Cvortho/R={high.ortho_cv_j_kg_k/model.thermo.gas_constant_J_kgK:.12g}. "
        f"Matched LH2DT equilibrium max difference={matched_equilibrium_error:.12g}.", "",
        "Energy finite differences use dT=1e-4*T. Below are maximum absolute derivative errors in J/(kg K), "
        "against the native Cv and native gap derivative; this verifies actual temperature-dependent energies.", "",
        f"ParaCv max={float(fd[:, 3].max()):.12g}; orthoCv max={float(fd[:, 6].max()):.12g}; gap derivative max={float(fd[:, 9].max()):.12g}.", "",
        "Native strict Milenko accepts liquid17-32K, gas40-120K, density up to92kg/m3 and primary ortho0.62-0.75. "
        "The public primary publisher abstract states density up to0.09g/cm3=90kg/m3; host admission conservatively caps90. "
        "This discrepancy remains explicit. Native parameter domains cannot be widened by the adapter. "
        "Phase/T/rho/composition admission is a necessary envelope screen, not validation of every combination. "
        "Frozen normal-H2 density references below retain their native property basis and an authored fixed-density "
        "composition approximation; they do not become evolving-spin EOS. Native converts kg/m3 to g/cm3 internally "
        "and its printed-rate units to1/s; no host rate formula is implemented.", "",
        "| Prescribed frozen density reference | Native branch | Density kg/m3 | k_forward 1/s | Para rate at c=.7 1/s | Heat at c=.7 W |",
        "|---|---|---:|---:|---:|---:|",
        *(f"| {m.frozen_density_reference.pressure_pa:.12g}Pa /{m.temperature_k:.12g}K | {m.phase} | {m.density_kg_m3:.12g} | "
          f"{float(r.native_forward_rate_per_s):.12g} | {r.para_fraction_rate_s:.12g} | {r.conversion_heat_w:.12g} |" for m, c, r in rates if c == .7), "",
        f"24 native rate points were executed across the eight media and three primary compositions. "
        f"Dilute native density-rate ratio={dilute_ratio:.12g}. Native reverse-threshold records count="
        f"{len(native.PETITPAS_REVERSE_VALIDITY_THRESHOLDS)}; their numeric table is not reproduced and does not override strict primary bounds.", "",
        "Detailed-balance probing explicitly calls the native mathematical extension only after strict medium admission. "
        "It labels low-ortho values unadmitted; pure-para c=0 is an absorbing state of this native law even when "
        "thermal equilibrium c is nonzero. Zero at equilibrium and correct nearby signs do not establish a universal reverse-conversion kinetic law. "
        "No catalyst or zero-rate fallback is inferred.", "",
        "The next calculation injects the actual native rate and rotor thermostat power into an external generic "
        "SciPy DOP853 verification driver. The library adds no advance, finite calorimeter ODE or trajectory API. "
        "A constant-T quadratic-law closed form provides an independent integration oracle, using native k and equilibrium "
        "without copying rate coefficients. Three driver settings(max_step/rtol)=(1000/1e-8,500/1e-10,250/1e-12)s "
        "use the absolute[100,10100]s clock, mass0.02kg, initial ortho0.7, actual frozen reference liquid density "
        "at20K/200000Pa, and an explicit rotor-bath thermostat. The path stays within the primary composition range.", "",
        f"Final para={last.y[0, -1]:.12g}; final external heat={last.y[1, -1]:.12g}J; "
        f"max composition errors={fraction_errors}; max delta-U-minus-Q residuals J={energy_errors}. "
        f"Analytic time to lower primary ortho boundary at these held inputs={time_to_lower_boundary:.12g}s; "
        "no continuation below that boundary is admitted. No complete low-ortho long-duration storage path is predicted.", "",
        f"Variable-T/composition energy tangent error={chain_error:.12g}W; common-zero shift error={energy_shift_error:.12g}J. "
        "Absolute rotor U/Cv belongs with a nonrotational sensible baseline. A full frozen EOS already contains rotational "
        "storage; callers instead request an evidenced frozen-composition correction. Identical actual/baseline composition "
        "gives zero correction. A general finite-energy driver still needs total positive heat capacity, density/phase/PV closure, "
        "strict kinetic-domain termination and a total-system energy ledger. The existing constant-gap calorimeter cannot "
        "silently accept the T-dependent native gap. It remains unchanged.", "",
        "| Verification gate | Pass |", "|---|---|", *(f"| {name} | {passed} |" for name, passed in gates.items()), "",
        "Primary sources: [Petitpas2014](https://doi.org/10.1016/j.ijhydene.2014.01.205), "
        "[Milenko1997 publisher record](https://link.springer.com/article/10.1007/BF02396837), "
        "[public native source/release](https://github.com/lyullee/pifira). "
        "The existing MIT dependency review is research/pifira_dependency.toml; code/data rights are separate. "
        "No original paper, coefficient table, reverse-threshold table, experimental history or external dataset is redistributed. "
        "Experimental apparatus-transfer and dense-fluid caloric/EOS qualification remain open.", "",
        "## Source fingerprints", "", f"Ordered pifira Python tree SHA256 begin={tree_before}; end={tree_after}.", "",
        "New host input bytes were checked as LF-only; generated report uses explicit LF newlines.", "",
        "| Host input | Begin SHA256 | End SHA256 |", "|---|---|---|",
        *(f"| {name} | {digest} | {after[name]} |" for name, digest in before.items()), "",
        "| Native input | Begin SHA256 | End SHA256 |", "|---|---|---|",
        *(f"| {name} | {digest} | {native_after[name]} |" for name, digest in native_before.items()), ""]
    (root/"research/native_spin_thermochemistry.md").write_text("\n".join(lines), encoding="utf-8", newline="\n")
    for name, passed in gates.items():
        print(f"{'PASS' if passed else 'FAIL'} {name}", flush=True)
    print(f"Actual native replay {elapsed:.6g}s; research/native_spin_thermochemistry.md", flush=True)
    return 0 if all(gates.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
