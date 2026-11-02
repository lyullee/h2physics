"""Lumped PAR device balances with native gas thermochemistry.

This level combines a supplied device-capacity law with a chimney momentum
closure, an algebraic gas-energy balance and a finite catalyst heat capacity.
It does not replace a catalytic surface mechanism or predict gas-phase ignition.
The thermal/flow model is an authored reduction, not a reproduction of PARUPM.
See https://doi.org/10.1051/epjn/2022046 and the dedicated device manual for
model-level and reference distinctions.
"""

import math
from collections.abc import Callable
from dataclasses import dataclass
from types import MappingProxyType

import numpy as np
from scipy.integrate import solve_ivp
from scipy.optimize import brentq

from ..core import finite
from .cantera import CanteraGas, MechanismBasis, ReactiveState


def _nonnegative(value, name):
    if finite(value, name) < 0:
        raise ValueError(f"{name} cannot be negative")


@dataclass(frozen=True, slots=True)
class PARCapacityCondition:
    """Inputs to a measured/calibrated whole-device removal-capacity law."""

    catalyst_temperature_k: float
    inlet: ReactiveState
    inlet_mass_flow_kg_s: float


@dataclass(frozen=True, slots=True)
class PARCapacityLaw:
    """Explicit device capacity in mol H2/s, before finite-feed limitation.

    ``evidence_id`` identifies a calibration, manufacturer map or explicitly
    synthetic reference. Declaring it does not establish experimental validity.
    Callbacks must be deterministic and side-effect free during root solving.
    """

    evidence_id: str
    hydrogen_capacity_mol_s: Callable[[PARCapacityCondition], float]
    catalyst_temperature_bounds_k: tuple[float, float]
    inlet_temperature_bounds_k: tuple[float, float]
    pressure_bounds_pa: tuple[float, float]
    hydrogen_mole_fraction_bounds: tuple[float, float]
    oxygen_mole_fraction_bounds: tuple[float, float]
    maximum_mass_flow_kg_s: float

    def __post_init__(self):
        if not isinstance(self.evidence_id, str) or not self.evidence_id.strip():
            raise ValueError("Identify the device-capacity evidence")
        if not callable(self.hydrogen_capacity_mol_s):
            raise TypeError("Supply a device-capacity callable")
        for name in ("catalyst_temperature_bounds_k", "inlet_temperature_bounds_k",
                     "pressure_bounds_pa", "hydrogen_mole_fraction_bounds",
                     "oxygen_mole_fraction_bounds"):
            bounds = getattr(self, name)
            if len(bounds) != 2:
                raise ValueError(f"{name} needs two ordered bounds")
            lo, hi = bounds
            finite(lo, name)
            finite(hi, name)
            if not lo < hi:
                raise ValueError(f"{name} must increase")
            if "fraction" in name:
                if lo < 0 or hi > 1:
                    raise ValueError("Mole-fraction bounds must lie in [0, 1]")
            elif lo <= 0:
                raise ValueError("Temperature/pressure bounds must be positive")
            object.__setattr__(self, name, tuple(bounds))
        finite(self.maximum_mass_flow_kg_s, "maximum mass flow", positive=True)

    def evaluate(self, condition):
        inlet = condition.inlet
        for value, bounds in (
            (condition.catalyst_temperature_k, self.catalyst_temperature_bounds_k),
            (inlet.temperature_k, self.inlet_temperature_bounds_k),
            (inlet.pressure_pa, self.pressure_bounds_pa),
            (inlet.mole_fractions.get("H2", 0.), self.hydrogen_mole_fraction_bounds),
            (inlet.mole_fractions.get("O2", 0.), self.oxygen_mole_fraction_bounds),
        ):
            if not bounds[0] <= value <= bounds[1]:
                raise ValueError("PAR capacity input is outside its declared domain")
        if not 0 <= condition.inlet_mass_flow_kg_s <= self.maximum_mass_flow_kg_s:
            raise ValueError("PAR capacity flow is outside its declared domain")
        result = self.hydrogen_capacity_mol_s(condition)
        _nonnegative(result, "device hydrogen capacity")
        return float(result)


