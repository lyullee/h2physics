"""Deferred native acceptance contracts for hydrogen fuel compression."""

from h2physics.cluster_validation import ValidationCase, ValidationOutcome

LIMITS = (
    "Cantera owns the ideal-gas path; the separate CoolProp path admits direct HEOS only.",
    "Efficiency, source state, throughput and discharge target are caller supplied.",
    "No compressor map, intercooling, transient control or machine qualification.",
)


def cases():
    return (
        ValidationCase(
            identifier="hydrogen-fuel-compression-native",
            profile="hydrogen-engine",
            entrypoint=__name__ + ":validate_native_compression",
            invariants=(
                "pure-h2-state-admission", "native-isentropic-pressure-reference",
                "caller-efficiency-enthalpy-rise", "mass-flow-scaled-shaft-power",
                "adiabatic-energy-ledger", "native-phase-currentness",
                "input-state-and-output-payload-seal",
            ),
        ),
        ValidationCase(
            identifier="hydrogen-fuel-compression-brayton-coupling",
            profile="hydrogen-engine",
            entrypoint=__name__ + ":validate_brayton_coupling",
            invariants=(
                "fuel-discharge-matches-combustor-pressure-temperature",
                "fuel-flow-matches-cycle-mixture-ratio", "same-mechanism-and-window-labels",
                "actual-native-mechanism-signature-matches", "fuel-compressor-power-subtracted-from-cycle",
                "nested-input-and-derived-link-seals", "source-state-mutation-rejected",
            ),
        ),
        ValidationCase(
            identifier="hydrogen-fuel-compression-input-guards",
            profile="hydrogen-engine",
            entrypoint=__name__ + ":validate_input_guards",
            invariants=(
                "discharge-pressure-above-source", "efficiency-range", "finite-positive-flow",
                "evidence-identities", "non-hydrogen-phase-rejected",
            ),
        ),
        ValidationCase(
            identifier="hydrogen-real-fluid-compression",
            profile="hydrogen-engine",
            entrypoint=__name__ + ":validate_real_fluid_compression",
            invariants=(
                "injected-coolprop-heos-provider-retained", "PT-inlet-PS-reference-PH-outlet",
                "property-basis-version-and-backend-retained", "single-phase-hydrogen-domain",
                "efficiency-enthalpy-rise", "exact-shaft-energy-ledger",
                "issued-state-provider-version-and-basis-currentness",
            ),
        ),
        ValidationCase(
            identifier="hydrogen-real-fluid-compression-guards",
            profile="hydrogen-engine",
            entrypoint=__name__ + ":validate_real_fluid_guards",
            invariants=(
                "liquid-state-rejected", "nonhydrogen-provider-rejected",
                "caller-temperature-domain-enforced", "caller-pressure-domain-enforced",
                "provider-backend-version-basis-stale-state-rejected",
            ),
        ),
        ValidationCase(
            identifier="hydrogen-compression-finite-mixture-storage-handoff",
            profile="mixture-vle",
            entrypoint=__name__ + ":validate_storage_handoff",
            invariants=(
                "compressor-native-hydrogen-fluid-matches-receiver-template",
                "common-coolprop-energy-reference-is-explicit",
                "receiver-pressure-must-be-below-compressor-discharge",
                "constant-flow-duration-converts-mass-to-species-moles",
                "outlet-enthalpy-is-carried-as-integrated-vapor-inlet-energy",
                "finite-v-u-vessel-accepts-the-produced-typed-interval",
                "receiver-and-interval-mutation-invalidates-handoff",
            ),
        ),
    )


