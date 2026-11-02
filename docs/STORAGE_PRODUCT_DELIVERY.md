# Adsorption vessel delivery mass-flow adapter

`AdsorptionProductMassFlow` connects the existing finite adsorption-vessel
endpoint ledger to equipment interfaces that consume component mass or average
mass rate. It does not add a second storage model.

The caller supplies the accepted `AdsorptionVesselDelivery`, molar masses in the
ledger's exact species order, and a positive elapsed interval in seconds. The
adapter computes, component by component,

```text
mass change [kg] = signed mole change [mol] * molar mass [kg/mol]
average rate [kg/s] = mass change [kg] / elapsed interval [s]
```

The chosen product set is inherited from the original delivery receipt; its
delivered product mass and interval-average rate are sums over those species.
Signed changes remain visible for every component, including negative
non-product changes caused by competitive displacement. The arrays are
read-only. Species order mismatch, nonpositive molar masses, and invalid
intervals are rejected.

Before reusing a stored projection downstream, call `require_current()`. It
rechecks the issuing delivery and the sealed component/product mass and rate
ledgers, and raises if either the source receipt or projection was changed.

This quotient is an interval-average boundary quantity. It does not describe
when flow occurred inside the interval, predict valve or compressor behavior,
or establish a material's measured capacity. Callers needing transient
equipment coupling must retain the native time history from an independently
qualified dynamic owner. The contract is registered for deferred cluster
execution and remains `implemented_unverified` until then.
