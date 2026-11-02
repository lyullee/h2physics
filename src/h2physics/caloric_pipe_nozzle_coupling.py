"""Typed nozzle coupling for a finite caloric pipe-network inventory."""

from __future__ import annotations

from dataclasses import dataclass

from .core import Origin, ThermoState, finite
from .finite_caloric_pipe_reservoir import FiniteCaloricPipeReservoir
from .release import HomogeneousIsentropicNozzle, NozzleOpening, NozzleResult, SourceLocation


@dataclass(frozen=True, slots=True)
class CaloricFiniteReservoirNozzleCoupling:
    """Caller-owned nozzle boundary attached to one finite caloric tank node.

    The upstream state is recovered from the tank's current ``m,U,V`` by the
    network EOS. The nozzle provider must use the exact same property basis
    and reproduce that state within the declared density tolerances.
    """

    identifier: str
    node_id: str
    reservoir_id: str
    edge_id: str
    opening: NozzleOpening
    opening_fraction: float
    back_pressure_pa: float
    location: SourceLocation
    nozzle: HomogeneousIsentropicNozzle
    state_owner_id: str
    evidence_id: str
    origin: Origin
    density_relative_tolerance: float = 2.e-6
    density_absolute_tolerance_kg_m3: float = 1.e-10

    def __post_init__(self) -> None:
        for name in ("identifier", "node_id", "reservoir_id", "edge_id",
                     "state_owner_id", "evidence_id"):
            if not isinstance(getattr(self, name), str) or not getattr(self, name).strip():
                raise ValueError(f"Declare caloric nozzle coupling {name}")
        if type(self.opening) is not NozzleOpening:
            raise TypeError("Caloric nozzle coupling requires NozzleOpening")
        if type(self.location) is not SourceLocation:
            raise TypeError("Caloric nozzle coupling requires SourceLocation")
        if type(self.nozzle) is not HomogeneousIsentropicNozzle:
            raise TypeError("Caloric nozzle coupling requires HomogeneousIsentropicNozzle")
        fraction = finite(self.opening_fraction, "opening_fraction")
        if not 0. <= fraction <= 1.:
            raise ValueError("Nozzle opening fraction must lie in [0, 1]")
        finite(self.back_pressure_pa, "back_pressure_pa", positive=True)
        finite(self.density_relative_tolerance, "density_relative_tolerance", positive=True)
        finite(self.density_absolute_tolerance_kg_m3,
               "density_absolute_tolerance_kg_m3", positive=True)
        if self.location.clock_id == "":
            raise ValueError("Nozzle source location must declare its clock")
        origin = Origin(self.origin)
        if origin is Origin.UNRESOLVED:
            raise ValueError("Resolve the caloric nozzle coupling origin")
        object.__setattr__(self, "origin", origin)

    def require_compatible(self, *, reservoir: FiniteCaloricPipeReservoir,
                           eos, clock_id: str, node_coordinates_m: tuple[float, float, float],
                           edge_id: str) -> None:
        if type(reservoir) is not FiniteCaloricPipeReservoir:
            raise TypeError("Caloric nozzle coupling requires a finite caloric reservoir")
        if (self.node_id != reservoir.node_id or self.reservoir_id != reservoir.identifier
                or self.state_owner_id != reservoir.state_owner_id):
            raise ValueError("Nozzle coupling node/reservoir/owner identity does not match")
        if self.edge_id != edge_id:
            raise ValueError("Nozzle coupling must identify the unique incident pipe edge")
        if self.location.clock_id != clock_id or reservoir.clock_id != clock_id:
            raise ValueError("Nozzle source, reservoir and network clocks must match exactly")
        if tuple(self.location.position_m) != tuple(node_coordinates_m):
            raise ValueError("Nozzle source location must match its tank node coordinates")
        if self.nozzle.properties.basis != reservoir.property_basis:
            raise ValueError("Nozzle provider must use the reservoir's exact PropertyBasis")
        if self.nozzle.properties.basis != eos.basis:
            raise ValueError("Nozzle provider and network EOS must use the exact same PropertyBasis")

    def evaluate(self, *, mass_kg: float, internal_energy_j: float,
                 reservoir: FiniteCaloricPipeReservoir, eos) -> NozzleResult:
        """Evaluate from the admitted tank state and cross-check provider identity."""
        upstream = reservoir.recover_state(mass_kg=mass_kg,
                                           internal_energy_j=internal_energy_j, eos=eos)
        provider_state = self.nozzle.properties.state_pt(upstream.pressure_pa,
                                                         upstream.temperature_k)
        self.nozzle.properties.basis.require_compatible(provider_state.basis)
        for name in ("pressure_pa", "temperature_k"):
            expected, actual = getattr(upstream, name), getattr(provider_state, name)
            if abs(actual - expected) > 2.e-6 * max(abs(expected), 1.):
                raise ValueError(f"Nozzle property provider does not reproduce tank {name}")
        density_error = abs(provider_state.density_kg_m3 - upstream.density_kg_m3)
        density_limit = (self.density_absolute_tolerance_kg_m3
                         + self.density_relative_tolerance * abs(upstream.density_kg_m3))
        if density_error > density_limit:
            raise ValueError("Nozzle provider density differs from recovered rho-u tank state")
        if provider_state.phase not in {"gas", "supercritical", "supercritical_gas"}:
            raise ValueError("Finite caloric gas reservoir nozzle requires a gas-like upstream state")
        result = self.nozzle.solve(upstream, back_pressure_pa=self.back_pressure_pa,
                                   opening=self.opening,
                                   opening_fraction=self.opening_fraction)
        if result.mass_flow_kg_s < 0. or result.withdrawal_energy_w < 0.:
            raise ValueError("Nozzle result must be a nonnegative outward tank debit")
        return result


__all__ = ["CaloricFiniteReservoirNozzleCoupling"]