def _inputs(**overrides):
    from h2physics.combustion.fuel_compression import HydrogenCompressionInputs

    values = dict(
        mechanism_id="cantera-gri30-fuel-compressor-example",
        process_window_id="steady-point-fuel",
        inlet_temperature_k=298.15,
        inlet_pressure_pa=300_000.0,
        discharge_pressure_pa=800_000.0,
        hydrogen_mass_flow_kg_s=0.04,
        isentropic_efficiency=0.78,
        state_evidence_id="authored-source-boundary",
        efficiency_evidence_id="authored-compressor-parameter",
    )
    values.update(overrides)
    return HydrogenCompressionInputs(**values)


def _cycle_inputs(**overrides):
    from h2physics.combustion.open_brayton import OpenBraytonInputs

    values = dict(
        mechanism_id="cantera-gri30-fuel-compressor-example",
        process_window_id="steady-point-fuel",
        air_temperature_k=288.15,
        air_pressure_pa=101325.0,
        air_mole_fractions=(("O2", 0.21), ("N2", 0.79)),
        compressor_pressure_ratio=8.0,
        compressor_isentropic_efficiency=0.86,
        combustor_pressure_recovery=0.97,
        hydrogen_fuel_to_air_mass_ratio=0.02,
        hydrogen_inlet_temperature_k=300.0,
        turbine_exhaust_pressure_pa=101325.0,
        turbine_isentropic_efficiency=0.88,
        hydrogen_lhv_j_kg=120.0e6,
        air_state_evidence_id="authored-air-boundary",
        hydrogen_feed_evidence_id="authored-compressed-fuel",
        machine_parameter_evidence_id="authored-point-data",
        lhv_evidence_id="authored-lhv",
    )
    values.update(overrides)
    return OpenBraytonInputs(**values)


def validate_native_compression(*, work_directory, **parameters):
    del work_directory, parameters
    import cantera as ct

    from h2physics.combustion.fuel_compression import run_hydrogen_compression

    result = run_hydrogen_compression(ct.Solution("gri30.yaml"), _inputs())
    assert result.inlet.station == "fuel_inlet"
    assert result.isentropic_outlet.station == "isentropic_reference"
    assert result.actual_outlet.pressure_pa == result.inputs.discharge_pressure_pa
    assert result.isentropic_outlet.entropy_j_kg_k >= result.inlet.entropy_j_kg_k - 1e-9
    expected_specific = ((result.isentropic_outlet.enthalpy_j_kg
                          - result.inlet.enthalpy_j_kg)
                         / result.inputs.isentropic_efficiency)
    assert abs(result.specific_shaft_work_j_kg-expected_specific) < 1e-8*expected_specific
    assert abs(result.energy_residual_w) <= 1e-10*result.shaft_power_w
    result.require_current()

    original_power = result.shaft_power_w
    object.__setattr__(result, "shaft_power_w", original_power + 1.0)
    rejected_output_mutation = 0
    try:
        result.require_current()
    except ValueError:
        rejected_output_mutation = 1
    assert rejected_output_mutation == 1
    object.__setattr__(result, "shaft_power_w", original_power)

    original_discharge = result.inputs.discharge_pressure_pa
    object.__setattr__(result.inputs, "discharge_pressure_pa", original_discharge + 1.0)
    rejected_input_mutation = 0
    try:
        result.require_current()
    except ValueError:
        rejected_input_mutation = 1
    assert rejected_input_mutation == 1
    object.__setattr__(result.inputs, "discharge_pressure_pa", original_discharge)
    result.require_current()

    original_isentropic_entropy = result.isentropic_outlet.entropy_j_kg_k
    object.__setattr__(result.isentropic_outlet, "entropy_j_kg_k",
                       original_isentropic_entropy + 1.0)
    rejected_state_mutation = 0
    try:
        result.require_current()
    except ValueError:
        rejected_state_mutation = 1
    assert rejected_state_mutation == 1
    object.__setattr__(result.isentropic_outlet, "entropy_j_kg_k",
                       original_isentropic_entropy)
    result.require_current()
    return ValidationOutcome(True, {
        "isentropic_outlet_temperature_k": result.isentropic_outlet.temperature_k,
        "actual_outlet_temperature_k": result.actual_outlet.temperature_k,
        "specific_shaft_work_j_kg": result.specific_shaft_work_j_kg,
        "shaft_power_w": result.shaft_power_w,
        "energy_residual_w": result.energy_residual_w,
        "forged_output_rejected": rejected_output_mutation,
        "mutated_input_rejected": rejected_input_mutation,
        "mutated_reference_state_rejected": rejected_state_mutation,
    }, LIMITS)


