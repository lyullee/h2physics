"""Finite staged thermochemical inventories through the shared reaction core.

Extents and endpoint temperatures are supplied operating constraints. The
model predicts neither equilibrium, conversion kinetics, a separator nor utility
availability. Public context: https://www.energy.gov/cmei/fuels/hydrogen-production-thermochemical-water-splitting
"""

import math
from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType

import numpy as np

from .core import Origin, finite, immutable_array
from .reactions import (
    MolarEnthalpyProvider,
    ReactionConversion,
    StoichiometricReaction,
    conversion_heat_j,
)


def _ids(*values):
    if any(not isinstance(v, str) or not v.strip() for v in values):
        raise ValueError(
            "Declare stage, clock, material/reference and boundary evidence identities"
        )


def _amounts(values):
    amounts = dict(values)
    for name, amount in amounts.items():
        _ids(name)
        if finite(amount, "finite species amount mol") < 0:
            raise ValueError("Finite species amounts cannot be negative")
    return MappingProxyType({name: float(value) for name, value in amounts.items()})


def _array(value):
    result = np.array(value, dtype=float, copy=True)
    if not np.all(np.isfinite(result)):
        raise ValueError("Finite stage arrays cannot contain nonfinite values")
    return immutable_array(result, name="thermochemical array")


def _sum(values, name):
    try:
        result = math.fsum(float(value) for value in values)
    except OverflowError as error:
        raise ValueError(f"{name} exceeds finite numerical storage") from error
    return finite(result, name)


def _dot(amounts, properties, name):
    return _sum(
        (finite(float(n) * float(h), name) for n, h in zip(amounts, properties, strict=True)), name
    )


@dataclass(frozen=True, slots=True)
class ThermochemicalInventory:
    amounts_mol: Mapping[str, float]
    temperature_k: float
    pressure_pa: float
    energy_basis_id: str

    def __post_init__(self):
        object.__setattr__(self, "amounts_mol", _amounts(self.amounts_mol))
        finite(self.temperature_k, "inventory temperature", positive=True)
        finite(self.pressure_pa, "inventory absolute pressure", positive=True)
        _ids(self.energy_basis_id)


@dataclass(frozen=True, slots=True)
class ThermochemicalFeed:
    inventory: ThermochemicalInventory
    source_id: str
    origin: Origin

    def __post_init__(self):
        _ids(self.source_id)
        object.__setattr__(self, "origin", Origin(self.origin))
        if self.origin == Origin.UNRESOLVED:
            raise ValueError("A finite feed needs resolved source meaning")


@dataclass(frozen=True, slots=True)
class PrescribedConversion:
    reaction: StoichiometricReaction
    extent_mol: float
    evidence_id: str

    def __post_init__(self):
        finite(self.extent_mol, "prescribed reaction extent")
        _ids(self.evidence_id)


@dataclass(frozen=True, slots=True)
class ThermochemicalStage:
    identifier: str
    start_s: float
    end_s: float
    clock_id: str
    endpoint_temperature_k: float
    conversions: tuple[PrescribedConversion, ...]
    evidence_id: str
    feeds: tuple[ThermochemicalFeed, ...] = ()
    pre_withdrawal_mol: Mapping[str, float] = field(default_factory=dict)

    def __post_init__(self):
        _ids(self.identifier, self.clock_id, self.evidence_id)
        if finite(self.start_s, "stage start") >= finite(self.end_s, "stage end"):
            raise ValueError("A stage requires an increasing finite time window")
        finite(self.endpoint_temperature_k, "prescribed endpoint temperature", positive=True)
        object.__setattr__(self, "conversions", tuple(self.conversions))
        object.__setattr__(self, "feeds", tuple(self.feeds))
        object.__setattr__(self, "pre_withdrawal_mol", _amounts(self.pre_withdrawal_mol))
        if not all(isinstance(c, PrescribedConversion) for c in self.conversions) or not all(
            isinstance(f, ThermochemicalFeed) for f in self.feeds
        ):
            raise TypeError("Supply explicit prescribed-conversion and finite-feed objects")


@dataclass(frozen=True, slots=True)
class ThermochemicalEvidence:
    process_id: str
    additive_phase_caloric_assumption_id: str
    component_withdrawal_assumption_id: str
    thermal_boundary_assumption_id: str
    origin: Origin

    def __post_init__(self):
        _ids(
            self.process_id,
            self.additive_phase_caloric_assumption_id,
            self.component_withdrawal_assumption_id,
            self.thermal_boundary_assumption_id,
        )
        object.__setattr__(self, "origin", Origin(self.origin))
        if self.origin == Origin.UNRESOLVED:
            raise ValueError("Resolve the thermochemical operating assumptions")


