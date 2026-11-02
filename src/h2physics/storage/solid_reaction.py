"""Finite forward solid-reaction schedules through existing thermochemical kernels.

Development status: implemented_unverified; execution is deferred to the HPC
validation cases. No hydride parameters, kinetic law or liquid-water property
database is supplied. Fixed-P additive phase enthalpy is the thermal boundary.
"""

import math
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from types import MappingProxyType

import numpy as np
from scipy.optimize import brentq

from ..core import Origin, finite, immutable_array
from ..reactions import MolarEnthalpyProvider, StoichiometricReaction
from ..thermochemical import (
    FiniteThermochemicalCycle,
    PrescribedConversion,
    ThermochemicalEvidence,
    ThermochemicalFeed,
    ThermochemicalInventory,
    ThermochemicalStage,
    ThermochemicalTolerances,
    ThermochemicalTrace,
)

STATUS = "implemented_unverified"
_PENDING_TRACE_ISSUERS: set[object] = set()


def _issue_reaction_trace(*args, **values):
    token = object()
    _PENDING_TRACE_ISSUERS.add(token)
    try:
        return SolidReactionTrace(*args, **values, _issuer_token=token)
    except Exception:
        _PENDING_TRACE_ISSUERS.discard(token)
        raise


def _ids(*values):
    if any(not isinstance(v, str) or not v.strip() for v in values):
        raise ValueError("Declare process, source, clock, phase and reference identities")


def _amounts(values):
    result = dict(values)
    for name, value in result.items():
        _ids(name)
        result[name] = finite(value, "finite species amount mol")
        if result[name] < 0:
            raise ValueError("Finite amounts cannot be negative")
    return MappingProxyType(result)


def _array(value):
    result = np.array(value, dtype=float, copy=True)
    if not np.all(np.isfinite(result)):
        raise ValueError("Solid-reaction audit arrays must be finite")
    return immutable_array(result, name="solid-reaction audit array")


def _sum(values, label):
    try:
        return finite(math.fsum(float(v) for v in values), label)
    except OverflowError as error:
        raise ValueError(f"{label} exceeds finite arithmetic") from error


def _inventory(value):
    if not isinstance(value, ThermochemicalInventory):
        raise TypeError("Supply an actual ThermochemicalInventory")
    return ThermochemicalInventory(
        value.amounts_mol, value.temperature_k, value.pressure_pa, value.energy_basis_id
    )


@dataclass(frozen=True, slots=True)
class SolidReactionEvidence:
    process_id: str
    stoichiometry_source_id: str
    caloric_basis_id: str
    common_temperature_assumption_id: str
    fixed_pressure_boundary_id: str
    component_takeoff_assumption_id: str
    origin: Origin

    def __post_init__(self):
        _ids(
            self.process_id,
            self.stoichiometry_source_id,
            self.caloric_basis_id,
            self.common_temperature_assumption_id,
            self.fixed_pressure_boundary_id,
            self.component_takeoff_assumption_id,
        )
        object.__setattr__(self, "origin", Origin(self.origin))
        if self.origin == Origin.UNRESOLVED:
            raise ValueError("Resolve the declared operating assumptions or use synthetic evidence")


@dataclass(frozen=True, slots=True)
class SolidRateState:
    time_s: float
    clock_id: str
    inventory: ThermochemicalInventory
    accumulated_extent_mol: float
    forward_extent_limit_mol: float


