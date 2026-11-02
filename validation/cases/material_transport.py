"""Deferred host-side surface-solubility-to-diffusion boundary contract."""

from h2physics.cluster_validation import ValidationCase, ValidationOutcome


def cases():
    return (ValidationCase(
        identifier="power-law-solubility-diffusion-boundary",
        profile="material-transport",
        entrypoint=__name__ + ":validate_boundary",
        invariants=(
            "one declared carrier and PowerLawSolubility map gas fugacity to mobile-entity concentration",
            "time-varying endpoint fugacities use the same solver-evaluated temperature as bulk diffusion",
            "surface-equilibrium mapping requires caller evidence and adds no kinetic law",
            "mismatched solubility and diffusion carrier identities are rejected",
            "slab diffusion results require native finite-volume issuance and reject copied or changed projections",
        ),
    ), ValidationCase(
        identifier="quasi-steady-permeation-history",
        profile="material-transport",
        entrypoint=__name__ + ":validate_quasi_steady_history",
        invariants=(
            "each signed sampled flux reuses the existing explicit steady slab law",
            "mass-per-area accumulation is a time integral over one identified increasing clock",
            "carrier mass and H2-equivalent conversions remain component-consistent",
            "quasi-steady use requires caller evidence and never claims transient membrane response",
            "mismatched clock grids and forged cumulative ledgers are rejected",
        ),
    ), ValidationCase(
        identifier="steady-permeation-surface-resistance",
        profile="material-transport",
        entrypoint=__name__ + ":validate_surface_resistance_permeation",
        invariants=(
            "upstream film, bulk diffusion and downstream film use one declared concentration/carrier basis",
            "signed flux equals the equilibrium concentration difference divided by total series resistance",
            "resolved membrane-side concentrations reproduce each film and bulk drop",
            "swapping boundary fugacities reverses flux without changing model scope",
            "surface mapping and transfer data require separate evidence IDs",
        ),
    ), ValidationCase(
        identifier="transient-fugacity-driven-surface-films",
        profile="material-transport",
        entrypoint=__name__ + ":validate_fugacity_surface_films",
        invariants=(
            "time-dependent hydrogen fugacity is mapped to the declared solid carrier using the solver temperature",
            "both surface-film transfer velocities are independently evaluated at the current time and temperature",
            "film boundaries preserve the common carrier and concentration basis",
            "missing mapping or transfer evidence and negative callback values are rejected",
        ),
    ), ValidationCase(
        identifier="cylindrical-shell-hydrogen-diffusion",
        profile="material-transport",
        entrypoint=__name__ + ":validate_cylindrical_shell_diffusion",
        invariants=(
            "radial shell cell volumes and lateral face areas include the declared finite length",
            "exact logarithmic radial resistance reproduces the steady Fick profile for constant D",
            "mesh steady profile uses the transient owner conductances and is read-only",
            "signed steady rate and profile reverse consistently when boundary concentrations are swapped",
            "unrepresentable series resistance is rejected without returning nonfinite values",
            "inner/outer boundary flux signs and integrated mobile inventory reconcile",
            "result histories reproduce the original successful native state and ledger before downstream access",
            "replacement with an altered projected concentration field is rejected",
            "zero axial/end transport and no stress-driven flux are explicit model limits",
        ),
    ), ValidationCase(
        identifier="radial-hydrogen-diffusion-shell-api",
        profile="material-transport",
        entrypoint=__name__ + ":validate_shell_api",
        invariants=(
            "one public shell API constructs the existing cylindrical and spherical control-volume meshes",
            "cylindrical length is required while spherical length is rejected",
            "returned transport uses whole-shell molar inventories and face fluxes",
            "native finite-volume result and signed boundary ledgers remain current",
            "radial-only, prescribed-temperature limits are explicit",
        ),
    ), ValidationCase(
        identifier="axial-annulus-diffusion-geometry-contract",
        profile="material-transport",
        entrypoint=__name__ + ":validate_axial_annulus_geometry",
        invariants=(
            "the axial-only facade delegates to the shared planar mesh and DiffusionDomain",
            "positive ordered radii, length and integer cell count are required",
            "all axial faces use the exact constant annulus area and each cell volume is area times axial width",
            "caller carrier, diffusivity callback and trap parameters remain attached to the facade",
            "radial gradients, r-z coupling and material qualification are excluded",
        ),
    ), ValidationCase(
        identifier="diffusion-outward-h2-finite-source-handoff",
        profile="material-transport",
        entrypoint=__name__ + ":validate_finite_source_handoff",
        invariants=(
            "native integrated right-face molar flux times explicit area becomes finite H2 mass",
            "outward-only interval sign and mobile entity molecular mass are preserved",
            "clock, source plane, gas-state projection and product origin remain explicit",
            "atomic-H carrier requires explicit H2 recombination evidence",
            "native diffusion and finite-source mutations invalidate the receipt",
            "no thermal state, pipe, nozzle or dispersion dynamics are inferred",
        ),
    ),)


