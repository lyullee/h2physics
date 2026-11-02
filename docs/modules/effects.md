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

- [고정 질량 이상 압력 이력에서 내용물 열유입 역산 / Contents heat inferred from fixed-mass two-phase pressure history](#module-h2physics-adapters-pifira_heat-pifiraclosedvesselheat-run)
- [결함·재료·압력 이력에 따른 조건부 파손 개시 / Conditional flaw/material pressure-path failure initiation](#module-h2physics-adapters-vessel_failure-helprvesselfailure-predict)
- [초기 상태가 주어진 파편의 궤적·충돌 / Conditional fragment flight from supplied launch state](#module-h2physics-fragment_trajectory-integrate_fragment_flight)
- [탄성 저장 에너지로 계산한 지정 파편 속도 상한 / Elastic strain-energy ceiling on a chosen fragment mass](#module-h2physics-fragment_energy_bound-bound_fragment_speed_from_elastic_energy)
- [지정 입사 열 노출에 대한 조건부 반응 / Conditional response to supplied incident thermal exposure](#module-h2physics-adapters-hyram_exposure-hyramexposure-thermal_response)
- [지정 압력 피크·충격량에 대한 조건부 반응 / Conditional response to supplied pressure peak/impulse](#module-h2physics-adapters-hyram_exposure-hyramexposure-pressure_response)
- [외부 균질 산소 이동·농도 응답 / Native homogeneous oxygen transport and criterion evaluation](#module-h2physics-adapters-oxygen_deficiency-canteraoxygenroom-run)
- [별도 선택한 일반 공기 조건 인체 열응답 / Separately selected ordinary-air human thermal response](#module-h2physics-adapters-jos3_thermal-jos3thermalresponse-run)

<a id="module-h2physics-adapters-pifira_heat-pifiraclosedvesselheat-run"></a>

## 고정 질량 이상 압력 이력에서 내용물 열유입 역산 / Contents heat inferred from fixed-mass two-phase pressure history

Family / navigation ID: `effects.heat_input`

Import module: `h2physics.adapters.pifira_heat`; selected entry: `PifiraClosedVesselHeat.run`.

#### `h2physics.adapters.pifira_heat.PifiraClosedVesselHeat`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/pifira_heat.py#L117)

Fixed-mass/volume equilibrium contents U change through actual native APIs.

Pressure is absolute SI. The native gauge zero is only a reversible API unit
conversion; it is never an inferred measured atmosphere. No wall storage,
external work, inlet/outlet or spin-conversion energy is inferred.

```python
PifiraClosedVesselHeat(native_module, native_tank, properties, *, evidence: ClosedHeatEvidence, domain: ClosedHeatDomain)
```

#### `h2physics.adapters.pifira_heat.PifiraClosedVesselHeat.run`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/pifira_heat.py#L164)

```python
run(self, pressure: TimeSeries, channel: str, *, mass_kg: float, mass_evidence_id: str) -> ContentsHeatTrace
```

### Returned value / 반환값

`ContentsHeatTrace`

### Related input/return records / 관련 입력·반환 객체

#### `h2physics.adapters.pifira_heat.ClosedHeatEvidence`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/pifira_heat.py#L54)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `source_id` | `str` | `required` |
| `constant_mass_evidence_id` | `str` | `required` |
| `rigid_volume_evidence_id` | `str` | `required` |
| `phase_equilibrium_evidence_id` | `str` | `required` |
| `energy_scope_id` | `str` | `required` |
| `origin` | `Origin` | `required` |

#### `h2physics.adapters.pifira_heat.ClosedHeatDomain`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/pifira_heat.py#L73)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `minimum_pressure_pa` | `float` | `required` |
| `maximum_pressure_pa` | `float` | `required` |
| `minimum_quality` | `float` | `1e-08` |
| `maximum_quality` | `float` | `1.0 - 1e-08` |
| `absolute_energy_tolerance_j` | `float` | `0.0001` |
| `relative_energy_tolerance` | `float` | `1e-08` |

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

#### `h2physics.adapters.pifira_heat.ContentsHeatTrace`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/pifira_heat.py#L92)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `native_module` | `object` | `required` |
| `native_tank` | `object` | `required` |
| `properties` | `object` | `required` |
| `evidence` | `ClosedHeatEvidence` | `required` |
| `pressure_history` | `TimeSeries` | `required` |
| `pressure_channel` | `str` | `required` |
| `mass_kg` | `float` | `required` |
| `mass_evidence_id` | `str` | `required` |
| `states` | `tuple[ThermoState, ...]` | `required` |
| `native_energy_j` | `np.ndarray` | `required` |
| `native_minus_eos_energy_j` | `np.ndarray` | `required` |
| `interval_heat_w` | `np.ndarray` | `required` |
| `interval_energy_residual_j` | `np.ndarray` | `required` |
| `native_gauge_zero_pa` | `float` | `required` |
| `interpretation` | `str` | `'signed-fluid-internal-energy-increase; wall/fire/other-energy scope separate'` |

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


<a id="module-h2physics-adapters-vessel_failure-helprvesselfailure-predict"></a>

## 결함·재료·압력 이력에 따른 조건부 파손 개시 / Conditional flaw/material pressure-path failure initiation

Family / navigation ID: `effects.rupture`

Import module: `h2physics.adapters.vessel_failure`; selected entry: `HelprVesselFailure.predict`.

#### `h2physics.adapters.vessel_failure.HelprVesselFailure`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/vessel_failure.py#L452)

Actual native static mechanics plus caller-evidenced thermal material law.

``native_2016_fad`` calls HELPR's existing curve without copying its equation.
``separate_yield_and_toughness`` uses the actual native dimensionless ratios.
Both retain caller-supplied load-ratio cutoff; neither claims full API579 FFS.

```python
HelprVesselFailure(geometry: HelprAxialFlaw, material_law: VesselMaterialLaw, *, criterion: str, criterion_evidence_id: str, native_stress_factory=None)
```

#### `h2physics.adapters.vessel_failure.HelprVesselFailure.predict`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/vessel_failure.py#L697)

```python
predict(self, history: VesselFailureHistory, *, maximum_reconstruction_step_s: float, root_time_tolerance_s: float=1e-07, maximum_evaluations: int=10000)
```

The source has no explicit return annotation; inspect its return statements and the domain manual. No return type is invented by this generator.

### Returned value / 반환값

`VesselFailurePrediction`

This return contract was reviewed from the implementation; it is not an annotation present in the source signature.

### Related input/return records / 관련 입력·반환 객체

#### `h2physics.adapters.vessel_failure.VesselFailurePrediction`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/vessel_failure.py#L364)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `history` | `VesselFailureHistory` | `required` |
| `geometry` | `HelprAxialFlaw` | `required` |
| `material_law` | `VesselMaterialLaw` | `required` |
| `criterion` | `str` | `required` |
| `criterion_evidence_id` | `str` | `required` |
| `evaluations` | `tuple[VesselFailureEvaluation, ...]` | `required` |
| `initiation` | `VesselFailureEvaluation &#124; None` | `required` |
| `resolved_bracket_s` | `tuple[float, float] &#124; None` | `required` |
| `native_root_result` | `object &#124; None` | `required` |
| `maximum_reconstruction_step_s` | `float` | `required` |
| `root_time_tolerance_s` | `float` | `required` |
| `maximum_evaluations` | `int` | `required` |
| `source_sha256` | `Mapping` | `required` |
| `input_sha256` | `str` | `required` |
| `termination` | `str` | `required` |
| `software_status` | `str` | `'implemented_unverified'` |

#### `h2physics.adapters.vessel_failure.HelprAxialFlaw`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/vessel_failure.py#L226)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `outer_diameter_m` | `float` | `required` |
| `wall_thickness_m` | `float` | `required` |
| `flaw_depth_m` | `float` | `required` |
| `flaw_length_m` | `float` | `required` |
| `location_factor` | `float` | `required` |
| `geometry_id` | `str` | `required` |
| `defect_id` | `str` | `required` |
| `evidence_id` | `str` | `required` |

#### `h2physics.adapters.vessel_failure.VesselMaterialLaw`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/vessel_failure.py#L269)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `material_id` | `str` | `required` |
| `law_id` | `str` | `required` |
| `evidence_id` | `str` | `required` |
| `wall_temperature_k` | `tuple[float, float]` | `required` |
| `internal_pressure_pa_absolute` | `tuple[float, float]` | `required` |
| `hydrogen_mole_fraction` | `tuple[float, float]` | `required` |
| `response` | `Callable[[VesselLoading, VesselFailureContext], VesselMaterialPoint]` | `required` |
| `origin` | `Origin` | `required` |

#### `h2physics.adapters.vessel_failure.VesselFailureHistory`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/vessel_failure.py#L178)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `context` | `VesselFailureContext` | `required` |
| `samples` | `tuple[VesselLoading, ...]` | `required` |
| `reconstruction_evidence_id` | `str` | `required` |
| `native_trace` | `object &#124; None` | `None` |

#### `h2physics.adapters.vessel_failure.VesselFailureContext`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/vessel_failure.py#L115)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `vessel_id` | `str` | `required` |
| `wall_region_id` | `str` | `required` |
| `frame_id` | `str` | `required` |
| `clock_id` | `str` | `required` |
| `source_id` | `str` | `required` |
| `fluid_basis` | `PropertyBasis` | `required` |
| `hydrogen_mole_fraction` | `float` | `required` |
| `hydrogen_service_evidence_id` | `str` | `required` |
| `wall_temperature_evidence_id` | `str` | `required` |
| `geometry_binding_evidence_id` | `str` | `required` |
| `origin` | `Origin` | `required` |

#### `h2physics.adapters.vessel_failure.VesselLoading`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/vessel_failure.py#L147)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `time_s` | `float` | `required` |
| `internal_pressure_pa_absolute` | `float` | `required` |
| `external_pressure_pa_absolute` | `float` | `required` |
| `wall_temperature_k` | `float` | `required` |
| `phase_id` | `str` | `required` |
| `native_snapshot` | `object &#124; None` | `None` |
| `native_state` | `object &#124; None` | `None` |
| `native_fluid` | `object &#124; None` | `None` |
| `reconstruction_parents` | `tuple` | `()` |

Computed properties: `pressure_difference_pa`.

#### `h2physics.adapters.vessel_failure.VesselMaterialPoint`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/vessel_failure.py#L256)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `yield_strength_pa` | `float` | `required` |
| `fracture_resistance_pa_sqrt_m` | `float` | `required` |
| `maximum_load_ratio` | `float` | `required` |
| `evidence_id` | `str` | `required` |

#### `h2physics.adapters.vessel_failure.VesselFailureEvaluation`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/vessel_failure.py#L344)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `loading` | `VesselLoading` | `required` |
| `material_point` | `VesselMaterialPoint` | `required` |
| `native` | `NativeVesselObjects` | `required` |
| `raw_stress_intensity` | `object` | `required` |
| `raw_reference_stress` | `object` | `required` |
| `raw_ratios` | `object` | `required` |
| `raw_fad_limit` | `object &#124; None` | `required` |
| `k_max_pa_sqrt_m` | `float` | `required` |
| `reference_stress_pa` | `float` | `required` |
| `toughness_ratio` | `float` | `required` |
| `load_ratio` | `float` | `required` |
| `fad_limit` | `float &#124; None` | `required` |
| `margin` | `float` | `required` |
| `failed` | `bool` | `required` |
| `governing_criterion` | `str` | `required` |
| `purpose` | `str` | `required` |


<a id="module-h2physics-fragment_trajectory-integrate_fragment_flight"></a>

## 초기 상태가 주어진 파편의 궤적·충돌 / Conditional fragment flight from supplied launch state

Family / navigation ID: `effects.fragment_trajectory`

Import module: `h2physics.fragment_trajectory`; selected entry: `integrate_fragment_flight`.

#### `h2physics.fragment_trajectory.integrate_fragment_flight`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/fragment_trajectory.py#L303)

Integrate a caller-defined fragment until ground impact or time horizon.

Drag uses ``-0.5*rho*Cd*A*|v-w|*(v-w)``. Density depends on height and
wind may vary with position and time. No default atmospheric or launch model
is inferred. The augmented state integrates aerodynamic impulse and work for
independent momentum and mechanical-energy checks.

```python
integrate_fragment_flight(launch: FragmentLaunch, environment: FragmentFlightEnvironment, settings: FragmentFlightSettings) -> FragmentFlightResult
```

### Returned value / 반환값

`FragmentFlightResult`

### Related input/return records / 관련 입력·반환 객체

#### `h2physics.fragment_trajectory.FragmentLaunch`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/fragment_trajectory.py#L30)

Caller-supplied rigid fragment mass, geometry and initial kinematics.

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `fragment_id` | `str` | `required` |
| `mass_kg` | `float` | `required` |
| `reference_area_m2` | `float` | `required` |
| `drag_coefficient` | `float` | `required` |
| `position_m` | `np.ndarray` | `required` |
| `velocity_m_s` | `np.ndarray` | `required` |
| `ground_z_m` | `float` | `required` |
| `frame_id` | `str` | `required` |
| `evidence_id` | `str` | `required` |

#### `h2physics.fragment_trajectory.FragmentFlightEnvironment`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/fragment_trajectory.py#L147)

Explicit callback owners for air density, wind and gravity.

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `density_kg_m3` | `Callable[[float], float]` | `required` |
| `wind_velocity_m_s` | `Callable[[np.ndarray, float], np.ndarray]` | `required` |
| `gravity_m_s2` | `np.ndarray` | `required` |
| `frame_id` | `str` | `required` |
| `evidence_id` | `str` | `required` |
| `density_evidence_id` | `str` | `required` |
| `wind_evidence_id` | `str` | `required` |

#### `h2physics.fragment_trajectory.FragmentFlightSettings`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/fragment_trajectory.py#L171)

Integrator controls and accepted output clock for one flight.

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `clock_id` | `str` | `required` |
| `time_s` | `np.ndarray` | `required` |
| `relative_tolerance` | `float` | `1e-08` |
| `absolute_tolerance` | `float` | `1e-10` |
| `maximum_step_s` | `float` | `0.02` |
| `momentum_tolerance_kg_m_s` | `float` | `1e-06` |
| `mechanical_energy_tolerance_j` | `float` | `1e-05` |

#### `h2physics.fragment_trajectory.FragmentFlightResult`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/fragment_trajectory.py#L196)

Trajectory, impact event and independent force/energy residuals.

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `launch` | `FragmentLaunch` | `required` |
| `environment` | `FragmentFlightEnvironment` | `required` |
| `settings` | `FragmentFlightSettings` | `required` |
| `time_s` | `np.ndarray` | `required` |
| `position_m` | `np.ndarray` | `required` |
| `velocity_m_s` | `np.ndarray` | `required` |
| `impact_time_s` | `float &#124; None` | `required` |
| `impact_position_m` | `np.ndarray &#124; None` | `required` |
| `impact_velocity_m_s` | `np.ndarray &#124; None` | `required` |
| `drag_impulse_kg_m_s` | `np.ndarray` | `required` |
| `drag_work_j` | `float` | `required` |
| `momentum_residual_kg_m_s` | `np.ndarray` | `required` |
| `mechanical_energy_residual_j` | `float` | `required` |
| `solver_message` | `str` | `required` |


<a id="module-h2physics-fragment_energy_bound-bound_fragment_speed_from_elastic_energy"></a>

## 탄성 저장 에너지로 계산한 지정 파편 속도 상한 / Elastic strain-energy ceiling on a chosen fragment mass

Family / navigation ID: `effects.fragment_trajectory`

Import module: `h2physics.fragment_energy_bound`; selected entry: `bound_fragment_speed_from_elastic_energy`.

#### `h2physics.fragment_energy_bound.bound_fragment_speed_from_elastic_energy`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/fragment_energy_bound.py#L52)

Return a one-fragment speed ceiling from differential-pressure strain energy.

The cylinder is long, uniform, isotropic, linear elastic and governed by
the existing Lamé solution. The admitted load must be a differential
pressure increment against a zero-pressure exterior. The end condition is
taken from ``geometry``. End-cap, local crack, plastic, gas-expansion and
fracture work are excluded. The caller supplies the fraction of stored
elastic energy assigned to this one fragment; it is not inferred.

```python
bound_fragment_speed_from_elastic_energy(geometry: CylinderGeometry, pressure_load: CylinderPressureLoad, *, cylinder_length_m: float, youngs_modulus_pa: float, poisson_ratio: float, fragment_mass_kg: float, fragment_energy_fraction: float, fragment_id: str, material_evidence_id: str) -> FragmentElasticEnergyBound
```

### Returned value / 반환값

`FragmentElasticEnergyBound`

### Related input/return records / 관련 입력·반환 객체

#### `h2physics.materials.elastic_cylinder.CylinderGeometry`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/materials/elastic_cylinder.py#L17)

Uniform hollow-cylinder dimensions in SI units.

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `inner_radius_m` | `float` | `required` |
| `outer_radius_m` | `float` | `required` |
| `end_condition` | `str` | `required` |
| `geometry_id` | `str` | `required` |

#### `h2physics.materials.elastic_cylinder.CylinderPressureLoad`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/materials/elastic_cylinder.py#L37)

Uniform absolute pressures on the inner and outer cylinder surfaces.

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `internal_pressure_pa` | `float` | `required` |
| `external_pressure_pa` | `float` | `required` |
| `load_id` | `str` | `required` |
| `origin` | `Origin` | `required` |

#### `h2physics.fragment_energy_bound.FragmentElasticEnergyBound`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/fragment_energy_bound.py#L15)

Energy and speed ceiling for an explicitly selected fragment mass.

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `geometry_id` | `str` | `required` |
| `pressure_load_id` | `str` | `required` |
| `material_evidence_id` | `str` | `required` |
| `fragment_id` | `str` | `required` |
| `elastic_strain_energy_j` | `float` | `required` |
| `fragment_energy_fraction` | `float` | `required` |
| `available_fragment_energy_j` | `float` | `required` |
| `fragment_mass_kg` | `float` | `required` |
| `maximum_speed_m_s` | `float` | `required` |


<a id="module-h2physics-adapters-hyram_exposure-hyramexposure-thermal_response"></a>

## 지정 입사 열 노출에 대한 조건부 반응 / Conditional response to supplied incident thermal exposure

Family / navigation ID: `effects.exposure`

Import module: `h2physics.adapters.hyram_exposure`; selected entry: `HyRAMExposure.thermal_response`.

#### `h2physics.adapters.hyram_exposure.HyRAMExposure`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/hyram_exposure.py#L403)

Actual separately installed HyRAM6.1; no model or probability defaults.

```python
HyRAMExposure(native_probits=None, *, quadrature_relative_tolerance=1e-09)
```

#### `h2physics.adapters.hyram_exposure.HyRAMExposure.thermal_response`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/hyram_exposure.py#L447)

```python
thermal_response(self, history: ExposureHistory, selection: NativeHarmSelection, *, additivity_evidence_id: str)
```

The source has no explicit return annotation; inspect its return statements and the domain manual. No return type is invented by this generator.

### Returned value / 반환값

`ExposureResult`

This return contract was reviewed from the implementation; it is not an annotation present in the source signature.

### Related input/return records / 관련 입력·반환 객체

#### `h2physics.adapters.hyram_exposure.ExposureResult`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/hyram_exposure.py#L306)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `input` | `Any` | `required` |
| `selection` | `NativeHarmSelection &#124; None` | `required` |
| `assumption_evidence_id` | `str` | `required` |
| `thermal_dose` | `float &#124; None` | `required` |
| `fluence_j_m2` | `float &#124; None` | `required` |
| `peak_overpressure_pa` | `float &#124; None` | `required` |
| `positive_impulse_pa_s` | `float &#124; None` | `required` |
| `probability` | `float &#124; None` | `required` |
| `native_probit` | `Any` | `required` |
| `native_result` | `Any` | `required` |
| `native_module` | `Any` | `required` |
| `native_calls` | `tuple[NativeExposureCall, ...]` | `required` |
| `quadrature_records` | `tuple` | `required` |
| `native_source_sha256` | `str` | `required` |
| `input_sha256` | `str` | `required` |
| `quadrature_relative_tolerance` | `float` | `required` |
| `evaluation_kind` | `str` | `required` |
| `evaluation_sha256` | `str` | `required` |
| `status` | `str` | `'conditional-on-supplied-exposure'` |

Computed properties: `receptor_id`, `frame_id`, `clock_id`, `support_s`, `source_id`, `model_id`, `evidence_id`.

#### `h2physics.adapters.hyram_exposure.ExposureHistory`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/hyram_exposure.py#L62)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `receptor` | `ExposureReceptor` | `required` |
| `time_s` | `np.ndarray` | `required` |
| `values` | `np.ndarray` | `required` |
| `quantity` | `str` | `required` |
| `unit` | `str` | `required` |
| `interpolation` | `str` | `required` |
| `clock_id` | `str` | `required` |
| `source_id` | `str` | `required` |
| `basis_id` | `str` | `required` |
| `origin` | `Origin` | `required` |
| `valid` | `np.ndarray &#124; None` | `None` |
| `input_evidence_ids` | `tuple[str, ...]` | `()` |

Computed properties: `support_s`, `content_sha256`.

#### `h2physics.adapters.hyram_exposure.NativeHarmSelection`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/hyram_exposure.py#L284)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `model_id` | `str` | `required` |
| `normal_distribution_mean` | `float` | `required` |
| `evidence_id` | `str` | `required` |
| `applicability_id` | `str` | `required` |
| `origin` | `Origin` | `required` |

#### `h2physics.adapters.hyram_exposure.ExposureReceptor`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/hyram_exposure.py#L45)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `receptor_id` | `str` | `required` |
| `frame_id` | `str` | `required` |
| `position_m` | `tuple[float, float, float]` | `required` |
| `input_basis_id` | `str` | `required` |

#### `h2physics.adapters.hyram_exposure.NativeExposureCall`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/hyram_exposure.py#L298)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `function` | `Any` | `required` |
| `args` | `tuple` | `required` |
| `kwargs` | `Any` | `required` |
| `raw` | `Any` | `required` |


<a id="module-h2physics-adapters-hyram_exposure-hyramexposure-pressure_response"></a>

## 지정 압력 피크·충격량에 대한 조건부 반응 / Conditional response to supplied pressure peak/impulse

Family / navigation ID: `effects.exposure`

Import module: `h2physics.adapters.hyram_exposure`; selected entry: `HyRAMExposure.pressure_response`.

#### `h2physics.adapters.hyram_exposure.HyRAMExposure`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/hyram_exposure.py#L403)

Actual separately installed HyRAM6.1; no model or probability defaults.

```python
HyRAMExposure(native_probits=None, *, quadrature_relative_tolerance=1e-09)
```

#### `h2physics.adapters.hyram_exposure.HyRAMExposure.pressure_response`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/hyram_exposure.py#L450)

```python
pressure_response(self, input: ExposureHistory | PressurePeak, selection: NativeHarmSelection, *, positive_phase_evidence_id: str)
```

The source has no explicit return annotation; inspect its return statements and the domain manual. No return type is invented by this generator.

### Returned value / 반환값

`ExposureResult`

This return contract was reviewed from the implementation; it is not an annotation present in the source signature.

### Related input/return records / 관련 입력·반환 객체

#### `h2physics.adapters.hyram_exposure.ExposureResult`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/hyram_exposure.py#L306)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `input` | `Any` | `required` |
| `selection` | `NativeHarmSelection &#124; None` | `required` |
| `assumption_evidence_id` | `str` | `required` |
| `thermal_dose` | `float &#124; None` | `required` |
| `fluence_j_m2` | `float &#124; None` | `required` |
| `peak_overpressure_pa` | `float &#124; None` | `required` |
| `positive_impulse_pa_s` | `float &#124; None` | `required` |
| `probability` | `float &#124; None` | `required` |
| `native_probit` | `Any` | `required` |
| `native_result` | `Any` | `required` |
| `native_module` | `Any` | `required` |
| `native_calls` | `tuple[NativeExposureCall, ...]` | `required` |
| `quadrature_records` | `tuple` | `required` |
| `native_source_sha256` | `str` | `required` |
| `input_sha256` | `str` | `required` |
| `quadrature_relative_tolerance` | `float` | `required` |
| `evaluation_kind` | `str` | `required` |
| `evaluation_sha256` | `str` | `required` |
| `status` | `str` | `'conditional-on-supplied-exposure'` |

Computed properties: `receptor_id`, `frame_id`, `clock_id`, `support_s`, `source_id`, `model_id`, `evidence_id`.

#### `h2physics.adapters.hyram_exposure.ExposureHistory`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/hyram_exposure.py#L62)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `receptor` | `ExposureReceptor` | `required` |
| `time_s` | `np.ndarray` | `required` |
| `values` | `np.ndarray` | `required` |
| `quantity` | `str` | `required` |
| `unit` | `str` | `required` |
| `interpolation` | `str` | `required` |
| `clock_id` | `str` | `required` |
| `source_id` | `str` | `required` |
| `basis_id` | `str` | `required` |
| `origin` | `Origin` | `required` |
| `valid` | `np.ndarray &#124; None` | `None` |
| `input_evidence_ids` | `tuple[str, ...]` | `()` |

Computed properties: `support_s`, `content_sha256`.

#### `h2physics.adapters.hyram_exposure.PressurePeak`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/hyram_exposure.py#L161)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `receptor` | `ExposureReceptor` | `required` |
| `overpressure_pa` | `float` | `required` |
| `positive_impulse_pa_s` | `float &#124; None` | `required` |
| `clock_id` | `str` | `required` |
| `support_s` | `tuple[float, float]` | `required` |
| `source_id` | `str` | `required` |
| `basis_id` | `str` | `required` |
| `origin` | `Origin` | `required` |
| `input_evidence_ids` | `tuple[str, ...]` | `()` |

Computed properties: `content_sha256`.

#### `h2physics.adapters.hyram_exposure.NativeHarmSelection`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/hyram_exposure.py#L284)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `model_id` | `str` | `required` |
| `normal_distribution_mean` | `float` | `required` |
| `evidence_id` | `str` | `required` |
| `applicability_id` | `str` | `required` |
| `origin` | `Origin` | `required` |

#### `h2physics.adapters.hyram_exposure.ExposureReceptor`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/hyram_exposure.py#L45)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `receptor_id` | `str` | `required` |
| `frame_id` | `str` | `required` |
| `position_m` | `tuple[float, float, float]` | `required` |
| `input_basis_id` | `str` | `required` |

#### `h2physics.adapters.hyram_exposure.NativeExposureCall`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/hyram_exposure.py#L298)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `function` | `Any` | `required` |
| `args` | `tuple` | `required` |
| `kwargs` | `Any` | `required` |
| `raw` | `Any` | `required` |


<a id="module-h2physics-adapters-oxygen_deficiency-canteraoxygenroom-run"></a>

## 외부 균질 산소 이동·농도 응답 / Native homogeneous oxygen transport and criterion evaluation

Family / navigation ID: `effects.cryogenic`

Import module: `h2physics.adapters.oxygen_deficiency`; selected entry: `CanteraOxygenRoom.run`.

#### `h2physics.adapters.oxygen_deficiency.CanteraOxygenRoom`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/oxygen_deficiency.py#L281)

Partition interval commands; delegate every physical step to the shared owner.

MassFlowControllers are prescribed transfers, including fan/pump work upstream
of the specified enthalpy boundary. No passive pressure-flow relation or
pressure-independent ventilation efficiency is inferred. Supply a GasVent
callback using the shared nozzle when a pressure-driven outlet is intended.

```python
CanteraOxygenRoom(phase_factory, mechanism_basis: MechanismBasis, region: OxygenRoomRegion)
```

#### `h2physics.adapters.oxygen_deficiency.CanteraOxygenRoom.run`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/oxygen_deficiency.py#L301)

```python
run(self, initial: ReactiveState, time_s, *, feeds=(), exhausts=(), heat_boundaries=(), event_times_s=(), settings=OxygenRoomSettings())
```

The source has no explicit return annotation; inspect its return statements and the domain manual. No return type is invented by this generator.

### Returned value / 반환값

`OxygenRoomResult`

This return contract was reviewed from the implementation; it is not an annotation present in the source signature.

### Related input/return records / 관련 입력·반환 객체

#### `h2physics.adapters.oxygen_deficiency.OxygenRoomResult`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/oxygen_deficiency.py#L202)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `region` | `OxygenRoomRegion` | `required` |
| `mechanism_basis` | `MechanismBasis` | `required` |
| `settings` | `OxygenRoomSettings` | `required` |
| `feeds` | `tuple[OxygenFeedAdmission, ...]` | `required` |
| `exhausts` | `tuple[GasVent, ...]` | `required` |
| `heat_boundaries` | `tuple[GasHeatBoundary, ...]` | `required` |
| `native_traces` | `tuple` | `required` |
| `admission_native_phases` | `tuple` | `required` |
| `source_sha256` | `tuple[str, ...]` | `required` |
| `source_definition_sha256` | `str` | `required` |
| `requested_time_s` | `np.ndarray` | `required` |
| `time_s` | `np.ndarray` | `required` |
| `snapshots` | `tuple` | `required` |
| `ledger_names` | `tuple[str, ...]` | `required` |
| `boundary_integrals` | `np.ndarray` | `required` |
| `species_names` | `tuple[str, ...]` | `required` |
| `species_inventory_kg` | `np.ndarray` | `required` |
| `oxygen_inventory_kg` | `np.ndarray` | `required` |
| `oxygen_inventory_mol` | `np.ndarray` | `required` |
| `wet_oxygen_mole_fraction` | `np.ndarray` | `required` |
| `dry_oxygen_mole_fraction` | `np.ndarray` | `required` |
| `dry_fraction_valid` | `np.ndarray` | `required` |
| `oxygen_partial_pressure_pa` | `np.ndarray` | `required` |
| `mass_residual_kg` | `np.ndarray` | `required` |
| `species_residual_kg` | `np.ndarray` | `required` |
| `energy_residual_j` | `np.ndarray` | `required` |
| `pressure_identity_residual_pa` | `np.ndarray` | `required` |
| `source_mass_residual_kg` | `np.ndarray` | `required` |
| `source_enthalpy_residual_j` | `np.ndarray` | `required` |
| `probability` | `None` | `None` |
| `status` | `str` | `'finite-homogeneous-oxygen-inventory;no-human-response-law'` |

Computed properties: `native`.

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

#### `h2physics.adapters.oxygen_deficiency.OxygenRoomRegion`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/oxygen_deficiency.py#L99)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `region_id` | `str` | `required` |
| `receptor_id` | `str` | `required` |
| `frame_id` | `str` | `required` |
| `clock_id` | `str` | `required` |
| `position_m` | `tuple[float, float, float]` | `required` |
| `elevation_m` | `float` | `required` |
| `volume_m3` | `float` | `required` |
| `mixing_evidence_id` | `str` | `required` |
| `single_gas_evidence_id` | `str` | `required` |
| `prescribed_transfer_evidence_id` | `str` | `required` |
| `origin` | `Origin` | `required` |

#### `h2physics.adapters.cantera.ReactiveState`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/cantera.py#L51)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `temperature_k` | `float` | `required` |
| `pressure_pa` | `float` | `required` |
| `mole_fractions` | `Mapping[str, float]` | `required` |

#### `h2physics.adapters.oxygen_deficiency.OxygenRoomSettings`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/oxygen_deficiency.py#L157)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `maximum_time_step_s` | `float` | `0.1` |
| `relative_tolerance` | `float` | `1e-10` |
| `absolute_tolerance` | `float` | `1e-14` |
| `minimum_inventory_kg` | `float` | `1e-09` |
| `mass_absolute_budget_kg` | `float` | `1e-09` |
| `energy_absolute_budget_j` | `float` | `0.001` |
| `pressure_absolute_budget_pa` | `float` | `1e-05` |
| `relative_audit_budget` | `float` | `1e-08` |

#### `h2physics.adapters.oxygen_deficiency.OxygenFeedAdmission`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/oxygen_deficiency.py#L134)

A real interval source with exactly the native formation/spin reference.

The native properties object remains available. No enthalpy offset or cold
source warming is inferred. Zero outside support needs explicit evidence;
a window_end source cannot be extrapolated after its unobserved endpoint.

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `source` | `IntervalMassSource` | `required` |
| `properties` | `CanteraFrozenGasProperties` | `required` |
| `admission_evidence_id` | `str` | `required` |
| `outside_support_evidence_id` | `str &#124; None` | `None` |

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


<a id="module-h2physics-adapters-jos3_thermal-jos3thermalresponse-run"></a>

## 별도 선택한 일반 공기 조건 인체 열응답 / Separately selected ordinary-air human thermal response

Family / navigation ID: `effects.cryogenic`

Import module: `h2physics.adapters.jos3_thermal`; selected entry: `JOS3ThermalResponse.run`.

#### `h2physics.adapters.jos3_thermal.JOS3ThermalResponse`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/jos3_thermal.py#L327)

```python
JOS3ThermalResponse(native: NativeJOS3, domain: ThermalDomain)
```

#### `h2physics.adapters.jos3_thermal.JOS3ThermalResponse.run`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/jos3_thermal.py#L333)

```python
run(self, source_model, intervals, *, evidence: ThermalRunEvidence)
```

The source has no explicit return annotation; inspect its return statements and the domain manual. No return type is invented by this generator.

### Returned value / 반환값

`ThermalResponse`

This return contract was reviewed from the implementation; it is not an annotation present in the source signature.

### Related input/return records / 관련 입력·반환 객체

#### `h2physics.adapters.jos3_thermal.ThermalResponse`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/jos3_thermal.py#L226)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `source_model` | `object` | `required` |
| `native_model` | `object` | `required` |
| `native_initial_history` | `tuple` | `required` |
| `native_outputs` | `tuple` | `required` |
| `steps` | `tuple[ThermalStep, ...]` | `required` |
| `evidence` | `ThermalRunEvidence` | `required` |
| `intervals` | `tuple[ThermalInterval, ...]` | `required` |
| `initial_body_temperature_k` | `np.ndarray` | `required` |
| `capacity_j_k` | `np.ndarray` | `required` |
| `source_model_sha256` | `str` | `required` |
| `input_sha256` | `str` | `required` |
| `native_source_sha256` | `str` | `required` |
| `body_part_names` | `tuple[str, ...]` | `required` |
| `node_index_map` | `tuple[tuple[str, str, int], ...]` | `required` |
| `native_global_shivering_before_w` | `float` | `required` |
| `native_global_shivering_after_w` | `float` | `required` |
| `native_global_memory_isolated` | `bool` | `False` |
| `status` | `str` | `'conditional-ordinary-air-thermal-state'` |
| `injury_probability` | `None` | `None` |
| `full_cryogenic_chain_validated` | `bool` | `False` |

#### `h2physics.adapters.jos3_thermal.ThermalDomain`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/jos3_thermal.py#L188)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `minimum_environment_k` | `float` | `required` |
| `maximum_environment_k` | `float` | `required` |
| `minimum_body_k` | `float` | `required` |
| `maximum_body_k` | `float` | `required` |
| `maximum_step_s` | `float` | `required` |
| `numerical_energy_budget_j` | `float` | `required` |

#### `h2physics.adapters.jos3_thermal.ThermalRunEvidence`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/jos3_thermal.py#L159)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `clock_id` | `str` | `required` |
| `frame_id` | `str` | `required` |
| `receptor_id` | `str` | `required` |
| `position_m` | `tuple[float, float, float]` | `required` |
| `source_id` | `str` | `required` |
| `subject_evidence_id` | `str` | `required` |
| `initialization_evidence_id` | `str` | `required` |
| `applicability_evidence_id` | `str` | `required` |
| `medium` | `str` | `required` |
| `reference_pressure_pa` | `float` | `required` |
| `origin` | `Origin` | `required` |

#### `h2physics.adapters.jos3_thermal.ThermalStep`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/jos3_thermal.py#L210)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `start_s` | `float` | `required` |
| `end_s` | `float` | `required` |
| `body_temperature_k` | `np.ndarray` | `required` |
| `skin_temperature_k` | `np.ndarray` | `required` |
| `core_temperature_k` | `np.ndarray` | `required` |
| `stored_energy_change_j` | `float` | `required` |
| `net_boundary_energy_j` | `float` | `required` |
| `energy_defect_j` | `float` | `required` |
| `output_rounding_budget_j` | `float` | `required` |
| `implicit_sensible_out_w` | `float` | `required` |
| `reported_previous_state_sensible_out_w` | `float` | `required` |
| `native_output` | `object` | `required` |

#### `h2physics.adapters.jos3_thermal.ThermalInterval`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/jos3_thermal.py#L143)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `start_s` | `float` | `required` |
| `end_s` | `float` | `required` |
| `environment` | `OrdinaryAirEnvironment` | `required` |


## Maintaining this guide / 갱신

Curated purposes and entry selection live in `scripts/readme_module_guide.py`. Run `python scripts/readme_module_guide.py` to regenerate both README blocks and this file. Run `python scripts/readme_module_guide.py --check` to reject stale output, unresolved callables or missing catalog IDs. The script parses source with the standard library, imports no physical engine and runs no calculation. Review purpose/units/limits against domain manuals when an API changes. It preserves authored scientific attribution and performs no automatic translation of external material.
