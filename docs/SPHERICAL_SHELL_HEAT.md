# Transient spherical-shell heat conduction

`h2physics.materials.spherical_shell_heat_history()` solves one-dimensional
transient conduction through a homogeneous spherical shell between positive
inner and outer radii. It reuses the explicit `RadialSolidMaterial` and
`RadialThermalBoundary` records already used by the cylindrical wall solver.
Temperature-dependent conductivity and heat capacity are caller callbacks in
SI units; the selected parameter source remains the caller's responsibility.

Spherical finite volumes use

```text
V_i = 4*pi/3 * (r_outer^3 - r_inner^3)
A(r) = 4*pi*r^2
R(a,b) = (1/(4*pi*k)) * abs(1/a - 1/b)
```

The two face heat ledgers are positive into the wall. Supported boundary kinds
are adiabatic, prescribed surface temperature, heat flux, convection, and
radiation. Convection includes an explicit film coefficient. Radiation uses a
caller-supplied effective irradiation temperature and emissivity-view-factor
product. The result stores cell temperatures, face surface temperatures,
accepted solver output, cumulative boundary energies, material identity, clock
and the sampled global energy residual.

If integration succeeds but later enthalpy quadrature, boundary readout or result
assembly fails, `SphericalShellHeatIntegrationError` retains the accepted SciPy
solution in `native_solution` and the original exception in `cause` and
`__cause__`. A failure inside the RHS may occur before SciPy returns any solution;
there `native_solution` is `None` while the triggering exception remains available.

```python
import numpy as np
from h2physics.materials import (
    RadialSolidMaterial,
    RadialThermalBoundary,
    spherical_shell_heat_history,
)

material = RadialSolidMaterial(
    7800.0,
    heat_capacity_j_kg_k=lambda temperature_k: 500.0,
    conductivity_w_m_k=lambda temperature_k: 2.0,
    material_id="caller-material",
    evidence_id="caller-property-source",
)
result = spherical_shell_heat_history(
    0.045, 0.050, material, 300.0, np.linspace(0.0, 10.0, 101),
    RadialThermalBoundary("convection", 295.0, "inner-fluid", coefficient=50.0),
    RadialThermalBoundary("adiabatic", 0.0, "outer-insulation"),
    history_id="shell-run-1", clock_id="plant-clock",
    evidence_id="spherical-conduction-model",
)
```

This level is a finite-wall conduction calculation with prescribed boundaries.
It has no gas/vessel feedback, LH2 phase change, axial or circumferential
gradients, stress, contact resistance, deformation, or sphere-size population.
It does not convert its output to an equipment rating or material qualification.
The new homogeneous reference comparison is deferred to Nurion; no new model or
validation case was executed locally.
