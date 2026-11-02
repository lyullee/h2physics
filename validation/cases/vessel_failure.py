"""Deferred metadata and remote handlers; no native execution at import/cases()."""

import hashlib
import json
from dataclasses import replace
from pathlib import Path

from h2physics.cluster_validation import ValidationCase, ValidationOutcome


def cases():
    return (
        ValidationCase(
            identifier="vessel-native-capacity-units",
            profile="fracture-fatigue",
            entrypoint="validation.cases.vessel_failure:validate_capacity",
            invariants=("actual native geometry/stress/FAD ratio objects", "independent thin-shell pressure limit", "absolute versus differential pressure", "native pressure linearity and SI"),
        ),
        ValidationCase(
            identifier="vessel-thermal-initiation-refinement",
            profile="fracture-fatigue",
            entrypoint="validation.cases.vessel_failure:validate_thermal",
            invariants=("independent authored thermal weakening root", "native 2016 FAD curve call", "time reconstruction refinement", "actual native roots and call ledger"),
        ),
        ValidationCase(
            identifier="vessel-native-finite-storage-binding",
            profile="fracture-fatigue",
            entrypoint="validation.cases.vessel_failure:validate_storage",
            invariants=("actual finite LH2DT fluid/wall history", "native mass and energy ledgers", "original state/time/pressure identity", "retained summary/context rejection"),
        ),
        ValidationCase(
            identifier="vessel-domains-failure-retention",
            profile="fracture-fatigue",
            entrypoint="validation.cases.vessel_failure:validate_negatives",
            invariants=("native material/admission failure retains actual pending objects", "unsupported geometry/external-pressure/clock failure", "no missing-root repair"),
        ),
    )

def _owner(thermal=False, *, criterion="separate_yield_and_toughness"):
    from examples.vessel_failure import authored_case
    from h2physics.adapters.vessel_failure import HelprVesselFailure

    geometry, law, history = authored_case(thermal_weakening=thermal)
    return HelprVesselFailure(
        geometry,
        law,
        criterion=criterion,
        criterion_evidence_id="authored-verification-criterion;not-standard-conformity",
    ), history


def _save(work_directory, name, metrics, owner):
    directory = Path(work_directory)
    directory.mkdir(parents=True, exist_ok=True)
    (directory / (name + ".json")).write_text(
        json.dumps(
            {"metrics": metrics, "native_source_sha256": dict(owner.source_sha256)},
            indent=2,
            allow_nan=False,
        )
        + "\n",
        encoding="utf-8",
        newline="\n",
    )


def validate_capacity(*, work_directory, **parameters):
    root = Path(__file__).resolve().parents[2]
    files = (
        "src/h2physics/adapters/vessel_failure.py",
        "examples/vessel_failure.py",
        "validation/cases/vessel_failure.py",
        "src/h2physics/adapters/fracture_fatigue.py",
    )
    before = {n: hashlib.sha256((root / n).read_bytes()).hexdigest() for n in files}
    owner, history = _owner()
    loading = history.samples[0]
    capacity = owner.pressure_capacity(
        loading,
        history.context,
        bracket_pressure_pa_absolute=(1e6, 40e6),
        continuation_evidence_id="authored-fixed-T-pressure-path",
    )
    capacity.require_current()
    capacity_rejections = 0
    try:
        from dataclasses import fields as dataclass_fields
        forged_values = {
            item.name: getattr(capacity, item.name)
            for item in dataclass_fields(capacity)
            if item.init and item.name != "_issuer_token"
        }
        type(capacity)(**forged_values)
    except ValueError:
        capacity_rejections += 1
    try:
        replace(capacity)
    except ValueError:
        capacity_rejections += 1
    original_digest = capacity.input_sha256
    object.__setattr__(capacity, "input_sha256", "forged-capacity-input")
    try:
        capacity.require_current()
    except ValueError:
        capacity_rejections += 1
    object.__setattr__(capacity, "input_sha256", original_digest)
    capacity.require_current()
    assert capacity_rejections == 2
    # Independent force balance limit: sigma_theta=DeltaP*Doutside/(2t).
    expected = loading.external_pressure_pa_absolute + 200e6 * 2 * 0.01 / 0.22
    error = abs(capacity.capacity.loading.internal_pressure_pa_absolute - expected)
    assert capacity.native_root_result.converged and error < 0.02
    first = owner.evaluate(loading, history.context)
    doubled = owner.evaluate(
        replace(
            loading,
            internal_pressure_pa_absolute=loading.external_pressure_pa_absolute
            + 2 * loading.pressure_difference_pa,
        ),
        history.context,
    )
    assert abs(doubled.k_max_pa_sqrt_m / first.k_max_pa_sqrt_m - 2) < 1e-12
    assert abs(doubled.reference_stress_pa / first.reference_stress_pa - 2) < 1e-12
    assert first.native.stress.__class__.__module__ == "helpr.physics.stress_state"
    assert first.k_max_pa_sqrt_m == float(first.raw_stress_intensity[0]) * 1e6
    assert first.load_ratio == float(first.raw_ratios[1])
    after = {n: hashlib.sha256((root / n).read_bytes()).hexdigest() for n in files}
    assert before == after
    metrics = {
        "absolute_pressure_error_pa": error,
        "capacity_pressure_pa_absolute": expected,
        "begin_sha256": before,
        "end_sha256": after,
        "actual_native_evaluations": len(capacity.evaluations),
        "forged_or_mutated_capacity_reports_rejected": capacity_rejections,
    }
    _save(work_directory, "vessel_capacity", metrics, owner)
    return ValidationOutcome(
        accepted=True,
        metrics=metrics,
        limitations=(
            "Authored strength/toughness isolates the yield limit; no measured capacity validation.",
        ),
    )