def validate_axial_annulus_geometry(*, work_directory, **parameters):
    """Check the geometry/API boundary without solving a diffusion history."""
    del work_directory, parameters
    import math

    import numpy as np

    from h2physics.cluster_validation import ValidationOutcome
    from h2physics.materials import AxialAnnulusDiffusion, HydrogenCarrier

    carrier = HydrogenCarrier("molecular_hydrogen", 2.016e-3)
    def diffusivity(temperature):
        return 1.0e-9

    model = AxialAnnulusDiffusion(
        carrier, inner_radius_m=0.04, outer_radius_m=0.05,
        length_m=1.2, cells=8, diffusivity_m2_s=diffusivity,
    )
    area = math.pi * (0.05 - 0.04) * (0.05 + 0.04)
    if model.mesh.geometry != "planar":
        raise AssertionError("Axial annulus did not reuse the planar diffusion mesh")
    if not np.array_equal(model.mesh.face_areas_m2, np.full(9, area)):
        raise AssertionError("Axial annulus faces are not the exact constant section")
    expected_volumes = area * np.diff(model.mesh.face_positions_m)
    if not np.array_equal(model.mesh.cell_volumes_m3, expected_volumes):
        raise AssertionError("Axial annulus volumes do not match area times axial width")
    if model.carrier is not carrier or model.diffusivity_m2_s is not diffusivity:
        raise AssertionError("Caller material/coefficient lineage was not retained")
    return ValidationOutcome(True, {
        "annulus_area_m2": area,
        "represented_volume_m3": float(model.mesh.cell_volumes_m3.sum()),
        "axial_cells": model.cells,
    }, limitations=(
        "geometry/API contract only; no physical integration or material qualification",
        "radial gradients and r-z coupling are excluded",
    ))


