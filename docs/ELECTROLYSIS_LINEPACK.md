# PV-electrolysis batch to pipeline linepack

## Native execution checkpoint — 2026-11-01

The native and explicit analytical cases both passed in the local
`h2physics-py312` environment after the ledger-value sealing fix. The authored
production trace delivered 0.02623012201575 mol (0.00005287677836911 kg) over
160–170 s. Native linepack pressure rose from 10,000 Pa to
11,300.6308741117 Pa at 298.15 K. Direct CoolProp endpoint inventory energies
gave a 142.8516765963 J storage change; the signed energy residual was 0 J and
mass residual was 2.71e-20 kg. Loss, clock, energy-reference, nonclosing energy,
receipt reissue and native EOS mutation gates passed. A balanced nested-ledger
mutation (+100 J source enthalpy, -100 J conditioning) was rejected in both
routes; restoring the original values restored receipt currentness. Scoped
Ruff passed. These are native integration and accounting tests with authored
conditions, not independent process-data or facility qualification.

`h2physics.adapters.charge_linepack_from_electrolysis(initial, producer, ...)`
maps one accepted net hydrogen production interval from `PVElectrolysisTrace`
to an existing `RealGasLinepackState` with CoolProp HEOS, or an explicitly
selected analytical `IsothermalLinepackState`. The return value is
an `ElectrolysisLinepackCharge` receipt with the final linepack state, mass
ledger, H2 amount, pressure margin and explicit boundary evidence.

The receipt also carries an `ElectrolysisSourceWithdrawalLedger` that reconciles
initial source H2, post-production stock, available batch, withdrawn amount,
transfer loss, delivered amount, retained batch and post-transfer source H2
moles. This is caller-evidenced stock accounting only: the original producer
trace is unchanged, and no post-transfer EOS pressure or temperature state is
calculated.

The transfer window is separate from production. It starts at or after the
producer's accepted end time, and the linepack's initial clock must equal the
declared transfer start. The adapter checks the same H2 molar-mass basis, a
neutral gaseous product, and caller-evidenced minimum source pressure and
temperature bounds over the transfer window. The pressure lower bound must
exceed the calculated final linepack pressure by the caller's margin, while the
temperature bounds must fit the isothermal receiving temperature tolerance. A
caller-declared molar loss is subtracted before the linepack mass ledger is
advanced. `require_current()` replays the producer admission and reconstructs
the receipt values from retained inputs.

The receipt also includes a caller-signed energy ledger tied to the transferred
mass. The caller supplies the integrated source transfer enthalpy from its
selected source state path, source and linepack reference IDs, signed reference
offset, conditioning energy and linepack energy change. The ledger checks
`H_transfer + E_reference_offset + E_conditioning - ΔE_linepack = 0` within
caller tolerances. The source reference must equal the accepted producer
`ThermoState` basis; a different linepack reference needs explicit mapping
evidence. For the native real-gas route the declared linepack reference must be
the retained CoolProp reference. The adapter independently checks the declared
storage change against `m_final*u_final - m_initial*u_initial`, using native
endpoint states and the existing owner pressure/density relation. It retains
the producer's fluid/spin identity and native method/object definitions. This
does not calculate the source path enthalpy, transfer pressure history, or
heat-transfer response. The legacy analytical route retains caller-declared
storage energy. Nested energy and source ledgers are sealed by their scalar
values so balanced post-issue edits cannot change their evidence unnoticed.

```python
from h2physics.adapters import charge_linepack_from_electrolysis

receipt = charge_linepack_from_electrolysis(
    linepack_initial_state,
    accepted_electrolysis_trace,
    source_withdrawal_mol=withdrawal_mol,
    source_removal_evidence_id="source-stock-removal-record",
    transfer_loss_mol=0.0,
    clock_id="plant-clock-v1",
    transfer_start_s=production_trace.final.time_s,
    transfer_end_s=production_trace.final.time_s + 10.0,
    minimum_source_pressure_margin_pa=50_000.0,
    minimum_source_pressure_during_transfer_pa=source_pressure_lower_bound_pa,
    source_temperature_bounds_k=(source_temperature_min_k, source_temperature_max_k),
    temperature_tolerance_k=1e-5,
    time_mapping_evidence_id="production-to-pipeline-clock-map",
    hydrogen_basis_evidence_id="verified-product-H2-basis",
    pressure_boundary_evidence_id="source-pressure-boundary-record",
    isothermal_boundary_evidence_id="linepack-temperature-boundary-record",
    transfer_boundary_evidence_id="finite-batch-transfer-record",
    source_transfer_state_evidence_id="source-window-state-evidence",
    source_energy_reference_id=product_state.basis.reference_id,
    linepack_energy_reference_id="caller-declared-linepack-reference",
    reference_mapping_evidence_id="signed-reference-mapping-record",
    boundary_energy_evidence_id="linepack-energy-boundary-record",
    reference_offset_j=0.0,
    conditioning_energy_j=conditioning_energy_j,
    source_transfer_enthalpy_j=integrated_source_transfer_enthalpy_j,
    linepack_energy_change_j=independently_calculated_linepack_energy_change_j,
    absolute_energy_tolerance_j=1e-6,
    relative_energy_tolerance=1e-10,
)
receipt.require_current()
print(receipt.final.pressure_pa, receipt.ledger.mass_residual_kg)
```

This boundary applies only if caller-evidenced pressure and temperature bounds
are compatible with the receiving isothermal linepack over the separate transfer
window. It does not calculate compressor work, valve flow, pressure loss, pipe
friction, source-path enthalpy, heat transfer, or a time-varying thermal
response. It does not calculate the caller-declared linepack energy change or
internal energy, or establish full plant energy closure,
equipment capacity, measured performance, or independent validation. The
source stock receipt does not mutate the producer trace or calculate its
post-transfer thermodynamic state. The
underlying linepack equation and its limitations are described in
[`PIPELINE_LINEPACK.md`](PIPELINE_LINEPACK.md); the producer interface and
source/caloric boundary are documented in [`PV_ELECTROLYSIS.md`](PV_ELECTROLYSIS.md).

Deferred contract: `pv-electrolysis-isothermal-linepack-charge-handoff` under
the `pv-electrolysis` Hangang profile. The case is registered and has not run.
