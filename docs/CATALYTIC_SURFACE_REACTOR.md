# Native finite catalytic gas/surface reactor

`h2physics.adapters.cantera_surface_reactor.CanteraCatalyticSurfaceReactor`
couples one finite ideal-gas volume to one native ideal surface. Cantera 3.2
owns surface kinetics, reactor integration and accepted states through its
`Interface`, `ReactorSurface` and `ReactorNet` APIs. The adapter audits gas
plus adsorbate element inventories, site coverage and energy accounting; it
does not provide its own reaction mechanism or kinetic correlation.

## Mechanism and state inputs

The caller supplies `NativeMechanismSource`, `MechanismBasis`, exact gas and
surface phase names, an initial `ReactiveState`, full initial surface
coverages, surface area, gas volume, clock and evidence identifiers, and
explicit Cantera step and tolerance controls. Only one ideal-gas phase adjacent
to one ideal surface is admitted. No mechanism file is bundled. Rights,
provenance of external YAML resources, and valid P/T/composition domains must
be established by the caller. See [Cantera's reactor API](https://cantera.org/3.2/python/zerodim.html)
and [thermodynamics API](https://cantera.org/3.2/python/thermo.html).

`run()` returns native accepted sample points and retains original gas,
surface, reactor and solver objects. Its base mode holds temperature at the
caller-declared value and reports the resulting thermostat demand; this is an
isothermal kinetic calculation, not a heat-transfer prediction. Gas and
surface species inventory projections are immutable molar series identified
by both species name and phase.

The retained combined energy uses native gas internal energy and native ideal-
surface partial molar enthalpies. Surface amounts in mol are converted to kmol
before multiplying Cantera's J/kmol values. The adapter preserves unsupported
native property errors rather than substituting a host correlation.

## Fixed-temperature wall mode

Passing `CatalyticThermalBoundary` enables the native reactor energy equation
and connects a `Wall` to an external `Reservoir` at prescribed wall
temperature. The boundary declares evidence, wall temperature, area, overall
heat-transfer coefficient and energy residual tolerances. Surface chemistry
then responds to the evolving gas temperature. The wall reservoir has no
finite capacity; this mode adds no catalyst-support storage, coolant, phase
change or spatial heat conduction.

Wall heat rate is sampled on requested output times, integrated by trapezoidal
quadrature, and compared with retained gas-plus-surface internal-energy change.
This sampled energy diagnostic is not the solver's hidden accepted-step heat
integral. Tight residual interpretation requires output-grid refinement.

## Finite-feed stirred reactor

`run_flowing_cstr()` adds caller-declared `CatalyticFlowBoundary` and requires
a `CatalyticThermalBoundary`. Cantera's native mass-flow controller sets the
feed rate and a pressure controller sets the discharge response to the stated
outlet pressure. The model is a well-mixed control volume, not plug flow. It
audits species, mass, element, site and energy ledgers over the requested
output grid; inlet/outlet and wall integrals use sampled quadrature. The caller
must supply feed composition/state, flow rate, outlet pressure, controller
coefficient, clock, mechanism and boundary evidence, and tolerances.

This level does not model porous diffusion, a packed bed, pressure loss,
industrial catalyst ageing, finite wall/coolant storage, external process
control or plant yield qualification. Mechanism and operating-domain
applicability remain separate research evidence.

## Deferred contract coverage

Four Hangang contracts are registered under `counterflow-flame`:
`cantera-finite-gas-surface-kinetics`,
`cantera-catalytic-fixed-wall-thermal-feedback`,
`cantera-catalytic-wall-heat-utility-handoff`, and
`cantera-finite-flow-catalytic-cstr`. They exercise software contracts with
the installed native mechanism and synthetic conditions; they are not
experimental validation and have not been executed in the current source
snapshot.
