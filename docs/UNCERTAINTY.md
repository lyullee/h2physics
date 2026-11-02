# Independent-input propagation and native sensitivity

`h2physics.uncertainty` connects declared continuous input distributions to any
Python physical-model callable. SciPy owns scrambled Sobol sampling and the
Saltelli variance-index estimator. Existing hydrogen models retain their EOS,
reaction, equipment and integration responsibilities. No sampling or sensitivity
algorithm, physical solver, parameter fit or annual accident frequency is copied
into this module.

Install `h2physics[uncertainty]` for the native SciPy>=1.15 Generator interface.
Core imports can retain the broader core SciPy requirement; invoking this level
on an older engine rejects explicitly. The checked engines are1.16.3 and1.18.1.

## Input law, physical admission and model identity

`ParameterDistribution` combines an observation `Variable` (name, quantity,
unit and reference basis), a frozen native SciPy continuous distribution,
distribution/source IDs, resolved `Origin` and finite physical admission bounds.
Its immutable `native_definition_snapshot` retains native version/class/name,
arguments, keyword parameters and support. A SHA binds those definitions; reuse
rejects changed native distribution arguments/support. The mathematical support
can be unbounded, while the physical admission remains explicit. A sampled
outside-domain point fails with its original quantile; no truncation, clipping,
resampling or change of probability law is inferred.

`IndependentParameterSpace` requires a source for the independence assumption.
It supports independent marginal distributions only. Fitted-parameter covariance,
time correlation, conditional laws, constrained compositions and posterior
dependence cannot be represented by independently sampling their marginals.
Those need a separately justified joint law/analysis. Distribution metadata and
input bounds are not evidence that measured uncertainty has been identified.

`UncertainModel` declares output `Variable` objects and `UncertaintyEvidence`:
model identity/revision, deterministic reset assumption, statistical scope and
origin. Its callable receives an immutable `{parameter_name: scalar}` mapping
and returns exactly the declared output mapping, or `ModelOutput(values, raw)`.
`raw` preserves the original caller-supplied result/object without copying native
engines. Raw mutable objects keep their usual ownership; the host separately
copies input/output scalar snapshots. Native solvers with memory must be reset
or independently constructed for each case. No IID simulator-noise or reset
guarantee is created merely by providing the evidence ID.

## Python composition

```python
from scipy import stats
from h2physics.core import Origin
from h2physics.observations import Variable
from h2physics.uncertainty import (
    IndependentParameterSpace, ModelOutput, ParameterDistribution,
    UncertainModel, UncertaintyEvidence, independent_qmc_design,
    propagate, sobol_sensitivity,
)

space = IndependentParameterSpace((
    ParameterDistribution(Variable("pressure", "pressure", "Pa", "absolute"),
        stats.uniform(loc=1e7, scale=2e7), "authored-pressure-law",
        "synthetic-verification", Origin.SYNTHETIC, 1e7, 3e7),
    ParameterDistribution(Variable("temperature", "temperature", "K"),
        stats.uniform(loc=280., scale=50.), "authored-temperature-law",
        "synthetic-verification", Origin.SYNTHETIC, 280., 330.),
), "authored-independence-assumption", "verification-domain")

# provider is an existing native-backed PropertyProvider with fixed fluid/spin.
def physical_case(p):
    state = provider.state_pt(p["pressure"], p["temperature"])
    provider.basis.require_compatible(state.basis)
    return ModelOutput({"density": state.density_kg_m3}, raw=state)

model = UncertainModel(physical_case,
    (Variable("density", "density", "kg/m3", provider.basis.reference_id),),
    UncertaintyEvidence("native-hydrogen-state", "declared-source-revision",
        "stateless-native-PT-query", "authored-inputs-not-measured-uncertainty",
        Origin.SYNTHETIC))
design = independent_qmc_design(space, power=12, seed=42)
result = propagate(design, model)
summary = result.summarize((.05, .5, .95))
indices = sobol_sensitivity(space, model, power=12, seed=81)
```

The values and independence assumption above are original numerical fixtures.
They are not measured operating distributions or a qualified facility envelope.
Replacing the provider/callback composes existing tanks, transport or process
models through their Python APIs without requiring JSON, files or a service.
Model evaluations are serial and deterministic in this level; callers can run
independent complete designs in separate local processes. Shared native mutable
state is not implicitly made thread-safe.

## Caller-defined joint scenarios

`JointScenarioSpace` is the explicit route when the inputs are dependent,
conditional, constrained, or otherwise cannot be represented by independent
marginals. Each `JointParameterDomain` declares the output variable, source,
origin, unit/reference basis, and finite physical bounds. The caller supplies a
Python function of `(numpy.random.Generator, count)` that returns a finite
`(scenario, parameter)` array in the declared order. Its `sampler_id`, revision,
source, dependence evidence and physical bounds become part of the space identity.
The Python function's bytecode and simple captured/global definitions are also
fingerprinted; opaque callable objects are rejected, while a changed captured
definition invalidates the space.

