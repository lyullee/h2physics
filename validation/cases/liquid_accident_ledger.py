"""Deferred exhaustive original liquid accident branch accounting."""

from h2physics.cluster_validation import ValidationCase, ValidationOutcome


def cases():
    return (
        ValidationCase(identifier="liquid-accident-exhaustive-mass-ledger", profile="droplet-impact",
            entrypoint=__name__+":validate_contract", parameters={}, invariants=(
                "original flash/flight/unit-contact/pool parent identities retained",
                "flash and impact vapor, rebound and unselected liquid stay explicit",
                "deposited intermediate transfer excluded from terminal sum",
                "all intermediate and final mass residuals satisfy explicit budgets",
                "mass ledger construction requires a single-use binding-factory receipt")),
        ValidationCase(identifier="liquid-accident-pool-energy-handoff", profile="droplet-impact",
            entrypoint=__name__+":validate_pool_energy_handoff", parameters={
                "fixture_module": "REPLACE_WITH_NATIVE_POOL_ENERGY_FIXTURE_MODULE",
                "fixture_builder": "build_original_accident_and_pool_energy_receipts",
            }, invariants=(
                "pool-energy-ledger-belongs-to-exact-original-continuation",
                "pool-window-and-reference-are-retained-by-native-owner",
                "stage-residuals-remain-separate",
                "global-accident-energy-closure-remains-false",
                "energy-diagnostics-require-a-builder-issued-token")),
    )


def validate_contract(*, work_directory, **parameters):
    from dataclasses import replace
    from math import fsum

    from dynamiclh2poolx import FixedAreaPoolConfig, Substrate

    from examples.droplet_impact import build_model
    from h2physics.adapters.droplet_transport import (
        BoilingHeat,
        ParcelBoundary,
        SaturatedParcelFlight,
    )
    from h2physics.adapters.liquid_accident_ledger import liquid_accident_mass_ledger_from_scenario
    from h2physics.adapters.liquid_release_chain import liquid_release_scenario
    from h2physics.adapters.parcel_population import ParcelPopulationGroup

    impact_owner = build_model()
    properties = impact_owner.properties
    location = impact_owner.patch.location

    def groups(flash):
        return (ParcelPopulationGroup("selected", 1, flash.liquid_mass_kg*.6,
                    (0., 0., 1.), (0., 0., -1.), "authored-selected"),
                ParcelPopulationGroup("unselected", 2, flash.liquid_mass_kg*.2,
                    (0., 0., 1.), (0., 0., -1.), "authored-unselected"))

    def flight(flash):
        return SaturatedParcelFlight(properties, 101325., ParcelBoundary(location.clock_id,
            location.coordinate_frame_id, "authored-fixed-carrier", .01, 1e-5,
            (0., 0., -1.), (0., 0., 0.), 1e5, 1., .002, .01),
            lambda state: BoilingHeat(0., "authored-adiabatic-flight"),
            force_approximation_evidence_id="authored-isolated-parcel")

    def pool_options(member):
        start = member.impact_result.steps[0].contact_end_s
        config = FixedAreaPoolConfig(area_m2=.01, initial_liquid_mass_kg=0.,
            substrate=Substrate("authored-separate-substrate", .2, 1e-7),
            ambient_temperature_K=80., ambient_pressure_Pa=101325., initial_thermal_age_s=.01)
        return dict(native_config=config, separate_continuation_heat_owner=config.substrate,
            continuation_evidence_id="authored-pool-stock", reference_properties=properties,
            vapor_location=location, output_times_s=(start, start+.01, start+.1))

    scenario = liquid_release_scenario(scenario_id="authored-exhaustive-mass",
        properties=properties, upstream_state=properties.saturated(.8e6, 0.),
        downstream_pressure_pa=101325., total_release_mass_kg=1e-6,
        phase_equilibrium_evidence_id="authored-equilibrium", population_factory=groups,
        flight_owner_factory=flight, flight_options=dict(start_s=100., end_s=102.,
            residual_mass_floor_kg=1e-12, maximum_step_s=.01, relative_tolerance=1e-10,
            absolute_tolerances=(1e-12,)*17, ground_z_m=0.),
        distribution_evidence_id="authored-population", impact_group_id="selected",
        impact_owner_factory=lambda population: impact_owner, pool_options_factory=pool_options)
    result = scenario.run()
    ledger = liquid_accident_mass_ledger_from_scenario(result,
        absolute_mass_tolerance_kg=1e-12, relative_mass_tolerance=1e-8)
    from h2physics.adapters.liquid_accident_ledger import LiquidAccidentMassLedger
    try:
        LiquidAccidentMassLedger(ledger.population, ledger.member_impact, ledger.pool,
            ledger.terminal_branches_kg, ledger.intermediate_transfers_kg,
            ledger.residuals_kg, ledger.absolute_mass_tolerance_kg,
            ledger.relative_mass_tolerance)
    except TypeError:
        pass
    else:
        raise AssertionError("Direct construction exposed an unissued accident mass ledger")
    from h2physics.adapters.liquid_accident_energy import liquid_accident_energy_diagnostics
    energy = liquid_accident_energy_diagnostics(ledger)
    energy.require_current()
    from h2physics.adapters.liquid_accident_energy import LiquidAccidentEnergyDiagnostics
    try:
        LiquidAccidentEnergyDiagnostics(
            ledger, energy.stage_energy_j, energy.unresolved_energy_terms,
            False, None,
        )
    except TypeError:
        pass
    else:
        raise AssertionError("Direct construction exposed an unissued energy diagnostic receipt")
    assert energy.mass_ledger is ledger
    assert not energy.global_energy_balance_closed
    assert any("substrate cumulative heat" in term for term in energy.unresolved_energy_terms)
    assert energy.stage_energy_j["flash_phase_enthalpy_residual_j"] == result.results["population"].initial_flash.enthalpy_residual_j
    try:
        replace(energy).require_current()
    except (TypeError, ValueError):
        pass
    else:
        raise AssertionError("Detached stage energy diagnostic retained issuance")
    assert ledger.terminal_branches_kg["unselected_liquid_kg"] > 0.
    assert ledger.terminal_branches_kg["initial_flash_vapor_kg"] > 0.
    assert "deposited_stock_transfer_kg" not in ledger.terminal_branches_kg
    assert abs(fsum(ledger.terminal_branches_kg.values())-1e-6) < 1e-12
    try:
        replace(ledger).require_current()
    except (TypeError, ValueError):
        pass
    else:
        raise AssertionError("Detached exhaustive ledger retained issuance")
    return ValidationOutcome(True, dict(ledger.residuals_kg),
        ("Conditional synthetic distribution/contact/substrate; un-routed branches remain explicit",))


