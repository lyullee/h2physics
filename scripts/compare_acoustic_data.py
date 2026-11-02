"""Compare acquired acoustic observations without inferring missing p or composition."""

import io
from pathlib import Path
from zipfile import ZipFile

import numpy as np

from h2physics.data.pif import acoustic_columns, read_property_file
from h2physics.thermo import CoolPropProperties


def main():
    root = Path(__file__).resolve().parents[1]
    archive_path = root / "data/raw/hydrogen-sound-speed/1.0.0/H2_speedofsound_dataset.zip"
    providers = {"normal-H2": CoolPropProperties("Hydrogen"),
                 "para-H2": CoolPropProperties("ParaHydrogen")}
    lines = ["# Acoustic observation comparison", "",
             "Source: Latcham, Bernardini, Richter and Trusler (2026), "
             "[dataset v1.0.0](https://doi.org/10.5281/zenodo.21355851), CC BY 4.0.", "",
             "Original numeric parser; the separately supplied program is not used. "
             "Errors are 100 × (HEOS − observation)/observation. "
             "Composition-unspecified records and missing pressures are excluded. "
             "No saturation pressure is reconstructed. Source uncertainties are retained "
             "in the acquired records but are not treated as standard deviations.", "",
             "This is an external consistency comparison. Overlap between historical "
             "observations and EOS development data is unresolved; it is not a blind "
             "validation or a new qualification of every state in the EOS domain.", "",
             "| File | Composition | Rows | Compared | Excluded | Mean signed % | Mean abs % | Max abs % |",
             "|---|---|---:|---:|---:|---:|---:|---:|"]
    totals = dict(files=0, rows=0, compared=0)
    exclusions = {}
    all_errors = []
    with ZipFile(archive_path) as archive:
        for member in sorted(archive.namelist()):
            if not member.endswith(".txt") or "summary" in member:
                continue
            with archive.open(member) as binary:
                data = read_property_file(io.TextIOWrapper(binary, encoding="utf-8-sig"))
            composition = data.metadata.get("_exptl_material_composition", "unspecified")
            provider = providers.get(composition)
            errors, count = [], 0
            for loop in data.loops:
                temperatures, pressures, speeds = acoustic_columns(data, loop)
                for temperature, pressure, speed in zip(temperatures, pressures, speeds):
                    count += 1
                    reason = None
                    if provider is None:
                        reason = "unsupported or unspecified spin composition"
                    elif not np.all(np.isfinite([temperature, pressure, speed])):
                        reason = "missing observed T, p or sound speed"
                    elif min(temperature, pressure, speed) <= 0:
                        reason = "nonpositive observed state or sound speed"
                    else:
                        try:
                            state = provider.state_pt(pressure, temperature)
                            if state.speed_of_sound_m_s is None:
                                reason = "sound speed unavailable at this state"
                            elif data.metadata.get("_exptl_material_state") == "gas" and state.phase == "liquid":
                                reason = "observed gas label conflicts with EOS phase"
                            else:
                                errors.append(100 * (state.speed_of_sound_m_s - speed) / speed)
                        except ValueError:
                            reason = "EOS rejected the declared state"
                    if reason:
                        exclusions[reason] = exclusions.get(reason, 0) + 1
            values = np.asarray(errors)
            metrics = ([f"{np.mean(values):.6g}", f"{np.mean(abs(values)):.6g}",
                        f"{np.max(abs(values)):.6g}"] if len(values) else ["—"] * 3)
            lines.append(f"| {Path(member).stem} | {composition} | {count} | {len(values)} | "
                         f"{count-len(values)} | " + " | ".join(metrics) + " |")
            totals["files"] += 1
            totals["rows"] += count
            totals["compared"] += len(values)
            all_errors.extend(errors)
    lines.extend(["", "## Reproduction and exclusions", "",
                  f"CoolProp {next(iter(providers.values())).version}; HEOS; "
                  f"{totals['files']} data files, {totals['rows']} observations, "
                  f"{totals['compared']} compared observations.", ""])
    lines.extend(f"- {reason}: {count}" for reason, count in sorted(exclusions.items()))
    if all_errors:
        lines.extend(["", f"Aggregate mean absolute relative deviation: "
                      f"{np.mean(np.abs(all_errors)):.6g} %. "
                      "The aggregate weights observations, not experiments; heterogeneous "
                      "historical precision and repeated sources prevent a universal accuracy claim."])
    (root / "research/acoustic_comparison.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(totals, "excluded", exclusions)


if __name__ == "__main__":
    main()