@dataclass(frozen=True, slots=True)
class SolidReactionKinetics:
    """Caller rate in mol extent/s, evaluated once after beginning-of-step mixing.

    Parameters are explicit immutable scalars. Neither their units nor their
    material applicability are inferred; the source identity must describe them.
    """

    reaction: StoichiometricReaction
    rate: Callable[[SolidRateState, Mapping[str, float]], float]
    identifier: str
    source_id: str
    origin: Origin
    parameters: Mapping[str, float] = field(default_factory=dict)

    def __post_init__(self):
        if not isinstance(self.reaction, StoichiometricReaction) or not callable(self.rate):
            raise TypeError("Supply an existing balanced reaction and explicit kinetic callable")
        _ids(self.identifier, self.source_id)
        parameters = dict(self.parameters)
        for key, value in parameters.items():
            _ids(key)
            parameters[key] = finite(value, "explicit kinetic parameter")
        object.__setattr__(self, "parameters", MappingProxyType(parameters))
        object.__setattr__(self, "origin", Origin(self.origin))
        if self.origin == Origin.UNRESOLVED:
            raise ValueError(
                "A kinetic callback needs resolved source or synthetic fixture identity"
            )


@dataclass(frozen=True, slots=True)
class SolidSupply:
    identifier: str
    inventory: ThermochemicalInventory
    source_id: str
    origin: Origin

    def __post_init__(self):
        _ids(self.identifier, self.source_id)
        object.__setattr__(self, "inventory", _inventory(self.inventory))
        object.__setattr__(self, "origin", Origin(self.origin))
        if self.origin == Origin.UNRESOLVED:
            raise ValueError("A finite supply needs an explicit source role")


@dataclass(frozen=True, slots=True)
class SolidFeedDraw:
    supply_id: str
    amounts_mol: Mapping[str, float]

    def __post_init__(self):
        _ids(self.supply_id)
        object.__setattr__(self, "amounts_mol", _amounts(self.amounts_mol))


@dataclass(frozen=True, slots=True)
class SolidReactionStep:
    """Packet operations at start/end, with an explicit frozen-rate middle step.

    ``limit_policy='truncate'`` explicitly admits inventory-limited extent and
    records it; ``'reject'`` refuses an overlarge kinetic time step.
    """

    identifier: str
    start_s: float
    end_s: float
    clock_id: str
    heat_input_j: float
    temperature_bracket_k: tuple[float, float]
    evidence_id: str
    feeds: tuple[SolidFeedDraw, ...] = ()
    pre_withdrawal_mol: Mapping[str, float] = field(default_factory=dict)
    post_withdrawal_mol: Mapping[str, float] = field(default_factory=dict)
    limit_policy: str = "reject"

    def __post_init__(self):
        _ids(self.identifier, self.clock_id, self.evidence_id)
        if finite(self.start_s, "step start") >= finite(self.end_s, "step end"):
            raise ValueError("Use an increasing explicit physical-seconds interval")
        finite(self.heat_input_j, "supplied heat J; positive enters reactor")
        bracket = tuple(self.temperature_bracket_k)
        if len(bracket) != 2 or not 0 < bracket[0] < bracket[1] < math.inf:
            raise ValueError("Declare a positive increasing temperature bracket")
        finite(bracket[0], "temperature bracket lower", positive=True)
        finite(bracket[1], "temperature bracket upper", positive=True)
        object.__setattr__(self, "temperature_bracket_k", bracket)
        object.__setattr__(self, "feeds", tuple(self.feeds))
        if not all(isinstance(v, SolidFeedDraw) for v in self.feeds):
            raise TypeError("Use explicit finite reservoir draws")
        object.__setattr__(
            self, "feeds", tuple(SolidFeedDraw(v.supply_id, v.amounts_mol) for v in self.feeds)
        )
        for name in ("pre_withdrawal_mol", "post_withdrawal_mol"):
            object.__setattr__(self, name, _amounts(getattr(self, name)))
        if self.limit_policy not in {"reject", "truncate"}:
            raise ValueError("Choose explicit reject or truncate finite-extent policy")


@dataclass(frozen=True, slots=True)
class SolidTemperatureTrial:
    temperature_k: float
    required_heat_j: float
    residual_j: float
    kernel_trace: ThermochemicalTrace


@dataclass(frozen=True, slots=True)
class SolidThermalSolve:
    kernel_trace: ThermochemicalTrace
    trials: tuple[SolidTemperatureTrial, ...]
    scipy_root_result: object | None
    supplied_heat_j: float
    heat_residual_j: float


