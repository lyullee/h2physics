# Native terminal vent verification

Completed UTC: 2026-10-27T04:44:57.759212+00:00. Native LH2DT 0.1.2 MIT revision `b2f276333c1b1793c39f25763703d196d36742ec`; aggregate module SHA-256 `5406adc4092bfad5c9d4671874951999a9e5f83ee2ffafaf823bb1a6bf2e3e61`. Existing fluids 1.3.1 direct Churchill_1977 is an explicitly selected hydraulic closure, with its MIT dependency review already recorded in HYDRAULICS.md.

All cases use authored geometry/UA/operating conditions and actual native VentStack, HEMPipe/PipeResult and ThermoState objects. Native code is not modified, and evaluation leaves the caller's configured input stack/property objects unchanged. It copies the native stack configuration and binds a recording proxy over the explicitly selected original pipe or existing shared Lh2dtDarcyPipe. The actual native finite-UA implementation still executes. No alternative pipe, EOS, nozzle or thermal solver is installed or silently selected.

## Independent authored limits

A test-only ideal gas supplies cp=12000 J/(kg K), R=3500 J/(kg K), mu=1e-5 Pa s, h=cp*T and matching entropy/U. It is not a measured hydrogen fit or production provider. The native stack is 3 m long, .02 m diameter, roughness 2e-6 m, K=1.2, zero elevation, left 102325 Pa/270 K, remote right 101325 Pa/450 K and ambient reservoir 310 K. The declared constant Darcy f=.03 limit has an independent closed flow expression. Relative flow error 0. The independent caloric limit is Tout=Ta+(Tin-Ta)*exp(-UA/(abs(mdot)*cp)); numerical integration is owned by native LH2DT.

| NTU | Native outlet K | Analytic outlet K | Absolute T error K | Physical heat W | Inverse-UA residual W/K |
|---:|---:|---:|---:|---:|---|
| 0.0 | 270 | 270 | 0 | 0 | None |
| 0.2 | 277.250769877 | 277.250769877 | 5.4e-12 | 168.487537491 | -3.82982534574694e-12 |
| 1.0 | 295.284822346 | 295.284822353 | 7.4e-09 | 587.54829146 | -1.1693252588429459e-08 |

Native UA integration has internal/final enthalpy clamps. Enthalpy/heat bookkeeping alone can close despite an inaccurate ODE trajectory. The host therefore independently reconstructs UA by inverse quadrature using actual PH states along the native outlet enthalpy interval; it does not integrate a replacement forward solution. Configured-UA agreement requires max(1e-8 W/K, 1e-5*UA), including quadrature uncertainty. There is no automatic segment refinement or acceptance-budget relaxation.

| NTU=8 native segments | Raw/accepted outlet K | Analytic T error K | Gate | Diagnostic |
|---:|---:|---:|---|---|
| 8 | 309.984357357 | 0.00222 | rejected | Native finite-UA integration fails independent conductance audit: -3.56379474927 W/K |
| 16 | 309.986496227 | 8.53e-05 | rejected | Native finite-UA integration fails independent conductance audit: -0.147194037564 W/K |
| 32 | 309.986577188 | 4.31e-06 | rejected | Native finite-UA integration fails independent conductance audit: -0.00745751007852 W/K |
| 64 | 309.986581252 | 2.42e-07 | accepted | -0.00041979595584962226 |
| 128 | 309.986581481 | 1.44e-08 | accepted | -2.4902793768433185e-05 |

At NTU=20 / 8 native segments the raw outlet is exactly 310 K; the authored analytic outlet is 309.999999917554 K. It is retained and rejected: `Finite-UA outlet reaches/crosses an ambient endpoint; native clamping/resolution unresolved`. Exactly reaching the ambient endpoint is not silently accepted as evidence of finite-UA resolution. At an actual equal-temperature input, UA is unidentifiable from zero heat; this separate analytic limit remains available.

## Actual HEOS stack cases

Normal/para hydrogen use separate explicitly identified host HEOS providers, existing low-level native facades and matching state factories. These share the original EOS rather than claiming independent experimental property validation. Geometry is the same 3 m/.02 m/roughness2e-6 m/K1.2; heating/cooling cases have elevation +2 m, pressures 102325/101325 Pa and remote port T=450 K. Normal gas inlet/ambient are 270/310 K; para gas inlet/ambient are 340/295 K. Heat is finite-UA, not prescribed outlet T. The resolved transport outlet is a PH state at the actual downstream pressure; remote header temperature is not substituted for it.

