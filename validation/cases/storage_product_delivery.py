"""Deferred contract for mass-flow projection of an adsorption vessel ledger."""

from h2physics.cluster_validation import ValidationCase, ValidationOutcome


def cases():
    return (ValidationCase(
        identifier="adsorption-delivery-component-mass-flow",
        profile="finite-adsorption-vessel",
        entrypoint=__name__ + ":validate_mass_flow_projection",
        invariants=(
            "species-resolved kg changes reconstruct from signed mol changes and caller molar masses",
            "interval-average kg/s uses only the explicitly supplied elapsed time",
            "selected product kg and kg/s conserve the accepted delivered-product basis",
            "species reordering, nonpositive molar mass, and invalid intervals are rejected",
            "result arrays are immutable and retain negative non-product component changes",
            "delivery receipt must be issued from the exact charged/discharged snapshots",
            "direct construction, replace-cloning, and forced snapshot/delivery mutation are rejected downstream",
            "a projected mass-flow receipt rejects changed source delivery or derived ledgers on later reuse",
        ),
    ), ValidationCase(
        identifier="adsorption-product-h2-linepack-charge-handoff",
        profile="finite-adsorption-vessel",
        entrypoint=__name__ + ":validate_linepack_charge",
        invariants=(
            "accepted adsorption H2 product mass enters the explicit analytic H2 linepack reference",
            "caller-mapped time interval equals both source averaging and linepack clock",
            "caller identifies the external transfer boundary and pressure/thermal interface evidence",
            "linepack inlet integral equals accepted product mass exactly",
            "molecular-mass mismatch and unaligned clock intervals are rejected",
            "no purification, compression, or time-resolved profile is inferred",
        ),
    ), ValidationCase(
        identifier="adsorption-product-native-real-gas-h2-linepack-charge",
        profile="finite-adsorption-vessel",
        entrypoint=__name__ + ":validate_native_linepack_charge",
        invariants=(
            "existing-CoolProp-real-gas-linepack-advance-conserves-accepted-product-mass",
            "source-known-spin-and-native-target-spin-must-match",
            "unresolved-mixture-spin-requires-explicit-caller-claim-and-evidence",
            "EOS-identity-native-pointer-callback-and-source-provenance-mutation-reject",
            "mass-only-transfer-does-not-infer-source-energy-conditioning-or-purification",
        ),
    ),)


def validate_linepack_charge(*, work_directory, **parameters):
    """Deferred contract for accepted adsorption product to pipeline inventory."""
    del work_directory, parameters
    from math import isclose

    from examples.finite_adsorption_vessel import authored_vessel
    from h2physics.adapters.adsorption_linepack import charge_linepack_from_adsorption_product
    from h2physics.pipeline_linepack import IsothermalLinepackState
    from h2physics.storage.product_delivery import AdsorptionProductMassFlow

    vessel = authored_vessel()
    delivery = vessel.delivery(10e6, 298.15, 1e6, 298.15, delivery_species=("H2",))
    product = AdsorptionProductMassFlow(
        delivery, tuple(delivery.charged.adsorption_basis.species),
        vessel.gas.molar_masses_kg_mol, 3600.)
    initial = IsothermalLinepackState.from_pressure(
        volume_m3=2., temperature_k=293.15,
        molecular_mass_kg_mol=0.00201588, pressure_pa=5.e6, time_s=120.)
    receipt = charge_linepack_from_adsorption_product(
        initial, product, start_time_s=120., end_time_s=3720.,
        minimum_mass_kg=0.01,
        time_mapping_evidence_id="authored-common-interval-clock-map",
        hydrogen_basis_evidence_id="authored-pure-H2-product-basis",
        transfer_boundary_evidence_id="authored-injection-boundary-accounting",
    )
    receipt.require_current()
    assert receipt.ledger.inlet_mass_kg == product.delivered_product_mass_kg
    assert isclose(receipt.final.mass_kg-receipt.initial.mass_kg,
                   product.delivered_product_mass_kg, rel_tol=1e-12, abs_tol=1e-15)
    assert receipt.ledger.start_time_s == 120. and receipt.ledger.end_time_s == 3720.
    rejected = 0
    try:
        charge_linepack_from_adsorption_product(
            initial, product, start_time_s=121., end_time_s=3721.,
            minimum_mass_kg=0.01,
            time_mapping_evidence_id="misaligned-clock",
            hydrogen_basis_evidence_id="authored-pure-H2-product-basis",
            transfer_boundary_evidence_id="authored-injection-boundary-accounting",
        )
    except ValueError:
        rejected += 1
    try:
        wrong_mass = IsothermalLinepackState.from_pressure(
            volume_m3=2., temperature_k=293.15,
            molecular_mass_kg_mol=0.004, pressure_pa=5.e6, time_s=120.)
        charge_linepack_from_adsorption_product(
            wrong_mass, product, start_time_s=120., end_time_s=3720.,
            minimum_mass_kg=0.01,
            time_mapping_evidence_id="authored-common-interval-clock-map",
            hydrogen_basis_evidence_id="authored-pure-H2-product-basis",
            transfer_boundary_evidence_id="authored-injection-boundary-accounting",
        )
    except ValueError:
        rejected += 1
    assert rejected == 2
    return ValidationOutcome(True, {
        "product_mass_kg": product.delivered_product_mass_kg,
        "linepack_mass_increase_kg": receipt.final.mass_kg-receipt.initial.mass_kg,
        "linepack_pressure_after_pa": receipt.final.pressure_pa,
        "rejected_invalid_boundaries": rejected,
    }, (
        "Authored adsorption and linepack fixtures only; no process qualification.",
        "The endpoint quotient is not a time-resolved process flow, and compressor or purification behavior is not modeled.",
    ))


