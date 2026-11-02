# Native finite anaerobic process

`h2physics.adapters.biological.QsdSanAdm1Digester` assembles an actual QSDsan
ADM1 `AnaerobicCSTR` and BioSTEAM `System`. Native objects own the biochemical
reaction matrix/rates, biomass growth/decay, acid/base equilibrium, gas/liquid
transfer, finite headspace pressure, one-way extraction law and BDF integration.
The host supplies units, explicit initialization, source/clock admission and a
separately sampled balance audit. There is no second bed/reactor ODE or EOS.

This is a **synthetically verified, isothermal continuous finite-inventory level** for
`production.biological`. It is an anaerobic community including H2-consuming
methanogens. It does not establish a dedicated dark-fermentation process,
experimental H2 yield, culture selection or calibrated production capacity.
The old workbook's missing biomass, feed and gas measurement bases remain
missing. No parameter was estimated from that workbook.

## Native revision and rights

The optional installation uses QSDsan1.5.3 and Thermosteam0.54.2 with official
BioSTEAM revision `0acb320455d3c6cdaace85bf6ca27a1256706918`. Its version string
is2.54.0, the same as the rejected PyPI release; admission therefore checks the
actual native `_system.py` SHA256. The published release passes a mutable
system-state array as solver `y0`. A real finite run changed its initial
trajectory coordinate by0.204454436 and failed the component audit. The official
revision copies `y0`; the same initial-state check then passes exactly.
No host monkeypatch or native-file edit was made.

The installed QSDsan, BioSTEAM and Thermosteam license files grant the NCSA
license. BioSTEAM/Thermosteam PyPI metadata additionally says MIT; the review
records the actual installed license. All native packages, bundled native
coefficient resources and install logs remain separately installed under ignored
`artifacts/`. The host distributes none of their source or data.
[biological_dependency.toml](../research/biological_dependency.toml) records the
resolved archives, fixed source revision, license and source fingerprints.

An unconstrained native install required an unavailable Windows C++ compiler for
numpoly1.3.9. The reviewed optional target uses its published pure Python1.2.14
wheel, which satisfies Chaospy's declared dependency. NUMBA_DISABLE_JIT=1 was
explicitly used for the native verification jobs; native equations/functions and
the SciPy solver remain unchanged. The host factory neither sets this environment
option nor installs packages. Deprecation warnings remain visible.

## Python boundary

```python
from h2physics.adapters.biological import (
    Adm1Geometry, BiologicalAudit, BiologicalEvidence,
    QsdSanAdm1Digester, QsdSanNative,
)
native = QsdSanNative.from_installed()  # lazy optional imports and revision check
from qsdsan import process_models as pm
components = pm.create_adm1_cmps()
model = pm.ADM1(components=components)  # actual caller-owned native model

# Supply complete mappings and source evidence for the intended process.
digester = QsdSanAdm1Digester(
    native, components=components, model=model,
    geometry=Adm1Geometry(
        liquid_volume_m3=liquid_volume, headspace_volume_m3=gas_volume,
        gas_pipe_coefficient_m3_s_pa=extraction_coefficient,
        external_pressure_pa=absolute_external_pressure,
        temperature_k=prescribed_temperature,
    ),
    evidence=source_evidence,  # BiologicalEvidence; finite absolute SI clock support
    feed_volume_flow_m3_s=liquid_feed_flow,
    feed_concentrations_kg_m3=feed_components,
    initial_liquid_concentrations_kg_m3=initial_liquid,
    initial_headspace_mol_m3=initial_dry_gases,
    audit=BiologicalAudit(
        component_absolute_tolerance_kg=declared_component_budget,
        invariant_absolute_tolerance_kg=declared_invariant_budget,
        maximum_pressure_pa=declared_pressure_limit,
        relative_tolerance=declared_relative_budget,
    ),
)
result = digester.run(start_time_s=t0, end_time_s=t1, sample_count=n,
                      rtol=1e-8, atol=1e-11, max_step_s=300)
```

The returned `BiologicalRun` is issued only after the native integration and
balance audit complete. Call `result.require_current()` before treating its samples
as current native output; it checks the retained solver history, live system state,
point records, balance and source/version bindings. Direct construction and
`dataclasses.replace()` cannot mint a native run receipt. These checks establish
result provenance and freshness, not biological calibration or full heat/water/H/O
closure.