def validate_thermal(*, work_directory, **parameters):
    owner, history = _owner(True)
    coarse = owner.predict(history, maximum_reconstruction_step_s=10.0)
    fine = owner.predict(history, maximum_reconstruction_step_s=1.0, root_time_tolerance_s=1e-9)
    fine.require_current()
    rejected_reports = 0
    try:
        from dataclasses import fields as dataclass_fields
        forged_values = {
            item.name: getattr(fine, item.name)
            for item in dataclass_fields(fine)
            if item.init and item.name != "_issuer_token"
        }
        type(fine)(**forged_values)
    except ValueError:
        rejected_reports += 1
    try:
        from dataclasses import replace as dataclass_replace
        dataclass_replace(fine)
    except ValueError:
        rejected_reports += 1
    object.__setattr__(fine, "termination", "forged-native-termination")
    try:
        fine.require_current()
    except ValueError:
        rejected_reports += 1
    object.__setattr__(fine, "termination", "first_resolved_initiation")
    fine.require_current()
    assert rejected_reports == 3
    # Independent supplied linear strength crossing against pressure force balance.
    sigma = 2e6 * 0.22 / (2 * 0.01)
    expected_t = ((300e6 - sigma) / 700000.0) / 4.0
    error = abs(fine.initiation.loading.time_s - expected_t)
    assert fine.native_root_result.converged and error < 1e-6
    assert abs(coarse.initiation.loading.time_s - fine.initiation.loading.time_s) < 1e-5
    fad_owner, fad_history = _owner(True, criterion="native_2016_fad")
    fad = fad_owner.predict(fad_history, maximum_reconstruction_step_s=1.0)
    assert fad.initiation is not None and fad.native_root_result.converged
    assert fad.initiation.loading.time_s <= fine.initiation.loading.time_s + 1e-5
    assert any(p.raw_fad_limit is not None for p in fad.evaluations)
    assert float(fad_owner.fad_function(0.0)) == 1.0
    metrics = {
        "thermal_time_error_s": error,
        "forged_or_mutated_reports_rejected": rejected_reports,
        "yield_boundary_time_s": fine.initiation.loading.time_s,
        "native_fad_boundary_time_s": fad.initiation.loading.time_s,
        "time_refinement_difference_s": abs(
            coarse.initiation.loading.time_s - fine.initiation.loading.time_s
        ),
    }
    _save(work_directory, "vessel_thermal", metrics, fad_owner)
    return ValidationOutcome(
        accepted=True,
        metrics=metrics,
        limitations=(
            "Linear wall-temperature reconstruction and synthetic strength law, no hot-vessel experiment.",
            "First resolved crossing; no guarantee for arbitrary hidden nonmonotonic excursions.",
        ),
    )


