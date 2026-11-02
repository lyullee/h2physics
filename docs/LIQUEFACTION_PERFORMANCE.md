# Hydrogen liquefaction performance boundary

`h2physics.adapters.liquefaction_performance` reports a thermodynamic reference
and a process-boundary specific external-work figure for a loss-free hydrogen
feed-to-liquid comparison. Supply feed and product specific enthalpy and entropy
from one identified property reference, a common environment temperature, equal
feed/product mass over the same process window, an explicit `process_window_id`,
and evidence identifiers for the states and work measurement. The window identity
binds the state, mass and work values to one accounting interval; wall-clock
endpoints are not inferred or compared.

The ideal reversible work is the flow-exergy difference

`w_min = (h_product - h_feed) - T0 * (s_product - s_feed)`.

The API also reports external work per kilogram of liquid product and the ratio of
reversible minimum work to declared external work. These are boundary metrics;
the ratio is not a cycle efficiency if boundary work, heat exergy, vent/purge
streams or mass losses are omitted. The current API rejects unequal feed/product
masses and incompatible property-reference identifiers. It does not calculate
thermodynamic states or supply data; callers can use the existing property APIs,
including CoolProp where appropriate.

This is an implemented-unverified benchmark, not a liquefaction plant model. It
does not represent compressor stages, heat exchangers, expansion devices,
refrigerant mixtures, ortho-para conversion, controls, yield losses, utility
recovery or plant-specific performance. Those require an explicit process boundary
and qualified component/state data. The deferred acceptance definitions are
registered under the existing `reliquefier-product` Nurion profile; they have not
been executed.
