"""Finite, well-mixed gas volumes using native Cantera integration.

Cantera owns the EOS and physical mass/species/temperature equations. A native
ExtensibleIdealGasReactor appends boundary and reaction integrals through public hooks:
https://cantera.org/3.2/python/zerodim.html#extensiblereactor
https://cantera.org/3.2/reference/reactors/ideal-gas-reactor.html

This is a thermodynamic control volume, not spatial or stratified dispersion.
The inlet reservoir states are fixed during one run; their rates may vary.
"""

import hashlib
import json
import math
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from types import MappingProxyType

import numpy as np

from ..core import immutable_array, Origin, TimeSeries, finite
from .cantera import MechanismBasis, ReactiveState


def _require_boundary_clock(boundary_id, clock_id, start, end):
    if (not isinstance(boundary_id, str) or not boundary_id.strip()
            or not isinstance(clock_id, str) or not clock_id.strip()):
        raise ValueError("Boundary and absolute clock identities are required")
    finite(start, "support start")
    finite(end, "support end")
    if start >= end:
        raise ValueError("Boundary support must have increasing endpoints")


@dataclass(frozen=True, slots=True)
class GasBoundaryRate:
    """Nonnegative oriented rate on an explicit absolute clock and finite support.

    By default ``callback(time_s, native_volume_phase)`` returns kg/s. The phase is
    read-only during this callback. Explicit ``phase_access="time_only"`` instead
    calls ``callback(time_s)`` and permits private reactive phases. Negative signed
    observations are rejected, never clipped
    by Cantera's own nonnegative MassFlowController implementation. Callbacks must
    be continuous within the integration window at this model level.
    """

    boundary_id: str
    clock_id: str
    support_start_s: float
    support_end_s: float
    callback: Callable
    origin: Origin
    source_id: str
    phase_access: str = "native"

    def __post_init__(self):
        _require_boundary_clock(self.boundary_id, self.clock_id, self.support_start_s,
                                self.support_end_s)
        if not callable(self.callback):
            raise ValueError("A rate callback is required")
        if self.phase_access not in {"native", "time_only"}:
            raise ValueError("Choose native phase access or an explicit time_only callback")
        object.__setattr__(self, "origin", Origin(self.origin))
        if (self.origin == Origin.UNRESOLVED or not isinstance(self.source_id, str)
                or not self.source_id.strip()):
            raise ValueError("Rate origin and source identity must be resolved explicitly")

    def require_time(self, time_s):
        if not self.support_start_s <= finite(time_s, "callback time") <= self.support_end_s:
            raise ValueError(f"Boundary {self.boundary_id} evaluated outside its clock support")

    def value(self, time_s, phase):
        self.require_time(time_s)
        if self.phase_access == "time_only":
            rate = self.callback(float(time_s))
            if finite(rate, "oriented mass flow") < 0:
                raise ValueError("Negative oriented mass flow is not clipped or reversed")
            return float(rate)
        before = phase.state.copy()
        old_basis = phase.basis
        rate = self.callback(float(time_s), phase)
        if not np.array_equal(phase.state, before) or phase.basis != old_basis:
            raise ValueError("A gas boundary callback mutated the native volume phase")
        if finite(rate, "oriented mass flow") < 0:
            raise ValueError("Negative oriented mass flow is not clipped or reversed")
        return float(rate)


def sampled_gas_rate(series: TimeSeries, channel: str, *, boundary_id: str) -> GasBoundaryRate:
    """Explicit piecewise-linear sampling of one complete, nonnegative kg/s channel.

    No extrapolation, mask filling, measured-clock alignment or sign repair is
    performed. Pressure recorder clocks are not source-flow clocks by implication.
    """
    values, valid = series.channel_values(channel, quantity="mass_flow")
    index = series.channels.index(channel)
    if series.units[index] != "kg/s" or series.origin == Origin.UNRESOLVED:
        raise ValueError("A resolved kg/s mass-flow history is required")
    if len(series.time_s) < 2 or not np.all(valid):
        raise ValueError("A rate history needs at least two valid samples and no masked gaps")
    if np.any(values < 0):
        raise ValueError("Negative signed measurements cannot be clipped into a gas source")
    return GasBoundaryRate(boundary_id, series.clock_id, float(series.time_s[0]),
                           float(series.time_s[-1]),
                           lambda t, phase: float(np.interp(t, series.time_s, values)),
                           series.origin, series.source_id)


