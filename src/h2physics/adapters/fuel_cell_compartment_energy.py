"""Complete-window compartment/solid/coolant energy diagnostics.

Original owners integrate all states. Missing membrane/phase/caloric coupling is
represented by an unresolved signed residual; this API never declares combined
reaction energy closed by choosing an unmeasured heat term.
"""

from dataclasses import dataclass, field
from math import fsum
from types import MappingProxyType

from ..core import finite
from ..electrochemical_thermal import FiniteCoolantStackTrace
from .fuel_cell import FuelCellTrace
from .fuel_cell_compartments import FuelCellCompartmentTrace
from .result_provenance import recorded_content_sha256


def compartment_reaction_extent_audit(trace, *, mass_budget_kg, mole_budget_mol,
                                      deterministic_command_evidence_id):
    """Compare independently integrated native reaction-port masses.

    Shared time callbacks do not establish equal native quadratures. Report each
    role's actual native boundary integral and reaction-equivalent H2 extent.
    """
    if type(trace) is not FuelCellCompartmentTrace:
        raise TypeError("Retain an original separated-compartment trace")
    trace.require_current()
    if not isinstance(deterministic_command_evidence_id, str) or not deterministic_command_evidence_id.strip():
        raise ValueError("Declare deterministic command evidence")
    mass_budget = finite(mass_budget_kg, "reaction mass budget kg", positive=True)
    mole_budget = finite(mole_budget_mol, "reaction extent budget mol", positive=True)
    rows = {}
    windows = {(float(native.time_s[0]), float(native.time_s[-1]), native.clock_id)
               for native in trace.native_traces.values()}
    if len(windows) != 1 or next(iter(windows))[2] != trace.clock_id:
        raise ValueError("Reaction extents require native role ledgers on one exact clock/window")
    for compartment in trace.owner.compartments:
        native = trace.native_traces[compartment.role]
        prefix = "inlet:" if compartment.role == "water_vapor" else "outlet:"
        labels = [name for name in native.ledger_names if name.startswith(prefix) and name.endswith(":mass")]
        if len(labels) != 1:
            raise ValueError("Each separated role needs exactly one original reaction material boundary")
        amount = float(native.integral(labels[0])[-1]-native.integral(labels[0])[0])
        if amount < 0.:
            raise ValueError("Native reaction material boundary integral cannot be negative")
        factor = abs(trace.stoichiometric_molar_factors[compartment.role])
        extent = amount/(factor*compartment.molar_mass_kg_mol)
        rows[compartment.role] = (finite(amount, "native reaction mass"), finite(extent, "native H2-equivalent extent"))
    reference = rows["hydrogen"][1]
    residual_mol = {role: extent-reference for role, (_mass, extent) in rows.items()}
    residual_kg = {compartment.role: residual_mol[compartment.role]
                   *abs(trace.stoichiometric_molar_factors[compartment.role])*compartment.molar_mass_kg_mol
                   for compartment in trace.owner.compartments}
    trace.require_current()
    return MappingProxyType(dict(native_mass_and_extent=MappingProxyType(rows),
        extent_residual_mol=MappingProxyType(residual_mol), mass_residual_kg=MappingProxyType(residual_kg),
        mass_budget_kg=mass_budget, mole_budget_mol=mole_budget,
        within_declared_budgets=all(abs(v) <= mole_budget for v in residual_mol.values())
            and all(abs(v) <= mass_budget for v in residual_kg.values()),
        deterministic_command_evidence_id=deterministic_command_evidence_id))


@dataclass(frozen=True, slots=True)
class FuelCellCompartmentEnergyLedger:
    compartments: FuelCellCompartmentTrace
    electrical_source: FuelCellTrace
    thermal_source: FiniteCoolantStackTrace
    reaction_extent_audit: MappingProxyType
    compartment_energy_change_j: float
    native_reaction_port_enthalpy_into_j: float
    native_compartment_heat_into_j: float
    solid_energy_change_j: float
    coolant_enthalpy_change_j: float
    electricity_into_j: float
    external_thermal_heat_into_j: float
    unresolved_combined_energy_residual_j: float
    reference_allocation_evidence_id: str
    _signature: str = field(init=False, repr=False)
    combined_reaction_energy_closed: bool = field(default=False, init=False)

    def __post_init__(self):
        object.__setattr__(self, "_signature", self._content())

    def _content(self):
        return recorded_content_sha256((
            id(self.compartments), id(self.electrical_source), id(self.thermal_source),
            self.reaction_extent_audit, self.compartment_energy_change_j,
            self.native_reaction_port_enthalpy_into_j, self.native_compartment_heat_into_j,
            self.solid_energy_change_j, self.coolant_enthalpy_change_j,
            self.electricity_into_j, self.external_thermal_heat_into_j,
            self.unresolved_combined_energy_residual_j, self.reference_allocation_evidence_id,
            self.combined_reaction_energy_closed,
        ))

    def require_current(self):
        self.compartments.require_current()
        self.electrical_source.require_current()
        self.thermal_source.require_current()
        if self._content() != self._signature:
            raise ValueError("Original compartment/thermal/electrical energy ledger changed")
        return self


