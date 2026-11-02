"""Synthetic fixed-flaw thermal initiation. No model runs at import.

The supplied thermal strength law is an authored verification limit, not a steel
alloy, hydrogen correction, creep law or material dataset. Execute only after the
separate reviewed HELPR profile is prepared for deferred validation.
"""

from h2physics.adapters.vessel_failure import (
    HelprAxialFlaw,
    HelprVesselFailure,
    VesselFailureContext,
    VesselFailureHistory,
    VesselLoading,
    VesselMaterialLaw,
    VesselMaterialPoint,
)
from h2physics.core import Origin, PropertyBasis


def authored_case(*, thermal_weakening=True):
    """Metadata and pure material callback only; does not import/run HELPR."""
    context = VesselFailureContext(
        "authored-cylinder",
        "authored-uniform-wall",
        "vessel-fixed-frame",
        "operation-clock",
        "authored-P-T-loading",
        PropertyBasis("Hydrogen", "authored-mechanical-context", "normal"),
        1.0,
        "no-measured-H2-material-qualification",
        "authored-uniform-wall-temperature",
        "authored-cylinder-section;end-caps-not-modeled",
        Origin.SYNTHETIC,
    )
    geometry = HelprAxialFlaw(
        0.22,
        0.01,
        0.001,
        0.02,
        1.0,
        "authored-cylinder-section",
        "fixed-internal-axial-flaw",
        "synthetic-geometry-not-equipment",
    )

    def material(loading, _context):
        strength = (
            300e6 - 700000.0 * (loading.wall_temperature_k - 300.0) if thermal_weakening else 200e6
        )
        # Huge authored toughness isolates the native reference-stress/yield limit.
        return VesselMaterialPoint(strength, 1e12, 1.0, "synthetic-strength-and-toughness-limit")

    law = VesselMaterialLaw(
        "authored-not-an-alloy",
        "synthetic-temperature-law",
        "no-calibration-or-measured-hydrogen-claim",
        (250.0, 700.0),
        (0.2e6, 100e6),
        (0.0, 1.0),
        material,
        Origin.SYNTHETIC,
    )
    history = VesselFailureHistory(
        context,
        (
            VesselLoading(0.0, 2.1e6, 0.1e6, 300.0, "supplied-single-fluid"),
            VesselLoading(100.0, 2.1e6, 0.1e6, 700.0, "supplied-single-fluid"),
        ),
        "authored-linear-mechanical-signals;not-a-fluid-EOS-path",
    )
    return geometry, law, history


def run_example():
    geometry, law, history = authored_case()
    owner = HelprVesselFailure(
        geometry,
        law,
        criterion="separate_yield_and_toughness",
        criterion_evidence_id="authored-separate-limits;not-code-conformity",
    )
    prediction = owner.predict(history, maximum_reconstruction_step_s=5.0)
    return prediction, prediction.evaluations[0].native.stress


if __name__ == "__main__":
    prediction, native_stress = run_example()
    print(prediction.termination, prediction.initiation.loading.time_s)
