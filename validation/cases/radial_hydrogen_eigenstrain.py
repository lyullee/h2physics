"""Deferred synthetic contracts for one-way hydrogen eigenstrain stress mapping."""

from h2physics.cluster_validation import ValidationCase, ValidationOutcome


def cases():
    return (ValidationCase(
        identifier="radial-hydrogen-concentration-eigenstrain",
        profile="fracture-fatigue",
        entrypoint=__name__ + ":validate_hydrogen_eigenstrain",
        invariants=(
            "caller maps one declared carrier concentration basis to a linear isotropic eigenstrain coefficient",
            "pressure and thermal baseline is retained separately from the combined stress field",
            "hydrogen-only radial, hoop, axial and free/fixed support increments reconstruct the combined result",
            "equal-to-reference concentration contributes zero eigenstrain stress",
            "reference wall bounds and temperature must match exactly",
            "nonuniform hydrogen concentration produces a displacement/stress response with explicit sign convention",
            "stress output adds no concentration evolution, trapping partition, stress-assisted diffusion, plasticity or failure law",
            "result deltas reject post-admission mutation and forged direct construction",
            "result freshness includes retained baseline and combined stress-field contents",
            "quasi-static history rejects carrier, basis, reference and expansion-coefficient changes across samples",
            "public eigenstrain mapping rejects negative or nonfinite concentration",
            "caller-supplied exact-time profiles form a sealed quasi-static stress history without interpolation",
        ),
    ),)