| Fluid / case | UA W/K | Signed flow kg/s | Resolved outlet K | Physical heat W | Enthalpy residual W | Independent momentum residual Pa | Inverse-UA residual W/K | g*dz J/kg | Upstream hydraulic v2/2 J/kg | Upstream Mach | Downstream section Mach | Runtime s |
|---|---:|---:|---:|---:|---:|---:|---|---:|---:|---:|---:|---|
| Hydrogen | 0.0 | 0.00181611033575 | 270.000239975 | 0 | -7.85e-10 | 1.14e-13 | None | 19.6133 | 1981.56804472 | 0.0501983111804 | 0.0506937930752 | 0.003231099999993603 |
| Hydrogen | 5.0 | 0.00181611033575 | 277.050037965 | 181.797580566 | -6.7e-10 | 1.14e-13 | -3.4496849821152864e-12 | 19.6133 | 1981.56804472 | 0.0501983111804 | 0.0513789416154 | 0.055438500000036584 |
| Hydrogen | 20.0 | 0.00181611033575 | 291.541371286 | 556.843225539 | -4.9e-10 | 1.14e-13 | -3.538165316285813e-09 | 19.6133 | 1981.56804472 | 0.0501983111804 | 0.0527547433752 | 0.05570189999980357 |
| Hydrogen reverse gravity / 256 segments | 5.0 | -4.8808872897e-05 | 309.968637256 | 27.8404038444 | -8.98e-12 | 0 | -2.5903041489527823e-08 | -39.2266 | 1.45964415434 | 0.00136242039199 | 0.0014632636461 | None |
| ParaHydrogen | 0.0 | 0.00156800248975 | 340.000356292 | 0 | -2e-10 | -1.14e-13 | None | 19.6133 | 2341.94767056 | 0.0489630784498 | 0.0494463500501 | 0.003372900000158552 |
| ParaHydrogen | 5.0 | 0.00156800248975 | 331.211374899 | -202.226677314 | -2.32e-10 | -1.14e-13 | -5.575984118877386e-12 | 19.6133 | 2341.94767056 | 0.0489630784498 | 0.0488224040478 | 0.05576620000010735 |
| ParaHydrogen | 20.0 | 0.00156800248975 | 313.914199238 | -601.612902115 | -2.69e-10 | -1.14e-13 | -5.601517472086925e-09 | 19.6133 | 2341.94767056 | 0.0489630784498 | 0.0475774821569 | 0.05819289999999455 |
| ParaHydrogen reverse gravity / 256 segments | 5.0 | -2.68829480019e-05 | 310.000102319 | -11.8690630391 | -4.39e-12 | -4.44e-16 | -2.535362169098221e-07 | -39.2266 | 0.702041968788 | 0.000847742901632 | 0.000810817726982 | None |

Native reverse-flow heat_into_fluid_W is left-to-right oriented. The original field remains available as oriented_native_heat_w; common BoundaryPower explicitly multiplies it by the actual flow direction so heat is positive into the transported fluid. Common ConnectionTransfer checks enthalpy using absolute throughput. At equal port pressures, +4 m elevation drives reverse gravity flow: one-way mode returns zero flow, unavailable momentum and no transported state; explicitly enabled reverse mode retains negative flow and its real upstream port. Reverse cases use a 310 K ambient reservoir and 256 native segments; separately attempted 64-segment failures remain listed below under the unchanged UA audit budget. At -4 m elevation, forward flow is possible even with left pressure 1 Pa below the right pressure.

Declared dry-gas verification bounds are 50-500 kPa, 80-600 K, pressure difference <=5% of maximum port pressure and outlet/upstream density change <=50%. These are authored numerical-domain assumptions, not construction/experimental applicability qualification. An additional explicit Mach<=0.3 gate checks upstream hydraulic velocity and a same-bore downstream pipe-section estimate against sound speed from the actual selected HEOS provider. Small pressure/density changes do not imply this gate. The authored ideal-gas sound relation is confined to the verification fixture; production requires an injected provider capability and rejects absent/nonfinite sound. Tiny-loss actual-native cases at the same approximately 1% pressure drop are retained and rejected for supersonic hydraulic velocity. The downstream estimate is not a resolved atmospheric plane or an assurance about every unmodeled interior station. The upstream-density hydraulic and downstream-pressure thermal approximations remain separate. Existing common budgets are .01 Pa momentum and .05 W / 1e-6 relative enthalpy power; the independent final Darcy/friction loss is reconstructed even when the original native result reports a zero residual.

## Retained native transition and explicit correlation selection

