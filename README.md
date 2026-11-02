# h2physics

Composable Python models for hydrogen production, storage, transfer and safety research.

h2physics supplies calculation objects, explicit physical state and time-series contracts, and optional adapters to specialist engines. Parameters and providers can be replaced through ordinary Python objects, functions and arrays. A web service or serialization layer is not required.

This is a research software release. Implementation, software verification, experimental comparison and application qualification have separate evidence. Start with the [quickstart](https://github.com/lyullee/h2physics/blob/main/docs/QUICKSTART.md), [Korean overview](https://github.com/lyullee/h2physics/blob/main/README_KO.md), or [Python API index](https://github.com/lyullee/h2physics/blob/main/docs/PUBLIC_API_INDEX.md).

Version **0.2.0** is Alpha research software. [PyPI 0.2.0](https://pypi.org/project/h2physics/0.2.0/)
and [Zenodo 0.2.0](https://doi.org/10.5281/zenodo.23889027) are public. Find downloads and citations through
[PyPI](https://pypi.org/project/h2physics/), [GitHub releases](https://github.com/lyullee/h2physics/releases),
and the [Zenodo version series](https://doi.org/10.5281/zenodo.23886389).
[Publication status](https://github.com/lyullee/h2physics/blob/main/docs/PUBLICATION_STATUS.md)
records service-confirmed versions and file identities.

This version adds [eight model-level extensions](https://github.com/lyullee/h2physics/blob/main/docs/ENHANCEMENTS_20261102.md):
indoor HyRAM accumulation/conditional peaks, FA/DDT screening, mechanical
expansion energy and weak-wave loads, linear structural dynamics, native thermal
cycles/exergy, solid redox equilibrium, electrode measurement analysis and a
coupled PAR device. Each manual states its numerical evidence and remaining
experimental limits. The scoped campaign completed 92 new and 47 related existing
checks across the main and separately selected native runtime profiles.

## What is included

| Area | Selected capabilities | Important boundary |
| --- | --- | --- |
| Thermodynamic state | CoolProp pure fluids, fixed-composition mixtures, reference-aware reaction enthalpies, qualified table interfaces | Native properties or explicitly qualified tables; no silent substitute EOS |
| Equipment and transfer | Tank inventories, valves, pumps, pipes, heat exchange, insulation, compression, relief, recovery and finite transfer | Each selected level declares its geometry, boundary conditions and native dependency |
| Storage | Hydride equilibrium/kinetics and finite beds, adsorption, carrier conversion, microspheres, porous reservoirs | Model levels and material coefficients are explicit; a material fit is not a whole-vessel qualification |
| Production and separation | Electrolyzer/fuel-cell core, PV coupling, photochemistry, finite reactions, membrane and PSA interfaces | Optional engines and measured parameter evidence are installed/supplied separately |
| Materials | Solubility, permeation, conservative diffusion, trapping, thermal/mechanical fields and integrity interfaces | Carrier definition, specimen geometry, stress/temperature references and units must agree |
| Releases and safety | Gas/liquid/two-phase nozzle, finite source histories, parcels, impact/pool boundaries, dispersion/fire/exposure interfaces | Source prediction, field prediction and receptor response are separate stages |
| Facility and research | Networks, sensors, alarms, isolation, detector voting, conditional risk, uncertainty and cost projections | Inputs must state clocks, assumptions, evidence and any frequency or economic basis |

The [catalog](https://github.com/lyullee/h2physics/blob/main/docs/MODEL_CATALOG.md) contains **82 catalog entries**. The recent verification campaigns use **78 scoped topic families**. Neither number counts independent equations or proves complete physical qualification. Several entries expose native engines, supporting accounting, or narrower selectable model levels. Use [model selection](https://github.com/lyullee/h2physics/blob/main/docs/MODEL_SELECTION.md) and the individual manuals to choose the actual callable and its limits.

## Installation

Python **3.12** is the recorded reference interpreter. The package metadata permits Python 3.12 or later; optional native providers can impose narrower compatibility requirements.

For a source checkout:

```bash
git clone https://github.com/lyullee/h2physics.git
cd h2physics
python -m venv .venv
# Activate .venv with the command appropriate to your shell.
python -m pip install --upgrade pip
python -m pip install -e ".[thermo,hydraulics,test]"
```

The distribution and import name are currently `h2physics`. The command below installs the selected optional capabilities from the package index. See the [publication status](https://github.com/lyullee/h2physics/blob/main/docs/PUBLICATION_STATUS.md):

```bash
python -m pip install "h2physics[thermo,hydraulics]"
```

Core installation provides NumPy/SciPy-based functionality. Install `thermo` for the CoolProp-backed fluid calculations. Production fluid properties must use CoolProp or a table qualified against that provider. An optional extra does not install every specialist engine or clear its license. See [dependencies](https://github.com/lyullee/h2physics/blob/main/docs/DEPENDENCIES.md), [native integration](https://github.com/lyullee/h2physics/blob/main/docs/NATIVE_EQUIPMENT.md), and [rights/provenance](https://github.com/lyullee/h2physics/blob/main/docs/RIGHTS_AND_PROVENANCE.md).

## First calculation: a hydrogen pipe

This example uses a real-fluid upstream state from CoolProp and a separately selected friction correlation. It is a frozen-property steady reference, not a transient or thermal pipe model.

```python
from fluids.friction import friction_factor
from h2physics.hydraulics import DarcyGeometry, solve_darcy_flow
from h2physics.thermo import CoolPropProperties

properties = CoolPropProperties("Hydrogen")
upstream = properties.state_pt(200_000.0, 300.0)  # Pa absolute, K

result = solve_darcy_flow(
    DarcyGeometry(length_m=10.0, diameter_m=0.01, roughness_m=1e-6),
    density_kg_m3=upstream.density_kg_m3,
    viscosity_pa_s=upstream.viscosity_pa_s,
    driving_pressure_pa=1_000.0,
    friction_law=lambda reynolds, relative_roughness: friction_factor(
        reynolds, relative_roughness
    ),
)
print(result.mass_flow_kg_s)       # kg/s
print(result.velocity_m_s)         # m/s
print(result.momentum_residual_pa) # Pa
```

The [quickstart](https://github.com/lyullee/h2physics/blob/main/docs/QUICKSTART.md) continues with electrochemistry, parameter replacement, error handling, representative runs and reproducible analysis. The [API guide](https://github.com/lyullee/h2physics/blob/main/docs/API.md) explains shared object contracts; the [symbol index](https://github.com/lyullee/h2physics/blob/main/docs/PUBLIC_API_INDEX.md) lists actual modules and definitions.

## Physical contracts

- Use SI values: Pa **absolute**, K, kg, m and s. Convert gauge pressure, Celsius, normal-volume flow and engineering units explicitly at the input boundary.
- Keep fluid/species, H versus H₂ carrier, phase, spin composition and enthalpy reference identifiable. A property-library enthalpy zero is not automatically a reaction formation reference.
- A shared time label does not establish aligned clocks. Declare the source interval, sampling/interpolation rule and support explicitly.
- A mass-flow rate is not a complete accident scenario. An accident source needs its opening, location, phase, inventory, event clock and termination.
- Result objects retain diagnostics and, where supported, issuing provider/source bindings. Read the selected API's `require_current()` contract before reusing a result.
- Failures and out-of-domain results are retained or rejected. Preferred-provider failure does not silently switch physics.

## Optional engines

HyRAM+ is the preferred high-pressure gaseous-hydrogen dispersion provider; SLABx-LH2 is preferred for liquid-hydrogen-origin dispersion. Other selectable integrations include Cantera, LH2DT, PSA-Dyna, HELPR and further specialist modules. These are not bundled copies of external solvers.

Each native adapter has its own installation, revision, runtime and applicability requirements. Read the relevant guide before calling it. A missing optional provider can legitimately prevent that operation while unrelated core models remain usable. A generic `pip install h2physics` is not a full native-engine installation. The [preferred dispersion guide](https://github.com/lyullee/h2physics/blob/main/docs/PREFERRED_DISPERSION.md) documents provider ownership and rejection boundaries.

## Recorded verification and measured-data comparisons

The following results describe specific recorded campaigns, not a release-wide accuracy guarantee. Detailed reports retain exact scope, limitations, commands and evidence references.

| Campaign | Recorded result | Interpretation |
| --- | --- | --- |
| [Input contracts](https://github.com/lyullee/h2physics/blob/main/docs/INPUT_CONTRACT_CAMPAIGN.md) | 78/78 topic families; 162 passing cases | Representative invalid inputs and one manifest check |
| [Nominal calculations](https://github.com/lyullee/h2physics/blob/main/docs/FORMULA_CONTRACT_CAMPAIGN.md) | 67 passing cases across 66 families | 30 model equations, 35 supporting calculations, one thermodynamic identity; 12 selected native cores excluded |
| [Extreme/boundary checks](https://github.com/lyullee/h2physics/blob/main/docs/EXTREME_CONTRACT_CAMPAIGN.md) | 108 passing cases across 66 families | Includes numerical, mapping and domain-edge checks of different depths |
| [Module connections](https://github.com/lyullee/h2physics/blob/main/docs/CONNECTION_CONTRACT_CAMPAIGN.md) | 72 normal families, 2 rejection-only, 2 blocked, 2 terminal | The final selected batch has 55 positive and 2 rejection-gate cases; historical deeper checks are identified |
| [Existing regression and representative runs](https://github.com/lyullee/h2physics/blob/main/docs/REGRESSION_REPRESENTATIVE_CAMPAIGN.md) | 50 selected original tests and 6 input-to-output examples passed | Basic selected regression/examples, not 78 complete operating envelopes |
| [Measured-data comparison](https://github.com/lyullee/h2physics/blob/main/docs/PHYSICAL_VALIDATION_CAMPAIGN.md) | Four conditional held-out comparisons | Calibration and evaluation data separated; full physical qualification remains unestablished |

The measured comparisons gave effective permeance mean relative errors of 2.15–4.06%, normalized hydride curve RMSE of approximately 4.49/4.86 percentage points, PEM polarization voltage RMSE of 23.1 mV, and a fixed-coefficient nozzle flow mean relative error of 29.8%. These are different metrics and physical quantities; they must not be pooled into one accuracy score. Missing conditions and parameter-identifiability limits are recorded in the [comparison report](https://github.com/lyullee/h2physics/blob/main/docs/PHYSICAL_VALIDATION_CAMPAIGN.md).

Known normal-connection gaps remain explicit: jet fire and outdoor dispersion have rejection-only evidence; underground storage is blocked by a native scalar-input compatibility issue; obstacle dispersion lacks an executed FDS runtime; biological and gasification results currently have no selected downstream consumer. These are not six interchangeable implementation omissions.

## Running checks

A small existing test selection for a core/thermo development environment is:

```bash
python -m pytest tests/test_core_thermo.py tests/test_electrochemistry.py tests/test_hydride.py tests/test_materials.py tests/test_reactions.py tests/test_hydraulics.py -q
```

Representative examples are in `examples/`. The six recorded basic representative runs use:

```bash
python -m pytest tests/test_representative_run_equipment.py -q
python -m pytest tests/test_representative_run_production_safety.py -q
```

Run those two suites in separate processes with their documented optional providers. Some research tests require independently acquired observations or installed native packages. Running every test from a core-only environment does not reproduce the recorded native campaigns. Use the per-campaign commands and source pins instead of treating skipped dependencies as passing evidence.

## Documentation and continuing the research

| Need | Entry point |
| --- | --- |
| Start using Python APIs | [Quickstart](https://github.com/lyullee/h2physics/blob/main/docs/QUICKSTART.md), [API guide](https://github.com/lyullee/h2physics/blob/main/docs/API.md), [public symbol index](https://github.com/lyullee/h2physics/blob/main/docs/PUBLIC_API_INDEX.md) |
| Detailed Korean instructions | [Korean overview](https://github.com/lyullee/h2physics/blob/main/README_KO.md), [user/research guide](https://github.com/lyullee/h2physics/blob/main/docs/USER_GUIDE_KO.md) |
| Choose model level and provider | [Model selection](https://github.com/lyullee/h2physics/blob/main/docs/MODEL_SELECTION.md), [catalog](https://github.com/lyullee/h2physics/blob/main/docs/MODEL_CATALOG.md), [architecture](https://github.com/lyullee/h2physics/blob/main/docs/ARCHITECTURE.md) |
| Reproduce measured comparisons | [Physical comparison report](https://github.com/lyullee/h2physics/blob/main/docs/PHYSICAL_VALIDATION_CAMPAIGN.md), [data qualification](https://github.com/lyullee/h2physics/blob/main/docs/DATA_QUALIFICATION.md), [source ledger](https://github.com/lyullee/h2physics/tree/main/research/data) |
| Understand changes and resume | [Development history](https://github.com/lyullee/h2physics/blob/main/docs/DEVELOPMENT_HISTORY.md), [research continuation](https://github.com/lyullee/h2physics/blob/main/docs/RESEARCH_CONTINUATION.md), [handoff](https://github.com/lyullee/h2physics/blob/main/docs/HANDOFF.md), [checkpoint](https://github.com/lyullee/h2physics/blob/main/docs/RESUME_CHECKPOINT.md) |
| Review limitations and extensions | [Progress evidence](https://github.com/lyullee/h2physics/blob/main/docs/PROGRESS.md), [implementation requirements](https://github.com/lyullee/h2physics/blob/main/docs/IMPLEMENTATION_REQUIREMENTS.md), [receiving-engine requests](https://github.com/lyullee/h2physics/blob/main/requests/README.md) |
| Prepare a public artifact | [Rights/provenance](https://github.com/lyullee/h2physics/blob/main/docs/RIGHTS_AND_PROVENANCE.md), [release readiness](https://github.com/lyullee/h2physics/blob/main/docs/RELEASE_SOURCE_READINESS.md) |

Local acquisition caches, native installations and detailed execution artifacts are excluded from distributions. Public scripts, source metadata and aggregate documentation provide the route to reproduce them. Exact source versions, parameter choices and data availability still matter.

## License, attribution and release boundaries

Original project code is licensed under **Apache-2.0**; see [LICENSE](https://github.com/lyullee/h2physics/blob/main/LICENSE) and [NOTICE](https://github.com/lyullee/h2physics/blob/main/NOTICE). External libraries, mechanisms, observations and publications retain their own terms. An optional import does not authorize bundling its source or data. Keep the original attribution and check the terms of any combined distribution.

Public releases exclude original reference documents, private inputs, raw/normalized external observations, native binaries, local environments and credentials. Comments and manuals are authored descriptions of implemented contracts and methods. Rewording alone does not establish rights clearance; primary scientific references, dependency license records and dataset-specific attribution remain necessary.

For a new issue or research result, include the selected callable/provider, package/native versions, parameters with units, input source/version, relevant clocks, exact command and original diagnostic. Preserve a failing case before changing coefficients or tolerances.
