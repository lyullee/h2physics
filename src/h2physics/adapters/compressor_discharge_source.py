"""Caller-bounded release source from an accepted HEOS compressor discharge.

This adapter projects a declared throughflow leak interval from the exact
compressor discharge state into the existing finite ``IntervalMassSource``.
It does not calculate a leak rate, opening, nozzle flow or dispersion field.
"""

from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass, field

from ..combustion.fuel_compression import HydrogenRealFluidCompressionRun
from ..core import Origin, ThermoState, finite
from ..release import SourceLocation
from ..sources import IntervalMassSource

_PENDING_ISSUERS: set[object] = set()


def _text(value, name):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Declare {name}")
    return value.strip()


def _project(compressor, *, location, start_time_s, end_time_s,
             release_mass_flow_kg_s, origin, time_mapping_evidence_id,
             release_flow_evidence_id):
    if type(compressor) is not HydrogenRealFluidCompressionRun:
        raise TypeError("Supply an owner-issued CoolProp real-fluid hydrogen compressor result")
    if type(location) is not SourceLocation:
        raise TypeError("Supply an explicit SourceLocation for the release plane")
    compressor.require_current()
    if (compressor.provider.backend != "HEOS"
            or compressor.provider.basis.fluid not in {"Hydrogen", "ParaHydrogen"}
            or not math.isclose(compressor.actual_outlet.mass_fraction_h2, 1.,
                                rel_tol=0., abs_tol=1e-12)):
        raise ValueError("Only a direct pure-H2 HEOS compressor discharge is admitted")
    start = finite(start_time_s, "release window start")
    end = finite(end_time_s, "release window end")
    if end <= start:
        raise ValueError("Finite release window must have positive duration")
    if location.clock_id.strip() == "":
        raise ValueError("Source location requires the mapped physical clock")
    time_id = _text(time_mapping_evidence_id, "compressor process-window time mapping")
    flow_id = _text(release_flow_evidence_id, "caller-supplied release-flow evidence")
    origin = Origin(origin)
    if origin is Origin.UNRESOLVED:
        raise ValueError("Resolve the compressor discharge source origin")

    compressor_rate = finite(compressor.inputs.hydrogen_mass_flow_kg_s,
                              "compressor hydrogen throughput", positive=True)
    release_rate = finite(release_mass_flow_kg_s,
                          "caller-declared compressor discharge leak flow", positive=True)
    if release_rate > compressor_rate:
        raise ValueError("Prescribed discharge leak flow cannot exceed the accepted compressor H2 throughput")
    duration = end-start
    mass = release_rate*duration
    state = compressor.provider.state_pt(
        compressor.actual_outlet.pressure_pa,
        compressor.actual_outlet.temperature_k,
    )
    if type(state) is not ThermoState:
        raise TypeError("Compressor property owner did not return its native outlet ThermoState")
    compressor.property_basis.require_compatible(state.basis)
    if (state.phase not in {"gas", "supercritical_gas", "supercritical"}
            or state.vapor_mass_fraction not in (None, 1.)):
        raise ValueError("Compressor discharge source must be a single-phase H2 gas")
    outlet = compressor.actual_outlet
    for actual, expected, abs_tol, rel_tol, name in (
        (state.pressure_pa, outlet.pressure_pa, 1e-6, 1e-12, "absolute pressure"),
        (state.temperature_k, outlet.temperature_k, 1e-9, 1e-12, "temperature"),
        (state.density_kg_m3, outlet.density_kg_m3, 1e-10, 1e-9, "density"),
        (state.enthalpy_j_kg, outlet.enthalpy_j_kg, 1e-6, 1e-10, "specific enthalpy"),
        (state.entropy_j_kg_k, outlet.entropy_j_kg_k, 1e-8, 1e-9, "specific entropy"),
    ):
        if not math.isclose(actual, expected, rel_tol=rel_tol, abs_tol=abs_tol):
            raise ValueError(f"Finite-source state does not preserve compressor {name}")
    evidence = ":".join((compressor.inputs.process_window_id, time_id, flow_id))
    source = IntervalMassSource(
        location, [start, end], [mass], state, origin, evidence, "window_end",
    )
    return (source, state, start, end, duration, compressor_rate, release_rate,
            mass, mass*state.enthalpy_j_kg, origin, time_id, flow_id)


