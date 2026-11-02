"""Deferred synthetic contract for the explicitly authorized AB2 shell bridge."""

from dataclasses import replace
from datetime import datetime, timedelta

from h2physics.cluster_validation import ValidationCase, ValidationOutcome


def cases():
    return (ValidationCase(
        identifier="ab2-shell-temperature-finite-hydride-boundary",
        profile="source-data-ingestion",
        entrypoint=__name__ + ":validate_shell_boundary",
        invariants=(
            "only a selected valid K shell sensor can supply a caller-authorized bath boundary",
            "piecewise-linear forcing is limited to the exact source clock support",
            "the issued boundary rechecks immutable source rows and retains mapping evidence",
            "unresolved flow, pressure and shell-to-bed physics are not inferred",
        ),
    ),)


def validate_shell_boundary(*, work_directory):
    from openpyxl import Workbook

    from h2physics.adapters.hydride_shell_temperature import bind_hydride_shell_temperature
    from h2physics.data.hydride_tank import HEADERS, iter_hydride_tank_blocks

    work_directory.mkdir(parents=True, exist_ok=True)
    path = work_directory / "ab2-shell-boundary-contract.xlsx"
    origin = datetime(2026, 1, 1, 0, 0, 0)
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Synthetic"
    sheet.append(HEADERS)
    for n, second, temp in ((1, 0, 300.), (2, 10, 320.), (3, 20, 340.)):
        sheet.append((n, origin + timedelta(seconds=second), second, 0., 0.,
                      temp - 1, temp, temp + 1, temp + 2, temp + 3, 0., 0.))
    workbook.save(path)

    blocks = iter_hydride_tank_blocks(path, "Synthetic", source_id="synthetic-ab2",
        experiment_id="synthetic-shell-run", clock_id="synthetic-shell-run/local",
        datetime_origin=origin)
    block = next(blocks)
    try:
        next(blocks)
    except StopIteration:
        pass
    binding = bind_hydride_shell_temperature(block, sensor_name="shell_2",
        clock_id="synthetic-shell-run/local",
        mapping_evidence_id="synthetic-contract-explicit-shell-equals-bath")
    binding.require_current()
    forged_mapping_rejected = False
    try:
        replace(binding, mapping_evidence_id="caller-substituted-mapping")
    except (TypeError, ValueError):
        forged_mapping_rejected = True
    direct_issue_rejected = False
    try:
        type(binding)(block, binding.boundary, binding.sensor_name,
            binding.mapping_evidence_id, binding.times_s, binding.temperatures_k)
    except (TypeError, ValueError):
        direct_issue_rejected = True
    t0, t1 = binding.times_s[0], binding.times_s[-1]
    start = binding.boundary.value(t0, None).bath_temperature_k
    middle = binding.boundary.value((t0 + t1) / 2., None).bath_temperature_k
    end = binding.boundary.value(t1, None).bath_temperature_k
    rejected = False
    try:
        binding.boundary.value(t1 + 1., None)
    except ValueError:
        rejected = True
    if (start, middle, end, rejected, forged_mapping_rejected,
            direct_issue_rejected) != (300., 320., 340., True, True, True):
        raise AssertionError("AB2 finite shell boundary contract failed")
    return ValidationOutcome(accepted=True, metrics={
        "source_sha256": dict(block.observations.context)["file_sha256"],
        "sensor": binding.sensor_name,
        "mapping_evidence_id": binding.mapping_evidence_id,
        "support_start_s": t0,
        "support_end_s": t1,
        "midpoint_bath_temperature_k": middle,
        "outside_support_rejected": rejected,
        "mapping_forgery_rejected": forged_mapping_rejected,
        "direct_boundary_issue_rejected": direct_issue_rejected,
        "physical_validation_claimed": False,
    })
