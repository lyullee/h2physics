# Scientific sources and method decisions

References establish equations, API semantics or experimental provenance; they do not
transfer an author's validation to this implementation. Source-specific coefficients and
third-party implementations are not copied into the original library.

| Area | Public primary reference | Implementation decision and evidence |
|---|---|---|
| Native nonideal isothermal pipe momentum | [CoolProp homogeneous derivative API](https://coolprop.org/coolprop/HighLevelAPI.html); [Conner and Manousiouthakis, 2024 author preprint](https://arxiv.org/abs/2410.20292) | The existing compressible Darcy function integrates native density against pressure with constant declared viscosity and independently reconstructs the pressure path. Its mass-flux/acceleration relation is derived from mass and momentum conservation. No cubic EOS, source code or parameter fit is copied. Native tests include a density-variable ODE, ideal limit and rejected phase/sonic/definition failures. Experimental qualification remains open. |
| Caloric transient pipe networks | [Rusanov (1962)](https://doi.org/10.1016/0041-5553(62)90062-9); [Lang and Mindt (2018), Euler junction coupling conditions](https://doi.org/10.3934/nhm.2018008); [Gyrya and Zlotnik (2019), transient gas-network discretization](https://doi.org/10.1016/j.apm.2018.07.051) | `CaloricPipeNetworkWaveModel` reuses the project's single-pipe caloric Euler/Rusanov kernel over a connected graph. The current junction closure is a zero-volume, adiabatic, perfectly mixed resting node solved from the exact applied mass and total-energy fluxes, with an entropy-production inequality; it is not the characteristic entropy-preserving coupling law in Lang and Mindt. The three synthetic Hangang contracts are deferred. Junction loss, volume, momentum, measured-pipeline behavior and facility qualification remain outside this level. |
| Transient conduction in a finite spherical shell | [MIT OpenCourseWare, 3.185 heat-diffusion handout](https://ocw.mit.edu/courses/3-185-transport-phenomena-in-materials-engineering-fall-2003/927ddb6b3dfc423de5570a0070614129_handout_htrans.pdf) and [3.044 transient-conduction notes](https://ocw.mit.edu/courses/3-044-materials-processing-spring-2013/resources/mit3_044s13_tranheacondsol/) | `spherical_shell_heat_history()` uses spherical finite-volume cell measures and exact radial conduction resistance, with the existing explicit solid-property and thermal-boundary contracts. Boundary heat and stored enthalpy are integrated as separate ledgers. The registered analytic steady-annulus and energy checks are deferred; this model is not yet numerically exercised or independently qualified. It does not provide internal-fluid feedback, boiling, stress or axial effects. |
| Buried-pipeline positional observation handling | [Guo (2025), version 2 dataset](https://doi.org/10.17632/x8zkds4fyn.2) | `load_buried_pipeline_numeric_table()` admits only publisher-listed CC BY 4.0 files by byte count and SHA-256. `BuriedPipelineNumericTable.column_series()` preserves one positional column with its raw cell tokens, mask, row IDs and file digest. The reader does not infer a measured quantity, unit, clock or observation operator because the acquired release does not provide that dictionary. This is ingestion provenance, not pipeline-model validation. |
| Mixture composition algebra | [IUPAC Gold Book: amount fraction](https://goldbook.iupac.org/terms/view/A00296); [mass fraction](https://goldbook.iupac.org/terms/view/M03722); [molar mass](https://goldbook.iupac.org/terms/view/12214) | `GasComposition` converts between component amount and mass bases using declared molar masses and checks normalized, finite composition/flow ledgers. It owns no equation of state, fugacity or mixture transport closure. Deferred algebraic checks are not EOS or experimental validation. |
| Native ideal-mixture property binding | [Cantera 3.2 thermodynamic API](https://cantera.org/3.2/python/thermo.html); [IUPAC molar mass](https://goldbook.iupac.org/terms/view/12214) | `CanteraFrozenGasProperties.from_gas_composition` compares declared kg/mol values against Cantera's documented kg/kmol species weights before constructing a provider or changing the native phase, then converts the shared mole-basis composition to mass fractions. A machine-precision sum repair is bounded and retained; caller composition identity is checked at subsequent state calls. Cantera retains EOS/property ownership; the integration case is authored and deferred, without real-gas, spin or experimental-mixture claims. |
| Hydrogen EOS | [Leachman et al. (2009)](https://doi.org/10.1063/1.3160306); [CoolProp fluid record](https://coolprop.org/fluid_properties/fluids/Hydrogen.html) | Use the maintained library, preserve spin/reference identity; do not implement another EOS fit. |
| Geological-material H2 adsorption observations | [Corrected Zenodo latest-version record, CC BY 4.0](https://zenodo.org/records/22305898); [license text](https://creativecommons.org/licenses/by/4.0/); [Zenodo license scope](https://developers.zenodo.org/#licenses) | The archive reports signed excess adsorption, blank calibration and uncertainty limits. Its source/data dictionary and archive hashes are recorded in `research/data/geological-adsorption-2026-09.toml`. Do not treat these excess-loading measurements as absolute uptake or vessel-capacity data without a separately evidenced conversion; raw table schemas are not yet audited. |
| Real-gas fixed mixtures | [CoolProp mixture model and supported flash pairs](https://coolprop.org/fluid_properties/Mixtures.html); [CoolProp low-level mixture API](https://coolprop.org/coolprop/LowLevelAPI.html) | `CoolPropMixtureProperties` binds an identified `GasComposition` to HEOS fluid names and mole fractions, checks component molar masses, and uses native PT/PQ/TQ flashes. Optional PH/PS/P-density calls use bounded scalar inversion through PT states with declared temperature bounds and single-gas monotonicity checks. An opt-in immutable `MixtureInverseGrid` stores sampled enthalpy, entropy and density versus pressure/temperature; reuse requires the exact mixture fingerprint, property basis and inverse domain, while a candidate root bracket is reevaluated at the requested pressure. This is an initial-bracket aid, not an independently qualified EOS table. Installed-release binary-pair coverage is required; no simple mixing-rule estimate or mixture transport law is inferred. Its deferred Nurion case checks API/round-trip/energy identity and grid reuse only, not measured-mixture accuracy or speedup. |
| Fixed-volume mixture inventory flash | [CoolProp mixture PQ flash and `AbstractState` outputs](https://coolprop.org/fluid_properties/Mixtures.html); [SciPy bounded least-squares solver](https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.least_squares.html) | `flash_two_phase_inventory_vu()` solves one bounded two-phase state for fixed component moles, total volume and internal energy using native phase compositions/densities/enthalpies. Multiple caller seeds must converge to one clustered pressure/quality root; packet admission independently reconstructs each species, phase volume and energy. This local seed search is not a global uniqueness proof. It does not integrate changing inventories, ports or events; those remain Request032 native work. The synthetic PQ round-trip case is deferred. |
| Property service | [CoolProp low-level API](https://coolprop.org/coolprop/LowLevelAPI.html); [library paper](https://doi.org/10.1021/ie4033999) | Reuse a protected AbstractState; compare PT and inverse state inputs. |
| Acceleration | [CoolProp tabular methods](https://coolprop.org/coolprop/Tabular.html) | Benchmark actual public-state calls. Preserve native-table negative results and expose an explicit dependent-u option. Never infer interpolation quality from speed. |
| Hydride plateau | [Ge, Energy Storage](https://doi.org/10.1002/est2.504) | Implement only the stated Van't Hoff plateau/slope/hysteresis level, with replaceable equilibrium objects. Full phase-region reconstruction is not claimed. |
| Hydride kinetics/heat | [Muthukumar et al.](https://doi.org/10.1016/j.ijhydene.2007.08.010) | Independent reservoir-driven capacity/rate/thermal formulation, with no alloy parameter table. Use a stiff adaptive solver and conservation diagnostics. |
| Spatial hydrides | [Font et al., 2025](https://arxiv.org/abs/2507.22083) | Reviewed as a higher-resolution candidate. Not yet implemented. Temperature/pressure coupling and spatial kinetic variation need identifiable measurements, rather than extra fitted functions by default. |
| Hydride identification | [Chen et al., author manuscript](https://web.mat.upc.edu/carles.batlle/fitxers/JES2025.pdf) | Identifiability precedes multi-parameter fitting. Shell-only measurements do not identify every internal heat/kinetic parameter. No source optimizer code is reused. |
| Bulk and surface-resistance permeation | [NASA/TM-2019-220189](https://ntrs.nasa.gov/citations/20190030498); [Shu and Watanabe, Phys. Rev. B 55, 9348 (1997)](https://doi.org/10.1103/PhysRevB.55.9348) | The existing `quasi_steady_permeation_history` evaluates a carrier-explicit Fick relation on caller boundaries. The new `steady_permeation_with_surface_resistance` combines two declared linear transfer films with that bulk resistance on one mapped concentration basis; its algebra follows continuity of steady flux and separately retained film/bulk drops. This does not fit surface coefficients, model surface chemistry, or provide transient membrane response. |
| Radial hydrogen transport in a pipe wall | [Auinger et al. (2023), experimentally compared cylindrical pipeline-steel model, CC BY 4.0](https://doi.org/10.1016/j.ijhydene.2023.05.181); [version-of-record repository and license](https://repositum.tuwien.at/handle/20.500.12708/190151) | `DiffusionMesh.cylindrical_shell` adds exact cylindrical shell volumes, lateral areas and integrated radial Fick resistance to the existing conservative mobile/trap solver. This adopts only radial geometry and the shared Fick balance, not the paper's uptake kinetics or coefficients. The registered steady logarithmic-profile and inventory contract is deferred. The level excludes axial/end effects and stress-driven chemical-potential transport; material calibration remains separate. |
| Normalized hydrogen permeation in MS1700 and QP1180 | [Macoretta and Belardini, Mendeley Data v1, CC BY 4.0](https://doi.org/10.17632/zj7zh24frt.1) | The 39,455-byte MAT attachment is acquired under a publisher-recorded CC BY 4.0 grant and its SHA-256 matches the file listing. Header inspection identifies two grade arrays with 2,197 and 1,333 rows; the SciPy reader validates and retains their two columns in source order, using the publisher's normalized-time/normalized-flux description. No dimensional diffusion or solubility coefficient is inferred. Detailed normalization and in-file third-party rights review remain open; see `research/data/hydrogen-diffusivity-ms1700-qp1180.toml`. |
| Diffusion/traps | [FESTIM research paper](https://doi.org/10.1016/j.ijhydene.2024.03.184); [theory](https://festim.readthedocs.io/en/latest/theory.html) | Portable reduced planar finite-volume level with molar units, finite trap capacity, sparse BDF and an analytic series check. No FESTIM source or parameter table copied. |
| Hydrogen surface-controlled permeation | [Turnbull and Wright, NPL Report MAT 69 (2014)](https://eprintspublications.npl.co.uk/6253/); [Zhang, Zheng, and Wu (1999)](https://doi.org/10.1149/1.1391836) | `SurfaceFilmCondition` adds a caller-parameterized linear Robin transfer boundary to the shared bulk diffusion owner. It accepts an already mapped same-carrier solid-basis concentration and transfer velocity; it does not infer fugacity, electrochemical charging, surface reaction rates, or material coefficients. Its analytical profile and conservation contract remain deferred. |
| Hydrogen concentration eigenstrain | [Frolova et al. (2022)](https://doi.org/10.1002/zamm.202100505); [Connolly, Malavé, and Martin (2022)](https://doi.org/10.1103/PhysRevMaterials.6.L040601) | `radial_hydrogen_eigenstrain_cylinder()` extends the existing long-cylinder thermoelastic BVP with a caller-provided scalar isotropic eigenstrain profile and retains pressure/thermal and combined fields plus component-wise differences. Coefficients, concentration basis and reference state remain caller-owned; the API does not feed stress back to diffusion. Its deferred contract is pending. |
| Higher-resolution materials | [FESTIM installation](https://festim.readthedocs.io/en/latest/installation.html) | Prefer the specialized FE engine for spatial material/thermal/stress extensions after review. Its current FEniCSx dependency requires WSL/Linux on this Windows host; no system/WSL installation was made. |
| Cylinder thermoelasticity | [MIT OCW structural mechanics lecture 12](https://ocw.mit.edu/courses/22-314j-structural-mechanics-in-nuclear-power-technology-fall-2006/e6664ebdbc4bcad10e2602deb9bf389d_m12.pdf); [Applied Mechanics of Solids, axisymmetric thick cylinder](https://solidmechanics.org/text/Chapter4_1/Chapter4_1.htm) | Extend the existing Lamé pressure field by isotropic constitutive compatibility for a uniform wall-temperature change and explicit axial strain boundary. No radial thermal-gradient solution or code-design acceptance is implied. |
| Electrochemical systems | [NREL report 83155](https://www.nrel.gov/docs/fy23osti/83155.pdf); [NREL/CP-550-47302](https://www.nrel.gov/docs/fy10osti/47302.pdf) | One native polarization/Faraday/reaction-energy core. Reaction-energy and water-phase references are explicit; empirical coefficients and Faradaic-loss heat are not invented. |
| Reacting mixtures | [Cantera equilibrium API](https://cantera.org/3.2/python/thermo.html); [reactor API](https://cantera.org/3.2/python/zerodim.html) | Reuse the solver and pass native phase factories. Record source hashes/domains and element/energy diagnostics. |
| Finite gas/surface thermal response | [Cantera 3.2 reactor API](https://cantera.org/3.2/python/zerodim.html); [control-volume reactor energy equation](https://cantera.org/3.2/reference/reactors/controlreactor.html); [reactor interactions](https://cantera.org/3.2/reference/reactors/interactions.html) | The native Cantera gas/surface ReactorNet has an optional energy-on path with an explicit fixed-temperature Reservoir/Wall boundary. Native kinetics and the reactor energy equation remain the owner; a sampled output-grid trapezoidal heat ledger is checked against retained gas/adsorbate U. No catalyst thermal mass, spatial bed, or caller-supplied heat-transfer coefficient is inferred. The software contract is deferred to Nurion. |
| Flame transport | [Cantera 1D API](https://cantera.org/3.2/python/onedim.html) | Use a native premixed flame with optional multicomponent/Soret transport. Grid and domain refinement are recorded separately from experimental validation. |
| Shared short nozzle | [NASA Glenn analytical gas relations](https://www.grc.nasa.gov/www/k-12/airplane/mflchk.html); [CoolProp phase inputs](https://coolprop.org/coolprop/HighLevelAPI.html) | Original continuity/isentropic-energy kernel for all inlet phases; include pressure endpoints and report numerical convergence. Ideal-gas limits are numerical verification, not real-fluid discharge validation. |

## Current comparisons

`research/property_tables.md`, `research/acoustic_comparison.md`,
`research/native_cantera.md`, `research/native_lh2dt.toml` and the verification scripts
contain actual positive/negative results. The acoustic compilation is newer than the EOS,
but some historical observations may already have been used in EOS development. This
comparison cannot be treated as wholly independent holdout validation.

The exact [PSA-Dyna revision](https://github.com/lyullee/psa-dyna/tree/a26a8ef687c90cd4a5c18d38aaa4209ea5c5dcd6)
owns competitive equilibrium and bed equations. `research/native_psa.md` and
`native_psa_bed.md` verify the local SI/native boundaries with authored parameters;
no source material coefficients or solver code are copied. The fixed native temperature
guard remains visible and is the subject of a concrete cryogenic extension request.

[SciPy least_squares](https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.least_squares.html)
is used for bounded native observation operators. Whole-group splitting, per-column origins,
data fingerprints and scaled-Jacobian diagnostics support research reproducibility without
turning curve reproduction into experimental qualification.

The reviewed [PRISM HEM implementation](https://github.com/lyullee/prism/blob/884b0553341beb2d51d1d3c563f86982f378e160/lh2-tno/src/prism_lh2_models/lh2_critical_flow.py)
uses the same equilibrium physical level. The new original shared kernel addresses explicit
phase inputs, back-pressure endpoints and failure/convergence visibility; request 006
specifies consolidation by delegation. `research/native_release.md` checks actual native
tank depletion. The current native negative-flow enthalpy policy supports only bulk withdrawal.

[Sandia's official HyRAM+ overview](https://energy.sandia.gov/programs/sustainable-transportation/hydrogen/hydrogen-safety-codes-and-standards/hyram/)
was checked as a maintained hydrogen-safety comparison candidate (6.1 release, September 2025).
Its GPL-3.0 solver source is not bundled or imported by this Apache-2.0 core. This is a
dependency choice, not a claim that general conservation equations have that source license.
The current manual download was unavailable during this review; no unread manual equation
or independent validation result is claimed as evidence for the new nozzle.

Modern numerical tools are selected for a demonstrated benefit at an explicit model level.
An updated publication alone does not establish better physics, and a more detailed mesh
does not repair unknown experimental boundary conditions.

The public [PRESLHY discharge collection](https://doi.org/10.35097/1187), CC BY 4.0,
now exercises the shared nozzle through a conditional measured-P/T inventory balance.
The observation operator, whole-experiment holdout, explicit assumptions and remaining
metrology gaps are documented in PRESLHY_COMPARISON.md. No independent flow validation is
inferred from reconstructing inventory with the same EOS used by the nozzle.

[SciPy brentq](https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.brentq.html)
resolves the equivalent single-phase sonic condition on a sign-changing bracket when
the provider supplies consistent sound speed. [CoolProp's low-level interface](https://coolprop.org/coolprop/LowLevelAPI.html)
retains the common state backend. Cases without the optional single-phase property retain
the shared flux-maximization path. Numerical failures and a strictly opt-in quality-roundoff
policy are recorded rather than hiding EOS violations or relaxing pressure/flux gates.

`FiniteAdsorptionVessel.pressure_for_inventory()` samples a caller-selected
fixed-temperature, frozen-composition pressure interval, rejects sampled decreases
or multiple target crossings, and applies [SciPy brentq](https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.brentq.html)
only to the remaining local sign-changing bracket. This is scalar inversion of
provider-owned endpoint inventory; it does not add an adsorption isotherm, prove
monotonicity between samples or validate material parameters.

The exact [LH2DT public revision](https://github.com/lyullee/lh2dt_models/tree/b2f276333c1b1793c39f25763703d196d36742ec)
owns the equipment/phase/network implementations. Host code maps native objects and uses
mass/enthalpy/power identities to check the boundaries. Gas/HEM laminar limits are compared
to the analytical cylindrical-flow relation; HEM mixture viscosity remains the native
declared phase-weighted approximation. A SciPy DOP853 enthalpy-coordinate integration
independently checks the native vaporizer's numerical quadrature on the same EOS.
This is numerical verification, not independent validation of friction, maps or heat transfer.

The measured repeated-flash cost justified a structural facade over the existing protected
CoolProp state. It preserves the HEOS and native state factory, compares additional inverse
inputs, and times actual complete native states and the coupled solver separately.
The 22.7 versus 2.34 speed ratios describe different workloads. Cold tables remain subject
to phase/domain/inverse-state qualification. The native external-heat ledger mismatch and
explicit host bridge are documented in request 007 with a reproduced negative case.

The same pinned engine's [finite pipe](https://github.com/lyullee/lh2dt_models/blob/b2f276333c1b1793c39f25763703d196d36742ec/src/lh2dt/dynamic_pipe.py),
[finite vaporizer](https://github.com/lyullee/lh2dt_models/blob/b2f276333c1b1793c39f25763703d196d36742ec/src/lh2dt/dynamic_vaporizer.py)
and [dynamic network](https://github.com/lyullee/lh2dt_models/blob/b2f276333c1b1793c39f25763703d196d36742ec/src/lh2dt/dynamic_network.py)
are reused through actual objects. Original host composition stops at prescribed command
times, translates callback clocks and checks fluid-plus-wall storage against integrated
boundary transfers. The wall-only linear ODE has an independently evaluated analytic
solution. A comparison with unsplit discontinuous controls shows why matching the specified
switch time is additional evidence beyond a conserved numerical trajectory. No source
solver, explanatory prose or parameter table is copied; synthetic inputs are authored here.

The combined supply template reuses the same [native pump implementation](https://github.com/lyullee/lh2dt_models/blob/b2f276333c1b1793c39f25763703d196d36742ec/src/lh2dt/pump.py)
and the already reviewed finite-device/phase equations. An original host mode selector
delegates actual components with separate explicit power readers; it does not invent a
zero-speed map or rotor dynamics. The generic sampled-rate integral retains both command
limits and declares linear-sample trapezoidal quadrature. An analytic step-rate test and
the independent external inventory comparison verify that numerical boundary. Longer
heating/reverse-transfer refinement retains an initially failed coarse-pair gate and
independently checks accepted Darcy pressure loss, without copying a new pipe solver.

The finer check exposed a roughly 44 Pa inconsistency in native reported friction/flow
at an authored transition state. An original common bracketed Darcy kernel now verifies
its final constitutive residual. A discontinuity in the original friction law is retained
as a separate negative result: bracketing alone cannot close a missing root. The explicit
continuous closure is the direct [fluids Churchill_1977 API](https://fluids.readthedocs.io/fluids.friction.html#fluids.friction.Churchill_1977),
with [MIT license](https://github.com/CalebBell/fluids/blob/master/LICENSE.txt), exact installed
version and module checksum. It is called as a dependency; no implementation or roughness
table is copied. This improves verified numerical consistency, with experimental validity
of the homogeneous-mixture empirical closure still requiring data. HYDRAULICS.md and
request 009 distinguish those responsibilities and consolidate equivalent solvers.

The measured PEM source is Steffen Brundiers (2026),
[Zenodo v1](https://doi.org/10.5281/zenodo.19361280), CC BY 4.0; metadata and rights
are retained in the acquisition receipt. The primary
[university dataset record](https://research.uni-hannover.de/de/datasets/datasets-time-resolved-performance-and-stability-of-different-gas/)
describes cell/protocol/channel meaning. Actual CSV headers, zero placeholders, acquired
sweeps and DC gaps are checked separately from nominal descriptions. Complex response
is reconstructed as magnitude times exp(j phase), with explicitly declared phase sign.
No publication prose, source plot, example code or data file is copied into the release.

[Murbach et al., impedance.py (2020)](https://doi.org/10.21105/joss.02349) and the
[native API](https://impedancepy.readthedocs.io/en/latest/circuits.html) identify the
equivalent-circuit owner. The released MIT 1.7.1 package is used as an optional dependency,
with actual object/parameter-name/units checks and a source checksum. Development
documentation showing 1.8 does not establish a released installation. The alpha=1
series-L/R + parallel-RC analytic limit independently verifies the adapter's complex
convention and parameters; it is not a second production circuit implementation.
The existing SciPy bounded least-squares/SVD engine estimates effective parameters.
Whole-sweep repeated-protocol failures and fixed-coefficient cross-cell failures remain
reported. No unique electrode/crossover mechanism or independent-source qualification
is inferred. PEM_IMPEDANCE.md records the full operator, selected data, units and limits.

The optional pool owner is the exact MIT
[DynamicLH2PoolX revision](https://github.com/lyullee/DynamicLH2PoolX/tree/6a700e8e183039bbb81803bacc416f6c9117ed71).
Its [radial solver](https://github.com/lyullee/DynamicLH2PoolX/blob/6a700e8e183039bbb81803bacc416f6c9117ed71/src/dynamiclh2poolx/spreading.py),
[thermal closures](https://github.com/lyullee/DynamicLH2PoolX/blob/6a700e8e183039bbb81803bacc416f6c9117ed71/src/dynamiclh2poolx/substrates.py)
and actual runner were inspected as independently installed native implementations.
The underlying shallow-layer work is bibliographically identified in
[Dienhart, JUEL-3155 (1995)](https://juser.fz-juelich.de/record/860517).
No source solver, numerical example or digitised source figure is copied into this host.
Original host code maps clocks/identities, independently integrates a declared step
history and conservatively projects cumulative vapor to finite intervals. An independent
quadrature of the capped conduction relation checks the selected thermal component.

The native default uses normal Hydrogen at constant saturation pressure. The checked
PyPI pre-release 0.2.0rc2 and GitHub revision have identical module bytes; a release
label alone is not used as proof of equivalence. Negative clock, domain and coarse-mesh
cases are retained in `research/native_pool.md`. No instantaneous source footprint or
complete energy/momentum ledger is supplied by the present interface. The
[PRESLHY E3.4 metadata](https://doi.org/10.35097/1319) establish a relevant experiment
collection and CC BY-SA 4.0 terms; its eleven attachments remain withheld by the default
reuse policy. Upstream component evidence and digitised derivatives are not reclassified
as independent host validation. NATIVE_POOL.md and request 010 document the remaining work.

The optional gas/jet owner is the exact MIT
[DEGALI snapshot](https://github.com/lyullee/degali/tree/6ead182dc19039725a0b40811b48c6d39f947790).
The independently installed
[supplied-throat expansion](https://github.com/lyullee/degali/blob/6ead182dc19039725a0b40811b48c6d39f947790/src/degali/addons/notional.py)
and [conserved jet](https://github.com/lyullee/degali/blob/6ead182dc19039725a0b40811b48c6d39f947790/src/degali/addons/axisymmetric_jet.py)
provide the actual equations and numerical owner. Their bibliographic basis includes
Sandia's SAND2025-04942 technical reference, listed on the
[official HyRAM+ documentation page](https://energy.sandia.gov/programs/sustainable-transportation/hydrogen/hydrogen-safety-codes-and-standards/hyram/).
HyRAM+ implementation is separately installed for the selected optional native path; it is not copied or bundled by this host. Native DEGALI is a
separate reviewed MIT dependency, not a transfer of HyRAM+ field validation.

The host's original work checks supplied mass, effective-area pressure thrust and h+KE;
maps explicit coordinates and component enthalpy references; and audits actual native
results. The thermal/composition profile has non-Gaussian density. Its vertical source
must therefore use the actual section integral of gravity times ambient-minus-mixture
density. The explicit thin native subclass replaces only that source and retains native
profiles, Jacobian, entrainment and integration. No native solver text, source example,
experimental curve or table is copied. Initial root failures, coarse conservation failures
and the remaining cold energy failure are recorded in `research/native_degali.md`.
No coefficients are fitted and no field accuracy or complete real-mixture EOS is claimed.

The measured spatial-jet source is [Grune and Sempert's HyTunnel-CS record](https://doi.org/10.5281/zenodo.4668554),
version 4668554, CC BY 4.0. Its original numeric workbooks, source description and hashes
are acquired separately. The schema profile and original analysis read spatial means/
maxima/minima without digitising a source figure. Actual cell/label/statistic conflicts
remain in masks and issues; no data-derived coefficient is inserted into the native jet.
The [primary apparatus study](https://hysafe.info/uploads/papers/2021/41.pdf) establishes
horizontal jet scans, pipe pressure instrumentation and suction sampling. Those features
motivate separate source/observation assumptions rather than a mixed-box validation claim.

The shared nozzle is inverted through SciPy's bracketed scalar root at fixed declared
T0/area; no new flow law is introduced. A source-flow-conditioned equivalent pressure is
not relabeled a measured nozzle inlet. Native five-flux energy and source targets undergo
the original affine transformation E'=E+C*m_H2. Subtracting C times the H2 mass balance
recovers the original energy equation. This is numerical reference conditioning, not a
changed heat input or fitted mixing coefficient. The [CoolProp reference-state documentation](https://coolprop.org/coolprop/HighLevelAPI.html#reference-states)
also distinguishes relative thermodynamic references; no global CoolProp reference is
modified here. Physical audits retain their original reference, scale and limits.

The dry-gas spatial observer uses native profiles, piecewise-linear centreline projection
and the mass-to-mole definition under an explicit gas-volume approximation. Tail use,
temperature/pressure/humidity envelope and unbounded geometry are declared. Numerical
reference invariance is checked independently of field accuracy. Failed energy and
concentration targets remain in `research/hytunnel_jets.md`.

The [2026 primary wind-model study](https://doi.org/10.58895/hysafe.74) is a relevant
newer fidelity candidate for vector wind and vent stacks. It is not installed/copied as
a substitute for the selected native path. Existing native yaw/vector-wind research
levels need their own conservative interfaces, reversal/domain and data checks before
being used for the dataset's co/counter/cross flow. The current calm case does not
inherit that study's validation or an optimized coefficient set.

The computed carrier input is Hassan Harb's [QM9-LOHC Zenodo release](https://doi.org/10.5281/zenodo.10926772),
CC BY 4.0, interpreted with the [primary descriptor](https://doi.org/10.1038/s41597-025-04468-0).
The host authors its own conservation/duty calculations and data profile. Computed
standard gas dehydrogenation heat is normalized from kJ/mol H2 to J/mol reaction extent
at 298.15 K and 101325 Pa. It is not measured liquid reaction evidence. Duplicate and
contradictory molecular pairs remain visible; no source program/notebook is executed or
reproduced. Acquisition receipts retain the exact archive and source metadata hashes.

Molecular interpretation reuses native [RDKit APIs](https://rdkit.org/docs/GettingStartedInPython.html)
and [BSD-3-Clause core](https://github.com/rdkit/rdkit/blob/master/license.txt).
The separately installed wheel builder's license is MIT; these scopes are distinguished
in research/rdkit_dependency.toml. Native average molecular weights are used consistently
for both carrier and H2; source capacity discrepancies are retained. Public test fixtures
use independently chosen chemistry/heat values, not copied data rows.

The caloric path uses the [native Cantera thermodynamic API](https://cantera.org/3.2/python/thermo.html)
and installed [GRI-Mech input](https://cantera.org/3.2/examples/input/gri30.html).
The reported gas example is verification using source-distributed thermochemistry,
not selection of a qualified catalyst mechanism. No mechanism is bundled. Fixed extent
solves a different constraint from native equilibrium or a kinetic reactor; those
existing engines remain reused. The independently authored finite balance is
n_out=n_in+nu*extent, with constant-pressure heat equal to the difference of total
species enthalpies. Caloric functions must share formation/reference offsets; arbitrary
pure-fluid sensible zeros do not determine chemical reaction heat.

The preferred native gas path now uses the separately installed [HyRAM+ Python engine](https://github.com/sandialabs/hyram/blob/master/src/hyram/README.md),
release 6.1, GPL-3.0-only. The host's original coupling checks compare the integral of
rho*Y*V over the native Gaussian section to native upstream mass. The general radial
Gaussian integral is authored as a conservation audit, without copying a native solver.
Initial mismatch and ODE drift remain distinct; default model constants are not fitted
or corrected to pass. Native source/field qualification does not follow from installation.
The separately installed MIT [SLABx](https://github.com/lyullee/slabx) and
[SLABx-LH2](https://github.com/lyullee/slabx-lh2) retain EOS/water, spreading, entrainment,
plume/puff integration and post-run premise diagnostics. The host maps a qualified steady
vapor interval source and retains both pass/fail native trajectories. Native source
history/temperature losses found in SourceLedger conversion are targeted by request012.

The pressure-peaking input is [Lach and Gaathaug's versioned USN record](https://doi.org/10.23642/usn.17932439.v1),
CC BY4.0. The original profile reads independently verified MAT unit/channel metadata and
XLSX calibration/header/clock cells; the source handling guide's inconsistent pressure
column is retained as an issue. No calibration, experiment table, diagram or explanatory
source text is copied. Full source checksums, bounded block rules and masks remain in
research/pressure_peaking_data.md; this is qualification of observations, not validation.

Cantera's [ideal-gas reactor definition](https://cantera.org/3.2/reference/reactors/ideal-gas-reactor.html)
and [documented public extension hooks](https://cantera.org/3.2/python/zerodim.html#extensiblereactor)
underlie the open finite-volume adapter. Native physical equations remain reused; appended
boundary integrals are independently compared with inventories and analytic limits.
Frozen property/flash/nozzle and evolving-volume tests use original authored inputs and
separately installed species thermochemistry. Formation-energy, spin, physical phase,
mechanism/ideal-gas domain and trial-state correction limits remain explicit. These
numerical checks do not establish measured pressure or chemical-mixture accuracy.

Native insulation and fixed-ratio compression reuse the MIT LH2DT revision already
recorded in research/native_lh2dt.toml. NATIVE_INSULATION.md and
NATIVE_COMPRESSION.md identify independently accessible primary equations/APIs,
actual native source hashes, authored numerical limits and remaining construction/
machine qualifications. Prescribed cooling outlet PT is a boundary condition,
not a duplicated exchanger law or a predicted manufacturer operating point.

Finite hydride storage reuses HydrideKinetics and the native CoolProp DU/PT/fugacity
API. FINITE_HYDRIDE.md derives the original gas/solid internal-energy accounting,
including the reference pressure-work term and isothermal thermostat ledger. The
actual AB2 source is Ramadhan, Suwarno and Hijriawan's
[versioned dataset](https://doi.org/10.17632/8km9z62tct.1), CC BY 4.0. Its cached
mass/moles/volume are derived fields, not independent validation targets. HYDRIDE_DATA.md
and the full-file audit preserve the unresolved measurement/reference bases.

Pressure protection, vents, recovery and instrument response reuse the reviewed MIT
LH2DT snapshot. NATIVE_RELIEF.md explains transactional accepted latch copies,
public flow delegation and bracketed physical events. NATIVE_VENT.md independently
audits final Darcy/gravity momentum and reconstructs finite-UA conductance through
native PH queries, retaining raw coarse/clamped failures. NATIVE_RELIQUEFACTION.md
records explicit saturation/capacity targets and native finite fluid/wall recovery;
there is no duplicated cooling or refrigeration-cycle solver.

The native instrument API owns deterministic response and indication effects.
[NIST's sensor response study](https://tsapps.nist.gov/publication/get_pdf.cfm?pub_id=909856)
provides context for time-constant meaning under specified physical conditions; its
thermal coefficients are not pressure-transmitter calibration inputs. The
[BIPM uncertainty definition](https://jcgm.bipm.org/vim/en/2.26.html) distinguishes a
quantity's uncertainty from an unsupported probability assumption. Reported span/
resolution bounds are retained without converting them to sigma or coverage.
All verification coefficients/fixtures are authored; independently acquired USN
pressure data retain their CC-BY attribution and unresolved basis/location.

Native spin equilibrium/conversion reuses the same MIT LH2DT snapshot and is
compared against independently authored rotor-cutoff, thermostat and finite
constant-pressure enthalpy checks. NATIVE_SPIN.md links primary spin/EOS studies
and distinguishes supplied scalar enthalpy gaps from evolving liquid-spin EOS.
The two-side finite heat exchanger delegates each native fluid/wall derivative
and simultaneous native integration; only conservative coupling and audit
integrals are authored here. Per-side output access projects native accepted
transfer samples and the cumulative RK ledger without reintegration.
NATIVE_HEAT_EXCHANGER.md documents the closed scope.

Finite-rate gas conversion extends the existing Cantera volume rather than
adding a second process solver. REACTIVE_PROCESS.md derives boundary/reaction,
element and formation-energy accounting from native public APIs. Actual installed
GRI30 gas references are compared against an unextended native reactor and finer
integration; no catalyst table, mechanism, implementation or published worked
example is reproduced. Independent source/owned definition identities preserve
native thermo bounds and runtime kinetics while auditing unit-roundtrip error.

The compressor observations are Fleming's [MHC v1.2 dataset](https://doi.org/10.5281/zenodo.19036733),
CC BY4.0. Its versioned rights/attachment receipts remain in research/data/ and
the raw archive remains ignored. HYDRIDE_COMPRESSOR_DATA.md explains independent
recorder clocks, engineering reference roles, source-specific schema variations,
selected-cycle dependence and retained invalid/source fields. Ingestion does not
establish hydride kinetics, compressor efficiency or independent model validation.

The safety continuation reuses separately installed [HyRAM+](https://github.com/sandialabs/hyram)
Flame and public Bauwens correlation APIs. The [Sandia technical reference](https://doi.org/10.2172/2563814)
and [Bauwens/Dorofeev primary paper](https://hysafe.info/uploads/papers/2019/279.pdf)
support their declared levels. The host independently integrates native reacting
fuel-origin profiles and audits the native caloric equation; source/transport/heat
failures remain rejected. No native solver, reaction fit or blast coefficient
table is copied. Supplied participating energy is distinct from a predicted cloud.

The MIT [pifira0.3.0 native release](https://doi.org/10.5281/zenodo.22291661)
owns pressure-rise contents energy and effective angular area. Direct HEOS
pressure/density states and independently prescribed forward power audit its
inverse result. The host translates explicit axial intervals, checks geometry
and keeps contents heat separate from wall/incident-fire allocation. Native
wheel/license/source identities and original cases are recorded; no published
worked example or experiment is reproduced.

Lach and Gaathaug's [USN thermal collection v1](https://doi.org/10.23642/usn.17695082.v1)
is CC BY4.0 and now has all ten attachments. The eight-file native-HDF5 audit
preserves every source vector and documents unresolved time units, candidate
clock associations and sensor/derived-field meanings. It supplies observations,
not a validation result or an inferred dose/incident boundary.

Finite cryo-compressed composition is informed by the independent
[LLNL/DOE storage report](https://www.hydrogen.energy.gov/docs/hydrogenprogramlibraries/pdfs/progress07/vi_a_6_aceves.pdf)
and [NIST hydrogen EOS](https://doi.org/10.1063/1.3160306). Actual native tank,
wall, relief and shared-nozzle functions own the physics. The host contributes
domain, evidence, reusable assembly and independent inventory/property audits.
Authored power/geometry cases are not manufacturer specifications or measurements.

The separately installed pifira rotor API supplies partition sums and natural
conversion. Its [primary conversion context](https://doi.org/10.1016/j.ijhydene.2014.01.205)
and [Milenko study](https://doi.org/10.1007/BF02396837) define interpretation and
admission; the accessible90kg/m3 primary density bound is kept distinct from
the native92kg/m3 ceiling. The host copies no kinetic coefficient table.
Absolute rotor energy, frozen-baseline corrections and PV assumptions remain
different contracts; native functions alone do not supply evolving-spin liquid EOS.

[Glass H2 permeation research](https://doi.org/10.3389/fmats.2019.00342) and
[molecular diffusion measurements](https://doi.org/10.1063/1.324180) provide
scientific context for spherical storage. Original geometric integration and
conservative control-volume equations extend the one material core. Independent
analytic series and actual native gas states verify numerics. No published
material coefficients, data tables, optical response or worked case are reproduced.

Roberto Hernández's [fermentation version2 data](https://doi.org/10.17632/2nwcdx9hst.2),
CC BY4.0, are hash-audited through an original bounded observation profile.
Raw/normalized records remain excluded from releases. Same-export gas-volume
algebra is a source-consistency check, not independent yield or microbial
kinetic evidence. Retained provenance and unresolved units/replicates govern
future parameter estimation.

Original spectral photon accounting uses the
[IUPAC photocatalysis definitions](https://doi.org/10.1351/PAC-REC-09-09-36)
and [BIPM SI constants](https://www.bipm.org/en/publications/si-brochure).
Flat power-density wavelength bins and discrete lines have explicit meanings.
Prescribed incident/absorbed electron yields do not identify carrier kinetics.
Independent continuous quadrature, optical limits and actual native calorimetry
check numerics; no published optical coefficient or worked example is copied.
The staged finite-photo operation applies explicit segment rates through the
shared stoichiometric inventory and preserves completed prefixes on later
inventory rejection; it makes no time-dependent kinetic or shutoff claim.

The gas/solid engine directly uses the
[Cantera Mixture API](https://cantera.org/3.2/python/thermo.html#cantera.Mixture)
and separately installed thermochemistry with its recorded NASA/GRI provenance.
Independent mass-action and extensive/KKT checks compare actual native states;
trace-species thresholds and unobserved internal HP trials remain explicit.
No second equilibrium solver, mechanism or printed thermochemical table is included.

Native PSA-Dyna owns warm cyclic physics and CSS, informed by the public
[Skarstrom primary cycle record](https://patents.google.com/patent/US2944627A/en).
The host retains native checkpoint evidence, signed ledgers and the distinction
between a separate audit Network and the unexposed original integrator Network.
Authored adsorbent/valve inputs are not experimental material coefficients.

Hejazi and coauthors' [TiO2 dataset](https://doi.org/10.5281/zenodo.15277951),
CC BY4.0, supplies the source observations. The
[primary study](https://doi.org/10.1021/acsaem.4c01950) informs explicitly reviewed
column/unit interpretation; inaccessible full SI/apparatus evidence is not
silently promoted to validation. Repeated files/controls, calculated AQY/rates
and characterization fits keep their dependency and origin. No source data
table, figure, publication text or fit coefficient is reproduced in the release.

## Porous gases and finite redox calorimetry

The [Cantera3.2 transport API](https://cantera.org/3.2/python/transport.html#cantera.DustyGasTransport.molar_fluxes)
supplies coupled native porous-gas transport and states its kmol flux basis.
The host's independent Knudsen/Darcy limits check units, signs and parameter
coupling without copying native implementation. Species coefficients remain
separately installed and require material/source qualification for application.

The [DOE thermochemical production overview](https://www.energy.gov/cmei/fuels/hydrogen-production-thermochemical-water-splitting)
provides primary process context for carrier reuse. Native caloric functions
retain [NASA source provenance](https://ntrs.nasa.gov/citations/19940013151)
and exact installed source hashes. The example's densities, extents and stage
T/clocks are authored verification inputs. The selected thermochemical fit
range does not establish phase stability or chemical feasibility; no published
operating table, source implementation or coefficient matrix is reproduced.
Required heat, finite material accounting, kinetics and feasible process design
remain separate evidence categories.

## Finite membrane and independent statistics

Native reactor hook units were checked by an independent short-time species
inventory calculation, and finite porous transport by a two-volume Knudsen
exponential limit. The underlying [native Cantera reactor](https://cantera.org/3.2/reference/reactors/ideal-gas-reactor.html)
and [transport API](https://cantera.org/3.2/python/transport.html) retain their
physical equations. Identical prescribed T is paired with explicit required
thermostat heat; native numerical extensions are disclosed separately from
host-admitted samples and unobserved internal solver steps.

[Native SciPy QMC](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.qmc.Sobol.html)
and [variance indices](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.sobol_indices.html)
provide statistics for existing model callables. Original additive/product
limits and independent tensor quadrature of actual HEOS hydrogen inventory
check the composition. Input distributions and independence are authored cases,
not inferred measurement uncertainty. Full sources, definitions, failures and
numerical convergence are in UNCERTAINTY.md and research/uncertainty.md.

The HE-Austenite compilation's CC BY4.0 source identity is recorded in the
existing dataset receipt. Original publication rights and specimen dependence
remain distinct. The new profile reconstructs explicit SI views while retaining
ambiguous unit/pressure roles and conflicting linked compositions; no fracture
law or new independently measured dataset is asserted.

## Native safety calculations and conditional case evidence

The official [Caltech SDToolbox](https://shepherd.caltech.edu/EDL/PublicResources/sdt/)
archive is separately reviewed for its native CJ/frozen-shock and thermodynamic
functions. Exact archive/license/source receipts govern the selected code;
native endpoint/jump/sonic tests are numerical evidence. No source algorithm or
mechanism table is copied into the host. Unavailable native intermediate search
and sound states do not receive an invented all-trial domain qualification.

Actual [HyRAM source](https://github.com/sandialabs/hyram) owns selected harm
coefficients and native dose/CDF functions. Field type, reduction assumptions,
model/mean choice and replayed-result provenance are explicit. Original
calibration datasets were not independently reviewed here; no calibrated
facility exposure or source/fire chain follows from API/numerical agreement.

The [user's consequence toolkit](https://github.com/lyullee/process-risk-consequence-toolkit)
provides actual native conditional risk with typed receipts. Host finite-source,
coordinate/clock and evidence/credit bindings prevent lossy summary coupling.
Authored branch/frequency/occupancy/source-field assumptions are not measured
occurrence data or independent protection qualification. Acquired ELVHYS data
support source-specific BLEVE observations; missing premixed reacting-state
conditions prevent a direct CJ comparison.

## Finite oxygen, ordinary-air thermal response and physical residuals

The actual Cantera3.2 ideal-gas reactor remains the finite species/energy owner:
https://cantera.org/3.2/reference/reactors/ideal-gas-reactor.html . The O2 assembly
adds source/caloric/clock admission and independent species/U/P checks, not a
new gas-volume solver. OSHA1910.134 and WAC296-62-135 are independently accessible
occupational criterion sources with different fraction/pressure/site scopes;
criterion selection/applicability stays explicit and is not human-response
calibration. See OXYGEN_DEFICIENCY.md for primary links and preserved limits.
The sampled threshold-deficit integral is the analytic positive-part area of the
explicit linear interpolant. Its units follow the selected criterion (fraction·s
or Pa·s); it adds no injury or dose-response law.

The native JOS3 source/API is https://pythermalcomfort.readthedocs.io/en/latest/documentation/models.html
and actual release metadata https://pypi.org/project/pythermalcomfort/4.7.0/ .
The original model bibliographic reference is DOI10.1016/j.enbuild.2020.110575;
publisher full-text403 and unavailable original validation data are recorded.
Native85node/17segment thermoregulation is checked against its actual implicit
heat boundary and time refinement. It does not determine H2-rich convection,
cryogenic phase/contact injury or hypoxic physiology.

Actual learned residual ownership is https://github.com/lyullee/process-monitoring-toolkit
at the reviewed immutable revision in monitoring_dependency.toml. Native causal
feature/scaler/PCA/mode execution is tested with whole-run fitting/calibration/
evaluation separation and retained actual physical/instrument references.
Synthetic injections establish numerical behavior only, not detector accuracy.

The new independent experimental discovery is DOI10.18710/JXJP0H, ELVHYS4.2v1.1.
Original authors/CC0/file checksums and all-source qualification remain in its
receipt and oxygen_observation_data.md. No measured O2 or qualified H2 release
mass flow exists in those exports; processed H2 point observations, unqualified
clock/sensor mappings and source-invalid cases are not repaired to force a fit.
The original native air-phase diagnostic negative is reproducible through
check_air_condensation_boundary.py and native_air_condensation_review.md.

## Unverified coding-wave ownership

PV/directDC composition targets actual pvlib0.16.1 I-V; fracture composition
uses pinned official SandiaHELPR2.1.0 constitutive/fugacity APIs; solid reaction
reuses the existing balanced conversion and phase-enthalpy kernel. Respective
manuals/dependency/development records retain primary sources, source hashes,
licenses and model limits. No local numerical/clinical/mechanical performance
claim was established. All22 scientific cases await later execution. Primary
Nurion scheduler references are linked in NURION_VALIDATION_PLAN.md; their
availability does not verify the current account/environment or script runtime.


## Cavern, microbial cell, impact and material front — coding checkpoint

Four further partial first levels now have code: actual UH2SC cavern/rock audits,
native-electrode finite microbial electrolysis, finite surface-impact phase and
mechanical energy, and a native premixed material-path front reference. All are
`implemented_unverified`. Code inventory is70/72 (about97%):21 partial implemented,
38 historical native-adapter checks,11 unverified and2 planned. Last executed
coverage remains59/72 (about82%) at6eae06c. Full-programme effort remains an
uncertain30-40%; more code does not establish independent physical validity.

New21 deferred cases comprise4underground,5microbial,8impact and4front cases.
The combined pending campaign is62 case definitions. No model, example, case,
test, replay, benchmark, build, installed replay or cluster job was executed.
The static syntax/lint/source/license review is not numerical acceptance.

UH2SC's suspected GHE indexing/capacity/energy conventions are retained for strict
independent rejection rather than patched. Its well is ideal/prescribed-flow,
not a finite well inventory. MEC organism/activity/thermochemical data remain
qualified caller inputs. Impact contact/outcome data and a continuous finite-wall
pool handoff are unresolved. The front is a material-frame discrete reference,
not lab flame propagation, obstacle flow or a person heat-injury prediction.
Preferred HyRAM gas and SLABx-LH2 liquid-origin ownership remains unchanged.

Read UNDERGROUND_STORAGE.md, MICROBIAL_CELL.md, DROPLET_IMPACT.md and FLASH_FRONT.md.
Request025 records specific native APIs, evidence and coupling work. A CC0-claimed
MEC dataset candidate is recorded in research/microbial_electrolysis_data_candidate.toml;
no data assets were acquired, no source schema/units were qualified, and the
existing28 collections/466 acquired files/6,017,963,546bytes are unchanged.

The remaining planned families are obstacle-resolved dispersion and accepted
jet fire. Every partial family also retains the limits in MODEL_CATALOG.md;
70coded families are not70complete models. Last full installed-artifact audit
remains785dae7; later source/artifact acceptance is still deferred.


## New unexecuted integration interfaces

Read [OBSTACLE_DISPERSION.md](OBSTACLE_DISPERSION.md) for actual optional FDS
case/mesh/source/process/ledger interfaces, [JET_FIRE_CONSERVATION.md](JET_FIRE_CONSERVATION.md)
for rejected-native-path energy diagnostics, [MICROBIAL_ECONOMICS.md](MICROBIAL_ECONOMICS.md)
for the actual MEC-to-existing-cost-owner bridge, and [CLUSTER_EVIDENCE.md](CLUSTER_EVIDENCE.md)
for read-only selected-result reconciliation. These source additions have not
been executed. The76pending case definitions do not establish model accuracy.

Request026 specifies native reacting-establishment/chemistry/radiating-energy,
CFD build/runtime/source boundaries, a provider-neutral cost protocol, public
MEC geometry/result verification and separate campaign acceptance. Source/plan,
clock, material, phase and energy-reference ownership remain explicit. Preferred
HyRAM/SLABx ownership is unchanged; no failed native prediction is promoted.
The unexecuted LOHC/ammonia, equipment provenance and facility protection
interfaces reuse existing source-reviewed engines and shared kernels. Their
primary method links, source revisions and scope limits are recorded in
LIQUID_CARRIER_AMMONIA.md, NATIVE_COMPRESSION.md,
NATIVE_HEAT_EXCHANGER.md and FACILITY_PROTECTION.md. No supplied-document text,
table, figure, code or citation was used in these additions.

The adsorption-vessel, valve-actuator, relief-lift and continuity layers are
original compositions over existing reviewed owners. They copy no supplied-
document prose, table, figure, equation set or code. Caller data and each native
provider retain their own source and license identity. The valve map also exposes
a bounded inverse lookup with explicit endpoint selection for flat-area plateaus;
it does not infer a flow demand or control policy.

Pump/compressor map data remain caller-owned evidence with URI, license and
hash. The flowing-HX and reliquefier layers reuse original native results and
copy no external prose, tables, figures, equations or implementation code.

The 2026-10-29 host composition interfaces reuse the documented methods and native
versions in DROPLET_TRANSPORT.md, DROPLET_IMPACT.md, NATIVE_POOL.md,
PREFERRED_DISPERSION.md, RADIAL_HEAT_TRANSFER.md, THERMAL_UTILITIES.md,
FINITE_FUEL_CELL.md and NATIVE_ADSORPTION.md. No new constitutive correlation,
contact coefficient, material law or mixture EOS is introduced by these bridges.
The population and adsorption ledgers use explicit count/mass and component sums;
scenario scheduling and joint-input transforms preserve the original model and
caller law identities. See SCENARIO_COMPOSITION.md and JOINT_UNCERTAINTY.md for
implemented boundaries. New execution and measured qualification remain pending.

`thermo.GasStateDiagnostics` reports compressibility and transport combinations
from the caller's existing gas `ThermoState`; it uses explicit specific gas
constant and provider-supplied transport properties. Definitions follow the
[NIST REFPROP property conventions](https://www.nist.gov/system/files/documents/srd/REFPROP8_manua3.htm).
No EOS, transport correlation, missing value, or safety applicability is inferred.
