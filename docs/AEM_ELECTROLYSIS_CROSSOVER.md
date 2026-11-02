# AEM electrolysis performance and hydrogen crossover data

## Source and rights

The source is the open Zenodo record [10.5281/zenodo.20068087](https://zenodo.org/records/20068087), version v1, published 2026-07-26. Its record title is “Data for the Publication: Impact of Electrolyte Feed and Catalyst-Coated Substrate Properties on Cell Performance and Hydrogen Crossover in AEM Water Electrolysis.” The record metadata explicitly declares CC BY 4.0. Attribute the creators listed in the record: Jan Witte, Patrick Trinke, Boris Bensmann, Maik Becker, Vinzent Olszok, Alfred P. Weber, Richard Hanke-Rauschenbach, and Thomas Turek. Related publication DOI: [10.1149/1945-7111/ae87d5](https://doi.org/10.1149/1945-7111/ae87d5).

The licensed payload selected here is the single workbook `SI2_raw_data.xlsx`. The authoritative Zenodo API endpoint is <https://zenodo.org/api/records/20068087>. Its metadata snapshot SHA-256 is `bd56cdc61eab1904d7436e8708e3dd332fd743a7161a6c3cd0b98a62e6c254ea`. The file is 1,780,457 bytes; Zenodo's MD5 `9d5a8655039f014431d3b9bc81e0d3f7` and acquired local SHA-256 `f9729dfc0b068962843ceb089bedbc6f6eb1ea8f52e214cd7eba6550d6c334ad` were verified by the bounded acquisition utility. The byte payload and API snapshot are kept under ignored `data/raw/aem-water-electrolysis-crossover/20068087/`; they are not committed or packaged.

The record describes data on electrolyte feed, catalyst-coated substrate, cell polarization, and hydrogen crossover. Workbook inventory, inspected without fitting or interpreting measurements:

| Worksheet | Rows × columns |
|---|---:|
| `Pol_curve_wet-dry` | 46 × 56 |
| `Pol_curve_individual_runs` | 7,329 × 45 |
| `Pol_curve_individual_runs_BoT` | 139 × 41 |
| `Crossover_wet-dry` | 77 × 37 |
| `Crossover_individual_runs` | 72,069 × 19 |
| `H2_and_H2O_transport` | 10 × 6 |

## Modeling fit and limits

This is a useful source for data-backed AEM polarization and hydrogen crossover observation work. The existing PEM crossover set covers a different membrane chemistry, and the existing alkaline short-stack set covers a different cell technology; neither replaces AEM-specific crossover observations. No model fitting, parameter extraction, unit conversion, or physical validation was performed in this acquisition lane. Worksheet labels and dimensions alone do not establish a calibrated sensor basis or a validated transport law.

Do not use these measurements to qualify PEM or alkaline models. A future reader must preserve the workbook's source labels and units, bind any extracted rows to their sheet/cell lineage and exact raw-file digest, and keep experiment grouping explicit. Candidate uses include AEM polarization comparison and hydrogen-crossover sensitivity studies after worksheet units, condition definitions, and measurement semantics are reviewed. They do not by themselves identify a complete membrane transport law or prove full-stack/system behavior.

This work used the repository's own source registry and bounded data-acquisition utility. No source code or prose from the associated publication was copied into the implementation.
