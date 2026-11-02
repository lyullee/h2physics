"""Adaptive host-side V/U integration for bounded evolving mixtures.

CoolProp owns every composition-specific equilibrium flash. SciPy owns the
explicitly identified integration clock; this is not a native external-vessel
solver. The finite-interval API remains preferable when a caller already owns
accepted boundary integrals or requires a native receiving integrator.
"""

from collections.abc import Callable
from dataclasses import dataclass, field
from math import fsum

import numpy as np

from ..core import finite, immutable_array
from .finite_mixture_inventory import (
    MixtureProviderTemplate, MixtureVesselAcceptedState, _thermo_reference_signature,
)
from .mixture_inventory_flash import flash_two_phase_inventory_vu

_PENDING_ODE_TRACES: set[object] = set()


def _issue(**values):
    token = object()
    _PENDING_ODE_TRACES.add(token)
    try:
        return MixtureVesselODETrace(**values, _issuer=token)
    except Exception:
        _PENDING_ODE_TRACES.discard(token)
        raise


def _callback_binding(callback):
    from ..adapters.facility_consequence import _evaluator_binding
    return _evaluator_binding(callback)


@dataclass(frozen=True, slots=True)
class MixtureODEState:
    """One RHS evaluation with the exact composition-specific equilibrium."""

    time_s: float
    component_moles: tuple[float, ...]
    internal_energy_j: float
    provider: object = field(repr=False, compare=False)
    flash: object = field(repr=False, compare=False)


@dataclass(frozen=True, slots=True)
class MixtureBoundaryRates:
    """Caller rates at one trial state; mole rates are ordered as the template.

    Feed vectors are nonnegative mol/s and have separate integrated enthalpy
    rates in watts. Liquid/vapor outlets are total phase molar rates; their
    species and enthalpy fluxes are computed from the current flashed phase.
    Heat and work are signed rates into the vessel.
    """

    liquid_feed_mol_s: tuple[float, ...]
    vapor_feed_mol_s: tuple[float, ...]
    liquid_feed_enthalpy_w: float
    vapor_feed_enthalpy_w: float
    liquid_outlet_mol_s: float
    vapor_outlet_mol_s: float
    heat_into_vessel_w: float
    work_into_vessel_w: float
    evidence_id: str
    energy_reference_id: str

    def __post_init__(self):
        for name in ("liquid_feed_mol_s", "vapor_feed_mol_s"):
            values = tuple(finite(v, name) for v in getattr(self, name))
            if any(v < 0. for v in values):
                raise ValueError(f"{name} cannot contain negative rates")
            object.__setattr__(self, name, values)
        for vector_name, enthalpy_name in (
            ("liquid_feed_mol_s", "liquid_feed_enthalpy_w"),
            ("vapor_feed_mol_s", "vapor_feed_enthalpy_w"),
        ):
            if not any(getattr(self, vector_name)) and getattr(self, enthalpy_name) != 0.:
                raise ValueError("A zero-mole feed cannot carry a nonzero enthalpy rate")
        for name in ("liquid_feed_enthalpy_w", "vapor_feed_enthalpy_w",
                     "heat_into_vessel_w", "work_into_vessel_w"):
            object.__setattr__(self, name, finite(getattr(self, name), name))
        for name in ("liquid_outlet_mol_s", "vapor_outlet_mol_s"):
            value = finite(getattr(self, name), name)
            if value < 0.:
                raise ValueError(f"{name} cannot be negative")
            object.__setattr__(self, name, value)
        if not isinstance(self.evidence_id, str) or not self.evidence_id.strip():
            raise ValueError("Every boundary-rate evaluation needs an evidence identity")
        if not isinstance(self.energy_reference_id, str) or not self.energy_reference_id.strip():
            raise ValueError("Boundary enthalpy rates need an explicit energy reference")


