# Native steady and finite-volume reliquefaction verification

Synthetic numerical/interface/conservation evidence only. No measured boiloff-recovery efficiency, refrigeration cycle or manufacturer map is qualified.

LH2DT 0.1.2, revision b2f276333c1b1793c39f25763703d196d36742ec; CoolProp 8.0.0.

| Native source | SHA-256 |
|---|---|
| Native top-level ordered filename+bytes | 5406adc4092bfad5c9d4671874951999a9e5f83ee2ffafaf823bb1a6bf2e3e61 |
| lh2dt/reliquefier.py | 5cbe8867bfa3a32a7d49c45f4946437419bdba183e4de731b93db0f2efee4cb9 |
| lh2dt/dynamic_reliquefier.py | d280c6194ed53d9c7cb03ce0dd715d40dc0056df0009b6c9b3c685b6d18627d4 |
| lh2dt/dynamic_vaporizer.py | 153a07dd99225043d23fdf7e122d7abeeb65546a0899b9388dcecca9c5e4068a |
| lh2dt/dynamic_network.py | 9a16013db2668e28b1d03b64cad4e407c87e6e9c61c87d25e43d53dfd8a45ff1 |
| Installed MIT license | cd63f148087d189cedb2a388fed0bc3f1f0676df5f7ad1adfc8a8789f9570a72 |

Host source/test/script fingerprints, guarded at the beginning and end:

| File | SHA-256 |
|---|---|
| src/h2physics/adapters/lh2dt_reliquefier.py | c3dea8305b982f231f931bfe9301c08c7afa9fff60f9eff4bca82c4975fd84c7 |
| tests/test_lh2dt_reliquefier.py | 48740b58744ad472096525b57602db23c0a3e7b5774e3fa2cb129e73de00dba7 |
| scripts/check_reliquefier_integration.py | b55484ff9daf5c492a6a77eaace0cbfe2f423efba6d14caa65e950b5c87063ba |
| src/h2physics/adapters/lh2dt_dynamics.py | 24d47555c295cfd7850459933a2077b1c37bf5ffcffa292045b962cd93daec69 |
| src/h2physics/adapters/lh2dt_equipment.py | 87c29e0b47f35da3e38baf4ca2ce1832f58a91104701a95c144e5e30f7080b33 |
| src/h2physics/adapters/lh2dt_properties.py | 818fb98b5d2084107c072f62c8e00f9b4d7df36f6044db2af8f3b82f0f6910c2 |
| src/h2physics/dynamics.py | d3964d476994dc12cee0113ee137cc1313c8e0d4f97dfd3167b487c8367e9abd |
| src/h2physics/thermo/coolprop.py | d6b2e7f663ab8815e3935294855ebb2d763ad27685e3056af46b0776694e4b8b |

## Steady saturated latent-heat and capacity limits

The actual native Reliquefier receives an explicit saturation-pressure/quality target. For a saturated-vapor inlet at fixed pressure, the independent latent-heat oracle is newly condensed fraction = removed_heat/(mdot*(h_g-h_l)). Saturated enthalpies come from the selected HEOS provider, so this is a conservation oracle rather than independent property validation. No outlet quality is overwritten.

