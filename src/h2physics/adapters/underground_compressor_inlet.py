"""Map one admitted UH2SC cavern withdrawal bin to existing compressor input.

The adapter reuses ``UndergroundWithdrawalProjection`` and the existing
``HydrogenRealFluidCompressionInputs`` contract. It neither reruns the cavern
nor solves a well, compressor, pressure-loss, or conditioning model.
"""

from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass, field

import numpy as np

from ..combustion.fuel_compression import HydrogenRealFluidCompressionInputs
from ..core import ThermoState, finite
from ..thermo.coolprop import CoolPropProperties
from .underground_storage import UndergroundWithdrawalProjection

_PENDING: set[object] = set()


def _text(value, name):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Declare {name}")
    return value.strip()


def _project(projection, provider, *, interval_index, discharge_pressure_pa,
             isentropic_efficiency, temperature_bounds_k, pressure_bounds_pa,
             provider_id, process_window_id, state_evidence_id,
             efficiency_evidence_id, domain_evidence_id,
             transfer_evidence_id, time_mapping_evidence_id,
             state_projection_evidence_id, energy_mapping_evidence_id,
             conditioning_energy_j, absolute_mass_tolerance_kg,
             relative_mass_tolerance, absolute_energy_tolerance_j,
             relative_energy_tolerance):
    if type(projection) is not UndergroundWithdrawalProjection:
        raise TypeError("Supply an accepted UH2SC UndergroundWithdrawalProjection")
    if type(provider) is not CoolPropProperties or provider.backend != "HEOS":
        raise TypeError("Supply the existing CoolProp HEOS hydrogen property owner")
    projection.require_current()
    trace = projection.trace
    if not trace.numerically_admitted:
        raise ValueError("Only an independently admitted native cavern trace can feed compression")
    source = projection.source
    if (source.state.phase not in {"gas", "supercritical_gas", "supercritical"}
            or source.state.vapor_mass_fraction not in (None, 1.)
            or source.state.basis.fluid not in {"H2", "Hydrogen", "ParaHydrogen"}):
        raise ValueError("Cavern source projection must retain a single-phase pure-H2 representative state")
    if provider.basis.fluid not in {"Hydrogen", "ParaHydrogen"}:
        raise ValueError("Compressor property owner must represent pure hydrogen")
    source.state.basis.require_compatible(provider.basis)

    index = interval_index
    if isinstance(index, bool) or not isinstance(index, int) or not 0 <= index < len(source.mass_kg):
        raise ValueError("Select one accepted cavern withdrawal bin by its left-edge index")
    start, end = float(source.edges_s[index]), float(source.edges_s[index+1])
    duration = end-start
    if duration <= 0. or source.location.clock_id != trace.evidence.clock_id:
        raise ValueError("Cavern withdrawal source has invalid duration or a foreign clock")
    mass = finite(float(source.mass_kg[index]), "cavern dry-H2 withdrawal bin mass", positive=True)
    native_enthalpy = finite(projection.native_dry_hydrogen_enthalpy_j[index],
                             "native dry-H2 withdrawal enthalpy")
    projected_enthalpy = finite(projection.projected_enthalpy_j[index],
                                 "representative-state projected enthalpy")
    rate = finite(mass/duration, "compressor inlet H2 mass flow", positive=True)
    inlet_pressure = finite(source.state.pressure_pa, "compressor inlet pressure", positive=True)
    inlet_temperature = finite(source.state.temperature_k, "compressor inlet temperature", positive=True)
    discharge = finite(discharge_pressure_pa, "compressor discharge pressure", positive=True)
    if discharge <= inlet_pressure:
        raise ValueError("Compressor discharge pressure must exceed cavern withdrawal pressure")

    mapped = provider.state_pt(inlet_pressure, inlet_temperature)
    if type(mapped) is not ThermoState:
        raise TypeError("HEOS property owner did not return its native ThermoState")
    provider.basis.require_compatible(mapped.basis)
    if mapped != source.state:
        raise ValueError("HEOS replay does not reproduce the accepted cavern representative state")
    if not math.isclose(mass*mapped.enthalpy_j_kg, projected_enthalpy,
                        rel_tol=1e-12, abs_tol=1e-9):
        raise ValueError("Representative-state energy ledger differs from the exact source-bin mass")

    expected_ids = (
        ("provider identity", provider_id), ("process-window identity", process_window_id),
        ("compressor state evidence", state_evidence_id),
        ("compressor efficiency evidence", efficiency_evidence_id),
        ("compressor domain evidence", domain_evidence_id),
        ("cavern-to-compressor transfer evidence", transfer_evidence_id),
        ("native clock mapping evidence", time_mapping_evidence_id),
        ("source-state projection evidence", state_projection_evidence_id),
        ("source-to-compressor energy mapping evidence", energy_mapping_evidence_id),
    )
    ids = tuple(_text(value, name) for name, value in expected_ids)
    absolute_mass = finite(absolute_mass_tolerance_kg, "absolute H2 mass tolerance", positive=True)
    relative_mass = finite(relative_mass_tolerance, "relative H2 mass tolerance", positive=True)
    absolute_energy = finite(absolute_energy_tolerance_j, "absolute energy tolerance", positive=True)
    relative_energy = finite(relative_energy_tolerance, "relative energy tolerance", positive=True)
    if relative_mass > 1e-2 or relative_energy > 1e-2:
        raise ValueError("Relative mass/energy tolerances cannot exceed 1e-2")
    mass_residual = rate*duration-mass
    if abs(mass_residual) > absolute_mass+relative_mass*mass:
        raise ValueError("Compressor inlet throughput does not reproduce the accepted source bin mass")

    expected_conditioning = mass*mapped.enthalpy_j_kg-native_enthalpy
    supplied_conditioning = finite(conditioning_energy_j,
                                   "signed cavern-to-compressor energy mapping")
    energy_residual = supplied_conditioning-expected_conditioning
    energy_budget = absolute_energy+relative_energy*max(
        abs(supplied_conditioning), abs(expected_conditioning), 1.,
    )
    if abs(energy_residual) > energy_budget:
        raise ValueError("Caller energy mapping does not close native cavern withdrawal to compressor inlet")

    inputs = HydrogenRealFluidCompressionInputs(
        provider_id=ids[0], process_window_id=ids[1],
        inlet_temperature_k=inlet_temperature, inlet_pressure_pa=inlet_pressure,
        discharge_pressure_pa=discharge, hydrogen_mass_flow_kg_s=rate,
        isentropic_efficiency=isentropic_efficiency,
        temperature_bounds_k=temperature_bounds_k, pressure_bounds_pa=pressure_bounds_pa,
        state_evidence_id=ids[2], efficiency_evidence_id=ids[3],
        domain_evidence_id=ids[4],
    )
    return (inputs, mapped, start, end, duration, mass, rate, native_enthalpy,
            projected_enthalpy, expected_conditioning, supplied_conditioning,
            energy_residual, mass_residual, absolute_mass, relative_mass,
            absolute_energy, relative_energy, *ids, index)


