# Cantera catalytic wall heat to the thermal utility ledger

`CanteraCatalyticWallHeatAdapter` implements the existing `HeatDutyAdapter`
contract for a current `CatalyticSurfaceTrace` that retains its actual native
fixed-temperature wall boundary. `HeatDuty.bind` invokes this adapter and
replays it during `require_current()`, so changes to the native reactor, wall,
trace or adapter snapshot cannot leave a valid-looking stale utility record.

The caller chooses a `HeatWindow` whose start and end exactly match accepted
native samples on the same clock. The adapter differences the native cumulative
wall heat into the catalytic reactor to form signed per-interval joules. It
retains the original trace, reactor owner, native wall/reservoir/network,
boundary evidence, temperatures and mechanism identity. Heat into the reactor
is positive according to the native left/right convention. The fixed wall is
reported as an imposed external heat device; the adapter does not establish a
finite wall inventory, utility availability, cost, recoverability or whole-
plant energy supply.

Isothermal traces with thermostat demand do not carry the native wall ledger
and are rejected. The deferred Hangang case
`cantera-catalytic-wall-heat-utility-handoff` exercises this route with the
installed Cantera `ptcombust.yaml` mechanism; no mechanism file is bundled.