@dataclass(frozen=True, slots=True)
class GasFeed:
    rate: GasBoundaryRate
    state: ReactiveState


@dataclass(frozen=True, slots=True)
class GasVent:
    """Prescribed outward extraction; its magnitude can call the shared nozzle.

    It is not itself a pressure-driven valve law. A callback is responsible for
    declaring that closure, including zero flow at an unavailable pressure head.
    The native flow device removes well-mixed upstream composition and enthalpy.
    """

    rate: GasBoundaryRate
    downstream_state: ReactiveState


@dataclass(frozen=True, slots=True)
class GasHeatBoundary:
    """Stationary native wall, oriented environment -> enclosure.

    ``heat_flux_w_m2(time_s)`` is signed heat into the volume. Conduction and
    radiation also use native Cantera Wall terms and a fixed environment state.
    Wall thermal storage is not resolved.
    """

    boundary_id: str
    clock_id: str
    support_start_s: float
    support_end_s: float
    environment_state: ReactiveState
    area_m2: float
    heat_transfer_coefficient_w_m2_k: float = 0.
    emissivity: float = 0.
    heat_flux_w_m2: Callable = lambda t: 0.

    def __post_init__(self):
        _require_boundary_clock(self.boundary_id, self.clock_id, self.support_start_s,
                                self.support_end_s)
        finite(self.area_m2, "wall area", positive=True)
        if finite(self.heat_transfer_coefficient_w_m2_k, "heat transfer coefficient") < 0:
            raise ValueError("Wall heat transfer coefficient must be nonnegative")
        if not 0 <= finite(self.emissivity, "emissivity") <= 1:
            raise ValueError("Wall emissivity must lie in [0, 1]")
        if not callable(self.heat_flux_w_m2):
            raise ValueError("A heat-flux callback is required")

    def value(self, time_s):
        if not self.support_start_s <= finite(time_s, "wall time") <= self.support_end_s:
            raise ValueError(f"Wall {self.boundary_id} evaluated outside its clock support")
        return finite(self.heat_flux_w_m2(float(time_s)), "signed wall heat flux")


@dataclass(frozen=True, slots=True)
class GasVolumeSnapshot:
    time_s: float
    mass_kg: float
    volume_m3: float
    temperature_k: float
    pressure_pa: float
    mass_fractions: Mapping[str, float]
    mole_fractions: Mapping[str, float]
    internal_energy_j: float
    specific_enthalpy_j_kg: float

    def __post_init__(self):
        for name in ("mass_fractions", "mole_fractions"):
            object.__setattr__(self, name, MappingProxyType(dict(getattr(self, name))))


@dataclass(frozen=True, slots=True)
class NativeGasVolumeObjects:
    reactor: object
    network: object
    feed_reservoirs: tuple
    vent_reservoirs: tuple
    environment_reservoirs: tuple
    feed_devices: tuple
    vent_devices: tuple
    walls: tuple


@dataclass(frozen=True, slots=True)
class NativePhaseCopyAudit:
    source_fingerprint: str
    owned_fingerprint: str
    maximum_relative_roundtrip: float
    numeric_roundtrip_count: int
    omitted_note_count: int
    source_element_names: tuple[str, ...]
    owned_element_names: tuple[str, ...]
    relative_roundtrip_limit: float = 2e-15


