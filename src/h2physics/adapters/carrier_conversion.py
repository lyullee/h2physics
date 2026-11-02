"""Finite LOHC/ammonia material and caloric boundaries using existing kernels.

Implemented_unverified. Extent, temperature and component withdrawal are imposed
operations, not catalyst, equilibrium, separator or industrial reactor predictions.
The common thermochemical driver owns conversion and heat accounting.
"""

import math
import weakref
from collections.abc import Mapping
from dataclasses import dataclass, field, fields
from types import MappingProxyType

from ..core import Origin, finite
from ..reactions import FunctionalMolarEnthalpy, StoichiometricReaction
from ..thermochemical import (
    FiniteThermochemicalCycle,
    ThermochemicalEvidence,
    ThermochemicalFeed,
    ThermochemicalInventory,
    ThermochemicalStage,
    ThermochemicalTolerances,
)
from .result_provenance import recorded_content_sha256 as _sha

STATUS = "implemented_unverified"


def _text(*values):
    if any(not isinstance(value, str) or not value.strip() for value in values):
        raise ValueError("Declare carrier, phase/reference, source, clock and boundary identities")


def _origin(value):
    value = Origin(value)
    if value == Origin.UNRESOLVED:
        raise ValueError("Resolve input meaning or declare an authored synthetic input")
    return value


def _sum(values, label):
    try:
        return finite(math.fsum(float(value) for value in values), label)
    except OverflowError as cause:
        raise ValueError(label + " exceeds finite arithmetic") from cause


class CarrierCaloricSource:
    """Actual common-reference provider plus an explicit read-only definition probe.

    A probe must read retained definitions, not evaluate h, kinetics or a solver.
    Hidden closure/private/external state remains the provider owner's contract.
    Native helper probes below use actual existing phase-definition guards.
    """

    def __init__(
        self,
        provider,
        *,
        phase_reference_id,
        hydrogen_partition_id,
        source_id,
        origin,
        definition_probe,
        native_objects=(),
    ):
        _text(phase_reference_id, hydrogen_partition_id, source_id, provider.basis_id)
        if not callable(definition_probe):
            raise TypeError("Supply a nonexecuting provider-definition probe")
        self.provider, self.phase_reference_id = provider, phase_reference_id
        self.hydrogen_partition_id, self.source_id = hydrogen_partition_id, source_id
        self.origin, self.definition_probe = _origin(origin), definition_probe
        self.native_objects = tuple(native_objects)
        self._definition = _sha(self._data())

    def _data(self):
        return (
            self.provider,
            self.provider.species,
            self.provider.basis_id,
            self.provider.enthalpies_j_mol,
            getattr(self.provider.enthalpies_j_mol, "__self__", None),
            self.phase_reference_id,
            self.hydrogen_partition_id,
            self.source_id,
            self.origin,
            self.definition_probe,
            getattr(self.definition_probe, "__self__", None),
            self.native_objects,
            self.definition_probe(),
        )

    def require_current(self):
        if _sha(self._data()) != self._definition:
            raise ValueError("Caloric source definitions/reference/native pointers changed")
        return self


def functional_carrier_caloric(
    provider, *, phase_reference_id, hydrogen_partition_id, source_id, origin
):
    """Bind an existing caller-authored FunctionalMolarEnthalpy; no new heat law."""
    if not isinstance(provider, FunctionalMolarEnthalpy):
        raise TypeError("Supply the existing FunctionalMolarEnthalpy provider")

    def probe(provider=provider):
        return (
            provider.species,
            provider.functions,
            provider.basis_id,
            provider.temperature_bounds_k,
            provider.pressure_bounds_pa,
        )

    return CarrierCaloricSource(
        provider,
        phase_reference_id=phase_reference_id,
        hydrogen_partition_id=hydrogen_partition_id,
        source_id=source_id,
        origin=origin,
        definition_probe=probe,
    )


def coolprop_carrier_caloric(
    provider, *, phase_reference_id, hydrogen_partition_id, source_id, origin
):
    """Bind a native CoolProp reaction provider with its actual owned states."""
    from ..thermo.coolprop import CoolPropMolarEnthalpy

    if type(provider) is not CoolPropMolarEnthalpy:
        raise TypeError("Supply the existing CoolPropMolarEnthalpy provider")

    def probe(provider=provider):
        return (provider.definition_signature, provider.definition_signature())

    return CarrierCaloricSource(
        provider, phase_reference_id=phase_reference_id,
        hydrogen_partition_id=hydrogen_partition_id, source_id=source_id,
        origin=origin, definition_probe=probe, native_objects=provider._states,
    )


