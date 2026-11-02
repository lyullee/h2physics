# Geological-material hydrogen adsorption observations

## Purpose and boundary

`h2physics.data.load_geological_adsorption_isotherm()` reads one of the four
processed isotherm CSVs from the exact Zenodo archive listed below. It keeps source
rows in memory, retains their original fields and row numbers, and does not extract
or copy the archive into the package. It is a data-ingestion API, not an adsorption
fit, storage-bed model, or vessel-capacity calculation.

The loaded `q_mmol_g` value is represented as
`signed_excess_loading_mmol_per_g`. Signed values are intentional observations;
the loader does not clip negative values, convert excess loading to absolute uptake,
or claim that `FiniteAdsorptionVessel` can consume this data. Calling
`require_absolute_uptake()` fails until a separate pore-volume/gas-density conversion
has an identified source and independent checks.

## Loading an acquired archive

Keep the acquired archive outside Git and pass its absolute local path:

```python
from h2physics.data import load_geological_adsorption_isotherm

observations = load_geological_adsorption_isotherm(
    "data/raw/geological-adsorption/zenodo-22305898/submission_package.zip",
    material_id="mof177",
)
point = observations.points[0]
print(point.pressure_bar, point.temperature_k)
print(point.signed_excess_loading_mmol_per_g)
```

Valid material identifiers are `cox`, `kunipia`, `laponite`, and `mof177`. The
reader checks the whole archive SHA-256 against the pinned publisher acquisition,
then parses only the selected CSV with the Python standard library. Pressure remains
in bar, temperature in kelvin, excess loading and its reported uncertainty/limits in
mmol/g. `source_fields` preserves source strings, including columns that are not yet
qualified for a physical calculation. The returned dataclasses and source-row tuple
are immutable.
The source-bound `GeologicalAdsorptionIsotherm` can only be issued by this archive
loader. Direct construction and dataclass replacement cannot attach a pinned archive
digest to caller-substituted source rows; build isotherms through
`load_geological_adsorption_isotherm()` before creating a research provider.

## Research provider handoff

An individual measured isotherm can be exposed through the existing
`AdsorptionProvider` interface without changing its uptake meaning:

```python
provider = observations.surface_excess_provider(
    temperature_k=observations.points[0].temperature_k,
)
state = provider.equilibrium([pressure_pa], provider.temperature_k)
assert state.basis.loading_definition == "surface_excess"
```

The caller must select one temperature actually present in the table. This first
provider level supports one H2 partial pressure and linear interpolation in
log-pressure between measured points. It refuses multicomponent competition,
temperature interpolation and pressure extrapolation. Signed observations remain
signed. The result can support bounded surface-excess comparisons, but it is not
absolute adsorption capacity. `FiniteAdsorptionVessel` therefore rejects this
provider; no excess-to-absolute conversion or commercial-bed inference is made.
The provider receipt retains the original licensed source object and detects later
changes to its measured points or interpolation arrays. At construction, its arrays
and retained row objects are checked against the exact loader-issued measured isotherm,
so replacement cannot relabel altered values as that source. Each returned site carries
immutable `AdsorptionSourceObservation` receipts with H2 identity, source row IDs,
raw signed-excess loading, log-pressure weights, and reported standard uncertainty,
detection limit, and quantification limit in mol/kg. These values are numerically
equivalent to the source mmol/g fields. State construction checks that their weighted
loading reconstructs the returned site value. Missing statistics remain `None`.
Weights record lineage only; no statistical propagation is inferred because
independence and covariance are not established.

Each source-row receipt now also carries the dataset DOI/checksum and labels a
reported uncertainty as `reported_standard_uncertainty`, without changing its
excess basis or asserting a distribution. `FiniteAdsorptionVessel` can retain
uncertainty only for compatible absolute-basis state receipts; it rejects direct
surface-excess conversion, interpolated reported errors without covariance, and
covariance labels without a covariance-derived state value.

## Source record and rights

The source is Zenodo record [10.5281/zenodo.22305898](https://zenodo.org/records/22305898),
declared CC BY 4.0 by the record. The archive is not redistributed by this package;
the receipt `research/data/geological-adsorption-2026-09.toml` records file identity,
checksums, acquisition location, source links and known limits. Users who redistribute
derived observations must meet the source license terms and review the rights of
third-party components identified in the deposit.

The archive tables contain measured and processed material observations. This
ingestion path selects the four processed isotherm tables only. Their schema audit
found six data rows per material and fields for pressure, temperature, reported
loading, uncertainty, detection limits and status. Full uncertainty reproduction,
third-party provenance review, and an independently justified excess-to-absolute
mapping remain open work. These observations therefore do not qualify a commercial
adsorbent or pressure vessel.

`adapters.bind_absolute_adsorption_state()` now provides a narrow bridge into the
existing finite-vessel API when an independently qualified, source-backed absolute
loading state already exists. The bridge checks row coverage for every site/species
and returns the original state only at its exact measured condition. It does not
convert the geological surface-excess rows, fit an isotherm, interpolate, or certify
vessel performance. Its deferred API contract is
`absolute-adsorption-single-point-vessel-bridge`.

## Deferred verification

The separate [raw calibration interface](GEOLOGICAL_CALIBRATION.md) retains the
original H2/He observations and sample configuration without fitting a baseline
or filling missing values. [The raw CSV structure audit](../research/geological_raw_schema.md)
records14 member hashes/columns/widths and blank fields; literature-derived
comparison files remain outside admitted host reuse.

`validation/cases/geological_adsorption.py` defines a Nurion-deferred provenance and
schema contract. It checks the pinned digest and material-table dimensions, retained
row identity, and fail-closed basis behavior. The contract has not been executed as
part of implementation; data schema assertions do not constitute model or material
validation.
