# Native adsorption and bed coupling

The equation owner is [PSA-Dyna](https://github.com/lyullee/psa-dyna), reviewed MIT revision
`a26a8ef687c90cd4a5c18d38aaa4209ea5c5dcd6`. Install it separately for the native checks:

```powershell
.venv\Scripts\python -m pip install --no-deps --target artifacts/native_packages https://github.com/lyullee/psa-dyna/archive/a26a8ef687c90cd4a5c18d38aaa4209ea5c5dcd6.zip
.venv\Scripts\python scripts/check_psa_integration.py
.venv\Scripts\python scripts/check_psa_bed.py
```

## Equilibrium provider

`PsaDynaEquilibrium(native_equilibrium, native_material, basis, domain)` exposes the
structural `AdsorptionProvider` contract. The material is a separate native Python
dictionary; the adapter takes a deep copy. `material_parameters()` returns another copy
for inspection/customization. Changing the caller's original dictionary does not silently
change an existing provider's evidence.

`AdsorptionBasis` records material, species order, amount/mass basis, native engine and
parameter identity, references and `loading_definition`. The latter distinguishes absolute,
surface-excess and source-defined loadings. Signed excess values are allowed; negative
absolute loadings are rejected. `loading_working_capacity` subtracts compatible loadings
only and never invents free-gas, pore-volume or excess-to-absolute corrections.

The local interface takes component partial pressures in Pa. The installed native function
takes bar. Pressure derivatives are converted too: the native per-bar Jacobian is divided
by 100000. Result axes are species × site for loadings, site × output-species × input-species
for pressure derivatives and species × site for temperature derivatives. Missing native
derivatives remain None. The wrapper does not substitute fugacity for an empirical pressure
fit or synthesize a derivative.

Actual checks in `research/native_psa.md` compare nine native/adapter states and independently
perturb Pa and K inputs to check derivative conversion. Parameters are an authored synthetic
fixture, not a measured adsorbent fit. A successful adapter does not transfer every upstream
material's qualification to an arbitrary new material or temperature.

## Native bed snapshots and rates

`PsaDynaBed(native_bed, basis, domain, energy_reference_id=...)` exposes an actual native
loading-LDF Bed without reimplementing its equations. This level requires explicitly
absolute uptake. Partial-pressure-LDF pellet states have a different meaning and are not
silently relabeled as loadings.

`snapshot(state)` returns immutable gas component inventories, loadings, bed/wall T,
pressure Pa, composition, total native inventory and stored energy. Negative raw gas or
loading values are rejected before the native field function could floor them.
`rates(state, BedFaceTransfers(...))` delegates to the native RHS.

Face transfers contain one component molar-flow vector and enthalpy W per native cell face,
with an explicit species order and energy-reference ID. The orientation is positive
left-to-right at both boundary faces. Internal hydraulic fluxes and external boundary fluxes
must be supplied consistently by the composing solver; the adapter is not a PSA schedule.
The returned native derivative and ambient heat are available to that same Python solver.

The native constant-Cp or PR energy convention is not automatically a CoolProp energy
reference. A caller must align physical reference states before connecting enthalpy streams.
Changing an owned native Bed configuration invalidates its previous parameter/evidence
identity until the caller updates that identity and reruns relevant checks.

`research/native_psa_bed.md` records an actual closed warm uniform bed relaxation, including
component and total-energy residuals. This checks a kinetic/thermal boundary. It does not
verify axial transport, cyclic steady state, purity/recovery or independent experiments.

## Cryogenic extension

The current native Bed fields reject T≤100 K and T≥1000 K. The local wrapper preserves that
limitation. Lowering the bound alone would not provide valid low-T heat capacities, real-gas
fugacity, spin identity, free condensation or adsorption-energy accounting.
The concrete [extension request](../requests/005_psa_cryogenic_adsorption.md) is based on the
implemented local contracts and warm verification, with cryogenic acceptance evidence left open.
