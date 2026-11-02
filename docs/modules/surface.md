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

- [외부 액체 풀 퍼짐·저장량·구간별 증발 방출원 / Native pool spreading/storage and finite vapor-source intervals](#module-h2physics-adapters-pool-nativedynamicpool-run)

<a id="module-h2physics-adapters-pool-nativedynamicpool-run"></a>

## 외부 액체 풀 퍼짐·저장량·구간별 증발 방출원 / Native pool spreading/storage and finite vapor-source intervals

Family / navigation ID: `surface.pool`

Import module: `h2physics.adapters.pool`; selected entry: `NativeDynamicPool.run`.

#### `h2physics.adapters.pool.NativeDynamicPool`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/pool.py#L159)

```python
NativeDynamicPool(runner: Callable[..., Any], reference_properties, *, engine_id: str, tolerances: PoolTolerances | None=None)
```

#### `h2physics.adapters.pool.NativeDynamicPool.run`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/pool.py#L170)

```python
run(self, config, inflow: DeclaredGroundInflow, *, output_times_s, vapor_location: SourceLocation, require_closed: bool=True) -> NativePoolRun
```

### Returned value / 반환값

`NativePoolRun`

### Related input/return records / 관련 입력·반환 객체

#### `h2physics.adapters.pool.PoolTolerances`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/pool.py#L65)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `absolute_mass_kg` | `float` | `1e-10` |
| `relative_mass` | `float` | `1e-08` |
| `maximum_numerical_adjustment_kg` | `float` | `0.0` |
| `maximum_escaped_mass_kg` | `float` | `0.0` |
| `property_relative` | `float` | `1e-08` |
| `event_clock_roundoff_s` | `float` | `0.0` |

#### `h2physics.adapters.pool.DeclaredGroundInflow`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/pool.py#L21)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `native` | `Any` | `required` |
| `location` | `SourceLocation` | `required` |
| `liquid_state` | `ThermoState` | `required` |
| `start_time_s` | `float` | `required` |
| `end_time_s` | `float` | `required` |
| `origin` | `Origin` | `required` |
| `evidence_id` | `str` | `required` |
| `end_reason` | `str` | `required` |
| `schedule_times_s` | `tuple[float, ...]` | `field(init=False)` |
| `schedule_rates_kg_s` | `tuple[float, ...]` | `field(init=False)` |

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

#### `h2physics.adapters.pool.NativePoolRun`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/pool.py#L121)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `native` | `Any` | `required` |
| `config` | `Any` | `required` |
| `inflow` | `DeclaredGroundInflow` | `required` |
| `vapor_location` | `SourceLocation` | `required` |
| `liquid_state` | `ThermoState` | `required` |
| `vapor_state` | `ThermoState` | `required` |
| `samples` | `tuple[PoolSampleAudit, ...]` | `required` |
| `engine_id` | `str` | `required` |
| `issues` | `tuple[str, ...]` | `required` |
| `input_clock` | `EventClockInflow &#124; None` | `required` |

Computed properties: `admissible`, `validation_qualified`, `maximum_input_clock_correction_s`.

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

#### `h2physics.adapters.pool.PoolSampleAudit`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/pool.py#L106)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `time_s` | `float` | `required` |
| `native` | `Any` | `required` |
| `declared_cumulative_inflow_kg` | `float` | `required` |
| `independently_recomputed_mass_residual_kg` | `float` | `required` |
| `mass_limit_kg` | `float` | `required` |

#### `h2physics.adapters.pool.EventClockInflow`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/pool.py#L82)

An explicit bounded time correction before calling the actual native input.

The reviewed runner accepts this dataclass structurally. Its native input
remains available, and every nonzero time correction is retained.

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `times_s` | `tuple[float, ...]` | `required` |
| `rates_kg_s` | `tuple[float, ...]` | `required` |
| `native` | `Any` | `required` |
| `roundoff_s` | `float` | `required` |
| `corrections_s` | `list[tuple[float, float]]` | `field(default_factory=list)` |


## Maintaining this guide / 갱신

Curated purposes and entry selection live in `scripts/readme_module_guide.py`. Run `python scripts/readme_module_guide.py` to regenerate both README blocks and this file. Run `python scripts/readme_module_guide.py --check` to reject stale output, unresolved callables or missing catalog IDs. The script parses source with the standard library, imports no physical engine and runs no calculation. Review purpose/units/limits against domain manuals when an API changes. It preserves authored scientific attribution and performs no automatic translation of external material.
