# Native mixture saturation from mass quality

Status: **implemented_unverified**. This increment was written without running
property calculations, examples, or tests. Only source syntax and lint checks
are intended for the coding-first stage.

`CoolPropMixtureProperties.phase_partition_pq_mass()` resolves a supplied vapor
mass fraction at fixed absolute pressure. `phase_partition_tq_mass()` does the
same at fixed temperature. Both reuse the existing native PQ/TQ phase partition
and its component-mole balance admission. No equilibrium composition, caloric
property, EOS, or transport mixing rule is implemented locally.

CoolProp's mixture Q coordinate is a **mole** fraction. The existing phase
partition computes mass quality from the native liquid and vapor compositions
and their native molar masses. A scalar Brent inverse searches that actual
quantity, re-flashing each new mole-quality point. Freezing one pair of phase
compositions for the whole inverse would select a different state and is not
used here. The underlying native property APIs are described in the
[CoolProp mixture interface](https://coolprop.org/fluid_properties/Mixtures.html)
and [AbstractState API](https://coolprop.org/apidoc/CoolProp.AbstractState.html).

## Explicit branch and tolerances

Every inverse requires:

- `quality_bounds`: increasing native **mole**-quality bounds in `[0, 1]`;
- `component_mole_balance_tolerance`: existing native component balance gate;
- `mass_quality_absolute_tolerance`: final absolute mass-fraction residual gate;
- `quality_absolute_tolerance`: root tolerance in the native mole coordinate;
- `branch_evidence_id`: caller evidence identifying the selected phase branch.

`branch_samples` defaults to 9 and `maximum_iterations` to 100. All declared
samples must show strict monotonicity; any contradictory subsequent root sample
rejects the solve. A target outside the sampled endpoint range also rejects.
This is a bounded numerical admission, not a proof of global uniqueness or an
automatic choice among multiple phase-envelope branches. Native flash failures
propagate through `MixturePartitionInverseError`, which preserves completed native
evaluations and the available root result. There is no fallback EOS or clipping.

```python
# properties is a configured CoolPropMixtureProperties instance.
# pressure and bounds must belong to a caller-qualified native phase branch.
inverse = properties.phase_partition_pq_mass(
    pressure_pa,
    vapor_mass_fraction,
    quality_bounds=native_mole_quality_bounds,
    component_mole_balance_tolerance=component_tolerance,
    mass_quality_absolute_tolerance=mass_fraction_tolerance,
    quality_absolute_tolerance=mole_fraction_root_tolerance,
    branch_evidence_id=phase_branch_evidence_id,
)
partition = inverse.partition
actual_mass_quality = partition.vapor_mass_fraction
native_mole_quality = partition.vapor_mole_fraction
state = inverse.state
amounts = partition.split_mass(total_inventory_mass_kg)
```

`from h2physics.thermo import MixtureMassQualityInverse` exposes the result type.
`MixtureMassQualityInverse` retains target, actual residual, branch bounds,
fixed coordinate, native evaluations and root diagnostics. Its `require_current()`
rechecks the existing native partitions. The underlying state preserves native
`vapor_mole_fraction`; `state.vapor_mass_fraction` stays `None` to keep the
existing mixture-state contract. Read the derived mass fraction from the phase
partition, not from that base-state field.

## Existing saturation API

`saturated(P, q_mass)` and `saturated_at_temperature(T, q_mass)` still accept
zero/one endpoints without inverse configuration. For an interior mass fraction,
pass the same inverse keywords in a Python mapping as `mass_quality_options`.
For example:

```python
state = properties.saturated(
    pressure_pa, vapor_mass_fraction,
    mass_quality_options={
        "quality_bounds": native_mole_quality_bounds,
        "component_mole_balance_tolerance": component_tolerance,
        "mass_quality_absolute_tolerance": mass_fraction_tolerance,
        "quality_absolute_tolerance": mole_fraction_root_tolerance,
        "branch_evidence_id": phase_branch_evidence_id,
    },
)
```

Use the partition method when the derived mass quality or numerical diagnostics
must be retained. This extension provides one equilibrium state only; it does
not integrate a separator, establish stability beyond native admission, resolve
metastability or kinetics, or determine a critical-point branch.
