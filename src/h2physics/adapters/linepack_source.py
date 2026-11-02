"""Typed handoff from an existing linepack owner to a finite source.

Native real-gas inputs delegate to the existing CoolProp source adapter.
The explicit ideal owner remains an analytical verification route.
"""

from dataclasses import dataclass, field
from hashlib import sha256
from math import isclose

from ..core import Origin, ThermoState
from ..pipeline_linepack import IsothermalLinepackState, LinepackStepLedger
from ..release import SourceLocation
from ..sources import IntervalMassSource

_PENDING_LINEPACK_SOURCES: set[object] = set()
_R_UNIVERSAL_J_MOL_K = 8.31446261815324
_H2_MOLAR_MASS_KG_MOL = 0.00201588


def _signature(before, after, ledger, source, state_projection_evidence_id):
    return sha256(repr((id(before), id(after), id(ledger), id(source),
        before, after, ledger, source._fingerprint,
        state_projection_evidence_id)).encode()).hexdigest()


@dataclass(frozen=True, slots=True)
class LinepackSourceHandoff:
    initial: IsothermalLinepackState
    final: IsothermalLinepackState
    ledger: LinepackStepLedger
    source: IntervalMassSource
    state_projection_evidence_id: str
    _issuer: object = field(default=None, repr=False, compare=False)
    _issued: object = field(default=None, init=False, repr=False, compare=False)
    _seal: str = field(default="", init=False, repr=False, compare=False)

    def __post_init__(self):
        if self._issuer not in _PENDING_LINEPACK_SOURCES:
            raise TypeError("Create linepack source receipts through advance_linepack_to_source")
        _PENDING_LINEPACK_SOURCES.remove(self._issuer)
        object.__setattr__(self, "_issued", self._issuer)
        object.__setattr__(self, "_seal", _signature(
            self.initial, self.final, self.ledger, self.source,
            self.state_projection_evidence_id))

    def _signature(self):
        return _signature(self.initial, self.final, self.ledger, self.source,
                          self.state_projection_evidence_id)

    def require_current(self):
        if self._issuer is not self._issued:
            raise ValueError("Linepack handoff lost its original issuer")
        if (type(self.initial) is not IsothermalLinepackState
                or type(self.final) is not IsothermalLinepackState
                or type(self.ledger) is not LinepackStepLedger
                or type(self.source) is not IntervalMassSource):
            raise TypeError("Linepack receipt must retain its exact native model objects")
        self.source.require_current()
        row = self.ledger
        if (row.start_time_s != self.initial.time_s
                or row.end_time_s != self.final.time_s
                or row.initial_mass_kg != self.initial.mass_kg
                or row.final_mass_kg != self.final.mass_kg
                or self.initial.volume_m3 != self.final.volume_m3
                or self.initial.temperature_k != self.final.temperature_k
                or self.initial.molecular_mass_kg_mol != self.final.molecular_mass_kg_mol
                or abs(row.mass_residual_kg) > 1e-12*max(1., row.initial_mass_kg)
                or not isclose(row.inlet_mass_kg-row.outlet_mass_kg,
                               self.final.mass_kg-self.initial.mass_kg,
                               rel_tol=1e-12, abs_tol=1e-15)
                or self.source.edges_s.tolist() != [row.start_time_s, row.end_time_s]
                or self.source.mass_kg.tolist() != [row.outlet_mass_kg]
                or self.source.state.pressure_pa < min(row.initial_pressure_pa, row.final_pressure_pa)
                or self.source.state.pressure_pa > max(row.initial_pressure_pa, row.final_pressure_pa)
                or not isclose(self.source.state.temperature_k, self.initial.temperature_k,
                               rel_tol=1e-12, abs_tol=1e-10)
                or self.source.state.basis.fluid != "H2"
                or self.source.state.phase != "gas"
                or self._signature() != self._seal):
            raise ValueError("Linepack inventory, port ledger, source state or handoff changed")
        return self


