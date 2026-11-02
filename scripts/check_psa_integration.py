"""Verify actual PSA-Dyna adsorption states and derivative unit conversions."""

import hashlib
import sys
from pathlib import Path

import numpy as np

from h2physics.adapters.psa import PsaDynaEquilibrium
from h2physics.adsorption import AdsorptionBasis, AdsorptionDomain, loading_working_capacity


def main():
    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root / "artifacts/native_packages"))
    import psa_dynamic
    import psa_dynamic.core as native

    revision = "a26a8ef687c90cd4a5c18d38aaa4209ea5c5dcd6"
    parameters = {"name": "authored two-species two-site verification",
        "a1": [[3., 1.2], [2., .8]], "a2": [[0., 0.], [0., 0.]],
        "b0_per_bar": [[.02, .002], [.04, .003]],
        "binding_energy_j_mol": [[3000., 4500.], [2500., 4000.]],
        "species_order": ["H2", "N2"]}
    parameter_hash = hashlib.sha256(repr(parameters).encode("utf-8")).hexdigest()
    basis = AdsorptionBasis("authored-verification-material", ("H2", "N2"),
        "absolute:mol(entity)/kg(dry-adsorbent)", f"psa-dyna:{psa_dynamic.__version__}:{revision}",
        parameter_hash, (f"https://github.com/lyullee/psa-dyna/tree/{revision}",), loading_definition="absolute")
    adapter = PsaDynaEquilibrium(native.equilibrium, parameters, basis, AdsorptionDomain(290, 350, 1e6))
    state_error = pressure_error = temperature_error = 0.
    for temperature in (295., 320., 345.):
        for pressures in (np.array([1e4, 2e4]), np.array([2e5, 1e5]), np.array([4e5, 3e5])):
            state = adapter.equilibrium(pressures, temperature)
            direct, _, _ = native.equilibrium(pressures/1e5, temperature, parameters)
            state_error = max(state_error, float(np.max(abs(direct-state.site_loadings_mol_kg))))
            for species in range(2):
                step = 1.  # one Pa centered difference, distinct from native bar derivatives
                perturbation = np.eye(2)[species]*step
                numeric = (adapter.equilibrium(pressures+perturbation, temperature).site_loadings_mol_kg
                           - adapter.equilibrium(pressures-perturbation, temperature).site_loadings_mol_kg)/(2*step)
                expected = state.site_pressure_derivatives_mol_kg_pa[:, :, species].T
                pressure_error = max(pressure_error, float(np.max(abs(numeric-expected)/np.maximum(abs(expected), 1e-12))))
            step = 1e-3
            numeric = (adapter.equilibrium(pressures, temperature+step).site_loadings_mol_kg
                       - adapter.equilibrium(pressures, temperature-step).site_loadings_mol_kg)/(2*step)
            expected = state.site_temperature_derivatives_mol_kg_k
            temperature_error = max(temperature_error, float(np.max(abs(numeric-expected)/np.maximum(abs(expected), 1e-12))))
    if state_error != 0 or max(pressure_error, temperature_error) > 1e-6:
        raise RuntimeError("Native PSA equilibrium or derivative conversion verification failed")
    charged = adapter.equilibrium([4e5, 1e5], 300.)
    discharged = adapter.equilibrium([1e5, 1e4], 300.)
    capacity = loading_working_capacity(charged, discharged)
    core_hash = hashlib.sha256(Path(native.__file__).read_bytes()).hexdigest()
    lines = ["# Native PSA adsorption verification", "",
        f"Engine: PSA-Dyna {psa_dynamic.__version__}, public MIT revision `{revision}`.",
        f"Native core source SHA-256: `{core_hash}`.", f"Authored parameter representation SHA-256: `{parameter_hash}`.", "",
        "The fixture uses two species and two sites with coefficients authored for this "
        "unit/interface check. It is not a measured adsorbent parameter set. The adapter "
        "calls the installed native function without copying an isotherm implementation. "
        "Declared domain: 290–350 K, total partial pressure 0–1 MPa.", "",
        f"- Nine native/adapter states: maximum loading difference {state_error:.9g} mol/kg.",
        f"- Centered one-Pa pressure derivative: largest relative discrepancy {pressure_error:.9g}.",
        f"- Centered 0.001-K temperature derivative: largest relative discrepancy {temperature_error:.9g}.",
        f"- Loading-only working capacity H2/N2: {tuple(float(x) for x in capacity)} mol/kg.", "",
        "The pressure Jacobian is converted from per bar to per Pa, including off-diagonal "
        "competition terms. Species/site derivative axes are preserved. Negative pressure, "
        "wrong species order and out-of-domain T/P are rejected before native evaluation. "
        "No fugacity, pore/free-gas correction or uptake-basis transformation is inferred.", "",
        "This verifies the equilibrium adapter. A nonisothermal bed, cyclic steady state, "
        "process purity/recovery and experimental adsorption validation are not established here."]
    (root / "research/native_psa.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("native PSA checked", state_error, pressure_error, temperature_error)


if __name__ == "__main__":
    main()