def validate_brayton_coupling(*, work_directory, **parameters):
    del work_directory, parameters
    import cantera as ct

    from dataclasses import replace
    from h2physics.combustion.fuel_compression import (
        couple_hydrogen_compression_to_brayton, run_hydrogen_compression)
    from h2physics.combustion.open_brayton import run_open_cycle_brayton

    air_flow = 2.0
    pressure = 101325.0*8.0*0.97
    fuel = run_hydrogen_compression(ct.Solution("gri30.yaml"), _inputs(
        discharge_pressure_pa=pressure,
        hydrogen_mass_flow_kg_s=0.02*air_flow,
    ))
    cycle = run_open_cycle_brayton(ct.Solution("gri30.yaml"), _cycle_inputs(
        hydrogen_inlet_temperature_k=fuel.actual_outlet.temperature_k,
    ))
    linked = couple_hydrogen_compression_to_brayton(
        cycle, fuel, air_mass_flow_kg_s=air_flow, evidence_id="authored-matching-flow-and-pressure")
    assert linked.cycle_shaft_power_w == cycle.net_work_j_kg_air*air_flow
    assert linked.fuel_compressor_power_w == fuel.shaft_power_w
    assert abs(linked.net_after_fuel_compression_w
               -(linked.cycle_shaft_power_w-fuel.shaft_power_w)) < 1e-9
    linked.require_current()

    original_net = linked.net_after_fuel_compression_w
    object.__setattr__(linked, "net_after_fuel_compression_w", original_net + 1.0)
    rejected_output_mutation = 0
    try:
        linked.require_current()
    except ValueError:
        rejected_output_mutation = 1
    assert rejected_output_mutation == 1
    object.__setattr__(linked, "net_after_fuel_compression_w", original_net)

    original_evidence = linked.coupling_evidence_id
    object.__setattr__(linked, "coupling_evidence_id", "forged-link-evidence")
    rejected_evidence_mutation = 0
    try:
        linked.require_current()
    except ValueError:
        rejected_evidence_mutation = 1
    assert rejected_evidence_mutation == 1
    object.__setattr__(linked, "coupling_evidence_id", original_evidence)
    linked.require_current()

    original_air_flow = linked.air_mass_flow_kg_s
    object.__setattr__(linked, "air_mass_flow_kg_s", original_air_flow + 0.1)
    rejected_air_flow_mutation = 0
    try:
        linked.require_current()
    except ValueError:
        rejected_air_flow_mutation = 1
    assert rejected_air_flow_mutation == 1
    object.__setattr__(linked, "air_mass_flow_kg_s", original_air_flow)
    linked.require_current()

    different_phase = ct.Solution("gri30.yaml")
    different_phase.set_multiplier(0.5, 0)
    different_fuel = run_hydrogen_compression(different_phase, _inputs(
        discharge_pressure_pa=pressure,
        hydrogen_mass_flow_kg_s=0.02*air_flow,
    ))
    mechanism_rejected = 0
    try:
        couple_hydrogen_compression_to_brayton(
            cycle, different_fuel, air_mass_flow_kg_s=air_flow,
            evidence_id="same-label-but-different-native-mechanism")
    except ValueError:
        mechanism_rejected = 1
    assert mechanism_rejected == 1

    fuel.native_phase.TP = fuel.native_phase.T + 1.0, fuel.native_phase.P
    rejected = 0
    try:
        linked.require_current()
    except ValueError:
        rejected = 1
    assert rejected == 1
    # dataclasses.replace deliberately replays guards, so the altered native phase
    # cannot silently inherit the old run's state binding.
    forged_rejected = 0
    try:
        replace(fuel, native_phase=fuel.native_phase)
    except (TypeError, ValueError):
        forged_rejected = 1
    assert forged_rejected == 1
    return ValidationOutcome(True, {
        "cycle_shaft_power_w": linked.cycle_shaft_power_w,
        "fuel_compressor_power_w": linked.fuel_compressor_power_w,
        "net_after_fuel_compression_w": linked.net_after_fuel_compression_w,
        "forged_link_output_rejected": rejected_output_mutation,
        "mutated_link_evidence_rejected": rejected_evidence_mutation,
        "mutated_air_flow_rejected": rejected_air_flow_mutation,
        "mismatched_native_mechanism_rejected": mechanism_rejected,
        "mutated_native_phase_rejected": rejected,
        "reissued_trace_rejected": forged_rejected,
    }, LIMITS)


