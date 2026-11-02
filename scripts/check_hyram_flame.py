"""Replay actual HyRAM+ Flame; exit 1 preserves unresolved physical acceptance failures."""

import argparse
import hashlib
import importlib.metadata
import sys
from pathlib import Path
from time import perf_counter


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def native_tree(root):
    digest = hashlib.sha256()
    for path in sorted(root.rglob("*.py")):
        digest.update(path.relative_to(root).as_posix().encode())
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--hyram-packages", type=Path, required=True)
    parser.add_argument("--use-main-scipy", action="store_true",
                        help="Import the main environment's SciPy before adding the native target")
    args = parser.parse_args()
    if args.use_main_scipy:
        import scipy
    sys.path.insert(0, str(args.hyram_packages.resolve()))
    import hyram
    import numpy as np
    import scipy
    from hyram.phys import Flame, Fluid, Orifice
    from hyram.phys._flame import calc_transmissivity

    from h2physics.adapters.hyram_flame import (
        SteadyFlameWindow,
        fuel_origin_section_flows,
        run_hyram_flame,
    )
    from h2physics.core import Origin
    from h2physics.release import NozzleOpening, SourceLocation
    from h2physics.thermo.coolprop import CoolPropProperties

    root = Path(__file__).resolve().parents[1]
    paths = ("src/h2physics/adapters/hyram_flame.py", "tests/test_hyram_flame.py",
             "scripts/check_hyram_flame.py", "docs/NATIVE_JET_FIRE.md")
    before = {name: sha(root/name) for name in paths}
    package = Path(hyram.__file__).resolve().parent
    metadata = importlib.metadata.distribution("hyram")
    if metadata.version != "6.1":
        raise ValueError("This diagnostic replay checks the separately installed HyRAM+6.1")
    native_paths = ("phys/_flame.py", "phys/_jet.py", "phys/_comps.py", "phys/_therm.py",
                    "phys/_notional_nozzle.py", "phys/_fuel_props.py")
    native_before = {name: sha(package/name) for name in native_paths}
    tree_before = native_tree(package)
    license_path = Path(metadata.locate_file("hyram-6.1.dist-info/licenses/COPYING.txt"))
    license_before = sha(license_path)
    metadata_path = Path(metadata.locate_file("hyram-6.1.dist-info/METADATA"))
    metadata_before = sha(metadata_path)
    air = CoolPropProperties("Air").state_pt(101325., 293.15)
    window = SteadyFlameWindow("authored-steady-fire-clock", 10., 20.,
        "authored-reservoir-opening", "fixed-reservoir-and-established-burning-premise", Origin.SYNTHETIC)

    def solve(pressure, diameter, count, tolerance, angle=0.):
        start = perf_counter()
        result = run_hyram_flame(fluid_factory=Fluid, orifice_factory=Orifice,
            flame_factory=Flame, transmissivity_function=calc_transmissivity,
            upstream=CoolPropProperties("Hydrogen").state_pt(pressure, 300.), ambient=air,
            opening=NozzleOpening.circular("authored-native-opening", diameter, effective_area_factor=.8,
                                           area_basis_id="native-Cd-times-geometric-area"),
            location=SourceLocation("authored-HP-H2-fire", "authored-incident", "global-xz",
                (0., 2., 2.), (float(np.cos(angle)), 0., float(np.sin(angle)))), window=window,
            solver_options={"Smax": 30., "tol": tolerance, "n_pts_integral": count},
            require_accepted=False)
        return result, perf_counter()-start

    started = perf_counter()
    coarse, coarse_s = solve(2e6, .002, 100, 1e-6)
    fine, fine_s = solve(2e6, .002, 300, 1e-7)
    finest, finest_s = solve(2e6, .002, 600, 1e-8)
    inclined, inclined_s = solve(20e6, .001, 300, 1e-7, np.pi/4)
    runs = (coarse, fine, finest, inclined)
    times = (coarse_s, fine_s, finest_s, inclined_s)
    tail = fuel_origin_section_flows(finest.native, radial_cutoff_widths=10.,
                                     radial_panels=48, quadrature_order=24)
    tail_difference = float(np.max(abs(tail-finest.fuel_origin_flows_kg_s)))
    chemistry = finest.native.chem
    derivatives = []
    for f in (.005, .1, .4, .8):
        step = 1e-7
        difference = (float(chemistry.rho_prod(f+step))-float(chemistry.rho_prod(f-step)))/(2*step)
        derivatives.append((f, float(chemistry.drhodf(f)), difference))
    fractions = np.linspace(.001, .999, 101)
    products = chemistry._Yprod(fractions)
    equivalent = products[chemistry.reac]+products["H2O"]*chemistry.MW[chemistry.reac]/chemistry.MW["H2O"]
    mixture_error = float(np.max(abs(equivalent-fractions)))
    points = np.array([[0., 5., 2.], [1., 5., 2.], [1., -1., 2.]])
    radiation = finest.irradiance(points, relative_humidity=.5, minimum_source_distance_m=.1,
                                 allow_rejected_flame=True)
    native = finest.native
    centre = np.array([(native.x.min()+native.x.max())/2, 2., (native.y.min()+native.y.max())/2])
    radius = 100*native.Lvis
    far = [finest.irradiance([centre+np.array([0., radius, 0.])], relative_humidity=.5,
        minimum_source_distance_m=.1, number_of_sources=n, allow_rejected_flame=True) for n in (25, 50, 100)]
    far_expected = finest.emitted_radiative_power_w*calc_transmissivity(radius, air.temperature_k, .5)/(4*np.pi*radius**2)
    far_error = abs(far[-1].irradiance_w_m2[0]/far_expected-1)
    radiation_refinement = abs(far[-1].irradiance_w_m2[0]-far[-2].irradiance_w_m2[0])/far_expected
    host_after = {name: sha(root/name) for name in paths}
    native_after = {name: sha(package/name) for name in native_paths}
    tree_after = native_tree(package)
    evidence_gates = {
        "actual native Flame objects executed": all(isinstance(r.native, Flame) for r in runs),
        "complete visible paths reached": all(r.gates["finite positive full-visible native flame"] for r in runs),
        "independent order/tail quadrature agrees <1e-12 kg/s": max(tail_difference,
            *(r.maximum_section_quadrature_difference_kg_s for r in runs)) < 1e-12,
        "f includes product water as conserved fuel origin, error <1e-7": mixture_error < 1e-7,
        "native source stagnation power audit passes": all(r.gates[
            "native throat and expansion stagnation energy"] for r in runs),
        "native emitted-power budgets pass": all(r.gates[
            "emitted radiation within native chemical-power budget"] for r in runs),
        "actual diagnostic radiation kernel gates pass": radiation.kernel_accepted,
        "diagnostic radiation remains unaccepted": not radiation.accepted and radiation.status == "diagnostic-unaccepted-flame",
        "out-of-plane symmetry relative <1e-12": abs(radiation.irradiance_w_m2[1]/radiation.irradiance_w_m2[2]-1) < 1e-12,
        "far-field attenuated inverse-square limit relative <1e-4": far_error < 1e-4,
        "50/100 radiation sources relative <1e-6": radiation_refinement < 1e-6,
        "native mass/caloric failures remain rejected under refinement": all(not r.accepted for r in runs)
            and finest.maximum_source_mass_residual_kg_s/finest.mass_flow_kg_s > .1,
        "host/test/script/docs begin/end hashes equal": before == host_after,
        "host module/test/script/docs are LF text": all(b"\r" not in (root/name).read_bytes()
                                                        for name in paths),
        "native source/tree/license/metadata begin/end hashes equal": native_before == native_after
            and tree_before == tree_after and license_before == sha(license_path)
            and metadata_before == sha(metadata_path),
    }
    elapsed = perf_counter()-started
    physical_acceptance = all(r.accepted for r in runs)
    lines = ["# Actual HyRAM+ jet-fire diagnostic replay", "",
        "Reproduce: `python scripts/check_hyram_flame.py --hyram-packages artifacts/native_hyram_packages`.", "",
        f"HyRAM+ {metadata.version}; SciPy {scipy.__version__}; CoolProp {importlib.metadata.version('CoolProp')}. "
        f"Four actual native Flame solves plus audits took {elapsed:.6g} s. "
        f"Full source-to-flame physical acceptance: **{physical_acceptance}**. "
        "The replay exits1 when physical acceptance fails, even if diagnostic verification gates pass.", "",
        "All cases are original synthetic numerical inputs: normal gaseous H2 at300K, "
        "calm Air101325Pa/293.15K, Cd0.8 circular opening. Global x/y/z uses z upward; "
        "source position(0,2,2)m. A caller-declared steady established-burning premise holds "
        "on absolute clock[10,20]s; no ignition, blowdown, transient duration or frequency is computed. "
        "Native HyRAM owns the only nozzle/choking and notional-expansion solve; no shared-nozzle exit is re-choked. "
        "No engine/source field or coefficient was changed to pass an audit.", "",
        "| Case | P0 Pa /d m /angle rad | Native radial points /tol | Native rows | Time s | mdot kg/s | Entry /end fuel-origin flux kg/s | Accepted |",
        "|---|---|---|---:|---:|---:|---|---|",
        *(f"| {name} | {p:.8g} /{d:.8g} /{angle:.8g} | {count} /{tol:g} | {len(r.centreline)} | {seconds:.6g} | "
          f"{r.mass_flow_kg_s:.12g} | {r.fuel_origin_flows_kg_s[0]:.12g} /{r.fuel_origin_flows_kg_s[-1]:.12g} | {r.accepted} |"
          for name, p, d, angle, count, tol, r, seconds in zip(
              ("coarse", "fine", "finest", "inclined"), (2e6, 2e6, 2e6, 20e6), (.002, .002, .002, .001),
              (0., 0., 0., np.pi/4), (100, 300, 600, 300), (1e-6, 1e-7, 1e-8, 1e-7), runs, times, strict=True)), "",
        "| Native physical acceptance gate | Coarse | Fine | Finest | Inclined |", "|---|---|---|---|---|",
        *(f"| {gate} | "+" | ".join(str(r.gates[gate]) for r in runs)+" |" for gate in coarse.gates), "",
        "The field audit independently integrates2*pi*r*rho_prod(f)*f*v dr. "
        "It uses the actual native Gaussian f/velocity widths and native reacting density. "
        "f denotes conserved fuel-origin material, including H2 bound in product water; unburned H2 is not conserved. "
        "The native ODE's last conservation row uses this same rho*f*v integrand. "
        "Splitting at actual native chemistry-table knots plus32 regular radial panels, Gauss orders8/16, "
        "and refined24-point/48-panel10B integration separates physical defects from quadrature error. "
        f"Maximum8B/10B difference={tail_difference:.12g}kg/s; product-based mixture-fraction check "
        f"max error={mixture_error:.12g}. No section has been rescaled to the nozzle flow.", "",
        "| Quantity, finest case | Observed |", "|---|---:|",
        f"| Source-to-field max mass defect /relative | {finest.maximum_source_mass_residual_kg_s:.12g}kg/s /{finest.maximum_source_mass_residual_kg_s/finest.mass_flow_kg_s:.12g} |",
        f"| Entry-to-downstream max transport defect | {finest.maximum_transport_mass_residual_kg_s:.12g}kg/s |",
        f"| Throat /expansion stagnation power defect | {finest.throat_energy_residual_w:.12g} /{finest.expansion_energy_residual_w:.12g}W |",
        f"| Native visible length /radiant fraction | {native.Lvis:.12g}m /{finest.radiant_fraction:.12g} |",
        f"| Native heat of combustion /chemical power /radiated power | {finest.native_heat_of_combustion_j_kg:.12g}J/kg /{finest.chemical_power_w:.12g}W /{finest.emitted_radiative_power_w:.12g}W |",
        f"| Native radiant-power identity residual | {finest.radiant_power_residual_w:.12g}W |",
        f"| Finest native warnings | {finest.warning_messages} |", "",
        "Native combustion uses a fixed100-point T(f) interpolation and an interpolated density derivative. "
        "The following compares its actual derivative with a central difference of its actual rho_prod(f), "
        "using df=1e-7 away from the stoichiometric kink. This diagnoses a native function inconsistency; "
        "the host does not replace that derivative or ODE.", "",
        "| f | Native drho/df kg/m3 | Direct rho finite difference kg/m3 |", "|---|---:|---:|",
        *(f"| {f:.12g} | {a:.12g} | {b:.12g} |" for f, a, b in derivatives), "",
        "The next direct-EOS audit evaluates actual native pure-fluid enthalpies at native T(f) and "
        "checks the native as-defined caloric equation. That equation multiplies reactant h by "
        "MWreactants/MWproducts before adding its heat of combustion. The unscaled mass-specific reference "
        "residual is shown separately and is not adopted as a new combustion model. Native pure-fluid zeros "
        "are not established common species formation energies. Combustion is initialized at ambient T/P, "
        "rather than the expanded cold-source state; radiation is postprocessed and does not cool the "
        "adiabatic product-temperature solution. No total radiating-flame energy closure is claimed.", "",
        "| f | Native T K | Released heat J/kg | Native MW factor | Direct-EOS native-equation defect J/kg | Unscaled reference defect J/kg |",
        "|---|---:|---:|---:|---:|---:|",
        *(f"| {row[0]:.12g} | {row[1]:.12g} | {row[2]:.12g} | {row[3]:.12g} | {row[6]:.12g} | {row[7]:.12g} |"
          for row in finest.combustion_caloric_audit), "",
        "Native multisource radiation is retained only as a diagnostic of an unaccepted flame. "
        "It returns scalar incident irradiance with each emitter facing the observer, not a specified "
        "receiver-normal/absorbed wall heat flux. Native atmospheric transmission must lie in[0,1] at every "
        "path; no humidity/path/flux clipping is performed. Positive normalized-source power bounds and "
        "a far-field inverse-square limit are independent geometry/power checks, not validation of the "
        "underlying flame or radiative correlation.", "",
        f"Diagnostic observer points global m={points.tolist()}; irradiance W/m2={radiation.irradiance_w_m2.tolist()}. "
        f"Status={radiation.status}; kernel accepted={radiation.kernel_accepted}; whole-chain accepted={radiation.accepted}. "
        f"RH=.5; excluded emitter distance=.1m; actual min path={radiation.minimum_path_m:.12g}m; "
        f"tau range={radiation.minimum_transmissivity:.12g}..{radiation.maximum_transmissivity:.12g}. "
        f"Far-field relative error={far_error:.12g};50/100-source difference={radiation_refinement:.12g}.", "",
        "| Diagnostic verification gate | Pass |", "|---|---|",
        *(f"| {name} | {passed} |" for name, passed in evidence_gates.items()), "",
        "The existing unignited HyRAM Gaussian-jet mass failure remains separate and unchanged. "
        "This Flame evidence does not qualify a jet-fire family, heat dose, ignition/fatality model, "
        "receiver boundary, facility fire scenario or measured experiment. No independent measured comparison "
        "has been performed. Required native work includes source-matched reacting initialization, "
        "consistent rho/derivative functions, explicit caloric references and interpolation error control, "
        "and retained native solver status. Full mass/energy gates must be rerun after a reviewed revision.", "",
        "Primary sources: [HyRAM+6.1 official release and manuals](https://hyram.sandia.gov/), "
        "[native6.0 technical reference](https://doi.org/10.2172/2563814), "
        "[Ekoto et al. buoyancy/radiation model](https://doi.org/10.1016/j.ijhydene.2014.03.235), "
        "[public native API/source](https://github.com/sandialabs/hyram). "
        "HyRAM+ is separately installed under GPL-3.0-only; source/coefficient tables/mechanisms/examples "
        "are not copied into these five host files. No new external dataset is downloaded or redistributed.", "",
        "## Reproduction fingerprints", "",
        "Host module/test/script/docs were checked as LF-only bytes. The generated report is written with explicit LF newlines.", "",
        f"Ordered native hyram/*.py relative-name+NUL+bytes+NUL SHA256 begin={tree_before};end={tree_after}.", "",
        f"Native GPL COPYING.txt SHA256 begin={license_before};end={sha(license_path)}.", "",
        f"Native6.1 METADATA SHA256 begin={metadata_before};end={sha(metadata_path)}.", "",
        "| Host input | Begin SHA256 | End SHA256 |", "|---|---|---|",
        *(f"| {name} | {digest} | {host_after[name]} |" for name, digest in before.items()), "",
        "| Native input | Begin SHA256 | End SHA256 |", "|---|---|---|",
        *(f"| {name} | {digest} | {native_after[name]} |" for name, digest in native_before.items()), ""]
    (root/"research/native_jet_fire.md").write_text("\n".join(lines), encoding="utf-8", newline="\n")
    for name, passed in evidence_gates.items():
        print(f"{'PASS' if passed else 'FAIL'} diagnostic verification: {name}", flush=True)
    for name, passed in finest.gates.items():
        print(f"{'PASS' if passed else 'FAIL'} physical acceptance: {name}", flush=True)
    print(f"Native elapsed {elapsed:.6g}s; whole-chain accepted={physical_acceptance}; research/native_jet_fire.md", flush=True)
    return 0 if physical_acceptance and all(evidence_gates.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
