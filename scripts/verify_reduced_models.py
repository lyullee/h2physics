"""Record analytic and conservation checks for original reduced model levels."""

from pathlib import Path

import numpy as np

from h2physics.materials import DiffusionSlab, HydrogenCarrier, SlabBoundary, SurfaceCondition
from h2physics.storage import (
    ArrheniusRate,
    HydrideBed,
    HydrideBoundary,
    HydrideKinetics,
    HydrideParameters,
    HydrideState,
    VanthoffPlateau,
)


def main():
    root = Path(__file__).resolve().parents[1]
    equilibrium = VanthoffPlateau(24000, 80, 100000)
    kinetics = HydrideKinetics(equilibrium, ArrheniusRate(.01, 0, 300), ArrheniusRate(.02, 0, 300))
    times = np.linspace(0, 100, 101)
    lines = ["# Reduced-model verification", "",
             "All parameters below are authored synthetic cases, not material fits. "
             "They test equations/numerics and do not establish experimental validity.", "",
             "## Hydride analytic limit", "",
             "At constant 300 K, Peq=100 kPa, f=200 kPa, k_abs=0.01/s and x0=0.1, "
             "the independent isothermal solution is x(t)=1−0.9 exp(−0.01t). "
             "The zero reaction-heat case isolates that kinetic limit.", "",
             "| Relative tolerance | Max fraction error | Max reduced heat residual J |",
             "|---:|---:|---:|"]
    for tolerance in (1e-6, 1e-8, 1e-10):
        bed = HydrideBed(HydrideParameters(.002, 1000, 0, .002, 0), kinetics)
        result = bed.simulate(times, HydrideState(.1, 300), lambda t, s: HydrideBoundary(200000, 300),
                               relative_tolerance=tolerance)
        error = np.max(abs(result.fraction - (1-.9*np.exp(-.01*times))))
        lines.append(f"| {tolerance:g} | {error:.9g} | {np.max(abs(result.reduced_energy_residual_j)):.9g} |")
    bed = HydrideBed(HydrideParameters(.002, 1000, 12000, .002, 0), kinetics)
    result = bed.simulate(times, HydrideState(.1, 300), lambda t, s: HydrideBoundary(200000, 300))
    lines += ["", f"With positive reaction heat and no boundary heat, the adiabatic "
              f"reduced energy residual is {np.max(abs(result.reduced_energy_residual_j)):.9g} J. "
              "Hydrogen stored is capacity × fraction; the caller must supply the opposite "
              "gas-reservoir transfer. This is not a full gas/vessel energy ledger.", "",
              "## Planar diffusion startup", "",
              "L=1 m, D=0.1 m²/s, initially empty slab; left concentration=1, right=0 mol/m³. "
              "At t=1 s the exact average concentration follows the integrated Fourier series "
              "0.5 − (4/pi²) sum over positive odd n of exp(−n² pi² D t/L²)/n².", "",
              "| Cells | Average concentration error mol/m³ | Max inventory residual mol/m² |",
              "|---:|---:|---:|"]
    odd = np.arange(1, 200, 2)
    exact = .5 - 4/np.pi**2*np.sum(np.exp(-odd**2*np.pi**2*.1)/odd**2)
    errors = []
    for cells in (10, 20, 40, 80):
        slab = DiffusionSlab(HydrogenCarrier("atomic_hydrogen", .001), 1., cells, lambda t: .1)
        result = slab.simulate(np.linspace(0, 1, 21), np.zeros(cells),
            boundary=lambda t: SlabBoundary(SurfaceCondition("concentration", 1), SurfaceCondition("concentration", 0)),
            temperature_k=lambda t: 300.)
        error = abs(np.mean(result.mobile_mol_m3[-1])-exact)
        errors.append(error)
        lines.append(f"| {cells} | {error:.9g} | {np.max(abs(result.inventory_residual_mol_m2)):.9g} |")
    lines += ["", "Successive grid error ratios: " + ", ".join(f"{a/b:.6g}" for a, b in zip(errors[:-1], errors[1:])) + ".",
              "Approximately fourfold reduction per doubled grid verifies the expected second-order spatial behavior.",
              "Closed finite-trap equilibrium, reversed permeation and entity/H2 flux conversion are tested in the suite.", "",
              "Electrolyzer/fuel-cell tests use one shared synthetic reaction-energy basis to "
              "check direction, Faraday stoichiometry, polarization limits and the power ledger. "
              "No empirical polarization calibration is claimed."]
    (root / "research/reduced_models.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("reduced model verification recorded; last diffusion error", errors[-1])


if __name__ == "__main__":
    main()
