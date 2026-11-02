# Opposed-flow nonpremixed flame API

`h2physics.combustion` now exposes a steady one-dimensional counterflow diffusion
flame through Cantera's actual `CounterflowDiffusionFlame`. The existing premixed
`FreeFlame` remains available in `CanteraGas`; these are distinct boundary-value
problems within the same consolidated laminar-flame family.

## Inputs and ownership

The caller supplies a `CanteraGas` created from a mechanism whose source, rights,
thermochemical range and kinetic applicability have been reviewed. `MechanismBasis`
declares the source identity and valid temperature/pressure envelope. Fuel and
oxidizer are independent `CounterflowBoundary` values, each with a `ReactiveState`
and a positive mass flux in kg m⁻² s⁻¹. The two inlets must use one absolute
pressure. No fuel/oxidizer flow, release condition, or extinction strain is inferred.

`CounterflowFlameSettings` selects inlet separation, transport model, Soret and
radiation switches, grid-refinement criteria, grid cap and native solver verbosity.
The adapter assigns these values to Cantera and returns the exact editable native
solution. The result summary includes the actual peak temperature/location, grid
size, finite-difference maximum axial-velocity gradient and native extinction flag.
The gradient is a profile diagnostic; it is not advertised as a canonical strain
definition or a flame-stability criterion.

For analysis and measurement coupling, `counterflow_profile(result)` verifies the
retained native solution and makes a read-only columnar snapshot containing axial
position, temperature, velocity, density, complete species mole/mass fractions,
volumetric heat release and named native strain-rate definitions. Species arrays
use `(species, axial_point)` ordering; use `species_mole_fraction("H2")` or
`species_mass_fraction("H2")` for one species. Cantera's `mean`, `max`,
`potential_flow_fuel` and `potential_flow_oxidizer` strain rates are kept under
their own names so a downstream fit cannot silently substitute one definition for
another. The exact editable Cantera solution is still on `result.native_solution`.
For aligning measured points to the computed mesh, `profile.sample(z_m)` performs
linear interpolation within the solved interval and rejects extrapolation; it does
not claim a sub-grid solution.

`profile.integrate_heat_release(z0_m, z1_m)` integrates the retained volumetric
heat-release samples with piecewise-linear trapezoidal quadrature and returns a
signed per-unit-area quantity in W/m². With no bounds it integrates over the full
native domain. Optional bounds must remain inside the solved mesh. The method
does not infer a burner area, radial symmetry correction, total flame power, or
an independent combustion rate; it is a reduction of the native profile only.
The associated integral-partition and bounds contract is deferred for Nurion.

```python
from h2physics.adapters.cantera import CanteraGas, MechanismBasis, ReactiveState
from h2physics.combustion import (
    CounterflowBoundary,
    CounterflowFlameSettings,
    solve_counterflow_diffusion_flame,
    verify_counterflow_diffusion_flame,
)

# `mechanism_yaml` and its rights/domain record are caller-owned, source-audited inputs.
gas = CanteraGas.from_yaml(mechanism_yaml, mechanism_basis, phase_name="gas")
fuel = CounterflowBoundary(
    ReactiveState(300.0, 101325.0, {"H2": 1.0}), 0.2
)
oxidizer = CounterflowBoundary(
    ReactiveState(300.0, 101325.0, {"O2": 0.21, "N2": 0.79}), 0.8
)
result = solve_counterflow_diffusion_flame(
    gas, fuel, oxidizer,
    settings=CounterflowFlameSettings(width_m=0.02, soret_enabled=True),
)
verify_counterflow_diffusion_flame(result)
profile = counterflow_profile(result)
hydrogen = profile.species_mole_fraction("H2")
max_strain_rate = profile.strain_rates_s_inv["max"]
```

The mechanism must contain every declared species. A solve whose temperature
profile leaves the declared mechanism envelope is rejected. The result verifier
binds the original owner, inlet/settings identities, native mechanism definition,
native profile arrays and summary. Mutating the returned Cantera object invalidates
the stored result until the caller deliberately performs a new solve.

## Evidence and limits

