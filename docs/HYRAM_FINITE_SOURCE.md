# HyRAM steady jet to finite source

`h2physics.adapters.hyram_jet_source.project_hyram_jet_to_finite_source()` maps an
already admitted `HyRAMJetRun` onto the shared `IntervalMassSource` Python type for a
caller-declared clock window. This lets downstream physical components consume the
same typed source object used by other native equipment models.

The caller supplies the start and end times, state at the source plane, evidence for
that state, source origin, and termination meaning. The interval mass is the admitted
HyRAM hydrogen flow multiplied by the declared steady duration. The API retains the
upstream and projected enthalpy flow separately and reports their difference. It does
not tune the native opening or flow, change the source state, or repair a rejected
Gaussian-entry mass discrepancy. A failed energy gate raises
`HyRAMFiniteSourceError`, whose `projection` property retains the rejected diagnostic.

```python
projection = project_hyram_jet_to_finite_source(
    admitted_jet,
    start_s=0.0,
    end_s=30.0,
    clock_id="plant-clock",
    source_state=upstream_state,
    source_state_evidence_id="leak-state-study-03",
    origin=Origin.PREDICTED,
    end_reason="isolation",
)
finite_source = projection.source
projection.require_current()
```

The source state must use the same hydrogen/property-reference basis as the HyRAM
upstream state. A downstream receiving solver still owns any later pressure, phase,
temperature or clock evolution; none is inferred from the steady jet. The finite source
is an interval-average representation and does not resolve source transients. It carries
the jet location and clock identity. Do not convert a diagnostic or rejected HyRAM run
into a preferred-provider prediction.

## Explicit gas-component flow handoff

For a downstream model that requires an explicit mixture mass basis, use the
existing `GasComposition` algebra without inventing an entrainment correlation:

```python
component_flow = projection.component_flow(gas_composition)
component_flow.require_current()
```

The composition must name `H2` and provide molar masses. Its caller-declared H2
mass fraction sets total mixture flow so the H2 component is exactly the admitted
HyRAM mass flow. Every other component is an explicit caller input, not inferred
from HyRAM centerline concentration or ambient-air entrainment. The returned
component mass-flow vector retains the composition's species order and is
read-only. Mixture thermodynamic properties and source-plane state remain the
responsibility of a separately selected EOS/property path; this composition-only
handoff does not fabricate a mixed `ThermoState`.

`validation/cases/hyram_finite_source.py` describes a synthetic deferred contract for
mass integration, enthalpy projection rejection, explicit mixture component allocation
native-boundary mutation, and the immutability of the captured centreline snapshot.
The snapshot uses immutable backing storage: callers cannot re-enable NumPy writes to
change data covered by the admission receipt. The deferred case has not
been run. No native HyRAM calculation, scientific validation or Nurion submission was
performed for this API.


HyRAMJetRun receipts are issued only by the checked run_hyram_gas_jet() boundary.
Reconstructing a mass-flux-consistent centerline from a caller-created object does
not establish native execution provenance. One-use issuance prevents fabricated
native-like records from entering the finite-source handoff.
