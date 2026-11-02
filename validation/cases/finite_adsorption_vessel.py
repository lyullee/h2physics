"""Deferred finite adsorption-vessel cases; discovery returns metadata only."""

import numpy as np

from h2physics.cluster_validation import ValidationCase, ValidationOutcome

LIMITS = (
    "Component contracts do not establish independent material or vessel validation.",
    "Native CoolProp gas properties with authored adsorption-equilibrium fixtures.",
    "Equilibrium frozen-composition endpoints; no fill/heat/transport/device dynamics.",
)


def cases():
    definitions = (
        ("adsorption-vessel-partial-pressure-contract", "validate_partial_pressure",
         ("absolute-pressure Dalton result", "invalid pressure and fraction rejection",
          "broadcast output is immutable")),
        ("adsorption-vessel-inventory", "validate_inventory",
         ("free plus adsorbed component closure", "explicit void volume")),
        ("adsorption-vessel-capacity", "validate_capacity",
         ("charged-minus-discharged phase ledger", "selected H2 delivery")),
        ("adsorption-vessel-volume", "validate_volume",
         ("solid/inaccessible volume once", "invalid void rejection")),
        ("adsorption-vessel-uptake-basis", "validate_uptake_basis",
         ("absolute uptake admitted", "surface-excess rejected")),
        ("adsorption-vessel-owner-basis", "validate_owner_basis",
         ("property identity retained", "species-order guard",
          "provider-exposed composition mutation after binding is rejected")),
        ("adsorption-vessel-delivery-sign", "validate_delivery_sign",
         ("signed component changes visible", "nonpositive product rejected")),
        ("adsorption-vessel-pressure-inverse", "validate_pressure_inverse",
         ("isothermal target-inventory pressure recovery", "out-of-bracket target rejected",
          "sampled nonmonotone isotherm rejected",
          "snapshot-backed residual receipt", "immutable sampled inversion curve",
          "direct snapshot/solution construction and dataclass replacement are rejected")),
        ("adsorption-vessel-uncertainty-lineage", "validate_uncertainty_lineage",
         ("reported row uncertainties remain unqualified unless propagated by a declared law",
          "explicitly independent source errors combine by weighted variance",
          "propagated loading standard uncertainty scales with adsorbent mass",
          "partial species/site uncertainty coverage cannot silently appear as zero uncertainty",
          "a propagated state uncertainty vector requires covariance-derived semantics and evidence IDs",
          "surface-excess observations remain rejected by finite absolute inventory")),
    )
    return tuple(
        ValidationCase(
            identifier=name,
            profile="finite-adsorption-vessel",
            entrypoint=__name__ + ":" + entry,
            parameters={},
            invariants=invariants,
        )
        for name, entry, invariants in definitions
    )


def _outcome(metrics, *extra):
    return ValidationOutcome(True, metrics, (*LIMITS, *extra))


def validate_partial_pressure(*, work_directory, **parameters):
    from h2physics import partial_pressure_pa

    vector = partial_pressure_pa(10e6, np.array([0.25, 0.75]))
    assert np.array_equal(vector, np.array([2.5e6, 7.5e6]))
    assert not vector.flags.writeable
    assert partial_pressure_pa(2e5, 0.2) == 4e4
    rejected = 0
    for pressure, fraction in ((0., 0.2), (-1., 0.2), (np.nan, 0.2),
                               (1e5, -0.1), (1e5, 1.1), (True, 0.2),
                               ("100000", 0.2), (1e5, "0.2"), (1e5 + 0j, 0.2),
                               ([1e5, 2e5], [True, 0.5])):
        try:
            partial_pressure_pa(pressure, fraction)
        except ValueError:
            rejected += 1
    assert rejected == 10
    return _outcome({"invalid_inputs_rejected": rejected,
                     "array_read_only": not vector.flags.writeable})


def validate_inventory(*, work_directory, **parameters):
    from dataclasses import replace

    from examples.finite_adsorption_vessel import authored_vessel
    from h2physics.adapters.finite_adsorption_vessel import AdsorptionVesselSnapshot

    snapshot = authored_vessel().snapshot(10e6, 298.15)
    residual = snapshot.total_component_mol - (
        snapshot.free_gas_component_mol + snapshot.adsorbed_component_mol
    )
    assert np.max(np.abs(residual)) < 1e-12
    assert np.isclose(snapshot.geometry.void_volume_m3, 0.08, rtol=0., atol=1e-15)
    direct_values = {
        name: getattr(snapshot, name)
        for name in AdsorptionVesselSnapshot.__dataclass_fields__
        if not name.startswith("_")
    }
    rejected = 0
    for construct in (
        lambda: AdsorptionVesselSnapshot(**direct_values),
        lambda: replace(snapshot, free_gas_component_mol=(True, 1.0)),
        lambda: replace(snapshot, total_component_mol=(1.0, "2.0")),
    ):
        try:
            construct()
        except TypeError:
            rejected += 1
    assert rejected == 3
    return _outcome({"maximum_component_residual_mol": float(np.max(np.abs(residual))),
                     "void_volume_m3": snapshot.geometry.void_volume_m3,
                     "unissued_or_cloned_snapshots_rejected": rejected})


