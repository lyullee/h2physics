"""Application-supplied map/phase example; no mechanism or machine data bundled.

Call this function with qualified application inputs. The module performs no
calculation when imported and has not been executed for this coding increment.
"""

from h2physics.combustion import MapMatchedBraytonShaftFeedback, integrate_shaft_transient


def run_coupled_shaft(
    shaft_inputs,
    *,
    phase_factory,
    corrected_speeds,
    operating_inputs,
    speed_mapping_evidence_id,
    operating_law_evidence_id,
):
    """Run the existing rotor with native mapped powers at each trial speed.

    The application must set both prescribed power histories to zero, provide
    fresh native phases, and supply the operating law and both map-speed units.
    Load torque and rotor mechanical-loss parameters stay in shaft_inputs.
    """
    feedback = MapMatchedBraytonShaftFeedback(
        phase_factory=phase_factory,
        corrected_speeds=corrected_speeds,
        operating_inputs=operating_inputs,
        feedback_id="application-native-map-feedback",
        shaft_id=shaft_inputs.shaft_id,
        power_basis_id=shaft_inputs.power_basis_id,
        speed_mapping_evidence_id=speed_mapping_evidence_id,
        operating_law_evidence_id=operating_law_evidence_id,
    )
    return integrate_shaft_transient(shaft_inputs, gas_path_feedback=feedback)
