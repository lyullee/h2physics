"""Deferred contract for one-native-network fuel-cell coupling."""

from h2physics.cluster_validation import ValidationCase, ValidationOutcome


def cases():
    return (
        ValidationCase(
            identifier="cantera-native-synchronized-fuel-cell-thermal-coupling",
            profile="fuel-cell-native",
            entrypoint=__name__ + ":validate_contract",
            parameters={},
            invariants=(
            "three distinct ideal-gas Cantera mole reactors and one scalar stack-temperature state share one ReactorNet",
            "every native RHS exchange uses live exact-time H2/O2/H2O phase states and caller current policy",
            "native pressure/composition feed shared activity and HydrogenStack voltage at fixed requested current",
            "stack hydrogen molar mass uses native Cantera kg/kmol converted to matching kg/mol without weakening the guard",
            "species source rates, native partial enthalpy transfer and caller heat partition close at each RHS evaluation",
            "finite stack sensible energy, assigned stack heat and coolant transfer close independently",
            "accepted snapshots retain exact channel histories; a failed RHS retains the native trial and accepted prefix",
            "reactant floor failure does not invent current limiting, shutdown or event localization",
            ),
        ),
        ValidationCase(
            identifier="cantera-native-fuel-cell-zero-current-boundary",
            profile="fuel-cell-native",
            entrypoint=__name__ + ":validate_zero_current",
            parameters={},
            invariants=(
                "zero current is admitted as a native isolated-compartment limit",
                "all native species source rates and reaction-energy terms remain exactly zero",
                "the finite thermal and gas inventory histories remain unchanged under zero coolant conductance",
            ),
        ),
        ValidationCase(
            identifier="cantera-fuel-cell-coolant-heat-duty-handoff",
            profile="fuel-cell-native",
            entrypoint=__name__ + ":validate_coolant_heat_duty",
            parameters={},
            invariants=(
                "native accepted cumulative coolant-to-stack joules project to exact source-clock interval bins",
                "sign convention remains heat into stack from the declared coolant boundary",
                "only exact accepted window endpoints are admitted",
                "the handoff does not claim recoverable utility heat or a heat exchanger",
            ),
        ),
    )


def _native_inputs(ct):
    from h2physics.adapters.cantera_fuel_cell import CanteraFuelCellChannel, StackThermalParameters
    from h2physics.electrochemistry import HydrogenStack, ReactionEnergy, StackGeometry

    energy_reference = "caller-qualified-cantera-mechanism-enthalpy-reference"
    channels = {}
    initial = {
        "hydrogen": ("H2:0.8, AR:0.2", 315.0, 150000.0),
        "oxygen": ("O2:0.7, AR:0.3", 318.0, 145000.0),
        "water_vapor": ("H2O:0.6, AR:0.4", 322.0, 130000.0),
    }
    species = {"hydrogen": "H2", "oxygen": "O2", "water_vapor": "H2O"}
    volumes = {"hydrogen": .02, "oxygen": .025, "water_vapor": .015}
    for role in ("hydrogen", "oxygen", "water_vapor"):
        phase = ct.Solution("h2o2.yaml")
        composition, temperature, pressure = initial[role]
        phase.TPX = temperature, pressure, composition
        channels[role] = CanteraFuelCellChannel(role, phase, species[role], volumes[role],
            100000., role+"-reference-pressure", energy_reference, role+"-native-channel")

    reaction = ReactionEnergy(228000., 241800., "authored-vapor-reaction-energy", "vapor")
    # Cantera reports molecular weights in kg/kmol and its mechanism's atomic
    # weights need not equal the rounded externally authored H2 molar mass.
    # Derive the stack's kg/mol value from this exact native phase so the
    # coupling's strict mass-basis identity check compares like with like.
    hydrogen_phase = channels["hydrogen"].phase
    hydrogen_index = hydrogen_phase.species_index("H2")
    hydrogen_molar_mass_kg_mol = float(hydrogen_phase.molecular_weights[hydrogen_index])/1000.
    stack = HydrogenStack(
        StackGeometry(12, .02, hydrogen_molar_mass_kg_mol),
        lambda _temperature: reaction, {},
    )
    return channels, stack, reaction, energy_reference


