# Cantera gas composition to hydrogen detector/alarm

`evaluate_cantera_species_alarm()` connects a current homogeneous Cantera
`ReactorTrace` to existing `FirstOrderConcentrationSensorConfig` and
`ConcentrationAlarmConfig` interfaces. Select a gas-phase species and provide
the physical location, clock, source evidence, source origin, operating mode
and episode explicitly; a closed reactor trace does not establish those site
identities.

The sensor basis must be `cantera-gas-phase-mole-fraction:<species>` with unit
`mole_fraction`. The handoff transfers each retained Cantera gas-phase sample
unchanged to the existing first-order lag. Existing sampled trip/reset logic
then creates `ConcentrationAlarmEvidence` for facility-protection replay. The
receipt retains the original reactor trace, sensor, alarm and trip evidence.
`require_current()` rechecks the native reactor owner, exact species series,
sensor/alarm clocks and identities, and each emitted trip.

This is a local, homogeneous gas-composition handoff. It does not model a leak,
room mixing, spatial dispersion, receptor transport, detector placement,
sensor chemistry, alarm setpoint qualification or human consequence. The
deferred Hangang case `cantera-reactor-hydrogen-sensor-alarm-handoff` uses an
installed Cantera thermodynamic species set; no mechanism is bundled.
