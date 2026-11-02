"""Explicit deposited-stock continuation through the reviewed native pool owner.

This uses cumulative native evaporation rather than instantaneous heat flux to
construct conservative vapor bins. The separately declared pool substrate is
not a continuation of the finite impact wall's thermal inventory.
"""

from dataclasses import dataclass, field
from typing import Any

import numpy as np

from ..core import Origin, finite
from ..sources import IntervalMassSource
from .droplet_impact import NativePoolInitialization, prepare_native_fixed_area_pool
from .result_provenance import recorded_content_sha256


class ParcelPoolChainError(RuntimeError):
    def __init__(self, cause, initialization, native_result=None):
        super().__init__(str(cause))
        self.cause = cause
        self.initialization = initialization
        self.native_result = native_result


@dataclass(frozen=True, slots=True)
class ParcelPoolContinuation:
    initialization: NativePoolInitialization
    native_result: Any
    vapor_source: IntervalMassSource
    mass_residuals_kg: tuple[float, ...]
    absolute_times_s: tuple[float, ...]
    finite_patch_thermal_continuation_solved: bool = False
    status: str = "implemented_unverified"
    _binding: tuple = field(default=(), init=False, repr=False, compare=False)

    def _payload(self):
        return (id(self.initialization), id(self.native_result), id(self.vapor_source),
                recorded_content_sha256(self.initialization), recorded_content_sha256(self.native_result),
                self.mass_residuals_kg, self.absolute_times_s,
                self.finite_patch_thermal_continuation_solved, self.status)

    def require_current(self):
        if not self._binding or self._payload() != self._binding:
            raise ValueError("Pool continuation must retain its original issuing run and results")
        initial = self.initialization
        initial.impact_owner.require_original_step(initial.impact_step)
        self.vapor_source.require_current()
        rows = tuple(self.native_result.ledger)
        if len(rows) != len(self.absolute_times_s):
            raise ValueError("Native pool output count changed after continuation")
        cumulative = tuple(float(row.cumulative_evaporation_kg) for row in rows)
        if not cumulative or cumulative[0] != 0.:
            raise ValueError("Initial-stock continuation must start before any pool evaporation")
        if not np.array_equal(np.diff(cumulative), self.vapor_source.mass_kg):
            raise ValueError("Native cumulative evaporation changed after source construction")
        for row, time, residual in zip(rows, self.absolute_times_s, self.mass_residuals_kg, strict=True):
            current = initial.batch.mass_kg-row.liquid_mass_kg-row.cumulative_evaporation_kg
            if (row.time_s != time-initial.absolute_start_s or current != residual
                    or row.cumulative_inflow_kg != 0.):
                raise ValueError("Native initial-stock ledger changed after continuation")
        return self

    def quasi_steady_dispersion(self, **slab_options):
        """Run explicitly independent preferred SLAB snapshots from this vapor."""
        return run_parcel_pool_dispersion(self, **slab_options)

    def fire_seed(self, *, evidence_id, ignition_transition_evidence_id,
                  temperature_absolute_tolerance_k, density_relative_tolerance):
        """Hand exact final unburned stock to the existing conditional fire owner."""
        from .pool_fire import PoolFireSeed
        self.require_current()
        return PoolFireSeed.from_deposited_pool(
            self, evidence_id=evidence_id,
            ignition_transition_evidence_id=ignition_transition_evidence_id,
            temperature_absolute_tolerance_k=temperature_absolute_tolerance_k,
            density_relative_tolerance=density_relative_tolerance,
        )


@dataclass(frozen=True, slots=True)
class ParcelPoolDispersion:
    continuation: ParcelPoolContinuation
    dispersion: Any
    plume_memory_included: bool = False
    status: str = "implemented_unverified"
    _binding: tuple = field(default=(), init=False, repr=False, compare=False)

    def require_current(self):
        if self._binding != (id(self.continuation), id(self.dispersion)):
            raise ValueError("Dispersion receipt must retain its original issuing objects")
        self.continuation.require_current()
        if self.dispersion.source is not self.continuation.vapor_source:
            raise ValueError("SLAB snapshot series belongs to a different vapor source")
        if self.plume_memory_included or self.dispersion.plume_memory_included:
            raise ValueError("Independent SLAB snapshots cannot claim plume memory")
        guard = getattr(self.dispersion, "require_current", None)
        if callable(guard):
            guard()
        return self

    @property
    def accepted(self) -> bool | None:
        """Forward the child SLAB aggregate gate without hiding diagnostic runs.

        ``None`` is preserved when the series has no positive-mass snapshot;
        ``False`` remains visible when any requested snapshot failed its gate.
        """
        self.require_current()
        value = self.dispersion.all_snapshots_accepted
        if value is not None and type(value) is not bool:
            raise TypeError("SLAB aggregate acceptance must be bool or None")
        return value


class ParcelPoolDispersionError(RuntimeError):
    def __init__(self, cause, continuation, dispersion=None):
        super().__init__(str(cause))
        self.cause = cause
        self.continuation = continuation
        self.dispersion = dispersion
        self.result = dispersion if dispersion is not None else getattr(cause, "result", None)