def validate_input_guards(*, work_directory, **parameters):
    del work_directory, parameters
    rejected = 0
    for change in (
        {"discharge_pressure_pa": 300_000.0},
        {"isentropic_efficiency": 1.01},
        {"hydrogen_mass_flow_kg_s": 0.0},
        {"efficiency_evidence_id": " "},
    ):
        try:
            _inputs(**change)
        except ValueError:
            rejected += 1
    assert rejected == 4

    import cantera as ct
    from h2physics.combustion.fuel_compression import run_hydrogen_compression

    run_hydrogen_compression(ct.Solution("gri30.yaml"), _inputs())
    try:
        # The native air mechanism contains no H2 species.
        run_hydrogen_compression(ct.Solution("air.yaml"), _inputs())
    except (ValueError, TypeError):
        rejected += 1
    assert rejected == 5
    return ValidationOutcome(True, {"rejected_inputs": rejected}, LIMITS)


def _real_fluid_inputs(**overrides):
    from h2physics.combustion.fuel_compression import HydrogenRealFluidCompressionInputs

    values = dict(
        provider_id="coolprop-hydrogen-heos",
        process_window_id="steady-real-fluid-fuel",
        inlet_temperature_k=298.15,
        inlet_pressure_pa=300_000.0,
        discharge_pressure_pa=800_000.0,
        hydrogen_mass_flow_kg_s=0.04,
        isentropic_efficiency=0.78,
        temperature_bounds_k=(250.0, 700.0),
        pressure_bounds_pa=(100_000.0, 20_000_000.0),
        state_evidence_id="authored-real-fluid-boundary",
        efficiency_evidence_id="authored-real-fluid-efficiency",
        domain_evidence_id="authored-compressor-domain",
        entropy_relative_tolerance=1e-8,
    )
    values.update(overrides)
    return HydrogenRealFluidCompressionInputs(**values)


