# Quickstart: Python calculation and research workflow

This guide uses the source checkout or an installed `h2physics` distribution. Commands assume Python 3.12 and an activated isolated environment. Version 0.1.0 is public on PyPI, GitHub and Zenodo; see [publication status](PUBLICATION_STATUS.md).

## 1. Install only the capabilities needed

```bash
python -m venv .venv
python -m pip install --upgrade pip
python -m pip install -e ".[thermo,hydraulics,test]"
```

Activate the environment before the last two commands. On PowerShell use `.venv\Scripts\Activate.ps1`; on POSIX shells use `source .venv/bin/activate`. Optional dependency details are in [DEPENDENCIES.md](DEPENDENCIES.md). External engine source and acquired observations are not part of a core install.

For the public registry distribution, the installation command is `python -m pip install "h2physics[thermo,hydraulics]"`. Use `==0.1.0` when reproducing this release rather than implicitly installing a future version. Inspect the version actually installed with:

```bash
python -c "from importlib.metadata import version; print(version('h2physics'))"
```

## 2. Obtain a physical state

```python
from h2physics.thermo import CoolPropProperties

hydrogen = CoolPropProperties("Hydrogen")
state = hydrogen.state_pt(200_000.0, 300.0)
print(state.basis)
print(state.phase)
print(state.density_kg_m3)
print(state.enthalpy_j_kg)
```

`state_pt` accepts pressure in Pa absolute and temperature in K. Preserve `basis` when passing the state to another calculation. It records physical/reference identity; it is not a decorative label. `Hydrogen` selects the native fluid definition; inspect `state.basis.spin_composition` for its reported descriptor. Choose the native fluid definition explicitly when a different spin convention is required. Relabeling a state does not change its physical composition.

CoolProp enthalpy references are not automatically chemical formation references. Reaction models require a separately declared consistent species/reference convention. See [reaction references](CARRIER_REACTIONS.md).

## 3. Solve a steady hydraulic reference

```python
from fluids.friction import friction_factor
from h2physics.hydraulics import DarcyGeometry, solve_darcy_flow
from h2physics.thermo import CoolPropProperties

fluid = CoolPropProperties("Hydrogen").state_pt(200_000.0, 300.0)
geometry = DarcyGeometry(10.0, 0.01, 1e-6)
result = solve_darcy_flow(
    geometry,
    density_kg_m3=fluid.density_kg_m3,
    viscosity_pa_s=fluid.viscosity_pa_s,
    driving_pressure_pa=1_000.0,
    friction_law=lambda re, relative_roughness: friction_factor(re, relative_roughness),
)
assert result.root_converged
print({"mass_flow_kg_s": result.mass_flow_kg_s,
       "velocity_m_s": result.velocity_m_s,
       "residual_pa": result.momentum_residual_pa})
```

The recorded representative input gives approximately `2.14275e-4 kg/s`. This value is a reproduction aid, not a pipe design acceptance limit. The function solves a positive flow magnitude with frozen supplied density/viscosity. Direction, elevation, boundary pressure and thermal effects remain caller responsibilities. Use the selectable real-gas isothermal or transient level when its assumptions are needed; do not relabel this result as a transient solution. See [HYDRAULICS.md](HYDRAULICS.md).

## 4. Configure the electrochemical core

```python
from h2physics.electrochemistry import (
    HydrogenStack, OhmicLoss, ReactionEnergy, StackGeometry,
)

# Demonstration coefficients and reaction reference, not a measured cell fit.
energy = ReactionEnergy(
    gibbs_j_mol_h2=237_000.0,
    enthalpy_j_mol_h2=286_000.0,
    reference_id="explicit-demonstration-water-splitting-reference",
    water_phase="liquid",
)
stack = HydrogenStack(
    StackGeometry(series_cells=10, active_area_m2=0.01,
                  hydrogen_molar_mass_kg_mol=0.00201588),
    thermochemistry=lambda temperature_k: energy,
    losses={"ohmic": OhmicLoss(lambda temperature_k: 0.0002)},
)
result = stack.evaluate(1_000.0, 300.0, mode="electrolysis")
print(result.cell_voltage_v)
print(result.hydrogen_production_mol_s)
print(result.electric_input_w)
```

Current density is a nonnegative magnitude in A/m². In electrolysis mode, positive electric input and positive H₂ production represent consumption and production at the declared boundary. Fuel-cell mode uses the same core with reversed boundary signs. This simple example does not predict cell temperature, aging, crossover, pressure dynamics or plant efficiency.

Replace `thermochemistry` and the loss callbacks with qualified inputs for the intended operating domain. The callback receives the stated temperature; a constant demonstration callback does not become temperature-dependent evidence. A Faradaic efficiency below one changes material accounting, but its unmodeled thermal fate is not silently assigned to heat.