@dataclass(frozen=True, slots=True)
class SolidReactionStepResult:
    step: SolidReactionStep
    before: ThermochemicalInventory
    mixed: ThermochemicalInventory
    after: ThermochemicalInventory
    rate_state: SolidRateState
    rate_mol_extent_s: float
    requested_extent_mol: float
    accepted_extent_mol: float
    inventory_limited: bool
    limiting_species: tuple[str, ...]
    mixing: SolidThermalSolve | None
    reaction: SolidThermalSolve
    takeoff: ThermochemicalTrace | None
    hydrogen_generated_mol: float
    feed_mol: np.ndarray
    removed_mol: np.ndarray
    feed_enthalpy_j: float
    removed_enthalpy_j: float

    def __post_init__(self):
        for name in ("feed_mol", "removed_mol"):
            object.__setattr__(self, name, _array(getattr(self, name)))


@dataclass(frozen=True, slots=True)
class SolidReactionTrace:
    initial: ThermochemicalInventory
    final: ThermochemicalInventory
    initial_supplies: tuple[SolidSupply, ...]
    remaining_supplies: tuple[SolidSupply, ...]
    steps: tuple[SolidReactionStepResult, ...]
    species: tuple
    elements: tuple[str, ...]
    exported_mol: np.ndarray
    exported_enthalpy_j: float
    hydrogen_generated_mol: float
    heat_input_j: float
    element_residual_mol: np.ndarray
    mass_residual_kg: float
    enthalpy_residual_j: float
    evidence: SolidReactionEvidence
    kinetics: SolidReactionKinetics
    enthalpy_provider: object
    kernel: FiniteThermochemicalCycle
    _issuer_token: object = field(default=None, repr=False, compare=False)

    def __post_init__(self):
        token = self._issuer_token
        if token not in _PENDING_TRACE_ISSUERS:
            raise ValueError("Use FiniteSolidReactionReactor.run() to issue a reaction trace")
        _PENDING_TRACE_ISSUERS.remove(token)
        object.__setattr__(self, "_issuer_token", None)
        for name in ("exported_mol", "element_residual_mol"):
            object.__setattr__(self, name, _array(getattr(self, name)))


class SolidReactionError(ValueError):
    """Actual failed context, original cause and completed prefix remain available."""

    def __init__(
        self,
        message,
        *,
        initial=None,
        current=None,
        step=None,
        phase=None,
        completed_steps=(),
        remaining_supplies=(),
        rate_state=None,
        raw_rate=None,
        requested_extent_mol=None,
        accepted_extent_mol=None,
        trials=(),
        failed_kernel=None,
        failed_step=None,
        trial_supplies=(),
        trace=None,
        provider=None,
        element_residual_mol=None,
        mass_residual_kg=None,
        enthalpy_residual_j=None,
    ):
        self.initial, self.current, self.step, self.phase = initial, current, step, phase
        self.completed_steps = tuple(completed_steps)
        self.remaining_supplies = tuple(remaining_supplies)
        self.rate_state, self.raw_rate = rate_state, raw_rate
        self.requested_extent_mol, self.accepted_extent_mol = (
            requested_extent_mol,
            accepted_extent_mol,
        )
        self.trials, self.failed_kernel, self.trace = tuple(trials), failed_kernel, trace
        self.failed_step, self.trial_supplies = failed_step, tuple(trial_supplies)
        self.provider = provider
        self.element_residual_mol = (
            None if element_residual_mol is None else _array(element_residual_mol))
        self.mass_residual_kg = mass_residual_kg
        self.enthalpy_residual_j = enthalpy_residual_j
        super().__init__(message)