def run_parcel_pool_dispersion(continuation: ParcelPoolContinuation, **slab_options):
    """Compose native pool evaporation with preferred independent SLAB slices.

    All native SLAB objects, atmospheric conditions, source footprint and solver
    options must be supplied through the existing keyword interface. This does
    not evolve a plume between intervals or infer its ground footprint.
    """
    from ..dispersion import HydrogenReleaseFamily, run_preferred_lh2_quasi_steady_slices

    if type(continuation) is not ParcelPoolContinuation:
        raise TypeError("Use the original deposited-stock pool continuation")
    if "source" in slab_options or "family" in slab_options:
        raise ValueError("Source and LH2 origin are bound by the pool continuation")
    dispersion = None
    try:
        continuation.require_current()
        dispersion = run_preferred_lh2_quasi_steady_slices(
            HydrogenReleaseFamily.LIQUID_HYDROGEN_ORIGIN,
            source=continuation.vapor_source, **slab_options,
        )
        continuation.require_current()
        result = ParcelPoolDispersion(continuation, dispersion)
        object.__setattr__(result, "_binding", (id(continuation), id(dispersion)))
        return result.require_current()
    except Exception as cause:
        raise ParcelPoolDispersionError(cause, continuation, dispersion) from cause


def run_deposited_batch_pool(step, native_config, *, impact_owner,
                             separate_continuation_heat_owner,
                             continuation_evidence_id, reference_properties,
                             vapor_location, output_times_s,
                             absolute_mass_tolerance_kg=1e-10,
                             relative_mass_tolerance=1e-8):
    """Continue one admitted deposited batch over explicit absolute-clock edges.

    The config declares fixed footprint, substrate, thermal age and heat cap.
    No arrival duration, deposited fraction or surface heat is inferred.
    """
    initialization = prepare_native_fixed_area_pool(
        step, native_config, impact_owner=impact_owner,
        separate_continuation_heat_owner=separate_continuation_heat_owner,
        continuation_evidence_id=continuation_evidence_id,
    )
    native = None
    try:
        times = tuple(finite(value, "output time") for value in output_times_s)
        if (len(times) < 2 or times[0] != initialization.absolute_start_s
                or any(b <= a for a, b in zip(times, times[1:]))):
            raise ValueError("Pool edges must start at contact end on the original absolute clock")
        batch = initialization.batch
        if batch.mass_kg <= 0.:
            raise ValueError("Initial-stock continuation needs positive deposited liquid")
        if (vapor_location.clock_id != initialization.clock_id
                or vapor_location.coordinate_frame_id != batch.location.coordinate_frame_id
                or vapor_location.position_m != batch.location.position_m):
            raise ValueError("Vapor boundary must preserve deposited-stock clock, frame and location")
        if vapor_location.direction_unit != (0., 0., 1.):
            raise ValueError("Ground-pool vapor must explicitly point upward in its declared z-up frame")
        reference_properties.basis.require_compatible(batch.state.basis)
        liquid = reference_properties.saturated(batch.state.pressure_pa, 0.)
        vapor = reference_properties.saturated(batch.state.pressure_pa, 1.)
        if liquid != batch.state:
            raise ValueError("Deposited liquid must match the reference saturated endpoint exactly")
        reference_properties.basis.require_compatible(vapor.basis)
        absolute = finite(absolute_mass_tolerance_kg, "absolute mass tolerance", positive=True)
        relative = finite(relative_mass_tolerance, "relative mass tolerance", positive=True)
        limit = absolute+relative*batch.mass_kg
        impact_owner.require_original_step(step)
        configuration = repr(initialization.native_config)
        initial_inflow = repr(initialization.native_zero_inflow)
        native = initialization.native_runner(
            initialization.native_config, initialization.native_zero_inflow,
            output_times_s=tuple(time-times[0] for time in times),
        )
        impact_owner.require_original_step(step)
        if (repr(initialization.native_config) != configuration
                or repr(initialization.native_zero_inflow) != initial_inflow):
            raise ValueError("Native pool configuration or zero-inflow boundary changed during execution")
        rows = tuple(native.ledger)
        if len(rows) != len(times):
            raise ValueError("Native pool omitted requested output edges")
        cumulative, residuals = [], []
        for time, row in zip(times, rows, strict=True):
            elapsed = finite(row.time_s, "native time")
            stock = finite(row.liquid_mass_kg, "native liquid mass")
            evaporated = finite(row.cumulative_evaporation_kg, "native cumulative evaporation")
            residual = batch.mass_kg-stock-evaporated
            if (elapsed != time-times[0] or stock < 0. or evaporated < 0.
                    or row.cumulative_inflow_kg != 0. or abs(residual) > limit
                    or (cumulative and evaporated < cumulative[-1])
                    or row.source_status != "within_declared_scope"):
                raise ValueError("Native deposited-stock clock, domain or mass ledger failed")
            cumulative.append(evaporated)
            residuals.append(residual)
        if cumulative[0] != 0.:
            raise ValueError("Native initial edge already contains evaporation")
        if abs(finite(native.mass_balance_residual_kg, "native mass residual")-residuals[-1]) > limit:
            raise ValueError("Native final mass residual disagrees with independent stock accounting")
        source = IntervalMassSource(
            vapor_location, np.asarray(times), np.diff(cumulative), vapor,
            Origin.PREDICTED, continuation_evidence_id, "window_end",
        )
        result = ParcelPoolContinuation(initialization, native, source, tuple(residuals), times)
        object.__setattr__(result, "_binding", result._payload())
        return result.require_current()
    except Exception as cause:
        raise ParcelPoolChainError(cause, initialization, native) from cause
