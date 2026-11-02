"""Map a finite linepack withdrawal to the existing H2 compressor input API.

The bridge preserves the accepted linepack withdrawal interval and mass,
reprojects the caller-selected outlet P/T onto the compressor's HEOS property
owner, and requires an explicit signed enthalpy-conditioning ledger. It does
not advance either model or solve pressure loss, heat transfer, or compression.
"""

from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass, field

from ..combustion.fuel_compression import HydrogenRealFluidCompressionInputs
from ..core import ThermoState, finite
from ..thermo import CoolPropProperties
from .linepack_source import LinepackSourceHandoff

_PENDING: set[object] = set()


def _text(value, label):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Declare {label}")
    return value.strip()


def _project(source, provider, *, discharge_pressure_pa, isentropic_efficiency,
             temperature_bounds_k, pressure_bounds_pa, process_window_id,
             provider_id, state_evidence_id, efficiency_evidence_id, domain_evidence_id,
             transfer_evidence_id, time_mapping_evidence_id,
             conditioning_evidence_id, conditioning_energy_j,
             absolute_energy_tolerance_j, relative_energy_tolerance):
    if type(source) is not LinepackSourceHandoff:
        raise TypeError("Supply an accepted LinepackSourceHandoff")
    if type(provider) is not CoolPropProperties or provider.backend != "HEOS":
        raise TypeError("Supply the existing CoolProp HEOS hydrogen property owner")
    source.require_current()
    interval_source = source.source
    if (interval_source.state.basis.fluid != "H2"
            or interval_source.state.phase != "gas"
            or interval_source.state.vapor_mass_fraction not in (None, 1.)):
        raise ValueError("Only a single-phase H2 linepack withdrawal can feed this inlet")
    if provider.basis.fluid not in {"Hydrogen", "ParaHydrogen"}:
        raise ValueError("The compressor property owner must represent pure hydrogen")

    start, end = (float(value) for value in interval_source.edges_s)
    duration = end - start
    if duration <= 0.:
        raise ValueError("The linepack source interval must have positive duration")
    mass = interval_source.total_mass_kg
    if not math.isclose(mass, source.ledger.outlet_mass_kg,
                        rel_tol=1e-12, abs_tol=1e-15):
        raise ValueError("Source mass differs from the accepted linepack withdrawal ledger")
    rate = finite(mass / duration, "linepack withdrawal rate", positive=True)
    inlet_pressure = finite(interval_source.state.pressure_pa,
                            "linepack compressor inlet pressure", positive=True)
    inlet_temperature = finite(interval_source.state.temperature_k,
                               "linepack compressor inlet temperature", positive=True)
    discharge = finite(discharge_pressure_pa, "compressor discharge pressure", positive=True)
    if discharge <= inlet_pressure:
        raise ValueError("Compressor discharge pressure must exceed linepack outlet pressure")

    process_id = _text(process_window_id, "compressor process-window identity")
    state_id = _text(state_evidence_id, "compressor inlet-state evidence")
    efficiency_id = _text(efficiency_evidence_id, "compressor efficiency evidence")
    domain_id = _text(domain_evidence_id, "compressor property-domain evidence")
    transfer_id = _text(transfer_evidence_id, "linepack-to-compressor transfer evidence")
    clock_id = _text(time_mapping_evidence_id, "linepack source clock mapping evidence")
    conditioning_id = _text(conditioning_evidence_id, "signed inlet conditioning evidence")
    absolute = finite(absolute_energy_tolerance_j, "absolute conditioning energy tolerance", positive=True)
    relative = finite(relative_energy_tolerance, "relative conditioning energy tolerance", positive=True)
    if relative > 1e-2:
        raise ValueError("Relative conditioning energy tolerance cannot exceed 1e-2")

    mapped_state = provider.state_pt(inlet_pressure, inlet_temperature)
    if type(mapped_state) is not ThermoState:
        raise TypeError("HEOS provider must return its native ThermoState")
    provider.basis.require_compatible(mapped_state.basis)
    if (mapped_state.phase not in {"gas", "supercritical_gas", "supercritical"}
            or mapped_state.vapor_mass_fraction not in (None, 1.)):
        raise ValueError("Mapped compressor inlet must remain single-phase H2 gas")
    expected_energy = mass * (mapped_state.enthalpy_j_kg - interval_source.state.enthalpy_j_kg)
    supplied_energy = finite(conditioning_energy_j, "signed inlet conditioning energy")
    residual = supplied_energy - expected_energy
    budget = absolute + relative * max(abs(supplied_energy), abs(expected_energy), 1.)
    if abs(residual) > budget:
        raise ValueError("Caller conditioning ledger does not close the linepack-to-HEOS inlet enthalpy change")

    inputs = HydrogenRealFluidCompressionInputs(
        provider_id=_text(provider_id, "compressor property-provider identity"),
        process_window_id=process_id,
        inlet_temperature_k=inlet_temperature,
        inlet_pressure_pa=inlet_pressure,
        discharge_pressure_pa=discharge,
        hydrogen_mass_flow_kg_s=rate,
        isentropic_efficiency=isentropic_efficiency,
        temperature_bounds_k=temperature_bounds_k,
        pressure_bounds_pa=pressure_bounds_pa,
        state_evidence_id=state_id,
        efficiency_evidence_id=efficiency_id,
        domain_evidence_id=domain_id,
    )
    return (inputs, mapped_state, start, end, duration, mass, rate,
            expected_energy, supplied_energy, residual, absolute, relative,
            transfer_id, clock_id, conditioning_id)


