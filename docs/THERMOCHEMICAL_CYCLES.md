# Finite staged thermochemical inventories

`thermochemical.FiniteThermochemicalCycle` composes supplied reaction extents,
finite carrier inventories, batch feeds, component withdrawals and prescribed
endpoint temperatures. It reuses `StoichiometricReaction.convert` and
`conversion_heat_j`; there is no additional reaction/kinetic ODE or equilibrium
solver. This is a constant-pressure enthalpy-budget reference level, not a
prediction of an achievable reactor cycle.

## Caloric and physical contracts

Inject the existing `MolarEnthalpyProvider`: ordered `ChemicalSpecies`, an
explicit `basis_id`, and `enthalpies_j_mol(T,P)`. Every stage reaction uses
exactly that complete species/phase order, with zero coefficients for unaffected
species. All amounts are mol, temperature K, pressure Pa absolute and enthalpy
J/mol. The property basis includes compatible formation/reference energies.
An unrelated sensible-energy zero does not establish a reaction heat.

The native gas/pure-solid provider described in MULTIPHASE_CALORIMETRY.md is
one optional implementation. A caller's `FunctionalMolarEnthalpy` can supply
other qualified phases. This level assumes additive species enthalpies that
depend only on T/P; mixture excess heat and composition-dependent partial
enthalpies require another supported provider/contract. A reused mutable
native output array is copied before another property evaluation can change it.
Nonfinite extensive properties, scales, budgets and residuals are rejected.

`ThermochemicalEvidence` declares process identity, additive-caloric,
component-withdrawal and thermal-boundary assumptions and resolved origin.
These declarations are evidence references, not automatic coefficient validation.
`ThermochemicalTolerances` controls independent element/mass/enthalpy budgets
and carrier/thermal closure. All limits remain explicit.

## Stage order and conservation

Each `ThermochemicalStage` has an identifier, contiguous start/end seconds,
one operation clock, endpoint temperature, supplied conversions and boundary
evidence. The operation order is:

1. Withdraw declared component moles from the previous inventory at its current T.
2. Add each declared finite feed with its own T, common pressure and caloric basis.
3. Condition the retained material and feeds to the stage endpoint T.
4. Apply each supplied reaction extent using the existing finite reaction core.

A feed in step2 cannot fund an excessive pre-withdrawal in step1. Component
takeoff is an imposed boundary, not a predicted separator or an assertion of
free separation work. Use another stage for a later takeoff. A stage without
conversions is an explicit thermal/transfer operation. An empty inventory has
no predicted endpoint T and is rejected. Time windows cannot overlap or leave
an unmodeled gap; no residence-time or conversion-rate law is inferred.

Conditioning heat is the sum of retained-material and feed enthalpy changes
to the endpoint T. Reaction heat is the existing caloric function at that T.
The independent stage ledger checks:

`H_after - H_before = H_feed - H_withdrawn + Q_required`.

Positive Q requires heat input; negative Q requires removal. Pressure is fixed
throughout and no non-PV shaft/electrical work is supplied. Enthalpy includes
the relevant constant-P energy convention; this is not a fixed-volume U model.
Feed pressure mismatch is rejected without inventing a compressor or a work
correction. A declared stage duration gives mean required W, not a furnace
power trajectory, heat-transfer area or a native device rating.

## Python construction

First create a qualified caloric provider as shown in MULTIPHASE_CALORIMETRY.md.
For its Fe3O4/FeO/H2O/H2/O2 mapping:

