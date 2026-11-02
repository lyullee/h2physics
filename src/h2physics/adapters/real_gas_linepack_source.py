"""Finite real-gas linepack withdrawal through the existing CoolProp EOS.

This boundary projects a mass interval, not an enthalpy integral or pressure
regulator. Integrated energy and conditioning remain separate caller evidence.
"""

from dataclasses import dataclass, field
from hashlib import sha256
from math import isclose

from ..core import Origin, ThermoState
from ..real_gas_linepack import RealGasLinepackState, RealGasLinepackStepLedger
from ..release import SourceLocation
from ..sources import IntervalMassSource
from ..thermo import CoolPropIsothermalEOS, CoolPropProperties

_PENDING: set[object] = set()


def _definitions(eos, properties):
    return (id(eos), eos.identity, eos.fluid, eos.backend, eos.version,
            id(eos._state), eos.density_pt, eos.pressure_rho_t,
            id(properties), properties.basis, properties.backend, properties.version,
            id(properties._state), properties.state_pt,
            properties.molar_mass_kg_mol)


@dataclass(frozen=True, slots=True)
class RealGasLinepackSourceHandoff:
    initial: RealGasLinepackState
    final: RealGasLinepackState
    ledger: RealGasLinepackStepLedger
    source: IntervalMassSource
    properties: CoolPropProperties = field(repr=False, compare=False)
    state_projection_evidence_id: str
    _issuer: object = field(default=None, repr=False, compare=False)
    _definitions: tuple = field(default=(), init=False, repr=False, compare=False)
    _seal: str = field(default="", init=False, repr=False, compare=False)

    def __post_init__(self):
        if self._issuer not in _PENDING:
            raise TypeError("Issue through advance_real_gas_linepack_to_source")
        _PENDING.remove(self._issuer)
        object.__setattr__(self, "_definitions", _definitions(self.initial.eos, self.properties))
        object.__setattr__(self, "_seal", self._content())

    @property
    def hydrogen_molar_mass_kg_mol(self):
        self.require_current()
        return self.properties.molar_mass_kg_mol

    def _content(self):
        return sha256(repr((id(self.initial), self.initial, id(self.final), self.final,
            id(self.ledger), self.ledger, id(self.source), self.source._fingerprint,
            id(self.properties), self.state_projection_evidence_id,
            self._definitions, id(self._issuer))).encode()).hexdigest()

    def require_current(self):
        if self._seal != self._content() or self._definitions != _definitions(
                self.initial.eos, self.properties):
            raise ValueError("Real-gas source lineage or property definition changed")
        self.source.require_current()
        before, after, row, state = self.initial, self.final, self.ledger, self.source.state
        if (type(before) is not RealGasLinepackState or type(after) is not RealGasLinepackState
                or type(row) is not RealGasLinepackStepLedger or after.eos is not before.eos
                or row.eos_identity != before.eos_identity or after.eos_identity != before.eos_identity
                or before.eos.identity != before.eos_identity
                or before.volume_m3 != after.volume_m3 or before.temperature_k != after.temperature_k
                or row.start_time_s != before.time_s or row.end_time_s != after.time_s
                or row.initial_mass_kg != before.mass_kg or row.final_mass_kg != after.mass_kg
                or row.initial_pressure_pa != before.pressure_pa or row.final_pressure_pa != after.pressure_pa
                or self.source.edges_s.tolist() != [before.time_s, after.time_s]
                or self.source.mass_kg.tolist() != [row.outlet_mass_kg]
                or abs(row.mass_residual_kg) > 1e-12 * max(before.mass_kg, 1.)
                or not isclose(row.inlet_mass_kg-row.outlet_mass_kg,
                               after.mass_kg-before.mass_kg, rel_tol=1e-12, abs_tol=1e-14)
                or not min(before.pressure_pa, after.pressure_pa) <= state.pressure_pa <= max(
                    before.pressure_pa, after.pressure_pa)
                or state.temperature_k != before.temperature_k):
            raise ValueError("Real-gas mass ledger, time interval or outlet-state bounds differ")
        self.properties.basis.require_compatible(state.basis)
        replay = self.properties.state_pt(state.pressure_pa, state.temperature_k)
        for name in ("density_kg_m3", "enthalpy_j_kg", "internal_energy_j_kg", "entropy_j_kg_k"):
            if not isclose(getattr(state, name), getattr(replay, name), rel_tol=1e-10, abs_tol=1e-8):
                raise ValueError("Representative outlet differs from its native CoolProp state")
        if state.phase != replay.phase or state.phase not in {"gas", "supercritical_gas", "supercritical"}:
            raise ValueError("Real-gas linepack outlet must remain homogeneous hydrogen gas")
        for name in ("cp_j_kg_k", "cv_j_kg_k", "viscosity_pa_s", "conductivity_w_m_k",
                     "speed_of_sound_m_s", "vapor_mass_fraction", "raw_vapor_mass_fraction"):
            actual, expected = getattr(state, name), getattr(replay, name)
            if ((actual is None or expected is None) and actual != expected
                    or actual is not None and expected is not None
                    and not isclose(actual, expected, rel_tol=1e-10, abs_tol=1e-12)):
                raise ValueError("Representative outlet transport/phase properties differ from CoolProp")
        for endpoint in (before, after):
            native_density = self.properties.state_pt(endpoint.pressure_pa, endpoint.temperature_k).density_kg_m3
            if not isclose(native_density, endpoint.density_kg_m3, rel_tol=1e-8, abs_tol=1e-10):
                raise ValueError("Linepack EOS and outlet properties do not share a density basis")
        return self


