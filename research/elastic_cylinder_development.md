# Thick-cylinder elastic pressure field checkpoint

Status: **implemented_unverified**. This increment adds an original SI Python
evaluation of the axisymmetric Lamé pressure field. No numerical case, unit suite,
fatigue integration, or measured vessel comparison has been executed locally.

`h2physics.materials.elastic_cylinder` returns radial, hoop, closed/open-end axial,
and von Mises stresses at caller-specified radii in a long, uniform hollow cylinder.
Internal and external inputs are absolute Pa; the resulting field depends on their
difference and preserves tension-positive sign. Radius points must remain within
the wall. The shape is held constant and the input pressure is spatially uniform.

The equations are the classical elastic thick-cylinder solution documented in
Cambridge Engineering's [thick-cylinder derivation](https://www-mdp.eng.cam.ac.uk/web/library/enginfo/textbooks_dvd_only/DAN/cylinders/thick/thick.html)
and the Oak Ridge National Laboratory report [ORNL/TM-2014/106](https://www.osti.gov/servlets/purl/1133475).
The module implements only the radial and hoop field plus the conventional uniform
pressure axial resultant for an explicitly closed end. Its authored validation
case compares pressure tractions at both surfaces, distinguishes open and closed
ends, and checks the returned principal-stress invariant. The case is deferred for
Nurion; the inequalities recorded here are not results.

This is a pressure-stress reference, not a vessel qualification. It omits end
transitions, nozzles, supports, residual/autofrettage stresses, thermal gradients,
plasticity, local stress concentration, fatigue geometry factors, crack initiation,
fracture toughness, and code design margins. Pairing it with hydrogen crack growth
still requires an explicit flaw geometry and a qualified stress-intensity callback;
no formula converts this stress field to a crack-driving force.

## Uniform-temperature axial restraint extension — 2026-10-29

`IsotropicThermoelasticMaterial`, `UniformCylinderTemperature`, and
`thermoelastic_lame_stress_field` extend the pressure solution to a homogeneous,
isotropic, constant-property cylinder with a spatially uniform wall temperature.
The caller supplies Young's modulus, Poisson ratio, thermal expansion coefficient,
material/property evidence identity, reference/current absolute temperatures,
temperature evidence identity, and either free or fixed axial expansion.

Let `A=(Pi*ri^2-Po*ro^2)/(ro^2-ri^2)`, the pressure solution's constant
`sigma_r+sigma_theta=2A`. Under fixed axial strain, isotropic thermoelastic
compatibility gives `sigma_z=2*nu*A-E*alpha*(T-Tref)`. With free axial expansion,
the original open/closed pressure boundary result remains and uniform temperature
adds no stress. Radial and hoop stresses remain the pressure Lamé solution because
the added uniform axial stress does not change radial equilibrium or traction
boundaries in this idealization. For fixed restraint the result also reports the
axial support reaction after subtracting closed-end pressure thrust from the wall
axial resultant. Positive reaction follows +z on the positive end; the caller must
establish that such supports exist.

The constitutive form and long-cylinder plane-strain boundary distinctions are
consistent with the thermoelastic relations in [MIT OCW structural mechanics lecture
12](https://ocw.mit.edu/courses/22-314j-structural-mechanics-in-nuclear-power-technology-fall-2006/e6664ebdbc4bcad10e2602deb9bf389d_m12.pdf)
and the axisymmetric thick-cylinder boundary derivation in [Applied Mechanics of
Solids, section 4.1.9](https://solidmechanics.org/text/Chapter4_1/Chapter4_1.htm).
The extension is implemented and statically reviewed only. The deferred Nurion
case checks the free-temperature invariant, plane-strain compatibility, support
force accounting and von Mises reconstruction; none has been executed. No radial
temperature gradient, end transition, yielding, residual stress, local concentration,
fatigue, crack-intensity mapping or vessel qualification is inferred.
