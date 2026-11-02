# Finite spherical-wall storage

`storage.microsphere.MicrosphereStorage` resolves a finite pure-H2 cavity and a
spherical permeable wall. Inner pressure follows the actual native gas EOS as
moles enter or leave. Wall mobile and trapped inventories are retained. This
adds spherical geometry and finite boundary feedback to the existing material
diffusion model, through one shared finite-volume solver.

## Inputs and native ownership

Provide inner/outer radii in metres, at least three cells, a uniform D(T) in
m2/s and the existing `PowerLawSolubility`. Its carrier must be molecular H2
with the native gas molar mass. Concentration is mol(H2)/m3 of wall; the linear
solubility coefficient is mol(H2)/(m3 Pa), or more generally
mol(H2)/(m3 Pa**exponent). Fugacity is in Pa. Selecting a power law requires
material/surface evidence; no glass coefficient or fitting table is supplied.

Inject the existing `HydrideGasThermodynamics` native capability. Despite its
historical name, its density/T, fixed-spin reference, fugacity and molar mass
functions describe the same pure H2 needed here. Its actual native objects
remain inspectable. `HydrideGasThermodynamics.coolprop("Hydrogen")` selects
normal H2; `"ParaHydrogen"` explicitly selects para H2. There is no duplicated
EOS or silent change of spin identity. A future generic alias belongs in the
shared property layer, rather than a separate microsphere thermodynamic engine.

`MicrosphereDomain` requires increasing T/P bounds and a positive gas-mole
floor. Every native evaluation checks basis, gas-like phase, pressure,
temperature and reconstructed density. A property failure rejects the window.
Floor crossing is rejected without mass clipping or a claimed crossing time.

## Python example

```python
import numpy as np
from h2physics.materials import HydrogenCarrier, PowerLawSolubility
from h2physics.storage.finite_hydride import HydrideGasThermodynamics
from h2physics.storage import MicrosphereDomain, MicrosphereStorage

gas = HydrideGasThermodynamics.coolprop("Hydrogen")
wall_h2 = HydrogenCarrier("molecular_hydrogen", gas.molar_mass_kg_mol)
model = MicrosphereStorage(
    inner_radius_m=10e-6, outer_radius_m=11e-6, cells=24,
    diffusivity_m2_s=lambda T: 1e-14,
    solubility=PowerLawSolubility(wall_h2, lambda T: 1e-5, 1.),
    gas=gas, domain=MicrosphereDomain(200., 600., 1., 1e7, 1e-20),
    parameter_evidence="authored demonstration; not a material fit")
initial = gas.state_pt(1e5, 300.)
moles = initial.density_kg_m3*model.cavity_volume_m3/gas.molar_mass_kg_mol
result = model.simulate(
    np.linspace(100., 200., 101), moles, np.zeros(24),
    temperature_k=lambda t: 300., external_hydrogen_fugacity_pa=lambda t: 0.,
    clock_id="authored-clock", boundary_evidence="authored zero-fugacity bath",
    maximum_step_s=1.)
pressure_pa = np.array([s.pressure_pa for s in result.gas_states])
```

Replace demonstration values with qualified material and boundary inputs.
External H2 fugacity is a boundary condition; supplying ambient total pressure
as H2 fugacity requires a supported composition/thermodynamic relation.

For a coating that blocks the exterior, omit external fugacity and provide
`external_wall_condition=lambda t,T: SurfaceCondition("flux", 0.)`. A signed
flux is mol(H2)/(m2 s), positive radially outward. Exactly one outside boundary
owner is required. General callers may supply explicit concentrations or
fluxes with appropriate evidence. Charge and release use the same equations.

## Results and conservation

`result.transport` retains the actual SciPy solution, read-only wall fields,
trap fields, inner/outer time-integrated molar transfers and both wall and
whole-system molar residuals. Left flux is positive from cavity into wall;
right flux is positive from wall into the exterior. Cavity moles therefore
change by minus the inner transfer. Whole cavity-plus-wall inventory changes
by minus the exterior transfer. Mass is the entity inventory times the declared
molar mass. `gas_states` retain pressure, phase and thermodynamic reference;
`gas_fugacity_pa`, `gas_transfer_residual_mol` and
`total_hydrogen_mass_kg` support separate audits. Clock and evidence strings
follow the result.

`materials.DiffusionMesh` supplies true shell volumes, face areas and integrated
radial resistances. `DiffusionDomain` owns the shared BDF method and kinetic
trap law. `DiffusionSlab` delegates to it with unit area while preserving its
existing mol/m2 output API. Finite faces are optional
`FiniteSurfaceInventory` objects in mol of the declared carrier; do not pass
moles H2 directly to an atomic-H wall without the factor-of-two mapping.
The generic kernel supports finite inventories on both faces. Static face
conditions use `TransportBoundary`; a finite-owned face must be `None` there.
The wall field is cell-centered. Multiplying it by each exact geometric volume
is a spatial quadrature approximation; exact steady radial face resistance
does not make every transient wall integral exact. The independent series and
mesh-refinement checks measure that remaining spatial error.

## Verification and physical limits

Run `python scripts/check_microsphere_storage.py` with the thermo extra and
`python -m pytest tests/test_materials.py tests/test_curvilinear_diffusion.py
tests/test_microsphere.py`. The executed report in
[research/microsphere_storage.md](../research/microsphere_storage.md) contains
exact spherical steady transport, independent transient series, mesh
convergence, cavity/wall/exterior conservation and independent actual-EOS
reconstruction. Source hashes identify the code that ran. The existing planar
Fourier and trap checks are preserved.

Temperature is prescribed uniformly for gas and wall. The model does not
compute heat capacity, thermostat power, self-heating or a thermal stress
cycle. It excludes mechanical deformation/rupture, optical enhancement,
size distributions and surface-limited kinetics. Single gas-like cavity
states and a homogeneous material are required. Source-specific D/solubility,
traps, boundary experiments and held-out data remain needed before physical
qualification. Increasing cell count does not provide that evidence.

Original geometry and conservation equations use public scientific context:
[glass H2 permeation](https://doi.org/10.3389/fmats.2019.00342),
[molecular diffusion study](https://doi.org/10.1063/1.324180) and
[native CoolProp API](https://coolprop.org/coolprop/LowLevelAPI.html).
Published parameter tables, figures, worked examples and code are not included.