@dataclass(frozen=True, slots=True)
class MixtureODEInputs:
    """Evidence-bound adaptive integration controls and flash domain."""

    template: MixtureProviderTemplate
    initial_component_moles: tuple[float, ...]
    initial_internal_energy_j: float
    vessel_volume_m3: float
    start_time_s: float
    end_time_s: float
    integration_boundaries_s: tuple[float, ...]
    pressure_bounds_pa: tuple[float, float]
    flash_quality_bounds: tuple[float, float]
    terminal_quality_bounds: tuple[float, float]
    initial_guesses: tuple[tuple[float, float], ...]
    boundary_rates: Callable[[MixtureODEState], MixtureBoundaryRates] = field(repr=False, compare=False)
    boundary_rate_evidence_id: str
    branch_evidence_id: str
    run_id: str
    minimum_component_moles: float
    maximum_step_s: float
    relative_tolerance: float = 1e-6
    component_mole_absolute_tolerance: float = 1e-9
    energy_absolute_tolerance_j: float = 1e-3
    volume_absolute_tolerance_m3: float = 1e-9
    phase_mole_balance_tolerance: float = 1e-8
    root_pressure_relative_tolerance: float = 1e-7
    root_quality_absolute_tolerance: float = 1e-8
    method: str = "BDF"
    _seal: tuple = field(default=(), init=False, repr=False, compare=False)

    def __post_init__(self):
        if type(self.template) is not MixtureProviderTemplate:
            raise TypeError("Supply MixtureProviderTemplate")
        if not callable(self.boundary_rates):
            raise TypeError("boundary_rates must be a deterministic Python callback")
        n = tuple(finite(v, "initial component moles", positive=True)
                  for v in self.initial_component_moles)
        if len(n) != len(self.template.species):
            raise ValueError("Initial component inventory must follow the template species order")
        object.__setattr__(self, "initial_component_moles", n)
        object.__setattr__(self, "initial_internal_energy_j",
                           finite(self.initial_internal_energy_j, "initial internal energy"))
        object.__setattr__(self, "vessel_volume_m3", finite(self.vessel_volume_m3,
                           "fixed vessel volume", positive=True))
        t0 = finite(self.start_time_s, "integration start time")
        tf = finite(self.end_time_s, "integration end time")
        if tf <= t0:
            raise ValueError("Integration end must follow its start")
        boundaries = tuple(finite(v, "integration boundary") for v in self.integration_boundaries_s)
        if (len(boundaries) < 2 or boundaries[0] != t0 or boundaries[-1] != tf
                or any(b <= a for a, b in zip(boundaries[:-1], boundaries[1:]))):
            raise ValueError("Integration boundaries must increase from exact start to end")
        object.__setattr__(self, "integration_boundaries_s", boundaries)
        pressure = tuple(finite(v, "pressure bound", positive=True) for v in self.pressure_bounds_pa)
        quality = tuple(finite(v, "flash quality bound") for v in self.flash_quality_bounds)
        events = tuple(finite(v, "terminal quality bound") for v in self.terminal_quality_bounds)
        if len(pressure) != 2 or pressure[0] >= pressure[1]:
            raise ValueError("Pressure bounds must increase")
        if len(quality) != 2 or not 0. <= quality[0] < quality[1] <= 1.:
            raise ValueError("Flash quality bounds must be an ordered subset of [0, 1]")
        if (len(events) != 2 or not quality[0] < events[0] < events[1] < quality[1]):
            raise ValueError("Terminal quality events must lie strictly inside the flash bounds")
        object.__setattr__(self, "pressure_bounds_pa", pressure)
        object.__setattr__(self, "flash_quality_bounds", quality)
        object.__setattr__(self, "terminal_quality_bounds", events)
        guesses = tuple(tuple(finite(v, "flash seed") for v in guess) for guess in self.initial_guesses)
        if len(guesses) < 2 or any(len(g) != 2 for g in guesses):
            raise ValueError("Supply at least two (pressure, vapor-mole-quality) branch seeds")
        if any(not pressure[0] <= g[0] <= pressure[1] or not quality[0] < g[1] < quality[1]
               for g in guesses):
            raise ValueError("Each seed must be strictly inside the admitted flash rectangle")
        object.__setattr__(self, "initial_guesses", guesses)
        for name in ("boundary_rate_evidence_id", "branch_evidence_id", "run_id"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"Declare {name}")
        for name in ("minimum_component_moles", "maximum_step_s", "relative_tolerance",
                     "component_mole_absolute_tolerance", "energy_absolute_tolerance_j",
                     "volume_absolute_tolerance_m3", "phase_mole_balance_tolerance",
                     "root_pressure_relative_tolerance", "root_quality_absolute_tolerance"):
            object.__setattr__(self, name, finite(getattr(self, name), name, positive=True))
        if any(v <= self.minimum_component_moles for v in n):
            raise ValueError("Initial stocks must exceed the localized component floor")
        if self.relative_tolerance >= 1.:
            raise ValueError("Relative tolerance must be below one")
        if self.method not in {"BDF", "Radau", "RK45", "DOP853", "LSODA"}:
            raise ValueError("Select a supported SciPy solve_ivp method explicitly")
        object.__setattr__(self, "_seal", self._payload())

    def _payload(self):
        return (id(self.template), self.initial_component_moles, self.initial_internal_energy_j,
                self.vessel_volume_m3, self.start_time_s, self.end_time_s,
                self.integration_boundaries_s, self.pressure_bounds_pa, self.flash_quality_bounds,
                self.terminal_quality_bounds, self.initial_guesses, id(self.boundary_rates),
                _callback_binding(self.boundary_rates), self.boundary_rate_evidence_id,
                self.branch_evidence_id, self.run_id, self.minimum_component_moles,
                self.maximum_step_s, self.relative_tolerance,
                self.component_mole_absolute_tolerance, self.energy_absolute_tolerance_j,
                self.volume_absolute_tolerance_m3, self.phase_mole_balance_tolerance,
                self.root_pressure_relative_tolerance, self.root_quality_absolute_tolerance,
                self.method)

    def require_current(self):
        if not self._seal or self._payload() != self._seal:
            raise ValueError("Mixture ODE inputs or callback binding changed after admission")
        return self


