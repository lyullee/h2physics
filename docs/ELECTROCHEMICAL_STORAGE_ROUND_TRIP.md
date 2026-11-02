# Electrochemical hydrogen storage: metered electric round trip

`h2physics.adapters.electrochemical_round_trip` connects an already admitted
finite electrolysis trace, the existing finite fuel-cell trace, and their
`HydrogenInventoryHandoff`. It reports the charge-side and discharge-side
electrical meter totals on a caller-declared common boundary and energy basis,
alongside the native stack electricity ledgers and the associated H2 batch
ledger.

The measured electricity ratio is

`metered discharge electricity / metered charge electricity`.

This is an accounting result for the particular meter locations and operating
windows. A full-system ratio requires the caller's meters to include every
electricity import/export inside that boundary, including compression,
conditioning, auxiliaries, and power conversion that lie between the meters.
The API checks that the charge meter covers the entire producer trace, the
discharge meter covers the entire consumer trace, and the meter totals are
consistent with the stack-level electricity ledgers. It does not estimate
missing meter values or loss terms. The H2 receipt separately reports produced,
delivered, consumed, remaining and transfer-loss amounts.

## Python use

```python
from h2physics.adapters.electrochemical_hydrogen_handoff import (
    bind_electrolysis_to_fuel_cell,
)
from h2physics.adapters.electrochemical_round_trip import (
    ElectricalBoundaryMeter,
    account_electrochemical_storage_round_trip,
)

h2 = bind_electrolysis_to_fuel_cell(
    electrolyzer_trace,
    fuel_cell_trace,
    transfer_loss_mol=loss_mol,
    source_id=producer_source_id,
    sink_id=fuel_cell_inlet_id,
    transfer_evidence_id=transfer_evidence_id,
    conditioning_evidence_id=conditioning_evidence_id,
    closure_tolerance_mol=inventory_tolerance_mol,
)
result = account_electrochemical_storage_round_trip(
    h2,
    charge_meter=ElectricalBoundaryMeter(
        meter_id="charge-meter", system_boundary_id="plant-boundary",
        window_id="charge-window", clock_id=clock_id,
        energy_basis_id="AC-terminal-meter", evidence_id="charge-receipt",
        start_s=charge_start_s, end_s=charge_end_s,
        energy_j=measured_charge_j,
    ),
    discharge_meter=ElectricalBoundaryMeter(
        meter_id="discharge-meter", system_boundary_id="plant-boundary",
        window_id="discharge-window", clock_id=clock_id,
        energy_basis_id="AC-terminal-meter", evidence_id="discharge-receipt",
        start_s=discharge_start_s, end_s=discharge_end_s,
        energy_j=measured_discharge_j,
    ),
)
ratio = result.round_trip_electricity_ratio
```

The charge and discharge meter evidence must identify the integrated energy,
time window, common electrical basis and common system boundary. The values are
caller-supplied measurement inputs; this module does not inspect a meter file or
validate meter calibration. `ratio` is not constrained to be at most one: a
value above one signals that the declared boundary may include external energy
or that the readings are not comparable, and needs engineering review.

## Scope and limitations

- The producer and consumer must be the existing admitted finite-trace objects
  linked by an up-to-date hydrogen inventory handoff on one physical clock.
- The electrical boundary must use compatible charge and discharge bases. For
  example, comparing an electrolyzer DC input with a fuel-cell AC output does
  not yield an AC-to-AC plant ratio unless both readings have first been mapped
  to a declared common basis using evidence-backed conversions.
- A charge meter below the electrolyzer's accepted stack consumption or a
  discharge meter above the accepted fuel-cell electrical output is rejected.
- Heat, H2 chemical heating value, storage state of charge, compression work,
  standby periods, degradation, availability and annualized performance are
  not inferred. They are covered only when they affect caller-provided boundary
  meter totals or are separately analyzed.
- No design or safety qualification follows from this accounting API.

This system boundary is necessary because hydrogen storage round-trip results
depend on which conversion, compression, storage and power-electronics elements
are inside the measured chain. A U.S. DOE ARIES/Flatirons hydrogen-system report
describes an AC-to-DC electrolyzer, compression/storage, a fuel cell and DC-to-AC
conversion as one system and reports the particular test configuration's
measured performance; its values are not defaults or targets in this API.

## References

- U.S. Department of Energy, Hydrogen and Fuel Cell Technologies Office, *ARIES
  / Flatirons Facility – Hydrogen System Capability Buildout*, 2024. [Official
  project report](https://www.hydrogen.energy.gov/docs/hydrogenprogramlibraries/pdfs/review24/ta048_leighton_2024_o.pdf?sfvrsn=1bc055ce_3).
- U.S. DOE, *Energy Storage Analysis – Hydrogen Program*. [Program scope and
  pathway overview](https://www.hydrogen.energy.gov/program-areas/systems-analysis/energy-storage-analysis).
