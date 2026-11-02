# 016 — Fire conservation, heat allocation and qualified observations

Status: local receiving specification. No receiving repository or external record
has been edited or contacted. The actual baselines are separately installed
HyRAM+6.1 and pifira0.3.0; source/license identities are in the research reports.
This extends request012 without bypassing the preferred gas-dispersion owner.

## Native reacting flame boundary

The host executes actual HyRAM Flame with its own native nozzle/expansion,
combustion, ODE and radiation. It does not pass a previously choked shared-nozzle
exit through another nozzle. Actual full-visible native paths complete, but all
four checked cases fail physical acceptance. Numerical diagnostic verification
passing is not an accepted jet-fire prediction.

Original numerical fixtures: normal gaseous H2 at300K, Air101325Pa/293.15K,
Cd0.8;2MPa/2mm horizontal and20MPa/1mm45degree sources. Three radial/tolerance
settings100/300/600 and1e-6/1e-7/1e-8 retain the failures. The default host API
raises with raw native/results; explicit diagnostic irradiance remains labeled
unaccepted. Exact inputs, source hashes and independent quadrature are in
research/native_jet_fire.md and scripts/check_hyram_flame.py.

Receiving native API should expose:

1. A conserved established-flame source boundary carrying fuel-origin mass,
   momentum, stagnation/formation energy, pressure/area, actual composition and
   frame. Initial Gaussian fields must reproduce the declared source integrals.
   A fitted radiant fraction or post-hoc section rescaling cannot repair them.
2. One consistent reacting-density function and derivative. The supplied
   derivative must differentiate the actual same T/composition/interpolation
   representation used by rho_prod, with explicit stoichiometric knot handling.
   Retain native solver status, endpoint, termination reason and dense/accepted
   output; an array reaching a requested point is weaker than a solver report.
3. Explicit mass/molar caloric units, species formation/sensible reference and
   source versus ambient initialization. T(f), rho(f), derivatives and the energy
   equation must agree at held-out f values as chemistry interpolation is refined.
   No arbitrary conversion between pure-fluid zeros and formation energies.
4. Separate adiabatic-product/radiation-postprocessing scope from a fully radiating
   energy equation. Expose emitted power, actual transmission, receiver geometry
   and any omitted sink. Scalar irradiance with emitters facing the observer is
   not a specified-normal absorbed wall boundary.
5. Stable public chemistry injection/metadata. At this baseline the Flame
   initialization reads chemistry pressure metadata differently from the actual
   Combustion object's stored field and can recreate default chemistry through an
   exception path. Requested chemistry resolution must remain visible and retained.

Observed acceptance fixtures to preserve:

- The2MPa source is0.00309566981064kg/s; native field entry is0.00167863456267kg/s
  and finest endpoint0.00203150580650kg/s. Fuel-origin includes hydrogen in water;
  it is not residual unburned H2. The initial gap is about45.77%.
- Independently integrated rho*f*v agrees across knot-split radial quadratures
  and8/10width tails to below1e-12kg/s. Tightening the native ODE does not remove
  its fuel-origin drift. Correct source, transport and quadrature gates separately.
- At f0.005, native drho/df is about−134.87 versus about−58.40kg/m3 from its actual
  density finite difference. A direct-EOS check of the native as-defined caloric
  equation has about−18.824kJ/kg defect there. Refinement and reference accounting
  must explain these differences before native physical acceptance changes.
- Native source stagnation-energy and emitted-power identities already pass.
  Keep those distinct from a closed whole-flame mass/energy balance.
- Radiation-kernel symmetry, source-count refinement and far-field checks must
  remain separate from physical/experimental validation of the source flame.

Do not weaken budgets, suppress native warnings, fit coefficients to a desired
acceptance result or silently substitute another engine. The host provides
reproducible failures and injectable factories, not a duplicate combustion/EOS solver.

## Conditional peak overpressure boundary

The actual public Bauwens static pressure correlation is usable independently of
a native Jet. The host supplies evidenced participating H2 mass, combustion heat,
ambient absolute pressure, event centre/frame/clock and a declared domain. It
returns conditional peak rise above ambient, with an optional numerical inverse
threshold radius. It does not manufacture the participating mass or a valid cloud.

Receiving full cloud APIs should accept actual qualified source/field objects,
retain flammable versus detonable fuel mass and concentration-gradient/cell-size
criteria, and expose the selected event centre and energy basis. A failed native
Gaussian field cannot become an accepted blast input. Waveform, impulse,
reflection, obstacles, ignition and DDT require their own justified native levels.
Use the host's static-correlation/zero-energy/forward-inverse tests as one narrow
compatibility fixture, without calling a conditional radius a safe distance.

## Inverse contents heat and axial geometry

PifiraClosedVesselHeat retains the actual native TankSpec and energy functions.
Its direct HEOS pressure/density audit rejects states outside the declared
fixed-mass two-phase domain before native lever-rule extrapolation. Pa absolute
inputs are reversibly mapped to the native gauge API coordinate; no measured
atmosphere is inferred. The result is contents ΔU/Δt, not incident fire flux.

Receiving pifira should offer a public SI absolute-pressure interface with fixed
mass/volume/reference evidence, phase/quality guards and native residuals. It
should expose angular-fit amplitude, optimizer status and covariance/residuals
with explicit observation semantics rather than only sigma/arc. The native
moving-window slope's pressure perturbation and actual fitted sample support
also need public metadata before that separate level is qualified here.

Axial intervals need explicit starts/ends and one common axis frame. The host now
translates supplied flame and wetted intervals to a common overlap start before
delegating the native positive min-height. It retains the complete geometry;
disjoint intervals return zero area and flux division fails. The fixtures
[0.3,0.9] intersect[0,0.5] over0.2m, while[0.8,1.4] has zero overlap. Bare lengths
cannot represent arbitrary offset contact intervals.

Future wall coupling must distinguish contents heat, wall storage, incident
radiation/convection, emission/loss, work and material transport. Supply actual
surface geometry, normals/absorptivity, area/clock and a conservative native wall
boundary. Ordinary mean T cannot replace mean T^4. A contents-equivalent flux
needs its explicit allocation evidence and must not silently become incident
wall flux or exposure dose. Normal/para/ortho fixed EOS do not supply evolving
spin conversion energy.

## Thermal observations and continuation

The versioned USN thermal collection is now complete:8MAT experiments and2DOCX
descriptions, all checksummed. The profile preserves independent clocks, original
vectors/indices, signed radiation/combined-flux/flow/pressure fields and masked
nonphysical temperatures. The original time unit and synchronization remain
unqualified. RHF3/timech7 are separate by default; length equality is candidate
metadata, with only an explicit reconstructed association available. Exp2 Vent/T
remains unclocked rather than truncated or assigned another group's time.

Native consumers should require independently evidenced clock units/relationships,
sensor orientation/location/frame and THF processing before integrating dose or
using a measured field as an incident boundary. Meter/bolt temperature is not
bulk gas temperature; reported pressure is not automatically absolute. Preserve
source attribution, raw/derived roles and experiment-level fitting/holdout groups.
This is a request for explicit consumer contracts, not authorization to modify
the original third-party observations or invent their missing metadata.

All native implementations and external observations remain separately installed
or ignored. The public host includes original adapters, authored numerical cases,
provenance, numerical failures and continuation specifications only.
