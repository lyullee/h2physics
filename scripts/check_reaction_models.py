"""Audit actual computed carrier pairs and native constrained calorimetry."""

import hashlib
import importlib.metadata as metadata
from collections import Counter
from pathlib import Path

import numpy as np

from h2physics.adapters.cantera import MechanismBasis
from h2physics.adapters.cantera_thermo import CanteraMolarEnthalpy
from h2physics.data.lohc import audit_qm9_lohc_dataset, load_qm9_lohc_archive
from h2physics.reactions import StoichiometricReaction, conversion_heat_j, solve_product_temperature


def main():
    import cantera as ct

    root = Path(__file__).resolve().parents[1]
    inputs = ["src/h2physics/reactions.py", "src/h2physics/data/lohc.py",
              "src/h2physics/adapters/rdkit.py", "src/h2physics/adapters/cantera_thermo.py",
              "scripts/check_reaction_models.py"]
    fingerprints = {name: hashlib.sha256((root/name).read_bytes()).hexdigest() for name in inputs}
    source = root / "data/raw/lohc-enthalpies/QM9-LOHC/QM9-LOHC-QM9-LOHC.zip"
    archive = load_qm9_lohc_archive(source)
    audits = audit_qm9_lohc_dataset(archive)
    issues = Counter(issue for audit in audits for issue in audit.issues)
    pairs = Counter(a.pair_key for a in audits if a.pair_key is not None)
    valid_heat = [a for a in audits if a.reference_heat is not None]
    duplicate_groups = {}
    for audit in audits:
        if pairs.get(audit.pair_key, 0) > 1:
            duplicate_groups.setdefault(audit.pair_key, []).append(float(audit.row.cells["delta_H"]))
    maximum_pair_heat_spread = max((max(v)-min(v) for v in duplicate_groups.values()), default=0.)
    capacities = np.array([a.capacity_difference_percentage_points for a in audits])
    mass_diffs = np.array([a.lean_molar_mass_difference_g_mol for a in audits])
    maximum_mass_error = maximum_cycle_error = maximum_capacity_scaling_error = 0.
    total_reference_heat = 0.
    for audit in valid_heat:
        reaction = audit.reaction
        converted = reaction.convert({"rich": 1.}, 1.)
        backward = reaction.convert(converted.final_amounts, -1.)
        heat = audit.reference_heat
        total_reference_heat += heat.heat_j(converted, temperature_k=298.15, pressure_pa=101325)
        maximum_mass_error = max(maximum_mass_error, abs(converted.mass_residual_kg))
        maximum_cycle_error = max(maximum_cycle_error, max(abs(backward.final_mol-converted.initial_mol)))
        # Finite-inventory result and independent capacity expression must coincide.
        h2_mass = converted.final_amounts["H2"]*audit.hydrogen.species.molar_mass_kg_mol
        capacity = h2_mass/audit.rich.species.molar_mass_kg_mol
        maximum_capacity_scaling_error = max(maximum_capacity_scaling_error,
                                             abs(capacity-audit.calculated_capacity_mass_fraction))
    raw = (Path(ct.__file__).parent / "data/gri30.yaml").read_bytes()
    basis = MechanismBasis(f"Cantera:{ct.__version__}:gri30:prescribed-conversion",
        hashlib.sha256(raw).hexdigest(), "Cantera-BSD-3-Clause; upstream GRI-Mech provenance",
        ("https://cantera.org/3.2/examples/input/gri30.html",), 200, 3000, 1e4, 2e6)
    provider = CanteraMolarEnthalpy(lambda: ct.Solution(yaml=raw.decode("utf-8")), basis,
                                   ("CH4", "H2O", "CO", "H2"))
    reaction = StoichiometricReaction("authored-prescribed-steam-reforming", provider.species,
                                     (-1, -1, 1, 3))
    converted = reaction.convert({"CH4": 1, "H2O": 3}, .2)
    q = conversion_heat_j(converted, provider, inlet_temperature_k=298.15,
                          outlet_temperature_k=298.15, pressure_pa=101325)
    native = provider.native_phase
    native.TPX = 298.15, 101325, {"CH4": 1, "H2O": 3}
    hin = native.enthalpy_mole*4/1000
    native.TPX = 298.15, 101325, dict(converted.final_amounts)
    hout = native.enthalpy_mole*sum(converted.final_mol)/1000
    independent_heat_error = q-(hout-hin)
    result = solve_product_temperature(converted, provider, inlet_temperature_k=1200,
        pressure_pa=101325, supplied_heat_j=0, bracket_k=(400, 1600))
    gates = {
        "authoritative row count": len(audits) == 10373,
        "archive web table is an exact duplicate": archive.duplicate_table_matches,
        "all source rows have balanced molecular reactions": all(a.reaction is not None for a in audits),
        "versioned qualified reference-heat count": len(valid_heat) == 10317,
        "conflicting canonical-pair heats withheld": all(a.reference_heat is None for a in audits
            if "conflicting_reference_enthalpies_for_canonical_pair" in a.issues),
        "accepted molecular mass conservation <1e-12 kg per mol extent": maximum_mass_error < 1e-12,
        "accepted forward/reverse inventory cycle <1e-12 mol": maximum_cycle_error < 1e-12,
        "accepted independent capacity scaling <1e-14 mass fraction": maximum_capacity_scaling_error < 1e-14,
        "native mixture/species heat paths <1e-7 J": abs(independent_heat_error) < 1e-7,
        "native prescribed-extent calorimetry <1e-6 J": abs(result.energy_residual_j) < 1e-6,
    }
    lines = ["# Computed carrier reactions and constrained calorimetry", "",
        "This is data qualification and software/numerical verification. It is not measured "
        "liquid-carrier, catalyst, kinetic, equilibrium or process validation.", "",
        "## Actual acquired data", "",
        "Hassan Harb, HydrogenStorage/QM9-LOHC, release QM9-LOHC, "
        "[Zenodo 10.5281/zenodo.10926772](https://doi.org/10.5281/zenodo.10926772), CC BY 4.0. "
        "Interpretation uses the independently accessible "
        "[primary descriptor](https://doi.org/10.1038/s41597-025-04468-0). "
        "Its reference is gas-phase dehydrogenation at 298.15 K and 1 atm, in kJ/mol H2. "
        "Publisher values stay unmodified. Raw data and native molecular objects are excluded "
        "from public distributions.", "",
        f"Archive SHA-256 `{archive.source_sha256}`; authoritative CSV SHA-256 `{archive.member_sha256}`.",
        f"Rows: {len(audits)}; unique canonical ordered pairs: {len(pairs)}; extra repeated-pair rows: "
        f"{sum(n-1 for n in pairs.values())}; admitted reference-heat rows: {len(valid_heat)}. "
        "Repeated pairs and the duplicate web CSV are not independent reactions or validation data.", "",
        f"Repeated molecular-pair groups: {len(duplicate_groups)}; largest within-pair enthalpy "
        f"spread: {maximum_pair_heat_spread:.12g} kJ/mol H2. Conflicting pairs retain every "
        "original row, but all their reference heats are withheld by the dataset-level API. "
        "No average or first-row selection is used without additional molecular-state evidence.", "",
        f"Native mass reconstruction uses RDKit {metadata.version('rdkit')} average atomic weights "
        "for both carriers and H2; explicit isotopes/radicals are rejected by this level. "
        "The source molar_mass column is tested against the lean species. Source capacity "
        "differences are recorded at an explicit 0.01 percentage-point reporting threshold; "
        "a capacity discrepancy cannot change molecular stoichiometry or its computed heat.", "",
        "| Source issue | Rows |", "|---|---:|"]
    lines += [f"| {key} | {count} |" for key, count in sorted(issues.items())]
    lines += ["", f"Capacity reconstruction minus publisher range: {np.nanmin(capacities):.10g} to "
              f"{np.nanmax(capacities):.10g} percentage points; maximum absolute lean mass "
              f"difference: {np.nanmax(abs(mass_diffs)):.10g} g/mol.", "",
              "Rows without an admitted heat remain available with original cells, CSV line and "
              "member/archive identity. No unqualified row is silently repaired or dropped.", "",
              f"Largest accepted mass residual: {maximum_mass_error:.12g} kg; reverse-cycle error: "
              f"{maximum_cycle_error:.12g} mol; capacity-scaling error: "
              f"{maximum_capacity_scaling_error:.12g}. Aggregate reference duty for one mole extent "
              f"per admitted row is {total_reference_heat:.12g} J. "
              "That aggregate is a reproducibility checksum, not a realizable carrier blend.", "",
              "## Native thermochemistry reuse", "",
              f"Cantera {ct.__version__}, installed gri30.yaml SHA-256 `{basis.source_sha256}`. "
              "The native phase object, molecular weights, species compositions and caloric fits "
              "are used directly. Mechanism files are not bundled. Source/license context is "
              "[Cantera GRI input documentation](https://cantera.org/3.2/examples/input/gri30.html). "
              "This authored CH4/H2O -> CO + 3 H2 case imposes extent, without a catalyst or "
              "rate claim. Existing native equilibrium/reactor modules retain those solvers.", "",
              f"At 298.15 K and 101325 Pa: reaction heat {q/.2:.12g} J/mol extent; mixture/species "
              f"accounting difference {independent_heat_error:.12g} J. For one initial mol CH4, "
              "three mol steam, imposed extent 0.2 mol, inlet 1200 K and zero supplied heat: "
              f"outlet {result.temperature_k:.12g} K, enthalpy residual {result.energy_residual_j:.12g} J. "
              "The fitted thermochemistry's previously documented breakpoint behavior is not changed.", "",
              "## Authored numerical acceptance gates", "", "| Gate | Result |", "|---|---|"]
    lines += [f"| {key} | {'PASS' if passed else 'FAIL'} |" for key, passed in gates.items()]
    lines += ["", "These gates assess admitted data paths and bookkeeping; they do not require "
              "all publisher rows to be admissible, nor prove measured reaction heat, liquid "
              "stability, reversibility, safety or equipment performance.", "",
              "## Reproduction fingerprints", "", "| File | SHA-256 |", "|---|---|"]
    lines += [f"| {name} | `{value}` |" for name, value in fingerprints.items()]
    if fingerprints != {name: hashlib.sha256((root/name).read_bytes()).hexdigest() for name in inputs}:
        raise RuntimeError("Implementation changed while the audit was running")
    (root / "research/carrier_reactions.md").write_text("\n".join(lines)+"\n", encoding="utf-8", newline="\n")
    print(f"{len(audits)} rows, {len(valid_heat)} reference heats, {len(pairs)} pairs; issues={dict(issues)}")
    print(f"Native q={q/.2:.10g} J/mol, adiabatic T={result.temperature_k:.10g} K; gates={gates}")
    return 0 if all(gates.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