def validate_shell_api(*, work_directory, **parameters):
    del work_directory, parameters
    import numpy as np

    from h2physics.cluster_validation import ValidationOutcome
    from h2physics.materials import HydrogenCarrier, HydrogenDiffusionShell
    from h2physics.materials.finite_volume import TransportBoundary
    from h2physics.materials.transport import SurfaceCondition

    carrier = HydrogenCarrier("molecular_hydrogen", 2.016e-3)
    common = dict(carrier=carrier, inner_radius_m=0.04, outer_radius_m=0.05,
                  cells=8, diffusivity_m2_s=lambda temperature: 1.0e-9)
    cylindrical = HydrogenDiffusionShell(**common, geometry="cylindrical", length_m=1.2)
    spherical = HydrogenDiffusionShell(**common, geometry="spherical")
    rejected_geometry_arguments = 0
    for kwargs in (
        {**common, "geometry": "cylindrical"},
        {**common, "geometry": "spherical", "length_m": 1.2},
    ):
        try:
            HydrogenDiffusionShell(**kwargs)
        except ValueError:
            rejected_geometry_arguments += 1
    if rejected_geometry_arguments != 2:
        raise AssertionError("Shell API accepted incomplete or inapplicable geometry arguments")
    if cylindrical.mesh.geometry != "cylindrical_shell" or spherical.mesh.geometry != "spherical_shell":
        raise AssertionError("Shell API did not retain its selected physical geometry")
    cylinder_volume = np.pi * 1.2 * (0.05**2 - 0.04**2)
    sphere_volume = 4.0 * np.pi / 3.0 * (0.05**3 - 0.04**3)
    if not np.isclose(cylindrical.mesh.cell_volumes_m3.sum(), cylinder_volume):
        raise AssertionError("Cylindrical wrapper omitted its finite length")
    if not np.isclose(spherical.mesh.cell_volumes_m3.sum(), sphere_volume):
        raise AssertionError("Spherical wrapper did not recover shell volume")
    result = spherical.simulate(
        [0.0, 1.0], np.full(8, 2.0),
        boundary=lambda time: TransportBoundary(
            SurfaceCondition("concentration", 3.0),
            SurfaceCondition("concentration", 1.0),
        ),
        temperature_k=lambda time: 298.15,
    )
    result.require_current()
    if np.max(np.abs(result.total_residual_mol)) > 1.0e-10:
        raise AssertionError("Spherical-shell total molar inventory did not close")
    if result.mesh.geometry != "spherical_shell":
        raise AssertionError("Transport receipt lost shell geometry")
    if result.left_integrated_mol[-1] <= 0.0 or result.right_integrated_mol[-1] <= 0.0:
        raise AssertionError(
            "Both face integrals must be positive for transport in the left-to-right coordinate"
        )
    return ValidationOutcome(True, {
        "cylindrical_volume_m3": float(cylinder_volume),
        "spherical_volume_m3": float(sphere_volume),
        "spherical_total_residual_mol": float(np.max(np.abs(result.total_residual_mol))),
        "left_integrated_mol": float(result.left_integrated_mol[-1]),
        "right_integrated_mol": float(result.right_integrated_mol[-1]),
        "rejected_geometry_argument_forms": rejected_geometry_arguments,
        "cylinder_length_m": cylindrical.length_m,
        "extensive_inventory_unit": "mol",
    }, (
        "Synthetic geometry and zero-gradient ledger contract only; material properties, transient qualification, end effects, and heat coupling remain outside this case.",
    ))


