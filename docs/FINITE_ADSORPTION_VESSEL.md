# Finite adsorption vessel capacity

`FiniteAdsorptionVessel` closes the inventory boundary left open by loading-only
working capacity. It combines two existing owners:

- an `AdsorptionProvider`, such as the separately installed PSA-Dyna equilibrium
  adapter, owns competitive equilibrium loading;
- a common `PropertyProvider`, such as a pure-fluid CoolProp provider or a
  reviewed frozen-mixture adapter, owns free-gas density.

The new layer performs only rigid-volume bookkeeping. It does not reproduce an
isotherm, gas EOS, adsorption heat or dynamic bed solver.

## Python contract

`AdsorptionVesselGeometry` records total internal volume, adsorbent envelope
volume, inaccessible volume, adsorbent mass and a measurement-basis identifier.
Free-gas void is the explicit difference. Pellet skeletal density, pore volume and
packed-bed void fraction are therefore never silently substituted for one another.

`FrozenGasBinding.bind(...)` ties one species order and mole-fraction vector to a
common property provider. Molar masses are explicit SI inputs used only to convert
the owner's mass density into total molar inventory. The composition identity is
evidence supplied by the application; a generic EOS object is not treated as proof
of mixture composition. If the provider itself exposes composition metadata, the
binding checks the complete species order, mole fractions, molar masses and ID both
at admission and before/after each state query. A later provider-side composition
change invalidates the binding. Providers with no composition metadata remain
caller-evidenced, and that limitation is not converted into a claim of provider
verification.

`FiniteAdsorptionVessel.snapshot(P, T)` obtains the original adsorption equilibrium
and gas state, then reports component inventories:

```text
free gas = rho(P,T) * declared void volume / mean molar mass
adsorbed = absolute loading(P_i,T) * adsorbent mass
total = free gas + adsorbed
```

The charged/discharged `AdsorptionVesselDelivery` is issued only by the vessel
owner. It retains the two current snapshots and reconstructs free-gas, adsorbed,
total and selected-product changes from those endpoints. The downstream
`AdsorptionProductMassFlow` projection rechecks both endpoint snapshots and the
delivery receipt before and after converting signed mole changes to mass and
caller-selected interval-average flow. Directly authored deltas, clone replacement,
or post-capture snapshot/delivery mutation cannot claim the owner calculation.
This remains an endpoint quotient, not a time-resolved valve or station model.

Vessel snapshots are issued only by `FiniteAdsorptionVessel.snapshot()`; direct
construction and dataclass replacement cannot relabel or alter their inventory
arrays as a fresh endpoint result.

`delivery(charged_P, charged_T, discharged_P, discharged_T,
delivery_species=...)` returns the signed free-gas, adsorbed and total component
changes and a positive selected-product delivery. Competitive displacement may
make a non-product component change negative; the complete signed vector remains
visible.

`pressure_for_inventory(target, species_id, temperature_k, pressure_bounds_pa)`
inverts the same equilibrium endpoint inventory at fixed temperature and frozen
gas composition. It samples the caller's full pressure bracket, rejects sampled
nonmonotonicity and targets outside the sampled inventory range, then uses a
bracketed scalar solve and retains the final snapshot and inventory residual in
`AdsorptionPressureSolution`; `pressure_pa` reads the solved pressure from the
snapshot. The full sampled pressure/inventory curve is also copied into read-only
arrays on the solution receipt. The sampling guard does not prove monotonicity
between sample points; callers remain responsible for selecting a domain where
the supplied EOS and equilibrium provider are valid. The solution records the
pressure and inventory tolerances used in addition to the sampled bracket. It
is issued only by the vessel's inverse operation; direct construction and
`dataclasses.replace()` cannot turn another snapshot or edited curve into a
solver-issued pressure result.

```python
charged = vessel.snapshot(10e6, 298.15)
h2_index = charged.adsorption_basis.species.index("H2")
solution = vessel.pressure_for_inventory(
    charged.total_component_mol[h2_index],
    "H2",
    298.15,
    (1e6, 10e6),
)
print(solution.pressure_pa, solution.residual_mol)
```

This example needs a caller-provided vessel instance and does not imply that its
equilibrium or gas-property providers are experimentally qualified.

## Admission and rejection

Only an explicitly `absolute` loading basis is admitted. Surface-excess or
source-defined uptake requires a separate, evidence-backed excess-volume
correction and is rejected here. Adsorption and gas species order must match.
Provider basis or exposed-composition changes, non-gas property results, changed
endpoint pressure or temperature, negative absolute loading and zero/negative
selected delivery fail instead of being repaired. The deferred owner-basis contract
also rejects a provider composition mutation after binding; it has not been run.

