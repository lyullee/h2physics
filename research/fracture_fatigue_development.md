# Finite fracture/fatigue development checkpoint

Status: **implemented_unverified**. Development only; native calculations, local
pytest, numerical checks, benchmarks, examples and deferred case handlers were not
executed. The user explicitly deferred testing to parallel Nurion execution.

The implementation reuses actual optional HELPR2.1.0 constitutive calls, caller
mode-I SIF geometry and the existing SciPy integrator. It adds no diffusion/EOS,
growth-rate equation, pressure-to-stress formula or hydrogen material coefficient
database. Native objects/results and original failure causes remain inspectable.
The complete Python contract and physical limits are in FRACTURE_FATIGUE.md.

## Inspected native owner

Official source: https://github.com/sandialabs/helpr

Pinned revision: ae12d20b6608123af41dd9d5f70db6b6547fece5. Source pyproject version2.1.0;
Python>=3.9; dependencies matplotlib/numpy/scipy/pandas/xarray/netcdf4. License
BSD-3-Clause, copyright NTESS2023–2025. Source was obtained only for read-only
inspection under ignored artifacts/fracture_provider_review/helpr; it was not
installed, imported or copied into a public host package.

Inspected actual API:

- `helpr.physics.crack_growth.CrackGrowth(environment,growth_model_specification)`.
- `.calc_change_in_crack_size(delta_n,delta_k,r_ratio,cycle_index=0)` with crack
  increment m and DeltaK in MPa*sqrt(m).
- Native `paris_law`, `code_case_2938`, `g_202006` dispatch paths and the actual
  `EnvironmentSpecification` native fugacity/reference inputs.
- Environment T bounds230–330K. The H2 argument is bounded0–1 despite a docstring
  percent label. Public adapter chooses explicit mole fraction and validates
  compatibility; no factor100 ambiguity is hidden.
- Native `LifeAssessment` is pipe/stress-state/crack-shape specific. Generic
  geometry callbacks use native constitutive calls plus host SciPy composition;
  whole native trajectory reuse is not claimed.

Source fingerprints are in fracture_dependency.toml. No published branch
coefficient/table, source implementation or native worked example is in host code.
The original host example uses synthetic independently authored values and an
analytic geometry. It is neither a calibrated alloy nor a validated H2 design rule.

Primary sources inspected: official HELPR site/docs/source; Sandia hydrogen
materials references; Paris/Erdogan1963 publisher metadata/abstract. These support
API/model context, not missing experimental coefficients or regulatory conformity.
Full-paper/standard tables were not acquired or reproduced.

## Candidate rejected without runtime execution

PyPI py_fatigue latest2.1.1 (2026-06-09), wheel102194B, was downloaded under ignored
artifacts and checked against the publisher SHA. Actual wheel LICENSE is GNU GPLv3
and metadata classifier says GPLv3; license-expression fields are null. Metadata
requires Numba>=0.61,<0.66 on Python<3.14, so it cannot share the parent's explicitly
pinned newer thermal Numba profile without separate resolution. No candidate was
installed or imported.

Static source evidence identifies two limitations, not reproduced runtime defects:
`get_crack_growth`/`get_geometry_factor` hard-code INF_SUR_00 and HOL_CYL_01; no
arbitrary SIF callback is accepted. `CalcCrackGrowth.calc_crack_depth` returns an
array excluding its final updated depth while `final_cycles` sums input-cycle
entries through the returned depth count. That endpoint/index correspondence
needs an actual future native audit before treating it as a finite terminal state.
No host last-step repair, fake native field or alternate geometry-ID trick is used.

## Prepared execution and remaining decisions

The four metadata cases cover synthetic independent finite-growth/event limits,
native H2 point calls and retained negative/arrest cases. Their handlers run only
when invoked by the cluster framework. They return ValidationOutcome from actual
execution, never a cached local pass. Before Nurion execution the isolated HELPR
profile, complete transitive rights/runtime lock and parent case API must be checked.

Numerical trial extensions are explicitly caller-declared; insufficient geometry
or DeltaK range must remain a retained failure. Event roots, native return units,
near-zero rates, source/method mutation, missing clocks, material bounds and
step/tolerance convergence need real execution. SciPy's unreturned internal solver
on RHS exceptions remains unobservable; completed OdeResults and last trial/raw
native calls are retained instead of invented accepted steps.

Data requirement: matched-alloy da/dN versus DeltaK, R, pressure/fugacity,
temperature, frequency/waveform and surface/microstructure history, plus geometry/
stress-intensity and toughness evidence. Existing embrittlement tensile/ductility
compilation is not automatically such a curve. No measured validation, life
prediction qualification, inspection interval or facility rupture probability is
claimed. No local test/native timing exists at this checkpoint.

Static-only preparation: the three new Python files were parsed with the standard
AST parser; the receipt was parsed with tomllib. Ruff lint and formatting were
applied. These operations did not import/execute the adapter, native provider,
example or validation handlers. Runtime validation remains pending irrespective
of a clean syntax result. Final source hashes are reported at handoff separately
to avoid a self-referential report hash.
