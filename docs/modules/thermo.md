# Module inputs and outputs / 모듈 입출력 전체 명세

This source-derived companion expands every entry in the English and Korean README module tables. Start with those task/purpose tables to select a level, then use the exact signatures below.

README의 분야별 목적 표에서 경로를 고른 뒤 이 문서의 생성자·계산 인자·연결 객체·반환 필드를 확인하세요. 전체 인자 이름·타입 주석·기본값은 실제 소스에서 추출합니다. 제공된 타입 주석 자체가 런타임 보증은 아닙니다.

## Reading the contracts / 읽는 방법

- Import from the displayed `h2physics.*` module; construct the owner before calling an instance method. `self` and `cls` in source signatures are bound by Python, not user inputs.
- A parameter with no default is required. `field(init=False)` is computed, not a constructor input. `field(default_factory=...)` supplies a factory default. Class/protocol fields remain declarations, not a claim that every class has a generated dataclass constructor.
- Setup and execution are distinct. Inject actual provider objects, callbacks, material coefficients, boundaries and clocks; preserve the original result when a receiving API requires it.
- Source-linked input/return records include their declared fields and computed-property names. Related records are expanded to two record edges; more deeply nested contracts, inherited behavior and unannotated callbacks stay in their linked source/domain manuals.
- Unit-bearing names follow SI: Pa, K, kg, mol, m, s, W, J, with their stated compound units. Fluid-state pressure is absolute; pressure differences, overpressure and residuals use their declared difference basis. Native/provider objects can use their own explicitly documented field spellings and conventions. Read angle, rpm, fraction, percentage, H/H2, phase, spin, formation/sensible enthalpy and signed-power bases explicitly.
- A `Trace` usually retains multiple samples/stages; a state/point usually describes one state. Neither object naming nor source extraction proves numerical execution or experimental qualification.

## Navigation / 바로가기

