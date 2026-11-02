"""Conservative material-energy estimate for hydrogen transfer-line cooldown.

This is an inventory/duty calculation, not a transient pipe-flow or conjugate
heat-transfer solver. The caller supplies the per-zone wall and trapped-fluid
state changes and a stream enthalpy rise that it considers achievable.
"""

from __future__ import annotations

import hashlib
import math
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from dataclasses import field as dataclass_field

import numpy as np

from .core import PropertyBasis, PropertyProvider, ThermoState, finite

HeatCapacity = Callable[[float], float]
SpecificEnthalpy = Callable[[float, float], float]


def _cooldown_receipt_fingerprint(estimate: LineCooldownEstimate) -> str:
    """Fingerprint retained declarations and accounting values (not callback closures)."""
    segment_rows = []
    for segment in estimate.segments:
        segment_rows.append((
            segment.segment_id, segment.wall_mass_kg,
            segment.wall_initial_temperature_k, segment.wall_target_temperature_k,
            segment.fluid_mass_kg, segment.fluid_pressure_pa,
            segment.fluid_initial_temperature_k, segment.fluid_target_temperature_k,
            segment.quadrature_order, id(segment.solid_cp_j_kg_k),
            id(segment.fluid_enthalpy_j_kg),
        ))
    payload = repr((
        tuple(segment_rows), estimate.segment_duties, estimate._wall_energy_j,
        estimate._contained_fluid_energy_j, estimate.additional_heat_j,
        estimate.design_factor, estimate._required_cooling_energy_j,
        estimate.coolant_enthalpy_rise_j_kg, estimate._minimum_hydrogen_mass_kg,
        estimate.evidence_ids, estimate.coolant_inlet_enthalpy_j_kg,
        estimate.coolant_outlet_enthalpy_j_kg,
    )).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _property_path_fingerprint(path: IsobaricEnthalpyPath) -> str:
    payload = repr((
        id(path.provider), path.pressure_pa, path.evidence_id,
        path.allowed_phases, path._basis,
    )).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _property_cooldown_fingerprint(
    result: PropertyBackedLineCooldownEstimate,
) -> str:
    payload = repr((
        result.estimate._receipt_fingerprint,
        _property_path_fingerprint(result.coolant_path),
        result.inlet_temperature_k, result.outlet_temperature_k,
        result.inlet_state, result.outlet_state,
    )).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