def advance_real_gas_linepack_to_source(initial: RealGasLinepackState, *, duration_s,
        inlet_mass_flow_kg_s, outlet_mass_flow_kg_s, minimum_mass_kg,
        location: SourceLocation, gas_state: ThermoState, properties: CoolPropProperties,
        origin: Origin, evidence_id: str, state_projection_evidence_id: str):
    """Advance the existing real-gas owner and issue its accepted withdrawal bin.

    The representative outlet must be an actual CoolProp HEOS Hydrogen state
    within the accepted pressure endpoints at the owner's held temperature.
    This records no integrated enthalpy or thermal-conditioning calculation.
    """
    if type(initial) is not RealGasLinepackState or type(initial.eos) is not CoolPropIsothermalEOS:
        raise TypeError("Supply the existing real-gas linepack with its CoolProp isothermal EOS")
    if (type(properties) is not CoolPropProperties or properties.basis.fluid != "Hydrogen"
            or initial.eos.fluid != "Hydrogen" or properties.backend != "HEOS"
            or properties.version != initial.eos.version):
        raise ValueError("Use matched direct CoolProp HEOS Hydrogen providers")
    if type(location) is not SourceLocation or type(gas_state) is not ThermoState:
        raise TypeError("Supply typed source location and native outlet state")
    for value in (evidence_id, state_projection_evidence_id, location.clock_id, location.coordinate_frame_id):
        if not isinstance(value, str) or not value.strip():
            raise ValueError("Declare source, projection, clock and frame evidence")
    selected_origin = Origin(origin)
    if selected_origin is Origin.UNRESOLVED:
        raise ValueError("Resolve the source origin")
    final, ledger = initial.advance(duration_s=duration_s,
        inlet_mass_flow_kg_s=inlet_mass_flow_kg_s, outlet_mass_flow_kg_s=outlet_mass_flow_kg_s,
        minimum_mass_kg=minimum_mass_kg)
    if ledger.outlet_mass_kg <= 0.:
        raise ValueError("Withdrawal must have positive integrated mass")
    source = IntervalMassSource(location, [initial.time_s, final.time_s],
        [ledger.outlet_mass_kg], gas_state, selected_origin,
        evidence_id.strip() + ":" + state_projection_evidence_id.strip(), "window_end")
    token = object()
    _PENDING.add(token)
    try:
        receipt = RealGasLinepackSourceHandoff(initial, final, ledger, source, properties,
            state_projection_evidence_id.strip(), token)
    finally:
        _PENDING.discard(token)
    return receipt.require_current()