def validate_capacity(*, work_directory, **parameters):
    from examples.finite_adsorption_vessel import authored_vessel

    result = authored_vessel().delivery(10e6, 298.15, 1e6, 298.15,
                                         delivery_species=("H2",))
    residual = result.total_change_mol - (
        result.free_gas_change_mol + result.adsorbed_change_mol
    )
    h2 = result.charged.adsorption_basis.species.index("H2")
    assert np.max(np.abs(residual)) < 1e-12
    assert result.delivered_product_mol == result.total_change_mol[h2] > 0
    return _outcome({"delivered_h2_mol": result.delivered_product_mol,
                     "phase_ledger_residual_mol": float(np.max(np.abs(residual)))})


def validate_volume(*, work_directory, **parameters):
    from h2physics.adapters.finite_adsorption_vessel import AdsorptionVesselGeometry

    valid = AdsorptionVesselGeometry(1., 10., 0.25, 0.15, "measured-envelope")
    rejected = 0
    for values in ((1., 10., 0.9, 0.1), (1., 10., 1.1, 0.0), (1., 10., -0.1, 0.0)):
        try:
            AdsorptionVesselGeometry(*values, "invalid")
        except ValueError:
            rejected += 1
    assert valid.void_volume_m3 == 0.6 and rejected == 3
    return _outcome({"void_volume_m3": valid.void_volume_m3,
                     "invalid_geometries_rejected": rejected})


def validate_uptake_basis(*, work_directory, **parameters):
    from dataclasses import replace

    from examples.finite_adsorption_vessel import authored_vessel
    from h2physics.adapters.finite_adsorption_vessel import FiniteAdsorptionVessel

    original = authored_vessel()
    original.adsorption.basis = replace(original.adsorption.basis,
                                        loading_definition="surface_excess")
    try:
        FiniteAdsorptionVessel(vessel_id="reject-excess", geometry=original.geometry,
                               adsorption=original.adsorption, gas=original.gas)
    except ValueError as error:
        assert "absolute uptake" in str(error)
        return _outcome({"surface_excess_rejected": True})
    raise AssertionError("Surface-excess loading was counted as absolute inventory")


def validate_owner_basis(*, work_directory, **parameters):
    import numpy as np

    from examples.finite_adsorption_vessel import authored_vessel
    from h2physics.adapters.finite_adsorption_vessel import FrozenGasBinding

    vessel = authored_vessel()
    assert vessel.gas.property_basis == vessel.gas.provider.basis
    reordered = None
    try:
        reordered = FrozenGasBinding.bind(
            vessel.gas.provider, species=("N2", "H2"), mole_fractions=(0.9, 0.1),
            molar_masses_kg_mol=(28.0134e-3, 2.01588e-3), composition_id="wrong-order",
        )
        from h2physics.adapters.finite_adsorption_vessel import FiniteAdsorptionVessel
        FiniteAdsorptionVessel(vessel_id="wrong-order", geometry=vessel.geometry,
                               adsorption=vessel.adsorption, gas=reordered)
    except ValueError:
        species_order_rejected = True
    else:
        species_order_rejected = False
    if not species_order_rejected:
        raise AssertionError("Adsorption and gas species order mismatch was admitted")

    # Native CoolProp identity rejects mutation immediately. The separate mutable
    # metadata view also exercises the generic binding's post-admission guard.
    native = vessel.gas.provider
    try:
        native.composition_id = "altered-native-composition"
    except AttributeError:
        pass
    else:
        raise AssertionError("Native CoolProp composition identity was mutable")
    assert vessel.gas.require_current() is vessel.gas

    class MutableMetadataView:
        basis = native.basis
        composition_id = vessel.gas.composition_id
        species = vessel.gas.species
        mole_fractions = np.array(vessel.gas.mole_fractions, copy=True)
        molar_masses_kg_mol = np.array(vessel.gas.molar_masses_kg_mol, copy=True)

        def state_pt(self, pressure_pa, temperature_k):
            return native.state_pt(pressure_pa, temperature_k)

        def state_ph(self, pressure_pa, enthalpy_j_kg):
            return native.state_ph(pressure_pa, enthalpy_j_kg)

        def state_ps(self, pressure_pa, entropy_j_kg_k):
            return native.state_ps(pressure_pa, entropy_j_kg_k)

    provider = MutableMetadataView()
    bound = FrozenGasBinding.bind(
        provider, species=vessel.gas.species,
        mole_fractions=vessel.gas.mole_fractions,
        molar_masses_kg_mol=vessel.gas.molar_masses_kg_mol,
        composition_id=vessel.gas.composition_id,
    )
    provider.mole_fractions[:] = (0.8, 0.2)
    try:
        bound.state_pt(1e5, 300.)
    except ValueError as error:
        assert "composition changed" in str(error)
    else:
        raise AssertionError("Provider composition mutation after binding was admitted")
    return _outcome({"species_order_rejected": species_order_rejected,
                     "native_identity_mutation_rejected": True,
                     "provider_composition_mutation_rejected": True,
                     "property_basis_retained": True})


