# Oxygen-room, thermal physiology, learned monitoring and cold-room evidence

## Current ownership and explicit remaining scope

The host now composes the existing native Cantera finite-volume/nozzle owner,
actual pythermalcomfort JOS3 and the user's actual Process Monitoring Toolkit.
ELVHYS4.2 version1.1 is fully acquired/inspected. No receiving repository or
native implementation was edited. These requests describe missing capabilities
and acceptance evidence; writing them does not implement or validate them.

## Native finite room, source and observation boundaries

Retain actual phase factories/objects and exact gas composition, molecular/energy
reference, spin scope and inlet total-versus-static enthalpy/kinetic energy.
Current single-gas finite source admission rejects arbitrary CoolProp-to-native
formation reference relabeling. An already-warmed gas boundary does not supply
LH2 evaporation, droplet/air condensation, entrainment, wall impingement or mixing.
Actual prescribed fan/transfer flows include upstream work in their admitted
enthalpy boundary; passive pressure-driven flow must use its physical owner.

Expose an accepted-step/failed-state observer with original native boundary and
species/U/H/Q integrals, actual solver status and explicit distinction between
accepted states, interpolation outputs and nonlinear/derivative trial states.
Current shared failure API retains native state/time and completed command
partitions, not hidden outputs within a failed partition or an exact first
bad trial. Localize event/depletion roots with raw brackets before claiming exact
exhaustion, source isolation or safeguard timing. Numerical time extensions and
off-simplex constitutive extensions must remain distinct from physical states.

Retain oxygen mass/mol, wet gas mole fraction, explicitly converted dry fraction,
actual gas-phase water and absolute pO2 separately. A volume-fraction occupational
screen is not a physiological dose or interchangeable partial-pressure criterion.
Pressure/elevation/site applicability and comparator need explicit evidence.
Verify owner-built result bindings against original native snapshots before a
criterion consumer uses summaries; a dataclass copy with changed oxygen/time/
region must fail. All existing mass/species/U/pressure and sampled-crossing
refinement tests must continue to pass without a replacement gas-volume solver.

## JOS3 public native energy/state hooks

Provide an owned native prepared-state clone, explicit neutral initialization
protocol/setpoints and full initialization trajectory when available. A final
neutral output cannot prove measured pre-exposure conditioning. Expose capacities,
body/layer node mapping, clothing vapor coefficients and unrounded thermogenesis,
respiratory, latent and sensible boundary powers through a versioned public API.
The host currently pins source and uses actual native fields; do not depend on
private field names indefinitely.

The native displayed sensible loss uses the old skin state, while its implicit
step uses updated skin with beginning-step resistance/operative temperature.
Return both with evaluation times, plus the exact native implicit heat ledger.
Do not make users fit a heat correction to rounded reported powers. Current
0.01W outputs produce a0.095W summed rounding bound across19 independently
rounded quantities. Preserve the native outputs and distinguish display precision
from numerical or physical-model error. Provide explicit custom hc/hr/ex_q heat
contracts before adding those boundaries to the accepted energy ledger.

Move previous-shivering memory into each model instance; the current module
global makes rate-limited interleaving ambiguous. Expose and implement the
shivering option consistently rather than retaining an unused switch. Preserve
original native model objects, first failures and complete admitted prefixes.
No patching globals or substituting another physiology engine is requested.

Use integer/native elapsed-clock resolution and reconstruct absolute coordinates
from a stable offset. Reject an absolute floating-point grid that cannot advance
or represent each native duration before executing that step. Preserve actual
native timedelta increments and exact command boundaries.

Ordinary-air thermoregulation is not H2-rich convection, breathing in deficient
O2, cold contact/boiling, tissue phase change or injury probability. Adding those
requires justified heat/mass-transfer properties, contact/clothing/respiration,
phase/perfusion/geometry and independent experiments. Native node temperatures
alone cannot complete cold injury or a source-to-human accident chain. Finite
body-water/nutrient/chemical energy is also outside the current thermal ledger.

