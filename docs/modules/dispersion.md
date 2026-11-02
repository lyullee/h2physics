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

- [고압 기체 수소 우선 확산 경로: HyRAM+ / Preferred high-pressure gas route: HyRAM+](#module-h2physics-dispersion-run_preferred_gas_dispersion)
- [액화수소 유래 증기운 우선 확산 경로: SLABx-LH2 / Preferred LH2-origin vapor-cloud route: SLABx-LH2](#module-h2physics-dispersion-run_preferred_lh2_dispersion)
- [고정 유량 독립 스냅숏 인터페이스·호환 수신기 필요 / Independent fixed-flow snapshot contract; compatible receiver required](#module-h2physics-adapters-hyram_finite_source_snapshots-run_hyram_finite_source_snapshots)
- [유한 완전혼합 비반응 기체 공간의 압력·열응답 / Finite well-mixed nonreacting volume and thermal pressure](#module-h2physics-adapters-cantera_volume-canteraopengasvolume-run)
- [두 통풍구 공간의 부력 상부 수소층 축적 / Buoyant upper-layer accumulation with two vents](#module-h2physics-buoyant_layer-run_two_vent_hydrogen_layer)
- [지정 몰 이동량에 따른 고정 상태 구획 간 수소 혼합 / Fixed-state room mixing with prescribed balanced molar transfers](#module-h2physics-compartment_network-simulate_hydrogen_compartment_network)
- [외부 FDS 장애물 확산 사례의 격자·형상 정의 / External FDS obstacle-case mesh and geometry contract](#module-h2physics-adapters-obstacle_dispersion-cfdmesh)
- [별도 설치 FDS로 지정 장애물 확산 사례 실행 / Run a declared obstacle case with a separately installed FDS executable](#module-h2physics-adapters-obstacle_dispersion-run_obstacle_dispersion)

<a id="module-h2physics-dispersion-run_preferred_gas_dispersion"></a>

## 고압 기체 수소 우선 확산 경로: HyRAM+ / Preferred high-pressure gas route: HyRAM+

Family / navigation ID: `dispersion.outdoor`

Import module: `h2physics.dispersion`; selected entry: `run_preferred_gas_dispersion`.

#### `h2physics.dispersion.run_preferred_gas_dispersion`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/dispersion.py#L261)

Run the preferred gas provider while retaining the declared accident origin.

HyRAM supports this checked high-pressure-gas entry point. An LH2-origin
release needs its separate pool/source boundary and SLABx-LH2 interface;
it cannot be represented by this nozzle call or rerouted automatically.

```python
run_preferred_gas_dispersion(family: HydrogenReleaseFamily | str, *, fluid_factory: Callable, orifice_factory: Callable, jet_factory: Callable, upstream: ThermoState, ambient: ThermoState, opening: NozzleOpening, location: SourceLocation, evidence_id: str, solver_options: dict, require_accepted: bool=True)
```

The source has no explicit return annotation; inspect its return statements and the domain manual. No return type is invented by this generator.

### Returned value / 반환값

`HyRAMJetRun`

This return contract was reviewed from the implementation; it is not an annotation present in the source signature.

### Related input/return records / 관련 입력·반환 객체

#### `h2physics.adapters.hyram.HyRAMJetRun`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/hyram.py#L67)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `native` | `Any` | `required` |
| `upstream` | `ThermoState` | `required` |
| `ambient` | `ThermoState` | `required` |
| `opening` | `NozzleOpening` | `required` |
| `location` | `SourceLocation` | `required` |
| `evidence_id` | `str` | `required` |
| `mass_flow_kg_s` | `float` | `required` |
| `gaussian_entry_h2_flow_kg_s` | `float` | `required` |
| `maximum_transport_h2_residual_kg_s` | `float` | `required` |
| `maximum_h2_flux_residual_kg_s` | `float` | `required` |
| `mass_budget_kg_s` | `float` | `required` |
| `accepted` | `bool` | `required` |
| `centreline` | `np.ndarray` | `required` |

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

#### `h2physics.core.PropertyBasis`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/core.py#L97)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `fluid` | `str` | `required` |
| `reference_id` | `str` | `required` |
| `spin_composition` | `str` | `'unspecified'` |


<a id="module-h2physics-dispersion-run_preferred_lh2_dispersion"></a>

## 액화수소 유래 증기운 우선 확산 경로: SLABx-LH2 / Preferred LH2-origin vapor-cloud route: SLABx-LH2

Family / navigation ID: `dispersion.outdoor`

Import module: `h2physics.dispersion`; selected entry: `run_preferred_lh2_dispersion`.

#### `h2physics.dispersion.run_preferred_lh2_dispersion`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/dispersion.py#L304)

Run the preferred SLABx-LH2 vapor path from an explicit pool boundary.

The interval source describes emitted vapor, not liquid release or pool
formation. Callers must supply that declared boundary, footprint evidence,
atmosphere, thermophysical objects and native engine functions themselves.

```python
run_preferred_lh2_dispersion(family: HydrogenReleaseFamily | str, *, source, native_pool_factory: Callable, substance: Any, area_m2: float, footprint_evidence_id: str, ambient_pressure_pa: float, atmosphere: Any, emission_thermo: Any, water_thermo: Any, runner: Callable, premise_check: Callable, width_context: Callable, width_coupling: bool, x_max_m: float, solver_options: dict | None=None, source_tolerances: SLABLH2SourceTolerances | None=None, require_accepted: bool=True)
```

The source has no explicit return annotation; inspect its return statements and the domain manual. No return type is invented by this generator.

### Returned value / 반환값

`SLABLH2Run`

This return contract was reviewed from the implementation; it is not an annotation present in the source signature.

### Related input/return records / 관련 입력·반환 객체

#### `h2physics.adapters.slabx_lh2.SLABLH2Run`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/slabx_lh2.py#L758)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `native` | `Any` | `required` |
| `used_source` | `Any` | `required` |
| `boundary` | `NativeVaporPoolBoundary` | `required` |
| `atmosphere` | `Any` | `required` |
| `premise` | `Mapping[str, Any]` | `required` |
| `source_mass_residual_kg` | `float` | `required` |
| `source_area_change_m2` | `float` | `required` |
| `boundary_audit` | `'SLABLH2SourceAudit'` | `required` |
| `source_tolerances` | `SLABLH2SourceTolerances` | `required` |
| `accepted` | `bool` | `required` |

#### `h2physics.adapters.slabx_lh2.SLABLH2SourceTolerances`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/slabx_lh2.py#L736)

Dimensioned acceptance tolerances for native source-boundary drift.

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `rate_absolute_kg_s` | `float` | `1e-10` |
| `duration_absolute_s` | `float` | `1e-10` |
| `area_absolute_m2` | `float` | `1e-12` |
| `mass_absolute_kg` | `float` | `1e-10` |
| `temperature_absolute_k` | `float` | `1e-08` |
| `relative` | `float` | `1e-08` |

#### `h2physics.adapters.slabx_lh2.NativeVaporPoolBoundary`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/slabx_lh2.py#L18)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `native_source` | `Any` | `required` |
| `mass_source` | `IntervalMassSource` | `required` |
| `area_m2` | `float` | `required` |
| `footprint_evidence_id` | `str` | `required` |
| `ambient_pressure_pa` | `float` | `required` |
| `native_rate_kg_s` | `float` | `required` |
| `native_area_m2` | `float` | `required` |
| `native_duration_s` | `float` | `required` |
| `native_temperature_k` | `float` | `required` |

#### `h2physics.adapters.slabx_lh2.SLABLH2SourceAudit`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/slabx_lh2.py#L871)

Requested, constructed and finally used source settings for one run.

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `requested_rate_kg_s` | `float` | `required` |
| `initial_native_rate_kg_s` | `float` | `required` |
| `used_rate_kg_s` | `float` | `required` |
| `requested_duration_s` | `float` | `required` |
| `initial_native_duration_s` | `float` | `required` |
| `used_duration_s` | `float` | `required` |
| `requested_area_m2` | `float` | `required` |
| `initial_native_area_m2` | `float` | `required` |
| `used_area_m2` | `float` | `required` |
| `requested_temperature_k` | `float` | `required` |
| `initial_native_temperature_k` | `float` | `required` |
| `used_temperature_k` | `float` | `required` |
| `requested_mass_kg` | `float` | `required` |

Computed properties: `initial_mass_kg`, `used_mass_kg`, `initial_mass_residual_kg`, `used_mass_residual_kg`, `initial_rate_change_kg_s`, `used_rate_change_kg_s`, `initial_duration_change_s`, `used_duration_change_s`, `initial_area_change_m2`, `used_area_change_m2`, `initial_temperature_change_k`, `used_temperature_change_k`.


<a id="module-h2physics-adapters-hyram_finite_source_snapshots-run_hyram_finite_source_snapshots"></a>

## 고정 유량 독립 스냅숏 인터페이스·호환 수신기 필요 / Independent fixed-flow snapshot contract; compatible receiver required

Family / navigation ID: `dispersion.fixed_flow_snapshots`

Import module: `h2physics.adapters.hyram_finite_source_snapshots`; selected entry: `run_hyram_finite_source_snapshots`.

#### `h2physics.adapters.hyram_finite_source_snapshots.run_hyram_finite_source_snapshots`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/hyram_finite_source_snapshots.py#L412)

Call a compatible fixed-flow receiver once for each positive source bin.

Calls use the left-hold H2 rate and upstream state over each original
interval. Zero-flow intervals are retained without a native call. Raised
solver exceptions stay attached to their exact interval. This entrypoint
deliberately has no plume memory, time interpolation, dose, or native
HyRAM compatibility claim.

```python
run_hyram_finite_source_snapshots(projection: NozzleSourceProjection, *, receiver: HyRAMFixedFlowReceiver, conditions: Sequence[HyRAMFixedFlowCondition | None], receiver_identity: str, source_rate_budget_kg_s: float, require_accepted: bool=True) -> HyRAMFiniteSourceSnapshotSeries
```

### Returned value / 반환값

`HyRAMFiniteSourceSnapshotSeries`

### Related input/return records / 관련 입력·반환 객체

#### `h2physics.release.NozzleSourceProjection`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/release.py#L454)

Immutable mass/energy projection receipt for one sampled nozzle history.

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `history` | `SourceHistory` | `required` |
| `source` | `'IntervalMassSource'` | `required` |
| `representative_state` | `ThermoState` | `required` |
| `flow_rule` | `Literal['left_hold', 'right_hold', 'trapezoid']` | `required` |
| `quadrature_evidence_id` | `str` | `required` |
| `state_projection_evidence_id` | `str` | `required` |
| `sample_mass_flow_kg_s` | `tuple[float, ...]` | `required` |
| `sample_withdrawal_energy_w` | `tuple[float, ...]` | `required` |
| `sample_static_enthalpy_w` | `tuple[float, ...]` | `required` |
| `sample_kinetic_power_w` | `tuple[float, ...]` | `required` |
| `interval_mass_kg` | `tuple[float, ...]` | `required` |
| `interval_withdrawal_energy_j` | `tuple[float, ...]` | `required` |
| `interval_static_enthalpy_j` | `tuple[float, ...]` | `required` |
| `interval_kinetic_energy_j` | `tuple[float, ...]` | `required` |
| `nozzle_energy_residual_j` | `tuple[float, ...]` | `required` |
| `representative_enthalpy_j` | `tuple[float, ...]` | `required` |
| `state_projection_residual_j` | `tuple[float, ...]` | `required` |

Computed properties: `total_mass_kg`, `total_nozzle_energy_residual_j`, `total_state_projection_residual_j`.

#### `h2physics.adapters.hyram_finite_source_snapshots.HyRAMFixedFlowCondition`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/hyram_finite_source_snapshots.py#L77)

Caller-owned atmospheric and native-solver boundary for one interval.

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `ambient` | `ThermoState` | `required` |
| `native_atmosphere` | `Any` | `required` |
| `atmosphere_evidence_id` | `str` | `required` |
| `state_mapping_evidence_id` | `str` | `required` |
| `solver_options` | `Mapping[str, Any]` | `field(default_factory=dict)` |

#### `h2physics.adapters.hyram_finite_source_snapshots.HyRAMFiniteSourceSnapshotSeries`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/hyram_finite_source_snapshots.py#L282)

Finite-source results as independent snapshots, never a transient plume.

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `projection` | `NozzleSourceProjection` | `required` |
| `conditions` | `tuple[HyRAMFixedFlowCondition &#124; None, ...]` | `required` |
| `interval_results` | `tuple[HyRAMFiniteSourceSnapshot, ...]` | `required` |
| `receiver_identity` | `str` | `required` |
| `source_rate_budget_kg_s` | `float` | `required` |

Computed properties: `plume_memory_included`, `method_id`, `source_end_reason`, `requested_source_mass_kg`, `accepted_source_mass_kg`, `source_plane_mass_residual_kg`, `all_intervals_accepted`.

#### `h2physics.release.SourceHistory`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/release.py#L302)

Predicted nozzle-plane samples. No atmospheric or ground partition is inferred.

Samples describe a window, including its final endpoint. No interpolation or
integration rule is implicit; discontinuities need separate windows.

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `location` | `SourceLocation` | `required` |
| `time_s` | `tuple[float, ...]` | `required` |
| `samples` | `tuple[NozzleResult, ...]` | `required` |
| `end_reason` | `Literal['window_end', 'isolation', 'pressure_equalized', 'inventory_limit']` | `required` |

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

#### `h2physics.adapters.hyram_finite_source_snapshots.HyRAMFiniteSourceSnapshot`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/hyram_finite_source_snapshots.py#L200)

One source interval and its independent stationary receiver result.

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `interval_index` | `int` | `required` |
| `start_s` | `float` | `required` |
| `end_s` | `float` | `required` |
| `requested_mass_flow_kg_s` | `float` | `required` |
| `requested_mass_kg` | `float` | `required` |
| `run` | `HyRAMFixedFlowRun &#124; None` | `required` |
| `failure` | `BaseException &#124; None` | `required` |
| `source_rate_residual_kg_s` | `float &#124; None` | `required` |
| `source_rate_budget_kg_s` | `float` | `required` |
| `accepted` | `bool &#124; None` | `required` |

Computed properties: `native_failure_result`.


<a id="module-h2physics-adapters-cantera_volume-canteraopengasvolume-run"></a>

## 유한 완전혼합 비반응 기체 공간의 압력·열응답 / Finite well-mixed nonreacting volume and thermal pressure

Family / navigation ID: `dispersion.enclosure`

Import module: `h2physics.adapters.cantera_volume`; selected entry: `CanteraOpenGasVolume.run`.

#### `h2physics.adapters.cantera_volume.CanteraOpenGasVolume`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/cantera_volume.py#L369)

A constant-volume, finite-inventory thermodynamic reference model.

``phase_factory`` must produce fresh native ideal-gas Solutions. Default
chemistry="frozen" requires zero reactions, retaining the established level.
Explicit chemistry="finite_rate" delegates gas kinetics to Cantera and appends
chemical production integrals for independent species/element accounting.
There are no surfaces, catalysts, solids or custom reaction-rate equations.
The basis record is
caller-supplied evidence, not proof of its provenance. No mechanism is bundled.
Native Cantera 3.2 owns every physical state derivative and integration step.

```python
CanteraOpenGasVolume(phase_factory: Callable, mechanism_basis: MechanismBasis, *, chemistry: str='frozen')
```

#### `h2physics.adapters.cantera_volume.CanteraOpenGasVolume.run`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/cantera_volume.py#L393)

```python
run(self, initial: ReactiveState, time_s, *, volume_m3: float, clock_id: str, feeds: tuple[GasFeed, ...]=(), vents: tuple[GasVent, ...]=(), heat_boundaries: tuple[GasHeatBoundary, ...]=(), maximum_time_step_s: float, relative_tolerance: float=1e-09, absolute_tolerance: float=1e-13, minimum_inventory_kg: float=1e-12, energy_ledger_scale_j: float=1000000.0) -> GasVolumeTrace
```

### Returned value / 반환값

`GasVolumeTrace`

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

#### `h2physics.adapters.cantera_volume.GasFeed`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/cantera_volume.py#L110)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `rate` | `GasBoundaryRate` | `required` |
| `state` | `ReactiveState` | `required` |

#### `h2physics.adapters.cantera_volume.GasVent`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/cantera_volume.py#L116)

Prescribed outward extraction; its magnitude can call the shared nozzle.

It is not itself a pressure-driven valve law. A callback is responsible for
declaring that closure, including zero flow at an unavailable pressure head.
The native flow device removes well-mixed upstream composition and enthalpy.

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `rate` | `GasBoundaryRate` | `required` |
| `downstream_state` | `ReactiveState` | `required` |

#### `h2physics.adapters.cantera_volume.GasHeatBoundary`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/cantera_volume.py#L129)

Stationary native wall, oriented environment -> enclosure.

``heat_flux_w_m2(time_s)`` is signed heat into the volume. Conduction and
radiation also use native Cantera Wall terms and a fixed environment state.
Wall thermal storage is not resolved.

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `boundary_id` | `str` | `required` |
| `clock_id` | `str` | `required` |
| `support_start_s` | `float` | `required` |
| `support_end_s` | `float` | `required` |
| `environment_state` | `ReactiveState` | `required` |
| `area_m2` | `float` | `required` |
| `heat_transfer_coefficient_w_m2_k` | `float` | `0.0` |
| `emissivity` | `float` | `0.0` |
| `heat_flux_w_m2` | `Callable` | `lambda t: 0.0` |

#### `h2physics.adapters.cantera_volume.GasVolumeTrace`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/cantera_volume.py#L206)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `mechanism_basis` | `MechanismBasis` | `required` |
| `phase_fingerprint` | `str` | `required` |
| `clock_id` | `str` | `required` |
| `species_names` | `tuple[str, ...]` | `required` |
| `time_s` | `np.ndarray` | `required` |
| `snapshots` | `tuple[GasVolumeSnapshot, ...]` | `required` |
| `ledger_names` | `tuple[str, ...]` | `required` |
| `ledger_units` | `tuple[str, ...]` | `required` |
| `ledger_native_scale_to_si` | `np.ndarray` | `required` |
| `boundary_integrals` | `np.ndarray` | `required` |
| `mass_residual_kg` | `np.ndarray` | `required` |
| `species_residual_kg` | `np.ndarray` | `required` |
| `energy_residual_j` | `np.ndarray` | `required` |
| `native` | `NativeGasVolumeObjects` | `required` |
| `feeds` | `tuple[GasFeed, ...]` | `required` |
| `vents` | `tuple[GasVent, ...]` | `required` |
| `heat_boundaries` | `tuple[GasHeatBoundary, ...]` | `required` |
| `evaluated_clock_bounds_s` | `tuple[float, float] &#124; None` | `required` |
| `ledger_method` | `str` | `'native-CVODES-appended-boundary-integrals'` |
| `hydrogen_partition_id` | `str` | `'mechanism-H2-spin-unresolved'` |
| `chemistry` | `str` | `'frozen'` |
| `reaction_species_integrals_kg` | `np.ndarray &#124; None` | `None` |
| `element_names` | `tuple[str, ...]` | `()` |
| `element_residual_kg` | `np.ndarray &#124; None` | `None` |
| `definition_guard` | `str` | `'every-native-RHS'` |
| `source_phase_fingerprint` | `str` | `''` |
| `phase_copy_audits` | `tuple[NativePhaseCopyAudit, ...]` | `()` |

#### `h2physics.adapters.cantera_volume.GasBoundaryRate`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/cantera_volume.py#L36)

Nonnegative oriented rate on an explicit absolute clock and finite support.

By default ``callback(time_s, native_volume_phase)`` returns kg/s. The phase is
read-only during this callback. Explicit ``phase_access="time_only"`` instead
calls ``callback(time_s)`` and permits private reactive phases. Negative signed
observations are rejected, never clipped
by Cantera's own nonnegative MassFlowController implementation. Callbacks must
be continuous within the integration window at this model level.

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `boundary_id` | `str` | `required` |
| `clock_id` | `str` | `required` |
| `support_start_s` | `float` | `required` |
| `support_end_s` | `float` | `required` |
| `callback` | `Callable` | `required` |
| `origin` | `Origin` | `required` |
| `source_id` | `str` | `required` |
| `phase_access` | `str` | `'native'` |

#### `h2physics.adapters.cantera_volume.GasVolumeSnapshot`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/cantera_volume.py#L165)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `time_s` | `float` | `required` |
| `mass_kg` | `float` | `required` |
| `volume_m3` | `float` | `required` |
| `temperature_k` | `float` | `required` |
| `pressure_pa` | `float` | `required` |
| `mass_fractions` | `Mapping[str, float]` | `required` |
| `mole_fractions` | `Mapping[str, float]` | `required` |
| `internal_energy_j` | `float` | `required` |
| `specific_enthalpy_j_kg` | `float` | `required` |

#### `h2physics.adapters.cantera_volume.NativeGasVolumeObjects`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/cantera_volume.py#L182)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `reactor` | `object` | `required` |
| `network` | `object` | `required` |
| `feed_reservoirs` | `tuple` | `required` |
| `vent_reservoirs` | `tuple` | `required` |
| `environment_reservoirs` | `tuple` | `required` |
| `feed_devices` | `tuple` | `required` |
| `vent_devices` | `tuple` | `required` |
| `walls` | `tuple` | `required` |

#### `h2physics.adapters.cantera_volume.NativePhaseCopyAudit`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/cantera_volume.py#L194)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `source_fingerprint` | `str` | `required` |
| `owned_fingerprint` | `str` | `required` |
| `maximum_relative_roundtrip` | `float` | `required` |
| `numeric_roundtrip_count` | `int` | `required` |
| `omitted_note_count` | `int` | `required` |
| `source_element_names` | `tuple[str, ...]` | `required` |
| `owned_element_names` | `tuple[str, ...]` | `required` |
| `relative_roundtrip_limit` | `float` | `2e-15` |


<a id="module-h2physics-buoyant_layer-run_two_vent_hydrogen_layer"></a>

## 두 통풍구 공간의 부력 상부 수소층 축적 / Buoyant upper-layer accumulation with two vents

Family / navigation ID: `dispersion.buoyant_layer`

Import module: `h2physics.buoyant_layer`; selected entry: `run_two_vent_hydrogen_layer`.

#### `h2physics.buoyant_layer.run_two_vent_hydrogen_layer`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/buoyant_layer.py#L241)

Integrate a steady vertical H2 release into a still-air two-vent room.

The state uses upper-layer volume and H2 mass. A fourth-order fixed-step
Runge-Kutta march is used; vent pressure is obtained from an inner scalar
continuity solve. The case stops with an error if the interface reaches
the source or the assumed one-way vent-flow regime ceases to exist.

```python
run_two_vent_hydrogen_layer(config: TwoVentHydrogenLayerConfig, *, hydrogen_mass_flow_kg_s: float, duration_s: float, maximum_step_s: float, properties: CoolPropHydrogenAirProperties | None=None) -> TwoVentHydrogenLayerResult
```

### Returned value / 반환값

`TwoVentHydrogenLayerResult`

### Related input/return records / 관련 입력·반환 객체

#### `h2physics.buoyant_layer.TwoVentHydrogenLayerConfig`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/buoyant_layer.py#L94)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `compartment_height_m` | `float` | `required` |
| `floor_area_m2` | `float` | `required` |
| `source_height_m` | `float` | `required` |
| `lower_vent_area_m2` | `float` | `required` |
| `upper_vent_area_m2` | `float` | `required` |
| `lower_discharge_coefficient` | `float` | `required` |
| `upper_discharge_coefficient` | `float` | `required` |
| `ambient_pressure_pa` | `float` | `required` |
| `ambient_temperature_k` | `float` | `required` |
| `initial_upper_layer_volume_m3` | `float` | `required` |
| `initial_upper_h2_mole_fraction` | `float` | `required` |
| `entrainment_coefficient` | `float` | `0.102` |
| `gravity_m_s2` | `float` | `9.80665` |
| `maximum_pressure_drop_pa` | `float &#124; None` | `None` |

#### `h2physics.buoyant_layer.TwoVentHydrogenLayerResult`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/buoyant_layer.py#L137)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `time_s` | `tuple[float, ...]` | `required` |
| `interface_height_m` | `tuple[float, ...]` | `required` |
| `upper_h2_mole_fraction` | `tuple[float, ...]` | `required` |
| `upper_h2_mass_fraction` | `tuple[float, ...]` | `required` |
| `upper_layer_volume_m3` | `tuple[float, ...]` | `required` |
| `upper_layer_density_kg_m3` | `tuple[float, ...]` | `required` |
| `compartment_overpressure_pa` | `tuple[float, ...]` | `required` |
| `lower_inflow_m3_s` | `tuple[float, ...]` | `required` |
| `upper_outflow_m3_s` | `tuple[float, ...]` | `required` |
| `hydrogen_inventory_kg` | `tuple[float, ...]` | `required` |
| `cumulative_hydrogen_in_kg` | `tuple[float, ...]` | `required` |
| `cumulative_hydrogen_out_kg` | `tuple[float, ...]` | `required` |
| `hydrogen_mass_residual_kg` | `tuple[float, ...]` | `required` |
| `vent_mass_continuity_residual_kg_s` | `tuple[float, ...]` | `required` |
| `property_backend_id` | `str` | `''` |
| `dry_air_mole_fractions` | `tuple[float, ...]` | `()` |


<a id="module-h2physics-compartment_network-simulate_hydrogen_compartment_network"></a>

## 지정 몰 이동량에 따른 고정 상태 구획 간 수소 혼합 / Fixed-state room mixing with prescribed balanced molar transfers

Family / navigation ID: `dispersion.compartment_network`

Import module: `h2physics.compartment_network`; selected entry: `simulate_hydrogen_compartment_network`.

#### `h2physics.compartment_network.simulate_hydrogen_compartment_network`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/compartment_network.py#L247)

Solve exact well-mixed H2 transport over piecewise-constant flow steps.

Per-room total inflow and outflow must balance on every interval, retaining
fixed room pressure and temperature. The species ODE uses an augmented
matrix exponential, so transport and external H2 ledgers share the exact
same accepted piecewise-constant flow schedule.

```python
simulate_hydrogen_compartment_network(model: CompartmentNetworkModel, *, time_samples_s: Sequence[float]) -> HydrogenCompartmentNetworkTrace
```

### Returned value / 반환값

`HydrogenCompartmentNetworkTrace`

### Related input/return records / 관련 입력·반환 객체

#### `h2physics.compartment_network.CompartmentNetworkModel`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/compartment_network.py#L113)

Fixed-state compartment set and its explicitly scheduled stream graph.

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `compartments` | `tuple[WellMixedCompartment, ...]` | `required` |
| `transfers` | `tuple[CompartmentMolarTransfer, ...]` | `required` |
| `clock_id` | `str` | `required` |
| `flow_balance_rtol` | `float` | `1e-09` |
| `flow_balance_atol_mol_s` | `float` | `1e-12` |

#### `h2physics.compartment_network.HydrogenCompartmentNetworkTrace`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/compartment_network.py#L151)

Run-issued H2 mole fractions and whole-network species ledger.

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `time_s` | `np.ndarray` | `field(repr=False, compare=False)` |
| `hydrogen_mole_fraction` | `np.ndarray` | `field(repr=False, compare=False)` |
| `cumulative_external_hydrogen_in_mol` | `np.ndarray` | `field(repr=False, compare=False)` |
| `cumulative_external_hydrogen_out_mol` | `np.ndarray` | `field(repr=False, compare=False)` |
| `hydrogen_balance_residual_mol` | `np.ndarray` | `field(repr=False, compare=False)` |
| `cumulative_external_carrier_in_mol` | `np.ndarray` | `field(repr=False, compare=False)` |
| `cumulative_external_carrier_out_mol` | `np.ndarray` | `field(repr=False, compare=False)` |
| `carrier_balance_residual_mol` | `np.ndarray` | `field(repr=False, compare=False)` |
| `model` | `CompartmentNetworkModel` | `field(repr=False, compare=False)` |

Computed properties: `compartment_ids`, `hydrogen_moles`, `carrier_mole_fraction`, `carrier_moles`.

#### `h2physics.compartment_network.WellMixedCompartment`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/compartment_network.py#L31)

Fixed-volume ideal-gas room with caller-owned constant P/T state.

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `identifier` | `str` | `required` |
| `volume_m3` | `float` | `required` |
| `absolute_pressure_pa` | `float` | `required` |
| `temperature_k` | `float` | `required` |
| `initial_hydrogen_mole_fraction` | `float` | `required` |
| `state_owner_id` | `str` | `required` |
| `state_evidence_id` | `str` | `required` |

Computed properties: `total_moles`.

#### `h2physics.compartment_network.CompartmentMolarTransfer`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/compartment_network.py#L62)

One direction of a caller-prescribed piecewise-constant molar stream.

A missing source denotes an external inlet and requires its hydrogen mole
fraction. A missing destination denotes discharge to the exterior. Both
endpoints may be internal for inter-compartment transfer.

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `identifier` | `str` | `required` |
| `source_compartment_id` | `str &#124; None` | `required` |
| `destination_compartment_id` | `str &#124; None` | `required` |
| `molar_flow_mol_s` | `tuple[float, ...]` | `required` |
| `state_owner_id` | `str` | `required` |
| `state_evidence_id` | `str` | `required` |
| `clock_id` | `str` | `required` |
| `external_hydrogen_mole_fraction` | `float &#124; None` | `None` |


<a id="module-h2physics-adapters-obstacle_dispersion-cfdmesh"></a>

## 외부 FDS 장애물 확산 사례의 격자·형상 정의 / External FDS obstacle-case mesh and geometry contract

Family / navigation ID: `dispersion.obstacle`

Import module: `h2physics.adapters.obstacle_dispersion`; selected entry: `CFDMesh`.

#### `h2physics.adapters.obstacle_dispersion.CFDMesh`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/obstacle_dispersion.py#L124)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `bounds_m` | `tuple[float, ...]` | `required` |
| `cells` | `tuple[int, int, int]` | `required` |
| `obstacles` | `tuple[CartesianObstacle, ...]` | `required` |
| `geometry_evidence_id` | `str` | `required` |
| `grid_evidence_id` | `str` | `required` |
| `geometry_tolerance_m` | `float` | `required` |

Computed properties: `spacing_m`, `fluid_volume_m3`.

### Returned value / 반환값

`CFDMesh`

### Related input/return records / 관련 입력·반환 객체

#### `h2physics.adapters.obstacle_dispersion.CartesianObstacle`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/obstacle_dispersion.py#L110)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `identifier` | `str` | `required` |
| `bounds_m` | `tuple[float, ...]` | `required` |

Computed properties: `volume_m3`.


<a id="module-h2physics-adapters-obstacle_dispersion-run_obstacle_dispersion"></a>

## 별도 설치 FDS로 지정 장애물 확산 사례 실행 / Run a declared obstacle case with a separately installed FDS executable

Family / navigation ID: `dispersion.obstacle`

Import module: `h2physics.adapters.obstacle_dispersion`; selected entry: `run_obstacle_dispersion`.

#### `h2physics.adapters.obstacle_dispersion.run_obstacle_dispersion`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/obstacle_dispersion.py#L667)

Actual optional external solve; called only in the later selected profile.

```python
run_obstacle_dispersion(case: ObstacleDispersionCase, engine: FDSEngine, budgets: CFDAuditBudgets, *, work_directory)
```

The source has no explicit return annotation; inspect its return statements and the domain manual. No return type is invented by this generator.

### Returned value / 반환값

`ObstacleDispersionResult`

This return contract was reviewed from the implementation; it is not an annotation present in the source signature.

### Related input/return records / 관련 입력·반환 객체

#### `h2physics.adapters.obstacle_dispersion.ObstacleDispersionResult`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/obstacle_dispersion.py#L491)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `case` | `ObstacleDispersionCase` | `required` |
| `engine` | `FDSEngine` | `required` |
| `budgets` | `CFDAuditBudgets` | `required` |
| `native_process` | `object` | `required` |
| `artifacts` | `NativeFDSArtifacts` | `required` |
| `native_git_text` | `str` | `required` |
| `device_table` | `NativeCSV` | `required` |
| `energy_table` | `NativeCSV` | `required` |
| `time_s` | `np.ndarray` | `required` |
| `hydrogen_mass_kg` | `np.ndarray` | `required` |
| `total_mass_kg` | `np.ndarray` | `required` |
| `sensible_enthalpy_j` | `np.ndarray` | `required` |
| `native_integrals` | `np.ndarray` | `required` |
| `residuals` | `np.ndarray` | `required` |
| `receptor_hydrogen_mole_fraction` | `np.ndarray` | `required` |
| `resolved_obstacles` | `tuple` | `required` |
| `failures` | `tuple[str, ...]` | `required` |
| `numerically_admitted` | `bool` | `required` |
| `software_status` | `str` | `'implemented_unverified'` |
| `residual_columns` | `tuple` | `('hydrogen_mass_kg', 'background_air_mass_kg', 'source_mass_kg', 'sensible_enthalpy_j', 'native_enthalpy_rate_integral_j', 'fluid_volume_m3')` |

#### `h2physics.adapters.obstacle_dispersion.ObstacleDispersionCase`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/obstacle_dispersion.py#L307)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `identifier` | `str` | `required` |
| `mesh` | `CFDMesh` | `required` |
| `source` | `HydrogenCFDSource` | `required` |
| `receptors` | `tuple[CFDReceptor, ...]` | `required` |
| `end_time_s` | `float` | `required` |
| `start_time_s` | `float` | `required` |
| `ambient_temperature_k` | `float` | `required` |
| `ambient_pressure_pa_absolute` | `float` | `required` |
| `gravity_m_s2` | `tuple[float, float, float]` | `required` |
| `simulation_mode` | `str` | `required` |
| `output_interval_s` | `float` | `required` |
| `initial_time_step_s` | `float` | `required` |
| `pressure_velocity_tolerance_m_s` | `float` | `required` |
| `maximum_pressure_iterations` | `int` | `required` |
| `low_mach_domain_evidence_id` | `str` | `required` |
| `diagnostic_adiabatic_boundary_evidence_id` | `str` | `required` |

#### `h2physics.adapters.obstacle_dispersion.FDSEngine`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/obstacle_dispersion.py#L385)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `executable` | `Path` | `required` |
| `executable_sha256` | `str` | `required` |
| `executable_evidence_id` | `str` | `required` |
| `threads` | `int` | `required` |
| `timeout_s` | `float` | `required` |

#### `h2physics.adapters.obstacle_dispersion.CFDAuditBudgets`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/obstacle_dispersion.py#L406)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `mass_kg` | `float` | `required` |
| `energy_j` | `float` | `required` |
| `relative` | `float` | `required` |
| `clock_s` | `float` | `required` |
| `geometry_m` | `float` | `required` |
| `volume_m3` | `float` | `required` |
| `species_fraction` | `float` | `required` |
| `maximum_speed_m_s` | `float` | `required` |
| `maximum_pressure_change_fraction` | `float` | `required` |
| `maximum_velocity_error_m_s` | `float` | `required` |
| `minimum_temperature_k` | `float` | `required` |
| `maximum_temperature_k` | `float` | `required` |

#### `h2physics.adapters.obstacle_dispersion.CFDMesh`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/obstacle_dispersion.py#L124)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `bounds_m` | `tuple[float, ...]` | `required` |
| `cells` | `tuple[int, int, int]` | `required` |
| `obstacles` | `tuple[CartesianObstacle, ...]` | `required` |
| `geometry_evidence_id` | `str` | `required` |
| `grid_evidence_id` | `str` | `required` |
| `geometry_tolerance_m` | `float` | `required` |

Computed properties: `spacing_m`, `fluid_volume_m3`.

#### `h2physics.adapters.obstacle_dispersion.HydrogenCFDSource`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/obstacle_dispersion.py#L233)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `identifier` | `str` | `required` |
| `time_s` | `tuple[float, ...]` | `required` |
| `mass_rate_kg_s` | `tuple[float, ...]` | `required` |
| `inlet_yz_m` | `tuple[float, float, float, float]` | `required` |
| `temperature_k` | `float` | `required` |
| `clock_id` | `str` | `required` |
| `frame_id` | `str` | `required` |
| `source_evidence_id` | `str` | `required` |
| `post_expansion_admission_id` | `str` | `required` |
| `species_basis` | `str` | `required` |
| `origin` | `Origin` | `required` |

Computed properties: `area_m2`.

#### `h2physics.adapters.obstacle_dispersion.CFDReceptor`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/obstacle_dispersion.py#L294)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `identifier` | `str` | `required` |
| `position_m` | `tuple[float, float, float]` | `required` |

#### `h2physics.adapters.obstacle_dispersion.NativeFDSArtifacts`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/obstacle_dispersion.py#L446)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `directory` | `Path` | `required` |
| `files_sha256` | `object` | `required` |

#### `h2physics.adapters.obstacle_dispersion.NativeCSV`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/obstacle_dispersion.py#L430)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `columns` | `tuple[str, ...]` | `required` |
| `units` | `tuple[str, ...]` | `required` |
| `values` | `np.ndarray` | `required` |


## Maintaining this guide / 갱신

Curated purposes and entry selection live in `scripts/readme_module_guide.py`. Run `python scripts/readme_module_guide.py` to regenerate both README blocks and this file. Run `python scripts/readme_module_guide.py --check` to reject stale output, unresolved callables or missing catalog IDs. The script parses source with the standard library, imports no physical engine and runs no calculation. Review purpose/units/limits against domain manuals when an API changes. It preserves authored scientific attribution and performs no automatic translation of external material.