def native_ammonia_caloric(
    phase_factory, mechanism_basis, *, phase_reference_id, hydrogen_partition_id, source_id, origin
):
    """Reuse the audited Cantera gas/solid caloric owner for one ideal-gas phase.

    No mechanism is bundled. NH3, N2 and H2 fits/domains, molar masses and
    formation offsets remain in the separately installed native engine.
    """
    from .cantera_caloric import CaloricSpeciesMapping, CanteraMultiphaseMolarEnthalpy
    from .cantera_multiphase import EquilibriumPhase

    provider = CanteraMultiphaseMolarEnthalpy(
        (
            EquilibriumPhase(
                "carrier-gas",
                "gas",
                phase_factory,
                mechanism_basis,
                phase_reference_id,
                hydrogen_partition_id,
            ),
        ),
        tuple(CaloricSpeciesMapping("carrier-gas", name, name) for name in ("NH3", "N2", "H2")),
    )

    def probe(provider=provider):
        provider._require_definitions()
        return (
            provider.species,
            provider.basis_id,
            provider.phases,
            provider.species_mapping,
            provider.source_phases,
            provider.owned_phases,
            provider.phase_copy_audits,
            provider.native_gas_providers,
            provider._require_definitions,
            getattr(provider._require_definitions, "__self__", None),
            provider._phase_indices,
            provider._mapped_indices,
            provider.energy_reference_id,
            provider.hydrogen_partition_id,
            tuple(
                (
                    key,
                    value.native_phase,
                    value.mechanism_basis,
                    value.species,
                    value._indices,
                    value.basis_id,
                    value.enthalpies_j_mol,
                    getattr(value.enthalpies_j_mol, "__self__", None),
                )
                for key, value in provider.native_gas_providers.items()
            ),
        )

    return CarrierCaloricSource(
        provider,
        phase_reference_id=phase_reference_id,
        hydrogen_partition_id=hydrogen_partition_id,
        source_id=source_id,
        origin=origin,
        definition_probe=probe,
        native_objects=(*provider.source_phases, *provider.owned_phases),
    )


@dataclass(frozen=True, slots=True)
class CarrierPathway:
    identifier: str
    kind: str
    reaction: StoichiometricReaction
    hydrogen_id: str
    carrier_species: tuple[str, ...]
    phase_reference_id: str
    source_id: str
    origin: Origin
    original_source: object = None

    def __post_init__(self):
        _text(self.identifier, self.hydrogen_id, self.phase_reference_id, self.source_id)
        if self.kind not in {"liquid-lohc", "ammonia-gas"}:
            raise ValueError("Select explicit liquid-LOHC or ideal-gas-ammonia scope")
        if not isinstance(self.reaction, StoichiometricReaction):
            raise TypeError("Reuse the existing balanced reaction contract")
        names = tuple(s.identifier for s in self.reaction.species)
        carriers = tuple(self.carrier_species)
        if (
            len(carriers) != 2
            or len(set(carriers)) != 2
            or self.hydrogen_id in carriers
            or set(carriers) - set(names)
            or self.hydrogen_id not in names
        ):
            raise ValueError("Identify the finite carrier and molecular H2 species")
        hydrogen = self.reaction.species[names.index(self.hydrogen_id)]
        if (
            dict(hydrogen.elements) != {"H": 2}
            or hydrogen.charge != 0
            or not (hydrogen.phase in {"gas", "ideal-gas"} or hydrogen.phase.startswith("gas:"))
            or self.reaction.coefficients[names.index(self.hydrogen_id)] <= 0
        ):
            raise ValueError("Forward pathway must form explicitly gaseous neutral molecular H2")
        first, second = (self.reaction.species[names.index(name)] for name in carriers)
        expected = {
            carriers[0]: -1.0,
            carriers[1]: 1.0,
            self.hydrogen_id: self.reaction.coefficients[names.index(self.hydrogen_id)],
        }
        if self.kind == "liquid-lohc":
            if any(
                item.charge != 0 or not (item.phase == "liquid" or item.phase.startswith("liquid:"))
                for item in (first, second)
            ):
                raise ValueError("LOHC pathway requires two neutral explicitly liquid carriers")
        else:
            if (
                dict(first.elements) != {"N": 1, "H": 3}
                or dict(second.elements) != {"N": 2}
                or any(
                    item.phase != "ideal-gas" or item.charge != 0
                    for item in (first, second, hydrogen)
                )
            ):
                raise ValueError("Ammonia pathway roles must be neutral ideal-gas NH3/N2/H2")
            expected = {carriers[0]: -2.0, carriers[1]: 1.0, self.hydrogen_id: 3.0}
        if self.reaction.coefficients != tuple(expected.get(name, 0.0) for name in names):
            raise ValueError("Pathway coefficients differ from its declared chemical roles")
        object.__setattr__(self, "carrier_species", carriers)
        object.__setattr__(self, "origin", _origin(self.origin))


