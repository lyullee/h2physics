"""Replay native contents-heat inversion, independent EOS forward power and area limits."""

import argparse
import hashlib
import sys
from importlib.metadata import version
from pathlib import Path
from time import perf_counter

import numpy as np

from h2physics.adapters.pifira_heat import (
    AxialContactGeometry,
    ClosedHeatDomain,
    ClosedHeatEvidence,
    EffectiveAreaEvidence,
    PifiraClosedVesselHeat,
    contents_equivalent_heat_flux,
    pifira_effective_area,
)
from h2physics.core import Origin, TimeSeries
from h2physics.thermo import CoolPropProperties


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--native-packages", default="artifacts/native_fire_packages")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    target = (root/args.native_packages).resolve()
    if target.is_dir():
        sys.path.insert(0, str(target))
    import pifira as native

    paths = ("src/h2physics/adapters/pifira_heat.py", "tests/test_pifira_heat.py",
             "scripts/check_pifira_heat.py", "src/h2physics/thermo/coolprop.py",
             "src/h2physics/core.py", "research/pifira_dependency.toml")
    before = {p: hashlib.sha256((root/p).read_bytes()).hexdigest() for p in paths}
    native_root = Path(native.__file__).parent

    def native_hashes():
        return {p.relative_to(native_root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in sorted(native_root.rglob("*.py"))}

    native_before = native_hashes()
    started = perf_counter()
    rows, traces, errors = [], [], []
    evidence = ClosedHeatEvidence("authored-native-heat", "sealed-no-material-ports", "rigid-volume",
        "homogeneous-two-phase-equilibrium", "fluid-U-only; wall/loss/work separate", Origin.SYNTHETIC)
    for fluid in ("Hydrogen", "ParaHydrogen", "OrthoHydrogen"):
        provider = CoolPropProperties(fluid)
        tank = native.TankSpec(volume=.04, fluid="HEOS::"+fluid, fill=.35)
        adapter = PifiraClosedVesselHeat(native, tank, provider, evidence=evidence,
            domain=ClosedHeatDomain(2e4, 8e5))
        mass = adapter.derive_initial_mass(1.5e5)
        density = mass/tank.volume
        u0 = provider.state_prho(1.5e5, density).internal_energy_j_kg
        for count in (9, 33):
            t = np.linspace(100., 120., count)
            dt = t-t[0]
            # Independent direct-EOS forward path: Q=1000+20*(t-100) W.
            states = [provider.state_rho_u(density, u0+(1000*x+10*x*x)/mass) for x in dt]
            history = TimeSeries(t, np.array([s.pressure_pa for s in states])[:, None], ("P",),
                ("Pa",), np.ones((count, 1), bool), "authored-heat-clock", Origin.SYNTHETIC,
                evidence.source_id, ("pressure",), ("absolute",))
            trace = adapter.run(history, "P", mass_kg=mass, mass_evidence_id="explicit-native-initial-fill")
            expected = 1000+20*(.5*(t[1:]+t[:-1])-100)
            error = float(np.max(abs(trace.interval_heat_w-expected)))
            errors.append(error)
            traces.append(trace)
            rows.append((fluid, count, mass, trace.states[-1].pressure_pa,
                float(np.max(abs(trace.native_minus_eos_energy_j))), error))
    fine = traces[3]  # Para-H2, 33 samples.
    coarse = traces[2]
    integrated_difference = abs(np.dot(fine.interval_heat_w, np.diff(fine.pressure_history.time_s))
        -np.dot(coarse.interval_heat_w, np.diff(coarse.pressure_history.time_s)))
    theta = np.array([-120., -60., 0., 60., 120.])
    ambient, sigma, amplitude = 295., 32., 8e10
    temperatures = (ambient**4+amplitude*np.exp(-.5*(theta/sigma)**2))**.25
    ae = EffectiveAreaEvidence(evidence.source_id, fine.pressure_history.clock_id,
        100., 100.625, "declared-geometric-centre", "authored-centered-local-Gaussian",
        "conditional-wetted-region", "fourth-power-equivalent", Origin.SYNTHETIC)

    def area(temps, amb, angles=theta, geometry=None):
        return pifira_effective_area(native, angles_deg=angles, wall_temperature_k=temps,
            ambient_temperature_k=amb, diameter_m=.4,
            axial_geometry=(AxialContactGeometry(0., .6, 0., .5, "authored-tank-axis")
                            if geometry is None else geometry),
            evidence=ae, maximum_normalized_fit_error=1e-5)

    a = area(temperatures, ambient)
    scaled = area(2*temperatures, 2*ambient)
    offset = area(temperatures, ambient,
        geometry=AxialContactGeometry(.3, .9, 0., .5, "authored-tank-axis"))
    disjoint = area(temperatures, ambient,
        geometry=AxialContactGeometry(.8, 1.4, 0., .5, "authored-tank-axis"))
    expected_area = np.pi*.4*(np.sqrt(2*np.pi)*32/360)*.5
    flux = contents_equivalent_heat_flux(fine, 0, a,
        allocation_evidence_id="authored-contents-energy-over-declared-area; not-incident-fire")
    rejected = {}
    attempts = {
        "single-phase inventory": lambda: adapter.run(history, "P", mass_kg=.02, mass_evidence_id="invalid-gas"),
        "truncated angular tails": lambda: area((ambient**4+amplitude*np.exp(-.5*(np.array([-20,-10,0,10,20])/sigma)**2))**.25,
            ambient, np.array([-20., -10., 0., 10., 20.])),
        "ordinary mean temperature statistic": lambda: EffectiveAreaEvidence(evidence.source_id,
            ae.clock_id, ae.start_s, ae.end_s, "centre", "shape", "wetted", "arithmetic-mean", Origin.SYNTHETIC),
        "zero overlap flux": lambda: contents_equivalent_heat_flux(fine, 0, disjoint,
            allocation_evidence_id="disjoint-geometry"),
    }
    for name, attempt in attempts.items():
        try:
            attempt()
            rejected[name] = False
        except ValueError:
            rejected[name] = True
    after = {p: hashlib.sha256((root/p).read_bytes()).hexdigest() for p in paths}
    native_after = native_hashes()
    gates = {
        "three actual pure H2 spin providers /two sample grids retain native objects": len(traces) == 6 and all(
            r.native_module is native and isinstance(r.native_tank, native.TankSpec) for r in traces),
        "independent forward-EOS interval power errors <1e-5 W": max(errors) < 1e-5,
        "independent native-vs-direct-EOS total U errors <1e-5 J": max(r[4] for r in rows) < 1e-5,
        "two output grids preserve integrated total contents heat <1e-5 J": integrated_difference < 1e-5,
        "all native fixed-mass states stay explicitly two phase": all(s.phase == "two_phase"
            and s.vapor_mass_fraction is not None for r in traces for s in r.states),
        "native centered Gaussian sigma/area agree with independent analytic geometry":
            abs(a.native_fit["sigma"]-sigma) < 1e-9 and abs(a.area_m2-expected_area) < 1e-12,
        "doubling absolute temperatures preserves shape/area": abs(a.area_m2-scaled.area_m2) < 1e-12,
        "explicit offset intervals give0.2m overlap and disjoint intervals give zero area":
            abs(offset.height_m-.2) < 1e-12 and abs(offset.area_m2-.4*a.area_m2) < 1e-12
            and disjoint.height_m == 0. and disjoint.area_m2 == 0.,
        "native kW/m2 to SI W/m2 and explicit allocation retained":
            abs(flux.flux_w_m2-fine.interval_heat_w[0]/a.area_m2) < 1e-9 and bool(flux.allocation_evidence_id),
        "all attempted domain/statistic failures remain rejections": all(rejected.values()),
        "native and executed-host begin/end source bytes match": before == after and native_before == native_after,
    }
    elapsed = perf_counter()-started
    lines = ["# Native pressure-rise contents heat and conditional area", "",
        "Reproduce: `python scripts/check_pifira_heat.py` with the separately installed inverse_heat extra/native target.", "",
        f"pifira{native.__version__}, CoolProp{version('CoolProp')}, SciPy{version('scipy')}; six native heat inversions "
        f"and three-spin direct-EOS forward paths completed in {elapsed:.6g}s. No native source or source data is bundled.", "",
        "Original authored verification case: rigid0.04m3 vessel, initial liquid volume fill0.35 and pressure150000Pa(abs). "
        "Native initial mass is explicitly requested. Direct HEOS rho/U forward states use prescribed Q(t)=1000+20(t-100)W "
        "on absolute100–120s, independently yielding each pressure. Native inversion sees only that pressure history, "
        "fixed mass and actual TankSpec. Nine and33 output samples test interval-average power and total energy; "
        "no pressure or kinetic coefficient is fitted.", "",
        "The public API takes Pa absolute. Native gauge coordinates subtract its recorded101325Pa API zero, "
        "then native routines add it back; this is a reversible native unit conversion, not an atmospheric offset "
        "inferred from a measured gauge sensor. Direct native/EOS U checks enforce material/energy-reference agreement. "
        "Every sampled fixed-density state must stay within the declared two-phase domain; unobserved between-sample "
        "paths, mass/volume closure and missing wall/loss/work boundaries are not inferred.", "",
        "| Fluid | Samples | Fixed mass kg | Final P Pa(abs) | Max native/EOS U error J | Max forward-power error W |",
        "|---|---:|---:|---:|---:|---:|", *(f"| {f} | {n} | {m:.12g} | {p:.12g} | {u:.12g} | {q:.12g} |"
            for f, n, m, p, u, q in rows), "",
        f"Independent analytic angular drive uses295K ambient,8e10K4 amplitude,32degree sigma and five centered "
        f"angles[-120,-60,0,60,120]degrees. Native equivalent area is{a.area_m2:.12g}m2 for0.4m diameter and "
        f"[0,0.6]m flame /[0,0.5]m wetted intervals on one declared axis; fit residual{a.normalized_fit_error:.12g}. "
        f"An offset[0.3,0.9]m flame intersects the same wetted region over{offset.height_m:.12g}m; "
        f"[0.8,1.4]m is disjoint and gives{disjoint.area_m2:.12g}m2 with explicit flux rejection. Doubling all absolute "
        f"temperatures leaves the native area difference{abs(a.area_m2-scaled.area_m2):.12g}m2. "
        f"Explicit first-interval contents-equivalent flux is{flux.flux_w_m2:.12g}W/m2. It is not incident fire flux.", "",
        "| Gate | Pass |", "|---|---|", *(f"| {name} | {passed} |" for name, passed in gates.items()), "",
        "This is numerical/native-reference verification. The heat result is signed contents internal-energy rate. "
        "It does not separate incident radiation/convection, wall storage, losses, work, vents or spin conversion. "
        "The area interpretation assumes the evidenced centered local positive Gaussian radiation shape and wetted "
        "axial boundary. Ordinary mean T does not establish mean T^4; fourth-power-equivalent/instantaneous statistics "
        "and exact source/clock/interval identities remain explicit. Native fit failure, excessive arc/tail/residual "
        "and unavailable phase/EOS states are rejected. No acquired thermal experiment is fitted or called validated.", "",
        "Primary sources: [native pifira API](https://github.com/lyullee/pifira), "
        "[archived0.3.0 source](https://doi.org/10.5281/zenodo.22291661), "
        "[CoolProp low-level EOS](https://coolprop.org/coolprop/LowLevelAPI.html). The original host composition, "
        "forward cases and guards do not copy native implementation, published examples or experimental values.", "",
        "## Executed source identities", "", "| Host source | Begin SHA-256 | End SHA-256 |", "|---|---|---|",
        *(f"| `{name}` | `{sha}` | `{after[name]}` |" for name, sha in before.items()), "",
        "| Separately installed native file | Begin SHA-256 | End SHA-256 |", "|---|---|---|",
        *(f"| pifira/{name} | `{sha}` | `{native_after[name]}` |" for name, sha in native_before.items()), ""]
    (root/"research/native_fire_heat.md").write_text("\n".join(lines), encoding="utf-8", newline="\n")
    for name, passed in gates.items():
        print(f"{'PASS' if passed else 'FAIL'} {name}")
    print(f"Local calculation{elapsed:.6g}s; report: research/native_fire_heat.md")
    return 0 if all(gates.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