@dataclass(frozen=True, slots=True)
class PARDeviceParameters:
    """Caller-supplied lumped geometry and thermal coefficients, all SI.

    Loss coefficient uses inlet-area mass flux and the mean of inlet/outlet
    gas densities. Background flow is an imposed exchange-flow floor; it is
    not calculated diffusion or a model of autonomous cold startup.
    """

    evidence_id: str
    chimney_height_m: float
    inlet_area_m2: float
    loss_coefficient: float
    catalyst_heat_capacity_j_k: float
    catalyst_to_gas_ua_w_k: float
    catalyst_to_room_ua_w_k: float
    radiating_area_m2: float
    emissivity: float
    reaction_heat_to_catalyst_fraction: float
    maximum_mass_flow_kg_s: float
    background_mass_flow_kg_s: float = 0.
    gravity_m_s2: float = 9.80665

    def __post_init__(self):
        if not isinstance(self.evidence_id, str) or not self.evidence_id.strip():
            raise ValueError("Identify device geometry/thermal evidence")
        for name in ("chimney_height_m", "inlet_area_m2", "loss_coefficient",
                     "catalyst_heat_capacity_j_k", "maximum_mass_flow_kg_s", "gravity_m_s2"):
            finite(getattr(self, name), name, positive=True)
        for name in ("catalyst_to_gas_ua_w_k", "catalyst_to_room_ua_w_k",
                     "radiating_area_m2", "background_mass_flow_kg_s"):
            _nonnegative(getattr(self, name), name)
        for name in ("emissivity", "reaction_heat_to_catalyst_fraction"):
            if not 0 <= finite(getattr(self, name), name) <= 1:
                raise ValueError(f"{name} must lie in [0, 1]")
        if self.background_mass_flow_kg_s >= self.maximum_mass_flow_kg_s:
            raise ValueError("Background flow must be below the flow-solve bound")


@dataclass(frozen=True, slots=True)
class PARDevicePoint:
    catalyst_temperature_k: float
    inlet: ReactiveState
    outlet: ReactiveState
    inlet_mass_flow_kg_s: float
    outlet_mass_flow_kg_s: float
    inlet_species_mol_s: object
    outlet_species_mol_s: object
    hydrogen_removed_mol_s: float
    reaction_heat_w: float
    catalyst_to_gas_heat_w: float
    catalyst_to_room_heat_w: float
    catalyst_heating_w: float
    inlet_enthalpy_flow_w: float
    outlet_enthalpy_flow_w: float
    buoyancy_pressure_pa: float
    momentum_residual_kg_s: float
    mass_residual_kg_s: float
    energy_residual_w: float
    entropy_generation_w_k: float
    flow_status: str
    capacity_evidence_id: str
    device_evidence_id: str
    mechanism_basis: MechanismBasis
    native_version: str


@dataclass(frozen=True, slots=True)
class PARThermalSample:
    time_s: float
    point: PARDevicePoint
    cumulative_hydrogen_removed_mol: float
    cumulative_inlet_enthalpy_j: float
    cumulative_outlet_enthalpy_j: float
    cumulative_heat_to_room_j: float
    energy_residual_j: float


@dataclass(frozen=True, slots=True)
class PARThermalTrace:
    clock_id: str
    samples: tuple[PARThermalSample, ...]


