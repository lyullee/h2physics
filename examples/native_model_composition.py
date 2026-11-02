"""Lazy recipes for existing native model APIs; import performs no calculation.

Every quantity, property owner, native state, tolerance and evidence identity is
supplied by the calling research application. Call ``prepared.run()`` only in
the intended execution environment. No example parameter value is fabricated.
"""

from dataclasses import dataclass
from functools import partial


@dataclass(frozen=True, slots=True)
class PreparedNativeOperation:
    owner: object
    run: object
    interpretation: str


def prepare_finite_coolant_stack(*, stack, stack_boundary, coolant_properties,
                                 coolant_mass_kg, coolant_pressure_pa,
                                 coolant_temperature_bounds_k, external_coolant_heat_w,
                                 coolant_boundary_id, clock_id, coolant_evidence_id,
                                 initial_stack_temperature_k, initial_coolant_state,
                                 stages, relative_tolerance, absolute_tolerance,
                                 energy_tolerance_j):
    """Prepare the shared stack solver with one finite constant-P liquid coolant.

    ``stack`` is HydrogenStack, ``stack_boundary`` is ThermalStackBoundary and
    ``stages`` contains ThermalStackStage objects. ``coolant_properties`` supplies
    basis/state_ph; the initial ThermoState must belong to that provider. The heat
    callback accepts time_s, clock_id, state and returns W into coolant. Stage
    currents use A/m2, all temperatures K, pressure Pa absolute, mass kg, time s.
    Coolant phase and cp gates are enforced when the original owner runs.
    """
    from h2physics.electrochemical_thermal import FiniteCoolantReservoir, FiniteThermalStack

    reservoir = FiniteCoolantReservoir(
        coolant_mass_kg, coolant_pressure_pa, coolant_properties,
        coolant_temperature_bounds_k, external_coolant_heat_w, coolant_boundary_id,
        clock_id, coolant_evidence_id,
    )
    owner = FiniteThermalStack(
        stack, stack_boundary, relative_tolerance=relative_tolerance,
        absolute_tolerance=absolute_tolerance, energy_tolerance_j=energy_tolerance_j,
    )
    return PreparedNativeOperation(
        owner,
        partial(owner.run_with_coolant, initial_stack_temperature_k,
                initial_coolant_state, tuple(stages), reservoir=reservoir),
        "shared stack temperature plus finite liquid enthalpy; fixed coolant pressure/mass",
    )


def prepare_separated_compartments(*, stack, compartment_definitions,
                                   electrical_command, evidence_id, time_s, clock_id,
                                   support_start_s, support_end_s, maximum_time_step_s,
                                   relative_tolerance, absolute_tolerance,
                                   minimum_inventory_kg, energy_ledger_scale_j):
    """Prepare three separate original frozen Cantera gas-volume owners.

    Each definition is a mapping matching FuelCellGasCompartment: compartment_id,
    role (hydrogen/oxygen/water_vapor), species_name, owner (CanteraOpenGasVolume),
    initial_state and exchange_state (ReactiveState), volume_m3, heat_boundaries,
    molar_mass_kg_mol and evidence_id. The caller constructs native phases and
    reviews mechanism/reference applicability. The deterministic command takes
    absolute time_s and returns (current_density_A_m2, stack_temperature_K).
    Native adaptive callback support must extend beyond the final output time
    by the declared maximum step. Pressure evolves independently in each volume;
    it does not feed back into the shared stack polarization.
    """
    from h2physics.adapters.fuel_cell_compartments import (
        FuelCellGasCompartment,
        SeparatedFuelCellCompartments,
    )

    compartments = tuple(FuelCellGasCompartment(**dict(definition))
                         for definition in compartment_definitions)
    owner = SeparatedFuelCellCompartments(
        stack, compartments, electrical_command, evidence_id=evidence_id,
    )
    return PreparedNativeOperation(
        owner,
        partial(owner.run, tuple(time_s), clock_id=clock_id,
                support_start_s=support_start_s, support_end_s=support_end_s,
                maximum_time_step_s=maximum_time_step_s,
                relative_tolerance=relative_tolerance, absolute_tolerance=absolute_tolerance,
                minimum_inventory_kg=minimum_inventory_kg,
                energy_ledger_scale_j=energy_ledger_scale_j),
        "separate finite native gas inventories with prescribed Faraday operation",
    )


def prepare_phase_selective_separator(*, native_owner, initial_state, bridge,
                                      material_species_id, duration_s, maximum_step_s,
                                      start_time_s, clock_id, phase_flows,
                                      ambient_temperature_k, phase_assignment_evidence_id,
                                      phase_domains, mass_tolerance_kg, energy_tolerance_j,
                                      minimum_liquid_inventory_kg, minimum_vapor_inventory_kg,
                                      wall_heat_callback, fluid_heat_callback):
    """Prepare original pure-hydrogen native StratifiedTank phase-selective flow.

    ``native_owner`` is an actual StratifiedTank sharing ``bridge.native``;
    ``initial_state`` is its native two-region finite inventory. ``phase_flows``
    receives absolute physical time and native thermo and returns distinct native
    (liquid_flows, vapor_flows) sequences of MassEnergyFlow. Positive kg/s enters
    the assigned phase; native outgoing enthalpy follows its actual phase state.
    ``phase_domains`` maps liquid/vapor to caller state-admission functions. Heat
    callbacks retain their original native contracts and may explicitly be None.
    This is pure-fluid storage/withdrawal, not a mixture equilibrium flash.
    """
    from h2physics.adapters.finite_separator import run_finite_pure_fluid_separator

    return PreparedNativeOperation(
        native_owner,
        partial(run_finite_pure_fluid_separator, native_owner, initial_state,
                bridge=bridge, material_species_id=material_species_id,
                duration_s=duration_s, maximum_step_s=maximum_step_s,
                start_time_s=start_time_s, clock_id=clock_id, phase_flows=phase_flows,
                ambient_temperature_k=ambient_temperature_k,
                phase_assignment_evidence_id=phase_assignment_evidence_id,
                phase_domains=dict(phase_domains), mass_tolerance_kg=mass_tolerance_kg,
                energy_tolerance_j=energy_tolerance_j,
                minimum_liquid_inventory_kg=minimum_liquid_inventory_kg,
                minimum_vapor_inventory_kg=minimum_vapor_inventory_kg,
                wall_heat_callback=wall_heat_callback, fluid_heat_callback=fluid_heat_callback),
        "original native two-region phase-selective finite pure-hydrogen storage",
    )


__all__ = ["PreparedNativeOperation", "prepare_finite_coolant_stack",
           "prepare_separated_compartments", "prepare_phase_selective_separator"]
