"""Separate native finite gas compartments driven by prescribed Faraday operation.

Each Cantera volume owns pressure, temperature, species and energy integration.
H2 and O2 never share a reactor. The shared stack supplies prescribed current/T
Faraday rates; compartment pressure does not feed back into voltage or kinetics.
Independent compartment heat/U ledgers do not close the combined reaction energy.
"""

from collections.abc import Mapping
from dataclasses import dataclass, field
from hashlib import sha256
from types import MappingProxyType

from ..core import Origin, finite
from ..electrochemistry import HydrogenStack
from .cantera import ReactiveState
from .cantera_volume import CanteraOpenGasVolume, GasBoundaryRate, GasFeed, GasVent


_PENDING_COMPARTMENT_TRACE_ISSUERS = set()


def _issue_compartment_trace(**values):
    token = object()
    _PENDING_COMPARTMENT_TRACE_ISSUERS.add(token)
    try:
        return FuelCellCompartmentTrace(**values, _issuer_token=token)
    except Exception:
        _PENDING_COMPARTMENT_TRACE_ISSUERS.discard(token)
        raise


def _owner_snapshot(owner):
    return (id(owner.stack), repr(owner.stack.geometry), id(owner.stack.thermochemistry),
        tuple((name, id(model)) for name, model in owner.stack.losses.items()),
        id(owner.electrical_command), owner.evidence_id,
        tuple((id(c), repr(c.initial_state), repr(c.exchange_state), c.role, c.species_name,
               c.volume_m3, c.molar_mass_kg_mol, c.evidence_id, repr(c.heat_boundaries),
               id(c.owner), id(c.owner.phase_factory), c.owner.mechanism_basis,
               c.owner.chemistry) for c in owner.compartments))


def _trace_snapshot(traces):
    rows = []
    for role, trace in traces.items():
        arrays = tuple((name, id(getattr(trace, name)), getattr(trace, name).shape,
                        sha256(getattr(trace, name).tobytes()).hexdigest()) for name in (
                            "time_s", "boundary_integrals", "mass_residual_kg",
                            "species_residual_kg", "energy_residual_j", "ledger_native_scale_to_si"))
        rows.append((role, id(trace), id(trace.native), id(trace.native.reactor), arrays,
            tuple(repr(s) for s in trace.snapshots), trace.clock_id, trace.ledger_names,
            trace.ledger_units, trace.phase_fingerprint))
    return tuple(rows)


@dataclass(frozen=True, slots=True)
class FuelCellGasCompartment:
    compartment_id: str
    role: str
    species_name: str
    owner: CanteraOpenGasVolume = field(repr=False)
    initial_state: ReactiveState
    volume_m3: float
    exchange_state: ReactiveState
    heat_boundaries: tuple
    molar_mass_kg_mol: float
    evidence_id: str

    def __post_init__(self):
        if self.role not in {"hydrogen", "oxygen", "water_vapor"}:
            raise ValueError("Declare separate hydrogen, oxygen or water-vapor compartment")
        if type(self.owner) is not CanteraOpenGasVolume or self.owner.chemistry != "frozen":
            raise TypeError("Separate compartments require actual frozen native gas-volume owners")
        for name in ("compartment_id", "species_name", "evidence_id"):
            if not isinstance(getattr(self, name), str) or not getattr(self, name).strip():
                raise ValueError("Declare compartment, species and applicability evidence identities")
        finite(self.volume_m3, "volume_m3", positive=True)
        finite(self.molar_mass_kg_mol, "molar_mass_kg_mol", positive=True)
        for state in (self.initial_state, self.exchange_state):
            if type(state) is not ReactiveState or dict(state.mole_fractions) != {self.species_name: 1.}:
                raise ValueError("Initial/exchange states must be the explicitly assigned pure gas species")
        object.__setattr__(self, "heat_boundaries", tuple(self.heat_boundaries))