@dataclass(frozen=True, slots=True)
class CompressorDischargeSource:
    """One source-owned finite leak interval from an accepted compressor point."""

    compressor: HydrogenRealFluidCompressionRun = field(repr=False, compare=False)
    location: SourceLocation
    source: IntervalMassSource = field(repr=False, compare=False)
    state: ThermoState = field(repr=False, compare=False)
    start_time_s: float
    end_time_s: float
    duration_s: float
    compressor_throughput_kg_s: float
    release_mass_flow_kg_s: float
    released_mass_kg: float
    released_enthalpy_j: float
    origin: Origin
    time_mapping_evidence_id: str
    release_flow_evidence_id: str
    _issuer_token: object = field(default=None, repr=False, compare=False)
    _seal: str = field(default="", init=False, repr=False, compare=False)

    def __post_init__(self):
        if self._issuer_token not in _PENDING_ISSUERS:
            raise TypeError("Issue compressor-discharge sources through bind_compressor_discharge_source")
        _PENDING_ISSUERS.remove(self._issuer_token)
        object.__setattr__(self, "_issuer_token", None)
        self.require_current()
        object.__setattr__(self, "_seal", self._content())

    def _content(self):
        return hashlib.sha256(repr((
            id(self.compressor), id(self.location), id(self.source), id(self.state),
            self.source._fingerprint, self.start_time_s, self.end_time_s,
            self.duration_s, self.compressor_throughput_kg_s,
            self.release_mass_flow_kg_s, self.released_mass_kg,
            self.released_enthalpy_j, self.origin,
            self.time_mapping_evidence_id, self.release_flow_evidence_id,
        )).encode()).hexdigest()

    def require_current(self):
        projected = _project(
            self.compressor, location=self.location,
            start_time_s=self.start_time_s, end_time_s=self.end_time_s,
            release_mass_flow_kg_s=self.release_mass_flow_kg_s,
            origin=self.origin,
            time_mapping_evidence_id=self.time_mapping_evidence_id,
            release_flow_evidence_id=self.release_flow_evidence_id,
        )
        source, state, start, end, duration, throughput, rate, mass, enthalpy, origin, time_id, flow_id = projected
        self.source.require_current()
        if (self.source._fingerprint != source._fingerprint
                or self.state != state
                or (self.start_time_s, self.end_time_s, self.duration_s,
                    self.compressor_throughput_kg_s, self.release_mass_flow_kg_s,
                    self.released_mass_kg, self.released_enthalpy_j, self.origin,
                    self.time_mapping_evidence_id, self.release_flow_evidence_id)
                   != (start, end, duration, throughput, rate, mass, enthalpy,
                       origin, time_id, flow_id)):
            raise ValueError("Compressor discharge finite-source mapping changed")
        if self._seal and self._content() != self._seal:
            raise ValueError("Compressor discharge source identity or payload changed after issue")
        return self


def bind_compressor_discharge_source(
    compressor: HydrogenRealFluidCompressionRun,
    *,
    location: SourceLocation,
    start_time_s: float,
    end_time_s: float,
    release_mass_flow_kg_s: float,
    origin: Origin,
    time_mapping_evidence_id: str,
    release_flow_evidence_id: str,
) -> CompressorDischargeSource:
    """Project a caller-declared throughflow leak window to finite H2 source.

    ``release_mass_flow_kg_s`` and its evidence are caller supplied and cannot
    exceed the compressor's accepted throughput. Compressor outlet state,
    location and physical interval remain exact. No leak-size, nozzle, valve,
    choked-flow or downstream dispersion calculation is performed.
    """
    projected = _project(
        compressor, location=location, start_time_s=start_time_s,
        end_time_s=end_time_s, release_mass_flow_kg_s=release_mass_flow_kg_s,
        origin=origin, time_mapping_evidence_id=time_mapping_evidence_id,
        release_flow_evidence_id=release_flow_evidence_id,
    )
    source, state, start, end, duration, throughput, rate, mass, enthalpy, source_origin, time_id, flow_id = projected
    token = object()
    _PENDING_ISSUERS.add(token)
    try:
        result = CompressorDischargeSource(
            compressor, location, source, state, start, end, duration,
            throughput, rate, mass, enthalpy, source_origin, time_id, flow_id,
            _issuer_token=token,
        )
    except Exception:
        _PENDING_ISSUERS.discard(token)
        raise
    return result.require_current()


__all__ = ["CompressorDischargeSource", "bind_compressor_discharge_source"]
