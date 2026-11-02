"""Deferred contracts for finite staged photochemical operation."""

from h2physics.cluster_validation import ValidationCase, ValidationOutcome


def cases():
    return (
        ValidationCase(
            identifier="photochemical-adjacent-finite-operation",
            profile="hydrogen-engine",
            entrypoint=__name__ + ":validate_adjacent_finite_operation",
            parameters={},
            invariants=(
                "adjacent windows retain their common absolute clock and original rate receipts",
                "per-window conversion reuses one exact stoichiometric reaction and chains finite inventories",
                "operation optical and caloric summaries reconstruct from original segment results",
                "photochemical conversion and operation traces require one-use function issuance",
                "issued conversions reject clones and downstream use after nested input mutation",
                "insufficient later inventory preserves all completed segments and the original failure",
                "no kinetics, dynamic optical response or automatic light termination is inferred",
            ),
        ),
        ValidationCase(
            identifier="photochemical-gibbs-path-energy-bound",
            profile="photochemistry",
            entrypoint=__name__ + ":validate_gibbs_path_energy_bound",
            invariants=(
                "caller reaction affinity is integrated along the exact finite reaction extent",
                "path compositions reconstruct from the retained stoichiometric inventory",
                "reaction state evidence matches the actual photon-yield condition state",
                "absorbed optical energy is only a necessary energy upper-bound comparison",
                "a passing bound does not imply radiation exergy, kinetics, or reactor feasibility",
            ),
        ),
    )


def validate_gibbs_path_energy_bound(*, work_directory, **parameters):
    del work_directory, parameters
    from dataclasses import replace

    import numpy as np

    from h2physics.core import Origin
    from h2physics.photochemistry import (
        BeerLambertPath, PhotoConditions, PhotonSupply, PhotonYield,
        SteadyPhotoWindow, assess_photo_gibbs_energy, convert_photon_exposure,
        photon_hydrogen_rate,
    )
    from h2physics.reactions import ChemicalSpecies, StoichiometricReaction

    geometry = "synthetic-gibbs-photo-geometry"
    conditions = PhotoConditions(
        "synthetic-catalyst", "synthetic-medium", 1e-3, 300., 1e5,
        geometry, "synthetic-photo-condition-state",
    )
    supply = PhotonSupply.from_lines(
        [500e-9], [0.25], geometry_id=geometry, source_id="synthetic-gibbs-light",
    )
    optical_path = BeerLambertPath.uniform(
        supply, depth_m=0.01, absorption_coefficient_m_inv=100.,
        evidence_id="synthetic-gibbs-optical-path",
    )
    yield_curve = PhotonYield.bind(
        supply, [0.2], basis="absorbed_electron_equivalents", conditions=conditions,
        evidence_id="synthetic-gibbs-yield", origin=Origin.SYNTHETIC,
    )
    rate = photon_hydrogen_rate(supply, optical_path, yield_curve)
    reaction = StoichiometricReaction("synthetic-gibbs-water-splitting", (
        ChemicalSpecies("water", {"H": 2, "O": 1}, 0.018, "declared-liquid"),
        ChemicalSpecies("hydrogen", {"H": 2}, 0.002, "declared-gas"),
        ChemicalSpecies("oxygen", {"O": 2}, 0.032, "declared-gas"),
    ), (-2., 2., 1.))
    conversion = convert_photon_exposure(
        rate, SteadyPhotoWindow(0., 1., "synthetic-gibbs-clock", "synthetic-window"),
        reaction=reaction, initial_mol={"water": 1e-5}, hydrogen_species_id="hydrogen",
    )
    extent = conversion.conversion.extent_mol
    if extent <= 0. or conversion.absorbed_optical_energy_j <= 0.:
        raise AssertionError("The synthetic photon conversion must carry positive product and optical energy")
    extent_path = np.linspace(0., extent, 5)
    energy_per_extent = conversion.absorbed_optical_energy_j/extent
    insufficient = assess_photo_gibbs_energy(
        conversion, reaction_extent_mol=extent_path,
        reaction_gibbs_j_mol=np.full(5, 2.*energy_per_extent),
        thermodynamic_state_id=conditions.evidence_id,
        thermodynamic_source_id="synthetic constant-affinity provider",
        path_evidence_id="synthetic constant path interpolation",
    )
    sufficient = assess_photo_gibbs_energy(
        conversion, reaction_extent_mol=extent_path,
        reaction_gibbs_j_mol=np.full(5, 0.5*energy_per_extent),
        thermodynamic_state_id=conditions.evidence_id,
        thermodynamic_source_id="synthetic constant-affinity provider",
        path_evidence_id="synthetic constant path interpolation",
    )
    if insufficient.photon_energy_necessary_condition_met or not sufficient.photon_energy_necessary_condition_met:
        raise AssertionError("The photon-only necessary energy bound misclassified its synthetic cases")
    if not np.array_equal(sufficient.sampled_species_amounts_mol[-1], conversion.conversion.final_mol):
        raise AssertionError("The integrated Gibbs path lost its exact finite-reaction endpoint")
    try:
        replace(sufficient)
    except ValueError:
        pass
    else:
        raise AssertionError("A copied Gibbs budget reused its consumed issuer")
    return ValidationOutcome(True, {
        "finite_reaction_extent_mol": extent,
        "absorbed_optical_energy_j": conversion.absorbed_optical_energy_j,
        "integrated_gibbs_demand_j": sufficient.reaction_gibbs_change_j,
        "insufficient_path_margin_j": insufficient.photon_energy_margin_j,
        "sufficient_path_margin_j": sufficient.photon_energy_margin_j,
        "composition_samples": int(len(sufficient.sampled_species_amounts_mol)),
    }, (
        "Synthetic finite Gibbs path and optical-energy bound only; no material thermodynamics are validated.",
        "The comparison is necessary, not sufficient; no radiation exergy, thermal-work conversion or kinetics is inferred.",
    ))


