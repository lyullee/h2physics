# Conditional premixed material-front reference

Status: **implemented_unverified**. No local native flame, equilibrium, graph,
example or deferred case has been executed for this module.

`h2physics.adapters.flash_front` composes an actual existing Cantera
`FreeFlameResult`, the shared `CanteraGas.equilibrium` HP endpoint and SciPy
shortest paths. It introduces no replacement chemistry, flame-speed correlation
or dispersion engine. HyRAM remains the preferred gas-dispersion provider and
SLABx-LH2 the preferred liquid-origin provider. Their rejected source/field
premises are not repaired by this model.

The chemistry is a warm ideal-gas mechanism reference. Spin-specific cryogenic
liquid/vapor enthalpy is not identified with mechanism enthalpy. Connecting a
release or dispersion field requires a separately qualified composition,
temperature/pressure, phase and energy-reference bridge; this module supplies no
automatic cold-release-to-reactive-cloud conversion.

## Physical level and required evidence

This is a **discrete initial-material-coordinate network** for an admitted
premixed hydrogen/oxygen/diluent cloud. It predicts conditional centre-to-centre
front arrival along specified face-connected material paths. It does not solve
laboratory flame motion, expansion-driven flow, evolving turbulent dispersion,
flame acceleration, obstacles, ignition probability or heat injury. A missing
path is a missing material connection, not a resolved wall or obstacle flow.

The supplied native flame must have positive flow, a positive admitted temperature
rise, a monotone temperature profile and a bounded native mass-flux variation.
Only H2, O2 and explicitly supported nonfuel diluents H2O/N2/Ar/He/CO2 are admitted
initially. Radicals and additional fuels need another qualified level. There is
no default flammability interval: a solved steady flame and caller qualification
do not establish an atmospheric flammability limit or transient ignition.

`FrontAdmission` requires clock, material frame, mixture/native-flame evidence,
thermal progress bounds and numerical energy/element/mass-flux budgets. Authored
example evidence is explicitly synthetic; it does not qualify a facility.

## Direct Python API

1. Use the existing `CanteraGas.free_flame(initial, settings)` to obtain an actual
   native premixed result, with its source/mechanism/transport evidence and
   original `native_phase_handle`. The example uses the public
   `CanteraGas.from_yaml` source-byte-verified constructor.
2. Call `premixed_reference(identifier, gas_owner, flame_result, admission)`.
   The function binds the original flame and creates native HP material states
   through public `create_phase`/`bind_phase` hooks. Bare native phases remain
   available through their retained handles. No private `_phase` call is used.
3. Construct `FrontCell(identifier, lattice_index, reference)` instances. Lattice
   indices are three Python integers; spacings are positive SI lengths. Cell
   identity and position must be unique. All cells share one pressure, material
   frame and clock; different admitted mixture references may be attached.
4. Call `run_material_front(cells, spacing_m=..., ignition_cell_ids=...,
   ignition_s=..., horizon_s=..., clock_projection_tolerance_s=..., contacts=...)`.

Relative native travel times are preserved. Projecting a positive travel or
thermal-band span onto an absolute clock must advance that clock and reproduce
the span within the explicit projection budget. Otherwise the run rejects the
clock representation; a large epoch cannot silently create simultaneous arrivals.

Ignition sites are declared cell centres with the same ignition time. No kernel
size, spark energy or spontaneous ignition is inferred. Cells are finite initial
parcels. At their computed arrival the whole parcel is assigned its native HP
endpoint as a lumped event. The ignition cell is therefore burned at the supplied
start; this is an explicitly declared coarse-grained ignition convention.

The edge time for neighbouring cells is half the lattice spacing traversed at
each cell's native inlet burning velocity. SciPy `dijkstra` supplies the shortest
path, source and predecessor arrays. Six-neighbour paths retain directional
lattice bias; refining the grid is not claimed to recover isotropic continuum
eikonal propagation. The reference is useful for native coupling, conservation
and material-path sensitivity; it is not a CFD flash-fire forecast.

## Finite material and energy accounting

Cell mass is native initial density times initial cell volume. Reached parcels
retain that mass and use the native HP equilibrium density to compute expanded
volume. Initial and final H2 masses use native species mass fractions. Net H2
creation is rejected as an inadmissible fuel-burn endpoint. Unreached or
beyond-horizon cells remain explicitly unburned; they are not relabelled as
burned at the last output time.

