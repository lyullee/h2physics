"""Execute native gas/graphite TP/HP equilibrium and independent extensive audits."""

import hashlib
import importlib.metadata
import math
from dataclasses import replace
from pathlib import Path
from time import perf_counter

import numpy as np

from h2physics.adapters.cantera import MechanismBasis
from h2physics.adapters.cantera_multiphase import (
    CanteraMultiphaseEquilibrium,
    EquilibriumPhase,
    MultiphaseEquilibriumError,
    MultiphaseFeed,
    MultiphaseSettings,
)
from h2physics.core import Origin


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    import cantera as ct

    root = Path(__file__).resolve().parents[1]
    data = Path(ct.__file__).parent/"data"
    host_names = ("src/h2physics/adapters/cantera_multiphase.py", "tests/test_cantera_multiphase.py",
        "scripts/check_cantera_multiphase.py", "docs/MULTIPHASE_CONVERSION.md",
        "src/h2physics/adapters/cantera.py", "src/h2physics/adapters/cantera_volume.py")
    before = {name: sha(root/name) for name in host_names}
    distribution = importlib.metadata.distribution("cantera")
    license_file = next(Path(distribution.locate_file(p)) for p in distribution.files
                        if str(p).endswith("licenses/License.txt"))
    native_paths = {"gri30.yaml": data/"gri30.yaml", "graphite.yaml": data/"graphite.yaml",
        "Cantera License.txt": license_file, "Cantera compiled extension": Path(ct._cantera.__file__)}
    native_before = {name: sha(path) for name, path in native_paths.items()}

    def specification(file, name, role, *, subset=False):
        raw = (data/file).read_bytes()
        def factory():
            native = ct.Solution(yaml=raw.decode("utf-8"), name=name)
            if subset:
                selected = ct.Solution(thermo="ideal-gas", species=[native.species(s) for s in ("CO", "CO2")],
                                       name="authored-CO-CO2-selection")
                selected.TP = native.TP
                return selected
            return native
        basis = MechanismBasis("installed-"+name+("-authored-subset" if subset else ""), sha(data/file),
            "Cantera BSD-3-Clause; installed upstream thermochemistry provenance retained",
            ("https://cantera.org/3.2/python/thermo.html#cantera.Mixture",), 300., 2800., 1e4, 1e6)
        return EquilibriumPhase("gas" if role == "gas" else "carbon", role, factory, basis,
            "caller-declared-native-NASA-standard-formation-and-third-law", "native-mechanism-H2-spin-unresolved")

    phases = (specification("gri30.yaml", "gri30", "gas"),
              specification("graphite.yaml", "graphite", "solid"))
    engine = CanteraMultiphaseEquilibrium(phases)
    rich = MultiphaseFeed(750., 101325., {"gas": {"CH4": .6, "H2O": .12, "CO2": .08, "AR": .2},
        "carbon": {"C(gr)": 0.}}, "authored-rich-finite-feed", Origin.SYNTHETIC)
    wet = MultiphaseFeed(1100., 101325., {"gas": {"H2O": .7, "CO2": .15, "H2": .05, "AR": .1},
        "carbon": {"C(gr)": .18}}, "authored-steam-carbon-finite-feed", Origin.SYNTHETIC)
    started = perf_counter()
    appeared = engine.equilibrate(rich)
    disappeared = engine.equilibrate(wet)
    adiabatic = engine.equilibrate(wet, constraint="HP")
    tighter = engine.equilibrate(wet, constraint="HP", settings=MultiphaseSettings(relative_tolerance=1e-12))
    subset_engine = CanteraMultiphaseEquilibrium((specification("gri30.yaml", "gri30", "gas", subset=True), phases[1]))
    simple_feed = MultiphaseFeed(800., 101325., {"gas": {"CO": 1.}, "carbon": {}},
                                "authored-single-reaction-oracle", Origin.SYNTHETIC)
    analytic_case = subset_engine.equilibrate(simple_feed)
    gas, carbon = (p.factory() for p in subset_engine.phases)
    potentials = {}
    for species in ("CO", "CO2"):
        gas.TPX = 800., 101325., {species: 1.}
        potentials[species] = gas.chemical_potentials[gas.species_index(species)]
    carbon.TP = 800., 101325.
    equilibrium_constant = math.exp(-(potentials["CO2"]+carbon.chemical_potentials[0]-2*potentials["CO"])
                                     /(ct.gas_constant*800.))
    exact_extent = .5*(1-1/math.sqrt(1+4*equilibrium_constant))
    extent_error = abs(analytic_case.amount_mol("carbon", "C(gr)")-exact_extent)
    gas_limit = phases[0].factory()
    gas_limit.TPX = 1100., 101325., {**dict(wet.species_mol["gas"]), "C": .18}
    gas_limit.equilibrate("TP", solver="gibbs", rtol=1e-10)
    gas_limit_error = float(np.max(abs(gas_limit.X-disappeared.owned_phases[0].X)))
    failures = {}
    for label, candidate, supplied_feed, settings in (
        ("one-native-step-budget", engine, rich, MultiphaseSettings(maximum_steps=1)),
        ("zero-total-carbon-solid-candidate-HP", engine,
         MultiphaseFeed(750., 101325., {"gas": {"H2": .05, "O2": .025, "AR": .925}, "carbon": {}},
                        "authored-native-HP-failure-probe", Origin.SYNTHETIC), MultiphaseSettings())):
        try:
            candidate.equilibrate(supplied_feed, constraint="TP" if label.startswith("one") else "HP", settings=settings)
        except MultiphaseEquilibriumError as error:
            failures[label] = error
    narrow = CanteraMultiphaseEquilibrium(tuple(replace(p, mechanism_basis=replace(
        p.mechanism_basis, minimum_temperature_k=1099.)) for p in phases))
    try:
        narrow.equilibrate(wet, constraint="HP")
    except MultiphaseEquilibriumError as error:
        failures["completed-native-HP-outside-host-envelope"] = error
    all_results = (appeared, disappeared, adiabatic, tighter, analytic_case)
    after = {name: sha(root/name) for name in host_names}
    native_after = {name: sha(path) for name, path in native_paths.items()}
    gates = {
        "actual native Mixture owns every equilibrium solve": all(isinstance(r.native_mixture, ct.Mixture) for r in all_results),
        "all reference states pass material/constraint/chemical audits": all(r.accepted for r in all_results),
        "solid appears from zero feed": appeared.initial.phase_mol[1] == 0 and appeared.final.phase_mol[1] > .05,
        "initial carbon disappears with positive absent-phase affinity": disappeared.final.phase_mol[1] == 0
            and disappeared.chemical_audit.absent_solid_affinity_over_rt["carbon"] > 0,
        "independent Boudouard mass-action extent error <1e-9 mol": extent_error < 1e-9,
        "native gas-only no-solid TP composition limit error <1e-7": gas_limit_error < 1e-7,
        "TP heat is separate from HP adiabatic enthalpy": appeared.heat_into_j != 0 and disappeared.heat_into_j != 0
            and adiabatic.heat_into_j == 0,
        "independent HP tolerance replay T error <1e-4 K": abs(adiabatic.final.temperature_k-tighter.final.temperature_k) < 1e-4,
        "native solver failures retain actual mixture/cause": len(failures) == 3 and all(
            isinstance(e.native_mixture, ct.Mixture) and e.__cause__ is not None and e.initial is not None
            for e in failures.values()),
        "post-completed native domain failure retains final candidate": failures.get("completed-native-HP-outside-host-envelope") is not None
            and failures["completed-native-HP-outside-host-envelope"].native_solver_completed
            and failures["completed-native-HP-outside-host-envelope"].final is not None,
        "source phase definitions and owned native phases are independent": all(
            all(a is not b for a, b in zip(r.source_phases, r.owned_phases, strict=True)) for r in all_results),
        "host/test/script/docs and reused contracts unchanged": before == after,
        "installed thermochemical sources/license/binary unchanged": native_before == native_after,
        "new host inputs are LF text": all(b"\r" not in (root/name).read_bytes() for name in host_names[:4]),
    }
    elapsed = perf_counter()-started
    lines = ["# Native gas/solid equilibrium conversion reference", "",
        "Reproduce: `python scripts/check_cantera_multiphase.py` with optional Cantera3.2.", "",
        f"Actual Cantera{ct.__version__}; five accepted equilibrium/reference solves plus native failure probes "
        f"and independent audits took {elapsed:.6g}s. No native source or thermochemical table is bundled or modified.", "",
        "Original numerical feeds use SI mol at101325Pa. Rich case750K: gas CH4=.6,H2O=.12,CO2=.08,Ar=.2mol, "
        "graphite0mol. Steam-carbon case1100K: gas H2O=.7,CO2=.15,H2=.05,Ar=.1mol and graphite.18mol. "
        "The independent CO/CO2 subset case starts from1mol CO and zero graphite at800K. These compositions are "
        "authored verification inputs, not native worked examples, biomass/catalyst measurements or apparatus data.", "",
        "The native engine is ct.Mixture, with one ideal-gas phase and neutral fixed-stoichiometry constant-volume "
        "solids. Native amounts are kmol; the public amounts/element counts are mol. H/U/G use J, S uses J/K and "
        "chemical potentials use J/mol. Thermochemical source identities and the caller-declared common NASA formation/"
        "third-law reference are retained per phase; the adapter cannot prove a caller's provenance claim. H2 spin is "
        "mechanism-unresolved, with no CoolProp/ParaHydrogen energy-zero substitution.", "",
        "| Case | Constraint | Final T K | Gas mol | Graphite mol | H2 mol | CO mol | Heat into J | PV work out J |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|",
        *(f"| {name} | {r.constraint} | {r.final.temperature_k:.12g} | {r.final.phase_mol[0]:.12g} | "
          f"{r.final.phase_mol[1]:.12g} | {r.amount_mol('gas', 'H2'):.12g} | {r.amount_mol('gas', 'CO'):.12g} | "
          f"{r.heat_into_j:.12g} | {r.pressure_volume_work_out_j:.12g} |" for name, r in
          (("carbon appearance", appeared), ("carbon disappearance", disappeared), ("adiabatic conversion", adiabatic))), "",
        "TP specifies a thermostat at constant pressure: Q_into=H_final-H_initial, with PV work out=P*(V_final-V_initial). "
        "HP specifies adiabatic constant-pressure equilibrium: Q=0, total H is retained. Independent first-law checks use "
        "delta_U+P*delta_V-Q. Formation energy already belongs to native H/U; no separate reaction heat is added. "
        "These finite equilibrium heats are J, not a measured rate, fire power or cycle efficiency.", "",
        "| Case | Mass residual kg | Max element residual mol | H-constraint residual J | First-law residual J | Populated max affinity/RT |",
        "|---|---:|---:|---:|---:|---:|",
        *(f"| {name} | {r.mass_residual_kg:.12g} | {float(np.max(abs(r.element_residual_mol))):.12g} | "
          f"{r.enthalpy_constraint_residual_j:.12g} | {r.energy_balance_residual_j:.12g} | "
          f"{r.chemical_audit.maximum_populated_affinity_over_rt:.12g} |" for name, r in
          (("appearance", appeared), ("disappearance", disappeared), ("HP", adiabatic))), "",
        "Chemical-potential auditing independently fits elemental potentials to populated feasible species and checks "
        "mu-A.T*lambda. Species containing initially unavailable elements are excluded from this fit. "
        "Trace cutoff=max(1e-14mol,1e-10*initial totalmol) is explicit; omitted trace species are counted, not declared "
        "individually converged. Feasible pure solids below that amount threshold also require nonnegative formation "
        "affinity. A populated gas phase is required; an absent-gas tangent-plane stability calculation is not implemented.", "",
        f"Disappeared-carbon formation affinity/RT={disappeared.chemical_audit.absent_solid_affinity_over_rt['carbon']:.12g}. "
        f"Boudouard native carbon={analytic_case.final.phase_mol[1]:.12g}mol, independently derived extent={exact_extent:.12g}mol, "
        f"error={extent_error:.12g}mol. Pure native chemical potentials at the same T/P define the mass-action constant; "
        "the closed-form finite-extent oracle does not call an equilibrium solver. Gas-only TP comparison preserves elements, "
        f"not the graphite-versus-atomic-carbon feed enthalpy; max X error={gas_limit_error:.12g}. "
        f"HP rtol1e-10/1e-12 finalT difference={abs(adiabatic.final.temperature_k-tighter.final.temperature_k):.12g}K.", "",
        "| Retained failure probe | Native returned | Final snapshot present | Actual partial/native T K | Original cause |",
        "|---|---|---|---:|---|",
        *(f"| {name} | {e.native_solver_completed} | {e.final is not None} | {e.native_mixture.T:.12g} | "
          f"{type(e.__cause__).__name__}: {str(e).strip().replace(chr(10), ' ')[:350]} |" for name, e in failures.items()), "",
        "The zero-total-carbon H2/O2/Ar HP case with an explicit zero graphite candidate actually fails native "
        "temperature convergence. It is not replaced by a gas-only solve, another algorithm or a removed phase. "
        "The source of this native failure has not been independently established. The returned exception preserves "
        "the real partial Mixture, phases, initial snapshot and original cause; no final equilibrium is fabricated. "
        "A separate successful carbon/steam HP solve outside a deliberately narrow host envelope preserves its completed "
        "final snapshot. Cantera documents multiphase solver limitations. HP internal trial temperatures/iteration "
        "history are not exposed by this public API; only supplied and returned states are domain-admitted here. "
        "No claim of bounded internal trial extrapolation or a certified global convergence history is made.", "",
        "| Verification gate | Pass |", "|---|---|", *(f"| {name} | {passed} |" for name, passed in gates.items()), "",
        "This is an equilibrium carbon/steam gasification reference and a generic gas/pure-solid core. It does not "
        "predict reaction times, particle transport, porous char reactivity, coke kinetics, catalyst behavior, ashes, "
        "biomass conversion, a validated solid-redox cycle or full process efficiency. Solids not supplied as candidates "
        "cannot appear. No independent measured comparison has been performed. Additional phase models, charged phases, "
        "absent-gas stability and coupled boundary dynamics require separately evidenced native capabilities.", "",
        "Primary references: [native Mixture API and solver limitations](https://cantera.org/3.2/python/thermo.html#cantera.Mixture), "
        "[installed GRI30 provenance](https://cantera.org/3.2/examples/input/gri30.html), "
        "[native graphite definition and NASA source references](https://github.com/Cantera/cantera/blob/v3.2.0/data/graphite.yaml), "
        "[NASA thermochemical coefficient reference](https://ntrs.nasa.gov/citations/19940013151). "
        "Cantera BSD-3-Clause implementation rights and upstream thermochemical provenance are distinct; files remain "
        "separately installed, and no mechanism or printed coefficient table is redistributed here.", "",
        "## Source fingerprints", "", "New module/test/script/docs were checked as LF-only bytes; report is written with explicit LF.", "",
        "| Host input | Begin SHA256 | End SHA256 |", "|---|---|---|",
        *(f"| {name} | {value} | {after[name]} |" for name, value in before.items()), "",
        "| Installed input | Begin SHA256 | End SHA256 |", "|---|---|---|",
        *(f"| {name} | {value} | {native_after[name]} |" for name, value in native_before.items()), "",
        "| Phase | Source native definition | Owned native definition | Numeric roundtrip count /max relative |",
        "|---|---|---|---|", *(f"| {p.phase_id} | {a.source_fingerprint} | {a.owned_fingerprint} | "
        f"{a.numeric_roundtrip_count} /{a.maximum_relative_roundtrip:.12g} |" for p, a in
        zip(appeared.phases, appeared.phase_copy_audits, strict=True)), ""]
    (root/"research/multiphase_conversion.md").write_text("\n".join(lines), encoding="utf-8", newline="\n")
    for name, passed in gates.items():
        print(f"{'PASS' if passed else 'FAIL'} {name}", flush=True)
    print(f"Actual native equilibrium replay {elapsed:.6g}s; research/multiphase_conversion.md", flush=True)
    return 0 if all(gates.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