def validate_adjacent_finite_operation(*, work_directory, **parameters):
    from dataclasses import replace

    import numpy as np

    from h2physics.core import Origin
    from h2physics.photochemistry import (
        BeerLambertPath, PhotoConditions, PhotoConversion, PhotoOperationError,
        PhotoOperationTrace, PhotonSupply,
        PhotonYield, SteadyPhotoWindow, photon_hydrogen_rate,
        run_photochemical_operation,
    )
    from h2physics.reactions import ChemicalSpecies, StoichiometricReaction

    geometry = "authored-photo-geometry"
    conditions = PhotoConditions(
        "authored-catalyst", "authored-medium", .001, 300., 1e5,
        geometry, "authored-condition-evidence",
    )
    reaction = StoichiometricReaction("authored-water-splitting", (
        ChemicalSpecies("water", {"H": 2, "O": 1}, .018, "declared-liquid"),
        ChemicalSpecies("hydrogen", {"H": 2}, .002, "declared-gas"),
        ChemicalSpecies("oxygen", {"O": 2}, .032, "declared-gas"),
    ), (-2., 2., 1.))

    def rate(power, source):
        supply = PhotonSupply.from_lines(
            [500e-9], [power], geometry_id=geometry, source_id=source,
        )
        path = BeerLambertPath.uniform(
            supply, depth_m=.01, absorption_coefficient_m_inv=100.,
            evidence_id="authored-optical-boundary",
        )
        yield_curve = PhotonYield.bind(
            supply, [.2], basis="absorbed_electron_equivalents",
            conditions=conditions, evidence_id="authored-condition-specific-yield",
            origin=Origin.SYNTHETIC,
        )
        return photon_hydrogen_rate(supply, path, yield_curve)

    first, second = rate(.25, "authored-light-a"), rate(.5, "authored-light-b")
    windows = (
        (first, SteadyPhotoWindow(0., 1., "authored-clock", "window-a")),
        (second, SteadyPhotoWindow(1., 2., "authored-clock", "window-b")),
    )
    trace = run_photochemical_operation(
        windows, reaction=reaction, initial_mol={"water": 1e-5},
        hydrogen_species_id="hydrogen",
    )
    if len(trace.segments) != 2 or trace.clock_id != "authored-clock":
        raise AssertionError("Adjacent photon windows did not retain their declared operation axis")
    if not np.array_equal(trace.initial_mol, trace.segments[0].conversion.initial_mol):
        raise AssertionError("Operation input inventory differs from the first segment")
    if not np.array_equal(trace.final_mol, trace.segments[-1].conversion.final_mol):
        raise AssertionError("Operation final inventory differs from the last segment")
    if not np.array_equal(trace.segments[1].conversion.initial_mol,
                          trace.segments[0].conversion.final_mol):
        raise AssertionError("The second exposure did not consume the first segment's remaining inventory")
    if not np.isclose(trace.incident_optical_energy_j, sum(
            segment.incident_optical_energy_j for segment in trace.segments), rtol=1e-14):
        raise AssertionError("Optical energy summary does not reconstruct from the segment receipts")
    first_conversion = trace.segments[0]
    try:
        PhotoConversion(
            first_conversion.rate, first_conversion.window, first_conversion.conversion,
            first_conversion.incident_optical_energy_j, first_conversion.absorbed_optical_energy_j,
            first_conversion.reaction_enthalpy_change_j, first_conversion.required_isothermal_heat_j,
            first_conversion.energy_basis_id,
        )
    except ValueError:
        pass
    else:
        raise AssertionError("A caller-created PhotoConversion claimed calculation provenance")
    try:
        replace(first_conversion)
    except ValueError:
        pass
    else:
        raise AssertionError("Dataclass replacement reused a consumed PhotoConversion issuer")
    try:
        PhotoOperationTrace(
            trace.reaction, trace.hydrogen_species_id, trace.clock_id,
            trace.segments, trace.initial_mol, trace.final_mol,
        )
    except ValueError:
        pass
    else:
        raise AssertionError("A caller-created operation trace claimed run provenance")
    try:
        replace(trace)
    except ValueError:
        pass
    else:
        raise AssertionError("Dataclass replacement reused a consumed operation issuer")
    original_source = first_conversion.rate.supply.source_id
    object.__setattr__(first_conversion.rate.supply, "source_id", "forged-after-conversion")
    try:
        first_conversion.require_current()
    except ValueError:
        pass
    else:
        raise AssertionError("A changed nested optical source remained current after conversion")
    object.__setattr__(first_conversion.rate.supply, "source_id", original_source)

    excessive = rate(10., "authored-light-excess")
    try:
        run_photochemical_operation(
            (windows[0], (excessive, windows[1][1])), reaction=reaction,
            initial_mol={"water": 1e-7}, hydrogen_species_id="hydrogen",
        )
    except PhotoOperationError as error:
        if len(error.completed_segments) != 1 or error.failed_window is not windows[1][1]:
            raise AssertionError("Failure did not preserve the completed prefix and failed interval")
        if error.cause.rate is not excessive:
            raise AssertionError("Original segment inventory failure was not retained")
    else:
        raise AssertionError("Finite photochemical operation must reject insufficient later inventory")
    return ValidationOutcome(True, {
        "segment_count": len(trace.segments),
        "hydrogen_final_mol": float(trace.final_mol[1]),
        "incident_energy_j": trace.incident_optical_energy_j,
    }, (
        "Prescribed segment yields are not a catalyst-kinetics prediction",
        "Finite inventory rejection does not imply automatic light shutoff",
    ))
