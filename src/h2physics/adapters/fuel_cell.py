"""Finite fuel-cell material/electric/enthalpy composition; implemented_unverified.

HydrogenStack owns polarization/Faraday, the shared thermochemical driver owns
finite conversion/calorimetry. Currents, temperature, activities and component
takeoff are explicitly imposed boundaries, not new transport/utility laws.
"""

import math
import weakref
from collections.abc import Mapping
from dataclasses import dataclass, field, fields
from types import MappingProxyType

import numpy as np

from ..constants import FARADAY_C_MOL
from ..core import Origin, finite
from ..electrochemistry import (
    FuelCellOperatingState,
    HydrogenStack,
    ReactionEnergy,
    StackGeometry,
    StackResult,
    fuel_cell_activity_correction,
)
from ..reactions import StoichiometricReaction
from ..thermochemical import (
    FiniteThermochemicalCycle,
    PrescribedConversion,
    ThermochemicalEvidence,
    ThermochemicalFeed,
    ThermochemicalInventory,
    ThermochemicalStage,
    ThermochemicalTolerances,
)
from .carrier_conversion import CarrierCaloricSource, CarrierWithdrawal
from .result_provenance import recorded_content_sha256 as _sha

STATUS = "implemented_unverified"


def _text(*values):
    if any(not isinstance(v, str) or not v.strip() for v in values):
        raise ValueError(
            "Declare fuel-cell reference, phase, activity, boundary and clock evidence"
        )


def _sum(values, label):
    try:
        return finite(math.fsum(float(v) for v in values), label)
    except OverflowError as cause:
        raise ValueError(label + " exceeds finite arithmetic") from cause


@dataclass(frozen=True, slots=True)
class FuelCellBoundary:
    pressure_pa: float
    water_phase: str
    temperature_bounds_k: tuple[float, float]
    maximum_current_density_a_m2: float
    reaction_enthalpy_match_j_mol: float
    activity_source_id: str
    thermal_boundary_id: str
    pressure_source_id: str
    frame_id: str
    hydrogen_inlet_id: str
    oxidant_inlet_id: str
    product_outlet_id: str

    def __post_init__(self):
        for name in (
            "pressure_pa",
            "maximum_current_density_a_m2",
            "reaction_enthalpy_match_j_mol",
        ):
            finite(getattr(self, name), name, positive=True)
        bounds = tuple(self.temperature_bounds_k)
        if len(bounds) != 2 or not 0 < bounds[0] < bounds[1] < math.inf:
            raise ValueError("Declare finite positive increasing stack/caloric temperature bounds")
        if self.water_phase not in {"liquid", "vapor"}:
            raise ValueError("Match the actual product phase to shared ReactionEnergy convention")
        _text(
            self.activity_source_id,
            self.thermal_boundary_id,
            self.pressure_source_id,
            self.frame_id,
            self.hydrogen_inlet_id,
            self.oxidant_inlet_id,
            self.product_outlet_id,
        )
        if len({self.hydrogen_inlet_id, self.oxidant_inlet_id, self.product_outlet_id}) != 3:
            raise ValueError("Declare distinct hydrogen/oxidant inlet and component outlet ports")
        object.__setattr__(self, "temperature_bounds_k", bounds)


@dataclass(frozen=True, slots=True)
class FuelCellEvidence:
    process_id: str
    clock_id: str
    region_id: str
    polarization_source_id: str
    reaction_energy_source_id: str
    withdrawal_source_id: str
    faradaic_policy_id: str
    origin: Origin

    def __post_init__(self):
        _text(*(getattr(self, f.name) for f in fields(self) if f.name != "origin"))
        object.__setattr__(self, "origin", Origin(self.origin))
        if self.origin == Origin.UNRESOLVED:
            raise ValueError("Resolve physical evidence or declare an authored synthetic boundary")


