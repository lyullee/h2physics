"""Unexecuted finite-speed pump construction sketch."""

from h2physics.adapters.lh2dt_pump_operation import (
    NormalizedPumpMap,
    PumpMapEvidence,
    PumpSpeedActuator,
    PumpSpeedCommand,
)

evidence = PumpMapEvidence(
    "replace-with-source-record", "https://example.invalid/pump-map",
    "replace-with-reviewed-license", "0"*64, "ParaHydrogen",
    qualified_for_prediction=False,
)
pump_map = NormalizedPumpMap(
    "caller-map", 3000.0, 0.008, 600000.0, 0.5,
    (0.0, 0.5, 1.0), (1.0, 0.75, 0.0),
    (0.7, 0.7, 0.7), (1.0, 1.0, 1.0), evidence,
)
actuator = PumpSpeedActuator("pump-drive", "plant-clock", 0.5, 0.5, 1.0,
                            "replace-with-actuator-evidence")
commands = (
    PumpSpeedCommand("ramp", 0.0, 1.0, 1.0),
    PumpSpeedCommand("hold", 1.0, 2.0, 1.0, "hold"),
)

# The native pump and native states are supplied by the installed reviewed owner.
# model = FiniteSpeedPump(native_pump, actuator, pump_map)
# trace = model.run(left_native_state, right_native_state, commands,
#                   (0.0, 0.5, 1.0, 2.0), clock_id="plant-clock")
