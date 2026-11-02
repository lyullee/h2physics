"""Fixed-temperature real-gas linepack inventory with explicit mass ports.

This is a lumped inventory closure. Spatial flow, momentum loss, wall heat,
and the control needed to hold temperature remain caller-owned or belong to a
separate pipe-network model.
"""

from dataclasses import dataclass, field
from math import isclose

from .core import finite
from .thermo.isothermal_eos import IsothermalSinglePhaseEOS


def _nonnegative(value, name):
    result = finite(value, name)
    if result < 0.0:
        raise ValueError(f"{name} must be nonnegative")
    return result


def _eos_identity(eos):
    identity = getattr(eos, "identity", None)
    if not isinstance(identity, str) or not identity.strip():
        raise ValueError("Real-gas linepack requires a stable EOS identity")
    if not callable(getattr(eos, "density_pt", None)) or not callable(
            getattr(eos, "pressure_rho_t", None)):
        raise TypeError("EOS must implement density_pt and pressure_rho_t")
    return identity


@dataclass(frozen=True, slots=True)
class RealGasLinepackState:
    """One well-mixed fixed-volume inventory evaluated by an isothermal EOS.

    The EOS must reject states outside its homogeneous single-phase domain.
    Pressure is recalculated from current mass density and fixed temperature;
    no perfect-gas compressibility factor or ideal-gas fallback is applied.
    """

    volume_m3: float
    temperature_k: float
    mass_kg: float
    eos: IsothermalSinglePhaseEOS = field(repr=False, compare=False)
    time_s: float = 0.0
    minimum_pressure_pa: float | None = None
    maximum_pressure_pa: float | None = None
    pressure_pa: float = field(init=False)
    eos_identity: str = field(init=False)

    def __post_init__(self):
        volume = finite(self.volume_m3, "volume_m3", positive=True)
        temperature = finite(self.temperature_k, "temperature_k", positive=True)
        mass = finite(self.mass_kg, "mass_kg", positive=True)
        time = _nonnegative(self.time_s, "time_s")
        identity = _eos_identity(self.eos)
        lower = self.minimum_pressure_pa
        upper = self.maximum_pressure_pa
        if lower is not None:
            lower = finite(lower, "minimum_pressure_pa", positive=True)
        if upper is not None:
            upper = finite(upper, "maximum_pressure_pa", positive=True)
        if lower is not None and upper is not None and lower >= upper:
            raise ValueError("Pressure-domain limits must be increasing")
        density = mass / volume
        pressure = finite(self.eos.pressure_rho_t(density, temperature),
                          "EOS pressure", positive=True)
        if _eos_identity(self.eos) != identity:
            raise ValueError("EOS identity changed during pressure evaluation")
        if lower is not None and pressure < lower:
            raise ValueError("Linepack pressure is below the declared EOS operating domain")
        if upper is not None and pressure > upper:
            raise ValueError("Linepack pressure is above the declared EOS operating domain")
        object.__setattr__(self, "volume_m3", volume)
        object.__setattr__(self, "temperature_k", temperature)
        object.__setattr__(self, "mass_kg", mass)
        object.__setattr__(self, "time_s", time)
        object.__setattr__(self, "minimum_pressure_pa", lower)
        object.__setattr__(self, "maximum_pressure_pa", upper)
        object.__setattr__(self, "pressure_pa", pressure)
        object.__setattr__(self, "eos_identity", identity)

    @classmethod
    def from_pressure(cls, *, volume_m3, temperature_k, pressure_pa, eos,
                      time_s=0.0, minimum_pressure_pa=None, maximum_pressure_pa=None):
        volume = finite(volume_m3, "volume_m3", positive=True)
        temperature = finite(temperature_k, "temperature_k", positive=True)
        pressure = finite(pressure_pa, "pressure_pa", positive=True)
        identity = _eos_identity(eos)
        density = finite(eos.density_pt(pressure, temperature),
                         "EOS density", positive=True)
        if _eos_identity(eos) != identity:
            raise ValueError("EOS identity changed during density evaluation")
        mass = density * volume
        state = cls(volume, temperature, mass, eos, time_s,
                    minimum_pressure_pa, maximum_pressure_pa)
        if state.eos_identity != identity:
            raise ValueError("EOS identity changed while initializing linepack")
        scale = max(pressure, state.pressure_pa)
        if abs(state.pressure_pa-pressure) > 1e-8*scale:
            raise ValueError("EOS pressure and density paths are not inverse within tolerance")
        return state

    @property
    def density_kg_m3(self):
        return self.mass_kg / self.volume_m3

    def advance(self, *, duration_s, inlet_mass_flow_kg_s, outlet_mass_flow_kg_s,
                minimum_mass_kg=0.0):
        """Advance constant prescribed port rates over one caller interval.

        The step rejects inventory-floor, pressure-domain, EOS-phase and EOS-
        identity failures; requested flows are never silently clipped.
        """
        if _eos_identity(self.eos) != self.eos_identity:
            raise ValueError("EOS identity changed after the state was issued")
        duration = finite(duration_s, "duration_s", positive=True)
        inlet_rate = _nonnegative(inlet_mass_flow_kg_s, "inlet_mass_flow_kg_s")
        outlet_rate = _nonnegative(outlet_mass_flow_kg_s, "outlet_mass_flow_kg_s")
        floor = _nonnegative(minimum_mass_kg, "minimum_mass_kg")
        inlet = inlet_rate * duration
        outlet = outlet_rate * duration
        final_mass = self.mass_kg + inlet - outlet
        if final_mass <= floor:
            raise ValueError("Linepack step reaches or crosses the declared mass floor")
        final = RealGasLinepackState(
            self.volume_m3, self.temperature_k, final_mass, self.eos,
            self.time_s + duration, self.minimum_pressure_pa,
            self.maximum_pressure_pa,
        )
        ledger = RealGasLinepackStepLedger(
            start_time_s=self.time_s, end_time_s=final.time_s,
            inlet_mass_kg=inlet, outlet_mass_kg=outlet,
            initial_mass_kg=self.mass_kg, final_mass_kg=final.mass_kg,
            initial_pressure_pa=self.pressure_pa, final_pressure_pa=final.pressure_pa,
            mass_residual_kg=inlet-outlet-(final.mass_kg-self.mass_kg),
            eos_identity=self.eos_identity,
        )
        return final, ledger