Inputs are Python objects and mappings; JSON, files and a service are unnecessary.
The replay script contains an explicitly authored synthetic configuration, not a
third-party example or a default experimental reconstruction. Native kinetic
parameters are changed through the actual native `ADM1` constructor. No copied
coefficient table is present in host source.

Every native liquid component is required in the initial mapping, including
water, ionic bookkeeping components, all substrate pools and all biomass groups.
The constant feed mapping requires every component except bulk H2O; native
`WasteStream.set_flow_by_concentration` closes the feed's water volume and its
actual concentrations are used in the ledger. An exactly zero feed uses an actual
empty native stream. It is never replaced by an epsilon flow. Native volumetric
flow conversion is checked within1e-12 relative; the algebraic Q coordinate uses
the actual native inlet flow. Initial physical inventories must remain bitwise
unchanged by initialization. Initial gas values require all three native IDs
`S_h2`, `S_ch4`, `S_IC`; `S_IC` in gas means molecular CO2. Their input unit is
mol/m3, converted explicitly to native kmol/m3. The native automatic gas mixture
is replaced through the pinned native state-initialization/transfer methods.

The exactly closed, zero-liquid-flow case currently fails native output-stream
finalization: QSDsan `_state2flows` calls `set_flow_by_concentration(Q=0)`, which
raises `RuntimeError` for the empty outlet after BDF completed successfully.
`BiologicalAuditError` retains that completed trajectory and actual final state
under clock kind `native-finalization`. Its closed COD/C/N invariants can be
examined as a diagnostic, but this is **not an accepted closed-process run**.
The accepted level requires positive liquid throughput. Gas extraction may
independently be zero or blocked by downstream pressure.

Pressure is Pa absolute at the host and bar absolute natively. Extraction
coefficient converts from m3/(s Pa) to native m3/(day bar); the native parameter is
named `pipe_resistance` although it multiplies pressure difference. No host valve
or choking equation is introduced. The temperature domain is a declared warm
liquid280–330K boundary, not a cryogenic or high-pressure bioprocess claim.
Liquid volume is fixed, liquid throughput prescribed, biomass retention zero.
Temperature is prescribed and native pH is solved; no external pH controller,
heat storage, heat duty or thermal feedback is inferred. Construction explicitly
changes native process-global thermo settings. Do not concurrently mutate those
settings, the native components or model during a run.

## Inventory, reference and audit meaning

Native liquid values are kg(native measured component basis)/m3, not a universal
physical kg/m3. Organic pools and biomass are generally COD; inorganic C and N
have their own measured bases. `measured_inventories_kg` preserves those meanings.
Physical H2 mass uses the actual native component's `i_mass`; molar conversion
uses its `chem_MW`. The checked component gives
`i_mass=0.1259972248959336 kgH2/kgCOD`, `chem_MW=2.01588 kg/kmol`, equivalent to
15.9996kgCOD/kmolH2. This package-specific conversion is recorded rather than
rounding COD to a guessed universal factor8.

For each native component, the audit forms liquid inventory plus the native
measured equivalent of its finite gas inventory. Its change is compared with
integrated feed minus liquid/dry-gas export plus the actual native biochemical
production/consumption. Native gas transfer is an internal exchange and cancels
between liquid and headspace. Independent COD/C/N checks use native component
weights and verify the native biochemical stoichiometric nullspaces before
checking boundary-only totals. H2 is chemically created/consumed and is not an
invariant; `hydrogen_formed_kg`, `hydrogen_consumed_kg`, physical inventory and
signed inlet/export ledger are separate.

H2 spin is unresolved. COD is an electron-equivalent accounting basis, **not an
enthalpy reference**. There is no total-U/enthalpy ledger, complete H/O atom or
total wet mass claim. Native headspace contains three dynamic dry gases plus
saturated water vapor pressure; evaporation, water inventory and latent heat are
not jointly conserved states. Gas export purity is the integrated H2 molar
export divided by integrated H2+CH4+CO2 export. It is a dry, finite-window stream
quantity, may include initial headspace gas, and is not feed-origin recovery or
biogenic yield. Zero dry export returns `None` rather than a fabricated purity.

