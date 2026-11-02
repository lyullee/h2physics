"""Bind accepted adsorption H2 outflow bins to a finite-hydride gas inlet."""

from __future__ import annotations

from bisect import bisect_right
from dataclasses import dataclass, field
from math import fsum, isclose

from ..core import ThermoState, finite
from ..storage.adsorption_dynamics import AdsorptionDynamicsTrace
from ..storage.finite_hydride import (
    FiniteHydrideGasPortBoundary,
    FiniteHydrideGasPortInput,
    HydrideGasThermodynamics,
)
from .result_provenance import recorded_content_sha256

_PENDING: set[object] = set()


def _project(trace, bed_gas, *, stream_states, clock_id,
             clock_alignment_evidence_id, hydraulic_transfer_evidence_id,
             state_projection_evidence_ids, absolute_enthalpy_tolerance_j,
             relative_enthalpy_tolerance):
    if type(trace) is not AdsorptionDynamicsTrace:
        raise TypeError("Use the owner-issued AdsorptionDynamicsTrace")
    if type(bed_gas) is not HydrideGasThermodynamics:
        raise TypeError("Use the exact finite-hydride H2 thermodynamics owner")
    trace.require_current()
    if trace.status != "completed":
        raise ValueError("Only a completed adsorption window can feed finite storage")
    source_gas = trace.inputs.vessel.gas
    source_gas.require_current()
    if tuple(source_gas.species) != ("H2",):
        raise ValueError("Only a single-component H2 adsorption outlet is supported")
    source_gas.property_basis.require_compatible(bed_gas.basis)
    if (not isinstance(clock_id, str) or not clock_id.strip()
            or not isinstance(clock_alignment_evidence_id, str)
            or not clock_alignment_evidence_id.strip()
            or not isinstance(hydraulic_transfer_evidence_id, str)
            or not hydraulic_transfer_evidence_id.strip()):
        raise ValueError("Declare clock alignment and hydraulic transfer evidence")
    source_states = tuple(stream_states)
    count = len(trace.time_s) - 1
    evidence = tuple(state_projection_evidence_ids)
    if (count < 1 or len(source_states) != count or len(evidence) != count
            or any(not isinstance(value, str) or not value.strip() for value in evidence)):
        raise ValueError("Provide one typed stream state and projection evidence per accepted source interval")
    times = tuple(finite(value, "accepted adsorption time") for value in trace.time_s)
    if any(right <= left for left, right in zip(times[:-1], times[1:])):
        raise ValueError("Accepted adsorption source times must strictly increase")
    if times[0] != trace.inputs.start_time_s or times[-1] != trace.inputs.end_time_s:
        raise ValueError("Use the original completed adsorption support without truncation")
    states, mass_rates, native_enthalpy, projected_enthalpy, residuals = [], [], [], [], []
    molar_mass = finite(source_gas.mean_molar_mass_kg_mol, "adsorption H2 molar mass", positive=True)
    if not isclose(molar_mass, bed_gas.molar_mass_kg_mol, rel_tol=1e-9, abs_tol=1e-12):
        raise ValueError("Adsorption and finite-hydride H2 molar masses differ")
    absolute = finite(absolute_enthalpy_tolerance_j, "per-interval enthalpy tolerance", positive=True)
    relative = finite(relative_enthalpy_tolerance, "relative enthalpy tolerance", positive=True)
    if relative > 1e-2:
        raise ValueError("Relative enthalpy tolerance cannot exceed 1e-2")
    for index, (state, evidence_id) in enumerate(zip(source_states, evidence, strict=True)):
        if type(state) is not ThermoState:
            raise TypeError("Every adsorption outlet bin needs an explicit ThermoState")
        bed_gas.basis.require_compatible(state.basis)
        source_pressure = finite(trace.pressure_pa[index], "accepted adsorption outlet pressure", positive=True)
        source_temperature = finite(trace.temperature_k[index], "accepted adsorption outlet temperature", positive=True)
        # Native PT reflashes may differ from their input by floating-point ulps.
        # This tolerance admits numerical roundoff, not a pressure/thermal transfer.
        if (not isclose(state.pressure_pa, source_pressure, rel_tol=1e-12, abs_tol=0.)
                or not isclose(state.temperature_k, source_temperature, rel_tol=1e-12, abs_tol=0.)):
            raise ValueError(
                "Outlet state must match the accepted adsorption trace pressure/temperature; "
                "pressure or thermal transfer mappings are not implemented"
            )
        if state.phase not in {"gas", "supercritical", "supercritical_gas"} or state.vapor_mass_fraction not in (None, 1.):
            raise ValueError("Every finite-hydride inlet state must be single-phase H2 gas")
        dt = times[index+1] - times[index]
        delta_mol = finite(trace.cumulative_outlet_mol[index+1]
                           - trace.cumulative_outlet_mol[index], "accepted H2 outlet interval")
        if delta_mol < -1e-12:
            raise ValueError("Accepted adsorption outlet flow cannot reverse direction")
        mass = max(0., delta_mol)*molar_mass
        native = finite(trace.outlet_enthalpy_j[index+1]
                        - trace.outlet_enthalpy_j[index], "native adsorption outlet enthalpy interval")
        projected = mass*state.enthalpy_j_kg
        residual = projected-native
        budget = absolute + relative*max(abs(projected), abs(native), 1.)
        if abs(residual) > budget:
            raise ValueError("Caller stream state does not close this accepted outlet interval enthalpy")
        states.append(state)
        mass_rates.append(mass/dt)
        native_enthalpy.append(native)
        projected_enthalpy.append(projected)
        residuals.append(residual)

    if fsum(mass_rates[index]*(times[index+1]-times[index])
            for index in range(count)) <= 0.:
        raise ValueError("Completed adsorption source has no positive H2 outlet mass")
    source_id = "adsorption-to-hydride:" + ":".join((
        trace.inputs.run_id, clock_alignment_evidence_id.strip(),
        hydraulic_transfer_evidence_id.strip(),
    ))

    def stream_at(time_s, _snapshot):
        trace.require_current()
        time = finite(time_s, "finite-hydride port time")
        if not times[0] <= time <= times[-1]:
            raise ValueError("Finite-hydride gas port was queried outside accepted adsorption support")
        index = min(max(bisect_right(times, time)-1, 0), count-1)
        return FiniteHydrideGasPortInput(mass_rates[index], states[index], source_id)

    boundary = FiniteHydrideGasPortBoundary(
        clock_id.strip(), times[0], times[-1], stream_at, source_id,
    )
    return (boundary, source_id, times, tuple(states), tuple(mass_rates),
            tuple(native_enthalpy), tuple(projected_enthalpy), tuple(residuals),
            tuple(evidence), absolute, relative)