```python
from h2physics.core import Origin
from h2physics.reactions import StoichiometricReaction
from h2physics.thermochemical import (
    FiniteThermochemicalCycle, PrescribedConversion, ThermochemicalEvidence,
    ThermochemicalFeed, ThermochemicalInventory, ThermochemicalStage,
)

reduction = StoichiometricReaction("reduction", caloric.species, (-1,3,0,0,.5))
oxidation = StoichiometricReaction("steam-oxidation", caloric.species, (1,-3,-1,1,0))
initial = ThermochemicalInventory({"Fe3O4": 1.}, 300., 101325., caloric.basis_id)
steam = ThermochemicalFeed(
    ThermochemicalInventory({"H2O": .1}, 500., 101325., caloric.basis_id),
    "authored-steam-feed", Origin.SYNTHETIC)
stages = (
    ThermochemicalStage("reduce", 100., 110., "clock", 1400.,
        (PrescribedConversion(reduction,.1,"authored-extent"),), "authored-stage"),
    ThermochemicalStage("oxidize", 110., 120., "clock", 900.,
        (PrescribedConversion(oxidation,.1,"authored-extent"),), "authored-stage",
        feeds=(steam,), pre_withdrawal_mol={"O2": .05}),
    ThermochemicalStage("reset", 120., 130., "clock", 300., (), "authored-stage",
        pre_withdrawal_mol={"H2": .1}),
)
model = FiniteThermochemicalCycle(caloric, ThermochemicalEvidence(
    "authored-cycle", "additive-native-phase-enthalpy", "imposed-component-takeoff",
    "constant-P-required-heat-without-nonPV-work", Origin.SYNTHETIC))
trace = model.run(initial, stages, carrier_species=("Fe3O4", "FeO"),
                  require_full_inventory_closed=True)
```

These temperatures, extents, clocks and the provider example's solid densities
are authored calorimetry fixtures. They are inside the selected native fit
range, which does not prove reduction equilibrium, phase stability, kinetics
or the feasibility of operating this iron cycle at those conditions. Replace
the inputs with source-qualified operating/phase/volume evidence for research.

## Results, closure and failures

`ThermochemicalTrace` retains the actual supplied provider, shared conversion
objects, all before/after inventories, incoming/outgoing moles and enthalpies,
conditioning/reaction/net duty, element and mass defects and clocked steps.
Array snapshots are read-only. `gross_heat_input_j` and
`gross_heat_rejection_j` preserve the positive and negative stage duties;
their difference is the signed net heat. No recovery fraction or heat-exchanger
credit is invented. Serial stages do not automatically exchange heat across time.

Carrier-composition, endpoint-temperature and complete-inventory closure are
separate flags. By default the selected nonempty carrier inventory and T must
return. `require_full_inventory_closed=True` also requires every tracked amount
to return. A diagnostic finite campaign can explicitly waive carrier/T closure;
its flags remain false and do not establish a periodic plant state. The first
level does not compute solar efficiency, vacuum/compression work, optical loss,
heat storage/recovery or a utility's ability to provide the required duty.

`ThermochemicalCycleError` preserves the active stage and previous state,
completed steps, partial shared conversions, a completed failed-step/trace
when available, provider and original cause. Finite exhaustion, pre-overdraw,
caloric/phase/reference failure and failed closure are not clipped or repaired
by inventing an input, stopping a clock or resetting the carrier.

## Verification and sources

Run `python -m pytest tests/test_thermochemical.py` and
`python scripts/check_thermochemical_cycle.py` with the chemistry extra for
actual native calorimetry. The report in
[research/thermochemical_cycle.md](../research/thermochemical_cycle.md) checks
finite oxide/steam loops, independent fresh-native Mixture enthalpy for each
stage, actual hot-product/cold-feed energy, finite extent scaling, and retained
nonclosure/depletion. Functional checks include an analytic heat ledger,
element-reference gauge shifts, heat-only stages, reused property buffers and
overflow rejection. Numerical verification is separate from apparatus/material
validation or reaction-yield identification.

Public context: [DOE thermochemical cycles](https://www.energy.gov/cmei/fuels/hydrogen-production-thermochemical-water-splitting),
[native NASA thermochemistry provenance](https://ntrs.nasa.gov/citations/19940013151)
and [Cantera properties](https://cantera.org/3.2/python/thermo.html).
The original composition and fixtures include no published coefficient arrays,
operating tables, figures, source implementation or worked example.