@dataclass(frozen=True, slots=True)
class UndergroundCompressorInlet:
    """Sealed single-bin cavern withdrawal projection to compressor inputs."""

    projection: UndergroundWithdrawalProjection = field(repr=False, compare=False)
    provider: CoolPropProperties = field(repr=False, compare=False)
    interval_index: int
    inputs: HydrogenRealFluidCompressionInputs
    inlet_state: ThermoState = field(repr=False, compare=False)
    start_time_s: float
    end_time_s: float
    duration_s: float
    transferred_mass_kg: float
    mass_flow_kg_s: float
    native_source_enthalpy_j: float
    representative_source_enthalpy_j: float
    required_energy_mapping_j: float
    supplied_energy_mapping_j: float
    energy_mapping_residual_j: float
    mass_residual_kg: float
    absolute_mass_tolerance_kg: float
    relative_mass_tolerance: float
    absolute_energy_tolerance_j: float
    relative_energy_tolerance: float
    provider_id: str
    process_window_id: str
    state_evidence_id: str
    efficiency_evidence_id: str
    domain_evidence_id: str
    transfer_evidence_id: str
    time_mapping_evidence_id: str
    state_projection_evidence_id: str
    energy_mapping_evidence_id: str
    _issuer: object = field(default=None, repr=False, compare=False)
    _seal: str = field(default="", init=False, repr=False, compare=False)

    def __post_init__(self):
        if self._issuer not in _PENDING:
            raise TypeError("Issue receipts through bind_underground_compressor_inlet")
        _PENDING.remove(self._issuer)
        object.__setattr__(self, "_issuer", None)
        self.require_current()
        object.__setattr__(self, "_seal", self._content())

    def _content(self):
        return hashlib.sha256(repr((
            id(self.projection), id(self.provider), self.interval_index,
            id(self.inputs), id(self.inlet_state), self.start_time_s,
            self.end_time_s, self.duration_s, self.transferred_mass_kg,
            self.mass_flow_kg_s, self.native_source_enthalpy_j,
            self.representative_source_enthalpy_j, self.required_energy_mapping_j,
            self.supplied_energy_mapping_j, self.energy_mapping_residual_j,
            self.mass_residual_kg, self.absolute_mass_tolerance_kg,
            self.relative_mass_tolerance, self.absolute_energy_tolerance_j,
            self.relative_energy_tolerance, self.provider_id, self.process_window_id,
            self.state_evidence_id, self.efficiency_evidence_id, self.domain_evidence_id,
            self.transfer_evidence_id, self.time_mapping_evidence_id,
            self.state_projection_evidence_id, self.energy_mapping_evidence_id,
        )).encode()).hexdigest()

    def _replay(self):
        return _project(
            self.projection, self.provider,
            interval_index=self.interval_index,
            discharge_pressure_pa=self.inputs.discharge_pressure_pa,
            isentropic_efficiency=self.inputs.isentropic_efficiency,
            temperature_bounds_k=self.inputs.temperature_bounds_k,
            pressure_bounds_pa=self.inputs.pressure_bounds_pa,
            provider_id=self.provider_id,
            process_window_id=self.process_window_id,
            state_evidence_id=self.state_evidence_id,
            efficiency_evidence_id=self.efficiency_evidence_id,
            domain_evidence_id=self.domain_evidence_id,
            transfer_evidence_id=self.transfer_evidence_id,
            time_mapping_evidence_id=self.time_mapping_evidence_id,
            state_projection_evidence_id=self.state_projection_evidence_id,
            energy_mapping_evidence_id=self.energy_mapping_evidence_id,
            conditioning_energy_j=self.supplied_energy_mapping_j,
            absolute_mass_tolerance_kg=self.absolute_mass_tolerance_kg,
            relative_mass_tolerance=self.relative_mass_tolerance,
            absolute_energy_tolerance_j=self.absolute_energy_tolerance_j,
            relative_energy_tolerance=self.relative_energy_tolerance,
        )

    def require_current(self):
        self.projection.require_current()
        expected = self._replay()
        (inputs, state, start, end, duration, mass, rate, native_h, projected_h,
         required, supplied, energy_residual, mass_residual, abs_m, rel_m, abs_e,
         rel_e, provider_id, window_id, state_id, efficiency_id, domain_id,
         transfer_id, clock_id, projection_id, energy_id, index) = expected
        actual = (self.inputs, self.inlet_state, self.start_time_s, self.end_time_s,
                  self.duration_s, self.transferred_mass_kg, self.mass_flow_kg_s,
                  self.native_source_enthalpy_j, self.representative_source_enthalpy_j,
                  self.required_energy_mapping_j, self.supplied_energy_mapping_j,
                  self.energy_mapping_residual_j, self.mass_residual_kg,
                  self.absolute_mass_tolerance_kg, self.relative_mass_tolerance,
                  self.absolute_energy_tolerance_j, self.relative_energy_tolerance,
                  self.provider_id, self.process_window_id, self.state_evidence_id,
                  self.efficiency_evidence_id, self.domain_evidence_id,
                  self.transfer_evidence_id, self.time_mapping_evidence_id,
                  self.state_projection_evidence_id, self.energy_mapping_evidence_id,
                  self.interval_index)
        replay = (inputs, state, start, end, duration, mass, rate, native_h,
                  projected_h, required, supplied, energy_residual, mass_residual,
                  abs_m, rel_m, abs_e, rel_e, provider_id, window_id, state_id,
                  efficiency_id, domain_id, transfer_id, clock_id, projection_id,
                  energy_id, index)
        if actual != replay:
            raise ValueError("Underground compressor inlet differs from its source replay")
        if self._seal and self._content() != self._seal:
            raise ValueError("Underground compressor inlet changed after issuance")
        return self