@dataclass(frozen=True, slots=True)
class AdsorptionFiniteHydridePort:
    trace: AdsorptionDynamicsTrace = field(repr=False, compare=False)
    bed_gas: HydrideGasThermodynamics = field(repr=False, compare=False)
    boundary: FiniteHydrideGasPortBoundary
    source_id: str
    clock_id: str
    clock_alignment_evidence_id: str
    hydraulic_transfer_evidence_id: str
    stream_states: tuple[ThermoState, ...]
    state_projection_evidence_ids: tuple[str, ...]
    mass_flow_kg_s: tuple[float, ...]
    native_enthalpy_j: tuple[float, ...]
    projected_enthalpy_j: tuple[float, ...]
    residuals_j: tuple[float, ...]
    absolute_enthalpy_tolerance_j: float
    relative_enthalpy_tolerance: float
    _token: object = field(default=None, repr=False, compare=False)
    _seal: tuple = field(default=(), init=False, repr=False, compare=False)

    def __post_init__(self):
        if self._token not in _PENDING:
            raise TypeError("Issue this port through bind_adsorption_to_finite_hydride")
        _PENDING.remove(self._token)
        object.__setattr__(self, "_token", None)
        object.__setattr__(self, "_seal", (id(self.trace), id(self.bed_gas), id(self.boundary),
            id(self.boundary.callback),
            self.source_id, self.clock_id, self.clock_alignment_evidence_id,
            self.hydraulic_transfer_evidence_id, self.stream_states,
            self.state_projection_evidence_ids, self.mass_flow_kg_s,
            self.native_enthalpy_j, self.projected_enthalpy_j, self.residuals_j,
            self.absolute_enthalpy_tolerance_j, self.relative_enthalpy_tolerance,
            tuple(recorded_content_sha256(state) for state in self.stream_states)))

    def require_current(self):
        current = self._seal
        if not current:
            raise ValueError("Adsorption/finite-hydride port has no issuing seal")
        self.trace.require_current()
        projected = _project(
            self.trace, self.bed_gas, stream_states=self.stream_states,
            clock_id=self.clock_id,
            clock_alignment_evidence_id=self.clock_alignment_evidence_id,
            hydraulic_transfer_evidence_id=self.hydraulic_transfer_evidence_id,
            state_projection_evidence_ids=self.state_projection_evidence_ids,
            absolute_enthalpy_tolerance_j=self.absolute_enthalpy_tolerance_j,
            relative_enthalpy_tolerance=self.relative_enthalpy_tolerance,
        )
        boundary, source_id, _, states, rates, native, projected_h, residuals, evidence, absolute, relative = projected
        actual = (id(self.trace), id(self.bed_gas), id(self.boundary),
            id(self.boundary.callback), self.source_id,
            self.clock_id, self.clock_alignment_evidence_id, self.hydraulic_transfer_evidence_id,
            self.stream_states, self.state_projection_evidence_ids, self.mass_flow_kg_s,
            self.native_enthalpy_j, self.projected_enthalpy_j, self.residuals_j,
            self.absolute_enthalpy_tolerance_j, self.relative_enthalpy_tolerance,
            tuple(recorded_content_sha256(state) for state in self.stream_states))
        if (actual != current or source_id != self.source_id
                or self.boundary.clock_id != self.clock_id
                or self.boundary.support_start_s != self.trace.time_s[0]
                or self.boundary.support_end_s != self.trace.time_s[-1]
                or self.boundary.source_id != self.source_id
                or states != self.stream_states or rates != self.mass_flow_kg_s
                or native != self.native_enthalpy_j or projected_h != self.projected_enthalpy_j
                or residuals != self.residuals_j or evidence != self.state_projection_evidence_ids
                or absolute != self.absolute_enthalpy_tolerance_j or relative != self.relative_enthalpy_tolerance):
            raise ValueError("Adsorption-to-hydride stream projection or owner changed")
        return self