The computational owner is Cantera's maintained 1D opposed-flow solver; no second
chemistry, transport or flame solver is copied. The official API and an official
hydrogen counterflow example are linked below. Solver availability is not mechanism
qualification. Grid, transport, radiation, chemistry, inlet apparatus and measured
uncertainty need to be assessed for each application.

The KIT NH₃/H₂ counterflow dataset record and RADAR4KIT metadata declare CC BY 4.0.
Its BagIt package was acquired to the git-ignored raw-data directory; all eight
payload checksums matched the publisher manifest. Five workbooks and nine worksheets
were schema-audited. This supports transfer comparison for hydrogen transport and
chemistry, not pure-hydrogen flame validation. The implemented reader exposes the
flat extinction-strain table, tied to its workbook SHA-256 and source row numbers.
It does not infer fuel composition, burner geometry, inlet mass fluxes, uncertainty,
or Cantera's native strain definition.

```python
from pathlib import Path

from h2physics.data.counterflow_flame import (
    load_extinction_strain_rates,
    load_inflame_species_profiles,
    load_normalized_optical_profiles,
    load_optical_band_integrals,
    load_optical_spectra,
    load_temperature_profiles,
)

archive = Path("data/raw/nh3-h2-counterflow-flame/archive/10.35097-bnpe6n1ppv92yjw4")
extinction = load_extinction_strain_rates(archive)
temperature = load_temperature_profiles(archive)
species = load_inflame_species_profiles(archive)
optical_spatial = load_normalized_optical_profiles(archive)
band_integrals = load_optical_band_integrals(archive)
spectra = load_optical_spectra(archive)
```

The source-bound readers also expose nine paired temperature profiles and twelve
species profiles (four condition groups, each with H2/NH3/NO). Only the checksum-reading
functions issue records that may claim publisher-workbook provenance; direct record
construction and dataclass replacement cannot reuse that identity. Conditions, workbook
hashes, source columns and worksheet rows travel with each immutable profile; reported
millimetres and centimetres are converted to metres while missing cells are preserved.
A cluster ingestion case checks counts and alignment, but has not yet run successfully.
The optical readers retain sixty spatially normalized intensity profiles, three
spatial band-integral series and three wavelength spectra. Their typed fields label
all signal values as normalized intensity; none is exposed as a species concentration
or temperature. The optical ingestion case in array `24229638[]` was stopped after
the read-only worksheet path showed no CPU progress; profile extraction now streams
each worksheet in one pass and needs a fresh pinned run. Raw workbooks are excluded from Git. Any separate redistribution must
retain the stated CC BY attribution and terms. Pure H₂/H₂-N₂ archives from DLR and
TNF remain excluded until their reuse terms are established. Receipt, checksums and
schema decisions are [recorded here](../research/data/nh3_h2_counterflow_flame.toml).
A deferred cluster case checks the BagIt archive hash, workbook hash, license tag and
source-row sequence for the ESR reader; it is ingestion verification, not a model-data
comparison.

References:

- [Cantera 3.2 one-dimensional reacting-flow API](https://cantera.org/3.2/python/onedim.html)
- [Cantera 3.2 opposed-flow diffusion-flame example](https://cantera.org/3.2/examples/python/onedim/diffusion_flame.html)
- [KITopen dataset record and CC BY 4.0 declaration](https://publikationen.bibliothek.kit.edu/1000197646)
- [Associated research article](https://doi.org/10.1016/j.fuel.2026.141356)

The wrapper, data reader and immutable profile view are not yet scientifically
validated. No native Cantera solve, numerical refinement or experiment comparison
has been performed. The workbook schema audit confirms file layout, not apparatus
reconstruction or independent validation. Those checks require a mechanism and case
conditions qualified against the source article.

## Result issuance boundary

`CounterflowFlameResult` is issued once by `solve_counterflow_diffusion_flame()`.
Its internal seal is not an authorization token: caller construction and
`dataclasses.replace()` cannot claim native-solver provenance. The deferred
`counterflow-result-issuer` contract checks both rejection paths. This ownership
guard does not establish flame accuracy; the model and experiment comparisons above
remain outstanding.
