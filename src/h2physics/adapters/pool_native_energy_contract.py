"""Validation contract for energy terms emitted at native pool accepted edges.

This module does not integrate pool heat, evaporation, or wall dynamics. The
native pool solver must provide each accepted-edge state and interval-integrated
transfers itself. The host only verifies the emitted trace and its balances.
"""

from dataclasses import dataclass, field
from math import fsum

from ..core import finite


_CUMULATIVE = (
    "cumulative_liquid_inlet_mass_kg",
    "cumulative_vapor_outlet_mass_kg",
    "cumulative_liquid_inlet_enthalpy_j",
    "cumulative_vapor_outlet_enthalpy_j",
    "cumulative_substrate_heat_into_liquid_j",
    "cumulative_pressure_volume_work_out_j",
    "cumulative_unapplied_heat_j",
    "cumulative_dry_surface_heat_j",
    "cumulative_heat_cap_rejection_j",
)


class PoolNativeEnergyCapabilityError(RuntimeError):
    """The native result does not issue accepted-edge energy records."""


@dataclass(frozen=True, slots=True)
class PoolNativeEnergyEdge:
    """One original accepted solver edge and the terms emitted by that solver.

    Cumulative transfers must be integrated inside the native solver across its
    actual internal/event intervals. This record is not an output-sample
    quadrature interface. ``accepted_state`` and ``step_identity`` preserve the
    original native objects for audit.
    """

    time_s: float
    step_identity: str
    accepted_state: object = field(repr=False, compare=False)
    liquid_mass_kg: float
    liquid_internal_energy_j: float
    liquid_volume_m3: float
    boundary_pressure_pa: float
    cumulative_liquid_inlet_mass_kg: float
    cumulative_vapor_outlet_mass_kg: float
    cumulative_liquid_inlet_enthalpy_j: float
    cumulative_vapor_outlet_enthalpy_j: float
    cumulative_substrate_heat_into_liquid_j: float
    cumulative_pressure_volume_work_out_j: float
    cumulative_unapplied_heat_j: float
    cumulative_dry_surface_heat_j: float
    cumulative_heat_cap_rejection_j: float
    substrate_energy_change_j: float | None = None
    cumulative_external_heat_into_substrate_j: float | None = None

    def __post_init__(self):
        object.__setattr__(self, "time_s", finite(self.time_s, "accepted time"))
        if not isinstance(self.step_identity, str) or not self.step_identity.strip():
            raise ValueError("Every accepted pool edge requires its native step identity")
        if self.accepted_state is None:
            raise ValueError("Retain the exact native accepted state object")
        for name in ("time_s", "liquid_mass_kg", "liquid_internal_energy_j",
                     "liquid_volume_m3", "boundary_pressure_pa"):
            try:
                state_value = finite(getattr(self.accepted_state, name),
                                     f"native accepted state {name}")
            except (AttributeError, TypeError, ValueError) as error:
                raise ValueError(f"Native accepted state must expose {name}") from error
            if state_value != finite(getattr(self, name), name):
                raise ValueError(f"Pool edge {name} differs from its exact native accepted state")
        nonnegative = ("liquid_mass_kg", "liquid_volume_m3",
                       "cumulative_liquid_inlet_mass_kg",
                       "cumulative_vapor_outlet_mass_kg",
                       "cumulative_unapplied_heat_j", "cumulative_dry_surface_heat_j",
                       "cumulative_heat_cap_rejection_j")
        for name in nonnegative:
            value = finite(getattr(self, name), name)
            if value < 0.:
                raise ValueError(f"{name} cannot be negative")
            object.__setattr__(self, name, value)
        object.__setattr__(self, "liquid_internal_energy_j",
                           finite(self.liquid_internal_energy_j, "liquid internal energy"))
        object.__setattr__(self, "boundary_pressure_pa",
                           finite(self.boundary_pressure_pa, "boundary pressure", positive=True))
        for name in ("substrate_energy_change_j", "cumulative_external_heat_into_substrate_j"):
            value = getattr(self, name)
            if value is not None:
                object.__setattr__(self, name, finite(value, name))


