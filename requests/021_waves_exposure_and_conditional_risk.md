# Native wave, exposure and conditional-risk continuation

## Ownership and actual current boundary

The host reuses reviewed Caltech SDToolbox/Cantera waves, HyRAM receptor response
and process-risk-consequence-toolkit conditional aggregation. Native algorithms
remain with their providers. No receiving repository was edited. These requests
specify missing capabilities and acceptance evidence, not completed functionality.

## SDToolbox wave API and observable solver states

Accept an actual owned Cantera phase and explicit mechanism/state evidence in
CJspeed, CJ_calc and postshock calls. CJspeed currently requires a mechanism file;
the host uses an ignored audited YAML bridge and checks the exported phase.
Provide an in-memory API retaining its source phase, owned copies and returned
phases without a caller-supplied filesystem path.

Expose native CJ density/search candidates, fit bracket and convergence status,
iteration/tolerance controls, and all sound-speed transformed trial states. The
host cannot currently inspect the internal CJspeed phase objects or every native
sound perturbation. Native fit R-squared alone is not convergence or domain
qualification. Supply versioned immutable artifacts and source/notice hashes.
Keep frozen-shock and equilibrium-CJ states distinct, with explicit upstream
velocity/reference frame, thermochemistry, composition, energy reference and
allowed phase/temperature/pressure domain.

Acceptance: constant-cp inert shocks over several Mach numbers; independent
mass/momentum/Hugoniot/element closure; equilibrium sound/sonic residual;
owned/source phase invariance; global search/tolerance/perturbation refinement;
all internal states admitted or original failure retained. A restricted H2/O2/N2
mechanism without NOx is not general high-temperature qualification. ZND, DDT,
initiation and geometry-resolved blast remain separate model levels.

## HyRAM conditional exposure contracts

The native peak-only pressure models need an API that does not require or test
unused impulse. Current convenience behavior returns zero for irrelevant zero
impulse even when the selected peak-only function returns a nonzero probability.
Expose model-specific required inputs and original native response values.

Keep incident W/m2 distinct from absorbed heat, gauge peak from absolute
pressure, and signed trace from explicitly selected positive-phase impulse.
Transient dose accumulation needs explicit calibration/additivity/recovery
scope, model identity, normal distribution mean, input units and evidence.
Publish source/version and original calibration provenance with reusable rights.
Do not promote a probability computed from a supplied history to verified
source-to-receptor transport or independently validated human response.

Preserve an owner verification API that binds actual input, native functions,
arguments, raw scalar result, model/mean and evidence. A dataclass/model copy
with a replaced probability or response model must fail replay verification.
Only active quadrature work entries are deterministic; unused native work-array
tails must not become scientific input. Check zero exposure, missing samples,
negative flux, finite range, linear/held histories, positive pressure impulse
and model-specific absent-impulse rejection.

## Native conditional-risk direct Python execution

Offer one native in-memory call returning the actual typed RiskOutput and
reproducible Receipt together. Current host must call native aggregation and the
native receipt API separately, then compare their outputs; receipt normalization
internally serializes values. Preserve original and owned typed request/context,
strict revalidation of model_copy updates, actual native output and failures.
No new server or required user wire format is requested.

Frequency must remain an explicitly evidenced annual LOC rate, separate from
branch probability, conditional harm and occupancy. Accept exclusive exhaustive
branch partitions and explicit factor/credit identifiers. Reject duplicate
upstream credit, incomplete partitions, nonfinite probabilities, context/rate
identity mismatch and unsupported independence. A frequency database needs
source asset/population/operating exposure, event definitions, censoring,
uncertainty and transfer applicability; do not infer rates from dose or alarms.

Physical coupling must bind the actual finite source state/location/basis,
clock and support, actual receptor coordinates/frame, verified native computed
harm/model, and an explicit source-to-field assumption or accepted transport
chain. Source and exposure time windows stay distinct. Acceptance includes
replaced probability/model rejection, absent/invalid source state rejection,
coordinate/clock mismatch, retained native failures and an independently checked
single-case product. Facility IR/F-N, common-cause/dependence, multiple sources
and independently qualified source-field-risk chains remain future scope.

## ELVHYS BLEVE data clarification before physical comparison

Dataset DOI10.18710/M5LOLM describes LH2 membrane-rupture/BLEVE trials. It does
not supply a homogeneous premixed reacting upstream state or measured CJ speed;
no direct detonation validation is admissible from the current attachments.

Request per-sensor absolute/gauge definitions for p1/p3, calibration/uncertainty,
DAQ channel mapping and clock origin/synchronization, actual 10us versus stated
10kHz sampling, temperature T2e dummy flags and duplicate time interpretation.
Preserve original invalid/zero/negative observations and reversible encoding.
For BLEVE source/pressure comparison supply fill mass/level, phase/temperature
profiles, geometry/diaphragm history, rupture timing, surroundings/ignition and
sensor observation kernels. Separate all source-to-field hypotheses and declare
held-out runs before parameter fitting. Do not repair inconsistent clocks,
change pressure references or substitute a nominal premix without evidence.
