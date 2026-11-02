"""Finite, single-component adsorption vessel with LDF kinetics and heat storage.

This host-side level composes the existing absolute-uptake provider and gas EOS.
It does not add a new isotherm or property model. The single-component restriction
keeps gas composition fixed, which is required by the existing frozen-gas binding.
"""

from collections.abc import Callable
from dataclasses import dataclass, field

import numpy as np
from scipy.integrate import solve_ivp
from scipy.optimize import brentq

from ..adapters.finite_adsorption_vessel import FiniteAdsorptionVessel
from ..adsorption import AdsorptionState
from ..core import finite, immutable_array

_PENDING_TRACE_ISSUERS: set[object] = set()
_INPUT_PAYLOAD_FIELDS = (
    "vessel_identity", "geometry_identity", "geometry", "adsorption_identity",
    "adsorption_basis", "equilibrium_callback", "gas_binding", "gas_property_basis",
    "gas_state_callback", "initial_pressure", "initial_temperature", "initial_loadings",
    "ldf_rates", "adsorption_energies", "solid_wall_heat_capacity", "reference_temperature",
    "temperature_bounds", "pressure_bounds", "start_time", "end_time", "integration_boundaries",
    "boundary_callback_identity", "boundary_callback_binding", "rate_evidence_id",
    "energy_evidence_id", "run_id", "minimum_gas_inventory", "solver_method",
    "relative_tolerance", "absolute_tolerance",
)


def _issue_trace(**values):
    issuer = object()
    _PENDING_TRACE_ISSUERS.add(issuer)
    try:
        return AdsorptionDynamicsTrace(**values, _issuer=issuer)
    except Exception:
        _PENDING_TRACE_ISSUERS.discard(issuer)
        raise


def _callback_binding(callback):
    from ..adapters.facility_consequence import _configuration_token, _evaluator_binding

    # Accessing ``instance.method`` creates a fresh bound-method wrapper each
    # time. Bind the stable function and owner separately so repeated provider
    # lookups remain current while edits to code, closure, defaults, or owner
    # configuration still invalidate the admitted inputs.
    function = getattr(callback, "__func__", None)
    owner = getattr(callback, "__self__", None)
    if function is not None and owner is not None:
        return ("bound-method", _evaluator_binding(function),
                _configuration_token(owner))
    return _evaluator_binding(callback)


@dataclass(frozen=True, slots=True)
class AdsorptionDynamicState:
    time_s: float
    pressure_pa: float
    temperature_k: float
    free_gas_mol: float
    site_loadings_mol_kg: tuple[float, ...]
    equilibrium_loadings_mol_kg: tuple[float, ...]


@dataclass(frozen=True, slots=True)
class AdsorptionBoundaryRates:
    """Signed energy transfer and nonnegative feed/outflow rates at one state."""

    feed_mol_s: float
    feed_enthalpy_j_mol: float
    outlet_mol_s: float
    heat_into_vessel_w: float
    evidence_id: str
    energy_reference_id: str

    def __post_init__(self):
        for name in ("feed_mol_s", "outlet_mol_s"):
            value = finite(getattr(self, name), name)
            if value < 0.:
                raise ValueError(f"{name} cannot be negative")
            object.__setattr__(self, name, value)
        for name in ("feed_enthalpy_j_mol", "heat_into_vessel_w"):
            object.__setattr__(self, name, finite(getattr(self, name), name))
        if self.feed_mol_s == 0. and self.feed_enthalpy_j_mol != 0.:
            raise ValueError("A zero feed cannot transport a nonzero feed enthalpy")
        for name in ("evidence_id", "energy_reference_id"):
            if not isinstance(getattr(self, name), str) or not getattr(self, name).strip():
                raise ValueError(f"Declare {name}")


