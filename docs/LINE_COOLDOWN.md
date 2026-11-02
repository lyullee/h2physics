# Hydrogen transfer-line cooldown energy estimate

`h2physics.cooldown` provides a reusable first-law estimate for the hydrogen
mass needed to cool a declared collection of transfer-line sections. It is
intended for early operating-sequence design and for passing a consistent duty
into a later equipment model. It does not predict a cooldown transient.

## Python API

Each `CooldownSegment` represents a thermally lumped wall and, optionally, a
contained hydrogen inventory. Geometry can be reduced to the wall mass by the
caller. Wall heat capacity and fluid enthalpy are callables, so the application
may use CoolProp, another EOS, or qualified measured fits without binding this
module to a particular package.

`h2physics.IsobaricEnthalpyPath` is the common-provider bridge. It pins one absolute
pressure, the provider's `PropertyBasis`, a property-evidence identity and an
explicit allowed-phase set. It can be passed directly as the contained-fluid
enthalpy callback, while `state_at(T)` supplies coolant endpoint enthalpies from
the same property owner:

```python
from h2physics import IsobaricEnthalpyPath
from h2physics.thermo import CoolPropProperties

hydrogen = CoolPropProperties("Hydrogen")
line_h2_path = IsobaricEnthalpyPath(
    hydrogen, pressure_pa=line_pressure_pa,
    evidence_id="coolprop-heos-hydrogen-property-path",
    allowed_phases=("liquid", "gas", "supercritical_gas", "supercritical"),
)
inlet_h = line_h2_path.state_at(inlet_temperature_k).enthalpy_j_kg
outlet_h = line_h2_path.state_at(outlet_temperature_k).enthalpy_j_kg
```

The caller must choose phase labels that cover the actual endpoint path. If a
two-phase state is intended, include `"two_phase"` explicitly and verify that the
provider supports the requested PT state. The bridge rejects a changed pressure,
energy-reference basis or phase outside the declared set; it does not smooth or
interpolate properties.

For a provider-backed coolant calculation, call
`estimate_line_cooldown_with_provider(segments, coolant_path=..., coolant_inlet_temperature_k=...,
coolant_outlet_temperature_k=..., evidence_ids=...)`. The returned
`PropertyBackedLineCooldownEstimate` wraps the energy ledger and retains the exact
inlet/outlet `ThermoState` objects and property path. `require_current()` re-queries
both endpoints before the reported minimum coolant mass or duty is consumed. Its
scalar coolant inlet and outlet enthalpies must each match those exact states, not
only have the same difference; this prevents mixing a shifted enthalpy reference
with provider-bound endpoints. The
provider path evidence is added to the energy ledger; if a segment's contained-fluid
callback is another `IsobaricEnthalpyPath`, its evidence ID is added as well.

```python
from h2physics.cooldown import CooldownSegment, estimate_line_cooldown

section = CooldownSegment(
    segment_id="transfer-line-01",
    wall_mass_kg=120.0,
    solid_cp_j_kg_k=qualified_wall_cp,
    wall_initial_temperature_k=295.0,
    wall_target_temperature_k=25.0,
    fluid_mass_kg=0.0,
)
estimate = estimate_line_cooldown(
    (section,),
    coolant_inlet_enthalpy_j_kg=h_hydrogen_in,
    coolant_outlet_enthalpy_j_kg=h_hydrogen_out,
    additional_heat_j=declared_known_heat_leak_j,
    design_factor=1.0,
    evidence_ids=("wall-cp-record", "coolant-state-provider"),
)
minimum_mass_kg = estimate.minimum_hydrogen_mass_kg
```

For each segment, the wall duty is evaluated as

`m_wall * integral(cp_wall(T), T_target..T_initial)`.

If an initial contained-fluid mass is supplied, the helper adds
`m_fluid * (h_initial - h_target)`. The coolant mass follows from the retained
energy ledger divided by the declared positive coolant enthalpy rise. `design_factor`
scales that energy after the explicit additional heat term. The result retains
the ordered input segments, per-section duties, evidence IDs, and the final energy
and mass balance for inspection.

`LineCooldownEstimate.require_current()` recomputes the retained wall and
contained-fluid duties from the source callbacks and rejects changed results. Public
energy and coolant-mass properties invoke this check automatically before returning
their values. The provider-backed wrapper also invokes it when its coolant endpoint
states are checked. Callback state that changes internally but produces
identical values at the declared quadrature nodes and fluid endpoints cannot be
distinguished; callback provenance and validity remain the caller's responsibility.
The receipt also fingerprints the declared segment inputs, callback object identities,
per-segment duty rows, evidence IDs and energy/mass fields at construction; mutation of
those retained declarations or ledger fields is rejected as well.
The property path and provider-backed wrapper fingerprint the provider identity,
pressure/basis/phase/evidence declarations, endpoint temperatures and exact endpoint
states. Public results reject post-estimation edits to those bindings. The provider's
internal implementation is still checked by re-querying each endpoint state.

## Assumptions and boundary

- Endpoint temperatures and pressure for the contained fluid are selected by
  the caller; the callback must use a consistent enthalpy reference and physical
  phase model at both states.
- Solid heat capacity is integrated with fixed-order Gauss-Legendre quadrature.
  Increase `quadrature_order` until stable for the selected property function;
  this is not a quadrature error certificate.
- All coolant kilograms are assigned the same declared enthalpy rise. The output
  is therefore an ideal mass lower bound for that chosen endpoint rise, not a
  prediction of actual consumption.
- No axial distribution, transient pipe friction, pressure drop, film coefficient,
  fluid-wall temperature split, boiling/front propagation, two-phase flow,
  stratification, ambient transient, purge, vent or control logic is solved.
- `additional_heat_j` is an explicit user input; the module does not infer heat
  leak, purge mass, valve loss or operating reserve.

The formulation uses an enthalpy balance from the first law with caller-owned
property paths. It introduces no empirical cooldown correlation or copied
third-party implementation. The deferred metadata contract is
`line-cooldown-energy-bound` in `validation/cases/line_cooldown.py` and remains
unexecuted pending the designated verification campaign.