def lohc_pathway(
    species,
    *,
    rich_id,
    lean_id,
    hydrogen_id,
    hydrogen_per_carrier,
    identifier,
    phase_reference_id,
    source_id,
    origin,
    original_source=None,
):
    """Liquid rich -> liquid lean + n H2; phases and h(T,P) are supplied evidence.

    Existing QM9 gas-reference heat/audit objects may be retained as original
    context but are never read as liquid caloric parameters by this adapter.
    """
    species = tuple(species)
    names = tuple(s.identifier for s in species)
    if len({rich_id, lean_id, hydrogen_id}) != 3 or not {rich_id, lean_id, hydrogen_id} <= set(
        names
    ):
        raise ValueError("Declare three distinct participating species from the common provider")
    count = finite(hydrogen_per_carrier, "H2 mol per mol rich carrier", positive=True)
    for name in (rich_id, lean_id):
        phase = species[names.index(name)].phase
        if not (phase == "liquid" or phase.startswith("liquid:")):
            raise ValueError("LOHC liquid calorimetry requires explicitly liquid carrier species")
    coefficients = tuple(
        -1.0
        if name == rich_id
        else 1.0
        if name == lean_id
        else count
        if name == hydrogen_id
        else 0.0
        for name in names
    )
    return CarrierPathway(
        identifier,
        "liquid-lohc",
        StoichiometricReaction(identifier, species, coefficients),
        hydrogen_id,
        (rich_id, lean_id),
        phase_reference_id,
        source_id,
        origin,
        original_source,
    )


def ammonia_pathway(
    species,
    *,
    identifier,
    phase_reference_id,
    source_id,
    origin,
    ammonia_id="NH3",
    nitrogen_id="N2",
    hydrogen_id="H2",
):
    """2 NH3(g) -> N2(g) + 3 H2(g); reverse extent is synthesis bookkeeping."""
    species = tuple(species)
    names = tuple(s.identifier for s in species)
    identities = (
        (ammonia_id, {"N": 1, "H": 3}, -2.0),
        (nitrogen_id, {"N": 2}, 1.0),
        (hydrogen_id, {"H": 2}, 3.0),
    )
    if len({ammonia_id, nitrogen_id, hydrogen_id}) != 3:
        raise ValueError("Ammonia/nitrogen/hydrogen aliases must be distinct")
    for name, elements, _ in identities:
        if name not in names:
            raise ValueError("Native/common provider lacks a required ammonia species")
        item = species[names.index(name)]
        if dict(item.elements) != elements or item.phase != "ideal-gas" or item.charge != 0:
            raise ValueError("This ammonia path requires explicit neutral ideal-gas species")
    coefficients = dict((name, coefficient) for name, _, coefficient in identities)
    reaction = StoichiometricReaction(
        identifier, species, tuple(coefficients.get(name, 0.0) for name in names)
    )
    return CarrierPathway(
        identifier,
        "ammonia-gas",
        reaction,
        hydrogen_id,
        (ammonia_id, nitrogen_id),
        phase_reference_id,
        source_id,
        origin,
    )


@dataclass(frozen=True, slots=True)
class CarrierProcessEvidence:
    process_id: str
    clock_id: str
    region_id: str
    phase_reference_id: str
    extent_source_id: str
    thermal_boundary_id: str
    withdrawal_assumption_id: str
    origin: Origin

    def __post_init__(self):
        _text(*(getattr(self, f.name) for f in fields(self) if f.name != "origin"))
        object.__setattr__(self, "origin", _origin(self.origin))


