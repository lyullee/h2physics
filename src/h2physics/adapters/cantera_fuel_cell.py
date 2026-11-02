"""Synchronized separated-channel fuel-cell coupling on one Cantera ReactorNet.

The reactor RHS extension reads all three channel phases after ReactorNet has
restored every reactor from the same trial vector. The stack temperature is an
additional scalar state on the H2 reactor's extended vector; no dummy gas phase
is created for the stack.
"""

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from math import fsum, isclose
from types import MappingProxyType

import numpy as np

from ..core import finite
from ..electrochemistry import HydrogenStack, ReactionEnergy
from .fuel_cell_activity_receipt import FuelCellFugacityActivityProvider
from .fuel_cell_current_limit import FuelCellReactantCurrentLimit
from .fuel_cell_trial import (
    FuelCellSynchronizedTrial,
    FuelCellTrialExchange,
    FuelCellTrialGasState,
    evaluate_fuel_cell_trial_exchange,
)

_ROLES = ("hydrogen", "oxygen", "water_vapor")
_PENDING_NATIVE_FUEL_CELL_TRACES = set()


def _issue_trace(**values):
    token = object()
    _PENDING_NATIVE_FUEL_CELL_TRACES.add(token)
    try:
        return CanteraFuelCellTrace(**values, _issuer=token)
    except Exception:
        _PENDING_NATIVE_FUEL_CELL_TRACES.discard(token)
        raise


def _callable_binding(callback):
    from .facility_consequence import _evaluator_binding
    return _evaluator_binding(callback)


@dataclass(frozen=True, slots=True)
class CanteraFuelCellChannel:
    """One independently owned Cantera ideal-gas phase and rigid CV."""

    role: str
    phase: object = field(repr=False, compare=False)
    species_id: str
    volume_m3: float
    activity_reference_pressure_pa: float
    activity_reference_id: str
    energy_reference_id: str
    evidence_id: str

    def __post_init__(self):
        if self.role not in _ROLES:
            raise ValueError("Choose hydrogen, oxygen or water_vapor as channel role")
        for name in ("species_id", "activity_reference_id", "energy_reference_id", "evidence_id"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"Declare {name} for each native fuel-cell channel")
        if not all(hasattr(self.phase, name) for name in (
                "species_names", "species_index", "molecular_weights", "P", "T", "X")):
            raise TypeError("Supply an independently owned native Cantera Solution phase")
        finite(self.volume_m3, "channel fixed volume", positive=True)
        finite(self.activity_reference_pressure_pa, "activity reference pressure", positive=True)


