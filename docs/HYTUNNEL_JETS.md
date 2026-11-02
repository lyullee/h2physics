# Measured jet scans and conditional model comparison

The [HyTunnel-CS dataset](https://doi.org/10.5281/zenodo.4668554) by Joachim Grune and
Karsten Sempert is licensed CC BY 4.0. It contains spatial hydrogen-jet measurements,
ventilation velocity maps and apparatus descriptions. Its title does not make it a
well-mixed enclosure inventory experiment. The current comparison uses the calm jet
configurations and retains wind cases for a separately qualified vector-wind model.

Raw/normalized files and original source illustrations are excluded from distributions.
The loader, analysis, original derived plots and aggregate comparison record are separate
research work. Retain the source authors, version, DOI and terms when using derived data.

## Reproduce

```powershell
.venv\Scripts\python -m pip install -e ".[thermo,data,test]"
.venv\Scripts\python -m pip install -r requirements/native-degali-pinned.txt
.venv\Scripts\python scripts/acquire_data.py --keys mechanical-ventilation --include-suffixes .xlsx .zip .pdf --maximum-mb 20 --maximum-file-mb 15 --workers 1
.venv\Scripts\python scripts/compare_hytunnel_jets.py --plot
```

`--plot` also needs a separately installed Matplotlib; it is present in the observed
verification environment. An isolated native installation can be selected with
`--native-packages artifacts/native_dispersion_packages`. Exact native revision/module
bytes are checked. `--case d4_m1` selects one configuration and `--quick` runs a coarse
diagnostic. Those restricted reports stay under ignored artifacts rather than replacing
the full public research record. The current full comparison exits nonzero after writing
`research/hytunnel_jets.md`, because declared numerical/accuracy targets fail.

## Source data contract

```python
from pathlib import Path
from h2physics.data.hytunnel import load_hytunnel_jet_workbook

book = load_hytunnel_jet_workbook(
    Path("data/raw/mechanical-ventilation/4668554/HTE2440PS003MIXED_300321.xlsx"),
    source_id="doi:10.5281/zenodo.4668554/HTE2440PS003MIXED_300321.xlsx",
)
sheet = next(item for item in book.sheets if item.sheet_name == "4 mm 1g H2 W=0")
observations = sheet.observations
x, valid_x = observations.column("x")
concentration, valid_c = observations.column("mean_h2_volume_fraction")
print(book.source_sha256, sheet.issues, observations.content_sha256)
```

Each row retains source scan row, channel, original mean cell, experiment/configuration
identity and masks. Coordinates become metres; gas volume percent becomes a dimensionless
volume fraction. Mean, maximum and minimum remain separate measurements. There is no
fabricated sample time, sorting across experiments or conversion of a missing value to zero.
Maxima/minima describe observed fluctuations and are not confidence intervals or standard
errors. Source conditions repeat per sensor row; aggregate them across distinct scan rows.

Actual four-workbook scope is **42 worksheets / 5,256 spatial sensor rows**, including two
extra calm baselines relative to the stated forty-configuration campaign. A repeated header
can change the sensor offsets partway down a sheet; the loader preserves that change.
Reported source pipe overpressure remains separate from its ambient-added absolute value
and is not labeled nozzle stagnation pressure. Ambient pressure/temperature header conflicts
in the 1 mm / 1 g/s calm sheet remain invalid source conditions. Its concentration values
are retained. A sheet labelled He while the columns identify H2 has unresolved gas identity;
its H2 observation masks are false. No automatic tracer renaming occurs.

Negative readings, missing values and inconsistent min/mean/max order are retained and
masked according to separate checks. Valid zeros stay zero. `AmbientColumnOverride` is a
per-sheet structural option only when a caller supplies explicit correction evidence;
corrected P/T and dependent absolute pressure acquire reconstructed origin. No such
override is applied in the published comparison. The airflow workbook needs its own
spatial velocity contract; its nominal fan speed is not a uniform velocity boundary.

For the PS001 `1 mm 1g H2 W = 0` sheet, the literal condition headers are
`Pu/mbar` and `Tu / °C`; its first scan row records 9.3 and 1011.5. Treating
these as the stated ambient pressure and temperature is implausible, while
reversing the columns is only a conjecture. The record-level description says
the concentration sheets include release conditions, but supplies no row-aligned
column correction. Therefore no `AmbientColumnOverride` is admitted for this
sheet, its ambient condition channels remain invalid, and this case stays out of
the native-jet comparison. The workbook's H2 concentration observations remain
available through the existing reader.

## Condition a source through the one existing nozzle

```python
from h2physics.release import NozzleOpening
from h2physics.release_inverse import infer_nozzle_stagnation_pressure
from h2physics.thermo import CoolPropProperties

# Authored illustrative inputs; replace with reviewed measurements/assumptions.
properties = CoolPropProperties("Hydrogen")
inferred = infer_nozzle_stagnation_pressure(properties,
    observed_mass_flow_kg_s=.001, stagnation_temperature_k=290.,
    temperature_basis_id="declared source-temperature assumption",
    evidence_id="declared flow evidence", back_pressure_pa=100_000.,
    opening=NozzleOpening.circular("opening", .004, effective_area_factor=1.,
                                  area_basis_id="declared nominal opening"),
    pressure_bounds_pa=(100_000., 30e6),
)
print(inferred.equivalent_stagnation_pressure_pa, inferred.relative_mass_error)
# inferred.nozzle is the existing NozzleResult accepted by expand_nozzle_gas.
```

The inverse calls the same EOS/nozzle kernel, checks a sampled monotone gas path and
brackets the target at fixed T0/area. Zero/unbracketed flow, unsupported phase, incompatible
states and missing temperature/evidence interpretation are rejected. The result has
reconstructed origin and records sampled P/flow, evaluations and root iterations.
Sampling is not a proof of monotonicity over another EOS/domain.

The comparison uses measured mean mass flow and nominal area, assuming T0 equals mean
ambient temperature. It reconstructs an **equivalent inlet pressure**, rather than treating
the instrumented supply-pipe pressure as the nozzle inlet. A source-flow-conditioned
dispersion comparison does not validate the nozzle's independent flow prediction or the
unresolved supply-line loss. Virtual ambient-plane position is explicitly set at the
physical orifice; that axial-offset assumption remains a source of uncertainty.

## Numerical energy reference

The actual native initializer scales an energy residual by net energy, which can be small
when static enthalpy and kinetic energy cancel. Some measured-flow-conditioned cases fail
that initializer. An explicit native subclass expresses flux energy as
`E_native = E_physical + C * H2_mass_flux`; source specific energy receives `C*Y_H2`.
This is a constant H2 component reference transformation. It changes neither thermodynamic
tables, physical profiles, entrainment coefficients nor the native root/ODE solver.

```python
from degali.addons.axisymmetric_jet import ConservedGaussianJet
from h2physics.adapters.degali import (
    profile_integrated_buoyancy_type, hydrogen_energy_gauge_type,
)

BaseJet = profile_integrated_buoyancy_type(ConservedGaussianJet)
# plane is the checked ambient gas plane; use the full constructor in NATIVE_JETS.md.
Jet = hydrogen_energy_gauge_type(BaseJet, shift_j_kg_h2=.5*plane.velocity_m_s**2)
```

The native raw result retains its declared shifted reference. Host audits first recover
`E_physical = E_native - C*H2_mass_flux`; they keep the original energy scale and limits.
`run.physical_energy_flux_w` returns that conversion as a read-only array. Only H2 mass
flux is used, not the mixture mass including entrained air. The gauge shift is retained in
`run.audit.native_energy_gauge_shift_j_kg_h2`. Initial physical-reference energy is checked
separately. No budget is increased to pass an initialization or an integration failure.

The script records unshifted failures and C/2C initial-state comparisons for every case,
plus full trajectory/observer comparisons for the low-flow 4 mm case and held-out case.
Energy reference conditioning does not repair a failed downstream conservation budget.
Request 011 describes the public native flux/reference/integration interfaces needed next.

## Cartesian gas observation

`observe_native_gas_jet` projects declared Cartesian positions onto the actual computed
piecewise-linear native centreline. It calls the native interpolated state and radial
profile. It requires the exact coordinate frame, coordinate origin and evidence identity.
An explicitly unbounded `JetPlane(..., ground_vertical_coordinate_m=None)` represents
relative free-field geometry without inventing the source height or a ground clearance.
The default ground coordinate remains zero for the original facility cases.

The gas-volume operator is restricted to dry gas, 200-300 K and at most 200 kPa. Within
that declared envelope, gas mole fraction approximates the reported sample volume
fraction. It does not label a complete gas-plus-condensate mass fraction as a gas sensor
reading. Unknown humidity, sampling-tube response/aperture, wall effects and real-mixture
volume departures remain comparison assumptions/limitations.

Choose `radial_tail_policy="mask"` or `"native_gaussian_continuation"` explicitly. The
latter evaluates the public native analytic radial profile beyond its flux quadrature
and flags every tail point. Neither policy extrapolates beyond computed axial distance.
Out-of-envelope rows retain coordinates, masks and reasons. Failed conservation runs need
`allow_failed_run=True` for diagnostic observation; their failed status stays in context.

## Current comparison evidence

Five unambiguous calm configurations are evaluated at 81/161/321 radial points with fixed
coefficients and prescribed accuracy/conservation/refinement targets. The entire 4 mm /
5 g/s configuration is reserved in the reporting split. No concentration coefficients are
estimated in either split, and upstream dataset-training independence is not established.

The initial source reference transformation closes previously failing roots without
changing the physical state in C/2C checks. Four finest native numerical runs pass their
conservation gates; the 4 mm / 1 g/s energy budget still fails. All five fail at least one
authored field-accuracy target. Fine-pair observer agreement does not override those
failures. The full record reports absolute volume-fraction errors, valid coverage,
native energy defects, source/observation fingerprints and initial/full-path gauge checks.
This supports continued model development, not a qualified hazard distance or facility use.