@dataclass(frozen=True, slots=True)
class GasVolumeTrace:
    mechanism_basis: MechanismBasis
    phase_fingerprint: str
    clock_id: str
    species_names: tuple[str, ...]
    time_s: np.ndarray
    snapshots: tuple[GasVolumeSnapshot, ...]
    ledger_names: tuple[str, ...]
    ledger_units: tuple[str, ...]
    ledger_native_scale_to_si: np.ndarray
    boundary_integrals: np.ndarray
    mass_residual_kg: np.ndarray
    species_residual_kg: np.ndarray
    energy_residual_j: np.ndarray
    native: NativeGasVolumeObjects
    feeds: tuple[GasFeed, ...]
    vents: tuple[GasVent, ...]
    heat_boundaries: tuple[GasHeatBoundary, ...]
    evaluated_clock_bounds_s: tuple[float, float] | None
    ledger_method: str = "native-CVODES-appended-boundary-integrals"
    hydrogen_partition_id: str = "mechanism-H2-spin-unresolved"
    chemistry: str = "frozen"
    reaction_species_integrals_kg: np.ndarray | None = None
    element_names: tuple[str, ...] = ()
    element_residual_kg: np.ndarray | None = None
    definition_guard: str = "every-native-RHS"
    source_phase_fingerprint: str = ""
    phase_copy_audits: tuple[NativePhaseCopyAudit, ...] = ()

    def __post_init__(self):
        for name in ("time_s", "ledger_native_scale_to_si", "boundary_integrals", "mass_residual_kg",
                     "species_residual_kg", "energy_residual_j", "reaction_species_integrals_kg",
                     "element_residual_kg"):
            if getattr(self, name) is None:
                continue
            value = np.array(getattr(self, name), dtype=float, copy=True)
            value = immutable_array(value, name="value")
            object.__setattr__(self, name, value)

    def integral(self, name):
        return self.boundary_integrals[:, self.ledger_names.index(name)]


class GasVolumeIntegrationError(RuntimeError):
    """Native failure retaining actual native objects for diagnostic inspection."""

    def __init__(self, message, native):
        super().__init__(message)
        self.native = native


def _phase_fingerprint(phase, *, include_reactions=False):
    # State is excluded. Species thermo, elements, ordering and molecular data
    # must agree across reservoirs; a mechanism filename alone cannot prove it.
    material = {"thermo": phase.thermo_model,
                "species": [dict(s.input_data) for s in phase.species()],
                "molecular_weights": phase.molecular_weights.tolist(),
                "thermo_bounds": [(s.thermo.min_temp, s.thermo.max_temp,
                                   s.thermo.reference_pressure) for s in phase.species()]}
    if include_reactions:
        material["kinetics"] = phase.kinetics_model
        material["reactions"] = [dict(reaction.input_data) for reaction in phase.reactions()]
        material["multipliers"] = [phase.multiplier(i) for i in range(phase.n_reactions)]
    return hashlib.sha256(json.dumps(material, sort_keys=True).encode()).hexdigest()


def _snapshot(time_s, reactor):
    phase = reactor.phase
    return GasVolumeSnapshot(float(time_s), reactor.mass, reactor.volume, phase.T, phase.P,
        dict(zip(phase.species_names, phase.Y, strict=True)),
        dict(zip(phase.species_names, phase.X, strict=True)),
        reactor.mass*phase.int_energy_mass, phase.enthalpy_mass)


