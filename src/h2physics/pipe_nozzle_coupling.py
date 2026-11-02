"""Explicit isothermal pipe-reservoir to shared-nozzle source coupling."""

from __future__ import annotations

from dataclasses import dataclass

from .core import Origin, PropertyBasis, ThermoState, finite
from .finite_pipe_reservoir import FiniteIsothermalPipeReservoir
from .release import HomogeneousIsentropicNozzle, NozzleOpening, NozzleResult, SourceLocation
from .thermo.isothermal_eos import IsothermalSinglePhaseEOS


@dataclass(frozen=True, slots=True)
class IsothermalToCaloricStateMapping:
    """Caller evidence that maps network EOS states to a nozzle caloric basis."""

    source_eos_identity: str
    target_basis: PropertyBasis
    evidence_id: str
    density_relative_tolerance: float
    density_absolute_tolerance_kg_m3: float

    def __post_init__(self) -> None:
        if not isinstance(self.source_eos_identity, str) or not self.source_eos_identity.strip():
            raise ValueError("Declare the source isothermal EOS identity")
        if type(self.target_basis) is not PropertyBasis:
            raise TypeError("Retain the explicit nozzle caloric PropertyBasis")
        if not isinstance(self.evidence_id, str) or not self.evidence_id.strip():
            raise ValueError("Declare evidence for the isothermal-to-caloric EOS mapping")
        relative = finite(self.density_relative_tolerance, "density_relative_tolerance")
        absolute = finite(self.density_absolute_tolerance_kg_m3,
                          "density_absolute_tolerance_kg_m3")
        if relative < 0. or absolute < 0. or (relative == 0. and absolute == 0.):
            raise ValueError("Declare a positive density-mapping tolerance budget")
        object.__setattr__(self, "density_relative_tolerance", relative)
        object.__setattr__(self, "density_absolute_tolerance_kg_m3", absolute)