## Native air-condensation diagnostic correction

`scripts/check_air_condensation_boundary.py` reproduces the original separately
installed SLABx-LH2 diagnostic. At dry293.15K/101325Pa, H2 feed mass fraction0.5
it returns55.062703293K, O2 condensate0.1004719682kg/kgfeed, but its remaining-gas
O2 partial pressure is189.9182153Pa versus its own saturation182.0539641Pa:
positive condensate coexists with4.3197363% supersaturation. The native phase
state is rejected, not repaired in the host.

The native saturation caps use total moles before condensation. Solve coupled
remaining-gas normalization/complementarity with consistent mass/enthalpy and
solid/liquid definitions. Expose original feed basis, remaining gas basis,
condensed inventories, gas density and bulk apparent density distinctly.
Current y_h2=93.4927055mol% follows feed moles, while remaining gas is97.5313439mol%.
Do not overwrite one basis with another without a named API change.

Acceptance: zero-condensation limits, each species material closure, actual
remaining-gas saturation/complementarity, phase/enthalpy/reference bounds,
humidity and pressure variation, continuity/refinement and original failed cases.
Actual air-condensation onset is separate from a fixed flammability label.
No use as an O2 receptor/source boundary is authorized by passing a warm diluted
case. The existing preferred HyRAM gas/SLABx-LH2 dispersion boundaries remain
separate and their original failed physical premises stay rejected.

## Native learned monitoring and direct physical evidence

Keep actual SignalBatch/feature/scaler/PCA/mode objects, whole-run train/calibration/
evaluation partitions, causal history resets, invalid masks and unseen-mode
abstention. Expose native fit/score/calibration status and preserved original
failure/attempted model without learning again on calibration or held-out data.
Pin actual method/function/code bindings as well as source bytes; changing a
class method must not keep old native provenance. Revalidate current physical
TimeSeries values, not just their formerly frozen instance identity.

The reviewed source is an immutable official MIT archive; no PyPI release existed
at review. Publish versioned artifacts/notices if desired, without assuming a
source version string is a released wheel. A retained caller prediction object
is not independent replay verification of arbitrary predictions. Bind the
observation operator, location, variable, scale, basis and clock explicitly.
Measured calibration/reference drift, faults and deployment data are required
before detector accuracy, physical cause, control or annual reliability claims.
A percentile on authored normal residuals is not a facility false-alarm guarantee.

## ELVHYS4.2 source clarification and independent validation

Preserve DOI10.18710/JXJP0H version1.1 and its198 original attachments/checksums.
The nominal48tests differ from40actual exported cases; source-invalid27/28 and
missing flow channels in5ignited cases must remain explicit. H2 traces have
publisher normalization/time alignment for20m sampling lines; publish the raw
signals, transform, uncertainty and delay procedure if available.

Resolve Time unit/epoch/synchronization for each recorder, separate BlastTime,
source event zero and nominal-rate versus actual-clock interpretation. Resolve
Var4/Var5 box pressure roles in35PRES files, DPT meaning, H2 headers matching
T-only station labels, sensor coordinates/orientations and contradictory
instrument/range/accuracy descriptions. Clarify Autumn2024 versus Nov2025 record
labels. Keep actual/reference ventilation P/T, point-nozzle temperature versus
stagnation state, upstream inventory, phase/spin, aperture/geometry and qualified
H2 mass flow separate. There is no directly measured O2 time history here.

An explicit caller file/hash-bound clock declaration can enable a reconstructed
TimeSeries; it cannot be renamed source-qualified time. Hold out whole independent
cases before any fit. Gauge/absolute pressure and gas/sample versus room-average
concentration need their physical observation operator. Additional source data
or closure evidence is required before claiming direct ODH/cold-room validation.
The separate Dryad gas-O2 chamber discovery has CC0 metadata but no acquired
attachments (HTTP401); it is not an examined substitute experiment.