| Fluid | Pressure Pa | Capacity / latent duty | Outlet liquid fraction | Oracle absolute error | Heat into fluid W | Energy residual W |
|---|---:|---:|---:|---:|---:|---:|
| Hydrogen | 100000 | 0.1 | 0.1 | 2.7755576e-17 | -44.89145459 | 2.8421709e-14 |
| Hydrogen | 100000 | 0.5 | 0.5 | 1.110223e-16 | -224.4572729 | 2.8421709e-14 |
| Hydrogen | 100000 | 1 | 1 | 0 | -448.9145459 | 0 |
| Hydrogen | 100000 | 2 | 1 | 0 | -448.9145459 | 0 |
| Hydrogen | 300000 | 0.1 | 0.1 | 2.7755576e-17 | -41.32713965 | 3.5527137e-14 |
| Hydrogen | 300000 | 0.5 | 0.5 | 1.110223e-16 | -206.6356982 | 5.6843419e-14 |
| Hydrogen | 300000 | 1 | 1 | 0 | -413.2713965 | 5.6843419e-14 |
| Hydrogen | 300000 | 2 | 1 | 0 | -413.2713965 | 5.6843419e-14 |
| ParaHydrogen | 100000 | 0.1 | 0.1 | 8.3266727e-17 | -44.62646515 | -3.5527137e-14 |
| ParaHydrogen | 100000 | 0.5 | 0.5 | 1.110223e-16 | -223.1323258 | -2.8421709e-14 |
| ParaHydrogen | 100000 | 1 | 1 | 0 | -446.2646515 | 0 |
| ParaHydrogen | 100000 | 2 | 1 | 0 | -446.2646515 | 0 |
| ParaHydrogen | 300000 | 0.1 | 0.1 | 8.3266727e-17 | -41.05660672 | 0 |
| ParaHydrogen | 300000 | 0.5 | 0.5 | 0 | -205.2830336 | 0 |
| ParaHydrogen | 300000 | 1 | 1 | 0 | -410.5660672 | 0 |
| ParaHydrogen | 300000 | 2 | 1 | 0 | -410.5660672 | 0 |
| OrthoHydrogen | 100000 | 0.1 | 0.1 | 2.4980018e-16 | -45.06754032 | -1.4210855e-14 |
| OrthoHydrogen | 100000 | 0.5 | 0.5 | 0 | -225.3377016 | 2.8421709e-14 |
| OrthoHydrogen | 100000 | 1 | 1 | 0 | -450.6754032 | 0 |
| OrthoHydrogen | 100000 | 2 | 1 | 0 | -450.6754032 | 0 |
| OrthoHydrogen | 300000 | 0.1 | 0.1 | 2.7755576e-17 | -41.47436866 | -4.2632564e-14 |
| OrthoHydrogen | 300000 | 0.5 | 0.5 | 0 | -207.3718433 | 0 |
| OrthoHydrogen | 300000 | 1 | 1 | 0 | -414.7436866 | 0 |
| OrthoHydrogen | 300000 | 2 | 1 | 0 | -414.7436866 | 0 |

A 1 W capacity at 0.001 kg/s, 80 K / 200 kPa leaves gas at 79.9153940465 K with zero liquid production. Capacity limitation does not force saturation. A separate inlet with 70% existing liquid gives 0.001 kg/s total liquid but only 0.0003 kg/s newly produced liquid.

The explicitly selected inherited endpoint-quality roundoff policy is 1e-8; this final pair's facade recorded 1 adjustments, maximum 3.28343033018e-17. These diagnostics do not authorize a physical phase or spin conversion.

## Native finite fluid/wall cooling and condensation

A 0.001 m3 rigid mixed volume starts at saturated vapor at 200 kPa. Wall C=2 J/K, initial wall/cold reservoir 18 K, fluid-wall UA=20 W/K, reservoir-wall UA=20 W/K and native maximum_cooling=5 W. The 5 W cap limits fluid-wall exchange; it does not cap the cold-reservoir heat into the wall. Native EOS/inventory feedback determines pressure and actual condensation. No pressure or quality is imposed after initialization. All parameters are synthetic.

| Step s | Final pressure Pa | Final liquid hold-up kg | Cold-side heat integral J | Max mass residual kg | Max energy residual J | Analytic fluid-U error J | Analytic wall-T error K |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 0.08 | 197705.502919 | 2.77739549942e-05 | -9.50000000118 | 0 | 5.8975047e-13 | 5.6843419e-13 | 7.3544726e-11 |
| 0.04 | 197705.502919 | 2.77739549942e-05 | -9.50000000104 | 0 | 2.245315e-12 | 2.2737368e-12 | 3.0802028e-12 |
| 0.02 | 197705.502919 | 2.77739549942e-05 | -9.50000000103 | 0 | 2.314593e-12 | 2.2737368e-12 | 1.6342483e-13 |

Finest-two-run pressure relative difference: 0, gate 1e-6. Liquid hold-up is stored material, not a collected product or a phase-separated outlet. The fluid-wall cap is active throughout this case, giving independent U(t)=U0-5*t and Twall(t)=18+(5/20)*(1-exp(-20*t/2)) references. No convergence order is inferred from a pressure difference at the floating-point floor.

## Independent cooling/clock and inactive limits

With zero fluid-wall UA, wall C=2 J/K and reservoir-wall UA=1 W/K, the cold temperature is 18+0.1*(absolute_time-10) K on the declared 10–30 s support. The native run advances 10–11 s with the existing absolute-clock driver. The original analytic forced-exponential wall reference is independent of the native integrator; fluid mass/U remain exactly unchanged.

