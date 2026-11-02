# Exact-time radial thermoelastic stress paths

`RadialThermoelasticStressHistory.stress_path_at(sample_index, radius_m)` exports
radial, hoop and axial normal stresses plus von Mises stress at selected radii for
one already-computed clock sample. The result is an immutable
`RadialThermoelasticStressPath` bound to the exact
`RadialThermoelasticStressSample` and source history.

The supplied radial coordinates must be strictly increasing and remain inside the
cylinder wall. Non-extrapolating PCHIP samples the solved stress profile; it does
not reconstruct a time between stored samples. `field_convention` is fixed to
`total_pressure_plus_thermal`, because the source solve already includes pressure
traction and thermal strain. `require_current()` checks the source linkage and
the result arrays before downstream use.

This API provides radial field data to a receiving fracture method that accepts
nonuniform total stresses. It does not produce a stress intensity factor, create a
crack weight function, select a crack plane, or predict crack initiation. The
existing HELPR pressure-only calculation remains separate until its native owner
supports and qualifies a nonuniform stress-field route.

The deferred contract is part of `elastic-cylinder-radial-thermoelasticity` in
`validation/cases/radial_thermoelastic_cylinder.py`. Its authored checks cover
wall-boundary tractions, exact clock linkage, immutable output and rejection of
out-of-wall requests. That contract has not been executed; no solver calculation
or Nurion job was run for this addition.