def validate_storage(*, work_directory, **parameters):
    from h2physics.adapters.cryo_compressed import CryoCompressedNative
    from h2physics.adapters.vessel_failure import (
        HelprVesselFailure,
        VesselFailureContext,
        VesselFailureError,
        VesselMaterialPoint,
        history_from_cryo_compressed,
    )
    from h2physics.core import Origin
    from scripts.check_cryo_compressed import build, run

    native = CryoCompressedNative.from_installed(
        source_id="LH2DT:b2f276333c1b1793c39f25763703d196d36742ec"
    )
    storage = build(native)
    coarse, fine = [run(storage, duration=2.0, step=step, power=100.0) for step in (0.5, 0.25)]
    template, _ = _owner()
    material = replace(
        template.material_law,
        wall_temperature_k=(20.0, 350.0),
        response=lambda load, context: VesselMaterialPoint(
            500e6, 1e12, 1.0, "authored-cryogenic-mechanical-limit"
        ),
    )
    owner = HelprVesselFailure(
        template.geometry,
        material,
        criterion="separate_yield_and_toughness",
        criterion_evidence_id="authored-mechanics-coupling-only",
    )
    context = VesselFailureContext(
        "actual-native-storage",
        "actual-lumped-wall",
        "storage-frame",
        fine.native_trace.clock_id,
        fine.boundary.source_id,
        storage.properties.basis,
        1.0,
        "synthetic-strength;not-a-qualified-cryogenic-alloy",
        "actual-native-lumped-wall",
        "authored-cylinder-section-binding;not-derived-from-tank-volume",
        Origin.PREDICTED,
    )
    history = history_from_cryo_compressed(
        fine,
        context=context,
        external_pressure_pa_absolute=lambda time: 1e5,
        reconstruction_evidence_id="linear-mechanical-samples-only",
    )
    result = owner.predict(history, maximum_reconstruction_step_s=0.25)
    assert result.history.native_trace is fine and result.initiation is None
    assert history.samples[-1].native_state is fine.points[-1].native_state
    assert all(not p.balance.violations(fine.inventory_tolerances) for p in fine.points)
    error = abs(coarse.points[-1].fluid.pressure_pa - fine.points[-1].fluid.pressure_pa)
    assert error / fine.points[-1].fluid.pressure_pa < 1e-4
    retained = 0
    altered = replace(
        fine.points[-1],
        fluid=replace(fine.points[-1].fluid, pressure_pa=fine.points[-1].fluid.pressure_pa * 1.01),
    )
    for source, ctx in (
        (replace(fine, points=(*fine.points[:-1], altered)), context),
        (fine, replace(context, clock_id="wrong-clock")),
    ):
        try:
            history_from_cryo_compressed(
                source,
                context=ctx,
                external_pressure_pa_absolute=lambda time: 1e5,
                reconstruction_evidence_id="negative-binding-probe",
            )
        except VesselFailureError as failure:
            assert failure.__cause__ is not None and failure.source is source
            retained += 1
    changed_history = replace(
        history,
        samples=(
            *history.samples[:-1],
            replace(
                history.samples[-1],
                internal_pressure_pa_absolute=history.samples[-1].internal_pressure_pa_absolute
                * 1.01,
            ),
        ),
    )
    try:
        owner.predict(changed_history, maximum_reconstruction_step_s=0.25)
    except VesselFailureError as failure:
        assert failure.source is changed_history and failure.__cause__ is not None
        retained += 1
    assert retained == 3
    metrics = {
        "native_storage_pressure_refinement_pa": error,
        "bound_samples": len(history.samples),
        "retained_binding_failures": retained,
        "maximum_native_mass_residual_kg": max(
            abs(p.balance.mass_residual_kg) for p in fine.points
        ),
        "maximum_native_energy_residual_j": max(
            abs(p.balance.energy_residual_j) for p in fine.points
        ),
    }
    _save(work_directory, "vessel_native_storage", metrics, owner)
    return ValidationOutcome(
        accepted=True,
        metrics=metrics,
        limitations=(
            "Actual finite fluid/wall integration with synthetic structural properties and geometry binding.",
            "Lumped wall cannot resolve a local fire hot spot or through-wall thermal stress.",
        ),
    )


def validate_negatives(*, work_directory, **parameters):
    from h2physics.adapters.vessel_failure import HelprVesselFailure, VesselFailureError

    owner, history = _owner()
    retained = 0
    try:
        owner.pressure_capacity(
            history.samples[0],
            history.context,
            bracket_pressure_pa_absolute=(1e6, 2e6),
            continuation_evidence_id="no-crossing-negative",
        )
    except VesselFailureError as failure:
        assert (
            failure.__cause__ is not None
            and len(failure.evaluations) == 2
            and failure.native_objects
        )
        retained += 1
    for constructor in (
        lambda: replace(owner.geometry, flaw_depth_m=0.009),
        lambda: replace(history.samples[0], external_pressure_pa_absolute=3e6),
        lambda: replace(history, samples=(history.samples[1], history.samples[0])),
    ):
        try:
            constructor()
        except ValueError:
            retained += 1

    def wrong_native_binding(pipe, load, material, defect, *, stress_intensity_method):
        altered_pipe = type(pipe)(pipe.outer_diameter * 1.01, pipe.wall_thickness)
        return owner.stress_class(altered_pipe, load, material, defect, stress_intensity_method)

    rejected = HelprVesselFailure(
        owner.geometry,
        owner.material_law,
        criterion=owner.criterion,
        criterion_evidence_id="actual-native-pointer-binding-negative",
        native_stress_factory=wrong_native_binding,
    )
    try:
        rejected.evaluate(history.samples[0], history.context)
    except VesselFailureError as failure:
        assert (
            type(failure.pending["stress"]) is owner.stress_class and failure.__cause__ is not None
        )
        retained += 1
    assert retained == 5
    metrics = {"explicit_rejected_cases": retained}
    _save(work_directory, "vessel_negatives", metrics, owner)
    return ValidationOutcome(
        accepted=True,
        metrics=metrics,
        limitations=(
            "Additional source/parameter mutation and actual native exception paths remain qualification work.",
        ),
    )
