# Photon accounting and finite H2 conversion

`photochemistry` connects an explicit incident spectrum, an evidenced optical
path and a prescribed electron-equivalent quantum yield to H2 production.
Finite conversion and calorimetry reuse the existing `StoichiometricReaction`
and `MolarEnthalpyProvider` interfaces. This is a condition-specific optical/
stoichiometric reference level. It does not identify charge-recombination,
catalyst kinetics, phase transfer or a universal activity coefficient.

## Spectral input and units

`PhotonSupply.from_bands(edges_m, irradiance_w_m2_per_m, ...)` takes positive
increasing wavelength edges, nonnegative flat spectral power density in each
band, and the illuminated projected area in m2. The number of density entries
is one less than the number of edges. Per band, optical power is irradiance
density times wavelength width times area. Photon amount rate is the power
times the mean wavelength divided by h*c*N_A. This mean is exact for the
declared flat-per-wavelength power density; it is an approximation to a smooth
physical spectrum whose accuracy depends on the selected bins.

`from_nanometer_bands` explicitly accepts nm and W/(m2 nm), applying both length
and inverse-length scale changes. A factor1e9 is required when changing a
per-nm density to a per-m density. `from_lines(wavelength_m, optical_power_w,
...)` represents discrete monochromatic powers with no invented bandwidth.
Optical power is W, photon amount rate is mol photons/s, not photon count/s.
Arrays are copied and read-only. Source/incident-plane identity and exact
spectral representation follow a content fingerprint.

## Optical and quantum-yield contracts

`BeerLambertPath.uniform` takes a depth in m, an absorption coefficient in1/m
and reflectance in[0,1], either scalar or matching per-band/per-line arrays.
Absorption/reflection are constant in each declared band. After input-plane
reflection, the unscattered path transmits exp(-alpha*depth); the remainder
is absorbed. `expm1` preserves a thin path's small absorption. Zero depth or
coefficient is transparent; reflectance1 is fully reflected. Coefficients
must come from appropriate material, medium and geometry evidence. Scattering,
multiple reflection, angular refraction and loading-dependent optics are absent.
The path retains an exact wavelength-grid/representation fingerprint. An old
two-band array cannot silently move to two different wavelengths or from lines
to finite bands. The linear optical path may be reused at different power on
the same grid; quantum yield still requires a separately evidenced rebind to
the new complete light input.

`PhotoConditions` declares catalyst/medium identities, catalyst mass kg,
temperature K, pressure Pa absolute, incident geometry and evidence.
`PhotonYield.bind` requires that context and an actual photon-supply fingerprint.
Changing input spectrum or power requires rebinding with explicit evidence;
the model does not infer an intensity-independent material law.

Yield is a fraction of productive electron equivalents per photon:

- `absorbed_electron_equivalents`: multiply absorbed photon rate by yield.
- `incident_electron_equivalents`: multiply incident photon rate by yield.

H2 formation requires two productive electron equivalents per molecule. A
product-molecule quantum yield and a percentage are different inputs; convert
only after the source's denominator, percentage and electron convention are
known. Incident AQY is not multiplied by absorption a second time.

This level admits at most one productive electron equivalent per absorbed
photon. Absorbed yield must be in[0,1]. Incident yield must additionally be no
greater than each band's absorbed fraction, within an eight-machine-epsilon
fraction roundoff budget. An integrated budget cannot hide an excessive
yield in one band. This restriction excludes chain/multiple-exciton mechanisms
that require a different justified model level. It is a photon-budget test,
not a proof of reaction energetics or experimental validity.

## Python rate example

```python
from h2physics.core import Origin
from h2physics.photochemistry import (
    BeerLambertPath, PhotoConditions, PhotonSupply, PhotonYield,
    photon_hydrogen_rate,
)

# Authored numerical inputs only; replace with qualified experimental inputs.
light = PhotonSupply.from_nanometer_bands(
    [350., 450., 550., 650.], [1., .8, .4], illuminated_area_m2=.002,
    geometry_id="beam-plane", source_id="authored-spectrum")
conditions = PhotoConditions("catalyst", "solution", .002, 300., 1e5,
                             "beam-plane", "authored-condition-evidence")
optics = BeerLambertPath.uniform(
    light, depth_m=.001, absorption_coefficient_m_inv=[1200., 800., 100.],
    reflectance=.08, evidence_id="authored-optical-coefficients")
yield_curve = PhotonYield.bind(
    light, [.3, .2, .05], basis="absorbed_electron_equivalents",
    conditions=conditions, evidence_id="authored-prescribed-efficiencies",
    origin=Origin.SYNTHETIC)
rate = photon_hydrogen_rate(light, optics, yield_curve)
mol_h2_s = rate.hydrogen_mol_s
mol_h2_kg_catalyst_s = rate.specific_hydrogen_mol_kg_s
```

Specific rate divides by the declared catalyst mass; it does not imply that
changing catalyst mass scales the overall rate linearly. The same light/path/
yield and compatible geometry must support any comparison. Source-specific
reported rate or AQY alone does not determine an incident spectrum.

`PhotoRate` keeps actual input objects, per-band reflected/absorbed/transmitted
power, absorbed photon rate, productive electron rate and both optical ledger
defects. `photon_budget_admitted` names its restricted gate. An inadmissible
incident yield raises `PhotoAdmissibilityError` containing the original result.
Those diagnostic values cannot drive `convert_photon_exposure`.

## Finite chemistry and thermal requirement

