# Data suitability and unresolved boundaries

This ledger records scientific suitability separately from download and license status.
Exact versions, creators, dates, rights URLs and hashes are in `research/data/*.toml`.
Rows in wide instrument logs, spreadsheet dimensions and repeated computed results are
not counts of independent experiments. All files are kept outside release artifacts.

## Newly acquired PEM process measurements

`pem-ripple-degradation` is now acquired locally under the publisher's CC BY 4.0
terms, with the complete 90,759,411-byte attachment matching its SHA-256 receipt.
Its source-bound streaming reader retains measured IV rows and per-cell continuous
voltage/current logs, including source time gaps; fitted parameter values remain
separate derived outputs. This provides rights-qualified, inspectable process data,
but it is not yet model-validation qualified: active area, calibration, test state,
timezone and cross-cell clock alignment are unresolved. No current-density
conversion, missing-period reconstruction or fit is admitted. See
[`PEM_RIPPLE_DEGRADATION.md`](PEM_RIPPLE_DEGRADATION.md) and the acquisition receipt.

| Collection | Useful observations or inputs | Qualification boundary / next action |
|---|---|---|
| bath-cryo-kinetics | Two acquired Bath workbooks; kinetic sheets report time (min), excess H2 uptake (micromols), pressure (MPa), and sample temperature (K) for MIL-101 (Cr) and AX-21 | Source-hash-bound reader preserves row values and declared units. The record states “No restrictions”; only measurement workbooks are retained. Finite `storage.adsorption_dynamics` coupling is blocked because the kinetic sample mass and mapping to isotherm specimens are absent; no excess-to-absolute conversion or fit is performed. Deferred Hangang case checks schema/provenance only. See `BATH_CRYO_KINETICS.md`. |
| grinhy2-electrolysis-transient | One acquired CC BY 4.0 plant workbook, normalized as a 447-row source-attributed CSV with four boundary-flow series | `h2physics.data.grinhy2.load_grinhy2_flow` provides a hash-pinned immutable Python reader and keeps the 8,205 s logger gap and negative raw readings. Deferred Hangang cases cover ingestion and the model-linkage evidence gap. There are no current/current-density, electrical-power, cell-temperature or stack-temperature observations; the `Nm³` reference state is unspecified, so no molar/mass conversion, producer-model fit, forcing profile, or electrochemical validation is supported. See `data_sources/grinhy2/README.md`. |
| oxygen-hypoxia-chamber | Dryad version 6, measured hypoxia-chamber workbook and README; record declares CC0 1.0 and describes gas/liquid O2, inlet composition/flow, temperature, evaporation and probe delay | Both publisher files are listed with SHA-256 receipts, but the captured file downloads failed HTTP 401 and no bytes/schema are acquired. A future gas-phase comparison may fit existing `CanteraOxygenRoom` only after inlet flow basis, source composition, room/vent boundaries, shared clock and sensor calibration/delay are known. Liquid transfer/evaporation is outside that API. Metadata-only Hangang case `oxygen-hypoxia-chamber-gas-transfer-model-link-gap` records the gap; no model run is claimed. See `OXYGEN_HYPOXIA_CHAMBER_DATA_LINK_GAP.md` and `research/data/oxygen-hypoxia-chamber.toml`. |
| ab2-hydride-tank | Three acquired Mendeley v1 CC BY 4.0 workbooks with source-clock and five external shell thermocouple channels | The source-bound block reader preserves missing rows, raw cells and unresolved MFC reference state/pressure basis. An optional adapter maps one selected shell sensor into the existing `FiniteHydrideHeatBoundary` only with caller-supplied shell-to-bath evidence, and only over measured clock support. This is not bed-temperature inference, flow conversion, kinetic fitting or experiment validation. Deferred Hangang synthetic contract checks API/support/currentness only. See `HYDRIDE_DATA.md` and `research/data/ab2-hydride-tank.toml`. |
| peace-alkaline-short-stack | Zenodo v1 describes three pressurized alkaline short-stack runs at nominal 2/4/6 bar; three raw sensor-channel exports and a column-description table are acquired under CC BY 4.0 | Explicit-unit electrical, temperature and pressure channels have an optional immutable numeric view in A/W/V/K/reported Pa; original tokens and hashes remain attached. A source-bound bridge sends same-row reported current, voltage and caller-selected temperature into existing `HydrogenStack` evaluations without interpolation/extrapolation. Caller must justify electrical scope, active area, series-cell count and temperature mapping; trace rechecks source/model owners and reproduces results. Residuals are diagnostic only, not calibration/validation. Pressure basis, normal-volume reference conditions, H2 quality basis, calibration and clock behavior remain unresolved. Synthetic Hangang case does not read ignored archive files. See `PEACE_ALKALINE_DATA.md`. |
| bam-hydrogen-jet-fire | Source-bound thermocouple, pressure, sensor-voltage and mass-flow exports | The open CC BY 4.0 archive/member reader feeds an optional source-bound view that converts explicit seconds, kg/h, volts and reported bar while retaining original tokens. A new comparator joins a caller-selected plate `[°C]` channel to an existing `ThermalTargetTrace` only with separate evidence for absolute-temperature interpretation, target-sensor mapping, clock alignment and model-point interpolation; it retains both source/model owners and performs no flux inference. Temperature difference-like, dimensionless and unknown channels remain raw. Pressure basis, calibration, flow direction, sensor transfer functions and physical target mapping remain unresolved. The Hangang case uses a synthetic target and does not validate fire/thermal physics. See BAM_HYDROGEN_JET_FIRE_DATA.md and BAM_THERMAL_TARGET_MAPPING_GAP.md. |
| peace-alkaline-cell-testing | Official PEACE listing identifies TU/e alkaline flow-cell electrochemical tests; DataCite DOI metadata lists v1 and CC BY 4.0 | 4TU's repository record/API and file list could not be inspected. No names, sizes, per-file checksums or schema were available, so nothing was downloaded and no parser or validation case was created. See PEACE_ALKALINE_CELL_TESTING_DATA.md. |
| hydrogen-channel | 22 release cases; explicit flow time in s and mass flow in g/s | A source-hash-bound intake now projects the exact flow-time/mass-flow pair to existing `IntervalMassSource` finite safety inputs. It uses explicit caller quadrature and state/location, preserves archive/member hashes and stops at observed endpoints. Sensor time has no header unit; concentration histories are not aligned. Filling-pressure basis and release plane remain unresolved, so this is a measured-source boundary input only—not a jet/plume validation. Deferred Hangang bridge case is fixture-backed and unexecuted. |
| ignited-hydrogen-jet-x044qk | 40 condition rows for open-atmosphere under-expanded H2 jets with delayed ignition | DataverseNO dataset/file metadata declares CC0 1.0. The 14,199-byte condition matrix is acquired at SHA-256 `c50162c995c01bb37c407e7ce0f132301297bf3b2562518c86940fb758ae2557`; its note says MFR is calculated from experimental pressure. A new source-row adapter projects the reported average MFR and release duration as one finite `IntervalMassSource` bin with explicit caller state/location/clock and evidence; no pressure conversion is applied and peak MFR is unused. 39 raw pressure-history CSVs and six high-speed video bundles remain unacquired; pressure basis/calibration remain unresolved. This is a bounded source projection, not dispersion or overpressure validation. See `IGNITED_HYDROGEN_JET_DATA.md` and `research/data/ignited-hydrogen-jet-x044qk.toml`. |
| mechanical-ventilation | Four concentration workbooks: 42 sheets / 5256 spatial sensor rows; separate flow maps, apparatus description and CAD | Jet scans in an open test vessel, not a mixed-box inventory. Repeated sensor grids and one He/H2 identity conflict are preserved. PS001 calm 1 mm/1 g/s first-row `Pu/mbar=9.3`, `Tu/°C=1011.5` is inconsistent with plausible ambient conditions; record documentation does not resolve whether columns are swapped. Do not use `AmbientColumnOverride` without explicit correction evidence. Five other unambiguous calm configurations have conditional flow-inferred-source/native-jet comparisons; accuracy targets and one finest energy audit still fail. Source T0, line/nozzle pressure, dry point response and wall/wind qualification remain open. |
| carpark-unignited | 22/23 CC BY 4.0 files cached; metadata-only audit of Exp03 MAT (3,174,901 B, SHA-256 `2c74d3575c00fe84757ffcd9580f36f29bd3be43af58f1c9814a1544ac799cb4`) finds 49,999-row MFM and ventilation histories and 38 sensors | MFM label identifies g/s but its clock unit/origin and synchronization to separate sensor/tank/vent clocks are not declared. Sensor time is `sec`, concentration `%vol`, but `pos` unit/frame and sensor calibration/response are unresolved; no source direction/nozzle-plane/expansion-T mapping is established. The file-handling guide remains unacquired. Metadata-only case `usn-carpark-unignited-fds-boundary-evidence-gap` records why `HydrogenCFDSource`/FDS cannot yet receive a reproducible measured boundary or compare receptor data. No MAT values were read and no FDS was run. See `CARPARK_UNIGNITED_FDS_LINK_GAP.md` and `research/data/carpark-unignited.toml`. |
| pressure-unignited | 8 acquired MAT and 9 XLSX exports, with 19 attachment hashes verified | Fully inspected 7999992 SIGMA rows, 33310586 GEN3i rows and 78272 XLSX rows. A selected nonnegative SIGMA measured mass-flow window can enter `IntervalMassSource` through a hash/file-bound adapter with caller quadrature, flow-meter-to-release-plane evidence and representative H2 state. Requested endpoints must be exact source timestamps; missing/negative flow rejects, with pressure channels excluded. Pressure bases, concentration convention, clock alignment and spatial/response roles remain unresolved. Deferred Hangang case `usn-unignited-measured-flow-finite-source-contract` exercises a reader-backed non-row-aligned endpoint rejection, not an accepted source. See `PRESSURE_PEAKING_DATA.md` and `research/pressure_peaking_data.md`. |
| pressure-ignited | 14 of 33 CC BY 4.0 attachments acquired; selected MAT has SIGMA (999,999×7) and GEN3i (78,894×3) with separate clocks | Hash-bound reader and adapter expose only documented measured SIGMA H2 mass flow (g/s→kg/s) to `IntervalMassSource`; flow quadrature, exact row-aligned clock window, release plane, and representative H2 state are caller supplied. Negative flow rejects. GEN3i column 2 stays unresolved; pressure, temperature, ignition timing, and recorder alignment are not used. Deferred Hangang case `usn-ignited-measured-flow-finite-source-contract` checks source/API contract only. Sensor identity/calibration/filtering, ignition-clock mapping, and experiment source-state mapping block any pressure-peaking comparison. See `IGNITED_PRESSURE_PEAKING_SOURCE.md`. |
| carpark-thermal | All eight MAT experiments and two supporting attachments acquired and hash-verified | All245 vectors/157964002 scalar elements audited. Preserve unclocked signals, unresolved time units/associations, sensor roles and derived THF; no automatic dose or incident heat. See THERMAL_EFFECTS_DATA.md. |
| elvhys-shock-tube | DataverseNO DOI 10.18710/M5LOLM, version 1.0, CC0-1.0; 42 of 133 files acquired, 534,609,893 B | Reader retains raw source rows and per-file clocks, but recorder epochs/rupture alignment, dynamic pressure calibration/baseline, containment station coordinates (missing D4.8 drawing), tube-side gas composition/liquid inventory, and thermal sensor mapping are unresolved. Signed PRESF `bar_a` is not treated as thermodynamic absolute pressure. Metadata-only Hangang case `elvhys-lh2-rupture-model-link-evidence-gap` records why current release/pressure APIs cannot yet be compared. No physical validation claim. See `ELVHYS_MODEL_LINK_GAP.md` and the prepared request. |
| preslhy-discharge | All ten published high-pressure warm/cryogenic DisCha attachments; 160 workbook sheets | Previously throttled cold bundles completed after explicit spaced requests. Four actual 1 mm warm runs are loaded with independent recorder clocks. Fast pressure and closed vessel temperatures drive a conditional EOS-inventory/nozzle comparison with one whole run held out. Gauge/ambient/spin and homogeneous-temperature assumptions remain explicit; force/balance are not a quantitative flow reference here. Sheet/file counts are not independent experiments. |
| preslhy-pool | E3.4 ten pool experiments with different substrates; eleven listed attachments | Metadata/rights/version/authors and omissions recorded. CC BY-SA 4.0 is outside the default permissive-data policy, so all eleven attachments remain withheld. The apparatus is a bounded 0.5 m square repeated-fill pool, not an unconfined axisymmetric radius experiment. No source-derived observations or upstream digitised curves are reused in the host's authored native pool verification. Ground-inflow/composition/clock and applicable comparison operators still require review. |
| pem-crossover | Four measured PEM cell CSVs, protocol/DC/EIS/GC channels | Full-member hashes cover 23764321 rows. Initial two POL_GEIS counters yield 144 actual sweeps/3312 positive-frequency readings; 28 sweeps lack admissible DC context at the explicit 120 s gap. Measured whole-sweep circuit fits/repeat and cross-cell comparisons are documented, with unchanged failed targets. Block temperature is not reaction temperature, sparse corrected GC is protocol-restricted, and no crossover/degradation law or independent-source validation is inferred. See PEM_IMPEDANCE.md. |
| ab2-hydride-tank | Three workbooks, six absorption/desorption cases and one vacuum record | 355388 relative-time shell-temperature observations loaded with missing masks. Pressure unit/basis and MFC reference conditions unresolved. Derived cumulative mass is not independent. Internal bed temperature is not observed directly. |
| hydride-compressor | Acquired MHC v1.2 CC BY 4.0 archive; 29 experiment workbooks with raw logger channels and explicit channel units | A checked example has a roughly 2 s timestamp offset; preserve separate clocks and sensor status, and do not classify every workbook as H2 cycling. `compare_mhc_temperature_to_compressor_bed` adds a source/member-hash-bound diagnostic to native compressor bed solid temperature. It accepts archive-reader-issued raw measured K channels only, requires independent sensor-to-bed and clock evidence, and samples only within model support. Logger aliases do not prove sensor location; no fit or equipment validation is claimed. Hangang case `mhc-compressor-temperature-observation-contract` opens a three-row workbook window through the verified reader and rejects caller-forged/cloned blocks. See `HYDRIDE_COMPRESSOR_DATA.md`. |
| hydride-pct-simulation | Five acquired CC BY 4.0 workbooks; ten ABS/DES worksheets; source-bound reader preserves formulas, raw cells and row identity under each file's SHA-256 receipt | Source origin is simulated. Headers report temperature in °C/K, pressure in bar, and uptake in NL/kg (three files) or wt% (two files). Pressure gauge/absolute basis, NL/kg reference state/denominator, and wt% loading basis for mapping to `VanthoffPlateau` remain unresolved. Deferred case `hydride-pct-xlsx-source-preservation` covers source integrity only; `hydride-pct-simulated-equilibrium-model-link-gap` records the model boundary. Any future comparison is source-regression only, not independent validation. No unit conversion or fit is admitted. See `HYDRIDE_PCT_SOURCE_READER.md`, `HYDRIDE_PCT_MODEL_LINK_GAP.md` and manifest `research/data/hydride-pct-simulation.toml`. |
| hydrogen-sound-speed | 30 compiled composition/phase-specific numeric files | 1027 points parsed, 761 compared to HEOS without inferring missing pressure/spin composition. A source-hash-bound pointwise comparator now routes exact rows through existing `CoolPropProperties` only when the recorded normal/para spin basis matches; there is no fit or extrapolation. Historical EOS training overlap remains unresolved, so this is a diagnostic and not independent validation. Large deviations are retained. Deferred Hangang case `hydrogen-acoustic-source-to-coolprop-pointwise-diagnostic` reads the small Carey normal-H2 member. See `HYDROGEN_SOUND_SPEED_DATA.md` and acoustic report. |
| hydrogen-engine-flame-wall | Eight acquired CC BY 4.0 HDF5 figure bitstreams, 8,828,090 bytes | Hash-pinned HDF5 structure inspection supplies shapes/attributes only; it does not read measurement values. Figure-specific quantity/location, crank-angle references, population/uncertainty meanings and several coordinate mappings remain incomplete, and component-level third-party rights review is open. Metadata-only case `hydrogen-engine-figure-data-model-link-gap` tracks a prepared author request; no engine pressure or wall heat boundary is assigned. See `HYDROGEN_ENGINE_DATA_SCHEMA.md`, `HYDROGEN_ENGINE_DATA_LINK_GAP.md` and `requests/hydrogen_engine_figure_data_mapping.md`. |
| geological-adsorption | Latest corrected CC BY 4.0 record contains measured H2/He calibration and geological/reference-material H2 measurements plus processed isotherms | The four processed material CSVs are schema-audited and have a source-hash-checked signed-excess loader. A pinned structural report covers 14 raw CSV members; a typed raw H2/He loader retains 18 equilibrium points, 33 calibration points and four sample configurations with missing fields preserved. It does not fit a helium baseline or authorize an EOS pressure. Absolute-versus-gauge basis, logger clocks, linked COx workbook inputs, uncertainty reproduction, pore-volume correction and excess-to-absolute conversion remain unresolved; no finite-vessel validation follows. |
| carbon-chemisorption | 19 acquired Mendeley v1 files; aggregate H2 chemisorption table has `Material`, `Pressure (torr)`, `Volume (STP cm3/g)` plus blank-labeled columns; record identifies H2 chemisorption at 973 K | CO2 at 273 K and N2 at 77 K are physisorption, not H2 storage evidence. The H2 table's STP reference, absolute/total uptake definition, pressure basis and material-column mapping are not resolved in the local table schema. Existing `ExtendedLangmuirIsotherm` expects a declared loading basis in mol/kg; no pressure/loading conversion or model comparison is admitted. Metadata-only Hangang case `carbon-h2-chemisorption-model-link-gap` and a targeted not-sent request track the missing model boundary. See `CARBON_H2_CHEMISORPTION_MODEL_LINK_GAP.md` and `requests/carbon_h2_chemisorption_basis_request.md`. |
| cryo-mof-dormancy | MOF/carbon cryo-adsorbent and dormancy replication record | All 68 original attachments are acquired under Etalab Open Licence 2.0. A source-bound reader retains exact branch rows and hashes. A new pointwise bridge evaluates 77/87 K rows through the existing `ExtendedLangmuirIsotherm` only when caller evidence authorizes absolute-pressure, absolute-uptake/mass basis and exact material mapping; 20 K remains excluded. This is diagnostic under declared interpretations, not fit or validation. Pressure basis, excess/absolute uptake and mass convention remain source-unresolved. The deferred Hangang contract uses a synthetic file only. See CRYO_MOF_DATA.md. |
| austenite-embrittlement | Compiled steel/material descriptors and hydrogen effects; reported material hydrogen mass fraction, charging conditions and mechanical outcomes | This is not a solubility or diffusivity dataset. Reported hydrogen content does not separate mobile, diffusible and trapped species; exposure pressure reference/purity and matched equilibrium concentration are unresolved. No D(T), S(T,fugacity), permeability, membrane geometry/time history, or trap capture/release coefficients are supplied. Compilation license does not automatically settle rights in each underlying publication table. Raw compilation is not redistributed. |
| oedi-hydrogen-materials | Curated gaseous-H2 material strength and fatigue tables, including a 4130X crack-growth workbook | CC BY 4.0 applies through the Data.gov dataset record. Its workbook reports four H2 series at 45 MPa and one air series at 0.1 MPa. A related HyMatBase item reports 4.5 MPa, but its listed MD5 exactly matches the acquired XLSX and Sandia's study record independently gives 45 MPa. Admit workbook test points at 45 MPa while preserving the catalog discrepancy; no fitting or vessel-life qualification is implied. Heat mapping and specimen/component applicability remain limited. See `research/data/oedi-hydrogen-materials.toml`. |
| hydrogen-in-metal-transport-parameters | A source-bound CC BY 4.0 normalized permeation record for MS1700 and QP1180 is acquired, but no matched dimensional H₂ solubility/diffusivity/permeability parameter set is available | The normalized MAT coordinates are retained by a hash-bound reader but are not yet a material law. Do not map them to `PowerLawSolubility`, `steady_permeation` or `DiffusionSlab` until the normalization equations, carrier basis (H vs H₂), measured concentration versus fugacity/pressure convention, temperature, material heat/composition/processing, coefficient units, geometry and surface conditions have independent source support. If trapping is modeled, site density and capture/release definitions are also required. Independently sourced D and S values must share material, state and reference conventions before composing P=D·S. No material prediction is qualified. See `research/data/hydrogen-diffusivity-ms1700-qp1180.toml`. |
| hydrogen-permeation-ms-ahss-1300 | 1,260 and 599 measured time/current observations for MS AHSS grade 1300 under two cathodic-ramp groups | Actual acquired workbook intake passed locally. Both sheets have row-1 headers and material label E3. Original XML resolves Greek mu (U+03BC): current is microampere; raw rows are retained and `current_ampere(sheet_name)` converts by 1e-6 to A. Pinned metadata gives 50 by 50 by 1.2 mm specimens, but planform does not establish exposed electrode area. Entry boundary history and initial state remain unresolved, so no current-to-H flux, diffusivity fit or transport-model validation is claimed. Five parser schema negatives and byte/receipt/currentness guards passed. See `research/data/hydrogen-permeation-ms-ahss-1300.toml` and `MATERIAL_TRANSPORT.md`. |
| lohc-enthalpies | Computed gas-reference enthalpies for 10373 molecular-pair rows | Native molecular audit closes element/charge/mass; 10345 canonical pairs include 28 conflicting repeated pairs, so 56 rows' heats are withheld. 10317 rows admit G4MP2 gas-reference heat at 298.15 K/101325 Pa. Nine capacity differences exceed the declared reporting threshold. Not measured liquid thermochemistry or kinetics. See CARRIER_REACTIONS.md and research/carrier_reactions.md. |
| pv-pem-dispatch | Zenodo mixed-origin archive, 47,443-byte manuscript-figure ZIP, SHA-256 `2fb59438156bd9ccfd8caad6e9540dd68648ffa08816a5c2eedde0043be96b39`, CC BY 4.0 | The archive contains figure reconstructions and strategy-specific dispatch/cumulative-H2 outputs, not independent measurements of a PV/PEM plant. Existing `PVElectrolysis` requires effective irradiance, array parameters, PV cell temperature, stack temperature and aligned intervals; those inputs and measured-response lineage are absent. Metadata-only Hangang case `pv-pem-dispatch-figure-output-model-linkage-gap` protects this boundary; no model calculation or validation claim is admitted. See `PV_PEM_DISPATCH_DATA.md` and `research/data/pv-pem-dispatch.toml`. |
| pem-grid-system | Dryad record 10.5061/dryad.8931zcs64 describes a 60 kW NEL C-Series PEM system and lists a 72.10 MB simulation archive plus README; Dryad states CC0 1.0 reuse | The primary page's README text identifies `data/experiment/timestamp.txt`, command/stack/SMPS/chiller/subsystem power, and two H2-flow trace files. API file downloads returned HTTP 401 and the current public README stream HTTP 403 (checked 2026-10-31), so no attachment bytes or source hashes are acquired. Experimental power units, H2-flow units/reference basis, sampling support, uncertainty, calibration, sensor mapping, and system boundary remain unknown. The MW convention belongs to separate simulation grid inputs and is not projected onto the experimental traces. Existing metadata-only Hangang case tracks this boundary. A system-boundary diagnostic may be considered after acquisition; cell-level HydrogenStack polarization is not established. See `research/data/pem-grid-system.toml`. |
| alkaline-bubble-observations | Mendeley Data v2, DOI 10.17632/r6np4f7gmf.2; record declares CC BY 4.0; official files endpoint lists 35 root files totaling 375,513,822 bytes | One 1,274-byte README is acquired under CC BY 4.0 and its local SHA-256 matches the publisher; it is retained only in ignored `data/raw/`. The project's paraphrased note records 7M KOH, room temperature, and 1000 FPS capture saved as 15 FPS MP4; the listing describes processed figure folders/scripts and raw hydrogen/oxygen videos. The other 34 image/video assets and nested folder contents were not acquired or inspected. No image scale, bubble measurement schema, current-density mapping or paired electrical observations are established. Caller-calibrated electrode-coverage and electrolyte-void voltage penalties are now available in `h2physics.adapters.alkaline_bubbles`, but this source has no reviewed numeric measurement schema and does not qualify coverage or void parameters. The reduced closure requires explicit caller inputs; no values are inferred from images. Metadata-only Hangang case `alkaline-bubble-electrolysis-model-link-gap` records the source/model boundary. See `ALKALINE_BUBBLE_MODEL_LINK_GAP.md`, `research/data/alkaline-bubble-observations.toml`, and `research/data/alkaline-bubble-observations-file-list.toml`. |
| pressurized-alkaline-bubble-electrode-potentials | RODARE v1, DOI 10.14278/rodare.4547, CC BY 4.0; condition-index CSV and 8.59 GB HDF5 archive | The 1,499-byte, 60-row condition index is hash- and schema-checked by `load_rodare_alkaline_bubble_index()`; the registered Hangang case checks ingestion integrity only. The numeric HDF5 archive is unavailable because bounded byte-range retrieval was not honored. Channel names, units, calibration, pressure reference and clock remain unreviewed. This is not polarization or bubble-loss validation. A bounded/versioned measurement subset or author-supplied files are still required. See `RODARE_ALKALINE_BUBBLE_INDEX.md`, `PRESSURIZED_ALKALINE_BUBBLE_DATA.md` and `research/data/pressurized-alkaline-bubble-electrode-potentials.toml`. |
| sofc-polarization | Four Mendeley v1 SOFC text files with nominal H2/H2O/N2 feeds and four temperature conditions | Hash-pinned reader now exposes source-row polarization curves with explicit °C/mA/cm²/V unit policy; voltage origins stay unresolved because the publisher says the archive mixes experimental and multiphysics-generated values. An adapter can evaluate one selected curve through existing `HydrogenStack` fuel-cell mode, retaining model owner and source receipt; outputs are diagnostic, not fit/validation. Local gas activities, pressure, thermochemistry and cell geometry remain caller evidence. Deferred Hangang contract uses synthetic callbacks. See `SOFC_POLARIZATION_DATA.md`. |
| dark-fermentation | Mendeley v2 CC BY 4.0 workbook, 165,296 B; 830-row/24-column worksheet with per-reactor grouping, raw-cell/mask audit and 13,980 valid numeric observations | Duplicate/repeated/decreasing days, missing fields and the row239 component-production discrepancy are retained. HP/HY/HPR/MP/MPR are reconstructed; BP gas reference P/T and wet/dry basis, fraction denominator/alignment, feed/COD/biomass initial state, reactor volume, clock origin/cadence and R1/R2/R3 independence remain unresolved. Existing BP/fraction checks are same-export algebra, not an independent yield measurement. Metadata-only Hangang case `dark-fermentation-h2-process-model-link-gap` tracks a prepared not-sent gas-basis/state request; no ADM1 model comparison or yield fit is admitted. See `FERMENTATION_DATA.md`, `DARK_FERMENTATION_MODEL_LINK_GAP.md` and `requests/dark_fermentation_gas_basis_request.md`. |
| tio2-photo-evolution | All37 TXT members /42856 rows /241264 source cells, including196397 finite numbers | Full two-partition hash audit; explicit raw/line/header/grid/mask and duplicate/study roles. Specific-rate/AQY mappings are reconstructed and source-evidenced, but the existing photon-accounted production API cannot replay AQY rows without an exact incident/absorbed electron-yield convention and row-matched photon supply, geometry, catalyst and conditions. Metadata-only case `tio2-brookite-aqy-model-link-evidence-gap` tracks the missing link; a targeted not-sent author request seeks the required sidecar data. No model result or kinetics fit is admitted. See `PHOTOCATALYSIS_DATA.md` and `requests/photocatalysis_aqy_condition_mapping.md`. |
| cds-photo-screen | Computational photocatalyst screening workbook | Computed material descriptors, not measured reactor hydrogen yield. |
| h2safe-indoor | Two lab geometries/sensor coordinate files and five test CSVs; HVAC description | A first-party hash-pinned reader now retains source tokens, sensor mapping, missing values, and numeric observations. The [primary catalog](https://data.nlr.gov/submissions/330) identifies helium surrogate releases, not measured H2 dispersion; this dataset is not direct hydrogen validation. Coordinates are in metres; concentration/time conventions and source/HVAC clocks still need qualification. No direct H2 percent/ppm or flow conversion is assumed. The previously advertised source-code link was unavailable at review. |
| grinhy2-electrolysis-transient | One public spreadsheet, 27,069 bytes; locally acquired and normalized to a tracked 447-row CSV | [Zenodo record and API](https://doi.org/10.5281/zenodo.7612826) explicitly declare CC BY 4.0; source MD5 matches. The sheet has time, vent, HPU, grid and demand columns in Nm³/h with no missing cells. Sampling is 15 s except one 8,205 s gap; negative vent/grid readings are preserved. Timezone, normalized-volume reference conditions, meter provenance and state alignment are unresolved. No stack current, electrical power or temperature channels exist; the HPU name does not establish stack production or its measurement plane. Thus no producer parameter fit/forcing profile or rate conversion is admitted; this remains a boundary schedule, not stack/plant validation. |
| hydelta-outflow-closed-spaces | Two public report PDFs (14,260,186 bytes total), no files acquired | [Zenodo record and API](https://doi.org/10.5281/zenodo.8154318) declare CC BY 4.0. The record describes concentration build-up experiments for hydrogen/natural gas across 50, 100, 300 and 1000 dm³/h in a meter-cabinet, hall and room arrangement with ventilation variations and a 3×3×6 sensor-position matrix. Archive files are reports rather than machine-readable time series. Release stops beyond 50% LEL, and some endpoint categories use extrapolation. Coordinates, calibration, cadence, run mapping and extraction fidelity require manual review; candidate for screening/qualitative comparison, not validation evidence. |
| hydelta-pressure-station-ventilation | Two public reports (17,156,658 bytes total), no files acquired | [Zenodo record and API](https://doi.org/10.5281/zenodo.8164602) version 2 declares CC BY 4.0 and contains measured H2/natural-gas leak observations for mini, 0.5 m³ and 4 m³ pressure-station cabinets plus supplemental CFD. The record exposes only report files, not machine-readable sensor histories. Metadata lists 8,542,387 B English and 8,614,271 B Dutch reports with publisher MD5 pins. No report was acquired or extracted. Treat this as a facility-model discovery lead; full run mapping, spatial calibration, release/vent clocks, sensor response and raw-series availability remain unresolved. Publisher notes say its CFD comparison is supplemental and not independently field-qualified. |
| hysam-sampling-system | Three acquired workbooks (1,022,797 bytes) | [Zenodo v1.0 record](https://doi.org/10.5281/zenodo.20590842) declares CC BY 4.0; all publisher MD5 and local SHA-256 checks pass. A source-bound reader retains three single-sheet schemas (6,601×23, 721×14 and 2,161×21). Tags remain uninterpreted because no channel dictionary, units, pressure reference, calibration, system layout or aligned clock is provided. This is ingestion/schema evidence and a discovery lead for sampling/transient work; no parameter fit or model-validation claim is admitted. See `HYSAM_SAMPLING_DATA.md` and `research/data/hysam-sampling-system.toml`. |
| large-scale-open-hydrogen-explosion | Selective acquisition: 3/59 files including one 207,853,888-byte Test001 trace | [DataverseNO record](https://doi.org/10.18710/WSKBIJ) declares dataset-level CC0 1.0; all 59 entries are public. File-level license fields are not exposed, and embedded third-party rights were not reviewed. Test001's channel names and units are schema-pinned; pressure channels are kPa while PT1/PT2/MFR and trigger remain raw voltage. Full trace ingestion is pending Hangang receipt; no calibration, geometry map or explosion-model comparison is claimed. |
| soe-fault-operation | Eleven files (1,092,175,741 bytes), no files acquired | [Zenodo record and API](https://doi.org/10.5281/zenodo.10648884) declare CC BY 4.0. The record describes a six-repeating-unit, 80 cm² SOE and polarization, temperature, pressure and flow under four faults. No MAT file, channel schema, state clock or exact fault labels were independently audited. Metadata-only Hangang contract `soe-fault-operation-data-schema-gap` records the gap; no data-to-model link is admitted. A targeted author/repository request seeks one small file per fault plus baseline, schema, units, clock, sensor interpretation and per-file rights/checksums before bulk acquisition. See `SOE_FAULT_OPERATION_DATA.md` and `requests/soe_fault_operation_data_request.md`. |

## Important data gaps and discovery candidates

- [GrInHy2.0 transient electrolyser hydrogen flow](https://doi.org/10.5281/zenodo.7612826):
  one 27 kB CC BY 4.0 workbook is acquired and normalized as a tracked 447-row
  CSV. The observed columns are vent, HPU, grid and demand flow in Nm³/h on a
  15-second cadence except one retained 8,205-second gap. Negative vent/grid
  values are preserved. Logger timezone and normalized-volume reference state
  are unknown, so do not convert to mass flow or claim model validation. Full
  checksums, schema and attribution are in `data_sources/grinhy2/README.md`.
- [SOE operation under four faulty conditions](https://doi.org/10.5281/zenodo.10648884):
  Zenodo declares CC BY 4.0 and lists 11 files (1.092 GB). The described set
  includes polarization, temperature, pressure and flow data for hydrogen
  starvation, high steam conversion, oxygen-electrode humidification and fuel-
  electrode silicon poisoning. It is relevant to electrolyser operation and
  fault response, but no file or measurement-channel schema has been reviewed;
  consider a subset first.

- [HyDelta D6A.1 closed-space outflow experiments](https://doi.org/10.5281/zenodo.8154318):
  Zenodo's record API declares CC BY 4.0 and lists two public report PDFs
  (14,260,186 bytes total; 0/2 acquired). It describes concentration build-up
  experiments for hydrogen/natural gas with several outflow rates, enclosure
  ventilation states and a 3×3×6 sensor-position matrix. The archive lists
  reports rather than machine-readable raw time series. This is a small
  report-extraction candidate; source tables, unit conventions and derived
  endpoint categories must be audited before any validation use.

- [Large-scale hydrogen explosions: obstructed open-atmosphere releases](https://doi.org/10.18710/WSKBIJ):
  DataverseNO's metadata API lists 59 public files (52 text/plain and seven
  other types), a total of 96,861,179,314 bytes; the web page's text-only filter
  explains the 52-file subset. The dataset record declares CC0 1.0 at dataset
  scope; file-specific license properties are absent from returned file
  metadata, so embedded content rights remain unaudited. The repository
  description says the collection is too large for a single download. The
  selected 6,753 B README and 21,165 B results workbook are acquired with
  publisher MD5 and local SHA-256 pins; no test time series or video is acquired.
  The workbook provides per-test nozzle diameter, reservoir-pressure label,
  ignition code and four signed pressure summaries. This is an observation
  summary only: ambient conditions, absolute sensor coordinates and transient
  source/pressure histories remain missing, and no FDS or explosion-pressure
  comparison is supported. See `LARGE_SCALE_H2_EXPLOSION_SUMMARY.md`.

- [PRESLHY high-pressure cryogenic discharge](https://doi.org/10.35097/1187):
  CC BY 4.0 metadata and individual checksum-bearing attachments are now supported by
  the `radar-kit` provider. Exact completed/deferred scope is in the acquisition receipt.
  See PRESLHY_COMPARISON.md; warm conditional consistency does not qualify cold flashing.
- [PRESLHY combustion collection](https://doi.org/10.35097/1483): share-alike terms require
  a separate redistribution decision; it is not folded into the permissive-data release.
- [LH2/LCH4 neutron phase-change experiments](https://www.nist.gov/publications/results-neutron-imaging-phase-change-experiments-lh2-and-lch4):
  promising cell-scale phase-change evidence. Find the actual numerical repository and
  its data-specific rights before acquisition. A publication abstract is not raw data.
- Large free-spreading LH2 pool/ground-impact data remain a priority. Available papers
  often omit raw histories or full surface/source conditions. Do not digitize an unidentified
  plot and silently label the result an independently qualified experiment.
- [PRESLHY E3.4](https://doi.org/10.35097/1319) is now a separately recorded pool discovery
  target. Its share-alike attachments remain withheld by the current project policy;
  the existence of an MIT native pool implementation does not change data-source terms.
- NIST SRD resources require resource-specific rights review; the agency's general
  government-work policy is not blanket permission for every SRD or extramural dataset.
- H2FillS download/registration terms were not automatically accepted or repackaged.

The TU Darmstadt hydrogen-engine collection ([DOI 10.48328/tudatalib-2291](https://doi.org/10.48328/tudatalib-2291)) declares CC BY 4.0/open access and provides flame-propagation and piston-surface-temperature figure data. A schema-neutral HDF5 inventory now exposes object structure without interpreting array values; source-specific mapping into immutable observations remains future work. These observations do not replace crank-angle pressure, cycle work, or valve-boundary measurements. Its eight HDF5 attachments remain excluded from release artifacts pending component-level rights review.

## Applying data to the models

Data already exercise native flow and temperature ingestion and an EOS acoustic comparison.
Acquiring a dataset does not justify assigning missing units, aligning logger clocks, fitting
all parameters simultaneously or marking a model validated. Next qualified comparisons
should predeclare the apparatus boundary, measured quantity, input reconstruction, fitting
subset, held-out experiment, error metric and acceptance criterion. Unknown inputs remain
visible in the run record.

## Complete AB2 channel profile

HYDRIDE_DATA.md adds bounded observation blocks for all365402 source rows across
seven sheets, retaining10014 missing-datetime rows rather than omitting them. This
complements355388 earlier shell time-series rows. Every acquired workbook matches
its original SHA/byte receipt. Numeric clocks, reference-volume flow, unresolved
pressure, five shell temperatures and cached volume fields retain separate roles.
The summary formula uses293.15K/101.31kPa, but this convention does not establish
MFC calibration P/T. One summary selects an intermediate source row; one desorption
sheet has an absorption-labelled summary. No mass/reference/pressure/shell-to-bed
repair or kinetic parameter fit follows. The finite storage reference uses authored
parameters, independently of these unresolved experimental inputs.

## Native equipment and instrument evidence

The new protection/vent/recovery levels use authored operating conditions and native
engine/EOS behavior; no missing manufacturer map, time constant or recovery-cycle
power is fitted from unrelated acquired logs. Instrument replay loads one already
hash-verified USN pressure export and demonstrates its unresolved meter-pressure
basis/location cannot automatically become absolute headspace process pressure.
This is a compatibility rejection, not response-model calibration or measured
validation. Acquisition totals remain265 attachments/4307123731bytes.

## Complete MHC compressor profile

Fleming's MHCv1.2 CC-BY4.0 archive now has a complete35-member CRC/SHA/MD5 and
metadata check,29 experiment workbooks,186 sheets and182 logger export groups.
The final offline audit took311.92s with at most two workbook snapshots. XML
contains655373 stored rows,11448663 numeric cells and3809671 cached formulas.
There are941985 XML error cells:2 in raw sheets and941983 in derived/other
sheets. Formula caches and copied selections are not independent measurements.

The observation profile retains1563461 recorder-grid rows, of which520726 are
populated and1042735 are padding.516306 have valid clocks;4420 populated rows
retain missing clocks and17 nonincreasing clock edges remain.108429 negative
reported-pressure values and10645 raw string-channel fields survive. Source
Date/Time encodings, workbook epochs and caller calendar origins are explicit;
no logger synchronization, gauge offset or reference-flow mass conversion is inferred.
Selected-cycle copies remain part of their raw physical experiment group.

HYDRIDE_COMPRESSOR_DATA.md and research/hydride_compressor_data.md record limits,
source identities, masks and the distinction between original argon/thermal cases
and hydrogen compression. Pressure/normal-flow bases, sensor positions, possible
unmeasured paths and material/heat-transfer parameters still need qualification
before an inventory or efficiency fit. Acquisition totals are unchanged. This
advances ingestion evidence without validating a hydride-compressor model.

## Complete thermal-effects observation profile

The pinned USN thermal-effects collection now has ten attachments: eight MAT
experiments and two descriptions,693385633bytes. Three missing MAT files were
acquired against the version1 metadata and publisher MD5; all earlier file hashes
and the original supporting metadata were preserved. The global acquired inventory
is268 attachments/4588753807bytes;24 of26 cataloged collections have acquired files.

Final LF-receipt audit consumes245 vectors/157964002 source scalar elements
exactly once. It preserves43779121 profile rows and7774576 unclocked signal rows.
There are no nonfinite source cells;151 nonphysical absolute temperatures retain
their raw values with masks. Negative radiation/combined-flux/flow/pressure and
all-zero channels are not silently repaired or declared defective.

Clock units/zeros and synchronization are unresolved. RHF3 and timech7 remain
separate by default; experiment2 Vent/T retains its complete unclocked vector
instead of borrowing another time. THF processing, sensor normals/locations,
per-experiment source conditions and bulk-temperature/pressure meaning need
further evidence. THERMAL_EFFECTS_DATA.md distinguishes those roles and explicitly
refuses automatic TimeSeries/duration/dose conversion. None of the new native
flame, conditional blast or inverse-heat levels is validated by this ingestion.

## Conditioned austenitic material observations

The source-specific EMBRITTLEMENT_DATA.md profile covers all9 acquired files:
113condition/property rows, five property definitions,103absolute paired values
and10ratio-only observations. Linked composition is a second representation;
40numeric/missing-element disagreements in15records remain separate. Exposure
pressure total/partial/gauge/purity, charging versus test conditions and four
absolute plastic-strain units remain unresolved. Do not feed reported exposure
pressure to an EOS or treat bibliography records as independent specimens.
No independent fracture/material-model validation follows from source arithmetic.
See research/embrittlement_data.md for exact rights, masks, line identities,
workbook/formula audits and receipts. Overall acquisition counts are unchanged.

## ELVHYS BLEVE shock-tube observations

SHOCK_TUBE_DATA.md now qualifies all42 acquired files, including38 numeric signal
CSVs and4,886,225rows/48,526,984finite cells. Zero-filled T2e samples are masked
without removing their raw values;27nonincreasing TEMP clocks block unsupported
TimeSeries promotion. Actual10us fast exports conflict with a10kHz README label,
and pressure headers/instrument/reference descriptions conflict. Keep each
reported pressure/recorder clock distinct. This is an LH2 BLEVE experiment with
12date-qualified runs and91omitted videos, not premixed CJ conditions or a
validated pressure-to-harm input. Overall acquisition counts remain unchanged.
Read the source-specific report for masks, negative observations and raw lineage.

## ELVHYS4.2 cold enclosure and missing O2 evidence

All198v1.1assets/1429209739bytes are acquired, with195numericCSVs:40CONC,
40PRES,40TEMP,40MISC and35FLMT. The40actual export cases differ from48nominal;
source-invalid27/28 stay masked and5ignited cases lack FLMT. Whole-source audit
has8150693rows/89332905sourcecells,85607986finite numeric values,
72078446ingestion-valid and17254459masked cells. These are correlated recorded
cells, including reported clocks/unknown roles, not independent experiments or
scientifically qualified samples.

H2 is a publisher-normalized and sampling-delay-aligned point observation,
not directly measured room O2. Pressure Var4/Var5 roles, Time unit/epoch/alignment,
separate BlastTime, several H2-versusT-only station names and instrument/range
conflicts remain unresolved. Ventilation volume flow is not H2 mass discharge.
No O2 history is invented by diluting a presumed unchanged air composition.
Direct native oxygen/thermal qualification requires additional source/observation
premises and independently held-out experiments. The separate Dryad O2 candidate
has no acquired files and contributes no validation evidence.

- [DataverseNO large-scale hydrogen explosion record](https://doi.org/10.18710/WSKBIJ): version 1.0 declares dataset-level CC0 1.0 and lists 59 public files totaling 96,861,179,314 bytes. The README, summary workbook and 207,853,888 B Test001 trace are acquired; publisher MD5 and local SHA-256 receipts are in `research/data/large-scale-open-hydrogen-explosion.toml`. The typed trace reader streams rows and retains pressure and raw voltage channels. A deferred Hangang case checks the complete selected trace. Remaining source, ambient, geometry and sensor-coordinate requirements prevent model comparison; see `LARGE_SCALE_H2_EXPLOSION_SUMMARY.md` and `LARGE_SCALE_H2_EXPLOSION_FDS_LINK_GAP.md`.

- [Residential hydrogen pilot PLC dataset](https://doi.org/10.5281/zenodo.15166733): the Zenodo v1 page documents 5-second samples for electrical subsystem powers, tank/fuel-cell pressures, electrolyzer and fuel-cell H2 flow, cumulative production, battery SOC and ambient temperature. Its listed 38.6 MB CSV has publisher MD5 `9a3c3e3b1668596854b43bfd790d3e0e`, but the official License field is empty; no file was acquired. Case `residential-h2-pilot-license-and-physical-boundary-gap` records the rights block and remaining clock, normal-liter reference-state, pressure-basis and equipment-boundary evidence needs. No data/model comparison is claimed; see the dedicated gap document.

- [HFCEV heavy-duty fleet telemetry](https://doi.org/10.5281/zenodo.23477229): the v1.0 primary record declares the dataset CC BY 4.0. Four selective files (README, channel dictionary, counter bit map, and one V001 operation-day CSV) totaling 2,383,383 B were acquired to the ignored raw-data area and matched publisher MD5s plus local SHA-256 hashes. The source reader retains receipt-time and device-time status, current/voltage, masks, and corrected-counter provenance; the adapter sums only publisher-attributed restored H2 mass increments whose previous valid counter rows are inside exact row-aligned windows. It compares aggregate mass only to a current existing `FuelCellTrace`, requiring caller evidence for clock alignment. It does not infer stack area, cell conditions, hydrogen state, or GPS, and this source comparison is not independent validation. See `HFCEV_FLEET_TELEMETRY.md` and `research/data/hfcev-fleet-telemetry.toml`.

- [ELVHYS 4.1 condensed-phase explosion campaign](https://doi.org/10.18710/YGHHTR): DataverseNO v1.1 declares CC0-1.0. Three selective files (README, metadata CSV, Test-1 vent-concentration CSV) totaling 1,035,075 B are acquired to the ignored raw-data area with publisher MD5 and local SHA-256 receipts. The reader retains source-relative seconds and H2/O2 vent concentrations as vol%; the adapter can compare physically admissible points against the existing `CanteraOxygenRoom` only with explicit clock, volume/state, gas-composition and vent-to-region evidence and exact model snapshot times. The source reports concentration sensor delay normalization, while some near-zero H2 readings are negative; these are preserved and excluded from physical comparisons, not clipped. No liquid-source boundary history, calibrated outlet flow, ignition, flame or explosion-pressure model is added. See `ELVHYS41_CONDENSED_EXPLOSION.md`.

- [ELVHYS 4.3.2 fire exposure of transfer-line sections](https://doi.org/10.18710/HDZLJ1): DataverseNO v1.0 declares CC0-1.0. The acquired subset is the README plus one Test-1 Lake Shore diode CSV (482,617 B), with publisher MD5 and local SHA-256 receipts. The source reader preserves time in minutes and two temperatures in kelvin: SD1 pipe surface and SD2 outlet process. Optional exact-time SD1 comparison to a native radial wall surface requires external evidence for sensor position, pipe/domain equivalence and clock offset. The README says silicon diodes were not calibrated; no fit, heat-flux inference or physical validation is claimed. The other 12 public files, including pressure/thermocouple data and videos, were not acquired. See `ELVHYS432_FIRELINE.md`.

- [Wasserstoffatlas / Hydrogen Map](https://doi.org/10.5281/zenodo.10548190): the official file-level table assigns CC BY 4.0 to `Bestand.csv`, although Zenodo's record metadata declares CC0; the reader follows the specific file-level term and retains creator/DOI attribution. The acquired 181,145-byte CSV has 1,049 facility inventory rows and 20 columns. A typed source-bound reader preserves source tokens, provider-lineage fields, and point WKT. Quantity units/measurement bases and CSV CRS are not normalized or inferred, and no process, spatial-distance, safety, or consequence validation is claimed. See `WASSERSTOFFATLAS_INVENTORY.md` and `research/data/wasserstoffatlas-hydrogen-map.toml`.

- [Clashach H2 micro-CT/PNM](https://doi.org/10.5281/zenodo.10500728): Zenodo v2 declares CC BY 4.0. Only the 214,983-byte publisher README is acquired and hashed. Its pore/throat files are 16-bit label volumes at 7 μm voxels, not tabular pore geometry or flow properties; acquisition of those archives and direct parameterization of the present radial reservoir model are deferred. The source-gap Hangang case preserves exact dimensions, labels and missing physical mapping; no model validation is claimed. See `CLASHACH_H2_PNM_MODEL_LINK_GAP.md`.

- [Pd leaky-coating sorption traces](https://doi.org/10.5281/zenodo.6670268): Zenodo v1 declares CC BY 4.0. Four Figure 4 text files (468,409 B) provide measured channels in seconds and mbar for feed-pressure changes and UHV mass-spectrometer signal during Pd membrane absorption/desorption. A hash-pinned reader preserves separate source clocks and channels. The UHV signal scale is arbitrary relative to feed pressure, and no absolute feed baseline or initial membrane state is provided. This source is not used to fit diffusion or hydride kinetics; the Hangang case checks byte/schema ingestion only. See `LEAKY_COATING_HYDRIDE_SORPTION.md`.
# HRS registry and process-trace gap

- [H2-Stations registry export](https://map.h2-stations.eu/): the Clean Hydrogen Joint Undertaking platform terms state CC BY 4.0. One rolling 15,024-byte workbook snapshot is hash-pinned locally; its single 166×7 worksheet is station registry metadata. The new Python reader retains source rows and values without inferring status, capacity, location reference, or process performance. This is not refuelling validation data. See `H2_STATIONS_DATA.md` and `research/data/h2-stations-hrs-inventory.toml`.
- [Hydrogen refuelling process traces](HYDROGEN_REFUELLING_PROCESS_DATA_GAP.md): refreshed audit covers CARB's measured HyStEP in-use study, NREL/NLR station composite products and protected Hydrogen Secure Data Center records, H2FillS registration/license materials, H2-Stations API v2 and public HyStEP technical records. CARB publishes selected measured pressure, temperature and mass-flow report figures but no raw event files or reuse grant; NREL products are aggregated; H2-Stations is CC BY 4.0 operational metadata/status with token-authenticated v2, not per-fill synchronized sensor data. Powertech/H2Protocol still lacks an inspectable file inventory and explicit rights. No trace is acquired or digitized. No reviewed package met the per-file, schema, timebase and rights contract; source gap remains open.

# Cryogenic phase-change source qualification

`cryo-neutron-phase-change` is a source-bound NIST/Mendeley observation subset under CC BY 4.0. The selected DAQ, image, and rate tables retain publisher tokens, source units, and separate clocks. The experimental cell and its sensor/thermal boundaries do not map to the repository's finite pressure-vessel model; the rate column's unit is unresolved. No model fitting or validation claim is made. Consult `docs/CRYO_NEUTRON_PHASE_CHANGE_DATA.md` for attribution and field-level details.

## Electrolyzer process-data discovery update

The PEM accelerated-stress-testing candidate (`pemwe-ast-hannover`, 709,873,892-byte CSV; 1,402 h campaign) remains metadata-only and has not been schema-qualified. The current-ripple PEM dataset is separately acquired and schema-reviewed as described above. The alkaline electrolyte-purity WUR record identifies current and voltage measurements at 25 °C and atmospheric pressure, but lacks retrievable resource inventory, field units and timebase. See `ELECTROLYZER_PROCESS_DATA_DISCOVERY.md` and the individual `research/data/*` receipts.


## Measured-data comparison checkpoint — 2026-11-02

Four selected own-model closures were compared with real experiments using separated calibration/evaluation data: effectivepermeance(64train/32heldout),normalizedhydridekinetics(100train/44heldoutcurves),PEMpolarizationlosses(46train/56heldoutcontexts),andfixed-coefficientgasnozzle(13train/22heldoutscanrows). Results are conditional measured comparisons, not formal qualification; qualifiedcount remains0. Permeance heldoutMARE2.15–4.06%; hydride mean-curveRMSE4.49/4.86percentagepoints; PEMRMSE23.102mV; nozzleMARE29.83%. Native engine internal physics and whole-facility physics were excluded. All365productPythonfiles match the prior basic checkpoint; no productionmodel/default changed. See [PHYSICAL_VALIDATION_CAMPAIGN.md](PHYSICAL_VALIDATION_CAMPAIGN.md), its source/identifiability limits and artifacts/physical-validation-20261102/summary.json. Raw datasets remain ignored; two original public source-metadata ledgers and four replay scripts were added. No further calculation is running.

