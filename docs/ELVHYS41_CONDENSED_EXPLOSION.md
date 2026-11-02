# ELVHYS 4.1 vent gas composition data

## Source and acquired scope

The official [DataverseNO record](https://doi.org/10.18710/YGHHTR), version 1.1, declares CC0 1.0. This project acquired only three public files: the source README, experiment metadata CSV, and Test-1 concentration CSV. Bytes are kept under gitignored `data/raw/elvhys-condensed-explosion/1/`, not included in package distributions or source releases.

| File | Bytes | Publisher MD5 | Local SHA-256 |
|---|---:|---|---|
| `00_ELVHYSWP4_1 README.txt` | 7,769 | `a8649100dab484f0ce9e89a14cd75142` | `afaaf3f55823f6d9c6ee9cb71df7e50a2d7d2755c85e03195da892f9ca0b05d1` |
| `ELE401HSEMETA.csv` | 2,291 | `637bbc863c18d3110a90567e9afe3824` | `625ecee98de0ef3ca5a6b574b67f7f09d5efe9331da9a16f3bc7b058574de798` |
| `ELE401HSE001CONC20251021.csv` | 1,025,015 | `65c081d72b84e6fe47617c6c603b16f3` | `f2239638dc86a1d482a87f1e886951a9f5cdadbdc4594109f925c654ce9da9a6` |

Attribution: Rattigan, W.; Welch, J.; Vizma, J. (2025), *ELVHYS 4.1 Oxygen enrichment and condensed phase explosions*, DataverseNO, DOI 10.18710/YGHHTR. The file-specific persistent IDs and source receipts are in `research/data/elvhys41-condensed-explosion.toml`.

## Reader and existing model boundary

`h2physics.data.load_elvhys41_concentration_csv(raw_root)` requires the three pinned files and verifies their publisher MD5s, sizes, local SHA-256 values, and the selected test concentration CSV header. It preserves raw `Time Interval` seconds and the H2/O2 sensor values in vol%, and requires strictly increasing source times before model linking. It does not alter negative near-zero readings.

The reader rejects duplicate and non-increasing timestamps at ingestion, before any source-to-model linkage is considered. This prevents ambiguous same-time row selection and preserves the exact source clock ordering.

`h2physics.adapters.compare_elvhys41_vent_composition` can compare selected, physically admissible concentration points with `OxygenRoomResult` snapshots from the existing `CanteraOxygenRoom` model. It converts vol% to mole fraction only under explicit caller evidence, maps each source time using a declared clock offset, and requires one exact model snapshot per selected time. It rejects values below zero, above 100 vol%, or with H2 plus O2 above 100%; it never clips or interpolates. Callers must separately justify the vent-to-homogeneous-region mapping and the model's volume/gas-state boundary. The registered Hangang case reads actual data and checks provenance/schema; it does not execute the physical model comparison.

## Evidence limits

The source README describes a nominal 100 L vessel, a cryogenic liquid-hydrogen campaign and 1 Hz logging. It documents sensor delay normalization for the two concentration channels, along with calibration procedures and uncertainties: H2 sensor ±2% of its 0–100 vol% full scale and O2 sensor ±1% of its 0–120 vol% full scale. The experiment involves a vent sample; equating it to a homogeneous vessel/room state is an external modeling assumption and must be evidenced by the caller.

The outlet flow rate is described as a calculated value using differential pressure across an orifice, and the README says that channel is awaiting calibration. That input has not been acquired here. This bridge does not reconstruct the cryogenic H2 evaporation or vent-rate histories, oxygen enrichment mechanism, ignition, flame, blast pressure, or condensed-phase explosion physics. Results are pointwise gas-composition diagnostics only and do not establish independent validation.
