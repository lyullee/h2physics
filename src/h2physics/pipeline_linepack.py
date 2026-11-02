"""Analytic ideal-gas linepack reference with explicit port mass ledgers.

For physical fluid properties, use ``real_gas_linepack.RealGasLinepackState``
with ``thermo.CoolPropIsothermalEOS``. This explicit ideal reference remains for
analytic verification and legacy comparison; it is never a CoolProp fallback.

This model resolves inventory and pressure transients in one well-mixed pipe
segment. It does not solve spatial pressure waves or pipe friction; use the
steady hydraulic closures for those separate questions.
"""

from dataclasses import dataclass

from .core import finite

_R_UNIVERSAL_J_MOL_K = 8.31446261815324


def _nonnegative(value, name):
    result = finite(value, name)
    if result < 0.0:
        raise ValueError(f"{name} must be nonnegative")
    return result


@dataclass(frozen=True, slots=True)
class IsothermalLinepackState:
    """A fixed-volume, fixed-temperature, fixed-composition line segment."""

    volume_m3: float
    temperature_k: float
    molecular_mass_kg_mol: float
    mass_kg: float
    time_s: float = 0.0

    def __post_init__(self):
        for name in ("volume_m3", "temperature_k", "molecular_mass_kg_mol", "mass_kg"):
            finite(getattr(self, name), name, positive=True)
        _nonnegative(self.time_s, "time_s")

    @classmethod
    def from_pressure(cls, *, volume_m3, temperature_k, molecular_mass_kg_mol,
                      pressure_pa, time_s=0.0):
        """Create an inventory from the perfect-gas pressure relation."""
        volume = finite(volume_m3, "volume_m3", positive=True)
        temperature = finite(temperature_k, "temperature_k", positive=True)
        molecular_mass = finite(molecular_mass_kg_mol,
                                "molecular_mass_kg_mol", positive=True)
        pressure = finite(pressure_pa, "pressure_pa", positive=True)
        mass = pressure * volume * molecular_mass / (
            _R_UNIVERSAL_J_MOL_K * temperature)
        return cls(volume, temperature, molecular_mass, mass, time_s)

    @property
    def pressure_pa(self):
        return (self.mass_kg * (_R_UNIVERSAL_J_MOL_K / self.molecular_mass_kg_mol)
                * self.temperature_k / self.volume_m3)

    @property
    def specific_gas_constant_j_kg_k(self):
        return _R_UNIVERSAL_J_MOL_K / self.molecular_mass_kg_mol

    def advance(self, *, duration_s, inlet_mass_flow_kg_s, outlet_mass_flow_kg_s,
                minimum_mass_kg=0.0):
        """Advance one interval with constant, caller-prescribed nonnegative ports.

        Returns a new immutable state and a closure ledger. The interval is
        rejected if its net withdrawal reaches the caller-declared inventory
        floor; automatic flow clipping is intentionally not applied.
        """
        duration = finite(duration_s, "duration_s", positive=True)
        inlet_rate = _nonnegative(inlet_mass_flow_kg_s, "inlet_mass_flow_kg_s")
        outlet_rate = _nonnegative(outlet_mass_flow_kg_s, "outlet_mass_flow_kg_s")
        floor = _nonnegative(minimum_mass_kg, "minimum_mass_kg")
        inlet = inlet_rate * duration
        outlet = outlet_rate * duration
        final_mass = self.mass_kg + inlet - outlet
        if final_mass <= floor:
            raise ValueError("Linepack step reaches or crosses the declared mass floor")
        final = IsothermalLinepackState(
            self.volume_m3, self.temperature_k, self.molecular_mass_kg_mol,
            final_mass, self.time_s + duration,
        )
        residual = inlet - outlet - (final.mass_kg - self.mass_kg)
        return final, LinepackStepLedger(
            start_time_s=self.time_s, end_time_s=final.time_s,
            inlet_mass_kg=inlet, outlet_mass_kg=outlet,
            initial_mass_kg=self.mass_kg, final_mass_kg=final.mass_kg,
            initial_pressure_pa=self.pressure_pa, final_pressure_pa=final.pressure_pa,
            mass_residual_kg=residual,
        )


@dataclass(frozen=True, slots=True)
class LinepackStepLedger:
    """Integrated port and inventory changes for one accepted linepack step."""

    start_time_s: float
    end_time_s: float
    inlet_mass_kg: float
    outlet_mass_kg: float
    initial_mass_kg: float
    final_mass_kg: float
    initial_pressure_pa: float
    final_pressure_pa: float
    mass_residual_kg: float

    def __post_init__(self):
        _nonnegative(self.start_time_s, "start_time_s")
        finite(self.end_time_s, "end_time_s", positive=True)
        if self.end_time_s <= self.start_time_s:
            raise ValueError("Linepack ledger interval must have positive duration")
        for name in ("inlet_mass_kg", "outlet_mass_kg", "initial_mass_kg", "final_mass_kg",
                     "initial_pressure_pa", "final_pressure_pa"):
            _nonnegative(getattr(self, name), name)
        finite(self.mass_residual_kg, "mass_residual_kg")