def validate_finite_source_handoff(*, work_directory, **parameters):
    del work_directory, parameters
    import numpy as np

    from h2physics.adapters.diffusion_finite_source import source_from_diffusion_result
    from h2physics.core import Origin, PropertyBasis, ThermoState
    from h2physics.materials import DiffusionSlab, HydrogenCarrier
    from h2physics.materials.transport import SlabBoundary, SurfaceCondition
    from h2physics.release import SourceLocation

    carrier = HydrogenCarrier("molecular_hydrogen", 2.016e-3)
    diffusion = DiffusionSlab(carrier, thickness_m=0.01, cells=3,
        diffusivity_m2_s=lambda temperature: 1e-9).simulate(
            [0., 1., 2., 3.], [100., 100., 100.],
            boundary=lambda time: SlabBoundary(
                SurfaceCondition("flux", 0.), SurfaceCondition("flux", 1e-8)),
            temperature_k=lambda time: 300.,
        )
    state = ThermoState(PropertyBasis("H2", "authored-source-state"),
        101325., 300., 0.0812, 1e6, 1e6-101325./0.0812, 0.0, "gas",
        vapor_mass_fraction=1.0)
    location = SourceLocation("material-transport-slab", "authored-clock",
        "membrane-exit-plane", (0., 0., 0.), (1., 0., 0.))
    handoff = source_from_diffusion_result(diffusion, surface_area_m2=0.25,
        location=location, clock_alignment_evidence_id="authored-time-origin-map",
        state_projection_evidence_id="authored-h2-state-projection",
        source_evidence_id="authored-slab-exit-source",
        gas_state=state, origin=Origin.PREDICTED)
    handoff.require_current()
    expected = np.diff(diffusion.right_integrated_flux_mol_m2)*0.25*carrier.molar_mass_kg_mol
    assert np.array_equal(handoff.source.mass_kg, expected)
    assert np.array_equal(handoff.source.edges_s, diffusion.time_s)
    original = handoff.source.mass_kg
    altered = original.copy()
    altered[-1] *= 1.01
    object.__setattr__(handoff.source, "mass_kg", altered)
    try:
        handoff.require_current()
    except ValueError:
        stale_source_rejected = True
    else:
        raise AssertionError("Changed finite mass bins remained attached to diffusion flux")
    object.__setattr__(handoff.source, "mass_kg", original)
    handoff.require_current()
    atomic = HydrogenCarrier("atomic_hydrogen", 1.008e-3)
    atomic_diffusion = DiffusionSlab(atomic, thickness_m=0.01, cells=3,
        diffusivity_m2_s=lambda temperature: 1e-9).simulate(
            [0., 1., 2., 3.], [100., 100., 100.],
            boundary=lambda time: SlabBoundary(
                SurfaceCondition("flux", 0.), SurfaceCondition("flux", 1e-8)),
            temperature_k=lambda time: 300.,
        )
    try:
        source_from_diffusion_result(atomic_diffusion, surface_area_m2=0.25,
            location=location, clock_alignment_evidence_id="authored-time-origin-map",
            state_projection_evidence_id="authored-atomic-H-state-projection",
            source_evidence_id="authored-atomic-H-source", gas_state=state,
            origin=Origin.PREDICTED)
    except ValueError as error:
        atomic_recombination_rejected = "recombination evidence" in str(error)
    else:
        raise AssertionError("Atomic-H boundary flux was silently reinterpreted as H2")
    return ValidationOutcome(True, {
        "integrated_outward_h2_mass_kg": float(original.sum()),
        "surface_area_m2": handoff.area_m2,
        "interval_count": len(original),
        "stale_source_rejected": stale_source_rejected,
        "atomic_recombination_required": atomic_recombination_rejected,
    }, (
        "Authored molecular-H2 surface-flux case only; no permeation material is qualified",
        "H2 gas-state basis is a caller projection because diffusion carries no gas energy/EOS state",
        "No downstream pipe, nozzle or atmospheric consequence is modeled",
    ))


