# Research continuation and reproducibility

This guide supports a new checkout without the development conversation or local run cache. Read [Development history](DEVELOPMENT_HISTORY.md) for decisions and evidence, [Architecture](ARCHITECTURE.md) for ownership, and the focused model manual before changing a calculation.

## 1. Establish the starting revision

Record these outputs before changing source:

```text
git rev-parse HEAD
git status --short
python --version
python -m pip --version
```

Use Python 3.12 in an isolated environment. Keep raw measurements, credentials, native source trees, tables and execution receipts outside tracked content. The ignored `data/raw/`, `data/processed/` and `artifacts/` directories are suitable local locations. Do not commit them just to make a workstation-specific test pass elsewhere.

The catalogue's 82 families and the staged campaigns' 78 topics are different counts. Neither means every optional provider is installed or experimentally qualified. Read [Catalogue](MODEL_CATALOG.md), [Public API index](PUBLIC_API_INDEX.md) and [Exact model selection](MODEL_SELECTION.md).

## 2. Install only the needed capabilities

Create and activate a virtual environment using the platform's normal activation command:

```text
python -m venv .venv
python -m pip install --upgrade pip
python -m pip install -e ".[thermo,data,hydraulics,test]"
```

The existing Conda definition is an alternative:

```text
conda env create -f environment.yml
conda activate h2physics-py312
```

An editable install supports development, not clean-wheel verification. Test a release wheel in a separate environment without the source checkout on its import path.

Native engines remain separate dependencies. Read [Dependency decisions](DEPENDENCIES.md), the relevant `requirements/` file and model manual. Some providers require an exact inspected revision and compatible runtime. A missing provider is not permission to insert a fake module, copy a foreign solver or bypass admission. Preserve actual module/version identities where an adapter requires them.

Production thermophysical paths use CoolProp or qualified provider-derived tables. Explicit ideal/constant-property closures are analytical verification fixtures, not fallback production providers. Tables need saved domains, phase gates and direct-provider error evidence.

## 3. Choose the evidence question

| Question | Suitable check | Misleading shortcut |
| --- | --- | --- |
| Input contract | Relevant diagnostic at the actual public boundary | Any unrelated dependency/solver error |
| Equation implementation | Independent analytical answer or conservation relation | Same implementation used as its own oracle |
| Boundary numerics | Finite valid limits or explicit domain refusal | Nominal example renamed as an extreme |
| Module connection | Genuine result into the actual consumer | A generic constructor or forged issued result |
| Regression | Existing selected behavior on the changed source | Dependencies skipped and counted as passes |
| Representative run | Declared input through structured finite final output | Import-only success |
| Physical prediction | Matched measurements with separated evaluation data | Fitting and evaluating the same curve |

Connection checks currently focus on basic delivery, units, material identity and clocks. Do not automatically reopen a deep mutation, precision or facility-wide campaign. Existing native engines' internal physics is outside the independent host-model validation scope.

## 4. Start with the recorded basic regression

For small deterministic runs, disable unrelated auto-loaded pytest plugins and set numerical-library thread counts to one. Use `MPLBACKEND=Agg` when optional native imports use plotting. Each focused report lists the actual environment and prerequisites.

The historical 50-case regression used eight complete small files and eight named tests. This exact selection is reproducible from the project root:

```text
python -m pytest -q tests/test_core_thermo.py tests/test_electrochemistry.py tests/test_hydride.py tests/test_materials.py tests/test_reactions.py tests/test_hydraulics.py tests/test_observations.py tests/test_units_loaders.py tests/test_thermochemical.py::test_finite_carrier_closes_with_explicit_steam_and_separate_hot_product_exports tests/test_thermochemical.py::test_heat_only_stages_are_explicit_and_do_not_invent_a_reaction_or_heat_recovery tests/test_photochemistry.py::test_discrete_lines_use_exact_photon_energy_and_explicit_si_amount tests/test_photochemistry.py::test_finite_batch_reuses_stoichiometry_and_explicit_isothermal_energy_requirement tests/test_finite_hydride.py::test_zero_kinetics_keeps_both_finite_inventories_and_energy tests/test_finite_hydride.py::test_real_gas_isothermal_mode_preserves_native_inventory_and_thermostat_heat tests/test_uncertainty.py::test_propagation_preserves_raw_objects_and_declared_response_order tests/test_uncertainty.py::test_qmc_summary_uniform_linear_moments_and_explicit_quantiles
```