@dataclass(frozen=True, slots=True)
class IsobaricEnthalpyPath:
    """Bind an existing property provider to one evidence-bearing pressure path.

    The object is also a ``(temperature_k, pressure_pa) -> enthalpy_j_kg``
    callback, so it can be passed directly to ``CooldownSegment``. It never
    substitutes an ideal-gas or constant-cp property model.
    """

    provider: PropertyProvider
    pressure_pa: float
    evidence_id: str
    allowed_phases: tuple[str, ...]
    _basis: PropertyBasis = dataclass_field(init=False, repr=False, compare=False)
    _path_fingerprint: str = dataclass_field(init=False, repr=False, compare=False)

    def __post_init__(self):
        if not isinstance(self.provider, PropertyProvider):
            raise TypeError("Bind a common PropertyProvider with PT/PH/PS state methods")
        pressure = finite(self.pressure_pa, "isobaric path pressure", positive=True)
        if not isinstance(self.evidence_id, str) or not self.evidence_id.strip():
            raise ValueError("Identify the pressure-path property evidence")
        if isinstance(self.allowed_phases, str):
            raise TypeError("allowed_phases must be a sequence of phase IDs, not one string")
        phases = tuple(self.allowed_phases)
        if not phases or any(not isinstance(x, str) or not x.strip() for x in phases):
            raise ValueError("Declare at least one allowed property-provider phase")
        if len(set(phases)) != len(phases):
            raise ValueError("Allowed property phases must be unique")
        if not isinstance(self.provider.basis, PropertyBasis):
            raise TypeError("Property provider must expose its declared PropertyBasis")
        object.__setattr__(self, "pressure_pa", pressure)
        object.__setattr__(self, "allowed_phases", phases)
        object.__setattr__(self, "_basis", self.provider.basis)
        object.__setattr__(self, "_path_fingerprint", _property_path_fingerprint(self))

    @property
    def basis(self) -> PropertyBasis:
        return self._basis

    def state_at(self, temperature_k: float) -> ThermoState:
        temperature = finite(temperature_k, "property-path temperature", positive=True)
        if _property_path_fingerprint(self) != self._path_fingerprint:
            raise ValueError("Property path declarations changed after binding")
        if self.provider.basis != self._basis:
            raise ValueError("Property provider basis changed after path binding")
        state = self.provider.state_pt(self.pressure_pa, temperature)
        if not isinstance(state, ThermoState):
            raise TypeError("PropertyProvider.state_pt must return the shared ThermoState")
        if (state.basis != self._basis
                or not math.isclose(state.pressure_pa, self.pressure_pa,
                                    rel_tol=1e-12, abs_tol=1e-6)):
            raise ValueError("Property-provider state changed the bound basis or pressure")
        if state.phase not in self.allowed_phases:
            raise ValueError(
                f"Property phase {state.phase!r} is outside the declared cooldown path"
            )
        return state

    def enthalpy_j_kg(self, temperature_k: float, pressure_pa: float) -> float:
        pressure = finite(pressure_pa, "callback pressure", positive=True)
        if not math.isclose(pressure, self.pressure_pa, rel_tol=1e-12, abs_tol=1e-6):
            raise ValueError("Enthalpy callback pressure differs from its bound path")
        return self.state_at(temperature_k).enthalpy_j_kg

    def __call__(self, temperature_k: float, pressure_pa: float) -> float:
        return self.enthalpy_j_kg(temperature_k, pressure_pa)


def _integrate_heat_capacity(cp: HeatCapacity, start_k: float, end_k: float,
                             order: int) -> float:
    """Integrate a caller heat-capacity function with fixed Gauss-Legendre nodes."""
    nodes, weights = np.polynomial.legendre.leggauss(order)
    midpoint = (start_k + end_k) / 2.0
    half_width = (end_k - start_k) / 2.0
    values = np.asarray([finite(cp(float(midpoint + half_width * x)),
                                "solid heat capacity", positive=True) for x in nodes])
    return float(half_width * np.dot(weights, values))


