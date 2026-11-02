# Simulated hydride PCT source-to-model gap

## Source and inspected schema

The Mendeley Data v1 record [10.17632/trpnk55pmz.1](https://doi.org/10.17632/trpnk55pmz.1)
contains five acquired CC BY 4.0 workbooks, classified as `simulated` in the
source manifest. A read-only header review found absorption and desorption
worksheets, temperature columns labeled in both °C and K, pressure columns
labeled in bar, and concentration columns labeled either `NL/kg` (three
workbooks) or `wt%` (two workbooks). No source values were converted, evaluated,
or fit during this review.

The existing `VanthoffPlateau` API evaluates hydrogen fugacity at a specified
temperature, loading fraction, and branch. The worksheet headers do not resolve
whether pressure is absolute or gauge, the normal-volume reference and uptake
denominator for `NL/kg`, or the mass/sample basis for `wt%`. Mapping these
concentrations to the model's loading fraction would therefore require unsupported
assumptions. The source's simulated origin also means a future match cannot serve
as independent equilibrium validation without tracing and separating the
generating model.

The deferred metadata-only Hangang contract is
`hydride-pct-simulated-equilibrium-model-link-gap`. It checks that the licensing,
source origin, file inventory and unresolved conversion boundary remain
documented; it does not read or score workbook rows. The full evidence checklist
is recorded in [`research/data/hydride-pct-simulation.toml`](../research/data/hydride-pct-simulation.toml).

## Evidence needed for a source-bound regression

Document pressure basis, `NL/kg` normal-volume reference and denominator,
`wt%` mass basis, temperature-column/material mapping, absorption/desorption
branch mapping, and the source model/code that generated the curves. Then a
pointwise regression can be considered without relabeling simulated records as
experimental validation. Until then no pressure conversion, uptake conversion,
parameter fit, or model comparison is admitted.