## 5. Customize ordinary Python objects

No server, transport format or application framework is needed:

```python
from dataclasses import replace
from h2physics.hydraulics import DarcyGeometry

base = DarcyGeometry(length_m=10.0, diameter_m=0.01, roughness_m=1e-6)
larger_pipe = replace(base, diameter_m=0.02)
print(larger_pipe)
```

Model-specific immutable parameter objects are preferred to changing an issued result in place. Supply NumPy arrays and time-series objects through the documented API. Keep a result's source object, provider definition and clock support available when the receiving interface requires them. Some adapters reject copied, relabeled or altered issued results even when their numbers look similar.

## 6. Work with time and finite inventories

Use explicit time samples, event boundaries and declared interpolation. A source's start/end support must cover the receiving calculation. Do not assume a scheduled valve command instantaneously removes inventory already downstream of the valve.

Finite examples include:

- [Finite supply](FINITE_SUPPLY.md): tank, pump, line and vaporizer composition.
- [Finite transfer](FINITE_TRANSFER.md): source/receiver inventories and product delivery.
- [Finite hydride](FINITE_HYDRIDE.md): finite gas/solid storage and energy references.
- [Finite fuel cell](FINITE_FUEL_CELL.md): material, electrical and heat accounting.
- [Facility continuity](FACILITY_CONTINUITY.md): node and boundary ledgers.

Read each example's declared native revision and required optional installations before executing it. A fixture using an authored material coefficient is an example, not independent material validation.

## 7. Handle failures without changing the physics silently

```python
from h2physics.thermo import CoolPropProperties

try:
    CoolPropProperties("Hydrogen").state_pt(-1.0, 300.0)
except ValueError as error:
    print("Invalid physical input:", error)
```

A missing dependency is different from invalid input, an out-of-domain model, a native numerical rejection or a failed conservation check. Preserve the exception and any retained partial result. Do not catch every failure and substitute an ideal-gas or unrelated solver result. Native preferred-provider rules are in [PREFERRED_DISPERSION.md](PREFERRED_DISPERSION.md).

## 8. Run a bounded software check

```bash
python -m pytest tests/test_core_thermo.py tests/test_electrochemistry.py tests/test_hydride.py tests/test_materials.py tests/test_reactions.py tests/test_hydraulics.py -q
```

These are selected existing tests. A core-only environment cannot run all native/data-dependent research tests. The [regression/representative report](REGRESSION_REPRESENTATIVE_CAMPAIGN.md) preserves the recorded 50-case selection and six representative input-to-output runs. Prefer the report's exact commands when reproducing evidence.

For the representative suites, use separate processes and install the providers specified by the report:

```bash
python -m pytest tests/test_representative_run_equipment.py -q
python -m pytest tests/test_representative_run_production_safety.py -q
```

The prior broad campaigns are [input](INPUT_CONTRACT_CAMPAIGN.md), [nominal](FORMULA_CONTRACT_CAMPAIGN.md), [extreme](EXTREME_CONTRACT_CAMPAIGN.md) and [connections](CONNECTION_CONTRACT_CAMPAIGN.md). Scope and exclusions differ; do not add their case counts to obtain a number of validated models.

## 9. Compare a model with measurements

Keep source rights, original units, geometry/material definition and measured versus simulated origin explicit. Fit coefficients on calibration data only, then evaluate whole held-out curves, experiments or conditions. Do not use a curve's held-out values to tune its coefficients or choose a favorable threshold.

The [physical comparison report](PHYSICAL_VALIDATION_CAMPAIGN.md) gives four worked replay paths and explains their limits. Scripts under `scripts/validate_*_experiments.py` consume separately acquired files with source checksums. A script returning zero means that its execution completed; it does not turn a conditional comparison into formal qualification. The local per-row outputs and raw source files are excluded from distribution.

## 10. Continue or extend the work

Use [DEVELOPMENT_HISTORY.md](DEVELOPMENT_HISTORY.md) for the sequence of decisions and [RESEARCH_CONTINUATION.md](RESEARCH_CONTINUATION.md) for the restart procedure. Preserve before/after source hashes, interpreter/provider versions, input parameters, measured-data identity and the exact command for each new run. Keep unknown conditions and rejected cases visible.

For an extension owned by an existing engine, write a concrete receiving-interface request rather than creating another solver at the same physical level. Existing requests are indexed in [requests/README.md](../requests/README.md).

Original project code is Apache-2.0. External inputs/providers retain their terms; see [RIGHTS_AND_PROVENANCE.md](RIGHTS_AND_PROVENANCE.md), [LICENSE](../LICENSE) and [NOTICE](../NOTICE).
