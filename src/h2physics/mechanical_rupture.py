"""Finite stored-pressure expansion reference and explicit rupture-load handoff.

This closed-inventory, reversible adiabatic reference is not a BLEVE prediction.
CoolProp owns all fluid thermodynamics. A separate qualified provider owns the
shock waveform; chemical combustion energy is never inferred from pressure work.

Context on model dependence of hydrogen physical-explosion estimates:
https://www.cetjournal.it/index.php/cet/article/view/CET2291071
Native state inputs: https://coolprop.org/coolprop/LowLevelAPI.html
"""

from dataclasses import dataclass
from typing import Protocol

import numpy as np

from .core import ThermoState, _real_numeric_array, finite, immutable_array
from .pressure_loads import PressureTimeHistory
from .thermo.coolprop import CoolPropProperties


@dataclass(frozen=True, slots=True)
class IsentropicExpansionEnergy:
    source_id: str
    inventory_mass_kg: float
    initial_state: ThermoState
    final_state: ThermoState
    gross_expansion_work_j: float
    ambient_displacement_work_j: float
    net_mechanical_work_j: float
    native_version: str

    def __post_init__(self):
        for name in ("source_id", "native_version"):
            if not isinstance(getattr(self, name), str) or not getattr(self, name).strip():
                raise ValueError("Source and native property version identities are required")
        finite(self.inventory_mass_kg, "inventory mass", positive=True)
        self.initial_state.basis.require_compatible(self.final_state.basis)
        for name in ("gross_expansion_work_j", "ambient_displacement_work_j", "net_mechanical_work_j"):
            finite(getattr(self, name), name)
        if self.net_mechanical_work_j < 0:
            raise ValueError("Mechanical energy must be nonnegative")
        scale = max(abs(self.gross_expansion_work_j), 1.)
        if abs(self.gross_expansion_work_j-self.ambient_displacement_work_j
               -self.net_mechanical_work_j) > 1e-10*scale:
            raise ValueError("Mechanical energy balance does not close")


def isentropic_expansion_energy(properties: CoolPropProperties, *, source_id: str,
                                inventory_mass_kg: float, initial_pressure_pa: float,
                                initial_temperature_k: float,
                                ambient_pressure_pa: float) -> IsentropicExpansionEnergy:
    """Evaluate m*(u1-u2) - p0*m*(v2-v1), with p2=p0 and s2=s1.

    This is net useful work along the stated reversible path, excluding ambient
    displacement. It is not the complete thermal exergy, vessel strain energy,
    a shock-conversion efficiency, or chemical energy. The initial stock is a
    homogeneous equilibrium state; stratified tanks need a different model.
    Two-phase endpoints are retained when the native state solver supports them.
    """
    if not isinstance(properties, CoolPropProperties) or properties.backend != "HEOS":
        raise TypeError("This reference requires direct CoolProp HEOS properties")
    if not isinstance(source_id, str) or not source_id.strip():
        raise ValueError("Declare the finite inventory/source identity")
    mass = finite(inventory_mass_kg, "inventory mass", positive=True)
    p1 = finite(initial_pressure_pa, "initial pressure", positive=True)
    p0 = finite(ambient_pressure_pa, "ambient pressure", positive=True)
    if p1 < p0:
        raise ValueError("Expansion reference requires initial pressure >= ambient pressure")
    initial = properties.state_pt(p1, finite(initial_temperature_k, "temperature", positive=True))
    final = properties.state_ps(p0, initial.entropy_j_kg_k) if p1 != p0 else initial
    initial.basis.require_compatible(final.basis)
    gross = mass*(initial.internal_energy_j_kg-final.internal_energy_j_kg)
    displacement = p0*mass*(1/final.density_kg_m3-1/initial.density_kg_m3)
    net = gross-displacement
    tolerance = 1e-8*max(abs(gross), abs(displacement), 1.)
    if min(gross, displacement, net) < -tolerance:
        raise ValueError("Native states do not yield nonnegative expansion work on this path")
    if net < 0:
        raise ValueError("Expansion energy is unresolved at the native numerical precision")
    return IsentropicExpansionEnergy(source_id, mass, initial, final, gross, displacement,
                                     net, properties.version)


