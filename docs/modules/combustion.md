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

- [외부 HP/UV 단열 반응 평형 / Native HP/UV adiabatic reacting equilibrium](#module-h2physics-adapters-cantera-canteragas-equilibrium)
- [외부 밀폐 반응기의 시간별 반응·상태 계산 / Native closed reacting-vessel time integration](#module-h2physics-adapters-cantera-canteragas-closed_reactor)
- [외부 1차원 예혼합 층류 화염속도 / Native one-dimensional premixed laminar flame](#module-h2physics-adapters-cantera-canteragas-free_flame)
- [외부 대향류 비예혼합 화염 / Native opposed-flow nonpremixed flame](#module-h2physics-combustion-counterflow-solve_counterflow_diffusion_flame)
- [조건부 외부 정상 제트 화염·복사와 허용영역 검사 / Conditional native steady jet flame and radiation gates](#module-h2physics-adapters-hyram_flame-run_hyram_flame)
- [연소율·점화가 주어진 조건부 유한 풀 연소 / Conditional finite pool burning with supplied flux and ignition](#module-h2physics-adapters-pool_fire-finitepoolfire-run)
- [조건부 물질 경로 화염 전파·유한 구획 연소 / Conditional material-path front and finite parcel burn](#module-h2physics-adapters-flash_front-run_material_front)
- [피스톤 체적·일을 포함한 밀폐 충전 엔진 구간 / Native closed-charge engine interval with piston work](#module-h2physics-combustion-closed_charge_engine-run_closed_charge_engine_segment)
- [밸브·유입출 경계를 명시한 개방 실린더 구간 / Native open-cylinder interval with declared valves and ports](#module-h2physics-combustion-open_cylinder_engine-run_open_cylinder_segment)
- [외부 반응 평형을 이용한 수소 Brayton 기준 사이클 / Native-equilibrium hydrogen Brayton reference](#module-h2physics-combustion-open_brayton-run_open_cycle_brayton)
- [기기 맵·유량·축 동력 잔차를 맞추는 운전점 해석 / Bounded component-map operating-point solve](#module-h2physics-combustion-steady_map_solver-solve_steady_map_operating_point)
- [지정 터빈·압축기 동력에 따른 단축 회전 에너지 응답 / One-shaft energy dynamics with supplied turbine/compressor powers](#module-h2physics-combustion-shaft_transient-integrate_shaft_transient)
- [참여 수소 에너지를 입력한 조건부 비구속 최고 과압 / Conditional unconfined peak from supplied participating energy](#module-h2physics-adapters-hyram_overpressure-hyrambauwensoverpressure-evaluate)
- [외부 평형 CJ 폭굉 종단 상태 / Native equilibrium CJ detonation endpoint](#module-h2physics-adapters-detonation-sdtoolboxdetonation-cj)
- [외부 동결 이상기체 정상 충격파 / Native frozen ideal-gas normal shock](#module-h2physics-adapters-detonation-sdtoolboxdetonation-frozen_shock)

<a id="module-h2physics-adapters-cantera-canteragas-equilibrium"></a>

## 외부 HP/UV 단열 반응 평형 / Native HP/UV adiabatic reacting equilibrium

Family / navigation ID: `combustion.equilibrium`

Import module: `h2physics.adapters.cantera`; selected entry: `CanteraGas.equilibrium`.

#### `h2physics.adapters.cantera.CanteraGas`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/cantera.py#L392)

Own a fresh native phase for each solve; expose native factories for deep coupling.

Public create_phase returns a retained NativePhaseHandle. Live handles guard
reuse and definitions without retaining all historical native objects.
Legacy callback source bytes remain unverified. from_yaml binds the original
supplied top-level bytes to the declared SHA; it does not qualify a mechanism.

```python
CanteraGas(phase_factory: Callable, basis: MechanismBasis)
```

Computed properties: `mechanism_source`, `source_bytes_verified`, `live_phase_handle_count`, `last_legacy_phase_handle`.

#### `h2physics.adapters.cantera.CanteraGas.equilibrium`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/cantera.py#L599)

```python
equilibrium(self, initial: ReactiveState, *, constraint: Literal['HP', 'UV']='HP', relative_tolerance: float=1e-09) -> EquilibriumResult
```

### Returned value / 반환값

`EquilibriumResult`

### Related input/return records / 관련 입력·반환 객체

#### `h2physics.adapters.cantera.MechanismBasis`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/cantera.py#L22)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `identifier` | `str` | `required` |
| `source_sha256` | `str` | `required` |
| `license_id` | `str` | `required` |
| `references` | `tuple[str, ...]` | `required` |
| `minimum_temperature_k` | `float` | `required` |
| `maximum_temperature_k` | `float` | `required` |
| `minimum_pressure_pa` | `float` | `required` |
| `maximum_pressure_pa` | `float` | `required` |

#### `h2physics.adapters.cantera.ReactiveState`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/cantera.py#L51)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `temperature_k` | `float` | `required` |
| `pressure_pa` | `float` | `required` |
| `mole_fractions` | `Mapping[str, float]` | `required` |

#### `h2physics.adapters.cantera.EquilibriumResult`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/cantera.py#L189)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `basis` | `MechanismBasis` | `required` |
| `constraint` | `str` | `required` |
| `initial` | `ReactiveSnapshot` | `required` |
| `final` | `ReactiveSnapshot` | `required` |
| `energy_residual_j_kg` | `float` | `required` |
| `maximum_element_mass_fraction_residual` | `float` | `required` |

#### `h2physics.adapters.cantera.ReactiveSnapshot`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/cantera.py#L70)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `state` | `ReactiveState` | `required` |
| `density_kg_m3` | `float` | `required` |
| `enthalpy_j_kg` | `float` | `required` |
| `internal_energy_j_kg` | `float` | `required` |
| `elemental_mass_fractions` | `tuple[tuple[str, float], ...]` | `required` |


<a id="module-h2physics-adapters-cantera-canteragas-closed_reactor"></a>

## 외부 밀폐 반응기의 시간별 반응·상태 계산 / Native closed reacting-vessel time integration

Family / navigation ID: `combustion.kinetics`

Import module: `h2physics.adapters.cantera`; selected entry: `CanteraGas.closed_reactor`.

#### `h2physics.adapters.cantera.CanteraGas`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/cantera.py#L392)

Own a fresh native phase for each solve; expose native factories for deep coupling.

Public create_phase returns a retained NativePhaseHandle. Live handles guard
reuse and definitions without retaining all historical native objects.
Legacy callback source bytes remain unverified. from_yaml binds the original
supplied top-level bytes to the declared SHA; it does not qualify a mechanism.

```python
CanteraGas(phase_factory: Callable, basis: MechanismBasis)
```

Computed properties: `mechanism_source`, `source_bytes_verified`, `live_phase_handle_count`, `last_legacy_phase_handle`.

#### `h2physics.adapters.cantera.CanteraGas.closed_reactor`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/cantera.py#L614)

```python
closed_reactor(self, initial: ReactiveState, time_s, *, constraint: Literal['HP', 'UV']='UV', maximum_time_step_s: float, relative_tolerance: float=1e-09, absolute_tolerance: float=1e-18) -> ReactorTrace
```

### Returned value / 반환값

`ReactorTrace`

### Related input/return records / 관련 입력·반환 객체

#### `h2physics.adapters.cantera.MechanismBasis`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/cantera.py#L22)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `identifier` | `str` | `required` |
| `source_sha256` | `str` | `required` |
| `license_id` | `str` | `required` |
| `references` | `tuple[str, ...]` | `required` |
| `minimum_temperature_k` | `float` | `required` |
| `maximum_temperature_k` | `float` | `required` |
| `minimum_pressure_pa` | `float` | `required` |
| `maximum_pressure_pa` | `float` | `required` |

#### `h2physics.adapters.cantera.ReactiveState`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/cantera.py#L51)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `temperature_k` | `float` | `required` |
| `pressure_pa` | `float` | `required` |
| `mole_fractions` | `Mapping[str, float]` | `required` |

#### `h2physics.adapters.cantera.ReactorTrace`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/cantera.py#L224)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `basis` | `MechanismBasis` | `required` |
| `constraint` | `str` | `required` |
| `time_s` | `np.ndarray` | `required` |
| `snapshots` | `tuple[ReactiveSnapshot, ...]` | `required` |
| `maximum_energy_residual_j_kg` | `float` | `required` |
| `maximum_element_mass_fraction_residual` | `float` | `required` |

#### `h2physics.adapters.cantera.ReactiveSnapshot`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/cantera.py#L70)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `state` | `ReactiveState` | `required` |
| `density_kg_m3` | `float` | `required` |
| `enthalpy_j_kg` | `float` | `required` |
| `internal_energy_j_kg` | `float` | `required` |
| `elemental_mass_fractions` | `tuple[tuple[str, float], ...]` | `required` |


<a id="module-h2physics-adapters-cantera-canteragas-free_flame"></a>

## 외부 1차원 예혼합 층류 화염속도 / Native one-dimensional premixed laminar flame

Family / navigation ID: `combustion.laminar_flame`

Import module: `h2physics.adapters.cantera`; selected entry: `CanteraGas.free_flame`.

#### `h2physics.adapters.cantera.CanteraGas`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/cantera.py#L392)

Own a fresh native phase for each solve; expose native factories for deep coupling.

Public create_phase returns a retained NativePhaseHandle. Live handles guard
reuse and definitions without retaining all historical native objects.
Legacy callback source bytes remain unverified. from_yaml binds the original
supplied top-level bytes to the declared SHA; it does not qualify a mechanism.

```python
CanteraGas(phase_factory: Callable, basis: MechanismBasis)
```

Computed properties: `mechanism_source`, `source_bytes_verified`, `live_phase_handle_count`, `last_legacy_phase_handle`.

#### `h2physics.adapters.cantera.CanteraGas.free_flame`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/cantera.py#L651)

Return an actual native freely propagating, premixed 1D flame solution.

Grid/domain refinement and experimental comparison are caller research
tasks. The returned object stays editable; changing it invalidates the
recorded summary. This is not an enclosure explosion or a detonation.

```python
free_flame(self, initial: ReactiveState, settings: FlameSettings) -> FreeFlameResult
```

### Returned value / 반환값

`FreeFlameResult`

### Related input/return records / 관련 입력·반환 객체

#### `h2physics.adapters.cantera.MechanismBasis`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/cantera.py#L22)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `identifier` | `str` | `required` |
| `source_sha256` | `str` | `required` |
| `license_id` | `str` | `required` |
| `references` | `tuple[str, ...]` | `required` |
| `minimum_temperature_k` | `float` | `required` |
| `maximum_temperature_k` | `float` | `required` |
| `minimum_pressure_pa` | `float` | `required` |
| `maximum_pressure_pa` | `float` | `required` |

#### `h2physics.adapters.cantera.ReactiveState`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/cantera.py#L51)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `temperature_k` | `float` | `required` |
| `pressure_pa` | `float` | `required` |
| `mole_fractions` | `Mapping[str, float]` | `required` |

#### `h2physics.adapters.cantera.FlameSettings`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/cantera.py#L271)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `width_m` | `float` | `required` |
| `refinement_ratio` | `float` | `3.0` |
| `refinement_slope` | `float` | `0.08` |
| `refinement_curve` | `float` | `0.12` |
| `transport_model` | `Literal['mixture-averaged', 'multicomponent']` | `'multicomponent'` |
| `soret_enabled` | `bool` | `True` |
| `maximum_grid_points` | `int` | `1000` |

#### `h2physics.adapters.cantera.FreeFlameResult`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/cantera.py#L295)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `basis` | `MechanismBasis` | `required` |
| `settings` | `FlameSettings` | `required` |
| `speed_m_s` | `float` | `required` |
| `grid_points` | `int` | `required` |
| `relative_mass_flux_span` | `float` | `required` |
| `native_solution` | `object` | `required` |
| `native_phase_handle` | `NativePhaseHandle &#124; None` | `None` |

#### `h2physics.adapters.cantera.NativePhaseHandle`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/cantera.py#L113)

A retained live lease on an original native phase, not a state lock.

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `owner` | `object` | `required` |
| `basis` | `MechanismBasis` | `required` |
| `native_phase` | `object` | `required` |
| `requested_state` | `ReactiveState` | `required` |
| `creation_snapshot` | `ReactiveSnapshot` | `required` |
| `definition_sha256` | `str` | `required` |
| `source_sha256` | `str` | `required` |
| `source_bytes_verified` | `bool` | `required` |
| `source_phase_name` | `str &#124; None` | `required` |


<a id="module-h2physics-combustion-counterflow-solve_counterflow_diffusion_flame"></a>

## 외부 대향류 비예혼합 화염 / Native opposed-flow nonpremixed flame

Family / navigation ID: `combustion.laminar_flame`

Import module: `h2physics.combustion.counterflow`; selected entry: `solve_counterflow_diffusion_flame`.

#### `h2physics.combustion.counterflow.solve_counterflow_diffusion_flame`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/combustion/counterflow.py#L330)

Solve one steady opposed-flow flame through the original Cantera owner.

Inlet mass fluxes are caller inputs, not inferred from a release source.
The two inlets must share an absolute pressure and the selected mechanism
must cover both inlet states and the resulting temperature profile.

```python
solve_counterflow_diffusion_flame(gas_owner: CanteraGas, fuel: CounterflowBoundary, oxidizer: CounterflowBoundary, *, settings: CounterflowFlameSettings=CounterflowFlameSettings()) -> CounterflowFlameResult
```

### Returned value / 반환값

`CounterflowFlameResult`

### Related input/return records / 관련 입력·반환 객체

#### `h2physics.combustion.counterflow.CounterflowBoundary`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/combustion/counterflow.py#L46)

One physical inlet, with a fresh composition and declared mass flux.

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `state` | `ReactiveState` | `required` |
| `mass_flux_kg_m2_s` | `float` | `required` |

#### `h2physics.combustion.counterflow.CounterflowFlameSettings`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/combustion/counterflow.py#L60)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `width_m` | `float` | `0.02` |
| `transport_model` | `Literal['mixture-averaged', 'multicomponent']` | `'multicomponent'` |
| `soret_enabled` | `bool` | `True` |
| `radiation_enabled` | `bool` | `False` |
| `refinement_ratio` | `float` | `4.0` |
| `refinement_slope` | `float` | `0.1` |
| `refinement_curve` | `float` | `0.2` |
| `refinement_prune` | `float` | `0.0` |
| `maximum_grid_points` | `int` | `1000` |
| `loglevel` | `int` | `0` |

#### `h2physics.combustion.counterflow.CounterflowFlameResult`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/combustion/counterflow.py#L100)

Owner-issued summary retaining the exact editable native solution.

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `gas_owner` | `CanteraGas` | `field(repr=False, compare=False)` |
| `mechanism_basis` | `MechanismBasis` | `required` |
| `phase_handle` | `NativePhaseHandle` | `field(repr=False, compare=False)` |
| `fuel` | `CounterflowBoundary` | `required` |
| `oxidizer` | `CounterflowBoundary` | `required` |
| `settings` | `CounterflowFlameSettings` | `required` |
| `pressure_pa` | `float` | `required` |
| `grid_points` | `int` | `required` |
| `peak_temperature_k` | `float` | `required` |
| `peak_temperature_position_m` | `float` | `required` |
| `maximum_velocity_gradient_s_inv` | `float` | `required` |
| `extinct` | `bool` | `required` |
| `native_solution` | `object` | `field(repr=False, compare=False)` |
| `solution_sha256` | `str` | `required` |

#### `h2physics.adapters.cantera.ReactiveState`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/cantera.py#L51)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `temperature_k` | `float` | `required` |
| `pressure_pa` | `float` | `required` |
| `mole_fractions` | `Mapping[str, float]` | `required` |

#### `h2physics.adapters.cantera.MechanismBasis`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/cantera.py#L22)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `identifier` | `str` | `required` |
| `source_sha256` | `str` | `required` |
| `license_id` | `str` | `required` |
| `references` | `tuple[str, ...]` | `required` |
| `minimum_temperature_k` | `float` | `required` |
| `maximum_temperature_k` | `float` | `required` |
| `minimum_pressure_pa` | `float` | `required` |
| `maximum_pressure_pa` | `float` | `required` |

#### `h2physics.adapters.cantera.NativePhaseHandle`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/cantera.py#L113)

A retained live lease on an original native phase, not a state lock.

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `owner` | `object` | `required` |
| `basis` | `MechanismBasis` | `required` |
| `native_phase` | `object` | `required` |
| `requested_state` | `ReactiveState` | `required` |
| `creation_snapshot` | `ReactiveSnapshot` | `required` |
| `definition_sha256` | `str` | `required` |
| `source_sha256` | `str` | `required` |
| `source_bytes_verified` | `bool` | `required` |
| `source_phase_name` | `str &#124; None` | `required` |


<a id="module-h2physics-adapters-hyram_flame-run_hyram_flame"></a>

## 조건부 외부 정상 제트 화염·복사와 허용영역 검사 / Conditional native steady jet flame and radiation gates

Family / navigation ID: `combustion.jet_fire`

Import module: `h2physics.adapters.hyram_flame`; selected entry: `run_hyram_flame`.

#### `h2physics.adapters.hyram_flame.run_hyram_flame`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/hyram_flame.py#L299)

Execute native Flame from a reservoir, then audit its complete visible field.

Supply actual HyRAM+ 6.1 factories/functions. No optional engine is imported
at module import. The native pipeline owns the only choking/expansion solve;
no shared-nozzle exit, prescribed mdot, developed-flow surrogate or chemistry
object can replace it through solver_options. Calm normal gaseous H2/air is
the checked level. Native warnings and inadmissible fields remain visible.

```python
run_hyram_flame(*, fluid_factory: Callable, orifice_factory: Callable, flame_factory: Callable, transmissivity_function: Callable, upstream: ThermoState, ambient: ThermoState, opening: NozzleOpening, location: SourceLocation, window: SteadyFlameWindow, solver_options: Mapping[str, Any], policy: FlameAuditPolicy=FlameAuditPolicy(), require_accepted: bool=True) -> HyRAMFlameRun
```

### Returned value / 반환값

`HyRAMFlameRun`

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

#### `h2physics.release.NozzleOpening`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/release.py#L28)

An effective-area closure; the factor is not a measured velocity model.

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `opening_id` | `str` | `required` |
| `nominal_area_m2` | `float` | `required` |
| `effective_area_factor` | `float` | `required` |
| `area_basis_id` | `str` | `required` |

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

#### `h2physics.adapters.hyram_flame.SteadyFlameWindow`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/hyram_flame.py#L23)

Caller-evidenced steady premise, not a computed ignition/duration model.

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `clock_id` | `str` | `required` |
| `start_s` | `float` | `required` |
| `end_s` | `float` | `required` |
| `source_evidence_id` | `str` | `required` |
| `steady_evidence_id` | `str` | `required` |
| `origin` | `Origin` | `required` |

#### `h2physics.adapters.hyram_flame.FlameAuditPolicy`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/hyram_flame.py#L45)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `relative_mass_tolerance` | `float` | `0.001` |
| `absolute_mass_tolerance_kg_s` | `float` | `1e-09` |
| `relative_source_energy_tolerance` | `float` | `1e-06` |
| `absolute_source_energy_tolerance_w` | `float` | `0.1` |
| `relative_quadrature_tolerance` | `float` | `1e-07` |
| `relative_caloric_tolerance` | `float` | `0.001` |
| `absolute_caloric_tolerance_j_kg` | `float` | `1.0` |
| `radial_cutoff_widths` | `float` | `8.0` |
| `radial_panels` | `int` | `32` |
| `quadrature_order` | `int` | `16` |

#### `h2physics.adapters.hyram_flame.HyRAMFlameRun`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/hyram_flame.py#L195)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `native` | `Any` | `required` |
| `native_signature` | `str` | `required` |
| `upstream` | `ThermoState` | `required` |
| `ambient` | `ThermoState` | `required` |
| `opening` | `NozzleOpening` | `required` |
| `location` | `SourceLocation` | `required` |
| `window` | `SteadyFlameWindow` | `required` |
| `solver_options` | `Mapping[str, Any]` | `required` |
| `policy` | `FlameAuditPolicy` | `required` |
| `transmissivity_function` | `Callable` | `required` |
| `mass_flow_kg_s` | `float` | `required` |
| `expanded_mass_flow_kg_s` | `float` | `required` |
| `fuel_origin_flows_kg_s` | `np.ndarray` | `required` |
| `maximum_section_quadrature_difference_kg_s` | `float` | `required` |
| `maximum_source_mass_residual_kg_s` | `float` | `required` |
| `maximum_transport_mass_residual_kg_s` | `float` | `required` |
| `throat_energy_residual_w` | `float` | `required` |
| `expansion_energy_residual_w` | `float` | `required` |
| `native_heat_of_combustion_j_kg` | `float` | `required` |
| `chemical_power_w` | `float` | `required` |
| `emitted_radiative_power_w` | `float` | `required` |
| `radiant_fraction` | `float` | `required` |
| `radiant_power_residual_w` | `float` | `required` |
| `combustion_caloric_audit` | `np.ndarray` | `required` |
| `centreline` | `np.ndarray` | `required` |
| `warning_messages` | `tuple[str, ...]` | `required` |
| `gates` | `Mapping[str, bool]` | `required` |
| `accepted` | `bool` | `required` |

#### `h2physics.core.PropertyBasis`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/core.py#L97)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `fluid` | `str` | `required` |
| `reference_id` | `str` | `required` |
| `spin_composition` | `str` | `'unspecified'` |


<a id="module-h2physics-adapters-pool_fire-finitepoolfire-run"></a>

## 연소율·점화가 주어진 조건부 유한 풀 연소 / Conditional finite pool burning with supplied flux and ignition

Family / navigation ID: `combustion.pool_fire`

Import module: `h2physics.adapters.pool_fire`; selected entry: `FinitePoolFire.run`.

#### `h2physics.adapters.pool_fire.FinitePoolFire`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/pool_fire.py#L491)

Fixed-area complete H2 burning reference with supplied flame geometry.

No replenishment or additional evaporation sink is supported after the seed.
Each consumed kilogram is explicitly gasified, conditioned and combusted.
External conditioning capacity is declared; fire feedback is not inferred.

```python
FinitePoolFire(native: PoolFireNative, seed: PoolFireSeed, reference: H2CombustionReference, reaction: StoichiometricReaction, *, hydrogen_id: str, oxygen_id: str, water_id: str, tolerances: PoolFireTolerances=PoolFireTolerances())
```

#### `h2physics.adapters.pool_fire.FinitePoolFire.run`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/pool_fire.py#L588)

```python
run(self, stages, receptors, *, ignition: DeclaredIgnition, conditioning: ExternalConditioningBudget, initial_oxygen_mol: float, initial_water_mol: float=0.0) -> PoolFireTrace
```

### Returned value / 반환값

`PoolFireTrace`

### Related input/return records / 관련 입력·반환 객체

#### `h2physics.adapters.pool_fire.PoolFireNative`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/pool_fire.py#L71)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `toolkit` | `ConditionalRiskNative` | `required` |
| `fire` | `Any` | `required` |
| `bindings` | `tuple` | `required` |

#### `h2physics.adapters.pool_fire.PoolFireSeed`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/pool_fire.py#L101)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `time_s` | `float` | `required` |
| `liquid_mass_kg` | `float` | `required` |
| `area_m2` | `float` | `required` |
| `location` | `SourceLocation` | `required` |
| `liquid_state` | `ThermoState` | `required` |
| `vapor_state` | `ThermoState` | `required` |
| `thermodynamic_owner` | `Any` | `required` |
| `evidence_id` | `str` | `required` |
| `origin` | `Origin` | `required` |
| `native_pool_run` | `NativePoolRun &#124; None` | `None` |
| `preignition_evaporation` | `IntervalMassSource &#124; None` | `None` |
| `preignition_source_sha256` | `str &#124; None` | `None` |
| `deposited_pool_continuation` | `Any` | `None` |
| `ignition_transition_evidence_id` | `str &#124; None` | `None` |
| `continuation_temperature_tolerance_k` | `float &#124; None` | `None` |
| `continuation_density_relative_tolerance` | `float &#124; None` | `None` |

#### `h2physics.adapters.pool_fire.H2CombustionReference`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/pool_fire.py#L223)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `lower_heating_value_j_kg` | `float` | `required` |
| `reference_hydrogen` | `ThermoState` | `required` |
| `lhv_evidence_id` | `str` | `required` |
| `hydrogen_applicability_id` | `str` | `required` |
| `oxidizer_reference_id` | `str` | `required` |
| `origin` | `Origin` | `required` |
| `water_product_phase` | `str` | `required` |
| `combustion_efficiency` | `float` | `required` |

#### `h2physics.reactions.StoichiometricReaction`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/reactions.py#L41)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `identifier` | `str` | `required` |
| `species` | `tuple[ChemicalSpecies, ...]` | `required` |
| `coefficients` | `tuple[float, ...]` | `required` |

#### `h2physics.adapters.pool_fire.PoolFireTolerances`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/pool_fire.py#L339)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `mass_kg` | `float` | `1e-10` |
| `energy_j` | `float` | `1e-05` |
| `flux_w_m2` | `float` | `1e-08` |
| `geometry_m` | `float` | `1e-09` |
| `clock_s` | `float` | `1e-09` |

#### `h2physics.adapters.pool_fire.DeclaredIgnition`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/pool_fire.py#L264)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `time_s` | `float` | `required` |
| `clock_id` | `str` | `required` |
| `evidence_id` | `str` | `required` |
| `origin` | `Origin` | `required` |

#### `h2physics.adapters.pool_fire.ExternalConditioningBudget`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/pool_fire.py#L247)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `clock_id` | `str` | `required` |
| `available_energy_j` | `float` | `required` |
| `maximum_power_w` | `float` | `required` |
| `evidence_id` | `str` | `required` |
| `origin` | `Origin` | `required` |

#### `h2physics.adapters.pool_fire.PoolFireTrace`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/pool_fire.py#L393)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `seed` | `PoolFireSeed` | `required` |
| `ignition` | `DeclaredIgnition` | `required` |
| `reference` | `H2CombustionReference` | `required` |
| `conditioning` | `ExternalConditioningBudget` | `required` |
| `steps` | `tuple[PoolFireStep, ...]` | `required` |
| `native_provider` | `PoolFireNative` | `required` |
| `reaction` | `StoichiometricReaction` | `required` |
| `initial_oxygen_mol` | `float` | `required` |
| `initial_water_mol` | `float` | `required` |
| `fuel_to_flame` | `IntervalMassSource` | `required` |
| `heat_feedback_solved` | `bool` | `False` |
| `postignition_spreading_solved` | `bool` | `False` |
| `ignition_probability_solved` | `bool` | `False` |
| `dispersion_solved` | `bool` | `False` |
| `total_pool_flame_internal_energy_solved` | `bool` | `False` |
| `external_conditioning_heat_transfer_solved` | `bool` | `False` |
| `full_cryogenic_fire_chain_validated` | `bool` | `False` |
| `status` | `str` | `STATUS` |

#### `h2physics.adapters.conditional_risk.ConditionalRiskNative`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/conditional_risk.py#L276)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `package` | `Any` | `required` |
| `risk_module` | `Any` | `required` |
| `contracts` | `Any` | `required` |
| `api` | `Any` | `required` |
| `version` | `str` | `required` |
| `source_sha256` | `str` | `required` |
| `native_bindings` | `tuple` | `required` |

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

#### `h2physics.adapters.pool_fire.PoolFireStep`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/pool_fire.py#L366)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `stage` | `PoolFireStage` | `required` |
| `native_pool_input` | `Any` | `required` |
| `native_pool_result` | `Any` | `required` |
| `reaction_conversion` | `Any` | `required` |
| `initial_liquid_kg` | `float` | `required` |
| `remaining_liquid_kg` | `float` | `required` |
| `vaporized_and_combusted_kg` | `float` | `required` |
| `active_end_s` | `float` | `required` |
| `oxygen_remaining_mol` | `float` | `required` |
| `water_product_mol` | `float` | `required` |
| `latent_conditioning_j` | `float` | `required` |
| `sensible_conditioning_j` | `float` | `required` |
| `chemical_energy_j` | `float` | `required` |
| `radiation_export_j` | `float` | `required` |
| `convective_export_j` | `float` | `required` |
| `unallocated_release_j` | `float` | `required` |
| `remaining_conditioning_budget_j` | `float` | `required` |
| `emitted_surface_power_w_m2` | `float` | `required` |
| `mass_residual_kg` | `float` | `required` |
| `energy_partition_residual_j` | `float` | `required` |
| `native_energy_residual_j` | `float` | `required` |
| `native_power_energy_residual_j` | `float` | `required` |
| `receptors` | `tuple[ReceptorRadiation, ...]` | `required` |


<a id="module-h2physics-adapters-flash_front-run_material_front"></a>

## 조건부 물질 경로 화염 전파·유한 구획 연소 / Conditional material-path front and finite parcel burn

Family / navigation ID: `combustion.flash_fire`

Import module: `h2physics.adapters.flash_front`; selected entry: `run_material_front`.

#### `h2physics.adapters.flash_front.run_material_front`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/flash_front.py#L414)

Lumped cell ignition along face-connected material-coordinate paths.

Each edge traverses half a cell at each cell's native unburned flame speed.
Six-neighbor paths retain lattice directional bias; no claim of continuum
eikonal convergence, obstacle flow, expansion-induced advection or lab-frame
receptor position is made. A missing cell is an absent path, not a CFD wall.

```python
run_material_front(cells: Iterable[FrontCell], *, spacing_m: tuple[float, float, float], ignition_cell_ids: Iterable[str], ignition_s: float, horizon_s: float, clock_projection_tolerance_s: float, contacts: Iterable[MaterialContact]=()) -> FlashFrontTrace
```

### Returned value / 반환값

`FlashFrontTrace`

### Related input/return records / 관련 입력·반환 객체

#### `h2physics.adapters.flash_front.FrontCell`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/flash_front.py#L307)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `identifier` | `str` | `required` |
| `lattice_index` | `tuple` | `required` |
| `reference` | `NativePremixedReference` | `required` |

#### `h2physics.adapters.flash_front.MaterialContact`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/flash_front.py#L340)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `receptor_id` | `str` | `required` |
| `cell_id` | `str` | `required` |
| `occupancy_start_s` | `float` | `required` |
| `occupancy_end_s` | `float` | `required` |
| `evidence_id` | `str` | `required` |

#### `h2physics.adapters.flash_front.FlashFrontTrace`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/flash_front.py#L363)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `cells` | `tuple` | `required` |
| `spacing_m` | `tuple` | `required` |
| `ignition_cell_ids` | `tuple` | `required` |
| `ignition_s` | `float` | `required` |
| `horizon_s` | `float` | `required` |
| `clock_projection_tolerance_s` | `float` | `required` |
| `arrival_s` | `object` | `required` |
| `native_sparse_graph` | `object` | `required` |
| `native_travel_times_s` | `np.ndarray` | `required` |
| `native_predecessors` | `np.ndarray` | `required` |
| `native_sources` | `np.ndarray` | `required` |
| `burned_cells` | `tuple` | `required` |
| `contacts` | `tuple` | `required` |
| `initial_cloud_mass_kg` | `float` | `required` |
| `burned_mixture_mass_kg` | `float` | `required` |
| `unburned_mixture_mass_kg` | `float` | `required` |
| `mass_residual_kg` | `float` | `required` |
| `total_energy_residual_j` | `float` | `required` |
| `laboratory_flame_prediction` | `bool` | `False` |
| `radiation_or_injury_prediction` | `bool` | `False` |

#### `h2physics.adapters.flash_front.NativePremixedReference`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/flash_front.py#L147)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `identifier` | `str` | `required` |
| `gas_owner` | `CanteraGas` | `required` |
| `flame_result` | `FreeFlameResult` | `required` |
| `admission` | `FrontAdmission` | `required` |
| `initial` | `ReactiveState` | `required` |
| `hp_result` | `EquilibriumResult` | `required` |
| `unburned_phase` | `object` | `required` |
| `burned_phase` | `object` | `required` |
| `speed_m_s` | `float` | `required` |
| `thermal_band_residence_s` | `float` | `required` |
| `thermal_progress_time_s` | `np.ndarray` | `required` |
| `thermal_progress_temperature_k` | `np.ndarray` | `required` |
| `flame_sha256` | `str` | `required` |
| `unburned_sha256` | `str` | `required` |
| `burned_sha256` | `str` | `required` |
| `flame_source_binding` | `NativePhaseBinding` | `required` |
| `unburned_binding` | `NativePhaseBinding` | `required` |
| `burned_binding` | `NativePhaseBinding` | `required` |


<a id="module-h2physics-combustion-closed_charge_engine-run_closed_charge_engine_segment"></a>

## 피스톤 체적·일을 포함한 밀폐 충전 엔진 구간 / Native closed-charge engine interval with piston work

Family / navigation ID: `combustion.piston_engine`

Import module: `h2physics.combustion.closed_charge_engine`; selected entry: `run_closed_charge_engine_segment`.

#### `h2physics.combustion.closed_charge_engine.run_closed_charge_engine_segment`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/combustion/closed_charge_engine.py#L385)

Integrate a premixed H2 charge through a caller-selected crank interval.

``phase_factory`` returns a fresh Cantera ideal-gas ``Solution``. ``initial``
supplies the uniform chamber mixture at ``crank_start_rad``. The interval is
strictly shorter than one four-stroke cycle; its endpoints are not interpreted
as valve events. A static ambient reservoir on the other side of a native Wall
supplies the reference pressure for piston work. No mass crosses the chamber
boundary. An optional ``piston_heat_flux_schedule`` imposes a caller-specified
W/m2 heat flux through the piston face, positive into the cylinder. Cantera
applies it on the same native Wall as the prescribed motion; no heat-transfer
correlation is inferred. Hydrogen and oxygen must both exist in the phase and have
positive initial mole fractions. Finite-rate reaction is delegated to the
native phase mechanism; no spark or ignition delay is prescribed.

``indicated_boundary_work_j`` is positive for work delivered by the gas and is
estimated from the returned samples. The optional piston-face flux is signed
positive into the gas and integrated over the geometry-derived face area. The
first-law residual is a sampled diagnostic, not a native accepted-step
conservation certificate.

```python
run_closed_charge_engine_segment(phase_factory, mechanism_basis: MechanismBasis, initial: ReactiveState, geometry: SliderCrank, *, crank_start_rad: float, crank_end_rad: float, piston_heat_flux_schedule: EngineBoundarySchedule | None=None, samples_per_revolution: int=720, relative_tolerance: float=1e-09, absolute_tolerance: float=1e-13) -> ClosedChargeEngineTrace
```

### Returned value / 반환값

`ClosedChargeEngineTrace`

### Related input/return records / 관련 입력·반환 객체

#### `h2physics.adapters.cantera.MechanismBasis`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/cantera.py#L22)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `identifier` | `str` | `required` |
| `source_sha256` | `str` | `required` |
| `license_id` | `str` | `required` |
| `references` | `tuple[str, ...]` | `required` |
| `minimum_temperature_k` | `float` | `required` |
| `maximum_temperature_k` | `float` | `required` |
| `minimum_pressure_pa` | `float` | `required` |
| `maximum_pressure_pa` | `float` | `required` |

#### `h2physics.adapters.cantera.ReactiveState`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/cantera.py#L51)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `temperature_k` | `float` | `required` |
| `pressure_pa` | `float` | `required` |
| `mole_fractions` | `Mapping[str, float]` | `required` |

#### `h2physics.combustion.closed_charge_engine.SliderCrank`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/combustion/closed_charge_engine.py#L138)

Single-cylinder geometry and constant-speed crank timing in SI units.

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `bore_m` | `float` | `required` |
| `stroke_m` | `float` | `required` |
| `connecting_rod_m` | `float` | `required` |
| `compression_ratio` | `float` | `required` |
| `speed_rpm` | `float` | `required` |

Computed properties: `piston_area_m2`, `clearance_volume_m3`.

#### `h2physics.combustion.closed_charge_engine.EngineBoundarySchedule`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/combustion/closed_charge_engine.py#L71)

Source-bound scalar input history on an explicit absolute clock.

This is schedule bookkeeping only: it does not define a valve, injector,
spark, heat-transfer, or flow law. Values are interpolated linearly at
requested absolute clock times, with extrapolation rejected.

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `quantity` | `str` | `required` |
| `units` | `str` | `required` |
| `source_id` | `str` | `required` |
| `clock_origin_s` | `float` | `required` |
| `time_s` | `np.ndarray` | `required` |
| `values` | `np.ndarray` | `required` |

Computed properties: `support_s`.

#### `h2physics.combustion.closed_charge_engine.ClosedChargeEngineTrace`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/combustion/closed_charge_engine.py#L216)

Native-state history and sampled first-law diagnostics for one interval.

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `crank_angle_rad` | `np.ndarray` | `required` |
| `time_s` | `np.ndarray` | `required` |
| `volume_m3` | `np.ndarray` | `required` |
| `pressure_pa` | `np.ndarray` | `required` |
| `temperature_k` | `np.ndarray` | `required` |
| `mass_kg` | `np.ndarray` | `required` |
| `internal_energy_j` | `np.ndarray` | `required` |
| `species_names` | `tuple[str, ...]` | `required` |
| `mass_fractions` | `np.ndarray` | `required` |
| `indicated_boundary_work_j` | `float` | `required` |
| `first_law_residual_j` | `float` | `required` |
| `native_reactor` | `object` | `required` |
| `native_network` | `object` | `required` |
| `native_piston_wall` | `object` | `field(default=None, repr=False, compare=False)` |
| `piston_heat_flux_schedule` | `EngineBoundarySchedule &#124; None` | `None` |
| `piston_heat_area_m2` | `float &#124; None` | `None` |
| `piston_heat_input_j` | `np.ndarray &#124; None` | `None` |


<a id="module-h2physics-combustion-open_cylinder_engine-run_open_cylinder_segment"></a>

## 밸브·유입출 경계를 명시한 개방 실린더 구간 / Native open-cylinder interval with declared valves and ports

Family / navigation ID: `combustion.piston_engine`

Import module: `h2physics.combustion.open_cylinder_engine`; selected entry: `run_open_cylinder_segment`.

#### `h2physics.combustion.open_cylinder_engine.run_open_cylinder_segment`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/combustion/open_cylinder_engine.py#L543)

Run a moving-volume cylinder segment with prescribed, valve or nozzle feeds.

Each inlet composition, temperature and pressure are fixed over the run.
Multiple feeds permit independently scheduled species or carrier streams;
the resulting species feed rates are the sum of each reservoir's mass rate
times its native composition. Prescribed outlets remove the current mixture
at their declared rate; pressure-valved ports use Cantera's one-way linear
law ``mdot = K * opening(t) * max(P_up-P_down, 0)``. Valve coefficients and
opening histories are caller-owned and evidence-tagged; the native law does
not represent measured valve-seat flow. Optional shared-nozzle inlets use
``HomogeneousIsentropicNozzle`` with live cylinder pressure as backpressure;
Cantera's ``MassFlowController`` only adapts its resulting nonnegative rate.
No spark is included. With ``wall_thermal`` supplied, one finite wall
temperature is coupled to the same native network through caller-owned UA
and heat inputs.

Returned source/energy residuals are sampled trapezoidal diagnostics over
exact requested clock points, including all input schedule knots. They do
not replace Cantera's accepted-step energy equations or certify a complete
cycle. Any failure raises ``OpenCylinderEngineError`` with native owners and
the last accepted requested-sample prefix.

```python
run_open_cylinder_segment(phase_factory, mechanism_basis: MechanismBasis, initial: ReactiveState, geometry: SliderCrank, boundary: OpenCylinderBoundary, *, absolute_clock_origin_s: float, crank_start_rad: float, crank_end_rad: float, samples_per_revolution: int=720, relative_tolerance: float=1e-09, absolute_tolerance: float=1e-13, wall_thermal: CylinderWallThermal | None=None) -> OpenCylinderEngineTrace
```

### Returned value / 반환값

`OpenCylinderEngineTrace`

### Related input/return records / 관련 입력·반환 객체

#### `h2physics.adapters.cantera.MechanismBasis`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/cantera.py#L22)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `identifier` | `str` | `required` |
| `source_sha256` | `str` | `required` |
| `license_id` | `str` | `required` |
| `references` | `tuple[str, ...]` | `required` |
| `minimum_temperature_k` | `float` | `required` |
| `maximum_temperature_k` | `float` | `required` |
| `minimum_pressure_pa` | `float` | `required` |
| `maximum_pressure_pa` | `float` | `required` |

#### `h2physics.adapters.cantera.ReactiveState`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/cantera.py#L51)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `temperature_k` | `float` | `required` |
| `pressure_pa` | `float` | `required` |
| `mole_fractions` | `Mapping[str, float]` | `required` |

#### `h2physics.combustion.closed_charge_engine.SliderCrank`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/combustion/closed_charge_engine.py#L138)

Single-cylinder geometry and constant-speed crank timing in SI units.

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `bore_m` | `float` | `required` |
| `stroke_m` | `float` | `required` |
| `connecting_rod_m` | `float` | `required` |
| `compression_ratio` | `float` | `required` |
| `speed_rpm` | `float` | `required` |

Computed properties: `piston_area_m2`, `clearance_volume_m3`.

#### `h2physics.combustion.open_cylinder_engine.OpenCylinderBoundary`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/combustion/open_cylinder_engine.py#L227)

Collection of fixed-state inlet feeds and bulk-mixture outlet schedules.

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `inlets` | `tuple[OpenCylinderInlet, ...]` | `required` |
| `outlets` | `tuple[OpenCylinderOutlet, ...]` | `required` |
| `valve_inlets` | `tuple[OpenCylinderValveInlet, ...]` | `()` |
| `valve_outlets` | `tuple[OpenCylinderValveOutlet, ...]` | `()` |
| `nozzle_inlets` | `tuple[OpenCylinderNozzleInlet, ...]` | `()` |

#### `h2physics.combustion.engine_wall.CylinderWallThermal`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/combustion/engine_wall.py#L83)

One finite wall node and evidence-bound boundary heat callback.

``external_heat_into_wall`` returns signed watts entering the wall from
every non-cylinder boundary (for example, a coolant stream). The gas-wall
transfer is ``UA * (Tgas - Twall)`` and is counted with opposite signs in
the gas and wall energy equations.

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `heat_capacity_j_k` | `float` | `required` |
| `reference_temperature_k` | `float` | `required` |
| `initial_temperature_k` | `float` | `required` |
| `conductance_ua_w_k` | `float` | `required` |
| `energy_reference_id` | `str` | `required` |
| `property_evidence_id` | `str` | `required` |
| `boundary_evidence_id` | `str` | `required` |
| `external_heat_into_wall` | `Callable[[float, float, float], float] &#124; None` | `field(default=None, repr=False, compare=False)` |

#### `h2physics.combustion.open_cylinder_engine.OpenCylinderEngineTrace`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/combustion/open_cylinder_engine.py#L328)

Native Cantera output samples and sampled boundary/conservation ledgers.

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `crank_angle_rad` | `np.ndarray` | `required` |
| `time_s` | `np.ndarray` | `required` |
| `volume_m3` | `np.ndarray` | `required` |
| `pressure_pa` | `np.ndarray` | `required` |
| `temperature_k` | `np.ndarray` | `required` |
| `mass_kg` | `np.ndarray` | `required` |
| `internal_energy_j` | `np.ndarray` | `required` |
| `species_names` | `tuple[str, ...]` | `required` |
| `mass_fractions` | `np.ndarray` | `required` |
| `species_transfer_kg` | `np.ndarray` | `required` |
| `inlet_enthalpy_transfer_j` | `np.ndarray` | `required` |
| `outlet_enthalpy_transfer_j` | `np.ndarray` | `required` |
| `pressure_volume_work_j` | `np.ndarray` | `required` |
| `mass_balance_residual_kg` | `np.ndarray` | `required` |
| `sampled_first_law_residual_j` | `np.ndarray` | `required` |
| `mechanism_basis` | `MechanismBasis` | `required` |
| `geometry` | `SliderCrank` | `required` |
| `boundary` | `OpenCylinderBoundary` | `required` |
| `absolute_clock_origin_s` | `float` | `required` |
| `native_reactor` | `object` | `field(repr=False, compare=False)` |
| `native_network` | `object` | `field(repr=False, compare=False)` |
| `native_wall` | `object` | `field(repr=False, compare=False)` |
| `native_flow_devices` | `tuple` | `field(repr=False, compare=False)` |
| `native_reservoirs` | `tuple` | `field(repr=False, compare=False)` |
| `wall_thermal` | `CylinderWallThermal &#124; None` | `field(default=None, repr=False, compare=False)` |
| `wall_temperature_k` | `np.ndarray &#124; None` | `None` |
| `wall_internal_energy_j` | `np.ndarray &#124; None` | `None` |
| `gas_wall_heat_into_gas_j` | `np.ndarray &#124; None` | `None` |
| `wall_boundary_heat_j` | `np.ndarray &#124; None` | `None` |
| `nozzle_results` | `tuple[tuple[NozzleResult, ...], ...]` | `field(default=(), repr=False)` |

#### `h2physics.combustion.open_cylinder_engine.OpenCylinderInlet`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/combustion/open_cylinder_engine.py#L55)

One fixed, source-bound feed state with a scheduled nonnegative rate.

``state`` supplies the fixed reservoir composition, temperature and pressure.
The retained enthalpy reference identifies the caller's interpretation of
mechanism-relative enthalpy; it is not a license or thermodynamic conversion.

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `identifier` | `str` | `required` |
| `state` | `ReactiveState` | `required` |
| `mass_flow` | `EngineBoundarySchedule` | `required` |
| `source_reference` | `str` | `required` |
| `enthalpy_reference` | `str` | `required` |

#### `h2physics.combustion.open_cylinder_engine.OpenCylinderOutlet`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/combustion/open_cylinder_engine.py#L148)

One prescribed extraction of the current, well-mixed cylinder gas.

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `identifier` | `str` | `required` |
| `mass_flow` | `EngineBoundarySchedule` | `required` |
| `source_reference` | `str` | `required` |

#### `h2physics.combustion.open_cylinder_engine.OpenCylinderValveInlet`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/combustion/open_cylinder_engine.py#L168)

Pressure-driven inlet through Cantera Valve with caller-specified opening.

Cantera's native linear valve law is mdot = K * opening(t) * max(dP, 0).
The coefficient is source-bound and expressed in kg/s/Pa; this API does not
infer a discharge coefficient, area, compressible-flow law, or valve timing.

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `identifier` | `str` | `required` |
| `state` | `ReactiveState` | `required` |
| `opening` | `EngineBoundarySchedule` | `required` |
| `coefficient_kg_s_pa` | `float` | `required` |
| `coefficient_reference` | `str` | `required` |
| `source_reference` | `str` | `required` |
| `enthalpy_reference` | `str` | `required` |

#### `h2physics.combustion.open_cylinder_engine.OpenCylinderValveOutlet`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/combustion/open_cylinder_engine.py#L201)

Pressure-driven exhaust from the well-mixed cylinder through Cantera Valve.

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `identifier` | `str` | `required` |
| `opening` | `EngineBoundarySchedule` | `required` |
| `coefficient_kg_s_pa` | `float` | `required` |
| `coefficient_reference` | `str` | `required` |
| `source_reference` | `str` | `required` |

#### `h2physics.combustion.open_cylinder_engine.OpenCylinderNozzleInlet`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/combustion/open_cylinder_engine.py#L109)

Pressure-driven source feed evaluated by the shared isentropic nozzle.

The source is a fixed native gas reservoir. Its outlet mass flow is obtained
from the shared phase-aware nozzle at the live Cantera cylinder backpressure;
the source rate is then supplied through a native MassFlowController. The
property provider must share the source/cylinder native phase definition.

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `identifier` | `str` | `required` |
| `state` | `ReactiveState` | `required` |
| `nozzle` | `HomogeneousIsentropicNozzle` | `required` |
| `opening` | `NozzleOpening` | `required` |
| `opening_schedule` | `EngineBoundarySchedule` | `required` |
| `source_reference` | `str` | `required` |
| `enthalpy_reference` | `str` | `required` |

#### `h2physics.release.NozzleResult`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/release.py#L90)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `opening` | `NozzleOpening` | `required` |
| `upstream_stagnation` | `ThermoState` | `required` |
| `back_pressure_pa` | `float` | `required` |
| `effective_area_m2` | `float` | `required` |
| `exit_state` | `ThermoState &#124; None` | `required` |
| `velocity_m_s` | `float` | `required` |
| `mass_flux_kg_m2_s` | `float` | `required` |
| `mass_flow_kg_s` | `float` | `required` |
| `regime` | `Literal['choked', 'back_pressure_limited', 'closed', 'no_forward_pressure']` | `required` |
| `diagnostics` | `NozzleDiagnostics` | `required` |
| `model_id` | `str` | `'homogeneous-equilibrium-isentropic-effective-area-v1'` |

Computed properties: `withdrawal_energy_w`, `kinetic_power_w`, `static_enthalpy_flow_w`, `energy_residual_w`, `effective_area_thrust_n`.


<a id="module-h2physics-combustion-open_brayton-run_open_cycle_brayton"></a>

## 외부 반응 평형을 이용한 수소 Brayton 기준 사이클 / Native-equilibrium hydrogen Brayton reference

Family / navigation ID: `combustion.gas_turbine`

Import module: `h2physics.combustion.open_brayton`; selected entry: `run_open_cycle_brayton`.

#### `h2physics.combustion.open_brayton.run_open_cycle_brayton`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/combustion/open_brayton.py#L511)

Evaluate a single-point H2 open Brayton reference with native Cantera.

Compressor and turbine deviations are represented solely by caller-provided
isentropic efficiencies; the combustor is adiabatic, constant-pressure and
HP-equilibrium. Turbine expansion freezes the combustor outlet composition.
This algebra includes neither component maps nor auxiliary hardware.

```python
run_open_cycle_brayton(phase, inputs: OpenBraytonInputs) -> OpenBraytonRun
```

### Returned value / 반환값

`OpenBraytonRun`

### Related input/return records / 관련 입력·반환 객체

#### `h2physics.combustion.open_brayton.OpenBraytonInputs`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/combustion/open_brayton.py#L58)

Explicit one-point boundary and caller-supplied machine performance inputs.

The reference is per kilogram of compressor-inlet air. Fuel compression,
generator conversion, mechanical loss, cooling flow, pressure-side bleed,
external heat loss and accessory loads are outside the boundary.

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `mechanism_id` | `str` | `required` |
| `process_window_id` | `str` | `required` |
| `air_temperature_k` | `float` | `required` |
| `air_pressure_pa` | `float` | `required` |
| `air_mole_fractions` | `tuple` | `required` |
| `compressor_pressure_ratio` | `float` | `required` |
| `compressor_isentropic_efficiency` | `float` | `required` |
| `combustor_pressure_recovery` | `float` | `required` |
| `hydrogen_fuel_to_air_mass_ratio` | `float` | `required` |
| `hydrogen_inlet_temperature_k` | `float` | `required` |
| `turbine_exhaust_pressure_pa` | `float` | `required` |
| `turbine_isentropic_efficiency` | `float` | `required` |
| `hydrogen_lhv_j_kg` | `float` | `required` |
| `air_state_evidence_id` | `str` | `required` |
| `hydrogen_feed_evidence_id` | `str` | `required` |
| `machine_parameter_evidence_id` | `str` | `required` |
| `lhv_evidence_id` | `str` | `required` |

#### `h2physics.combustion.open_brayton.OpenBraytonRun`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/combustion/open_brayton.py#L207)

Reference cycle result; powers are ideal single-shaft terms before losses.

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `inputs` | `OpenBraytonInputs` | `required` |
| `states` | `tuple[BraytonGasState, ...]` | `required` |
| `elemental_mass_residuals` | `tuple[tuple[str, float], ...]` | `required` |
| `compressor_work_j_kg_air` | `float` | `required` |
| `turbine_work_j_kg_air` | `float` | `required` |
| `net_work_j_kg_air` | `float` | `required` |
| `hydrogen_heat_input_j_kg_air` | `float` | `required` |
| `thermal_efficiency` | `float` | `required` |
| `combustor_enthalpy_residual_j_kg_air` | `float` | `required` |
| `open_cycle_energy_residual_j_kg_air` | `float` | `required` |
| `native_phase` | `object` | `required` |

#### `h2physics.combustion.open_brayton.BraytonGasState`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/combustion/open_brayton.py#L137)

Immutable scalar/native-composition snapshot of one reference-cycle station.

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `station` | `str` | `required` |
| `temperature_k` | `float` | `required` |
| `pressure_pa` | `float` | `required` |
| `enthalpy_j_kg` | `float` | `required` |
| `entropy_j_kg_k` | `float` | `required` |
| `species_names` | `tuple[str, ...]` | `required` |
| `mass_fractions` | `tuple[float, ...]` | `required` |
| `elemental_mass_fractions` | `tuple[tuple[str, float], ...]` | `required` |
| `mechanism_id` | `str` | `required` |
| `process_window_id` | `str` | `required` |


<a id="module-h2physics-combustion-steady_map_solver-solve_steady_map_operating_point"></a>

## 기기 맵·유량·축 동력 잔차를 맞추는 운전점 해석 / Bounded component-map operating-point solve

Family / navigation ID: `combustion.gas_turbine`

Import module: `h2physics.combustion.steady_map_solver`; selected entry: `solve_steady_map_operating_point`.

#### `h2physics.combustion.steady_map_solver.solve_steady_map_operating_point`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/combustion/steady_map_solver.py#L386)

Solve map-flow and shaft residuals with bounded multi-start least squares.

The unknown vector contains exactly compressor corrected speed, compressor
pressure ratio and inlet-air mass flow. Three residuals are solved: compressor
corrected flow, turbine corrected flow, and net shaft power minus explicit
loss and target. Turbine corrected speed and both corrected-flow conversions
are never inferred; caller callbacks and evidence IDs supply them.

Each trial delegates all cycle thermodynamics and HP equilibrium to the
existing Cantera Brayton runner. Map interpolation rejects extrapolation.
Only roots meeting every physical tolerance are returned as candidates.
Multiple distinct roots produce status ``multiple``; no nearest-root choice
is made on behalf of the caller.

```python
solve_steady_map_operating_point(phase_factory, inputs: SteadyMapSolveInputs) -> SteadyMapSolveResult
```

### Returned value / 반환값

`SteadyMapSolveResult`

### Related input/return records / 관련 입력·반환 객체

#### `h2physics.combustion.steady_map_solver.SteadyMapSolveInputs`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/combustion/steady_map_solver.py#L76)

Bounds, evidence and residual closures for one steady map-matched solve.

The exact solve vector is ``(compressor corrected speed, compressor pressure
ratio, inlet-air mass flow)``. Turbine corrected speed is not independently
optimized: ``speed_link`` maps compressor corrected speed to it. Both flow
converters return corrected mass flow in kg/s for comparison with their
respective admitted maps. They receive the actual flow, the existing native
cycle result, and the selected interpolated map point.

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `cycle_inputs` | `OpenBraytonInputs` | `required` |
| `compressor_map` | `CompressorComponentMap` | `required` |
| `turbine_map` | `TurbineComponentMap` | `required` |
| `compressor_speed_bounds` | `tuple[float, float]` | `required` |
| `compressor_pressure_ratio_bounds` | `tuple[float, float]` | `required` |
| `air_mass_flow_bounds_kg_s` | `tuple[float, float]` | `required` |
| `seeds` | `tuple[MapOperatingSeed, ...]` | `required` |
| `speed_link` | `Callable[[float], float]` | `field(repr=False, compare=False)` |
| `compressor_corrected_flow` | `Callable[[float, OpenBraytonRun, CompressorMapPoint], float]` | `field(repr=False, compare=False)` |
| `turbine_corrected_flow` | `Callable[[float, OpenBraytonRun, TurbineMapPoint], float]` | `field(repr=False, compare=False)` |
| `speed_link_evidence_id` | `str` | `required` |
| `compressor_flow_evidence_id` | `str` | `required` |
| `turbine_flow_evidence_id` | `str` | `required` |
| `shaft_loss_evidence_id` | `str` | `required` |
| `shaft_target_evidence_id` | `str` | `required` |
| `shaft_mechanical_loss_w` | `float` | `required` |
| `shaft_residual_target_w` | `float` | `required` |
| `flow_relative_tolerance` | `float` | `0.001` |
| `flow_absolute_tolerance_kg_s` | `float` | `1e-06` |
| `shaft_absolute_tolerance_w` | `float` | `0.01` |
| `root_merge_tolerance` | `float` | `1e-05` |
| `max_nfev` | `int` | `120` |

Computed properties: `unknowns`.

#### `h2physics.combustion.steady_map_solver.SteadyMapSolveResult`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/combustion/steady_map_solver.py#L287)

All distinct roots and seed attempts; ambiguity is never silently hidden.

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `inputs` | `SteadyMapSolveInputs` | `required` |
| `status` | `str` | `required` |
| `candidates` | `tuple[SteadyMapOperatingPoint, ...]` | `required` |
| `attempts` | `tuple[SteadyMapSeedAttempt, ...]` | `required` |

Computed properties: `unique_candidate`.

#### `h2physics.combustion.open_brayton.OpenBraytonInputs`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/combustion/open_brayton.py#L58)

Explicit one-point boundary and caller-supplied machine performance inputs.

The reference is per kilogram of compressor-inlet air. Fuel compression,
generator conversion, mechanical loss, cooling flow, pressure-side bleed,
external heat loss and accessory loads are outside the boundary.

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `mechanism_id` | `str` | `required` |
| `process_window_id` | `str` | `required` |
| `air_temperature_k` | `float` | `required` |
| `air_pressure_pa` | `float` | `required` |
| `air_mole_fractions` | `tuple` | `required` |
| `compressor_pressure_ratio` | `float` | `required` |
| `compressor_isentropic_efficiency` | `float` | `required` |
| `combustor_pressure_recovery` | `float` | `required` |
| `hydrogen_fuel_to_air_mass_ratio` | `float` | `required` |
| `hydrogen_inlet_temperature_k` | `float` | `required` |
| `turbine_exhaust_pressure_pa` | `float` | `required` |
| `turbine_isentropic_efficiency` | `float` | `required` |
| `hydrogen_lhv_j_kg` | `float` | `required` |
| `air_state_evidence_id` | `str` | `required` |
| `hydrogen_feed_evidence_id` | `str` | `required` |
| `machine_parameter_evidence_id` | `str` | `required` |
| `lhv_evidence_id` | `str` | `required` |

#### `h2physics.combustion.compressor_map.CompressorComponentMap`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/combustion/compressor_map.py#L69)

Rectangular corrected-flow/efficiency observations for a gas compressor.

Rows index corrected speed and columns index outlet-over-inlet total
pressure ratio. No correction reference is inferred from these values.

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `map_id` | `str` | `required` |
| `evidence_id` | `str` | `required` |
| `source_uri` | `str` | `required` |
| `license_id` | `str` | `required` |
| `source_sha256` | `str` | `required` |
| `speed_unit` | `str` | `required` |
| `pressure_ratio_convention` | `str` | `required` |
| `corrected_mass_flow_basis` | `str` | `required` |
| `corrected_speed` | `tuple[float, ...]` | `required` |
| `compression_pressure_ratio` | `tuple[float, ...]` | `required` |
| `corrected_mass_flow_kg_s` | `tuple[tuple[float, ...], ...]` | `required` |
| `isentropic_efficiency` | `tuple[tuple[float, ...], ...]` | `required` |

#### `h2physics.combustion.turbine_map.TurbineComponentMap`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/combustion/turbine_map.py#L58)

Caller-provided corrected-flow and efficiency map on a rectangular grid.

Rows index ``corrected_speed`` and columns index ``expansion_pressure_ratio``.
The pressure-ratio convention, correction basis, units, and evidence identity
are mandatory metadata; this type assigns no universal map convention.

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `map_id` | `str` | `required` |
| `evidence_id` | `str` | `required` |
| `source_uri` | `str` | `required` |
| `license_id` | `str` | `required` |
| `source_sha256` | `str` | `required` |
| `speed_unit` | `str` | `required` |
| `pressure_ratio_convention` | `str` | `required` |
| `corrected_mass_flow_basis` | `str` | `required` |
| `corrected_speed` | `tuple[float, ...]` | `required` |
| `expansion_pressure_ratio` | `tuple[float, ...]` | `required` |
| `corrected_mass_flow_kg_s` | `tuple[tuple[float, ...], ...]` | `required` |
| `isentropic_efficiency` | `tuple[tuple[float, ...], ...]` | `required` |

#### `h2physics.combustion.steady_map_solver.MapOperatingSeed`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/combustion/steady_map_solver.py#L52)

One initial guess for the three supported caller-selected unknowns.

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `compressor_corrected_speed` | `float` | `required` |
| `compressor_pressure_ratio` | `float` | `required` |
| `air_mass_flow_kg_s` | `float` | `required` |

#### `h2physics.combustion.compressor_map.CompressorMapPoint`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/combustion/compressor_map.py#L136)

Bounded bilinear map output retaining its source grid.

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `component_map` | `CompressorComponentMap` | `required` |
| `corrected_speed` | `float` | `required` |
| `compression_pressure_ratio` | `float` | `required` |
| `corrected_mass_flow_kg_s` | `float` | `required` |
| `isentropic_efficiency` | `float` | `required` |

#### `h2physics.combustion.open_brayton.OpenBraytonRun`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/combustion/open_brayton.py#L207)

Reference cycle result; powers are ideal single-shaft terms before losses.

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `inputs` | `OpenBraytonInputs` | `required` |
| `states` | `tuple[BraytonGasState, ...]` | `required` |
| `elemental_mass_residuals` | `tuple[tuple[str, float], ...]` | `required` |
| `compressor_work_j_kg_air` | `float` | `required` |
| `turbine_work_j_kg_air` | `float` | `required` |
| `net_work_j_kg_air` | `float` | `required` |
| `hydrogen_heat_input_j_kg_air` | `float` | `required` |
| `thermal_efficiency` | `float` | `required` |
| `combustor_enthalpy_residual_j_kg_air` | `float` | `required` |
| `open_cycle_energy_residual_j_kg_air` | `float` | `required` |
| `native_phase` | `object` | `required` |

#### `h2physics.combustion.turbine_map.TurbineMapPoint`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/combustion/turbine_map.py#L130)

Interpolated map point retaining and rechecking its complete map source.

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `component_map` | `TurbineComponentMap` | `required` |
| `corrected_speed` | `float` | `required` |
| `expansion_pressure_ratio` | `float` | `required` |
| `corrected_mass_flow_kg_s` | `float` | `required` |
| `isentropic_efficiency` | `float` | `required` |

#### `h2physics.combustion.steady_map_solver.SteadyMapOperatingPoint`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/combustion/steady_map_solver.py#L209)

One converged map/cycle/shaft root with retained original native run.

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `inputs` | `SteadyMapSolveInputs` | `required` |
| `compressor_corrected_speed` | `float` | `required` |
| `compressor_pressure_ratio` | `float` | `required` |
| `air_mass_flow_kg_s` | `float` | `required` |
| `turbine_corrected_speed` | `float` | `required` |
| `cycle_run` | `MapMatchedBraytonRun` | `required` |
| `compressor_flow_residual_kg_s` | `float` | `required` |
| `turbine_flow_residual_kg_s` | `float` | `required` |
| `shaft_residual_w` | `float` | `required` |
| `optimizer_nfev` | `int` | `required` |

#### `h2physics.combustion.steady_map_solver.SteadyMapSeedAttempt`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/combustion/steady_map_solver.py#L274)

Convergence record for one initial seed, including nonaccepted attempts.

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `seed` | `MapOperatingSeed` | `required` |
| `converged` | `bool` | `required` |
| `final_vector` | `tuple[float, float, float] &#124; None` | `required` |
| `scaled_residuals` | `tuple[float, float, float] &#124; None` | `required` |
| `nfev` | `int` | `required` |
| `message` | `str` | `required` |
| `failure` | `str &#124; None` | `None` |


<a id="module-h2physics-combustion-shaft_transient-integrate_shaft_transient"></a>

## 지정 터빈·압축기 동력에 따른 단축 회전 에너지 응답 / One-shaft energy dynamics with supplied turbine/compressor powers

Family / navigation ID: `combustion.gas_turbine`

Import module: `h2physics.combustion.shaft_transient`; selected entry: `integrate_shaft_transient`.

#### `h2physics.combustion.shaft_transient.integrate_shaft_transient`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/combustion/shaft_transient.py#L223)

Integrate a single-spool rotor using explicit boundary power/torque inputs.

The state is rotational kinetic energy, which avoids division by angular
velocity at the stalled condition. Input histories are linearly interpolated;
energy terms enter the same ODE as additional integral states. Solver failure
returns its accepted dense-output prefix with an explicit ``solver_failed``
status. Speed limits terminate at the event and are never clipped. Optional
mapped gas-path feedback replaces the two scheduled power channels at every
ODE trial using that trial's physical speed. Their schedules must then be zero;
load torque and rotor losses retain their original meanings.

```python
integrate_shaft_transient(inputs: ShaftTransientInputs, *, gas_path_feedback: MapMatchedBraytonShaftFeedback | None=None) -> ShaftTransientTrace
```

### Returned value / 반환값

`ShaftTransientTrace`

### Related input/return records / 관련 입력·반환 객체

#### `h2physics.combustion.shaft_transient.ShaftTransientInputs`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/combustion/shaft_transient.py#L53)

Caller-owned powers and load torque over one finite rotor window.

Power histories use piecewise-linear interpolation between strictly
increasing absolute times. Positive turbine power drives the shaft;
compressor power, load torque and loss parameters oppose it. Load torque
may be signed to represent motoring. ``output_time_s`` is a reporting grid;
the ODE solver controls its own internal steps and terminates at speed
bounds rather than clipping the rotor state.

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `time_s` | `np.ndarray` | `required` |
| `turbine_power_w` | `np.ndarray` | `required` |
| `compressor_power_w` | `np.ndarray` | `required` |
| `load_torque_nm` | `np.ndarray` | `required` |
| `output_time_s` | `np.ndarray` | `required` |
| `rotor_inertia_kg_m2` | `float` | `required` |
| `initial_speed_rad_s` | `float` | `required` |
| `minimum_speed_rad_s` | `float` | `required` |
| `maximum_speed_rad_s` | `float` | `required` |
| `coulomb_loss_torque_nm` | `float` | `required` |
| `viscous_loss_nm_per_rad_s` | `float` | `required` |
| `relative_tolerance` | `float` | `required` |
| `absolute_energy_tolerance_j` | `float` | `required` |
| `maximum_step_s` | `float` | `required` |
| `shaft_id` | `str` | `required` |
| `power_basis_id` | `str` | `required` |
| `load_basis_id` | `str` | `required` |
| `inertia_evidence_id` | `str` | `required` |

#### `h2physics.combustion.shaft_brayton_feedback.MapMatchedBraytonShaftFeedback`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/combustion/shaft_brayton_feedback.py#L66)

Caller-declared speed correction and operating law, native power owner.

``corrected_speeds(time_s, omega_rad_s)`` returns compressor and turbine
corrected speeds in the units of the admitted maps. ``operating_inputs``
receives those two values as its last arguments and returns a complete
MapMatchedBraytonInputs. Actual flow admission and mapped efficiencies are
checked by the existing cycle composition. The operating law must specify
the remaining pressure-ratio, flow and fuel boundaries; it is not inferred
from the shaft energy equation. Factories must return fresh native phases.

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `phase_factory` | `Callable` | `field(repr=False, compare=False)` |
| `corrected_speeds` | `Callable` | `field(repr=False, compare=False)` |
| `operating_inputs` | `Callable` | `field(repr=False, compare=False)` |
| `feedback_id` | `str` | `required` |
| `shaft_id` | `str` | `required` |
| `power_basis_id` | `str` | `required` |
| `speed_mapping_evidence_id` | `str` | `required` |
| `operating_law_evidence_id` | `str` | `required` |
| `maximum_evaluations` | `int` | `10000` |

#### `h2physics.combustion.shaft_transient.ShaftTransientTrace`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/combustion/shaft_transient.py#L131)

Sampled rotor response, cumulative shaft work, and solver/event status.

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `inputs` | `ShaftTransientInputs` | `field(repr=False, compare=False)` |
| `time_s` | `np.ndarray` | `required` |
| `speed_rad_s` | `np.ndarray` | `required` |
| `kinetic_energy_j` | `np.ndarray` | `required` |
| `cumulative_turbine_work_j` | `np.ndarray` | `required` |
| `cumulative_compressor_work_j` | `np.ndarray` | `required` |
| `cumulative_load_work_j` | `np.ndarray` | `required` |
| `cumulative_coulomb_loss_j` | `np.ndarray` | `required` |
| `cumulative_viscous_loss_j` | `np.ndarray` | `required` |
| `energy_residual_j` | `np.ndarray` | `required` |
| `termination` | `str` | `required` |
| `solver_success` | `bool` | `required` |
| `solver_status` | `int` | `required` |
| `solver_message` | `str` | `required` |
| `function_evaluations` | `int` | `required` |
| `gas_path_feedback` | `MapMatchedBraytonShaftFeedback &#124; None` | `field(default=None, repr=False, compare=False)` |
| `gas_path_evaluations` | `tuple[MapMatchedShaftPowerEvaluation, ...]` | `field(default=(), repr=False, compare=False)` |

#### `h2physics.combustion.shaft_brayton_feedback.MapMatchedShaftPowerEvaluation`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/combustion/shaft_brayton_feedback.py#L25)

One actual gas-path evaluation at an ODE trial time and rotor speed.

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `time_s` | `float` | `required` |
| `speed_rad_s` | `float` | `required` |
| `compressor_corrected_speed` | `float` | `required` |
| `turbine_corrected_speed` | `float` | `required` |
| `native_run` | `MapMatchedBraytonRun` | `field(repr=False, compare=False)` |
| `native_phase` | `object` | `field(repr=False, compare=False)` |
| `speed_mapping_evidence_id` | `str` | `required` |

Computed properties: `turbine_power_w`, `compressor_power_w`.


<a id="module-h2physics-adapters-hyram_overpressure-hyrambauwensoverpressure-evaluate"></a>

## 참여 수소 에너지를 입력한 조건부 비구속 최고 과압 / Conditional unconfined peak from supplied participating energy

Family / navigation ID: `combustion.overpressure`

Import module: `h2physics.adapters.hyram_overpressure`; selected entry: `HyRAMBauwensOverpressure.evaluate`.

#### `h2physics.adapters.hyram_overpressure.HyRAMBauwensOverpressure`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/hyram_overpressure.py#L301)

Actual standalone native pressure correlation, without a Jet instance.

E=m_H2*q; R*=R*(Pambient/E)^(1/3); deltaP=Pambient*Pstar.
These are the published dimensional boundary definitions, not another blast
model. E is the participating fuel's combustion energy, with no inferred yield
or ground/reflection multiplier. All correlation values come from HyRAM.

```python
HyRAMBauwensOverpressure(native_bauwens_class, *, domain: BauwensCorrelationDomain, native_source_id: str)
```

#### `h2physics.adapters.hyram_overpressure.HyRAMBauwensOverpressure.evaluate`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/hyram_overpressure.py#L339)

```python
evaluate(self, energy: DetonableHydrogenEnergy, event: OverpressureEvent, environment: OverpressureEnvironment, receptors_m, *, frame_id: str)
```

The source has no explicit return annotation; inspect its return statements and the domain manual. No return type is invented by this generator.

### Returned value / 반환값

`BauwensPeakResult`

This return contract was reviewed from the implementation; it is not an annotation present in the source signature.

### Related input/return records / 관련 입력·반환 객체

#### `h2physics.adapters.hyram_overpressure.BauwensPeakResult`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/hyram_overpressure.py#L160)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `energy` | `DetonableHydrogenEnergy` | `required` |
| `event` | `OverpressureEvent` | `required` |
| `environment` | `OverpressureEnvironment` | `required` |
| `domain` | `BauwensCorrelationDomain` | `required` |
| `receptors_m` | `np.ndarray` | `required` |
| `distance_m` | `np.ndarray` | `required` |
| `scaled_distance` | `np.ndarray` | `required` |
| `scaled_overpressure` | `np.ndarray` | `required` |
| `peak_overpressure_pa` | `np.ndarray` | `required` |
| `ambient_plus_peak_overpressure_pa` | `np.ndarray` | `required` |
| `native_class` | `Any` | `required` |
| `native_function` | `Any` | `required` |
| `native_scaled_result` | `Any` | `required` |
| `native_source_id` | `str` | `required` |
| `zero_energy_limit` | `bool` | `required` |

#### `h2physics.adapters.hyram_overpressure.BauwensCorrelationDomain`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/hyram_overpressure.py#L127)

Caller-declared application envelope, not a measured validation certificate.

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `minimum_scaled_distance` | `float` | `required` |
| `maximum_scaled_distance` | `float` | `required` |
| `minimum_ambient_pressure_pa` | `float` | `required` |
| `maximum_ambient_pressure_pa` | `float` | `required` |
| `minimum_standoff_m` | `float` | `required` |
| `evidence_id` | `str` | `required` |

#### `h2physics.adapters.hyram_overpressure.DetonableHydrogenEnergy`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/hyram_overpressure.py#L69)

Supplied participating H2 mass, not released/flammable-cloud mass inferred here.

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `participating_hydrogen_mass_kg` | `float` | `required` |
| `heat_of_combustion_j_kg` | `float` | `required` |
| `mass_evidence_id` | `str` | `required` |
| `heat_evidence_id` | `str` | `required` |
| `combustion_basis_id` | `str` | `required` |
| `source_id` | `str` | `required` |
| `origin` | `Origin` | `required` |

Computed properties: `energy_j`.

#### `h2physics.adapters.hyram_overpressure.OverpressureEvent`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/hyram_overpressure.py#L99)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `event_id` | `str` | `required` |
| `centre_m` | `tuple[float, float, float]` | `required` |
| `frame_id` | `str` | `required` |
| `centre_evidence_id` | `str` | `required` |
| `snapshot_time_s` | `float` | `required` |
| `clock_id` | `str` | `required` |

#### `h2physics.adapters.hyram_overpressure.OverpressureEnvironment`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/hyram_overpressure.py#L117)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `ambient_pressure_pa_absolute` | `float` | `required` |
| `pressure_evidence_id` | `str` | `required` |


<a id="module-h2physics-adapters-detonation-sdtoolboxdetonation-cj"></a>

## 외부 평형 CJ 폭굉 종단 상태 / Native equilibrium CJ detonation endpoint

Family / navigation ID: `combustion.detonation`

Import module: `h2physics.adapters.detonation`; selected entry: `SDToolboxDetonation.cj`.

#### `h2physics.adapters.detonation.SDToolboxDetonation`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/detonation.py#L312)

Stationary homogeneous neutral ideal gas: equilibrium CJ/frozen shocks.

Native CJspeed requires a mechanism filename. A managed, explicitly supplied
ASCII-relative workspace bridges an actual source phase without altering
native code, CWD or input-file search globals. Only identical thermochemistry
is admitted; kinetics/transport are not used by this equilibrium level.

```python
SDToolboxDetonation(native: NativeSDToolbox, phase_factory: Callable, basis: MechanismBasis, *, native_workspace: Path | str, tolerances: DetonationTolerances=DetonationTolerances())
```

#### `h2physics.adapters.detonation.SDToolboxDetonation.cj`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/detonation.py#L469)

```python
cj(self, initial: ReactiveState, *, evidence: DetonationEvidence, settings: DetonationSettings=DetonationSettings())
```

The source has no explicit return annotation; inspect its return statements and the domain manual. No return type is invented by this generator.

### Returned value / 반환값

`CJWaveResult`

This return contract was reviewed from the implementation; it is not an annotation present in the source signature.

### Related input/return records / 관련 입력·반환 객체

#### `h2physics.adapters.detonation.CJWaveResult`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/detonation.py#L241)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `mechanism_basis` | `MechanismBasis` | `required` |
| `evidence` | `DetonationEvidence` | `required` |
| `settings` | `DetonationSettings` | `required` |
| `initial` | `WaveSnapshot` | `required` |
| `final` | `WaveSnapshot` | `required` |
| `speed_m_s` | `float` | `required` |
| `native_fitted_speed_m_s` | `float` | `required` |
| `native_fit_r_squared` | `float` | `required` |
| `native_density_ratio` | `float` | `required` |
| `conservation` | `WaveConservation` | `required` |
| `independent_equilibrium_sound_m_s` | `float` | `required` |
| `toolbox_equilibrium_sound_m_s` | `float` | `required` |
| `frozen_sound_m_s` | `float` | `required` |
| `cj_sonic_relative_residual` | `float` | `required` |
| `native_sound_relative_difference` | `float` | `required` |
| `local_density_speed_results` | `tuple` | `required` |
| `native_upstream` | `Any` | `required` |
| `native_cj_phase` | `Any` | `required` |
| `native_fit_result` | `Any` | `required` |
| `native_cj_result` | `Any` | `required` |
| `native_sound_phase` | `Any` | `required` |
| `native_isentropic_phases` | `tuple` | `required` |
| `native_local_density_phases` | `tuple` | `required` |
| `local_density_conservation` | `tuple` | `required` |
| `native_bridge` | `NativeMechanismBridge` | `required` |
| `native_provider` | `NativeSDToolbox` | `required` |
| `source_phase` | `Any` | `required` |
| `copy_audits` | `tuple` | `required` |
| `native_fit_internal_phases_available` | `bool` | `False` |
| `native_fit_controls_exposed` | `bool` | `False` |
| `hydrogen_partition_id` | `str` | `'mechanism-H2-spin-unresolved'` |

#### `h2physics.adapters.detonation.NativeSDToolbox`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/detonation.py#L90)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `postshock` | `Any` | `required` |
| `thermo` | `Any` | `required` |
| `config` | `Any` | `required` |
| `source_id` | `str` | `required` |
| `source_sha256` | `str` | `required` |

#### `h2physics.adapters.cantera.MechanismBasis`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/cantera.py#L22)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `identifier` | `str` | `required` |
| `source_sha256` | `str` | `required` |
| `license_id` | `str` | `required` |
| `references` | `tuple[str, ...]` | `required` |
| `minimum_temperature_k` | `float` | `required` |
| `maximum_temperature_k` | `float` | `required` |
| `minimum_pressure_pa` | `float` | `required` |
| `maximum_pressure_pa` | `float` | `required` |

#### `h2physics.adapters.detonation.DetonationTolerances`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/detonation.py#L143)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `mass_flux_absolute_kg_m2_s` | `float` | `1e-07` |
| `momentum_absolute_pa` | `float` | `0.1` |
| `total_enthalpy_absolute_j_kg` | `float` | `0.01` |
| `elemental_mass_fraction` | `float` | `1e-10` |
| `sonic_relative` | `float` | `0.0001` |
| `native_sound_relative` | `float` | `0.0002` |
| `minimum_native_fit_r_squared` | `float` | `0.99999` |

#### `h2physics.adapters.cantera.ReactiveState`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/cantera.py#L51)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `temperature_k` | `float` | `required` |
| `pressure_pa` | `float` | `required` |
| `mole_fractions` | `Mapping[str, float]` | `required` |

#### `h2physics.adapters.detonation.DetonationEvidence`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/detonation.py#L110)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `source_id` | `str` | `required` |
| `initial_state_source_id` | `str` | `required` |
| `gas_phase_scope_id` | `str` | `required` |
| `clock_id` | `str` | `required` |
| `event_time_s` | `float` | `required` |
| `frame_id` | `str` | `required` |
| `origin` | `Origin` | `required` |

#### `h2physics.adapters.detonation.DetonationSettings`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/detonation.py#L130)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `native_jump_relative_tolerance` | `float` | `1e-08` |
| `sound_density_relative_step` | `float` | `0.001` |
| `sound_equilibrium_relative_tolerance` | `float` | `1e-11` |
| `local_density_ratio_relative_step` | `float` | `0.001` |

#### `h2physics.adapters.detonation.WaveSnapshot`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/detonation.py#L160)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `temperature_k` | `float` | `required` |
| `pressure_pa` | `float` | `required` |
| `density_kg_m3` | `float` | `required` |
| `enthalpy_j_kg` | `float` | `required` |
| `internal_energy_j_kg` | `float` | `required` |
| `entropy_j_kg_k` | `float` | `required` |
| `mole_fractions` | `Mapping[str, float]` | `required` |
| `mass_fractions` | `Mapping[str, float]` | `required` |
| `elemental_mass_fractions` | `Mapping[str, float]` | `required` |

#### `h2physics.adapters.detonation.WaveConservation`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/detonation.py#L184)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `upstream_relative_velocity_m_s` | `float` | `required` |
| `downstream_relative_velocity_m_s` | `float` | `required` |
| `downstream_lab_velocity_m_s` | `float` | `required` |
| `density_ratio` | `float` | `required` |
| `mass_flux_residual_kg_m2_s` | `float` | `required` |
| `momentum_residual_pa` | `float` | `required` |
| `total_enthalpy_residual_j_kg` | `float` | `required` |
| `hugoniot_residual_j_kg` | `float` | `required` |
| `maximum_element_mass_fraction_residual` | `float` | `required` |
| `entropy_increase_j_kg_k` | `float` | `required` |

#### `h2physics.adapters.detonation.NativeMechanismBridge`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/detonation.py#L198)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `yaml_sha256` | `str` | `required` |
| `source_thermo_sha256` | `str` | `required` |
| `reloaded_thermo_sha256` | `str` | `required` |
| `actual_reloaded_phase` | `Any` | `required` |
| `kinetics_and_transport_used` | `bool` | `False` |


<a id="module-h2physics-adapters-detonation-sdtoolboxdetonation-frozen_shock"></a>

## 외부 동결 이상기체 정상 충격파 / Native frozen ideal-gas normal shock

Family / navigation ID: `combustion.detonation`

Import module: `h2physics.adapters.detonation`; selected entry: `SDToolboxDetonation.frozen_shock`.

#### `h2physics.adapters.detonation.SDToolboxDetonation`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/detonation.py#L312)

Stationary homogeneous neutral ideal gas: equilibrium CJ/frozen shocks.

Native CJspeed requires a mechanism filename. A managed, explicitly supplied
ASCII-relative workspace bridges an actual source phase without altering
native code, CWD or input-file search globals. Only identical thermochemistry
is admitted; kinetics/transport are not used by this equilibrium level.

```python
SDToolboxDetonation(native: NativeSDToolbox, phase_factory: Callable, basis: MechanismBasis, *, native_workspace: Path | str, tolerances: DetonationTolerances=DetonationTolerances())
```

#### `h2physics.adapters.detonation.SDToolboxDetonation.frozen_shock`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/detonation.py#L436)

```python
frozen_shock(self, initial: ReactiveState, *, speed_m_s: float, evidence: DetonationEvidence, settings: DetonationSettings=DetonationSettings())
```

The source has no explicit return annotation; inspect its return statements and the domain manual. No return type is invented by this generator.

### Returned value / 반환값

`FrozenShockResult`

This return contract was reviewed from the implementation; it is not an annotation present in the source signature.

### Related input/return records / 관련 입력·반환 객체

#### `h2physics.adapters.detonation.FrozenShockResult`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/detonation.py#L207)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `mechanism_basis` | `MechanismBasis` | `required` |
| `evidence` | `DetonationEvidence` | `required` |
| `initial` | `WaveSnapshot` | `required` |
| `final` | `WaveSnapshot` | `required` |
| `conservation` | `WaveConservation` | `required` |
| `native_upstream` | `Any` | `required` |
| `native_downstream` | `Any` | `required` |
| `native_solver_result` | `Any` | `required` |
| `source_phase` | `Any` | `required` |
| `native_provider` | `NativeSDToolbox` | `required` |
| `copy_audits` | `tuple` | `required` |

#### `h2physics.adapters.detonation.NativeSDToolbox`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/detonation.py#L90)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `postshock` | `Any` | `required` |
| `thermo` | `Any` | `required` |
| `config` | `Any` | `required` |
| `source_id` | `str` | `required` |
| `source_sha256` | `str` | `required` |

#### `h2physics.adapters.cantera.MechanismBasis`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/cantera.py#L22)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `identifier` | `str` | `required` |
| `source_sha256` | `str` | `required` |
| `license_id` | `str` | `required` |
| `references` | `tuple[str, ...]` | `required` |
| `minimum_temperature_k` | `float` | `required` |
| `maximum_temperature_k` | `float` | `required` |
| `minimum_pressure_pa` | `float` | `required` |
| `maximum_pressure_pa` | `float` | `required` |

#### `h2physics.adapters.detonation.DetonationTolerances`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/detonation.py#L143)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `mass_flux_absolute_kg_m2_s` | `float` | `1e-07` |
| `momentum_absolute_pa` | `float` | `0.1` |
| `total_enthalpy_absolute_j_kg` | `float` | `0.01` |
| `elemental_mass_fraction` | `float` | `1e-10` |
| `sonic_relative` | `float` | `0.0001` |
| `native_sound_relative` | `float` | `0.0002` |
| `minimum_native_fit_r_squared` | `float` | `0.99999` |

#### `h2physics.adapters.cantera.ReactiveState`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/cantera.py#L51)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `temperature_k` | `float` | `required` |
| `pressure_pa` | `float` | `required` |
| `mole_fractions` | `Mapping[str, float]` | `required` |

#### `h2physics.adapters.detonation.DetonationEvidence`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/detonation.py#L110)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `source_id` | `str` | `required` |
| `initial_state_source_id` | `str` | `required` |
| `gas_phase_scope_id` | `str` | `required` |
| `clock_id` | `str` | `required` |
| `event_time_s` | `float` | `required` |
| `frame_id` | `str` | `required` |
| `origin` | `Origin` | `required` |

#### `h2physics.adapters.detonation.DetonationSettings`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/detonation.py#L130)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `native_jump_relative_tolerance` | `float` | `1e-08` |
| `sound_density_relative_step` | `float` | `0.001` |
| `sound_equilibrium_relative_tolerance` | `float` | `1e-11` |
| `local_density_ratio_relative_step` | `float` | `0.001` |

#### `h2physics.adapters.detonation.WaveSnapshot`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/detonation.py#L160)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `temperature_k` | `float` | `required` |
| `pressure_pa` | `float` | `required` |
| `density_kg_m3` | `float` | `required` |
| `enthalpy_j_kg` | `float` | `required` |
| `internal_energy_j_kg` | `float` | `required` |
| `entropy_j_kg_k` | `float` | `required` |
| `mole_fractions` | `Mapping[str, float]` | `required` |
| `mass_fractions` | `Mapping[str, float]` | `required` |
| `elemental_mass_fractions` | `Mapping[str, float]` | `required` |

#### `h2physics.adapters.detonation.WaveConservation`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/detonation.py#L184)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `upstream_relative_velocity_m_s` | `float` | `required` |
| `downstream_relative_velocity_m_s` | `float` | `required` |
| `downstream_lab_velocity_m_s` | `float` | `required` |
| `density_ratio` | `float` | `required` |
| `mass_flux_residual_kg_m2_s` | `float` | `required` |
| `momentum_residual_pa` | `float` | `required` |
| `total_enthalpy_residual_j_kg` | `float` | `required` |
| `hugoniot_residual_j_kg` | `float` | `required` |
| `maximum_element_mass_fraction_residual` | `float` | `required` |
| `entropy_increase_j_kg_k` | `float` | `required` |


## Maintaining this guide / 갱신

Curated purposes and entry selection live in `scripts/readme_module_guide.py`. Run `python scripts/readme_module_guide.py` to regenerate both README blocks and this file. Run `python scripts/readme_module_guide.py --check` to reject stale output, unresolved callables or missing catalog IDs. The script parses source with the standard library, imports no physical engine and runs no calculation. Review purpose/units/limits against domain manuals when an API changes. It preserves authored scientific attribution and performs no automatic translation of external material.