def validate_delivery_sign(*, work_directory, **parameters):
    from examples.finite_adsorption_vessel import authored_vessel

    vessel = authored_vessel()
    result = vessel.delivery(10e6, 298.15, 1e6, 298.15, delivery_species=("H2",))
    assert result.total_change_mol.shape == (2,)
    try:
        vessel.delivery(1e6, 298.15, 10e6, 298.15, delivery_species=("H2",))
    except ValueError as error:
        assert "positive" in str(error)
        return _outcome({"signed_components": len(result.total_change_mol),
                         "negative_product_rejected": True})
    raise AssertionError("A charging endpoint was mislabeled as positive delivery")


def validate_pressure_inverse(*, work_directory, **parameters):
    from dataclasses import replace

    from examples.finite_adsorption_vessel import authored_vessel
    from h2physics.adapters.finite_adsorption_vessel import AdsorptionPressureSolution
    from h2physics.adsorption import AdsorptionState

    vessel = authored_vessel()
    reference = vessel.snapshot(5e6, 298.15)
    species_index = reference.adsorption_basis.species.index("H2")
    target = float(reference.total_component_mol[species_index])
    solution = vessel.pressure_for_inventory(
        target, "H2", 298.15, (1e6, 10e6), samples=33,
        inventory_tolerance_mol=1e-7,
    )
    assert np.isclose(solution.snapshot.gas_state.pressure_pa, 5e6, rtol=1e-10)
    assert abs(solution.residual_mol) <= 1e-7
    assert solution.snapshot.vessel_id == vessel.vessel_id
    assert solution.sampled_pressure_count == solution.sampled_pressures_pa.size == 33
    assert not solution.sampled_pressures_pa.flags.writeable
    assert not solution.sampled_species_inventory_mol.flags.writeable
    assert solution.sampled_pressures_pa[0] == 1e6
    assert solution.sampled_pressures_pa[-1] == 10e6
    direct_values = {
        name: getattr(solution, name)
        for name in AdsorptionPressureSolution.__dataclass_fields__
        if not name.startswith("_")
    }
    unissued_solution_rejected = 0
    for construct in (
        lambda: AdsorptionPressureSolution(**direct_values),
        lambda: replace(solution, residual_mol=0.),
        lambda: replace(solution, snapshot=reference),
    ):
        try:
            construct()
        except TypeError:
            unissued_solution_rejected += 1
    assert unissued_solution_rejected == 3
    rejected = 0
    for invalid_target in (target * 100., 1e-12):
        try:
            vessel.pressure_for_inventory(
                invalid_target, "H2", 298.15, (1e6, 10e6), samples=33,
                inventory_tolerance_mol=1e-12,
            )
        except ValueError:
            rejected += 1
    assert rejected == 2
    nonmonotone = authored_vessel()
    equilibrium = nonmonotone.adsorption

    class NonmonotoneEquilibrium:
        basis = nonmonotone.adsorption.basis

        def equilibrium(self, partial_pressures_pa, temperature_k):
            base = equilibrium.equilibrium(partial_pressures_pa, temperature_k)
            loading = np.array(base.site_loadings_mol_kg, copy=True)
            pressure = float(partial_pressures_pa[0])
            loading[0, 0] += max(0., 1e6 * (1. - abs(pressure - 5e6) / 2e6))
            return AdsorptionState(
                self.basis, partial_pressures_pa, temperature_k, loading,
                base.site_pressure_derivatives_mol_kg_pa,
                base.site_temperature_derivatives_mol_kg_k,
            )

    nonmonotone.adsorption = NonmonotoneEquilibrium()
    try:
        nonmonotone.pressure_for_inventory(
            target, "H2", 298.15, (1e6, 10e6), samples=33,
            inventory_tolerance_mol=1e-7,
        )
    except ValueError as error:
        assert "nonmonotone" in str(error)
    else:
        raise AssertionError("Sampled nonmonotonic inventory was inverted")
    nonmonotone.adsorption = equilibrium
    return _outcome({"recovered_pressure_pa": solution.snapshot.gas_state.pressure_pa,
                     "inventory_residual_mol": solution.residual_mol,
                     "out_of_bracket_targets_rejected": rejected,
                     "unissued_solution_rejected": unissued_solution_rejected,
                     "sampled_nonmonotone_curve_rejected": True})