@dataclass(frozen=True, slots=True)
class FuelCellStep:
    identifier: str
    start_s: float
    end_s: float
    clock_id: str
    temperature_k: float
    current_density_a_m2: float
    faradaic_efficiency: float
    evidence_id: str
    feeds: tuple[ThermochemicalFeed, ...] = ()
    feed_ports: Mapping[str, str] = field(default_factory=dict)
    pre_withdrawal_mol: Mapping[str, float] = field(default_factory=dict)
    operating_state: FuelCellOperatingState | None = None

    def __post_init__(self):
        _text(self.identifier, self.clock_id, self.evidence_id)
        if finite(self.start_s, "start s") >= finite(self.end_s, "end s"):
            raise ValueError("Supply an increasing finite interval on the declared clock")
        finite(self.end_s - self.start_s, "duration s", positive=True)
        finite(self.temperature_k, "imposed stack temperature K", positive=True)
        if self.operating_state is not None:
            if type(self.operating_state) is not FuelCellOperatingState:
                raise TypeError("A step operating state must use the shared fuel-cell state type")
            if (self.operating_state.temperature_k != self.temperature_k):
                raise ValueError("Step temperature must exactly match its declared channel operating state")
        if finite(self.current_density_a_m2, "current density A/m2") < 0:
            raise ValueError("Current density is a nonnegative fuel-cell magnitude")
        if (
            isinstance(self.faradaic_efficiency, bool)
            or finite(self.faradaic_efficiency, "explicit Faradaic efficiency") != 1.0
        ):
            raise ValueError(
                "Finite closed heat fate requires explicitly unity Faradaic efficiency"
            )
        feeds = tuple(self.feeds)
        if not all(isinstance(v, ThermochemicalFeed) for v in feeds):
            raise TypeError("Reuse existing finite thermochemical feed packets")
        ports = dict(self.feed_ports)
        if set(ports) != {v.source_id for v in feeds}:
            raise ValueError("Declare one target inlet port for each finite feed packet ID")
        _text(*(value for pair in ports.items() for value in pair))
        takeoff = dict(self.pre_withdrawal_mol)
        for name, value in takeoff.items():
            _text(name)
            if finite(value, "finite pre-withdrawal mol") < 0:
                raise ValueError("Component withdrawal cannot be negative")
        object.__setattr__(self, "feeds", feeds)
        object.__setattr__(self, "feed_ports", MappingProxyType(ports))
        object.__setattr__(self, "pre_withdrawal_mol", MappingProxyType(takeoff))


@dataclass(frozen=True, slots=True)
class FuelCellStepResult:
    command: FuelCellStep
    stack_result: StackResult
    kernel_trace: object
    molar_enthalpies_j_mol: tuple[float, ...]
    extent_mol_h2: float
    electricity_into_j: float
    required_heat_into_j: float
    charge_residual_mol: float
    energy_residual_j: float
    operating_state: FuelCellOperatingState | None = None


@dataclass(frozen=True, slots=True, weakref_slot=True)
class FuelCellTrace:
    owner: "FiniteFuelCell"
    initial: ThermochemicalInventory
    final: ThermochemicalInventory
    steps: tuple[FuelCellStepResult, ...]
    stack: HydrogenStack
    geometry: object
    caloric_source: CarrierCaloricSource
    kernel: FiniteThermochemicalCycle
    reaction: StoichiometricReaction
    boundary: FuelCellBoundary
    evidence: FuelCellEvidence
    feed_bindings: tuple
    hydrogen_consumed_mol: float
    oxygen_consumed_mol: float
    water_formed_mol: float
    electricity_into_j: float
    required_heat_into_j: float
    element_residual_mol: tuple[float, ...]
    mass_residual_kg: float
    energy_residual_j: float
    status: str = STATUS
    _admission: object = field(default=None, repr=False, compare=False)

    def require_current(self):
        if type(self.owner) is not FiniteFuelCell:
            raise FuelCellBindingError("No actual finite fuel-cell producer", result=self)
        return FiniteFuelCell.verify_result(self.owner, self)