No arbitrary combustion-energy or TNT factor is used. For each reached parcel,
the recorded internal-energy change plus constant-pressure expansion work is
the energy residual. The outgoing mechanical work is `P*(V_final-V_initial)`.
This is an open mechanical boundary against the declared pressure reservoir,
not a sealed-cell UV explosion. Expanded volume is a material endpoint and is
not fitted back into the original cell geometry. Element residuals come from
the actual shared native HP solve and are mass-weighted per cell.

The result retains original native flame/phase/HP objects, the sparse graph,
raw shortest-path arrays, finite burn events and aggregate mass/energy residuals.
Public frozen bindings/snapshots supply SI mass density and internal energy for
the finite material ledger. The flame's input binding is definition-only because
the native solver legitimately evolves its working gas state. Unburned/burned
references explicitly freeze their separate native states. Source/definition
and state-seal semantics, weak lifetime tracking and legacy callback limits are
described in [CANTERA_FACTORY.md](CANTERA_FACTORY.md).
Native flame fingerprints, mass-flux admission and saved density fields use the
actual `FlameBase.density_mass` array. Scalar snapshots use `density_mass` too;
native display-basis changes do not change the kg/m3 meaning or finite mass/U/PV
ledger. Native FreeFlame setup requires mass display basis and rejects a molar
factory result before construction, retaining its original phase without reset.
Unreachable arrival is `None`. Factory failures retain the flame and any
completed native phase/HP objects in `PremixedReferenceError`. Propagation
failures retain completed burns and original graph/path outputs in
`FlashFrontError`; no alternate speed or equilibrium method is substituted.

Native solution fingerprints and factory-bound summary identities reject changed
flame profiles, pressure, transport settings, thermodynamic phases or replaced
cached speeds. These guards detect ordinary stale/mutated research inputs; they
are not a security boundary against deliberate private-object modification.

## Material contact, not heat injury

`MaterialContact` associates an occupancy interval with a material cell. The
native flame temperature band is selected by explicit interior progress
fractions. A gas parcel's residence across that band is obtained by integrating
inverse native axial velocity across the interpolated band boundaries. The
reported overlap intersects this residence with the declared occupancy and
campaign horizon. It is a material-following thermal passage, not the exposure
of a stationary geographical person. Native temperature/time band arrays remain
available for a later separately qualified transfer model.

No radiant or convective surface flux, absorbed dose, garment response, fatality
probability or protective credit is inferred. Such outputs require an actual
heat-transfer boundary and the existing separately qualified receptor APIs.

## Deferred verification

Four case definitions are in `validation.cases.flash_front`, profile
`flash-front`: independent axial arrival/finite native HP ledgers, disconnected
paths/material occupancy, native/summary mutation rejection, and actual native
flame width/grid sensitivity. No case discovery or execution was performed.
The existing binding case now also defines public factory source-SHA/live-reuse,
mutable-versus-frozen state, domain/definition, cached-binding and weak-handle
lifecycle checks; case count remains four. These checks are unexecuted.
The same case defines scalar/vector and finite mass/U/PV invariance under native
mass/molar display changes, and molar-display flame-setup rejection.
The example lives in `examples/flash_front.py`; import defines functions only.

The existing `chemistry` extra and core SciPy suffice at the dependency level;
actual Linux versions/native mechanism compatibility remain a cluster check.
Numerical reference gates do not establish measured flash-fire validity.

Primary native references:

- [Cantera premixed one-dimensional flow API](https://cantera.org/3.2/python/onedim.html)
- [Cantera thermodynamics API](https://cantera.org/3.2/python/thermo.html)
- [Native mass-density array](https://cantera.org/3.2/python/onedim.html#cantera.FlameBase.density_mass)
- [SciPy Dijkstra API](https://docs.scipy.org/doc/scipy/reference/generated/scipy.sparse.csgraph.dijkstra.html)

Native code and mechanism resources are used through installed dependencies;
no external reaction table, solver implementation or publication prose is copied.


The returned FlashFrontTrace is issued once by run_material_front. Its identity
snapshot includes the native reference bindings, output ledger, arrival map and
SciPy sparse graph arrays; cloning or later graph/source mutation invalidates it.
The existing flash-front-binding contract now covers these cases. It remains a
material-coordinate reference, not a validated fire/consequence prediction.

Its retained HP equilibrium result is also tied to a one-use Cantera issuance
token and the exact native phase handle. `require_current()` checks the recorded
summary and current native phase state; the existing flash-front-binding case
covers direct construction and dataclass replacement. Reactor traces and free
flame summaries still need equivalent result-level issuance/currentness guards.