`native_solution.t/y` retain the actual native solver's accepted-step result;
`points` use separately requested dense-output sample clocks. Cumulative Simpson
integration of sampled native stream/reaction rates is an independent audit,
not an exact integrated native ledger. Each use needs declared budgets and
temporal/sample refinement. A coarse underresolved ledger is rejected even if
the native solver reports success. Domain/ledger failures retain the completed
actual native solution, failing state/time/clock kind and audited prefix through
`BiologicalAuditError`, with the original exception as cause.
Native rates, quadrature inputs/results, component weights and residuals must
also be finite; NaN cannot pass an inequality gate. If native endpoint-cache
synchronization fails while an audit error is already pending, the original
error/cause remains primary and the secondary error is retained separately as
`restoration_error`.

Native `_update_state` zeros entries below1e-16 (in its mixed native state units),
including negative trial values. The host does not remove or hide this native
behavior and does not clip its own audited states. Accepted/dense states must be
finite and nonnegative, and inventory defects must pass the stated budgets.
Internal trial corrections are not individually observable; exact positivity or
zero correction is not claimed. Pressure bounds are post-run accepted/sample
audits, not localized stopping events. No arbitrary within-step domain-event
completeness is claimed.

## Primary basis and remaining work

ADM1's community/substrate/biomass/acid-base/gas-transfer formulation is described
by [Batstone et al., Water Sci. Technol.45(10),65–73](https://research.wur.nl/en/publications/the-iwa-anaerobic-digestion-model-no-1-adm1/).
The implementation choices, differential/algebraic H2 alternatives and finite
gas/liquid balances are detailed by
[Rosén and Jeppsson, Lund report, §3.1.1](https://lup.lub.lu.se/search/files/5715450/588082.pdf).
The [official QSDsan ADM1 API](https://qsdsan.com/en/latest/api/process_models/ADM1.html)
and [native dynamic reactor API](https://qsdsan.com/en/latest/api/unit_operations/dynamic/anaerobic_reactor.html)
describe the native owners. Current web documentation may describe1.6.0; the
installed source fingerprint defines this1.5.3 contract. Equations/coefficients
are delegated to the installed native package, not transcribed from these pages.

Receiving hooks still needed: immutable accepted-step observer and initial-state
contract; explicit record of native trial-state zeroing; native integrated
component/element/gas-export ledgers; zero-flow stream finalization and
initialization without an unused0/0 inlet average; package-level thermal/water/H/O closure if those capabilities
are requested; and source-specific fermentation/culture/feed/gas-basis evidence
before calibration or held-out validation. Existing workbook omissions cannot
be resolved by this engine installation.

## Local isolated reproduction

The native stack has its own SciPy1.18.1 and NumPy2.5.4. Run it separately from
the host's normal and SciPy1.16.3 compatibility suites; prepending its target to
those processes would change their dependency stack. Fresh reproduction uses
the exact resolved artifacts in the dependency receipt; these commands show the
two-level installation and public entry points:

```powershell
.venv\Scripts\python -m pip install --no-compile --target artifacts\native_biological_packages qsdsan==1.5.3 numpoly==1.2.14
.venv\Scripts\python -m pip install --no-deps --no-compile --target artifacts\native_biological_core_fixed https://github.com/BioSTEAMDevelopmentGroup/biosteam/archive/0acb320455d3c6cdaace85bf6ca27a1256706918.zip
$env:PYTHONPATH = (Join-Path $PWD 'artifacts\native_biological_core_fixed') + ';' + (Join-Path $PWD 'artifacts\native_biological_packages')
$env:NUMBA_DISABLE_JIT = '1'
.venv\Scripts\python -m pytest tests/test_biological.py -q
.venv\Scripts\python scripts/check_biological.py
```

The script also accepts repeated explicit `--native-target` arguments, fixed
core first, without modifying an installation. Native tests visibly skip when
the optional engine is absent; those skips are not execution evidence. The
separate fully executed native tests and replay are recorded in
[native_biological_process.md](../research/native_biological_process.md).