A 100-point authored 1-100 Pa drive scan finds 20 original-native vent points failing the independent final momentum gate. The largest retained case has drive 51 Pa, native Re 2781.00758681, reported momentum 0 Pa, while the independently reconstructed residual is -24.7310296783 Pa. Original flow/friction/raw stack and hydraulic results remain in the failed exception.

The explicitly selected existing shared Darcy root with direct Churchill_1977 gives 0.000354438735989 kg/s and residual -5.68e-14 Pa at the same port states. This is a declared numerical/empirical closure selection, not a fallback or evidence of improved measured transition accuracy. Using the original discontinuous native friction law in the shared root gives residual -3.719219263299024: `Darcy constitutive residual -3.71922 Pa does not meet the declared pressure gate`.

## Other negative gates

- Hydrogen one-way gravity block: `0 kg/s; momentum unavailable; no outlet state`.
- Hydrogen tiny-loss / small-pressure-drop high velocity: `Upstream hydraulic Mach exceeds the declared low-Mach vent envelope; Downstream same-bore section Mach exceeds the declared low-Mach vent envelope; raw upstream Mach 1520.2797857, downstream same-bore Mach 1535.2856911`.
- Hydrogen wrong reference: `Property, spin-composition or energy-reference bases differ`.
- Hydrogen inconsistent enthalpy: `Vent port state disagrees with the selected property reference: enthalpy_j_kg`.
- Hydrogen excess pressure ratio: `Vent pressure difference exceeds the declared quasi-steady upstream-density envelope`.
- Hydrogen wet inlet: `This vent level requires dry single gas; phase boundaries are unsupported`.
- ParaHydrogen reverse gravity / 64 segments: `Native finite-UA integration fails independent conductance audit: -7.34309981585e-05 W/K`.
- ParaHydrogen one-way gravity block: `0 kg/s; momentum unavailable; no outlet state`.
- ParaHydrogen tiny-loss / small-pressure-drop high velocity: `Upstream hydraulic Mach exceeds the declared low-Mach vent envelope; Downstream same-bore section Mach exceeds the declared low-Mach vent envelope; raw upstream Mach 1530.43974104, downstream same-bore Mach 1545.54536932`.
- ParaHydrogen wrong reference: `Property, spin-composition or energy-reference bases differ`.
- ParaHydrogen inconsistent enthalpy: `Vent port state disagrees with the selected property reference: enthalpy_j_kg`.
- ParaHydrogen excess pressure ratio: `Vent pressure difference exceeds the declared quasi-steady upstream-density envelope`.
- ParaHydrogen wet inlet: `This vent level requires dry single gas; phase boundaries are unsupported`.

## Boundary meaning and unfinished work

This is a steady enthalpy-transport equipment boundary. Native stack hydraulics uses declared diameter/length/loss/elevation and upstream density/viscosity; its thermal ODE uses downstream pressure. Gravity direction is checked in the momentum equation, while port kinetic/potential energies remain excluded from the existing enthalpy-only ledger. Results explicitly report this energy_scope, signed g*dz and upstream constitutive hydraulic v2/2 diagnostics. These are not an outlet-plane velocity or a bound on its unresolved kinetic-energy change. Cases where elevation or velocity changes matter require a separately qualified mechanical-energy model; a small h/Q residual cannot certify them. No complete mechanical/total-energy source-plane closure, exit speed/momentum, critical discharge, stagnation-to-static conversion, atmospheric expansion, discharge coefficient, rainout or dispersion source is inferred. The native accident exporter is not used. A downstream low-pressure boundary does not make an unchoked Darcy result a qualified atmospheric nozzle history.

Receiving work: expose public hydraulic-provider/phase-viscosity injection and native iteration diagnostics; expose UA integration error/clamp counts/refinement instead of accepting hidden endpoint clamps; give raw heat a documented direction basis; define compressible/critical and kinetic/potential-energy ownership at a separately qualified outlet plane. Do not introduce another copy of the shared Darcy/nozzle solver. Installed roughness, local-loss/UA values, phase applicability and measured vent performance remain unqualified.

