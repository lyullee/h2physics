"""Finite inventory state for a fixed-volume isothermal pipe endpoint.

Unlike :mod:`h2physics.pipe_reservoir_boundary`, this object owns a changing
mass inventory. It supplies pressure from that inventory through the shared
single-phase isothermal EOS; it does not prescribe a pressure-time curve.
"""

from __future__ import annotations

from dataclasses import dataclass

from .core import Origin, finite
from .thermo.isothermal_eos import IsothermalSinglePhaseEOS


@dataclass(frozen=True, slots=True)
class FiniteIsothermalPipeReservoir:
    """Caller-owned, well-mixed endpoint inventory at fixed volume and T.

    `mass_kg` is the initial inventory. Network coupling must apply the same
    signed pipe-outward endpoint flux to this inventory: positive flux leaves
    the reservoir and enters the pipe. This class does not model a valve,
    reservoir energy balance, heat transfer, or a pressure controller.
    """

    identifier: str
    node_id: str
    state_owner_id: str
    state_evidence_id: str
    clock_id: str
    eos_identity: str
    temperature_k: float
    volume_m3: float
    mass_kg: float
    minimum_mass_kg: float
    maximum_mass_kg: float
    origin: Origin

    def __post_init__(self) -> None:
        for label, value in (
            ("reservoir identifier", self.identifier),
            ("network node ID", self.node_id),
            ("state owner ID", self.state_owner_id),
            ("state evidence ID", self.state_evidence_id),
            ("clock ID", self.clock_id),
            ("EOS identity", self.eos_identity),
        ):
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"Declare {label}")
        for name in ("temperature_k", "volume_m3", "mass_kg", "maximum_mass_kg"):
            finite(getattr(self, name), name, positive=True)
        lower = finite(self.minimum_mass_kg, "minimum_mass_kg")
        if lower < 0.:
            raise ValueError("minimum_mass_kg cannot be negative")
        if not lower < self.mass_kg <= self.maximum_mass_kg:
            raise ValueError("Initial reservoir inventory must lie above its floor and at or below its ceiling")
        origin = Origin(self.origin)
        if origin is Origin.UNRESOLVED:
            raise ValueError("Resolve or explicitly author the finite reservoir inventory origin")
        object.__setattr__(self, "origin", origin)

    def require_eos(self, eos: IsothermalSinglePhaseEOS) -> None:
        if eos.identity != self.eos_identity:
            raise ValueError("Finite reservoir inventory names a different isothermal EOS")

    def pressure_at_mass(self, mass_kg: float, eos: IsothermalSinglePhaseEOS) -> float:
        """Evaluate pressure from mass/volume and replay density through EOS."""
        self.require_eos(eos)
        mass = finite(mass_kg, "reservoir mass_kg", positive=True)
        if not self.minimum_mass_kg < mass <= self.maximum_mass_kg:
            raise ValueError("Reservoir mass is depleted or outside its declared inventory bounds")
        density = mass / self.volume_m3
        pressure = finite(eos.pressure_rho_t(density, self.temperature_k),
                           "finite reservoir pressure", positive=True)
        density_replay = finite(eos.density_pt(pressure, self.temperature_k),
                                "finite reservoir density replay", positive=True)
        if abs(density_replay - density) > 1.e-8 * max(1., abs(density)):
            raise ValueError("Finite reservoir EOS pressure/density replay does not close")
        return pressure

    def advance(self, *, current_mass_kg: float, pipe_outward_mass_flow_kg_s: float,
                duration_s: float) -> tuple[float, float]:
        """Update inventory by an integrated signed pipe-side boundary flux.

        Returns `(new_mass_kg, mass_residual_kg)`. The caller must pass the
        exact flux used by the network endpoint Rusanov update, with positive
        sign oriented from reservoir into pipe. Invalid/depleted steps reject;
        no clipping or implicit flow limiting is performed.
        """
        return self.advance_with_leak(
            current_mass_kg=current_mass_kg,
            pipe_outward_mass_flow_kg_s=pipe_outward_mass_flow_kg_s,
            nozzle_outflow_mass_flow_kg_s=0., duration_s=duration_s,
        )

    def advance_with_leak(self, *, current_mass_kg: float,
                          pipe_outward_mass_flow_kg_s: float,
                          nozzle_outflow_mass_flow_kg_s: float,
                          duration_s: float) -> tuple[float, float]:
        """Advance from pipe exchange plus an independent leak/nozzle sink.

        Positive pipe outward flow transfers stock into the pipe; nozzle flow
        is a nonnegative external withdrawal. The resulting stock is checked
        once after both terms are combined, so a transient intermediate value
        is never used as a separate inventory state.
        """
        current = finite(current_mass_kg, "current reservoir mass", positive=True)
        if not self.minimum_mass_kg < current <= self.maximum_mass_kg:
            raise ValueError("Current reservoir inventory is depleted or out of bounds")
        outward_rate = finite(pipe_outward_mass_flow_kg_s,
                              "pipe outward mass flow")
        leak_rate = finite(nozzle_outflow_mass_flow_kg_s,
                           "nozzle outflow mass flow")
        if leak_rate < 0.:
            raise ValueError("Nozzle outflow must be nonnegative")
        duration = finite(duration_s, "reservoir step duration", positive=True)
        final = current - duration * (outward_rate + leak_rate)
        if not self.minimum_mass_kg < final <= self.maximum_mass_kg:
            raise ValueError("Finite reservoir step depletes or exceeds its declared inventory bounds")
        residual = (final - current) + duration * (outward_rate + leak_rate)
        return final, residual

    def require_subsonic(self, *, mass_kg: float, outward_mass_flow_kg_s: float,
                         endpoint_area_m2: float,
                         eos: IsothermalSinglePhaseEOS) -> float:
        """Reject endpoint states outside the model's subsonic characteristic scope."""
        pressure = self.pressure_at_mass(mass_kg, eos)
        density = finite(eos.density_pt(pressure, self.temperature_k),
                         "finite reservoir density", positive=True)
        area = finite(endpoint_area_m2, "endpoint area_m2", positive=True)
        rate = finite(outward_mass_flow_kg_s, "pipe outward mass flow")
        velocity = rate / (density * area)
        sound_speed = finite(eos.isothermal_sound_speed_rho_t(density, self.temperature_k),
                             "isothermal sound speed", positive=True)
        if abs(velocity) >= sound_speed:
            raise ValueError("Finite reservoir endpoint state is supersonic")
        return pressure


__all__ = ["FiniteIsothermalPipeReservoir"]