def _authored_stack_heat_partition(view, exchange, native_species_enthalpy_rate_w):
    """Keep the synthetic callback module-level, with no captured class object."""
    from h2physics.adapters.cantera_fuel_cell import FuelCellThermalPartition

    # This authored allocation sends the complete balance to the finite stack
    # node. The API requires real applications to own this choice.
    return FuelCellThermalPartition(
        0., 0., 0., exchange.stack_result.electric_input_w-native_species_enthalpy_rate_w,
        "authored-all-residual-to-stack",
    )


def _zero_current_no_heat(view, exchange, native_species_enthalpy_rate_w):
    """Stable module-level callback for the zero-current synthetic boundary."""
    from h2physics.adapters.cantera_fuel_cell import FuelCellThermalPartition

    del view, exchange, native_species_enthalpy_rate_w
    return FuelCellThermalPartition(0., 0., 0., 0., "zero-current-no-heat")


def _authored_constant_current(view):
    """Stable module-level command for the authored 350 A/m2 case."""
    del view
    return 350.0


def _zero_current_command(view):
    """Stable module-level command for the isolated zero-current limit."""
    del view
    return 0.0


def validate_contract(*, work_directory, **parameters):
    del work_directory, parameters
    import cantera as ct

    from h2physics.adapters.cantera_fuel_cell import (
        CanteraFuelCellSettings,
        StackThermalParameters,
        run_cantera_synchronized_fuel_cell,
    )
    clock = "authored-native-fuel-cell-clock"
    run_id = "synthetic-separated-channel-reactor-network"
    channels, stack, reaction, energy_reference = _native_inputs(ct)
    thermal = StackThermalParameters(500., 298.15, 333.15, 300., 3.,
        energy_reference, "authored-lumped-stack-and-coolant-boundary")

    trace = run_cantera_synchronized_fuel_cell(
        channels=channels, stack=stack, standard_reaction_energy=reaction,
        thermal=thermal, current_density=_authored_constant_current,
        thermal_partition=_authored_stack_heat_partition, time_s=(0., .05, .1, .2),
        clock_id=clock, run_evidence_id=run_id,
        energy_reference_id=energy_reference,
        settings=CanteraFuelCellSettings(maximum_time_step_s=.005,
            energy_absolute_tolerance_j=2e-4,
            component_mole_absolute_tolerance_mol=2e-9))
    assert trace.require_current() is trace
    assert len(trace.native.reactors) == 3
    assert trace.native.network.reactors == list(trace.native.reactors)
    assert len(trace.accepted) == 4
    assert all(point.trial_view.time_s == point.time_s for point in trace.accepted)
    assert all(point.exchange.trial.current_density_a_m2 == 350. for point in trace.accepted)
    assert trace.accepted[0].channels["hydrogen"].pressure_pa != trace.accepted[-1].channels["hydrogen"].pressure_pa
    assert trace.accepted[0].exchange.stack_result.electric_input_w != trace.accepted[-1].exchange.stack_result.electric_input_w
    assert trace.maximum_component_mole_residual_mol <= 2e-9
    assert max(abs(trace.maximum_channel_energy_residual_j), abs(trace.stack_energy_residual_j),
               abs(trace.combined_energy_residual_j)) <= .01
    assert trace.accepted[0].stack_temperature_k != trace.accepted[-1].stack_temperature_k

    return ValidationOutcome(True, {
        "accepted_output_times_s": tuple(point.time_s for point in trace.accepted),
        "reactor_count": len(trace.native.reactors),
        "hydrogen_pressure_pa_initial_final": (
            trace.accepted[0].channels["hydrogen"].pressure_pa,
            trace.accepted[-1].channels["hydrogen"].pressure_pa),
        "cell_voltage_v_initial_final": (
            trace.accepted[0].exchange.stack_result.cell_voltage_v,
            trace.accepted[-1].exchange.stack_result.cell_voltage_v),
        "stack_temperature_k_initial_final": (
            trace.accepted[0].stack_temperature_k,
            trace.accepted[-1].stack_temperature_k),
        "maximum_component_mole_residual_mol": trace.maximum_component_mole_residual_mol,
        "maximum_channel_energy_residual_j": trace.maximum_channel_energy_residual_j,
        "stack_energy_residual_j": trace.stack_energy_residual_j,
        "combined_energy_residual_j": trace.combined_energy_residual_j,
    }, ("Synthetic Cantera 3.2 native-coupling contract only; no material, membrane, stack-control or device qualification",))