@dataclass(frozen=True, slots=True, weakref_slot=True)
class CarrierConversionResult:
    owner: "FiniteCarrierConversion"
    pathway: CarrierPathway
    caloric_source: CarrierCaloricSource
    kernel: FiniteThermochemicalCycle
    process_trace: object
    evidence: CarrierProcessEvidence
    hydrogen_initial_mol: float
    hydrogen_final_mol: float
    hydrogen_formed_mol: float
    hydrogen_consumed_mol: float
    hydrogen_withdrawn_mol: float
    hydrogen_species_residual_mol: float
    feed_bindings: tuple
    status: str = STATUS
    _admission: object = field(default=None, repr=False, compare=False)

    def require_current(self):
        if type(self.owner) is not FiniteCarrierConversion:
            raise CarrierBindingError("No actual carrier producer binding", result=self)
        return FiniteCarrierConversion.verify_result(self.owner, self)

    @property
    def hydrogen_mass_ledger_kg(self):
        """Return the issued H2 species ledger converted with its declared molar mass.

        This is a mass-unit view of the retained molar ledger, not a product purity,
        delivery-flow, or separate-hydrogen-stream calculation.
        """
        self.require_current()
        species_index = next(
            index for index, species in enumerate(self.pathway.reaction.species)
            if species.identifier == self.pathway.hydrogen_id
        )
        molar_mass = self.pathway.reaction.species[species_index].molar_mass_kg_mol
        process = self.process_trace
        return MappingProxyType({
            "initial_inventory_kg": self.hydrogen_initial_mol * molar_mass,
            "final_inventory_kg": self.hydrogen_final_mol * molar_mass,
            "feed_kg": float(process.feed_mol[species_index]) * molar_mass,
            "formed_gross_kg": self.hydrogen_formed_mol * molar_mass,
            "consumed_gross_kg": self.hydrogen_consumed_mol * molar_mass,
            "withdrawn_kg": self.hydrogen_withdrawn_mol * molar_mass,
            "species_residual_kg": self.hydrogen_species_residual_mol * molar_mass,
        })


@dataclass(frozen=True, slots=True, weakref_slot=True)
class CarrierWithdrawal:
    """Finite imposed component takeoff at one stage-start event, not a flow law."""

    result: CarrierConversionResult
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
    amounts_mol: Mapping[str, float]
    enthalpy_j: float
    _admission: object = field(default=None, repr=False, compare=False)

    def require_current(self):
        if type(self.result) is not CarrierConversionResult:
            raise CarrierBindingError(
                "Withdrawal lacks an actual carrier result", result=self.result, withdrawal=self
            )
        owner = self.result.owner
        if type(owner) is not FiniteCarrierConversion:
            raise CarrierBindingError(
                "No actual withdrawal producer", result=self.result, withdrawal=self
            )
        return FiniteCarrierConversion.verify_withdrawal(owner, self)

    def as_feed(self, *, source_id):
        """Finite material/caloric packet; pass its original binding to the receiver.

        The receiving run must include ``feed_bindings={source_id: self}`` to
        preserve producer evidence. This performs no separator or flow solve.
        """
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
class _IssuedSeal:
    original: object
    content_sha256: str
    configuration_sha256: str


class CarrierBindingError(ValueError):
    def __init__(self, message, *, result=None, withdrawal=None):
        super().__init__(message)
        self.result, self.withdrawal = result, withdrawal


class CarrierConversionError(ValueError):
    def __init__(
        self, cause, *, owner, initial, stages, process_trace=None, result=None, feed_bindings=()
    ):
        super().__init__(str(cause))
        self.cause, self.owner, self.initial, self.stages = cause, owner, initial, stages
        self.process_trace, self.result = process_trace, result
        self.feed_bindings = tuple(feed_bindings)
        self.kernel_error = cause
        self.completed_steps = tuple(
            process_trace.steps
            if process_trace is not None
            else getattr(cause, "completed_steps", ())
        )


