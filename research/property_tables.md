# Thermodynamic table qualification

Direct HEOS comparisons check interpolation error, not independent EOS accuracy.
The envelope excludes phase change and the critical temperature region.
Timings include complete state construction and the public table domain guards. The workload contains PT and interior PH/PS calls in approximately equal numbers.

PT and interior PH/PS states are compared. Energy identity uses a separate gate.

The explicit derive_from_h_p_rho policy computes internal energy from h − p/rho and records the change from the library value. It does not modify h, rho, s, cp, cv or acoustic derivatives, and does not establish complete differential thermodynamic consistency. The default remains library-provided internal energy.

| Fluid | Backend | Energy policy | PT points | PH/PS points | Largest relative error | Speedup | Gate |
|---|---|---|---:|---:|---:|---:|---|
| Hydrogen | BICUBIC&HEOS | library | 1004 | 2000 | 0.000592424 | 4.157 | FAIL |
| Hydrogen | BICUBIC&HEOS | derive_from_h_p_rho | 1004 | 2000 | 0.000592424 | 4.766 | PASS |
| Hydrogen | TTSE&HEOS | library | 1004 | 2000 | 0.00252284 | 4.690 | FAIL |
| Hydrogen | TTSE&HEOS | derive_from_h_p_rho | 1004 | 2000 | 0.00252284 | 4.068 | PASS |
| ParaHydrogen | BICUBIC&HEOS | library | 1004 | 2000 | 0.00132348 | 4.863 | FAIL |
| ParaHydrogen | BICUBIC&HEOS | derive_from_h_p_rho | 1004 | 2000 | 0.00132348 | 4.080 | PASS |
| ParaHydrogen | TTSE&HEOS | library | 1004 | 2000 | 0.0026249 | 5.461 | FAIL |
| ParaHydrogen | TTSE&HEOS | derive_from_h_p_rho | 1004 | 2000 | 0.0026249 | 4.971 | PASS |

## Hydrogen with BICUBIC&HEOS, library

- density_kg_m3: 1.35151e-06
- enthalpy_j_kg: 4.4174668e-07
- internal_energy_j_kg: 6.150327e-07
- entropy_j_kg_k: 5.9668607e-08
- cp_j_kg_k: 1.5033059e-05
- cv_j_kg_k: 2.2476371e-05
- viscosity_pa_s: 0.00040077449
- conductivity_w_m_k: 0.00059242405
- speed_of_sound_m_s: 1.0912777e-05
- Maximum h-u-p/rho residual: 1.61131 J/kg
- Maximum scaled identity error: 5.02803e-07
- Identity error limit: 1e-07
- Maximum internal-energy adjustment: 0 J/kg
- Envelope: GasEnvelope(minimum_pressure_pa=100000.0, maximum_pressure_pa=90000000.0, minimum_temperature_k=230, maximum_temperature_k=400)
- Seed: 20261026


## Hydrogen with BICUBIC&HEOS, derive_from_h_p_rho

- density_kg_m3: 1.35151e-06
- enthalpy_j_kg: 4.4174668e-07
- internal_energy_j_kg: 1.1268716e-06
- entropy_j_kg_k: 5.9668607e-08
- cp_j_kg_k: 1.5033059e-05
- cv_j_kg_k: 2.2476371e-05
- viscosity_pa_s: 0.00040077449
- conductivity_w_m_k: 0.00059242405
- speed_of_sound_m_s: 1.0912777e-05
- Maximum h-u-p/rho residual: 2.3283064e-10 J/kg
- Maximum scaled identity error: 7.5315044e-17
- Identity error limit: 1e-07
- Maximum internal-energy adjustment: 1.61131 J/kg
- Envelope: GasEnvelope(minimum_pressure_pa=100000.0, maximum_pressure_pa=90000000.0, minimum_temperature_k=230, maximum_temperature_k=400)
- Seed: 20261026


## Hydrogen with TTSE&HEOS, library

- density_kg_m3: 0.000148034
- enthalpy_j_kg: 0.00011629787
- internal_energy_j_kg: 0.00013444358
- entropy_j_kg_k: 4.1221046e-06
- cp_j_kg_k: 0.001331456
- cv_j_kg_k: 0.0019064415
- viscosity_pa_s: 0.00041502998
- conductivity_w_m_k: 0.00091845639
- speed_of_sound_m_s: 0.0025228371
- Maximum h-u-p/rho residual: 215.94859 J/kg
- Maximum scaled identity error: 7.2520165e-05
- Identity error limit: 1e-07
- Maximum internal-energy adjustment: 0 J/kg
- Envelope: GasEnvelope(minimum_pressure_pa=100000.0, maximum_pressure_pa=90000000.0, minimum_temperature_k=230, maximum_temperature_k=400)
- Seed: 20261026


