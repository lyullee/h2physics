"""Independent spectral integrals and actual native photo-conversion calorimetry."""

import argparse
import hashlib
from pathlib import Path
from time import perf_counter

import numpy as np
from scipy.integrate import quad

from h2physics.adapters.cantera import MechanismBasis
from h2physics.adapters.cantera_thermo import CanteraMolarEnthalpy
from h2physics.core import Origin
from h2physics.photochemistry import (
    BeerLambertPath,
    PhotoAdmissibilityError,
    PhotoConditions,
    PhotoInventoryError,
    PhotonSupply,
    PhotonYield,
    SteadyPhotoWindow,
    convert_photon_exposure,
    photon_hydrogen_rate,
)
from h2physics.reactions import StoichiometricReaction


def main():
    import cantera as ct
    import scipy

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, default=Path("research/photochemistry.md"))
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    paths = ("src/h2physics/photochemistry.py", "tests/test_photochemistry.py",
        "scripts/check_photochemistry.py", "src/h2physics/reactions.py",
        "src/h2physics/adapters/cantera_thermo.py", "src/h2physics/adapters/cantera.py",
        "docs/PHOTOCHEMISTRY.md")

    def hashes():
        return {p: hashlib.sha256((root/p).read_bytes()).hexdigest() for p in paths}

    before = hashes()
    started = perf_counter()
    hcna = 6.62607015e-34*299792458*6.02214076e23
    conditions = PhotoConditions("authored-spectral-catalyst", "authored-solution",
        .002, 300., 1e5, "authored-collimated-plane", "authored-fixed-conditions")

    def rate(supply, values, basis="absorbed_electron_equivalents", *, c=conditions, alpha=1200.,
             depth=.001, reflectance=.08):
        path = BeerLambertPath.uniform(supply, depth_m=depth, absorption_coefficient_m_inv=alpha,
            reflectance=reflectance, evidence_id="authored-nonscattering-homogeneous-path")
        efficiency = PhotonYield.bind(supply, values, basis=basis, conditions=c,
            evidence_id="authored-prescribed-bandwise-yield", origin=Origin.SYNTHETIC)
        return photon_hydrogen_rate(supply, path, efficiency)

    def irradiance(wavelength_nm):
        return 1.5*np.exp(-((wavelength_nm-500.)/100.)**2)

    def efficiency(wavelength_nm):
        return .3+.1*(wavelength_nm-350.)/350.

    absorption = .92*(1-np.exp(-1.2))
    reference, reference_error = quad(lambda wavelength_nm: .002*irradiance(wavelength_nm)
        *wavelength_nm*1e-9/hcna*absorption*efficiency(wavelength_nm)/2, 350., 700.,
        epsabs=1e-20, epsrel=1e-12)
    rows, runs, errors = [], [], []
    for n in (12, 24, 48, 96):
        edges_nm = np.linspace(350., 700., n+1)
        center_nm = (edges_nm[:-1]+edges_nm[1:])/2
        light = PhotonSupply.from_nanometer_bands(edges_nm, irradiance(center_nm),
            illuminated_area_m2=.002, geometry_id=conditions.geometry_id,
            source_id=f"authored-midpoint-irradiance-{n}")
        output = rate(light, efficiency(center_nm))
        error = abs(output.hydrogen_mol_s-reference)
        rows.append((n, np.sum(light.incident_power_w), np.sum(light.incident_photons_mol_s),
                     output.hydrogen_mol_s, error))
        runs.append(output)
        errors.append(error)
    finest = runs[-1]
    line = PhotonSupply.from_lines([380e-9, 530e-9, 680e-9], [.2, .7, .1],
        geometry_id=conditions.geometry_id, source_id="authored-three-line-source")
    intrinsic = rate(line, [.2, .4, .1])
    apparent = rate(line, intrinsic.optical_path.absorbed_fraction*np.array([.2,.4,.1]),
                    "incident_electron_equivalents")
    partitions = []
    for alpha, reflection in ((0.,0.), (1e-9,.2), (1200.,.08), (1e8,0.), (1200.,1.)):
        partitions.append(rate(line, .3, alpha=alpha, reflectance=reflection))
    energy_error = max(float(np.max(abs(r.energy_residual_w))) for r in runs+partitions)
    photon_error = max(float(np.max(abs(r.photon_residual_mol_s))) for r in runs+partitions)
    line_photon_error = float(np.max(abs(line.incident_photons_mol_s
        -line.incident_power_w*line.representative_wavelength_m/hcna)))
    source = Path(ct.__file__).parent/"data/gri30.yaml"
    native_sha = hashlib.sha256(source.read_bytes()).hexdigest()
    basis = MechanismBasis(f"Cantera:{ct.__version__}:authored-gas-photo-calorimetry", native_sha,
        "Cantera-BSD-3-Clause; upstream GRI-Mech provenance",
        ("https://cantera.org/3.2/examples/input/gri30.html",), 200., 1500., 1e4, 1e6)
    native_yaml = source.read_text(encoding="utf-8")
    caloric = CanteraMolarEnthalpy(lambda: ct.Solution(yaml=native_yaml), basis, ("H2O", "H2", "O2"))
    reaction = StoichiometricReaction("authored-prescribed-gas-water-photoconversion",
                                      caloric.species, (-2, 2, 1))
    window = SteadyPhotoWindow(100., 1100., "authored-absolute-clock", "authored-constant-light-path-yield")
    conversion = convert_photon_exposure(finest, window, reaction=reaction,
        initial_mol={"H2O": .1}, hydrogen_species_id="H2", enthalpy=caloric)
    native = ct.Solution(yaml=native_yaml)
    native.TPX = 300., 1e5, {"H2O": .1}
    hin = native.enthalpy_mole*.1/1000
    native.TPX = 300., 1e5, dict(conversion.conversion.final_amounts)
    hout = native.enthalpy_mole*sum(conversion.conversion.final_mol)/1000
    independent_heat_error = conversion.reaction_enthalpy_change_j-(hout-hin)
    inferred_heat_error = (conversion.required_isothermal_heat_j+conversion.absorbed_optical_energy_j
                           -(hout-hin))
    depleted_rejected = invalid_rejected = diagnostic_rejected = grid_rejected = False
    shifted = PhotonSupply.from_lines([400e-9, 550e-9, 700e-9], [.2, .7, .1],
        geometry_id=conditions.geometry_id, source_id="authored-different-optical-grid")
    shifted_yield = PhotonYield.bind(shifted, [.2,.4,.1], basis="absorbed_electron_equivalents",
        conditions=conditions, evidence_id="authored-shifted-light-yield", origin=Origin.SYNTHETIC)
    try:
        photon_hydrogen_rate(shifted, intrinsic.optical_path, shifted_yield)
    except ValueError as error:
        grid_rejected = "spectral grid/representation" in str(error)
    try:
        convert_photon_exposure(finest, window, reaction=reaction,
            initial_mol={"H2O": 1e-12}, hydrogen_species_id="H2", enthalpy=caloric)
    except PhotoInventoryError as error:
        depleted_rejected = error.rate is finest and error.window is window and error.__cause__ is not None
    try:
        rate(line, .99, "incident_electron_equivalents")
    except PhotoAdmissibilityError as error:
        invalid_rejected = error.result.supply is line and not error.result.photon_budget_admitted
        try:
            convert_photon_exposure(error.result, window, reaction=reaction,
                initial_mol={"H2O": .1}, hydrogen_species_id="H2")
        except PhotoAdmissibilityError:
            diagnostic_rejected = True
    after = hashes()
    gates = {
        "actual host source bytes and native mechanism unchanged": before == after
            and native_sha == hashlib.sha256(source.read_bytes()).hexdigest(),
        "line photon molar amounts match independent exact SI constants": line_photon_error < 1e-20,
        "finite-band smooth-spectrum midpoint convergence ratio above3.8":
            all(a/b > 3.8 for a,b in zip(errors[:-1],errors[1:],strict=True)),
        "finest H2 rate relative quadrature disagreement below1e-4": errors[-1]/reference < 1e-4,
        "transparent thin opaque reflecting optical energy defect below1e-14W": energy_error < 1e-14,
        "spectral photon partition defect below1e-19mol/s": photon_error < 1e-19,
        "incident versus absorbed yield use same physical H2 count":
            abs(intrinsic.hydrogen_mol_s-apparent.hydrogen_mol_s) < 1e-20,
        "existing finite stoichiometry conserves H/O mass below1e-15kg":
            abs(conversion.conversion.mass_residual_kg) < 1e-15,
        "native species calorimetry matches independent native mixture H below1e-9J":
            abs(independent_heat_error) < 1e-9,
        "required signed isothermal heat matches independent first law below1e-9J":
            abs(inferred_heat_error) < 1e-9,
        "finite depletion rejects without capping light or losing budget": depleted_rejected,
        "per-band incident photon excess retains rejected diagnostics": invalid_rejected,
        "rejected diagnostic cannot drive finite conversion": diagnostic_rejected,
        "optical wavelength-grid change rejects despite matching vector length": grid_rejected,
    }
    elapsed = perf_counter()-started
    lines = ["# Photon accounting and finite photochemical conversion", "",
        f"Actual local replay: SciPy{scipy.__version__}, Cantera{ct.__version__}; {elapsed:.9g}s.", "",
        "All spectra, optical coefficients and electron-equivalent yields are authored verification inputs. "
        "No catalyst coefficient, source experiment or universal charge-recombination law is fitted. "
        "The existing stoichiometric/caloric core owns finite conversion and native Cantera owns species "
        "enthalpies. Native files are separately installed and unchanged.", "",
        "Public H2 rate uses two productive electron equivalents per H2. Yield explicitly refers to incident "
        "or absorbed photons and is bound to actual optical-input identity plus catalyst/medium/mass/T/P/geometry. "
        "The one-electron-per-absorbed-photon scope is checked per constant-response band. Incident yield is "
        "not multiplied by absorption again. A reported AQY whose denominator/electron convention is unresolved "
        "cannot be silently attached to this model.", "",
        "The independent smooth source on350–700nm is E(lambda_nm)=1.5exp(-((lambda_nm-500)/100)^2)W/(m2 nm), "
        "area0.002m2; prescribed absorbed electron yield=0.3+0.1(lambda_nm-350)/350. Optical path1mm, "
        "alpha1200/m and reflectance0.08 are constant. Each numerical band holds irradiance/response fixed "
        "at its midpoint. Independent adaptive quadrature integrates the continuous formula, with no band "
        "assumption in its oracle.", "",
        f"Independent continuous H2 reference={reference:.12g}mol/s; quadrature estimate={reference_error:.12g}mol/s.", "",
        "| Bands | Incident W | Incident mol photons/s | H2 mol/s | Absolute H2 error mol/s |",
        "|---:|---:|---:|---:|---:|", *(f"| {n} | {p:.12g} | {ph:.12g} | {h:.12g} | {e:.12g} |"
            for n,p,ph,h,e in rows), "",
        f"Across declared limits: maximum optical power defect={energy_error:.12g}W, "
        f"photon partition defect={photon_error:.12g}mol/s. Three original line wavelengths380/530/680nm "
        "with0.2/0.7/0.1W test discrete photon energy and equivalent incident/absorbed yield.", "",
        "## Finite reaction and caloric requirement", "",
        "An authored ideal-gas H2O→H2/O2 conversion uses0.1mol initial steam,300K/100000Pa(abs), "
        "and the explicit steady[100,1100]s exposure. This is a balance/formation-enthalpy verification "
        "case, not a liquid water reactor or evidence of achievable water splitting.", "",
        f"Produced H2={conversion.conversion.final_amounts['H2']:.12g}mol; reaction extent="
        f"{conversion.conversion.extent_mol:.12g}mol; mass defect={conversion.conversion.mass_residual_kg:.12g}kg. "
        f"Incident/absorbed optical energy={conversion.incident_optical_energy_j:.12g}/"
        f"{conversion.absorbed_optical_energy_j:.12g}J. Actual native formation-enthalpy change="
        f"{conversion.reaction_enthalpy_change_j:.12g}J; required signed isothermal thermal boundary="
        f"{conversion.required_isothermal_heat_j:.12g}J. Independent native mixture-enthalpy defect="
        f"{independent_heat_error:.12g}J and first-law requirement defect={inferred_heat_error:.12g}J.", "",
        "Required isothermal heat is a derived boundary requirement, not an available utility or a predicted "
        "temperature. First-law bookkeeping alone does not establish Gibbs/exergy feasibility, band alignment, "
        "carrier potentials, reaction kinetics, donor/product chemistry or solar-to-H2 efficiency. A finite "
        "feed that cannot support the requested fixed-yield exposure is rejected without clipping extent or "
        "inventing source termination. Thermochemistry absent means heat remains None.", "",
        "| Verification gate | Pass |", "|---|---|", *(f"| {n} | {v} |" for n,v in gates.items()), "",
        "Primary definitions: [IUPAC photocatalysis terminology](https://doi.org/10.1351/PAC-REC-09-09-36), "
        "[SI photon/amount constants](https://www.bipm.org/en/publications/si-brochure), "
        "[native species thermochemistry](https://cantera.org/3.2/python/thermo.html). "
        "Original formulas/tests reproduce no third-party prose, coefficient table or worked example.", "",
        "## Executed identities", "", f"Native separately installed gri30.yaml SHA-256={native_sha}.", "",
        "| Host source | Begin SHA-256 | End SHA-256 |", "|---|---|---|",
        *(f"| `{p}` | `{before[p]}` | `{after[p]}` |" for p in paths), ""]
    target = args.report if args.report.is_absolute() else root/args.report
    target.write_text("\n".join(lines), encoding="utf-8", newline="\n")
    for name, passed in gates.items():
        print(f"{'PASS' if passed else 'FAIL'} {name}")
    print(f"Actual local photo replay {elapsed:.6g}s; {target.name}")
    return 0 if all(gates.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