def bind_adsorption_to_finite_hydride(
    trace: AdsorptionDynamicsTrace,
    bed_gas: HydrideGasThermodynamics,
    *,
    stream_states,
    clock_id: str,
    clock_alignment_evidence_id: str,
    hydraulic_transfer_evidence_id: str,
    state_projection_evidence_ids,
    absolute_enthalpy_tolerance_j: float = 1e-3,
    relative_enthalpy_tolerance: float = 1e-8,
) -> AdsorptionFiniteHydridePort:
    """Translate accepted H2 outlet bins into the existing finite-bed inlet port.

    Each native interval becomes a piecewise-constant mass rate over its exact
    accepted time span. The caller supplies the inlet state per bin; the
    adapter admits it only if native interval enthalpy closes within budget.
    This does not infer timing alignment, gas-line hydraulics, a valve law, or
    any pressure evolution.
    """
    states, evidence = tuple(stream_states), tuple(state_projection_evidence_ids)
    values = _project(trace, bed_gas, stream_states=states, clock_id=clock_id,
        clock_alignment_evidence_id=clock_alignment_evidence_id,
        hydraulic_transfer_evidence_id=hydraulic_transfer_evidence_id,
        state_projection_evidence_ids=evidence,
        absolute_enthalpy_tolerance_j=absolute_enthalpy_tolerance_j,
        relative_enthalpy_tolerance=relative_enthalpy_tolerance)
    boundary, source_id, _, accepted_states, rates, native, projected, residuals, evidence, absolute, relative = values
    token = object()
    _PENDING.add(token)
    try:
        return AdsorptionFiniteHydridePort(
            trace, bed_gas, boundary, source_id, clock_id.strip(),
            clock_alignment_evidence_id.strip(), hydraulic_transfer_evidence_id.strip(),
            accepted_states, evidence, rates, native, projected, residuals,
            absolute, relative, _token=token,
        )
    except Exception:
        _PENDING.discard(token)
        raise