class FiniteSolidReactionReactor:
    """One forward reaction, common T and externally maintained constant P.

    The existing thermochemical kernel owns every phase caloric/material step.
    This class adds finite supply debits, frozen-start-rate time discretization,
    optional declared limiting-reactant truncation and thermal root assembly.
    It predicts no equilibrium, gas EOS, volume, separation or intrinsic rate.
    """

    def __init__(
        self,
        enthalpy: MolarEnthalpyProvider,
        kinetics: SolidReactionKinetics,
        evidence: SolidReactionEvidence,
        *,
        hydrogen_species: str,
        mode: str,
        water_species: str | None = None,
        tolerances: ThermochemicalTolerances = ThermochemicalTolerances(),
        maximum_temperature_iterations: int = 100,
    ):
        if not isinstance(kinetics, SolidReactionKinetics) or not isinstance(
            evidence, SolidReactionEvidence
        ):
            raise TypeError("Declare actual kinetic and physical-assumption evidence objects")
        # Re-run the shared elemental/charge/mass admission on actual fields.
        reaction = StoichiometricReaction(
            kinetics.reaction.identifier, kinetics.reaction.species, kinetics.reaction.coefficients
        )
        if (
            tuple(enthalpy.species) != reaction.species
            or evidence.caloric_basis_id != enthalpy.basis_id
        ):
            raise ValueError(
                "Reaction phase/species/order and caloric formation reference must match"
            )
        if not isinstance(tolerances, ThermochemicalTolerances):
            raise TypeError("Use explicit shared thermochemical audit tolerances")
        if (
            isinstance(maximum_temperature_iterations, bool)
            or not isinstance(maximum_temperature_iterations, int)
            or maximum_temperature_iterations < 2
        ):
            raise ValueError("Declare at least two bounded thermal root iterations")
        names = tuple(s.identifier for s in reaction.species)
        if hydrogen_species not in names:
            raise ValueError("Identify the actual generated H2 species")
        index = names.index(hydrogen_species)
        hydrogen = reaction.species[index]
        if (
            dict(hydrogen.elements) != {"H": 2}
            or hydrogen.charge != 0
            or not (
                hydrogen.phase.lower() in {"gas", "ideal-gas"}
                or hydrogen.phase.lower().startswith("gas:")
            )
            or reaction.coefficients[index] <= 0
        ):
            raise ValueError(
                "The named product must be neutral gas-phase H2 with positive coefficient"
            )
        if not any(
            (s.phase.lower() == "solid" or s.phase.lower().startswith("solid:")) and v < 0
            for s, v in zip(reaction.species, reaction.coefficients, strict=True)
        ):
            raise ValueError(
                "Declare a consumed solid phase; liquid carriers use their existing model"
            )
        if mode not in {"decomposition", "hydrolysis"}:
            raise ValueError("Declare decomposition or hydrolysis explicitly")
        water_reactants = tuple(
            s.identifier
            for s, v in zip(reaction.species, reaction.coefficients, strict=True)
            if dict(s.elements) == {"H": 2, "O": 1} and s.charge == 0 and v < 0
        )
        if mode == "hydrolysis":
            if water_reactants != (water_species,):
                raise ValueError(
                    "Identify the single consumed water phase explicitly for hydrolysis"
                )
        elif water_species is not None or water_reactants:
            raise ValueError("Water-consuming chemistry must use explicit hydrolysis mode")
        kernel_evidence = ThermochemicalEvidence(
            evidence.process_id,
            evidence.common_temperature_assumption_id,
            evidence.component_takeoff_assumption_id,
            evidence.fixed_pressure_boundary_id,
            evidence.origin,
        )
        self.enthalpy, self.kinetics, self.evidence = enthalpy, kinetics, evidence
        self.kernel = FiniteThermochemicalCycle(enthalpy, kernel_evidence, tolerances=tolerances)
        self.species, self.names, self.reaction = reaction.species, names, reaction
        self.hydrogen_species, self.mode, self.water_species = hydrogen_species, mode, water_species
        self.tolerances, self.maximum_temperature_iterations = (
            tolerances,
            maximum_temperature_iterations,
        )
        self.elements = tuple(sorted({e for s in self.species for e in s.elements}))
        self._atoms = _array([[s.elements.get(e, 0) for s in self.species] for e in self.elements])
        self._mass = _array([s.molar_mass_kg_mol for s in self.species])
        self._bound = (enthalpy, kinetics, evidence, self.kernel, kinetics.rate)
        self._species_signature = self._signature(self.species)
        self._coefficients = tuple(reaction.coefficients)
        self._basis = evidence.caloric_basis_id
        self._parameters = tuple(kinetics.parameters.items())
        self._model_labels = (names, hydrogen_species, mode, water_species)
        self._evidence_fields = tuple(
            getattr(evidence, name) for name in evidence.__dataclass_fields__
        )
        self._law_labels = (
            kinetics.identifier,
            kinetics.source_id,
            kinetics.origin,
            reaction.identifier,
        )
        self._settings = (
            maximum_temperature_iterations,
            tuple(getattr(tolerances, name) for name in tolerances.__dataclass_fields__),
        )

    @staticmethod
    def _signature(species):
        return tuple(
            (
                s.identifier,
                tuple(sorted(s.elements.items())),
                s.molar_mass_kg_mol,
                s.phase,
                s.charge,
            )
            for s in species
        )

    def _require_binding(self):
        if (
            self.enthalpy is not self._bound[0]
            or self.kinetics is not self._bound[1]
            or self.evidence is not self._bound[2]
            or self.kernel is not self._bound[3]
            or self.kinetics.rate is not self._bound[4]
            or self.kernel.enthalpy is not self.enthalpy
            or self.enthalpy.basis_id != self._basis
            or self.evidence.caloric_basis_id != self._basis
            or self._signature(tuple(self.enthalpy.species)) != self._species_signature
            or self._signature(self.kinetics.reaction.species) != self._species_signature
            or self._signature(self.reaction.species) != self._species_signature
            or self._signature(self.species) != self._species_signature
            or (self.names, self.hydrogen_species, self.mode, self.water_species)
            != self._model_labels
            or tuple(self.reaction.coefficients) != self._coefficients
            or tuple(self.kinetics.reaction.coefficients) != self._coefficients
            or tuple(self.kinetics.parameters.items()) != self._parameters
            or tuple(getattr(self.evidence, n) for n in self.evidence.__dataclass_fields__)
            != self._evidence_fields
            or (
                self.kinetics.identifier,
                self.kinetics.source_id,
                self.kinetics.origin,
                self.kinetics.reaction.identifier,
            )
            != self._law_labels
            or (
                self.maximum_temperature_iterations,
                tuple(getattr(self.tolerances, n) for n in self.tolerances.__dataclass_fields__),
            )
            != self._settings
            or self.kernel.tolerances is not self.tolerances
        ):
            raise ValueError(
                "Reaction/provider/kinetic binding changed; construct a newly evidenced model"
            )

    def _state(self, inventory, pressure):
        value = _inventory(inventory)
        if value.energy_basis_id != self._basis or value.pressure_pa != pressure:
            raise ValueError("Reservoir/reactor reference or imposed absolute pressure differs")
        self.reaction.amounts(value.amounts_mol)
        return value

    def _enthalpy(self, inventory):
        self._require_binding()
        # Shared kernel copies and checks provider scratch arrays and bindings.
        h = self.kernel._h(inventory.temperature_k, inventory.pressure_pa)
        return _sum(self.reaction.amounts(inventory.amounts_mol) * h, "finite inventory enthalpy")

    def _thermal(self, initial, command, heat, trials):
        """Temperature root wraps the existing finite-stage heat ledger unchanged."""

        def at(temperature):
            self._require_binding()
            stage = ThermochemicalStage(
                command.identifier,
                command.start_s,
                command.end_s,
                command.clock_id,
                temperature,
                command.conversions,
                command.evidence_id,
                command.feeds,
                command.pre_withdrawal_mol,
            )
            trace = self.kernel.run(
                initial,
                (stage,),
                carrier_species=(self.names[0],),
                require_carrier_closed=False,
                require_temperature_closed=False,
            )
            residual = finite(trace.net_heat_required_j - heat, "thermal residual")
            trial = SolidTemperatureTrial(temperature, trace.net_heat_required_j, residual, trace)
            trials.append(trial)
            self._require_binding()
            return residual

        lower, upper = command._temperature_bracket
        root, result = brentq(
            at,
            lower,
            upper,
            xtol=self.tolerances.temperature_k,
            rtol=4 * np.finfo(float).eps,
            maxiter=self.maximum_temperature_iterations,
            full_output=True,
            disp=True,
        )
        at(root)  # Retain the actual endpoint kernel/native provider query.
        last = trials[-1]
        budget = finite(
            self.tolerances.energy_j
            + self.tolerances.relative
            * max(abs(heat), abs(last.kernel_trace.steps[0].before_enthalpy_j), 1.0),
            "thermal acceptance budget",
            positive=True,
        )
        if abs(last.residual_j) > budget or not result.converged:
            raise ValueError(
                "Supplied heat and solved endpoint temperature fail the declared budget"
            )
        return SolidThermalSolve(last.kernel_trace, tuple(trials), result, heat, last.residual_j)

    def _command(self, step, suffix, *, conversions=(), feeds=(), withdrawal=None):
        # ThermochemicalStage is frozen: the independent bracket stays in an
        # original assembly record rather than being attached to native objects.
        return _ThermalCommand(
            step.identifier + ":" + suffix,
            step.start_s,
            step.end_s,
            step.clock_id,
            step.evidence_id,
            tuple(conversions),
            tuple(feeds),
            {} if withdrawal is None else withdrawal,
            step.temperature_bracket_k,
        )

    def run(self, initial: ThermochemicalInventory, steps, *, supplies=()) -> SolidReactionTrace:
        self._require_binding()
        initial = _inventory(initial)
        initial = self._state(initial, initial.pressure_pa)
        schedule = tuple(steps)
        if not schedule or not all(isinstance(s, SolidReactionStep) for s in schedule):
            raise ValueError("Supply a nonempty explicit SolidReactionStep schedule")
        # Revalidate frozen objects as supplied, including nested transfer maps.
        schedule = tuple(
            SolidReactionStep(**{n: getattr(s, n) for n in s.__dataclass_fields__})
            for s in schedule
        )
        if len({s.identifier for s in schedule}) != len(schedule):
            raise ValueError("Step identities must be unique")
        for step in schedule:
            self.reaction.amounts(step.pre_withdrawal_mol)
            self.reaction.amounts(step.post_withdrawal_mol)
        for left, right in zip(schedule[:-1], schedule[1:], strict=True):
            if left.end_s != right.start_s or left.clock_id != right.clock_id:
                raise ValueError("Use contiguous steps on one explicitly identified clock")
        donors = {}
        for supply in supplies:
            if not isinstance(supply, SolidSupply) or supply.identifier in donors:
                raise ValueError("Declare uniquely identified actual finite supplies")
            donors[supply.identifier] = SolidSupply(
                supply.identifier,
                self._state(supply.inventory, initial.pressure_pa),
                supply.source_id,
                supply.origin,
            )
        original_supplies = tuple(donors.values())
        current, completed = initial, []
        self._enthalpy(initial)
        for donor in original_supplies:
            self._enthalpy(donor.inventory)
        accumulated, exported_h, supplied_heat = 0.0, 0.0, 0.0
        exported = np.zeros(len(self.species))
        for step in schedule:
            phase, state, raw_rate, requested, accepted = "admission", None, None, None, None
            trials, mixing, takeoff, result = [], None, None, None
            trial_donors, before = dict(donors), current
            try:
                self._require_binding()
                phase, feeds = "finite-feed", []
                for draw in step.feeds:
                    if draw.supply_id not in trial_donors:
                        raise ValueError("Feed refers to an undeclared finite supply")
                    donor = trial_donors[draw.supply_id]
                    n = self.reaction.amounts(draw.amounts_mol)
                    remaining = self.reaction.amounts(donor.inventory.amounts_mol) - n
                    if np.any(remaining < 0):
                        raise ValueError("Feed draw exceeds its actual remaining finite supply")
                    feed_inventory = ThermochemicalInventory(
                        draw.amounts_mol,
                        donor.inventory.temperature_k,
                        initial.pressure_pa,
                        self._basis,
                    )
                    feeds.append(ThermochemicalFeed(feed_inventory, donor.source_id, donor.origin))
                    trial_donors[draw.supply_id] = SolidSupply(
                        donor.identifier,
                        ThermochemicalInventory(
                            dict(zip(self.names, remaining, strict=True)),
                            donor.inventory.temperature_k,
                            initial.pressure_pa,
                            self._basis,
                        ),
                        donor.source_id,
                        donor.origin,
                    )
                phase = "beginning-withdrawal-and-adiabatic-mixing"
                if feeds or any(step.pre_withdrawal_mol.values()):
                    mixing = self._thermal(
                        before,
                        self._command(step, "mix", feeds=feeds, withdrawal=step.pre_withdrawal_mol),
                        0.0,
                        trials,
                    )
                    mixed = mixing.kernel_trace.final
                else:
                    mixed = before
                phase = "kinetics"
                upper = self.reaction.extent_limits_mol(mixed.amounts_mol)[1]
                state = SolidRateState(step.start_s, step.clock_id, mixed, accumulated, upper)
                raw_rate = self.kinetics.rate(state, self.kinetics.parameters)
                rate = finite(raw_rate, "forward rate mol extent/s")
                self._require_binding()
                if rate < 0:
                    raise ValueError("This forward-only solid law rejects reverse kinetic rates")
                requested = finite(rate * (step.end_s - step.start_s), "requested kinetic extent")
                limited = requested > upper
                if limited and step.limit_policy == "reject":
                    raise ValueError(
                        "Kinetic step exceeds finite reactants; refine or explicitly truncate"
                    )
                accepted = upper if limited else requested
                limiting = tuple(
                    s.identifier
                    for s, v in zip(self.species, self._coefficients, strict=True)
                    if v < 0 and mixed.amounts_mol.get(s.identifier, 0.0) / -v == upper
                )
                phase, trials = "reaction-and-thermal-root", []
                thermal = self._thermal(
                    mixed,
                    self._command(
                        step,
                        "reaction",
                        conversions=(
                            PrescribedConversion(self.reaction, accepted, step.evidence_id),
                        ),
                    ),
                    step.heat_input_j,
                    trials,
                )
                after = thermal.kernel_trace.final
                phase = "endpoint-component-takeoff"
                if any(step.post_withdrawal_mol.values()):
                    takeoff = self.kernel.run(
                        after,
                        (
                            ThermochemicalStage(
                                step.identifier + ":takeoff",
                                step.start_s,
                                step.end_s,
                                step.clock_id,
                                after.temperature_k,
                                (),
                                step.evidence_id,
                                pre_withdrawal_mol=step.post_withdrawal_mol,
                            ),
                        ),
                        carrier_species=(self.names[0],),
                        require_carrier_closed=False,
                        require_temperature_closed=False,
                    )
                    after = takeoff.final
                traces = tuple(
                    t
                    for t in (
                        None if mixing is None else mixing.kernel_trace,
                        thermal.kernel_trace,
                        takeoff,
                    )
                    if t is not None
                )
                feed = np.sum([t.feed_mol for t in traces], axis=0)
                removed = np.sum([t.exported_mol for t in traces], axis=0)
                feed_h = _sum((s.feed_enthalpy_j for t in traces for s in t.steps), "feed enthalpy")
                removed_h = _sum(
                    (s.withdrawn_enthalpy_j for t in traces for s in t.steps), "removed enthalpy"
                )
                generated = finite(
                    accepted * self._coefficients[self.names.index(self.hydrogen_species)],
                    "generated H2 mol",
                )
                result = SolidReactionStepResult(
                    step,
                    before,
                    mixed,
                    after,
                    state,
                    rate,
                    requested,
                    accepted,
                    limited,
                    limiting,
                    mixing,
                    thermal,
                    takeoff,
                    generated,
                    feed,
                    removed,
                    feed_h,
                    removed_h,
                )
                self._require_binding()
                # A failed step never commits partially debited supply packets.
                next_accumulated = _sum((accumulated, accepted), "cumulative reaction extent")
                next_exported = _array(exported + removed)
                next_exported_h = _sum((exported_h, removed_h), "cumulative exported enthalpy")
                next_heat = _sum((supplied_heat, step.heat_input_j), "cumulative supplied heat")
                current, donors = after, trial_donors
                completed.append(result)
                accumulated, exported, exported_h, supplied_heat = (
                    next_accumulated,
                    next_exported,
                    next_exported_h,
                    next_heat,
                )
            except Exception as error:
                raise SolidReactionError(
                    f"Solid-reaction step {step.identifier} failed in {phase}: {error}",
                    initial=initial,
                    current=before,
                    step=step,
                    phase=phase,
                    completed_steps=completed,
                    remaining_supplies=donors.values(),
                    rate_state=state,
                    raw_rate=raw_rate,
                    requested_extent_mol=requested,
                    accepted_extent_mol=accepted,
                    trials=trials,
                    failed_kernel=error,
                    failed_step=result,
                    trial_supplies=trial_donors.values(),
                    provider=self.enthalpy,
                ) from error
        trace = None
        element = mass = residual = None
        try:
            phase = "whole-finite-system-audit"
            initial_n = self.reaction.amounts(initial.amounts_mol)
            final_n = self.reaction.amounts(current.amounts_mol)
            for donor in original_supplies:
                initial_n = initial_n + self.reaction.amounts(donor.inventory.amounts_mol)
            for donor in donors.values():
                final_n = final_n + self.reaction.amounts(donor.inventory.amounts_mol)
            defect = _array(final_n + exported - initial_n)
            element = _array(self._atoms @ defect)
            mass = _sum(defect * self._mass, "whole-system mass residual")
            initial_h = _sum(
                [self._enthalpy(initial)]
                + [self._enthalpy(d.inventory) for d in original_supplies],
                "initial reactor and supplies enthalpy",
            )
            final_h = _sum(
                [self._enthalpy(current)] + [self._enthalpy(d.inventory) for d in donors.values()],
                "final reactor and supplies enthalpy",
            )
            residual = _sum(
                (final_h, exported_h, -initial_h, -supplied_heat), "whole-system enthalpy residual"
            )
            self.kernel._check_balance(
                element,
                mass,
                residual,
                _sum(initial_n, "initial mol scale"),
                max(abs(initial_h), abs(final_h), abs(exported_h), abs(supplied_heat)),
            )
            self._require_binding()
            trace = _issue_reaction_trace(
                initial,
                current,
                original_supplies,
                tuple(donors.values()),
                tuple(completed),
                self.species,
                self.elements,
                exported,
                exported_h,
                _sum((s.hydrogen_generated_mol for s in completed), "generated H2"),
                supplied_heat,
                element,
                mass,
                residual,
                self.evidence,
                self.kinetics,
                self.enthalpy,
                self.kernel,
            )
            return trace
        except Exception as error:
            raise SolidReactionError(
                f"Solid-reaction whole-system audit failed: {error}",
                initial=initial,
                current=current,
                phase=phase,
                completed_steps=completed,
                remaining_supplies=donors.values(),
                trace=trace,
                provider=self.enthalpy,
                element_residual_mol=element,
                mass_residual_kg=mass,
                enthalpy_residual_j=residual,
            ) from error


@dataclass(frozen=True, slots=True)
class _ThermalCommand:
    identifier: str
    start_s: float
    end_s: float
    clock_id: str
    evidence_id: str
    conversions: tuple
    feeds: tuple
    pre_withdrawal_mol: Mapping
    _temperature_bracket: tuple[float, float]