def _private_native_phase(phase, ct):
    """Copy through native species/reaction APIs and verify physical definitions.

    Cantera 3.2's YAML-based clone path can lose ConstantCp fit bounds and runtime
    multipliers. No such definition change is accepted for this owned copy.
    """
    species = []
    for original in phase.species():
        item = ct.Species.from_dict(dict(original.input_data))
        thermo = original.thermo
        item.thermo = type(thermo)(thermo.min_temp, thermo.max_temp,
                                  thermo.reference_pressure, thermo.coeffs)
        species.append(item)
    copied = ct.Solution(thermo=phase.thermo_model, kinetics=phase.kinetics_model,
                         transport_model=phase.transport_model, species=species, reactions=[])
    copied.name = phase.name
    for reaction in phase.reactions():
        copied.add_reaction(ct.Reaction.from_dict(dict(reaction.input_data), copied))
    for index in range(phase.n_reactions):
        copied.set_multiplier(phase.multiplier(index), index)
    copied.state = phase.state
    copied.basis = phase.basis
    # Native parsing can round SI activation energies by one or two ulps, and
    # reconstruction drops thermo notes. Audit those differences once; the owned
    # definition's exact hash guards accepted output, without numeric tolerance.
    numeric_errors, omitted_notes = [], []

    def compare(source, owned, path):
        if isinstance(source, Mapping) and isinstance(owned, Mapping):
            for key in set(source) | set(owned):
                if key == "note":
                    if source.get(key) != owned.get(key):
                        omitted_notes.append(path+"/note")
                    continue
                if key not in source or key not in owned:
                    raise ValueError(f"Native private copy changed definition keys at {path}/{key}")
                compare(source[key], owned[key], path+"/"+key)
        elif isinstance(source, (list, tuple)) and isinstance(owned, (list, tuple)):
            if len(source) != len(owned):
                raise ValueError(f"Native private copy changed definition size at {path}")
            for i, (a, b) in enumerate(zip(source, owned, strict=True)):
                compare(a, b, path+f"/{i}")
        elif source != owned:
            if (isinstance(source, (int, float)) and isinstance(owned, (int, float))
                    and not isinstance(source, bool) and not isinstance(owned, bool)):
                error = abs(source-owned)/max(abs(source), abs(owned))
                if not math.isfinite(error) or error > 2e-15:
                    raise ValueError(f"Native private copy changed physical coefficient at {path}")
                numeric_errors.append(error)
            else:
                raise ValueError(f"Native private copy changed physical definition at {path}")

    for original, owned in zip(phase.species(), copied.species(), strict=True):
        # Thermo coefficients, validity bounds and reference pressure are copied
        # directly through native APIs, and must survive exactly.
        a, b = original.thermo, owned.thermo
        if (type(a) is not type(b) or a.min_temp != b.min_temp or a.max_temp != b.max_temp
                or a.reference_pressure != b.reference_pressure
                or not np.array_equal(a.coeffs, b.coeffs)):
            raise ValueError("Native private copy changed species thermo coefficients/bounds")
        compare(dict(original.input_data), dict(owned.input_data), "species/"+original.name)
    compare([dict(r.input_data) for r in phase.reactions()],
            [dict(r.input_data) for r in copied.reactions()], "reactions")
    if (phase.species_names != copied.species_names
            or set(phase.element_names) != set(copied.element_names)
            or any(phase.atomic_weight(e) != copied.atomic_weight(e) for e in phase.element_names)
            or not np.array_equal(phase.molecular_weights, copied.molecular_weights)
            or any(phase.multiplier(i) != copied.multiplier(i) for i in range(phase.n_reactions))):
        raise ValueError("Native private copy changed species/elements/molecular data/multipliers")
    audit = NativePhaseCopyAudit(_phase_fingerprint(phase, include_reactions=True),
        _phase_fingerprint(copied, include_reactions=True), max(numeric_errors, default=0.),
        len(numeric_errors), len(omitted_notes), tuple(phase.element_names),
        tuple(copied.element_names))
    return copied, audit


