# Native porous-gas membrane transport

`h2physics.adapters.cantera_membrane.CanteraDustyGasTransport` calls actual
Cantera3.2 `DustyGas.molar_fluxes`. It exposes coupled multicomponent, molecule-wall
Knudsen and pressure-driven Darcy transport beyond the existing pure-H/H₂ Fick
material level. Cantera owns the EOS, gas transport fits and coupled flux solve.
The host adds Python objects, SI conversion, identity and applicability checks.
No equivalent diffusion matrix solver or new EOS is implemented.

This is a two-point constitutive closure. It is not a solved finite membrane
profile, a finite-feed separator, a purity/recovery prediction or a thermal model.
It does not include adsorption, polymer solution-diffusion, swelling, reaction,
electrochemical transport, condensation or dense-gas membrane selectivity.

## Native gas and evidence

Construct the adapter with a callable returning a full, neutral, zero-reaction
native `cantera.Solution` with `thermo_model="ideal-gas"` and
`transport_model="multicomponent"`, a common `MechanismBasis`, and a
`MembraneTransportEvidence` object. The source factory may return a shared gas
object; the adapter never sets its state. The explicit evidence includes
transport source, gas phase, gas scope, energy reference and H₂ partition IDs.
A mechanism source SHA and license declaration do not experimentally qualify
transport data, ideal-gas accuracy or a membrane material.

The checked local native mechanism is installed `h2o2.yaml`, with an authored
H₂/N₂/Ar species selection. Its thermochemistry/transport originate in the native
GRI-Mech data and remain separately installed. No mechanism data or third-party
implementation is redistributed. Native code has BSD-3-Clause licensing; retain
the separately reviewed mechanism/transport attribution. Native YAML bytes can
be passed to `Species.list_from_yaml(..., section="species")`, avoiding the
native Windows filename lookup problem in this Korean-path workspace.

The existing audited `_private_native_phase` helper creates independent native
endpoint phases. Species thermo, bounds, molecular masses, transport data,
ordering and source definitions are audited. An additional transport-copy audit
compares binary diffusion, viscosity and collision-integral polynomial arrays.
Runtime fit changes that cannot survive regeneration are rejected; they are not
silently replaced by default fits. The recorded relative copy tolerance is2e-13.
Source and owned transport fingerprints remain separate. Subsequent calls reject
a changed source thermo/transport definition until a new adapter/evidence is bound.

## Python objects and units

`PorousTransportGeometry` requires every pore parameter explicitly:

| Field | Meaning and admissible range |
|---|---|
| `porosity` | dimensionless, strictly0<ε<1 |
| `tortuosity` | native dimensionless factor τ≥1; no squared convention is inferred |
| `mean_pore_radius_m` | positive mean pore radius, m |
| `permeability_m2` | explicit κ≥0, m²; zero disables the Darcy contribution |
| `thickness_m` | positive distance between left/right points, m |
| `geometry_id`, `evidence_id`, `origin` | declared geometry and parameter provenance |

Explicit κ avoids the native unset-permeability correlation. Negative/zero
thickness and invalid pore parameters are rejected before native setters are
called. Native setters themselves do not supply the required physical guards.

`MembraneEndpoint` declares T in K, P in Pa absolute, the complete native species
tuple, fractions as a NumPy-compatible vector, `composition_basis="mole"` or
`"mass"`, boundary/phase/geometry/source IDs and origin. Nonnegative fractions
must sum to1 within eight machine epsilons; no physical normalization or missing
species repair is performed. Native roundoff is checked and the original vector
is retained separately from native X/Y. The species tuple must exactly match the
native ordering. Distinct left/right boundary IDs share the admitted phase and
geometry identity; swapping their order changes the flux direction.

```python
from h2physics.adapters.cantera_membrane import (
    CanteraDustyGasTransport, MembraneEndpoint,
    MembraneTransportEvidence, PorousTransportGeometry,
)
from h2physics.core import Origin

# native_factory and basis are explicit, separately licensed native inputs.
evidence = MembraneTransportEvidence(
    "transport-source", "warm-gas", "neutral-ideal-gas-scope",
    "native-formation-enthalpy-reference", "H2-spin-unresolved")
model = CanteraDustyGasTransport(native_factory, basis, evidence=evidence)
pore = PorousTransportGeometry(
    .4, 3., 80e-9, 2e-16, .002, "porous-plane", "authored-geometry", Origin.SYNTHETIC)
left = MembraneEndpoint(
    360., 101325., ("H2", "N2", "AR"), [.65, .25, .1], "mole",
    "left", "warm-gas", "porous-plane", "authored-state", Origin.SYNTHETIC)
right = MembraneEndpoint(
    360., 101325., ("H2", "N2", "AR"), [.35, .55, .1], "mole",
    "right", "warm-gas", "porous-plane", "authored-state", Origin.SYNTHETIC)
result = model.flux(left, right, pore)
species_flux_mol_m2_s = result.molar_flux_mol_m2_s
```