Run the representative suites in separate processes so optional provider imports do not share process state:

```text
python -m pytest tests/test_representative_run_equipment.py -q -o junit_family=xunit1
python -m pytest tests/test_representative_run_production_safety.py -q -o junit_family=xunit1
```

[Recorded inputs and outputs](REGRESSION_REPRESENTATIVE_CAMPAIGN.md) cover six examples. They are not 78-family end-to-end qualification. If a new checkout fails a prerequisite, record the source/environment mismatch instead of claiming the historical result applies.

## 5. Recreate larger campaign evidence only when needed

These selected campaigns are not prerequisites for every documentation edit.

### Input rejection

Run the three `tests/test_input_contract_*.py` suites using the [input report](INPUT_CONTRACT_CAMPAIGN.md). The recorded result was 162 cases across 78 families. Actual native constructors are dependencies; an unavailable package is not a successful input refusal.

### Nominal calculations

Run the three `tests/test_formula_contract_*.py` suites in separate processes. Reconcile XML with `scripts/summarize_formula_contracts.py`. Historical scope: 67 cases, 66 families, including supporting arithmetic and one thermodynamic identity. The 12 excluded selected native cores are not passes; an identity is not independent EOS validation.

### Extreme and connection campaigns

The historical runner filename supports both stages:

```text
python scripts/run_extreme_contracts.py --stage extreme --output-dir artifacts/extreme-replay
python scripts/run_extreme_contracts.py --stage connection --output-dir artifacts/connection-replay
```

Use an empty output directory. The runner preserves logs, XML, source hashes, return codes and bounded timeouts. `--lanes` selects existing independent lanes when a completed expensive result can be reused. Inspect `--help` for supported names.

Parse actual XML paths with `scripts/summarize_extreme_contracts.py` or `scripts/summarize_connection_contracts.py`. Family reconciliation needs the scope record produced by the input campaign; use `--scope` when it is not at the historical location. Inspect positive connection counts separately from rejection-only checks.

Preserve failed, interrupted and completed receipts separately. Partial pytest dots, an uncollected process outcome, queue admission or source transfer are not passes. Results from old source pins do not automatically cover a new worktree.

## 6. Resume the six connection exceptions precisely

| Path | Next required evidence | Keep unchanged |
| --- | --- | --- |
| Jet fire to exposure | Genuine admitted flame/radiation output under documented source conditions | No forced success flag, fake field or relaxed radiation gate |
| Outdoor dispersion | Accepted preferred-provider output in its qualified runtime | No automatic fallback or version spoofing |
| Underground to compressor | Receiving scalar CoolProp compatibility repair and a real successful native withdrawal | Native units, state/enthalpy ownership and accepted clocks; [request 038](../requests/038_uh2sc_coolprop_scalar_compatibility.md) |
| Obstacle dispersion | Supported real FDS executable and calculated output | Export/input-deck creation alone is not field delivery |
| Biological output | A separately specified real consumer if a use case needs one | Do not invent a consumer merely to reach a count |
| Gasification output | The same explicit use-case decision | A terminal result is not absent implementation |

The [connection report](CONNECTION_CONTRACT_CAMPAIGN.md) lists actual positive paths and numerical limitations. For a missing native capability, preserve the receiving revision and write a concrete request rather than introducing a duplicate local solver.

## 7. Reproduce measured-data comparisons

All four recorded comparisons remain conditional:

| Target | Fixed separation | Current applicability |
| --- | --- | --- |
| Effective permeance | Calibrate 350/450°C; evaluate whole 400°C curves | Pure hydrogen, supported Pd specimens, feed 1.5–5 bar absolute, permeate 1 bar absolute |
| Hydride kinetics | D/E/F/G calibration, H evaluation | Source-normalized fraction under mean forcing, not absolute capacity or vessel thermal history |
| PEM losses | First protocol curves calibrate, second evaluate | Same-cell voltage losses with an uncertain reaction-temperature proxy |
| Gas nozzle | Calm four-mm low-flow calibration, high-flow evaluation | Fixed coefficient transfer with ambient temperature as a gas-temperature proxy |

Acquire exact source versions using their primary metadata, grants and checksums. `research/data/` contains source records; [Physical comparison](PHYSICAL_VALIDATION_CAMPAIGN.md) explains attribution and limits.

