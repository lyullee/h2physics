"""Actual native finite oxide-cycle calorimetry, without a yield/kinetics claim."""

import argparse
import hashlib
from pathlib import Path
from time import perf_counter

import numpy as np

from h2physics.adapters.cantera import MechanismBasis
from h2physics.adapters.cantera_caloric import CanteraMultiphaseMolarEnthalpy, SolidDensityEvidence
from h2physics.adapters.cantera_multiphase import EquilibriumPhase
from h2physics.core import Origin
from h2physics.reactions import StoichiometricReaction
from h2physics.thermochemical import (
    FiniteThermochemicalCycle,
    PrescribedConversion,
    ThermochemicalCycleError,
    ThermochemicalEvidence,
    ThermochemicalFeed,
    ThermochemicalInventory,
    ThermochemicalStage,
)


def authored_native_provider():
    """Original fixture factories; the installed library owns all thermo/EOS."""
    import cantera as ct

    data = Path(ct.__file__).parent / "data"

    def phase(identifier, species=None, density=None):
        path = data / ("nasa_condensed.yaml" if species else "h2o2.yaml")
        raw = path.read_bytes()

        def factory():
            if species is None:
                return ct.Solution(yaml=raw.decode("utf-8"), name="ohmech")
            item = next(
                s
                for s in ct.Species.list_from_yaml(raw.decode("utf-8"), "species")
                if s.name == species
            )
            definition = dict(item.input_data)
            definition["equation-of-state"] = {"model": "constant-volume", "density": density}
            native = ct.Solution(
                thermo="fixed-stoichiometry",
                species=[ct.Species.from_dict(definition)],
                name=identifier,
                transport_model="none",
            )
            native.TP = 300.0, 101325.0
            return native

        basis = MechanismBasis(
            "authored-cycle-native:" + identifier,
            hashlib.sha256(raw).hexdigest(),
            "Cantera BSD-3-Clause; upstream NASA thermochemistry",
            ("https://ntrs.nasa.gov/citations/19940013151",),
            300.0,
            1650.0,
            1e4,
            2e6,
        )
        return EquilibriumPhase(
            identifier,
            "solid" if species else "gas",
            factory,
            basis,
            "native-NASA-standard-formation-reference",
            "native-H2-spin-unresolved",
        )

    phases = (phase("Fe3O4", "Fe3O4(s)", 4800.0), phase("FeO", "FeO(s)", 5000.0), phase("gas"))
    mapping = (
        ("Fe3O4", "Fe3O4(s)", "Fe3O4"),
        ("FeO", "FeO(s)", "FeO"),
        ("gas", "H2O", "H2O"),
        ("gas", "H2", "H2"),
        ("gas", "O2", "O2"),
    )
    evidence = {
        name: SolidDensityEvidence(
            density,
            "authored-density-fixture",
            Origin.SYNTHETIC,
            "Authored constant-density caloric fixture; no measured EOS or phase-stability evidence",
        )
        for name, density in (("Fe3O4", 4800.0), ("FeO", 5000.0))
    }
    return CanteraMultiphaseMolarEnthalpy(phases, mapping, solid_density_evidence=evidence)


def authored_cycle(provider, *, extent=0.1):
    reduction = StoichiometricReaction(
        "authored-oxide-reduction", provider.species, (-1, 3, 0, 0, 0.5)
    )
    oxidation = StoichiometricReaction(
        "authored-steam-oxidation", provider.species, (1, -3, -1, 1, 0)
    )
    initial = ThermochemicalInventory({"Fe3O4": 1.0}, 300.0, 101325.0, provider.basis_id)
    feed = ThermochemicalFeed(
        ThermochemicalInventory({"H2O": extent}, 500.0, 101325.0, provider.basis_id),
        "authored-steam-feed",
        Origin.SYNTHETIC,
    )
    stages = (
        ThermochemicalStage(
            "reduction",
            100.0,
            110.0,
            "authored-clock",
            1400.0,
            (PrescribedConversion(reduction, extent, "prescribed-extent"),),
            "authored-hot-stage",
        ),
        ThermochemicalStage(
            "steam-oxidation",
            110.0,
            120.0,
            "authored-clock",
            900.0,
            (PrescribedConversion(oxidation, extent, "prescribed-extent"),),
            "authored-cold-stage",
            feeds=(feed,),
            pre_withdrawal_mol={"O2": extent * 0.5},
        ),
        ThermochemicalStage(
            "carrier-reset",
            120.0,
            130.0,
            "authored-clock",
            300.0,
            (),
            "authored-carrier-cooling",
            pre_withdrawal_mol={"H2": extent},
        ),
    )
    return initial, stages