@dataclass(frozen=True, slots=True, weakref_slot=True)
class FuelCellWithdrawal:
    result: FuelCellTrace
    step_index: int
    boundary_id: str
    frame_id: str
    evidence_id: str
    clock_id: str
    region_id: str
    event_time_s: float
    temperature_k: float
    pressure_pa: float
    energy_basis_id: str
    species: tuple
    phase_reference_id: str
    hydrogen_partition_id: str
    amounts_mol: Mapping[str, float]
    enthalpy_j: float
    _admission: object = field(default=None, repr=False, compare=False)

    def require_current(self):
        if type(self.result) is not FuelCellTrace or type(self.result.owner) is not FiniteFuelCell:
            raise FuelCellBindingError(
                "No actual withdrawal producer", result=self.result, withdrawal=self
            )
        return FiniteFuelCell.verify_withdrawal(self.result.owner, self)

    def as_feed(self, *, source_id):
        self.require_current()
        _text(source_id)
        return ThermochemicalFeed(
            ThermochemicalInventory(
                self.amounts_mol, self.temperature_k, self.pressure_pa, self.energy_basis_id
            ),
            source_id,
            self.result.evidence.origin,
        )


@dataclass(frozen=True, slots=True, weakref_slot=True)
class _Seal:
    original: object
    content_sha256: str
    configuration_sha256: str


class FuelCellBindingError(ValueError):
    def __init__(self, message, *, result=None, withdrawal=None):
        super().__init__(message)
        self.result, self.withdrawal = result, withdrawal


class FuelCellError(ValueError):
    def __init__(
        self,
        cause,
        *,
        owner,
        initial,
        command=None,
        current=None,
        completed_steps=(),
        stack_result=None,
        kernel_trace=None,
        attempted_enthalpies=None,
        attempted_extent=None,
        trace=None,
        feed_bindings=(),
        commands=(),
    ):
        super().__init__(str(cause))
        self.cause, self.owner, self.initial = cause, owner, initial
        self.command, self.current, self.completed_steps = command, current, tuple(completed_steps)
        self.stack_result, self.kernel_trace = stack_result, kernel_trace
        self.attempted_enthalpies, self.attempted_extent = attempted_enthalpies, attempted_extent
        self.trace, self.feed_bindings = trace, tuple(feed_bindings)
        self.commands = tuple(commands)