@dataclass(frozen=True, slots=True)
class LinepackCompressorInlet:
    """Sealed linepack withdrawal projection for the existing compressor API."""

    source: LinepackSourceHandoff = field(repr=False, compare=False)
    provider: CoolPropProperties = field(repr=False, compare=False)
    inputs: HydrogenRealFluidCompressionInputs
    mapped_inlet_state: ThermoState = field(repr=False, compare=False)
    start_time_s: float
    end_time_s: float
    duration_s: float
    transferred_mass_kg: float
    mass_flow_kg_s: float
    required_conditioning_energy_j: float
    supplied_conditioning_energy_j: float
    conditioning_energy_residual_j: float
    absolute_energy_tolerance_j: float
    relative_energy_tolerance: float
    transfer_evidence_id: str
    time_mapping_evidence_id: str
    conditioning_evidence_id: str
    _issuer_token: object = field(default=None, repr=False, compare=False)
    _seal: str = field(default="", init=False, repr=False, compare=False)

    def __post_init__(self):
        if self._issuer_token not in _PENDING:
            raise TypeError("Issue linepack compressor inlets through bind_linepack_compressor_inlet")
        _PENDING.remove(self._issuer_token)
        object.__setattr__(self, "_issuer_token", None)
        self.require_current()
        object.__setattr__(self, "_seal", self._content())

    def _content(self):
        return hashlib.sha256(repr((
            id(self.source), id(self.provider), id(self.inputs), id(self.mapped_inlet_state),
            self.start_time_s, self.end_time_s, self.duration_s,
            self.transferred_mass_kg, self.mass_flow_kg_s,
            self.required_conditioning_energy_j, self.supplied_conditioning_energy_j,
            self.conditioning_energy_residual_j, self.absolute_energy_tolerance_j,
            self.relative_energy_tolerance, self.transfer_evidence_id,
            self.time_mapping_evidence_id, self.conditioning_evidence_id,
        )).encode()).hexdigest()

    def _replay(self):
        return _project(
            self.source, self.provider,
            discharge_pressure_pa=self.inputs.discharge_pressure_pa,
            isentropic_efficiency=self.inputs.isentropic_efficiency,
            temperature_bounds_k=self.inputs.temperature_bounds_k,
            pressure_bounds_pa=self.inputs.pressure_bounds_pa,
            process_window_id=self.inputs.process_window_id,
            provider_id=self.inputs.provider_id,
            state_evidence_id=self.inputs.state_evidence_id,
            efficiency_evidence_id=self.inputs.efficiency_evidence_id,
            domain_evidence_id=self.inputs.domain_evidence_id,
            transfer_evidence_id=self.transfer_evidence_id,
            time_mapping_evidence_id=self.time_mapping_evidence_id,
            conditioning_evidence_id=self.conditioning_evidence_id,
            conditioning_energy_j=self.supplied_conditioning_energy_j,
            absolute_energy_tolerance_j=self.absolute_energy_tolerance_j,
            relative_energy_tolerance=self.relative_energy_tolerance,
        )

    def require_current(self):
        projection = self._replay()
        inputs, state, start, end, duration, mass, rate, expected, supplied, residual, absolute, relative, transfer, clock, conditioning = projection
        if ((self.inputs, self.mapped_inlet_state, self.start_time_s, self.end_time_s,
             self.duration_s, self.transferred_mass_kg, self.mass_flow_kg_s,
             self.required_conditioning_energy_j, self.supplied_conditioning_energy_j,
             self.conditioning_energy_residual_j, self.absolute_energy_tolerance_j,
             self.relative_energy_tolerance, self.transfer_evidence_id,
             self.time_mapping_evidence_id, self.conditioning_evidence_id)
            != (inputs, state, start, end, duration, mass, rate, expected, supplied,
                residual, absolute, relative, transfer, clock, conditioning)):
            raise ValueError("Linepack-to-compressor receipt differs from current source replay")
        if self._seal and self._content() != self._seal:
            raise ValueError("Linepack-to-compressor receipt changed after issuance")
        return self


