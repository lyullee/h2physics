"""Native closed loading-LDF bed: component and total energy conservation."""

import hashlib
import sys
from pathlib import Path

import numpy as np
from scipy.integrate import solve_ivp

from h2physics.adapters.psa import BedFaceTransfers, PsaDynaBed
from h2physics.adsorption import AdsorptionBasis, AdsorptionDomain


def main():
    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root / "artifacts/native_packages"))
    from psa_dynamic.core import Bed

    material = {"name": "authored closed-bed fixture", "end_fraction": 1.,
        "a1": [[.3], [.2]], "b0_per_bar": [[.02], [.04]],
        "binding_energy_j_mol": [[2000.], [3000.]], "ldf_per_s": [.1, .05]}
    spec = {"n_cells": 4, "diameter_m": .1, "length_m": .5, "void_fraction": .4,
        "particle_diameter_m": .002, "bulk_density_kg_m3": 500., "solid_cp_j_kg_k": 700.,
        "ambient_k": 300., "materials": [material], "wall_thickness_m": .003,
        "wall_density_kg_m3": 7800., "wall_cp_j_kg_k": 500., "wall_k_w_m_k": 10.,
        "bed_k_w_m_k": .25, "h_bed_wall_w_m2_k": 10., "h_ambient_w_m2_k": 0.,
        "wall_model": "dynamic_lumped", "energy_mode": "internal_energy", "kinetics": "loading_ldf"}
    species = [{"name": "H2", "mw_kg_mol": .002, "cp_j_mol_k": 29.},
               {"name": "N2", "mw_kg_mol": .028, "cp_j_mol_k": 29.}]
    signature = hashlib.sha256(repr((spec, species)).encode()).hexdigest()
    basis = AdsorptionBasis("authored-warm-bed", ("H2", "N2"), "absolute:dry-adsorbent",
        "psa-dyna:0.1.0:a26a8ef687c90cd4a5c18d38aaa4209ea5c5dcd6", signature,
        ("https://github.com/lyullee/psa-dyna",), loading_definition="absolute")
    native = Bed(spec, species)
    bed = PsaDynaBed(native, basis, AdsorptionDomain(290, 350, 1e6),
                     energy_reference_id="authored:gas-constant-Cv-from-0K;solid-wall-298.15K;native-binding-energy")
    initial = native.initial(1., [.8, .2], 300.).reshape(native.n, native.nv)
    initial[:, :native.ns] *= 2  # instantaneous authored gas addition before t=0
    initial = initial.ravel()
    transfers = BedFaceTransfers(basis.species, np.zeros((native.n+1, native.ns)),
                                 np.zeros(native.n+1), bed.energy_reference_id)
    solution = solve_ivp(lambda t, state: bed.rates(state, transfers)[0], (0, 50), initial,
                         method="BDF", rtol=1e-9, atol=1e-11, t_eval=np.linspace(0, 50, 101))
    if not solution.success:
        raise RuntimeError(solution.message)
    snapshots = [bed.snapshot(state) for state in solution.y.T]
    start, end = snapshots[0], snapshots[-1]
    component_residual = max(float(np.max(abs(s.total_inventory_mol-start.total_inventory_mol))) for s in snapshots)
    energy_residual = max(abs(s.stored_energy_j-start.stored_energy_j) for s in snapshots)
    if component_residual > 1e-9 or energy_residual > 1e-5:
        raise RuntimeError("Native closed bed conservation gate failed")
    lines = ["# Native closed adsorption-bed verification", "",
        f"Parameter representation SHA-256: `{signature}`. The full authored fixture is in the verification script.", "",
        "Four equal finite-volume cells, H2/N2 loading LDF, dynamic wall, no ambient heat or "
        "face transfers. The initial native 1-bar equilibrium state receives a doubled "
        "gas inventory before t=0; it then relaxes in a closed system. Uniform conditions "
        "make this a kinetic/thermal and interface check, not a transport/grid study or PSA cycle.", "",
        f"- Maximum component-inventory residual: {component_residual:.9g} mol.",
        f"- Maximum total-energy residual: {energy_residual:.9g} J.",
        f"- Final pressure: {end.pressure_pa[0]:.9g} Pa.",
        f"- Final bed temperature: {end.temperature_k[0]:.9g} K.",
        f"- Explicit energy reference: `{bed.energy_reference_id}`.", "",
        "The adapter retains the actual native Bed/rates implementation and exposes immutable "
        "SI snapshots. Face-transfer species and energy references must match. The current "
        "native fields function rejects bed temperatures ≤100 K or ≥1000 K; this warm "
        "verification does not authorize 20 K cryo-adsorption. See the separate extension request."]
    (root / "research/native_psa_bed.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("native PSA bed", component_residual, energy_residual)


if __name__ == "__main__":
    main()
