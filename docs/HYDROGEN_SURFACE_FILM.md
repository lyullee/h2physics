# Hydrogen diffusion with a surface transfer film

`h2physics.materials.SurfaceFilmCondition` represents a linear external
transfer resistance at either face of the shared planar, spherical-shell, or
cylindrical-shell diffusion mesh. It adds a distinct boundary-resistance level
to the existing bulk mobile/trap solver; no second diffusion integrator is
introduced.

The caller supplies an external concentration already expressed in mol of the
declared mobile entity per cubic metre of solid-equivalent basis, plus a transfer
velocity in m/s. Both may be constants or callbacks of `(time_s, temperature_k)`.
The boundary also requires an evidence identifier. A callback may return
different conditions at the two faces and over time. A velocity of zero means
no exchange. Neither gas pressure/fugacity conversion nor a solubility or surface
reaction law is inferred.

At each wall face, the solver combines the external film and center-to-face solid
diffusion conductances in series. If `k_s` is the supplied transfer velocity,
`A_f` the mesh face area, and `D G_f` the bulk half-cell conductance, the total
face conductance is

`K_f = (k_s A_f)(D G_f) / (k_s A_f + D G_f)`.

The face rate is `K_f (C_ext - C_cell)` at the left face and
`K_f (C_cell - C_ext)` at the right face; both rates are positive in the mesh's
left-to-right coordinate convention. The computation uses a scaled harmonic
form to avoid overflow in the product. The native integrated boundary ledgers
then retain the net amount exchanged with the wall and external reservoirs.

```python
from h2physics.materials import (
    DiffusionDomain, DiffusionMesh, HydrogenCarrier,
    SurfaceFilmCondition, TransportBoundary,
)

carrier = HydrogenCarrier("atomic_hydrogen", 1.008e-3)
mesh = DiffusionMesh.cylindrical_shell(
    inner_radius_m=0.02, outer_radius_m=0.03, length_m=0.5, cells=32,
)
boundary = lambda time_s: TransportBoundary(
    SurfaceFilmCondition(
        bulk_concentration_mol_m3=2.0,
        transfer_velocity_m_s=1.0e-6,
        evidence_id="caller-qualified-entry-film",
    ),
    SurfaceFilmCondition(
        bulk_concentration_mol_m3=lambda t, temperature: 0.2,
        transfer_velocity_m_s=lambda t, temperature: 5.0e-7,
        evidence_id="caller-qualified-exit-film",
    ),
)
result = DiffusionDomain(
    carrier, mesh, diffusivity_m2_s=lambda temperature_k: 1.0e-10,
).simulate(
    time_s=[0.0, 10.0, 100.0],
    initial_mobile_mol_m3=[0.0] * 32,
    boundary=boundary,
    temperature_k=lambda time_s: 298.15,
)
result.require_current()
```

The example coefficients are placeholders and are not suitable material or
process data. External concentrations must already share the same mobile carrier
and concentration basis as the wall state. Existing finite surface inventories
remain a separate boundary owner and cannot simultaneously own the same face.
The model does not add electrochemical charge/reaction balances, oxide-layer
state, adsorption/desorption kinetics, gas-side film calculation, stress-driven
chemical potential, or a coupled temperature field.

The boundary choice is supported by hydrogen-permeation research showing that
surface conditions affect inferred bulk diffusivity and that generalized charging
conditions can represent limits beyond fixed concentration or fixed flux. This
API provides only a linear transfer law with caller-owned coefficients; it does
not reproduce a particular experiment or the nonlinear reaction equations in
those studies. See Turnbull and Wright, [NPL Report MAT 69 (2014)](https://eprintspublications.npl.co.uk/6253/),
and Zhang, Zheng, and Wu, [J. Electrochem. Soc. 146 (1999), 1741–1750](https://doi.org/10.1149/1.1391836).

The deferred contract is `hydrogen-diffusion-surface-film-boundary` in
`validation/cases/material_surface_film.py`. Its analytical steady profile and
inventory checks have not been executed. This model level is unverified; no
acquired dataset currently identifies the caller's film coefficient or matched
material transport properties.
