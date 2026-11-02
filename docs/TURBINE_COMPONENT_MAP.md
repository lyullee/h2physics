# Caller supplied turbine component maps

`h2physics.combustion.TurbineComponentMap` stores a rectangular grid of corrected
mass flow and isentropic efficiency against corrected speed and expansion pressure
ratio. It requires a map identifier, evidence identifier, source URI, license ID,
source SHA-256, speed unit, pressure-ratio convention and corrected-flow basis.
Rows correspond to speed coordinates and columns correspond to pressure-ratio
coordinates.

`interpolate_turbine_map()` performs bilinear interpolation only inside the declared
grid. It rejects malformed dimensions, unordered coordinates, invalid flow or
efficiency values, nonpositive corrected-speed coordinates, and any request outside the map domain. The returned
`TurbineMapPoint` retains the map and reconstructs both interpolated values during
construction, so callers cannot attach arbitrary summaries to a different map.
The admitted map also seals its complete metadata and numeric grids. Map
interpolation, map-bound inputs and retained map points recheck that seal, so
replacing map values or provenance after admission rejects; calling initialization
again cannot silently reseal modified data. A deferred mutation contract records
this behavior and has not run.

`TurbineMapPoint.require_current()` rechecks its retained map and reconstructs
the interpolation from the stored corrected speed and expansion ratio. This is
the point-level freshness API used by the cooling-bleed Brayton result; it does
not run the gas-cycle model.

`TurbineMapPairingReceipt` can retain one current `MappedCompressorTrace` observation
alongside one `TurbineMapPoint`. The current `MappedCompressorTrace` owner wraps an
LH2DT compressor stage; it is not the air compressor in `run_open_cycle_brayton()`.
The receipt pairs separately owned map observations and does not represent a gas-
turbine compressor/turbine operating point. It requires caller evidence identifiers linking the
process window, clock, component pairing, shaft-speed basis, flow basis and pressure-
ratio convention. This is an evidence-bound pairing only: the existing compressor
adapter and turbine map use different coordinate owners, and the receipt makes no
mass-flow, power or shaft-balance claim.

This is a component-data adapter. It does not infer map conventions, convert between
corrected-flow reference conditions, model choking or surge, predict missing map
regions, interpolate transient behavior, or solve the coupled machine shaft. Units,
correction reference, total/static station conventions, test provenance and
uncertainties must be documented by the data provider. A map supplied for one
machine is not transferable to another without evidence.

Deferred contracts are registered in `validation/cases/turbine_component_map.py`.
They cover interpolation and domain rejection; they have not been executed and do
not qualify a turbine. Machine use still needs owner-reviewed map data, native
thermodynamic integration into the existing open Brayton route, shaft balance,
off-design guards and experimental comparison.

The pairing receipt contract is registered in `validation/cases/compressor_map.py`
under the existing `compressor-map` profile. It requires an untracked project fixture
module that constructs a real pinned-LH2DT compressor trace and a reviewed,
source-hashed turbine map point. The plan stores explicit replacement placeholders
for that module, source URI, SHA-256 and license. Until those project fixtures and
rights records are supplied, the case is intentionally not runnable. The profile
association is already present because the contract extends the existing
`compressor_map` case module.
