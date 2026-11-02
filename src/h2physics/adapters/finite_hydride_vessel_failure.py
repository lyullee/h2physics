"""Evidence-gated projection of a finite-hydride gas trace to vessel loading.

This module maps accepted gas pressure samples to the existing HELPR history
contract. It does not infer shell temperatures from hydride solid temperature
or calculate a failure criterion.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
import math

from ..storage.finite_hydride import FiniteHydrideTrace
from .vessel_failure import (
    Origin, VesselFailureContext, VesselFailureHistory, VesselLoading,
)


def history_from_finite_hydride(
    trace: FiniteHydrideTrace,
    *,
    context: VesselFailureContext,
    wall_temperature_k: Sequence[float],
    external_pressure_pa_absolute: Callable[[float], float],
    shell_id: str,
    wall_mapping_evidence_id: str,
    geometry_mapping_evidence_id: str,
    reconstruction_evidence_id: str,
) -> VesselFailureHistory:
    """Project accepted pure-H2 gas states into an existing failure history.

    Wall temperatures are explicit caller data aligned one-for-one to trace
    times. ``FiniteHydrideSnapshot.solid_temperature_k`` is deliberately not
    treated as a metal-shell temperature. Geometry, material law and failure
    mechanics remain owned by the HELPR consumer.
    """
    if type(trace) is not FiniteHydrideTrace or type(context) is not VesselFailureContext:
        raise TypeError("Use an issued FiniteHydrideTrace and typed failure context")
    trace.require_current()
    if context.origin is Origin.MEASURED:
        raise ValueError("A computed hydride simulation cannot be relabeled as measured history")
    if context.clock_id != trace.clock_id:
        raise ValueError("Hydride and vessel-history clock identities must match exactly")
    if context.source_id != trace.gas_thermodynamics.source_id:
        raise ValueError("Failure context must identify the exact retained hydrogen EOS source")
    if context.hydrogen_mole_fraction != 1.0:
        raise ValueError("Finite hydride trace represents pure H2; mixture relabeling is forbidden")
    context.fluid_basis.require_compatible(trace.gas_thermodynamics.basis)
    for label, value in (("shell identity", shell_id),
                         ("wall mapping", wall_mapping_evidence_id),
                         ("geometry mapping", geometry_mapping_evidence_id),
                         ("history reconstruction", reconstruction_evidence_id)):
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"Explicit {label} evidence identity is required")
    if shell_id.strip() != context.wall_region_id:
        raise ValueError("Declared shell identity must match the HELPR wall region")
    if wall_mapping_evidence_id.strip() != context.wall_temperature_evidence_id:
        raise ValueError("Wall mapping evidence must match the failure-context temperature evidence")
    if geometry_mapping_evidence_id.strip() != context.geometry_binding_evidence_id:
        raise ValueError("Geometry evidence must match the HELPR vessel geometry binding")
    times = tuple(float(value) for value in trace.time_s)
    walls = tuple(float(value) for value in wall_temperature_k)
    if len(times) < 2 or len(walls) != len(times):
        raise ValueError("Provide one wall temperature for every accepted time sample")
    if any(not math.isfinite(value) or value <= 0.0 for value in walls):
        raise ValueError("Mapped wall temperatures must be finite positive kelvin values")
    if any(sample.time_s != time for sample, time in zip(trace.snapshots, times, strict=True)):
        raise ValueError("Snapshot clock coordinates differ from the accepted trace axis")
    trace.gas_thermodynamics.basis.require_compatible(context.fluid_basis)

    samples = []
    for time, snapshot, wall_k in zip(times, trace.snapshots, walls, strict=True):
        gas = snapshot.gas
        trace.gas_thermodynamics.basis.require_compatible(gas.basis)
        # Re-evaluate the retained EOS at each accepted P,T point to detect a
        # changed provider binding before the history is consumed.
        external = float(external_pressure_pa_absolute(time))
        samples.append(VesselLoading(
            time, gas.pressure_pa, external, wall_k, gas.phase,
            snapshot, gas, gas, (trace, shell_id.strip(),
                                 wall_mapping_evidence_id.strip(),
                                 geometry_mapping_evidence_id.strip()),
        ))
    return VesselFailureHistory(
        context, tuple(samples), reconstruction_evidence_id.strip(), trace,
    )
