"""Synthetic contract checks for native accepted-edge pool energy records."""

from dataclasses import dataclass, replace

from h2physics.cluster_validation import ValidationCase, ValidationOutcome

LIMITS = (
    "Synthetic accepted-edge records validate the Python contract only.",
    "No pool evaporation, heat integration, dryout, finite-wall physics or native solver is exercised.",
    "The receiving DynamicLH2PoolX result must still publish native accepted edges and interval integrals.",
)


def cases():
    return (ValidationCase(
        identifier="native-pool-accepted-edge-energy-contract",
        profile="pool-energy-contract",
        entrypoint=__name__ + ":validate_native_pool_energy_contract",
        invariants=("native-accepted-edge-identities-retained",
                    "liquid-mass-and-first-law-signs-recomputed",
                    "finite-wall-transfer-cancels-once",
                    "external-reservoir-cannot-claim-finite-wall-storage",
                    "cumulative-allocation-mutation-rejected"),
    ),)


def validate_native_pool_energy_contract(*, work_directory, **parameters):
    del work_directory, parameters
    from h2physics.adapters.pool_native_energy_contract import (
        PoolNativeEnergyCapabilityError,
        PoolNativeEnergyEdge,
        PoolNativeEnergyTrace,
    )

    @dataclass(frozen=True)
    class SyntheticAcceptedState:
        time_s: float
        liquid_mass_kg: float
        liquid_internal_energy_j: float
        liquid_volume_m3: float
        boundary_pressure_pa: float

    initial_state = SyntheticAcceptedState(0., 5., 1000., .005, 101325.)
    accepted_state = SyntheticAcceptedState(1., 5.5, 12500., .0055, 101325.)
    first = PoolNativeEnergyEdge(
        time_s=0., step_identity="native-step-0", accepted_state=initial_state,
        liquid_mass_kg=5., liquid_internal_energy_j=1000., liquid_volume_m3=.005,
        boundary_pressure_pa=101325.,
        cumulative_liquid_inlet_mass_kg=0., cumulative_vapor_outlet_mass_kg=0.,
        cumulative_liquid_inlet_enthalpy_j=0., cumulative_vapor_outlet_enthalpy_j=0.,
        cumulative_substrate_heat_into_liquid_j=0., cumulative_pressure_volume_work_out_j=0.,
        cumulative_unapplied_heat_j=0., cumulative_dry_surface_heat_j=0.,
        cumulative_heat_cap_rejection_j=0., substrate_energy_change_j=0.,
        cumulative_external_heat_into_substrate_j=0.,
    )
    # m=5 + 1 kg inlet - 0.5 kg vapor; dU=Hin-Hout+Q-W=11,500 J.
    second = PoolNativeEnergyEdge(
        time_s=1., step_identity="native-step-1", accepted_state=accepted_state,
        liquid_mass_kg=5.5, liquid_internal_energy_j=12500., liquid_volume_m3=.0055,
        boundary_pressure_pa=101325.,
        cumulative_liquid_inlet_mass_kg=1., cumulative_vapor_outlet_mass_kg=.5,
        cumulative_liquid_inlet_enthalpy_j=20000., cumulative_vapor_outlet_enthalpy_j=10000.,
        cumulative_substrate_heat_into_liquid_j=2000., cumulative_pressure_volume_work_out_j=500.,
        cumulative_unapplied_heat_j=100., cumulative_dry_surface_heat_j=20.,
        cumulative_heat_cap_rejection_j=30., substrate_energy_change_j=-500.,
        cumulative_external_heat_into_substrate_j=1500.,
    )
    @dataclass(frozen=True)
    class SyntheticNativeResult:
        accepted_energy_samples: tuple

    native = SyntheticNativeResult((first, second))
    trace = PoolNativeEnergyTrace(
        native_result=native, accepted_edges=(first, second), substrate_mode="finite_wall",
        energy_reference_id="synthetic-H2-reference", vapor_phase_id="H2:normal:vapor",
        mass_tolerance_kg=1e-10, energy_tolerance_j=1e-8,
    )
    assert trace.verify_result(native) is native
    assert trace.mass_residual_kg == (0., 0.)
    assert trace.energy_residual_j == (0., 0.)
    try:
        trace.verify_result(object())
    except ValueError:
        detached_rejected = True
    else:
        raise AssertionError("A detached native result must not reuse the captured energy trace")
    try:
        third_state = SyntheticAcceptedState(2., 5.5, 12500., .0055, 101325.)
        bad_allocation = replace(second, time_s=2., step_identity="native-step-2",
                                 accepted_state=third_state, cumulative_dry_surface_heat_j=10.)
        bad_native = SyntheticNativeResult((first, second, bad_allocation))
        PoolNativeEnergyTrace(
            native_result=bad_native, accepted_edges=(first, second, bad_allocation),
            substrate_mode="finite_wall", energy_reference_id="synthetic-H2-reference",
            vapor_phase_id="H2:normal:vapor", mass_tolerance_kg=1e-10,
            energy_tolerance_j=1e-8,
        )
    except ValueError:
        allocation_decrease_rejected = True
    else:
        raise AssertionError("Decreasing cumulative dry-surface allocation must be rejected")
    try:
        reservoir_native = SyntheticNativeResult((first, second))
        PoolNativeEnergyTrace(
            native_result=reservoir_native, accepted_edges=(first, second),
            substrate_mode="prescribed_external_reservoir",
            energy_reference_id="synthetic-H2-reference", vapor_phase_id="H2:normal:vapor",
            mass_tolerance_kg=1e-10, energy_tolerance_j=1e-8,
        )
    except ValueError:
        reservoir_wall_claim_rejected = True
    else:
        raise AssertionError("Reservoir mode must reject finite-wall energy fields")
    assert detached_rejected and allocation_decrease_rejected and reservoir_wall_claim_rejected
    try:
        PoolNativeEnergyTrace(
            native_result=object(), accepted_edges=(first, second),
            substrate_mode="finite_wall", energy_reference_id="synthetic-H2-reference",
            vapor_phase_id="H2:normal:vapor", mass_tolerance_kg=1e-10,
            energy_tolerance_j=1e-8,
        )
    except PoolNativeEnergyCapabilityError:
        missing_native_edges_rejected = True
    else:
        raise AssertionError("Native result without its own accepted energy edges must fail closed")
    return ValidationOutcome(True, {
        "accepted_edges": len(trace.accepted_edges),
        "mass_residual_kg": trace.mass_residual_kg,
        "energy_residual_j": trace.energy_residual_j,
        "finite_wall_mode": trace.substrate_mode,
        "detached_result_rejected": detached_rejected,
        "decreasing_allocation_rejected": allocation_decrease_rejected,
        "reservoir_wall_claim_rejected": reservoir_wall_claim_rejected,
        "missing_native_edges_rejected": missing_native_edges_rejected,
    }, LIMITS)
