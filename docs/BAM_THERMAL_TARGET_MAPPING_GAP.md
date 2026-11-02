# BAM measurements and thermal-target mapping gap

The BAM archive contains time-labelled plate thermocouple temperatures in
degrees Celsius, hydrogen/total mass flow in kilograms per hour, pressure
channels in bar, and several gas/pipe/flame temperature and sensor-voltage
channels. The export reports a sample-rate value of 100. One plate-average
column is labelled with an unresolved unit, so it is not admitted as a
temperature quantity. See the [source intake record](BAM_HYDROGEN_JET_FIRE_DATA.md).

These data do not provide incident heat flux. A plate temperature is a response
to its thermal boundary and cannot be substituted for incident flux or uniquely
inverted into it without a qualified heat-transfer model and independently
known target properties and surroundings. The existing
[thermal-target adapter](THERMAL_TARGET.md) requires incident radiant flux in
watts per square metre and independently evidenced target area, heat capacity,
absorptivity, emissivity, convection coefficient, ambient/radiant-surroundings
temperatures, and an admitted temperature range. None of those can be derived
from the BAM channel labels alone.

## Missing evidence for a source-to-target adapter

- A calibrated incident-heat-flux time series, or an independently qualified
  provider that supplies it on the exact experiment clock and target frame.
- Plate dimensions, exposed area, thickness, construction/material, mass, and
  temperature-dependent or justified effective heat capacity.
- Thermocouple coordinates, attachment/contact details, calibration, accuracy,
  response time, and mapping from each numbered plate channel to the target.
- Emissivity/absorptivity and evidence for the convection and radiative
  surroundings used by the forward balance.
- Experiment-level ignition time, clock origin, trigger relationship, and
  alignment evidence for any separately recorded source history.
- A documented pressure basis and calibration for the pressure channels, plus
  injector/nozzle geometry and boundary conditions before using flow data to
  drive a separate fire/radiation calculation.

No adapter is defined between these temperature/flow records and
IncidentHeatHistory or LumpedThermalTarget. In particular, the channel
T_Platte_Avg with an unresolved unit and the individual plate temperatures
remain source measurements; they are not converted to flux, heat capacity, or
material properties. A future comparison needs a separately admitted
measurement operator and clock/geometry contract. Until then, the data are
ingestion evidence only and do not validate a fire, radiation, or target model.

The radial cylindrical-wall solver also has no direct mapping here: the BAM
plate channels describe a flat target instrumented at numbered locations, while
the solver requires cylinder radii, length, radial material properties, an
initial wall state, and independently specified inner and outer thermal
boundary histories. The archive labels do not establish those quantities or
equivalence between the plate setup and a cylindrical vessel wall.

No adapter converts these measurements into `IncidentHeatHistory` or drives `LumpedThermalTarget` from BAM temperature. A separate observation comparator, `compare_bam_plate_temperature_to_target()`, compares one caller-qualified plate-temperature channel against an already completed `ThermalTargetTrace`; it does not feed that measurement into the target solve or infer incident flux.