@dataclass(frozen=True, slots=True)
class CooldownSegment:
    """One thermally lumped section of line hardware and contained hydrogen.

    Temperatures are Kelvin, pressures are absolute Pa, heat capacities are
    J/(kg K), enthalpies are J/kg, and masses are kg. The heat-capacity
    integral is evaluated along the supplied initial-to-target temperature
    path. A fluid enthalpy callback is required when ``fluid_mass_kg`` is nonzero.
    """

    segment_id: str
    wall_mass_kg: float
    solid_cp_j_kg_k: HeatCapacity
    wall_initial_temperature_k: float
    wall_target_temperature_k: float
    fluid_mass_kg: float = 0.0
    fluid_pressure_pa: float | None = None
    fluid_initial_temperature_k: float | None = None
    fluid_target_temperature_k: float | None = None
    fluid_enthalpy_j_kg: SpecificEnthalpy | None = None
    quadrature_order: int = 16

    def __post_init__(self):
        if not isinstance(self.segment_id, str) or not self.segment_id.strip():
            raise ValueError("segment_id must be nonempty text")
        finite(self.wall_mass_kg, "wall mass", positive=True)
        finite(self.wall_initial_temperature_k, "initial wall temperature", positive=True)
        finite(self.wall_target_temperature_k, "target wall temperature", positive=True)
        if self.wall_target_temperature_k > self.wall_initial_temperature_k:
            raise ValueError("Cooldown target cannot exceed initial wall temperature")
        if not callable(self.solid_cp_j_kg_k):
            raise ValueError("solid_cp_j_kg_k must be callable")
        finite(self.fluid_mass_kg, "contained fluid mass")
        if self.fluid_mass_kg < 0:
            raise ValueError("Contained fluid mass cannot be negative")
        if isinstance(self.quadrature_order, bool) or not isinstance(self.quadrature_order, int):
            raise ValueError("quadrature_order must be an integer")
        if not 2 <= self.quadrature_order <= 128:
            raise ValueError("quadrature_order must lie between 2 and 128")
        fluid_inputs = (self.fluid_pressure_pa, self.fluid_initial_temperature_k,
                        self.fluid_target_temperature_k, self.fluid_enthalpy_j_kg)
        if self.fluid_mass_kg > 0:
            if any(value is None for value in fluid_inputs):
                raise ValueError("Nonzero fluid inventory requires pressure, temperatures and enthalpy callback")
            finite(self.fluid_pressure_pa, "absolute fluid pressure", positive=True)
            finite(self.fluid_initial_temperature_k, "initial fluid temperature", positive=True)
            finite(self.fluid_target_temperature_k, "target fluid temperature", positive=True)
            if self.fluid_target_temperature_k > self.fluid_initial_temperature_k:
                raise ValueError("Cooldown target cannot exceed initial fluid temperature")
            if not callable(self.fluid_enthalpy_j_kg):
                raise ValueError("fluid_enthalpy_j_kg must be callable")
        elif any(value is not None for value in fluid_inputs):
            raise ValueError("Fluid state inputs must be omitted when contained fluid mass is zero")


@dataclass(frozen=True, slots=True)
class CooldownSegmentDuty:
    segment_id: str
    wall_energy_j: float
    contained_fluid_energy_j: float

    def __post_init__(self):
        if not isinstance(self.segment_id, str) or not self.segment_id.strip():
            raise ValueError("segment_id must be nonempty text")
        for name in ("wall_energy_j", "contained_fluid_energy_j"):
            finite(getattr(self, name), name)
            if getattr(self, name) < 0:
                raise ValueError(f"{name} cannot be negative for a cooling path")


