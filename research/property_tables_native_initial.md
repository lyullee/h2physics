# Thermodynamic table qualification

Direct HEOS comparisons check interpolation error, not independent EOS accuracy.
The envelope excludes phase change and the critical temperature region.
Timings include construction of the same complete native state object.

PT and interior PH/PS states are compared. Energy identity uses a separate gate.

| Fluid | Backend | States | Largest relative error | Speedup | Qualification |
|---|---|---:|---:|---:|---|
| Hydrogen | BICUBIC&HEOS | 1004 | 0.000592424 | 1.282 | FAIL |
| Hydrogen | TTSE&HEOS | 1004 | 0.00252284 | 1.673 | FAIL |
| ParaHydrogen | BICUBIC&HEOS | 1004 | 0.00132348 | 1.514 | FAIL |
| ParaHydrogen | TTSE&HEOS | 1004 | 0.0026249 | 1.850 | FAIL |

## Hydrogen with BICUBIC&HEOS

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


## Hydrogen with TTSE&HEOS

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


## ParaHydrogen with BICUBIC&HEOS

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


## ParaHydrogen with TTSE&HEOS

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
