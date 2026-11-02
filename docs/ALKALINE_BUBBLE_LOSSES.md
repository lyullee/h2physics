# Alkaline electrolyzer bubble-loss contribution

Status: **implemented_unverified**. This is an optional correction around the
shared `HydrogenStack`; it does not replace its thermochemistry, Faraday law, or
base polarization losses. The deferred Hangang contract is
`alkaline-bubble-electrode-and-electrolyte-losses`. No local physical calculation
or test has been run.

## Physics and intended level

The reduced model accounts for two electrical effects supplied by the caller:

1. Adhering gas bubbles reduce the active electrode area. If the measured or
   calibrated inactive fractions are `theta_a` and `theta_c`, a Tafel law adds
   `b_a log10(1/(1-theta_a)) + b_c log10(1/(1-theta_c))` volts per cell to a
   bubble-free kinetic baseline. The slopes `b_a` and `b_c` are user inputs in
   volts per decade and may depend on temperature.
2. Dispersed gas reduces electrolyte conductivity. For caller-supplied void
   fraction `phi`, bubble-free area resistance `R0` in ohm m² per cell, and
   effective-medium exponent `m`, the incremental resistance is
   `R0 * ((1-phi)**(-m) - 1)`. Its voltage contribution is geometric current
   density times this incremental area resistance. The default `m=1.5` is the
   Bruggeman form; a different exponent requires an explicitly identified
   correlation and calibration.

Surface coverage and electrolyte void fraction are independent inputs. The
model never infers one from the other or predicts either from current, flow,
pressure, temperature, or electrode geometry. Every callback receives a typed
condition carrying explicit absolute pressure, so a calibration may vary with
pressure without a hidden default. The baseline `HydrogenStack`
must exclude these bubble losses; otherwise the contribution would be counted
twice. Both corrections change voltage and electrical power only. They leave
the shared Faradaic hydrogen rate unchanged and do not apportion the additional
electrical demand to a thermal location.

This is a quasi-steady, lumped loss contribution. It does not resolve bubble
nucleation, growth, detachment, coalescence, population balance, dissolved-gas
transport, local current distribution, gas holdup profiles, pressure-mediated
transport or stack thermal feedback. It is suitable as a configurable composition point
for calibrated observations or a more detailed bubble model, not as a prediction
from nominal operating conditions alone.

## Python integration

```python
from h2physics.adapters import (
    AlkalineBubbleCondition, AlkalineBubbleModel, evaluate_alkaline_bubbles,
)

bubbles = AlkalineBubbleModel(
    anode_coverage=lambda c: measured_anode_coverage(c),
    cathode_coverage=lambda c: measured_cathode_coverage(c),
    electrolyte_void_fraction=lambda c: measured_bulk_void_fraction(c),
    bubble_free_area_resistance_ohm_m2=lambda c: electrolyte_area_resistance(c),
    anode_tafel_slope_v_decade=lambda c: anode_tafel_slope(c),
    cathode_tafel_slope_v_decade=lambda c: cathode_tafel_slope(c),
    coverage_evidence_id="versioned-electrode-coverage-source",
    void_fraction_evidence_id="versioned-electrolyte-void-source",
    electrolyte_resistance_evidence_id="bubble-free-resistance-source",
    tafel_slope_evidence_id="electrode-kinetic-source",
    correlation_evidence_id="effective-medium-correlation-selection",
)
result = evaluate_alkaline_bubbles(
    shared_hydrogen_stack, bubbles, current_density_a_m2=8_000.0,
    temperature_k=353.15, absolute_pressure_pa=6.0e5,
    electrolyte_concentration_mol_m3=6_000.0,
    electrolyte_composition_id="versioned-KOH-composition",
    anode_id="electrode-anode-record", cathode_id="electrode-cathode-record",
)
print(result.corrected_stack_voltage_v, result.corrected_electric_input_w)
```

Every callback receives one immutable `AlkalineBubbleCondition`. It always
contains geometric current density (A/m²), temperature (K), and mandatory
absolute pressure (Pa). Electrolyte concentration (mol/m³) and its composition
identity are an optional pair, and electrode identifiers are an optional
anode/cathode pair. Inputs are explicit at each call; no ambient-pressure or
electrolyte default is substituted. Callbacks should use only the fields
supported by their calibration and remain deterministic for a condition.
Evidence identifiers must point to the calibration records. Result access
rechecks the original stack result and bubble callback configuration.

## Sources, data, and limitations

- Bruggeman's effective-medium treatment provides a classical basis for the
  3/2 conductivity exponent: [Annalen der Physik, 1935](https://doi.org/10.1002/andp.19354160705).
- Measurements on gas-evolving electrodes studied the relation between bubble
  coverage and current density while emphasizing other controlling conditions:
  [Vogt and Balzer, Electrochimica Acta, 2005](https://doi.org/10.1016/j.electacta.2004.09.025).
- Alkaline-cell experiments separately measured electrode and bubble-related
  resistance contributions: [Chen et al., International Journal of Energy Research, 2017](https://doi.org/10.1002/er.3806).
- Alkaline solution-layer impedance measurements report bubble effects and
  discuss the Bruggeman relation: [Janssen and Barendrecht, Electrochimica Acta, 1983](https://doi.org/10.1016/0013-4686(83)85132-9).
- A later experimental reduced-order electrolyzer model also combines
  coverage and electrolyte void effects and compares its predictions against
  polarization data: [Pinto et al., Scientific Reports, 2025](https://doi.org/10.1038/s41598-025-25842-3).

These references justify considering the two mechanisms; they do not establish
universal coefficients or guarantee the chosen exponent for a particular porous
electrode or zero-gap architecture. The openly listed alkaline-bubble image/video
dataset currently has no reviewed numeric coverage/void channels with complete
operating-condition mapping. Therefore the new Hangang case uses authored inputs
only. No measurement is inferred from an image, chart, or literature figure.
The contract checks API decomposition and algebra, not scientific accuracy.

The RODARE record [10.14278/rodare.4547](https://doi.org/10.14278/rodare.4547)
provides a rights-qualified candidate with a summary index spanning several
pressure conditions. Its large HDF5 archive and underlying channels remain
unacquired and unqualified. Requiring pressure in `AlkalineBubbleCondition`
allows a future caller to bind supported operating-point data without treating
the summary index as coverage or polarization measurements.