def validate_real_fluid_compression(*, work_directory, **parameters):
    del work_directory, parameters
    from h2physics.combustion.fuel_compression import run_real_fluid_hydrogen_compression
    from h2physics.thermo import CoolPropProperties

    provider = CoolPropProperties("Hydrogen", backend="HEOS")
    result = run_real_fluid_hydrogen_compression(provider, _real_fluid_inputs())
    assert result.provider is provider
    assert result.provider_version == provider.version
    assert result.property_basis == provider.basis
    assert abs(result.inlet.pressure_pa-result.inputs.inlet_pressure_pa) <= 1e-8*result.inputs.inlet_pressure_pa
    assert abs(result.actual_outlet.pressure_pa-result.inputs.discharge_pressure_pa) <= 1e-8*result.inputs.discharge_pressure_pa
    assert all(state.density_kg_m3 > 0.0 for state in (
        result.inlet, result.isentropic_outlet, result.actual_outlet))
    assert result.isentropic_outlet.entropy_j_kg_k == result.inlet.entropy_j_kg_k or abs(
        result.isentropic_outlet.entropy_j_kg_k-result.inlet.entropy_j_kg_k
    ) <= max(1e-5, result.inputs.entropy_relative_tolerance*abs(result.inlet.entropy_j_kg_k))
    expected_work = ((result.isentropic_outlet.enthalpy_j_kg-result.inlet.enthalpy_j_kg)
                     / result.inputs.isentropic_efficiency)
    assert abs(result.specific_shaft_work_j_kg-expected_work) <= 1e-7*max(1., abs(expected_work))
    assert result.shaft_power_w == result.inputs.hydrogen_mass_flow_kg_s * result.specific_shaft_work_j_kg
    assert result.energy_residual_w == result.enthalpy_rise_w-result.shaft_power_w
    assert result.energy_residual_w == 0.0
    result.require_current()

    original_outlet_temperature = result.actual_outlet.temperature_k
    object.__setattr__(result.actual_outlet, "temperature_k", original_outlet_temperature + 1.0)
    changed_state_rejected = 0
    try:
        result.require_current()
    except ValueError:
        changed_state_rejected = 1
    assert changed_state_rejected == 1
    object.__setattr__(result.actual_outlet, "temperature_k", original_outlet_temperature)
    result.require_current()

    original_version = provider.version
    provider.version = original_version + ".forged"
    changed_version_rejected = 0
    try:
        result.require_current()
    except ValueError:
        changed_version_rejected = 1
    assert changed_version_rejected == 1
    provider.version = original_version
    result.require_current()

    from h2physics.core import PropertyBasis
    original_basis = provider.basis
    provider._basis = PropertyBasis(original_basis.fluid, original_basis.reference_id + ":forged",
                                    original_basis.spin_composition)
    changed_basis_rejected = 0
    try:
        result.require_current()
    except ValueError:
        changed_basis_rejected = 1
    assert changed_basis_rejected == 1
    provider._basis = original_basis
    result.require_current()

    original_backend = provider.backend
    provider.backend = "TTSE&HEOS"
    changed_backend_rejected = 0
    try:
        result.require_current()
    except ValueError:
        changed_backend_rejected = 1
    assert changed_backend_rejected == 1
    provider.backend = original_backend
    result.require_current()
    return ValidationOutcome(True, {
        "provider_version": result.provider_version,
        "basis": result.property_basis.reference_id,
        "inlet_phase": result.inlet.phase,
        "reference_phase": result.isentropic_outlet.phase,
        "outlet_phase": result.actual_outlet.phase,
        "specific_shaft_work_j_kg": result.specific_shaft_work_j_kg,
        "shaft_power_w": result.shaft_power_w,
        "energy_residual_w": result.energy_residual_w,
        "mutated_state_rejected": changed_state_rejected,
        "mutated_version_rejected": changed_version_rejected,
        "mutated_property_basis_rejected": changed_basis_rejected,
        "mutated_backend_rejected": changed_backend_rejected,
    }, LIMITS)