@dataclass(frozen=True, slots=True)
class FuelCellCompartmentTrace:
    owner: object = field(repr=False)
    clock_id: str
    evidence_id: str
    native_traces: Mapping
    stack_evaluations: tuple
    stoichiometric_molar_factors: Mapping
    pressure_feedback_resolved: bool = field(default=False, init=False)
    combined_reaction_energy_closed: bool = field(default=False, init=False)
    _binding: tuple = field(default=(), init=False, repr=False, compare=False)
    _issuer_token: object = field(default=None, repr=False, compare=False)

    def __post_init__(self):
        if self._issuer_token not in _PENDING_COMPARTMENT_TRACE_ISSUERS:
            raise ValueError("Fuel-cell compartment traces are issued only by the native owner run")
        _PENDING_COMPARTMENT_TRACE_ISSUERS.remove(self._issuer_token)
        object.__setattr__(self, "native_traces", MappingProxyType(dict(self.native_traces)))
        object.__setattr__(self, "stoichiometric_molar_factors",
                           MappingProxyType(dict(self.stoichiometric_molar_factors)))

    def require_current(self):
        payload = (id(self.owner), _owner_snapshot(self.owner), self.clock_id, self.evidence_id,
            _trace_snapshot(self.native_traces), repr(self.stack_evaluations),
            tuple(self.stoichiometric_molar_factors.items()), self.pressure_feedback_resolved,
            self.combined_reaction_energy_closed)
        if not self._binding or payload != self._binding:
            raise ValueError("Fuel-cell compartment result lost its issuing electrical/configuration/native ledgers")
        return self


class FuelCellCompartmentError(RuntimeError):
    def __init__(self, cause, owner, role, completed, evaluations):
        self.cause, self.owner, self.failed_role = cause, owner, role
        self.completed_native_traces = MappingProxyType(dict(completed))
        self.stack_evaluations = tuple(evaluations)
        self.native_failure = cause
        super().__init__(f"Separated fuel-cell compartment {role!r} failed")


