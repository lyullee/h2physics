"""Cantera native catalytic plug-flow reactor with source-bound outputs.

This level uses Cantera's steady FlowReactor and ReactorSurface for a single
ideal-gas stream over one ideal catalytic surface. It does not model pressure
drop, pore diffusion, finite catalyst thermal storage, or a plant-scale yield.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

import numpy as np

from ..core import finite, immutable_array
from .cantera import MechanismBasis, NativeMechanismSource, ReactiveState
from .result_provenance import recorded_content_sha256


def _array(values, name: str) -> np.ndarray:
    result = np.asarray(values, dtype=float)
    if result.ndim != 1 or len(result) < 2 or not np.all(np.isfinite(result)):
        raise ValueError(f"{name} must be a finite one-dimensional sequence with at least two entries")
    return immutable_array(result, name=name)


@dataclass(frozen=True, slots=True)
class CatalyticPFRPoint:
    """One accepted axial state from the native steady-flow integration."""

    axial_position_m: float
    temperature_k: float
    pressure_pa: float
    density_kg_m3: float
    speed_m_s: float
    gas_mole_fractions: np.ndarray
    surface_coverages: np.ndarray

    def __post_init__(self):
        finite(self.axial_position_m, "axial position m")
        if self.axial_position_m < 0.0:
            raise ValueError("Axial position cannot be negative")
        for name in ("temperature_k", "pressure_pa", "density_kg_m3", "speed_m_s"):
            finite(getattr(self, name), name, positive=True)
        object.__setattr__(self, "gas_mole_fractions", immutable_array(
            self.gas_mole_fractions, name="gas mole fractions"))
        object.__setattr__(self, "surface_coverages", immutable_array(
            self.surface_coverages, name="surface coverages"))


@dataclass(frozen=True, slots=True)
class CatalyticPFRTrace:
    """Retained native objects and requested-grid outputs for one PFR run."""

    owner: CanteraCatalyticPFR
    source: NativeMechanismSource
    basis: MechanismBasis
    inlet: ReactiveState
    initial_coverages: tuple[tuple[str, float], ...]
    cross_section_area_m2: float
    surface_area_to_volume_m_inv: float
    mass_flow_rate_kg_s: float
    axial_position_m: np.ndarray
    points: tuple[CatalyticPFRPoint, ...]
    gas_species_names: tuple[str, ...]
    surface_species_names: tuple[str, ...]
    native_gas: object
    native_surface: object
    native_reactor: object
    native_interface: object
    native_network: object
    configuration_sha256: str
    _issuer_token: object
    _seal: str

    def __post_init__(self):
        if type(self.owner) is not CanteraCatalyticPFR:
            raise TypeError("A PFR trace must retain its original model owner")
        if not self.owner._consume_trace_token(self._issuer_token):
            raise TypeError("Issue PFR traces only from a completed native integration")
        if type(self.source) is not NativeMechanismSource or type(self.basis) is not MechanismBasis:
            raise TypeError("Retain the exact source-bound mechanism and domain")
        positions = _array(self.axial_position_m, "axial_position_m")
        points = tuple(self.points)
        if (len(points) != len(positions)
                or any(type(point) is not CatalyticPFRPoint for point in points)
                or tuple(point.axial_position_m for point in points) != tuple(positions)):
            raise ValueError("Retain exactly one native point per requested axial position")
        object.__setattr__(self, "axial_position_m", positions)
        object.__setattr__(self, "points", points)
        object.__setattr__(self, "gas_species_names", tuple(self.gas_species_names))
        object.__setattr__(self, "surface_species_names", tuple(self.surface_species_names))

    def _content(self):
        return recorded_content_sha256((
            id(self.owner), self.source, self.basis, self.inlet, self.initial_coverages,
            self.cross_section_area_m2, self.surface_area_to_volume_m_inv,
            self.mass_flow_rate_kg_s, self.axial_position_m, self.points,
            self.gas_species_names, self.surface_species_names,
            tuple(id(v) for v in (self.native_gas, self.native_surface, self.native_reactor,
                                  self.native_interface, self.native_network)),
            self.native_reactor.area, self.native_reactor.mass_flow_rate,
            self.native_reactor.surface_area_to_volume_ratio, self.native_network.distance,
            float(self.native_reactor.phase.T), float(self.native_reactor.phase.P),
            tuple(float(v) for v in self.native_reactor.phase.X),
            tuple(float(v) for v in self.native_interface.coverages),
        ))

    def require_current(self):
        """Reject mutation of the original mechanism, result, or native endpoint."""
        if hashlib.sha256(self.source.source_bytes).hexdigest() != self.basis.source_sha256:
            raise ValueError("Catalytic PFR mechanism bytes no longer match their declared basis")
        if (self.owner._configuration() != self.configuration_sha256
                or self._content() != self._seal
                or self.native_surface.reactor is not self.native_reactor
                or self.native_reactor.phase is not self.native_gas
                or self.native_surface.phase is not self.native_interface):
            raise ValueError("Catalytic PFR source, native endpoint, or retained output changed")
        return self


class CanteraCatalyticPFR:
    """Steady ideal-gas plug flow over one native Cantera ideal surface.

    Mechanism and surface kinetics are supplied by the caller. Cantera owns
    reaction-rate evaluation, surface coverage evolution, and native spatial
    integration. The adapter binds mechanism bytes, model envelope, and the
    native objects so the output cannot be silently reused after mutation.
    """

    def __init__(self, source: NativeMechanismSource, basis: MechanismBasis, *,
                 gas_phase_name: str, surface_phase_name: str):
        if type(source) is not NativeMechanismSource or type(basis) is not MechanismBasis:
            raise TypeError("Supply source-bound Cantera mechanism bytes and a MechanismBasis")
        if hashlib.sha256(source.source_bytes).hexdigest() != basis.source_sha256:
            raise ValueError("Cantera mechanism bytes do not match MechanismBasis SHA-256")
        for value in (gas_phase_name, surface_phase_name):
            if not isinstance(value, str) or not value.strip():
                raise ValueError("Declare the gas and catalytic surface phase names")
        if source.phase_name != gas_phase_name:
            raise ValueError("Native mechanism source phase differs from the selected gas phase")
        self.source, self.basis = source, basis
        self.gas_phase_name, self.surface_phase_name = gas_phase_name, surface_phase_name
        self._pending_trace_tokens = set()

    def _issue_trace_token(self):
        token = object()
        self._pending_trace_tokens.add(token)
        return token

    def _consume_trace_token(self, token):
        if token not in self._pending_trace_tokens:
            return False
        self._pending_trace_tokens.remove(token)
        return True

    def _configuration(self):
        return recorded_content_sha256((id(self), self.source, self.basis,
                                        self.gas_phase_name, self.surface_phase_name))

    def run(self, inlet: ReactiveState, *, initial_coverages, axial_position_m,
            cross_section_area_m2: float, surface_area_to_volume_m_inv: float,
            mass_flow_rate_kg_s: float, maximum_axial_step_m: float,
            relative_tolerance: float, absolute_tolerance: float,
            site_fraction_tolerance: float = 1e-8) -> CatalyticPFRTrace:
        """Integrate the caller's steady feed along strictly increasing axial positions.

        Positions are measured from the reactor inlet in metres. The requested
        output grid is not an integration mesh; ``maximum_axial_step_m`` limits
        the native network's internal advance distance.
        """
        import cantera as ct

        if tuple(int(part) for part in ct.__version__.split(".")[:2]) != (3, 2):
            raise ValueError("This adapter currently admits Cantera 3.2")
        if type(inlet) is not ReactiveState:
            raise TypeError("Supply the shared explicit ReactiveState for inlet conditions")
        positions = _array(axial_position_m, "axial_position_m")
        if positions[0] != 0.0 or np.any(np.diff(positions) <= 0.0):
            raise ValueError("Axial positions must begin at zero and increase strictly")
        area = finite(cross_section_area_m2, "cross section area m2", positive=True)
        ratio = finite(surface_area_to_volume_m_inv, "surface area to volume ratio", positive=True)
        flow = finite(mass_flow_rate_kg_s, "mass flow kg/s", positive=True)
        dz = finite(maximum_axial_step_m, "maximum axial step m", positive=True)
        rtol = finite(relative_tolerance, "relative tolerance", positive=True)
        atol = finite(absolute_tolerance, "absolute tolerance", positive=True)
        site_budget = finite(site_fraction_tolerance, "site fraction tolerance", positive=True)
        self.basis.require_state(inlet.temperature_k, inlet.pressure_pa)
        configuration = self._configuration()
        raw = self.source.source_bytes.decode("utf-8")

        surface = ct.Interface(yaml=raw, name=self.surface_phase_name)
        if (surface.thermo_model != "ideal-surface"
                or set(surface.adjacent) != {self.gas_phase_name}):
            raise ValueError("This level requires one ideal catalytic surface adjacent to one gas phase")
        gas = surface.adjacent[self.gas_phase_name]
        if gas.thermo_model != "ideal-gas":
            raise ValueError("This level requires the mechanism's native ideal-gas phase")
        if set(inlet.mole_fractions) - set(gas.species_names):
            raise ValueError("Inlet species are not all present in the selected gas phase")
        gas.TPX = inlet.temperature_k, inlet.pressure_pa, dict(inlet.mole_fractions)
        surface.TP = inlet.temperature_k, inlet.pressure_pa
        coverages = dict(initial_coverages)
        if (set(coverages) != set(surface.species_names)
                or any(finite(value, "initial surface coverage") < 0.0
                       for value in coverages.values())
                or abs(sum(coverages.values()) - 1.0) > site_budget):
            raise ValueError("Supply a complete nonnegative normalized set of surface coverages")
        surface.coverages = coverages

        reactor = ct.FlowReactor(gas, energy="on", clone=False)
        reactor.area = area
        reactor.mass_flow_rate = flow
        reactor.surface_area_to_volume_ratio = ratio
        native_surface = ct.ReactorSurface(surface, reactor, clone=False)
        network = ct.ReactorNet([reactor])
        network.rtol, network.atol = rtol, atol
        network.max_time_step = dz
        points = []
        for position in positions:
            if self._configuration() != configuration:
                raise ValueError("Catalytic PFR source or domain changed during integration")
            if float(position) > 0.0:
                network.advance(float(position))
            phase = reactor.phase
            interface = native_surface.phase
            self.basis.require_state(float(phase.T), float(phase.P))
            x = np.asarray(phase.X, dtype=float)
            theta = np.asarray(interface.coverages, dtype=float)
            if (not np.all(np.isfinite(x)) or np.any(x < 0.0)
                    or abs(float(np.sum(x)) - 1.0) > 1e-8
                    or not np.all(np.isfinite(theta)) or np.any(theta < 0.0)
                    or abs(float(np.sum(theta)) - 1.0) > site_budget):
                raise ValueError("Native PFR state left its gas or surface fraction domain")
            points.append(CatalyticPFRPoint(
                float(position), float(phase.T), float(phase.P), float(phase.density),
                float(reactor.speed), x, theta,
            ))
        if self._configuration() != configuration:
            raise ValueError("Catalytic PFR source or domain changed before output issuance")
        token = self._issue_trace_token()
        trace = CatalyticPFRTrace(
            self, self.source, self.basis, inlet,
            tuple((name, float(coverages[name])) for name in surface.species_names),
            area, ratio, flow, positions, tuple(points), tuple(gas.species_names),
            tuple(surface.species_names), gas, surface, reactor, native_surface, network,
            configuration, token, "",
        )
        object.__setattr__(trace, "_seal", trace._content())
        return trace