def audit_fuel_cell_compartment_energy(compartments, electrical_source, thermal_source, *,
                                       mass_budget_kg, mole_budget_mol,
                                       deterministic_command_evidence_id,
                                       reference_allocation_evidence_id):
    """Retain complete original ledgers and report unresolved combined balance.

    The electrical source is an original finite fuel-cell result, not an assumed
    efficiency or numerically integrated adaptive callback log. Thermal capacity
    scope and caloric reference allocation are explicit caller evidence. Native
    reaction-port enthalpy is separately reported as an internal conversion-plane
    diagnostic; adding it again as external heat would duplicate chemical energy.
    """
    if (type(compartments) is not FuelCellCompartmentTrace or type(electrical_source) is not FuelCellTrace
            or type(thermal_source) is not FiniteCoolantStackTrace):
        raise TypeError("Retain original compartment, finite electrical and finite thermal results")
    electrical_source.require_current()
    thermal_source.require_current()
    compartments.require_current()
    if not isinstance(reference_allocation_evidence_id, str) or not reference_allocation_evidence_id.strip():
        raise ValueError("Declare caloric-reference, thermal-capacity and heat-allocation scope evidence")
    if (compartments.owner.stack is not electrical_source.stack
            or thermal_source.owner.stack is not electrical_source.stack
            or compartments.clock_id != electrical_source.evidence.clock_id
            or compartments.clock_id != thermal_source.reservoir.clock_id):
        raise ValueError("Combined energy requires exact shared stack and common physical clock")
    start = electrical_source.steps[0].command.start_s
    end = electrical_source.steps[-1].command.end_s
    if (thermal_source.stages[0].command.start_s != start
            or thermal_source.stages[-1].command.end_s != end
            or any(trace.time_s[0] != start or trace.time_s[-1] != end
                   for trace in compartments.native_traces.values())):
        raise ValueError("Every original energy ledger must span the exact complete common window")
    audit = compartment_reaction_extent_audit(
        compartments, mass_budget_kg=mass_budget_kg, mole_budget_mol=mole_budget_mol,
        deterministic_command_evidence_id=deterministic_command_evidence_id,
    )
    electrical_extent_residual = {
        role: row[1]-electrical_source.hydrogen_consumed_mol
        for role, row in audit["native_mass_and_extent"].items()
    }
    electrical_mass_residual = {
        compartment.role: electrical_extent_residual[compartment.role]
            *abs(compartments.stoichiometric_molar_factors[compartment.role])
            *compartment.molar_mass_kg_mol
        for compartment in compartments.owner.compartments
    }
    audit = MappingProxyType({**audit,
        "electrical_source_extent_mol": electrical_source.hydrogen_consumed_mol,
        "native_vs_electrical_extent_residual_mol": MappingProxyType(electrical_extent_residual),
        "native_vs_electrical_mass_residual_kg": MappingProxyType(electrical_mass_residual),
        "native_vs_electrical_within_declared_budgets": (
            all(abs(value) <= audit["mole_budget_mol"] for value in electrical_extent_residual.values())
            and all(abs(value) <= audit["mass_budget_kg"] for value in electrical_mass_residual.values())
        ),
    })
    native = tuple(compartments.native_traces.values())
    change = fsum(trace.snapshots[-1].internal_energy_j-trace.snapshots[0].internal_energy_j
                  for trace in native)
    transport = fsum(float(trace.integral("inlet:enthalpy")[-1]-trace.integral("inlet:enthalpy")[0]
                          -trace.integral("outlet:enthalpy")[-1]+trace.integral("outlet:enthalpy")[0])
                     for trace in native)
    compartment_heat = fsum(float(trace.integral("wall:heat")[-1]-trace.integral("wall:heat")[0]) for trace in native)
    solid = fsum(stage.internal_energy_change_j for stage in thermal_source.stages)
    coolant = thermal_source.reservoir.mass_kg*(thermal_source.final_coolant_state.enthalpy_j_kg
                                               -thermal_source.initial_coolant_state.enthalpy_j_kg)
    external = fsum(stage.auxiliary_heat_into_j+stage.external_coolant_heat_j
                    for stage in thermal_source.stages)
    residual = change+solid+coolant-electrical_source.electricity_into_j-external-compartment_heat
    return FuelCellCompartmentEnergyLedger(
        compartments, electrical_source, thermal_source, audit, change, transport,
        compartment_heat, solid, coolant, electrical_source.electricity_into_j,
        external, finite(residual, "unresolved combined energy residual"),
        reference_allocation_evidence_id,
    ).require_current()