def validate_boundary(*, work_directory, **parameters):
    from math import isclose

    import numpy as np

    from h2physics.materials import (
        DiffusionSlab,
        HydrogenCarrier,
        PowerLawSolubility,
        PowerLawSolubilityBoundary,
    )

    del work_directory, parameters
    carrier = HydrogenCarrier("atomic_hydrogen", 1.008e-3)
    solubility = PowerLawSolubility(
        carrier, lambda temperature: 2.0e-9 * temperature / 300.0, 0.5,
    )
    boundary = PowerLawSolubilityBoundary(
        solubility,
        lambda time: 2.0e6 if time < 1.0 else 8.0e6,
        1.0e6,
        "authored-surface-equilibrium-mapping",
    )
    first = boundary.at_temperature(0.5, 300.0)
    later = boundary.at_temperature(1.5, 450.0)
    assert first.left.kind == first.right.kind == "concentration"
    assert later.left.kind == later.right.kind == "concentration"
    assert isclose(first.left.value, 2.0e-9 * (2.0e6 ** 0.5), rel_tol=1e-14)
    assert isclose(first.right.value, 2.0e-9 * (1.0e6 ** 0.5), rel_tol=1e-14)
    assert isclose(later.left.value, 3.0e-9 * (8.0e6 ** 0.5), rel_tol=1e-14)
    assert isclose(later.right.value, 3.0e-9 * (1.0e6 ** 0.5), rel_tol=1e-14)
    result = DiffusionSlab(
        carrier,
        thickness_m=0.01,
        cells=3,
        diffusivity_m2_s=lambda temperature: 1.0e-9,
    ).simulate(
        [0.0, 1.0], [0.0, 0.0, 0.0], boundary=boundary,
        temperature_k=lambda time: 300.0 + 100.0 * time,
    )
    assert result.mobile_mol_m3.shape == (2, 3)
    result.require_current()
    from dataclasses import replace
    from h2physics.materials.transport import DiffusionResult
    try:
        DiffusionResult(
            result.carrier, result.time_s, result.cell_centers_m,
            result.mobile_mol_m3, result.trapped_mol_m3,
            result.left_integrated_flux_mol_m2,
            result.right_integrated_flux_mol_m2,
            result.inventory_residual_mol_m2, result.function_evaluations,
            result._source_result,
        )
    except ValueError:
        direct_forgery_rejected = True
    else:
        raise AssertionError("A directly constructed slab result claimed native solver output")
    try:
        replace(result, mobile_mol_m3=np.zeros_like(result.mobile_mol_m3))
    except ValueError:
        clone_rejected = True
    else:
        raise AssertionError("A cloned slab result retained native solver issuance")
    object.__setattr__(result, "mobile_mol_m3", np.ones_like(result.mobile_mol_m3))
    try:
        result.require_current()
    except ValueError:
        post_capture_mutation_rejected = True
    else:
        raise AssertionError("A mutated slab result remained current")
    incompatible = DiffusionSlab(
        HydrogenCarrier("molecular_hydrogen", 2.016e-3),
        thickness_m=0.01,
        cells=3,
        diffusivity_m2_s=lambda temperature: 1.0e-9,
    )
    try:
        incompatible.simulate(
            [0.0, 1.0], [0.0, 0.0, 0.0], boundary=boundary,
            temperature_k=lambda time: 300.0,
        )
    except ValueError:
        mismatch_rejected = True
    else:
        raise AssertionError("An atomic-H surface solubility boundary entered molecular-H2 diffusion")
    return ValidationOutcome(True, {
        "carrier": carrier.identity,
        "surface_mapping_evidence_id": boundary.evidence_id,
        "time_varying_fugacity_mapped": True,
        "shared_temperature_input_mapped": True,
        "native_slab_result_forgery_rejected": direct_forgery_rejected,
        "native_slab_result_clone_rejected": clone_rejected,
        "post_capture_slab_result_mutation_rejected": post_capture_mutation_rejected,
        "mismatched_carrier_rejected": mismatch_rejected,
    }, (
        "Synthetic coefficient and endpoint fugacities verify interface arithmetic only; no material property is qualified.",
    ))


def validate_quasi_steady_history(*, work_directory, **parameters):
    from math import isclose

    from h2physics.materials import (
        HydrogenCarrier,
        PowerLawSolubility,
        quasi_steady_permeation_history,
    )

    del work_directory, parameters
    carrier = HydrogenCarrier("molecular_hydrogen", 2.016e-3)
    solubility = PowerLawSolubility(carrier, lambda temperature: 1e-8, 1.)
    history = quasi_steady_permeation_history(
        solubility,
        time_s=[10., 12., 15.],
        upstream_fugacity_pa=[3e6, 5e6, 4e6],
        downstream_fugacity_pa=[1e6, 2e6, 2e6],
        temperature_k=[300., 310., 320.],
        diffusivity_m2_s=lambda temperature: 1e-9 * temperature / 300.,
        thickness_m=.01,
        clock_id="synthetic-absolute-clock",
        boundary_evidence_id="synthetic-boundary-input",
        quasi_steady_evidence_id="caller-accepted-steady-regime",
    )
    expected = sum(
        .5 * (history.hydrogen_mass_flux_kg_m2_s[i]
              + history.hydrogen_mass_flux_kg_m2_s[i + 1])
        * (history.time_s[i + 1] - history.time_s[i])
        for i in range(len(history.time_s) - 1)
    )
    if not isclose(history.cumulative_hydrogen_mass_kg_m2[-1], expected,
                   rel_tol=2e-12, abs_tol=1e-18):
        raise AssertionError("Per-area permeated mass does not match the sampled flux integral")
    return ValidationOutcome(True, {
        "carrier": carrier.identity,
        "clock_id": history.clock_id,
        "final_cumulative_hydrogen_mass_kg_m2": float(
            history.cumulative_hydrogen_mass_kg_m2[-1]
        ),
    }, (
        "Synthetic values exercise the selected quasi-steady interface only; transient diffusion and material parameters remain unqualified.",
    ))