class FiniteFuelCell:
    """Constant-P finite reaction packets with externally maintained stage T/activity.

    No reactant-limited truncation: if the current command consumes more than the
    actual inventory, the step rejects and retains the completed prefix.
    """

    def __init__(
        self,
        stack,
        caloric_source,
        boundary,
        evidence,
        *,
        hydrogen_id="H2",
        oxygen_id="O2",
        water_id="H2O",
        tolerances=ThermochemicalTolerances(),
    ):
        if (
            type(stack) is not HydrogenStack
            or not isinstance(caloric_source, CarrierCaloricSource)
            or not isinstance(boundary, FuelCellBoundary)
            or not isinstance(evidence, FuelCellEvidence)
            or not isinstance(tolerances, ThermochemicalTolerances)
        ):
            raise TypeError(
                "Supply actual shared stack, caloric source and explicit boundary/evidence"
            )
        caloric_source.require_current()
        StackGeometry(
            stack.geometry.series_cells,
            stack.geometry.active_area_m2,
            stack.geometry.hydrogen_molar_mass_kg_mol,
        )
        species = tuple(caloric_source.provider.species)
        names = tuple(s.identifier for s in species)
        if len({hydrogen_id, oxygen_id, water_id}) != 3:
            raise ValueError("Use distinct molecular H2/O2/water species aliases")
        expected = (
            (hydrogen_id, {"H": 2}, -1.0),
            (oxygen_id, {"O": 2}, -0.5),
            (water_id, {"H": 2, "O": 1}, 1.0),
        )
        for name, atoms, _ in expected:
            if name not in names or dict(species[names.index(name)].elements) != atoms:
                raise ValueError("Provider must explicitly identify molecular H2/O2/H2O")
            if species[names.index(name)].charge != 0:
                raise ValueError("Only neutral material species are admitted")
        for name in (hydrogen_id, oxygen_id):
            phase = species[names.index(name)].phase
            if not (phase in {"gas", "vapor", "ideal-gas"} or phase.startswith("gas:")):
                raise ValueError("H2 and O2 must have explicitly gaseous material phases")
        water_phase = species[names.index(water_id)].phase
        if not (
            (
                boundary.water_phase == "liquid"
                and (water_phase == "liquid" or water_phase.startswith("liquid:"))
            )
            or (
                boundary.water_phase == "vapor"
                and (water_phase in {"vapor", "gas", "ideal-gas"} or water_phase.startswith("gas:"))
            )
        ):
            raise ValueError("Actual water caloric phase differs from declared product phase")
        if not math.isclose(
            stack.geometry.hydrogen_molar_mass_kg_mol,
            species[names.index(hydrogen_id)].molar_mass_kg_mol,
            rel_tol=1e-12,
            abs_tol=0.0,
        ):
            raise ValueError("Stack and finite material hydrogen molar-mass bases differ")
        coefficients = {name: value for name, _, value in expected}
        self.reaction = StoichiometricReaction(
            "fuel-cell:H2+0.5O2-to-H2O",
            species,
            tuple(coefficients.get(name, 0.0) for name in names),
        )
        self.stack, self.caloric_source, self.boundary, self.evidence = (
            stack,
            caloric_source,
            boundary,
            evidence,
        )
        self.hydrogen_id, self.oxygen_id, self.water_id = hydrogen_id, oxygen_id, water_id
        self.tolerances = tolerances
        self.kernel = FiniteThermochemicalCycle(
            caloric_source.provider,
            ThermochemicalEvidence(
                evidence.process_id,
                caloric_source.phase_reference_id,
                evidence.withdrawal_source_id,
                boundary.thermal_boundary_id,
                evidence.origin,
            ),
            tolerances=tolerances,
        )
        self._binding = (
            stack,
            stack.geometry,
            caloric_source,
            boundary,
            evidence,
            self.reaction,
            self.kernel,
            tolerances,
        )
        self._shared_evaluate = HydrogenStack.evaluate
        self._configuration_sha256 = _sha(self._configuration())
        self._results, self._withdrawals = (
            weakref.WeakValueDictionary(),
            weakref.WeakValueDictionary(),
        )

    def _configuration(self):
        return (
            self.stack,
            self.stack.geometry,
            self.stack.thermochemistry,
            getattr(self.stack.thermochemistry, "__self__", None),
            self.stack.losses,
            self.stack.evaluate,
            self.caloric_source,
            self.caloric_source._data(),
            self.boundary,
            self.evidence,
            self.reaction,
            self.hydrogen_id,
            self.oxygen_id,
            self.water_id,
            self.kernel,
            self.kernel.enthalpy,
            self.kernel.evidence,
            self.kernel.tolerances,
            self.kernel.species,
            self.kernel.names,
            self.kernel.elements,
            self.kernel.energy_basis_id,
            self.kernel._atoms,
            self.kernel._masses,
            self.kernel.run,
            self.kernel._h,
            getattr(self.kernel.run, "__self__", None),
            getattr(self.kernel._h, "__self__", None),
            self.tolerances,
        )

    def require_current(self):
        current = (
            self.stack,
            self.stack.geometry,
            self.caloric_source,
            self.boundary,
            self.evidence,
            self.reaction,
            self.kernel,
            self.tolerances,
        )
        if (
            any(a is not b for a, b in zip(current, self._binding, strict=True))
            or HydrogenStack.evaluate is not self._shared_evaluate
            or getattr(self.stack.evaluate, "__func__", None) is not self._shared_evaluate
            or getattr(self.stack.evaluate, "__self__", None) is not self.stack
        ):
            raise ValueError("Actual shared stack/geometry/kernel owner binding changed")
        self.caloric_source.require_current()
        if _sha(self._configuration()) != self._configuration_sha256:
            raise ValueError("Stack/caloric/activity/phase/reference configuration changed")
        return self

    def run(self, initial, commands, *, feed_bindings=None):
        steps, current, command, raw, kernel_trace, h, extent, trace = (
            [],
            initial,
            None,
            None,
            None,
            None,
            None,
            None,
        )
        bindings, schedule = (), ()
        try:
            self.require_current()
            schedule = tuple(commands)
            if (
                not isinstance(initial, ThermochemicalInventory)
                or initial.pressure_pa != self.boundary.pressure_pa
            ):
                raise ValueError(
                    "Initial finite inventory must use the actual declared absolute pressure"
                )
            if not schedule or not all(isinstance(v, FuelCellStep) for v in schedule):
                raise TypeError("Supply a nonempty schedule of explicit FuelCellStep commands")
            if len({v.identifier for v in schedule}) != len(schedule):
                raise ValueError("Step identities must be unique")
            for a, b in zip(schedule[:-1], schedule[1:], strict=True):
                if a.end_s != b.start_s:
                    raise ValueError("Fuel-cell intervals must be contiguous")
            if feed_bindings is not None and not isinstance(feed_bindings, Mapping):
                raise TypeError("Feed bindings map finite packet IDs to actual source withdrawals")
            bindings = tuple(dict(feed_bindings or {}).items())
            binding_map, seen_ids, seen_sources = dict(bindings), set(), set()
            for command in schedule:
                if command.clock_id != self.evidence.clock_id:
                    raise ValueError("Fuel-cell commands use a foreign clock")
                for packet in command.feeds:
                    port = command.feed_ports[packet.source_id]
                    if port not in {
                        self.boundary.hydrogen_inlet_id,
                        self.boundary.oxidant_inlet_id,
                    }:
                        raise ValueError("Finite feed needs a declared hydrogen or oxidant inlet")
                    if (
                        port == self.boundary.hydrogen_inlet_id
                        and packet.inventory.amounts_mol.get(self.oxygen_id, 0.0) > 0
                    ) or (
                        port == self.boundary.oxidant_inlet_id
                        and packet.inventory.amounts_mol.get(self.hydrogen_id, 0.0) > 0
                    ):
                        raise ValueError(
                            "Reactive H2 and O2 feeds must use their declared separate ports"
                        )
                    if packet.source_id in seen_ids:
                        raise ValueError("Finite feed packet identity consumed twice")
                    seen_ids.add(packet.source_id)
                    if packet.source_id in binding_map:
                        source = binding_map[packet.source_id]
                        if type(source) not in {CarrierWithdrawal, FuelCellWithdrawal}:
                            raise TypeError("Use an actual producer-issued material withdrawal")
                        source.require_current()
                        key = (id(source.result), source.step_index)
                        if key in seen_sources:
                            raise ValueError(
                                "The actual finite source withdrawal was allocated twice"
                            )
                        seen_sources.add(key)
                        if (
                            source.result.caloric_source is not self.caloric_source
                            or source.clock_id != command.clock_id
                            or source.event_time_s != command.start_s
                            or source.temperature_k != packet.inventory.temperature_k
                            or source.pressure_pa != packet.inventory.pressure_pa
                            or source.energy_basis_id != packet.inventory.energy_basis_id
                            or dict(source.amounts_mol) != dict(packet.inventory.amounts_mol)
                            or source.result.evidence.origin != packet.origin
                        ):
                            raise ValueError(
                                "Feed differs from actual common-reference source event/material/state"
                            )
                        if source.frame_id != self.boundary.frame_id:
                            raise ValueError(
                                "Direct material transfer requires the same declared frame"
                            )
            if set(binding_map) - seen_ids:
                raise ValueError("Every source binding must refer to an actual scheduled feed")
            input_sha = _sha((initial, schedule, bindings))
            for command in schedule:
                raw, kernel_trace, h, extent = None, None, None, None
                self.require_current()
                lo, hi = self.boundary.temperature_bounds_k
                if (
                    not lo <= command.temperature_k <= hi
                    or command.current_density_a_m2 > self.boundary.maximum_current_density_a_m2
                ):
                    raise ValueError("Command is outside the supplied stack/activity domain")
                if command.operating_state is None:
                    raw = self.stack.evaluate(
                        command.current_density_a_m2,
                        command.temperature_k,
                        mode="fuel_cell",
                        faradaic_efficiency=command.faradaic_efficiency,
                    )
                else:
                    command.operating_state.__post_init__()
                    if command.operating_state.temperature_k != command.temperature_k:
                        raise ValueError("Operating-state and command temperatures differ")
                    if command.operating_state.water_phase != self.boundary.water_phase:
                        raise ValueError("Operating-state product-water phase differs from the caloric boundary")
                    standard = self.stack.thermochemistry(command.temperature_k)
                    if type(standard) is ReactionEnergy:
                        standard.__post_init__()
                    if (type(standard) is not ReactionEnergy
                            or standard.reference_id != self.kernel.energy_basis_id):
                        raise ValueError("Activity correction requires the actual shared caloric energy basis")
                    corrected = fuel_cell_activity_correction(standard, command.operating_state)

                    def step_thermochemistry(temperature, *, expected=command.temperature_k,
                                             value=corrected):
                        if temperature != expected:
                            raise ValueError("Operating-state correction is bound to its exact temperature")
                        return value

                    step_stack = HydrogenStack(
                        self.stack.geometry,
                        step_thermochemistry,
                        self.stack.losses,
                    )
                    raw = step_stack.evaluate(
                        command.current_density_a_m2,
                        command.temperature_k,
                        mode="fuel_cell",
                        faradaic_efficiency=command.faradaic_efficiency,
                    )
                self.require_current()
                if (
                    type(raw) is not StackResult
                    or raw.mode != "fuel_cell"
                    or raw.isothermal_heat_rejection_w is None
                ):
                    raise ValueError(
                        "Actual shared fuel-cell result with closed Faradaic heat fate required"
                    )
                for value in (
                    raw.current_a,
                    raw.cell_voltage_v,
                    raw.stack_voltage_v,
                    raw.electric_input_w,
                    raw.hydrogen_production_mol_s,
                    raw.hydrogen_production_kg_s,
                    raw.reaction_enthalpy_rate_w,
                    raw.unallocated_energy_rate_w,
                    raw.isothermal_heat_rejection_w,
                ):
                    finite(value, "actual shared stack result")
                if raw.electric_input_w > 0 or raw.hydrogen_production_mol_s > 0:
                    raise ValueError(
                        "Fuel-cell electricity/H2 signs differ from the shared boundary"
                    )
                energy = raw.reaction_energy
                if (
                    (energy.reference_id != self.kernel.energy_basis_id
                     and not (command.operating_state is not None
                              and energy.reference_id.startswith(self.kernel.energy_basis_id + ":activity:")))
                    or energy.water_phase != self.boundary.water_phase
                ):
                    raise ValueError(
                        "Actual stack reaction energy reference/product phase differs from caloric inventory"
                    )
                h = self.kernel._h(command.temperature_k, self.boundary.pressure_pa)
                split_h = -_sum(
                    (a * b for a, b in zip(h, self.reaction.coefficients, strict=True)),
                    "water-splitting reference enthalpy J/mol H2",
                )
                if (
                    abs(split_h - energy.enthalpy_j_mol_h2)
                    > self.boundary.reaction_enthalpy_match_j_mol
                ):
                    raise ValueError(
                        "Stack reaction enthalpy disagrees with actual common-reference h"
                    )
                duration = command.end_s - command.start_s
                extent = finite(-raw.hydrogen_production_mol_s * duration, "finite H2 consumed mol")
                charge_error = _sum(
                    (
                        extent,
                        -raw.current_a
                        * self.stack.geometry.series_cells
                        * duration
                        / (2 * FARADAY_C_MOL),
                    ),
                    "Faraday amount residual",
                )
                charge_budget = finite(
                    self.tolerances.amount_mol + self.tolerances.relative * extent,
                    "charge audit budget mol",
                    positive=True,
                )
                if abs(charge_error) > charge_budget:
                    raise ValueError("Actual stack current and consumed H2 charge disagree")
                stage = ThermochemicalStage(
                    command.identifier,
                    command.start_s,
                    command.end_s,
                    command.clock_id,
                    command.temperature_k,
                    (PrescribedConversion(self.reaction, extent, command.evidence_id),),
                    command.evidence_id,
                    command.feeds,
                    command.pre_withdrawal_mol,
                )
                kernel_trace = self.kernel.run(
                    current,
                    (stage,),
                    carrier_species=(self.hydrogen_id, self.oxygen_id, self.water_id),
                    require_carrier_closed=False,
                    require_temperature_closed=False,
                    require_full_inventory_closed=False,
                )
                electrical = finite(raw.electric_input_w * duration, "signed electricity into J")
                heat = _sum((kernel_trace.net_heat_required_j, -electrical), "required heat into J")
                chemical_heat = kernel_trace.steps[0].reaction_heat_required_j
                core_heat_residual = _sum(
                    (chemical_heat, -electrical, raw.isothermal_heat_rejection_w * duration),
                    "shared stack/caloric heat residual",
                )
                residual = _sum(
                    (
                        kernel_trace.energy_residual_j,
                        kernel_trace.net_heat_required_j,
                        -electrical,
                        -heat,
                    ),
                    "finite electric/thermal residual J",
                )
                scale = max(abs(chemical_heat), abs(electrical), abs(heat), 1.0)
                heat_budget = finite(
                    self.tolerances.energy_j + self.tolerances.relative * scale,
                    "electric/thermal audit budget J",
                    positive=True,
                )
                if max(abs(residual), abs(core_heat_residual)) > heat_budget:
                    raise ValueError(
                        "Shared stack and actual finite electric/thermal enthalpy audit failed"
                    )
                self.require_current()
                steps.append(
                    FuelCellStepResult(
                        command,
                        raw,
                        kernel_trace,
                        tuple(map(float, h)),
                        extent,
                        electrical,
                        heat,
                        charge_error,
                        residual,
                        command.operating_state,
                    )
                )
                current = kernel_trace.final
            trace = self._aggregate(initial, current, steps, bindings)
            self.require_current()
            for _, source in bindings:
                source.require_current()
            if _sha((initial, schedule, bindings)) != input_sha:
                raise ValueError("Original command/input/source changed during the finite run")
            seal = _Seal(weakref.ref(trace), _sha(trace), self._configuration_sha256)
            object.__setattr__(trace, "_admission", seal)
            self._results[id(trace)] = seal
            return trace
        except Exception as cause:
            raise FuelCellError(
                cause,
                owner=self,
                initial=initial,
                command=command,
                current=current,
                completed_steps=steps,
                stack_result=raw,
                kernel_trace=kernel_trace or getattr(cause, "trace", None),
                attempted_enthalpies=h,
                attempted_extent=extent,
                trace=trace or getattr(cause, "trace", None),
                feed_bindings=bindings,
                commands=schedule,
            ) from cause

    def _aggregate(self, initial, final, steps, bindings):
        feed = np.array(
            [
                _sum((s.kernel_trace.feed_mol[k] for s in steps), "finite total feed mol")
                for k in range(len(self.kernel.names))
            ]
        )
        out = np.array(
            [
                _sum((s.kernel_trace.exported_mol[k] for s in steps), "finite total takeoff mol")
                for k in range(len(self.kernel.names))
            ]
        )
        n0, nf = self.kernel._vector(initial.amounts_mol), self.kernel._vector(final.amounts_mol)
        defect = nf - n0 - feed + out
        elements = self.kernel._atoms @ defect
        mass = _sum(defect * self.kernel._masses, "global fuel-cell mass residual kg")
        electric = _sum((s.electricity_into_j for s in steps), "electricity into J")
        heat = _sum((s.required_heat_into_j for s in steps), "required heat into J")
        hin = steps[0].kernel_trace.steps[0].before_enthalpy_j
        hout = steps[-1].kernel_trace.steps[-1].after_enthalpy_j
        feed_h = _sum((s.kernel_trace.steps[0].feed_enthalpy_j for s in steps), "total feed H J")
        out_h = _sum(
            (s.kernel_trace.steps[0].withdrawn_enthalpy_j for s in steps), "total takeoff H J"
        )
        residual = _sum(
            (hout, -hin, -feed_h, out_h, -electric, -heat), "global electric/thermal H residual J"
        )
        extent = _sum((s.extent_mol_h2 for s in steps), "total H2 consumed mol")
        candidate = FuelCellTrace(
            self,
            initial,
            final,
            tuple(steps),
            self.stack,
            self.stack.geometry,
            self.caloric_source,
            self.kernel,
            self.reaction,
            self.boundary,
            self.evidence,
            bindings,
            extent,
            0.5 * extent,
            extent,
            electric,
            heat,
            tuple(map(float, elements)),
            mass,
            residual,
        )
        try:
            self.kernel._check_balance(
                elements,
                mass,
                residual,
                _sum(n0 + feed, "amount audit scale"),
                max(abs(hin), abs(hout), abs(feed_h), abs(out_h), abs(electric), abs(heat)),
            )
        except Exception as cause:
            raise FuelCellError(
                cause,
                owner=self,
                initial=initial,
                current=final,
                completed_steps=steps,
                trace=candidate,
                feed_bindings=bindings,
            ) from cause
        return candidate

    def verify_result(self, result):
        try:
            if type(result) is not FuelCellTrace or result.owner is not self:
                raise ValueError(
                    "Only the actual producer's original fuel-cell trace is admissible"
                )
            seal = result._admission
            if (
                seal is None
                or self._results.get(id(result)) is not seal
                or seal.original() is not result
            ):
                raise ValueError("Fuel-cell trace is copied, replaced or unissued")
            self.require_current()
            if (
                seal.configuration_sha256 != self._configuration_sha256
                or _sha(result) != seal.content_sha256
            ):
                raise ValueError(
                    "Original shared stack/material/charge/heat/source evidence changed"
                )
            for _, source in result.feed_bindings:
                source.require_current()
            return result
        except Exception as cause:
            raise FuelCellBindingError(str(cause), result=result) from cause

    def withdrawal(self, result, step_index, *, boundary_id, frame_id, evidence_id):
        self.verify_result(result)
        _text(boundary_id, frame_id, evidence_id)
        if boundary_id != self.boundary.product_outlet_id or frame_id != self.boundary.frame_id:
            raise ValueError("Use the admitted actual component outlet and frame")
        if type(step_index) is not int or not 0 <= step_index < len(result.steps):
            raise ValueError("Select an actual accepted step")
        step = result.steps[step_index].kernel_trace.steps[0]
        if _sum(step.withdrawn_mol, "actual withdrawn mol") <= 0:
            raise ValueError("No actual finite component withdrawal exists in this step")
        value = FuelCellWithdrawal(
            result,
            step_index,
            boundary_id,
            frame_id,
            evidence_id,
            self.evidence.clock_id,
            self.evidence.region_id,
            step.stage.start_s,
            step.before.temperature_k,
            step.before.pressure_pa,
            step.before.energy_basis_id,
            self.kernel.species,
            self.caloric_source.phase_reference_id,
            self.caloric_source.hydrogen_partition_id,
            MappingProxyType(
                dict(zip(self.kernel.names, map(float, step.withdrawn_mol), strict=True))
            ),
            step.withdrawn_enthalpy_j,
        )
        seal = _Seal(weakref.ref(value), _sha(value), self._configuration_sha256)
        object.__setattr__(value, "_admission", seal)
        self._withdrawals[id(value)] = seal
        return value

    def verify_withdrawal(self, value):
        try:
            if type(value) is not FuelCellWithdrawal:
                raise ValueError("Actual original fuel-cell withdrawal required")
            self.verify_result(value.result)
            seal = value._admission
            if (
                seal is None
                or self._withdrawals.get(id(value)) is not seal
                or seal.original() is not value
                or _sha(value) != seal.content_sha256
                or seal.configuration_sha256 != self._configuration_sha256
            ):
                raise ValueError("Original finite withdrawal identity/context changed")
            return value
        except Exception as cause:
            raise FuelCellBindingError(
                str(cause), result=getattr(value, "result", None), withdrawal=value
            ) from cause