class CanteraOpenGasVolume:
    """A constant-volume, finite-inventory thermodynamic reference model.

    ``phase_factory`` must produce fresh native ideal-gas Solutions. Default
    chemistry="frozen" requires zero reactions, retaining the established level.
    Explicit chemistry="finite_rate" delegates gas kinetics to Cantera and appends
    chemical production integrals for independent species/element accounting.
    There are no surfaces, catalysts, solids or custom reaction-rate equations.
    The basis record is
    caller-supplied evidence, not proof of its provenance. No mechanism is bundled.
    Native Cantera 3.2 owns every physical state derivative and integration step.
    """

    def __init__(self, phase_factory: Callable, mechanism_basis: MechanismBasis, *,
                 chemistry: str = "frozen"):
        import cantera as ct

        if tuple(int(v) for v in ct.__version__.split(".")[:2]) != (3, 2):
            raise ValueError("This native extensible-reactor level is checked with Cantera 3.2")
        if chemistry not in {"frozen", "finite_rate"}:
            raise ValueError("Choose explicit frozen or finite_rate native gas chemistry")
        self.ct, self.phase_factory, self.mechanism_basis = ct, phase_factory, mechanism_basis
        self.chemistry = chemistry

    def run(self, initial: ReactiveState, time_s, *, volume_m3: float, clock_id: str,
            feeds: tuple[GasFeed, ...] = (), vents: tuple[GasVent, ...] = (),
            heat_boundaries: tuple[GasHeatBoundary, ...] = (), maximum_time_step_s: float,
            relative_tolerance: float = 1e-9, absolute_tolerance: float = 1e-13,
            minimum_inventory_kg: float = 1e-12,
            energy_ledger_scale_j: float = 1e6) -> GasVolumeTrace:
        times = np.asarray(time_s, dtype=float)
        if (times.ndim != 1 or len(times) < 2 or not np.all(np.isfinite(times))
                or np.any(np.diff(times) <= 0)):
            raise ValueError("Output times must be finite, strictly increasing absolute times")
        if not isinstance(clock_id, str) or not clock_id.strip():
            raise ValueError("An absolute operation clock identity is required")
        finite(volume_m3, "enclosure volume", positive=True)
        finite(maximum_time_step_s, "maximum native time step", positive=True)
        finite(minimum_inventory_kg, "minimum inventory", positive=True)
        finite(energy_ledger_scale_j, "native energy-ledger scale in J", positive=True)
        for tolerance in (relative_tolerance, absolute_tolerance):
            if not 0 < finite(tolerance, "native integration tolerance") < 1:
                raise ValueError("Native integration tolerances must lie in (0, 1)")
        boundaries = [b.rate for b in (*feeds, *vents)] + list(heat_boundaries)
        ids = [b.boundary_id for b in boundaries]
        if len(set(ids)) != len(ids):
            raise ValueError("All mass and heat boundary identities must be unique")
        for boundary in boundaries:
            if boundary.clock_id != clock_id:
                raise ValueError("Boundary and volume clock identities differ")
            if not (boundary.support_start_s <= times[0] < times[-1]
                    and times[-1]+maximum_time_step_s <= boundary.support_end_s):
                raise ValueError("Output window plus one native maximum step exceeds boundary clock support")

        phases = []
        fingerprint = None
        source_fingerprint = None
        copy_audits = []
        reactive = self.chemistry == "finite_rate"
        # With no phase-exposing callback, native clones keep the physical
        # definitions private until the completed trace is returned. Time-only
        # callbacks cannot mutate these objects through the supplied API.
        # Full native-phase access retains the stronger per-RHS identity guard.
        private_phases = reactive and all(b.rate.phase_access == "time_only" for b in (*feeds, *vents))

        def phase_for(state):
            nonlocal fingerprint, source_fingerprint
            self.mechanism_basis.require_state(state.temperature_k, state.pressure_pa)
            phase = self.phase_factory()
            if not isinstance(phase, self.ct.Solution) or phase.thermo_model != "ideal-gas":
                raise ValueError("A native ideal-gas Solution is required")
            if not reactive and phase.n_reactions != 0:
                raise ValueError("A native ideal-gas Solution with zero reactions is required")
            if reactive and phase.n_reactions == 0:
                raise ValueError("Finite-rate chemistry requires actual native gas reactions")
            if phase.n_selected_species != phase.n_species:
                raise ValueError("A selected-species view is not a full native volume phase")
            if any(phase is earlier for earlier in phases):
                raise ValueError("The phase factory must return fresh independent native phases")
            phases.append(phase)
            actual = _phase_fingerprint(phase, include_reactions=reactive)
            if source_fingerprint is None:
                source_fingerprint = actual
            elif actual != source_fingerprint:
                raise ValueError("Reservoir and enclosure thermochemistry/selected kinetics differ")
            if not set(state.mole_fractions) <= set(phase.species_names):
                raise ValueError("A boundary declares species absent from the native phase")
            phase.TPX = state.temperature_k, state.pressure_pa, dict(state.mole_fractions)
            if phase.phase_of_matter != "gas":
                raise ValueError("Only a native gas phase is supported")
            if not phase.min_temp <= phase.T <= phase.max_temp:
                raise ValueError("Temperature is outside the native species-thermo range")
            if reactive:
                phase, audit = _private_native_phase(phase, self.ct)
                copy_audits.append(audit)
                actual = audit.owned_fingerprint
            if fingerprint is None:
                fingerprint = actual
            elif actual != fingerprint:
                raise ValueError("Owned reservoir and enclosure definitions differ")
            return phase

        phase = phase_for(initial)
        species = tuple(phase.species_names)
        elements = tuple(phase.element_names)
        nf, nv, ns = len(feeds), len(vents), len(species)
        labels = (tuple(f"inlet:{b.rate.boundary_id}:mass" for b in feeds)
                  + tuple(f"outlet:{b.rate.boundary_id}:mass" for b in vents)
                  + tuple(f"net:species:{name}" for name in species)
                  + (tuple(f"reaction:species:{name}" for name in species) if reactive else ())
                  + ("inlet:enthalpy", "outlet:enthalpy", "wall:heat"))
        species_start = nf+nv
        reaction_start = species_start+ns
        element_fractions = np.array([[phase.n_atoms(k, e)*phase.atomic_weight(e)
            / phase.molecular_weights[k] for k in range(ns)] for e in elements])
        ledger_scales = np.ones(len(labels))
        ledger_scales[-3:] = energy_ledger_scale_j
        evaluated = []
        boundary_error = None
        boundary_objects = None
        basis = self.mechanism_basis

        class LedgerReactor(self.ct.ExtensibleIdealGasReactor):
            def __init__(self, native_phase, **kwargs):
                self.ledger = np.zeros(len(labels))
                self.base_size = 0
                super().__init__(native_phase, **kwargs)

            def after_initialize(self, t0):
                self.base_size = self.n_vars
                self.n_vars += len(labels)

            def after_get_state(self, y):
                y[self.base_size:] = self.ledger

            def after_update_state(self, y):
                self.ledger[:] = y[self.base_size:]

            def before_component_name(self, index):
                if index >= self.base_size:
                    return labels[index-self.base_size]

            def before_component_index(self, name):
                if name in labels:
                    return self.base_size+labels.index(name)

            def after_eval(self, time, lhs, rhs):
                nonlocal boundary_error
                basis.require_state(self.T, self.phase.P)
                if not self.phase.min_temp <= self.T <= self.phase.max_temp:
                    raise ValueError("Native species-thermo temperature domain was exceeded")
                if self.mass <= minimum_inventory_kg:
                    raise ValueError("Finite gas inventory reached its declared minimum")
                if not private_phases and _phase_fingerprint(
                        self.phase, include_reactions=reactive) != fingerprint:
                    boundary_error = ValueError(
                        "A callback mutated native volume thermochemistry/selected kinetics")
                    raise boundary_error
                if self.expansion_rate != 0.:
                    raise ValueError("Native wall volume expansion is unsupported")

                # Read connected native rates/properties, not derivatives of the
                # physical inventory. Only the appended ledger rows are written.
                inflows = np.array([d.mass_flow_rate for d in boundary_objects.feed_devices])
                outflows = np.array([d.mass_flow_rate for d in boundary_objects.vent_devices])
                rates = np.zeros(len(labels))
                rates[:nf] = inflows
                rates[nf:nf+nv] = outflows
                for rate, reservoir in zip(inflows, boundary_objects.feed_reservoirs, strict=True):
                    rates[species_start:species_start+ns] += rate*reservoir.phase.Y
                    rates[-3] += rate*reservoir.phase.enthalpy_mass
                rates[species_start:species_start+ns] -= outflows.sum()*self.phase.Y
                if reactive:
                    # Native production is kmol/(m3*s); native molecular weights
                    # are kg/kmol. No chemical heat is added to the total-energy
                    # ledger: formation energy already belongs to native U/h.
                    rates[reaction_start:reaction_start+ns] = (
                        self.phase.net_production_rates*self.phase.molecular_weights*self.volume)
                rates[-2] = outflows.sum()*self.phase.enthalpy_mass
                rates[-1] = sum(w.heat_rate for w in boundary_objects.walls)
                lhs[self.base_size:] = 1.
                # Conditioning affects only the appended integral variables.
                # Native physical equations and scalar rtol/atol are unchanged.
                rhs[self.base_size:] = rates/ledger_scales

        reactor = LedgerReactor(phase, clone=False, energy="on", name="gas-volume")
        reactor.volume = volume_m3
        reactor.chemistry_enabled = reactive
        if reactor.mass <= minimum_inventory_kg:
            raise ValueError("Initial gas inventory is below its declared minimum")

        def mass_callback(boundary):
            def callback(t):
                nonlocal boundary_error
                record_time(t)
                try:
                    return boundary.value(t, reactor.phase)
                except Exception as exc:
                    boundary_error = exc
                    raise
            return callback

        def record_time(time):
            if not evaluated:
                evaluated[:] = [float(time), float(time)]
            else:
                evaluated[0] = min(evaluated[0], float(time))
                evaluated[1] = max(evaluated[1], float(time))

        feed_reservoirs = tuple(self.ct.Reservoir(phase_for(b.state), clone=False,
                                               name=f"feed-{b.rate.boundary_id}") for b in feeds)
        vent_reservoirs = tuple(self.ct.Reservoir(phase_for(b.downstream_state), clone=False,
                                               name=f"sink-{b.rate.boundary_id}") for b in vents)
        environment_reservoirs = tuple(self.ct.Reservoir(phase_for(b.environment_state),
            clone=False, name=f"environment-{b.boundary_id}") for b in heat_boundaries)
        feed_devices = tuple(self.ct.MassFlowController(reservoir, reactor,
            mdot=mass_callback(b.rate)) for b, reservoir in zip(feeds, feed_reservoirs, strict=True))
        vent_devices = tuple(self.ct.MassFlowController(reactor, reservoir,
            mdot=mass_callback(b.rate)) for b, reservoir in zip(vents, vent_reservoirs, strict=True))

        def heat_callback(boundary):
            def callback(t):
                nonlocal boundary_error
                record_time(t)
                try:
                    return boundary.value(t)
                except Exception as exc:
                    boundary_error = exc
                    raise
            return callback

        walls = []
        for boundary, reservoir in zip(heat_boundaries, environment_reservoirs, strict=True):
            wall = self.ct.Wall(reservoir, reactor, A=boundary.area_m2,
                U=boundary.heat_transfer_coefficient_w_m2_k, K=0., velocity=0.,
                Q=heat_callback(boundary), name=boundary.boundary_id)
            wall.emissivity = boundary.emissivity
            walls.append(wall)
        network = self.ct.ReactorNet([reactor])
        network.initial_time = float(times[0])
        network.rtol, network.atol = relative_tolerance, absolute_tolerance
        network.max_time_step = maximum_time_step_s
        boundary_objects = NativeGasVolumeObjects(reactor, network, feed_reservoirs,
            vent_reservoirs, environment_reservoirs, feed_devices, vent_devices, tuple(walls))
        snapshots = [_snapshot(times[0], reactor)]
        integrals = [reactor.ledger.copy()]
        try:
            for time in times[1:]:
                network.advance(float(time))
                if boundary_error is not None:
                    # CVODES can recover from a Python callback exception by
                    # retrying a shorter step. Retain an actual boundary breach
                    # even when the native solver subsequently reaches output.
                    raise ValueError(str(boundary_error)) from boundary_error
                basis.require_state(reactor.T, reactor.phase.P)
                if _phase_fingerprint(reactor.phase, include_reactions=reactive) != fingerprint:
                    raise ValueError("Accepted native thermochemistry/selected kinetics changed")
                if not math.isclose(reactor.volume, volume_m3, abs_tol=0., rel_tol=1e-12):
                    raise ValueError("Accepted native constant volume changed")
                if reactor.mass <= minimum_inventory_kg:
                    raise ValueError("Finite gas inventory reached its declared minimum")
                snapshots.append(_snapshot(time, reactor))
                integrals.append(reactor.ledger.copy())
        except Exception as exc:
            raise GasVolumeIntegrationError(f"Native open-volume integration failed: {exc}",
                                            boundary_objects) from exc
        integrals = np.array(integrals)*ledger_scales
        masses = np.array([s.mass_kg for s in snapshots])
        species_mass = np.array([[s.mass_kg*s.mass_fractions[k] for k in species]
                                 for s in snapshots])
        energy = np.array([s.internal_energy_j for s in snapshots])
        net_mass = integrals[:, :nf].sum(axis=1)-integrals[:, nf:nf+nv].sum(axis=1)
        mass_residual = masses-masses[0]-net_mass
        reaction_integrals = (integrals[:, reaction_start:reaction_start+ns] if reactive
                              else np.zeros_like(species_mass))
        boundary_species = integrals[:, species_start:species_start+ns]
        species_residual = species_mass-species_mass[0]-boundary_species-reaction_integrals
        element_mass = species_mass @ element_fractions.T
        element_residual = element_mass-element_mass[0]-boundary_species @ element_fractions.T
        energy_residual = energy-energy[0]-integrals[:, -3]+integrals[:, -2]-integrals[:, -1]
        return GasVolumeTrace(basis, fingerprint, clock_id, species, times, tuple(snapshots),
            labels, ("kg",)*(len(labels)-3)+("J",)*3, ledger_scales, integrals, mass_residual,
            species_residual, energy_residual, boundary_objects, tuple(feeds), tuple(vents),
            tuple(heat_boundaries), tuple(evaluated) if evaluated else None,
            chemistry=self.chemistry, reaction_species_integrals_kg=reaction_integrals,
            element_names=elements, element_residual_kg=element_residual,
            definition_guard=("private-native-clones-and-accepted-output" if private_phases
                              else "every-native-RHS"),
            source_phase_fingerprint=source_fingerprint, phase_copy_audits=tuple(copy_audits))
