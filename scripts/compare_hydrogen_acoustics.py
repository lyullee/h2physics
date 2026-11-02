"""Reproduce source-bound acoustic diagnostics without distributing raw rows."""

import argparse
import math
from pathlib import Path

from h2physics.adapters.hydrogen_acoustic_eos import compare_acoustic_file_with_eos
from h2physics.data.hydrogen_sound_speed import load_hydrogen_acoustic_dataset
from h2physics.thermo import CoolPropProperties


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, default=Path("data/raw/hydrogen-sound-speed/1.0.0"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    source = load_hydrogen_acoustic_dataset(
        args.source_root / "H2_speedofsound_dataset.zip",
        args.source_root / "repository-metadata.json",
    )
    providers = {"normal-h2": CoolPropProperties("Hydrogen"),
                 "para-h2": CoolPropProperties("ParaHydrogen")}
    lines = ["# Hydrogen acoustic EOS replay", "",
             "Source: https://doi.org/10.5281/zenodo.21355851 ; CC BY 4.0.",
             "Attribution: Riley Latcham, Luca Bernardini, Markus Richter and Martin Trusler.",
             f"Archive SHA-256: `{source.archive_sha256}`.",
             f"Metadata SHA-256: `{source.metadata_sha256}`.",
             f"CoolProp version: {providers['normal-h2'].version}; backend HEOS.", "",
             "Each source row is evaluated at its reported T and p with the declared spin basis.",
             "These literature measurements may overlap EOS development. Independence and",
             "experimental uncertainty remain unresolved; this is a replay diagnostic.",
             "Errors below are descriptive and have no imposed accuracy pass threshold.", "",
             "Phase mismatch rows are retained in the all-row residuals and flagged separately.", "",
             "| Member | Compared | Excluded | Phase mismatches | RMS error (m/s) | Max absolute error (%) |",
             "|---|---:|---:|---:|---:|---:|"]
    total = excluded = 0
    notes = []
    for file in source.files:
        spin = file.property_file.metadata.get("_exptl_material_composition", "").strip().casefold()
        if spin not in providers:
            lines.append(f"| `{file.member_path}` | 0 | {len(file.source_rows)} | unavailable | unavailable | unavailable |")
            excluded += len(file.source_rows)
            notes.append(f"- `{file.member_path}`: unsupported/unknown declared spin `{spin}`.")
            continue
        trace = compare_acoustic_file_with_eos(source, file.member_path, providers[spin])
        trace.require_current()
        n = len(trace.points)
        total += n
        excluded += len(trace.exclusions)
        rms = math.sqrt(math.fsum(p.residual_m_s**2 for p in trace.points)/n) if n else None
        maximum = max((abs(p.relative_error_percent) for p in trace.points), default=None)
        rms_text = f"{rms:.9g}" if rms is not None else "unavailable"
        max_text = f"{maximum:.9g}" if maximum is not None else "unavailable"
        mismatches = sum(point.phase_matches is False for point in trace.points)
        lines.append(f"| `{file.member_path}` | {n} | {len(trace.exclusions)} | {mismatches} | {rms_text} | {max_text} |")
        if n:
            worst = max(trace.points, key=lambda point: abs(point.relative_error_percent))
            notes.append(f"- `{file.member_path}`: largest-error row `{worst.row_id}`; "
                         f"source phase `{worst.source_phase}`, native EOS phase `{worst.predicted_phase}`. "
                         "Source phase/metastability is not reconstructed.")
        for reason in sorted({e.reason for e in trace.exclusions}):
            count = sum(e.reason == reason for e in trace.exclusions)
            notes.append(f"- `{file.member_path}`: {count} rows excluded: {reason}.")
    if not total:
        raise ValueError("No source rows were compared; report is not emitted")
    lines += ["", f"Total compared: {total}; total excluded: {excluded}.", "", "Exclusion accounting:", ""]
    lines += notes or ["No rows excluded."]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Compared {total} rows; excluded {excluded}; report {args.output}")


if __name__ == "__main__":
    main()
