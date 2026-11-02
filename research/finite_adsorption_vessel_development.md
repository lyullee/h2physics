# Finite adsorption vessel development record

Date: 2026-10-28

Status: `implemented_unverified`; scientific execution deferred to Nurion.

## Decision

The existing `loading_working_capacity` intentionally excludes free gas because
neither pore volume nor a gas property owner is known there. A separate composition
was added rather than changing that safe narrow function. The composition calls the
existing adsorption and common thermodynamic interfaces and owns only finite-vessel
inventory arithmetic.

The first level uses a frozen, declared gas composition. This is narrower than a
full multicomponent discharge but makes density, molar-mass and loading bases
auditable. Absolute uptake is mandatory. No empirical conversion from surface
excess to absolute loading was invented.

## Invariants prepared for cluster execution

1. total component inventory equals free plus adsorbed inventory;
2. void volume uses all declared geometric exclusions exactly once;
3. charged-minus-discharged capacity retains separate phase contributions;
4. selected product delivery equals the selected entries of the signed vector;
5. species, adsorption basis, gas composition and property basis cannot drift;
6. excess-loading, invalid volume and non-gas/property endpoint paths reject.

Six deferred definitions are in `validation/cases/finite_adsorption_vessel.py`
under profile `finite-adsorption-vessel`. They have not been imported, discovered
or run. The example is authored input only and is not material qualification.

## Remaining evidence

- source-qualified absolute isotherms and skeletal/particle/packed densities;
- independent charged/discharged vessel inventories;
- mixture real-gas evidence where relevant;
- nonisothermal heat of adsorption and wall/bed dynamics;
- finite-rate mass transfer, pressure drop and delivery equipment;
- cyclic degradation, purity and minimum-delivery-pressure qualification.

No supplied-document prose, figures, tables, equations, code or references were
used. This record documents original integration over already reviewed repository
contracts.