def validate_real_fluid_guards(*, work_directory, **parameters):
    del work_directory, parameters
    from dataclasses import replace

    from h2physics.combustion.fuel_compression import run_real_fluid_hydrogen_compression
    from h2physics.thermo import CoolPropProperties

    provider = CoolPropProperties("Hydrogen", backend="HEOS")
    domain_rejected = 0
    for change in (
        {"temperature_bounds_k": (300.0, 400.0)},
        {"pressure_bounds_pa": (400_000.0, 700_000.0)},
    ):
        try:
            run_real_fluid_hydrogen_compression(provider, _real_fluid_inputs(**change))
        except (ValueError, RuntimeError):
            domain_rejected += 1
    assert domain_rejected == 2

    liquid_rejected = 0
    try:
        run_real_fluid_hydrogen_compression(provider, _real_fluid_inputs(
            inlet_temperature_k=20.0,
            inlet_pressure_pa=2_000_000.0,
            discharge_pressure_pa=5_000_000.0,
            temperature_bounds_k=(14.0, 100.0),
            pressure_bounds_pa=(100_000.0, 10_000_000.0),
        ))
    except (ValueError, RuntimeError):
        liquid_rejected = 1
    assert liquid_rejected == 1

    wrong_provider_rejected = 0
    try:
        run_real_fluid_hydrogen_compression(CoolPropProperties("Nitrogen"),
                                            _real_fluid_inputs())
    except ValueError:
        wrong_provider_rejected = 1
    assert wrong_provider_rejected == 1

    bad_bounds_rejected = 0
    try:
        replace(_real_fluid_inputs(), temperature_bounds_k=(400.0, 300.0))
    except ValueError:
        bad_bounds_rejected = 1
    assert bad_bounds_rejected == 1
    return ValidationOutcome(True, {
        "domain_rejections": domain_rejected,
        "liquid_rejected": liquid_rejected,
        "wrong_provider_rejected": wrong_provider_rejected,
        "invalid_domain_rejected": bad_bounds_rejected,
    }, LIMITS)