@dataclass(frozen=True, slots=True)
class MechanicalEnergyAllocation:
    """Caller-declared disjoint shares; no universal shock fraction is assumed."""

    expansion: IsentropicExpansionEnergy
    shock_fraction: float
    fragment_fraction: float
    wall_fraction: float
    allocation_evidence_id: str

    def __post_init__(self):
        if type(self.expansion) is not IsentropicExpansionEnergy:
            raise TypeError("A mechanical expansion reference is required, not chemical energy")
        fractions = [finite(getattr(self, name), name) for name in
                     ("shock_fraction", "fragment_fraction", "wall_fraction")]
        if any(x < 0 or x > 1 for x in fractions) or sum(fractions) > 1:
            raise ValueError("Disjoint mechanical energy fractions must be nonnegative and sum <= 1")
        if not isinstance(self.allocation_evidence_id, str) or not self.allocation_evidence_id.strip():
            raise ValueError("Declare allocation assumptions or calibration evidence")

    @property
    def shock_energy_j(self):
        return self.expansion.net_mechanical_work_j*self.shock_fraction

    @property
    def fragment_energy_j(self):
        return self.expansion.net_mechanical_work_j*self.fragment_fraction

    @property
    def wall_energy_j(self):
        return self.expansion.net_mechanical_work_j*self.wall_fraction

    @property
    def remaining_energy_j(self):
        return self.expansion.net_mechanical_work_j*(
            1-self.shock_fraction-self.fragment_fraction-self.wall_fraction)


@dataclass(frozen=True, slots=True)
class MechanicalLoadRequest:
    allocation: MechanicalEnergyAllocation
    distance_m: float
    clock_id: str
    load_id: str

    def __post_init__(self):
        if type(self.allocation) is not MechanicalEnergyAllocation:
            raise TypeError("Supply a mechanical energy allocation")
        finite(self.distance_m, "receptor distance", positive=True)
        for value in (self.clock_id, self.load_id):
            if not isinstance(value, str) or not value.strip():
                raise ValueError("Load and actual event clock identities are required")


class MechanicalPressureProvider(Protocol):
    """External blast owner must check its own geometry/phase/energy domain."""

    def pressure_history(self, request: MechanicalLoadRequest) -> PressureTimeHistory: ...