@dataclass(frozen=True, slots=True)
class RealGasLinepackStepLedger:
    """Integrated boundary masses and EOS pressure endpoints for one step."""

    start_time_s: float
    end_time_s: float
    inlet_mass_kg: float
    outlet_mass_kg: float
    initial_mass_kg: float
    final_mass_kg: float
    initial_pressure_pa: float
    final_pressure_pa: float
    mass_residual_kg: float
    eos_identity: str

    def __post_init__(self):
        _nonnegative(self.start_time_s, "start_time_s")
        finite(self.end_time_s, "end_time_s", positive=True)
        if self.end_time_s <= self.start_time_s:
            raise ValueError("Linepack ledger interval must have positive duration")
        for name in ("inlet_mass_kg", "outlet_mass_kg"):
            _nonnegative(getattr(self, name), name)
        for name in ("initial_mass_kg", "final_mass_kg"):
            finite(getattr(self, name), name, positive=True)
        for name in ("initial_pressure_pa", "final_pressure_pa"):
            finite(getattr(self, name), name, positive=True)
        residual = finite(self.mass_residual_kg, "mass_residual_kg")
        expected = self.inlet_mass_kg - self.outlet_mass_kg - (
            self.final_mass_kg - self.initial_mass_kg
        )
        if not isclose(residual, expected, rel_tol=1e-12, abs_tol=1e-14):
            raise ValueError("Mass residual does not match the retained port and inventory ledger")
        if not isinstance(self.eos_identity, str) or not self.eos_identity.strip():
            raise ValueError("Retain the EOS identity used to evaluate this step")


__all__ = ["RealGasLinepackState", "RealGasLinepackStepLedger"]
