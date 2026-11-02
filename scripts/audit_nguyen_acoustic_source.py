"""Cross-check an admitted acoustic member against the licensed primary table.

Requires pdfplumber in the research environment. Emits aggregate diagnostics;
neither the source document nor its extracted table belongs in public artifacts.
"""

import argparse
import hashlib
import json
import math
import sys
from importlib.metadata import version
from pathlib import Path

from h2physics.adapters.hydrogen_acoustic_eos import compare_acoustic_file_with_eos
from h2physics.data.hydrogen_sound_speed import load_hydrogen_acoustic_dataset
from h2physics.thermo import CoolPropProperties

PDF_SHA256 = "718f08874e2881beeebd5d5067b8a847a131ed2bd4082ffa7a7dc6fb049bef90"
MEMBER = "H2_speedofsound_dataset/H2_speedofsound_Nguyen_2024_nH2.txt"


def primary_rows(pdf_path):
    import pdfplumber

    if hashlib.sha256(pdf_path.read_bytes()).hexdigest() != PDF_SHA256:
        raise ValueError("Primary manuscript differs from the reviewed source bytes")
    with pdfplumber.open(pdf_path) as document:
        text = document.pages[2].extract_text()
    if "Table4" not in text.replace(" ", ""):
        raise ValueError("Expected primary Table 4 on page 3")
    rows = []
    for line in text.splitlines():
        fields = line.split()
        if fields and fields[0] in {"CRb", "DPPEc"}:
            fields = fields[1:]
        try:
            values = [float(token) for token in fields]
        except ValueError:
            continue
        if len(values) not in {5, 10}:
            continue
        for index in range(0, len(values), 5):
            row = tuple(values[index:index+5])
            if 270 < row[0] < 325 and 0 < row[1] < 101 and 1200 < row[2] < 2300:
                rows.append(row)
    if len(rows) != 57 or len({row[:3] for row in rows}) != 57:
        raise ValueError("Expected 57 unique T/p/sound-speed observations in the primary table")
    if any(not 0 < row[3] < 2 or not 0 < row[4] < 0.1 for row in rows):
        raise ValueError("Unexpected expanded-uncertainty columns")
    return {row[:3]: row[3] for row in rows}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pdf", type=Path, required=True)
    parser.add_argument("--source-root", type=Path, default=Path("data/raw/hydrogen-sound-speed/1.0.0"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    primary = primary_rows(args.pdf)
    source = load_hydrogen_acoustic_dataset(args.source_root / "H2_speedofsound_dataset.zip",
                                           args.source_root / "repository-metadata.json")
    file = source.file(MEMBER)
    uncertainties = {}
    keys = set()
    offset = 0
    for loop in file.property_file.loops:
        for t, p, w in zip(loop.column("temperature"), loop.column("pressure"), loop.column("SoS"), strict=True):
            key = (float(t), float(p), float(w))
            if key not in primary or key in keys:
                raise ValueError("Compiled source row differs from the primary table or is duplicated")
            keys.add(key)
            uncertainties[file.source_rows[offset]] = primary[key]
            offset += 1
    if keys != set(primary) or offset != 57:
        raise ValueError("Primary and compiled observation sets do not match exactly")
    provider = CoolPropProperties("Hydrogen")
    trace = compare_acoustic_file_with_eos(source, MEMBER, provider).require_current()
    if len(trace.points) != 57 or trace.exclusions:
        raise ValueError("All 57 verified observations must be retained in this comparison")
    ratios = [abs(point.residual_m_s)/uncertainties[point.row_id] for point in trace.points]
    fluid = json.loads(provider._cp.get_fluid_param_string("Hydrogen", "JSON"))[0]
    fingerprint = hashlib.sha256(json.dumps(fluid["EOS"], sort_keys=True).encode()).hexdigest()
    rms = math.sqrt(math.fsum(point.residual_m_s**2 for point in trace.points)/57)
    report = ["# Primary-table audit of recent hydrogen acoustics", "",
              "Primary experiment: https://doi.org/10.1016/j.jct.2024.107341 ; CC BY 4.0.",
              "Authors: T.-T.-G. Nguyen, C. Wedler, S. Pohl, D. Penn, R. Span, J.P.M. Trusler, M. Thol.",
              "Compilation: https://doi.org/10.5281/zenodo.21355851 ; CC BY 4.0.",
              "Compilation authors: Riley Latcham, Luca Bernardini, Markus Richter, Martin Trusler.",
              f"Primary document SHA-256: `{PDF_SHA256}`.",
              f"Compilation archive SHA-256: `{source.archive_sha256}`.",
              f"Compilation metadata SHA-256: `{source.metadata_sha256}`.",
              f"Compiled member SHA-256: `{file.member_sha256}`.",
              f"Extractor pdfplumber {version('pdfplumber')}; Python {sys.version.split()[0]}.",
              f"Native EOS metadata/coefficients SHA-256: `{fingerprint}`.",
              f"CoolProp {provider.version}; native EOS citation: `{fluid['EOS'][0]['BibTeX_EOS']}`.", "",
              "All 57 temperature, pressure and measured sound-speed triplets match the primary table exactly.",
              "The primary table supplies expanded speed uncertainties with coverage factor k=2.",
              "The table layout and unit/coverage headings were visually inspected during qualification.", "",
              f"- RMS residual: {rms:.12g} m/s.",
              f"- Rows with absolute residual within the reported expanded uncertainty: {sum(x <= 1 for x in ratios)}/57.",
              f"- Maximum absolute residual / reported expanded uncertainty: {max(ratios):.12g}.",
              f"- Expanded uncertainty range: {min(primary.values())} to {max(primary.values())} m/s.", "",
              "These counts compare model discrepancies with experimental uncertainty only; they are not",
              "a statistical coverage test and do not include model-form uncertainty or measurement correlations.",
              "The experiment postdates the native EOS citation, supporting an external comparison;",
              "native coefficient revision history still needs review before independence qualification.",
              "No model fit, source correction or universal accuracy acceptance threshold is applied."]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("\n".join(report)+"\n", encoding="utf-8")
    print(f"primary rows matched=57; within expanded uncertainty={sum(x <= 1 for x in ratios)}/57; max ratio={max(ratios)}")


if __name__ == "__main__":
    main()