class SphericalAcousticPulse:
    """Normalize a supplied waveform to mechanical acoustic energy in a free field.

    E = 4*pi*r^2/(rho*c) * integral(p^2 dt) for an outgoing, linear far-field
    wave. This is a conditional weak-wave reference, not a strong-shock/BLEVE
    correlation. Pulse shape, duration, far-field distance and conversion share
    are explicit inputs; no tank-rupture waveform is invented.

    Acoustic basis: NASA/SP-2015-624, acoustics and noise control,
    https://ntrs.nasa.gov/api/citations/20160000818/downloads/20160000818.pdf
    """

    def __init__(self, ambient_properties: CoolPropProperties, *, ambient_pressure_pa: float,
                 ambient_temperature_k: float, time_s, dimensionless_shape,
                 minimum_distance_m: float, maximum_pressure_to_ambient_ratio: float,
                 assumption_evidence_id: str):
        if (not isinstance(ambient_properties, CoolPropProperties)
                or ambient_properties.backend != "HEOS"):
            raise TypeError("Ambient properties require direct CoolProp HEOS")
        self.ambient_state = ambient_properties.state_pt(ambient_pressure_pa, ambient_temperature_k)
        if self.ambient_state.speed_of_sound_m_s is None or self.ambient_state.phase not in {
                "gas", "supercritical_gas", "supercritical"}:
            raise ValueError("The acoustic reference requires a single gas with native sound speed")
        time = _real_numeric_array(time_s, "waveform time")
        shape = _real_numeric_array(dimensionless_shape, "waveform shape")
        if (time.ndim != 1 or len(time) < 2 or shape.shape != time.shape
                or not np.all(np.isfinite(time)) or not np.all(np.isfinite(shape))
                or time[0] < 0 or np.any(np.diff(time) <= 0) or not np.any(shape)):
            raise ValueError("Supply an increasing finite clock and nonzero waveform shape")
        self.time_s = immutable_array(time)
        self.dimensionless_shape = immutable_array(shape)
        # Exact square integral of the declared piecewise-linear shape, rather
        # than trapezoidal integration of sampled p^2 (a different interpolant).
        self.shape_square_integral_s = float(np.sum(np.diff(time)*(
            shape[:-1]**2+shape[:-1]*shape[1:]+shape[1:]**2)/3))
        if not np.isfinite(self.shape_square_integral_s) or self.shape_square_integral_s <= 0:
            raise ValueError("Waveform square integral must be resolved and positive")
        self.minimum_distance_m = finite(minimum_distance_m, "minimum far-field distance", positive=True)
        ratio = finite(maximum_pressure_to_ambient_ratio, "linear pressure-ratio gate", positive=True)
        if ratio > .1:
            raise ValueError("Select a small-pressure acceptance gate <= 0.1 for this linear reference")
        self.maximum_pressure_to_ambient_ratio = ratio
        if not isinstance(assumption_evidence_id, str) or not assumption_evidence_id.strip():
            raise ValueError("Declare evidence for the supplied shape and free-field assumptions")
        self.assumption_evidence_id = assumption_evidence_id

    def pressure_history(self, request: MechanicalLoadRequest) -> PressureTimeHistory:
        if type(request) is not MechanicalLoadRequest:
            raise TypeError("Supply a mechanical load request")
        if request.distance_m < self.minimum_distance_m:
            raise ValueError("Distance is below the caller's declared far-field limit")
        ambient = self.ambient_state
        if not np.isclose(request.allocation.expansion.final_state.pressure_pa, ambient.pressure_pa,
                          rtol=1e-9, atol=1e-6):
            raise ValueError("Expansion and acoustic ambient pressures must agree")
        amplitude = np.sqrt(request.allocation.shock_energy_j*ambient.density_kg_m3
                            *ambient.speed_of_sound_m_s/(
                                4*np.pi*request.distance_m**2*self.shape_square_integral_s))
        pressure = amplitude*self.dimensionless_shape
        if np.max(np.abs(pressure))/ambient.pressure_pa > self.maximum_pressure_to_ambient_ratio:
            raise ValueError("Pulse exceeds the declared linear-acoustic pressure gate")
        return PressureTimeHistory(self.time_s, pressure, request.clock_id, request.load_id,
                                   self.assumption_evidence_id)


@dataclass(frozen=True, slots=True)
class MechanicalRuptureLoad:
    request: MechanicalLoadRequest
    pressure: PressureTimeHistory


def mechanical_rupture_load(request: MechanicalLoadRequest,
                            provider: MechanicalPressureProvider) -> MechanicalRuptureLoad:
    """Hand mechanical energy to an explicit pressure owner without TNT substitution.

    A caller may supply a measured waveform provider. The local energy reference
    alone cannot determine pulse duration, reflection or peak pressure. A single
    receptor history does not independently establish total radiated energy.
    """
    if type(request) is not MechanicalLoadRequest:
        raise TypeError("Supply an identified mechanical load request")
    pressure = provider.pressure_history(request)
    if type(pressure) is not PressureTimeHistory:
        raise TypeError("Provider must return an actual-event PressureTimeHistory")
    if (pressure.clock_id, pressure.load_id) != (request.clock_id, request.load_id):
        raise ValueError("Pressure provider returned a different event clock or load")
    return MechanicalRuptureLoad(request, pressure)
