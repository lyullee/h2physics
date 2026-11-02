"""Bounded real-fluid compressor-to-finite-hydride gas-port handoff.

This adapter maps one caller-declared steady compressor interval onto the
existing finite-hydride gas boundary. The compressor remains the owner of the
discharge point; the hydride bed remains the owner of storage, uptake and
energy dynamics. No line, valve, control, or storage solver is added here.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from math import isclose

from ..combustion.fuel_compression import HydrogenRealFluidCompressionRun
from ..core import ThermoState, finite
from ..storage.finite_hydride import (
    FiniteHydrideGasPortBoundary,
    FiniteHydrideGasPortInput,
    HydrideGasThermodynamics,
)

_PENDING_ISSUERS: set[object] = set()


def _text(value, name):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Declare {name}")
    return value.strip()


def _project(compressor, bed_gas, stream_state, *, clock_id, start_time_s,
             end_time_s, clock_alignment_evidence_id,
             hydraulic_transfer_evidence_id, state_projection_evidence_id,
             absolute_enthalpy_tolerance_j_kg, relative_enthalpy_tolerance):
    if type(compressor) is not HydrogenRealFluidCompressionRun:
        raise TypeError("Supply the owner-issued CoolProp real-fluid hydrogen compression result")
    if type(bed_gas) is not HydrideGasThermodynamics:
        raise TypeError("Supply the exact finite-hydride gas thermodynamics owner")
    if type(stream_state) is not ThermoState:
        raise TypeError("Supply one native ThermoState for the compressor discharge mapping")
    compressor.require_current()
    compressor.property_basis.require_compatible(bed_gas.basis)
    bed_gas.basis.require_compatible(stream_state.basis)
    if compressor.provider.backend != "HEOS" or compressor.provider.basis.fluid not in {
            "Hydrogen", "ParaHydrogen"}:
        raise ValueError("Only a direct HEOS pure-hydrogen compressor discharge is admitted")
    if not isclose(compressor.actual_outlet.mass_fraction_h2, 1., rel_tol=0., abs_tol=1e-12):
        raise ValueError("Compressor discharge must retain a pure-H2 mass fraction")
    if stream_state.phase not in {"gas", "supercritical_gas", "supercritical"}:
        raise ValueError("Hydride port mapping requires an explicit single-phase H2 gas state")
    if stream_state.vapor_mass_fraction not in (None, 1.):
        raise ValueError("Hydride port mapping cannot admit a two-phase stream")
    clock = _text(clock_id, "shared physical clock identity")
    clock_evidence = _text(clock_alignment_evidence_id, "clock-alignment evidence")
    hydraulic_evidence = _text(hydraulic_transfer_evidence_id, "hydraulic-transfer evidence")
    projection_evidence = _text(state_projection_evidence_id, "discharge-state projection evidence")
    start = finite(start_time_s, "compressor transfer start time")
    end = finite(end_time_s, "compressor transfer end time")
    if end <= start:
        raise ValueError("Compressor transfer interval must have positive duration")
    absolute = finite(absolute_enthalpy_tolerance_j_kg,
                      "specific-enthalpy closure tolerance", positive=True)
    relative = finite(relative_enthalpy_tolerance,
                      "relative-enthalpy closure tolerance", positive=True)
    if relative > 1e-2:
        raise ValueError("Relative enthalpy tolerance cannot exceed 1e-2")

    outlet = compressor.actual_outlet
    reconstructed = bed_gas.state_pt(outlet.pressure_pa, outlet.temperature_k)
    if type(reconstructed) is not ThermoState:
        raise TypeError("Finite-hydride property owner did not return its native ThermoState")
    bed_gas.basis.require_compatible(reconstructed.basis)
    if (reconstructed.phase not in {"gas", "supercritical_gas", "supercritical"}
            or reconstructed.vapor_mass_fraction not in (None, 1.)):
        raise ValueError("Receiver property replay is not a single-phase gas")
    for actual, expected, label in (
        (reconstructed.pressure_pa, outlet.pressure_pa, "receiver-provider pressure"),
        (reconstructed.temperature_k, outlet.temperature_k, "receiver-provider temperature"),
    ):
        if not isclose(actual, expected, rel_tol=1e-12, abs_tol=1e-8):
            raise ValueError(f"Receiver state replay does not preserve compressor {label}")
    checks = (
        (stream_state.pressure_pa, outlet.pressure_pa, 1e-6, 1e-12, "absolute pressure"),
        (stream_state.temperature_k, outlet.temperature_k, 1e-9, 1e-12, "temperature"),
        (stream_state.density_kg_m3, outlet.density_kg_m3, 1e-10, 1e-9, "density"),
        (stream_state.enthalpy_j_kg, outlet.enthalpy_j_kg,
         absolute, relative, "compressor specific enthalpy"),
        (stream_state.entropy_j_kg_k, outlet.entropy_j_kg_k, 1e-7, 1e-9, "entropy"),
        (stream_state.internal_energy_j_kg, reconstructed.internal_energy_j_kg,
         absolute, relative, "finite-hydride-provider internal energy"),
    )
    for actual, expected, abs_tol, rel_tol, label in checks:
        if not isclose(actual, expected, rel_tol=rel_tol, abs_tol=abs_tol):
            raise ValueError(f"Caller discharge state does not close against {label}")
    # Replay the receiver provider at the same P/T and require a common caloric
    # basis. This prevents a merely similar state from silently changing energy.
    for actual, expected, abs_tol, rel_tol, label in (
        (stream_state.density_kg_m3, reconstructed.density_kg_m3, 1e-10, 1e-9, "density"),
        (stream_state.enthalpy_j_kg, reconstructed.enthalpy_j_kg,
         absolute, relative, "specific enthalpy"),
        (stream_state.entropy_j_kg_k, reconstructed.entropy_j_kg_k, 1e-7, 1e-9, "entropy"),
    ):
        if not isclose(actual, expected, rel_tol=rel_tol, abs_tol=abs_tol):
            raise ValueError(f"Mapped stream state does not close against receiver-provider {label}")

    rate = finite(compressor.inputs.hydrogen_mass_flow_kg_s,
                  "compressor hydrogen mass flow", positive=True)
    source_id = "compressor-to-finite-hydride:" + ":".join((
        compressor.inputs.process_window_id, clock_evidence,
        hydraulic_evidence, projection_evidence,
    ))
    stream_signature = (
        stream_state.basis, stream_state.pressure_pa, stream_state.temperature_k,
        stream_state.density_kg_m3, stream_state.enthalpy_j_kg,
        stream_state.internal_energy_j_kg, stream_state.entropy_j_kg_k,
        stream_state.phase, stream_state.vapor_mass_fraction,
    )

    def stream_at(time_s, _snapshot):
        compressor.require_current()
        replay = _project(
            compressor, bed_gas, stream_state, clock_id=clock,
            start_time_s=start, end_time_s=end,
            clock_alignment_evidence_id=clock_evidence,
            hydraulic_transfer_evidence_id=hydraulic_evidence,
            state_projection_evidence_id=projection_evidence,
            absolute_enthalpy_tolerance_j_kg=absolute,
            relative_enthalpy_tolerance=relative,
        )
        if replay[1] != source_id or replay[2] != rate:
            raise ValueError("Compressor/hydride source mapping changed while evaluating the port")
        if stream_signature != (
                stream_state.basis, stream_state.pressure_pa, stream_state.temperature_k,
                stream_state.density_kg_m3, stream_state.enthalpy_j_kg,
                stream_state.internal_energy_j_kg, stream_state.entropy_j_kg_k,
                stream_state.phase, stream_state.vapor_mass_fraction):
            raise ValueError("Mapped compressor discharge state changed after handoff issuance")
        time = finite(time_s, "finite-hydride port time")
        if not start <= time <= end:
            raise ValueError("Finite-hydride port was queried outside the declared compressor interval")
        return FiniteHydrideGasPortInput(rate, stream_state, source_id)

    boundary = FiniteHydrideGasPortBoundary(clock, start, end, stream_at, source_id)
    return (boundary, source_id, rate, start, end, clock, clock_evidence,
            hydraulic_evidence, projection_evidence, absolute, relative,
            reconstructed)


@dataclass(frozen=True, slots=True)
class CompressorFiniteHydridePort:
    """Currentness-sealed H2 port projection from one compressor operating point."""

    compressor: HydrogenRealFluidCompressionRun = field(repr=False, compare=False)
    bed_gas: HydrideGasThermodynamics = field(repr=False, compare=False)
    stream_state: ThermoState = field(repr=False, compare=False)
    boundary: FiniteHydrideGasPortBoundary
    source_id: str
    clock_id: str
    start_time_s: float
    end_time_s: float
    mass_flow_kg_s: float
    transferred_mass_kg: float
    transferred_enthalpy_j: float
    clock_alignment_evidence_id: str
    hydraulic_transfer_evidence_id: str
    state_projection_evidence_id: str
    absolute_enthalpy_tolerance_j_kg: float
    relative_enthalpy_tolerance: float
    _issuer_token: object = field(default=None, repr=False, compare=False)
    _seal: tuple = field(default=(), init=False, repr=False, compare=False)

    def __post_init__(self):
        if self._issuer_token not in _PENDING_ISSUERS:
            raise TypeError("Issue this port only through bind_compressor_to_finite_hydride")
        _PENDING_ISSUERS.remove(self._issuer_token)
        object.__setattr__(self, "_issuer_token", None)
        self.require_current()
        object.__setattr__(self, "_seal", self._content())

    def _content(self):
        return (id(self.compressor), id(self.bed_gas), id(self.stream_state),
                id(self.boundary), id(self.boundary.callback), self.source_id,
                self.clock_id, self.start_time_s, self.end_time_s,
                self.mass_flow_kg_s, self.transferred_mass_kg,
                self.transferred_enthalpy_j, self.clock_alignment_evidence_id,
                self.hydraulic_transfer_evidence_id, self.state_projection_evidence_id,
                self.absolute_enthalpy_tolerance_j_kg, self.relative_enthalpy_tolerance)

    def require_current(self):
        projected = _project(
            self.compressor, self.bed_gas, self.stream_state,
            clock_id=self.clock_id, start_time_s=self.start_time_s,
            end_time_s=self.end_time_s,
            clock_alignment_evidence_id=self.clock_alignment_evidence_id,
            hydraulic_transfer_evidence_id=self.hydraulic_transfer_evidence_id,
            state_projection_evidence_id=self.state_projection_evidence_id,
            absolute_enthalpy_tolerance_j_kg=self.absolute_enthalpy_tolerance_j_kg,
            relative_enthalpy_tolerance=self.relative_enthalpy_tolerance,
        )
        boundary, source_id, rate, start, end, *_ = projected
        expected = (id(self.compressor), id(self.bed_gas), id(self.stream_state),
                    id(boundary), id(boundary.callback), source_id, self.clock_id,
                    start, end, rate, rate*(end-start),
                    rate*(end-start)*self.stream_state.enthalpy_j_kg,
                    self.clock_alignment_evidence_id, self.hydraulic_transfer_evidence_id,
                    self.state_projection_evidence_id,
                    self.absolute_enthalpy_tolerance_j_kg, self.relative_enthalpy_tolerance)
        if self._seal and self._content() != self._seal:
            raise ValueError("Compressor-to-hydride handoff changed after issuance")
        actual = self._content()
        if (actual[:3] != expected[:3] or actual[5:] != expected[5:]
                or self.boundary.clock_id != boundary.clock_id
                or self.boundary.support_start_s != boundary.support_start_s
                or self.boundary.support_end_s != boundary.support_end_s
                or self.boundary.source_id != boundary.source_id):
            raise ValueError("Compressor-to-hydride boundary no longer matches the original mapping")
        if (not isclose(self.transferred_mass_kg, expected[10], rel_tol=1e-12, abs_tol=1e-14)
                or not isclose(self.transferred_enthalpy_j, expected[11], rel_tol=1e-12, abs_tol=1e-9)):
            raise ValueError("Compressor-to-hydride interval mass/enthalpy ledger changed")
        return self


def bind_compressor_to_finite_hydride(
    compressor: HydrogenRealFluidCompressionRun,
    bed_gas: HydrideGasThermodynamics,
    *,
    stream_state: ThermoState,
    clock_id: str,
    start_time_s: float,
    end_time_s: float,
    clock_alignment_evidence_id: str,
    hydraulic_transfer_evidence_id: str,
    state_projection_evidence_id: str,
    absolute_enthalpy_tolerance_j_kg: float,
    relative_enthalpy_tolerance: float = 1e-6,
) -> CompressorFiniteHydridePort:
    """Bind a constant-flow, caller-mapped interval to the existing hydride port.

    The compressor's native outlet P/T/flow and the receiver property's H2 basis
    must agree with the supplied stream state. The caller owns clock alignment,
    the physical line/valve transfer and the state projection evidence. The
    interval is piecewise constant because the source is one steady compressor
    point; no transient compressor or line hydraulics are inferred.
    """
    projected = _project(
        compressor, bed_gas, stream_state, clock_id=clock_id,
        start_time_s=start_time_s, end_time_s=end_time_s,
        clock_alignment_evidence_id=clock_alignment_evidence_id,
        hydraulic_transfer_evidence_id=hydraulic_transfer_evidence_id,
        state_projection_evidence_id=state_projection_evidence_id,
        absolute_enthalpy_tolerance_j_kg=absolute_enthalpy_tolerance_j_kg,
        relative_enthalpy_tolerance=relative_enthalpy_tolerance,
    )
    boundary, source_id, rate, start, end, clock, clock_evidence, hydraulic_evidence, state_evidence, absolute, relative, _ = projected
    mass = rate*(end-start)
    enthalpy = mass*stream_state.enthalpy_j_kg
    token = object()
    _PENDING_ISSUERS.add(token)
    try:
        result = CompressorFiniteHydridePort(
            compressor, bed_gas, stream_state, boundary, source_id, clock,
            start, end, rate, mass, enthalpy, clock_evidence,
            hydraulic_evidence, state_evidence, absolute, relative,
            _issuer_token=token,
        )
    except Exception:
        _PENDING_ISSUERS.discard(token)
        raise
    return result.require_current()


__all__ = ["CompressorFiniteHydridePort", "bind_compressor_to_finite_hydride"]