@dataclass(frozen=True, slots=True)
class ThermochemicalTolerances:
    amount_mol: float = 1e-10
    mass_kg: float = 1e-12
    energy_j: float = 1e-6
    temperature_k: float = 1e-9
    relative: float = 1e-10

    def __post_init__(self):
        for name in self.__dataclass_fields__:
            finite(getattr(self, name), name, positive=True)


@dataclass(frozen=True, slots=True)
class ThermochemicalStageResult:
    stage: ThermochemicalStage
    before: ThermochemicalInventory
    after: ThermochemicalInventory
    conversions: tuple[ReactionConversion, ...]
    feed_mol: np.ndarray
    withdrawn_mol: np.ndarray
    feed_enthalpy_j: float
    withdrawn_enthalpy_j: float
    before_enthalpy_j: float
    after_enthalpy_j: float
    conditioning_heat_required_j: float
    reaction_heat_required_j: float
    heat_required_j: float
    energy_residual_j: float
    element_residual_mol: np.ndarray
    mass_residual_kg: float

    def __post_init__(self):
        for name in ("feed_mol", "withdrawn_mol", "element_residual_mol"):
            object.__setattr__(self, name, _array(getattr(self, name)))

    @property
    def mean_required_heat_w(self):
        return self.heat_required_j / (self.stage.end_s - self.stage.start_s)


@dataclass(frozen=True, slots=True)
class ThermochemicalTrace:
    initial: ThermochemicalInventory
    final: ThermochemicalInventory
    steps: tuple[ThermochemicalStageResult, ...]
    species: tuple
    elements: tuple[str, ...]
    feed_mol: np.ndarray
    exported_mol: np.ndarray
    element_residual_mol: np.ndarray
    mass_residual_kg: float
    net_heat_required_j: float
    gross_heat_input_j: float
    gross_heat_rejection_j: float
    energy_residual_j: float
    carrier_species: tuple[str, ...]
    carrier_residual_mol: np.ndarray
    carrier_closed: bool
    temperature_closed: bool
    full_inventory_closed: bool
    evidence: ThermochemicalEvidence
    enthalpy_provider: object

    def __post_init__(self):
        for name in ("feed_mol", "exported_mol", "element_residual_mol", "carrier_residual_mol"):
            object.__setattr__(self, name, _array(getattr(self, name)))


class ThermochemicalCycleError(ValueError):
    def __init__(
        self,
        message,
        *,
        stage=None,
        before=None,
        completed_steps=(),
        partial_conversions=(),
        failed_step=None,
        trace=None,
        provider=None,
    ):
        self.stage, self.before = stage, before
        self.completed_steps, self.partial_conversions = (
            tuple(completed_steps),
            tuple(partial_conversions),
        )
        self.failed_step, self.trace, self.provider = failed_step, trace, provider
        super().__init__(message)