@dataclass(frozen=True, slots=True)
class StackThermalParameters:
    """Explicit lumped stack sensible storage and coolant boundary."""

    heat_capacity_j_k: float
    energy_reference_temperature_k: float
    initial_temperature_k: float
    coolant_temperature_k: float
    conductance_w_k: float
    energy_reference_id: str
    boundary_evidence_id: str

    def __post_init__(self):
        finite(self.heat_capacity_j_k, "stack lumped heat capacity", positive=True)
        for name in ("energy_reference_temperature_k", "initial_temperature_k", "coolant_temperature_k"):
            finite(getattr(self, name), name, positive=True)
        conductance = finite(self.conductance_w_k, "stack coolant conductance")
        if conductance < 0.:
            raise ValueError("Stack coolant conductance cannot be negative")
        for name in ("energy_reference_id", "boundary_evidence_id"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError("Declare the stack energy basis and coolant-boundary evidence")


@dataclass(frozen=True, slots=True)
class FuelCellThermalPartition:
    """Caller-assigned heat rates into each gas channel and the stack.

    The four signed values must sum to electrical power into the stack minus
    the native channel species-enthalpy transfer rate. No physical split is
    inferred by this adapter.
    """

    hydrogen_w: float
    oxygen_w: float
    water_vapor_w: float
    stack_w: float
    evidence_id: str

    def __post_init__(self):
        for name in ("hydrogen_w", "oxygen_w", "water_vapor_w", "stack_w"):
            finite(getattr(self, name), "assigned " + name)
        if not isinstance(self.evidence_id, str) or not self.evidence_id.strip():
            raise ValueError("Declare evidence for the caller-owned channel/stack heat partition")

    @property
    def total_into_device_w(self):
        return fsum((self.hydrogen_w, self.oxygen_w, self.water_vapor_w, self.stack_w))


@dataclass(frozen=True, slots=True)
class NativeFuelCellTrialView:
    """Live native channel coordinates passed to caller-owned control/heat callbacks."""

    time_s: float
    clock_id: str
    stack_temperature_k: float
    channels: Mapping[str, FuelCellTrialGasState]

    def __post_init__(self):
        finite(self.time_s, "native fuel-cell trial time")
        finite(self.stack_temperature_k, "native stack trial temperature", positive=True)
        channels = dict(self.channels)
        if set(channels) != set(_ROLES):
            raise ValueError("Retain synchronized native H2/O2/H2O trial states")
        for role, state in channels.items():
            state.require_current()
            if state.role != role or state.time_s != self.time_s or state.clock_id != self.clock_id:
                raise ValueError("Native trial channels must share one exact absolute time and clock")
        object.__setattr__(self, "channels", MappingProxyType(channels))


@dataclass(frozen=True, slots=True)
class NativeFuelCellChannelSnapshot:
    role: str
    time_s: float
    temperature_k: float
    pressure_pa: float
    volume_m3: float
    species: tuple[str, ...]
    species_moles_mol: tuple[float, ...]
    internal_energy_j: float
    species_source_moles_mol: float
    species_enthalpy_transfer_j: float
    assigned_heat_j: float


@dataclass(frozen=True, slots=True)
class CanteraFuelCellSnapshot:
    time_s: float
    channels: Mapping[str, NativeFuelCellChannelSnapshot]
    stack_temperature_k: float
    stack_energy_j: float
    stack_electrical_energy_into_j: float
    stack_coolant_energy_into_j: float
    stack_assigned_heat_into_j: float
    trial_view: NativeFuelCellTrialView
    exchange: FuelCellTrialExchange
    thermal_partition: FuelCellThermalPartition
    native_species_enthalpy_transfer_w: float

    def __post_init__(self):
        channels = dict(self.channels)
        if set(channels) != set(_ROLES):
            raise ValueError("Accepted snapshot requires all three native compartment states")
        for role, channel in channels.items():
            if channel.role != role or channel.time_s != self.time_s:
                raise ValueError("Accepted native compartments must share exact accepted time")
        self.exchange.require_current()
        object.__setattr__(self, "channels", MappingProxyType(channels))


@dataclass(frozen=True, slots=True)
class NativeCanteraFuelCellObjects:
    reactors: tuple[object, ...]
    network: object
    connection: object = field(repr=False, compare=False)


@dataclass(frozen=True, slots=True)
class CanteraFuelCellTrace:
    channels: Mapping[str, CanteraFuelCellChannel]
    stack: HydrogenStack = field(repr=False, compare=False)
    standard_reaction_energy: ReactionEnergy
    thermal: StackThermalParameters
    clock_id: str
    run_evidence_id: str
    settings: object
    accepted: tuple[CanteraFuelCellSnapshot, ...]
    native: NativeCanteraFuelCellObjects = field(repr=False, compare=False)
    maximum_component_mole_residual_mol: float
    maximum_channel_energy_residual_j: float
    stack_energy_residual_j: float
    combined_energy_residual_j: float
    _issuer: object = field(default=None, repr=False, compare=False)
    _seal: tuple = field(default=(), init=False, repr=False, compare=False)

    def __post_init__(self):
        if self._issuer not in _PENDING_NATIVE_FUEL_CELL_TRACES:
            raise TypeError("Native fuel-cell traces are issued only after the simultaneous run audit")
        _PENDING_NATIVE_FUEL_CELL_TRACES.remove(self._issuer)
        if len(self.accepted) < 2 or any(type(point) is not CanteraFuelCellSnapshot for point in self.accepted):
            raise ValueError("Retain initial and accepted native fuel-cell snapshots")
        object.__setattr__(self, "channels", MappingProxyType(dict(self.channels)))
        for name in ("maximum_component_mole_residual_mol", "maximum_channel_energy_residual_j",
                     "stack_energy_residual_j", "combined_energy_residual_j"):
            finite(getattr(self, name), name)
        object.__setattr__(self, "_seal", self._payload())

    def _payload(self):
        return (tuple((role, id(value.phase), value.species_id, value.volume_m3,
                       value.activity_reference_pressure_pa, value.activity_reference_id,
                       value.energy_reference_id, value.evidence_id)
                      for role, value in self.channels.items()),
                id(self.stack), self.standard_reaction_energy, self.thermal, self.clock_id,
                self.run_evidence_id, id(self.native.network), tuple(self.accepted),
                self.maximum_component_mole_residual_mol,
                self.maximum_channel_energy_residual_j, self.stack_energy_residual_j,
                self.combined_energy_residual_j)

    def require_current(self):
        if not self._seal or self._payload() != self._seal:
            raise ValueError("Native fuel-cell trace summary changed after issuance")
        self.native.connection.require_current()
        for point in self.accepted:
            point.trial_view.__post_init__()
            point.exchange.require_current()
        if self.native.network.time != self.accepted[-1].time_s:
            raise ValueError("Native ReactorNet no longer remains at the trace's accepted endpoint")
        return self


@dataclass(frozen=True, slots=True)
class CanteraFuelCellSettings:
    maximum_time_step_s: float = 0.1
    relative_tolerance: float = 1e-8
    absolute_tolerance: float = 1e-14
    maximum_steps: int = 100000
    minimum_species_inventory_mol: float = 1e-12
    energy_ledger_scale_j: float = 1.0
    energy_absolute_tolerance_j: float = 1e-5
    energy_relative_tolerance: float = 1e-8
    component_mole_absolute_tolerance_mol: float = 1e-10

    def __post_init__(self):
        for name in ("maximum_time_step_s", "relative_tolerance", "absolute_tolerance",
                     "minimum_species_inventory_mol", "energy_ledger_scale_j",
                     "energy_absolute_tolerance_j", "component_mole_absolute_tolerance_mol"):
            finite(getattr(self, name), name, positive=True)
        finite(self.energy_relative_tolerance, "energy relative tolerance", positive=True)
        if isinstance(self.maximum_steps, bool) or type(self.maximum_steps) is not int or self.maximum_steps < 1:
            raise ValueError("Declare a positive native maximum step count")


class CanteraFuelCellIntegrationError(RuntimeError):
    """Original failed RHS/native cause with the accepted prefix and last trial."""

    def __init__(self, cause, *, native, accepted, last_native_trial, trace=None):
        self.cause = cause
        self.native = native
        self.accepted_prefix = tuple(accepted)
        self.last_native_trial = last_native_trial
        self.trace = trace
        super().__init__("Synchronized Cantera fuel-cell native integration failed")


class _Connection:
    def __init__(self, channels, stack, standard, thermal, clock, run_id,
                 current_density, thermal_partition, fugacity_provider,
                 settings, energy_reference_id):
        self.channels, self.stack, self.standard, self.thermal = channels, stack, standard, thermal
        self.clock, self.run_id = clock, run_id
        self.current_density, self.thermal_partition = current_density, thermal_partition
        self.fugacity_provider, self.settings = fugacity_provider, settings
        self.energy_reference_id = energy_reference_id
        self.reactors = ()
        self.stack_temperature_k = thermal.initial_temperature_k
        self.first_error = None
        self.last_native_trial = None
        self.cache_key = None
        self.cache_value = None
        self.evaluated_clock_bounds_s = [float("inf"), -float("inf")]
        self.phase_fingerprints = ()
        self.callback_bindings = self._bindings()
        self.stack_signature = self._stack_signature()
        self.fugacity_binding = self._fugacity_signature()

    def _bindings(self):
        return (_callable_binding(self.current_density),
                _callable_binding(self.thermal_partition))

    def _stack_signature(self):
        from .result_provenance import recorded_content_sha256
        return recorded_content_sha256((id(self.stack), self.stack.geometry,
            self.stack.thermochemistry, self.stack.losses, self.standard, self.thermal))

    def _fugacity_signature(self):
        provider = self.fugacity_provider
        if provider is None:
            return None
        provider.require_current()
        return (id(provider), provider._current_signature())

    def require_current(self):
        current_bindings = self._bindings()
        if current_bindings[0] != self.callback_bindings[0]:
            raise ValueError("Fuel-cell current-density callback changed during native run")
        if current_bindings[1] != self.callback_bindings[1]:
            raise ValueError("Fuel-cell thermal-partition callback changed during native run")
        if self._stack_signature() != self.stack_signature:
            raise ValueError("HydrogenStack or reaction-energy boundary changed during native run")
        if self._fugacity_signature() != self.fugacity_binding:
            raise ValueError("Fuel-cell fugacity provider changed during native run")
        if self.fugacity_provider is not None:
            self.fugacity_provider.require_current()
        if self.phase_fingerprints:
            from .cantera_volume import _phase_fingerprint
            for channel, expected in zip(self.channels.values(), self.phase_fingerprints, strict=True):
                if _phase_fingerprint(channel.phase, include_reactions=True) != expected:
                    raise ValueError("Cantera channel mechanism or thermodynamic definition changed")
        return self

    def remember_error(self, error, time_s):
        if self.first_error is not None:
            return
        self.first_error = error
        channels = []
        for role, reactor in zip(_ROLES, self.reactors, strict=True):
            try:
                channels.append((role, float(reactor.T), float(reactor.phase.P),
                                 np.array(reactor.phase.X, copy=True),
                                 np.array(reactor.phase.state, copy=True)))
            except Exception as snapshot_error:
                channels.append((role, snapshot_error))
        self.last_native_trial = (float(time_s), self.stack_temperature_k, tuple(channels))

    def evaluate(self, time_s):
        self.require_current()
        t = finite(time_s, "native fuel-cell RHS time")
        self.evaluated_clock_bounds_s[0] = min(self.evaluated_clock_bounds_s[0], t)
        self.evaluated_clock_bounds_s[1] = max(self.evaluated_clock_bounds_s[1], t)
        try:
            gas_states = {}
            state_signature = []
            for role, channel, reactor in zip(_ROLES, self.channels.values(), self.reactors, strict=True):
                phase = reactor.phase
                species_index = phase.species_index(channel.species_id)
                fraction = float(phase.X[species_index])
                moles = float(phase.density_mole*reactor.volume*fraction*1000.)
                if not np.isfinite(moles) or moles <= self.settings.minimum_species_inventory_mol:
                    raise ValueError(f"Native {role} reactant/product reached the declared inventory floor")
                state_signature.extend((float(phase.T), float(phase.P),
                    np.asarray(phase.X, dtype=float).tobytes(), float(reactor.volume)))
                gas_states[role] = FuelCellTrialGasState(
                    role=role, species_id=channel.species_id, time_s=t, clock_id=self.clock,
                    pressure_pa=float(phase.P), temperature_k=float(phase.T),
                    volume_m3=float(reactor.volume), species_mole_fraction=fraction,
                    species_moles_mol=moles,
                    species_molar_mass_kg_mol=float(phase.molecular_weights[species_index]/1000.),
                    activity_reference_pressure_pa=channel.activity_reference_pressure_pa,
                    activity_reference_id=channel.activity_reference_id,
                    evidence_id=channel.evidence_id + ":native-trial")
            stack_t = finite(self.stack_temperature_k, "native stack trial temperature", positive=True)
            key = (t, stack_t, tuple(state_signature))
            if key == self.cache_key:
                return self.cache_value
            view = NativeFuelCellTrialView(t, self.clock, stack_t, gas_states)
            command = finite(self.current_density(view), "caller current-density control")
            if command < 0.:
                raise ValueError("Caller current-density command must be a nonnegative magnitude")
            trial = FuelCellSynchronizedTrial(t, self.clock, stack_t, command,
                gas_states, self.run_id + ":synchronized-native-trial")
            exchange = evaluate_fuel_cell_trial_exchange(self.stack, self.standard, trial,
                evidence_id=self.run_id + ":native-RHS", fugacity_provider=self.fugacity_provider)
            enthalpy_sources = {}
            internal_energy_sources = {}
            for role, channel, reactor in zip(_ROLES, self.channels.values(), self.reactors, strict=True):
                index = reactor.phase.species_index(channel.species_id)
                rate_kmol_s = exchange.species_molar_rate_into_cv_mol_s[role]/1000.
                enthalpy_sources[role] = float(reactor.phase.partial_molar_enthalpies[index])*rate_kmol_s
                internal_energy_sources[role] = float(reactor.phase.partial_molar_int_energies[index])*rate_kmol_s
            native_hdot = fsum(enthalpy_sources.values())
            partition = self.thermal_partition(view, exchange, native_hdot)
            if type(partition) is not FuelCellThermalPartition:
                raise TypeError("Supply a typed caller-owned channel/stack thermal partition")
            expected = exchange.stack_result.electric_input_w-native_hdot
            allowance = (self.settings.energy_absolute_tolerance_j
                         + self.settings.energy_relative_tolerance*max(abs(expected), abs(native_hdot), 1.))
            if abs(partition.total_into_device_w-expected) > allowance:
                raise ValueError("Caller heat partition does not close native species enthalpy and electrical power")
            coolant_w = self.thermal.conductance_w_k*(self.thermal.coolant_temperature_k-stack_t)
            value = (view, exchange, partition, enthalpy_sources, internal_energy_sources,
                     native_hdot, coolant_w, command)
            trial.require_current()
            self.require_current()
            self.cache_key, self.cache_value = key, value
            return value
        except Exception as error:
            self.remember_error(error, t)
            raise


def _safe_integrals(reactor):
    return np.array(reactor._h2fuelcell_integrals, dtype=float, copy=True)


def _snapshot(time_s, channels, reactors, thermal, connection, energy_scale):
    view, exchange, partition, hdot, _, native_hdot, _, _ = connection.evaluate(time_s)
    channel_snapshots = {}
    for role, channel, reactor in zip(_ROLES, channels.values(), reactors, strict=True):
        phase = reactor.phase
        integrals = _safe_integrals(reactor)
        state_moles = tuple(float(v*1000.) for v in (phase.density_mole*reactor.volume*np.asarray(phase.X)))
        channel_snapshots[role] = NativeFuelCellChannelSnapshot(
            role, float(time_s), float(phase.T), float(phase.P), float(reactor.volume),
            tuple(phase.species_names), state_moles,
            float(phase.int_energy_mass*reactor.mass), float(integrals[0]),
            float(integrals[1]*energy_scale), float(integrals[2]*energy_scale))
    h2_integrals = _safe_integrals(reactors[0])
    stack_t = float(connection.stack_temperature_k)
    stack_energy = thermal.heat_capacity_j_k*(stack_t-thermal.energy_reference_temperature_k)
    return CanteraFuelCellSnapshot(float(time_s), channel_snapshots, stack_t, stack_energy,
        float(h2_integrals[4]*energy_scale), float(h2_integrals[5]*energy_scale),
        float(h2_integrals[6]*energy_scale), view, exchange, partition, native_hdot)


def run_cantera_synchronized_fuel_cell(*, channels: Mapping[str, CanteraFuelCellChannel],
        stack: HydrogenStack, standard_reaction_energy: ReactionEnergy,
        thermal: StackThermalParameters, current_density: Callable[[NativeFuelCellTrialView], float],
        thermal_partition: Callable[[NativeFuelCellTrialView, FuelCellTrialExchange, float], FuelCellThermalPartition],
        time_s, clock_id: str, run_evidence_id: str, energy_reference_id: str,
        fugacity_provider: FuelCellFugacityActivityProvider | None = None,
        settings=CanteraFuelCellSettings()):
    """Integrate three separated gas channels and one finite stack state together.

    ``current_density(view)`` is the caller's requested current/control policy.
    Its response may use the live pressures/composition, but no current limiting
    or automatic depletion shutdown is invented here. The heat partition callback
    receives the native species-enthalpy transfer rate and returns signed heat
    rates whose total closes it against electrical power.
    """
    import cantera as ct

    channels = dict(channels)
    if set(channels) != set(_ROLES) or any(type(v) is not CanteraFuelCellChannel for v in channels.values()):
        raise ValueError("Supply distinct typed native channels for H2, O2 and vapor water")
    if tuple(channels) != _ROLES:
        channels = {role: channels[role] for role in _ROLES}
    if len({id(channel.phase) for channel in channels.values()}) != 3:
        raise ValueError("The three channel phases must be independently owned Cantera Solution objects")
    if type(stack) is not HydrogenStack or type(standard_reaction_energy) is not ReactionEnergy:
        raise TypeError("Reuse the existing HydrogenStack and ReactionEnergy APIs")
    if standard_reaction_energy.water_phase != "vapor":
        raise ValueError("This native coupling uses the separate water-vapor channel")
    if not callable(current_density) or not callable(thermal_partition):
        raise TypeError("Supply caller-owned current and channel/stack thermal-partition callbacks")
    if not isinstance(clock_id, str) or not clock_id.strip() or not isinstance(run_evidence_id, str) or not run_evidence_id.strip():
        raise ValueError("Declare a shared absolute clock and run evidence identity")
    if not isinstance(energy_reference_id, str) or not energy_reference_id.strip():
        raise ValueError("Declare the shared native gas/reaction energy-reference identity")
    for channel in channels.values():
        if channel.energy_reference_id != energy_reference_id:
            raise ValueError("All gas and electrochemical reaction enthalpies need one declared energy reference")
        phase = channel.phase
        if phase.phase_of_matter != "gas" or getattr(phase, "thermo_model", "ideal-gas") not in {"ideal-gas", "IdealGas"}:
            raise ValueError("Use ideal-gas Cantera Solution phases for these native mole reactors")
        if not phase.min_temp <= phase.T <= phase.max_temp or phase.P <= 0.:
            raise ValueError("Each initialized channel phase must start in its native thermo domain")
        if channel.species_id not in phase.species_names:
            raise ValueError("Each channel's electrochemical species must exist in its native mechanism")
        if float(phase.X[phase.species_index(channel.species_id)]) <= 0.:
            raise ValueError("Each reactive species needs a positive initial channel inventory")
        expected_atoms = {
            "hydrogen": {"H": 2., "O": 0.},
            "oxygen": {"H": 0., "O": 2.},
            "water_vapor": {"H": 2., "O": 1.},
        }[channel.role]
        species_index = phase.species_index(channel.species_id)
        for element, expected_count in expected_atoms.items():
            observed = (float(phase.n_atoms(species_index, phase.element_index(element)))
                        if element in phase.element_names else 0.)
            if observed != expected_count:
                raise ValueError(f"{channel.role} channel species lacks the declared H/O atom identity")
    if not isclose(stack.geometry.hydrogen_molar_mass_kg_mol,
            channels["hydrogen"].phase.molecular_weights[channels["hydrogen"].phase.species_index(
                channels["hydrogen"].species_id)]/1000., rel_tol=1e-6, abs_tol=1e-12):
        raise ValueError("HydrogenStack and native H2 channel molar masses differ")
    times = np.array(time_s, dtype=float, copy=True)
    if times.ndim != 1 or len(times) < 2 or not np.all(np.isfinite(times)) or np.any(np.diff(times) <= 0.):
        raise ValueError("Native accepted-output times must be finite and strictly increasing")
    if not isinstance(settings, CanteraFuelCellSettings):
        raise TypeError("Use typed Cantera fuel-cell integration settings")
    if type(current_density) is FuelCellReactantCurrentLimit:
        current_density.require_driver_compatibility(
            stack, settings.minimum_species_inventory_mol)
    if (fugacity_provider is not None
            and type(fugacity_provider) is not FuelCellFugacityActivityProvider):
        raise TypeError("Use the existing typed fugacity provider or omit it for ideal activities")
    if thermal.energy_reference_id != energy_reference_id:
        raise ValueError("Stack sensible energy and gas/reaction packets must share the declared energy reference")
    connection = _Connection(channels, stack, standard_reaction_energy, thermal, clock_id,
        run_evidence_id, current_density, thermal_partition, fugacity_provider, settings,
        energy_reference_id)
    from .cantera_volume import _phase_fingerprint
    connection.phase_fingerprints = tuple(_phase_fingerprint(channel.phase, include_reactions=True)
                                          for channel in channels.values())
    species_indices = {role: channel.phase.species_index(channel.species_id)
                       for role, channel in channels.items()}
    labels = {
        role: ("exchange:moles_mol", "exchange:enthalpy_j", "assigned:heat_j")
        for role in _ROLES
    }
    labels["hydrogen"] = labels["hydrogen"] + (
        "stack:temperature_k", "stack:electric_input_j", "stack:coolant_heat_j", "stack:assigned_heat_j")
    energy_scale = settings.energy_ledger_scale_j
    reactors = []

    class CoupledMoleReactor(ct.ExtensibleIdealGasMoleReactor):
        def __init__(self, phase, role):
            self.role = role
            self.base_size = 0
            self._h2fuelcell_integrals = np.zeros(len(labels[role]))
            super().__init__(phase, clone=False, energy="on", name="fuel-cell-"+role)
            self.chemistry_enabled = False
            self.volume = channels[role].volume_m3

        def after_initialize(self, t0):
            self.base_size = self.n_vars
            self.n_vars += len(labels[self.role])
            if self.role == "hydrogen":
                self._h2fuelcell_integrals[3] = thermal.initial_temperature_k

        def after_get_state(self, y):
            y[self.base_size:] = self._h2fuelcell_integrals

        def after_update_state(self, y):
            self._h2fuelcell_integrals[:] = y[self.base_size:]
            if self.role == "hydrogen":
                connection.stack_temperature_k = float(self._h2fuelcell_integrals[3])

        def before_component_name(self, index):
            if index >= self.base_size:
                return labels[self.role][index-self.base_size]

        def before_component_index(self, name):
            if name in labels[self.role]:
                return self.base_size+labels[self.role].index(name)

        def after_eval(self, time, lhs, rhs):
            try:
                view, exchange, partition, h_sources, u_sources, native_hdot, coolant_w, _ = connection.evaluate(time)
                role, channel = self.role, channels[self.role]
                rate_mol_s = exchange.species_molar_rate_into_cv_mol_s[role]
                rate_kmol_s = rate_mol_s/1000.
                idx = self.component_index(channel.species_id)
                rhs[idx] += rate_kmol_s
                # IdealGasMoleReactor uses m*cv*dT/dt and U as the physical
                # energy state. Convert the added species mole source to the
                # native partial-enthalpy open-boundary energy term.
                rhs[0] += h_sources[role]-u_sources[role]+partition.__getattribute__(role+"_w")
                base = self.base_size
                if role == "hydrogen":
                    rhs[base+3] = coolant_w+partition.stack_w
                    lhs[base+3] = thermal.heat_capacity_j_k
                    rates = [rate_mol_s, h_sources[role]/energy_scale,
                             partition.hydrogen_w/energy_scale, coolant_w+partition.stack_w,
                             exchange.stack_result.electric_input_w/energy_scale,
                             coolant_w/energy_scale, partition.stack_w/energy_scale]
                else:
                    rates = [rate_mol_s, h_sources[role]/energy_scale,
                             partition.__getattribute__(role+"_w")/energy_scale]
                # Cantera callback buffers expose scalar indexing; assigning a
                # Python list to a slice is not supported by the native view.
                indices = (*range(base, base+3), *range(base+4, base+7)) if role == "hydrogen" else range(base, base+len(rates))
                for index in indices:
                    lhs[index] = 1.
                for offset, value in enumerate(rates):
                    rhs[base+offset] = value
            except Exception as error:
                connection.remember_error(error, time)
                raise

    try:
        reactors = tuple(CoupledMoleReactor(channels[role].phase, role) for role in _ROLES)
        connection.reactors = reactors
        network = ct.ReactorNet(list(reactors))
        network.initial_time = float(times[0])
        network.rtol = settings.relative_tolerance
        network.atol = settings.absolute_tolerance
        network.max_time_step = settings.maximum_time_step_s
        network.max_steps = settings.maximum_steps
        native = NativeCanteraFuelCellObjects(reactors, network, connection)
        accepted = []

        def capture(time):
            if connection.first_error is not None:
                raise ValueError("A native fuel-cell trial failed and remains the first failure") from connection.first_error
            connection.require_current()
            point = _snapshot(time, channels, reactors, thermal, connection, energy_scale)
            if point.stack_temperature_k <= 0.:
                raise ValueError("Finite stack thermal state left the positive-temperature domain")
            for role, channel, reactor in zip(_ROLES, channels.values(), reactors, strict=True):
                index = species_indices[role]
                if reactor.volume != channel.volume_m3:
                    raise ValueError("Native fuel-cell channel volume changed during the fixed-volume run")
                moles = reactor.phase.density_mole*reactor.volume*reactor.phase.X[index]*1000.
                if moles <= settings.minimum_species_inventory_mol:
                    raise ValueError("Accepted native channel reached the declared reactant inventory floor")
            accepted.append(point)

        network.initialize()
        capture(float(times[0]))
        for requested in times[1:]:
            network.advance(float(requested))
            if connection.first_error is not None:
                raise ValueError("Native solver recovered after a failed trial; fail-closed boundary retained") from connection.first_error
            capture(float(requested))
        initial, final = accepted[0], accepted[-1]
        component_residuals, gas_energy_residuals = [], []
        for role in _ROLES:
            first, last = initial.channels[role], final.channels[role]
            channel = channels[role]
            species_residual = []
            for name, n0, n1 in zip(first.species, first.species_moles_mol,
                                     last.species_moles_mol, strict=True):
                expected = last.species_source_moles_mol if name == channel.species_id else 0.
                species_residual.append(n1-n0-expected)
            component_residuals.extend(species_residual)
            gas_energy_residuals.append(last.internal_energy_j-first.internal_energy_j
                -last.species_enthalpy_transfer_j-last.assigned_heat_j)
        stack_delta = final.stack_energy_j-initial.stack_energy_j
        stack_residual = stack_delta-final.stack_assigned_heat_into_j+initial.stack_assigned_heat_into_j \
            -final.stack_coolant_energy_into_j+initial.stack_coolant_energy_into_j
        # H2 ledger positions are cumulative from the zero initial state.
        electric = final.stack_electrical_energy_into_j-initial.stack_electrical_energy_into_j
        coolant = final.stack_coolant_energy_into_j-initial.stack_coolant_energy_into_j
        combined = fsum(last.internal_energy_j-first.internal_energy_j
            for first, last in ((initial.channels[r], final.channels[r]) for r in _ROLES))
        combined += stack_delta-electric-coolant
        max_component = max((abs(value) for value in component_residuals), default=0.)
        max_gas_energy = max((abs(value) for value in gas_energy_residuals), default=0.)
        scale = max(1., *(abs(s.internal_energy_j) for p in accepted for s in p.channels.values()),
                    abs(final.stack_energy_j-initial.stack_energy_j), abs(electric), abs(coolant))
        energy_limit = settings.energy_absolute_tolerance_j+settings.energy_relative_tolerance*scale
        if max_component > settings.component_mole_absolute_tolerance_mol:
            raise ValueError("Native species source ledger failed its component-inventory closure")
        if max_gas_energy > energy_limit or abs(stack_residual) > energy_limit or abs(combined) > energy_limit:
            raise ValueError("Native channel/stack energy ledgers failed their closure tolerance")
        return _issue_trace(channels=channels, stack=stack,
            standard_reaction_energy=standard_reaction_energy, thermal=thermal,
            clock_id=clock_id, run_evidence_id=run_evidence_id, settings=settings,
            accepted=tuple(accepted), native=native,
            maximum_component_mole_residual_mol=max_component,
            maximum_channel_energy_residual_j=max_gas_energy,
            stack_energy_residual_j=stack_residual, combined_energy_residual_j=combined)
    except CanteraFuelCellIntegrationError:
        raise
    except Exception as cause:
        if not reactors:
            reactors = tuple(reactors)
        native = NativeCanteraFuelCellObjects(tuple(reactors), locals().get("network"), connection)
        raise CanteraFuelCellIntegrationError(cause, native=native,
            accepted=locals().get("accepted", ()), last_native_trial=connection.last_native_trial) from cause


__all__ = ["CanteraFuelCellChannel", "StackThermalParameters", "FuelCellThermalPartition",
    "NativeFuelCellTrialView", "NativeFuelCellChannelSnapshot", "CanteraFuelCellSnapshot",
    "NativeCanteraFuelCellObjects", "CanteraFuelCellTrace", "CanteraFuelCellSettings",
    "CanteraFuelCellIntegrationError", "run_cantera_synchronized_fuel_cell"]
