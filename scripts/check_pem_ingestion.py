"""Replay licensed PEM members with source hashes and explicit protocol selection."""

import argparse
import hashlib
import zipfile
from pathlib import Path

import numpy as np

from h2physics.core import Origin
from h2physics.data.pem import VARIABLES, PemExperiment, PemLoadReport, load_pem_csv, pem_spectra
from h2physics.observations import ObservationTable

ROOT = Path(__file__).resolve().parents[1]
SOURCE = "10.5281/zenodo.19361280"
ARCHIVE_SHA = "ef15233374ece3af33a3f876a80d8a7c38c965dff122b884c6ebd39f391952e4"
MEMBERS = ("Reference_dataset.csv", "PtNano_dataset.csv", "PtBlack_dataset.csv", "PtC_dataset.csv")


def profile_sha():
    digest = hashlib.sha256()
    for name in ("src/h2physics/data/pem.py", "src/h2physics/impedance.py"):
        digest.update((ROOT/name).read_bytes())
    return digest.hexdigest()


def read_cache(member):
    path = ROOT/"artifacts/pem_eis"/(Path(member).stem+".npz")
    with np.load(path, allow_pickle=False) as cached:
        if str(cached["profile_sha"]) != profile_sha() or str(cached["archive_sha"]) != ARCHIVE_SHA:
            raise ValueError("PEM cache does not match the current profile and recorded source")
        table = ObservationTable(cached["values"], VARIABLES, cached["valid"], tuple(cached["rows"].tolist()),
            tuple(cached["groups"].tolist()), tuple(Origin(value) for value in cached["origins"].tolist()),
            SOURCE, tuple(tuple(pair) for pair in cached["context"].tolist()))
        if table.content_sha256 != str(cached["table_sha"]):
            raise ValueError("PEM cached observation content changed")
        stats = cached["report"].astype(int).tolist()
        report = PemLoadReport(stats[0], stats[1], str(cached["member_sha"]), stats[2], stats[3])
        return PemExperiment(table, tuple(cached["labels"].tolist()), 4e-4,
                             str(cached["clock_id"]), 1, report)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--use-cache", action="store_true", help="Reuse matching full-member audit caches")
    args = parser.parse_args()
    archive_path = next((ROOT/"data/raw/pem-crossover").rglob("*.zip"))
    digest = hashlib.sha256()
    with archive_path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024*1024), b""):
            digest.update(block)
    assert digest.hexdigest() == ARCHIVE_SHA
    destination = ROOT/"artifacts/pem_eis"
    destination.mkdir(exist_ok=True)
    text = ["# Measured PEM electrolysis protocol and impedance ingestion", "",
        "Source: Brundiers (2026), [dataset v1](https://doi.org/10.5281/zenodo.19361280), "
        "CC BY 4.0. Associated study: [Brundiers et al.](https://doi.org/10.1039/d6ey00106h).",
        f"Recorded archive SHA-256: `{ARCHIVE_SHA}`.", "",
        "The first two POL_GEIS protocol counters are selected in each of four actual cells. "
        "Every CSV member is nevertheless fully consumed and hashed. These source groups "
        "contain DC holds and measured EIS sweeps; protocol counters and AC samples are not "
        "independent cell replicates. Selected arrays remain in ignored local caches.", "",
        "Conversions are explicit: mA to A, degrees Celsius to K, bar absolute to Pa, "
        "micro-S/cm to S/m, and volume percent to fraction. Original source-row identities "
        "and file-specific reported elapsed clocks are retained; no sorting or clock alignment "
        "is inferred. The phase is used as arg(Z), consistent with the source's complex "
        "reconstruction example; plotting -Im(Z) does not change that convention.", "",
        "The actual CSVs encode some DC EIS placeholders as 0 Hz/0 ohm, despite documentation "
        "describing missing values. Positive-frequency blocks are identified explicitly; "
        "zero-frequency entries are retained but excluded from spectra. A frequency reset "
        "ratio of two separates adjacent ascending sweeps. A preceding 10-row non-EIS tail, "
        "with explicit maximum 120 s gap, supplies reconstructed DC context. Longer gaps leave DC context unknown. Instantaneous AC current "
        "is not rounded to a setpoint. Cell block temperature is not reaction temperature. "
        "Corrected GC is only admitted in the documented H2_char/CstC phases; no GC values "
        "are interpolated or converted to membrane flux.", "",
        "| Cell | Full CSV rows | Selected rows | Valid positive-frequency rows | Spectra | "
        "Spectra with DC context | Nonpositive selected frequency rows | Malformed selected numeric cells | CSV SHA-256 |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---|"]
    with zipfile.ZipFile(archive_path) as archive:
        for member in MEMBERS:
            cell = member.removesuffix("_dataset.csv")
            if args.use_cache and (destination/(Path(member).stem+".npz")).exists():
                loaded = read_cache(member)
                print("reusing matching complete-member audit", member, flush=True)
            else:
                print("reading complete member", member, flush=True)
                with archive.open(member) as stream:
                    loaded = load_pem_csv(stream, experiment_id="pem/"+cell, source_id=SOURCE,
                        measurement_types=("POL_GEIS",), counters=(1, 2), active_area_m2=4e-4, phase_sign=1)
            spectra = pem_spectra(loaded, maximum_dc_gap_s=120.)
            report, table = loaded.report, loaded.observations
            assert len(spectra) > 0
            assert all(len(item.spectrum.frequency_hz) == 23 and np.all(item.spectrum.valid)
                       for item in spectra)
            contexts = sum(item.dc_current_a is not None for item in spectra)
            np.savez(destination/(Path(member).stem+".npz"), values=table.values, valid=table.valid,
                rows=np.array(table.row_ids), groups=np.array(table.experiment_ids),
                origins=np.array([str(value) for value in table.origins]), context=np.array(table.context),
                labels=np.array(loaded.measurement_types), clock_id=np.array(loaded.clock_id),
                report=np.array([report.rows_seen, report.rows_retained, report.malformed_numeric_cells,
                                 report.nonpositive_frequency_rows]), member_sha=np.array(report.member_sha256),
                archive_sha=np.array(ARCHIVE_SHA), profile_sha=np.array(profile_sha()),
                table_sha=np.array(table.content_sha256))
            assert read_cache(member).observations.content_sha256 == table.content_sha256
            positive = int(np.count_nonzero(table.valid[:, 4]))
            text.append(f"| {cell} | {report.rows_seen} | {report.rows_retained} | {positive} | "
                f"{len(spectra)} | {contexts} | {report.nonpositive_frequency_rows} | "
                f"{report.malformed_numeric_cells} | `{report.member_sha256}` |")
            print(cell, report.rows_seen, "rows;", len(spectra), "spectra; DC currents A",
                  [None if item.dc_current_a is None else round(item.dc_current_a, 5) for item in spectra[:18]], flush=True)
    text += ["", "The inspected protocols contain 18 sweeps per counter; the nominal protocol "
        "describes 17 current levels ending at 12 A. The last counter-1 sweep is approximately "
        "12 A again in Reference/PtC and 14 A in PtNano/PtBlack where DC context is admissible. "
        "Actual sweeps are kept, without forcing the nominal level count. The profile does not impute "
        "missing DC context across a longer acquisition gap.", "",
        "No associated notebook was executed and no source plot or prose is redistributed. "
        "No equivalent-circuit fit, thermochemical reference, material property, crossover "
        "mechanism or independent model validation follows from this ingestion alone.", "",
        "Host code SHA-256:", ""]
    for relative in ("src/h2physics/data/pem.py", "src/h2physics/impedance.py", "scripts/check_pem_ingestion.py"):
        text.append(f"- `{relative}`: `{hashlib.sha256((ROOT/relative).read_bytes()).hexdigest()}`")
    (ROOT/"research/pem_ingestion.md").write_text("\n".join(text)+"\n", encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
