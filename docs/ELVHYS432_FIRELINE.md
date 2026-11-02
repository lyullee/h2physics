# ELVHYS 4.3.2 transfer-line temperature observations

## Source and rights

The source is DataverseNO DOI [10.18710/HDZLJ1](https://doi.org/10.18710/HDZLJ1), version 1.0, published 2026-10-21. The record declares CC0 1.0 and lists 14 public files with a combined display size of 4.2 GB. This project acquired only the 13,429-byte README and the 469,188-byte Test-1 Lake Shore diode CSV; both are kept under ignored `data/raw/elvhys-fireline/1/`. Their persistent identifiers, publisher MD5s and local SHA-256 values are in `research/data/elvhys432-fireline.toml`. The other runs, pressure and thermocouple time histories, and three video files were not acquired.

## Observations

The README describes a 2 m transfer section in the A2 vessel, with rigid pipe configurations and a vacuum-insulated hose in the campaign. It describes precooling with nitrogen or liquid hydrogen, liquid introduction and isolation, then burner exposure. The record-level description gives a vessel maximum of 5 barg and a burner mixture; those are test context, not per-row measurements in the selected file.

The selected `ELE432KIT001TEMPL20260819.csv` contains source time in minutes, `SD1` pipe-surface temperature in kelvin, and `SD2` outlet process temperature in kelvin. The README identifies Lake Shore 224 acquisition at a configured 0.5 s interval, calls SD1 a pipe-surface temperature and SD2 an outlet temperature, and lists the DT-670SD range/specification. It also says the silicon diodes were not calibrated. The reader preserves source minutes and both raw Kelvin channels; it does not resample, smooth or align them to a model clock.

## API boundary

`h2physics.data.load_elvhys432_temperature_csv(raw_root)` checks both source byte receipts, validates the exact three-column header, and returns an immutable source-bound sample. Its `require_current()` rehashes both files and checks the issued rows.

`h2physics.adapters.compare_elvhys432_surface_temperature(...)` offers a pointwise diagnostic from SD1 to one selected inner or outer face of an existing native `RadialHeatResult`. Every compared time must match exactly after the caller-declared seconds offset; there is no interpolation or extrapolation. Callers must identify evidence for SD1 sensor location, equivalence of the tested pipe section and radial model domain, and clock alignment. The adapter compares temperature only; it does not infer flux, material properties, or boundary conditions. SD2 remains available in the source reader and is not treated as a wall face.

The deferred Hangang case `elvhys432-pipe-surface-temperature-source-ingest` checks acquisition, rights and schema only. It does not run a thermal model or compare model output. Source-specific calibration, spatial sensor coordinates, pipe/domain mapping and a common clock remain open. This dataset does not validate cryogenic transfer-line failure or fire response.
