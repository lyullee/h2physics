# Elastic-energy ceiling for a vessel fragment scenario

`h2physics.fragment_energy_bound.bound_fragment_speed_from_elastic_energy`
uses the existing thick-cylinder Lamé pressure field to integrate linear-elastic
strain energy over a uniform cylindrical wall. The user supplies wall length,
Young's modulus, Poisson ratio, a fragment mass and an energy allocation between
zero and one. The result reports the strain-energy quantity, the selected
fragment's allocated energy, and the corresponding maximum speed if all of that
allocation became kinetic energy.

```python
bound = bound_fragment_speed_from_elastic_energy(
    geometry, differential_pressure_load,
    cylinder_length_m=1.5,
    youngs_modulus_pa=2.0e11,
    poisson_ratio=0.3,
    fragment_mass_kg=2.0,
    fragment_energy_fraction=0.1,
    fragment_id="section-a-piece-1",
    material_evidence_id="material-test-or-source-id",
)
```

The pressure load must represent an incremental gauge-pressure field with zero
external pressure. Closed or open axial support follows the input cylinder
geometry. This bound assumes isotropic linear elasticity and a long uniform
cylinder. It excludes end caps, crack-tip plasticity, local tearing, gas
expansion, pressure-wave work, thermal energy and contact. Fragment mass and
energy allocation are caller choices; no rupture criterion, breach geometry,
fragment count, direction, actual launch speed or risk probability is inferred.

The `cylinder-elastic-fragment-speed-ceiling` Hangang case is an authored
synthetic algebraic contract. It checks the exact annular strain-energy
integral and energy-to-speed closure only; it is not a material or vessel
qualification.
