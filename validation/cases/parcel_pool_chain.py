"""Deferred initial-stock continuation contract; no import-time physics."""

from h2physics.cluster_validation import ValidationCase, ValidationOutcome


def cases():
    return (ValidationCase(
        identifier="impact-pool-conservative-vapor-chain", profile="droplet-impact",
        entrypoint=__name__+":validate_contract", parameters={},
        invariants=("owner-issued deposited stock and distinct substrate heat",
                    "absolute-clock native initial-stock mass closure",
                    "cumulative evaporation produces conservative vapor bins",
                    "upward vapor boundary and zero initial evaporation",
                    "pool-to-dispersion wrapper preserves rejected, accepted and no-active-snapshot SLAB aggregate states",
                    "post-run native residual mutation and detached receipt rejection",
                    "pool energy ledger binds the deposited property reference and normal-hydrogen vapor phase",
                    "directly reconstructed energy receipts bind native accepted-edge energy fields",
                    "pool-energy adapter refuses sparse-flux quadrature when native cumulative energy is absent"),
    ),)


def validate_contract(*, work_directory, **parameters):
    from dataclasses import replace

    from dynamiclh2poolx import FixedAreaPoolConfig, Substrate

    from examples.droplet_impact import build_model, incident_trace
    from h2physics.adapters.parcel_pool_chain import (
        ParcelPoolChainError,
        run_deposited_batch_pool,
    )

    model = build_model()
    impact = model.run((incident_trace(model),)).steps[0]
    config = FixedAreaPoolConfig(
        area_m2=.01, initial_liquid_mass_kg=0.,
        substrate=Substrate("authored-independent-substrate", .2, 1e-7),
        ambient_temperature_K=80., ambient_pressure_Pa=101325.,
        critical_heat_flux_W_m2=None, initial_thermal_age_s=.01,
    )
    location = replace(impact.deposited_batch.location, direction_unit=(0., 0., 1.))
    start = impact.contact_end_s
    arguments = dict(
        impact_owner=model, separate_continuation_heat_owner=config.substrate,
        continuation_evidence_id="authored-independent-stock-continuation",
        reference_properties=model.properties, vapor_location=location,
        output_times_s=(start, start+.01, start+.1),
    )
    result = run_deposited_batch_pool(impact, config, **arguments)
    result.require_current()
    from h2physics.adapters.parcel_pool_chain import ParcelPoolDispersion

    class SnapshotStatus:
        source = result.vapor_source
        plume_memory_included = False

        def __init__(self, accepted):
            self.all_snapshots_accepted = accepted

        def require_current(self):
            return self

    status_results = {}
    for native_acceptance in (False, True, None):
        wrapper = ParcelPoolDispersion(result, SnapshotStatus(native_acceptance))
        object.__setattr__(wrapper, "_binding", (id(result), id(wrapper.dispersion)))
        wrapper.require_current()
        if wrapper.accepted is not native_acceptance:
            raise AssertionError("Pool dispersion wrapper hid or changed SLAB acceptance status")
        status_results[str(native_acceptance)] = wrapper.accepted
    from h2physics.adapters.pool_energy_ledger import (
        PoolEnergyCapabilityError,
        bind_native_pool_energy_ledger,
    )
    try:
        reference_id = result.initialization.batch.state.basis.reference_id
        vapor_phase_id = (f"{result.initialization.batch.state.basis.fluid}:"
                          f"{result.initialization.batch.state.basis.spin_composition}:vapor")
        for wrong_reference, wrong_phase in (("wrong-reference", vapor_phase_id),
                                             (reference_id, "unqualified-phase")):
            try:
                bind_native_pool_energy_ledger(
                    result, substrate_mode="prescribed_external_reservoir",
                    energy_reference_id=wrong_reference, vapor_phase_id=wrong_phase,
                    mass_tolerance_kg=1e-9, energy_tolerance_j=1e-6)
            except ValueError:
                pass
            else:
                raise AssertionError("Pool ledger admitted a mismatched phase/reference identity")
        ledger = bind_native_pool_energy_ledger(
            result, substrate_mode="prescribed_external_reservoir",
            energy_reference_id=reference_id, vapor_phase_id=vapor_phase_id,
            mass_tolerance_kg=1e-9, energy_tolerance_j=1e-6)
        direct_ledger = replace(ledger)
        assert direct_ledger.require_current() is direct_ledger
    except PoolEnergyCapabilityError:
        native_energy_ledger_available = False
    else:
        native_energy_ledger_available = True
    assert result.vapor_source.total_mass_kg == result.native_result.ledger[-1].cumulative_evaporation_kg
    assert result.vapor_source.location is location
    assert result.absolute_times_s[0] == start
    assert not result.finite_patch_thermal_continuation_solved
    seed = result.fire_seed(
        evidence_id="authored-deposited-pool-fire-stock",
        ignition_transition_evidence_id="authored-conditional-fire-model-transition",
        temperature_absolute_tolerance_k=1e-5, density_relative_tolerance=1e-6,
    )
    assert seed.deposited_pool_continuation is result
    assert seed.thermodynamic_owner is result
    assert seed.liquid_mass_kg == result.native_result.ledger[-1].liquid_mass_kg
    assert seed.time_s == result.absolute_times_s[-1]
    assert seed.preignition_evaporation is result.vapor_source
    seed._require_deposited_continuation()
    try:
        replace(result).require_current()
    except ValueError:
        pass
    else:
        raise AssertionError("Detached continuation was accepted as an issued result")
    original = result.native_result.mass_balance_residual_kg
    try:
        object.__setattr__(result.native_result, "mass_balance_residual_kg", original+1.)
        try:
            result.require_current()
        except ValueError:
            pass
        else:
            raise AssertionError("Changed native final residual was accepted")
        try:
            seed._require_deposited_continuation()
        except ValueError:
            pass
        else:
            raise AssertionError("Fire seed retained stale deposited-pool parent")
    finally:
        object.__setattr__(result.native_result, "mass_balance_residual_kg", original)
    bad_arguments = dict(arguments, vapor_location=replace(location, direction_unit=(1., 0., 0.)))
    try:
        run_deposited_batch_pool(impact, config, **bad_arguments)
    except ParcelPoolChainError as error:
        assert error.cause is error.__cause__ and error.native_result is None
    else:
        raise AssertionError("Horizontal source was accepted as ground-pool vapor")
    return ValidationOutcome(True, {
        "evaporated_mass_kg": result.vapor_source.total_mass_kg,
        "maximum_mass_residual_kg": max(abs(value) for value in result.mass_residuals_kg),
        "native_energy_ledger_available": native_energy_ledger_available,
        "slab_acceptance_states": status_results,
    }, ("Authored stock and separate substrate; no measured impact/pool validation",
        "Finite impact-wall thermal continuation is not resolved"))
