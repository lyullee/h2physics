"""Post-run receipt mapping native channel pressures to one explicit stack point.

This is a host-side handoff only: native compartments have already completed
independent integrations. It does not feed pressure back during integration or
claim a simultaneous electrochemical/thermal closure.
"""

from collections.abc import Callable
from dataclasses import dataclass, field
from ..core import finite
from ..electrochemistry import (
    FuelCellOperatingState,
    HydrogenStack,
    ReactionEnergy,
    StackResult,
    fuel_cell_activity_correction,
)
from .fuel_cell_compartments import FuelCellCompartmentTrace
from .result_provenance import recorded_content_sha256


@dataclass(frozen=True, slots=True)
class FuelCellFugacityActivityProvider:
    """Caller-owned fugacity service used to form non-ideal gas activities.

    The callback must return fugacity in Pa for the named pure channel at the
    supplied absolute pressure and temperature. Existing property providers can
    be adapted here; this type adds no equation of state or fugacity correlation.
    """

    evaluate_fugacity_pa: Callable[[str, float, float], float] = field(repr=False)
    provider_id: str
    evidence_id: str
    _seal: str = field(init=False, repr=False, compare=False)

    def __post_init__(self):
        if not callable(self.evaluate_fugacity_pa):
            raise TypeError("Supply a caller-owned fugacity callback")
        for value, name in ((self.provider_id, "provider"), (self.evidence_id, "fugacity evidence")):
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"Declare the {name} identity")
        object.__setattr__(self, "_seal", self._current_signature())

    def _current_signature(self):
        return recorded_content_sha256((
            self.evaluate_fugacity_pa, self.provider_id, self.evidence_id,
        ))

    def require_current(self):
        if self._current_signature() != self._seal:
            raise ValueError("Fuel-cell fugacity provider definition changed")
        return self

    def relative_activity(self, species_id, pressure_pa, reference_pressure_pa, temperature_k):
        self.require_current()
        if not isinstance(species_id, str) or not species_id.strip():
            raise ValueError("Declare the gas species for fugacity evaluation")
        pressure = finite(pressure_pa, "sample absolute pressure", positive=True)
        reference = finite(reference_pressure_pa, "reference absolute pressure", positive=True)
        temperature = finite(temperature_k, "activity temperature", positive=True)
        fugacity = finite(self.evaluate_fugacity_pa(species_id, pressure, temperature),
                          "sample fugacity", positive=True)
        reference_fugacity = finite(
            self.evaluate_fugacity_pa(species_id, reference, temperature),
            "reference fugacity", positive=True,
        )
        self.require_current()
        return finite(fugacity / reference_fugacity, "dimensionless gas activity", positive=True)