def validate_cylindrical_shell_diffusion(*, work_directory, **parameters):
    from math import log

    import numpy as np

    from h2physics.materials import (
        DiffusionDomain,
        DiffusionMesh,
        HydrogenCarrier,
        SurfaceCondition,
        TransportBoundary,
    )
    from h2physics.cluster_validation import ValidationOutcome

    del work_directory, parameters
    inner_radius, outer_radius, length = 0.04, 0.06, 1.7
    inner_c, outer_c, diffusivity = 2.0, 8.0, 3.0e-10
    mesh = DiffusionMesh.cylindrical_shell(
        inner_radius, outer_radius, length, 24,
    )
    if not np.allclose(
        mesh.face_areas_m2, 2 * np.pi * length * mesh.face_positions_m,
        rtol=2e-14, atol=0.0,
    ):
        raise AssertionError("Cylindrical shell lateral areas omit the declared length")
    expected_volume = np.pi * length * (outer_radius**2 - inner_radius**2)
    if not np.isclose(np.sum(mesh.cell_volumes_m3), expected_volume, rtol=2e-14, atol=0.0):
        raise AssertionError("Cylindrical shell cells do not recover the annular volume")
    initial = mesh.steady_concentration_profile_mol_m3(
        inner_c, outer_c,
    )
    reverse_profile = mesh.steady_concentration_profile_mol_m3(
        outer_c, inner_c,
    )
    if initial.flags.writeable or not np.allclose(
        initial + reverse_profile, inner_c + outer_c, rtol=2e-14, atol=2e-14,
    ):
        raise AssertionError("Steady mesh profile is mutable or fails signed reversal symmetry")
    try:
        initial.setflags(write=True)
    except ValueError:
        hard_read_only_profile = True
    else:
        raise AssertionError("A caller must not be able to make a returned steady profile writable")
    result = DiffusionDomain(
        HydrogenCarrier("atomic_hydrogen", 1.008e-3), mesh,
        lambda temperature: diffusivity,
    ).simulate(
        [0.0, 1.0e5], initial,
        boundary=lambda time: TransportBoundary(
            SurfaceCondition("concentration", inner_c),
            SurfaceCondition("concentration", outer_c),
        ),
        temperature_k=lambda time: 298.15,
        relative_tolerance=2.0e-9,
        absolute_tolerance_mol_m3=2.0e-11,
    )
    result.require_current()
    expected_flux = (
        -2 * np.pi * length * diffusivity * (outer_c - inner_c)
        / log(outer_radius / inner_radius)
    )
    steady_rate = mesh.steady_transport_rate_mol_s(diffusivity, inner_c, outer_c)
    if not np.isclose(steady_rate, expected_flux, rtol=2e-14, atol=1e-24):
        raise AssertionError("Mesh steady resistance does not reproduce the cylindrical Fick rate")
    from dataclasses import replace
    extreme_mesh = replace(mesh, conductance_m=np.full_like(mesh.conductance_m, 1.0e-320))
    try:
        extreme_mesh.steady_concentration_profile_mol_m3(inner_c, outer_c)
    except ValueError as error:
        if "resistance" not in str(error):
            raise
        unrepresentable_resistance_rejected = True
    else:
        raise AssertionError("An unrepresentable steady resistance returned a profile")
    scale = max(abs(expected_flux), 1.0e-30)
    left_flux = result.left_integrated_mol[-1] / 1.0e5
    right_flux = result.right_integrated_mol[-1] / 1.0e5
    relative_flux_error = max(
        abs(left_flux - expected_flux), abs(right_flux - expected_flux),
    ) / scale
    maximum_profile_drift = float(np.max(np.abs(result.mobile_mol_m3[-1] - initial)))
    if relative_flux_error > 2.0e-6:
        raise AssertionError("Cylindrical logarithmic profile does not produce its analytic Fick flux")
    if maximum_profile_drift > 2.0e-7 * max(outer_c, 1.0):
        raise AssertionError("Analytic cylindrical steady profile changed under fixed boundaries")
    if np.max(np.abs(result.total_residual_mol)) > 2.0e-7:
        raise AssertionError("Cylindrical shell total inventory ledger does not close")
    altered_mobile = np.array(result.mobile_mol_m3, copy=True)
    altered_mobile[0, 0] += 1.0
    try:
        replace(result, mobile_mol_m3=altered_mobile)
    except ValueError:
        native_projection_tampering_rejected = True
    else:
        raise AssertionError("Altered output field was detached from the original native solve")
    return ValidationOutcome(True, {
        "geometry": mesh.geometry,
        "length_m": length,
        "relative_analytic_flux_error": float(relative_flux_error),
        "steady_mesh_rate_mol_s": float(steady_rate),
        "unrepresentable_resistance_rejected": unrepresentable_resistance_rejected,
        "hard_read_only_profile": hard_read_only_profile,
        "steady_profile_endpoints_mol_m3": (float(initial[0]), float(initial[-1])),
        "left_boundary_flux_mol_s": float(left_flux),
        "right_boundary_flux_mol_s": float(right_flux),
        "maximum_profile_drift_mol_m3": maximum_profile_drift,
        "maximum_total_residual_mol": float(np.max(np.abs(result.total_residual_mol))),
        "native_projection_tampering_rejected": native_projection_tampering_rejected,
    }, (
        "The authored constant-D steady profile is a discretization and conservation check; "
        "it does not qualify steel diffusivity, stress-driven transport, end effects, or field data.",
    ))


