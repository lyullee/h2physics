# Raw geological H2/He calibration interface

`h2physics.data.load_geological_calibration(path)` reads
three raw CSV members from the same checksum-pinned archive as the processed
surface-excess reader. It returns immutable typed hydrogen rows, helium rows
and sample configuration rows. Raw numeric strings, member names, physical
source line numbers, material/run labels and source column names remain available.

The H2 table preserves separate reported initial and equilibrium pressure roles;
He points preserve their reported calibration-pressure role. Callers cannot relabel
an equilibrium observation as initial pressure. Absolute-versus-gauge qualification
is unresolved: conversion to Pa does not create an admissible EOS pressure.
Each `ReportedSIQuantity` rejects non-finite caller-created values and requires a
reason when its value is absent. Its `require_absolute_pressure_pa()` guard fails
closed for pressure roles because the archive does not qualify the reference basis;
callers must use independently documented evidence and an explicit pressure-reference
conversion before constructing any EOS state. Temperature, uncertainty and geometry
quantities cannot be passed through that pressure-specific guard.
Pa, K, kg and m3 quantities are named;
bar/mbar, grams and litres are converted once. Reported configuration standard
uncertainties remain separate values without statistical propagation. An empty
helium pressure difference stays `None`; no fitted or logger-derived value is
substituted.
Missing sample mass/reference volume/sample volume also remain `None` with an
explicit missing reason. The CSV omits these for the COx configuration; the linked
workbook values are not synthesized. Missing values therefore prevent unqualified
calibration calculations instead of being replaced by another material's geometry.

The source archive is external, excluded from Git and redistribution. The loader
checks the exact source SHA-256 and table headers before ingesting any rows.
Record-level license and limitations remain in the existing geological adsorption
provenance manifests. This reader supplies observations for caller customization;
it does not fit a helium correction, call an EOS, compute uptake, convert excess
to absolute adsorption, borrow a logger average or qualify vessel capacity.

The authored case `geological-raw-calibration-lineage` uses the separately staged
`H2_CLUSTER_DATA_RAW_ROOT` archive on Nurion. It has not run. Only source/header inspection and static syntax
review were performed during this implementation.
