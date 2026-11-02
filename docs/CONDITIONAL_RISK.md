# Native conditional risk with finite-source and exposure bindings

`h2physics.adapters.conditional_risk` connects existing finite source objects,
receptor/exposure records and explicitly supplied frequencies to the actual
optional Process Risk Consequence Toolkit0.1.0. That native engine owns single-
LOC branch aggregation, duplicate-credit/partition validation and calculation
receipts. The host does not implement another risk equation or derive frequency
from source mass, operating flow, alarms, consequence severity or model scores.

Every result remains conditional on the supplied source, harm and frequency.
It is not a qualified source/dispersion/fire chain, an independent physical
validation, an annual event probability or a complete facility QRA.

## Python objects and native installation

The native package is Apache-2.0 and remains separately installed; its source,
examples and coefficient tables are not bundled. Exact wheel/dependency and
installed-notice hashes are in `research/risk_dependency.toml`. The base native
package uses Pydantic; no dense-dispersion, HTTP or incompatible SLAB extra is
needed. The separate HyRAM exposure provider retains its GPL-3.0-only license.

```powershell
.venv\Scripts\python -m pip install --no-compile --target artifacts/native_risk_packages -r requirements/native-risk.txt
```

Choose the complete checked dependency profile in the receipt when reproducing
a run. Keep native targets separate from the core installation. The adapter
imports the native package only on request; base imports do not need it.

```python
from pathlib import Path
import sys

sys.path.insert(0, str(Path("artifacts/native_risk_packages").resolve()))

from h2physics.adapters.conditional_risk import (
    ConditionalRiskNative, ConditionalHarmBinding, RiskReceptor,
    RiskBindingEvidence, conditional_risk,
)

native = ConditionalRiskNative.from_installed()
risk_types = native.risk_module
context_types = native.contracts

# source is an existing IntervalMassSource with its original physical state.
# exposure is an actual probability-bearing result from HyRAMExposure.
harm = ConditionalHarmBinding.from_exposure(
    exposure, binding_evidence_id="declared-scenario-exposure-binding",
    origin=exposure.input.origin,
)
# Supply native risk_types.Frequency/Branch/RiskInput and
# context_types.Evidence/Context objects directly, with explicit values.
result = conditional_risk(
    native, native_request, native_context, source=source,
    receptor=risk_receptor, harm_bindings=branch_bindings,
    evidence=binding_evidence,
)
annual_harm_rate = result.native_output.annual_harm_frequency_per_year
native_receipt = result.native_receipt
```

The complete authored construction and executable composition are in
`scripts/check_conditional_risk.py`. Native Pydantic objects, host dataclasses,
source arrays and actual exposure/native results are retained. No user JSON,
file input or server is required. The native receipt function internally
normalizes its typed request; an additional direct native function call retains
the actual typed `RiskOutput`, which is cross-checked against the native receipt.
It is not relabeled as an output object recovered from a dictionary.

## Source, geometry, clock and provenance contracts

`finite_source_sha256` checks the actual `IntervalMassSource`, nested
`SourceLocation`, `ThermoState` and `PropertyBasis`, reapplying their original
physical contracts. It fingerprints actual interval masses/edges, location,
thermodynamic meaning, origin, evidence and termination. A source label alone
does not bind changed mass, frame, clock, state or isolation meaning. This is
structural/source admission, not a new EOS or independent source validation.

`RiskReceptor` requires ID, coordinate frame, three metre coordinates, exposure
clock, location evidence and resolved origin. The native case receptor and
source/receptor frames/clocks must agree. Actual computed exposure coordinates
must also match; matching labels or vector length is insufficient. No time
shift, recorder synchronization, spatial transform or source extension is inferred.
Source and exposure supports remain separate: a post-release exposure may have
a longer explicit window, without extending the finite release history.

`ConditionalHarmBinding` declares bounded probability, response model, source,
receptor/frame/clock/coordinates, exposure support, evidence IDs and origin.
`from_exposure` requires an actual probability-bearing supplied-exposure result
and owner-provided native replay audit before binding it. Replaced summary/model
values cannot claim the old retained native calculation. Original history,
selection, native dose/probit/CDF calls and their actual scalar outputs remain
accessible. Dose-only absorbed-flux diagnostics cannot supply a harm probability.
An explicit scalar declaration is also possible, but it must carry its own
model/evidence/origin and cannot claim a computed native exposure object.