@dataclass(frozen=True, slots=True)
class AdsorptionDynamicsInputs:
    vessel: FiniteAdsorptionVessel
    initial_pressure_pa: float
    initial_temperature_k: float
    initial_site_loadings_mol_kg: tuple[float, ...]
    ldf_rate_constant_s: tuple[float, ...]
    adsorption_energy_j_mol: tuple[float, ...]
    solid_wall_heat_capacity_j_k: float
    reference_temperature_k: float
    temperature_bounds_k: tuple[float, float]
    pressure_bounds_pa: tuple[float, float]
    start_time_s: float
    end_time_s: float
    boundaries_s: tuple[float, ...]
    boundary_rates: Callable[[AdsorptionDynamicState], AdsorptionBoundaryRates] = field(
        repr=False, compare=False
    )
    rate_evidence_id: str = ""
    energy_evidence_id: str = ""
    run_id: str = ""
    minimum_gas_inventory_mol: float = 1e-12
    method: str = "BDF"
    relative_tolerance: float = 1e-7
    absolute_tolerance: float = 1e-10
    _seal: tuple = field(default=(), init=False, repr=False, compare=False)

    def __post_init__(self):
        if type(self.vessel) is not FiniteAdsorptionVessel:
            raise TypeError("Supply the existing FiniteAdsorptionVessel owner")
        if len(self.vessel.adsorption_basis.species) != 1:
            raise ValueError("Dynamic adsorption currently requires one frozen gas species")
        pressure = finite(self.initial_pressure_pa, "initial pressure", positive=True)
        temperature = finite(self.initial_temperature_k, "initial temperature", positive=True)
        object.__setattr__(self, "initial_pressure_pa", pressure)
        object.__setattr__(self, "initial_temperature_k", temperature)
        loading = tuple(finite(v, "initial site loading") for v in self.initial_site_loadings_mol_kg)
        if not loading or any(v < 0. for v in loading):
            raise ValueError("Initial absolute site loadings must be a nonempty nonnegative vector")
        rates = tuple(finite(v, "LDF rate constant", positive=True) for v in self.ldf_rate_constant_s)
        energy = tuple(finite(v, "adsorption internal energy") for v in self.adsorption_energy_j_mol)
        if len(rates) != len(loading) or len(energy) != len(loading):
            raise ValueError("Initial loading, LDF coefficient and adsorption-energy site axes must match")
        object.__setattr__(self, "initial_site_loadings_mol_kg", loading)
        object.__setattr__(self, "ldf_rate_constant_s", rates)
        object.__setattr__(self, "adsorption_energy_j_mol", energy)
        object.__setattr__(self, "solid_wall_heat_capacity_j_k",
                           finite(self.solid_wall_heat_capacity_j_k, "solid/wall heat capacity", positive=True))
        object.__setattr__(self, "reference_temperature_k",
                           finite(self.reference_temperature_k, "energy reference temperature", positive=True))
        t_bounds = tuple(finite(v, "temperature bound", positive=True) for v in self.temperature_bounds_k)
        p_bounds = tuple(finite(v, "pressure bound", positive=True) for v in self.pressure_bounds_pa)
        if len(t_bounds) != 2 or t_bounds[0] >= t_bounds[1] or not t_bounds[0] <= temperature <= t_bounds[1]:
            raise ValueError("Temperature bounds must increase and contain the initial temperature")
        if len(p_bounds) != 2 or p_bounds[0] >= p_bounds[1] or not p_bounds[0] <= pressure <= p_bounds[1]:
            raise ValueError("Pressure bounds must increase and contain the initial pressure")
        object.__setattr__(self, "temperature_bounds_k", t_bounds)
        object.__setattr__(self, "pressure_bounds_pa", p_bounds)
        t0, tf = finite(self.start_time_s, "start time"), finite(self.end_time_s, "end time")
        if tf <= t0:
            raise ValueError("End time must follow start time")
        boundaries = tuple(finite(v, "integration boundary") for v in self.boundaries_s)
        if (len(boundaries) < 2 or boundaries[0] != t0 or boundaries[-1] != tf
                or any(b <= a for a, b in zip(boundaries[:-1], boundaries[1:]))):
            raise ValueError("Boundaries must strictly span the exact start and end times")
        object.__setattr__(self, "boundaries_s", boundaries)
        if not callable(self.boundary_rates):
            raise TypeError("boundary_rates must be a deterministic callback")
        for name in ("rate_evidence_id", "energy_evidence_id", "run_id"):
            if not isinstance(getattr(self, name), str) or not getattr(self, name).strip():
                raise ValueError(f"Declare {name}")
        object.__setattr__(self, "minimum_gas_inventory_mol",
                           finite(self.minimum_gas_inventory_mol, "minimum gas inventory", positive=True))
        if self.method not in {"BDF", "Radau", "RK45", "DOP853", "LSODA"}:
            raise ValueError("Select a supported solve_ivp integration method")
        rtol = finite(self.relative_tolerance, "relative tolerance", positive=True)
        atol = finite(self.absolute_tolerance, "absolute tolerance", positive=True)
        if rtol >= 1.:
            raise ValueError("Relative tolerance must be below one")
        object.__setattr__(self, "relative_tolerance", rtol)
        object.__setattr__(self, "absolute_tolerance", atol)
        object.__setattr__(self, "_seal", self._payload())

    def _payload(self):
        vessel = self.vessel
        return (
            id(vessel), id(vessel.geometry), vessel.geometry,
            id(vessel.adsorption), vessel.adsorption_basis,
            _callback_binding(vessel.adsorption.equilibrium),
            vessel.gas._binding_payload(), vessel.gas.property_basis,
            _callback_binding(vessel.gas.provider.state_pt),
            self.initial_pressure_pa, self.initial_temperature_k,
            self.initial_site_loadings_mol_kg, self.ldf_rate_constant_s,
            self.adsorption_energy_j_mol, self.solid_wall_heat_capacity_j_k,
            self.reference_temperature_k, self.temperature_bounds_k,
            self.pressure_bounds_pa, self.start_time_s, self.end_time_s,
            self.boundaries_s, id(self.boundary_rates), _callback_binding(self.boundary_rates),
            self.rate_evidence_id, self.energy_evidence_id, self.run_id,
            self.minimum_gas_inventory_mol, self.method,
            self.relative_tolerance, self.absolute_tolerance,
        )

    def require_current(self):
        self.vessel.gas.require_current()
        if self.vessel.adsorption.basis != self.vessel.adsorption_basis:
            raise ValueError("Adsorption provider basis changed after input admission")
        current = self._payload()
        if not self._seal:
            raise ValueError("Adsorption dynamic inputs have no admission seal")
        changed = tuple(
            name for name, actual, admitted in zip(
                _INPUT_PAYLOAD_FIELDS, current, self._seal, strict=True
            ) if actual != admitted
        )
        if changed:
            fields = ", ".join(changed)
            raise ValueError(
                "Adsorption dynamic inputs or callback bindings changed after admission; "
                f"changed fields: {fields}"
            )
        return self