@dataclass(frozen=True, slots=True, init=False)
class LineCooldownEstimate:
    """Energy-ledger receipt and ideal minimum coolant mass for one declared path."""

    segment_duties: tuple[CooldownSegmentDuty, ...]
    _wall_energy_j: float
    _contained_fluid_energy_j: float
    additional_heat_j: float
    design_factor: float
    _required_cooling_energy_j: float
    coolant_enthalpy_rise_j_kg: float
    _minimum_hydrogen_mass_kg: float
    evidence_ids: tuple[str, ...]
    segments: tuple[CooldownSegment, ...]
    coolant_inlet_enthalpy_j_kg: float
    coolant_outlet_enthalpy_j_kg: float
    _receipt_fingerprint: str = dataclass_field(init=False, repr=False, compare=False)

    def __init__(
        self,
        segment_duties: tuple[CooldownSegmentDuty, ...],
        wall_energy_j: float,
        contained_fluid_energy_j: float,
        additional_heat_j: float,
        design_factor: float,
        required_cooling_energy_j: float,
        coolant_enthalpy_rise_j_kg: float,
        minimum_hydrogen_mass_kg: float,
        evidence_ids: tuple[str, ...],
        segments: tuple[CooldownSegment, ...],
        coolant_inlet_enthalpy_j_kg: float,
        coolant_outlet_enthalpy_j_kg: float,
    ):
        object.__setattr__(self, "segment_duties", segment_duties)
        object.__setattr__(self, "_wall_energy_j", wall_energy_j)
        object.__setattr__(self, "_contained_fluid_energy_j", contained_fluid_energy_j)
        object.__setattr__(self, "additional_heat_j", additional_heat_j)
        object.__setattr__(self, "design_factor", design_factor)
        object.__setattr__(self, "_required_cooling_energy_j", required_cooling_energy_j)
        object.__setattr__(self, "coolant_enthalpy_rise_j_kg", coolant_enthalpy_rise_j_kg)
        object.__setattr__(self, "_minimum_hydrogen_mass_kg", minimum_hydrogen_mass_kg)
        object.__setattr__(self, "evidence_ids", evidence_ids)
        object.__setattr__(self, "segments", segments)
        object.__setattr__(self, "coolant_inlet_enthalpy_j_kg", coolant_inlet_enthalpy_j_kg)
        object.__setattr__(self, "coolant_outlet_enthalpy_j_kg", coolant_outlet_enthalpy_j_kg)
        self.__post_init__()

    def __post_init__(self):
        duties = tuple(self.segment_duties)
        segments = tuple(self.segments)
        if not duties or any(not isinstance(x, CooldownSegmentDuty) for x in duties):
            raise ValueError("At least one valid segment duty is required")
        if (len(segments) != len(duties)
                or any(not isinstance(x, CooldownSegment) for x in segments)
                or tuple(x.segment_id for x in segments)
                != tuple(x.segment_id for x in duties)):
            raise ValueError("Retain every source segment in the same order as its duty")
        if len({x.segment_id for x in duties}) != len(duties):
            raise ValueError("Segment IDs must be unique")
        object.__setattr__(self, "segment_duties", duties)
        object.__setattr__(self, "segments", segments)
        for name in ("_wall_energy_j", "_contained_fluid_energy_j", "additional_heat_j",
                     "_required_cooling_energy_j", "_minimum_hydrogen_mass_kg"):
            finite(getattr(self, name), name)
            if getattr(self, name) < 0:
                raise ValueError(f"{name} cannot be negative")
        finite(self.design_factor, "design factor", positive=True)
        if self.design_factor < 1.0:
            raise ValueError("design_factor must be at least one")
        finite(self.coolant_enthalpy_rise_j_kg, "coolant enthalpy rise", positive=True)
        h_in = finite(self.coolant_inlet_enthalpy_j_kg, "coolant inlet enthalpy")
        h_out = finite(self.coolant_outlet_enthalpy_j_kg, "coolant outlet enthalpy")
        if not math.isclose(h_out - h_in, self.coolant_enthalpy_rise_j_kg,
                            rel_tol=1e-12, abs_tol=1e-9):
            raise ValueError("Retained coolant endpoint enthalpies differ from the declared rise")
        if isinstance(self.evidence_ids, str):
            raise TypeError("evidence_ids must be a sequence of identities, not one string")
        ids = tuple(self.evidence_ids)
        if not ids or any(not isinstance(x, str) or not x.strip() for x in ids):
            raise ValueError("At least one nonempty evidence ID is required")
        object.__setattr__(self, "evidence_ids", ids)
        wall = math.fsum(x.wall_energy_j for x in duties)
        fluid = math.fsum(x.contained_fluid_energy_j for x in duties)
        expected = (wall + fluid + self.additional_heat_j) * self.design_factor
        if not math.isclose(wall, self._wall_energy_j, rel_tol=1e-12, abs_tol=1e-9):
            raise ValueError("Wall energy differs from retained segment ledger")
        if not math.isclose(fluid, self._contained_fluid_energy_j, rel_tol=1e-12, abs_tol=1e-9):
            raise ValueError("Fluid energy differs from retained segment ledger")
        if not math.isclose(expected, self._required_cooling_energy_j, rel_tol=1e-12, abs_tol=1e-9):
            raise ValueError("Required cooling energy differs from the ledger and design factor")
        if not math.isclose(self._required_cooling_energy_j / self.coolant_enthalpy_rise_j_kg,
                            self._minimum_hydrogen_mass_kg, rel_tol=1e-12, abs_tol=1e-12):
            raise ValueError("Minimum coolant mass differs from the energy balance")
        object.__setattr__(self, "_receipt_fingerprint", _cooldown_receipt_fingerprint(self))

    def require_current(self) -> LineCooldownEstimate:
        """Recompute retained source callbacks and reject stale ledger values.

        Callback internals that mutate but return identical values at the declared
        quadrature and endpoint states are observationally equivalent for this
        estimate; callers remain responsible for the provenance of those functions.
        """
        if _cooldown_receipt_fingerprint(self) != self._receipt_fingerprint:
            raise ValueError("Cooldown receipt declarations or ledger changed after estimation")
        current = estimate_line_cooldown(
            self.segments,
            coolant_inlet_enthalpy_j_kg=self.coolant_inlet_enthalpy_j_kg,
            coolant_outlet_enthalpy_j_kg=self.coolant_outlet_enthalpy_j_kg,
            additional_heat_j=self.additional_heat_j,
            design_factor=self.design_factor,
            evidence_ids=self.evidence_ids,
        )
        if _cooldown_receipt_fingerprint(current) != self._receipt_fingerprint:
            raise ValueError("Cooldown source callback or segment inputs changed after estimation")
        return self

    @property
    def wall_energy_j(self) -> float:
        self.require_current()
        return self._wall_energy_j

    @property
    def contained_fluid_energy_j(self) -> float:
        self.require_current()
        return self._contained_fluid_energy_j

    @property
    def required_cooling_energy_j(self) -> float:
        self.require_current()
        return self._required_cooling_energy_j

    @property
    def minimum_hydrogen_mass_kg(self) -> float:
        self.require_current()
        return self._minimum_hydrogen_mass_kg