@dataclass(frozen=True, slots=True)
class MixtureODEDiagnostics:
    status: str
    message: str
    method: str
    function_evaluations: int
    jacobian_evaluations: int
    lu_decompositions: int
    accepted_step_count: int
    event_name: str | None
    event_time_s: float | None
    attempted_rhs_calls: int = 0
    equilibrium_flash_calls: int = 0

    def __post_init__(self):
        if self.status not in {"completed", "event", "solver_failure", "rhs_failure"}:
            raise ValueError("Unknown mixture ODE diagnostic status")
        if not isinstance(self.message, str):
            raise TypeError("Retain a solver message")
        if self.method not in {"BDF", "Radau", "RK45", "DOP853", "LSODA"}:
            raise ValueError("Retain the selected SciPy solve_ivp method")
        for name in ("function_evaluations", "jacobian_evaluations", "lu_decompositions",
                     "accepted_step_count", "attempted_rhs_calls", "equilibrium_flash_calls"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValueError(f"{name} must be a nonnegative integer")
        if (self.event_name is None) != (self.event_time_s is None):
            raise ValueError("Event identity and time must be supplied together")
        if (self.status == "event") != (self.event_name is not None):
            raise ValueError("Only an event termination may carry a terminal event identity and time")
        if self.event_name is not None and (
                not isinstance(self.event_name, str) or not self.event_name.strip()):
            raise ValueError("Retain a nonempty terminal event identity")
        if self.event_time_s is not None:
            finite(self.event_time_s, "event time")


@dataclass(frozen=True, slots=True)
class MixtureVesselODETrace:
    """Owner-issued adaptive trajectory with accepted flash states and audit."""

    inputs: MixtureODEInputs
    accepted: tuple[MixtureVesselAcceptedState, ...]
    diagnostics: MixtureODEDiagnostics
    solver_values: np.ndarray = field(repr=False, compare=False)
    _issuer: object = field(default=None, repr=False, compare=False)
    _seal: tuple = field(default=(), init=False, repr=False, compare=False)

    def __post_init__(self):
        if self._issuer not in _PENDING_ODE_TRACES:
            raise TypeError("Create adaptive mixture traces through run_mixture_vessel_ode")
        _PENDING_ODE_TRACES.remove(self._issuer)
        accepted = tuple(self.accepted)
        values = np.asarray(self.solver_values, dtype=float)
        if len(accepted) < 1 or values.ndim != 2 or values.shape[1] != len(accepted):
            raise ValueError("Retain solver accepted states aligned with the adaptive solution prefix")
        if any(type(point) is not MixtureVesselAcceptedState for point in accepted):
            raise TypeError("Adaptive accepted history must retain issued mixture V/U states")
        if not np.all(np.isfinite(values)):
            raise ValueError("Accepted solver state values must remain finite")
        values = immutable_array(values, dtype=float, name="mixture ODE solver values")
        object.__setattr__(self, "accepted", accepted)
        object.__setattr__(self, "solver_values", values)
        self._audit()
        object.__setattr__(self, "_seal", self._payload())

    def _payload(self):
        return (id(self.inputs), self.inputs._payload(), tuple(id(v) for v in self.accepted),
                tuple(v._payload() for v in self.accepted), self.solver_values.tobytes(),
                self.diagnostics)

    def _audit(self):
        self.inputs.require_current()
        times = tuple(point.time_s for point in self.accepted)
        if any(b <= a for a, b in zip(times[:-1], times[1:])):
            raise ValueError("Adaptive accepted clock must increase strictly")
        if times[0] != self.inputs.start_time_s:
            raise ValueError("Adaptive prefix must retain the exact initial state")
        if self.diagnostics.status not in {"completed", "event", "solver_failure"}:
            raise ValueError("Unknown adaptive integration status")
        if self.diagnostics.status == "completed" and times[-1] != self.inputs.end_time_s:
            raise ValueError("Completed integration must reach the declared final time")
        if self.diagnostics.status == "event" and (
                self.diagnostics.event_name is None or self.diagnostics.event_time_s != times[-1]):
            raise ValueError("Terminal event time must match the final retained accepted state")
        if self.diagnostics.accepted_step_count != len(self.accepted) - 1:
            raise ValueError("Accepted-step diagnostic differs from the retained prefix")
        valid_events = tuple(f"component-floor:{name}" for name in self.inputs.template.species)
        if self.diagnostics.status == "event" and self.diagnostics.event_name not in (
                *valid_events, "quality-lower-bound", "quality-upper-bound"):
            raise ValueError("Event identity is not one of the declared terminal events")
        if self.solver_values.shape[0] != 3 * len(self.inputs.template.species) + 7:
            raise ValueError("Solver state must retain inventory, U and all integrated ledgers")
        k = len(self.inputs.template.species)
        n0 = self.inputs.initial_component_moles
        u0 = self.inputs.initial_internal_energy_j
        first = self.accepted[0]
        if (first.cumulative_inlet_component_moles != (0.,) * k
                or first.cumulative_outlet_component_moles != (0.,) * k
                or first.cumulative_energy_into_vessel_j != 0.
                or np.any(self.solver_values[k + 1:, 0] != 0.)):
            raise ValueError("Initial adaptive transfer and energy ledgers must be exactly zero")
        if first.admission.total_component_moles != n0 or first.admission.target_internal_energy_j != u0:
            raise ValueError("Initial accepted flash differs from the declared initial inventory/U")
        if tuple(first.provider.species) != self.inputs.template.species:
            raise ValueError("Initial provider species order differs from the template")
        reference_signature = _thermo_reference_signature(first.provider)
        for col, point in enumerate(self.accepted):
            point.require_current()
            if (tuple(point.provider.species) != self.inputs.template.species
                    or _thermo_reference_signature(point.provider) != reference_signature
                    or point.admission.vessel_volume_m3 != self.inputs.vessel_volume_m3):
                raise ValueError("Accepted mixture provider/EOS basis or fixed vessel volume changed")
            y = self.solver_values[:, col]
            n = tuple(float(v) for v in y[:k])
            if abs(float(y[k]) - point.admission.target_internal_energy_j) > self.inputs.energy_absolute_tolerance_j:
                raise ValueError("Accepted flash U differs from the adaptive solver state")
            if any(v < self.inputs.minimum_component_moles - self.inputs.component_mole_absolute_tolerance
                   for v in n):
                raise ValueError("Accepted inventory crossed the declared depletion floor")
            inlet = tuple(float(v) for v in y[k + 1:k + 1 + k])
            outlet = tuple(float(v) for v in y[k + 1 + k:k + 1 + 2 * k])
            for observed, expected in zip(point.admission.total_component_moles, n, strict=True):
                if abs(observed - expected) > self.inputs.component_mole_absolute_tolerance:
                    raise ValueError("Accepted flash inventory differs from solver state")
            for observed, expected in zip(point.cumulative_inlet_component_moles, inlet, strict=True):
                if abs(observed - expected) > self.inputs.component_mole_absolute_tolerance:
                    raise ValueError("Accepted inlet ledger differs from solver integral")
            for observed, expected in zip(point.cumulative_outlet_component_moles, outlet, strict=True):
                if abs(observed - expected) > self.inputs.component_mole_absolute_tolerance:
                    raise ValueError("Accepted outlet ledger differs from solver integral")
            energy_terms = tuple(float(v) for v in y[k + 1 + 2 * k:])
            cumulative_energy = fsum(v * sign for v, sign in zip(
                energy_terms, (1., 1., -1., -1., 1., 1.), strict=True))
            if abs(point.cumulative_energy_into_vessel_j - cumulative_energy) > self.inputs.energy_absolute_tolerance_j:
                raise ValueError("Accepted energy integral differs from solver state")
            mass_balance = tuple(n[i] - n0[i] - inlet[i] + outlet[i] for i in range(k))
            if any(abs(v) > self.inputs.component_mole_absolute_tolerance for v in mass_balance):
                raise ValueError("Adaptive species inventory fails its integrated boundary ledger")
            hin_l, hin_v, hout_l, hout_v, heat, work = (float(v) for v in y[k + 1 + 2*k:])
            energy_residual = point.admission.target_internal_energy_j - u0 - hin_l - hin_v + hout_l + hout_v - heat - work
            if abs(energy_residual) > self.inputs.energy_absolute_tolerance_j:
                raise ValueError("Adaptive U history fails its integrated first-law ledger")

    def require_current(self):
        if not self._seal or self._payload() != self._seal:
            raise ValueError("Adaptive mixture trajectory changed after issuance")
        self._audit()
        return self

    def boundary_energy_history(self):
        """Return named immutable cumulative joule channels on the accepted clock.

        Outlet enthalpy channels are exports; heat/work are signed into the
        vessel. These are the solver-integrated channels, without quadrature.
        """
        from types import MappingProxyType

        from ..core import immutable_array

        self.require_current()
        offset = 3 * len(self.inputs.template.species) + 1
        names = ("liquid_feed_enthalpy_j", "vapor_feed_enthalpy_j",
                 "liquid_outlet_enthalpy_j", "vapor_outlet_enthalpy_j",
                 "heat_into_vessel_j", "work_into_vessel_j")
        channels = {name: immutable_array(self.solver_values[offset + index], name=name)
                    for index, name in enumerate(names)}
        channels["time_s"] = immutable_array(
            [point.time_s for point in self.accepted], name="accepted time")
        channels["net_energy_into_vessel_j"] = immutable_array(
            [point.cumulative_energy_into_vessel_j for point in self.accepted],
            name="net energy into vessel")
        return MappingProxyType(channels)

    def component_inventory_history(self):
        """Return immutable accepted-time by species inventories and cumulative ports.

        Species columns follow ``inputs.template.species``. Port totals combine
        liquid and vapor transfers. Mass views use the retained template molar masses.
        """
        from types import MappingProxyType

        from ..core import immutable_array

        self.require_current()
        k = len(self.inputs.template.species)
        masses = np.asarray(self.inputs.template.molar_masses_kg_mol, dtype=float)
        return MappingProxyType({
            "species": self.inputs.template.species,
            "time_s": immutable_array([point.time_s for point in self.accepted],
                                      name="accepted time"),
            "component_moles": immutable_array(self.solver_values[:k].T,
                                               name="component inventories"),
            "cumulative_inlet_component_moles": immutable_array(
                self.solver_values[k + 1:2 * k + 1].T, name="cumulative inlet moles"),
            "cumulative_outlet_component_moles": immutable_array(
                self.solver_values[2 * k + 1:3 * k + 1].T, name="cumulative outlet moles"),
            "molar_masses_kg_mol": immutable_array(masses, name="component molar masses"),
            "component_mass_kg": immutable_array(
                self.solver_values[:k].T * masses, name="component mass"),
            "cumulative_inlet_component_mass_kg": immutable_array(
                self.solver_values[k + 1:2 * k + 1].T * masses,
                name="cumulative inlet component mass"),
            "cumulative_outlet_component_mass_kg": immutable_array(
                self.solver_values[2 * k + 1:3 * k + 1].T * masses,
                name="cumulative outlet component mass"),
        })


class MixtureVesselODEError(RuntimeError):
    """An RHS/property failure with original cause, last trial and accepted prefix."""

    def __init__(self, cause, *, last_trial, accepted_prefix, diagnostics):
        super().__init__(f"Adaptive mixture vessel solve failed: {cause}")
        self.cause = cause
        self.__cause__ = cause
        self.last_trial = last_trial
        self.accepted_prefix = tuple(accepted_prefix)
        self.diagnostics = diagnostics


def run_mixture_vessel_ode(inputs: MixtureODEInputs) -> MixtureVesselODETrace:
    """Integrate continuous caller rates with SciPy and localize bounded events.

    This is deliberately a host-side adaptive solver. Each RHS creates a new
    CoolProp provider for the trial overall composition and runs the existing
    bounded multi-seed V/U equilibrium flash. The native property backend does
    not own this ODE. Quality events are terminal interior thresholds inside
    the admitted flash rectangle; component depletion is localized at an
    explicit positive inventory floor.
    """
    from scipy.integrate import solve_ivp

    if type(inputs) is not MixtureODEInputs:
        raise TypeError("Supply MixtureODEInputs")
    inputs.require_current()
    k = len(inputs.template.species)
    # State layout: N_i, U, cumulative inlet N_i, cumulative outlet N_i,
    # Hin(liquid,vapor), Hout(liquid,vapor), Q, W.
    size = 3 * k + 7
    y = np.zeros(size, dtype=float)
    y[:k] = inputs.initial_component_moles
    y[k] = inputs.initial_internal_energy_j
    flash_kw = dict(
        vessel_volume_m3=inputs.vessel_volume_m3,
        pressure_bounds_pa=inputs.pressure_bounds_pa,
        quality_bounds=inputs.flash_quality_bounds,
        initial_guesses=inputs.initial_guesses,
        volume_absolute_tolerance_m3=inputs.volume_absolute_tolerance_m3,
        energy_absolute_tolerance_j=inputs.energy_absolute_tolerance_j,
        component_mole_absolute_tolerance=inputs.component_mole_absolute_tolerance,
        phase_mole_balance_tolerance=inputs.phase_mole_balance_tolerance,
        branch_evidence_id=inputs.branch_evidence_id,
        root_pressure_relative_tolerance=inputs.root_pressure_relative_tolerance,
        root_quality_absolute_tolerance=inputs.root_quality_absolute_tolerance,
    )
    last_trial = [None]
    last_packet = [None]
    accepted = []
    solver_columns = []
    counters = {"nfev": 0, "njev": 0, "nlu": 0, "rhs_attempts": 0, "flash_calls": 0}

    def packet_at(time_s, vector):
        # Equilibrium depends on stocks/U, not clock or cumulative port ledgers.
        key = np.asarray(vector[:k + 1], dtype=float).tobytes()
        stocks = tuple(float(v) for v in vector[:k])
        if last_packet[0] is not None and last_packet[0][0] == key:
            provider, flash = last_packet[0][1:3]
            state = MixtureODEState(float(time_s), stocks, float(vector[k]), provider, flash)
            last_trial[0] = state
            return provider, flash, state
        if any(v <= 0. for v in stocks):
            raise ValueError("Solver trial exhausted a mixture component before a positive-floor event")
        provider = inputs.template.provider_for(stocks)
        counters["flash_calls"] += 1
        flash = flash_two_phase_inventory_vu(
            provider, stocks, internal_energy_j=float(vector[k]), **flash_kw)
        state = MixtureODEState(float(time_s), stocks, float(vector[k]), provider, flash)
        last_trial[0] = state
        last_packet[0] = (key, provider, flash, state)
        return provider, flash, state

    def rates_at(time_s, vector):
        provider, flash, state = packet_at(time_s, vector)
        rates = inputs.boundary_rates(state)
        if type(rates) is not MixtureBoundaryRates:
            raise TypeError("Boundary callback must return MixtureBoundaryRates")
        if len(rates.liquid_feed_mol_s) != k or len(rates.vapor_feed_mol_s) != k:
            raise ValueError("Boundary feed vectors must follow the provider species order")
        if rates.evidence_id != inputs.boundary_rate_evidence_id:
            raise ValueError("Boundary-rate evidence identity changed during integration")
        if rates.energy_reference_id != inputs.template.energy_reference_id:
            raise ValueError("Feed enthalpy reference differs from the vessel internal-energy basis")
        partition = flash.partition
        amounts = flash.phase_amounts
        liquid_comp = partition.liquid_mole_fractions
        vapor_comp = partition.vapor_mole_fractions
        liquid_mass_per_mol = fsum(a*b for a, b in zip(
            liquid_comp, inputs.template.molar_masses_kg_mol, strict=True))
        vapor_mass_per_mol = fsum(a*b for a, b in zip(
            vapor_comp, inputs.template.molar_masses_kg_mol, strict=True))
        liquid_stock = fsum(amounts.liquid_component_moles)
        vapor_stock = fsum(amounts.vapor_component_moles)
        if rates.liquid_outlet_mol_s > 0. and (liquid_stock <= 0. or partition.liquid_enthalpy_j_kg is None):
            raise ValueError("Liquid withdrawal requires an occupied liquid phase and native enthalpy")
        if rates.vapor_outlet_mol_s > 0. and (vapor_stock <= 0. or partition.vapor_enthalpy_j_kg is None):
            raise ValueError("Vapor withdrawal requires an occupied vapor phase and native enthalpy")
        liquid_out = tuple(rates.liquid_outlet_mol_s * x for x in liquid_comp)
        vapor_out = tuple(rates.vapor_outlet_mol_s * yv for yv in vapor_comp)
        liquid_hout_w = (rates.liquid_outlet_mol_s * liquid_mass_per_mol
                         * float(partition.liquid_enthalpy_j_kg)
                         if rates.liquid_outlet_mol_s else 0.)
        vapor_hout_w = (rates.vapor_outlet_mol_s * vapor_mass_per_mol
                        * float(partition.vapor_enthalpy_j_kg)
                        if rates.vapor_outlet_mol_s else 0.)
        dn = tuple(a+b-c-d for a, b, c, d in zip(
            rates.liquid_feed_mol_s, rates.vapor_feed_mol_s,
            liquid_out, vapor_out, strict=True))
        du = fsum((rates.liquid_feed_enthalpy_w, rates.vapor_feed_enthalpy_w,
                   rates.heat_into_vessel_w, rates.work_into_vessel_w,
                   -liquid_hout_w, -vapor_hout_w))
        derivatives = np.zeros(size, dtype=float)
        derivatives[:k] = dn
        derivatives[k] = du
        offset = k + 1
        derivatives[offset:offset+k] = np.asarray(rates.liquid_feed_mol_s) + np.asarray(rates.vapor_feed_mol_s)
        derivatives[offset+k:offset+2*k] = np.asarray(liquid_out) + np.asarray(vapor_out)
        derivatives[offset+2*k:offset+2*k+6] = (
            rates.liquid_feed_enthalpy_w, rates.vapor_feed_enthalpy_w,
            liquid_hout_w, vapor_hout_w, rates.heat_into_vessel_w,
            rates.work_into_vessel_w,
        )
        return derivatives

    def rhs(time_s, vector):
        counters["rhs_attempts"] += 1
        inputs.require_current()
        return rates_at(time_s, vector)

    events = []
    event_names = []
    for i, species in enumerate(inputs.template.species):
        def component_event(_t, vector, idx=i):
            return float(vector[idx] - inputs.minimum_component_moles)
        component_event.terminal = True
        component_event.direction = -1
        events.append(component_event)
        event_names.append(f"component-floor:{species}")

    low_q, high_q = inputs.terminal_quality_bounds
    def quality_value(time_s, vector):
        _, flash, _ = packet_at(time_s, vector)
        return float(flash.admission.partition.vapor_mole_fraction)
    def low_quality_event(time_s, vector):
        return quality_value(time_s, vector) - low_q
    low_quality_event.terminal = True
    low_quality_event.direction = -1
    def high_quality_event(time_s, vector):
        return quality_value(time_s, vector) - high_q
    high_quality_event.terminal = True
    high_quality_event.direction = 1
    events.extend((low_quality_event, high_quality_event))
    event_names.extend(("quality-lower-bound", "quality-upper-bound"))

    # Issue exact initial state before solver callbacks can fail.
    initial_provider = inputs.template.provider_for(y[:k])
    counters["flash_calls"] += 1
    initial_flash = flash_two_phase_inventory_vu(
        initial_provider, y[:k], internal_energy_j=y[k], **flash_kw)
    initial_quality = float(initial_flash.admission.partition.vapor_mole_fraction)
    if not low_q < initial_quality < high_q:
        raise ValueError("Initial vapor quality must lie strictly inside the terminal quality bounds")
    accepted.append(MixtureVesselAcceptedState(
        inputs.start_time_s, initial_provider, initial_flash, initial_flash.admission,
        (0.,)*k, (0.,)*k, 0.))
    solver_columns.append(y.copy())
    status, message, event_name, event_time = "completed", "", None, None
    t_current = inputs.start_time_s
    try:
        for t_end in inputs.integration_boundaries_s[1:]:
            solution = solve_ivp(
                rhs, (t_current, t_end), y, method=inputs.method,
                rtol=inputs.relative_tolerance,
                atol=np.asarray((inputs.component_mole_absolute_tolerance,)*k
                    + (inputs.energy_absolute_tolerance_j,)
                    + (inputs.component_mole_absolute_tolerance,)*(2*k)
                    + (inputs.energy_absolute_tolerance_j,)*6, dtype=float),
                max_step=min(inputs.maximum_step_s, t_end-t_current), events=events,
            )
            counters["nfev"] += int(solution.nfev)
            counters["njev"] += int(getattr(solution, "njev", 0) or 0)
            counters["nlu"] += int(getattr(solution, "nlu", 0) or 0)
            if len(solution.t) > 1:
                for col in range(1, len(solution.t)):
                    sample = np.asarray(solution.y[:, col], dtype=float)
                    t_sample = float(solution.t[col])
                    provider, flash, _ = packet_at(t_sample, sample)
                    k_offset = k + 1
                    nin = tuple(float(v) for v in sample[k_offset:k_offset+k])
                    nout = tuple(float(v) for v in sample[k_offset+k:k_offset+2*k])
                    energy_terms = sample[k_offset+2*k:k_offset+2*k+6]
                    cumulative_net = fsum(float(v) * sign for v, sign in zip(
                        energy_terms, (1., 1., -1., -1., 1., 1.), strict=True))
                    accepted.append(MixtureVesselAcceptedState(
                        t_sample, provider, flash, flash.admission, nin, nout, cumulative_net))
                    solver_columns.append(sample.copy())
            y = np.asarray(solution.y[:, -1], dtype=float).copy()
            t_current = float(solution.t[-1])
            if not solution.success:
                status, message = "solver_failure", str(solution.message)
                break
            triggered = next((idx for idx, te in enumerate(solution.t_events)
                              if len(te)), None)
            if triggered is not None:
                event_name = event_names[triggered]
                event_time = float(solution.t_events[triggered][-1])
                status, message = "event", str(solution.message)
                break
        else:
            message = "all declared integration boundaries reached"
    except Exception as exc:
        diagnostics = MixtureODEDiagnostics(
            status="rhs_failure", message=f"{type(exc).__name__}: {exc}",
            method=inputs.method, function_evaluations=counters["nfev"],
            jacobian_evaluations=counters["njev"], lu_decompositions=counters["nlu"],
            accepted_step_count=max(len(accepted)-1, 0), event_name=None, event_time_s=None,
            attempted_rhs_calls=counters["rhs_attempts"],
            equilibrium_flash_calls=counters["flash_calls"],
        )
        raise MixtureVesselODEError(
            exc, last_trial=last_trial[0], accepted_prefix=tuple(accepted),
            diagnostics=diagnostics) from exc

    diagnostics = MixtureODEDiagnostics(
        status=status, message=message, method=inputs.method,
        function_evaluations=counters["nfev"], jacobian_evaluations=counters["njev"],
        lu_decompositions=counters["nlu"], accepted_step_count=max(len(accepted)-1, 0),
        event_name=event_name, event_time_s=event_time,
        attempted_rhs_calls=counters["rhs_attempts"],
        equilibrium_flash_calls=counters["flash_calls"],
    )
    return _issue(inputs=inputs, accepted=tuple(accepted), diagnostics=diagnostics,
                  solver_values=np.column_stack(solver_columns))


__all__ = ["MixtureODEState", "MixtureBoundaryRates", "MixtureODEInputs",
           "MixtureODEDiagnostics", "MixtureVesselODETrace", "MixtureVesselODEError",
           "run_mixture_vessel_ode"]