These numbers are original verification inputs, not material coefficients.
Use qualified pore/transport data and endpoint conditions for research comparison.
The runnable installed-native setup is in `scripts/check_cantera_membrane.py`.

## Result, ownership and limitations

`MembraneFlux` retains actual source/endpoint native phases, the actual native
`DustyGas` object, raw native kmol/(m²·s), SI mol/(m²·s), signed kg/(m²·s), native
multicomponent matrix, molecular masses and immutable endpoint/mean snapshots.
The SI mol flux is exactly1000 times native flux; native kg/kmol masses are
converted to kg/mol before multiplying SI mol flux. The normal is left→right
relative to stationary porous solid. These are total species fluxes including
Darcy transport; they need not sum to zero, and some species can counterdiffuse.
Normalizing their signed sum into a product composition is invalid.
Native effective transport already includes porosity/tortuosity. A later device
area must use the corresponding bulk geometric cross section; multiplying by
an additional porosity factor would count it twice.

Input, phase and transport fingerprints retain species/phase/reference/source
and geometry identity. Result construction checks unit/array axes and input
fingerprints. Arrays are copied read-only. The retained native objects remain
mutable diagnostics: after return, changing a native object is not a qualified
update of the original immutable record. Native pore values are write-only,
so the adapter creates and sets a new private `DustyGas` for every calculation.
It never reuses a returned native object. Existing results and subsequent calls
survive mutations of earlier returned native pore settings or endpoint phases.

The initial domain is a caller-declared warm, neutral, single ideal gas with
strictly isothermal endpoints. The mechanism domain begins at≥200K and each
endpoint also stays inside the selected native thermo-fit intersection. This
does not prove single-phase or ideal-gas accuracy for arbitrary materials or
pressure. T gradients, thermal diffusion/transpiration and heat transfer are
outside this level. Native endpoint partial molar enthalpies in J/mol are retained
as reference diagnostics, with an explicit energy-reference ID. They are not a
thermal closure, heat duty or transported-energy ledger. H₂ spin is not resolved
by a generic native mechanism label.

`MembraneTransportError` preserves actual native objects, completed raw flux
(including nonfinite diagnostics), immutable native-state snapshots, endpoint
inputs, pore geometry, copy audits and the chained cause. There is no alternative
transport provider, result clipping or silent native-correlation fallback.

Before a finite separator can be composed, supply area, absolute clock,
feed/permeate/retentate inventories, local flux-to-inventory boundaries, compatible
species/enthalpy references, energy storage/boundaries and spatial refinement.
Finite inventories and energy conservation belong to that later composition.
Constitutive flux and numerical verification alone establish no recovery,
manufacturer selectivity, capacity or experimental validation.

## Verification and primary sources

The original checks cover zero gradient, endpoint reversal, inverse separation,
coupled inert counterflux, native mass/mol conversion, porosity/tortuosity scaling,
explicit Darcy addition, source/copy mutation, rejected runtime fit replacement,
invalid geometry/composition/identity and retained native failures. The Knudsen
oracle keeps an80nm pore fixed while lowering pressure. It is a mathematical
dilute-gas limit; it is not an experimental pore qualification. A subnormal pore
appears only in a negative numerical-failure test.

```powershell
.venv\Scripts\python -m pytest tests/test_cantera_membrane.py -q
.venv\Scripts\python -X utf8 scripts/check_cantera_membrane.py
```

See [the executed report](../research/native_membrane_transport.md) for source
hashes, measured runtime and limiting errors. The authoritative native contract
is [Cantera3.2 Python transport](https://cantera.org/3.2/python/transport.html#cantera.DustyGasTransport.molar_fluxes)
and the [native DustyGas mathematical description](https://cantera.org/3.2/cxx/dc/de6/classCantera_1_1DustyGasTransport.html).
The public code implements admission/units/composition; Cantera retains the
coupled transport equations and gas properties.