@dataclass(frozen=True, slots=True)
class PropertyBackedLineCooldownEstimate:
    """Cooldown ledger with the exact shared-provider coolant endpoint states."""

    estimate: LineCooldownEstimate
    coolant_path: IsobaricEnthalpyPath
    inlet_temperature_k: float
    outlet_temperature_k: float
    inlet_state: ThermoState
    outlet_state: ThermoState
    _receipt_fingerprint: str = dataclass_field(init=False, repr=False, compare=False)

    def __post_init__(self):
        if type(self.estimate) is not LineCooldownEstimate:
            raise TypeError("Retain the actual line cooldown energy ledger")
        if type(self.coolant_path) is not IsobaricEnthalpyPath:
            raise TypeError("Retain the actual isobaric property path")
        inlet_t = finite(self.inlet_temperature_k, "coolant inlet temperature", positive=True)
        outlet_t = finite(self.outlet_temperature_k, "coolant outlet temperature", positive=True)
        if not isinstance(self.inlet_state, ThermoState) or not isinstance(self.outlet_state, ThermoState):
            raise TypeError("Retain the shared provider's coolant endpoint states")
        if self.inlet_state != self.coolant_path.state_at(inlet_t):
            raise ValueError("Coolant inlet state differs from the retained provider path")
        if self.outlet_state != self.coolant_path.state_at(outlet_t):
            raise ValueError("Coolant outlet state differs from the retained provider path")
        if (not math.isclose(self.estimate.coolant_inlet_enthalpy_j_kg,
                             self.inlet_state.enthalpy_j_kg, rel_tol=1e-12, abs_tol=1e-9)
                or not math.isclose(self.estimate.coolant_outlet_enthalpy_j_kg,
                                    self.outlet_state.enthalpy_j_kg,
                                    rel_tol=1e-12, abs_tol=1e-9)):
            raise ValueError(
                "Cooldown scalar coolant enthalpies differ from the retained provider endpoint states"
            )
        rise = self.outlet_state.enthalpy_j_kg-self.inlet_state.enthalpy_j_kg
        if (rise <= 0.0 or not math.isclose(
                rise, self.estimate.coolant_enthalpy_rise_j_kg,
                rel_tol=1e-12, abs_tol=1e-9)):
            raise ValueError("Cooldown ledger does not use the retained coolant enthalpy rise")
        if self.coolant_path.evidence_id not in self.estimate.evidence_ids:
            raise ValueError("Cooldown ledger omitted its coolant property-path evidence")
        object.__setattr__(self, "inlet_temperature_k", inlet_t)
        object.__setattr__(self, "outlet_temperature_k", outlet_t)
        object.__setattr__(self, "_receipt_fingerprint", _property_cooldown_fingerprint(self))

    def require_current(self) -> PropertyBackedLineCooldownEstimate:
        """Re-evaluate endpoint states and reject stale provider/source bindings."""
        if _property_cooldown_fingerprint(self) != self._receipt_fingerprint:
            raise ValueError("Provider-backed cooldown receipt changed after estimation")
        self.estimate.require_current()
        if (self.coolant_path.state_at(self.inlet_temperature_k) != self.inlet_state
                or self.coolant_path.state_at(self.outlet_temperature_k) != self.outlet_state):
            raise ValueError("Coolant property-provider endpoint changed after estimation")
        if (not math.isclose(self.estimate.coolant_inlet_enthalpy_j_kg,
                             self.inlet_state.enthalpy_j_kg, rel_tol=1e-12, abs_tol=1e-9)
                or not math.isclose(self.estimate.coolant_outlet_enthalpy_j_kg,
                                    self.outlet_state.enthalpy_j_kg,
                                    rel_tol=1e-12, abs_tol=1e-9)):
            raise ValueError("Cooldown scalar endpoint enthalpies no longer match provider states")
        rise = self.outlet_state.enthalpy_j_kg-self.inlet_state.enthalpy_j_kg
        if not math.isclose(
                rise, self.estimate.coolant_enthalpy_rise_j_kg,
                rel_tol=1e-12, abs_tol=1e-9):
            raise ValueError("Retained coolant states no longer reproduce the energy ledger")
        return self

    @property
    def minimum_hydrogen_mass_kg(self) -> float:
        self.require_current()
        return self.estimate.minimum_hydrogen_mass_kg

    @property
    def required_cooling_energy_j(self) -> float:
        self.require_current()
        return self.estimate.required_cooling_energy_j