def validate_zero_current(*, work_directory, **parameters):
    del work_directory, parameters
    import cantera as ct

    from h2physics.adapters.cantera_fuel_cell import (
        CanteraFuelCellSettings,
        StackThermalParameters,
        run_cantera_synchronized_fuel_cell,
    )

    channels, stack, reaction, energy_reference = _native_inputs(ct)
    thermal = StackThermalParameters(500., 298.15, 333.15, 300., 0.,
        energy_reference, "authored-adiabatic-zero-current-stack")

    trace = run_cantera_synchronized_fuel_cell(
        channels=channels, stack=stack, standard_reaction_energy=reaction,
        thermal=thermal, current_density=_zero_current_command, thermal_partition=_zero_current_no_heat,
        time_s=(0., .05, .1), clock_id="zero-current-common-clock",
        run_evidence_id="zero-current-isolated-compartments",
        energy_reference_id=energy_reference,
        settings=CanteraFuelCellSettings(maximum_time_step_s=.005))
    assert trace.require_current() is trace
    first, last = trace.accepted[0], trace.accepted[-1]
    assert all(point.exchange.stack_result.current_a == 0. for point in trace.accepted)
    assert all(all(rate == 0. for rate in point.exchange.species_molar_rate_into_cv_mol_s.values())
               for point in trace.accepted)
    for role in ("hydrogen", "oxygen", "water_vapor"):
        assert first.channels[role].species_moles_mol == last.channels[role].species_moles_mol
        assert first.channels[role].internal_energy_j == last.channels[role].internal_energy_j
    assert first.stack_temperature_k == last.stack_temperature_k
    return ValidationOutcome(True, {
        "accepted_output_times_s": tuple(point.time_s for point in trace.accepted),
        "all_reaction_rates_zero": True,
        "maximum_component_mole_residual_mol": trace.maximum_component_mole_residual_mol,
        "combined_energy_residual_j": trace.combined_energy_residual_j,
    }, ("Synthetic zero-current limit only; no independent device validation",))


def validate_coolant_heat_duty(*, work_directory, **parameters):
    del work_directory, parameters
    import cantera as ct
    import numpy as np

    from h2physics.adapters.cantera_fuel_cell import (
        CanteraFuelCellSettings, StackThermalParameters,
        run_cantera_synchronized_fuel_cell,
    )
    from h2physics.adapters.cantera_fuel_cell_coolant_heat import (
        bind_cantera_fuel_cell_coolant_heat,
    )
    from h2physics.adapters.thermal_utilities import HeatWindow

    channels, stack, reaction, energy_reference = _native_inputs(ct)
    thermal = StackThermalParameters(
        500., 298.15, 333.15, 300., 3., energy_reference,
        "authored-coolant-duty-boundary",
    )
    trace = run_cantera_synchronized_fuel_cell(
        channels=channels, stack=stack, standard_reaction_energy=reaction,
        thermal=thermal, current_density=_authored_constant_current,
        thermal_partition=_authored_stack_heat_partition,
        time_s=(0., .05, .1, .2), clock_id="authored-fuel-cell-duty-clock",
        run_evidence_id="authored-fuel-cell-coolant-duty-source",
        energy_reference_id=energy_reference,
        settings=CanteraFuelCellSettings(maximum_time_step_s=.005),
    )
    window = HeatWindow(0., .2, trace.clock_id, "authored-coolant-duty-window")
    duty = bind_cantera_fuel_cell_coolant_heat(trace, window)
    duty.require_current()
    accepted = np.asarray([point.stack_coolant_energy_into_j for point in trace.accepted])
    assert np.array_equal(duty.snapshot.edges_s, np.asarray([p.time_s for p in trace.accepted]))
    assert np.array_equal(duty.snapshot.heat_into_process_j, np.diff(accepted))
    assert duty.snapshot.scope == "external-device-heat"
    return ValidationOutcome(True, {
        "accepted_intervals": len(duty.snapshot.heat_into_process_j),
        "coolant_heat_into_stack_j": tuple(float(value) for value in duty.snapshot.heat_into_process_j),
        "energy_basis_id": duty.snapshot.energy_basis_id,
    }, ("Synthetic native coupling only; coolant ledger does not prove a recoverable downstream utility",))
