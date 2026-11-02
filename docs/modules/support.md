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

- [공통 유체 상태·물성 기준 객체 / Shared fluid/state/reference contract](#module-h2physics-core-thermostate)
- [열 이름·단위·시간축을 가진 시계열 객체 / Named time-series columns, units and clocks](#module-h2physics-core-timeseries)
- [공통 유한 화학양론 전환 수지 / Shared finite stoichiometric conversion accounting](#module-h2physics-reactions-stoichiometricreaction-convert)
- [구간 적분 질량을 유지하는 유한 방출원 객체 / Conservative finite-window mass-source contract](#module-h2physics-sources-intervalmasssource)
- [하나의 기계적 압력 하중에 대한 실제 시간 이력 / One mechanical pressure load versus physical time](#module-h2physics-pressure_loads-pressuretimehistory)
- [샘플별 시설 노드 질량·에너지 연속성 검사 / Sampled node mass and energy continuity](#module-h2physics-facility_continuity-facilitycontinuityaudit-audit)
- [대체 경로 없이 분야·수준·공급자를 명시 선택 / Exact family/level/provider selection without fallback](#module-h2physics-model_selection-modelregistry-select)

<a id="module-h2physics-core-thermostate"></a>

## 공통 유체 상태·물성 기준 객체 / Shared fluid/state/reference contract

Family / navigation ID: `support.state`

Import module: `h2physics.core`; selected entry: `ThermoState`.

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

### Returned value / 반환값

`ThermoState`

### Related input/return records / 관련 입력·반환 객체

#### `h2physics.core.PropertyBasis`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/core.py#L97)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `fluid` | `str` | `required` |
| `reference_id` | `str` | `required` |
| `spin_composition` | `str` | `'unspecified'` |


<a id="module-h2physics-core-timeseries"></a>

## 열 이름·단위·시간축을 가진 시계열 객체 / Named time-series columns, units and clocks

Family / navigation ID: `support.series`

Import module: `h2physics.core`; selected entry: `TimeSeries`.

#### `h2physics.core.TimeSeries`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/core.py#L195)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `time_s` | `NDArray[np.float64]` | `required` |
| `values` | `NDArray[np.float64]` | `required` |
| `channels` | `tuple[str, ...]` | `required` |
| `units` | `tuple[str, ...]` | `required` |
| `valid` | `NDArray[np.bool_]` | `required` |
| `clock_id` | `str` | `required` |
| `origin` | `Origin` | `required` |
| `source_id` | `str` | `required` |
| `quantities` | `tuple[str, ...]` | `required` |
| `basis_ids` | `tuple[str, ...]` | `()` |

### Returned value / 반환값

`TimeSeries`


<a id="module-h2physics-reactions-stoichiometricreaction-convert"></a>

## 공통 유한 화학양론 전환 수지 / Shared finite stoichiometric conversion accounting

Family / navigation ID: `support.reaction`

Import module: `h2physics.reactions`; selected entry: `StoichiometricReaction.convert`.

#### `h2physics.reactions.StoichiometricReaction`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/reactions.py#L41)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `identifier` | `str` | `required` |
| `species` | `tuple[ChemicalSpecies, ...]` | `required` |
| `coefficients` | `tuple[float, ...]` | `required` |

#### `h2physics.reactions.StoichiometricReaction.convert`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/reactions.py#L94)

```python
convert(self, supplied: Mapping[str, float], extent_mol: float) -> 'ReactionConversion'
```

### Returned value / 반환값

`ReactionConversion`

### Related input/return records / 관련 입력·반환 객체

#### `h2physics.reactions.ChemicalSpecies`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/reactions.py#L20)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `identifier` | `str` | `required` |
| `elements` | `Mapping[str, int]` | `required` |
| `molar_mass_kg_mol` | `float` | `required` |
| `phase` | `str` | `required` |
| `charge` | `int` | `0` |

#### `h2physics.reactions.ReactionConversion`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/reactions.py#L107)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `reaction` | `StoichiometricReaction` | `required` |
| `extent_mol` | `float` | `required` |
| `initial_mol` | `np.ndarray` | `required` |
| `final_mol` | `np.ndarray` | `required` |
| `maximum_roundoff_correction_mol` | `float` | `required` |

Computed properties: `mass_residual_kg`, `final_amounts`.


<a id="module-h2physics-sources-intervalmasssource"></a>

## 구간 적분 질량을 유지하는 유한 방출원 객체 / Conservative finite-window mass-source contract

Family / navigation ID: `support.sources`

Import module: `h2physics.sources`; selected entry: `IntervalMassSource`.

#### `h2physics.sources.IntervalMassSource`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/sources.py#L17)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `location` | `SourceLocation` | `required` |
| `edges_s` | `np.ndarray` | `required` |
| `mass_kg` | `np.ndarray` | `required` |
| `state` | `ThermoState` | `required` |
| `origin` | `Origin` | `required` |
| `evidence_id` | `str` | `required` |
| `end_reason` | `str` | `required` |

Computed properties: `total_mass_kg`, `mean_rates_kg_s`, `enthalpy_transfer_j`.

### Returned value / 반환값

`IntervalMassSource`

### Related input/return records / 관련 입력·반환 객체

#### `h2physics.release.SourceLocation`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/release.py#L278)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `source_id` | `str` | `required` |
| `clock_id` | `str` | `required` |
| `coordinate_frame_id` | `str` | `required` |
| `position_m` | `tuple[float, float, float]` | `required` |
| `direction_unit` | `tuple[float, float, float]` | `required` |

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


<a id="module-h2physics-pressure_loads-pressuretimehistory"></a>

## 하나의 기계적 압력 하중에 대한 실제 시간 이력 / One mechanical pressure load versus physical time

Family / navigation ID: `support.pressure_history`

Import module: `h2physics.pressure_loads`; selected entry: `PressureTimeHistory`.

#### `h2physics.pressure_loads.PressureTimeHistory`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/pressure_loads.py#L16)

Piecewise-linear applied pressure in Pa on an identified event clock.

Pressure is the net pressure difference across the loaded surface; positive
acts in the selected displacement direction. It is zero outside the sampled
support. Nonzero endpoints therefore declare instantaneous load jumps.
Reflection and spatial-to-generalized-load factors belong to the supplier.

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `time_s` | `np.ndarray` | `required` |
| `differential_pressure_pa` | `np.ndarray` | `required` |
| `clock_id` | `str` | `required` |
| `load_id` | `str` | `required` |
| `evidence_id` | `str` | `required` |

Computed properties: `signed_impulse_pa_s`.

### Returned value / 반환값

`PressureTimeHistory`


<a id="module-h2physics-facility_continuity-facilitycontinuityaudit-audit"></a>

## 샘플별 시설 노드 질량·에너지 연속성 검사 / Sampled node mass and energy continuity

Family / navigation ID: `support.continuity`

Import module: `h2physics.facility_continuity`; selected entry: `FacilityContinuityAudit.audit`.

#### `h2physics.facility_continuity.FacilityContinuityAudit`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/facility_continuity.py#L160)

Audit a fixed node/port topology without recalculating equipment physics.

```python
FacilityContinuityAudit(nodes: Iterable[FacilityNode], *, tolerances: EquipmentTolerances | None=None)
```

Computed properties: `nodes`.

#### `h2physics.facility_continuity.FacilityContinuityAudit.audit`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/facility_continuity.py#L182)

```python
audit(self, frame: FacilityContinuityFrame, *, require_closed: bool=True) -> FacilityContinuityResult
```

### Returned value / 반환값

`FacilityContinuityResult`

### Related input/return records / 관련 입력·반환 객체

#### `h2physics.facility_continuity.FacilityNode`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/facility_continuity.py#L24)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `node_id` | `str` | `required` |
| `basis` | `PropertyBasis` | `required` |

#### `h2physics.equipment.EquipmentTolerances`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/equipment.py#L87)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `mass_absolute_kg_s` | `float` | `1e-08` |
| `energy_absolute_w` | `float` | `0.05` |
| `momentum_absolute_pa` | `float` | `0.01` |
| `relative` | `float` | `1e-06` |

#### `h2physics.facility_continuity.FacilityContinuityFrame`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/facility_continuity.py#L85)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `clock_id` | `str` | `required` |
| `time_s` | `float` | `required` |
| `transfers` | `tuple[ConnectionTransfer, ...]` | `required` |
| `external_rates` | `tuple[ExternalFacilityRate, ...]` | `()` |
| `storage_rates` | `tuple[FacilityStorageRate, ...]` | `()` |

#### `h2physics.facility_continuity.FacilityContinuityResult`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/facility_continuity.py#L122)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `clock_id` | `str` | `required` |
| `time_s` | `float` | `required` |
| `nodes` | `tuple[NodeContinuity, ...]` | `required` |
| `component_energy_residual_w` | `tuple[tuple[str, float], ...]` | `required` |

Computed properties: `mass_residual_kg_s`, `node_energy_residual_w`, `equipment_energy_residual_w`.

#### `h2physics.core.PropertyBasis`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/core.py#L97)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `fluid` | `str` | `required` |
| `reference_id` | `str` | `required` |
| `spin_composition` | `str` | `'unspecified'` |

#### `h2physics.equipment.ConnectionTransfer`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/equipment.py#L28)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `component_id` | `str` | `required` |
| `left_node` | `str` | `required` |
| `right_node` | `str` | `required` |
| `left_port_id` | `str` | `required` |
| `right_port_id` | `str` | `required` |
| `mass_flow_kg_s` | `float` | `required` |
| `upstream` | `ThermoState &#124; None` | `required` |
| `transmitted` | `ThermoState &#124; None` | `required` |
| `power` | `BoundaryPower` | `required` |
| `momentum_residual_pa` | `float &#124; None` | `required` |
| `operating_point_admissible` | `bool &#124; None` | `required` |

Computed properties: `upstream_node`, `downstream_node`, `inlet_enthalpy_flow_w`, `outlet_enthalpy_flow_w`, `energy_residual_w`.

#### `h2physics.facility_continuity.ExternalFacilityRate`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/facility_continuity.py#L35)

One declared material or non-material boundary at a facility node.

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `boundary_id` | `str` | `required` |
| `node_id` | `str` | `required` |
| `port_id` | `str` | `required` |
| `mass_flow_into_node_kg_s` | `float` | `required` |
| `transported_state` | `ThermoState &#124; None` | `None` |
| `heat_into_node_w` | `float` | `0.0` |
| `shaft_work_into_node_w` | `float` | `0.0` |

Computed properties: `material_energy_into_node_w`, `nonmaterial_energy_into_node_w`.

#### `h2physics.facility_continuity.FacilityStorageRate`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/facility_continuity.py#L70)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `node_id` | `str` | `required` |
| `basis` | `PropertyBasis` | `required` |
| `mass_accumulation_kg_s` | `float` | `required` |
| `energy_accumulation_w` | `float` | `required` |

#### `h2physics.facility_continuity.NodeContinuity`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/facility_continuity.py#L104)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `node_id` | `str` | `required` |
| `mass_accumulation_kg_s` | `float` | `required` |
| `material_flow_into_node_kg_s` | `float` | `required` |
| `energy_accumulation_w` | `float` | `required` |
| `material_energy_into_node_w` | `float` | `required` |
| `nonmaterial_energy_into_node_w` | `float` | `required` |

Computed properties: `mass_residual_kg_s`, `energy_residual_w`.


<a id="module-h2physics-model_selection-modelregistry-select"></a>

## 대체 경로 없이 분야·수준·공급자를 명시 선택 / Exact family/level/provider selection without fallback

Family / navigation ID: `support.selection`

Import module: `h2physics.model_selection`; selected entry: `ModelRegistry.select`.

#### `h2physics.model_selection.ModelRegistry`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/model_selection.py#L98)

Caller-owned registry. Registration and selection never import a provider.

```python
ModelRegistry(families=MODELS)
```

Computed properties: `families`, `bindings`.

#### `h2physics.model_selection.ModelRegistry.select`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/model_selection.py#L132)

```python
select(self, request: ModelRequest)
```

The source has no explicit return annotation; inspect its return statements and the domain manual. No return type is invented by this generator.

### Returned value / 반환값

`ModelSelection`

This return contract was reviewed from the implementation; it is not an annotation present in the source signature.

### Related input/return records / 관련 입력·반환 객체

#### `h2physics.model_selection.ModelSelection`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/model_selection.py#L154)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `registry` | `ModelRegistry` | `field(repr=False, compare=False)` |
| `request` | `ModelRequest` | `required` |
| `binding` | `ProviderBinding` | `required` |

#### `h2physics.model_selection.ModelRequest`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/model_selection.py#L33)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `family_id` | `str` | `required` |
| `level_id` | `str` | `required` |
| `provider_id` | `str` | `required` |
| `accepted_statuses` | `frozenset[str]` | `required` |
| `required_capabilities` | `frozenset[str]` | `required` |
| `required_evidence_ids` | `frozenset[str]` | `frozenset()` |

#### `h2physics.model_selection.ProviderBinding`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/model_selection.py#L54)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `family_id` | `str` | `required` |
| `level_id` | `str` | `required` |
| `provider_id` | `str` | `required` |
| `status` | `str` | `required` |
| `revision` | `str` | `required` |
| `capabilities` | `frozenset[str]` | `required` |
| `evidence_ids` | `frozenset[str]` | `required` |
| `factory` | `object` | `field(repr=False, compare=False)` |

Computed properties: `key`.


## Maintaining this guide / 갱신

Curated purposes and entry selection live in `scripts/readme_module_guide.py`. Run `python scripts/readme_module_guide.py` to regenerate both README blocks and this file. Run `python scripts/readme_module_guide.py --check` to reject stale output, unresolved callables or missing catalog IDs. The script parses source with the standard library, imports no physical engine and runs no calculation. Review purpose/units/limits against domain manuals when an API changes. It preserves authored scientific attribution and performs no automatic translation of external material.
