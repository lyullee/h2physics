# HyRAM radiation to lumped thermal target

`incident_heat_history_from_hyram_radiation()` composes the existing accepted
HyRAM radiation observer with the existing `IncidentHeatHistory` boundary used
by `run_thermal_target()`. It retains the selected observer irradiance as a
left-held incident flux over a caller-bounded interval inside the flame's
evidenced steady window. The source guard reissues the original HyRAM exposure
projection before the thermal target accepts or revalidates its input.

The caller must identify the target receptor and provide evidence that the
selected observer represents the target surface and that any required
irradiance projection is already applied. HyRAM's scalar irradiance is not a
surface-normal flux by implication. The target's absorptivity, emissivity,
heat capacity, area and external heat-transfer coefficients remain separate
caller-supplied evidence. The adapter adds no view factor, projection law,
transient fire model, injury law, or equipment failure criterion.

The binding seals the surface-mapping, irradiance-projection and history-mapping
evidence identifiers at issue time and rechecks them whenever the thermal
target validates its input. The target history retains that exact source guard,
so changing any of the three identifiers invalidates the coupling.

Deferred Hangang contract: `hyram-radiation-lumped-thermal-target-handoff`
under `jet-fire-conservation`. It composes synthetic model inputs and does not
qualify a real target, fire exposure, or facility.
