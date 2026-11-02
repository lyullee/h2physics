# Measured PEM electrolysis and native small-signal models

This level connects measured complex spectra to the existing observation, estimation
and electrochemistry APIs. The optional impedance.py engine owns equivalent-circuit
elements and prediction. It is a frequency-domain electrical approximation around one
operating point, separate from the shared static polarization/Faraday/energy balance.
It does not add another stack or process integrator.

## Install and replay

```powershell
python -m pip install -e ".[eis,test]"
python scripts/replay_data.py pem-crossover
python scripts/check_pem_ingestion.py
python scripts/fit_pem_impedance.py
```

The pinned native release is impedance 1.7.1, MIT. Its import also needs pandas in the
tested modern Altair environment; the extra declares that otherwise missing dependency.
Prediction and parameter-name/unit introspection are exercised. Native plotting, fitting,
serialization and unrelated circuits have not all been qualified by this integration.
No JSON is required. The core package and data loader do not import impedance or pandas.

The first ingestion run streams all four CSV members from the checksum-pinned archive;
it does not extract 1.5 GB of uncompressed CSV files. The full source has 23,764,321 rows.
Only the first two POL_GEIS counters are retained: 14,971 rows, including 3,312
positive-frequency readings grouped into 144 complete 23-point sweeps. These are four
physical cells, not 144 independent cells. `--use-cache` explicitly permits matching
full-member audit caches after the archive hash, profile hash and observation content
hash have been checked. A stale cache fails; regenerate it with a full ingestion.
All caches and the generated original plot `artifacts/pem_eis/fits.png` are ignored.

The exact source and transformations are recorded in
[pem_ingestion.md](../research/pem_ingestion.md), fitted parameters and whole-sweep
comparisons in [pem_impedance.md](../research/pem_impedance.md). Source acquisition,
version, attribution and CC BY 4.0 terms are in `research/data/pem-crossover.toml`.

## Source profile and masks

`load_pem_csv(binary_stream, experiment_id=..., source_id=..., measurement_types=...,
counters=..., active_area_m2=..., phase_sign=...)` requires the reviewed actual headers.
It returns a frozen `PemExperiment`: a read-only `ObservationTable`, protocol labels,
explicit area, cell-specific clock, phase convention and full-member `PemLoadReport`.
The caller owns the stream. Unselected rows still contribute to the member SHA-256.
Malformed numeric cells become missing with a count; ragged rows and invalid selected
protocol counters fail. Empty selections remain empty, without invented observations.

Units are canonical: seconds, K, A, V, Hz, ohm, degrees, S/m, Pa absolute and gas volume
fraction. Corrected and uncorrected GC remain different channels with explicit bases.
The corrected channel is admitted only in the source's H2_char/CstC protocol phases;
it is not a continuous crossover-flux signal. Missing readings are never filled.
Block temperature is not a measured reaction temperature. The profile preserves raw
elapsed clocks and row identities instead of sorting, aligning cells or smoothing data.

Source DC placeholders use 0 Hz and 0 ohm. They remain in the table but are masked from
spectral use. Positive frequency does not make an invalid magnitude/phase valid.
`pem_spectra` separates positive-frequency blocks and explicit frequency resets, preserving
order and every repeated reading. Defaults are `dc_tail_rows=10`, `maximum_dc_gap_s=2`,
`frequency_reset_ratio=2` and `ascending_frequency=True`. The source-specific replay opts
into 120 s maximum DC gap; 28 spectra still have unknown DC context. The preceding tail
must be from the same protocol group and is cleared between holds. `PemSpectrum` retains
median DC current/voltage, block temperature, absolute cathode pressure, contributing row
IDs and the actual `dc_gap_s`, including rejected long gaps. Instantaneous AC current is
not rounded to infer the operating setpoint.

There are 18 acquired sweeps per counter despite the nominal 17-level description.
Counter 1 ends near 12 A again in Reference/PtC and near 14 A in PtNano/PtBlack where
admissible DC context is available. No nominal count or current grid replaces these data.

## Native Python composition

```python
from impedance.models.circuits import CustomCircuit
from h2physics.adapters import NativeCircuitOperator
from h2physics.data.pem import load_pem_csv, pem_spectra

# source_stream is a binary file or ZipExtFile owned by the caller.
experiment = load_pem_csv(
    source_stream, experiment_id="my-cell", source_id="my-versioned-record",
    measurement_types=("POL_GEIS",), counters=(1, 2),
    active_area_m2=4e-4, phase_sign=1,
)
spectra = pem_spectra(experiment, maximum_dc_gap_s=120.)
operator = NativeCircuitOperator(
    CustomCircuit, circuit="L0-R0-p(R1,CPE1)",
    parameter_names=("L0", "R0", "R1", "CPE1_0", "CPE1_1"),
    parameter_units=("H", "Ohm", "Ohm", "Ohm^-1 sec^a", ""),
)
parameters = {"L0": 1e-6, "R0": .05, "R1": .05, "CPE1_0": .1, "CPE1_1": .9}
evaluated = operator.evaluate(spectra[0].spectrum.frequency_hz, parameters)
native_circuit = evaluated.native
```

