"""Finite fixed-volume caloric inventory for a branched gas-pipe endpoint."""

from __future__ import annotations

from dataclasses import dataclass

from .caloric_pipe_waves import CaloricGasEOS, _eos_identity, _require_gas_state
from .core import Origin, PropertyBasis, ThermoState, finite


@dataclass(frozen=True, slots=True)
class FiniteCaloricPipeReservoir:
    """Caller-owned rigid gas inventory coupled through an endpoint flux.

    ``mass_kg`` and ``internal_energy_j`` are initial extensive stocks. The
    reservoir is spatially mixed and stationary. The network must use the
    same signed endpoint Rusanov flux for its pipe face and this inventory;
    positive outward flow leaves the reservoir and enters the pipe. This
    state does not add a valve, heat transfer, wall mass, stratification, or
    pressure control.
    """

    identifier: str
    node_id: str
    state_owner_id: str
    state_evidence_id: str
    clock_id: str
    eos_identity: str
    property_basis: PropertyBasis
    volume_m3: float
    mass_kg: float
    internal_energy_j: float
    minimum_mass_kg: float
    maximum_mass_kg: float
    pressure_bounds_pa: tuple[float, float]
    temperature_bounds_k: tuple[float, float]
    origin: Origin

    def __post_init__(self) -> None:
        for name in ("identifier", "node_id", "state_owner_id", "state_evidence_id",
                     "clock_id", "eos_identity"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"Declare finite caloric reservoir {name}")
        if not isinstance(self.property_basis, PropertyBasis):
            raise TypeError("Finite caloric reservoir requires a PropertyBasis")
        for name in ("volume_m3", "mass_kg", "maximum_mass_kg"):
            finite(getattr(self, name), name, positive=True)
        finite(self.internal_energy_j, "internal_energy_j")
        minimum = finite(self.minimum_mass_kg, "minimum_mass_kg")
        if minimum < 0. or not minimum < self.mass_kg <= self.maximum_mass_kg:
            raise ValueError("Initial reservoir mass must lie inside its explicit inventory bounds")
        for bounds, label in ((self.pressure_bounds_pa, "pressure"),
                              (self.temperature_bounds_k, "temperature")):
            if len(bounds) != 2:
                raise ValueError(f"Reservoir {label} domain requires lower and upper bounds")
            lower = finite(bounds[0], f"minimum_{label}", positive=True)
            upper = finite(bounds[1], f"maximum_{label}", positive=True)
            if lower >= upper:
                raise ValueError(f"Reservoir {label} bounds must increase strictly")
        object.__setattr__(self, "pressure_bounds_pa", tuple(self.pressure_bounds_pa))
        object.__setattr__(self, "temperature_bounds_k", tuple(self.temperature_bounds_k))
        origin = Origin(self.origin)
        if origin is Origin.UNRESOLVED:
            raise ValueError("Resolve the finite caloric reservoir state origin")
        object.__setattr__(self, "origin", origin)

    def require_eos(self, eos: CaloricGasEOS) -> None:
        if _eos_identity(eos) != self.eos_identity:
            raise ValueError("Finite caloric reservoir names a different EOS identity")
        if eos.basis != self.property_basis:
            raise ValueError("Finite caloric reservoir and EOS use different property bases")

    def recover_state(self, *, mass_kg: float, internal_energy_j: float,
                      eos: CaloricGasEOS) -> ThermoState:
        """Recover and domain-check the uniform vessel state from ``m,V,U``."""
        self.require_eos(eos)
        mass = finite(mass_kg, "reservoir mass_kg", positive=True)
        energy = finite(internal_energy_j, "reservoir internal_energy_j")
        if not self.minimum_mass_kg < mass <= self.maximum_mass_kg:
            raise ValueError("Finite caloric reservoir mass is depleted or outside its bounds")
        density = mass / self.volume_m3
        specific_internal_energy = energy / mass
        state = _require_gas_state(eos.state_rho_u(density, specific_internal_energy), eos,
                                   "Finite caloric reservoir")
        if (abs(state.density_kg_m3 - density) > 2.e-6 * max(1., abs(density))
                or abs(state.internal_energy_j_kg - specific_internal_energy)
                > 2.e-6 * max(1., abs(specific_internal_energy))):
            raise ValueError("Reservoir state did not replay through its declared rho-u EOS")
        p_lo, p_hi = self.pressure_bounds_pa
        t_lo, t_hi = self.temperature_bounds_k
        if not p_lo <= state.pressure_pa <= p_hi:
            raise ValueError("Finite caloric reservoir pressure left its declared EOS domain")
        if not t_lo <= state.temperature_k <= t_hi:
            raise ValueError("Finite caloric reservoir temperature left its declared EOS domain")
        return state

    def initial_state(self, eos: CaloricGasEOS) -> ThermoState:
        return self.recover_state(mass_kg=self.mass_kg,
                                  internal_energy_j=self.internal_energy_j, eos=eos)

    def advance(self, *, current_mass_kg: float, current_internal_energy_j: float,
                outward_mass_flow_kg_s: float, outward_energy_flow_w: float,
                duration_s: float, eos: CaloricGasEOS,
                nozzle_outflow_mass_flow_kg_s: float = 0.,
                nozzle_withdrawal_energy_w: float = 0.) -> tuple[float, float, ThermoState]:
        """Apply the signed endpoint mass/energy flux, rejecting invalid stock.

        The caller passes the exact Rusanov rates used by the adjacent pipe
        face. The returned state is fully admitted against the same EOS and
        caller domain bounds before any network state is committed.
        """
        duration = finite(duration_s, "reservoir step duration", positive=True)
        current_mass = finite(current_mass_kg, "current reservoir mass", positive=True)
        current_energy = finite(current_internal_energy_j, "current reservoir internal energy")
        mass_rate = finite(outward_mass_flow_kg_s, "outward mass flow")
        energy_rate = finite(outward_energy_flow_w, "outward energy flow")
        nozzle_mass_rate = finite(nozzle_outflow_mass_flow_kg_s,
                                  "nozzle_outflow_mass_flow_kg_s")
        nozzle_energy_rate = finite(nozzle_withdrawal_energy_w,
                                    "nozzle_withdrawal_energy_w")
        if nozzle_mass_rate < 0. or nozzle_energy_rate < 0.:
            raise ValueError("Nozzle reservoir debits must be nonnegative")
        self.recover_state(mass_kg=current_mass,
                           internal_energy_j=current_energy, eos=eos)
        next_mass = current_mass - duration * (mass_rate + nozzle_mass_rate)
        next_energy = current_energy - duration * (energy_rate + nozzle_energy_rate)
        next_state = self.recover_state(mass_kg=next_mass,
                                        internal_energy_j=next_energy, eos=eos)
        return next_mass, next_energy, next_state


__all__ = ["FiniteCaloricPipeReservoir"]