class FiniteThermochemicalCycle:
    """Constant-pressure staged species/enthalpy accounting, without a new ODE.

    Pre-withdrawals leave at the previous inventory temperature. Feeds retain
    their supplied temperature. Conditioning and prescribed reactions reach
    the stage endpoint temperature. Component takeoff is an imposed operation,
    not separation performance. Additive h_i(T,P) excludes mixture excess heat.
    """

    def __init__(
        self,
        enthalpy: MolarEnthalpyProvider,
        evidence: ThermochemicalEvidence,
        *,
        tolerances: ThermochemicalTolerances = ThermochemicalTolerances(),
    ):
        species = tuple(enthalpy.species)
        if not species or len({s.identifier for s in species}) != len(species):
            raise ValueError("Declare unique common-reference phase/species caloric inputs")
        _ids(enthalpy.basis_id)
        self.enthalpy, self.evidence, self.tolerances = enthalpy, evidence, tolerances
        self.species, self.energy_basis_id = species, enthalpy.basis_id
        self.names = tuple(s.identifier for s in species)
        self.elements = tuple(sorted({e for s in species for e in s.elements}))
        self._atoms = np.array([[s.elements.get(e, 0) for s in species] for e in self.elements])
        self._masses = np.array([s.molar_mass_kg_mol for s in species])

    def _vector(self, values):
        if set(values) - set(self.names):
            raise ValueError("Inventory/transfer contains undeclared phase species")
        result = np.array([finite(values.get(name, 0.0), "species amount") for name in self.names])
        if np.any(result < 0):
            raise ValueError("Finite material inventories cannot be negative")
        return result

    def _h(self, temperature, pressure):
        if (
            tuple(self.enthalpy.species) != self.species
            or self.enthalpy.basis_id != self.energy_basis_id
        ):
            raise ValueError("Caloric species/reference changed without rebinding the process")
        # Providers may legitimately reuse one mutable native scratch buffer.
        values = np.array(
            self.enthalpy.enthalpies_j_mol(temperature, pressure), dtype=float, copy=True
        )
        if values.shape != (len(self.species),) or not np.all(np.isfinite(values)):
            raise ValueError("Provider returned invalid phase/species molar enthalpies")
        return values

    def _inventory(self, n, temperature, pressure):
        return ThermochemicalInventory(
            dict(zip(self.names, n, strict=True)), temperature, pressure, self.energy_basis_id
        )

    def _check_balance(self, element, mass, energy, scale_n, scale_h):
        t = self.tolerances
        if not np.all(np.isfinite(element)):
            raise ValueError("Thermochemical element audit is nonfinite")
        for value, name in (
            (mass, "mass residual"),
            (energy, "energy residual"),
            (scale_n, "amount audit scale"),
            (scale_h, "enthalpy audit scale"),
        ):
            finite(value, name)
        amount_limit = finite(
            t.amount_mol + t.relative * scale_n, "amount tolerance budget", positive=True
        )
        mass_limit = finite(
            t.mass_kg + t.relative * scale_n * float(max(self._masses)),
            "mass tolerance budget",
            positive=True,
        )
        energy_limit = finite(
            t.energy_j + t.relative * scale_h, "energy tolerance budget", positive=True
        )
        if (
            np.max(abs(element)) > amount_limit
            or abs(mass) > mass_limit
            or abs(energy) > energy_limit
        ):
            raise ValueError("Finite thermochemical element/mass/enthalpy boundary audit failed")

    def run(
        self,
        initial: ThermochemicalInventory,
        stages,
        *,
        carrier_species,
        require_carrier_closed=True,
        require_temperature_closed=True,
        require_full_inventory_closed=False,
    ) -> ThermochemicalTrace:
        if initial.energy_basis_id != self.energy_basis_id:
            raise ValueError("Initial inventory uses another caloric reference")
        stages = tuple(stages)
        if not all(
            isinstance(v, (bool, np.bool_))
            for v in (
                require_carrier_closed,
                require_temperature_closed,
                require_full_inventory_closed,
            )
        ):
            raise ValueError("Cycle closure requirements must be explicit booleans")
        if not stages or len({s.identifier for s in stages}) != len(stages):
            raise ValueError("Provide at least one uniquely identified thermochemical stage")
        carriers = tuple(carrier_species)
        if not carriers or len(set(carriers)) != len(carriers) or set(carriers) - set(self.names):
            raise ValueError(
                "Declare the finite carrier species whose cyclic state must be checked"
            )
        for left, right in zip(stages[:-1], stages[1:], strict=True):
            if left.end_s != right.start_s or left.clock_id != right.clock_id:
                raise ValueError("Stages require contiguous explicit windows on one clock")
        for stage in stages:
            if any(c.reaction.species != self.species for c in stage.conversions):
                raise ValueError(
                    "Stage reaction species/order/phase differs from the common caloric provider"
                )
        pressure, current = initial.pressure_pa, initial
        n_initial = self._vector(initial.amounts_mol)
        if _sum(n_initial, "initial total amount") <= 0 or (
            require_carrier_closed
            and _sum(
                (n_initial[self.names.index(name)] for name in carriers), "initial carrier amount"
            )
            <= 0
        ):
            raise ValueError("A closed carrier cycle needs a nonempty initial carrier inventory")
        self._h(initial.temperature_k, pressure)
        steps, trace = [], None
        total_feed, total_out = np.zeros(len(self.species)), np.zeros(len(self.species))
        for stage in stages:
            conversions, step = [], None
            try:
                before = self._vector(current.amounts_mol)
                withdrawal = self._vector(stage.pre_withdrawal_mol)
                if np.any(withdrawal > before):
                    raise ValueError(
                        "Pre-withdrawal exceeds the existing inventory before this stage's feed"
                    )
                carry = before - withdrawal
                hinitial, htarget = (
                    self._h(current.temperature_k, pressure),
                    self._h(stage.endpoint_temperature_k, pressure),
                )
                feed, feed_h, conditioning = (
                    np.zeros(len(self.species)),
                    0.0,
                    _dot(carry, htarget - hinitial, "carrier conditioning heat"),
                )
                for boundary in stage.feeds:
                    inventory = boundary.inventory
                    if (
                        inventory.energy_basis_id != self.energy_basis_id
                        or inventory.pressure_pa != pressure
                    ):
                        raise ValueError(
                            "Feed reference/absolute pressure differs; compression/work is not inferred"
                        )
                    n = self._vector(inventory.amounts_mol)
                    hfeed = self._h(inventory.temperature_k, pressure)
                    feed += n
                    feed_h = finite(feed_h + _dot(n, hfeed, "feed enthalpy"), "total feed enthalpy")
                    conditioning = finite(
                        conditioning + _dot(n, htarget - hfeed, "feed conditioning heat"),
                        "total conditioning heat",
                    )
                state_n, reaction_heat = carry + feed, 0.0
                if _sum(state_n, "active process amount") <= 0:
                    raise ValueError("An empty process inventory has no endpoint temperature")
                for command in stage.conversions:
                    conversion = command.reaction.convert(
                        dict(zip(self.names, state_n, strict=True)), command.extent_mol
                    )
                    conversions.append(conversion)
                    reaction_heat += conversion_heat_j(
                        conversion,
                        self.enthalpy,
                        inlet_temperature_k=stage.endpoint_temperature_k,
                        outlet_temperature_k=stage.endpoint_temperature_k,
                        pressure_pa=pressure,
                    )
                    state_n = conversion.final_mol
                after = self._inventory(state_n, stage.endpoint_temperature_k, pressure)
                hbefore, hafter, hout = (
                    _dot(before, hinitial, "initial enthalpy"),
                    _dot(state_n, htarget, "final enthalpy"),
                    _dot(withdrawal, hinitial, "withdrawal enthalpy"),
                )
                heat = finite(conditioning + reaction_heat, "stage required heat")
                defect_n = state_n - before - feed + withdrawal
                element, mass = (
                    self._atoms @ defect_n,
                    _dot(defect_n, self._masses, "mass residual"),
                )
                energy = hafter - hbefore - feed_h + hout - heat
                step = ThermochemicalStageResult(
                    stage,
                    current,
                    after,
                    tuple(conversions),
                    feed,
                    withdrawal,
                    feed_h,
                    hout,
                    hbefore,
                    hafter,
                    conditioning,
                    reaction_heat,
                    heat,
                    energy,
                    element,
                    mass,
                )
                self._check_balance(
                    element,
                    mass,
                    energy,
                    float((before + feed).sum()),
                    max(abs(hbefore), abs(hafter), abs(feed_h), abs(heat)),
                )
                steps.append(step)
                current = after
                total_feed += feed
                total_out += withdrawal
            except Exception as error:
                raise ThermochemicalCycleError(
                    f"Thermochemical stage {stage.identifier} failed: {error}",
                    stage=stage,
                    before=current,
                    completed_steps=steps,
                    partial_conversions=conversions,
                    failed_step=step,
                    provider=self.enthalpy,
                ) from error
        try:
            final = self._vector(current.amounts_mol)
            defect_n = final - n_initial - total_feed + total_out
            element, mass = self._atoms @ defect_n, float(defect_n @ self._masses)
            net_heat = math.fsum(s.heat_required_j for s in steps)
            energy = (
                steps[-1].after_enthalpy_j
                - steps[0].before_enthalpy_j
                - math.fsum(s.feed_enthalpy_j - s.withdrawn_enthalpy_j for s in steps)
                - net_heat
            )
            indices = [self.names.index(name) for name in carriers]
            carrier_error = final[indices] - n_initial[indices]
            t = self.tolerances
            carrier_closed = bool(
                np.all(
                    abs(carrier_error)
                    <= t.amount_mol + t.relative * np.maximum(final[indices], n_initial[indices])
                )
            )
            temperature_closed = (
                abs(current.temperature_k - initial.temperature_k) <= t.temperature_k
            )
            complete = bool(
                np.all(
                    abs(final - n_initial)
                    <= t.amount_mol + t.relative * np.maximum(final, n_initial)
                )
            )
            trace = ThermochemicalTrace(
                initial,
                current,
                tuple(steps),
                self.species,
                self.elements,
                total_feed,
                total_out,
                element,
                mass,
                net_heat,
                math.fsum(max(0.0, s.heat_required_j) for s in steps),
                -math.fsum(min(0.0, s.heat_required_j) for s in steps),
                energy,
                carriers,
                carrier_error,
                carrier_closed,
                temperature_closed,
                complete,
                self.evidence,
                self.enthalpy,
            )
            self._check_balance(
                element,
                mass,
                energy,
                float((n_initial + total_feed).sum()),
                max(
                    abs(steps[0].before_enthalpy_j),
                    abs(steps[-1].after_enthalpy_j),
                    abs(net_heat),
                    sum(abs(s.feed_enthalpy_j) for s in steps),
                ),
            )
            if (
                (require_carrier_closed and not carrier_closed)
                or (require_temperature_closed and not temperature_closed)
                or (require_full_inventory_closed and not complete)
            ):
                raise ValueError(
                    "Requested carrier/temperature/complete-inventory cycle closure failed"
                )
            self._h(current.temperature_k, pressure)
        except Exception as error:
            raise ThermochemicalCycleError(
                str(error), completed_steps=steps, trace=trace, provider=self.enthalpy
            ) from error
        return trace