@dataclass(frozen=True, slots=True)
class AdsorptionDynamicsTrace:
    inputs: AdsorptionDynamicsInputs
    time_s: np.ndarray
    pressure_pa: np.ndarray
    temperature_k: np.ndarray
    free_gas_mol: np.ndarray
    site_loadings_mol_kg: np.ndarray
    total_component_mol: np.ndarray
    cumulative_feed_mol: np.ndarray
    cumulative_outlet_mol: np.ndarray
    component_residual_mol: np.ndarray
    stored_energy_j: np.ndarray
    feed_enthalpy_j: np.ndarray
    outlet_enthalpy_j: np.ndarray
    heat_energy_j: np.ndarray
    energy_residual_j: np.ndarray
    status: str
    message: str
    accepted_step_count: int
    _issuer: object = field(default=None, repr=False, compare=False)
    _seal: tuple = field(default=(), init=False, repr=False, compare=False)

    def __post_init__(self):
        if self._issuer not in _PENDING_TRACE_ISSUERS:
            raise TypeError("Create adsorption traces through integrate_adsorption_dynamics")
        _PENDING_TRACE_ISSUERS.remove(self._issuer)
        self.inputs.require_current()
        arrays = {}
        for name in ("time_s", "pressure_pa", "temperature_k", "free_gas_mol",
                     "total_component_mol", "cumulative_feed_mol", "cumulative_outlet_mol",
                     "component_residual_mol",
                     "stored_energy_j", "feed_enthalpy_j", "outlet_enthalpy_j",
                     "heat_energy_j", "energy_residual_j"):
            value = immutable_array(getattr(self, name), dtype=float, name=name)
            if value.ndim != 1 or value.size < 1 or not np.all(np.isfinite(value)):
                raise ValueError(f"{name} must be a finite retained solver history")
            arrays[name] = value
        loading = immutable_array(self.site_loadings_mol_kg, dtype=float, name="site loadings")
        if loading.shape != (arrays["time_s"].size, len(self.inputs.initial_site_loadings_mol_kg)):
            raise ValueError("Retained site-loading history has inconsistent axes")
        if any(value.size != arrays["time_s"].size for value in arrays.values()):
            raise ValueError("Retained histories must share one accepted solver clock")
        if np.any(np.diff(arrays["time_s"]) <= 0.) or arrays["time_s"][0] != self.inputs.start_time_s:
            raise ValueError("Retained accepted times must increase from the exact initial time")
        if self.status not in {"completed", "solver_failure"}:
            raise ValueError("Unknown integration status")
        if self.status == "completed" and arrays["time_s"][-1] != self.inputs.end_time_s:
            raise ValueError("Completed integration did not reach the requested end time")
        if self.accepted_step_count != arrays["time_s"].size - 1:
            raise ValueError("Accepted step count differs from the retained trajectory")
        calculated_total = arrays["free_gas_mol"] + (
            self.inputs.vessel.geometry.adsorbent_mass_kg * loading.sum(axis=1)
        )
        if not np.allclose(arrays["total_component_mol"], calculated_total,
                           rtol=1e-12, atol=1e-11):
            raise ValueError("Total component inventory does not equal free plus adsorbed moles")
        feed = arrays["cumulative_feed_mol"]
        outlet = arrays["cumulative_outlet_mol"]
        if (np.any(feed < 0.) or np.any(outlet < 0.)
                or np.any(np.diff(feed) < -1e-12) or np.any(np.diff(outlet) < -1e-12)
                or abs(feed[0]) > 1e-12 or abs(outlet[0]) > 1e-12):
            raise ValueError("Cumulative feed/outlet mole ledgers must start at zero and be nondecreasing")
        calculated_residual = ((arrays["total_component_mol"] - arrays["total_component_mol"][0])
                               - ((feed - feed[0]) - (outlet - outlet[0])))
        if not np.allclose(arrays["component_residual_mol"], calculated_residual,
                           rtol=1e-12, atol=1e-11):
            raise ValueError("Component inventory residual does not reconstruct from its ledgers")
        object.__setattr__(self, "site_loadings_mol_kg", loading)
        for name, value in arrays.items():
            object.__setattr__(self, name, value)
        object.__setattr__(self, "_seal", self._payload())

    def _payload(self):
        return (
            id(self.inputs), self.inputs._payload(),
            self.time_s.tobytes(), self.pressure_pa.tobytes(), self.temperature_k.tobytes(),
            self.free_gas_mol.tobytes(), self.site_loadings_mol_kg.tobytes(),
            self.total_component_mol.tobytes(), self.cumulative_feed_mol.tobytes(),
            self.cumulative_outlet_mol.tobytes(), self.component_residual_mol.tobytes(),
            self.stored_energy_j.tobytes(), self.feed_enthalpy_j.tobytes(),
            self.outlet_enthalpy_j.tobytes(), self.heat_energy_j.tobytes(),
            self.energy_residual_j.tobytes(), self.status, self.message,
            self.accepted_step_count,
        )

    def require_current(self):
        self.inputs.require_current()
        if not self._seal or self._payload() != self._seal:
            raise ValueError("Adsorption trace arrays or input/callback bindings changed after issuance")
        return self


