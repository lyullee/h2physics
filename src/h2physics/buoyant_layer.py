"""Reduced two-layer hydrogen accumulation model for a still-air enclosure.

This independent implementation integrates upper-layer volume and hydrogen
inventory. A classical pure-plume entrainment closure feeds the upper layer;
two vent orifices are coupled by an algebraic pressure-continuity solve.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import pi, sqrt
from threading import RLock

from scipy.optimize import brentq

from .core import finite


class CoolPropHydrogenAirProperties:
    """Native density for variable H2 content in a fixed dry-air carrier.

    Carrier fractions are N2/O2/Ar mole fractions and must sum to one. The
    default excludes water, CO2 and trace gases. This density-only interface
    supplies no reaction, sensible-energy or thermal-equilibrium model.
    """

    def __setattr__(self, name, value):
        if getattr(self, "_identity_locked", False):
            raise AttributeError("Native layer property configuration is immutable")
        object.__setattr__(self, name, value)

    def __init__(self, *, dry_air_mole_fractions=None):
        import CoolProp
        import CoolProp.CoolProp as cp

        raw = ((.78084/.99964, .20946/.99964, .00934/.99964)
               if dry_air_mole_fractions is None else tuple(dry_air_mole_fractions))
        if (len(raw) != 3 or any(finite(x, "carrier mole fraction") <= 0. for x in raw)
                or abs(sum(raw)-1.) > 1.e-12):
            raise ValueError("Declare normalized positive N2/O2/Ar carrier mole fractions")
        self._fractions = tuple(float(x) for x in raw)
        self._cp = cp
        self._state = CoolProp.AbstractState("HEOS", "Hydrogen&Nitrogen&Oxygen&Argon")
        self._hydrogen = CoolProp.AbstractState("HEOS", "Hydrogen")
        self._air = CoolProp.AbstractState("HEOS", "Nitrogen&Oxygen&Argon")
        self._air.set_mole_fractions(self._fractions)
        self._hydrogen_molar_mass = float(self._hydrogen.molar_mass())
        self._carrier_molar_mass = float(self._air.molar_mass())
        self._lock = RLock()
        self._identity = (f"CoolProp:{CoolProp.__version__}:HEOS:Hydrogen+N2/O2/Ar:"
                          + ",".join(x.hex() for x in self._fractions)
                          + ":normal-hydrogen-density-only")
        self._identity_locked = True

    @property
    def dry_air_mole_fractions(self):
        return self._fractions

    @property
    def identity(self):
        return self._identity

    def mass_fraction(self, hydrogen_mole_fraction):
        """Composition conversion using native component molar masses."""
        x = finite(hydrogen_mole_fraction, "H2 mole fraction")
        if not 0. <= x <= 1.:
            raise ValueError("H2 mole fraction must lie in [0, 1]")
        return x*self._hydrogen_molar_mass / (
            x*self._hydrogen_molar_mass+(1.-x)*self._carrier_molar_mass)

    def density_ptx(self, pressure_pa, temperature_k, hydrogen_mole_fraction):
        pressure = finite(pressure_pa, "pressure_pa", positive=True)
        temperature = finite(temperature_k, "temperature_k", positive=True)
        x = finite(hydrogen_mole_fraction, "H2 mole fraction")
        if not 0. <= x <= 1.:
            raise ValueError("H2 mole fraction must lie in [0, 1]")
        with self._lock:
            if x == 0.:
                state = self._air
                state.set_mole_fractions(self._fractions)
            elif x == 1.:
                state = self._hydrogen
            else:
                state = self._state
                state.set_mole_fractions([x, *((1.-x)*a for a in self._fractions)])
            state.update(self._cp.PT_INPUTS, pressure, temperature)
            if state.phase() not in (self._cp.iphase_gas, self._cp.iphase_supercritical_gas,
                                     self._cp.iphase_supercritical):
                raise ValueError("The buoyant-layer density closure requires a native gas state")
            return finite(state.rhomass(), "native layer density", positive=True)


@dataclass(frozen=True, slots=True)
class TwoVentHydrogenLayerConfig:
    compartment_height_m: float
    floor_area_m2: float
    source_height_m: float
    lower_vent_area_m2: float
    upper_vent_area_m2: float
    lower_discharge_coefficient: float
    upper_discharge_coefficient: float
    ambient_pressure_pa: float
    ambient_temperature_k: float
    initial_upper_layer_volume_m3: float
    initial_upper_h2_mole_fraction: float
    entrainment_coefficient: float = 0.102
    gravity_m_s2: float = 9.80665
    maximum_pressure_drop_pa: float | None = None

    def __post_init__(self):
        for name in (
            "compartment_height_m", "floor_area_m2", "lower_vent_area_m2",
            "upper_vent_area_m2", "ambient_pressure_pa", "ambient_temperature_k",
            "initial_upper_layer_volume_m3", "entrainment_coefficient", "gravity_m_s2",
        ):
            finite(getattr(self, name), name, positive=True)
        for name in ("source_height_m",):
            finite(getattr(self, name), name)
        if not 0.0 <= self.source_height_m < self.compartment_height_m:
            raise ValueError("The H2 source must lie inside the compartment below the ceiling")
        if self.initial_upper_layer_volume_m3 >= self.floor_area_m2 * (
            self.compartment_height_m - self.source_height_m
        ):
            raise ValueError("The initial interface must remain above the H2 source")
        for name in ("lower_discharge_coefficient", "upper_discharge_coefficient"):
            value = finite(getattr(self, name), name)
            if not 0.0 < value <= 1.0:
                raise ValueError("Vent discharge coefficients must lie in (0, 1]")
        x = finite(self.initial_upper_h2_mole_fraction, "initial H2 mole fraction")
        if not 0.0 < x < 1.0:
            raise ValueError("A small positive initial upper-layer H2 fraction is required")
        if self.maximum_pressure_drop_pa is not None:
            finite(self.maximum_pressure_drop_pa, "maximum vent pressure drop", positive=True)


@dataclass(frozen=True, slots=True)
class TwoVentHydrogenLayerResult:
    time_s: tuple[float, ...]
    interface_height_m: tuple[float, ...]
    upper_h2_mole_fraction: tuple[float, ...]
    upper_h2_mass_fraction: tuple[float, ...]
    upper_layer_volume_m3: tuple[float, ...]
    upper_layer_density_kg_m3: tuple[float, ...]
    compartment_overpressure_pa: tuple[float, ...]
    lower_inflow_m3_s: tuple[float, ...]
    upper_outflow_m3_s: tuple[float, ...]
    hydrogen_inventory_kg: tuple[float, ...]
    cumulative_hydrogen_in_kg: tuple[float, ...]
    cumulative_hydrogen_out_kg: tuple[float, ...]
    hydrogen_mass_residual_kg: tuple[float, ...]
    vent_mass_continuity_residual_kg_s: tuple[float, ...]
    property_backend_id: str = ""
    dry_air_mole_fractions: tuple[float, ...] = ()


def _layer_composition(volume, hydrogen_mass, pressure_pa, temperature_k, properties):
    """Invert native mixture partial mass density without an ideal-mixture EOS."""
    max_h2 = properties.density_ptx(pressure_pa, temperature_k, 1.)*volume
    if hydrogen_mass <= 0.0 or hydrogen_mass >= max_h2:
        raise ValueError("Layer H2 stock is outside the realizable single-gas mixture range")
    def residual(x):
        return (properties.density_ptx(pressure_pa, temperature_k, x)
                * properties.mass_fraction(x)*volume-hydrogen_mass)
    x = brentq(residual, 0., 1., xtol=1.e-14, rtol=1.e-12)
    return x, properties.mass_fraction(x)


def _plume_coefficient(epsilon):
    return (6.0 * epsilon / 5.0) * (9.0 * pi * pi * epsilon / 10.0) ** (-1.0 / 3.0)


def _evaluate(config, volume, hydrogen_mass, hydrogen_mass_flow, properties):
    height = config.compartment_height_m - volume / config.floor_area_m2
    if height <= config.source_height_m:
        raise ValueError("The layer interface reached the release elevation")
    pressure_limit = config.maximum_pressure_drop_pa or config.ambient_pressure_pa * 0.02
    rho_air = properties.density_ptx(config.ambient_pressure_pa, config.ambient_temperature_k, 0.)
    rho_h2 = properties.density_ptx(config.ambient_pressure_pa, config.ambient_temperature_k, 1.)
    q_h2 = hydrogen_mass_flow / rho_h2
    buoyancy_flux = q_h2 * (rho_air - rho_h2) / rho_air * config.gravity_m_s2
    if buoyancy_flux <= 0.0:
        raise ValueError("The source must be buoyant relative to ambient air")
    coefficient = _plume_coefficient(config.entrainment_coefficient)
    origin_offset = (q_h2 / (coefficient * buoyancy_flux ** (1.0 / 3.0))) ** (3.0 / 5.0)
    plume_flow = coefficient * buoyancy_flux ** (1.0 / 3.0) * (
        height - config.source_height_m + origin_offset
    ) ** (5.0 / 3.0)

    def vent_state(overpressure):
        layer_pressure = config.ambient_pressure_pa + overpressure
        x, y = _layer_composition(volume, hydrogen_mass, layer_pressure,
                                  config.ambient_temperature_k, properties)
        rho = properties.density_ptx(layer_pressure, config.ambient_temperature_k, x)
        buoyancy_head = config.gravity_m_s2 * (rho_air - rho) * (
            config.compartment_height_m - height
        )
        dp_lower = buoyancy_head - overpressure
        q_lower = 0.0 if dp_lower <= 0.0 else (
            config.lower_vent_area_m2 * config.lower_discharge_coefficient
            * sqrt(2.0 * dp_lower / rho_air)
        )
        q_upper = config.upper_vent_area_m2 * config.upper_discharge_coefficient * sqrt(
            2.0 * overpressure / rho
        )
        mass_residual = rho_air * q_lower + hydrogen_mass_flow - rho * q_upper
        return y, rho, q_lower, q_upper, buoyancy_head, mass_residual

    zero_head = vent_state(0.0)[4]
    if zero_head <= 0.0:
        raise ValueError("The current upper layer does not produce positive buoyancy head")
    low, high = 0.0, pressure_limit
    if vent_state(high)[4] < high:
        # Find the edge of the assumed lower-inflow regime before solving
        # vent continuity. This is a closure bound, not a pressure clipping.
        high = brentq(lambda dp: vent_state(dp)[4]-dp, 0., high,
                      xtol=1.e-12, rtol=1.e-12)

    def continuity(dp):
        _y, _rho, _q_lower, _q_upper, _head, residual = vent_state(dp)
        return residual
    f_low, f_high = continuity(low), continuity(high)
    if f_low < 0.0 or f_high > 0.0:
        raise ValueError("No one-way lower-inflow/upper-outflow pressure solution within declared bound")
    overpressure = brentq(continuity, low, high, xtol=1.e-12, rtol=1.e-12)
    y, rho, q_lower, q_upper, _head, vent_residual = vent_state(overpressure)
    h2_out = y * rho * q_upper
    return (
        plume_flow - q_upper,
        hydrogen_mass_flow - h2_out,
        h2_out,
        overpressure,
        y,
        rho,
        q_lower,
        q_upper,
        height,
        vent_residual,
    )


def run_two_vent_hydrogen_layer(
    config: TwoVentHydrogenLayerConfig,
    *,
    hydrogen_mass_flow_kg_s: float,
    duration_s: float,
    maximum_step_s: float,
    properties: CoolPropHydrogenAirProperties | None = None,
) -> TwoVentHydrogenLayerResult:
    """Integrate a steady vertical H2 release into a still-air two-vent room.

    The state uses upper-layer volume and H2 mass. A fourth-order fixed-step
    Runge-Kutta march is used; vent pressure is obtained from an inner scalar
    continuity solve. The case stops with an error if the interface reaches
    the source or the assumed one-way vent-flow regime ceases to exist.
    """
    if type(config) is not TwoVentHydrogenLayerConfig:
        raise TypeError("Supply a TwoVentHydrogenLayerConfig")
    if properties is None:
        properties = CoolPropHydrogenAirProperties()
    if type(properties) is not CoolPropHydrogenAirProperties:
        raise TypeError("Supply native CoolPropHydrogenAirProperties")
    mass_flow = finite(hydrogen_mass_flow_kg_s, "H2 mass flow", positive=True)
    duration = finite(duration_s, "release duration", positive=True)
    step_limit = finite(maximum_step_s, "maximum integration step", positive=True)
    volume = config.initial_upper_layer_volume_m3
    x0 = config.initial_upper_h2_mole_fraction
    pressure = config.ambient_pressure_pa
    hydrogen_mass = (properties.density_ptx(pressure, config.ambient_temperature_k, x0)
                     * properties.mass_fraction(x0)*volume)
    cumulative_in = 0.0
    cumulative_out = 0.0
    times = [0.0]
    inventory = [hydrogen_mass]
    input_history = [0.0]
    output_history = [0.0]
    residuals = [0.0]

    def evaluate(v, m):
        state = _evaluate(config, v, m, mass_flow, properties)
        x, _ = _layer_composition(v, m, pressure+state[3],
                                  config.ambient_temperature_k, properties)
        return state, x

    state0, x_start = evaluate(volume, hydrogen_mass)
    heights = [state0[8]]
    mole_fractions = [x_start]
    mass_fractions = [state0[4]]
    volumes = [volume]
    densities = [state0[5]]
    pressures = [state0[3]]
    lower_flows = [state0[6]]
    upper_flows = [state0[7]]
    vent_mass_residuals = [state0[9]]

    elapsed = 0.0
    while elapsed < duration:
        dt = min(step_limit, duration - elapsed)
        def rhs(v, m):
            state = _evaluate(config, v, m, mass_flow, properties)
            return state[0], state[1], state[2]
        k1v, k1m, k1o = rhs(volume, hydrogen_mass)
        k2v, k2m, k2o = rhs(volume+0.5*dt*k1v, hydrogen_mass+0.5*dt*k1m)
        k3v, k3m, k3o = rhs(volume+0.5*dt*k2v, hydrogen_mass+0.5*dt*k2m)
        k4v, k4m, k4o = rhs(volume+dt*k3v, hydrogen_mass+dt*k3m)
        volume += dt*(k1v+2*k2v+2*k3v+k4v)/6.0
        hydrogen_mass += dt*(k1m+2*k2m+2*k3m+k4m)/6.0
        out = dt*(k1o+2*k2o+2*k3o+k4o)/6.0
        cumulative_in += mass_flow * dt
        cumulative_out += out
        elapsed += dt
        state, x = evaluate(volume, hydrogen_mass)
        times.append(elapsed)
        inventory.append(hydrogen_mass)
        input_history.append(cumulative_in)
        output_history.append(cumulative_out)
        residuals.append(hydrogen_mass - inventory[0] - cumulative_in + cumulative_out)
        heights.append(state[8])
        mole_fractions.append(x)
        mass_fractions.append(state[4])
        volumes.append(volume)
        densities.append(state[5])
        pressures.append(state[3])
        lower_flows.append(state[6])
        upper_flows.append(state[7])
        vent_mass_residuals.append(state[9])

    return TwoVentHydrogenLayerResult(
        tuple(times), tuple(heights), tuple(mole_fractions), tuple(mass_fractions),
        tuple(volumes), tuple(densities), tuple(pressures), tuple(lower_flows),
        tuple(upper_flows), tuple(inventory), tuple(input_history),
        tuple(output_history), tuple(residuals),
        tuple(vent_mass_residuals),
        properties.identity, properties.dry_air_mole_fractions,
    )