def estimate_line_cooldown(
    segments: Sequence[CooldownSegment], *,
    coolant_inlet_enthalpy_j_kg: float,
    coolant_outlet_enthalpy_j_kg: float,
    additional_heat_j: float = 0.0,
    design_factor: float = 1.0,
    evidence_ids: Sequence[str],
) -> LineCooldownEstimate:
    """Estimate ideal H2 mass from caller-defined wall/fluid endpoint states.

    The computed quantity is a minimum under an enthalpy-only first-law balance:
    every kilogram of coolant is assigned the same positive enthalpy gain. Heat
    leak and other known loads belong in ``additional_heat_j``. No flow, wall-film,
    boiling, phase-front, axial conduction or outlet-state prediction is solved.
    """
    zones = tuple(segments)
    if not zones or any(not isinstance(zone, CooldownSegment) for zone in zones):
        raise ValueError("segments must contain at least one CooldownSegment")
    if len({zone.segment_id for zone in zones}) != len(zones):
        raise ValueError("Segment IDs must be unique")
    h_in = finite(coolant_inlet_enthalpy_j_kg, "coolant inlet enthalpy")
    h_out = finite(coolant_outlet_enthalpy_j_kg, "coolant outlet enthalpy")
    delta_h = h_out - h_in
    if delta_h <= 0:
        raise ValueError("Coolant enthalpy must increase across the declared cooling path")
    q_extra = finite(additional_heat_j, "additional heat")
    if q_extra < 0:
        raise ValueError("additional_heat_j cannot be negative")
    factor = finite(design_factor, "design factor", positive=True)
    if factor < 1.0:
        raise ValueError("design_factor must be at least one")
    if isinstance(evidence_ids, str):
        raise TypeError("evidence_ids must be a sequence of evidence identities, not one string")
    ids = tuple(evidence_ids)
    if not ids or any(not isinstance(x, str) or not x.strip() for x in ids):
        raise ValueError("At least one nonempty evidence ID is required")

    duties = []
    for zone in zones:
        cp_integral = _integrate_heat_capacity(
            zone.solid_cp_j_kg_k, zone.wall_target_temperature_k,
            zone.wall_initial_temperature_k, zone.quadrature_order,
        )
        wall_q = zone.wall_mass_kg * cp_integral
        fluid_q = 0.0
        if zone.fluid_mass_kg > 0:
            h_initial = finite(zone.fluid_enthalpy_j_kg(
                zone.fluid_initial_temperature_k, zone.fluid_pressure_pa),
                "initial contained-fluid enthalpy")
            h_target = finite(zone.fluid_enthalpy_j_kg(
                zone.fluid_target_temperature_k, zone.fluid_pressure_pa),
                "target contained-fluid enthalpy")
            fluid_q = zone.fluid_mass_kg * (h_initial - h_target)
            if fluid_q < -1e-9:
                raise ValueError("Contained-fluid target state has higher enthalpy than its initial state")
            fluid_q = max(fluid_q, 0.0)
        duties.append(CooldownSegmentDuty(zone.segment_id, wall_q, fluid_q))
    wall_total = math.fsum(x.wall_energy_j for x in duties)
    fluid_total = math.fsum(x.contained_fluid_energy_j for x in duties)
    required = (wall_total + fluid_total + q_extra) * factor
    return LineCooldownEstimate(
        tuple(duties), wall_total, fluid_total, q_extra, factor, required,
        delta_h, required / delta_h, ids, zones, h_in, h_out,
    )