class FiniteCarrierConversion:
    """One declared carrier path, finite packets and shared constant-P calorimetry.

    Stage temperature/extent/withdrawal are supplied constraints. Feeds are
    uniquely identified finite packets, consumed once in this run, not infinite
    or automatically replenished reservoirs. There is no new physical ODE.
    """

    def __init__(self, pathway, caloric_source, evidence, *, tolerances=ThermochemicalTolerances()):
        if (
            not isinstance(pathway, CarrierPathway)
            or not isinstance(caloric_source, CarrierCaloricSource)
            or not isinstance(evidence, CarrierProcessEvidence)
        ):
            raise TypeError("Supply actual pathway, caloric source and process evidence")
        caloric_source.require_current()
        if (
            pathway.reaction.species != tuple(caloric_source.provider.species)
            or pathway.phase_reference_id != caloric_source.phase_reference_id
            or evidence.phase_reference_id != pathway.phase_reference_id
        ):
            raise ValueError(
                "Pathway species/order/phase/reference differs from the caloric source"
            )
        self.pathway, self.caloric_source, self.evidence = pathway, caloric_source, evidence
        self.tolerances = tolerances
        self.kernel = FiniteThermochemicalCycle(
            caloric_source.provider,
            ThermochemicalEvidence(
                evidence.process_id,
                evidence.phase_reference_id,
                evidence.withdrawal_assumption_id,
                evidence.thermal_boundary_id,
                evidence.origin,
            ),
            tolerances=tolerances,
        )
        self._binding = (pathway, caloric_source, evidence, tolerances, self.kernel)
        self._configuration_sha256 = _sha(self._configuration())
        self._issued_results, self._issued_withdrawals = (
            weakref.WeakValueDictionary(),
            weakref.WeakValueDictionary(),
        )

    def _configuration(self):
        return (
            self.pathway,
            self.caloric_source,
            self.caloric_source._data(),
            self.evidence,
            self.tolerances,
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
        )

    def require_current(self):
        if any(
            current is not original
            for current, original in zip(
                (self.pathway, self.caloric_source, self.evidence, self.tolerances, self.kernel),
                self._binding,
                strict=True,
            )
        ):
            raise ValueError("Carrier producer owner bindings changed")
        self.caloric_source.require_current()
        if _sha(self._configuration()) != self._configuration_sha256:
            raise ValueError("Carrier pathway/caloric/kernel/evidence configuration changed")
        return self

    def run(self, initial, stages, *, feed_bindings=None):
        process, result = None, None
        schedule = tuple(stages)
        bindings = ()
        try:
            self.require_current()
            if not isinstance(initial, ThermochemicalInventory):
                raise TypeError("Supply actual finite molar inventory with common reference")
            if not schedule or not all(
                isinstance(stage, ThermochemicalStage) for stage in schedule
            ):
                raise TypeError("Supply existing nonempty thermochemical stage objects")
            if feed_bindings is not None and not isinstance(feed_bindings, Mapping):
                raise TypeError("Bind source packet IDs to original CarrierWithdrawal objects")
            bindings = tuple(dict(feed_bindings or {}).items())
            binding_map = dict(bindings)
            seen_feeds = set()
            seen_bound_withdrawals = set()
            for stage in schedule:
                if stage.clock_id != self.evidence.clock_id:
                    raise ValueError("Carrier process stage uses a foreign clock")
                if any(c.reaction is not self.pathway.reaction for c in stage.conversions):
                    raise ValueError("Stage conversion is not this admitted original pathway")
                for packet in stage.feeds:
                    if packet.source_id in seen_feeds:
                        raise ValueError("A finite feed packet identity cannot be consumed twice")
                    seen_feeds.add(packet.source_id)
                    if packet.source_id in binding_map:
                        original = binding_map[packet.source_id]
                        if type(original) is not CarrierWithdrawal:
                            raise TypeError(
                                "Bound feed must retain an actual producer-issued withdrawal"
                            )
                        original.require_current()
                        source_key = (id(original.result), original.step_index)
                        if source_key in seen_bound_withdrawals:
                            raise ValueError("An actual finite withdrawal cannot be consumed twice")
                        seen_bound_withdrawals.add(source_key)
                        if (
                            original.result.caloric_source is not self.caloric_source
                            or original.clock_id != stage.clock_id
                            or original.event_time_s != stage.start_s
                            or dict(packet.inventory.amounts_mol) != dict(original.amounts_mol)
                            or packet.inventory.temperature_k != original.temperature_k
                            or packet.inventory.pressure_pa != original.pressure_pa
                            or packet.inventory.energy_basis_id != original.energy_basis_id
                            or packet.origin != original.result.evidence.origin
                        ):
                            raise ValueError(
                                "Feed source/clock/event/material/reference differs from its actual withdrawal"
                            )
            if set(binding_map) - seen_feeds:
                raise ValueError(
                    "Source bindings must refer to actual finite feed packets in this run"
                )
            input_sha256 = _sha((initial, schedule, bindings))
            process = self.kernel.run(
                initial,
                schedule,
                carrier_species=self.pathway.carrier_species,
                require_carrier_closed=False,
                require_temperature_closed=False,
                require_full_inventory_closed=False,
            )
            self.require_current()
            for _, original in bindings:
                original.require_current()
            if _sha((initial, schedule, bindings)) != input_sha256:
                raise ValueError(
                    "Original input schedule or bound source packet changed during conversion"
                )
            index = self.kernel.names.index(self.pathway.hydrogen_id)
            changes = tuple(
                c.extent_mol * c.reaction.coefficients[index]
                for step in process.steps
                for c in step.conversions
            )
            formed = _sum((max(value, 0.0) for value in changes), "H2 formed mol")
            consumed = _sum((max(-value, 0.0) for value in changes), "H2 consumed mol")
            first = float(process.initial.amounts_mol.get(self.pathway.hydrogen_id, 0.0))
            last = float(process.final.amounts_mol.get(self.pathway.hydrogen_id, 0.0))
            removed = float(process.exported_mol[index])
            residual = _sum(
                (last, -first, -float(process.feed_mol[index]), removed, -formed, consumed),
                "H2 species residual mol",
            )
            budget = finite(
                self.tolerances.amount_mol
                + self.tolerances.relative
                * max(first, last, formed, consumed, removed, float(process.feed_mol[index])),
                "H2 species audit budget",
                positive=True,
            )
            if abs(residual) > budget:
                raise ValueError("Generated/consumed/feed/withdrawn H2 species audit failed")
            result = CarrierConversionResult(
                self,
                self.pathway,
                self.caloric_source,
                self.kernel,
                process,
                self.evidence,
                first,
                last,
                formed,
                consumed,
                removed,
                residual,
                bindings,
            )
            seal = _IssuedSeal(weakref.ref(result), _sha(result), self._configuration_sha256)
            object.__setattr__(result, "_admission", seal)
            self._issued_results[id(result)] = seal
            return result
        except Exception as cause:
            raise CarrierConversionError(
                cause,
                owner=self,
                initial=initial,
                stages=schedule,
                process_trace=process or getattr(cause, "trace", None),
                result=result,
                feed_bindings=bindings,
            ) from cause

    def verify_result(self, result):
        """Check issued identity/definitions/cached ledgers, without replaying physics."""
        try:
            if type(result) is not CarrierConversionResult or result.owner is not self:
                raise ValueError("Require the actual producer's original carrier result")
            seal = result._admission
            if (
                seal is None
                or self._issued_results.get(id(result)) is not seal
                or seal.original() is not result
            ):
                raise ValueError("Carrier result is copied, replaced or unissued")
            self.require_current()
            for _, original in result.feed_bindings:
                original.require_current()
            if (
                seal.configuration_sha256 != self._configuration_sha256
                or _sha(result) != seal.content_sha256
            ):
                raise ValueError("Retained carrier result/cache/reference changed")
            return result
        except Exception as cause:
            raise CarrierBindingError(str(cause), result=result) from cause

    def withdrawal(self, result, step_index, *, boundary_id, frame_id, evidence_id):
        self.verify_result(result)
        _text(boundary_id, frame_id, evidence_id)
        if type(step_index) is not int or not 0 <= step_index < len(result.process_trace.steps):
            raise ValueError("Select an actual accepted process step")
        step = result.process_trace.steps[step_index]
        if _sum(step.withdrawn_mol, "actual finite withdrawal mol") <= 0:
            raise ValueError("Selected step contains no actual finite component takeoff")
        value = CarrierWithdrawal(
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
            MappingProxyType(
                dict(zip(self.kernel.names, map(float, step.withdrawn_mol), strict=True))
            ),
            step.withdrawn_enthalpy_j,
        )
        seal = _IssuedSeal(weakref.ref(value), _sha(value), self._configuration_sha256)
        object.__setattr__(value, "_admission", seal)
        self._issued_withdrawals[id(value)] = seal
        return value

    def verify_withdrawal(self, value):
        try:
            if type(value) is not CarrierWithdrawal:
                raise ValueError("Require an actual producer-issued finite withdrawal")
            self.verify_result(value.result)
            seal = value._admission
            if (
                seal is None
                or self._issued_withdrawals.get(id(value)) is not seal
                or seal.original() is not value
                or _sha(value) != seal.content_sha256
                or seal.configuration_sha256 != self._configuration_sha256
            ):
                raise ValueError("Withdrawal identity/context/cache no longer matches its producer")
            return value
        except Exception as cause:
            raise CarrierBindingError(
                str(cause), result=getattr(value, "result", None), withdrawal=value
            ) from cause