def validate_hydrogen_eigenstrain(*, work_directory, **parameters):
    del work_directory, parameters
    import numpy as np

    from h2physics.core import Origin
    from h2physics.materials import (
        CylinderGeometry,
        CylinderPressureLoad,
        HydrogenCarrier,
        HydrogenConcentrationEigenstrainProfile,
        IsotropicThermoelasticMaterial,
        RadialTemperatureProfile,
        radial_hydrogen_eigenstrain_cylinder,
        radial_hydrogen_eigenstrain_history,
    )

    inner, outer = 0.05, 0.10
    profile_radius = np.linspace(inner, outer, 15)
    output_radius = np.linspace(inner, outer, 41)
    temperature_reference = 298.15
    temperature = RadialTemperatureProfile(
        profile_radius, np.linspace(320.0, 360.0, profile_radius.size),
        temperature_reference, "synthetic-wall-temperature", "synthetic-temperature-evidence",
    )
    geometry = CylinderGeometry(inner, outer, "closed", "synthetic-hollow-cylinder")
    load = CylinderPressureLoad(5e6, 1e5, "synthetic-pressure-load", Origin.SYNTHETIC)
    material = IsotropicThermoelasticMaterial(
        190e9, 0.29, 12e-6, "synthetic-isotropic-material", "synthetic-elastic-properties",
    )
    carrier = HydrogenCarrier("atomic_hydrogen", 1.008e-3)
    reference_concentration = 0.25
    concentration = np.linspace(0.25, 1.25, profile_radius.size)
    profile = HydrogenConcentrationEigenstrainProfile(
        carrier=carrier,
        concentration_basis_id="synthetic-mobile-lattice-H-mol-per-m3",
        radius_m=profile_radius,
        concentration_mol_m3=concentration,
        reference_concentration_mol_m3=reference_concentration,
        linear_expansion_m3_per_mol=1.0e-6,
        reference_temperature_k=temperature_reference,
        profile_id="synthetic-radial-mobile-H-profile",
        evidence_id="synthetic-concentration-to-eigenstrain-mapping",
    )
    results = {}
    for restraint in ("free", "fixed"):
        result = radial_hydrogen_eigenstrain_cylinder(
            geometry, load, temperature, material, profile, output_radius,
            axial_restraint=restraint,
            evidence_id="long-cylinder-isotropic-eigenstrain-equilibrium",
        )
        assert result.hydrogen_profile is profile
        assert result.require_current() is result
        assert np.allclose(
            result.baseline.radial_stress_pa + result.hydrogen_radial_stress_pa,
            result.combined.radial_stress_pa, rtol=5e-5, atol=10.0,
        )
        assert np.allclose(
            result.baseline.hoop_stress_pa + result.hydrogen_hoop_stress_pa,
            result.combined.hoop_stress_pa, rtol=5e-5, atol=10.0,
        )
        assert np.allclose(
            result.baseline.axial_stress_pa + result.hydrogen_axial_stress_pa,
            result.combined.axial_stress_pa, rtol=5e-5, atol=10.0,
        )
        assert np.any(np.abs(result.hydrogen_hoop_stress_pa) > 1.0)
        assert np.array_equal(result.combined.radius_m, output_radius)
        results[restraint] = result

    forged_rejected = 0
    try:
        from dataclasses import replace
        replace(results["free"])
    except ValueError:
        forged_rejected += 1
    assert forged_rejected == 1
    concentration_rejected = 0
    for invalid in (np.array([-1.0]), np.array([np.nan])):
        try:
            profile.eigenstrain(invalid)
        except ValueError:
            concentration_rejected += 1
    assert concentration_rejected == 2

    uniform_reference = HydrogenConcentrationEigenstrainProfile(
        carrier=carrier, concentration_basis_id=profile.concentration_basis_id,
        radius_m=profile_radius, concentration_mol_m3=np.full(profile_radius.shape,
                                                               reference_concentration),
        reference_concentration_mol_m3=reference_concentration,
        linear_expansion_m3_per_mol=profile.linear_expansion_m3_per_mol,
        reference_temperature_k=temperature_reference,
        profile_id="synthetic-uniform-reference-H-profile",
        evidence_id="synthetic-reference-state",
    )
    from dataclasses import replace
    altered_mapping_profiles = (
        replace(profile, linear_expansion_m3_per_mol=
                2.0 * profile.linear_expansion_m3_per_mol),
        replace(profile, concentration_basis_id="synthetic-different-mobile-basis"),
        replace(profile, carrier=HydrogenCarrier("molecular_hydrogen", 2.016e-3)),
    )
    rejected_time_mapping_changes = 0
    for changed_profile in altered_mapping_profiles:
        try:
            radial_hydrogen_eigenstrain_history(
                geometry, (load, load, load),
                (temperature, temperature, temperature),
                (profile, changed_profile, profile), material, output_radius,
                np.array([0.0, 2.0, 5.0]),
                axial_restraint="fixed",
                clock_id="synthetic-mapping-mismatch-clock",
                evidence_id="long-cylinder-isotropic-eigenstrain-equilibrium",
            )
        except ValueError:
            rejected_time_mapping_changes += 1
    assert rejected_time_mapping_changes == 3
    history = radial_hydrogen_eigenstrain_history(
        geometry,
        (load, load, load),
        (temperature, temperature, temperature),
        (profile, uniform_reference, profile),
        material,
        output_radius,
        np.array([0.0, 2.0, 5.0]),
        axial_restraint="fixed",
        clock_id="synthetic-hydrogen-eigenstrain-clock",
        evidence_id="long-cylinder-isotropic-eigenstrain-equilibrium",
    )
    assert history.sample_at(1) is history.samples[1]
    assert np.array_equal(history.time_s, np.array([0.0, 2.0, 5.0]))
    assert history.samples[1].hydrogen_profile is uniform_reference
    assert history.require_current() is history
    history_forgery_rejected = 0
    try:
        from dataclasses import replace
        replace(history)
    except ValueError:
        history_forgery_rejected += 1
    assert history_forgery_rejected == 1
    field = history.samples[0].combined
    altered = np.array(field.hoop_stress_pa, copy=True)
    altered[0] += 1.0
    object.__setattr__(field, "hoop_stress_pa", altered)
    nested_field_mutation_rejected = 0
    try:
        history.require_current()
    except ValueError:
        nested_field_mutation_rejected += 1
    assert nested_field_mutation_rejected == 1
    retained_material = results["fixed"].baseline.material
    object.__setattr__(retained_material, "young_modulus_pa",
                       retained_material.young_modulus_pa + 1.0)
    nested_input_mutation_rejected = 0
    try:
        results["fixed"].require_current()
    except ValueError:
        nested_input_mutation_rejected += 1
    assert nested_input_mutation_rejected == 1

    zero = radial_hydrogen_eigenstrain_cylinder(
        geometry, load, temperature, material, uniform_reference, output_radius,
        axial_restraint="fixed",
        evidence_id="long-cylinder-isotropic-eigenstrain-equilibrium",
    )
    assert np.allclose(zero.hydrogen_radial_stress_pa, 0.0, atol=10.0)
    assert np.allclose(zero.hydrogen_hoop_stress_pa, 0.0, atol=10.0)
    assert np.allclose(zero.hydrogen_axial_stress_pa, 0.0, atol=10.0)

    rejected_mismatch = 0
    incompatible_temperature = RadialTemperatureProfile(
        profile_radius, temperature.temperature_k, 300.0,
        "mismatched-reference-temperature", "synthetic-temperature-evidence",
    )
    try:
        radial_hydrogen_eigenstrain_cylinder(
            geometry, load, incompatible_temperature, material, profile, output_radius,
            axial_restraint="fixed", evidence_id="synthetic-mismatch",
        )
    except ValueError:
        rejected_mismatch += 1
    assert rejected_mismatch == 1
    return ValidationOutcome(True, {
        "free_hydrogen_hoop_stress_peak_pa": float(np.max(np.abs(
            results["free"].hydrogen_hoop_stress_pa))),
        "fixed_hydrogen_hoop_stress_peak_pa": float(np.max(np.abs(
            results["fixed"].hydrogen_hoop_stress_pa))),
        "zero_reference_stress_increment_max_pa": 0.0,
        "rejected_temperature_reference_mismatch": rejected_mismatch,
        "exact_history_samples": len(history.samples),
        "rejected_forged_history": history_forgery_rejected,
        "rejected_nested_stress_field_mutation": nested_field_mutation_rejected,
        "rejected_time_mapping_changes": rejected_time_mapping_changes,
        "rejected_nested_input_mutation": nested_input_mutation_rejected,
    }, (
        "Synthetic concentration and expansion coefficients exercise BVP composition only; no material expansion law, concentration history, or qualification is supplied.",
    ))