Analytic final wall T=25.2996740485 K; absolute error=1.22973666805e-08 K, gate 1e-7 K. A separate equal-temperature native step has wall deviation 1.7763568394e-14 K against a 1e-12 K/W roundoff budget; native returned values are unchanged.

With external cold-side UA=0, the sealed system still exchanges fluid/wall heat and stores finite gas. Total fluid+wall energy remains constant; the native constructor allows this mode without making the cooling cap zero. Hydraulic isolation (zero flows) independently leaves cold-side cooling active.

At 35 K fluid, 25 K wall, 18 K reservoir and both UAs 20 W/K, the actual native derivative gives -5 W into fluid from wall but -140 W from reservoir into the combined fluid/wall system. Calling the former a system-wide refrigerator capacity would be incorrect. No COP/electrical input or cycle efficiency is inferred.

## Flowing finite native recovery

The same finite condenser connects a 220 kPa/35 K H2 feed and a 180 kPa delivery boundary through two explicit 0.1 mm shared-nozzle valves with effective-area factor 1 and reverse flow disabled. The existing common nozzle owns each hydraulic closure; the native dynamic integrator owns every fluid/wall state update. The run is 10–10.1 s at 0.02 s steps.

Final pressure=199887.038003 Pa; stored liquid fraction=0.000530421958229; mass residual=-3.2560475888e-19 kg; energy residual=-1.82354131795e-14 J; external reservoir heat=-0.183942619063 J; net transported enthalpy=0.00770429341842 J. The native outlet is well mixed; no phase separator, collected liquid tank or return efficiency is invented.

## Retained native failures and capability limits

| Attempt | Actual rejected result |
|---|---|
| native steady zero flow unsupported | mass_flow_kg_s must be finite and positive |
| native steady zero capacity constructor unsupported | cooling_capacity_W must be positive |
| native saturation target above critical | Pressure to PQ_flash [2000000 Pa] may not be above the numerical critical point of 1285776.17852741 Pa |
| native finite over-withdrawal | dynamic vaporizer step would produce non-positive mass |
| native semantic node lacks cold-time callback keyword | dynamic_reliquefier_node() got an unexpected keyword argument 'ambient_temperature_K' |
| host clock support breach | Cold-side boundary evaluated outside declared absolute clock support |

The checked finite condenser only needs the shared native facade's rho/U, PH/PT and saturation capabilities. Its absent layered pressure-projection derivatives are not called or silently replaced. Time-varying cold forcing explicitly selects native dynamic_vaporizer_node over the actual inherited DynamicReliquefier component; no heat equation or RK step is copied.

A completed actual native step is retained when the declared minimum fluid temperature 34.999 K is crossed: raw returned fluid T=34.9944771782 K, raw fluid mass=0.00145091553894 kg. The full native state/derivative/step result remains in the exception; it is not rewritten or accepted.

## Sources, rights and remaining scope

Actual native states, derivatives, step results, dynamic nodes and accepted network/integrator rows remain available. External heat is signed into fluid plus wall; fluid-wall heat is internal and cancels from that combined ledger. A liquid mass fraction denotes actual equilibrium material, not collection efficiency. Native mass loss/depletion, below-triple states or unavailable quality do not receive a clipping, saturation or reverse-flow repair.

Primary references: [native steady source](https://github.com/lyullee/lh2dt_models/blob/b2f276333c1b1793c39f25763703d196d36742ec/src/lh2dt/reliquefier.py), [native finite source](https://github.com/lyullee/lh2dt_models/blob/b2f276333c1b1793c39f25763703d196d36742ec/src/lh2dt/dynamic_reliquefier.py), [CoolProp phase/quality API](https://coolprop.org/coolprop/HighLevelAPI.html), [hydrogen EOS](https://doi.org/10.1063/1.3160306), [first law](https://www.grc.nasa.gov/www/k-12/airplane/thermo1.html). Native code is separately installed under [MIT](https://github.com/lyullee/lh2dt_models/blob/b2f276333c1b1793c39f25763703d196d36742ec/LICENSE); no code, worked examples, mechanism, measured data or equipment curves are bundled.

Receiving/research gaps: public time-aware cold-side naming and independent reservoir-capacity versus internal-exchange-cap semantics, native averaged standalone-step boundary integrals, depletion/event localization, phase-selective withdrawal/collection and actual apparatus/cycle power data. No electrical power/COP is supplied by this cold-reservoir model.

Elapsed local replay time: 7.879825 s.

Native and host source/test/script begin/end byte guards passed.