@dataclass(frozen=True, slots=True)
class FiniteReservoirNozzleCoupling:
    """A fixed opening that withdraws mass from one network reservoir each step.

    The opening and external back pressure are caller-owned. Caloric state is
    obtained from the nozzle's PropertyProvider at each reservoir pressure and
    fixed network temperature; the declared mapping evidence and density
    tolerance are checked against the network's isothermal EOS state.
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
    state_mapping: IsothermalToCaloricStateMapping
    evidence_id: str
    origin: Origin

    def __post_init__(self) -> None:
        for label, value in (
            ("coupling identifier", self.identifier),
            ("network node ID", self.node_id),
            ("finite reservoir ID", self.reservoir_id),
            ("endpoint edge ID", self.edge_id),
            ("coupling evidence ID", self.evidence_id),
        ):
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"Declare {label}")
        if not isinstance(self.opening, NozzleOpening):
            raise TypeError("Supply the existing shared nozzle opening contract")
        if not isinstance(self.nozzle, HomogeneousIsentropicNozzle):
            raise TypeError("Supply the existing HomogeneousIsentropicNozzle owner")
        if type(self.state_mapping) is not IsothermalToCaloricStateMapping:
            raise TypeError("Supply explicit isothermal-to-caloric EOS mapping evidence")
        if not isinstance(self.location, SourceLocation):
            raise TypeError("Supply a source location with an explicit clock and frame")
        if self.location.source_id != self.identifier:
            raise ValueError("SourceLocation source_id must match the leak-coupling identifier")
        if not isinstance(self.origin, Origin):
            object.__setattr__(self, "origin", Origin(self.origin))
        if self.origin is Origin.UNRESOLVED:
            raise ValueError("Resolve the source origin before applying a nozzle sink")
        fraction = finite(self.opening_fraction, "nozzle opening fraction")
        if not 0. <= fraction <= 1.:
            raise ValueError("Nozzle opening fraction must lie in [0, 1]")
        object.__setattr__(self, "opening_fraction", fraction)
        object.__setattr__(self, "back_pressure_pa",
                           finite(self.back_pressure_pa, "nozzle back pressure", positive=True))
        self.nozzle.properties.basis.require_compatible(self.state_mapping.target_basis)
        if (self.state_mapping.target_basis.fluid != "Hydrogen"
                or self.state_mapping.target_basis.spin_composition != "normal"):
            raise ValueError("This gas-release bridge requires a normal-hydrogen caloric property basis")

    @property
    def caloric_basis(self) -> PropertyBasis:
        return self.state_mapping.target_basis

    def require_compatible(self, *, reservoir: FiniteIsothermalPipeReservoir,
                           eos: IsothermalSinglePhaseEOS, clock_id: str,
                           node_id: str, edge_id: str) -> None:
        if type(reservoir) is not FiniteIsothermalPipeReservoir:
            raise TypeError("Retain the finite isothermal reservoir owning this nozzle source")
        if (self.node_id != node_id or self.edge_id != edge_id
                or self.reservoir_id != reservoir.identifier
                or reservoir.node_id != node_id):
            raise ValueError("Nozzle coupling node/edge/reservoir identities do not match the network endpoint")
        if (self.location.clock_id != clock_id or reservoir.clock_id != clock_id):
            raise ValueError("Source location and finite inventory must use the network clock")
        if (self.state_mapping.source_eos_identity != eos.identity
                or reservoir.eos_identity != eos.identity):
            raise ValueError("Nozzle state mapping and reservoir must name the exact network EOS identity")
        self.nozzle.properties.basis.require_compatible(self.state_mapping.target_basis)

    def state_at_mass(self, *, mass_kg: float, reservoir: FiniteIsothermalPipeReservoir,
                      eos: IsothermalSinglePhaseEOS) -> ThermoState:
        """Map inventory P/T to a checked caloric state for the shared nozzle."""
        self.require_compatible(
            reservoir=reservoir, eos=eos,
            clock_id=reservoir.clock_id, node_id=reservoir.node_id,
            edge_id=self.edge_id,
        )
        pressure = reservoir.pressure_at_mass(mass_kg, eos)
        density_network = finite(mass_kg, "reservoir mass_kg", positive=True) / reservoir.volume_m3
        state = self.nozzle.properties.state_pt(pressure, reservoir.temperature_k)
        if not isinstance(state, ThermoState):
            raise TypeError("Nozzle PropertyProvider must return a ThermoState")
        state.basis.require_compatible(self.state_mapping.target_basis)
        if state.phase not in {"gas", "supercritical_gas", "supercritical"}:
            raise ValueError("Nozzle release requires a homogeneous gas/supercritical reservoir state")
        if (not abs(state.pressure_pa - pressure) <= 1.e-8 * max(pressure, 1.)
                or not abs(state.temperature_k - reservoir.temperature_k)
                <= 1.e-8 * max(reservoir.temperature_k, 1.)):
            raise ValueError("Caloric provider did not reproduce the network reservoir P/T state")
        tolerance = (self.state_mapping.density_absolute_tolerance_kg_m3
                     + self.state_mapping.density_relative_tolerance * abs(density_network))
        if abs(state.density_kg_m3 - density_network) > tolerance:
            raise ValueError("Caloric and isothermal EOS densities exceed the declared mapping budget")
        return state

    def nozzle_result(self, *, mass_kg: float, reservoir: FiniteIsothermalPipeReservoir,
                      eos: IsothermalSinglePhaseEOS) -> tuple[ThermoState, NozzleResult]:
        state = self.state_at_mass(mass_kg=mass_kg, reservoir=reservoir, eos=eos)
        result = self.nozzle.solve(
            state, back_pressure_pa=self.back_pressure_pa,
            opening=self.opening, opening_fraction=self.opening_fraction,
        )
        if result.opening != self.opening or result.mass_flow_kg_s < 0.:
            raise ValueError("Shared nozzle result lost the declared opening or outward-flow convention")
        return state, result


__all__ = ["IsothermalToCaloricStateMapping", "FiniteReservoirNozzleCoupling"]
