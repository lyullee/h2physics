# Competitive multicomponent Langmuir isotherm

`h2physics.adsorption.ExtendedLangmuirIsotherm` supplies one analytical,
caller-parameterized competitive equilibrium provider for absolute adsorption
loading. It implements the extended Langmuir relation independently for each
declared adsorption site:

\[
q_{i,j}=q_{\max,j}\frac{b_{i,j}(T)p_i}
 {1+\sum_k b_{k,j}(T)p_k}
\]

Here `i` follows `AdsorptionBasis.species` exactly and `j` indexes the supplied
site-capacity vector. `affinity_pa_inv(T)` returns a finite nonnegative matrix
with shape `(species, sites)`; `site_capacity_mol_kg` has shape `(sites,)` and
strictly positive absolute capacities. An optional affinity-temperature
derivative callback returns the same matrix shape and provides analytic loading
temperature derivatives. The provider also returns the analytic cross-species
pressure Jacobian in `AdsorptionState`.

```python
isotherm = ExtendedLangmuirIsotherm(
    basis=absolute_uptake_basis,
    domain=AdsorptionDomain(250.0, 450.0, 8.0e6),
    site_capacity_mol_kg=(2.1, 0.7),
    affinity_pa_inv=affinity_matrix_at_temperature,
    affinity_temperature_derivative_pa_inv_k=affinity_derivative,
    evidence_id="material-isotherm-parameter-source",
)
state = isotherm.equilibrium(partial_pressures_pa, temperature_k)
```

The implementation enforces species count, absolute-uptake semantics, positive
site capacity, finite affinities, and the declared pressure/temperature domain.
Capacity and returned state/Jacobian arrays are immutable. The caller supplies
the material data, temperature dependence, gas composition, and evidence
identity. This closure assumes ideal-gas partial pressures and independent
Langmuir site families with competition among the listed adsorbates; it does
not include nonideal fugacity, pore filling, cooperative interactions,
heterogeneous energy distributions, or fitted-parameter uncertainty. The
Hangang contract case is synthetic and does not qualify a sorbent or process.
