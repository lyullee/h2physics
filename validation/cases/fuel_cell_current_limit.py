"""Deferred contract cases for explicit reactant-inventory current limiting."""

from h2physics.cluster_validation import ValidationCase, ValidationOutcome


def cases():
    return (
        ValidationCase(
            identifier="fuel-cell-reactant-current-limit-boundary",
            profile="fuel-cell-native",
            entrypoint=__name__ + ":validate_synthetic_boundary",
            invariants=(
                "apply the smaller Faraday/series-cell/area cap from live H2 and O2 reserves",
                "honor a below-cap caller demand without clipping or changing its sign",
                "return zero current at or below either declared reserve",
                "reject a reserve at/below the synchronized driver's independent failure floor",
            ),
        ),
        ValidationCase(
            identifier="fuel-cell-native-reserve-current-limiting",
            profile="fuel-cell-native",
            entrypoint=__name__ + ":validate_native_reserve_run",
            invariants=(
                "use the policy as the native current_density callback with exact stack/floor binding",
                "accepted H2/O2 inventories remain above their explicit reserve and native floor",
                "accepted applied current never exceeds the requested or stoichiometric reserve cap",
                "retain the existing channel/stack energy and component ledgers",
                "report feedback limiting only; do not claim root-localized shutdown or event time",
            ),
        ),
    )


def _stack():
    from h2physics.electrochemistry import HydrogenStack, ReactionEnergy, StackGeometry

    reaction = ReactionEnergy(228000., 241800., "authored-fuel-cell-current-limit", "vapor")
    stack = HydrogenStack(StackGeometry(12, 0.02, 0.00201588),
                          lambda _temperature: reaction, {})
    return stack


def _view(h2_mol, o2_mol):
    from h2physics.adapters.cantera_fuel_cell import NativeFuelCellTrialView
    from h2physics.adapters.fuel_cell_trial import FuelCellTrialGasState

    coordinates = {
        "hydrogen": ("H2", h2_mol, 0.00201588, 150000.),
        "oxygen": ("O2", o2_mol, 0.031998, 145000.),
        "water_vapor": ("H2O", 0.25, 0.01801528, 130000.),
    }
    channels = {}
    for role, (species, amount, molar_mass, pressure) in coordinates.items():
        channels[role] = FuelCellTrialGasState(
            role, species, 1.0, "synthetic-current-limit-clock", pressure, 315.,
            0.02, 1.0, amount, molar_mass, 100000., role+"-activity-reference",
            role+"-current-limit-state")
    return NativeFuelCellTrialView(1.0, "synthetic-current-limit-clock", 330., channels)


def validate_synthetic_boundary(*, work_directory, **parameters):
    del work_directory, parameters
    from h2physics.adapters.fuel_cell_current_limit import FuelCellReactantCurrentLimit
    from h2physics.electrochemistry import FARADAY_C_MOL

    stack = _stack()
    # The declared oxygen reserve yields a cap near 1608 A/m². Keep this
    # synthetic request above that cap so the boundary selects oxygen.
    demand = lambda _view: 2000.
    policy = FuelCellReactantCurrentLimit(
        stack, demand, hydrogen_reserve_mol=.4, oxygen_reserve_mol=.2,
        solver_inventory_floor_mol=1e-12, response_horizon_s=10.,
        hydrogen_moles_per_electron=.5, oxygen_moles_per_electron=.25,
        stoichiometry_evidence_id="authored-H2-O2-electron-stoichiometry",
        policy_evidence_id="authored-inventory-reserve-policy")
    view = _view(.5, .21)
    decision = policy.decision(view)
    expected_o2_cap = (.01 * FARADAY_C_MOL
        / (.25 * stack.geometry.series_cells * 10. * stack.geometry.active_area_m2))
    assert decision.limiting_reactant == "oxygen"
    assert abs(decision.available_current_density_a_m2 - expected_o2_cap) <= 1e-10
    assert decision.applied_current_density_a_m2 < decision.requested_current_density_a_m2

    unbounded = FuelCellReactantCurrentLimit(
        stack, lambda _view: 10., hydrogen_reserve_mol=.4,
        oxygen_reserve_mol=.2, solver_inventory_floor_mol=1e-12,
        response_horizon_s=10., hydrogen_moles_per_electron=.5,
        oxygen_moles_per_electron=.25,
        stoichiometry_evidence_id="authored-H2-O2-electron-stoichiometry",
        policy_evidence_id="authored-inventory-reserve-policy")
    assert unbounded.decision(_view(1., 1.)).applied_current_density_a_m2 == 10.
    stopped = policy.decision(_view(.4, .21))
    assert stopped.applied_current_density_a_m2 == 0.
    try:
        FuelCellReactantCurrentLimit(
            stack, demand, hydrogen_reserve_mol=1e-12,
            oxygen_reserve_mol=.2, solver_inventory_floor_mol=1e-12,
            response_horizon_s=10., hydrogen_moles_per_electron=.5,
            oxygen_moles_per_electron=.25,
            stoichiometry_evidence_id="authored-H2-O2-electron-stoichiometry",
            policy_evidence_id="authored-inventory-reserve-policy")
    except ValueError:
        pass
    else:
        raise AssertionError("A reserve not above the driver floor was admitted")
    return ValidationOutcome(True, {
        "limiting_reactant": decision.limiting_reactant,
        "available_current_density_a_m2": decision.available_current_density_a_m2,
        "at_reserve_current_density_a_m2": stopped.applied_current_density_a_m2,
    }, ("Synthetic feedback-policy check only; no native event localization or control qualification.",))


