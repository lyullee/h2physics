# Preferred dispersion safety and rights gap audit

Audit scope: source-to-receptor-to-alarm chain for the selected high-pressure
gas and LH2-origin dispersion providers. This is a code/provenance review, not
a scientific execution or legal clearance.

## Evidence reviewed

- `src/h2physics/adapters/facility_accident_chain.py` admits a finite source
  together with an accepted preferred `DispersionExecution`. The high-pressure
  gas path also requires its HyRAM finite-source projection; the LH2 path binds
  an admitted vapor source. The chain does not sample a receptor field.
- `src/h2physics/adapters/preferred_dispersion_alarm.py` accepts a caller-supplied
  scalar H2 mole fraction. It retains caller evidence for the receptor mapping
  and steady-window applicability and passes the sampled value to the existing
  sensor/alarm engines. It does not inspect native provider grid values or
  verify a spatial extractor against them.
- `validation/cases/facility_accident_chain.py` explicitly says no successful
  dispersion run or source-to-field physics validation is established.
- `research/preferred_dispersion_dependencies.toml` records HyRAM 6.1 as
  GPL-3.0-only, and SLABx 1.0.8 / SLABx-LH2 0.2.0 as MIT with pinned revisions
  and installed-license hashes. It also records that the HyRAM Gaussian-entry
  source mass gap is rejected and SLABx-LH2 is a steady LH2-vapor calculation,
  not independent field validation.
- `docs/RIGHTS_AND_PROVENANCE.md` treats code licenses and dataset grants as
  separate rights and does not admit raw observations by default.

## Gaps and priority

### 1. High priority: provider-native receptor extraction is not connected

The current alarm bridge can only bind a concentration that the caller has
already extracted. Its metadata preserves who supplied the value and the
assumptions, but cannot show that a native HyRAM/SLABx result at the declared
coordinates actually produced it. Therefore the bridge is useful for composition
with an independently controlled extractor, but it is not yet an end-to-end
provider-to-detector calculation. Implement a typed extraction interface for
each native provider only after their supported spatial outputs, coordinate
conventions and versions are pinned. It must retain the native result identity,
reject unsupported coordinates/domains, and avoid inventing interpolation or
time dependence. Until then, report receptor fields as caller-projected inputs.

### 2. High priority for validation claims: no cleared measured plume benchmark

The reviewed provider licenses establish conditions for separately installed
code; they do not establish rights to redistribute experimental concentration
fields or validate this project's provider-to-receptor mapping. No dataset with
both file-level redistribution evidence and receptor-concentration measurement
metadata was identified in this scoped review. Keep raw benchmark files out of
the public tree. A future candidate needs version/DOI, explicit dataset grant,
file checksums, attribution, sensor/source/geometry/time metadata, and a
separate review of any paper/figure or embedded third-party material before
acquisition is treated as validation evidence.

## Rights status

The current provider code receipts are recorded in
`research/preferred_dispersion_dependencies.toml`; HyRAM remains an optional
GPL-3.0-only dependency and must not be bundled or represented as relicensed by
this host. The recorded MIT licenses for the user's SLABx repositories do not
clear unrelated datasets, papers, tables or figures. This audit makes no
redistribution or legal-safety guarantee.

No files or measured data were acquired or redistributed in this audit. No
scientific tests, native provider runs or HPC calculations were performed.