def validate_native_linepack_charge(*, work_directory, **parameters):
    del work_directory, parameters
    from dataclasses import replace
    from math import isclose

    import numpy as np

    from examples.finite_adsorption_vessel import authored_vessel
    from h2physics.adapters.adsorption_linepack import charge_linepack_from_adsorption_product
    from h2physics.adapters.finite_adsorption_vessel import FiniteAdsorptionVessel, FrozenGasBinding
    from h2physics.adsorption import AdsorptionBasis, AdsorptionState
    from h2physics.real_gas_linepack import RealGasLinepackState
    from h2physics.storage.product_delivery import AdsorptionProductMassFlow
    from h2physics.thermo import CoolPropIsothermalEOS, CoolPropProperties

    mixture_vessel = authored_vessel()
    mixed_delivery = mixture_vessel.delivery(10e6, 298.15, 1e6, 298.15, delivery_species=("H2",))
    mixed_product = AdsorptionProductMassFlow(mixed_delivery, ("H2", "N2"),
        mixture_vessel.gas.molar_masses_kg_mol, 3600.)
    properties = CoolPropProperties("Hydrogen")

    class ZeroUptake:
        basis = AdsorptionBasis("authored-zero-uptake-limit", ("H2",),
            "mol/kg-dry-adsorbent", "authored-zero-limit", "authored-coefficients",
            ("zero-loading-numerical-limit",), "absolute")

        def equilibrium(self, partial_pressures_pa, temperature_k):
            return AdsorptionState(self.basis, partial_pressures_pa, temperature_k,
                                   np.zeros((1, 1)))

    gas = FrozenGasBinding.bind(properties, species=("H2",), mole_fractions=(1.,),
        molar_masses_kg_mol=(properties.molar_mass_kg_mol,), composition_id="native-pure-normal-H2")
    vessel = FiniteAdsorptionVessel(vessel_id="native-pure-H2-zero-uptake-vessel",
        geometry=mixture_vessel.geometry, adsorption=ZeroUptake(), gas=gas)
    delivery = vessel.delivery(10e6, 298.15, 1e6, 298.15, delivery_species=("H2",))
    product = AdsorptionProductMassFlow(delivery, ("H2",), gas.molar_masses_kg_mol, 3600.)
    eos = CoolPropIsothermalEOS("Hydrogen")
    initial = RealGasLinepackState.from_pressure(volume_m3=2., temperature_k=293.15,
        pressure_pa=5e6, eos=eos, time_s=120., minimum_pressure_pa=1e5, maximum_pressure_pa=2e7)
    arguments = dict(start_time_s=120., end_time_s=3720., minimum_mass_kg=.01,
        time_mapping_evidence_id="authored-product-averaging-to-pipeline-clock",
        hydrogen_basis_evidence_id="selected-pure-H2-product-ledger",
        transfer_boundary_evidence_id="authored-mass-only-boundary-no-conditioning-solver")
    receipt = charge_linepack_from_adsorption_product(initial, product, **arguments)
    assert receipt.require_current() is receipt
    assert receipt.initial.eos is receipt.final.eos is eos
    assert receipt.hydrogen_spin_composition == "normal"
    assert isclose(receipt.final.mass_kg-receipt.initial.mass_kg,
                   product.delivered_product_mass_kg, rel_tol=1e-12, abs_tol=1e-15)
    direct = eos.pressure_rho_t(receipt.final.density_kg_m3, receipt.final.temperature_k)
    assert isclose(direct, receipt.final.pressure_pa, rel_tol=1e-12)
    claimed = charge_linepack_from_adsorption_product(initial, mixed_product, **arguments,
        hydrogen_spin_composition="normal", hydrogen_spin_evidence_id="authored-unresolved-mixture-spin-map")
    assert claimed.require_current() is claimed
    assert claimed.product.delivery.charged.gas_state.basis.spin_composition == "mixture-H2-spin-unresolved"

    rejected = 0
    wrong_mass = AdsorptionProductMassFlow(delivery, ("H2",), (.004,), 3600.)
    para = RealGasLinepackState.from_pressure(volume_m3=2., temperature_k=293.15,
        pressure_pa=5e6, eos=CoolPropIsothermalEOS("ParaHydrogen"), time_s=120.)
    helium = RealGasLinepackState.from_pressure(volume_m3=2., temperature_k=293.15,
        pressure_pa=5e6, eos=CoolPropIsothermalEOS("Helium"), time_s=120.)
    conflicting_gas = FrozenGasBinding.bind(CoolPropProperties("Helium"), species=("H2",),
        mole_fractions=(1.,), molar_masses_kg_mol=(properties.molar_mass_kg_mol,),
        composition_id="conflicting-native-fluid-alias")
    conflicting_vessel = FiniteAdsorptionVessel(vessel_id="conflicting-native-fluid",
        geometry=vessel.geometry, adsorption=ZeroUptake(), gas=conflicting_gas)
    conflicting_delivery = conflicting_vessel.delivery(10e6, 298.15, 1e6, 298.15,
        delivery_species=("H2",))
    conflicting_product = AdsorptionProductMassFlow(conflicting_delivery, ("H2",),
        gas.molar_masses_kg_mol, 3600.)
    for operation in (
        lambda: charge_linepack_from_adsorption_product(initial, mixed_product, **arguments),
        lambda: charge_linepack_from_adsorption_product(initial, mixed_product, **arguments,
            hydrogen_spin_composition="normal"),
        lambda: charge_linepack_from_adsorption_product(initial, product, **arguments,
            hydrogen_spin_composition="para", hydrogen_spin_evidence_id="contradicts-source"),
        lambda: charge_linepack_from_adsorption_product(para, product, **arguments),
        lambda: charge_linepack_from_adsorption_product(helium, product, **arguments),
        lambda: charge_linepack_from_adsorption_product(initial, wrong_mass, **arguments),
        lambda: charge_linepack_from_adsorption_product(initial, conflicting_product, **arguments,
            hydrogen_spin_composition="normal", hydrogen_spin_evidence_id="cannot-override-known-helium"),
        lambda: charge_linepack_from_adsorption_product(initial, product,
            **{**arguments, "start_time_s": 121., "end_time_s": 3721.}),
        lambda: replace(receipt),
    ):
        try:
            operation()
        except (TypeError, ValueError):
            rejected += 1
        else:
            raise AssertionError("Invalid native product/clock/spin or receipt clone admitted")
    mutations = ((eos, "version", "changed-version"),
                 (eos, "fluid", "ParaHydrogen"),
                 (eos, "density_pt", lambda p, t: 1.),
                 (eos, "pressure_rho_t", lambda rho, t: 5e6),
                 (receipt, "hydrogen_spin_evidence_id", "relabeled-after-issue"),
                 (receipt.product.delivery.charged, "vessel_id", "relabelled-source"))
    for target, name, changed in mutations:
        original = getattr(target, name)
        try:
            object.__setattr__(target, name, changed)
            try:
                receipt.require_current()
            except ValueError:
                rejected += 1
            else:
                raise AssertionError("Changed EOS/source/spin evidence retained receipt admission")
        finally:
            object.__setattr__(target, name, original)
        assert receipt.require_current() is receipt
    assert rejected == 15
    return ValidationOutcome(True, {
        "native_product_mass_kg": product.delivered_product_mass_kg,
        "native_linepack_mass_increase_kg": receipt.final.mass_kg-receipt.initial.mass_kg,
        "native_initial_pressure_pa": initial.pressure_pa,
        "native_final_pressure_pa": receipt.final.pressure_pa,
        "native_mass_residual_kg": receipt.ledger.mass_residual_kg,
        "native_spin": receipt.hydrogen_spin_composition,
        "explicit_mixture_spin_mapping_admitted": True,
        "invalid_boundaries_and_mutations_rejected": rejected,
    }, (
        "Native CoolProp H2 mass/EOS coupling; source uptake fixtures are not measured material data",
        "Unresolved mixed-source spin is accepted only as a sealed caller claim with evidence",
        "Mass ledger only; no inferred source enthalpy, purification, pressure matching or conditioning energy",
    ))


