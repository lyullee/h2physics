# Cal State LA hydrogen station operational data access review

**Review date:** 2026-10-31  
**Disposition:** Do not acquire, redistribute, or claim independent validation from the underlying operational records until raw files and their reuse terms are directly identified.

## Finding

The papers describe valuable measured operation at the California State University Los Angeles Hydrogen Research and Fueling Facility. However, the inspected official University of Calabria IRIS records for both papers state that no files are associated with the repository item. They expose bibliographic records and abstracts, not downloadable station-data assets. No raw-data asset identifier, direct file URL, checksum, or raw-data license was discoverable in those records.

The 2023 DOI is an open-access article under CC BY 4.0. That is the article's stated license; it does not establish reuse rights for the underlying operational data that are described but not deposited as files. The 2021 paper's publisher record states © 2021 Elsevier Ltd., all rights reserved. Its university repository record likewise has no file and states that repository documents are copyright-protected unless otherwise indicated. Neither article record establishes an open license for its raw operational dataset.

The second DOI supplied during discovery, `10.1016/j.jclepro.2021.129906`, is not the Cal State LA fueling paper. The verified HRS back-to-back paper is `10.1016/j.jclepro.2021.129737`.

## Publisher and repository records

| Record | What the source confirms | Raw downloadable data / terms |
|---|---|---|
| [2021 publisher record](https://www.sciencedirect.com/science/article/pii/S0959652621039135) · [University of Calabria IRIS record](https://iris.unical.it/handle/20.500.11770/326609) | Article describes one year of fueling activity and back-to-back scenarios at Cal State LA; publisher citation gives DOI `10.1016/j.jclepro.2021.129737`. | IRIS says no files are associated. Publisher copyright is all rights reserved. No raw-data license found. |
| [2024 publisher record](https://www.sciencedirect.com/science/article/pii/S0360319923018190) · [University of Calabria IRIS record](https://iris.unical.it/handle/20.500.11770/348868) | Article describes 2016–2020 operation, over 4,500 refueling events, dispensed hydrogen, electrolyzer, and compressor energy performance. | IRIS says no files are associated. Article is CC BY 4.0, but no separate raw-data files or raw-data license were found. |

The scoped machine-readable discovery record is [`research/data/cal-state-la-hrs-operational.toml`](../research/data/cal-state-la-hrs-operational.toml). It deliberately records zero raw assets and zero checksums.

## Reuse gate

Keep this source out of acquired/open-data collections until one of the following is obtained from the data owner or an official repository:

1. A stable record with directly downloadable raw or processed operational files, file-level identifiers and hashes, plus a clear reuse license; or
2. Written permission that identifies the specific files, permitted transformations, attribution, redistribution and any privacy or facility-security restrictions.

The article's figures and tables are not substitutes for raw-data files. Do not reconstruct or transcribe the paper's plots/tables into a project dataset under this entry.

## Conditional ingestion and validation outline

If reusable source files are later provided, first preserve each original byte stream outside Git, its source-specific filename, size, SHA-256, license/permission record, and retrieval event. Then build a read-only schema audit before any model adapter:

1. Enumerate files, sheets, columns, units, timestamps, missingness, duplicate keys, and row counts without normalizing or imputing values.
2. Record the station subsystem, meter/sensor identity, calibration or maintenance metadata, time zone, sampling period, and whether each quantity is measured, calculated, or reported as a quarterly aggregate.
3. Separate fueling-event records from station energy totals and distinguish event timing, delivered mass, pressure/temperature history, dispenser/chiller electrical use, electrolyzer output, and compressor operation only where the source fields explicitly support those meanings.
4. Preserve raw rows and create independently versioned typed projections with explicit units, clocks, pressure bases, event identifiers, and unresolved-field markers.
5. Validate ingestion using row counts, file hashes, timestamp monotonicity/duplicates, domain and unit checks, mass/energy aggregation reconciliation against source-provided summaries, and held-out intervals. Do not infer unavailable station controls, vessel state, or sensor calibration.
6. Only after semantic review, define model-specific cases. Candidate scopes include event-frequency/back-to-back scheduling and station energy accounting; they must not be presented as validated pressure-wave, compressor-map, fueling-protocol, or vehicle-tank models without the corresponding raw channels and independent evidence.

This outline is a future intake plan, not evidence that source data are available or that any model has been validated.
