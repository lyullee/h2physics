"""Deferred exact-source bridge contract for diffusion-to-cylinder stress."""

from h2physics.cluster_validation import ValidationCase, ValidationOutcome


def cases():
    return (ValidationCase(
        identifier="cylindrical-transport-eigenstrain-bridge",
        profile="fracture-fatigue",
        entrypoint=__name__ + ":validate_transport_eigenstrain_bridge",
        invariants=(
            "only a cylindrical-shell TransportResult with exact wall-surface geometry is admitted",
            "cell-center mobile concentration is retained without mixing trapped concentration",
            "caller supplies both surface concentrations at every exact source time and explicit mapping evidence",
            "carrier, concentration basis, reference concentration, expansion coefficient and temperature are explicit",
            "caller separately identifies the transport/stress clock join and axial-uniformity assumption",
            "source and stress histories share the exact time grid and returned binding rejects later source mutation",
            "one-use issuance rejects cloned bindings and stale mobile-concentration source arrays",
            "negative or boolean surface values and radial-bound mismatch reject before BVP execution",
            "no temporal interpolation, boundary-value inference, stress-assisted diffusion or feedback is introduced",
        ),
    ),)


def validate_transport_eigenstrain_bridge(*, work_directory, **parameters):
    del work_directory, parameters
    import numpy as np

    from h2physics.adapters.transport_eigenstrain import (
        bind_cylindrical_transport_to_eigenstrain,
    )
    from h2physics.core import Origin
    from h2physics.materials import (
        CylinderGeometry,
        CylinderPressureLoad,
        DiffusionDomain,
        DiffusionMesh,
        HydrogenCarrier,
        IsotropicThermoelasticMaterial,
        RadialTemperatureProfile,
        SurfaceCondition,
        TransportBoundary,
    )

    inner, outer, length = 0.04, 0.08, 1.5
    mesh = DiffusionMesh.cylindrical_shell(inner, outer, length, 5)
    carrier = HydrogenCarrier("atomic_hydrogen", 1.008e-3)
    times = np.array([0.0, 2.0, 4.0])
    domain = DiffusionDomain(carrier, mesh, lambda temperature_k: 2.0e-10)
    transport = domain.simulate(
        times, np.full(mesh.cell_centers_m.shape, 0.2),
        boundary=lambda time_s: TransportBoundary(
            SurfaceCondition("concentration", 1.0),
            SurfaceCondition("concentration", 0.1),
        ),
        temperature_k=lambda time_s: 300.0,
        relative_tolerance=1e-8,
        absolute_tolerance_mol_m3=1e-10,
    )
    geometry = CylinderGeometry(inner, outer, "closed", "synthetic-coupled-cylinder")
    loads = tuple(CylinderPressureLoad(3.0e6, 1.0e5, f"synthetic-load-{i}", Origin.SYNTHETIC)
                  for i in range(times.size))
    radial_temperature = np.linspace(inner, outer, 9)
    temperature_profiles = tuple(RadialTemperatureProfile(
        radial_temperature, np.linspace(300.0, 305.0, radial_temperature.size),
        298.15, f"synthetic-temperature-{i}", "synthetic-temperature-map",
    ) for i in range(times.size))
    material = IsotropicThermoelasticMaterial(
        190e9, 0.29, 12e-6, "synthetic-steel", "synthetic-elastic-properties",
    )
    surfaces = np.column_stack((np.ones(times.size), np.full(times.size, 0.1)))
    def build_binding(surface_values=surfaces, selected_geometry=geometry):
        return bind_cylindrical_transport_to_eigenstrain(
            transport, surface_values, selected_geometry, loads, temperature_profiles,
            material, np.linspace(inner, outer, 25),
            reference_concentration_mol_m3=0.2,
            linear_expansion_m3_per_mol=1e-7,
            reference_temperature_k=298.15,
            concentration_basis_id="synthetic-mobile-atomic-H-mol-per-m3",
            profile_id="synthetic-coupled-profile",
            mapping_evidence_id="synthetic-surface-extension-evidence",
            clock_mapping_evidence_id="synthetic-shared-clock-mapping",
            axial_uniformity_evidence_id="synthetic-axial-uniformity",
            clock_id="synthetic-shared-clock",
            evidence_id="synthetic-quasistatic-cylinder-equation",
            axial_restraint="free",
        )

    binding = build_binding()
    assert binding.require_current() is binding
    assert binding.stress_history.sample_at(1).hydrogen_profile is not None
    assert np.array_equal(binding.stress_history.time_s, transport.time_s)
    profile = binding.stress_history.samples[0].hydrogen_profile
    assert np.array_equal(profile.concentration_mol_m3[1:-1], transport.mobile_mol_m3[0])
    assert profile.carrier is transport.carrier
    from dataclasses import replace
    forged_binding_rejected = 0
    try:
        replace(binding)
    except ValueError:
        forged_binding_rejected += 1
    assert forged_binding_rejected == 1
    invalid_inputs_rejected = 0
    negative_surface = np.array(surfaces, copy=True)
    negative_surface[0, 0] = -1.0
    for surface_values, selected_geometry, error_type in (
        (negative_surface, geometry, ValueError),
        (np.ones(surfaces.shape, dtype=bool), geometry, TypeError),
        (surfaces, CylinderGeometry(inner * 0.99, outer, "closed",
                                    "synthetic-mismatched-cylinder"), ValueError),
    ):
        try:
            build_binding(surface_values, selected_geometry)
        except error_type:
            invalid_inputs_rejected += 1
    assert invalid_inputs_rejected == 3
    metrics = {
        "exact_samples": len(binding.stress_history.samples),
        "source_cells_per_sample": transport.mobile_mol_m3.shape[1],
        "maximum_total_inventory_residual_mol": float(np.max(np.abs(transport.total_residual_mol))),
        "rejected_cloned_binding": forged_binding_rejected,
        "rejected_invalid_inputs": invalid_inputs_rejected,
    }
    changed_mobile = np.array(transport.mobile_mol_m3, copy=True)
    changed_mobile[0, 0] += 1e-6
    object.__setattr__(transport, "mobile_mol_m3", changed_mobile)
    stale_source_rejected = 0
    try:
        binding.require_current()
    except ValueError:
        stale_source_rejected += 1
    assert stale_source_rejected == 1
    metrics["rejected_stale_transport_source"] = stale_source_rejected
    return ValidationOutcome(True, metrics, (
        "Synthetic transport and expansion coefficients exercise the typed source bridge only; "
        "they do not qualify material transport or hydrogen expansion parameters.",
    ))