def validate_surface_resistance_permeation(*, work_directory, **parameters):
    from math import isclose

    from h2physics.materials import (
        HydrogenCarrier,
        PowerLawSolubility,
        steady_permeation_with_surface_resistance,
    )

    del work_directory, parameters
    carrier = HydrogenCarrier("molecular_hydrogen", 2.016e-3)
    solubility = PowerLawSolubility(carrier, lambda temperature: 1.0e-8, 0.5)
    arguments = dict(
        diffusivity_m2_s=2.0e-8,
        thickness_m=1.0e-3,
        upstream_fugacity_pa=4.0e6,
        downstream_fugacity_pa=1.0e6,
        temperature_k=300.0,
        upstream_transfer_velocity_m_s=4.0e-5,
        downstream_transfer_velocity_m_s=4.0e-5,
        boundary_evidence_id="authored-power-law-boundary",
        surface_resistance_evidence_id="authored-linear-film-coefficients",
    )
    result = steady_permeation_with_surface_resistance(solubility, **arguments)
    expected_flux = (2.0e-5 - 1.0e-5) / (2.5e4 + 5.0e4 + 2.5e4)
    if not isclose(result.mobile_entity_flux_mol_m2_s, expected_flux,
                   rel_tol=2.0e-14, abs_tol=1.0e-24):
        raise AssertionError("Signed steady flux does not equal its series-resistance closure")
    if not isclose(result.upstream_equilibrium_concentration_mol_m3
                   - result.upstream_surface_concentration_mol_m3,
                   expected_flux * result.upstream_film_resistance_s_m,
                   rel_tol=2.0e-14, abs_tol=1.0e-20):
        raise AssertionError("Upstream film concentration drop does not close")
    if not isclose(result.downstream_surface_concentration_mol_m3
                   - result.downstream_equilibrium_concentration_mol_m3,
                   expected_flux * result.downstream_film_resistance_s_m,
                   rel_tol=2.0e-14, abs_tol=1.0e-20):
        raise AssertionError("Downstream film concentration drop does not close")
    reversed_result = steady_permeation_with_surface_resistance(
        solubility,
        **{**arguments, "upstream_fugacity_pa": arguments["downstream_fugacity_pa"],
           "downstream_fugacity_pa": arguments["upstream_fugacity_pa"]},
    )
    if not isclose(reversed_result.mobile_entity_flux_mol_m2_s, -expected_flux,
                   rel_tol=2.0e-14, abs_tol=1.0e-24):
        raise AssertionError("Boundary reversal did not reverse the signed flux")
    zero_gradient = steady_permeation_with_surface_resistance(
        solubility, **{**arguments, "downstream_fugacity_pa": arguments["upstream_fugacity_pa"]},
    )
    if zero_gradient.mobile_entity_flux_mol_m2_s != 0.0:
        raise AssertionError("Equal boundary fugacities must produce zero steady transport")
    return ValidationOutcome(True, {
        "carrier": carrier.identity,
        "signed_entity_flux_mol_m2_s": result.mobile_entity_flux_mol_m2_s,
        "upstream_surface_concentration_mol_m3": result.upstream_surface_concentration_mol_m3,
        "downstream_surface_concentration_mol_m3": result.downstream_surface_concentration_mol_m3,
        "boundary_evidence_id": result.boundary_evidence_id,
        "surface_resistance_evidence_id": result.surface_resistance_evidence_id,
        "reversal_and_zero_gradient_contracts": True,
    }, (
        "Synthetic inputs verify the algebraic resistance interface only; transfer coefficients, solubility, diffusivity, surface chemistry, and actual membrane observations remain unqualified.",
    ))