def main():
    import cantera as ct
    import scipy

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, default=Path("research/thermochemical_cycle.md"))
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    paths = (
        "src/h2physics/thermochemical.py",
        "tests/test_thermochemical.py",
        "scripts/check_thermochemical_cycle.py",
        "src/h2physics/reactions.py",
        "src/h2physics/adapters/cantera_caloric.py",
        "docs/THERMOCHEMICAL_CYCLES.md",
    )

    def hashes():
        return {p: hashlib.sha256((root / p).read_bytes()).hexdigest() for p in paths}

    before = hashes()
    start = perf_counter()
    provider = authored_native_provider()
    evidence = ThermochemicalEvidence(
        "authored-finite-oxide-campaign",
        "native-ideal-gas-and-pure-solids-additive-H",
        "prescribed-component-withdrawal-not-separator",
        "constant-P-no-nonPV-work-required-heat",
        Origin.SYNTHETIC,
    )
    engine = FiniteThermochemicalCycle(provider, evidence)
    initial, stages = authored_cycle(provider)
    trace = engine.run(
        initial, stages, carrier_species=("Fe3O4", "FeO"), require_full_inventory_closed=True
    )

    # Fresh factories, not the provider's owned/source instances, reconstruct
    # each extensive mixture enthalpy independently in native kmol units.
    independent_phases = [spec.factory() for spec in provider.phases]
    mixture = ct.Mixture([(p, 0.0) for p in independent_phases])

    def native_h(inventory):
        mixture.T, mixture.P = inventory.temperature_k, inventory.pressure_pa
        n = np.zeros(mixture.n_species)
        for mapping in provider.species_mapping:
            phase_index = next(
                i for i, p in enumerate(provider.phases) if p.phase_id == mapping.phase_id
            )
            index = mixture.species_index(phase_index, mapping.native_species)
            n[index] = inventory.amounts_mol.get(mapping.host_alias, 0.0) / 1000.0
        mixture.species_moles = n
        return float(
            sum(mixture.phase_moles(i) * p.enthalpy_mole for i, p in enumerate(independent_phases))
        )

    independent_errors = []
    for step in trace.steps:
        h_before, h_after = native_h(step.before), native_h(step.after)
        feed_h = sum(native_h(f.inventory) for f in step.stage.feeds)
        withdrawal = ThermochemicalInventory(
            step.stage.pre_withdrawal_mol,
            step.before.temperature_k,
            step.before.pressure_pa,
            provider.basis_id,
        )
        withdrawal_h = native_h(withdrawal)
        independent_errors.append(h_after - h_before - feed_h + withdrawal_h - step.heat_required_j)
    # Independent net gas export/import at their actual supplied temperatures.
    net_reference = (
        native_h(ThermochemicalInventory({"O2": 0.05}, 1400.0, 101325.0, provider.basis_id))
        + native_h(ThermochemicalInventory({"H2": 0.1}, 900.0, 101325.0, provider.basis_id))
        - native_h(ThermochemicalInventory({"H2O": 0.1}, 500.0, 101325.0, provider.basis_id))
    )
    short_initial, short_stages = authored_cycle(provider, extent=0.04)
    short = engine.run(
        short_initial,
        short_stages,
        carrier_species=("Fe3O4", "FeO"),
        require_full_inventory_closed=True,
    )
    from types import SimpleNamespace

    scratch = np.zeros(len(provider.species))

    def cached_enthalpies(temperature, pressure):
        scratch[:] = provider.enthalpies_j_mol(temperature, pressure)
        return scratch

    cached_provider = SimpleNamespace(
        species=provider.species,
        basis_id=provider.basis_id,
        enthalpies_j_mol=cached_enthalpies,
    )
    cached_trace = FiniteThermochemicalCycle(cached_provider, evidence).run(
        initial, stages, carrier_species=("Fe3O4", "FeO"), require_full_inventory_closed=True
    )
    buffer_error = max(
        abs(a.heat_required_j - b.heat_required_j)
        for a, b in zip(trace.steps, cached_trace.steps, strict=True)
    )
    overflow_rejected = False
    huge = ThermochemicalInventory({"Fe3O4": 1e308}, 300.0, 101325.0, provider.basis_id)
    hold = ThermochemicalStage("overflow-probe", 0.0, 1.0, "clock", 300.0, (), "authored")
    try:
        engine.run(huge, (hold,), carrier_species=("Fe3O4",))
    except ThermochemicalCycleError as error:
        overflow_rejected = (
            error.before is huge and error.stage is hold and error.__cause__ is not None
        )
    nonclosure_rejected = depletion_rejected = False
    try:
        engine.run(
            initial, stages[:1], carrier_species=("Fe3O4", "FeO"), require_temperature_closed=False
        )
    except ThermochemicalCycleError as error:
        nonclosure_rejected = error.trace is not None and not error.trace.carrier_closed
    bad_start, bad_stages = authored_cycle(provider, extent=1.1)
    try:
        engine.run(bad_start, bad_stages, carrier_species=("Fe3O4", "FeO"))
    except ThermochemicalCycleError as error:
        depletion_rejected = (
            not error.completed_steps and error.before is bad_start and error.__cause__ is not None
        )
    after = hashes()
    gates = {
        "executed sources unchanged": before == after,
        "actual native caloric phases and existing reaction conversions retained": trace.enthalpy_provider
        is provider
        and len(provider.owned_phases) == 3
        and all(
            len(s.conversions) == (0 if s.stage.identifier == "carrier-reset" else 1)
            for s in trace.steps
        ),
        "carrier composition and temperature return without resetting amounts": trace.carrier_closed
        and trace.temperature_closed
        and trace.full_inventory_closed,
        "finite water feed and separate H2/O2 export ratio": abs(trace.feed_mol[2] - 0.1) < 1e-14
        and abs(trace.exported_mol[3] - 0.1) < 1e-14
        and abs(trace.exported_mol[4] - 0.05) < 1e-14,
        "global element and mass defects below1e-12mol/1e-14kg": np.max(
            abs(trace.element_residual_mol)
        )
        < 1e-12
        and abs(trace.mass_residual_kg) < 1e-14,
        "stage and global enthalpy ledgers below1e-6J": max(
            abs(trace.energy_residual_j), *(abs(s.energy_residual_j) for s in trace.steps)
        )
        < 1e-6,
        "fresh native mixture reconstructs every stage heat below1e-6J": max(
            abs(x) for x in independent_errors
        )
        < 1e-6,
        "net heat equals actual hot-product less cold-feed enthalpy below1e-6J": abs(
            trace.net_heat_required_j - net_reference
        )
        < 1e-6,
        "gross input less rejection equals signed net duty below1e-8J": abs(
            trace.gross_heat_input_j - trace.gross_heat_rejection_j - trace.net_heat_required_j
        )
        < 1e-8,
        "different finite supplied conversion retains correct material scaling": abs(
            short.exported_mol[3] - 0.04
        )
        < 1e-14
        and short.full_inventory_closed,
        "incomplete carrier loop retains completed trace": nonclosure_rejected,
        "over-depletion rejects without inventing conversion or feed": depletion_rejected,
        "reused native caloric buffer preserves all stage heat below1e-8J": buffer_error < 1e-8,
        "finite input with extensive overflow rejects with actual stage and cause": overflow_rejected,
    }
    elapsed = perf_counter() - start
    lines = [
        "# Finite thermochemical cycle enthalpy and material verification",
        "",
        f"Actual native Cantera{ct.__version__}; SciPy{scipy.__version__}; {elapsed:.9g}s.",
        "",
        "All extents, temperatures, clocks and solid densities are authored calorimetry inputs. "
        "No phase-stability, equilibrium/kinetic yield, source material or achievable iron-cycle claim is made. "
        "The existing reaction core owns finite conversion and native Cantera owns gas/solid enthalpies.",
        "",
        "The fixed101325Pa campaign begins with1mol Fe3O4 at300K. It prescribes0.1mol reduction extent "
        "at1400K during[100,110]s; withdraws0.05mol O2 at1400K; admits0.1mol steam at500K; "
        "prescribes0.1mol steam oxidation at900K during[110,120]s; withdraws0.1mol H2 at900K; "
        "and returns the carrier to300K during[120,130]s. Component withdrawals are imposed boundary "
        "operations, not predicted separator performance. Native FeO/Fe3O4 source fits admit these "
        "caloric evaluations; this does not establish thermochemical reaction feasibility.",
        "",
        "| Stage | Conditioning J | Reaction J | Total required heat J | Native-independent defect J |",
        "|---|---:|---:|---:|---:|",
        *(
            f"| {s.stage.identifier} | {s.conditioning_heat_required_j:.12g} | "
            f"{s.reaction_heat_required_j:.12g} | {s.heat_required_j:.12g} | {e:.12g} |"
            for s, e in zip(trace.steps, independent_errors, strict=True)
        ),
        "",
        f"Net duty={trace.net_heat_required_j:.12g}J; gross input={trace.gross_heat_input_j:.12g}J; "
        f"gross rejected={trace.gross_heat_rejection_j:.12g}J. Independent hot exports minus cold feed="
        f"{net_reference:.12g}J. Global energy defect={trace.energy_residual_j:.12g}J; mass defect="
        f"{trace.mass_residual_kg:.12g}kg; max element defect={np.max(abs(trace.element_residual_mol)):.12g}mol.",
        "",
        "Heat is required signed constant-pressure enthalpy input, not a predicted furnace power or utility. "
        "Mean W divides by the caller's stage duration; no residence time is inferred. No heat recovery, "
        "thermal storage, optical absorption, pressure-change work, non-PV work, mixture excess heat or "
        "solar efficiency is assumed. Carrier, thermal and complete-inventory closure remain separate tests.",
        "",
        "| Gate | Pass |",
        "|---|---|",
        *(f"| {n} | {v} |" for n, v in gates.items()),
        "",
        "Primary context: [DOE thermochemical cycles](https://www.energy.gov/cmei/fuels/hydrogen-production-thermochemical-water-splitting), "
        "[native NASA thermochemistry provenance](https://ntrs.nasa.gov/citations/19940013151), "
        "[native Cantera properties](https://cantera.org/3.2/python/thermo.html). "
        "No published operating table, coefficient array, worked example or source implementation is bundled.",
        "",
        "## Executed source identities",
        "",
        "| Host source | Begin SHA-256 | End SHA-256 |",
        "|---|---|---|",
        *(f"| `{p}` | `{before[p]}` | `{after[p]}` |" for p in paths),
        "",
    ]
    target = args.report if args.report.is_absolute() else root / args.report
    target.write_text("\n".join(lines), encoding="utf-8", newline="\n")
    for n, v in gates.items():
        print(f"{'PASS' if v else 'FAIL'} {n}")
    print(f"Actual finite thermochemical replay {elapsed:.6g}s; {target.name}")
    return 0 if all(gates.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