def validate_native_reserve_run(*, work_directory, **parameters):
    del work_directory, parameters
    import cantera as ct

    from h2physics.adapters.cantera_fuel_cell import (
        CanteraFuelCellSettings,
        FuelCellThermalPartition,
        StackThermalParameters,
        run_cantera_synchronized_fuel_cell,
    )
    from h2physics.adapters.fuel_cell_current_limit import FuelCellReactantCurrentLimit
    from .cantera_fuel_cell_coupled import _native_inputs

    channels, stack, reaction, energy_reference = _native_inputs(ct)
    settings = CanteraFuelCellSettings(maximum_time_step_s=.002,
        minimum_species_inventory_mol=1e-12,
        energy_absolute_tolerance_j=2e-4,
        component_mole_absolute_tolerance_mol=2e-9)
    initial = {}
    for role in ("hydrogen", "oxygen"):
        channel = channels[role]
        index = channel.phase.species_index(channel.species_id)
        initial[role] = (channel.phase.density_mole*channel.volume_m3
                         *channel.phase.X[index]*1000.)

    policy = FuelCellReactantCurrentLimit(
        stack, lambda _view: 350.,
        hydrogen_reserve_mol=initial["hydrogen"]-1e-4,
        oxygen_reserve_mol=initial["oxygen"]-1e-4,
        solver_inventory_floor_mol=settings.minimum_species_inventory_mol,
        response_horizon_s=10., hydrogen_moles_per_electron=.5,
        oxygen_moles_per_electron=.25,
        stoichiometry_evidence_id="fuel-cell-native-H2-O2-stoichiometry",
        policy_evidence_id="synthetic-reserve-taper-policy")
    thermal = StackThermalParameters(500., 298.15, 333.15, 300., 3.,
        energy_reference, "authored-lumped-stack-and-coolant-boundary")

    def heat_partition(view, exchange, native_hdot):
        return FuelCellThermalPartition(0., 0., 0.,
            exchange.stack_result.electric_input_w-native_hdot,
            "authored-all-residual-to-stack")

    trace = run_cantera_synchronized_fuel_cell(
        channels=channels, stack=stack, standard_reaction_energy=reaction,
        thermal=thermal, current_density=policy, thermal_partition=heat_partition,
        time_s=(0., .05, .1, .2), clock_id="fuel-cell-current-limit-clock",
        run_evidence_id="synthetic-current-limit-native-run",
        energy_reference_id=energy_reference, settings=settings)
    trace.require_current()
    applied = []
    for point in trace.accepted:
        decision = policy.decision(point.trial_view)
        current = point.exchange.trial.current_density_a_m2
        assert 0. <= current <= 350.
        assert abs(current-decision.applied_current_density_a_m2) <= 1e-12
        for role, reserve in (("hydrogen", policy.hydrogen_reserve_mol),
                              ("oxygen", policy.oxygen_reserve_mol)):
            channel = point.channels[role]
            species_index = channel.species.index(channels[role].species_id)
            amount = channel.species_moles_mol[species_index]
            assert amount > reserve > settings.minimum_species_inventory_mol
        applied.append(current)
    assert max(applied) < 350.
    return ValidationOutcome(True, {
        "accepted_times_s": tuple(point.time_s for point in trace.accepted),
        "applied_current_density_a_m2": tuple(applied),
        "minimum_inventory_reserves_mol": (
            policy.hydrogen_reserve_mol, policy.oxygen_reserve_mol),
        "maximum_component_mole_residual_mol": trace.maximum_component_mole_residual_mol,
    }, ("Accepted-trial feedback policy only; no root-localized shutdown event.",))