class PARDevice:
    """Performance-map PAR with dynamic catalyst and quasi-steady gas channel.

    Cantera supplies density, heat capacity and species formation/sensible
    enthalpies on one native mechanism reference. No new gas EOS is introduced.
    The only chemical transformation here is H2 + 0.5 O2 -> H2O(vapor), whose
    extent is set by the supplied performance law and available feed.
    """

    def __init__(self, gas: CanteraGas, parameters: PARDeviceParameters,
                 capacity: PARCapacityLaw):
        if not isinstance(gas, CanteraGas):
            raise TypeError("Supply the existing CanteraGas native owner")
        if not isinstance(parameters, PARDeviceParameters) or not isinstance(capacity, PARCapacityLaw):
            raise TypeError("Declare PAR device parameters and capacity evidence")
        if parameters.maximum_mass_flow_kg_s > capacity.maximum_mass_flow_kg_s:
            raise ValueError("Flow-solve bound exceeds the capacity-law domain")
        self.gas, self.parameters, self.capacity = gas, parameters, capacity

    def evaluate(self, inlet: ReactiveState, catalyst_temperature_k: float) -> PARDevicePoint:
        if not isinstance(inlet, ReactiveState):
            raise TypeError("Supply a shared ReactiveState at the device inlet")
        finite(catalyst_temperature_k, "catalyst temperature", positive=True)
        p, capacity = self.parameters, self.capacity
        # Validate the map domain even when no-flow or oxygen starvation prevents
        # conversion. Missing evidence is never masked by a zero rate.
        capacity.evaluate(PARCapacityCondition(catalyst_temperature_k, inlet, p.background_mass_flow_kg_s))
        self.gas.basis.require_state(catalyst_temperature_k, inlet.pressure_pa)
        handle = self.gas.create_phase(inlet)
        phase = handle.native_phase
        if phase.thermo_model != "ideal-gas":
            raise ValueError("This PAR level requires native reacting ideal-gas thermochemistry")
        required = ("H2", "O2", "H2O")
        if any(name not in phase.species_names for name in required):
            raise ValueError("Native mechanism must contain H2, O2 and vapor H2O")
        # This device level deliberately excludes reactive contaminants rather
        # than treating CO poisoning, dissociation or gas ignition as resolved.
        if {name for name, fraction in inlet.mole_fractions.items() if fraction > 0} - {"H2", "O2", "H2O", "N2", "AR", "HE"}:
            raise ValueError("PAR inlet contains species outside this device level")
        rho_in, cp_in, h_in = phase.density, phase.cp_mass, phase.enthalpy_mass
        entropy_in = phase.entropy_mass
        mw = phase.mean_molecular_weight / 1000.  # native kg/kmol -> kg/mol
        names = tuple(phase.species_names)
        x_in = np.array(phase.X)
        ih, io, iw = (phase.species_index(s) for s in required)
        h_species = np.array(phase.partial_molar_enthalpies) / 1000.
        heat_per_mol = -(h_species[iw] - h_species[ih] - .5*h_species[io])
        if heat_per_mol <= 0:
            raise ValueError("Native reaction enthalpy is not exothermic in this domain")
        q_room = (p.catalyst_to_room_ua_w_k * (catalyst_temperature_k - inlet.temperature_k)
                  + p.emissivity * 5.670374419e-8 * p.radiating_area_m2
                  * (catalyst_temperature_k**4 - inlet.temperature_k**4))
        finite(q_room, "catalyst heat to room")

        def flow_state(mass_flow):
            incoming = mass_flow / mw * x_in
            rate = min(capacity.evaluate(PARCapacityCondition(catalyst_temperature_k, inlet, mass_flow)),
                       incoming[ih], 2*incoming[io])
            outgoing = incoming.copy()
            outgoing[ih] -= rate
            outgoing[io] -= .5*rate
            outgoing[iw] += rate
            heat = rate * heat_per_mol
            if mass_flow == 0:
                q_gas, rho_out, t_out, h_out = 0., rho_in, inlet.temperature_k, h_in
                entropy_out = entropy_in
                x_out = x_in
            else:
                # Finite-flow effectiveness prevents an unphysical finite heat
                # export through a zero-flow gas boundary.
                mcp = mass_flow * cp_in
                q_gas = -mcp * math.expm1(-p.catalyst_to_gas_ua_w_k/mcp) * (catalyst_temperature_k-inlet.temperature_k)
                x_out = outgoing / outgoing.sum()
                phase.TPX = inlet.temperature_k, inlet.pressure_pa, x_out
                target_h = h_in + (q_gas-p.reaction_heat_to_catalyst_fraction*heat)/mass_flow
                phase.HP = target_h, inlet.pressure_pa
                t_out, rho_out, h_out = phase.T, phase.density, phase.enthalpy_mass
                entropy_out = phase.entropy_mass
                self.gas.basis.require_state(t_out, inlet.pressure_pa)
            dp = p.gravity_m_s2*p.chimney_height_m*(rho_in-rho_out)
            mean_density = .5*(rho_in+rho_out)
            natural = p.inlet_area_m2 * math.sqrt(2*max(dp, 0)*mean_density/p.loss_coefficient)
            residual = mass_flow - p.background_mass_flow_kg_s - natural
            return incoming, outgoing, rate, heat, q_gas, t_out, h_out, entropy_out, dp, residual

        if p.background_mass_flow_kg_s == 0 and catalyst_temperature_k <= inlet.temperature_k:
            mass_flow, status = 0., "not_started_no_background_exchange"
        elif p.background_mass_flow_kg_s == 0 and p.catalyst_to_gas_ua_w_k == 0:
            mass_flow, status = 0., "not_started_no_gas_heating"
        else:
            lower = max(p.background_mass_flow_kg_s, p.maximum_mass_flow_kg_s*1e-12)
            upper = p.maximum_mass_flow_kg_s
            flo, fhi = flow_state(lower)[-1], flow_state(upper)[-1]
            if fhi < 0:
                raise ValueError("Buoyant flow exceeds the declared mass-flow solve domain")
            if flo >= 0:
                mass_flow = p.background_mass_flow_kg_s
            else:
                mass_flow = brentq(lambda value: flow_state(value)[-1], lower, upper,
                                   xtol=max(1e-14, upper*1e-10), rtol=1e-10)
            status = "background_and_buoyancy" if p.background_mass_flow_kg_s else "hot_catalyst_buoyancy"
        incoming, outgoing, rate, heat, q_gas, t_out, h_out, entropy_out, dp, momentum = flow_state(mass_flow)
        heating = p.reaction_heat_to_catalyst_fraction*heat-q_gas-q_room
        inlet_h, outlet_h = mass_flow*h_in, mass_flow*h_out
        mass_out = float(np.dot(outgoing, np.array(phase.molecular_weights)/1000.))
        mass_residual = mass_flow-mass_out
        energy_residual = inlet_h-outlet_h-q_room-heating
        if abs(mass_residual) > 1e-12+1e-10*mass_flow:
            raise ValueError("PAR native species-flow mass balance failed")
        if abs(energy_residual) > 1e-6+1e-8*max(abs(inlet_h), abs(outlet_h), abs(heat)):
            raise ValueError("PAR gas/catalyst energy balance failed")
        # The room is a reservoir at inlet temperature; catalyst entropy storage
        # is C/T*dT/dt. Native species entropy shares the same mechanism basis
        # as formation enthalpy. A supplied empirical map can otherwise drive a
        # reaction in the wrong thermodynamic direction despite conserving H.
        entropy_terms = (mass_out*entropy_out, -mass_flow*entropy_in,
                         q_room/inlet.temperature_k, heating/catalyst_temperature_k)
        entropy_generation = math.fsum(entropy_terms)
        finite(entropy_generation, "PAR entropy generation")
        entropy_tolerance = 1e-10+1e-9*max(map(abs, entropy_terms))
        if entropy_generation < -entropy_tolerance:
            raise ValueError("PAR capacity/thermal closure violates the combined entropy balance")
        outlet_fractions = x_in if mass_flow == 0 else outgoing/outgoing.sum()
        return PARDevicePoint(catalyst_temperature_k, inlet,
            ReactiveState(t_out, inlet.pressure_pa, dict(zip(names, outlet_fractions, strict=True))),
            mass_flow, mass_out,
            MappingProxyType(dict(zip(names, map(float, incoming), strict=True))),
            MappingProxyType(dict(zip(names, map(float, outgoing), strict=True))),
            rate, heat, q_gas, q_room, heating, inlet_h, outlet_h, dp, momentum,
            mass_residual, energy_residual, entropy_generation, status, capacity.evidence_id,
            p.evidence_id, self.gas.basis, self.gas.ct.__version__)

    def integrate(self, inlet: ReactiveState, *, initial_catalyst_temperature_k: float,
                  time_s, clock_id: str, relative_tolerance=1e-7,
                  maximum_step_s=1.) -> PARThermalTrace:
        """Integrate catalyst storage and cumulative ports for a fixed inlet.

        The room boundary remains prescribed: a compartment solver must receive
        the returned species and heat ports if a finite room is required.
        """
        if not isinstance(clock_id, str) or not clock_id.strip():
            raise ValueError("Identify the thermal evolution clock")
        times = np.asarray(time_s, dtype=float)
        if (times.ndim != 1 or len(times) < 2 or not np.all(np.isfinite(times))
                or times[0] < 0 or np.any(np.diff(times) <= 0)):
            raise ValueError("Observation times must be finite, nonnegative and strictly increasing")
        finite(relative_tolerance, "integration relative tolerance", positive=True)
        finite(maximum_step_s, "maximum step", positive=True)
        self.evaluate(inlet, initial_catalyst_temperature_k)
        capacity = self.parameters.catalyst_heat_capacity_j_k

        def rhs(_time, state):
            point = self.evaluate(inlet, float(state[0]))
            return (point.catalyst_heating_w/capacity, point.hydrogen_removed_mol_s,
                    point.inlet_enthalpy_flow_w, point.outlet_enthalpy_flow_w,
                    point.catalyst_to_room_heat_w)

        solution = solve_ivp(rhs, (times[0], times[-1]),
            (initial_catalyst_temperature_k, 0., 0., 0., 0.), t_eval=times,
            rtol=relative_tolerance, atol=(1e-8, 1e-12, 1e-7, 1e-7, 1e-7),
            max_step=maximum_step_s)
        if not solution.success or not np.all(np.isfinite(solution.y)):
            raise RuntimeError(f"PAR thermal integration failed: {solution.message}")
        samples = []
        for time, state in zip(solution.t, solution.y.T, strict=True):
            temperature, extent, hin, hout, qroom = map(float, state)
            residual = capacity*(temperature-initial_catalyst_temperature_k)-hin+hout+qroom
            samples.append(PARThermalSample(float(time), self.evaluate(inlet, temperature),
                                           extent, hin, hout, qroom, residual))
        return PARThermalTrace(clock_id, tuple(samples))