```text
python scripts/validate_material_experiments.py --acquire
python scripts/validate_storage_experiments.py --archive data/raw/hydride-kinetics-measured-holdout/v1.0/hydride-kinetics-v1.zip
python scripts/validate_electrochemical_experiments.py
python scripts/validate_nozzle_experiments.py
```

Acquire the storage ZIP and existing PEM/HyTunnel assets separately through their source records. Public scripts do not redistribute original observations. Do not execute or copy bundled author model code merely because it shares an archive with data. The hydride loader selects measurement curves/condition summaries and excludes author-fitted constants and neural-network output.

Keep all held-out rows, large residuals and actual training-support flags. Correct a genuinely mismatched initial condition consistently in both partitions and preserve the previous result. Do not tune model choices, bounds or acceptance thresholds in response to evaluation error and continue to call the same data independent evaluation.

The approximately 30% nozzle transfer error is a finding, not a reason to remove measurements. Audit actual gas temperature, pressure tap/losses and coefficient applicability. Hydride and electrochemical estimates at bounds indicate identification limits; they are not measured material properties. Different metrics and dependence structures must not be pooled into a single accuracy percentage.

## 8. Minimum receipt for new research

Record these next to each result:

1. Commit or source hash set, command and Python/native environment.
2. Family, level, provider, purpose and admitted domain.
3. Parameter values/units and measured, calibrated, authored or reconstructed origin.
4. Dataset/version, creators, grant, metadata URL and file hashes.
5. Clock, absolute/gauge pressure basis, carrier, phase and caloric-reference choices.
6. Calibration/evaluation partition and known measurement dependence.
7. Completion/failure, actual counts, metrics and retained rejected rows.
8. Numerical settings or acceptance criteria chosen independently of favourable results.
9. Missing conditions and conditional inferences.
10. Source/environment changes after execution and the replay needed.

Public summaries contain original aggregates and methods. Per-row data, restricted assets and machine-local details stay ignored. JSON receipts are execution artifacts, not a required application interface.

## 9. Repair or extend the correct layer

Inspect the current callable and manual before declaring code missing. A new model level needs distinct physics or resolution; ordinary parameter variation should reuse the existing interface.

For a repair, preserve the failing public input/result, then decide whether the owner is a fixture, adapter, source interpretation, numerical control or external engine. Change only that layer. Run affected original checks and an ordinary positive path; expand only when the change or a remaining concern warrants it. Update APIs, scope notes and receiving requests with the source pin.

Keep provider roundtrip tolerance separate from issued-result integrity. A fresh flash can differ by ulps; an already issued result remains bound to its original content. A blanket tolerance must not conceal changed phase, material or energy reference.

## 10. Public release preparation

Prepare the actual intended tree. Include original code, manuals, tests, replay scripts and source metadata. Exclude raw assets, native package copies, local credentials and generated caches. `.gitignore` does not remove already tracked/staged content, and a safe working file does not erase an unsafe staged version.

Useful local commands are:

```text
python scripts/audit_public_tree.py
python scripts/audit_document_links.py --help
python -m build
python scripts/release_audit.py
```

Inspect each tool's actual options. Content checks detect common forbidden artifacts/markers; they are not legal clearance or exhaustive textual originality proof. Keep independent scientific attribution and dependency notices. Equations, data, figures, implementation code and written explanations have different rights scopes.

Install the new wheel in a clean environment and run the README import plus one or two ordinary examples. Source-tree execution does not establish package installation. Optional providers should be described as separate prerequisites and fail clearly when unavailable.

Record publication URLs, archive hashes, version and DOI only after the service confirms them. A GitHub repository, PyPI upload and Zenodo record are separate publication events. Do not publish success badges or identifiers that have not actually been issued.

## 11. Research priorities after this checkpoint

These are options, not automatically running jobs:

1. Obtain pressure references, time units, actual reaction/gas temperatures and measurement uncertainty from primary owners.
2. Use independent capacity/equilibrium measurements before interpreting fitted hydride parameters as physical properties.
3. Resolve activation-parameter identifiability before reporting electrochemical optimizer bounds as material constants.
4. Re-examine nozzle transfer with actual source state/loss information; retain the present discrepancy.
5. Close concrete receiving-runtime blockers before claiming positive paths.
6. Define application-specific acceptance criteria separately if a facility study is requested.

Recording a demonstrated external/data blocker is meaningful progress. Repeated unchanged rejected runs do not increase validation coverage.
