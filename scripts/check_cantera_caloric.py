"""Replay actual common-reference native gas/solid finite calorimetry."""

import hashlib
import importlib.metadata
from dataclasses import replace
from pathlib import Path
from time import perf_counter

import numpy as np

from h2physics.adapters.cantera import MechanismBasis
from h2physics.adapters.cantera_caloric import CanteraMultiphaseMolarEnthalpy, SolidDensityEvidence
from h2physics.adapters.cantera_multiphase import EquilibriumPhase
from h2physics.core import Origin
from h2physics.reactions import StoichiometricReaction, conversion_heat_j, solve_product_temperature


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    import cantera as ct

    root = Path(__file__).resolve().parents[1]
    data = Path(ct.__file__).parent/"data"
    host_names = ("src/h2physics/adapters/cantera_caloric.py", "tests/test_cantera_caloric.py",
        "scripts/check_cantera_caloric.py", "docs/MULTIPHASE_CALORIMETRY.md",
        "src/h2physics/adapters/cantera.py", "src/h2physics/adapters/cantera_thermo.py",
        "src/h2physics/adapters/cantera_multiphase.py", "src/h2physics/adapters/cantera_volume.py",
        "src/h2physics/reactions.py")
    before = {name: sha(root/name) for name in host_names}
    distribution = importlib.metadata.distribution("cantera")
    license_path = next(Path(distribution.locate_file(p)) for p in distribution.files
                        if str(p).endswith("licenses/License.txt"))
    native_paths = {name: data/name for name in ("nasa_condensed.yaml", "h2o2.yaml")}
    native_paths.update({"Cantera license": license_path, "Cantera compiled binary": Path(ct._cantera.__file__)})
    native_before = {name: sha(path) for name, path in native_paths.items()}
    mapping = (("Fe3O4", "Fe3O4(s)", "Fe3O4"), ("FeO", "FeO(s)", "FeO"),
               ("gas", "H2O", "H2O"), ("gas", "H2", "H2"), ("gas", "O2", "O2"))

    def phase(phase_id, native_species=None, density=None):
        file = "h2o2.yaml" if native_species is None else "nasa_condensed.yaml"
        raw = (data/file).read_bytes()
        def factory():
            if native_species is None:
                return ct.Solution(yaml=raw.decode("utf-8"), name="ohmech")
            selected = next(s for s in ct.Species.list_from_yaml(raw.decode("utf-8"), "species")
                            if s.name == native_species)
            definition = dict(selected.input_data)
            definition["equation-of-state"] = {"model": "constant-volume", "density": density}
            result = ct.Solution(thermo="fixed-stoichiometry", species=[ct.Species.from_dict(definition)],
                                 name=phase_id, transport_model="none")
            result.TP = 300., 101325.
            return result
        basis = MechanismBasis("installed-"+file+":"+phase_id, sha(data/file),
            "Cantera BSD-3-Clause; NASA TM4513 upstream thermochemistry",
            ("https://ntrs.nasa.gov/citations/19940013151",), 300., 1650., 1e4, 2e6)
        return EquilibriumPhase(phase_id, "gas" if native_species is None else "solid", factory,
            basis, "declared-native-NASA-standard-formation-reference", "native-mechanism-H2-spin-unresolved")

    phases = (phase("Fe3O4", "Fe3O4(s)", 4800.), phase("FeO", "FeO(s)", 5000.), phase("gas"))
    evidence = {name: SolidDensityEvidence(density, "authored-calorimetry-fixture:"+name, Origin.SYNTHETIC,
        "Constant-density verification fixture; no measured solid EOS claim")
        for name, density in (("Fe3O4", 4800.), ("FeO", 5000.))}

    def provider():
        return CanteraMultiphaseMolarEnthalpy(phases, mapping, solid_density_evidence=evidence)

    started = perf_counter()
    caloric = provider()
    reduction = StoichiometricReaction("authored-oxide-reduction", caloric.species, (-1, 3, 0, 0, .5))
    oxidation = StoichiometricReaction("authored-oxide-steam-oxidation", caloric.species, (1, -3, -1, 1, 0))
    first = reduction.convert({"Fe3O4": .4, "H2O": 1.}, .15)
    second = oxidation.convert(first.final_amounts, .15)
    heat1 = conversion_heat_j(first, caloric, inlet_temperature_k=1000., outlet_temperature_k=1000., pressure_pa=101325.)
    heat2 = conversion_heat_j(second, caloric, inlet_temperature_k=1000., outlet_temperature_k=1000., pressure_pa=101325.)
    h1000 = caloric.enthalpies_j_mol(1000., 101325.)
    water_heat = .15*(h1000[3]+.5*h1000[4]-h1000[2])
    reaction_heat_error = heat1+heat2-water_heat
    conversion = reduction.convert({"Fe3O4": .4, "H2O": .6}, .05)
    supplied = conversion_heat_j(conversion, caloric, inlet_temperature_k=800., outlet_temperature_k=1120., pressure_pa=2e5)
    solved = solve_product_temperature(conversion, caloric, inlet_temperature_k=800., pressure_pa=2e5,
        supplied_heat_j=supplied, bracket_k=(700., 1500.))

    amounts = np.array([.37, .21, .6, .13, .08])
    h = caloric.enthalpies_j_mol(1050., 350000.)
    mixture = ct.Mixture([(p, 0.) for p in caloric.owned_phases])
    mixture.T, mixture.P = 1050., 350000.
    mol = np.zeros(mixture.n_species)
    for (phase_id, species, _), amount in zip(mapping, amounts, strict=True):
        mol[mixture.species_index(caloric._phase_indices[phase_id], species)] = amount/1000.
    mixture.species_moles = mol
    mixture.chemical_potentials
    native_h = sum(mixture.phase_moles(k)*p.enthalpy_mole for k, p in enumerate(caloric.owned_phases))
    native_u = sum(mixture.phase_moles(k)*p.int_energy_mole for k, p in enumerate(caloric.owned_phases))
    volume = sum(mixture.phase_moles(k)*p.mean_molecular_weight/p.density_mass
                 for k, p in enumerate(caloric.owned_phases))
    extensive_error = float(amounts@h-native_h)
    pv_error = native_h-native_u-mixture.P*volume
    pressure_a, pressure_b = 101325., 1100000.
    low_p = caloric.enthalpies_j_mol(950., pressure_a)
    high_p = caloric.enthalpies_j_mol(950., pressure_b)
    pressure_errors = [float(high_p[k]-low_p[k]-(pressure_b-pressure_a)*p.mean_molecular_weight/p.density_mass/1000.)
                       for k, p in enumerate(caloric.owned_phases[:2])]
    gas_pressure_error = float(np.max(abs(high_p[2:]-low_p[2:])))
    derivative_errors, minimum_cp = [], np.inf
    for temperature in (300.1, 600., 900., 1400., 1649.9):
        dt = .01
        fd = (caloric.enthalpies_j_mol(temperature+dt, 230000.)
              -caloric.enthalpies_j_mol(temperature-dt, 230000.))/(2*dt)
        caloric.enthalpies_j_mol(temperature, 230000.)
        exact = np.array([caloric.owned_phases[caloric._phase_indices[p]].partial_molar_cp[
            caloric.owned_phases[caloric._phase_indices[p]].species_index(s)]/1000. for p, s, _ in mapping])
        derivative_errors.append(float(np.max(abs(fd-exact)/abs(exact))))
        minimum_cp = min(minimum_cp, float(exact.min()))
    expected = caloric.enthalpies_j_mol(900., 101325.)
    caloric.owned_phases[2].TPX = 1400., 500000., {"H2O": .9, "H2": .1}
    reset_error = float(np.max(abs(caloric.enthalpies_j_mol(900., 101325.)-expected)))
    rejections = {}

    def reject(label, fn):
        try:
            fn()
        except ValueError as error:
            rejections[label] = str(error)

    wider = CanteraMultiphaseMolarEnthalpy(tuple(replace(p, mechanism_basis=replace(
        p.mechanism_basis, maximum_temperature_k=2000.)) for p in phases), mapping,
        solid_density_evidence=evidence)
    reject("selected FeO(s) native fit, wider host envelope", lambda: wider.enthalpies_j_mol(1700., 101325.))
    reject("pressure domain", lambda: caloric.enthalpies_j_mol(900., 3e6))
    reject("infinite/nonphysical input", lambda: caloric.enthalpies_j_mol(float("nan"), 101325.))
    reject("unrelated formation zero", lambda: CanteraMultiphaseMolarEnthalpy(
        (replace(phases[0], energy_reference_id="unrelated-sensible-zero"), *phases[1:]), mapping,
        solid_density_evidence=evidence))
    reject("missing volume evidence", lambda: CanteraMultiphaseMolarEnthalpy(phases, mapping))
    reject("finite inventory exceeded", lambda: reduction.convert({"Fe3O4": .4}, .4000001))
    changed = provider()
    original_coefficients = changed.owned_phases[0].species(0).thermo.coeffs.copy()
    native_species = changed.source_phases[0].species(0)
    thermo = native_species.thermo
    coeff = thermo.coeffs.copy()
    coeff[6] += .001
    coeff[13] += .001
    native_species.thermo = type(thermo)(thermo.min_temp, thermo.max_temp, thermo.reference_pressure, coeff)
    changed.source_phases[0].modify_species(0, native_species)
    alias_independent = np.array_equal(original_coefficients, changed.owned_phases[0].species(0).thermo.coeffs)
    reject("source definition mutation", lambda: changed.enthalpies_j_mol(900., 101325.))
    changed_owned = provider()
    changed_owned.owned_phases[2].set_multiplier(.5, 0)
    reject("owned runtime parameter mutation", lambda: changed_owned.enthalpies_j_mol(900., 101325.))
    def altered_weight_factory():
        native = phases[1].factory()
        return ct.Solution(yaml="elements:\n- symbol: O\n  atomic-weight: 17.0\n"
                           +native.write_yaml(precision=17), name=native.name)
    reject("actual native atomic-weight mismatch", lambda: CanteraMultiphaseMolarEnthalpy(
        (phases[0], replace(phases[1], factory=altered_weight_factory), phases[2]), mapping,
        solid_density_evidence=evidence))
    rebound = provider()
    reference_h = rebound.enthalpies_j_mol(900., 101325.)
    alternative = phases[2].factory()
    h2_index = alternative.species_index("H2")
    alternative_species = alternative.species(h2_index)
    thermo = alternative_species.thermo
    coefficients = thermo.coeffs.copy()
    coefficients[6] += 1000.
    coefficients[13] += 1000.
    alternative_species.thermo = type(thermo)(thermo.min_temp, thermo.max_temp,
                                             thermo.reference_pressure, coefficients)
    alternative.modify_species(h2_index, alternative_species)
    alternative.TP = 900., 101325.
    alternative_h2_shift = alternative.partial_molar_enthalpies[h2_index]/1000.-reference_h[3]
    gas_bridge = rebound.native_gas_providers["gas"]
    original_native = gas_bridge.native_phase
    gas_bridge.native_phase = alternative
    reject("alternative actual native gas phase pointer", lambda: rebound.enthalpies_j_mol(900., 101325.))
    gas_bridge.native_phase = original_native
    for field in ("_indices", "species", "mechanism_basis", "basis_id"):
        original_value = getattr(gas_bridge, field)
        changed_value = (tuple(reversed(original_value)) if field in {"_indices", "species"}
            else replace(original_value, identifier="unreviewed-basis") if field == "mechanism_basis"
            else "unreviewed-reference")
        setattr(gas_bridge, field, changed_value)
        reject("reused gas provider "+field+" binding", lambda: rebound.enthalpies_j_mol(900., 101325.))
        setattr(gas_bridge, field, original_value)
    restored_error = float(np.max(abs(rebound.enthalpies_j_mol(900., 101325.)-reference_h)))
    after = {name: sha(root/name) for name in host_names}
    native_after = {name: sha(path) for name, path in native_paths.items()}
    gates = {
        "actual native phases and existing gas enthalpy provider": all(isinstance(p, ct.Solution) for p in caloric.owned_phases)
            and caloric.native_gas_providers["gas"].native_phase is caloric.owned_phases[2],
        "native Mixture extensive H error <1e-8 J": abs(extensive_error) < 1e-8,
        "independent native H-U-PV error <1e-8 J": abs(pv_error) < 1e-8,
        "solid native pressure correction error <1e-8 J/mol": max(abs(e) for e in pressure_errors) < 1e-8,
        "gas h pressure independence <1e-9 J/mol": gas_pressure_error < 1e-9,
        "native Cp finite-difference error <1e-8 relative": max(derivative_errors) < 1e-8 and minimum_cp > 0,
        "finite two-stage mass and returned oxide inventories close": max(abs(first.mass_residual_kg), abs(second.mass_residual_kg)) < 1e-15
            and abs(second.final_amounts["Fe3O4"]-.4) < 1e-15 and abs(second.final_amounts["FeO"]) < 1e-15,
        "finite two-stage sum equals net water thermochemical heat <1e-8 J": abs(reaction_heat_error) < 1e-8,
        "existing product-temperature solve roundtrip <1e-8 K": abs(solved.temperature_k-1120.) < 1e-8
            and abs(solved.energy_residual_j) < 1e-7,
        "native state/composition reuse resets <1e-10 J/mol": reset_error < 1e-10,
        "source objects are independent native copies": alias_independent
            and all(a is not b for a, b in zip(caloric.source_phases, caloric.owned_phases, strict=True)),
        "actual native alternative gas pointer and metadata binding guarded":
            abs(alternative_h2_shift-ct.gas_constant) < 1e-8 and restored_error < 1e-10
            and "alternative actual native gas phase pointer" in rejections,
        "all fourteen invalid/domain/reference/parameter probes rejected": len(rejections) == 14,
        "host/test/script/docs and reused contracts unchanged": before == after,
        "native sources/license/binary unchanged": native_before == native_after,
        "new host inputs are LF text": all(b"\r" not in (root/name).read_bytes() for name in host_names[:4]),
    }
    elapsed = perf_counter()-started
    rows = ["# Native gas and iron-oxide molar calorimetry", "",
        "Reproduce: `python scripts/check_cantera_caloric.py` with optional Cantera3.2.", "",
        f"Actual native Cantera{ct.__version__}; property/finite-reaction calculations and negative probes took {elapsed:.6g}s. "
        "No native table, coefficient set or mechanism is bundled or modified.", "",
        "Installed nasa_condensed.yaml contains FeO(s)300–1650K and Fe3O4(s)300–5000K, with no EOS/density for either. "
        "This authored fixture uses explicit constant-volume densities FeO5000 and Fe3O4 4800kg/m3, both Origin.SYNTHETIC. "
        "They are not measured properties or phase-stability evidence. The common demonstrated range is300–1650K; native ideal-gas h2o2 species supply H2O/H2/O2.", "",
        "Native formation energy stays in H. All phases carry the caller-declared NASA formation reference and unresolved mechanism H2 spin identity. "
        "Matching metadata strings are not proof that arbitrary sources share a zero. Shared element atomic weights are checked. "
        "Gas partial h and pure-solid native h are divided by1000 from J/kmol to J/mol; native solid pressure corrections are retained.", "",
        "| Actual numerical check | Result |", "|---|---:|",
        f"| weighted SI species H minus actual native Mixture H J | {extensive_error:.12g} |",
        f"| native H-U-PV J | {pv_error:.12g} |",
        f"| max solid deltaP*V enthalpy error J/mol | {max(abs(e) for e in pressure_errors):.12g} |",
        f"| gas pressure-independence error J/mol | {gas_pressure_error:.12g} |",
        f"| max finite-difference h derivative / native Cp relative error | {max(derivative_errors):.12g} |",
        f"| minimum sampled native Cp J/mol/K | {minimum_cp:.12g} |",
        f"| reduction heat at1000K for extent.15mol J | {heat1:.12g} |",
        f"| steam oxidation heat at1000K for extent.15mol J | {heat2:.12g} |",
        f"| net water conversion heat J | {water_heat:.12g} |",
        f"| two-stage sum minus net water heat J | {reaction_heat_error:.12g} |",
        f"| product-temperature roundtrip error K | {solved.temperature_k-1120.:.12g} |",
        f"| product-temperature energy residual J | {solved.energy_residual_j:.12g} |",
        f"| native state reset error J/mol | {reset_error:.12g} |", "",
        f"The alternative actual native gas phase probe shifts both H2 NASA enthalpy constants by1000K, giving "
        f"a raw H2 enthalpy change of{alternative_h2_shift:.12g}J/mol at900K. Rebinding the exposed reused gas provider "
        "to that independent actual phase is rejected before returning a value under the recorded basis. "
        "Changes to its species order, native indices, MechanismBasis and basis_id are also rejected; "
        f"restoring the original binding recovers all enthalpies within{restored_error:.12g}J/mol. "
        "No source-global monkeypatch or replacement property function is used.", "",
        "The extensive native Mixture audit uses1050K/350000Pa and finite SI mol Fe3O4=.37,FeO=.21,H2O=.6,H2=.13,O2=.08, without equilibrium. "
        "Pressure correction uses950K/101325→1100000Pa. Derivative checks use300.1,600,900,1400,1649.9K and a.01K centered step. "
        "These comparisons verify native caloric composition and units; native-Cp/finite-difference checks are not an independent thermochemical dataset.", "",
        "Both finite reactions use the shared existing StoichiometricReaction.convert/conversion_heat_j contract. "
        "Initial Fe3O4=.4mol and H2O=1mol; supplied reduction/oxidation extents are.15mol at1000K. "
        "Returned solids match the starting composition, H2=.15mol,O2=.075mol, and steam is.85mol. "
        "The sum equals the net water-splitting enthalpy at the same T/P. This is finite prescribed isothermal calorimetry, "
        "not a prediction that the two reactions occur at that temperature. No reaction clock, equilibrium yield, actual cycle efficiency or hardware heat recovery is claimed.", "",
        "The nonisothermal case uses existing product-temperature root finding: reduction extent.05mol, initial Fe3O4=.4mol/steam=.6mol at800K, "
        "with heat independently evaluated at the target1120K/200000Pa. No duplicate heat or trajectory solver is present.", "",
        "| Deliberate rejected input | Retained reason |", "|---|---|"]
    rows.extend(f"| {name} | {reason} |" for name, reason in rejections.items())
    rows.extend(["", "| Verification gate | Pass |", "|---|---|"])
    rows.extend(f"| {name} | {passed} |" for name, passed in gates.items())
    rows.extend(["", "Every actual source/owned native definition is fingerprinted separately and checked exactly per query. "
        "Native reconstruction may alter notes/unit representation with audited tiny roundtrips; it does not merge their identities. "
        "State/composition reuse is reset. Source and owned objects, copy audits, factory parameters and explicit density evidence remain inspectable. "
        "Actual native gas/solid APIs supply the property values; no phase or property field is fabricated.", "",
        "This generic constitutive bridge does not itself add a new reaction/cycle family or imply measured iron-cycle validation. "
        "Phase-stable oxide data/EOS, achievable extent and kinetics, carrier loss/sintering, gas separation/vacuum work, heat exchange/solar input, "
        "operating clock and independent experiments remain receiving requirements. Fit bounds are not stable-phase limits. "
        "There is no inferred liquid phase, evolving hydrogen spin EOS or arbitrary CoolProp energy-zero substitution.", "",
        "Primary sources: [native thermo API](https://cantera.org/3.2/python/thermo.html), "
        "[versioned condensed-species provenance](https://github.com/Cantera/cantera/blob/v3.2.0/data/nasa_condensed.yaml), "
        "[NASA TM-4513](https://ntrs.nasa.gov/citations/19940013151). Cantera implementation is BSD-3-Clause; "
        "NASA's primary record identifies public distribution and US-government public use. Upstream thermochemical provenance and software rights remain distinct.", "",
        "## Source fingerprints", "", "| Host input | Begin SHA256 | End SHA256 |", "|---|---|---|"])
    rows.extend(f"| {name} | {before[name]} | {after[name]} |" for name in host_names)
    rows.extend(["", "| Installed input | Begin SHA256 | End SHA256 |", "|---|---|---|"])
    rows.extend(f"| {name} | {native_before[name]} | {native_after[name]} |" for name in native_paths)
    rows.extend(["", "| Phase | Source native definition | Owned native definition |", "|---|---|---|"])
    rows.extend(f"| {p.phase_id} | {a.source_fingerprint} | {a.owned_fingerprint} |"
                for p, a in zip(caloric.phases, caloric.phase_copy_audits, strict=True))
    (root/"research/multiphase_calorimetry.md").write_text("\n".join(rows)+"\n", encoding="utf-8", newline="\n")
    print(f"Cantera caloric: {sum(gates.values())}/{len(gates)} gates passed in {elapsed:.6g}s")
    for name, passed in gates.items():
        if not passed:
            print("FAILED:", name)
    return 0 if all(gates.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
