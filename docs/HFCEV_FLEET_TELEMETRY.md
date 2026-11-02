# HFCEV fleet telemetry source bridge

## Source and rights

The first-party [Zenodo v1.0 record](https://zenodo.org/records/23477229) states that the data are licensed CC BY 4.0 and that its separately distributed processing code is Apache-2.0. The dataset describes anonymized heavy-duty fuel-cell truck telemetry and lists 20 files totaling about 983.5 MB. This project selectively acquired the README, channel dictionary, and one operation sample for vehicle V001 dated 2025-12-23. The larger operation/GPS archives and all location files were left untouched. The three selected files are in gitignored `data/raw/hfcev-fleet/1/` and are not part of package or source release artifacts.

| File | Bytes | Publisher MD5 | Local SHA-256 |
|---|---:|---|---|
| `README.md` | 3,599 | `c4af7a5fb1f5888dd20e20a1056eb913` | `e49fb4dda0b5fe10e505c92f4c4a6b498b34b6470c321e0ac90abac6039c7787` |
| `dictionary.csv` | 15,472 | `0a7260b0128fcb6c61d80cfd756bc610` | `e3b7c99203d2d2988078e6fab0512c970df699cc437521108fafb44df44e0e75` |
| `field_bits.csv` | 914 | `a42517be9762f2177c8512d1bca9a9c6` | `372b4b3285e12f51afe7d6dfebfa92659ae31eceea1f2020192ff52a4e2ee337` |
| `sample_operation_V001_2025-12-23.csv` | 2,363,398 | `dea3bc817b59232931e4af6f40b7efaf` | `709cb310102649dce0b03553f532eace131c1a455f8dadf66be7d62bcd6fdec2` |

Attribution: Sun, Y.; Hang, Z.; Sun, P.; Xu, S.; Sun, Y.; Xu, Y.; Yang, X. (2026), *Factory-test and in-vehicle telemetry from a fleet of 100 hydrogen fuel-cell electric heavy-duty trucks*, v1.0, Zenodo, DOI 10.5281/zenodo.23477229. The acquired subset retains the source names and hashes for traceability.

## Reader and bounded model link

`h2physics.data.read_hfcev_operation_sample(raw_root)` admits only the named sample and verifies its pinned size, publisher MD5, and local SHA-256. It also rechecks the three small supporting files and their hashes, including the counter/missing-bit map. The typed row preserves receipt timestamp, optional device time and its status, vehicle/TBOX unit, reporting segment, counter correction status, missing and backward-counter masks, stack current and voltage, pressure and temperature observations, plus the publisher-derived `h2_increment` and `h2_attributed` fields.

`h2physics.adapters.select_hfcev_hydrogen_window` selects a positive-duration window only when both edges uniquely match actual source rows, all rows belong to one vehicle/unit/segment, and every included H2 interval is marked attributed with a nonnegative increment. It requires the preceding valid restored-counter row to be the immediately previous row and inside the window, preventing overlapping increments or mass accrued before the selected start; it records exact `(previous_counter_row, increment_row)` pairs. The H2 missing bit (26) and backward-counter bit (1) are enforced from the source bit map. `correction_status` applies to pressure/leak-sensor corrections, so it is preserved but does not gate hydrogen-counter increments. The API sums released kg increments; it does not reconstruct flow from electrical channels. `compare_hfcev_hydrogen_consumption` can compare that observed mass with the total H2 consumed by a current `FiniteFuelCell` result, but requires a typed `HFCEVTimeAlignment` that maps both source receipt-time endpoints to both model-second endpoints and an external evidence ID. The code checks endpoint and elapsed-duration equality; the external evidence remains responsible for interpreting receipt-time alignment. The deferred Hangang case reads the exact selected payload and exercises the source-window contract; no local tests or calculations were run.

## Evidence limits

The primary stream is server receipt time rounded or truncated per source notes. Device payload time is populated only when the provider's clock checks passed; gaps can cause delayed rows to arrive in bursts. Consequently, receipt time is not assumed to be physical event time. The selected sample is a factory/service telemetry slice; installation date and in-vehicle service onset for V001 are not supplied. `h2_increment` is a publisher-derived, restored counter difference with 0.01 kg source resolution; only increments explicitly marked `h2_attributed` are eligible. Zero `HyBottleP` values are missing pressure readings under the source README caveat.

No active cell area or per-cell operating map is established for this vehicle sample. Current, voltage, coolant, ambient and pressure channels are preserved as observations and are not mapped to a stack state, fuel-cell forcing profile, inlet composition, or model parameter. The comparison is an aggregate measured-versus-model diagnostic when caller-supplied time/boundary evidence is available; it does not establish model validation or fleet-wide representativeness.
