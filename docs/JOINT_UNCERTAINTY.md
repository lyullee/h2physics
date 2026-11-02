# Explicit dependent inputs

`h2physics.research.joint_uncertainty` composes the existing SciPy-backed QMC
design and uncertainty propagator with a caller-supplied joint transform.
`JointParameterSpace` declares the independent latent space, physical variables
and admission bounds, joint-law ID, dependence evidence and transform revision.
The transform receives named latent values and returns exactly the declared
physical variable names. Out-of-domain outputs fail before model evaluation.
Each transformed value must be one finite real numeric scalar. Boolean values and
arrays, including single-element arrays, are rejected instead of implicitly coerced.

`joint_qmc_design()` prepares the latent design. `propagate_joint()` evaluates the
existing `UncertainModel` with an explicit physical scenario ID. Each retained
`JointCaseResponse` contains latent inputs, transformed inputs and the original
model response. `JointEvaluationError` preserves the original cause and the
existing propagation error with its completed prefix. Samples are never replaced
after physical failures. The transform defines dependence; the API does not infer
it from a correlation coefficient or automatically generate a copula. Independent
Sobol interpretations do not transfer to dependent physical inputs. Parameter
samples do not establish event frequency.

`scenario_uncertain_model()` constructs an existing `UncertainModel` from a
caller scenario factory, explicit output reader and optional selected target nodes.
It runs the existing `OperationalScenario` and preserves that original execution
inside `ScenarioUncertaintyResponse`. Binding, execution and output-reading errors
retain their stage and original scenario error or completed execution.

`JointPropagationResult` is issued only by a completed `propagate_joint()` call.
It verifies that every retained response row matches the exact latent design row,
the corresponding `JointCaseResponse`, admitted joint bounds and the original
model outputs. `require_current()` and `summarize()` recheck that retained lineage
without rerunning user callbacks. A copied result cannot relabel its scenario ID
and reseal the prior propagation as a new receipt. This protects result provenance;
it does not qualify the caller's dependence law or infer covariance.

The nested `PropagationResult` is also issued only by the shared native propagator.
It verifies that each result row matches its exact sampled design coordinate and
declared output columns; direct construction or dataclass replacement cannot
fabricate a propagation receipt without a completed QMC call.

This is implemented but unexecuted. The deferred joint-input contract uses the
existing model-selection environment. No scientific calculation ran locally.

`JointPropagationResult` lineage sealing covers ordinary function defaults and
closure cells, plus ordinary bound-method/callable-instance attributes and slots.
Changing this visible callback configuration makes `require_current()` fail. Opaque
external state is represented by identity; callers must increment the declared
transform revision or model evidence identity when external dependencies change.

## Facility accident and consequence rows

`h2physics.adapters.facility_accident_uncertainty.facility_accident_consequence_uncertain_model`
adapts the existing joint-input model to the accepted facility accident chain and
receiving consequence evaluator. Per sample, the caller supplies a typed chain and
evaluator; an output reader maps the accepted `FacilityAccidentConsequenceRun` to
the declared scalar `Variable` outputs. The returned object is an ordinary existing
`UncertainModel`, so `joint_qmc_design()` and `propagate_joint()` remain the only
sampling and propagation machinery.

Each row retains the exact chain, source/dispersion handoff, consequence receipt,
and original reader response. A `require_current()` freshness check on raw model
responses is propagated through `JointPropagationResult.require_current()`. The
adapter does not create consequence laws or exposure metrics. Output quantities,
units, basis, response model, distribution, dependence, deterministic reset and
statistical scope remain caller supplied. Samples are not incident frequencies.
The `facility-accident-source-bound-uncertainty` case is a synthetic acceptance
contract registered in both Hangang and Nurion plans; it is not executed yet.