def bind_underground_compressor_inlet(
    projection: UndergroundWithdrawalProjection,
    provider: CoolPropProperties,
    *,
    interval_index: int,
    discharge_pressure_pa: float,
    isentropic_efficiency: float,
    temperature_bounds_k: tuple[float, float],
    pressure_bounds_pa: tuple[float, float],
    provider_id: str,
    process_window_id: str,
    state_evidence_id: str,
    efficiency_evidence_id: str,
    domain_evidence_id: str,
    transfer_evidence_id: str,
    time_mapping_evidence_id: str,
    state_projection_evidence_id: str,
    energy_mapping_evidence_id: str,
    conditioning_energy_j: float,
    absolute_mass_tolerance_kg: float,
    relative_mass_tolerance: float,
    absolute_energy_tolerance_j: float,
    relative_energy_tolerance: float,
) -> UndergroundCompressorInlet:
    """Bind one admitted dry-H2 cavern outlet bin to existing compressor inputs."""
    projected = _project(
        projection, provider, interval_index=interval_index,
        discharge_pressure_pa=discharge_pressure_pa,
        isentropic_efficiency=isentropic_efficiency,
        temperature_bounds_k=temperature_bounds_k, pressure_bounds_pa=pressure_bounds_pa,
        provider_id=provider_id, process_window_id=process_window_id,
        state_evidence_id=state_evidence_id,
        efficiency_evidence_id=efficiency_evidence_id,
        domain_evidence_id=domain_evidence_id,
        transfer_evidence_id=transfer_evidence_id,
        time_mapping_evidence_id=time_mapping_evidence_id,
        state_projection_evidence_id=state_projection_evidence_id,
        energy_mapping_evidence_id=energy_mapping_evidence_id,
        conditioning_energy_j=conditioning_energy_j,
        absolute_mass_tolerance_kg=absolute_mass_tolerance_kg,
        relative_mass_tolerance=relative_mass_tolerance,
        absolute_energy_tolerance_j=absolute_energy_tolerance_j,
        relative_energy_tolerance=relative_energy_tolerance,
    )
    (inputs, state, start, end, duration, mass, rate, native_h, projected_h,
     required, supplied, energy_residual, mass_residual, abs_m, rel_m, abs_e,
     rel_e, provider_id, window_id, state_id, efficiency_id, domain_id,
     transfer_id, clock_id, projection_id, energy_id, index) = projected
    token = object()
    _PENDING.add(token)
    try:
        result = UndergroundCompressorInlet(
            projection, provider, index, inputs, state, start, end, duration,
            mass, rate, native_h, projected_h, required, supplied, energy_residual,
            mass_residual, abs_m, rel_m, abs_e, rel_e, provider_id, window_id,
            state_id, efficiency_id, domain_id, transfer_id, clock_id,
            projection_id, energy_id, _issuer=token,
        )
    except Exception:
        _PENDING.discard(token)
        raise
    return result.require_current()


__all__ = ["UndergroundCompressorInlet", "bind_underground_compressor_inlet"]