## Hydrogen with TTSE&HEOS, derive_from_h_p_rho

- density_kg_m3: 0.000148034
- enthalpy_j_kg: 0.00011629787
- internal_energy_j_kg: 0.00023874295
- entropy_j_kg_k: 4.1221046e-06
- cp_j_kg_k: 0.001331456
- cv_j_kg_k: 0.0019064415
- viscosity_pa_s: 0.00041502998
- conductivity_w_m_k: 0.00091845639
- speed_of_sound_m_s: 0.0025228371
- Maximum h-u-p/rho residual: 2.3283064e-10 J/kg
- Maximum scaled identity error: 7.5151442e-17
- Identity error limit: 1e-07
- Maximum internal-energy adjustment: 215.94859 J/kg
- Envelope: GasEnvelope(minimum_pressure_pa=100000.0, maximum_pressure_pa=90000000.0, minimum_temperature_k=230, maximum_temperature_k=400)
- Seed: 20261026


## ParaHydrogen with BICUBIC&HEOS, library

- density_kg_m3: 8.2205091e-07
- enthalpy_j_kg: 4.2733962e-07
- internal_energy_j_kg: 6.6385946e-07
- entropy_j_kg_k: 4.1551357e-08
- cp_j_kg_k: 4.1166201e-05
- cv_j_kg_k: 6.3656853e-05
- viscosity_pa_s: 0.00054824603
- conductivity_w_m_k: 0.0013234782
- speed_of_sound_m_s: 1.217585e-05
- Maximum h-u-p/rho residual: 0.89731433 J/kg
- Maximum scaled identity error: 2.3699119e-07
- Identity error limit: 1e-07
- Maximum internal-energy adjustment: 0 J/kg
- Envelope: GasEnvelope(minimum_pressure_pa=100000.0, maximum_pressure_pa=90000000.0, minimum_temperature_k=230, maximum_temperature_k=400)
- Seed: 20261026


## ParaHydrogen with BICUBIC&HEOS, derive_from_h_p_rho

- density_kg_m3: 8.2205091e-07
- enthalpy_j_kg: 4.2733962e-07
- internal_energy_j_kg: 6.7516377e-07
- entropy_j_kg_k: 4.1551357e-08
- cp_j_kg_k: 4.1166201e-05
- cv_j_kg_k: 6.3656853e-05
- viscosity_pa_s: 0.00054824603
- conductivity_w_m_k: 0.0013234782
- speed_of_sound_m_s: 1.217585e-05
- Maximum h-u-p/rho residual: 4.6566129e-10 J/kg
- Maximum scaled identity error: 7.971655e-17
- Identity error limit: 1e-07
- Maximum internal-energy adjustment: 0.89731433 J/kg
- Envelope: GasEnvelope(minimum_pressure_pa=100000.0, maximum_pressure_pa=90000000.0, minimum_temperature_k=230, maximum_temperature_k=400)
- Seed: 20261026


## ParaHydrogen with TTSE&HEOS, library

- density_kg_m3: 8.5699286e-05
- enthalpy_j_kg: 7.6319121e-05
- internal_energy_j_kg: 7.887306e-05
- entropy_j_kg_k: 4.1458249e-06
- cp_j_kg_k: 0.00092469258
- cv_j_kg_k: 0.0012529758
- viscosity_pa_s: 0.00054594171
- conductivity_w_m_k: 0.0026248994
- speed_of_sound_m_s: 0.0022210682
- Maximum h-u-p/rho residual: 82.47991 J/kg
- Maximum scaled identity error: 2.3245672e-05
- Identity error limit: 1e-07
- Maximum internal-energy adjustment: 0 J/kg
- Envelope: GasEnvelope(minimum_pressure_pa=100000.0, maximum_pressure_pa=90000000.0, minimum_temperature_k=230, maximum_temperature_k=400)
- Seed: 20261026


## ParaHydrogen with TTSE&HEOS, derive_from_h_p_rho

- density_kg_m3: 8.5699286e-05
- enthalpy_j_kg: 7.6319121e-05
- internal_energy_j_kg: 7.6100835e-05
- entropy_j_kg_k: 4.1458249e-06
- cp_j_kg_k: 0.00092469258
- cv_j_kg_k: 0.0012529758
- viscosity_pa_s: 0.00054594171
- conductivity_w_m_k: 0.0026248994
- speed_of_sound_m_s: 0.0022210682
- Maximum h-u-p/rho residual: 4.6566129e-10 J/kg
- Maximum scaled identity error: 7.9577499e-17
- Identity error limit: 1e-07
- Maximum internal-energy adjustment: 82.47991 J/kg
- Envelope: GasEnvelope(minimum_pressure_pa=100000.0, maximum_pressure_pa=90000000.0, minimum_temperature_k=230, maximum_temperature_k=400)
- Seed: 20261026
