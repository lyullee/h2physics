# Finite Cantera membrane thermostat duty handoff

`CanteraMembraneThermostatHeatAdapter` exposes the two cumulative thermostat-energy ledgers retained by `FiniteMembraneTrace` through the existing `HeatDuty` interface. Use `bind_cantera_membrane_thermostat_heat(trace, window)` with a `HeatWindow` whose endpoints are exact accepted samples on the membrane's declared physical-seconds clock.

For each interval, the adapter differences the native cumulative ledger and returns two `HeatDuty` objects, one per side. Each `HeatSnapshot.heat_into_process_j` therefore retains the selected thermostat's signed joules and matching side temperature pair without combining distinct thermal levels. Source ID, thermal-boundary ID, species order, accepted points, and native network are retained as provenance. The adapter checks that the native network clock and both terminal reactor states still match the final accepted trace state before and after snapshot construction. The existing `HeatDuty.require_current()` replays that check.

The sign convention is energy into the modeled gas sides. The quantity is an imposed isothermal boundary duty from the finite-device energy ledger. It does not mean heat can be recovered, sold, transferred between sides, or supplied by a utility, and it provides no heat-exchanger, refrigeration, storage, or utility-capacity calculation. The underlying membrane remains a frozen gas, rigid-volume, prescribed-temperature model; no temperature response is inferred.

The deferred Hangang contract is `cantera-membrane-thermostat-heat-duty-handoff`, registered under the existing `counterflow-flame` profile (Cantera 3.2). Its synthetic run is a software-interface contract, not membrane-device qualification or experimental validation.
