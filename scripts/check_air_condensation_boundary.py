"""Retain an actual native diagnostic's rejected phase/composition boundary.

This is a source-owner extension reproducer, not a replacement equilibrium solver
or a source of oxygen-deficiency/dispersion predictions.
"""

import argparse
import hashlib
import importlib.metadata
import json
import sys
from pathlib import Path

EXPECTED_SOURCE = "c883b28baa6f002ad660f09b565f6226f41110f9d847f35b40a1290b4a4c8ec7"
ROOT = Path(__file__).resolve().parents[1]


def replay(native):
    path = Path(native.__file__)
    before = hashlib.sha256(path.read_bytes()).hexdigest()
    host = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    if before != EXPECTED_SOURCE or importlib.metadata.version("slabx-lh2") != "0.2.0":
        raise ValueError("Use the reviewed original native diagnostic, not an unreviewed replacement")
    calls, rows = [], []
    # Explicit input dry-air composition, matching the fixed native assumption.
    # Molecular masses below are queried from the actual provider, not copied.
    fractions = {"N2": .7808, "O2": .2095, "Ar": .0097}
    for w in (.005, .5):
        kwargs = dict(T_ambient=293.15, rh=0., p=101325., allow_air=True)
        raw = native.adiabatic_mix(w, **kwargs)
        calls.append((native.adiabatic_mix, (w,), kwargs, raw))
        masses = {name: native.SPECIES[name][1] for name in ("N2", "O2")}
        masses.update(Ar=native._M_AR, H2=native._M_H2)
        air_molar_mass = sum(fractions[k]*masses[k] for k in fractions)
        feed_moles = {k: (1-w)*fractions[k]/air_molar_mass for k in fractions}
        feed_moles["H2"] = w/masses["H2"]
        gas_moles = dict(feed_moles)
        for species, condensed in raw["condensed"].items():
            if species == "H2O":
                if condensed != 0.:
                    raise ValueError("A dry-air audit unexpectedly gained condensed water")
                continue
            gas_moles[species] -= condensed/masses[species]
        if any(v < 0 for v in gas_moles.values()):
            raise ValueError("Native condensed mass exceeds the declared feed inventory")
        total_feed = sum(feed_moles.values())
        total_gas = sum(gas_moles.values())
        partial = kwargs["p"]*gas_moles["O2"]/total_gas
        saturation = native.p_saturation("O2", raw["T"])
        calls.append((native.p_saturation, ("O2", raw["T"]), {}, saturation))
        rows.append(dict(hydrogen_feed_mass_fraction=w, native_output=raw,
            feed_moles_per_kg=feed_moles, gas_moles_per_kg=gas_moles,
            feed_hydrogen_mol_percent=100*feed_moles["H2"]/total_feed,
            gas_hydrogen_mol_percent=100*gas_moles["H2"]/total_gas,
            gas_oxygen_partial_pressure_pa=partial,
            native_oxygen_saturation_pa=None if saturation == float("inf") else saturation,
            relative_oxygen_supersaturation=None if saturation == float("inf") else partial/saturation-1,
            admitted_oxygen_phase_state=False if raw["condensed"]["O2"] > 0 else None))
    errors = []
    for value in (0., 1.):
        try:
            native.adiabatic_mix(value, T_ambient=293.15, rh=0., p=101325., allow_air=True)
        except ValueError as error:
            errors.append((native.adiabatic_mix, value, error))
    warm, cold = rows
    gates = {
        "warm no-air-condensate feed and gas compositions agree":
            all(v == 0 for v in warm["native_output"]["condensed"].values())
            and abs(warm["gas_hydrogen_mol_percent"]-warm["native_output"]["y_h2"]) < 1e-12,
        "original cold native O2 condensate is positive": cold["native_output"]["condensed"]["O2"] > .1,
        "original cold native O2 saturation failure reproduced":
            .04 < cold["relative_oxygen_supersaturation"] < .05,
        "native H2 output follows original feed rather than remaining gas":
            abs(cold["feed_hydrogen_mol_percent"]-cold["native_output"]["y_h2"]) < 1e-12
            and cold["gas_hydrogen_mol_percent"]-cold["native_output"]["y_h2"] > 4.,
        "native endpoint failures are original ValueErrors": len(errors) == 2,
        "native diagnostic source unchanged": hashlib.sha256(path.read_bytes()).hexdigest() == before,
        "executed host source unchanged": hashlib.sha256(Path(__file__).read_bytes()).hexdigest() == host,
    }
    if not all(gates.values()):
        raise ValueError("Reviewed native diagnostic boundary changed; inspect before updating its evidence")
    return dict(rows=rows, gates=gates, native_source_sha256=before, host_source_sha256=host,
        failure_causes=[dict(argument=w, type=type(e).__name__, message=str(e)) for _, w, e in errors]), calls, errors


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--native-packages", type=Path, default=Path("artifacts/native_slabx_packages"))
    parser.add_argument("--report", type=Path, default=Path("research/native_air_condensation_review.md"))
    parser.add_argument("--details", type=Path, default=Path("artifacts/air_condensation_boundary.json"))
    args = parser.parse_args()
    sys.path.append(str(args.native_packages.resolve()))
    from slabx_lh2 import air_condensation

    report, calls, failures = replay(air_condensation)
    args.details.write_text(json.dumps(report, indent=2, allow_nan=False), encoding="utf-8")
    cold = report["rows"][1]
    rows = ["# Rejected native air-condensation diagnostic boundary", "",
        "This reproduces a source-owner correction request. It adds no accepted model family or production phase/ODH result. "
        "The separately installed MIT SLABx-LH2 0.2.0 diagnostic is unmodified. It is a constant-Cp standalone comparison "
        "with a fixed20.37K H2 inlet and a fixed dry-air composition; it is not the accepted steady dispersion execution. "
        "The finite oxygen-room and ordinary-air human thermal adapters do not call it.", "",
        "The authored audit uses a1kg feed, dry293.15K air at101325Pa and explicit input mole fractions "
        "N2=.7808, O2=.2095, Ar=.0097. Original native molecular masses and returned condensate masses reconstruct "
        "the remaining gas inventory; no substitute thermodynamic solve or correction is applied. "
        "Positive O2 condensate requires its remaining-gas partial pressure to match the selected native saturation pressure "
        "under that diagnostic's own ideal-partial-pressure assumption.", "",
        f"At H2 feed mass fraction0.5 the actual native temperature is{cold['native_output']['T']:.12g}K, "
        f"O2 condensate{cold['native_output']['condensed']['O2']:.12g}kg/kgfeed, "
        f"remaining-gas O2 partial pressure{cold['gas_oxygen_partial_pressure_pa']:.12g}Pa "
        f"and actual native O2 saturation{cold['native_oxygen_saturation_pa']:.12g}Pa. "
        f"The relative excess is{100*cold['relative_oxygen_supersaturation']:.8g}%: this phase state is rejected.", "",
        f"Native y_h2={cold['native_output']['y_h2']:.12g}mol% matches the original total-feed gas-mole basis. "
        f"The actual remaining-gas inventory gives{cold['gas_hydrogen_mol_percent']:.12g}mol%. "
        "Those are different bases; the original native result is retained, not overwritten. "
        "Native source uses a pre-condensation total-mole denominator in each saturation cap. "
        "Coupled remaining-gas normalization/complementarity and explicit returned gas/feed bases need a native-owner fix. "
        "Finite condensed-phase volume, solid/liquid calorimetry and a full cloud/room coupling are not independently qualified here.", "",
        "At feed mass fraction0.005 no air condenses and feed/gas H2 fractions agree. "
        "Original endpoint errors atw=0/1 remain ValueErrors. Actual native function/argument/raw-result references "
        "and original exceptions are retained during replay. Exact scalar/input detail is emitted only under ignored artifacts.", "",
        "| Negative-evidence verification gate | Pass |", "|---|---|"]
    rows += [f"| {name} | {value} |" for name, value in report["gates"].items()]
    rows += ["", "| Executed host source | SHA256 before/after |", "|---|---|",
        f"| scripts/check_air_condensation_boundary.py | {report['host_source_sha256']} |", "",
        f"Actual native air_condensation.py SHA256 before/after: `{report['native_source_sha256']}`.", "",
        "Reproduce with `python scripts/check_air_condensation_boundary.py` using the reviewed separately installed target. "
        "Source provenance remains in [preferred_dispersion.md](preferred_dispersion.md). "
        "Request022 specifies the receiving fix; no receiving repository or native implementation was changed. "
        "This is an internal conservation/phase-consistency failure, not an experimental comparison or a replacement mixture EOS."]
    args.report.write_text("\n".join(rows)+"\n", encoding="utf-8", newline="\n")
    print(f"Retained original native diagnostic: {len(report['gates'])}/{len(report['gates'])} negative-evidence gates; "
          f"actualcalls={len(calls)}, originalfailures={len(failures)}, coldphaseaccepted=False")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
