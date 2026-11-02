# Brookite photocatalysis observation profile

`h2physics.data.photocatalysis` reads the acquired, pinned
[Hejazi et al. dataset](https://doi.org/10.5281/zenodo.15277951), version15277951,
under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Attribution and
the twelve authors are retained in `research/data/tio2-photo-evolution.toml`.
The archive contains37 TXT exports and4 images. The API reads numeric observations;
it does not decode images, execute source programs or reproduce publication tables.
Raw data and audit JSON remain ignored and excluded from distributions.

```python
from h2physics.data.photocatalysis import PhotocatalysisArchive, reported_aqy

with PhotocatalysisArchive(
    "data/raw/tio2-photo-evolution/15277951/Dataset.zip",
    source_id="10.5281/zenodo.15277951",
    study_id="10.5281/zenodo.15277951/one-study",
) as source:
    for block in source.iter_blocks("Figure4b.txt", block_rows=128):
        raw = block.observations
        aqy = reported_aqy(block)
        # aqy.source retains every original field, including unresolved columns.
```

`PhotocatalysisBlock` retains an immutable common `ObservationTable`, exact header
cells, original data cells, one-based ZIP-member source lines, one-based column
definitions, masks and per-cell invalid reasons. Source rows include archive SHA,
member path and member SHA; same-named/duplicate exports do not collapse identity.
Raw variable units remain `source_unit_unresolved`, with original header units
available independently. Categorical labels are kept as strings; their numeric
mask is false. Blanks, `--`, overflow and unresolved text have different reasons.
Signed values, zero, padding and entirely missing rows survive.

`first_line`/`last_line` select inclusive original data lines, after each member's
declared header region. `block_rows` is1–2048. Numeric arrays are block bounded;
each text member is separately bounded before decoding. Default limits are8MB
compressed,10MB expanded,2MB per member,100 members and20000 lines per text file.
ZIP paths, symlinks, encryption, sizes, compression ratios, CRC and SHA are checked
without extraction. A source SHA check on context exit detects source mutation.
UTF-8 decoding is explicit; a recorded CP1252 fallback is available. Every acquired
TXT in the audited version decoded as UTF-8. There is no extra reader dependency.

All original columns survive independently. Adjacent or separate exports do not
automatically share an x-grid, wavelength, clock, unit, sample or normalization.
The duplicate `Component3` labels in one PL export retain distinct column IDs.
Preparation duration is not reaction time. `as_time_series()` rejects automatic
conversion, including histories with `Time(h)` whose ordinate remains unresolved.
Experimental-labelled characterization fields can have `Origin.MEASURED`; fitted
components, residuals and identifiable processed outputs are reconstructed.
An experimental-labelled field with explicit source normalization is reconstructed.
S13b categorical energy `row_labels` are separate from catalyst `sample_labels`.
Headerless ambiguous fields stay unresolved. None become independent H₂ kinetics.

## Specific-rate and AQY views

`reported_h2_specific_rate(block, evidence=...)` is restricted to Figure4a column2.
The TXT itself has no unit header. `PhotocatalysisMappingEvidence` must name the
exact member SHA/column, source unit, primary reference/locator, evidence ID and
catalyst-mass basis. Its default `candidate_unverified` status is rejected;
`caller_reviewed` is an explicit caller declaration, not software verification of
a paper. A basis can explicitly retain unresolved details. A separate returned
`MappedPhotocatalysisBlock` retains the source block and evidence object.

The reviewed limited mapping uses the [primary article](https://doi.org/10.1021/acsaem.4c01950)
and its [author-institution PDF](https://ris.utwente.nl/ws/portalfiles/portal/472661098/hejazi-et-al-2024-suppressing-charge-recombination-by-engineering-homojunctions-in-brookite-tio2-nanorods-for-enhanced.pdf):
indexed p9428 Figure4A discussion relates named samples to a specific molar rate.
The conversion from μmol H₂/(g catalyst h) to mol H₂/(kg catalyst s) is
`1e-6 / (1e-3 * 3600)`. This is unit/column evidence; the dry/wet mass definition,
gas collection/calibration and apparatus qualification remain unresolved. The
reported rate and converted view are `Origin.RECONSTRUCTED`. Column3 is retained
as an unresolved auxiliary field; it never becomes sigma, standard error or a
replicate count. No catalyst-mass value is inferred to create total H₂ production.

`reported_aqy(block)` uses only Figure4b's explicit column1 `nm` and column2 `%`
headers, returning metres and dimensionless reported AQY. It retains sample
identity from the source header and reconstructs no photon supply. Column3 has
an ambiguous unit header and requires its own reviewed `%` mapping; columns4–7
are retained without borrowing roles. Negative reported values survive. A
nonpositive wavelength is masked in the mapped view while remaining in the source.

The primary Methods indexed p9424 defines AQY using incident photons and two
electrons per evolved H₂. That separately inspected evidence does not silently
change the raw profile's `reported_apparent_quantum_yield` quantity or unresolved
optical basis. The data API applies only the percent scaling; it never applies
an extra factor2 or binds a productive photon yield. Full SI, wavelength-dependent
light power, T/P and gas calibration were not acquired by this qualification.
The source formula/conditions and the model's incident/absorbed-photon convention
must be reviewed explicitly before a comparison.

## Independence and applicability

All rows use one caller-declared study group. File names, catalyst configurations,
fitted components and sample labels are not independent replicate experiments.
Figure7b and7d are exact duplicate members. Figure4a/S5 share two exact raw rows.
Original identities and `source_equivalence_id` are retained; no deduplication or
independent held-out split is automatic. Matching rows establish numerical
overlap, not the provenance of separate physical repetitions.

The principal usable targets are conditioned source-reported specific H₂ rates
and reported wavelength/AQY observations after separate evidence review. Material
spectra constrain their own characterization operators. Fitted spectra, Tauc
fields, PL peak areas and preparation-time trends cannot independently validate
H₂ rate, recombination lifetime, elementary mechanisms or a universal catalyst
coefficient. The source context includes methanol-assisted tests; these data do
not establish overall water splitting or a complete reaction/energy inventory.

Model comparison additionally needs an actual light spectrum/power fingerprint,
geometry, medium, catalyst basis, T/P and collection boundary. The source exports
do not replace those conditions. Parent production/reaction APIs own the coupled
photon/material/energy calculation; this profile introduces no photocatalytic
solver, normalization, fit, uncertainty estimate or model validation claim.

Run `.venv\Scripts\python -X utf8 scripts/check_photocatalysis_data.py` for the
offline all37-member two-partition replay. The detailed output is ignored under
`data/processed/tio2-photo-evolution/15277951/`. Original fixture tests are in
`tests/test_photocatalysis_data.py`; the completed source audit is recorded in
`research/photocatalysis_data.md`.
