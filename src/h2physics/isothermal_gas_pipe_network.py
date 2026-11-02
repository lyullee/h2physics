"""Segmented quasi-steady inventories with native EOS or explicit ideal basis.

Native cells obtain fluid properties from the existing CoolProp owner. The
explicit analytic cell basis remains available for numerical comparisons.

Each cell is a fixed-volume, fixed-temperature, well-mixed inventory. Adjacent
cells exchange mass through the shared steady compressible Darcy closure; this
adds spatial pressure/inventory resolution without introducing pipe inertia or
pressure-wave physics.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from hashlib import sha256

import numpy as np
from scipy.integrate import solve_ivp

from .core import finite, immutable_array
from .hydraulics import DarcyGeometry, solve_isothermal_compressible_gas_flow
from .thermo.isothermal_eos import CoolPropIsothermalEOS, CoolPropMixtureIsothermalEOS

_R_UNIVERSAL_J_MOL_K = 8.31446261815324
_PENDING_TRACES: set[object] = set()


def _callable_definition(function):
    actual = getattr(function, "__func__", function)
    closure = getattr(actual, "__closure__", None)
    return (id(actual), id(getattr(actual, "__code__", None)),
            id(getattr(function, "__self__", None)),
            repr(getattr(actual, "__defaults__", None)),
            repr(getattr(actual, "__kwdefaults__", None)),
            repr(getattr(actual, "__dict__", None)),
            tuple((id(cell), repr(cell.cell_contents)) for cell in closure) if closure else ())


def _digest(value):
    return sha256(repr(value).encode("utf-8")).hexdigest()


def _native_definition(eos):
    if type(eos) is CoolPropMixtureIsothermalEOS:
        identity = eos.identity
        properties = eos.properties
        if properties.backend != "HEOS":
            raise ValueError("Native mixture cells require direct CoolProp HEOS")
        method_names = ("density_pt", "pressure_rho_t", "isothermal_sound_speed_rho_t")
        for name in method_names:
            if getattr(getattr(eos, name), "__func__", None) is not getattr(CoolPropMixtureIsothermalEOS, name):
                raise ValueError("Native mixture cells require the original EOS methods")
        if eos._require_gas is not CoolPropMixtureIsothermalEOS._require_gas:
            raise ValueError("Native mixture cells require the original gas-phase admission")
        basis = properties.basis
        mass = properties.molar_mass_kg_mol
        semantics = (basis.fluid, basis.spin_composition, properties.backend, properties.version,
                     mass, basis.reference_id, properties.composition_sha256,
                     properties.coolprop_fluids, properties.mole_fractions,
                     properties.coolprop_molar_masses_kg_mol,
                     tuple(_callable_definition(getattr(getattr(eos, name), "__func__"))
                           for name in method_names),
                     _callable_definition(eos._require_gas),
                     _callable_definition(type(properties).molar_mass_kg_mol.fget))
        ownership = (id(eos), identity, eos._definition_snapshot(),
                     _callable_definition(eos._require_gas))
        return semantics, ownership
    if type(eos) is not CoolPropIsothermalEOS or eos.backend != "HEOS":
        raise TypeError("Native cells require an existing direct CoolProp pure or frozen-mixture isothermal EOS")
    expected_phases = frozenset((eos._cp.iphase_gas, eos._cp.iphase_supercritical_gas,
                                 eos._cp.iphase_supercritical))
    if eos._allowed_phases != expected_phases:
        raise ValueError("Native pipeline EOS must retain its homogeneous-gas phase policy")
    method_names = ("density_pt", "pressure_rho_t", "_update_pt", "_update_rho_t",
                    "_require_homogeneous_gas", "isothermal_sound_speed_rho_t")
    for name in method_names:
        if getattr(getattr(eos, name), "__func__", None) is not getattr(CoolPropIsothermalEOS, name):
            raise ValueError("Native cell requires the original direct CoolProp EOS methods")
    with eos._lock:
        fluids = tuple(eos._state.fluid_names())
        if len(fluids) != 1:
            raise ValueError("This network level requires one pure native fluid")
        if eos.fluid != fluids[0]:
            raise ValueError("Use the canonical native CoolProp fluid name shared by the Darcy closure")
        mass = finite(eos._state.molar_mass(), "native molar mass", positive=True)
    spin = {"Hydrogen": "normal", "ParaHydrogen": "para", "OrthoHydrogen": "ortho"}.get(
        fluids[0], "not-hydrogen")
    semantics = (fluids[0], spin, eos.backend, eos.version,
                 mass, _callable_definition(getattr(eos.density_pt, "__func__", eos.density_pt)),
                 tuple(_callable_definition(getattr(getattr(eos, name), "__func__"))
                       for name in method_names))
    ownership = (id(eos), eos.identity, eos.fluid, id(eos._state), id(eos._cp), eos._allowed_phases)
    return semantics, ownership


@dataclass(frozen=True, slots=True)
class IsothermalPipeCell:
    """One fixed-volume inventory; native EOS is explicit, never a fallback."""

    cell_id: str
    volume_m3: float
    temperature_k: float
    molecular_mass_kg_mol: float | None = None
    initial_mass_kg: float | None = None
    eos: CoolPropIsothermalEOS | CoolPropMixtureIsothermalEOS | None = field(default=None, repr=False, compare=False, kw_only=True)
    _eos_binding: tuple = field(default=(), init=False, repr=False, compare=False)

    def __post_init__(self):
        if not isinstance(self.cell_id, str) or not self.cell_id.strip():
            raise ValueError("Each pipe cell requires a stable nonempty ID")
        if self.initial_mass_kg is None:
            raise ValueError("Declare a positive initial mass or use the native from_pressure factory")
        for name in ("volume_m3", "temperature_k", "initial_mass_kg"):
            finite(getattr(self, name), name, positive=True)
        if self.eos is None:
            if self.molecular_mass_kg_mol is None:
                raise ValueError("An analytic cell requires explicit molecular_mass_kg_mol")
            finite(self.molecular_mass_kg_mol, "molecular_mass_kg_mol", positive=True)
        else:
            binding = _native_definition(self.eos)
            _fluid, _spin, _backend, _version, native_mass, *_details = binding[0]
            if (self.molecular_mass_kg_mol is not None
                    and not np.isclose(self.molecular_mass_kg_mol, native_mass, rtol=1e-9, atol=1e-12)):
                raise ValueError("Cell molecular mass differs from its native fluid")
            object.__setattr__(self, "molecular_mass_kg_mol", native_mass)
            object.__setattr__(self, "_eos_binding", binding)
            self.pressure_for_mass(self.initial_mass_kg)

    @classmethod
    def from_pressure(cls, *, cell_id, volume_m3, temperature_k, pressure_pa, eos):
        """Construct a native cell from direct CoolProp density at P/T."""
        definition = _native_definition(eos)
        p = finite(pressure_pa, "pressure_pa", positive=True)
        volume = finite(volume_m3, "volume_m3", positive=True)
        t = finite(temperature_k, "temperature_k", positive=True)
        mass = eos.density_pt(p, t)*volume
        if definition != _native_definition(eos):
            raise ValueError("Native EOS definition changed during initial density evaluation")
        cell = cls(cell_id, volume, t, initial_mass_kg=mass, eos=eos)
        if cell._eos_binding != definition:
            raise ValueError("Native EOS definition changed before the cell was issued")
        if not np.isclose(cell.initial_pressure_pa, p, rtol=1e-8, atol=1e-6):
            raise ValueError("Native pressure/density paths do not reproduce the requested initial state")
        return cell

    def require_current(self):
        if self.eos is not None and self._eos_binding != _native_definition(self.eos):
            raise ValueError("Pipe-cell native fluid/EOS definition changed")
        return self

    def pressure_for_mass(self, mass_kg):
        self.require_current()
        mass = finite(mass_kg, "cell mass", positive=True)
        if self.eos is not None:
            pressure = self.eos.pressure_rho_t(mass/self.volume_m3, self.temperature_k)
            self.require_current()
            return finite(pressure, "native cell pressure", positive=True)
        return mass*self.specific_gas_constant_j_kg_k*self.temperature_k/self.volume_m3

    @property
    def specific_gas_constant_j_kg_k(self) -> float | None:
        if self.eos is not None:
            return None
        return _R_UNIVERSAL_J_MOL_K / self.molecular_mass_kg_mol

    @property
    def initial_pressure_pa(self) -> float:
        return self.pressure_for_mass(self.initial_mass_kg)


@dataclass(frozen=True, slots=True)
class IsothermalPipeLink:
    """One horizontal, frictional link using the shared steady Darcy solver."""

    link_id: str
    geometry: DarcyGeometry
    viscosity_pa_s: float

    def __post_init__(self):
        if not isinstance(self.link_id, str) or not self.link_id.strip():
            raise ValueError("Each pipe link requires a stable nonempty ID")
        if not isinstance(self.geometry, DarcyGeometry):
            raise TypeError("Pipe links require the shared DarcyGeometry")
        if self.geometry.local_loss_coefficient != 0.0:
            raise ValueError("This transient network level does not include local-loss elements")
        finite(self.viscosity_pa_s, "viscosity_pa_s", positive=True)


@dataclass(frozen=True, slots=True)
class IsothermalGasPipeNetworkTrace:
    """Immutable cell inventories and pressure-driven link flows over time."""

    cell_ids: tuple[str, ...]
    link_ids: tuple[str, ...]
    time_s: np.ndarray = field(repr=False, compare=False)
    mass_kg: np.ndarray = field(repr=False, compare=False)
    pressure_pa: np.ndarray = field(repr=False, compare=False)
    link_mass_flow_kg_s: np.ndarray = field(repr=False, compare=False)
    mass_balance_residual_kg: np.ndarray = field(repr=False, compare=False)
    boundary_evidence_ids: tuple[str, ...]
    friction_law_id: str
    complete: bool
    terminal_cell_id: str | None
    eos_identities: tuple[str, ...] = ()
    network: IsothermalGasPipeNetwork | None = field(default=None, repr=False, compare=False)
    boundary_mass_flow_kg_s: tuple[float, ...] = ()
    _issuer: object = field(default=None, repr=False, compare=False)
    _seal: str = field(default="", init=False, repr=False, compare=False)

    def __post_init__(self):
        cells, links = tuple(self.cell_ids), tuple(self.link_ids)
        if not cells or len(set(cells)) != len(cells):
            raise ValueError("Trace cell IDs must be nonempty and unique")
        if len(links) != len(cells) - 1 or len(set(links)) != len(links):
            raise ValueError("Trace link IDs must identify each adjacent cell pair")
        if type(self.complete) is not bool:
            raise TypeError("complete must be bool")
        if self.complete and self.terminal_cell_id is not None:
            raise ValueError("A complete trace cannot name a terminal inventory event")
        if not self.complete and self.terminal_cell_id not in cells:
            raise ValueError("An incomplete trace must identify its inventory-floor cell")
        if not isinstance(self.friction_law_id, str) or not self.friction_law_id.strip():
            raise ValueError("Trace friction_law_id must identify the caller correlation")
        evidence = tuple(self.boundary_evidence_ids)
        if (not evidence or any(not isinstance(item, str) or not item.strip() for item in evidence)):
            raise ValueError("Boundary rates require explicit evidence identities")
        time = immutable_array(self.time_s, dtype=float, name="time_s")
        mass = immutable_array(self.mass_kg, dtype=float, name="mass_kg")
        pressure = immutable_array(self.pressure_pa, dtype=float, name="pressure_pa")
        flow = immutable_array(self.link_mass_flow_kg_s, dtype=float, name="link_mass_flow_kg_s")
        residual = immutable_array(self.mass_balance_residual_kg, dtype=float,
                                   name="mass_balance_residual_kg")
        n_time, n_cells, n_links = len(time), len(cells), len(links)
        if (n_time < 2 or time.ndim != 1 or not np.all(np.isfinite(time))
                or np.any(np.diff(time) <= 0.)):
            raise ValueError("Trace time samples must be finite and strictly increasing")
        if (mass.shape != (n_time, n_cells) or pressure.shape != mass.shape
                or flow.shape != (n_time, n_links) or residual.shape != (n_time,)):
            raise ValueError("Trace arrays must align on their time, cell, and link axes")
        if (not np.all(np.isfinite(mass)) or np.any(mass <= 0.)
                or not np.all(np.isfinite(pressure)) or np.any(pressure <= 0.)
                or not np.all(np.isfinite(flow)) or not np.all(np.isfinite(residual))):
            raise ValueError("Trace state and balance arrays must be finite and physically bounded")
        object.__setattr__(self, "cell_ids", cells)
        object.__setattr__(self, "link_ids", links)
        object.__setattr__(self, "time_s", time)
        object.__setattr__(self, "mass_kg", mass)
        object.__setattr__(self, "pressure_pa", pressure)
        object.__setattr__(self, "link_mass_flow_kg_s", flow)
        object.__setattr__(self, "mass_balance_residual_kg", residual)
        object.__setattr__(self, "boundary_evidence_ids", evidence)
        if self.network is not None:
            if self._issuer not in _PENDING_TRACES:
                raise TypeError("A network-bound trace must be issued by the original simulate call")
            _PENDING_TRACES.remove(self._issuer)
            object.__setattr__(self, "_seal", self._content())

    def _content(self):
        arrays = tuple((array.dtype.str, array.shape, sha256(array.tobytes()).hexdigest())
                       for array in (self.time_s, self.mass_kg, self.pressure_pa,
                                     self.link_mass_flow_kg_s, self.mass_balance_residual_kg))
        return _digest((id(self.network), self.cell_ids, self.link_ids,
            arrays, self.boundary_evidence_ids,
            self.friction_law_id, self.complete, self.terminal_cell_id,
            self.eos_identities, self.boundary_mass_flow_kg_s))

    def require_current(self):
        if self.network is None or self._seal != self._content():
            raise ValueError("Trace is unissued or its native state/flow/evidence content changed")
        self.network.require_current()
        expected_ids = tuple(cell.eos.identity if cell.eos is not None else "explicit-ideal-gas"
                             for cell in self.network.cells)
        if expected_ids != self.eos_identities:
            raise ValueError("Trace native fluid identities differ from the retained network")
        for masses, pressures, flows in zip(self.mass_kg, self.pressure_pa,
                                            self.link_mass_flow_kg_s, strict=True):
            replay = self.network._pressures(masses)
            if not np.allclose(replay, pressures, rtol=1e-10, atol=1e-6):
                raise ValueError("Stored pressure does not reproduce from the retained cell EOS")
            if not np.allclose(self.network._link_flows(replay), flows, rtol=1e-9, atol=1e-12):
                raise ValueError("Stored flows do not reproduce from the shared Darcy closure")
        expected = np.sum(self.mass_kg, axis=1)-np.sum(self.mass_kg[0])-sum(
            self.boundary_mass_flow_kg_s)*(self.time_s-self.time_s[0])
        if not np.allclose(expected, self.mass_balance_residual_kg, rtol=1e-9, atol=1e-12):
            raise ValueError("Trace signed-boundary mass ledger no longer closes")
        return self


@dataclass(frozen=True, slots=True)
class IsothermalGasPipeNetwork:
    """A one-dimensional chain of finite isothermal gas inventories.

    Positive boundary rates add mass to a cell; negative rates withdraw it.
    Positive link flow is from cell ``i`` to cell ``i+1``. Flow in each link is
    recalculated from the instantaneous endpoint pressures using the existing
    steady isothermal compressible Darcy closure. It has no momentum storage,
    acoustic wave, choking, heat-transfer or species equation. Native pressure
    and steady-link properties come from the existing direct CoolProp owners.
    """

    cells: tuple[IsothermalPipeCell, ...]
    links: tuple[IsothermalPipeLink, ...]
    friction_law: Callable[[float, float], float] = field(repr=False, compare=False)
    friction_law_id: str
    _definition: str = field(default="", init=False, repr=False, compare=False)

    def __post_init__(self):
        cells, links = tuple(self.cells), tuple(self.links)
        if (len(cells) < 2 or any(type(cell) is not IsothermalPipeCell for cell in cells)
                or len({cell.cell_id for cell in cells}) != len(cells)):
            raise ValueError("Supply at least two uniquely identified isothermal pipe cells")
        if len(links) != len(cells) - 1 or any(type(link) is not IsothermalPipeLink for link in links):
            raise ValueError("Supply exactly one ordered Darcy link between each adjacent cell pair")
        if len({link.link_id for link in links}) != len(links):
            raise ValueError("Pipe link identities must be unique")
        basis = {(cell.temperature_k, cell.molecular_mass_kg_mol) for cell in cells}
        if len(basis) != 1:
            raise ValueError("This level uses one fixed temperature and molecular mass across all cells")
        native = tuple(cell.eos is not None for cell in cells)
        if any(native) and not all(native):
            raise ValueError("A network cannot mix native real-fluid and analytic cells")
        if all(native):
            semantics = tuple(_native_definition(cell.eos)[0] for cell in cells)
            if any(value != semantics[0] for value in semantics[1:]):
                raise ValueError("Native cells must match fluid/spin/version and EOS definitions")
        if not callable(self.friction_law):
            raise TypeError("friction_law must be a caller-supplied Darcy factor correlation")
        if not isinstance(self.friction_law_id, str) or not self.friction_law_id.strip():
            raise ValueError("friction_law_id must identify the supplied correlation")
        object.__setattr__(self, "cells", cells)
        object.__setattr__(self, "links", links)
        object.__setattr__(self, "_definition", self._content())

    def _content(self):
        cells = tuple((id(cell), cell.cell_id, cell.volume_m3, cell.temperature_k,
                       cell.molecular_mass_kg_mol, cell.initial_mass_kg,
                       id(cell.eos), cell._eos_binding) for cell in self.cells)
        links = tuple((id(link), link.link_id, link.geometry, link.viscosity_pa_s)
                      for link in self.links)
        return _digest((cells, links, _callable_definition(self.friction_law),
            self.friction_law_id, _callable_definition(solve_isothermal_compressible_gas_flow),
            _callable_definition(type(self)._pressures),
            _callable_definition(type(self)._link_flows),
            _callable_definition(type(self).simulate)))

    def require_current(self):
        for cell in self.cells:
            cell.require_current()
        if self._definition != self._content():
            raise ValueError("Network geometry, boundary basis or Darcy/EOS definition changed")
        return self

    def _pressures(self, masses_kg):
        self.require_current()
        return np.asarray([
            cell.pressure_for_mass(mass)
            for cell, mass in zip(self.cells, masses_kg)
        ], dtype=float)

    def _link_flows(self, pressures_pa):
        self.require_current()
        temperature = self.cells[0].temperature_k
        molar_mass = self.cells[0].molecular_mass_kg_mol
        flows = []
        for left, right, link in zip(pressures_pa[:-1], pressures_pa[1:], self.links):
            delta = left - right
            scale = max(left, right, 1.)
            if abs(delta) <= 1e-12 * scale:
                flows.append(0.)
                continue
            upstream, downstream = (left, right) if delta > 0. else (right, left)
            rate = solve_isothermal_compressible_gas_flow(
                link.geometry,
                upstream_pressure_pa=float(upstream), downstream_pressure_pa=float(downstream),
                temperature_k=temperature, molecular_mass_kg_mol=molar_mass,
                viscosity_pa_s=link.viscosity_pa_s, friction_law=self.friction_law,
                friction_law_id=self.friction_law_id,
                eos=self.cells[0].eos,
            ).mass_flow_kg_s
            flows.append(rate if delta > 0. else -rate)
        return np.asarray(flows, dtype=float)

    def simulate(
        self,
        *,
        boundary_mass_flow_kg_s: Sequence[float],
        boundary_evidence_ids: Sequence[str],
        time_samples_s: Sequence[float],
        minimum_cell_mass_kg: float,
        method: str = "BDF",
        relative_tolerance: float = 1e-8,
        absolute_tolerance_kg: float = 1e-11,
        maximum_step_s: float | None = None,
    ) -> IsothermalGasPipeNetworkTrace:
        """Integrate finite cell stocks with constant signed external boundary rates.

        Event termination is localized when any cell reaches the explicit
        positive stock floor. A terminal trace includes that exact event state
        and the sampled accepted prefix. The constant boundary rates are held
        over the complete requested integration window.
        """
        self.require_current()
        if isinstance(boundary_mass_flow_kg_s, (str, bytes)):
            raise TypeError("boundary_mass_flow_kg_s must be an ordered numeric sequence")
        if isinstance(boundary_evidence_ids, (str, bytes)):
            raise TypeError("boundary_evidence_ids must be an ordered sequence of IDs")
        if isinstance(time_samples_s, (str, bytes)):
            raise TypeError("time_samples_s must be an ordered numeric sequence")
        try:
            boundary_values = tuple(boundary_mass_flow_kg_s)
            evidence = tuple(boundary_evidence_ids)
            time_values = tuple(time_samples_s)
        except TypeError as exc:
            raise TypeError("Boundary rates, evidence IDs, and sample times must be sequences") from exc
        boundary = np.asarray([
            finite(value, f"boundary_mass_flow_kg_s[{index}]")
            for index, value in enumerate(boundary_values)
        ], dtype=float)
        times = np.asarray([
            finite(value, f"time_samples_s[{index}]")
            for index, value in enumerate(time_values)
        ], dtype=float)
        n_cells = len(self.cells)
        if boundary.shape != (n_cells,):
            raise ValueError("Supply one finite signed boundary mass rate per pipe cell")
        if (len(evidence) != n_cells or any(not isinstance(item, str) or not item.strip()
                                            for item in evidence)):
            raise ValueError("Supply one boundary evidence identity per cell rate")
        if len(times) < 2 or np.any(np.diff(times) <= 0.):
            raise ValueError("time_samples_s must contain at least two increasing finite times")
        minimum = finite(minimum_cell_mass_kg, "minimum_cell_mass_kg", positive=True)
        initial = np.asarray([cell.initial_mass_kg for cell in self.cells], dtype=float)
        if np.any(initial <= minimum):
            raise ValueError("Every initial cell mass must exceed the declared positive floor")
        rtol = finite(relative_tolerance, "relative_tolerance", positive=True)
        atol = finite(absolute_tolerance_kg, "absolute_tolerance_kg", positive=True)
        max_step = np.inf if maximum_step_s is None else finite(
            maximum_step_s, "maximum_step_s", positive=True)
        if not isinstance(method, str) or method not in {"BDF", "Radau", "RK45", "DOP853"}:
            raise ValueError("method must be one of BDF, Radau, RK45, or DOP853")

        def rhs(_time_s, masses):
            if np.any(masses <= 0.) or not np.all(np.isfinite(masses)):
                raise ValueError("A trial pipe cell reached nonpositive gas inventory")
            edge_flows = self._link_flows(self._pressures(masses))
            derivative = boundary.copy()
            derivative[:-1] -= edge_flows
            derivative[1:] += edge_flows
            return derivative

        events = []
        for index in range(n_cells):
            def floor_event(_time, masses, cell_index=index):
                return masses[cell_index] - minimum
            floor_event.terminal = True
            floor_event.direction = -1
            events.append(floor_event)

        solution = solve_ivp(
            rhs, (float(times[0]), float(times[-1])), initial,
            method=method, t_eval=times, events=events,
            rtol=rtol, atol=atol, max_step=max_step,
        )
        if not solution.success:
            raise RuntimeError(f"Isothermal pipe network integration failed: {solution.message}")
        output_times = list(map(float, solution.t))
        mass_rows = [row.copy() for row in solution.y.T]
        terminal_cell = None
        if solution.status == 1:
            event_candidates = [
                (float(event_times[0]), index, solution.y_events[index][0])
                for index, event_times in enumerate(solution.t_events) if len(event_times)
            ]
            if not event_candidates:
                raise RuntimeError("Pipe network stopped without a recorded inventory-floor event")
            event_time, event_index, event_mass = min(event_candidates, key=lambda item: item[0])
            if output_times and abs(output_times[-1] - event_time) <= 1e-12 * max(abs(event_time), 1.):
                output_times[-1] = event_time
                mass_rows[-1] = event_mass.copy()
            else:
                output_times.append(event_time)
                mass_rows.append(event_mass.copy())
            terminal_cell = self.cells[event_index].cell_id

        output_times = np.asarray(output_times, dtype=float)
        masses = np.asarray(mass_rows, dtype=float)
        pressures = np.vstack([self._pressures(row) for row in masses])
        link_flows = np.vstack([self._link_flows(row) for row in pressures])
        external_net = float(np.sum(boundary))
        mass_residual = np.sum(masses, axis=1) - np.sum(initial) - external_net * (
            output_times - times[0]
        )
        self.require_current()
        token = object()
        _PENDING_TRACES.add(token)
        try:
            trace = IsothermalGasPipeNetworkTrace(
                tuple(cell.cell_id for cell in self.cells),
                tuple(link.link_id for link in self.links),
                output_times, masses, pressures, link_flows, mass_residual,
                evidence, self.friction_law_id, solution.status == 0, terminal_cell,
                tuple(cell.eos.identity if cell.eos is not None else "explicit-ideal-gas"
                      for cell in self.cells), self, tuple(map(float, boundary)), token,
            )
        finally:
            _PENDING_TRACES.discard(token)
        return trace