def validate_storage_handoff(*, work_directory, **parameters):
    del work_directory, parameters
    from h2physics.adapters.compression_mixture_handoff import (
        bind_compression_to_mixture_receiver,
    )
    from h2physics.combustion.fuel_compression import run_real_fluid_hydrogen_compression
    from h2physics.mixtures import GasComposition
    from h2physics.thermo import CoolPropMixtureProperties, CoolPropProperties
    from h2physics.thermo.finite_mixture_inventory import (
        MixtureProviderTemplate, MixtureVesselInterval,
        run_finite_mixture_vu_intervals,
    )

    pure_h2 = CoolPropProperties("Hydrogen", backend="HEOS")
    compressor = run_real_fluid_hydrogen_compression(
        pure_h2, _real_fluid_inputs(discharge_pressure_pa=6.0e6,
                                    temperature_bounds_k=(250., 1200.)))
    species = ("H2", "N2")
    masses = (2.01588e-3, 28.0134e-3)
    mixture = CoolPropMixtureProperties(
        GasComposition("handoff-initial-mixture", species, (.5, .5), masses),
        fluid_names={"H2": "Hydrogen", "N2": "Nitrogen"})
    partition = mixture.phase_partition_pq(
        5.0e6, .5, component_mole_balance_tolerance=2e-5)
    amounts = partition.split_moles(2.0)
    template = MixtureProviderTemplate(
        species, masses, ("Hydrogen", "Nitrogen"),
        energy_reference_id=pure_h2.basis.reference_id,
        molar_mass_relative_tolerance=1e-4)
    seed_interval = MixtureVesselInterval(
        end_time_s=1., liquid_inlet_component_moles=(0., 0.),
        vapor_inlet_component_moles=(1e-6, 0.),
        liquid_inlet_enthalpy_j=0.,
        vapor_inlet_enthalpy_j=(1e-6*masses[0]*partition.vapor_enthalpy_j_kg),
        evidence_id="authored-receiver-seed-v1")
    volume = sum(amounts.phase_volumes_m3)
    base = run_finite_mixture_vu_intervals(
        template, amounts.component_moles,
        initial_internal_energy_j=amounts.total_internal_energy_j,
        vessel_volume_m3=volume, intervals=(seed_interval,),
        pressure_bounds_pa=(4e6, 12e6), quality_bounds=(.2, .8),
        initial_guesses=((4.9e6, .45), (5.1e6, .55)),
        volume_absolute_tolerance_m3=1e-9,
        energy_absolute_tolerance_j=1e-2,
        component_mole_absolute_tolerance=2e-5,
        phase_mole_balance_tolerance=2e-5,
        branch_evidence_id="authored-bounded-receiver-branch-v1",
        run_id="authored-receiver-state-for-compressor-handoff")
    receipt = bind_compression_to_mixture_receiver(
        compressor, base.accepted[0], template=template,
        hydrogen_species="H2", start_time_s=0.0, end_time_s=1e-4,
        evidence_id="authored-compressor-to-vessel-port-v1")
    receipt.require_current()
    expected_mass = compressor.inputs.hydrogen_mass_flow_kg_s * 1e-4
    assert receipt.transferred_mass_kg == expected_mass
    assert receipt.interval.vapor_inlet_component_moles[0] == expected_mass/masses[0]
    assert receipt.interval.vapor_inlet_component_moles[1] == 0.
    assert receipt.interval.vapor_inlet_enthalpy_j == (
        expected_mass * compressor.actual_outlet.enthalpy_j_kg)

    original_moles = receipt.interval.vapor_inlet_component_moles
    object.__setattr__(receipt.interval, "vapor_inlet_component_moles",
                       (original_moles[0] + 1e-6, *original_moles[1:]))
    stale_interval_rejected = 0
    try:
        receipt.require_current()
    except ValueError:
        stale_interval_rejected = 1
    assert stale_interval_rejected == 1
    object.__setattr__(receipt.interval, "vapor_inlet_component_moles", original_moles)
    original_receiver_time = base.accepted[0].time_s
    object.__setattr__(base.accepted[0], "time_s", original_receiver_time + 1e-3)
    stale_receiver_rejected = 0
    try:
        receipt.require_current()
    except ValueError:
        stale_receiver_rejected = 1
    assert stale_receiver_rejected == 1
    object.__setattr__(base.accepted[0], "time_s", original_receiver_time)
    receipt.require_current()

    delivered = run_finite_mixture_vu_intervals(
        template, amounts.component_moles,
        initial_internal_energy_j=amounts.total_internal_energy_j,
        vessel_volume_m3=volume, intervals=(receipt.interval,),
        pressure_bounds_pa=(4e6, 12e6), quality_bounds=(.2, .8),
        initial_guesses=((4.9e6, .45), (5.1e6, .55)),
        volume_absolute_tolerance_m3=1e-9,
        energy_absolute_tolerance_j=1e-2,
        component_mole_absolute_tolerance=2e-5,
        phase_mole_balance_tolerance=2e-5,
        branch_evidence_id="authored-bounded-receiver-branch-v1",
        run_id="authored-compressor-fed-finite-mixture-vessel")
    delivered.require_current()
    assert delivered.accepted[-1].cumulative_inlet_component_moles[0] == (
        receipt.interval.vapor_inlet_component_moles[0])
    assert delivered.accepted[-1].cumulative_energy_into_vessel_j == (
        receipt.interval.vapor_inlet_enthalpy_j)
    return ValidationOutcome(True, {
        "compressor_discharge_pressure_pa": compressor.actual_outlet.pressure_pa,
        "receiver_initial_pressure_pa": receipt.receiver_pressure_pa,
        "transferred_hydrogen_mass_kg": receipt.transferred_mass_kg,
        "transferred_hydrogen_moles": receipt.interval.vapor_inlet_component_moles[0],
        "integrated_outlet_enthalpy_j": receipt.interval.vapor_inlet_enthalpy_j,
        "stale_interval_rejected": stale_interval_rejected,
        "stale_receiver_rejected": stale_receiver_rejected,
        "receiver_final_pressure_pa": delivered.accepted[-1].flash.pressure_pa,
        "receiver_final_vapor_mole_fraction": delivered.accepted[-1].flash.partition.vapor_mole_fraction,
    }, LIMITS + (
        "Receiver pressure is caller-provided at the start of the interval; no valve or transient compressor law is inferred.",
        "The synthetic starting mixture and energy-reference identity are not material or facility qualification.",
    ))
