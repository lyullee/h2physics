# GrInHy2.0 transient hydrogen-flow data

## Source and rights

- Creator: Konstantin Schwarze, Sunfire GmbH
- Dataset: [Transient recording of hydrogen flow within GrInHy2.0 electrolyser plant](https://doi.org/10.5281/zenodo.7612826)
- License declared by Zenodo's record API: [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)
- Source workbook: `Transient data (H2-flow) - Kopie.xlsx`, 27,069 bytes
- Source checksum from record: MD5 `6e1ccbce1f7b6ed4a7cee0d8acaa9464`
- Downloaded workbook SHA-256: `038b1ee17ce4bb7e332bdc5734978fd3f72305423da39ad6d1e1e68b9fb4e68c`
- Normalized CSV SHA-256: `04cf4c65676bac11024cc35aaa83ce55c94165044108a17a89abc065a4f28612`
- Git attributes preserve the normalized CSV's exact stored bytes so this checksum remains stable across Windows and Linux checkouts.

The workbook is held in the ignored `data/raw/grinhy2-electrolysis-transient/`
directory and is not included in the repository. The CSV is an attributed CC BY
4.0 adaptation. Its only transformation is adding elapsed seconds from the first
Excel time serial; all four recorded flow columns and all 447 source rows are
preserved. The creator and source DOI remain attached to this dataset record.

The tracked CSV schema is checked independently from the reader's normalized
API field names. Its exact header order is
`elapsed_time_s_from_start,source_time_excel_serial,hydrogen_to_vent_Nm3_h,hydrogen_to_HPU_Nm3_h,hydrogen_to_grid_Nm3_h,hydrogen_demand_Nm3_h`.
The loader maps the first two labels to `elapsed_s` and
`source_excel_time_serial`, respectively, and maps the four flow columns by
their recorded channel identity. HPU capitalization in the file is preserved
by the schema check; values are not recalibrated or converted.

## Workbook structure reviewed

Worksheet `Table1` has 448 rows including the header and five complete columns:

1. `Time`
2. `Hydrogen to vent [Nm³/h]`
3. `Hydrogen to HPU [Nm³/h]`
4. `Hydrogen to grid [Nm³/h]`
5. `Hydrogen demand [Nm³/h]`

The 447 observations span the naive Excel timestamps 2022-05-03 08:31:30 through
12:39:30. All but one adjacent interval are 15 seconds; the interval from
08:58:45 to 11:15:30 is 8,205 seconds. That gap is retained as-is and no values
are interpolated or integrated across it by this export. The source supplies no
timezone or normalized-volume reference temperature/pressure. Vent and grid
channels contain negative values, which are preserved rather than clipped.

## Use boundary

Use this file as an observed plant-boundary flow schedule for time-series
handling, demand comparison and operational-window studies. Do not convert
Nm³/h to molar or mass flow until the reference state is identified. The
workbook contains no cell current or electrical power series, so it cannot
independently validate electrochemical performance, stack efficiency, or the
plant's electrical energy balance.

## Producer-model linkage audit

The acquired schema contains only time plus vent, HPU, grid and demand volume
flows. It contains no stack current/current density, electrical input, cell
temperature or stack temperature. The workbook labels flows as `Nm³/h` but does
not specify the normal-volume reference temperature and pressure; those values
therefore cannot be converted to molar or mass production rates without adding
an unsupported assumption. The HPU channel's name alone does not establish that
it is stack production, its measurement plane, or its alignment with stack state.

Consequently this source cannot identify Faradaic efficiency, polarization,
thermal parameters, or a forcing profile for `HydrogenStack` or the PV/electrolysis
adapter. No fit, calibration, resampling across the long gap, or extrapolation is
made. The hash-pinned Hangang case
`grinhy2-electrolyzer-coupling-evidence-gap` records these absent inputs and
limits; it is a deferred evidence audit, not a model-validation case.