def estimate_line_cooldown_with_provider(
    segments: Sequence[CooldownSegment],
    *,
    coolant_path: IsobaricEnthalpyPath,
    coolant_inlet_temperature_k: float,
    coolant_outlet_temperature_k: float,
    additional_heat_j: float = 0.0,
    design_factor: float = 1.0,
    evidence_ids: Sequence[str],
) -> PropertyBackedLineCooldownEstimate:
    """Estimate cooldown while retaining shared EOS coolant endpoint states."""
    if type(coolant_path) is not IsobaricEnthalpyPath:
        raise TypeError("Pass an evidence-bound IsobaricEnthalpyPath")
    inlet_t = finite(coolant_inlet_temperature_k, "coolant inlet temperature", positive=True)
    outlet_t = finite(coolant_outlet_temperature_k, "coolant outlet temperature", positive=True)
    inlet = coolant_path.state_at(inlet_t)
    outlet = coolant_path.state_at(outlet_t)
    if outlet.enthalpy_j_kg <= inlet.enthalpy_j_kg:
        raise ValueError("Coolant enthalpy must increase across the declared cooling path")
    if isinstance(evidence_ids, str):
        raise TypeError("evidence_ids must be a sequence of evidence identities, not one string")
    zones = tuple(segments)
    property_evidence = tuple(
        zone.fluid_enthalpy_j_kg.evidence_id
        for zone in zones
        if isinstance(zone, CooldownSegment)
        and isinstance(zone.fluid_enthalpy_j_kg, IsobaricEnthalpyPath)
    )
    ids = tuple(dict.fromkeys((
        *evidence_ids, coolant_path.evidence_id, *property_evidence,
    )))
    estimate = estimate_line_cooldown(
        zones,
        coolant_inlet_enthalpy_j_kg=inlet.enthalpy_j_kg,
        coolant_outlet_enthalpy_j_kg=outlet.enthalpy_j_kg,
        additional_heat_j=additional_heat_j,
        design_factor=design_factor,
        evidence_ids=ids,
    )
    return PropertyBackedLineCooldownEstimate(
        estimate,
        coolant_path,
        inlet_t,
        outlet_t,
        inlet,
        outlet,
    )


__all__ = [
    "CooldownSegment",
    "CooldownSegmentDuty",
    "IsobaricEnthalpyPath",
    "LineCooldownEstimate",
    "PropertyBackedLineCooldownEstimate",
    "estimate_line_cooldown",
    "estimate_line_cooldown_with_provider",
]