class SeparatedFuelCellCompartments:
    """Prescribed electrical operation with independent native pressure evolution.

    ``electrical_command(time_s)`` supplies ``(current_density_a_m2, stack_temperature_k)``
    throughout the declared native callback support, continuously within a run.
    It must be deterministic because each independent native integrator evaluates
    its own stage clock. Product exchange temperature/pressure and compartment heat
    are explicit external boundaries. Depletion is rejected by the native inventory
    floor; it is not silently clamped into a lower requested current.
    """

    def __init__(self, stack, compartments, electrical_command, *, evidence_id):
        if type(stack) is not HydrogenStack or not callable(electrical_command):
            raise TypeError("Supply the original shared HydrogenStack and explicit command callback")
        compartments = tuple(compartments)
        if (len(compartments) != 3 or any(type(c) is not FuelCellGasCompartment for c in compartments)
                or {c.role for c in compartments} != {"hydrogen", "oxygen", "water_vapor"}
                or len({c.compartment_id for c in compartments}) != 3
                or len({id(c.owner) for c in compartments}) != 3):
            raise ValueError("Provide distinct native volumes for H2, O2 and gaseous product")
        if not isinstance(evidence_id, str) or not evidence_id.strip():
            raise ValueError("Declare deterministic electrical/stoichiometric boundary evidence")
        self.stack, self.compartments = stack, compartments
        self.electrical_command, self.evidence_id = electrical_command, evidence_id

    def run(self, time_s, *, clock_id, support_start_s, support_end_s,
            maximum_time_step_s, relative_tolerance, absolute_tolerance,
            minimum_inventory_kg, energy_ledger_scale_j):
        """Run three original native volumes without a new derivative/integrator."""
        import numpy as np

        times = np.array(time_s, dtype=float, copy=True)
        if (times.ndim != 1 or len(times) < 2 or not np.all(np.isfinite(times))
                or np.any(np.diff(times) <= 0)):
            raise ValueError("Declare increasing finite native output times")
        if not isinstance(clock_id, str) or not clock_id.strip():
            raise ValueError("Declare the common physical compartment clock")
        support_start = finite(support_start_s, "support_start_s")
        support_end = finite(support_end_s, "support_end_s")
        step = finite(maximum_time_step_s, "maximum_time_step_s", positive=True)
        if not support_start <= times[0] < times[-1] <= support_end-step:
            raise ValueError("Command support must include native integration overrun budget")
        roles = {c.role: c for c in self.compartments}
        factors = {"hydrogen": -1., "oxygen": -.5, "water_vapor": 1.}
        evaluations, completed = [], {}
        binding = (self.stack, self.compartments, self.electrical_command, self.evidence_id)
        original_configuration = _owner_snapshot(self)

        def guard():
            if (self.stack is not binding[0] or self.compartments is not binding[1]
                    or self.electrical_command is not binding[2] or self.evidence_id != binding[3]):
                raise ValueError("Fuel-cell compartment electrical/configuration binding changed")
            if _owner_snapshot(self) != original_configuration:
                raise ValueError("Fuel-cell stack or compartment configuration changed")

        role = "initial-admission"
        try:
            for role, compartment in roles.items():
                phase = compartment.owner.phase_factory()
                index = phase.species_index(compartment.species_name)
                expected_atoms = {"hydrogen": {"H": 2.}, "oxygen": {"O": 2.},
                                  "water_vapor": {"H": 2., "O": 1.}}[role]
                atoms = {name: phase.n_atoms(index, name) for name in phase.element_names
                         if phase.n_atoms(index, name) != 0.}
                if atoms != expected_atoms or not np.isclose(
                        phase.molecular_weights[index]/1000., compartment.molar_mass_kg_mol,
                        rtol=1e-6, atol=0.):
                    raise ValueError("Compartment role/molar mass differs from native species elemental definition")
            if not np.isclose(roles["hydrogen"].molar_mass_kg_mol
                              +.5*roles["oxygen"].molar_mass_kg_mol,
                              roles["water_vapor"].molar_mass_kg_mol, rtol=1e-6, atol=0.):
                raise ValueError("Compartment species molar masses do not close reaction mass")
            if not np.isclose(self.stack.geometry.hydrogen_molar_mass_kg_mol,
                              roles["hydrogen"].molar_mass_kg_mol, rtol=1e-6, atol=0.):
                raise ValueError("Shared stack and native H2 compartment molar masses differ")

            for role, compartment in roles.items():
                def rate(time, compartment=compartment, role=role):
                    guard()
                    current, temperature = self.electrical_command(time)
                    guard()
                    stack_result = self.stack.evaluate(current, temperature, mode="fuel_cell",
                                                       faradaic_efficiency=1.)
                    if stack_result.reaction_energy.water_phase != "vapor":
                        raise ValueError("Gas product compartments require the shared stack vapor-water convention")
                    consumption = -stack_result.hydrogen_production_mol_s
                    if finite(consumption, "H2 consumption mol/s") < 0:
                        raise ValueError("Shared stack returned the wrong reaction direction")
                    evaluations.append((role, time, stack_result))
                    return abs(factors[role])*consumption*compartment.molar_mass_kg_mol

                boundary = GasBoundaryRate(compartment.compartment_id+":reaction", clock_id,
                    support_start, support_end, rate, Origin.RECONSTRUCTED, self.evidence_id,
                    phase_access="time_only")
                feed = (GasFeed(boundary, compartment.exchange_state),) if role == "water_vapor" else ()
                vent = () if role == "water_vapor" else (GasVent(boundary, compartment.exchange_state),)
                completed[role] = compartment.owner.run(compartment.initial_state, times,
                    volume_m3=compartment.volume_m3, clock_id=clock_id, feeds=feed, vents=vent,
                    heat_boundaries=compartment.heat_boundaries, maximum_time_step_s=step,
                    relative_tolerance=relative_tolerance, absolute_tolerance=absolute_tolerance,
                    minimum_inventory_kg=minimum_inventory_kg, energy_ledger_scale_j=energy_ledger_scale_j)
                guard()
            result = _issue_compartment_trace(
                owner=self, clock_id=clock_id, evidence_id=self.evidence_id,
                native_traces=completed, stack_evaluations=tuple(evaluations),
                stoichiometric_molar_factors=factors)
            object.__setattr__(result, "_binding", (id(self), original_configuration, clock_id,
                self.evidence_id, _trace_snapshot(result.native_traces), repr(result.stack_evaluations),
                tuple(result.stoichiometric_molar_factors.items()), False, False))
            return result.require_current()
        except Exception as cause:
            raise FuelCellCompartmentError(cause, self, role, completed, evaluations) from cause


__all__ = ["FuelCellGasCompartment", "SeparatedFuelCellCompartments",
           "FuelCellCompartmentTrace", "FuelCellCompartmentError"]