@dataclass(frozen=True, slots=True)
class FuelCellActivityReceipt:
    """One pressure/fugacity activity point sampled from completed runs."""

    compartments: FuelCellCompartmentTrace = field(repr=False)
    sample_time_s: float
    operating_state: FuelCellOperatingState
    standard_reaction_energy: ReactionEnergy
    corrected_reaction_energy: ReactionEnergy
    stack_result: StackResult
    current_density_a_m2: float
    hydrogen_reference_pressure_pa: float
    oxygen_reference_pressure_pa: float
    water_reference_pressure_pa: float
    evidence_id: str
    fugacity_activity_provider: FuelCellFugacityActivityProvider | None = None
    _seal: str = field(init=False, repr=False)
    pressure_feedback_resolved: bool = field(default=False, init=False)
    simultaneous_energy_closure: bool = field(default=False, init=False)

    def __post_init__(self):
        # A public constructor must establish its own consistency; a seal alone
        # would merely preserve caller-supplied fabricated state/result fields.
        self._require_recomputed_content()
        object.__setattr__(self, "_seal", self._content())

    def _content(self):
        return recorded_content_sha256((
            id(self.compartments), self.sample_time_s, self.operating_state,
            self.standard_reaction_energy, self.corrected_reaction_energy,
            repr(self.stack_result), self.current_density_a_m2, self.evidence_id,
            self.fugacity_activity_provider,
            self.hydrogen_reference_pressure_pa, self.oxygen_reference_pressure_pa,
            self.water_reference_pressure_pa,
            self.pressure_feedback_resolved, self.simultaneous_energy_closure,
        ))

    def _recompute(self):
        trace = self.compartments
        if type(trace) is not FuelCellCompartmentTrace:
            raise TypeError("Retain the original separated-compartment trace")
        trace.require_current()
        time = finite(self.sample_time_s, "sample_time_s")
        state = self.operating_state
        if type(state) is not FuelCellOperatingState:
            raise TypeError("Retain the shared explicit fuel-cell operating state")
        if type(self.standard_reaction_energy) is not ReactionEnergy:
            raise TypeError("Retain the shared standard reaction-energy object")
        if self.standard_reaction_energy.water_phase != "vapor":
            raise ValueError("Separated gas activity receipt requires vapor product water")
        if not isinstance(self.evidence_id, str) or not self.evidence_id.strip():
            raise ValueError("Declare the ideal-gas/reference-state handoff evidence")
        provider = self.fugacity_activity_provider
        if provider is not None:
            if type(provider) is not FuelCellFugacityActivityProvider:
                raise TypeError("Use the typed caller-owned fugacity activity provider")
            provider.require_current()
        references = {
            "hydrogen": (finite(self.hydrogen_reference_pressure_pa, "H2 reference pressure", positive=True),
                         state.hydrogen_reference_id),
            "oxygen": (finite(self.oxygen_reference_pressure_pa, "O2 reference pressure", positive=True),
                       state.oxygen_reference_id),
            "water_vapor": (finite(self.water_reference_pressure_pa, "water reference pressure", positive=True),
                            state.water_reference_id),
        }
        times = {tuple(float(value) for value in native.time_s)
                 for native in trace.native_traces.values()}
        if len(times) != 1:
            raise ValueError("Independent native channels do not share an exact accepted output grid")
        selected = {}
        for role, (reference_pressure, reference_id) in references.items():
            if not isinstance(reference_id, str) or not reference_id.strip():
                raise ValueError("Every channel activity needs a named reference pressure")
            native = trace.native_traces[role]
            hits = [i for i, value in enumerate(native.time_s) if float(value) == time]
            if len(hits) != 1:
                raise ValueError("Select an exact accepted output time shared by every native channel")
            pressure = finite(native.snapshots[hits[0]].pressure_pa, role + " sampled pressure", positive=True)
            selected[role] = (pressure, reference_pressure, reference_id)
        p_h2, p_h2_ref, h2_ref_id = selected["hydrogen"]
        p_o2, p_o2_ref, o2_ref_id = selected["oxygen"]
        p_h2o, p_h2o_ref, h2o_ref_id = selected["water_vapor"]
        temperature = finite(state.temperature_k, "stack_temperature_k", positive=True)
        if provider is None:
            h2_activity, o2_activity, h2o_activity = (
                p_h2 / p_h2_ref, p_o2 / p_o2_ref, p_h2o / p_h2o_ref,
            )
        else:
            h2_activity = provider.relative_activity("hydrogen", p_h2, p_h2_ref, temperature)
            o2_activity = provider.relative_activity("oxygen", p_o2, p_o2_ref, temperature)
            h2o_activity = provider.relative_activity("water_vapor", p_h2o, p_h2o_ref, temperature)
            provider.require_current()
        expected_state = FuelCellOperatingState(
            temperature, p_h2, p_o2, h2_activity, o2_activity,
            h2o_activity, "vapor", h2_ref_id, o2_ref_id, h2o_ref_id,
            self.evidence_id + ":post-run-native-pressure-sample:" + format(time, ".17g"),
        )
        corrected = fuel_cell_activity_correction(self.standard_reaction_energy, expected_state)
        current = finite(self.current_density_a_m2, "current_density_a_m2")
        if current < 0.:
            raise ValueError("Current density is a nonnegative magnitude")
        source_stack = trace.owner.stack
        operating_stack = HydrogenStack(
            source_stack.geometry, lambda _temperature: corrected, source_stack.losses)
        expected_stack_result = operating_stack.evaluate(current, temperature, mode="fuel_cell")
        return expected_state, corrected, expected_stack_result

    def _require_recomputed_content(self):
        expected_state, expected_energy, expected_stack = self._recompute()
        if self.operating_state != expected_state:
            raise ValueError("Operating state does not match the retained native sample and reference pressures")
        if self.corrected_reaction_energy != expected_energy:
            raise ValueError("Corrected reaction energy does not match the retained native sample")
        if self.stack_result != expected_stack:
            raise ValueError("Stack result does not reproduce from the original stack and explicit inputs")
        if self.pressure_feedback_resolved or self.simultaneous_energy_closure:
            raise ValueError("A post-run sample cannot claim dynamic feedback or energy closure")
        return self

    def require_current(self):
        self.compartments.require_current()
        if self._content() != self._seal:
            raise ValueError("Sampled pressure/activity receipt content changed")
        self._require_recomputed_content()
        return self


