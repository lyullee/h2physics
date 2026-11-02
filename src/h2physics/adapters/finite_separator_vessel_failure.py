"""Project accepted pure-H2 separator pressure states to HELPR vessel history."""

from __future__ import annotations

from collections.abc import Callable, Sequence

from ..core import ThermoState, finite
from .finite_separator import FiniteSeparatorTrace
from .vessel_failure import Origin, VesselFailureContext, VesselFailureHistory, VesselLoading


def history_from_finite_separator(
    trace: FiniteSeparatorTrace,
    *,
    context: VesselFailureContext,
    wall_temperature_k: Sequence[float],
    external_pressure_pa_absolute: Callable[[float], float],
    shell_id: str,
    wall_mapping_evidence_id: str,
    geometry_mapping_evidence_id: str,
    pressure_basis_id: str,
    pressure_basis_evidence_id: str,
    external_pressure_evidence_id: str,
    reconstruction_evidence_id: str,
) -> VesselFailureHistory:
    """Bind accepted separator P/T/time samples to the existing HELPR input.

    The separator supplies fluid absolute pressure and phase temperatures, not
    a wall-temperature field. Wall temperatures, external pressure, shell
    identity/geometry mapping, and clock evidence remain caller-owned. No
    interpolation, pressure conversion, shell heat transfer, or failure
    criterion is added.
    """
    if type(trace) is not FiniteSeparatorTrace or type(context) is not VesselFailureContext:
        raise TypeError("Use an issued finite-separator trace and typed HELPR context")
    trace.require_current()
    if context.origin is Origin.MEASURED:
        raise ValueError("A computed separator simulation cannot be relabeled as measured history")
    if context.clock_id != trace.clock_id:
        raise ValueError("Separator and vessel-history clocks must match exactly")
    if context.hydrogen_mole_fraction != 1.0:
        raise ValueError("The admitted finite separator is pure hydrogen; mixture relabeling is forbidden")
    if pressure_basis_id != "Pa_absolute":
        raise ValueError("HELPR loading requires an explicit Pa_absolute pressure basis")
    if not callable(external_pressure_pa_absolute):
        raise TypeError("Supply external absolute pressure at each accepted sample")
    for label, value in (
        ("shell identity", shell_id), ("wall mapping", wall_mapping_evidence_id),
        ("geometry mapping", geometry_mapping_evidence_id),
        ("pressure-basis", pressure_basis_evidence_id),
        ("external-pressure", external_pressure_evidence_id),
        ("history reconstruction", reconstruction_evidence_id),
    ):
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"Explicit {label} evidence identity is required")
    if shell_id.strip() != context.wall_region_id:
        raise ValueError("Declared shell identity must match the HELPR wall region")
    if wall_mapping_evidence_id.strip() != context.wall_temperature_evidence_id:
        raise ValueError("Wall mapping evidence must match the failure-context temperature evidence")
    if geometry_mapping_evidence_id.strip() != context.geometry_binding_evidence_id:
        raise ValueError("Geometry evidence must match the HELPR geometry binding")
    if trace.material_species_id not in {"H2:normal", "H2:para", "H2:ortho"}:
        raise ValueError("Only an explicitly identified pure-hydrogen separator trace is supported")

    points = tuple(trace.points)
    times = tuple(finite(point.time_s, "accepted separator time") for point in points)
    walls = tuple(finite(value, "mapped shell wall temperature K", positive=True)
                  for value in wall_temperature_k)
    if len(times) < 2 or len(walls) != len(times):
        raise ValueError("Provide one wall temperature for every accepted separator sample")
    if any(right <= left for left, right in zip(times[:-1], times[1:])):
        raise ValueError("Accepted separator times must strictly increase")
    basis = points[0].liquid.basis
    expected_source = (f"finite-separator:{trace.material_species_id}:"
                       f"{basis.reference_id}:{trace.native_provenance.package_sha256}")
    if context.source_id != expected_source:
        raise ValueError("HELPR source identity must bind separator material, property basis and native source")
    context.fluid_basis.require_compatible(basis)

    samples = []
    for time_s, point, wall_k in zip(times, points, walls, strict=True):
        if (point.time_s != time_s or type(point.liquid) is not ThermoState
                or type(point.vapor) is not ThermoState):
            raise ValueError("Separator accepted rows must retain exact typed liquid/vapor states")
        context.fluid_basis.require_compatible(point.liquid.basis)
        context.fluid_basis.require_compatible(point.vapor.basis)
        if (point.liquid.pressure_pa != point.vapor.pressure_pa
                or point.liquid.pressure_pa <= 0.0):
            raise ValueError("Separator phase states do not share one valid absolute vessel pressure")
        external = finite(external_pressure_pa_absolute(time_s),
                          "external absolute pressure Pa", positive=True)
        if external >= point.liquid.pressure_pa:
            raise ValueError("HELPR history route requires internal pressure above external pressure")
        samples.append(VesselLoading(
            time_s, point.liquid.pressure_pa, external, wall_k,
            trace.material_species_id, point, point.native_state, point.liquid,
            (trace, shell_id.strip(), wall_mapping_evidence_id.strip(),
             geometry_mapping_evidence_id.strip(), pressure_basis_id,
             pressure_basis_evidence_id.strip(), external_pressure_evidence_id.strip()),
        ))
    trace.require_current()
    return VesselFailureHistory(context, tuple(samples), reconstruction_evidence_id.strip(), trace)


__all__ = ["history_from_finite_separator"]