def validate_uncertainty_lineage(*, work_directory, **parameters):
    from examples.finite_adsorption_vessel import authored_vessel
    from h2physics.adsorption import AdsorptionSourceObservation, AdsorptionState

    vessel = authored_vessel()
    base_provider = vessel.adsorption

    class ReportedAbsoluteProvider:
        basis = base_provider.basis

        def equilibrium(self, partial_pressures_pa, temperature_k):
            base = base_provider.equilibrium(partial_pressures_pa, temperature_k)
            observations = ((AdsorptionSourceObservation("H2", 12, 1.,
                float(base.site_loadings_mol_kg[0, 0]), .01,
                source_dataset_id="authored-dataset", source_sha256="a"*64,
                uncertainty_kind="reported_standard_uncertainty"),
                AdsorptionSourceObservation("N2", 13, 1.,
                float(base.site_loadings_mol_kg[1, 0]), 0.,
                source_dataset_id="authored-dataset", source_sha256="a"*64,
                uncertainty_kind="reported_standard_uncertainty")),)
            return AdsorptionState(self.basis, partial_pressures_pa, temperature_k,
                base.site_loadings_mol_kg, source_observations=observations)

    absolute = ReportedAbsoluteProvider()
    vessel.adsorption = absolute
    snapshot = vessel.snapshot(2e6, 298.15)
    assert snapshot.uncertainty_semantics == "reported_standard_uncertainty"
    assert np.isclose(snapshot.adsorbed_standard_uncertainty_component_mol[0], .01*42.)
    assert snapshot.uncertainty_source_ids == ("authored-dataset:"+"a"*64,)

    class PartialSpeciesUncertaintyProvider:
        basis = absolute.basis

        def equilibrium(self, partial_pressures_pa, temperature_k):
            base = absolute.equilibrium(partial_pressures_pa, temperature_k)
            receipt = AdsorptionSourceObservation(
                "H2", 14, 1., float(base.site_loadings_mol_kg[0, 0]), .01,
                source_dataset_id="authored-partial", source_sha256="c"*64,
                uncertainty_kind="reported_standard_uncertainty",
            )
            return AdsorptionState(self.basis, partial_pressures_pa, temperature_k,
                                   base.site_loadings_mol_kg, source_observations=((receipt,),))

    vessel.adsorption = PartialSpeciesUncertaintyProvider()
    partial_coverage_rejected = False
    try:
        vessel.snapshot(2e6, 298.15)
    except ValueError as error:
        partial_coverage_rejected = any(message in str(error) for message in (
            "every species at every adsorption site",
            "one un-interpolated source observation per species",
        ))
    assert partial_coverage_rejected

    class IndependentRowsProvider:
        basis = absolute.basis

        def equilibrium(self, partial_pressures_pa, temperature_k):
            base = absolute.equilibrium(partial_pressures_pa, temperature_k)
            loading_value = float(base.site_loadings_mol_kg[0, 0])
            observations = ((
                AdsorptionSourceObservation("H2", 22, .5, loading_value-.002, .01,
                    source_dataset_id="authored-independent", source_sha256="b"*64,
                    uncertainty_kind="independent_standard_uncertainty",
                    covariance_group_id="authored-independence-law"),
                AdsorptionSourceObservation("H2", 23, .5, loading_value+.002, .02,
                    source_dataset_id="authored-independent", source_sha256="b"*64,
                    uncertainty_kind="independent_standard_uncertainty",
                    covariance_group_id="authored-independence-law"),
                AdsorptionSourceObservation("N2", 24, .5,
                    float(base.site_loadings_mol_kg[1, 0]), 0.,
                    source_dataset_id="authored-independent", source_sha256="b"*64,
                    uncertainty_kind="independent_standard_uncertainty",
                    covariance_group_id="authored-independence-law"),
                AdsorptionSourceObservation("N2", 25, .5,
                    float(base.site_loadings_mol_kg[1, 0]), 0.,
                    source_dataset_id="authored-independent", source_sha256="b"*64,
                    uncertainty_kind="independent_standard_uncertainty",
                    covariance_group_id="authored-independence-law")),)
            return AdsorptionState(self.basis, partial_pressures_pa, temperature_k,
                base.site_loadings_mol_kg, source_observations=observations)

    vessel.adsorption = IndependentRowsProvider()
    independent = vessel.snapshot(2e6, 298.15)
    expected_independent_sigma = ((.5*.01)**2+(.5*.02)**2)**.5*42.
    assert independent.uncertainty_semantics == "independent_standard_uncertainty"
    assert np.isclose(independent.adsorbed_standard_uncertainty_component_mol[0],
                      expected_independent_sigma)

    class UnjustifiedInterpolatedProvider:
        basis = absolute.basis

        def equilibrium(self, partial_pressures_pa, temperature_k):
            base = absolute.equilibrium(partial_pressures_pa, temperature_k)
            loading_value = float(base.site_loadings_mol_kg[0, 0])
            observations = ((
                AdsorptionSourceObservation("H2", 12, .5, loading_value-.005, .01,
                    source_dataset_id="authored-dataset", source_sha256="a"*64,
                    uncertainty_kind="reported_standard_uncertainty"),
                AdsorptionSourceObservation("H2", 13, .5, loading_value+.005, .02,
                    source_dataset_id="authored-dataset", source_sha256="a"*64,
                    uncertainty_kind="reported_standard_uncertainty"),
                AdsorptionSourceObservation("N2", 14, .5,
                    float(base.site_loadings_mol_kg[1, 0])-.005, .01,
                    source_dataset_id="authored-dataset", source_sha256="a"*64,
                    uncertainty_kind="reported_standard_uncertainty"),
                AdsorptionSourceObservation("N2", 15, .5,
                    float(base.site_loadings_mol_kg[1, 0])+.005, .02,
                    source_dataset_id="authored-dataset", source_sha256="a"*64,
                    uncertainty_kind="reported_standard_uncertainty")),)
            # The synthetic values only exercise receipt gates. Their interpolated
            # source loading must exactly reconstruct the declared state loading.
            return AdsorptionState(self.basis, partial_pressures_pa, temperature_k,
                base.site_loadings_mol_kg, source_observations=observations)

    rejected = False
    try:
        vessel.adsorption = UnjustifiedInterpolatedProvider()
        vessel.snapshot(2e6, 298.15)
    except ValueError as error:
        rejected = "covariance" in str(error).lower() or "interpolated" in str(error).lower()
    assert rejected

    class CovarianceProvider:
        basis = absolute.basis

        def equilibrium(self, partial_pressures_pa, temperature_k):
            base = absolute.equilibrium(partial_pressures_pa, temperature_k)
            return AdsorptionState(self.basis, partial_pressures_pa, temperature_k,
                base.site_loadings_mol_kg,
                propagated_standard_uncertainty_mol_kg=np.array([.015, 0.]),
                uncertainty_semantics="covariance_matrix_propagated",
                uncertainty_source_ids=("covariance-study:authored",))

    vessel.adsorption = CovarianceProvider()
    propagated = vessel.snapshot(2e6, 298.15)
    assert propagated.uncertainty_semantics == "covariance_matrix_propagated"
    assert np.isclose(propagated.adsorbed_standard_uncertainty_component_mol[0], .015*42.)
    assert propagated.uncertainty_source_ids == ("covariance-study:authored",)
    unqualified_array_rejected = False
    try:
        base = absolute.equilibrium(np.array([2e6, 0.]), 298.15)
        AdsorptionState(
            absolute.basis, base.partial_pressures_pa, base.temperature_k,
            base.site_loadings_mol_kg,
            propagated_standard_uncertainty_mol_kg=np.array([.015, 0.]),
        )
    except ValueError as error:
        unqualified_array_rejected = "covariance-derived semantics" in str(error)
    assert unqualified_array_rejected
    return _outcome({"reported_sigma_mol": float(snapshot.adsorbed_standard_uncertainty_component_mol[0]),
        "independent_sigma_mol": float(independent.adsorbed_standard_uncertainty_component_mol[0]),
        "covariance_sigma_mol": float(propagated.adsorbed_standard_uncertainty_component_mol[0]),
        "interpolated_reported_error_rejected": rejected,
        "unqualified_propagated_array_rejected": unqualified_array_rejected})