```python
import numpy as np

from h2physics.uncertainty import (
    JointParameterDomain, JointScenarioSpace, joint_scenario_design,
    propagate_joint,
)

def sample_joint(rng, count):
    shared = rng.random(count)
    return np.column_stack((shared, 1.0 - shared))

space = JointScenarioSpace(
    parameters=(fraction_a_domain, fraction_b_domain),
    sampler=sample_joint,
    sampler_id="authored-copula-or-constraint-map",
    sampler_revision_id="revision-1",
    dependence_evidence_id="caller-source-for-dependence",
    source_id="caller-source-for-joint-law",
    space_id="facility-scenario-family",
)
design = joint_scenario_design(space, count=4096, seed=42)
joint_result = propagate_joint(design, model)
joint_result.require_current()
```

Sampling uses NumPy `Generator(PCG64(seed))`. Every sampled row and its stable
scenario identity are retained. `propagate_joint` binds one deterministic model
response to each row; a failure raises `UncertaintyEvaluationError` with the
failed scenario ID, actual input row, original cause and completed prefix.
Failures are never dropped or replaced. The API does not fit dependence,
validate the caller's probability law, infer event frequencies, or provide
Sobol indices for dependent inputs. A seed reproduces draws only while the
declared sampler definition and NumPy behavior remain compatible; the stored
rows remain the primary replay record.

`validation/cases/uncertainty_joint_scenarios.py` declares a deferred synthetic
contract for exact anti-correlation, seed replay, row identity and failure
retention. It is not registered in a shared HPC plan and has not been executed.

## Results and acceptance

Native QMC draws all `2**power` points with scrambling and a mandatory integer
seed. It does not thin/skip a point or optimize away low-discrepancy coordinates.
`ParameterDesign` retains actual engine, unit-cube coordinates, transformed
values and source identity. Matching shape cannot bind different quantiles.
Coordinate fingerprints are checked before and after propagation. Callbacks use
an independent batch copy, so a rewritten original design is rejected with the
original batch and completed actual cases instead of returning stale provenance.
The default point/evaluation budget is1,000,000 and can be explicitly changed;
requests beyond it fail before allocation. This is a computational budget.

`PropagationResult` retains actual model/design and every `CaseEvaluation`, with
input/output/raw results and call indices. `summarize` gives unweighted sample
mean, population variance (`ddof=0`) and linear sample quantiles. These are
quadrature estimates under the supplied law, not an experimental confidence
interval or an annual risk. Nonfinite/underflow summary arithmetic is rejected.
Use independent scrambles and increasing base2 resolution for error assessment.

`SobolSensitivity` retains the actual native result, all evaluations and copied
native input/output batches. First/total arrays always use output-by-parameter
shape. Native centering cannot overwrite copied physical responses. Finite
negative estimates and non-unit sums remain visible; no clipping/renormalization
is performed. A constant response has no variance denominator: the host mask is
false and indices are NaN, while the original native zero convention remains in
`native_result`. Varying responses whose variance underflows and extensive
overflow are rejected rather than being accepted as zero sensitivity.
Sensitivity receipts are issued only after the native Sobol analysis completes;
direct construction, dataclass replacement, and post-issuance edits to index or
batch data are rejected when the receipt is checked.

Native SciPy1.16.3/1.18.1 have an actual single-input/single-output squeeze/item-
assignment failure. The completed cases and native cause are retained. No dummy
output/input or replacement estimator is inserted. Single-input propagation and
single-input analysis with multiple actual outputs remain available. An upstream
shape fix is a receiving capability; the native result's optional bootstrap also
has its own native randomness/assumptions and is not a seeded host confidence API.

`UncertaintyEvaluationError` retains failing parameters, actual callable/space,
completed prefix, batch coordinates, propagation design and native result when
one was returned. If returned response validation fails, `failed_raw`,
`failed_response` and `failed_output_values` preserve the actual raw object,
response and a separate value mapping even when a numeric field is invalid.
`UncertaintyDesignError` retains native engine, original quantiles and transformed
points when available. Failed cases are not dropped to produce a conditional
successful-subset distribution. The original physical/native exception survives
as cause. A new scientific failure policy requires a new explicit analysis.

## Verification and remaining qualification

`scripts/check_uncertainty.py` compares native statistics with original additive/
product analytic limits and a smooth actual native-HEOS hydrogen inventory.
Independent tensor quadrature and two base2 resolutions check moment/index
convergence. Input distributions, gas volume and independence are authored.
This checks composition and numerical behavior, not measured sensor covariance,
material parameter uncertainty, calibrated event probabilities, structural model
uncertainty or a qualified full facility consequence ensemble.

Primary statistical APIs and mathematical sources:

- [Native SciPy sensitivity](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.sobol_indices.html)
- [Native SciPy Sobol engine](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.qmc.Sobol.html)
- [Sobol variance decomposition](https://doi.org/10.1016/S0378-4754(00)00270-6)
- [Saltelli et al. total-effect estimator](https://doi.org/10.1016/j.cpc.2009.09.018)
- [Native hydrogen EOS](https://doi.org/10.1063/1.3160306)

Native SciPy/NumPy and separately installed CoolProp retain their licenses and
implementations. No source implementation, coefficient table or external raw
dataset is bundled in the host. Actual source hashes and runtimes are recorded
in `research/uncertainty.md`.