- [CoolProp 순수 유체 상태·물성 계산 / Pure-fluid pressure/temperature flash with CoolProp](#module-h2physics-thermo-coolprop-coolpropproperties-state_pt)
- [오차·영역 자격을 확인한 물성 테이블 조회 / Qualified native-backed property acceleration within its admitted domain](#module-h2physics-thermo-tables-qualifiedgastable-state_pt)
- [오르토·파라 전환율과 전환열 계산 / Ortho/para conversion rate and conversion heat](#module-h2physics-adapters-lh2dt_spin-lh2dtorthopara-rate)
- [조성이 명시된 실제 혼합유체 상태 계산 / Fixed-composition real-fluid mixture flash](#module-h2physics-thermo-coolprop_mixture-coolpropmixtureproperties-state_pt)
- [유한 혼합물 성분·에너지 재고와 상태 변화 / Finite component and energy stocks with composition-dependent flashes](#module-h2physics-thermo-finite_mixture_inventory-run_finite_mixture_vu_intervals)

<a id="module-h2physics-thermo-coolprop-coolpropproperties-state_pt"></a>

## CoolProp 순수 유체 상태·물성 계산 / Pure-fluid pressure/temperature flash with CoolProp

Family / navigation ID: `thermo.pure_fluid`

Import module: `h2physics.thermo.coolprop`; selected entry: `CoolPropProperties.state_pt`.

#### `h2physics.thermo.coolprop.CoolPropProperties`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/thermo/coolprop.py#L88)

```python
CoolPropProperties(fluid: str='Hydrogen', *, backend: str='HEOS', internal_energy_policy: str='library', quality_roundoff_tolerance: float=0.0)
```

Computed properties: `basis`, `molar_mass_kg_mol`, `critical_temperature_k`, `critical_pressure_pa`.

#### `h2physics.thermo.coolprop.CoolPropProperties.state_pt`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/thermo/coolprop.py#L186)

```python
state_pt(self, pressure_pa: float, temperature_k: float) -> ThermoState
```

### Returned value / 반환값

`ThermoState`

### Related input/return records / 관련 입력·반환 객체

#### `h2physics.core.ThermoState`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/core.py#L114)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `basis` | `PropertyBasis` | `required` |
| `pressure_pa` | `float` | `required` |
| `temperature_k` | `float` | `required` |
| `density_kg_m3` | `float` | `required` |
| `enthalpy_j_kg` | `float` | `required` |
| `internal_energy_j_kg` | `float` | `required` |
| `entropy_j_kg_k` | `float` | `required` |
| `phase` | `str` | `required` |
| `cp_j_kg_k` | `float &#124; None` | `None` |
| `cv_j_kg_k` | `float &#124; None` | `None` |
| `viscosity_pa_s` | `float &#124; None` | `None` |
| `conductivity_w_m_k` | `float &#124; None` | `None` |
| `speed_of_sound_m_s` | `float &#124; None` | `None` |
| `vapor_mass_fraction` | `float &#124; None` | `None` |
| `raw_vapor_mass_fraction` | `float &#124; None` | `None` |

Computed properties: `enthalpy_identity_residual_j_kg`, `heat_capacity_ratio`.

#### `h2physics.core.PropertyBasis`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/core.py#L97)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `fluid` | `str` | `required` |
| `reference_id` | `str` | `required` |
| `spin_composition` | `str` | `'unspecified'` |


<a id="module-h2physics-thermo-tables-qualifiedgastable-state_pt"></a>

## 오차·영역 자격을 확인한 물성 테이블 조회 / Qualified native-backed property acceleration within its admitted domain

Family / navigation ID: `thermo.acceleration`

Import module: `h2physics.thermo.tables`; selected entry: `QualifiedGasTable.state_pt`.

#### `h2physics.thermo.tables.QualifiedGasTable`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/thermo/tables.py#L184)

A qualified PT/PH/PS provider. Out-of-envelope states raise; no EOS substitution.

```python
QualifiedGasTable(reference: CoolPropProperties, envelope: GasEnvelope, *, backend: str='BICUBIC&HEOS', validation_points: int=300, maximum_relative_error: float=0.005, seed: int=20261026, timing_repetitions: int=3, maximum_relative_identity_error: float=1e-07, internal_energy_policy: str='library')
```

Computed properties: `basis`.

#### `h2physics.thermo.tables.QualifiedGasTable.state_pt`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/thermo/tables.py#L331)

```python
state_pt(self, pressure_pa: float, temperature_k: float) -> ThermoState
```

### Returned value / 반환값

`ThermoState`

### Related input/return records / 관련 입력·반환 객체

#### `h2physics.thermo.tables.GasEnvelope`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/thermo/tables.py#L36)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `minimum_pressure_pa` | `float` | `required` |
| `maximum_pressure_pa` | `float` | `required` |
| `minimum_temperature_k` | `float` | `required` |
| `maximum_temperature_k` | `float` | `required` |

#### `h2physics.core.ThermoState`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/core.py#L114)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `basis` | `PropertyBasis` | `required` |
| `pressure_pa` | `float` | `required` |
| `temperature_k` | `float` | `required` |
| `density_kg_m3` | `float` | `required` |
| `enthalpy_j_kg` | `float` | `required` |
| `internal_energy_j_kg` | `float` | `required` |
| `entropy_j_kg_k` | `float` | `required` |
| `phase` | `str` | `required` |
| `cp_j_kg_k` | `float &#124; None` | `None` |
| `cv_j_kg_k` | `float &#124; None` | `None` |
| `viscosity_pa_s` | `float &#124; None` | `None` |
| `conductivity_w_m_k` | `float &#124; None` | `None` |
| `speed_of_sound_m_s` | `float &#124; None` | `None` |
| `vapor_mass_fraction` | `float &#124; None` | `None` |
| `raw_vapor_mass_fraction` | `float &#124; None` | `None` |

Computed properties: `enthalpy_identity_residual_j_kg`, `heat_capacity_ratio`.

#### `h2physics.core.PropertyBasis`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/core.py#L97)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `fluid` | `str` | `required` |
| `reference_id` | `str` | `required` |
| `spin_composition` | `str` | `'unspecified'` |


<a id="module-h2physics-adapters-lh2dt_spin-lh2dtorthopara-rate"></a>

## 오르토·파라 전환율과 전환열 계산 / Ortho/para conversion rate and conversion heat

Family / navigation ID: `thermo.spin`

Import module: `h2physics.adapters.lh2dt_spin`; selected entry: `Lh2dtOrthoPara.rate`.

#### `h2physics.adapters.lh2dt_spin.Lh2dtOrthoPara`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/lh2dt_spin.py#L165)

Actual native spin functions; rate and enthalpy remain caller evidence.

```python
Lh2dtOrthoPara(native_module, native_parameters, *, evidence: SpinEvidence, domain: SpinDomain)
```

#### `h2physics.adapters.lh2dt_spin.Lh2dtOrthoPara.rate`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/lh2dt_spin.py#L222)

```python
rate(self, state, temperature_k, mass_kg)
```

The source has no explicit return annotation; inspect its return statements and the domain manual. No return type is invented by this generator.

### Returned value / 반환값

`SpinRate`

This return contract was reviewed from the implementation; it is not an annotation present in the source signature.

### Related input/return records / 관련 입력·반환 객체

#### `h2physics.adapters.lh2dt_spin.SpinRate`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/lh2dt_spin.py#L106)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `temperature_k` | `float` | `required` |
| `mass_kg` | `float` | `required` |
| `equilibrium` | `SpinEquilibrium` | `required` |
| `para_fraction_rate_s` | `float` | `required` |
| `conversion_heat_w` | `float` | `required` |
| `native_state` | `Any` | `required` |
| `native_parameters` | `Any` | `required` |

#### `h2physics.adapters.lh2dt_spin.SpinEvidence`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/lh2dt_spin.py#L22)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `rate_evidence_id` | `str` | `required` |
| `conversion_enthalpy_evidence_id` | `str` | `required` |
| `phase_scope_id` | `str` | `required` |
| `source_ids` | `tuple[str, ...]` | `required` |
| `parameter_origin` | `Origin` | `required` |

#### `h2physics.adapters.lh2dt_spin.SpinDomain`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/lh2dt_spin.py#L43)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `minimum_temperature_k` | `float` | `required` |
| `maximum_temperature_k` | `float` | `required` |
| `reference_rotational_level` | `int` | `required` |
| `cutoff_absolute_tolerance` | `float` | `required` |
| `evidence_id` | `str` | `required` |

#### `h2physics.adapters.lh2dt_spin.SpinEquilibrium`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/lh2dt_spin.py#L90)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `temperature_k` | `float` | `required` |
| `para_fraction` | `float` | `required` |
| `reference_para_fraction` | `float` | `required` |
| `cutoff_difference` | `float` | `required` |
| `native_rotational_level` | `int` | `required` |
| `reference_rotational_level` | `int` | `required` |


<a id="module-h2physics-thermo-coolprop_mixture-coolpropmixtureproperties-state_pt"></a>

## 조성이 명시된 실제 혼합유체 상태 계산 / Fixed-composition real-fluid mixture flash

Family / navigation ID: `thermo.mixtures`

Import module: `h2physics.thermo.coolprop_mixture`; selected entry: `CoolPropMixtureProperties.state_pt`.

#### `h2physics.thermo.coolprop_mixture.CoolPropMixtureProperties`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/thermo/coolprop_mixture.py#L233)

A frozen mole-basis gas mixture backed by CoolProp HEOS.

``composition.species`` are mapped to CoolProp fluid names through the
optional ``fluid_names`` mapping. Molar masses are checked against each
pure component before a mixture state is created. Binary interaction data
remain owned by the installed CoolProp release; missing pairs fail closed.

```python
CoolPropMixtureProperties(composition: GasComposition, *, fluid_names: Mapping[str, str] | None=None, molar_mass_relative_tolerance: float=0.0001, inverse_temperature_bounds_k: tuple[float, float] | None=None, inverse_cache_size: int=512)
```

Computed properties: `molar_mass_kg_mol`, `critical_temperature_k`, `critical_pressure_pa`, `inverse_cache_info`.

#### `h2physics.thermo.coolprop_mixture.CoolPropMixtureProperties.state_pt`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/thermo/coolprop_mixture.py#L394)

Evaluate a frozen-composition mixture at absolute pressure and temperature.

```python
state_pt(self, pressure_pa: float, temperature_k: float) -> ThermoState
```

### Returned value / 반환값

`ThermoState`

### Related input/return records / 관련 입력·반환 객체

#### `h2physics.mixtures.GasComposition`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/mixtures.py#L28)

A fixed gas composition with explicit species and molar-mass identities.

Mole and mass fractions are converted using declared molar masses in kg/mol.
Component flow arrays put species on the final axis and retain the sign of
the supplied total flow. Composition is fixed; reactions require constructing
a new object after updating the composition.

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `composition_id` | `str` | `required` |
| `species` | `tuple[str, ...]` | `required` |
| `mole_fractions` | `np.ndarray` | `required` |
| `molar_masses_kg_mol` | `np.ndarray` | `required` |

Computed properties: `molar_mass_kg_mol`, `mass_fractions`.

#### `h2physics.core.ThermoState`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/core.py#L114)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `basis` | `PropertyBasis` | `required` |
| `pressure_pa` | `float` | `required` |
| `temperature_k` | `float` | `required` |
| `density_kg_m3` | `float` | `required` |
| `enthalpy_j_kg` | `float` | `required` |
| `internal_energy_j_kg` | `float` | `required` |
| `entropy_j_kg_k` | `float` | `required` |
| `phase` | `str` | `required` |
| `cp_j_kg_k` | `float &#124; None` | `None` |
| `cv_j_kg_k` | `float &#124; None` | `None` |
| `viscosity_pa_s` | `float &#124; None` | `None` |
| `conductivity_w_m_k` | `float &#124; None` | `None` |
| `speed_of_sound_m_s` | `float &#124; None` | `None` |
| `vapor_mass_fraction` | `float &#124; None` | `None` |
| `raw_vapor_mass_fraction` | `float &#124; None` | `None` |

Computed properties: `enthalpy_identity_residual_j_kg`, `heat_capacity_ratio`.

#### `h2physics.core.PropertyBasis`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/core.py#L97)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `fluid` | `str` | `required` |
| `reference_id` | `str` | `required` |
| `spin_composition` | `str` | `'unspecified'` |


<a id="module-h2physics-thermo-finite_mixture_inventory-run_finite_mixture_vu_intervals"></a>

## 유한 혼합물 성분·에너지 재고와 상태 변화 / Finite component and energy stocks with composition-dependent flashes

Family / navigation ID: `thermo.mixtures`

Import module: `h2physics.thermo.finite_mixture_inventory`; selected entry: `run_finite_mixture_vu_intervals`.

#### `h2physics.thermo.finite_mixture_inventory.run_finite_mixture_vu_intervals`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/thermo/finite_mixture_inventory.py#L343)

Advance caller-supplied finite intervals with phase-selective outlets.

This explicit accepted-step algorithm performs a native CoolProp two-phase
V/U flash at the initial state and after every interval. Outlet composition
and enthalpy are sampled from the preceding accepted equilibrium packet;
interval refinement is therefore required for rapidly varying trajectories.
Any flash, domain or closure failure aborts with no fabricated later rows.
Only a bounded two-phase branch is supported; phase events and wall states
are outside this first executable level.

```python
run_finite_mixture_vu_intervals(template: MixtureProviderTemplate, initial_component_moles, *, initial_internal_energy_j: float, vessel_volume_m3: float, intervals, pressure_bounds_pa, quality_bounds, initial_guesses, volume_absolute_tolerance_m3: float, energy_absolute_tolerance_j: float, component_mole_absolute_tolerance: float, phase_mole_balance_tolerance: float, branch_evidence_id: str, run_id: str, root_pressure_relative_tolerance: float=1e-07, root_quality_absolute_tolerance: float=1e-08)
```

The source has no explicit return annotation; inspect its return statements and the domain manual. No return type is invented by this generator.

### Returned value / 반환값

`FiniteMixtureVesselRun`

This return contract was reviewed from the implementation; it is not an annotation present in the source signature.

### Related input/return records / 관련 입력·반환 객체

#### `h2physics.thermo.finite_mixture_inventory.FiniteMixtureVesselRun`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/thermo/finite_mixture_inventory.py#L181)

Immutable owner-issued accepted trajectory and independent balance audit.

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `run_id` | `str` | `required` |
| `template` | `MixtureProviderTemplate` | `required` |
| `vessel_volume_m3` | `float` | `required` |
| `energy_reference_id` | `str` | `required` |
| `accepted` | `tuple[MixtureVesselAcceptedState, ...]` | `required` |
| `intervals` | `tuple[MixtureVesselInterval, ...]` | `required` |
| `component_mole_absolute_tolerance` | `float` | `required` |
| `energy_absolute_tolerance_j` | `float` | `required` |

#### `h2physics.thermo.finite_mixture_inventory.MixtureProviderTemplate`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/thermo/finite_mixture_inventory.py#L22)

Immutable component/backend settings used to issue a provider per stock.

CoolProp's provider captures one overall composition. A new provider is
therefore constructed for every accepted component inventory. The caller
supplies the component order and molar masses once; no species are inferred.

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `species` | `tuple[str, ...]` | `required` |
| `molar_masses_kg_mol` | `tuple[float, ...]` | `required` |
| `coolprop_fluids` | `tuple[str, ...]` | `required` |
| `energy_reference_id` | `str` | `required` |
| `inverse_temperature_bounds_k` | `tuple[float, float] &#124; None` | `None` |
| `molar_mass_relative_tolerance` | `float` | `0.0001` |

#### `h2physics.thermo.finite_mixture_inventory.MixtureVesselAcceptedState`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/thermo/finite_mixture_inventory.py#L137)

One accepted finite-volume state, equilibrium flash and cumulative ledgers.

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `time_s` | `float` | `required` |
| `provider` | `CoolPropMixtureProperties` | `field(repr=False, compare=False)` |
| `flash` | `object` | `field(repr=False, compare=False)` |
| `admission` | `MixtureInventoryStateAdmission` | `field(repr=False, compare=False)` |
| `cumulative_inlet_component_moles` | `tuple[float, ...]` | `required` |
| `cumulative_outlet_component_moles` | `tuple[float, ...]` | `required` |
| `cumulative_energy_into_vessel_j` | `float` | `required` |

#### `h2physics.thermo.finite_mixture_inventory.MixtureVesselInterval`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/thermo/finite_mixture_inventory.py#L91)

Finite transfers over one caller-chosen interval.

Inlet component moles and their integrated enthalpy are supplied by the
caller. Outlets are phase-selective total moles withdrawn from the *current
left-end accepted phase*, whose native composition and enthalpy determine
both species removal and exported energy. Heat/work are signed energy into
the vessel in J. No rates or interpolated control schedule are inferred.

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `end_time_s` | `float` | `required` |
| `liquid_inlet_component_moles` | `tuple[float, ...]` | `required` |
| `vapor_inlet_component_moles` | `tuple[float, ...]` | `required` |
| `liquid_inlet_enthalpy_j` | `float` | `required` |
| `vapor_inlet_enthalpy_j` | `float` | `required` |
| `liquid_outlet_total_moles` | `float` | `0.0` |
| `vapor_outlet_total_moles` | `float` | `0.0` |
| `heat_into_vessel_j` | `float` | `0.0` |
| `work_into_vessel_j` | `float` | `0.0` |
| `evidence_id` | `str` | `''` |


## Maintaining this guide / 갱신

Curated purposes and entry selection live in `scripts/readme_module_guide.py`. Run `python scripts/readme_module_guide.py` to regenerate both README blocks and this file. Run `python scripts/readme_module_guide.py --check` to reject stale output, unresolved callables or missing catalog IDs. The script parses source with the standard library, imports no physical engine and runs no calculation. Review purpose/units/limits against domain manuals when an API changes. It preserves authored scientific attribution and performs no automatic translation of external material.