`evaluate` checks positive finite frequencies, declared parameter order, optional expected native units and
finite complex output. It returns the actual native circuit, read-only prediction/frequency
arrays and parameter metadata. Without `parameter_units`, native unit strings are retained
but not compared to an expected contract. Another supported native factory/circuit can
be injected; the caller must supply and qualify its parameters, bounds and applicability. A native
error does not select a different circuit. The only filtered warning reports the intentional
use of declared initial parameters for prediction, without a native fit claim.

`ImpedanceSpectrum` accepts complex arrays, masks, original point IDs, source, experiment
and explicit response origin. `frequency_origin` can be supplied separately; otherwise it
inherits the response origin. The source loader declares measured frequency and reconstructed
complex response. The phasor convention is exp(+j omega t), so capacitive response has
negative imaginary part. A Nyquist plot of -Im(Z) does not change that convention.

`.cartesian_observations()` produces the shared variables `FREQUENCY`, `COMPONENT` and
`IMPEDANCE`; selectors 0/1 mean real/imaginary. Both projections preserve source point IDs
with distinct suffixes and the same whole-sweep group. They are correlated components,
not additional independent experiments. Pass this table, the operator and explicit
`BoundedParameter` objects directly to `fit_observations`; `assess_held_out` rejects reused
rows/groups. See the replay script for a complete executable example with SVD diagnostics.

An explicitly interpreted whole-cell resistance can feed the existing `OhmicLoss`
through a Python callable: area resistance = R0 times active area (ohm m2). This is a
unit-correct coupling demonstration. R0 can include contacts/leads and several cell
contributions; it is not automatically membrane resistivity or a valid static DC loss.
Do not add it to an existing ohmic term and count the same loss twice. Operating-point
dependence, temperature and large-signal behavior need separate evidence.

`adapters.PemOhmicLossBinding.from_fit(...)` now packages that coupling as a typed
receipt. It requires the fit's ordered row IDs and content fingerprint to match either one
exact real/imaginary sweep table or the caller-ordered concatenation of selected sweep tables,
and checks the retained PEM member hash, DC context rows, active area, model and fit identities.
For multiple sweeps, the caller must select `operating_spectrum_id`; the binding retains every
sweep fingerprint and its DC context while using only the selected operating point for the
stack context. The caller must supply an `interpretation_id` approving use of effective
whole-cell R0 as a DC loss. A caller-owned temperature multiplier is available for an
independently supplied law and is kept separate from the measured constant-R0 estimate.
Rank-deficient Jacobians and an R0 estimate on an active bound are withheld from transfer;
the full fit report is still retained. A caller can set a maximum scaled condition number
for a study-specific gate, because no universal threshold is assigned here.
The receipt creates the existing `OhmicLoss`, retaining its effective current, block
temperature and pressure context. `extend_loss_mapping(existing, component_id=...)`
produces a `PemStackLossMap`, an immutable ordinary mapping for `HydrogenStack` that also
retains the originating EIS binding and any distinct-ohmic evidence ID. It rejects component
replacement and requires an explicit evidence identity before coexisting with another `OhmicLoss` law.
This prevents accidental double counting while allowing separately characterized interfaces
when their distinction is supported. This is a Python integration contract; it does not
refit the archive or establish a physical resistance decomposition.

## Evidence boundaries

The replay fits the first complete counter-1 spectrum with reconstructed DC current in
[11.8,12.2] A per cell. Entire eligible repeats in counters 1/2 are held out. No points
are removed to improve residuals, and the approximately 100–10000 Hz band is not extended.
The same bounds/starts and a predeclared complex-RMSE diagnostic apply to every case.
Reference coefficients are also transferred unchanged to the other cells to expose
portability limits. These are same-source measured comparisons, not independent plant
validation. Numerical parameter rank, conditioning, active bounds and failed targets
remain visible in the report.

The analytic alpha=1 RC limit checks the native connection independently. It cannot
validate the selected CPE topology or establish a unique electrode mechanism. Q has
alpha-dependent units and is an ordinary capacitance only at alpha=1. The finite band,
unqualified linear/time-invariant behavior, absent noise model and untested
Kramers–Kronig consistency limit interpretation. Thermal inventory, thermochemical
activities, gas crossover, catalyst recombination and degradation laws remain separate
unfinished physical work. No safety qualification follows from a small fit residual.
