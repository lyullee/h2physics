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

- [유한 탱크·펌프·배관·기화기·출구를 조립 / Compose finite tank, pump, line, vaporizer and outlet](#module-h2physics-adapters-lh2dt_supply-assemble_lh2dt_supply)
- [동일 물리 운전 사례에 지정 보호·차단 조치 적용 / Execute prescribed protection against the same physical operation](#module-h2physics-adapters-facility_protection-execute_protected)
- [빈도·피해 근거를 입력한 조건부 분기 위험도 / Conditional branch risk with supplied frequency and harm evidence](#module-h2physics-adapters-conditional_risk-conditional_risk)
- [농도 센서 1차 지연 응답 / First-order concentration sensor response](#module-h2physics-adapters-gas_detection-evaluate_first_order_concentration_sensor)
- [같은 시간축의 k-of-n 농도 경보 투표 / Same-clock k-of-n alarm voting](#module-h2physics-adapters-gas_detection-evaluate_concentration_alarm_voting)
- [외부 인과적 PCA 잔차 감시 / Native causal PCA residual monitoring](#module-h2physics-adapters-process_monitoring-nativeresidualmonitor-evaluate)
- [사용자 확률에 따른 k-of-n 검출 실패 집계 / Caller-probability k-of-n detector fail-to-alarm aggregation](#module-h2physics-detector_reliability-evaluate_kofn_detector_reliability)

<a id="module-h2physics-adapters-lh2dt_supply-assemble_lh2dt_supply"></a>

## 유한 탱크·펌프·배관·기화기·출구를 조립 / Compose finite tank, pump, line, vaporizer and outlet

Family / navigation ID: `facility.network`

Import module: `h2physics.adapters.lh2dt_supply`; selected entry: `assemble_lh2dt_supply`.

#### `h2physics.adapters.lh2dt_supply.assemble_lh2dt_supply`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/lh2dt_supply.py#L39)

Build one explicit liquid-port topology from injected native instances.

Required power-reader keys are running_pump, isolated_pump, restriction,
outlet. The isolated branch is caller-selected and is not a rotor model.
For arbitrary topologies use Lh2dtEquipmentNetwork directly.

```python
assemble_lh2dt_supply(bridge: Lh2dtProperties, *, native_api: Any, state_factory: Callable[..., Any], tank: Any, initial_tank: Any, line: Any, initial_line: Any, vaporizer: Any, initial_vaporizer: Any, pump: Any, isolated_pump_component: Any, restriction: Any, outlet: Any, delivery_state: ThermoState, power_readers: Mapping[str, Callable[[Any], BoundaryPower]], tank_ambient_temperature_k: float | Callable[[float], float], node_ids: Mapping[str, str] | None=None) -> Lh2dtSupplyAssembly
```

### Returned value / 반환값

`Lh2dtSupplyAssembly`

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

#### `h2physics.equipment.BoundaryPower`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/equipment.py#L14)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `heat_w` | `float` | `0.0` |
| `shaft_work_w` | `float` | `0.0` |

Computed properties: `total_w`.

#### `h2physics.adapters.lh2dt_supply.Lh2dtSupplyAssembly`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/lh2dt_supply.py#L26)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `network` | `Lh2dtEquipmentNetwork` | `required` |
| `driver` | `Lh2dtDynamicEquipment` | `required` |
| `pump` | `Lh2dtModeSwitch` | `required` |
| `outlet` | `Any` | `required` |
| `node_ids` | `Mapping[str, str]` | `required` |
| `native_models` | `Mapping[str, Any]` | `required` |

#### `h2physics.core.PropertyBasis`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/core.py#L97)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `fluid` | `str` | `required` |
| `reference_id` | `str` | `required` |
| `spin_composition` | `str` | `'unspecified'` |


<a id="module-h2physics-adapters-facility_protection-execute_protected"></a>

## 동일 물리 운전 사례에 지정 보호·차단 조치 적용 / Execute prescribed protection against the same physical operation

Family / navigation ID: `facility.isolation`

Import module: `h2physics.adapters.facility_protection`; selected entry: `execute_protected`.

#### `h2physics.adapters.facility_protection.execute_protected`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/facility_protection.py#L543)

Delegate one explicit replay to the existing LH2DT driver; no new scheduler.

```python
execute_protected(driver, plans, *, duration_s, time_step_s, start_time_s, clock_id, mode_definition_id, scenario_evidence_id)
```

The source has no explicit return annotation; inspect its return statements and the domain manual. No return type is invented by this generator.

### Returned value / 반환값

`ProtectedEquipmentRun`

This return contract was reviewed from the implementation; it is not an annotation present in the source signature.

### Related input/return records / 관련 입력·반환 객체

#### `h2physics.adapters.facility_protection.ProtectedEquipmentRun`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/facility_protection.py#L479)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `native_run` | `DynamicEquipmentRun` | `required` |
| `driver` | `object` | `required` |
| `plans` | `tuple[ScheduledProtection, ...]` | `required` |
| `accepted` | `tuple[AcceptedProtection, ...]` | `required` |
| `mode_definition_id` | `str` | `required` |
| `scenario_evidence_id` | `str` | `required` |
| `interpretation` | `str` | `'prescribed replay; no online detection/actuator dynamics or reliability proof'` |

#### `h2physics.adapters.lh2dt_dynamics.DynamicEquipmentRun`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/lh2dt_dynamics.py#L103)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `clock_id` | `str` | `required` |
| `start_time_s` | `float` | `required` |
| `initial_inventories` | `Mapping[str, ConservedInventory]` | `required` |
| `initial_equipment` | `EquipmentNetworkSnapshot` | `required` |
| `steps` | `tuple[DynamicEquipmentStep, ...]` | `required` |
| `transitions` | `tuple[EquipmentCommandTransition, ...]` | `required` |

#### `h2physics.adapters.facility_protection.AcceptedProtection`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/facility_protection.py#L448)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `plan` | `ScheduledProtection` | `required` |
| `invocation` | `ActionInvocation` | `required` |
| `run` | `DynamicEquipmentRun` | `required` |
| `native_transition` | `object` | `required` |


<a id="module-h2physics-adapters-conditional_risk-conditional_risk"></a>

## 빈도·피해 근거를 입력한 조건부 분기 위험도 / Conditional branch risk with supplied frequency and harm evidence

Family / navigation ID: `facility.risk`

Import module: `h2physics.adapters.conditional_risk`; selected entry: `conditional_risk`.

#### `h2physics.adapters.conditional_risk.conditional_risk`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/conditional_risk.py#L525)

Execute native single-LOC risk with explicit finite-source/receptor bindings.

The native receipt API internally normalizes its typed input. No user JSON,
file, HTTP call or replacement risk solver is needed. The additional direct
native call retains the actual typed RiskOutput, independently cross-checked
against that native receipt rather than reconstructed from its dictionary.

```python
conditional_risk(native: ConditionalRiskNative, request, context, *, source: IntervalMassSource, receptor: RiskReceptor, harm_bindings: Mapping[str, ConditionalHarmBinding], evidence: RiskBindingEvidence) -> ConditionalRiskResult
```

### Returned value / 반환값

`ConditionalRiskResult`

### Related input/return records / 관련 입력·반환 객체

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

#### `h2physics.adapters.conditional_risk.RiskReceptor`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/conditional_risk.py#L112)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `receptor_id` | `str` | `required` |
| `frame_id` | `str` | `required` |
| `clock_id` | `str` | `required` |
| `position_m` | `tuple[float, float, float]` | `required` |
| `position_evidence_id` | `str` | `required` |
| `origin` | `Origin` | `required` |

#### `h2physics.adapters.conditional_risk.ConditionalHarmBinding`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/conditional_risk.py#L130)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `probability` | `float` | `required` |
| `receptor_id` | `str` | `required` |
| `frame_id` | `str` | `required` |
| `clock_id` | `str` | `required` |
| `support_s` | `tuple[float, float]` | `required` |
| `source_id` | `str` | `required` |
| `response_model_id` | `str` | `required` |
| `position_m` | `tuple[float, float, float]` | `required` |
| `evidence_ids` | `tuple[str, ...]` | `required` |
| `origin` | `Origin` | `required` |
| `exposure_result` | `Any` | `None` |
| `exposure_signature` | `str &#124; None` | `None` |

#### `h2physics.adapters.conditional_risk.RiskBindingEvidence`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/conditional_risk.py#L260)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `source_binding_evidence_id` | `str` | `required` |
| `source_to_harm_assumption_id` | `str` | `required` |
| `partition_evidence_id` | `str` | `required` |
| `origin` | `Origin` | `required` |

#### `h2physics.adapters.conditional_risk.ConditionalRiskResult`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/conditional_risk.py#L352)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `original_request` | `Any` | `required` |
| `original_context` | `Any` | `required` |
| `native_request` | `Any` | `required` |
| `native_context` | `Any` | `required` |
| `native_output` | `Any` | `required` |
| `native_receipt` | `Any` | `required` |
| `source` | `IntervalMassSource` | `required` |
| `source_sha256` | `str` | `required` |
| `receptor` | `RiskReceptor` | `required` |
| `harm_bindings` | `Mapping[str, ConditionalHarmBinding]` | `required` |
| `evidence` | `RiskBindingEvidence` | `required` |
| `native` | `ConditionalRiskNative` | `required` |
| `status` | `str` | `'conditional-single-LOC-on-supplied-source-harm-and-frequency'` |

Computed properties: `annual_harm_frequency_per_year`.

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


<a id="module-h2physics-adapters-gas_detection-evaluate_first_order_concentration_sensor"></a>

## 농도 센서 1차 지연 응답 / First-order concentration sensor response

Family / navigation ID: `facility.monitoring`

Import module: `h2physics.adapters.gas_detection`; selected entry: `evaluate_first_order_concentration_sensor`.

#### `h2physics.adapters.gas_detection.evaluate_first_order_concentration_sensor`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/gas_detection.py#L196)

Filter piecewise-linear true concentration with a closed-form first-order lag.

The caller supplies the complete input clock, source identity and initial
indication. The signal is assumed linear between adjacent input samples; no
sensor dead time, calibration correction, clipping, noise or missing-data fill
is applied.

```python
evaluate_first_order_concentration_sensor(config, *, time_s, true_concentration, initial_indication, source_evidence_id, operating_mode_id, episode_id, origin)
```

The source has no explicit return annotation; inspect its return statements and the domain manual. No return type is invented by this generator.

### Returned value / 반환값

`FirstOrderConcentrationSensorTrace`

This return contract was reviewed from the implementation; it is not an annotation present in the source signature.

### Related input/return records / 관련 입력·반환 객체

#### `h2physics.adapters.gas_detection.FirstOrderConcentrationSensorTrace`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/gas_detection.py#L130)

Issued first-order indication retaining the exact true input history.

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `config` | `FirstOrderConcentrationSensorConfig` | `required` |
| `time_s` | `np.ndarray` | `required` |
| `true_concentration` | `np.ndarray` | `required` |
| `indicated_concentration` | `np.ndarray` | `required` |
| `initial_indication` | `float` | `required` |
| `source_evidence_id` | `str` | `required` |
| `operating_mode_id` | `str` | `required` |
| `episode_id` | `str` | `required` |
| `origin` | `Origin` | `required` |

#### `h2physics.adapters.gas_detection.FirstOrderConcentrationSensorConfig`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/gas_detection.py#L62)

Caller-qualified first-order response on the input concentration basis.

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `sensor_id` | `str` | `required` |
| `location_id` | `str` | `required` |
| `clock_id` | `str` | `required` |
| `concentration_basis` | `str` | `required` |
| `concentration_unit` | `str` | `required` |
| `response_time_constant_s` | `float` | `required` |
| `maximum_input_sample_gap_s` | `float` | `required` |
| `sensor_evidence_id` | `str` | `required` |
| `response_parameter_evidence_id` | `str` | `required` |
| `model_evidence_id` | `str` | `required` |


<a id="module-h2physics-adapters-gas_detection-evaluate_concentration_alarm_voting"></a>

## 같은 시간축의 k-of-n 농도 경보 투표 / Same-clock k-of-n alarm voting

Family / navigation ID: `facility.monitoring`

Import module: `h2physics.adapters.gas_detection`; selected entry: `evaluate_concentration_alarm_voting`.

#### `h2physics.adapters.gas_detection.evaluate_concentration_alarm_voting`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/gas_detection.py#L662)

Combine already latched detector traces with an explicit same-sample k-of-n rule.

Individual concentration bases, limits, hysteresis and confirmation rules remain
detector-owned. This layer adds no independence, common-cause, reliability, missing
data, asynchronous sampling, voting delay, or setpoint assumptions.

```python
evaluate_concentration_alarm_voting(traces, *, votes_required, voting_id, logic_evidence_id)
```

The source has no explicit return annotation; inspect its return statements and the domain manual. No return type is invented by this generator.

### Returned value / 반환값

`ConcentrationAlarmVotingTrace`

This return contract was reviewed from the implementation; it is not an annotation present in the source signature.

### Related input/return records / 관련 입력·반환 객체

#### `h2physics.adapters.gas_detection.ConcentrationAlarmVotingTrace`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/gas_detection.py#L564)

Same-clock sampled k-of-n vote over original, individually latched alarms.

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `voting_id` | `str` | `required` |
| `logic_evidence_id` | `str` | `required` |
| `votes_required` | `int` | `required` |
| `traces` | `tuple[ConcentrationAlarmTrace, ...]` | `required` |
| `time_s` | `np.ndarray` | `required` |
| `vote_count` | `np.ndarray` | `required` |
| `latched_alarm` | `np.ndarray` | `required` |
| `transitions` | `tuple[ConcentrationAlarmVoteTransition, ...]` | `required` |

Computed properties: `clock_id`, `operating_mode_id`, `episode_id`, `detector_evidence_ids`.

#### `h2physics.adapters.gas_detection.ConcentrationAlarmTrace`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/gas_detection.py#L356)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `config` | `ConcentrationAlarmConfig` | `required` |
| `time_s` | `np.ndarray` | `required` |
| `concentration` | `np.ndarray` | `required` |
| `latched_alarm` | `np.ndarray` | `required` |
| `transitions` | `tuple[ConcentrationAlarmTransition, ...]` | `required` |
| `sensor_response` | `FirstOrderConcentrationSensorTrace &#124; None` | `None` |

#### `h2physics.adapters.gas_detection.ConcentrationAlarmVoteTransition`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/gas_detection.py#L540)

A sampled change in an explicit k-of-n combination of detector latches.

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `alarm_active` | `bool` | `required` |
| `sample_index` | `int` | `required` |
| `time_s` | `float` | `required` |
| `active_detector_ids` | `tuple[str, ...]` | `required` |


<a id="module-h2physics-adapters-process_monitoring-nativeresidualmonitor-evaluate"></a>

## 외부 인과적 PCA 잔차 감시 / Native causal PCA residual monitoring

Family / navigation ID: `facility.monitoring`

Import module: `h2physics.adapters.process_monitoring`; selected entry: `NativeResidualMonitor.evaluate`.

#### `h2physics.adapters.process_monitoring.NativeResidualMonitor`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/process_monitoring.py#L322)

Native mode-specific learned PCA; explicit independent lifecycle and evidence.

```python
NativeResidualMonitor(native: NativeProcessMonitoring, settings: MonitoringSettings=MonitoringSettings())
```

#### `h2physics.adapters.process_monitoring.NativeResidualMonitor.evaluate`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/process_monitoring.py#L424)

```python
evaluate(self, data: ResidualBatch) -> MonitoringEvaluation
```

### Returned value / 반환값

`MonitoringEvaluation`

### Related input/return records / 관련 입력·반환 객체

#### `h2physics.adapters.process_monitoring.NativeProcessMonitoring`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/process_monitoring.py#L71)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `module` | `Any` | `required` |
| `thermo` | `Any` | `required` |
| `classical` | `Any` | `required` |
| `serialization` | `Any` | `required` |
| `sklearn` | `Any` | `required` |
| `source_sha256` | `str` | `required` |
| `versions` | `Mapping[str, str]` | `required` |
| `call_bindings` | `tuple` | `required` |

#### `h2physics.adapters.process_monitoring.MonitoringSettings`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/process_monitoring.py#L263)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `window` | `int` | `4` |
| `statistics` | `tuple[str, ...]` | `('mean', 'std')` |
| `maximum_gap_s` | `float` | `1.5` |
| `principal_components` | `int` | `1` |
| `false_alarm_fraction` | `float` | `0.05` |

#### `h2physics.adapters.process_monitoring.ResidualBatch`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/process_monitoring.py#L161)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `native_batch` | `Any` | `required` |
| `observations` | `ObservationTable` | `required` |
| `observed` | `TimeSeries` | `required` |
| `predicted` | `TimeSeries` | `required` |
| `features` | `tuple[ResidualFeature, ...]` | `required` |
| `context` | `ResidualContext` | `required` |
| `prediction_owner` | `Any` | `required` |
| `content_sha256` | `str` | `required` |

Computed properties: `episodes`, `contract`.

#### `h2physics.adapters.process_monitoring.MonitoringEvaluation`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/process_monitoring.py#L299)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `data` | `ResidualBatch` | `required` |
| `native_result` | `Any` | `required` |
| `native_model` | `Any` | `required` |
| `fitting_data` | `ResidualBatch` | `required` |
| `calibration_data` | `ResidualBatch` | `required` |
| `trained_state_sha256` | `str` | `required` |
| `mode_thresholds` | `Mapping[str, float]` | `required` |
| `score_meaning` | `str` | `'native combined-PCA score minus independently calibrated mode threshold'` |
| `physical_control_actions` | `bool` | `False` |
| `fault_identification` | `bool` | `False` |
| `time_s` | `np.ndarray` | `field(init=False)` |
| `scores` | `np.ndarray` | `field(init=False)` |
| `valid` | `np.ndarray` | `field(init=False)` |
| `alarms` | `np.ndarray` | `field(init=False)` |

#### `h2physics.observations.ObservationTable`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/observations.py#L40)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `values` | `NDArray[np.float64]` | `required` |
| `variables` | `tuple[Variable, ...]` | `required` |
| `valid` | `NDArray[np.bool_]` | `required` |
| `row_ids` | `tuple[str, ...]` | `required` |
| `experiment_ids` | `tuple[str, ...]` | `required` |
| `origins` | `tuple[Origin, ...]` | `required` |
| `source_id` | `str` | `required` |
| `context` | `tuple[tuple[str, str], ...]` | `()` |

Computed properties: `content_sha256`.

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

#### `h2physics.adapters.process_monitoring.ResidualFeature`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/process_monitoring.py#L109)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `name` | `str` | `required` |
| `observed_channel` | `str` | `required` |
| `predicted_channel` | `str` | `required` |
| `variable` | `Variable` | `required` |
| `observed_location_id` | `str` | `required` |
| `predicted_location_id` | `str` | `required` |
| `uncertainty_scale` | `float` | `required` |
| `uncertainty_id` | `str` | `required` |

#### `h2physics.adapters.process_monitoring.ResidualContext`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/process_monitoring.py#L136)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `partition_id` | `str` | `required` |
| `role` | `str` | `required` |
| `scope_id` | `str` | `required` |
| `mode_definition_id` | `str` | `required` |
| `prediction_model_id` | `str` | `required` |
| `observation_operator_id` | `str` | `required` |
| `normal_reference_id` | `str` | `''` |


<a id="module-h2physics-detector_reliability-evaluate_kofn_detector_reliability"></a>

## 사용자 확률에 따른 k-of-n 검출 실패 집계 / Caller-probability k-of-n detector fail-to-alarm aggregation

Family / navigation ID: `facility.detector_reliability`

Import module: `h2physics.detector_reliability`; selected entry: `evaluate_kofn_detector_reliability`.

#### `h2physics.detector_reliability.evaluate_kofn_detector_reliability`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/detector_reliability.py#L108)

Evaluate fail-to-alarm for a k-of-n vote with an explicit common-cause event.

Per-detector probabilities mean independent failure during the declared
mission, conditional on no modeled common-cause event. The common-cause
event disables all detectors with the separate supplied probability. No
event rate, repair model, setpoint, dependence law or evidence is inferred.

```python
evaluate_kofn_detector_reliability(detector_ids, independent_failure_probabilities, *, votes_required, common_cause_failure_probability, mission_duration_s, system_id, mission_id, voting_logic_id, independent_probability_evidence_ids, common_cause_evidence_id) -> KofNDetectorReliability
```

### Returned value / 반환값

`KofNDetectorReliability`

### Related input/return records / 관련 입력·반환 객체

#### `h2physics.detector_reliability.KofNDetectorReliability`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/detector_reliability.py#L16)

Fail-to-alarm probability for an ordered detector vote in one mission.

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `system_id` | `str` | `required` |
| `mission_id` | `str` | `required` |
| `voting_logic_id` | `str` | `required` |
| `independent_probability_evidence_ids` | `tuple[str, ...]` | `required` |
| `common_cause_evidence_id` | `str` | `required` |
| `detector_ids` | `tuple[str, ...]` | `required` |
| `votes_required` | `int` | `required` |
| `mission_duration_s` | `float` | `required` |
| `independent_failure_probabilities` | `tuple[float, ...]` | `required` |
| `common_cause_failure_probability` | `float` | `required` |
| `conditional_independent_vote_failure_probability` | `float` | `required` |
| `total_vote_failure_probability` | `float` | `required` |
| `marginal_failure_probabilities` | `tuple[float, ...]` | `required` |


## Maintaining this guide / 갱신

Curated purposes and entry selection live in `scripts/readme_module_guide.py`. Run `python scripts/readme_module_guide.py` to regenerate both README blocks and this file. Run `python scripts/readme_module_guide.py --check` to reject stale output, unresolved callables or missing catalog IDs. The script parses source with the standard library, imports no physical engine and runs no calculation. Review purpose/units/limits against domain manuals when an API changes. It preserves authored scientific attribution and performs no automatic translation of external material.