`RiskBindingEvidence` separately declares the source binding, source-to-harm
assumption and branch partition. Equal source/field labels do not establish a
transport/fire calculation. All source-binding, receptor, partition, branch/
factor-basis and harm evidence references must resolve in the native context.
The finite mass source's own evidence ID and every native frequency evidence ID
must also resolve there, in addition to the separate source-binding declaration.
The native frequency/context identities must match. Evidence strings are
declarations and traceability references; the host cannot validate the underlying
scientific assertions or make a synthetic assumption into observed data.

## Native frequency and probability ownership

Supply an actual native `Frequency` with an explicit nonnegative LOC rate per
year, source/data/code digests, origin and evidence IDs. It is a rate; values
above1/year are not automatically invalid probabilities. No Poisson/time-horizon
conversion, occurrence frequency, component failure law or risk threshold is
invented here. The actual native class fixes its endpoint to loss of containment.

Native `Branch` objects declare mutually exclusive/exhaustive conditional branch
probabilities and their ownership IDs, conditional harm and optional explicitly
basis-qualified factors such as occupancy. The partition must sum to1. Credited
factor IDs cannot be duplicated within a branch or applied again after inclusion
upstream. Names/IDs alone cannot prove physical independence or discover a
renamed duplicate; the caller must justify the supplied factorization and
conditional probability bases. Occupancy factors affect native harm frequency,
not the unconditioned LOC rate. Do not apply a factor already included in harm.

Original native models are copied/revalidated from their current Python values;
frozen Pydantic instance identity alone does not admit `model_copy(update=...)`
that bypassed validation. The reviewed native version/code digest and actual
function/class/registry bindings are checked before and after evaluation.
Original request/context, source and computed-harm identities cannot change
during the calculation. No alternate backend or default frequency is substituted.

## Outputs, failures and scientific limits

`ConditionalRiskResult` retains original and independently owned typed native
request/context, the actual native `RiskOutput` and `Receipt`, original finite
source/hash, receptor, branch harm objects, assumptions and native engine.
Native source-context, branch, evidence and receipt diagnostics remain visible.
The result is issued only by the evaluation function and exposes `require_current()`;
issuance is one-use and bound to the evaluator's original objects, so
`dataclasses.replace()` cannot mint another receipt even when all fields are copied
unchanged. It rechecks request/context identity, finite-source content,
receptor/branch-harm bindings, native code, and agreement between typed output and
native receipt.
The annual-frequency property performs this check before returning its value.
Native complete-facility and physical-validation flags remain false.

`ConditionalRiskError` retains original inputs and source/receptor/harm objects,
the active admission/evaluation/audit stage and owned/native result/receipt when
returned, with the original cause. Missing physical objects, invalid partitions,
duplicate credit, missing evidence and changed computed output do not become
zero risk or a partial successful-case total.

The authored replay pairs a declared finite mass budget with an actual native
HEOS state and an independently supplied radiant-flux pulse. Actual HyRAM
exposure feeds the actual native risk engine. LOC frequency, branch, occupancy
and source-to-field linkage are explicitly unmeasured assumptions. Independent
rational/product tests and exact native receipt checks establish numerical/API
composition, not an experiment, a validated harm calibration, protection credit
or total-facility individual/societal risk. Native preferred-provider physical
failures remain rejected elsewhere in the project.

Primary native contract and source ownership:
[Process Risk Consequence Toolkit](https://github.com/lyullee/process-risk-consequence-toolkit),
[published0.1.0 metadata](https://pypi.org/pypi/process-risk-consequence-toolkit/0.1.0/json).
HyRAM exposure sources/calibration limitations are documented in NATIVE_EXPOSURE.md.
No native implementation, raw field data, private frequency database or
third-party prose/coefficient tables are copied into this module.

Reproduce the complete authored source/exposure/native-risk case after installing
the reviewed separate HyRAM target:

```powershell
.venv\Scripts\python -X utf8 scripts/check_conditional_risk.py --risk-packages artifacts/native_risk_packages --hyram-packages artifacts/native_hyram_packages
```

Use `--use-main-scipy` to preload the core environment SciPy before adding the
separate HyRAM target. Default isolated-target execution exercises the compatible
HyRAM SciPy profile. These are distinct recorded environments, not silent provider
fallbacks. The script preserves explicit assumptions and native failure evidence.
