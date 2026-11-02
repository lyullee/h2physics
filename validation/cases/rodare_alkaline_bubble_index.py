"""Source-integrity contract for the RODARE alkaline-bubble condition index."""

from pathlib import Path
from shutil import copyfile

from h2physics.cluster_validation import ValidationCase, ValidationOutcome

SOURCE_PATH = (
    "/scratch/r1021a02/h2physics-source-attachments/"
    "rodare-alkaline-bubble-pressure/4547/Summary.csv"
)


def cases():
    return (ValidationCase(
        identifier="rodare-alkaline-bubble-condition-index-source-contract",
        profile="source-data-ingestion",
        entrypoint=__name__ + ":validate_condition_index",
        parameters={"source_path": SOURCE_PATH},
        invariants=(
            "source filename, publisher MD5, and SHA-256 match the RODARE v1 receipt",
            "all 60 condition rows preserve source identities and declared units/sign convention",
            "every electrode-pressure-current combination appears exactly once",
            "no voltage, bubble, gas-void, time-series, or fitted quantity is inferred",
            "changed source bytes invalidate the reader-issued index",
        ),
    ),)


def validate_condition_index(*, work_directory, source_path):
    from h2physics.data.rodare_alkaline_bubbles import load_rodare_alkaline_bubble_index

    index = load_rodare_alkaline_bubble_index(source_path).require_current()
    pressure_values = tuple(sorted({row.pressure_bar_abs for row in index.conditions}))
    current_values = tuple(sorted({row.current_density_mA_cm2 for row in index.conditions}))
    electrodes = tuple(sorted({row.electrode_id for row in index.conditions}))
    identifiers = tuple(row.measurement_id for row in index.conditions)
    if (len(index.conditions) != 60 or len(set(identifiers)) != 60
            or pressure_values != (1.0, 2.0, 4.0, 6.0)
            or current_values != (-100.0, -50.0, -25.0)
            or electrodes != ("LS_100", "LS_30", "LS_40", "LS_60", "Ref")):
        raise AssertionError("RODARE source condition grid differs from its pinned schema")

    altered = Path(work_directory) / "Summary-altered.csv"
    copyfile(source_path, altered)
    with altered.open("ab") as stream:
        stream.write(b"\n")
    try:
        load_rodare_alkaline_bubble_index(altered)
    except ValueError:
        stale_rejected = True
    else:
        raise AssertionError("Altered source bytes were accepted against a stale receipt")

    return ValidationOutcome(True, {
        "doi": "10.14278/rodare.4547",
        "version": "1",
        "source_sha256": index.source_sha256,
        "condition_count": len(index.conditions),
        "pressure_bar_absolute": pressure_values,
        "current_density_mA_cm2": current_values,
        "electrodes": electrodes,
        "stale_source_rejected": stale_rejected,
    }, (
        "The publisher file is an experiment-condition index only; it has no measured response channels.",
        "This source-ingestion contract is not model calibration or physical validation.",
    ))