def validate_fugacity_surface_films(*, work_directory, **parameters):
    import numpy as np

    from h2physics.materials import (
        HydrogenCarrier,
        PowerLawSolubility,
        PowerLawSolubilityFilmBoundary,
        SurfaceFilmCondition,
    )

    del work_directory, parameters
    carrier = HydrogenCarrier("molecular_hydrogen", 2.016e-3)
    boundary = PowerLawSolubilityFilmBoundary(
        PowerLawSolubility(carrier, lambda temperature: temperature * 1.0e-10, 0.5),
        lambda time: 1.0e6 + time * 1.0e5,
        1.0e5,
        lambda time, temperature: 1.0e-6 * (1.0 + time / 10.0),
        lambda time, temperature: 2.0e-6 * (temperature / 300.0),
        "authored-fugacity-to-solid-equilibrium-map",
        "authored-linear-film-coefficients",
    )
    state = boundary.at_temperature(2.0, 330.0)
    assert isinstance(state.left, SurfaceFilmCondition)
    assert isinstance(state.right, SurfaceFilmCondition)
    upstream, upstream_velocity = state.left.at(2.0, 330.0)
    downstream, downstream_velocity = state.right.at(2.0, 330.0)
    expected_upstream = (330.0e-10) * (1.2e6 ** 0.5)
    expected_downstream = (330.0e-10) * (1.0e5 ** 0.5)
    if (not np.isclose(upstream, expected_upstream, rtol=1e-14)
            or not np.isclose(downstream, expected_downstream, rtol=1e-14)
            or upstream_velocity != 1.2e-6 or downstream_velocity != 2.2e-6):
        raise AssertionError("Fugacity, temperature or film callback was not composed as declared")
    if (boundary.solubility.carrier is not carrier
            or state.left.evidence_id != "authored-linear-film-coefficients"
            or state.right.evidence_id != state.left.evidence_id):
        raise AssertionError("Surface-film carrier/evidence lineage was not retained")
    return ValidationOutcome(True, {
        "carrier": carrier.identity,
        "upstream_solid_basis_concentration_mol_m3": upstream,
        "downstream_solid_basis_concentration_mol_m3": downstream,
        "upstream_transfer_velocity_m_s": upstream_velocity,
        "downstream_transfer_velocity_m_s": downstream_velocity,
        "separate_boundary_and_film_evidence": True,
    }, (
        "Synthetic callback wiring only; fugacity mapping and transfer coefficients are not material-qualified.",
    ))