def validate_mass_flow_projection(*, work_directory, **parameters):
    from dataclasses import replace

    from examples.finite_adsorption_vessel import authored_vessel
    from h2physics.adapters.finite_adsorption_vessel import AdsorptionVesselDelivery
    from h2physics.storage.product_delivery import AdsorptionProductMassFlow

    del work_directory, parameters
    vessel = authored_vessel()
    delivery = vessel.delivery(10e6, 298.15, 1e6, 298.15, delivery_species=("H2",))
    species = tuple(delivery.charged.adsorption_basis.species)
    receipt = AdsorptionProductMassFlow(
        delivery, species, vessel.gas.molar_masses_kg_mol, 3600.
    )
    assert (receipt.component_mass_change_kg
            == delivery.total_change_mol * vessel.gas.molar_masses_kg_mol).all()
    assert (receipt.component_average_mass_rate_kg_s
            == receipt.component_mass_change_kg / 3600.).all()
    h2 = species.index("H2")
    assert receipt.delivered_product_mass_kg == receipt.component_mass_change_kg[h2]
    assert receipt.delivered_product_average_mass_rate_kg_s == receipt.delivered_product_mass_kg / 3600.
    assert not receipt.component_mass_change_kg.flags.writeable
    assert not receipt.component_average_mass_rate_kg_s.flags.writeable
    assert receipt.require_current() is receipt
    rejected_receipts = 0
    forged_args = (
        delivery.charged, delivery.discharged, delivery.free_gas_change_mol,
        delivery.adsorbed_change_mol, delivery.total_change_mol,
        delivery.delivery_species, delivery.delivered_product_mol,
    )
    try:
        forged = AdsorptionVesselDelivery(*forged_args)
        AdsorptionProductMassFlow(forged, species, vessel.gas.molar_masses_kg_mol, 3600.)
    except (TypeError, ValueError):
        rejected_receipts += 1
    try:
        clone = replace(delivery)
        AdsorptionProductMassFlow(clone, species, vessel.gas.molar_masses_kg_mol, 3600.)
    except (TypeError, ValueError):
        rejected_receipts += 1
    changed_delivery = vessel.delivery(10e6, 298.15, 1e6, 298.15, delivery_species=("H2",))
    object.__setattr__(changed_delivery, "delivered_product_mol",
                       changed_delivery.delivered_product_mol + 1.)
    try:
        AdsorptionProductMassFlow(
            changed_delivery, species, vessel.gas.molar_masses_kg_mol, 3600.
        )
    except ValueError:
        rejected_receipts += 1
    changed_snapshot = vessel.delivery(10e6, 298.15, 1e6, 298.15, delivery_species=("H2",))
    object.__setattr__(changed_snapshot.charged, "vessel_id", "forged-vessel")
    try:
        AdsorptionProductMassFlow(
            changed_snapshot, species, vessel.gas.molar_masses_kg_mol, 3600.
        )
    except ValueError:
        rejected_receipts += 1
    assert rejected_receipts == 4
    stale_delivery = vessel.delivery(10e6, 298.15, 1e6, 298.15, delivery_species=("H2",))
    stale_projection = AdsorptionProductMassFlow(
        stale_delivery, species, vessel.gas.molar_masses_kg_mol, 3600.
    )
    object.__setattr__(stale_delivery, "delivered_product_mol",
                       stale_delivery.delivered_product_mol + 1.)
    try:
        stale_projection.require_current()
    except ValueError:
        pass
    else:
        raise AssertionError("A projection remained usable after its source delivery changed")
    tampered_projection = AdsorptionProductMassFlow(
        vessel.delivery(10e6, 298.15, 1e6, 298.15, delivery_species=("H2",)),
        species, vessel.gas.molar_masses_kg_mol, 3600.
    )
    object.__setattr__(tampered_projection, "delivered_product_mass_kg",
                       tampered_projection.delivered_product_mass_kg + 1.)
    try:
        tampered_projection.require_current()
    except ValueError:
        pass
    else:
        raise AssertionError("A changed mass-flow projection passed currentness")
    rejected = 0
    for order, masses, interval in (
        (tuple(reversed(species)), vessel.gas.molar_masses_kg_mol, 3600.),
        (species, [0. if i == 0 else mass for i, mass in enumerate(vessel.gas.molar_masses_kg_mol)], 3600.),
        (species, vessel.gas.molar_masses_kg_mol, 0.),
    ):
        try:
            AdsorptionProductMassFlow(delivery, order, masses, interval)
        except (TypeError, ValueError):
            rejected += 1
    assert rejected == 3
    return ValidationOutcome(True, {
        "species_count": len(species),
        "elapsed_s": receipt.elapsed_s,
        "product_mass_kg": receipt.delivered_product_mass_kg,
        "rejections": rejected,
        "receipt_rejections": rejected_receipts,
        "result_arrays_immutable": True,
    }, (
        "Deferred contract only; the authored adsorption fixture is not material qualification.",
        "Average interval flow is an endpoint quotient, not a time-resolved flow history.",
    ))