def validate_pool_energy_handoff(*, work_directory, **parameters):
    """Use an explicit source/project fixture; do not synthesize a native energy owner."""
    import importlib

    module_name = parameters.get("fixture_module")
    builder_name = parameters.get("fixture_builder")
    if (not isinstance(module_name, str) or not module_name.strip()
            or "REPLACE_WITH" in module_name or not isinstance(builder_name, str)
            or not builder_name.isidentifier()):
        raise ValueError("Configure a reviewed project fixture for original accident and pool-energy receipts")
    module = importlib.import_module(module_name)
    builder = getattr(module, builder_name, None)
    if not callable(builder):
        raise ValueError("Pool-energy handoff fixture must expose the configured builder")
    values = builder(work_directory=work_directory, parameters=parameters)
    if not isinstance(values, dict) or set(values) != {"mass_ledger", "pool_energy_ledger"}:
        raise TypeError("Fixture must return the original mass_ledger and native pool_energy_ledger")
    from h2physics.adapters.liquid_accident_energy import liquid_accident_energy_diagnostics

    receipt = liquid_accident_energy_diagnostics(
        values["mass_ledger"], pool_energy_ledger=values["pool_energy_ledger"])
    receipt.require_current()
    assert receipt.pool_energy_ledger is values["pool_energy_ledger"]
    assert receipt.pool_energy_ledger.continuation is receipt.mass_ledger.pool
    assert receipt.global_energy_balance_closed is False
    assert not any("pool substrate cumulative heat" in item for item in receipt.unresolved_energy_terms)
    assert not any("Pool remaining-liquid U" in item for item in receipt.unresolved_energy_terms)
    return ValidationOutcome(True, {
        "pool_edges": len(receipt.pool_energy_ledger.time_s),
        "mass_ledger_bound": 1,
        "global_energy_balance_closed": 0,
    }, (
        "Pool energy is an independently retained control-volume receipt; stage residuals are not summed.",
        "The fixture must use a native owner that exposes accepted-edge cumulative energy fields.",
    ))