`SteadyPhotoWindow(start_s, end_s, clock_id, evidence_id)` declares an absolute
finite window in seconds. Spectrum, path, conditions and prescribed yield are
held fixed throughout it. Call `convert_photon_exposure(rate, window,
reaction=..., initial_mol=..., hydrogen_species_id=..., enthalpy=...)` with an
element/charge/mass-balanced reaction and declared phase-specific species.
The selected product must be neutral H2 with a positive coefficient.

The H2 photon rate times duration determines a prescribed stoichiometric
extent. The existing reaction core checks finite reactant availability and
returns the new inventory. An insufficient inventory raises `PhotoInventoryError`
with the rate, window, demanded extent and original cause. The function does
not cap extent, invent a light shutoff or assert a depletion event time. A
new illuminated process state after depletion would need its own boundary.

For a sequence of changing but explicitly admitted spectra or condition-specific
yields, `run_photochemical_operation([(rate, window), ...], ...)` applies adjacent
windows in order while carrying the exact remaining stoichiometric inventory.
Each segment retains its original `PhotoRate`, `SteadyPhotoWindow` and
`PhotoConversion`; all segments must use the same absolute clock and reaction,
and there may be no implicit gaps. Represent a dark interval with an explicit
zero-power spectrum. `PhotoOperationTrace` reports the original segment results
and aggregate optical/caloric totals. If a later finite inventory is inadequate,
`PhotoOperationError` retains the completed segment prefix, failed rate/window
and original `PhotoInventoryError`. This does not model evolving catalyst state,
photochemical kinetics, changing optical coefficients inside a window or an
automatic light shutoff/depletion event.

Without thermochemistry, heat fields stay `None`. With a compatible existing
enthalpy provider, the fixed-T/P first law computes H_out-H_in and the required
thermal boundary as that enthalpy change minus absorbed optical energy.
Positive heat must enter; negative heat requires removal to maintain the
prescribed temperature. The provider must include compatible formation/
reference enthalpies and correct phases. Actual native gas calorimetry can
use `CanteraMolarEnthalpy`; it cannot supply a liquid reaction reference merely
by renaming the species phase.

Required heat is a boundary requirement, not an available utility or predicted
temperature. First-law accounting does not prove Gibbs/exergy feasibility,
band alignment, carrier potentials or an achievable catalyst yield. No generic
solar-to-H2 efficiency is returned: donor chemistry, electrical bias, products,
spectral input and the relevant free-energy reference must be established.
Methanol photoreforming is not automatically overall water splitting.

`PhotoConversion` and `PhotoOperationTrace` are issued only by the finite-exposure
and operation functions through one-use tokens. Their nested rate, optical source,
reaction result, window, endpoint inventories and reported energy totals are sealed;
the operation checks every retained segment before composing summaries. Direct
construction, `dataclasses.replace()` token reuse and post-issue changes to nested
optical inputs are rejected. This guards result provenance and freshness without
adding catalyst kinetics or dynamic light control.

## Data and verification

The acquired TiO2 archive is accessed through the separate profile described
in PHOTOCATALYSIS_DATA.md. Its reported AQY and rate meanings, source rows,
duplicates and unresolved apparatus inputs survive mapping. The profile does
not fit or silently bind the model's quantum-yield convention. Catalyst
identity, mass, medium, irradiation and gas-collection evidence still govern
whether an observation can be compared with this model.

Run `python -m pytest tests/test_photochemistry.py` and
`python scripts/check_photochemistry.py` with the chemistry extra for actual
native calorimetry. [The research replay](../research/photochemistry.md) records
exact SI line photon counts, continuous-spectrum independent quadrature and
band refinement, transparent/thin/opaque/reflected limits, per-band electron
budget rejection, finite stoichiometry and an independent native mixture-H
audit. All coefficient/spectrum cases are authored verification inputs and
are not experimental validation.

Public definition sources are the
[IUPAC photocatalysis recommendations](https://doi.org/10.1351/PAC-REC-09-09-36),
[BIPM SI definitions](https://www.bipm.org/en/publications/si-brochure) and
[native Cantera thermochemistry API](https://cantera.org/3.2/python/thermo.html).
No source prose, coefficient table, measured-data table or worked case is
reproduced. The original optical model uses NumPy and existing SciPy constants;
it introduces no optional optics dependency or alternate reaction solver.

## Caller-supplied Gibbs path energy bound

`assess_photo_gibbs_energy()` can attach a finite reaction-affinity path to one
issued `PhotoConversion`. Supply monotone extents from zero to the exact conversion
extent and the matching reaction Gibbs affinity in `J/mol reaction` at each
sample. The helper reconstructs each intermediate species inventory from the
retained stoichiometry and integrates `ΔrG dξ` with piecewise-linear interpolation.
The thermodynamic state ID must match the conversion's temperature, pressure, and
medium-condition evidence. The caller owns the chemical-potential model,
phase/activity meaning, sample resolution, and interpolation evidence.

The receipt compares the positive integrated Gibbs increase in joules with the
absorbed optical energy in joules as a photon-only necessary energy upper bound.
A failed comparison means the absorbed photons alone cannot cover that Gibbs
increase under the declared boundary. A passing comparison is not sufficient for
feasibility and does not establish usable radiation exergy, heat-to-work
conversion, quantum yield, kinetics, or experimental performance. It is not a
complete process energy or exergy balance. The registered synthetic contract
checks both sides of the inequality but contains no material Gibbs data.