def advance_linepack_to_source(initial, *, duration_s,
        inlet_mass_flow_kg_s, outlet_mass_flow_kg_s, minimum_mass_kg,
        location: SourceLocation, gas_state: ThermoState, origin: Origin,
        evidence_id: str, state_projection_evidence_id: str, properties=None):
    """Advance a lumped linepack and expose its withdrawal as an IntervalMassSource.

    For a ``RealGasLinepackState``, supply the matching CoolProp ``properties``;
    the existing native source adapter owns all EOS, identity and receipt checks.
    No alternative property calculation is introduced by this dispatcher.

    For an explicit ideal verification state, ``gas_state`` is a caller-supplied
    representative outlet state. Its pressure
    must lie between the accepted endpoint pressures, and its density must obey
    the same ideal-H2 relation as the linepack. The projection evidence records
    why that one state represents the interval; no intra-step thermodynamic path
    is reconstructed.
    """
    from ..real_gas_linepack import RealGasLinepackState

    if type(initial) is RealGasLinepackState:
        from .real_gas_linepack_source import advance_real_gas_linepack_to_source

        return advance_real_gas_linepack_to_source(
            initial, duration_s=duration_s,
            inlet_mass_flow_kg_s=inlet_mass_flow_kg_s,
            outlet_mass_flow_kg_s=outlet_mass_flow_kg_s,
            minimum_mass_kg=minimum_mass_kg, location=location, gas_state=gas_state,
            properties=properties, origin=origin, evidence_id=evidence_id,
            state_projection_evidence_id=state_projection_evidence_id,
        )
    if properties is not None:
        raise ValueError("Native properties require a native real-gas linepack owner")
    if type(initial) is not IsothermalLinepackState:
        raise TypeError("Supply an IsothermalLinepackState")
    if not isclose(initial.molecular_mass_kg_mol, _H2_MOLAR_MASS_KG_MOL,
                   rel_tol=1e-8, abs_tol=0.):
        raise ValueError("This source bridge requires the declared molecular mass of H2")
    if type(location) is not SourceLocation or type(gas_state) is not ThermoState:
        raise TypeError("Supply typed source location and representative H2 gas state")
    for label, value in (("source evidence", evidence_id),
                         ("state projection evidence", state_projection_evidence_id)):
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"Declare {label}")
    if location.clock_id == "" or location.coordinate_frame_id == "":
        raise ValueError("A linepack withdrawal needs an explicit source clock and frame")
    if (gas_state.basis.fluid != "H2" or gas_state.phase != "gas"
            or gas_state.vapor_mass_fraction not in (None, 1.)):
        raise ValueError("Linepack source state must be single-phase gaseous H2")
    if Origin(origin) == Origin.UNRESOLVED:
        raise ValueError("Resolve the origin of the linepack withdrawal")
    expected_density = (gas_state.pressure_pa*initial.molecular_mass_kg_mol
                        / (_R_UNIVERSAL_J_MOL_K*gas_state.temperature_k))
    if (not isclose(gas_state.temperature_k, initial.temperature_k,
                    rel_tol=1e-12, abs_tol=1e-10)
            or not isclose(gas_state.density_kg_m3, expected_density,
                           rel_tol=1e-8, abs_tol=1e-12)):
        raise ValueError("Representative H2 state does not share the linepack ideal-gas basis")
    final, ledger = initial.advance(duration_s=duration_s,
        inlet_mass_flow_kg_s=inlet_mass_flow_kg_s,
        outlet_mass_flow_kg_s=outlet_mass_flow_kg_s,
        minimum_mass_kg=minimum_mass_kg)
    if ledger.outlet_mass_kg <= 0.:
        raise ValueError("A finite withdrawal source requires positive integrated outlet mass")
    source = IntervalMassSource(location, [ledger.start_time_s, ledger.end_time_s],
        [ledger.outlet_mass_kg], gas_state, Origin(origin),
        ":".join((evidence_id.strip(), state_projection_evidence_id.strip())),
        "window_end")
    token = object()
    _PENDING_LINEPACK_SOURCES.add(token)
    try:
        receipt = LinepackSourceHandoff(initial, final, ledger, source,
            state_projection_evidence_id.strip(), token)
    except Exception:
        _PENDING_LINEPACK_SOURCES.discard(token)
        raise
    return receipt.require_current()