def integrate_adsorption_dynamics(inputs: AdsorptionDynamicsInputs) -> AdsorptionDynamicsTrace:
    """Integrate a single-species finite vessel with site-resolved LDF uptake.

    The gas EOS in the existing vessel binding closes pressure and gas internal
    energy. A single lumped solid/wall heat capacity and caller-declared signed
    adsorption internal energies close the stored-energy state. Boundary feed,
    withdrawal and heat are supplied on each trial state. This is not a spatial
    bed, breakthrough front, thermal wave, or calibrated adsorption law.
    """
    if type(inputs) is not AdsorptionDynamicsInputs:
        raise TypeError("Supply AdsorptionDynamicsInputs")
    inputs.require_current()
    vessel = inputs.vessel
    vessel.gas.require_current()
    adsorbent_kg = vessel.geometry.adsorbent_mass_kg
    void_m3 = vessel.geometry.void_volume_m3
    molar_mass = vessel.gas.mean_molar_mass_kg_mol
    sites = len(inputs.initial_site_loadings_mol_kg)

    def gas_state(n_mol, temperature):
        if n_mol <= inputs.minimum_gas_inventory_mol:
            raise ValueError("Gas inventory reached its declared positive floor")
        mass = n_mol * molar_mass
        density = mass / void_m3
        def residual(pressure):
            state = vessel.gas.state_pt(pressure, temperature)
            return state.density_kg_m3 - density
        pressure = brentq(residual, *inputs.pressure_bounds_pa, xtol=1e-5, rtol=1e-10)
        return vessel.gas.state_pt(pressure, temperature)

    def system_energy(n_mol, q, temperature):
        gas = gas_state(n_mol, temperature)
        gas_u = n_mol * molar_mass * gas.internal_energy_j_kg
        solid_u = inputs.solid_wall_heat_capacity_j_k * (temperature - inputs.reference_temperature_k)
        adsorption_u = adsorbent_kg * float(np.dot(q, inputs.adsorption_energy_j_mol))
        return gas_u + solid_u + adsorption_u, gas

    def temperature_for_energy(n_mol, q, target_u):
        def residual(temperature):
            return system_energy(n_mol, q, temperature)[0] - target_u
        temperature = brentq(residual, *inputs.temperature_bounds_k, xtol=1e-8, rtol=1e-10)
        return temperature

    n0 = (vessel.gas.state_pt(inputs.initial_pressure_pa, inputs.initial_temperature_k).density_kg_m3
          * void_m3 / molar_mass)
    q0 = np.asarray(inputs.initial_site_loadings_mol_kg, dtype=float)
    u0, _ = system_energy(n0, q0, inputs.initial_temperature_k)
    # State coordinates retain free moles, site loading, stored U, cumulative
    # feed/outlet moles, and separate boundary-energy integrals.
    y = np.concatenate(([n0], q0, [u0, 0., 0., 0., 0., 0.]))
    times, states, status, message = [inputs.start_time_s], [y.copy()], "completed", "Integration reached the end time"

    def rhs(time, values):
        inputs.require_current()
        n = float(values[0])
        q = np.maximum(values[1:1 + sites], 0.)
        u = float(values[1 + sites])
        temperature = temperature_for_energy(n, q, u)
        gas = gas_state(n, temperature)
        partial = np.asarray([gas.pressure_pa], dtype=float)
        equilibrium = vessel.adsorption.equilibrium(partial, temperature)
        if type(equilibrium) is not AdsorptionState:
            raise TypeError("Adsorption provider must return AdsorptionState")
        vessel.adsorption_basis.require_compatible(equilibrium.basis)
        if (not np.allclose(equilibrium.partial_pressures_pa, partial, rtol=1e-12, atol=1e-6)
                or not np.isclose(equilibrium.temperature_k, temperature, rtol=1e-12, atol=1e-9)):
            raise ValueError("Adsorption provider changed the requested dynamic state")
        eq = np.asarray(equilibrium.site_loadings_mol_kg[0], dtype=float)
        if eq.shape != (sites,) or np.any(eq < 0.):
            raise ValueError("Equilibrium site layout differs from the admitted LDF model")
        dq = np.asarray(inputs.ldf_rate_constant_s) * (eq - q)
        dq[(dq > 0.) & (n <= inputs.minimum_gas_inventory_mol)] = 0.
        dq[(dq < 0.) & (q <= 0.)] = 0.
        public = AdsorptionDynamicState(float(time), gas.pressure_pa, temperature, n,
                                        tuple(float(x) for x in q), tuple(float(x) for x in eq))
        boundary = inputs.boundary_rates(public)
        if type(boundary) is not AdsorptionBoundaryRates:
            raise TypeError("boundary_rates must return AdsorptionBoundaryRates")
        if boundary.energy_reference_id != vessel.gas.property_basis.reference_id:
            raise ValueError("Boundary enthalpy reference differs from the gas EOS reference")
        transfer_mol_s = adsorbent_kg * float(np.sum(dq))
        dn = boundary.feed_mol_s - boundary.outlet_mol_s - transfer_mol_s
        outlet_enthalpy_j_mol = gas.enthalpy_j_kg * molar_mass
        du = (boundary.feed_mol_s * boundary.feed_enthalpy_j_mol
              - boundary.outlet_mol_s * outlet_enthalpy_j_mol + boundary.heat_into_vessel_w)
        return np.concatenate(([dn], dq, [du,
            boundary.feed_mol_s,
            boundary.outlet_mol_s,
            boundary.feed_mol_s * boundary.feed_enthalpy_j_mol,
            boundary.outlet_mol_s * outlet_enthalpy_j_mol,
            boundary.heat_into_vessel_w]))

    for left, right in zip(inputs.boundaries_s[:-1], inputs.boundaries_s[1:]):
        try:
            result = solve_ivp(rhs, (left, right), y, method=inputs.method,
                               rtol=inputs.relative_tolerance, atol=inputs.absolute_tolerance,
                               max_step=right-left)
        except Exception as exc:
            status, message = "solver_failure", f"RHS/property failure: {type(exc).__name__}: {exc}"
            break
        if result.t.size > 1:
            times.extend(float(value) for value in result.t[1:])
            states.extend(result.y[:, index].copy() for index in range(1, result.t.size))
        y = result.y[:, -1].copy()
        if not result.success:
            status, message = "solver_failure", str(result.message)
            break
    matrix = np.asarray(states, dtype=float)
    pressure_history, temperature_history = [], []
    for row in matrix:
        try:
            temp = temperature_for_energy(float(row[0]), row[1:1+sites], float(row[1+sites]))
            pressure_history.append(gas_state(float(row[0]), temp).pressure_pa)
            temperature_history.append(temp)
        except Exception:
            status, message = "solver_failure", "Retained prefix ended outside the admitted EOS/temperature domain"
            matrix = matrix[:len(pressure_history)]
            times = times[:len(pressure_history)]
            break
    if not len(matrix):
        raise RuntimeError("No admissible initial state could be retained")
    stored = np.array([system_energy(float(row[0]), row[1:1+sites], float(temperature_history[i]))[0]
                       for i, row in enumerate(matrix)])
    total_moles = matrix[:, 0] + adsorbent_kg * matrix[:, 1:1+sites].sum(axis=1)
    feed_moles = matrix[:, 2+sites]
    outlet_moles = matrix[:, 3+sites]
    component_residual = ((total_moles - total_moles[0])
                          - ((feed_moles - feed_moles[0]) - (outlet_moles - outlet_moles[0])))
    energy_residual = (stored - stored[0]) - (
        matrix[:, 4+sites] - matrix[0, 4+sites]
        - (matrix[:, 5+sites] - matrix[0, 5+sites])
        + (matrix[:, 6+sites] - matrix[0, 6+sites])
    )
    return _issue_trace(
        inputs=inputs, time_s=np.asarray(times), pressure_pa=np.asarray(pressure_history),
        temperature_k=np.asarray(temperature_history),
        free_gas_mol=matrix[:, 0], site_loadings_mol_kg=matrix[:, 1:1+sites],
        total_component_mol=total_moles, cumulative_feed_mol=feed_moles,
        cumulative_outlet_mol=outlet_moles, component_residual_mol=component_residual,
        stored_energy_j=stored, feed_enthalpy_j=matrix[:, 4+sites],
        outlet_enthalpy_j=matrix[:, 5+sites], heat_energy_j=matrix[:, 6+sites],
        energy_residual_j=energy_residual, status=status, message=message,
        accepted_step_count=len(times)-1,
    )
