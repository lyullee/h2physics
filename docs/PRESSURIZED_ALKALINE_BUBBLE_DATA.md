# Pressurized alkaline electrolysis bubble and electrode data

RODARE version 1 (DOI [10.14278/rodare.4547](https://doi.org/10.14278/rodare.4547)) is a strong public source for relating pressure, electrode structure and bubble/electrochemical behavior in alkaline electrolysis. RODARE records the files under CC BY 4.0. Cite Rox et al. and the version DOI, retain the license, and identify any changes when redistributing derived or source data.

The publisher describes experiments in 1 M KOH at 293 K, with absolute cell pressures of 1, 2, 4 and 6 bar and applied current densities of −25, −50 and −100 mA/cm². The experiment matrix includes four laser-structured nickel electrodes with spatial periods of 30, 40, 60 and 100 μm at about 7 μm depth, plus a reference electrode. The acquired `Summary.csv` index has 60 rows and identifies electrode, pressure and current density for each run. Its exact source and local checksums are recorded in `research/data/pressurized-alkaline-bubble-electrode-potentials.toml`.

## Acquisition boundary

Only the 1,499-byte `Summary.csv` and the exact 7,289-byte RODARE API metadata response were acquired to the ignored `data/raw/rodare-alkaline-bubble-pressure/4547/` path. Both local files have SHA-256 receipts; the CSV also matches the publisher's MD5. The summary is an experimental-condition index; it contains no observed polarization, void fraction, bubble coverage or bubble-size channels.

The main numeric source is `HDF5.zip`, listed by RODARE at 8,586,456,345 bytes with publisher MD5 `bb9736590d904cf8fc8b1bba259b16c8`. It is outside the repository's bounded per-file acquisition limit. The server did not honor a byte-range request, so a single selected HDF5 member cannot be retrieved without transferring the full archive. That archive remains unacquired and is not treated as locally verified. `Videos.zip` (262,988,757 bytes) contains illustrative videos and was omitted because the immediate ingestion target is numeric data.

RODARE's record says HDF5 files contain electrochemical/galvanostatic data and processed detected front-view bubble results, with unprocessed front-view images only in `LS_P_01.hdf5`; the other raw images can be requested from the authors. Since the archive is not available locally, internal group names, dataset shapes, units, sensor/channel semantics and missing-data rules remain unverified. The source cannot yet be used as a qualified polarization or bubble-coverage dataset.

## Qualification contract

Before using the measurements, acquire a bounded, version-pinned HDF5 subset or receive individual HDF5 files from the authors with an explicit link to the RODARE CC BY 4.0 record. Preserve source MD5 values and compute local SHA-256 values. Inspect each HDF5 group and dataset attribute; map raw voltage/current/reference electrode signals, bubble count/size/coverage, image orientation and timebase, pressure, KOH concentration, temperature, electrode type and measurement stage. Keep measured quantities separate from derived bubble metrics. Do not infer unreported electrolyte flow, gap geometry, electrode area, reference scale, sampling cadence or uncertainty. Do not compare against cell-scale stack polarization until electrode reference and apparatus boundaries are demonstrated to match.

The new [condition-index reader guide](RODARE_ALKALINE_BUBBLE_INDEX.md) documents a source-integrity case for the acquired summary. That contract checks only publisher-file identity and the 60-row experiment grid; it is not a validation input. A separate measurement-file ingestion case remains deferred until the exact HDF5 files and schemas are available in a complete immutable source pin.

## Related public-source search and current gap

The existing Mendeley record [10.17632/r6np4f7gmf.2](https://doi.org/10.17632/r6np4f7gmf.2) is tracked separately. Its anonymous public root listing contains a README, videos and images, but does not expose machine-readable measurement tables at that level; no values are transcribed from its figures or image assets. It is not a second copy of this RODARE dataset.

Two other leads were excluded from acquisition. The TU Delft [gas-fraction thesis record](https://repository.tudelft.nl/record/uuid:e27bb970-2bc4-473a-8537-ef4d5a6be109) is embargoed until 2028-08-26 and did not establish current open redistribution rights. The Mendeley [Raney-nickel dataset](https://doi.org/10.17632/tthzg5wf2f.1) advertises CC BY-SA 4.0, but its accessible description lacks sufficient operating-condition detail and its public file inventory could not be verified. The Mendeley [high-current catalyst-coated diaphragm record](https://doi.org/10.17632/wxb94xrctt.1) advertises CC BY 4.0, but a verifiable downloadable file list and channel schema were unavailable. These sources remain leads, not approved input data.

The present evidence therefore leaves a precise source gap: a rights-qualified, machine-readable numeric dataset whose bubble coverage or electrolyte gas fraction and/or polarization channels can be inspected together with operating conditions, units, calibration and timebase. RODARE v1 is promising but cannot close that gap until its HDF5 measurements are made available as a bounded, checksum-verifiable subset or individual files. No chart digitization, plot transcription, or image-derived numeric values are part of this research.

## Source records

- [RODARE record and file license](https://rodare.hzdr.de/record/4547)
- [Exact record API response](https://rodare.hzdr.de/api/records/4547)
- [RODARE collection data publication](https://www.hzdr.de/publications/Publ-43192)
- [Publisher journal record](https://doi.org/10.1016/j.electacta.2026.150090)