@dataclass(frozen=True, slots=True)
class PoolNativeEnergyTrace:
    """Audited immutable view over terms emitted by an original native pool run."""

    native_result: object = field(repr=False, compare=False)
    accepted_edges: tuple[PoolNativeEnergyEdge, ...]
    substrate_mode: str
    energy_reference_id: str
    vapor_phase_id: str
    mass_tolerance_kg: float
    energy_tolerance_j: float
    _seal: tuple = field(default=(), init=False, repr=False, compare=False)

    def __post_init__(self):
        if self.native_result is None:
            raise TypeError("Retain the exact original native pool result")
        issued = getattr(self.native_result, "accepted_energy_samples", None)
        if issued is None:
            raise PoolNativeEnergyCapabilityError(
                "Native result must issue its own accepted_energy_samples")
        edges = tuple(self.accepted_edges)
        if len(edges) < 2 or any(type(edge) is not PoolNativeEnergyEdge for edge in edges):
            raise ValueError("Supply the initial state and at least one native accepted edge")
        try:
            issued = tuple(issued)
        except TypeError as error:
            raise PoolNativeEnergyCapabilityError(
                "Native accepted_energy_samples must be an iterable of edge records") from error
        if len(issued) != len(edges) or any(a is not b for a, b in zip(issued, edges, strict=True)):
            raise ValueError("Trace edges must be the exact objects issued by the retained native result")
        if self.substrate_mode not in {"prescribed_external_reservoir", "finite_wall"}:
            raise ValueError("Select prescribed external reservoir or finite-wall substrate")
        for name in ("energy_reference_id", "vapor_phase_id"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"Declare the native {name}")
        mass_tol = finite(self.mass_tolerance_kg, "mass tolerance", positive=True)
        energy_tol = finite(self.energy_tolerance_j, "energy tolerance", positive=True)
        object.__setattr__(self, "mass_tolerance_kg", mass_tol)
        object.__setattr__(self, "energy_tolerance_j", energy_tol)
        object.__setattr__(self, "accepted_edges", edges)
        self._audit()
        object.__setattr__(self, "_seal", self._fingerprint())

    def _audit(self):
        edges = self.accepted_edges
        if any(b.time_s <= a.time_s for a, b in zip(edges[:-1], edges[1:], strict=True)):
            raise ValueError("Native accepted-edge clock must increase strictly")
        first = edges[0]
        if any(getattr(first, name) != 0. for name in _CUMULATIVE):
            raise ValueError("All native cumulative transfers and allocations start at zero")
        if self.substrate_mode == "finite_wall":
            if first.substrate_energy_change_j != 0. or first.cumulative_external_heat_into_substrate_j != 0.:
                raise ValueError("Finite-wall U change and heat integral start at zero")
        elif any(edge.substrate_energy_change_j is not None
                 or edge.cumulative_external_heat_into_substrate_j is not None for edge in edges):
            raise ValueError("External-reservoir mode cannot claim finite-wall storage or heat")
        for name in _CUMULATIVE:
            values = tuple(getattr(edge, name) for edge in edges)
            if any(b < a for a, b in zip(values[:-1], values[1:], strict=True)):
                if name in {"cumulative_unapplied_heat_j", "cumulative_dry_surface_heat_j",
                            "cumulative_heat_cap_rejection_j"}:
                    raise ValueError(f"Cumulative heat allocation {name} must not decrease")
                # Heat/work and reference-dependent enthalpy integrals can
                # decrease. Gross mass and allocation diagnostics cannot.
                if name not in {"cumulative_substrate_heat_into_liquid_j",
                                "cumulative_pressure_volume_work_out_j",
                                "cumulative_liquid_inlet_enthalpy_j",
                                "cumulative_vapor_outlet_enthalpy_j"}:
                    raise ValueError(f"Cumulative outward/inward magnitude {name} must not decrease")
        m0, u0 = first.liquid_mass_kg, first.liquid_internal_energy_j
        for edge in edges:
            mass_residual = fsum((edge.liquid_mass_kg, -m0,
                -edge.cumulative_liquid_inlet_mass_kg,
                edge.cumulative_vapor_outlet_mass_kg))
            energy_residual = fsum((edge.liquid_internal_energy_j, -u0,
                -edge.cumulative_liquid_inlet_enthalpy_j,
                edge.cumulative_vapor_outlet_enthalpy_j,
                -edge.cumulative_substrate_heat_into_liquid_j,
                edge.cumulative_pressure_volume_work_out_j))
            if abs(mass_residual) > self.mass_tolerance_kg:
                raise ValueError("Native accepted-edge pool mass balance exceeds tolerance")
            if abs(energy_residual) > self.energy_tolerance_j:
                raise ValueError("Native accepted-edge liquid energy balance exceeds tolerance")
            if self.substrate_mode == "finite_wall":
                residual = fsum((edge.substrate_energy_change_j,
                    -edge.cumulative_external_heat_into_substrate_j,
                    edge.cumulative_substrate_heat_into_liquid_j))
                if abs(residual) > self.energy_tolerance_j:
                    raise ValueError("Native accepted-edge finite-wall balance exceeds tolerance")

    def _fingerprint(self):
        return (id(self.native_result), self.substrate_mode, self.energy_reference_id,
                self.vapor_phase_id, self.mass_tolerance_kg, self.energy_tolerance_j,
                tuple((edge.time_s, edge.step_identity, id(edge.accepted_state),
                       tuple(finite(getattr(edge.accepted_state, name), name) for name in (
                           "time_s", "liquid_mass_kg", "liquid_internal_energy_j",
                           "liquid_volume_m3", "boundary_pressure_pa")),
                       tuple(getattr(edge, name) for name in (
                           "liquid_mass_kg", "liquid_internal_energy_j", "liquid_volume_m3",
                           "boundary_pressure_pa", *_CUMULATIVE,
                           "substrate_energy_change_j", "cumulative_external_heat_into_substrate_j")))
                      for edge in self.accepted_edges))

    def verify_result(self, result):
        """Return the exact native run after detecting detached or mutated traces."""
        if result is not self.native_result or not self._seal or self._fingerprint() != self._seal:
            raise ValueError("Pool energy trace no longer matches its original native run")
        issued = tuple(getattr(result, "accepted_energy_samples", ()))
        if len(issued) != len(self.accepted_edges) or any(
                a is not b for a, b in zip(issued, self.accepted_edges, strict=True)):
            raise ValueError("Native result changed its issued accepted-edge sequence")
        self._audit()
        return result

    @property
    def mass_residual_kg(self):
        first = self.accepted_edges[0].liquid_mass_kg
        return tuple(fsum((edge.liquid_mass_kg, -first,
            -edge.cumulative_liquid_inlet_mass_kg,
            edge.cumulative_vapor_outlet_mass_kg)) for edge in self.accepted_edges)

    @property
    def energy_residual_j(self):
        first = self.accepted_edges[0].liquid_internal_energy_j
        return tuple(fsum((edge.liquid_internal_energy_j, -first,
            -edge.cumulative_liquid_inlet_enthalpy_j,
            edge.cumulative_vapor_outlet_enthalpy_j,
            -edge.cumulative_substrate_heat_into_liquid_j,
            edge.cumulative_pressure_volume_work_out_j)) for edge in self.accepted_edges)


__all__ = ["PoolNativeEnergyCapabilityError", "PoolNativeEnergyEdge", "PoolNativeEnergyTrace"]