def bind_linepack_compressor_inlet(
    source: LinepackSourceHandoff,
    provider: CoolPropProperties,
    *,
    discharge_pressure_pa: float,
    isentropic_efficiency: float,
    temperature_bounds_k: tuple[float, float],
    pressure_bounds_pa: tuple[float, float],
    process_window_id: str,
    provider_id: str,
    state_evidence_id: str,
    efficiency_evidence_id: str,
    domain_evidence_id: str,
    transfer_evidence_id: str,
    time_mapping_evidence_id: str,
    conditioning_evidence_id: str,
    conditioning_energy_j: float,
    absolute_energy_tolerance_j: float,
    relative_energy_tolerance: float,
) -> LinepackCompressorInlet:
    """Project one accepted linepack outlet into existing compressor inputs.

    The source interval's integrated withdrawal fixes the inlet flow. The
    caller supplies the compressor target/domain and accounts for the signed
    enthalpy change from the linepack representative state to the HEOS state.
    No pressure-loss or thermal-conditioning model is implied.
    """
    projected = _project(
        source, provider, discharge_pressure_pa=discharge_pressure_pa,
        isentropic_efficiency=isentropic_efficiency,
        temperature_bounds_k=temperature_bounds_k,
        pressure_bounds_pa=pressure_bounds_pa,
        process_window_id=process_window_id,
        provider_id=provider_id,
        state_evidence_id=state_evidence_id,
        efficiency_evidence_id=efficiency_evidence_id,
        domain_evidence_id=domain_evidence_id,
        transfer_evidence_id=transfer_evidence_id,
        time_mapping_evidence_id=time_mapping_evidence_id,
        conditioning_evidence_id=conditioning_evidence_id,
        conditioning_energy_j=conditioning_energy_j,
        absolute_energy_tolerance_j=absolute_energy_tolerance_j,
        relative_energy_tolerance=relative_energy_tolerance,
    )
    inputs, state, start, end, duration, mass, rate, expected, supplied, residual, absolute, relative, transfer, clock, conditioning = projected
    token = object()
    _PENDING.add(token)
    try:
        receipt = LinepackCompressorInlet(
            source, provider, inputs, state, start, end, duration, mass, rate,
            expected, supplied, residual, absolute, relative, transfer, clock,
            conditioning, _issuer_token=token,
        )
    except Exception:
        _PENDING.discard(token)
        raise
    return receipt.require_current()


__all__ = ["LinepackCompressorInlet", "bind_linepack_compressor_inlet"]