Primary implementation references: [pinned native VentStack](https://github.com/lyullee/lh2dt_models/blob/b2f276333c1b1793c39f25763703d196d36742ec/src/lh2dt/vent_stack.py), [native pipe](https://github.com/lyullee/lh2dt_models/blob/b2f276333c1b1793c39f25763703d196d36742ec/src/lh2dt/pipe.py), [native MIT license](https://github.com/lyullee/lh2dt_models/blob/b2f276333c1b1793c39f25763703d196d36742ec/LICENSE), [direct Churchill API and Darcy convention](https://fluids.readthedocs.io/fluids.friction.html#fluids.friction.Churchill_1977). No third-party code or experimental table was copied into this repository.

Completed local computation time: 1.5419937 s. No measured/vendor/dispersion qualification, external writes/messages, source mutation, dependency installation or publication.

## Begin/end executed-source fingerprints

| Host source/test/script | Begin SHA-256 | End SHA-256 |
|---|---|---|
| src/h2physics/adapters/lh2dt_vent.py | `0ea128bc58f5346467f619f59dcee62b76bf8bfe63beb12be6056558ec18d47b` | `0ea128bc58f5346467f619f59dcee62b76bf8bfe63beb12be6056558ec18d47b` |
| tests/test_lh2dt_vent.py | `910c4c97bcb0e30ae44f987b5c0bc0a22e56ee9f9827b027fcca17d6085ed620` | `910c4c97bcb0e30ae44f987b5c0bc0a22e56ee9f9827b027fcca17d6085ed620` |
| scripts/check_vent_integration.py | `972b49155dc0cd9ce1b6646aab25349bb4bdf31a47af1674b4504a70beb474f9` | `972b49155dc0cd9ce1b6646aab25349bb4bdf31a47af1674b4504a70beb474f9` |
| src/h2physics/adapters/lh2dt_hydraulics.py | `3ff182e0a5b5cc802624f389a13d45a874c9867ca3b361ff9d6f33d1a418c46c` | `3ff182e0a5b5cc802624f389a13d45a874c9867ca3b361ff9d6f33d1a418c46c` |
| src/h2physics/hydraulics.py | `856d8ee8c3ce5781b5804c3c2351fc5133886e4c23807e6fe3835ec50ba4e2b7` | `856d8ee8c3ce5781b5804c3c2351fc5133886e4c23807e6fe3835ec50ba4e2b7` |
| src/h2physics/adapters/lh2dt_properties.py | `818fb98b5d2084107c072f62c8e00f9b4d7df36f6044db2af8f3b82f0f6910c2` | `818fb98b5d2084107c072f62c8e00f9b4d7df36f6044db2af8f3b82f0f6910c2` |
| src/h2physics/adapters/lh2dt.py | `0711da98a12a034d3af69b7f377f9b07b3cac1ad82d1a4336bfd0850d16d23ed` | `0711da98a12a034d3af69b7f377f9b07b3cac1ad82d1a4336bfd0850d16d23ed` |
| src/h2physics/core.py | `4317b90d1f60880e6c9353c17f15bda642270ec557a04d65f389499a525fdc68` | `4317b90d1f60880e6c9353c17f15bda642270ec557a04d65f389499a525fdc68` |
| src/h2physics/equipment.py | `071e2a1ccc2904d7bc39db8645487d79427fe4050ee908ece4eb1c325cdf0a36` | `071e2a1ccc2904d7bc39db8645487d79427fe4050ee908ece4eb1c325cdf0a36` |

| External dependency source | Begin SHA-256 | End SHA-256 |
|---|---|---|
| lh2dt/vent_stack.py | `13d93bdf4d77d345aba6d4a45f699b96e4a4f475b760d7183481805994e3b97f` | `13d93bdf4d77d345aba6d4a45f699b96e4a4f475b760d7183481805994e3b97f` |
| lh2dt/pipe.py | `531bd56e1c380e7d0f0930a9c7ff4899c5ab076881d8a62853b8e79a9767c0f4` | `531bd56e1c380e7d0f0930a9c7ff4899c5ab076881d8a62853b8e79a9767c0f4` |
| lh2dt/properties.py | `835f694d46c55882dc9b51bdeda714995c05eda4bd90b3055662fb06ae6293a3` | `835f694d46c55882dc9b51bdeda714995c05eda4bd90b3055662fb06ae6293a3` |
| native MIT license | `cd63f148087d189cedb2a388fed0bc3f1f0676df5f7ad1adfc8a8789f9570a72` | `cd63f148087d189cedb2a388fed0bc3f1f0676df5f7ad1adfc8a8789f9570a72` |
| fluids.friction module | `6e0327c701e8dc63a0fb2cc87a03cd3c4e25e2a86387b7f31d17b340e2e75a7c` | `6e0327c701e8dc63a0fb2cc87a03cd3c4e25e2a86387b7f31d17b340e2e75a7c` |

Aggregate native module SHA-256 at begin and end: `5406adc4092bfad5c9d4671874951999a9e5f83ee2ffafaf823bb1a6bf2e3e61`.
