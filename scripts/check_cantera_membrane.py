"""Small actual-native porous-gas replay; no membrane data or device prediction."""

import hashlib
import importlib.metadata
import time
from dataclasses import replace
from pathlib import Path

import numpy as np

from h2physics.adapters.cantera import MechanismBasis
from h2physics.adapters.cantera_membrane import (
    CanteraDustyGasTransport,
    MembraneEndpoint,
    MembraneTransportError,
    MembraneTransportEvidence,
    PorousTransportGeometry,
)
from h2physics.core import Origin

ROOT = Path(__file__).resolve().parents[1]
SOURCES = ("src/h2physics/adapters/cantera_membrane.py", "tests/test_cantera_membrane.py",
           "scripts/check_cantera_membrane.py", "src/h2physics/adapters/cantera_volume.py",
           "src/h2physics/adapters/cantera.py", "src/h2physics/core.py")
SPECIES = ("H2", "N2", "AR")


def fingerprints():
    result = {}
    for name in SOURCES:
        data = (ROOT/name).read_bytes()
        if b"\r" in data:
            raise ValueError("Executed sources must retain LF endings")
        result[name] = hashlib.sha256(data).hexdigest()
    return result


def main():
    import cantera as ct
    import cantera._cantera as native

    started = time.perf_counter()
    native_root = Path(ct.__file__).parent
    mechanism_path = native_root/"data/h2o2.yaml"
    raw = mechanism_path.read_bytes()
    native_paths = {"h2o2.yaml": mechanism_path, "compiled-native": Path(native.__file__),
        "transport.pyi": native_root/"transport.pyi",
        "Cantera-License.txt": Path(importlib.metadata.distribution("cantera").locate_file(
            "cantera-3.2.0.dist-info/licenses/License.txt"))}
    def native_hashes():
        return {name: hashlib.sha256(path.read_bytes()).hexdigest() for name, path in native_paths.items()}
    before, native_before = fingerprints(), native_hashes()
    def factory():
        by_name = {s.name: s for s in ct.Species.list_from_yaml(raw.decode(), section="species")}
        return ct.Solution(thermo="ideal-gas", species=[by_name[n] for n in SPECIES],
                           transport_model="multicomponent")
    basis = MechanismBasis("installed-h2o2-authored-H2-N2-Ar-selection", native_before["h2o2.yaml"],
        "Cantera-BSD-3-Clause; upstream GRI-Mech thermochemistry/transport provenance",
        ("https://cantera.org/3.2/python/transport.html",), 300., 1000., .001, 2e5)
    evidence = MembraneTransportEvidence("installed-h2o2-native-gri30-transport",
        "authored-neutral-gas-phase", "prescribed-warm-neutral-ideal-gas-no-condensation",
        "native-NASA-formation-reference", "native-mechanism-H2-spin-unresolved")
    pore = PorousTransportGeometry(.4, 3., 80e-9, 2e-16, .002,
        "authored-porous-plane", "authored-pore-coefficients-not-material-data", Origin.SYNTHETIC)
    def endpoint(name, X, P=101325.):
        return MembraneEndpoint(360., P, SPECIES, X, "mole", name, evidence.gas_phase_id,
            pore.geometry_id, "authored-warm-endpoint", Origin.SYNTHETIC)
    model = CanteraDustyGasTransport(factory, basis, evidence=evidence)
    left, right = endpoint("left", [.65, .25, .1]), endpoint("right", [.35, .55, .1])
    result = model.flux(left, right, pore)
    zero = model.flux(left, replace(left, boundary_id="right"), pore)
    reverse = model.flux(right, left, pore)
    thick = model.flux(left, right, replace(pore, thickness_m=pore.thickness_m*2))
    diffusive = replace(pore, permeability_m2=0.)
    reference = model.flux(left, right, diffusive)
    half_porosity = model.flux(left, right, replace(diffusive, porosity=.2))
    double_tortuosity = model.flux(left, right, replace(diffusive, tortuosity=6.))

    knudsen = []
    for pressure in (1e5, 1e3, 1., .01):
        a, b = replace(left, pressure_pa_absolute=pressure), replace(right, pressure_pa_absolute=pressure)
        actual = model.flux(a, b, diffusive)
        mass = actual.molecular_weights_kg_mol
        coefficient = (2/3)*pore.mean_pore_radius_m*pore.porosity/pore.tortuosity*np.sqrt(
            8*(ct.gas_constant/1000.)*a.temperature_k/(np.pi*mass))
        concentrations = [p.density_kg_m3*p.mass_fractions/mass
                          for p in (actual.left_state, actual.right_state)]
        expected = -coefficient*(concentrations[1]-concentrations[0])/pore.thickness_m
        error = float(np.max(abs(actual.molar_flux_mol_m2_s-expected))/np.max(abs(expected)))
        knudsen.append((pressure, error))

    pressure_left = endpoint("left", [.6, .25, .15], 105000.)
    pressure_right = endpoint("right", [.6, .25, .15], 95000.)
    native_zero = model.flux(pressure_left, pressure_right, diffusive)
    native_permeable = model.flux(pressure_left, pressure_right, pore)
    mean = factory()
    mean.TPX = 360., 100000., [.6, .25, .15]
    darcy = -mean.concentrations*1000.*pore.permeability_m2/mean.viscosity*(95000.-105000.)/pore.thickness_m
    darcy_error = float(np.max(abs(native_permeable.molar_flux_mol_m2_s-native_zero.molar_flux_mol_m2_s-darcy)))

    shared = factory()
    source_before = shared.state.copy()
    shared_model = CanteraDustyGasTransport(lambda: shared, basis, evidence=evidence)
    original = shared_model.flux(left, right, pore)
    original.native_dusty_gas.permeability = 1e-10
    original.native_dusty_gas.mean_pore_radius = 1e-4
    after_mutation = shared_model.flux(left, right, pore)
    source_preserved = np.array_equal(shared.state, source_before)
    native_failure = None
    try:
        model.flux(left, right, replace(pore, mean_pore_radius_m=np.nextafter(0., 1.)))
    except MembraneTransportError as error:
        native_failure = error
    changed = factory()
    changed.set_binary_diff_coeffs_polynomial(0, 1, changed.get_binary_diff_coeffs_polynomial(0, 1)*1.01)
    changed_rejected = False
    try:
        CanteraDustyGasTransport(lambda: changed, basis, evidence=evidence).flux(left, right, pore)
    except MembraneTransportError as error:
        changed_rejected = "runtime-modified" in str(error)
    after, native_after = fingerprints(), native_hashes()
    gates = {
        "actual native DustyGas/raw kmol and complete SI species arrays retained":
            isinstance(result.native_dusty_gas, ct.DustyGas) and result.species == SPECIES
            and np.array_equal(result.molar_flux_mol_m2_s, result.native_flux_kmol_m2_s*1000.),
        "native molecular masses give matching signed kg flux": np.array_equal(result.mass_flux_kg_m2_s,
            result.molar_flux_mol_m2_s*result.molecular_weights_kg_mol),
        "zero state gradient gives exact zero flux": bool(np.all(zero.native_flux_kmol_m2_s == 0)),
        "swapping endpoints reverses every signed flux": bool(np.allclose(reverse.molar_flux_mol_m2_s,
            -result.molar_flux_mol_m2_s, rtol=1e-13, atol=1e-18)),
        "doubling separation halves native flux": bool(np.allclose(thick.molar_flux_mol_m2_s,
            result.molar_flux_mol_m2_s/2, rtol=1e-13, atol=1e-18)),
        "coupled inert counterflux and nonzero total molar transport retained":
            result.molar_flux_mol_m2_s[2] != 0 and abs(result.molar_flux_mol_m2_s.sum()) > .001,
        "native porosity/tortuosity factor checked without a squared convention":
            bool(np.allclose(half_porosity.molar_flux_mol_m2_s, reference.molar_flux_mol_m2_s/2, rtol=1e-13)
            and np.allclose(double_tortuosity.molar_flux_mol_m2_s, reference.molar_flux_mol_m2_s/2, rtol=1e-13)),
        "fixed physical 80nm pore low-pressure Knudsen oracle converges below1e-6":
            all(b[1] < a[1] for a, b in zip(knudsen, knudsen[1:], strict=False)) and knudsen[-1][1] < 1e-6,
        "explicit Darcy addition agrees with independent native-viscosity oracle": darcy_error < 1e-14,
        "source state untouched and changed returned pore settings never reused":
            source_preserved and np.array_equal(original.molar_flux_mol_m2_s, after_mutation.molar_flux_mol_m2_s)
            and original.native_dusty_gas is not after_mutation.native_dusty_gas,
        "runtime-modified gas diffusion fits are rejected rather than replaced": changed_rejected,
        "native numerical failure preserves actual objects and original cause":
            native_failure is not None and native_failure.native_dusty_gas is not None
            and len(native_failure.owned_endpoint_phases) == 2 and native_failure.__cause__ is not None,
        "native enthalpy diagnostics keep reference without inventing thermal closure":
            "unresolved" in result.thermal_closure and not hasattr(result, "recovery"),
        "host/native input fingerprints unchanged and LF": before == after and native_before == native_after,
    }
    elapsed = time.perf_counter()-started
    lines = ["# Native porous-gas transport verification", "",
        f"Actual Cantera{ct.__version__} (`{ct.__git_commit__}`), BSD-3-Clause native code. "
        "Installed h2o2.yaml contains GRI-Mech-origin thermochemistry and gas transport; "
        "the H2/N2/Ar selection is authored. No source mechanism, parameter table, measured "
        "membrane data or native code is bundled. No native source was modified.", "",
        "Native DustyGas owns the coupled multicomponent/Knudsen/Darcy flux and ideal-gas EOS. "
        "The host reuses the existing audited native phase-copy helper and checks gas transport "
        "polynomial copying. Every calculation uses a new native DustyGas with explicitly "
        "declared porosity/tortuosity/pore radius/permeability; write-only native pore values "
        "are preserved by the immutable host parameter object.", "",
        f"Local replay elapsed{elapsed:.6f}s. Authored geometry: porosity0.4, tortuosity3, "
        "mean pore radius80nm, thickness2mm, explicit permeability2e-16m2. Endpoints360K; "
        "ordinary composition probe at101325Pa absolute. Coefficients are mathematical "
        "verification inputs, not a fitted or experimentally qualified membrane.", "",
        "| Gate | Pass |", "|---|---|",
        *(f"| {name} | {bool(passed)} |" for name, passed in gates.items()), "",
        "## Independent limiting checks", "",
        "The Knudsen oracle keeps the80nm pore fixed and reduces equal endpoint pressure. "
        "Its coefficient is (2/3)*r*(porosity/tortuosity)*sqrt(8RT/(pi*M)); the molar "
        "concentration gradient comes from separate native endpoint densities and fractions. "
        "No submolecular radius is used to claim material applicability. The subnormal-radius "
        "case is only a native failure-retention test.", "",
        "| Pressure Pa absolute | Relative max-norm Knudsen-limit error |", "|---:|---:|",
        *(f"| {p:.12g} | {error:.12g} |" for p, error in knudsen), "",
        f"At constant composition with105000/95000Pa endpoints, the explicit-permeability "
        f"flux increment agrees with -c_i*kappa/mu*grad(P) to{darcy_error:.12g}mol/(m2s), "
        "using a separate native gas viscosity. This independently checks the extra Darcy "
        "term without replacing native gas transport or solving another EOS.", "",
        "## Limits and continuation", "",
        "The signed total species flux is relative to stationary porous solid and includes "
        "Darcy transport. It need not sum to zero; species can counterdiffuse. Native "
        "kmol/(m2s) is scaled by1000 to SI mol/(m2s), and kg flux uses native kg/kmol masses. "
        "The two-nearby-point closure is not a solved finite membrane profile or an "
        "area/time/inventory-based device. Product purity, recovery and selective solid "
        "solution-diffusion are not returned.", "",
        "Admission requires normalized explicit X/Y and species order, neutral frozen "
        "single ideal gas, an explicit warm property/transport domain, isothermal endpoints, "
        "positive separation and valid pore geometry. Finite boundary inventories, axial "
        "profiles, reaction, adsorption, dense-gas corrections, condensation, scattering, "
        "thermal transpiration/Soret and solid/gas heat storage remain unresolved. "
        "Native endpoint partial enthalpies are diagnostics in the declared formation/phase "
        "reference; no heat balance or common stream is invented. H2 spin is unresolved. "
        "Future finite composition needs actual area/clock, component/energy ledgers and "
        "spatial refinement. Numerical verification is not measured membrane validation.", "",
        "Mutable native diagnostic objects are retained for inspection. They are never "
        "reused internally. A caller changing their write-only pore settings cannot use "
        "the old immutable geometry record as proof of that new native configuration. "
        "Source state stays unchanged; changes of source thermo or transport definitions "
        "require new evidence. Native errors retain source/copies/DustyGas/raw completed "
        "flux and chained cause; there is no replacement provider.", "",
        "## Sources and input fingerprints", "",
        "Primary API/equation references: "
        "[Cantera3.2 Python transport](https://cantera.org/3.2/python/transport.html#cantera.DustyGasTransport.molar_fluxes), "
        "[native DustyGas mathematical contract](https://cantera.org/3.2/cxx/dc/de6/classCantera_1_1DustyGasTransport.html). "
        "The implemented flux equations remain in Cantera; only independently authored "
        "limiting checks and unit/identity/admission logic are in this repository.", "",
        "| Native input | Begin SHA256 | End SHA256 |", "|---|---|---|",
        *(f"| {name} | {value} | {native_after[name]} |" for name, value in native_before.items()), "",
        "| Host/reused source | Begin SHA256 | End SHA256 |", "|---|---|---|",
        *(f"| {name} | {value} | {after[name]} |" for name, value in before.items()), ""]
    (ROOT/"research/native_membrane_transport.md").write_text("\n".join(lines), encoding="utf-8", newline="\n")
    for name, passed in gates.items():
        print(f"{'PASS' if passed else 'FAIL'} {name}", flush=True)
    print(f"local replay {elapsed:.6f}s; wrote research/native_membrane_transport.md", flush=True)
    if not all(gates.values()):
        raise SystemExit("A native porous-gas gate failed; report retained")


if __name__ == "__main__":
    main()
