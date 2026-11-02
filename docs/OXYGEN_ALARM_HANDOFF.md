# Oxygen-room to detector/alarm handoff

`evaluate_oxygen_deficit_alarm()` connects the current finite-room dry-O2
output to the existing first-order concentration sensor and sampled alarm
interfaces. The transformation is explicit and narrow:

```text
oxygen room dry O2 samples
  -> max(reference dry O2 - room dry O2, 0)
  -> existing first-order sensor API
  -> existing sampled trip/reset alarm API
  -> existing ConcentrationAlarmEvidence for protection replay
```

The caller supplies the reference dry oxygen mole fraction and its evidence,
initial sensor indication, a typed detector response model, trip/reset limits,
confirmation counts, operating mode and episode. All clocks, locations, bases,
units and origins must align. Undefined dry fractions, mismatched provenance,
stale room results and changed sensor/alarm records are rejected.

The returned `OxygenDeficitAlarmHandoff` retains the original room result,
sensor trace, alarm trace and rising-trip evidence. Call `require_current()`
before using the evidence with facility protection; it revalidates source room,
sensor and alarm owners and checks that the stored deficit is still derived from
the original dry oxygen output. A saturated positive deficit transform discards
above-reference oxygen excess by design; this is appropriate only for the
caller-declared oxygen-deficiency alarm. It is not an injury metric, dose,
probability or population consequence.

Hangang case `oxygen-room-deficit-detector-alarm-handoff` exercises the typed
route with a frozen native Cantera gas, synthetic room condition and explicit
sensor/alarm assumptions. Its result is an integration contract, not an alarm
setpoint qualification or measured-room validation.
