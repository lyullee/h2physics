# Elastic cylinder result contract

`h2physics.materials.lame_stress_field` returns a `CylinderStressField` carrying
radial, hoop, axial and von Mises stress at the requested wall radii. The result
constructor copies and freezes its arrays, checks that all vectors have the same
finite shape and that radii lie inside the retained cylinder geometry. It also
checks the von Mises invariant against the three stored principal stresses. These
guards apply to direct construction as well as solver-produced results.

The associated deferred contract is
`elastic-cylinder-pressure-boundaries` in
`validation/cases/elastic_cylinder.py`. It covers array immutability and rejects
an inconsistent constructed result. The contract remains deferred; no validation
run is claimed here. The underlying pressure-only Lamé model remains a long,
uniform, linear-elastic cylinder approximation and does not qualify finite-length,
plastic, residual-stress or flaw behavior.