def sample_fuel_cell_activity_receipt(
    compartments, *, sample_time_s, stack_temperature_k, current_density_a_m2,
    standard_reaction_energy, hydrogen_reference_pressure_pa,
    oxygen_reference_pressure_pa, water_reference_pressure_pa,
    hydrogen_reference_id, oxygen_reference_id, water_reference_id, evidence_id,
    fugacity_activity_provider=None,
):
    """Build a post-run pressure-normalized activity receipt and stack result.

    By default pure single-species ideal-gas channels use ``activity = p / p_reference``
    (fugacity coefficient unity). An explicit provider may instead evaluate actual
    and reference fugacity. Pressure is read from one exact accepted
    output sample. Stack temperature and current remain explicit caller inputs;
    no native callback is replayed and no pressure feedback is implied.
    """
    if type(compartments) is not FuelCellCompartmentTrace:
        raise TypeError("Supply an original separated-compartment trace")
    compartments.require_current()
    if type(standard_reaction_energy) is not ReactionEnergy:
        raise TypeError("Supply the shared standard reaction-energy object")
    if standard_reaction_energy.water_phase != "vapor":
        raise ValueError("This gas-compartment activity bridge requires vapor product water")
    if not isinstance(evidence_id, str) or not evidence_id.strip():
        raise ValueError("Declare the ideal-gas/reference-state handoff evidence")
    if fugacity_activity_provider is not None:
        if type(fugacity_activity_provider) is not FuelCellFugacityActivityProvider:
            raise TypeError("Use FuelCellFugacityActivityProvider for non-ideal gas activities")
        fugacity_activity_provider.require_current()
    time = finite(sample_time_s, "sample_time_s")
    temperature = finite(stack_temperature_k, "stack_temperature_k", positive=True)
    current = finite(current_density_a_m2, "current_density_a_m2")
    if current < 0.:
        raise ValueError("Current density is a nonnegative magnitude")
    references = {
        "hydrogen": finite(hydrogen_reference_pressure_pa, "H2 reference pressure", positive=True),
        "oxygen": finite(oxygen_reference_pressure_pa, "O2 reference pressure", positive=True),
        "water_vapor": finite(water_reference_pressure_pa, "water reference pressure", positive=True),
    }
    for reference_id in (hydrogen_reference_id, oxygen_reference_id, water_reference_id):
        if not isinstance(reference_id, str) or not reference_id.strip():
            raise ValueError("Every channel activity needs a named reference pressure")
    times = {tuple(float(value) for value in native.time_s)
             for native in compartments.native_traces.values()}
    if len(times) != 1 or time not in next(iter(times)):
        raise ValueError("Select an exact accepted output time shared by every native channel")
    pressures = {role: float(compartments.native_traces[role].snapshots[
                    tuple(float(value) for value in compartments.native_traces[role].time_s).index(time)
                ].pressure_pa) for role in ("hydrogen", "oxygen", "water_vapor")}
    if fugacity_activity_provider is None:
        activities = tuple(pressures[role] / references[role] for role in (
            "hydrogen", "oxygen", "water_vapor"))
    else:
        activities = tuple(fugacity_activity_provider.relative_activity(
            species, pressures[role], references[role], temperature,
        ) for role, species in (("hydrogen", "hydrogen"), ("oxygen", "oxygen"),
                                ("water_vapor", "water_vapor")))
    state = FuelCellOperatingState(
        temperature, pressures["hydrogen"], pressures["oxygen"],
        activities[0], activities[1], activities[2], "vapor",
        hydrogen_reference_id, oxygen_reference_id, water_reference_id,
        evidence_id + ":post-run-native-pressure-sample:" + format(time, ".17g"),
    )
    corrected = fuel_cell_activity_correction(standard_reaction_energy, state)
    source_stack = compartments.owner.stack
    operating_stack = HydrogenStack(
        source_stack.geometry, lambda _temperature: corrected, source_stack.losses)
    stack_result = operating_stack.evaluate(current, temperature, mode="fuel_cell")
    receipt = FuelCellActivityReceipt(
        compartments, time, state, standard_reaction_energy, corrected,
        stack_result, current, references["hydrogen"], references["oxygen"],
        references["water_vapor"], evidence_id, fugacity_activity_provider,
    )
    return receipt.require_current()


