"""Run actual preferred native dispersion providers without bundling their code."""

import argparse
import hashlib
import importlib.metadata
import sys
import time
from pathlib import Path


def fingerprint(root):
    paths = sorted(root.rglob("*.py"))
    digest = hashlib.sha256()
    for path in paths:
        digest.update(path.relative_to(root).as_posix().encode())
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--hyram-packages", type=Path, required=True)
    parser.add_argument("--slabx-packages", type=Path, required=True)
    args = parser.parse_args()
    hyram_path, slab_path = args.hyram_packages.resolve(), args.slabx_packages.resolve()
    sys.path[:0] = [str(hyram_path), str(slab_path)]
    import numpy as np
    import scipy
    from hyram.phys import Fluid, Jet, Orifice
    from slabx.core.plume import run_dispersion
    from slabx.core.source import EvaporatingPool
    from slabx.submodels.atmosphere import Atmosphere
    from slabx.thermo.coolprop import CoolPropThermo, coolprop_water, pseudo_component
    from slabx_lh2.diagnostics import premise_summary
    from slabx_lh2.plume_width import plume_width_coupling
    from slabx_lh2.water_ice import with_sublimation

    from h2physics.adapters.hyram import run_hyram_gas_jet
    from h2physics.adapters.slabx_lh2 import run_slabx_lh2, steady_vapor_pool_boundary
    from h2physics.core import Origin
    from h2physics.release import NozzleOpening, SourceLocation
    from h2physics.sources import IntervalMassSource
    from h2physics.thermo.coolprop import CoolPropProperties

    root = Path(__file__).resolve().parents[1]
    host_paths = ("src/h2physics/dispersion.py", "src/h2physics/adapters/hyram.py",
                  "src/h2physics/adapters/slabx_lh2.py", "scripts/check_preferred_dispersion.py")
    hashes = {p: hashlib.sha256((root/p).read_bytes()).hexdigest() for p in host_paths}
    if scipy.__version__ != "1.16.3":
        raise RuntimeError("Replay expects the explicitly qualified SciPy 1.16.3 native target")
    properties = CoolPropProperties("Hydrogen")
    ambient = CoolPropProperties("Air").state_pt(101325, 293.15)
    gas_location = SourceLocation("authored-HP-H2", "authored", "global-xz", (0, 0, 2), (1, 0, 0))
    started = time.perf_counter()
    gas = run_hyram_gas_jet(fluid_factory=Fluid, orifice_factory=Orifice, jet_factory=Jet,
        upstream=properties.state_pt(2e6, 300), ambient=ambient,
        opening=NozzleOpening.circular("authored-2mm", .002, effective_area_factor=.8,
                                       area_basis_id="native-orifice-Cd-area"),
        location=gas_location, evidence_id="authored-high-pressure-native-check",
        solver_options={"Smax": 2., "numpts": 100}, require_accepted=False)
    gas_seconds = time.perf_counter()-started
    print("HyRAM", gas.accepted, gas.mass_flow_kg_s, gas.maximum_h2_flux_residual_kg_s, flush=True)
    location = SourceLocation("authored-LH2-vapor", "authored-finite-window", "pool-relative",
                              (0, 0, 0), (0, 0, 1))
    vapor = properties.saturated(101325, 1.)
    finite_source = IntervalMassSource(location, np.array([10., 20., 30.]), np.array([.01, .01]),
                                       vapor, Origin.SYNTHETIC, "authored-vapor-source", "isolation")
    substance = pseudo_component("Hydrogen", {"Hydrogen": 1.}, p_ambient=101325)
    boundary = steady_vapor_pool_boundary(finite_source, native_pool_factory=EvaporatingPool,
        substance=substance, area_m2=1., footprint_evidence_id="authored-fixed-horizontal-area",
        ambient_pressure_pa=101325)
    emission = CoolPropThermo(substance)
    water = with_sublimation(coolprop_water())
    pool_runs = []
    pool_seconds = []
    for wind in (5., .2):
        atm = Atmosphere(u_ref=wind, z_ref=10., T=293.15, rh=40., z0=.01, stability="D")
        started = time.perf_counter()
        run = run_slabx_lh2(boundary=boundary, atmosphere=atm, emission_thermo=emission,
            water_thermo=water, runner=run_dispersion, premise_check=premise_summary,
            width_context=plume_width_coupling, width_coupling=True,
            x_max_m=20., require_accepted=False)
        pool_runs.append((wind, run))
        pool_seconds.append(time.perf_counter()-started)
        print("SLABx-LH2", wind, run.accepted, dict(run.premise), run.source_area_change_m2, flush=True)
    versions = {name: importlib.metadata.version(name) for name in ("hyram", "slabx", "slabx-lh2")}
    lines = ["# Preferred native dispersion-provider checks", "",
        "The user selects HyRAM+ for high-pressure gaseous-H2 dispersion and SLABx-LH2 "
        "for LH2-origin dispersion. These actual native checks are authored numerical/software "
        "cases, not new independent experimental validation. Existing DEGALI comparison records "
        "retain their results and limits.", "",
        f"Native versions: {versions}; SciPy {scipy.__version__}; NumPy {np.__version__}.", "",
        "HyRAM+ 6.1 is separately installed under GPL-3.0-only. The default SciPy 1.18.1 "
        "run raised a dopri5 solout callback TypeError; the compatible target uses SciPy 1.16.3 "
        "without changing native equations or patching global callbacks. SLABx 1.0.8 and "
        "SLABx-LH2 0.2.0 are separately installed MIT source revisions, not assumed equal "
        "to the PyPI LH2 0.1.5 release. Native code/mechanisms/data are not bundled by this host.", "",
        "## High-pressure gas case", "",
        "Authored normal H2 at 2 MPa/300 K, 2 mm opening, native Cd 0.8, calm air at "
        "101325 Pa/293.15 K, horizontal source 2 m above the declared datum. HyRAM owns "
        "its orifice, notional expansion, establishment and jet. An already solved shared "
        "nozzle is not passed through another choking stage. Requested arclength is 2 m; "
        "actual native integration extent is retained, including its endpoint overshoot.", "",
        f"Native flow {gas.mass_flow_kg_s:.12g} kg/s, maximum Gaussian-section H2 flux residual "
        f"{gas.maximum_h2_flux_residual_kg_s:.12g} kg/s, budget {gas.mass_budget_kg_s:.12g} kg/s; "
        f"material/finite-output gate {'PASS' if gas.accepted else 'FAIL'}. "
        f"Actual final S={gas.centreline[-1,0]:.12g} m; {len(gas.centreline)} centreline samples. "
        "This gate does not independently audit native constant-Cp energy or field accuracy.", "",
        f"Gaussian-entry H2 transport is {gas.gaussian_entry_h2_flow_kg_s:.12g} kg/s "
        f"({gas.gaussian_entry_h2_flow_kg_s/gas.mass_flow_kg_s:.12g} of upstream native flow). "
        f"Maximum downstream drift from that entry is {gas.maximum_transport_h2_residual_kg_s:.12g} kg/s. "
        "The initialization jump is therefore distinct from ODE transport drift. The native "
        "expanded plug preserves the upstream mass in this case; host audit rejects the "
        "plug-to-Gaussian mismatch without changing lambda or fitting a scalar correction.", "",
        "## LH2-origin resolved vapor case", "",
        "Authored atmospheric saturated normal-H2 vapor, fixed horizontal area 1 m2, upward "
        "mass flux 0.001 kg/s over absolute source-clock [10,30] s; total 0.02 kg, ending by "
        "declared isolation. The native duration is 20 s and its relative time must not be "
        "confused with that absolute clock. No nozzle-to-ground fraction or real pool radius "
        "is inferred. Native CoolProp emission and water/ice providers and explicitly enabled "
        "width coupling are retained. A steady source cannot silently consume variable bins.", "",
        "| Wind m/s at 10 m | Native max w_c/u | Premise violated | Area change m2 | Source mass residual kg | Host gate |",
        "|---:|---:|---|---:|---:|---|"]
    lines += [f"| {wind:g} | {r.premise['max']:.12g} | {r.premise['violated']} | "
              f"{r.source_area_change_m2:.12g} | {r.source_mass_residual_kg:.12g} | "
              f"{'PASS' if r.accepted else 'FAIL'} |" for wind, r in pool_runs]
    lines += ["", "A violated/nonfinite post-run premise or changed fixed-source area is rejected "
        "by default, with the raw native result retained. It does not route to DEGALI. "
        "Source mass agreement is separate from native plume/puff energy, finite-source "
        "travel, physical footprint and experimental concentration qualification.", "",
        f"Local native call times: HyRAM {gas_seconds:.6g} s; SLAB high/low wind "
        f"{pool_seconds[0]:.6g}/{pool_seconds[1]:.6g} s. These are observed calls during "
        "concurrent local development, excluding imports; they are not a comparative benchmark.", "",
        "## Fingerprints", "", "| Component | SHA-256 |", "|---|---|"]
    for folder in (hyram_path/"hyram", slab_path/"slabx", slab_path/"slabx_lh2"):
        lines.append(f"| installed {folder.name} Python paths/bytes | `{fingerprint(folder)}` |")
    lines += [f"| {name} | `{digest}` |" for name, digest in hashes.items()]
    if hashes != {p: hashlib.sha256((root/p).read_bytes()).hexdigest() for p in host_paths}:
        raise RuntimeError("Host implementation changed during the check")
    (root/"research/preferred_dispersion.md").write_text("\n".join(lines)+"\n", encoding="utf-8", newline="\n")
    return 0 if gas.accepted and pool_runs[0][1].accepted else 1


if __name__ == "__main__":
    raise SystemExit(main())
