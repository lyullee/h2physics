"""Actual HEOS finite-cavity and shared radial-diffusion verification."""

import argparse
import hashlib
from pathlib import Path
from time import perf_counter

import numpy as np

from h2physics.materials import (
    DiffusionDomain,
    DiffusionMesh,
    HydrogenCarrier,
    PowerLawSolubility,
    SurfaceCondition,
    TransportBoundary,
)
from h2physics.storage.finite_hydride import HydrideGasThermodynamics
from h2physics.storage.microsphere import MicrosphereDomain, MicrosphereStorage


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", type=Path, default=Path("research/microsphere_storage.md"))
    args = parser.parse_args()
    import CoolProp
    import CoolProp.CoolProp as cp
    import scipy

    root = Path(__file__).resolve().parents[1]
    sources = ("src/h2physics/materials/finite_volume.py", "src/h2physics/materials/transport.py",
        "src/h2physics/materials/__init__.py", "src/h2physics/storage/microsphere.py",
        "src/h2physics/storage/__init__.py", "src/h2physics/storage/finite_hydride.py",
        "src/h2physics/thermo/coolprop.py", "tests/test_microsphere.py",
        "tests/test_curvilinear_diffusion.py", "tests/test_materials.py",
        "scripts/check_microsphere_storage.py")
    def hashes():
        return {p: hashlib.sha256((root/p).read_bytes()).hexdigest() for p in sources}

    before = hashes()
    start = perf_counter()
    carrier = HydrogenCarrier("molecular_hydrogen", .002)
    exact_rate = 4*np.pi*.1/(1.-.5)
    mesh = DiffusionMesh.spherical_shell(1., 2., 24)
    def boundary(t):
        return TransportBoundary(SurfaceCondition("concentration", 1.),
                                 SurfaceCondition("concentration", 0.))
    steady_c = (1/mesh.cell_centers_m-.5)/.5
    steady = DiffusionDomain(carrier, mesh, lambda t: .1).simulate(
        [0., 1.], steady_c, boundary=boundary, temperature_k=lambda t: 300.)
    k = np.arange(1, 201)
    exact_inventory = 4*np.pi*(.5+1/6)-8*np.pi*np.sum(
        (1.-2*(-1.)**k)/(k*np.pi)**2*np.exp(-.1*(k*np.pi)**2))
    errors, radial_rows = [], []
    for n in (20, 40, 80):
        grid = DiffusionMesh.spherical_shell(1., 2., n)
        result = DiffusionDomain(carrier, grid, lambda t: .1).simulate(
            [0., 1.], np.zeros(n), boundary=boundary, temperature_k=lambda t: 300.)
        error = abs(result.wall_inventory_mol[-1]-exact_inventory)
        errors.append(error)
        radial_rows.append((n, result.wall_inventory_mol[-1], error,
                            np.max(abs(result.wall_residual_mol))))

    runs, cavity_refinement = [], []
    independent = cp.AbstractState("HEOS", "Hydrogen")
    max_density_mole_error, max_fugacity_relative_error = 0., 0.

    def model(fluid, n, coefficient=1e-5):
        gas = HydrideGasThermodynamics.coolprop(fluid)
        return MicrosphereStorage(inner_radius_m=1e-5, outer_radius_m=1.1e-5, cells=n,
            diffusivity_m2_s=lambda t: 1e-14, solubility=PowerLawSolubility(
                HydrogenCarrier("molecular_hydrogen", gas.molar_mass_kg_mol),
                lambda t: coefficient, 1.), gas=gas,
            domain=MicrosphereDomain(200., 600., 1., 1e7, 1e-20),
            parameter_evidence="authored-constant-D-and-solubility-not-material-calibration")

    def simulate(storage, name, external=0., duration=100., sealed=False, heating=False):
        initial = storage.gas.state_pt(1e5, 300.)
        n0 = initial.density_kg_m3*storage.cavity_volume_m3/storage.gas.molar_mass_kg_mol
        outer = ({"external_wall_condition": lambda t, temp: SurfaceCondition("flux", 0.)}
                 if sealed else {"external_hydrogen_fugacity_pa": lambda t: external})
        result = storage.simulate(np.linspace(100., 100.+duration, 101), n0,
            np.zeros(len(storage.mesh.cell_centers_m)), temperature_k=(
                (lambda t: 300.+t-100.) if heating else (lambda t: 300.)),
            clock_id="authored-absolute-clock-100s", boundary_evidence=f"authored-{name}",
            relative_tolerance=1e-9, absolute_tolerance_mol_m3=1e-12,
            maximum_step_s=1., **outer)
        runs.append((name, storage, result))
        return result

    for n in (8, 16, 32):
        cavity_refinement.append(simulate(model("Hydrogen", n), f"normal-release-{n}"))
    charge = simulate(model("Hydrogen", 16), "normal-charge", external=2e5, duration=300.)
    sealed = simulate(model("Hydrogen", 16), "normal-closed-outer", sealed=True)
    para = simulate(model("ParaHydrogen", 16), "para-release")
    heating = simulate(model("Hydrogen", 16, coefficient=0.), "prescribed-heating", heating=True,
                       duration=20.)
    max_total_residual, max_gas_residual, max_wall_residual = 0., 0., 0.
    rows = []
    for name, storage, result in runs:
        n0 = result.gas_inventory_mol[0]
        max_total_residual = max(max_total_residual,
            float(np.max(abs(result.transport.total_residual_mol))/n0))
        max_gas_residual = max(max_gas_residual,
            float(np.max(abs(result.gas_transfer_residual_mol))/n0))
        max_wall_residual = max(max_wall_residual,
            float(np.max(abs(result.transport.wall_residual_mol))/n0))
        native = independent if storage.gas.basis.fluid == "Hydrogen" else cp.AbstractState(
            "HEOS", storage.gas.basis.fluid)
        for n, state, f in zip(result.gas_inventory_mol, result.gas_states,
                                result.gas_fugacity_pa, strict=True):
            native.update(cp.PT_INPUTS, state.pressure_pa, state.temperature_k)
            reconstructed = native.rhomolar()*storage.cavity_volume_m3
            max_density_mole_error = max(max_density_mole_error, abs(reconstructed-n)/n)
            max_fugacity_relative_error = max(max_fugacity_relative_error,
                                               abs(native.fugacity(0)-f)/f)
        rows.append((name, n0, result.gas_inventory_mol[-1], result.gas_states[-1].pressure_pa,
                     result.transport.wall_inventory_mol[-1], result.transport.right_integrated_mol[-1]))
    refinements = [r.gas_inventory_mol[-1] for r in cavity_refinement]
    refinement_ratio = abs(refinements[0]-refinements[1])/abs(refinements[1]-refinements[2])
    domain_rejections = []
    storage = model("Hydrogen", 4)
    for n, temperature in ((1e-22, 300.), (1e-13, 700.), (1e-8, 300.)):
        try:
            storage.gas_state(n, temperature)
        except ValueError:
            domain_rejections.append(True)
        else:
            domain_rejections.append(False)
    after = hashes()
    gates = {
        "host source bytes unchanged during execution": before == after,
        "spherical exact steady resistance relative error below 1e-10":
            abs(steady.left_integrated_mol[-1]/exact_rate-1) < 1e-10,
        "radial startup independent series converges at second order":
            errors[0]/errors[1] > 3.5 and errors[1]/errors[2] > 3.5,
        "finite-cavity mesh refinement ratio exceeds 3": refinement_ratio > 3.,
        "total mass-equivalent residual below 1e-10 of initial cavity": max_total_residual < 1e-10,
        "gas transfer residual below 1e-10 of initial cavity": max_gas_residual < 1e-10,
        "wall transfer residual below 1e-10 of initial cavity": max_wall_residual < 1e-10,
        "independent HEOS pressure-to-moles inversion error below 1e-8": max_density_mole_error < 1e-8,
        "independent native fugacity agreement below 1e-10": max_fugacity_relative_error < 1e-10,
        "charge increases cavity moles": charge.gas_inventory_mol[-1] > charge.gas_inventory_mol[0],
        "normal and para release decrease cavity moles": all(r.gas_inventory_mol[-1] < r.gas_inventory_mol[0]
            for r in (cavity_refinement[-1], para)),
        "sealed outer stores wall H2 with zero exterior transfer":
            sealed.transport.wall_inventory_mol[-1] > 0. and sealed.transport.right_integrated_mol[-1] == 0.,
        "prescribed warming increases pressure at fixed cavity inventory":
            heating.gas_states[-1].pressure_pa > heating.gas_states[0].pressure_pa
            and np.max(abs(heating.gas_inventory_mol/heating.gas_inventory_mol[0]-1)) < 1e-12,
        "floor temperature and pressure domain violations reject": all(domain_rejections),
    }
    elapsed = perf_counter()-start
    lines = ["# Shared spherical diffusion and finite microsphere verification", "",
        f"Actual local execution: CoolProp {CoolProp.__version__}, SciPy {scipy.__version__}; {elapsed:.9g}s.", "",
        "All cases and coefficients are authored numerical checks. No glass-specific fit, optical response, "
        "experimental validation or vessel qualification is claimed. The same finite-volume BDF core owns planar "
        "and spherical mobile/trap transport. Native gas objects and fugacity are reused from the existing "
        "finite-gas thermodynamics contract. No new EOS, nozzle or cavity trajectory ODE is implemented.", "",
        "For a shell the analytic steady total rate is 4*pi*D*(c_inner-c_outer)/(1/r_inner-1/r_outer). "
        "Integrated radial face resistance recovers that rate. The independent startup reference transforms "
        "u=r*c and integrates its sine-series solution over the true shell volume; 200 modes at positive time "
        "were used. It is not the discrete solver used as its own oracle.", "",
        "| Cells | Numerical wall mol | Absolute series error mol | Maximum wall residual mol |",
        "|---:|---:|---:|---:|", *(f"| {n} | {i:.12g} | {e:.12g} | {r:.12g} |" for n,i,e,r in radial_rows), "",
        "Cavity cases use inner/outer radii 10/11 micrometres, initial native 100000Pa(abs)/300K, "
        "D=1e-14m2/s, linear solubility coefficient=1e-5mol(H2)/(m3 Pa), and fixed-spin normal or para H2. "
        "These are demonstration inputs, not material properties. Absolute times start at100s. Most cases end "
        "at200s; charge ends400s with outside fugacity200000Pa; the prescribed warming ends120s at320K and "
        "uses zero solubility to isolate constant-inventory EOS heating. Sealed outer means zero flux, while "
        "ordinary release imposes zero outside fugacity. Both are explicit caller boundaries.", "",
        "| Case | Initial gas mol | Final gas mol | Final P Pa(abs) | Final wall mol | Outward exterior mol |",
        "|---|---:|---:|---:|---:|---:|", *(f"| {name} | {ni:.12g} | {nf:.12g} | {p:.12g} | {w:.12g} | {q:.12g} |"
            for name,ni,nf,p,w,q in rows), "",
        f"Cavity refinement ratio={refinement_ratio:.12g}. Maximum normalized defects: total "
        f"{max_total_residual:.12g}, gas {max_gas_residual:.12g}, wall {max_wall_residual:.12g}. "
        f"Independent native pressure-to-inventory reconstruction {max_density_mole_error:.12g}; "
        f"fugacity relative disagreement {max_fugacity_relative_error:.12g}.", "",
        "| Gate | Pass |", "|---|---|", *(f"| {name} | {passed} |" for name,passed in gates.items()), "",
        "Prescribed temperature is shared by wall and gas, without a computed thermostat duty or an energy "
        "closure claim. Geometry is rigid and single-sized. Deformation, burst, surface kinetics, optical "
        "enhancement, source-specific transport coefficients and actual thermal transients need independent "
        "evidence. A finite-inventory floor crossing rejects the requested window; it is not clipped or "
        "reported as a localized depletion event. Fixed-spin EOS does not predict spin conversion.", "",
        "Public primary context: [hydrogen permeation through glass](https://doi.org/10.3389/fmats.2019.00342), "
        "[molecular diffusion measurements](https://doi.org/10.1063/1.324180); native "
        "[CoolProp API](https://coolprop.org/coolprop/LowLevelAPI.html). No source coefficients, tables, "
        "worked examples or implementation code are reproduced.", "",
        "## Executed source identities", "", "| Host source | Begin SHA-256 | End SHA-256 |", "|---|---|---|",
        *(f"| `{p}` | `{before[p]}` | `{after[p]}` |" for p in sources), ""]
    target = args.report if args.report.is_absolute() else root/args.report
    target.write_text("\n".join(lines), encoding="utf-8", newline="\n")
    for name, passed in gates.items():
        print(f"{'PASS' if passed else 'FAIL'} {name}")
    print(f"Local calculation {elapsed:.6g}s; report {target.name}")
    return 0 if all(gates.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