@dataclass(frozen=True, slots=True)
class FuelCellActivitySeries:
    """Post-run activity/stack samples covering one complete shared native grid."""

    compartments: FuelCellCompartmentTrace = field(repr=False)
    receipts: tuple[FuelCellActivityReceipt, ...]
    _seal: str = field(init=False, repr=False)
    pressure_feedback_resolved: bool = field(default=False, init=False)
    simultaneous_energy_closure: bool = field(default=False, init=False)

    def __post_init__(self):
        object.__setattr__(self, "receipts", tuple(self.receipts))
        self._validate()
        object.__setattr__(self, "_seal", self._content())

    @property
    def operating_states(self):
        self.require_current()
        return tuple(receipt.operating_state for receipt in self.receipts)

    @property
    def sample_times_s(self):
        self.require_current()
        return tuple(receipt.sample_time_s for receipt in self.receipts)

    def _content(self):
        return recorded_content_sha256((
            id(self.compartments), tuple(id(receipt) for receipt in self.receipts),
            self.pressure_feedback_resolved, self.simultaneous_energy_closure,
        ))

    def _validate(self):
        if type(self.compartments) is not FuelCellCompartmentTrace:
            raise TypeError("Retain the original separated-compartment trace")
        self.compartments.require_current()
        if not self.receipts or any(type(item) is not FuelCellActivityReceipt for item in self.receipts):
            raise TypeError("Supply one original sampled activity receipt per accepted output time")
        expected_times = tuple(float(value) for value in
            self.compartments.native_traces["hydrogen"].time_s)
        if tuple(item.sample_time_s for item in self.receipts) != expected_times:
            raise ValueError("Activity series must cover every shared accepted native output time in order")
        first = self.receipts[0]
        lineage = (first.standard_reaction_energy.reference_id,
            first.hydrogen_reference_pressure_pa, first.oxygen_reference_pressure_pa,
            first.water_reference_pressure_pa, first.operating_state.hydrogen_reference_id,
            first.operating_state.oxygen_reference_id, first.operating_state.water_reference_id,
            first.evidence_id)
        for item in self.receipts:
            item.require_current()
            if item.compartments is not self.compartments:
                raise ValueError("Every activity sample must retain the same original compartment trace")
            if item.fugacity_activity_provider is not first.fugacity_activity_provider:
                raise ValueError("Activity samples must retain one original fugacity provider")
            observed = (item.standard_reaction_energy.reference_id,
                item.hydrogen_reference_pressure_pa, item.oxygen_reference_pressure_pa,
                item.water_reference_pressure_pa, item.operating_state.hydrogen_reference_id,
                item.operating_state.oxygen_reference_id, item.operating_state.water_reference_id,
                item.evidence_id)
            if observed != lineage:
                raise ValueError("Activity samples must share one caloric and channel reference basis")
        if self.pressure_feedback_resolved or self.simultaneous_energy_closure:
            raise ValueError("Post-run activity samples cannot claim in-solver feedback or energy closure")
        return self

    def require_current(self):
        if self._content() != self._seal:
            raise ValueError("Sampled fuel-cell activity series membership changed")
        self._validate()
        return self


def sample_fuel_cell_activity_series(
    compartments, *, operating_points, hydrogen_reference_pressure_pa,
    oxygen_reference_pressure_pa, water_reference_pressure_pa,
    hydrogen_reference_id, oxygen_reference_id, water_reference_id, evidence_id,
    fugacity_activity_provider=None,
):
    """Map explicit (time, T, current, ReactionEnergy) rows over the full native grid.

    Each pressure is sampled after the independent compartment integrations. The
    operating point is never interpolated or fed back into the native solver.
    """
    if type(compartments) is not FuelCellCompartmentTrace:
        raise TypeError("Supply an original separated-compartment trace")
    compartments.require_current()
    rows = tuple(tuple(row) for row in operating_points)
    expected_times = tuple(float(value) for value in
        compartments.native_traces["hydrogen"].time_s)
    if len(rows) != len(expected_times) or any(len(row) != 4 for row in rows):
        raise ValueError("Supply (time, stack temperature, current density, reaction energy) for each accepted time")
    if tuple(finite(row[0], "sample time") for row in rows) != expected_times:
        raise ValueError("Operating-point rows must cover the exact full accepted native time grid")
    receipts = tuple(sample_fuel_cell_activity_receipt(
        compartments, sample_time_s=time, stack_temperature_k=temperature,
        current_density_a_m2=current, standard_reaction_energy=energy,
        hydrogen_reference_pressure_pa=hydrogen_reference_pressure_pa,
        oxygen_reference_pressure_pa=oxygen_reference_pressure_pa,
        water_reference_pressure_pa=water_reference_pressure_pa,
        hydrogen_reference_id=hydrogen_reference_id,
        oxygen_reference_id=oxygen_reference_id,
        water_reference_id=water_reference_id, evidence_id=evidence_id,
        fugacity_activity_provider=fugacity_activity_provider,
    ) for time, temperature, current, energy in rows)
    return FuelCellActivitySeries(compartments, receipts).require_current()


__all__ = ["FuelCellFugacityActivityProvider", "FuelCellActivityReceipt", "sample_fuel_cell_activity_receipt",
           "FuelCellActivitySeries", "sample_fuel_cell_activity_series"]