Snapshots also preserve optional source-row lineage and standard-uncertainty
semantics when an `AdsorptionState` supplies `AdsorptionSourceObservation`
receipts. The vessel passes a scalar uncertainty only when its semantics support
the operation: one unit-weight reported observation, explicitly independent
standard errors, or an already propagated source value. An already-propagated
state uncertainty is one standard uncertainty per species for the total adsorbed
loading across all sites; it is not assembled by summing site sigmas. Explicitly
declared independent row errors are combined by weighted variance, with their
dependence-evidence IDs retained. The vessel refuses interpolation
of reported errors without covariance, and it refuses a covariance-propagated
label without an actual covariance-derived state receipt. The scalar field covers
adsorbed loading only; gas EOS, geometry and shared calibration uncertainties are
not included. Geological signed-excess receipts remain ineligible because the
vessel continues to require absolute loading.
When source-row uncertainty produces a component vector, every species at every
adsorption site must have a qualified receipt. Partial coverage is rejected; an
absent species/site is never represented as zero uncertainty.
An `AdsorptionState` uncertainty vector is accepted only with
`covariance_matrix_propagated` semantics and nonempty evidence IDs; an explicitly
numeric vector cannot be labeled unqualified or reported-row uncertainty.

`AbsoluteAdsorptionVesselBridge.require_current()` also pins both the original
`AdsorptionState` object and its qualification evidence identity. Replacing the
state with an equal-valued copy or editing the qualification ID invalidates the
bridge before an exact-condition query. This preserves provenance ownership; it
does not establish the scientific adequacy of the caller's qualification evidence.

When the qualified state carries both provider-supplied derivative arrays,
`bridge.local_loading_sensitivity()` exposes the original per-site Jacobian with
respect to species partial pressures and temperature. Its directional response is
a first-order change in loading per adsorbent mass at the exact anchor. It is not
a new equilibrium state, does not supply finite-difference derivatives when data
are absent, and excludes free-gas/EOS response. The deferred bridge contract covers
derivative identity and directional mapping; no physical qualification follows.

`BedInventoryAudit` direct construction also checks its finite, absolute-loading
snapshot, geometry vectors, energy-reference identity and species-resolved totals
before capturing a freshness seal. A caller cannot instantiate a receipt with
invented component totals and then make those totals the integrity baseline. Its
adversarial contract remains deferred to Nurion.

The acquired geological-material reference dataset currently reports signed
surface excess. `GeologicalSurfaceExcessProvider` is available for bounded
single-component research comparisons on one measured temperature/log-pressure
curve. Its `surface_excess` basis intentionally fails this vessel's admission gate;
it must not be used to report absolute vessel inventory or capacity.

## Physical limit

This is an equilibrium endpoint capacity level. Temperature and composition are
prescribed; pressure can be solved only within a caller-supplied bracket. It does
not predict fill time, LDF/transport limitation, thermal fronts, adsorption heat,
vessel-wall storage, pressure loss, valve flow, product purity, cyclic operation or
pressure-dependent composition change. Those require the existing native
bed/equipment owners and independent material/vessel data. Code and deferred
contracts remain `implemented_unverified`; no local model or test was executed.



## 2026-11-01 finite adsorption CoolProp migration

The 90/10 H2/N2 finite adsorption-vessel example now uses the existing
GasComposition/CoolPropMixtureProperties HEOS owner. The authored ideal density
and zero enthalpy/internal-energy/entropy provider was removed; native H2/N2
molar masses are used. The adsorption equilibrium is still an authored fixture
and does not establish material or vessel performance validation.

All nine existing finite-vessel contracts passed locally after this migration.
The 10-to-1 MPa delivery example gives 311.22523700808125 mol H2, and the 5 MPa
pressure inverse has a 2.55795384874e-13 mol inventory residual. Void volume
checks now use a numerical tolerance; owner binding verifies both immutable
native identity rejection and mutation rejection through a mutable metadata view.
Uncertainty cases yielded reported sigma 0.42 mol, independent sigma
0.469574275275 mol and covariance sigma 0.63 mol, with unjustified interpolation
and unqualified propagated-array inputs rejected.

These tests exposed an existing, independent production provenance defect:
snapshot() collected source IDs but did not return them as uncertainty source
IDs in the observation path. It now preserves the sorted source/dependence IDs;
the uncertainty-lineage case passed after the correction. Targeted Ruff and
scoped whitespace checks passed. No independent adsorbent measurements were
introduced. Source/model status and rough overall progress remain unchanged
(approximately 30–40%; catalog implementation classes 56/82).

The AST API index was regenerated: 360 modules, 1802 public definitions. The
legacy Nurion metadata inventory remains 413 cases, 59 profiles, 114 modules;
it does not include all Hangang-only source-data cases. The new acoustic phase
diagnostic is registered in the active Hangang plan with staged source paths.
