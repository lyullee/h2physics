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

- [기체·액화수소 탱크와 기화기 등의 유한 재고·벽 열응답 / Native warm-gas/LH2 tank and stored-device inventory dynamics](#module-h2physics-adapters-lh2dt_dynamics-lh2dtdynamicequipment-run)
- [진공 단열 열유입과 벽 구역별 열 배분 / Vacuum insulation heat paths and wall allocation](#module-h2physics-adapters-lh2dt_insulation-lh2dtvacuuminsulation-evaluate)
- [마찰식을 교체할 수 있는 정상 배관 유량·압력손실 / Steady frozen-property pipe flow with injected friction law](#module-h2physics-hydraulics-solve_darcy_flow)
- [EOS를 명시한 등온 압축성 기체 배관 유동 / Steady isothermal compressible gas flow with explicit EOS selection](#module-h2physics-hydraulics-solve_isothermal_compressible_gas_flow)
- [실제 기체의 단일 셀 배관 저장량 변화 / One-cell real-gas pipeline inventory advance](#module-h2physics-real_gas_linepack-realgaslinepackstate-advance)
- [구간별 등온 배관망 재고·유량 과도응답 / Segmented quasi-steady isothermal network inventories](#module-h2physics-isothermal_gas_pipe_network-isothermalgaspipenetwork-simulate)
- [단일 등온 배관 압력·운동량 파동 / Single-pipe isothermal pressure and momentum waves](#module-h2physics-isothermal_pipe_waves-isothermalpipewavemodel-simulate)
- [분기 등온 배관망과 접합부 파동 / Branched isothermal pipe waves and junctions](#module-h2physics-isothermal_pipe_network_waves-isothermalpipenetworkwavemodel-simulate)
- [질량·운동량·에너지를 푸는 단상 배관 파동 / Single-phase pipe mass/momentum/energy waves](#module-h2physics-caloric_pipe_waves-caloricpipewavemodel-simulate)
- [혼합 접합부를 포함한 에너지 배관망 파동 / Branched caloric waves with mixing junctions](#module-h2physics-caloric_pipe_network_waves-caloricpipenetworkwavemodel-simulate)
- [배관 기체와 유한 열용량 벽의 열응답 결합 / Pipe gas coupled to finite wall thermal storage](#module-h2physics-caloric_pipe_finite_wall-simulate_caloric_pipe_with_finite_wall)
- [단상·균질평형 이상 배관과 공통 Darcy 계산 연결 / Native state/HEM pipe binding to shared Darcy closure](#module-h2physics-adapters-lh2dt_hydraulics-lh2dtdarcypipe-evaluate)
- [공통 노즐을 이용한 두 포트 밸브 감압 / Two-port throttling using the shared nozzle](#module-h2physics-adapters-lh2dt_equipment-lh2dtsharedvalve-evaluate)
- [사용자 유량 맵에 따른 밸브 개도 과도응답 / Finite-stroke actuation with a caller-supplied flow map](#module-h2physics-adapters-lh2dt_valve_actuator-finitestrokevalve-run)
- [탱크 안전밸브 개방·재폐쇄와 방출 재고 계산 / Finite-tank relief opening/reseat with inventory accounting](#module-h2physics-adapters-lh2dt_relief-lh2dtrelieftankdriver-run)
- [펌프 속도 명령·운전 맵·NPSH 조건 검사 / Pump speed commands, map and NPSH admission](#module-h2physics-adapters-lh2dt_pump_operation-finitespeedpump-run)
- [다단 기체 압축과 지정 중간 냉각의 동력·열량 / Gas compression stages and prescribed intercooling](#module-h2physics-adapters-lh2dt_compressor-lh2dtcompressiontrain-evaluate)
- [사용자 압축기 맵 기반 운전영역 검사 / Caller-map operating-envelope admission](#module-h2physics-adapters-compressor_map-mappedcompressor-evaluate)
- [운전점과 서지선 간 정적 여유 검사 / Static source-bound surge-margin screening](#module-h2physics-adapters-compressor_anti_surge-compressorantisurgeguard-evaluate)
- [정상 공간 분할 대향류 열교환 / Steady spatial counterflow heat exchange](#module-h2physics-adapters-counterflow_heat_exchanger-counterflowheatexchanger-solve)
- [양측 유체·벽의 유한 열저장·열교환 과도응답 / Finite two-side fluid/wall thermal storage](#module-h2physics-adapters-lh2dt_heat_exchanger-lh2dtfiniteheatexchanger-run)
- [냉각 용량 제한을 고려한 포화 냉각·액상 생산 / Capacity-limited saturation cooling and liquid production](#module-h2physics-adapters-lh2dt_reliquefier-lh2dtsteadyreliquefier-evaluate)
- [저마하 벤트 유량·압력손실·열전달 / Low-Mach vent hydraulics and enthalpy transfer](#module-h2physics-adapters-lh2dt_vent-lh2dtventstack-evaluate)
- [단위·위치가 명시된 계측기 지연 응답 / Native held-input transmitter response](#module-h2physics-adapters-lh2dt_instrumentation-lh2dttransmitter-run)

<a id="module-h2physics-adapters-lh2dt_dynamics-lh2dtdynamicequipment-run"></a>

## 기체·액화수소 탱크와 기화기 등의 유한 재고·벽 열응답 / Native warm-gas/LH2 tank and stored-device inventory dynamics

Family / navigation ID: `equipment.gas_tank`, `equipment.lh2_tank`, `equipment.vaporizer`

Import module: `h2physics.adapters.lh2dt_dynamics`; selected entry: `Lh2dtDynamicEquipment.run`.

#### `h2physics.adapters.lh2dt_dynamics.Lh2dtDynamicEquipment`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/lh2dt_dynamics.py#L618)

Partition prescribed command times while retaining the native solver.

Commands modify equipment modes, not dynamic inventories. A continuous
command callback must be smooth within each prescribed interval. Pressure
trigger localization and depletion events are outside this contract.

```python
Lh2dtDynamicEquipment(network: Lh2dtEquipmentNetwork, nodes: Mapping[str, Lh2dtInventoryNode], *, simulator_factory: Callable[..., Any], tolerances: InventoryTolerances | None=None)
```

#### `h2physics.adapters.lh2dt_dynamics.Lh2dtDynamicEquipment.run`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/lh2dt_dynamics.py#L653)

```python
run(self, duration_s: float, time_step_s: float, *, clock_id: str, start_time_s: float=0.0, commands: Sequence[ScheduledEquipmentCommand]=(), continuous_command: Callable[[float, Any], None] | None=None, pressure_solver_max_nfev: int=300)
```

The source has no explicit return annotation; inspect its return statements and the domain manual. No return type is invented by this generator.

### Returned value / 반환값

`DynamicEquipmentRun`

This return contract was reviewed from the implementation; it is not an annotation present in the source signature.

### Related input/return records / 관련 입력·반환 객체

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

#### `h2physics.adapters.lh2dt_dynamics.Lh2dtInventoryNode`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/lh2dt_dynamics.py#L47)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `native_node` | `Any` | `required` |
| `inventory_reader` | `Callable[[Any], ConservedInventory]` | `required` |

#### `h2physics.dynamics.InventoryTolerances`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/dynamics.py#L33)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `mass_absolute_kg` | `float` | `1e-08` |
| `energy_absolute_j` | `float` | `0.0001` |
| `relative` | `float` | `1e-08` |

#### `h2physics.dynamics.ScheduledEquipmentCommand`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/dynamics.py#L86)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `identifier` | `str` | `required` |
| `time_s` | `float` | `required` |
| `apply` | `Callable[[float, Any], None]` | `required` |

#### `h2physics.dynamics.ConservedInventory`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/dynamics.py#L15)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `basis` | `PropertyBasis` | `required` |
| `mass_kg` | `float` | `required` |
| `fluid_internal_energy_j` | `float` | `required` |
| `solid_internal_energy_j` | `float` | `required` |

Computed properties: `total_energy_j`.

#### `h2physics.adapters.lh2dt_equipment.EquipmentNetworkSnapshot`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/lh2dt_equipment.py#L72)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `node_states` | `Mapping[str, ThermoState]` | `required` |
| `transfers` | `tuple[ConnectionTransfer, ...]` | `required` |
| `junction_mass_residuals_kg_s` | `Mapping[str, float]` | `required` |
| `junction_energy_residuals_w` | `Mapping[str, float]` | `required` |
| `boundary_inlet_kg_s` | `float` | `required` |
| `boundary_outlet_kg_s` | `float` | `required` |
| `boundary_inlet_enthalpy_w` | `float` | `required` |
| `boundary_outlet_enthalpy_w` | `float` | `required` |
| `native_success` | `bool` | `required` |
| `native` | `Any` | `field(repr=False, compare=False)` |
| `native_component_results` | `Mapping[str, Any]` | `field(default_factory=dict, repr=False, compare=False)` |

Computed properties: `energy_residual_w`, `mass_residual_kg_s`, `missing_momentum_components`.

#### `h2physics.adapters.lh2dt_dynamics.DynamicEquipmentStep`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/lh2dt_dynamics.py#L82)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `time_s` | `float` | `required` |
| `inventories` | `Mapping[str, ConservedInventory]` | `required` |
| `balances` | `Mapping[str, InventoryBalance]` | `required` |
| `equipment` | `EquipmentNetworkSnapshot` | `required` |
| `native` | `Any` | `required` |

#### `h2physics.adapters.lh2dt_dynamics.EquipmentCommandTransition`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/lh2dt_dynamics.py#L95)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `time_s` | `float` | `required` |
| `identifiers` | `tuple[str, ...]` | `required` |
| `before` | `EquipmentNetworkSnapshot` | `required` |
| `after` | `EquipmentNetworkSnapshot` | `required` |


<a id="module-h2physics-adapters-lh2dt_insulation-lh2dtvacuuminsulation-evaluate"></a>

## 진공 단열 열유입과 벽 구역별 열 배분 / Vacuum insulation heat paths and wall allocation

Family / navigation ID: `equipment.insulation`

Import module: `h2physics.adapters.lh2dt_insulation`; selected entry: `Lh2dtVacuumInsulation.evaluate`.

#### `h2physics.adapters.lh2dt_insulation.Lh2dtVacuumInsulation`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/lh2dt_insulation.py#L106)

Keep an actual native VacuumInsulation object; do not collapse it into a UA.

```python
Lh2dtVacuumInsulation(native, *, evidence: InsulationEvidence, heat_tolerance_w: float=1e-10)
```

#### `h2physics.adapters.lh2dt_insulation.Lh2dtVacuumInsulation.evaluate`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/lh2dt_insulation.py#L136)

```python
evaluate(self, warm_temperature_k: float, cold_temperature_k: float, vacuum_pressure_pa_abs: float) -> InsulationHeat
```

### Returned value / 반환값

`InsulationHeat`

### Related input/return records / 관련 입력·반환 객체

#### `h2physics.adapters.lh2dt_insulation.InsulationEvidence`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/lh2dt_insulation.py#L19)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `geometry_id` | `str` | `required` |
| `closure_id` | `str` | `required` |
| `residual_gas_id` | `str` | `required` |
| `pressure_evidence_id` | `str` | `required` |
| `source_ids` | `tuple[str, ...]` | `required` |
| `origin` | `Origin` | `required` |
| `pressure_basis` | `str` | `'absolute'` |

#### `h2physics.adapters.lh2dt_insulation.InsulationHeat`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/lh2dt_insulation.py#L75)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `warm_temperature_k` | `float` | `required` |
| `cold_temperature_k` | `float` | `required` |
| `vacuum_pressure_pa_abs` | `float` | `required` |
| `power` | `BoundaryPower` | `required` |
| `path_heat_w` | `tuple[tuple[str, float], ...]` | `required` |
| `heat_residual_w` | `float` | `required` |
| `native` | `Any` | `required` |
| `evidence` | `InsulationEvidence` | `required` |

#### `h2physics.equipment.BoundaryPower`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/equipment.py#L14)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `heat_w` | `float` | `0.0` |
| `shaft_work_w` | `float` | `0.0` |

Computed properties: `total_w`.


<a id="module-h2physics-hydraulics-solve_darcy_flow"></a>

## 마찰식을 교체할 수 있는 정상 배관 유량·압력손실 / Steady frozen-property pipe flow with injected friction law

Family / navigation ID: `equipment.gas_pipe`

Import module: `h2physics.hydraulics`; selected entry: `solve_darcy_flow`.

#### `h2physics.hydraulics.solve_darcy_flow`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/hydraulics.py#L94)

Solve positive flow magnitude; the caller owns direction and hydrostatics.

A scalar root flag alone is insufficient for a discontinuous friction law.
The returned flow must also close its independently reconstructed loss.

```python
solve_darcy_flow(geometry: DarcyGeometry, *, density_kg_m3: float, viscosity_pa_s: float, driving_pressure_pa: float, friction_law: Callable[[float, float], float], pressure_absolute_tolerance_pa: float=1e-07, pressure_relative_tolerance: float=1e-10) -> DarcyFlowResult
```

### Returned value / 반환값

`DarcyFlowResult`

### Related input/return records / 관련 입력·반환 객체

#### `h2physics.hydraulics.DarcyGeometry`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/hydraulics.py#L20)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `length_m` | `float` | `required` |
| `diameter_m` | `float` | `required` |
| `roughness_m` | `float` | `required` |
| `local_loss_coefficient` | `float` | `0.0` |

#### `h2physics.hydraulics.DarcyFlowResult`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/hydraulics.py#L37)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `mass_flow_kg_s` | `float` | `required` |
| `velocity_m_s` | `float` | `required` |
| `reynolds_number` | `float` | `required` |
| `darcy_friction_factor` | `float` | `required` |
| `driving_pressure_pa` | `float` | `required` |
| `modeled_pressure_drop_pa` | `float` | `required` |
| `momentum_residual_pa` | `float` | `required` |
| `root_converged` | `bool` | `required` |
| `iterations` | `int` | `required` |


<a id="module-h2physics-hydraulics-solve_isothermal_compressible_gas_flow"></a>

## EOS를 명시한 등온 압축성 기체 배관 유동 / Steady isothermal compressible gas flow with explicit EOS selection

Family / navigation ID: `equipment.gas_pipe`

Import module: `h2physics.hydraulics`; selected entry: `solve_isothermal_compressible_gas_flow`.

#### `h2physics.hydraulics.solve_isothermal_compressible_gas_flow`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/hydraulics.py#L144)

Solve steady horizontal isothermal flow between two absolute pressures.

The 1-D momentum balance retains both wall friction and the pressure-driven
velocity change. The explicit analytic branch uses the perfect-gas density
relation; the native branch uses CoolProp density. Dynamic viscosity
and temperature are caller-declared constants. The caller supplies a Darcy
friction correlation. Elevation, heat exchange, local losses, choking,
and transient line inventory are outside this level. With ``eos=None`` an
explicit molecular mass selects the analytic ideal-gas reference. A native
CoolProp isothermal EOS instead supplies density and its derivative; no
ideal fallback or effective compressibility factor is used. Native flow
must remain below its isothermal sonic singularity along an adaptive
momentum-ODE trajectory. This is a numerical domain gate, not a global
mathematical proof or a choked-flow model.

The independent implementation integrates steady mass/momentum conservation:
G**2*(f*L/D + 2*log(rho_up/rho_down)) = 2*integral(rho(P,T), dP).
The relation follows the differential momentum balance, with held viscosity
and hence constant Re/f along the pipe. Scientific context:
https://dwsim.org/help/main/24-unit-operations.html (momentum balance)
https://coolprop.org/coolprop/HighLevelAPI.html (homogeneous derivatives).
https://arxiv.org/abs/2410.20292 (nonideal isothermal pipeline context;
its cubic EOS is not implemented here).
Positive flow is from the higher upstream pressure to the lower downstream
pressure; reverse flow is represented by swapping the endpoint pressures.

```python
solve_isothermal_compressible_gas_flow(geometry: DarcyGeometry, *, upstream_pressure_pa: float, downstream_pressure_pa: float, temperature_k: float, molecular_mass_kg_mol: float | None=None, viscosity_pa_s: float, friction_law: Callable[[float, float], float], friction_law_id: str, pressure_absolute_tolerance_pa: float=1e-05, pressure_relative_tolerance: float=1e-09, eos=None) -> IsothermalCompressibleGasResult
```

### Returned value / 반환값

`IsothermalCompressibleGasResult`

### Related input/return records / 관련 입력·반환 객체

#### `h2physics.hydraulics.DarcyGeometry`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/hydraulics.py#L20)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `length_m` | `float` | `required` |
| `diameter_m` | `float` | `required` |
| `roughness_m` | `float` | `required` |
| `local_loss_coefficient` | `float` | `0.0` |

#### `h2physics.hydraulics.IsothermalCompressibleGasResult`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/hydraulics.py#L57)

Steady isothermal flow; viscosity is explicitly held constant.

Native pressure diagnostics are reconstructed by a differential momentum
integration, separately from the integral used to determine the flow.

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `mass_flow_kg_s` | `float` | `required` |
| `inlet_velocity_m_s` | `float` | `required` |
| `outlet_velocity_m_s` | `float` | `required` |
| `reynolds_number` | `float` | `required` |
| `darcy_friction_factor` | `float` | `required` |
| `upstream_pressure_pa` | `float` | `required` |
| `downstream_pressure_pa` | `float` | `required` |
| `temperature_k` | `float` | `required` |
| `specific_gas_constant_j_kg_k` | `float &#124; None` | `required` |
| `modeled_downstream_pressure_pa` | `float` | `required` |
| `pressure_residual_pa` | `float` | `required` |
| `friction_law_id` | `str` | `required` |
| `eos_identity` | `str &#124; None` | `None` |
| `viscosity_model` | `str` | `'held-constant'` |
| `density_integral_pa_kg_m3` | `float &#124; None` | `None` |
| `density_integral_error_pa_kg_m3` | `float &#124; None` | `None` |
| `momentum_integral_residual_pa_kg_m3` | `float &#124; None` | `None` |
| `maximum_isothermal_mach_number` | `float &#124; None` | `None` |
| `native_path_gate` | `str &#124; None` | `None` |


<a id="module-h2physics-real_gas_linepack-realgaslinepackstate-advance"></a>

## 실제 기체의 단일 셀 배관 저장량 변화 / One-cell real-gas pipeline inventory advance

Family / navigation ID: `equipment.gas_pipe`

Import module: `h2physics.real_gas_linepack`; selected entry: `RealGasLinepackState.advance`.

#### `h2physics.real_gas_linepack.RealGasLinepackState`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/real_gas_linepack.py#L33)

One well-mixed fixed-volume inventory evaluated by an isothermal EOS.

The EOS must reject states outside its homogeneous single-phase domain.
Pressure is recalculated from current mass density and fixed temperature;
no perfect-gas compressibility factor or ideal-gas fallback is applied.

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `volume_m3` | `float` | `required` |
| `temperature_k` | `float` | `required` |
| `mass_kg` | `float` | `required` |
| `eos` | `IsothermalSinglePhaseEOS` | `field(repr=False, compare=False)` |
| `time_s` | `float` | `0.0` |
| `minimum_pressure_pa` | `float &#124; None` | `None` |
| `maximum_pressure_pa` | `float &#124; None` | `None` |
| `pressure_pa` | `float` | `field(init=False)` |
| `eos_identity` | `str` | `field(init=False)` |

Computed properties: `density_kg_m3`.

#### `h2physics.real_gas_linepack.RealGasLinepackState.advance`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/real_gas_linepack.py#L108)

Advance constant prescribed port rates over one caller interval.

The step rejects inventory-floor, pressure-domain, EOS-phase and EOS-
identity failures; requested flows are never silently clipped.

```python
advance(self, *, duration_s, inlet_mass_flow_kg_s, outlet_mass_flow_kg_s, minimum_mass_kg=0.0)
```

The source has no explicit return annotation; inspect its return statements and the domain manual. No return type is invented by this generator.

### Returned value / 반환값

`tuple[RealGasLinepackState, RealGasLinepackStepLedger]`

This return contract was reviewed from the implementation; it is not an annotation present in the source signature.

### Related input/return records / 관련 입력·반환 객체

#### `h2physics.real_gas_linepack.RealGasLinepackStepLedger`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/real_gas_linepack.py#L143)

Integrated boundary masses and EOS pressure endpoints for one step.

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `start_time_s` | `float` | `required` |
| `end_time_s` | `float` | `required` |
| `inlet_mass_kg` | `float` | `required` |
| `outlet_mass_kg` | `float` | `required` |
| `initial_mass_kg` | `float` | `required` |
| `final_mass_kg` | `float` | `required` |
| `initial_pressure_pa` | `float` | `required` |
| `final_pressure_pa` | `float` | `required` |
| `mass_residual_kg` | `float` | `required` |
| `eos_identity` | `str` | `required` |


<a id="module-h2physics-isothermal_gas_pipe_network-isothermalgaspipenetwork-simulate"></a>

## 구간별 등온 배관망 재고·유량 과도응답 / Segmented quasi-steady isothermal network inventories

Family / navigation ID: `equipment.gas_pipe`

Import module: `h2physics.isothermal_gas_pipe_network`; selected entry: `IsothermalGasPipeNetwork.simulate`.

#### `h2physics.isothermal_gas_pipe_network.IsothermalGasPipeNetwork`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/isothermal_gas_pipe_network.py#L291)

A one-dimensional chain of finite isothermal gas inventories.

Positive boundary rates add mass to a cell; negative rates withdraw it.
Positive link flow is from cell ``i`` to cell ``i+1``. Flow in each link is
recalculated from the instantaneous endpoint pressures using the existing
steady isothermal compressible Darcy closure. It has no momentum storage,
acoustic wave, choking, heat-transfer or species equation. Native pressure
and steady-link properties come from the existing direct CoolProp owners.

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `cells` | `tuple[IsothermalPipeCell, ...]` | `required` |
| `links` | `tuple[IsothermalPipeLink, ...]` | `required` |
| `friction_law` | `Callable[[float, float], float]` | `field(repr=False, compare=False)` |
| `friction_law_id` | `str` | `required` |

#### `h2physics.isothermal_gas_pipe_network.IsothermalGasPipeNetwork.simulate`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/isothermal_gas_pipe_network.py#L384)

Integrate finite cell stocks with constant signed external boundary rates.

Event termination is localized when any cell reaches the explicit
positive stock floor. A terminal trace includes that exact event state
and the sampled accepted prefix. The constant boundary rates are held
over the complete requested integration window.

```python
simulate(self, *, boundary_mass_flow_kg_s: Sequence[float], boundary_evidence_ids: Sequence[str], time_samples_s: Sequence[float], minimum_cell_mass_kg: float, method: str='BDF', relative_tolerance: float=1e-08, absolute_tolerance_kg: float=1e-11, maximum_step_s: float | None=None) -> IsothermalGasPipeNetworkTrace
```

### Returned value / 반환값

`IsothermalGasPipeNetworkTrace`

### Related input/return records / 관련 입력·반환 객체

#### `h2physics.isothermal_gas_pipe_network.IsothermalPipeCell`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/isothermal_gas_pipe_network.py#L98)

One fixed-volume inventory; native EOS is explicit, never a fallback.

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `cell_id` | `str` | `required` |
| `volume_m3` | `float` | `required` |
| `temperature_k` | `float` | `required` |
| `molecular_mass_kg_mol` | `float &#124; None` | `None` |
| `initial_mass_kg` | `float &#124; None` | `None` |
| `eos` | `CoolPropIsothermalEOS &#124; CoolPropMixtureIsothermalEOS &#124; None` | `field(default=None, repr=False, compare=False, kw_only=True)` |

Computed properties: `specific_gas_constant_j_kg_k`, `initial_pressure_pa`.

#### `h2physics.isothermal_gas_pipe_network.IsothermalPipeLink`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/isothermal_gas_pipe_network.py#L173)

One horizontal, frictional link using the shared steady Darcy solver.

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `link_id` | `str` | `required` |
| `geometry` | `DarcyGeometry` | `required` |
| `viscosity_pa_s` | `float` | `required` |

#### `h2physics.isothermal_gas_pipe_network.IsothermalGasPipeNetworkTrace`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/isothermal_gas_pipe_network.py#L191)

Immutable cell inventories and pressure-driven link flows over time.

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `cell_ids` | `tuple[str, ...]` | `required` |
| `link_ids` | `tuple[str, ...]` | `required` |
| `time_s` | `np.ndarray` | `field(repr=False, compare=False)` |
| `mass_kg` | `np.ndarray` | `field(repr=False, compare=False)` |
| `pressure_pa` | `np.ndarray` | `field(repr=False, compare=False)` |
| `link_mass_flow_kg_s` | `np.ndarray` | `field(repr=False, compare=False)` |
| `mass_balance_residual_kg` | `np.ndarray` | `field(repr=False, compare=False)` |
| `boundary_evidence_ids` | `tuple[str, ...]` | `required` |
| `friction_law_id` | `str` | `required` |
| `complete` | `bool` | `required` |
| `terminal_cell_id` | `str &#124; None` | `required` |
| `eos_identities` | `tuple[str, ...]` | `()` |
| `network` | `IsothermalGasPipeNetwork &#124; None` | `field(default=None, repr=False, compare=False)` |
| `boundary_mass_flow_kg_s` | `tuple[float, ...]` | `()` |

#### `h2physics.hydraulics.DarcyGeometry`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/hydraulics.py#L20)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `length_m` | `float` | `required` |
| `diameter_m` | `float` | `required` |
| `roughness_m` | `float` | `required` |
| `local_loss_coefficient` | `float` | `0.0` |


<a id="module-h2physics-isothermal_pipe_waves-isothermalpipewavemodel-simulate"></a>

## 단일 등온 배관 압력·운동량 파동 / Single-pipe isothermal pressure and momentum waves

Family / navigation ID: `equipment.gas_pipe`

Import module: `h2physics.isothermal_pipe_waves`; selected entry: `IsothermalPipeWaveModel.simulate`.

#### `h2physics.isothermal_pipe_waves.IsothermalPipeWaveModel`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/isothermal_pipe_waves.py#L192)

One horizontal, constant-area, closed-ended hydrogen pipe segment.

Pressures are absolute Pa, temperature is K, length/diameter are m,
velocity is m/s, and time is s. EOS is provided by the shared
``IsothermalSinglePhaseEOS`` API; the default is CoolProp HEOS hydrogen.
Missing CoolProp or a rejected native state raises an error; no ideal-gas
fallback is selected.
The wall condition is impermeable at both ends. A constant caller-selected
Darcy friction factor damps momentum.

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `length_m` | `float` | `required` |
| `internal_diameter_m` | `float` | `required` |
| `cell_count` | `int` | `required` |
| `temperature_k` | `float` | `required` |
| `darcy_friction_factor` | `float` | `0.0` |
| `maximum_cfl` | `float` | `0.4` |
| `maximum_internal_steps` | `int` | `2000000` |
| `eos` | `IsothermalSinglePhaseEOS` | `field(default_factory=CoolPropIsothermalEOS, repr=False, compare=False)` |

Computed properties: `cell_length_m`, `cross_section_area_m2`.

#### `h2physics.isothermal_pipe_waves.IsothermalPipeWaveModel.simulate`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/isothermal_pipe_waves.py#L245)

Advance the finite-volume solution to each requested sample time.

The spatial update is first-order Rusanov flux on cell averages. Closed
ends retain zero boundary mass flux and pressure wall traction. Optional
pressure reservoirs supply one incoming subsonic characteristic at an
open end while the adjacent cell supplies the outgoing characteristic.
At each substep,
the maximum acoustic/convective speed sets ``dt <= CFL*dx/(|u|+c)``.
Darcy drag is applied by its exact local momentum decay map after each
conservative flux update. Internal states that become nonpositive are
rejected rather than clipped. No output interpolation is used.

```python
simulate(self, *, initial_pressure_pa: Sequence[float], initial_velocity_m_s: Sequence[float], time_samples_s: Sequence[float], left_reservoir: FiniteReservoirPressureBoundary | None=None, right_reservoir: FiniteReservoirPressureBoundary | None=None, clock_id: str | None=None) -> IsothermalPipeWaveTrace
```

### Returned value / 반환값

`IsothermalPipeWaveTrace`

### Related input/return records / 관련 입력·반환 객체

#### `h2physics.pipe_reservoir_boundary.FiniteReservoirPressureBoundary`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/pipe_reservoir_boundary.py#L13)

A finite, externally modeled reservoir's prescribed pressure history.

This object carries an explicit pressure/time state sequence and its owner,
evidence, clock, EOS and origin. It does not evolve reservoir mass itself.
The pipe solver consumes the trace without extrapolating beyond its knots.

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `identifier` | `str` | `required` |
| `state_owner_id` | `str` | `required` |
| `state_evidence_id` | `str` | `required` |
| `clock_id` | `str` | `required` |
| `eos_identity` | `str` | `required` |
| `temperature_k` | `float` | `required` |
| `time_s` | `np.ndarray` | `field(repr=False, compare=False)` |
| `pressure_pa` | `np.ndarray` | `field(repr=False, compare=False)` |
| `origin` | `Origin` | `Origin.UNRESOLVED` |

#### `h2physics.isothermal_pipe_waves.IsothermalPipeWaveTrace`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/isothermal_pipe_waves.py#L30)

Immutable sampled pipe states, signed boundary flows and mass ledgers.

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `time_s` | `np.ndarray` | `field(repr=False, compare=False)` |
| `cell_center_m` | `np.ndarray` | `field(repr=False, compare=False)` |
| `pressure_pa` | `np.ndarray` | `field(repr=False, compare=False)` |
| `velocity_m_s` | `np.ndarray` | `field(repr=False, compare=False)` |
| `density_kg_m3` | `np.ndarray` | `field(repr=False, compare=False)` |
| `face_mass_flow_kg_s` | `np.ndarray` | `field(repr=False, compare=False)` |
| `total_mass_kg` | `np.ndarray` | `field(repr=False, compare=False)` |
| `mass_balance_residual_kg` | `np.ndarray` | `field(repr=False, compare=False)` |
| `isothermal_sound_speed_m_s` | `np.ndarray` | `field(repr=False, compare=False)` |
| `eos_closure_id` | `str` | `required` |
| `maximum_cfl` | `float` | `required` |
| `cfl_limit` | `float` | `required` |
| `darcy_friction_factor` | `float` | `required` |
| `temperature_k` | `float` | `required` |
| `boundary_mass_in_kg` | `np.ndarray &#124; None` | `field(default=None, repr=False, compare=False)` |
| `boundary_mass_out_kg` | `np.ndarray &#124; None` | `field(default=None, repr=False, compare=False)` |
| `left_reservoir_pressure_pa` | `np.ndarray &#124; None` | `field(default=None, repr=False, compare=False)` |
| `right_reservoir_pressure_pa` | `np.ndarray &#124; None` | `field(default=None, repr=False, compare=False)` |
| `boundary_clock_id` | `str &#124; None` | `None` |
| `left_reservoir_id` | `str &#124; None` | `None` |
| `right_reservoir_id` | `str &#124; None` | `None` |
| `left_reservoir_state_owner_id` | `str &#124; None` | `None` |
| `right_reservoir_state_owner_id` | `str &#124; None` | `None` |
| `left_reservoir_state_evidence_id` | `str &#124; None` | `None` |
| `right_reservoir_state_evidence_id` | `str &#124; None` | `None` |


<a id="module-h2physics-isothermal_pipe_network_waves-isothermalpipenetworkwavemodel-simulate"></a>

## 분기 등온 배관망과 접합부 파동 / Branched isothermal pipe waves and junctions

Family / navigation ID: `equipment.gas_pipe`

Import module: `h2physics.isothermal_pipe_network_waves`; selected entry: `IsothermalPipeNetworkWaveModel.simulate`.

#### `h2physics.isothermal_pipe_network_waves.IsothermalPipeNetworkWaveModel`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/isothermal_pipe_network_waves.py#L287)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `nodes` | `tuple[IsothermalPipeNetworkNode, ...]` | `required` |
| `edges` | `tuple[IsothermalPipeNetworkEdge, ...]` | `required` |
| `temperature_k` | `float` | `required` |
| `clock_id` | `str` | `required` |
| `eos` | `IsothermalSinglePhaseEOS` | `field(repr=False, compare=False)` |
| `maximum_cfl` | `float` | `0.35` |
| `maximum_internal_steps` | `int` | `2000000` |

#### `h2physics.isothermal_pipe_network_waves.IsothermalPipeNetworkWaveModel.simulate`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/isothermal_pipe_network_waves.py#L358)

Advance pipe waves with prescribed-pressure and finite-inventory terminals.

Prescribed-pressure exchange is accounted on the pipe side only. A
finite inventory endpoint evolves from the exact same Rusanov flux as
its adjacent pipe update and joins the combined network mass trace.

```python
simulate(self, *, initial_pressure_pa: Mapping[str, Sequence[float]], initial_velocity_m_s: Mapping[str, Sequence[float]], time_samples_s: Sequence[float], reservoir_boundaries: Mapping[str, FiniteReservoirPressureBoundary] | None=None, finite_reservoirs: Mapping[str, FiniteIsothermalPipeReservoir] | None=None, finite_reservoir_nozzles: Mapping[str, FiniteReservoirNozzleCoupling] | None=None) -> IsothermalPipeNetworkTrace
```

### Returned value / 반환값

`IsothermalPipeNetworkTrace`

### Related input/return records / 관련 입력·반환 객체

#### `h2physics.isothermal_pipe_network_waves.IsothermalPipeNetworkNode`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/isothermal_pipe_network_waves.py#L29)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `identifier` | `str` | `required` |
| `coordinates_m` | `tuple[float, float, float]` | `required` |
| `kind` | `str` | `required` |
| `state_owner_id` | `str` | `required` |
| `evidence_id` | `str` | `required` |
| `origin` | `Origin` | `Origin.UNRESOLVED` |
| `pressure_bounds_pa` | `tuple[float, float] &#124; None` | `None` |

#### `h2physics.isothermal_pipe_network_waves.IsothermalPipeNetworkEdge`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/isothermal_pipe_network_waves.py#L67)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `identifier` | `str` | `required` |
| `start_node_id` | `str` | `required` |
| `end_node_id` | `str` | `required` |
| `length_m` | `float` | `required` |
| `internal_diameter_m` | `float` | `required` |
| `cell_count` | `int` | `required` |
| `geometry_owner_id` | `str` | `required` |
| `geometry_evidence_id` | `str` | `required` |
| `darcy_friction_factor` | `float` | `0.0` |
| `origin` | `Origin` | `Origin.UNRESOLVED` |

#### `h2physics.pipe_reservoir_boundary.FiniteReservoirPressureBoundary`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/pipe_reservoir_boundary.py#L13)

A finite, externally modeled reservoir's prescribed pressure history.

This object carries an explicit pressure/time state sequence and its owner,
evidence, clock, EOS and origin. It does not evolve reservoir mass itself.
The pipe solver consumes the trace without extrapolating beyond its knots.

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `identifier` | `str` | `required` |
| `state_owner_id` | `str` | `required` |
| `state_evidence_id` | `str` | `required` |
| `clock_id` | `str` | `required` |
| `eos_identity` | `str` | `required` |
| `temperature_k` | `float` | `required` |
| `time_s` | `np.ndarray` | `field(repr=False, compare=False)` |
| `pressure_pa` | `np.ndarray` | `field(repr=False, compare=False)` |
| `origin` | `Origin` | `Origin.UNRESOLVED` |

#### `h2physics.finite_pipe_reservoir.FiniteIsothermalPipeReservoir`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/finite_pipe_reservoir.py#L17)

Caller-owned, well-mixed endpoint inventory at fixed volume and T.

`mass_kg` is the initial inventory. Network coupling must apply the same
signed pipe-outward endpoint flux to this inventory: positive flux leaves
the reservoir and enters the pipe. This class does not model a valve,
reservoir energy balance, heat transfer, or a pressure controller.

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `identifier` | `str` | `required` |
| `node_id` | `str` | `required` |
| `state_owner_id` | `str` | `required` |
| `state_evidence_id` | `str` | `required` |
| `clock_id` | `str` | `required` |
| `eos_identity` | `str` | `required` |
| `temperature_k` | `float` | `required` |
| `volume_m3` | `float` | `required` |
| `mass_kg` | `float` | `required` |
| `minimum_mass_kg` | `float` | `required` |
| `maximum_mass_kg` | `float` | `required` |
| `origin` | `Origin` | `required` |

#### `h2physics.pipe_nozzle_coupling.FiniteReservoirNozzleCoupling`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/pipe_nozzle_coupling.py#L40)

A fixed opening that withdraws mass from one network reservoir each step.

The opening and external back pressure are caller-owned. Caloric state is
obtained from the nozzle's PropertyProvider at each reservoir pressure and
fixed network temperature; the declared mapping evidence and density
tolerance are checked against the network's isothermal EOS state.

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `identifier` | `str` | `required` |
| `node_id` | `str` | `required` |
| `reservoir_id` | `str` | `required` |
| `edge_id` | `str` | `required` |
| `opening` | `NozzleOpening` | `required` |
| `opening_fraction` | `float` | `required` |
| `back_pressure_pa` | `float` | `required` |
| `location` | `SourceLocation` | `required` |
| `nozzle` | `HomogeneousIsentropicNozzle` | `required` |
| `state_mapping` | `IsothermalToCaloricStateMapping` | `required` |
| `evidence_id` | `str` | `required` |
| `origin` | `Origin` | `required` |

Computed properties: `caloric_basis`.

#### `h2physics.isothermal_pipe_network_waves.IsothermalPipeNetworkTrace`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/isothermal_pipe_network_waves.py#L101)

Sampled network state and pipe-side boundary mass-exchange ledgers.

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `time_s` | `np.ndarray` | `field(repr=False, compare=False)` |
| `edge_pressure_pa` | `Mapping[str, np.ndarray]` | `field(repr=False, compare=False)` |
| `edge_velocity_m_s` | `Mapping[str, np.ndarray]` | `field(repr=False, compare=False)` |
| `edge_face_mass_flow_kg_s` | `Mapping[str, np.ndarray]` | `field(repr=False, compare=False)` |
| `junction_pressure_pa` | `Mapping[str, np.ndarray]` | `field(repr=False, compare=False)` |
| `junction_mass_residual_kg_s` | `Mapping[str, np.ndarray]` | `field(repr=False, compare=False)` |
| `total_mass_kg` | `np.ndarray` | `field(repr=False, compare=False)` |
| `global_mass_balance_residual_kg` | `np.ndarray` | `field(repr=False, compare=False)` |
| `clock_id` | `str` | `required` |
| `eos_identity` | `str` | `required` |
| `temperature_k` | `float` | `required` |
| `node_state_owner_ids` | `Mapping[str, str]` | `required` |
| `node_evidence_ids` | `Mapping[str, str]` | `required` |
| `edge_geometry_owner_ids` | `Mapping[str, str]` | `required` |
| `edge_geometry_evidence_ids` | `Mapping[str, str]` | `required` |
| `reservoir_pressure_pa` | `Mapping[str, np.ndarray]` | `field(default_factory=dict, repr=False, compare=False)` |
| `boundary_mass_in_kg` | `np.ndarray &#124; None` | `field(default=None, repr=False, compare=False)` |
| `boundary_mass_out_kg` | `np.ndarray &#124; None` | `field(default=None, repr=False, compare=False)` |
| `reservoir_ids` | `Mapping[str, str]` | `field(default_factory=dict)` |
| `reservoir_state_owner_ids` | `Mapping[str, str]` | `field(default_factory=dict)` |
| `reservoir_evidence_ids` | `Mapping[str, str]` | `field(default_factory=dict)` |
| `reservoir_clock_ids` | `Mapping[str, str]` | `field(default_factory=dict)` |
| `reservoir_origins` | `Mapping[str, Origin]` | `field(default_factory=dict)` |
| `finite_inventory_mass_kg` | `Mapping[str, np.ndarray]` | `field(default_factory=dict, repr=False, compare=False)` |
| `finite_inventory_pressure_pa` | `Mapping[str, np.ndarray]` | `field(default_factory=dict, repr=False, compare=False)` |
| `finite_inventory_ids` | `Mapping[str, str]` | `field(default_factory=dict)` |
| `finite_inventory_state_owner_ids` | `Mapping[str, str]` | `field(default_factory=dict)` |
| `finite_inventory_evidence_ids` | `Mapping[str, str]` | `field(default_factory=dict)` |
| `finite_inventory_clock_ids` | `Mapping[str, str]` | `field(default_factory=dict)` |
| `finite_inventory_origins` | `Mapping[str, Origin]` | `field(default_factory=dict)` |
| `finite_reservoir_nozzle_history` | `Mapping[str, SourceHistory]` | `field(default_factory=dict, repr=False, compare=False)` |
| `finite_reservoir_nozzle_coupling_ids` | `Mapping[str, str]` | `field(default_factory=dict)` |
| `finite_reservoir_nozzle_evidence_ids` | `Mapping[str, str]` | `field(default_factory=dict)` |
| `finite_reservoir_nozzle_mass_out_kg` | `Mapping[str, np.ndarray]` | `field(default_factory=dict, repr=False, compare=False)` |

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

#### `h2physics.pipe_nozzle_coupling.IsothermalToCaloricStateMapping`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/pipe_nozzle_coupling.py#L14)

Caller evidence that maps network EOS states to a nozzle caloric basis.

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `source_eos_identity` | `str` | `required` |
| `target_basis` | `PropertyBasis` | `required` |
| `evidence_id` | `str` | `required` |
| `density_relative_tolerance` | `float` | `required` |
| `density_absolute_tolerance_kg_m3` | `float` | `required` |

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


<a id="module-h2physics-caloric_pipe_waves-caloricpipewavemodel-simulate"></a>

## 질량·운동량·에너지를 푸는 단상 배관 파동 / Single-phase pipe mass/momentum/energy waves

Family / navigation ID: `equipment.gas_pipe`

Import module: `h2physics.caloric_pipe_waves`; selected entry: `CaloricPipeWaveModel.simulate`.

#### `h2physics.caloric_pipe_waves.CaloricPipeWaveModel`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/caloric_pipe_waves.py#L373)

First-order finite-volume caloric gas pipe with a pluggable EOS.

The model uses uniform-area, horizontal, inviscid one-dimensional Euler
equations and a local Lax-Friedrichs/Rusanov flux. Closed ends are
reflective. Optional reservoir boundaries are caller-supplied fixed
ghost states and are not finite inventories. Optional Darcy friction and
fixed-wall heat sources are caller-evidenced; gravity, junctions and valves
remain outside this level.

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `length_m` | `float` | `required` |
| `internal_diameter_m` | `float` | `required` |
| `cell_count` | `int` | `required` |
| `eos` | `CaloricGasEOS` | `field(repr=False, compare=False)` |
| `maximum_cfl` | `float` | `0.35` |
| `maximum_internal_steps` | `int` | `1000000` |

Computed properties: `eos_identity`, `area_m2`, `cell_length_m`.

#### `h2physics.caloric_pipe_waves.CaloricPipeWaveModel.simulate`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/caloric_pipe_waves.py#L469)

Advance cell-average conserved states to requested absolute times.

The explicit time step obeys ``dt <= CFL*dx/max(|u|+a)``. Boundary
fluxes are integrated using the exact face flux used by the finite-
volume update, producing signed mass and total-energy closure ledgers.
Optional friction uses the Darcy convention and an exact frozen-factor
momentum relaxation; it does not remove total energy. Wall heat is
positive into the gas and is included exactly in the energy ledger.
No positivity clipping or silent EOS/phase substitution is performed.

```python
simulate(self, *, initial_pressure_pa: Sequence[float], initial_temperature_k: Sequence[float], initial_velocity_m_s: Sequence[float], time_samples_s: Sequence[float], clock_id: str, left_reservoir: CaloricPipeReservoirBoundary | None=None, right_reservoir: CaloricPipeReservoirBoundary | None=None, darcy_friction_law: CaloricDarcyFrictionLaw | None=None, wall_heat_boundary: CaloricPipeWallHeatBoundary | None=None) -> CaloricPipeWaveTrace
```

### Returned value / 반환값

`CaloricPipeWaveTrace`

### Related input/return records / 관련 입력·반환 객체

#### `h2physics.caloric_pipe_waves.CaloricPipeReservoirBoundary`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/caloric_pipe_waves.py#L179)

Fixed, explicitly evidenced ghost state representing a large reservoir.

This boundary does not deplete or evolve a reservoir inventory. Its
exchanged mass and total energy are retained in the pipe trace ledgers.

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `identifier` | `str` | `required` |
| `state_owner_id` | `str` | `required` |
| `state_evidence_id` | `str` | `required` |
| `clock_id` | `str` | `required` |
| `state` | `ThermoState` | `required` |
| `velocity_m_s` | `float` | `0.0` |

#### `h2physics.caloric_pipe_waves.CaloricDarcyFrictionLaw`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/caloric_pipe_waves.py#L54)

Caller-owned Darcy friction factor provider for each pipe cell.

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `identity` | `str` | `required` |
| `state_owner_id` | `str` | `required` |
| `evidence_id` | `str` | `required` |
| `clock_id` | `str` | `required` |

#### `h2physics.caloric_pipe_waves.CaloricPipeWallHeatBoundary`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/caloric_pipe_waves.py#L90)

Fixed-temperature wall heat boundary; positive heat flows into the gas.

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `identifier` | `str` | `required` |
| `state_owner_id` | `str` | `required` |
| `state_evidence_id` | `str` | `required` |
| `clock_id` | `str` | `required` |
| `wall_temperature_k` | `float` | `required` |
| `heat_transfer_coefficient_w_m2_k` | `float` | `required` |

#### `h2physics.caloric_pipe_waves.CaloricPipeWaveTrace`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/caloric_pipe_waves.py#L222)

Immutable states, boundary fluxes, and global mass/energy ledgers.

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `time_s` | `np.ndarray` | `field(repr=False, compare=False)` |
| `cell_center_m` | `np.ndarray` | `field(repr=False, compare=False)` |
| `pressure_pa` | `np.ndarray` | `field(repr=False, compare=False)` |
| `temperature_k` | `np.ndarray` | `field(repr=False, compare=False)` |
| `density_kg_m3` | `np.ndarray` | `field(repr=False, compare=False)` |
| `velocity_m_s` | `np.ndarray` | `field(repr=False, compare=False)` |
| `internal_energy_j_kg` | `np.ndarray` | `field(repr=False, compare=False)` |
| `face_mass_flow_kg_s` | `np.ndarray` | `field(repr=False, compare=False)` |
| `face_energy_flow_w` | `np.ndarray` | `field(repr=False, compare=False)` |
| `total_mass_kg` | `np.ndarray` | `field(repr=False, compare=False)` |
| `total_energy_j` | `np.ndarray` | `field(repr=False, compare=False)` |
| `cumulative_boundary_mass_in_kg` | `np.ndarray` | `field(repr=False, compare=False)` |
| `cumulative_boundary_energy_in_j` | `np.ndarray` | `field(repr=False, compare=False)` |
| `cumulative_wall_heat_in_j` | `np.ndarray` | `field(repr=False, compare=False)` |
| `darcy_factor_mean_by_interval` | `np.ndarray` | `field(repr=False, compare=False)` |
| `darcy_factor_max_by_interval` | `np.ndarray` | `field(repr=False, compare=False)` |
| `internal_steps_by_interval` | `np.ndarray` | `field(repr=False, compare=False)` |
| `mass_balance_residual_kg` | `np.ndarray` | `field(repr=False, compare=False)` |
| `energy_balance_residual_j` | `np.ndarray` | `field(repr=False, compare=False)` |
| `sound_speed_m_s` | `np.ndarray` | `field(repr=False, compare=False)` |
| `eos_identity` | `str` | `required` |
| `property_basis` | `PropertyBasis` | `required` |
| `pipe_length_m` | `float` | `required` |
| `internal_diameter_m` | `float` | `required` |
| `area_m2` | `float` | `required` |
| `maximum_cfl` | `float` | `required` |
| `cfl_limit` | `float` | `required` |
| `left_boundary_id` | `str &#124; None` | `None` |
| `right_boundary_id` | `str &#124; None` | `None` |
| `left_boundary_state_owner_id` | `str &#124; None` | `None` |
| `right_boundary_state_owner_id` | `str &#124; None` | `None` |
| `left_boundary_state_evidence_id` | `str &#124; None` | `None` |
| `right_boundary_state_evidence_id` | `str &#124; None` | `None` |
| `clock_id` | `str &#124; None` | `None` |
| `friction_law_id` | `str &#124; None` | `None` |
| `friction_state_owner_id` | `str &#124; None` | `None` |
| `friction_evidence_id` | `str &#124; None` | `None` |
| `friction_scheme` | `str &#124; None` | `None` |
| `wall_heat_boundary_id` | `str &#124; None` | `None` |
| `wall_heat_state_owner_id` | `str &#124; None` | `None` |
| `wall_heat_evidence_id` | `str &#124; None` | `None` |
| `wall_temperature_k` | `float &#124; None` | `None` |
| `heat_transfer_coefficient_w_m2_k` | `float &#124; None` | `None` |

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


<a id="module-h2physics-caloric_pipe_network_waves-caloricpipenetworkwavemodel-simulate"></a>

## 혼합 접합부를 포함한 에너지 배관망 파동 / Branched caloric waves with mixing junctions

Family / navigation ID: `equipment.gas_pipe`

Import module: `h2physics.caloric_pipe_network_waves`; selected entry: `CaloricPipeNetworkWaveModel.simulate`.

#### `h2physics.caloric_pipe_network_waves.CaloricPipeNetworkWaveModel`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/caloric_pipe_network_waves.py#L488)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `nodes` | `tuple[CaloricPipeNetworkNode, ...]` | `required` |
| `edges` | `tuple[CaloricPipeNetworkEdge, ...]` | `required` |
| `eos` | `CaloricGasEOS` | `field(repr=False, compare=False)` |
| `clock_id` | `str` | `required` |
| `maximum_cfl` | `float` | `0.3` |
| `maximum_internal_steps` | `int` | `2000000` |
| `junction_mass_tolerance_kg_s` | `float` | `1e-08` |
| `junction_energy_tolerance_w` | `float` | `0.001` |
| `junction_solver_tolerance` | `float` | `1e-11` |
| `junction_entropy_tolerance_w_k` | `float` | `1e-07` |

#### `h2physics.caloric_pipe_network_waves.CaloricPipeNetworkWaveModel.simulate`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/caloric_pipe_network_waves.py#L555)

Advance each caloric pipe edge on a shared explicit network clock.

```python
simulate(self, *, initial_pressure_pa: Mapping[str, Sequence[float]], initial_temperature_k: Mapping[str, Sequence[float]], initial_velocity_m_s: Mapping[str, Sequence[float]], time_samples_s: Sequence[float], reservoir_boundaries: Mapping[str, CaloricPipeReservoirBoundary] | None=None, finite_reservoirs: Mapping[str, FiniteCaloricPipeReservoir] | None=None, finite_reservoir_nozzles: Mapping[str, CaloricFiniteReservoirNozzleCoupling] | None=None, darcy_friction_laws: Mapping[str, CaloricDarcyFrictionLaw] | None=None, wall_heat_boundaries: Mapping[str, CaloricPipeWallHeatBoundary] | None=None) -> CaloricPipeNetworkWaveTrace
```

### Returned value / 반환값

`CaloricPipeNetworkWaveTrace`

### Related input/return records / 관련 입력·반환 객체

#### `h2physics.caloric_pipe_network_waves.CaloricPipeNetworkNode`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/caloric_pipe_network_waves.py#L48)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `identifier` | `str` | `required` |
| `coordinates_m` | `tuple[float, float, float]` | `required` |
| `kind` | `str` | `required` |
| `state_owner_id` | `str` | `required` |
| `evidence_id` | `str` | `required` |
| `origin` | `Origin` | `required` |
| `pressure_bounds_pa` | `tuple[float, float] &#124; None` | `None` |
| `temperature_bounds_k` | `tuple[float, float] &#124; None` | `None` |

#### `h2physics.caloric_pipe_network_waves.CaloricPipeNetworkEdge`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/caloric_pipe_network_waves.py#L90)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `identifier` | `str` | `required` |
| `start_node_id` | `str` | `required` |
| `end_node_id` | `str` | `required` |
| `length_m` | `float` | `required` |
| `internal_diameter_m` | `float` | `required` |
| `cell_count` | `int` | `required` |
| `geometry_owner_id` | `str` | `required` |
| `geometry_evidence_id` | `str` | `required` |
| `origin` | `Origin` | `required` |

#### `h2physics.caloric_pipe_waves.CaloricPipeReservoirBoundary`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/caloric_pipe_waves.py#L179)

Fixed, explicitly evidenced ghost state representing a large reservoir.

This boundary does not deplete or evolve a reservoir inventory. Its
exchanged mass and total energy are retained in the pipe trace ledgers.

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `identifier` | `str` | `required` |
| `state_owner_id` | `str` | `required` |
| `state_evidence_id` | `str` | `required` |
| `clock_id` | `str` | `required` |
| `state` | `ThermoState` | `required` |
| `velocity_m_s` | `float` | `0.0` |

#### `h2physics.finite_caloric_pipe_reservoir.FiniteCaloricPipeReservoir`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/finite_caloric_pipe_reservoir.py#L12)

Caller-owned rigid gas inventory coupled through an endpoint flux.

``mass_kg`` and ``internal_energy_j`` are initial extensive stocks. The
reservoir is spatially mixed and stationary. The network must use the
same signed endpoint Rusanov flux for its pipe face and this inventory;
positive outward flow leaves the reservoir and enters the pipe. This
state does not add a valve, heat transfer, wall mass, stratification, or
pressure control.

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `identifier` | `str` | `required` |
| `node_id` | `str` | `required` |
| `state_owner_id` | `str` | `required` |
| `state_evidence_id` | `str` | `required` |
| `clock_id` | `str` | `required` |
| `eos_identity` | `str` | `required` |
| `property_basis` | `PropertyBasis` | `required` |
| `volume_m3` | `float` | `required` |
| `mass_kg` | `float` | `required` |
| `internal_energy_j` | `float` | `required` |
| `minimum_mass_kg` | `float` | `required` |
| `maximum_mass_kg` | `float` | `required` |
| `pressure_bounds_pa` | `tuple[float, float]` | `required` |
| `temperature_bounds_k` | `tuple[float, float]` | `required` |
| `origin` | `Origin` | `required` |

#### `h2physics.caloric_pipe_nozzle_coupling.CaloricFiniteReservoirNozzleCoupling`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/caloric_pipe_nozzle_coupling.py#L13)

Caller-owned nozzle boundary attached to one finite caloric tank node.

The upstream state is recovered from the tank's current ``m,U,V`` by the
network EOS. The nozzle provider must use the exact same property basis
and reproduce that state within the declared density tolerances.

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `identifier` | `str` | `required` |
| `node_id` | `str` | `required` |
| `reservoir_id` | `str` | `required` |
| `edge_id` | `str` | `required` |
| `opening` | `NozzleOpening` | `required` |
| `opening_fraction` | `float` | `required` |
| `back_pressure_pa` | `float` | `required` |
| `location` | `SourceLocation` | `required` |
| `nozzle` | `HomogeneousIsentropicNozzle` | `required` |
| `state_owner_id` | `str` | `required` |
| `evidence_id` | `str` | `required` |
| `origin` | `Origin` | `required` |
| `density_relative_tolerance` | `float` | `2e-06` |
| `density_absolute_tolerance_kg_m3` | `float` | `1e-10` |

#### `h2physics.caloric_pipe_waves.CaloricDarcyFrictionLaw`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/caloric_pipe_waves.py#L54)

Caller-owned Darcy friction factor provider for each pipe cell.

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `identity` | `str` | `required` |
| `state_owner_id` | `str` | `required` |
| `evidence_id` | `str` | `required` |
| `clock_id` | `str` | `required` |

#### `h2physics.caloric_pipe_waves.CaloricPipeWallHeatBoundary`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/caloric_pipe_waves.py#L90)

Fixed-temperature wall heat boundary; positive heat flows into the gas.

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `identifier` | `str` | `required` |
| `state_owner_id` | `str` | `required` |
| `state_evidence_id` | `str` | `required` |
| `clock_id` | `str` | `required` |
| `wall_temperature_k` | `float` | `required` |
| `heat_transfer_coefficient_w_m2_k` | `float` | `required` |

#### `h2physics.caloric_pipe_network_waves.CaloricPipeNetworkWaveTrace`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/caloric_pipe_network_waves.py#L133)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `time_s` | `np.ndarray` | `field(repr=False, compare=False)` |
| `pressure_pa` | `Mapping[str, np.ndarray]` | `field(repr=False, compare=False)` |
| `temperature_k` | `Mapping[str, np.ndarray]` | `field(repr=False, compare=False)` |
| `density_kg_m3` | `Mapping[str, np.ndarray]` | `field(repr=False, compare=False)` |
| `velocity_m_s` | `Mapping[str, np.ndarray]` | `field(repr=False, compare=False)` |
| `face_mass_flow_kg_s` | `Mapping[str, np.ndarray]` | `field(repr=False, compare=False)` |
| `face_energy_flow_w` | `Mapping[str, np.ndarray]` | `field(repr=False, compare=False)` |
| `junction_pressure_pa` | `Mapping[str, np.ndarray]` | `field(repr=False, compare=False)` |
| `junction_temperature_k` | `Mapping[str, np.ndarray]` | `field(repr=False, compare=False)` |
| `junction_mass_residual_kg_s` | `Mapping[str, np.ndarray]` | `field(repr=False, compare=False)` |
| `junction_energy_residual_w` | `Mapping[str, np.ndarray]` | `field(repr=False, compare=False)` |
| `junction_entropy_generation_w_k` | `Mapping[str, np.ndarray]` | `field(repr=False, compare=False)` |
| `total_mass_kg` | `np.ndarray` | `field(repr=False, compare=False)` |
| `total_energy_j` | `np.ndarray` | `field(repr=False, compare=False)` |
| `cumulative_terminal_mass_in_kg` | `np.ndarray` | `field(repr=False, compare=False)` |
| `cumulative_terminal_energy_in_j` | `np.ndarray` | `field(repr=False, compare=False)` |
| `cumulative_junction_mass_kg` | `np.ndarray` | `field(repr=False, compare=False)` |
| `cumulative_junction_energy_j` | `np.ndarray` | `field(repr=False, compare=False)` |
| `cumulative_wall_heat_in_j` | `np.ndarray` | `field(repr=False, compare=False)` |
| `mass_balance_residual_kg` | `np.ndarray` | `field(repr=False, compare=False)` |
| `energy_balance_residual_j` | `np.ndarray` | `field(repr=False, compare=False)` |
| `edge_cell_centers_m` | `Mapping[str, np.ndarray]` | `required` |
| `edge_lengths_m` | `Mapping[str, float]` | `required` |
| `edge_diameters_m` | `Mapping[str, float]` | `required` |
| `edge_cell_counts` | `Mapping[str, int]` | `required` |
| `edge_start_node_ids` | `Mapping[str, str]` | `required` |
| `edge_end_node_ids` | `Mapping[str, str]` | `required` |
| `edge_origins` | `Mapping[str, Origin]` | `required` |
| `edge_geometry_owner_ids` | `Mapping[str, str]` | `required` |
| `edge_geometry_evidence_ids` | `Mapping[str, str]` | `required` |
| `node_coordinates_m` | `Mapping[str, tuple[float, float, float]]` | `required` |
| `node_kinds` | `Mapping[str, str]` | `required` |
| `node_origins` | `Mapping[str, Origin]` | `required` |
| `node_state_owner_ids` | `Mapping[str, str]` | `required` |
| `node_evidence_ids` | `Mapping[str, str]` | `required` |
| `reservoir_boundary_ids` | `Mapping[str, str]` | `required` |
| `reservoir_boundary_states` | `Mapping[str, ThermoState]` | `required` |
| `reservoir_boundary_velocities_m_s` | `Mapping[str, float]` | `required` |
| `friction_law_ids` | `Mapping[str, str]` | `required` |
| `friction_state_owner_ids` | `Mapping[str, str]` | `required` |
| `friction_evidence_ids` | `Mapping[str, str]` | `required` |
| `wall_heat_boundary_ids` | `Mapping[str, str]` | `required` |
| `wall_heat_state_owner_ids` | `Mapping[str, str]` | `required` |
| `wall_heat_evidence_ids` | `Mapping[str, str]` | `required` |
| `finite_reservoir_records` | `Mapping[str, FiniteCaloricPipeReservoir]` | `required` |
| `finite_reservoir_nozzle_couplings` | `Mapping[str, CaloricFiniteReservoirNozzleCoupling]` | `required` |
| `finite_reservoir_mass_kg` | `Mapping[str, np.ndarray]` | `required` |
| `finite_reservoir_internal_energy_j` | `Mapping[str, np.ndarray]` | `required` |
| `finite_reservoir_pressure_pa` | `Mapping[str, np.ndarray]` | `required` |
| `finite_reservoir_temperature_k` | `Mapping[str, np.ndarray]` | `required` |
| `finite_reservoir_nozzle_history` | `Mapping[str, SourceHistory]` | `required` |
| `finite_reservoir_nozzle_coupling_ids` | `Mapping[str, str]` | `required` |
| `finite_reservoir_nozzle_state_owner_ids` | `Mapping[str, str]` | `required` |
| `finite_reservoir_nozzle_evidence_ids` | `Mapping[str, str]` | `required` |
| `cumulative_nozzle_mass_out_kg` | `Mapping[str, np.ndarray]` | `required` |
| `cumulative_nozzle_withdrawal_energy_j` | `Mapping[str, np.ndarray]` | `required` |
| `clock_id` | `str` | `required` |
| `eos_identity` | `str` | `required` |
| `property_basis` | `PropertyBasis` | `required` |
| `maximum_cfl` | `float` | `required` |
| `cfl_limit` | `float` | `required` |

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


<a id="module-h2physics-caloric_pipe_finite_wall-simulate_caloric_pipe_with_finite_wall"></a>

## 배관 기체와 유한 열용량 벽의 열응답 결합 / Pipe gas coupled to finite wall thermal storage

Family / navigation ID: `equipment.gas_pipe`

Import module: `h2physics.caloric_pipe_finite_wall`; selected entry: `simulate_caloric_pipe_with_finite_wall`.

#### `h2physics.caloric_pipe_finite_wall.simulate_caloric_pipe_with_finite_wall`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/caloric_pipe_finite_wall.py#L177)

Advance gas and a single lumped wall node on caller output intervals.

Per interval, wall temperature is frozen for the existing gas integration;
its temperature then changes by ``-Q_gas/C_wall``. Ambient exchange is
integrated exactly for a constant ambient temperature and UA over that
interval. Refine ``time_samples_s`` until split-step sensitivity is small.

```python
simulate_caloric_pipe_with_finite_wall(model: CaloricPipeWaveModel, *, wall: LumpedPipeWall, initial_pressure_pa: Sequence[float], initial_temperature_k: Sequence[float], initial_velocity_m_s: Sequence[float], time_samples_s: Sequence[float], clock_id: str) -> FiniteWallCaloricPipeTrace
```

### Returned value / 반환값

`FiniteWallCaloricPipeTrace`

### Related input/return records / 관련 입력·반환 객체

#### `h2physics.caloric_pipe_waves.CaloricPipeWaveModel`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/caloric_pipe_waves.py#L373)

First-order finite-volume caloric gas pipe with a pluggable EOS.

The model uses uniform-area, horizontal, inviscid one-dimensional Euler
equations and a local Lax-Friedrichs/Rusanov flux. Closed ends are
reflective. Optional reservoir boundaries are caller-supplied fixed
ghost states and are not finite inventories. Optional Darcy friction and
fixed-wall heat sources are caller-evidenced; gravity, junctions and valves
remain outside this level.

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `length_m` | `float` | `required` |
| `internal_diameter_m` | `float` | `required` |
| `cell_count` | `int` | `required` |
| `eos` | `CaloricGasEOS` | `field(repr=False, compare=False)` |
| `maximum_cfl` | `float` | `0.35` |
| `maximum_internal_steps` | `int` | `1000000` |

Computed properties: `eos_identity`, `area_m2`, `cell_length_m`.

#### `h2physics.caloric_pipe_finite_wall.LumpedPipeWall`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/caloric_pipe_finite_wall.py#L36)

One perfectly mixed wall node representing the whole modeled pipe.

``heat_capacity_j_k`` is total wall heat capacity, not volumetric capacity.
Optional ambient exchange uses a caller-supplied total UA in W/K.

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `identifier` | `str` | `required` |
| `state_owner_id` | `str` | `required` |
| `state_evidence_id` | `str` | `required` |
| `clock_id` | `str` | `required` |
| `initial_temperature_k` | `float` | `required` |
| `heat_capacity_j_k` | `float` | `required` |
| `gas_heat_transfer_coefficient_w_m2_k` | `float` | `required` |
| `ambient_temperature_k` | `float &#124; None` | `None` |
| `ambient_ua_w_k` | `float` | `0.0` |
| `ambient_evidence_id` | `str &#124; None` | `None` |

#### `h2physics.caloric_pipe_finite_wall.FiniteWallCaloricPipeTrace`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/caloric_pipe_finite_wall.py#L82)

Outer-clock wall states and the underlying accepted gas segment traces.

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `time_s` | `np.ndarray` | `field(repr=False, compare=False)` |
| `wall_temperature_k` | `np.ndarray` | `field(repr=False, compare=False)` |
| `cumulative_wall_energy_change_j` | `np.ndarray` | `field(repr=False, compare=False)` |
| `cumulative_gas_wall_heat_into_gas_j` | `np.ndarray` | `field(repr=False, compare=False)` |
| `cumulative_ambient_heat_into_wall_j` | `np.ndarray` | `field(repr=False, compare=False)` |
| `combined_energy_balance_residual_j` | `np.ndarray` | `field(repr=False, compare=False)` |
| `gas_traces` | `tuple[CaloricPipeWaveTrace, ...]` | `required` |
| `wall` | `LumpedPipeWall` | `required` |
| `clock_id` | `str` | `required` |

#### `h2physics.caloric_pipe_waves.CaloricPipeWaveTrace`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/caloric_pipe_waves.py#L222)

Immutable states, boundary fluxes, and global mass/energy ledgers.

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `time_s` | `np.ndarray` | `field(repr=False, compare=False)` |
| `cell_center_m` | `np.ndarray` | `field(repr=False, compare=False)` |
| `pressure_pa` | `np.ndarray` | `field(repr=False, compare=False)` |
| `temperature_k` | `np.ndarray` | `field(repr=False, compare=False)` |
| `density_kg_m3` | `np.ndarray` | `field(repr=False, compare=False)` |
| `velocity_m_s` | `np.ndarray` | `field(repr=False, compare=False)` |
| `internal_energy_j_kg` | `np.ndarray` | `field(repr=False, compare=False)` |
| `face_mass_flow_kg_s` | `np.ndarray` | `field(repr=False, compare=False)` |
| `face_energy_flow_w` | `np.ndarray` | `field(repr=False, compare=False)` |
| `total_mass_kg` | `np.ndarray` | `field(repr=False, compare=False)` |
| `total_energy_j` | `np.ndarray` | `field(repr=False, compare=False)` |
| `cumulative_boundary_mass_in_kg` | `np.ndarray` | `field(repr=False, compare=False)` |
| `cumulative_boundary_energy_in_j` | `np.ndarray` | `field(repr=False, compare=False)` |
| `cumulative_wall_heat_in_j` | `np.ndarray` | `field(repr=False, compare=False)` |
| `darcy_factor_mean_by_interval` | `np.ndarray` | `field(repr=False, compare=False)` |
| `darcy_factor_max_by_interval` | `np.ndarray` | `field(repr=False, compare=False)` |
| `internal_steps_by_interval` | `np.ndarray` | `field(repr=False, compare=False)` |
| `mass_balance_residual_kg` | `np.ndarray` | `field(repr=False, compare=False)` |
| `energy_balance_residual_j` | `np.ndarray` | `field(repr=False, compare=False)` |
| `sound_speed_m_s` | `np.ndarray` | `field(repr=False, compare=False)` |
| `eos_identity` | `str` | `required` |
| `property_basis` | `PropertyBasis` | `required` |
| `pipe_length_m` | `float` | `required` |
| `internal_diameter_m` | `float` | `required` |
| `area_m2` | `float` | `required` |
| `maximum_cfl` | `float` | `required` |
| `cfl_limit` | `float` | `required` |
| `left_boundary_id` | `str &#124; None` | `None` |
| `right_boundary_id` | `str &#124; None` | `None` |
| `left_boundary_state_owner_id` | `str &#124; None` | `None` |
| `right_boundary_state_owner_id` | `str &#124; None` | `None` |
| `left_boundary_state_evidence_id` | `str &#124; None` | `None` |
| `right_boundary_state_evidence_id` | `str &#124; None` | `None` |
| `clock_id` | `str &#124; None` | `None` |
| `friction_law_id` | `str &#124; None` | `None` |
| `friction_state_owner_id` | `str &#124; None` | `None` |
| `friction_evidence_id` | `str &#124; None` | `None` |
| `friction_scheme` | `str &#124; None` | `None` |
| `wall_heat_boundary_id` | `str &#124; None` | `None` |
| `wall_heat_state_owner_id` | `str &#124; None` | `None` |
| `wall_heat_evidence_id` | `str &#124; None` | `None` |
| `wall_temperature_k` | `float &#124; None` | `None` |
| `heat_transfer_coefficient_w_m2_k` | `float &#124; None` | `None` |


<a id="module-h2physics-adapters-lh2dt_hydraulics-lh2dtdarcypipe-evaluate"></a>

## 단상·균질평형 이상 배관과 공통 Darcy 계산 연결 / Native state/HEM pipe binding to shared Darcy closure

Family / navigation ID: `equipment.two_phase_pipe`

Import module: `h2physics.adapters.lh2dt_hydraulics`; selected entry: `Lh2dtDarcyPipe.evaluate`.

#### `h2physics.adapters.lh2dt_hydraulics.Lh2dtDarcyPipe`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/lh2dt_hydraulics.py#L22)

Reuse native geometry/viscosity with an explicitly selected friction law.

Native thermal parameters and actual result factories remain available.
The selected correlation is a declared physical closure, never a fallback.

```python
Lh2dtDarcyPipe(native_pipe, bridge: Lh2dtProperties, *, viscosity_reader: Callable[[Any], float], friction_law: Callable[[float, float], float], friction_law_id: str, result_factory: Callable[..., Any])
```

Computed properties: `geometry`, `elevation_change_m`, `heat_into_fluid_w`.

#### `h2physics.adapters.lh2dt_hydraulics.Lh2dtDarcyPipe.evaluate`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/lh2dt_hydraulics.py#L56)

```python
evaluate(self, left, right)
```

The source has no explicit return annotation; inspect its return statements and the domain manual. No return type is invented by this generator.

### Returned value / 반환값

`DarcyPipeEvaluation`

This return contract was reviewed from the implementation; it is not an annotation present in the source signature.

### Related input/return records / 관련 입력·반환 객체

#### `h2physics.adapters.lh2dt_hydraulics.DarcyPipeEvaluation`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/lh2dt_hydraulics.py#L13)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `native` | `Any` | `required` |
| `hydraulic` | `DarcyFlowResult &#124; None` | `required` |
| `friction_law_id` | `str` | `required` |

#### `h2physics.hydraulics.DarcyFlowResult`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/hydraulics.py#L37)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `mass_flow_kg_s` | `float` | `required` |
| `velocity_m_s` | `float` | `required` |
| `reynolds_number` | `float` | `required` |
| `darcy_friction_factor` | `float` | `required` |
| `driving_pressure_pa` | `float` | `required` |
| `modeled_pressure_drop_pa` | `float` | `required` |
| `momentum_residual_pa` | `float` | `required` |
| `root_converged` | `bool` | `required` |
| `iterations` | `int` | `required` |


<a id="module-h2physics-adapters-lh2dt_equipment-lh2dtsharedvalve-evaluate"></a>

## 공통 노즐을 이용한 두 포트 밸브 감압 / Two-port throttling using the shared nozzle

Family / navigation ID: `equipment.valve`

Import module: `h2physics.adapters.lh2dt_equipment`; selected entry: `Lh2dtSharedValve.evaluate`.

#### `h2physics.adapters.lh2dt_equipment.Lh2dtSharedValve`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/lh2dt_equipment.py#L28)

Native two-port throttling interface using the one shared nozzle kernel.

Both remote ports have negligible kinetic energy; the downstream mixed
enthalpy equals upstream enthalpy. The nozzle-plane static/kinetic split
remains a separate source result and is not a downstream pipe state.

```python
Lh2dtSharedValve(nozzle: HomogeneousIsentropicNozzle, bridge: Lh2dtProperties, opening: NozzleOpening, *, result_factory: Callable[..., Any], opening_fraction: float, allow_reverse: bool)
```

#### `h2physics.adapters.lh2dt_equipment.Lh2dtSharedValve.evaluate`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/lh2dt_equipment.py#L52)

```python
evaluate(self, left, right)
```

The source has no explicit return annotation; inspect its return statements and the domain manual. No return type is invented by this generator.

### Returned value / 반환값

`SharedValveEvaluation`

This return contract was reviewed from the implementation; it is not an annotation present in the source signature.

### Related input/return records / 관련 입력·반환 객체

#### `h2physics.adapters.lh2dt_equipment.SharedValveEvaluation`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/lh2dt_equipment.py#L20)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `native` | `Any` | `required` |
| `nozzle` | `NozzleResult` | `required` |

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


<a id="module-h2physics-adapters-lh2dt_valve_actuator-finitestrokevalve-run"></a>

## 사용자 유량 맵에 따른 밸브 개도 과도응답 / Finite-stroke actuation with a caller-supplied flow map

Family / navigation ID: `equipment.valve`

Import module: `h2physics.adapters.lh2dt_valve_actuator`; selected entry: `FiniteStrokeValve.run`.

#### `h2physics.adapters.lh2dt_valve_actuator.FiniteStrokeValve`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/lh2dt_valve_actuator.py#L224)

Own one shared valve and apply finite stroke plus an admitted CdA map.

```python
FiniteStrokeValve(valve: Lh2dtSharedValve, actuator: StrokeActuator, area_map: ValveEffectiveAreaMap)
```

#### `h2physics.adapters.lh2dt_valve_actuator.FiniteStrokeValve.run`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/lh2dt_valve_actuator.py#L265)

```python
run(self, left_state, right_state, commands: Sequence[ValveCommand], sample_times_s: Sequence[float], *, clock_id: str) -> ActuatedValveTrace
```

### Returned value / 반환값

`ActuatedValveTrace`

### Related input/return records / 관련 입력·반환 객체

#### `h2physics.adapters.lh2dt_valve_actuator.StrokeActuator`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/lh2dt_valve_actuator.py#L116)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `actuator_id` | `str` | `required` |
| `opening_rate_fraction_s` | `float` | `required` |
| `closing_rate_fraction_s` | `float` | `required` |
| `initial_stroke_fraction` | `float` | `required` |
| `clock_id` | `str` | `required` |
| `evidence_id` | `str` | `required` |

#### `h2physics.adapters.lh2dt_valve_actuator.ValveEffectiveAreaMap`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/lh2dt_valve_actuator.py#L59)

Monotone stroke to relative effective-area data; no extrapolation.

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `map_id` | `str` | `required` |
| `stroke_fraction` | `tuple[float, ...]` | `required` |
| `effective_area_fraction` | `tuple[float, ...]` | `required` |
| `evidence` | `ValveMapEvidence` | `required` |

#### `h2physics.adapters.lh2dt_valve_actuator.ValveCommand`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/lh2dt_valve_actuator.py#L144)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `start_s` | `float` | `required` |
| `end_s` | `float` | `required` |
| `target_stroke_fraction` | `float` | `required` |
| `command_id` | `str` | `required` |
| `mode` | `Literal['operate', 'hold', 'isolate']` | `'operate'` |

#### `h2physics.adapters.lh2dt_valve_actuator.ActuatedValveTrace`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/lh2dt_valve_actuator.py#L184)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `actuator` | `StrokeActuator` | `required` |
| `area_map` | `ValveEffectiveAreaMap` | `required` |
| `commands` | `tuple[ValveCommand, ...]` | `required` |
| `points` | `tuple[ActuatedValvePoint, ...]` | `required` |
| `left_state` | `Any` | `field(repr=False, compare=False)` |
| `right_state` | `Any` | `field(repr=False, compare=False)` |
| `owner` | `Any` | `field(repr=False, compare=False)` |
| `input_sha256` | `str` | `required` |
| `output_sha256` | `str` | `required` |

#### `h2physics.adapters.lh2dt_valve_actuator.ValveMapEvidence`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/lh2dt_valve_actuator.py#L35)

Identity and interpretation of one caller-supplied effective-area map.

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `evidence_id` | `str` | `required` |
| `source_uri` | `str` | `required` |
| `license_id` | `str` | `required` |
| `source_sha256` | `str` | `required` |
| `fluid_basis` | `str` | `required` |
| `pressure_basis` | `Literal['absolute']` | `'absolute'` |
| `map_basis` | `Literal['CdA_ratio']` | `'CdA_ratio'` |
| `qualified_for_prediction` | `bool` | `False` |

#### `h2physics.adapters.lh2dt_valve_actuator.ActuatedValvePoint`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/lh2dt_valve_actuator.py#L167)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `time_s` | `float` | `required` |
| `command` | `ValveCommand` | `required` |
| `stroke_fraction` | `float` | `required` |
| `effective_opening_fraction` | `float` | `required` |
| `result` | `SharedValveEvaluation` | `field(repr=False, compare=False)` |

Computed properties: `mass_flow_kg_s`, `upstream_side`.


<a id="module-h2physics-adapters-lh2dt_relief-lh2dtrelieftankdriver-run"></a>

## 탱크 안전밸브 개방·재폐쇄와 방출 재고 계산 / Finite-tank relief opening/reseat with inventory accounting

Family / navigation ID: `equipment.relief`

Import module: `h2physics.adapters.lh2dt_relief`; selected entry: `Lh2dtReliefTankDriver.run`.

#### `h2physics.adapters.lh2dt_relief.Lh2dtReliefTankDriver`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/lh2dt_relief.py#L370)

Partition actual native tank integration at bracketed physical pressure events.

Every candidate/replay uses HomogeneousTank.simulate with a frozen accepted
latch. Native RK4 owns fluid/wall states and its boundary ledger. Endpoint
bracketing detects the first resolved crossing; arbitrary hidden within-step
nonmonotonic excursions are outside this event-detection guarantee.

```python
Lh2dtReliefTankDriver(tank, protection: Lh2dtReliefProtection, *, flow_factory: Callable, state_factory: Callable, event_settings: ReliefEventSettings | None=None)
```

#### `h2physics.adapters.lh2dt_relief.Lh2dtReliefTankDriver.run`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/lh2dt_relief.py#L390)

```python
run(self, initial, *, duration_s: float, maximum_step_s: float, start_time_s: float, clock_id: str, boundary: ReliefTankBoundary, minimum_inventory_kg: float) -> ReliefTankTrace
```

### Returned value / 반환값

`ReliefTankTrace`

### Related input/return records / 관련 입력·반환 객체

#### `h2physics.adapters.lh2dt_relief.ReliefEventSettings`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/lh2dt_relief.py#L168)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `time_tolerance_s` | `float` | `1e-08` |
| `pressure_tolerance_pa` | `float` | `0.001` |
| `mass_tolerance_kg` | `float` | `1e-12` |
| `minimum_native_interval_s` | `float` | `1e-09` |
| `maximum_iterations` | `int` | `80` |
| `maximum_events` | `int` | `1000` |

#### `h2physics.adapters.lh2dt_relief.ReliefTankBoundary`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/lh2dt_relief.py#L143)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `clock_id` | `str` | `required` |
| `support_start_s` | `float` | `required` |
| `support_end_s` | `float` | `required` |
| `downstream` | `ThermoState` | `required` |
| `ambient_temperature_k` | `Callable` | `required` |
| `direct_wall_heat_w` | `Callable` | `required` |
| `source_id` | `str` | `required` |

#### `h2physics.adapters.lh2dt_relief.ReliefTankTrace`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/lh2dt_relief.py#L237)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `clock_id` | `str` | `required` |
| `initial_state` | `object` | `required` |
| `initial_source` | `SharedValveEvaluation` | `required` |
| `intervals` | `tuple[ReliefNativeInterval, ...]` | `required` |
| `transitions` | `tuple[ReliefTransition, ...]` | `required` |
| `time_s` | `np.ndarray` | `required` |
| `mass_residual_kg` | `np.ndarray` | `required` |
| `energy_residual_j` | `np.ndarray` | `required` |
| `released_mass_kg` | `np.ndarray` | `required` |
| `released_enthalpy_j` | `np.ndarray` | `required` |
| `external_heat_j` | `np.ndarray` | `required` |
| `native_tank` | `object` | `required` |
| `native_relief_origin` | `object` | `required` |
| `native_relief_final` | `object` | `required` |
| `termination` | `str` | `required` |
| `minimum_inventory_kg` | `float` | `required` |
| `trial_interval_count` | `int` | `required` |
| `event_settings` | `ReliefEventSettings` | `required` |
| `inventory_event` | `ReliefInventoryTermination &#124; None` | `required` |

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

#### `h2physics.adapters.lh2dt_equipment.SharedValveEvaluation`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/lh2dt_equipment.py#L20)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `native` | `Any` | `required` |
| `nozzle` | `NozzleResult` | `required` |

#### `h2physics.adapters.lh2dt_relief.ReliefNativeInterval`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/lh2dt_relief.py#L197)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `start_time_s` | `float` | `required` |
| `end_time_s` | `float` | `required` |
| `native_step` | `object` | `required` |
| `stages` | `tuple[ReliefStage, ...]` | `required` |
| `interval_is_open` | `bool` | `required` |
| `released_mass_kg` | `float` | `required` |
| `released_enthalpy_j` | `float` | `required` |
| `external_heat_j` | `float` | `required` |
| `source_at_start` | `SharedValveEvaluation` | `required` |
| `source_at_end` | `SharedValveEvaluation` | `required` |

#### `h2physics.adapters.lh2dt_relief.ReliefTransition`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/lh2dt_relief.py#L211)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `time_s` | `float` | `required` |
| `kind` | `str` | `required` |
| `pressure_pa` | `float` | `required` |
| `threshold_pa` | `float` | `required` |
| `lower_bracket_time_s` | `float` | `required` |
| `upper_bracket_time_s` | `float` | `required` |
| `native_before` | `object` | `required` |
| `native_after` | `object` | `required` |
| `source_before` | `SharedValveEvaluation` | `required` |
| `source_after` | `SharedValveEvaluation` | `required` |
| `native_tank_state` | `object` | `required` |

#### `h2physics.adapters.lh2dt_relief.ReliefInventoryTermination`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/lh2dt_relief.py#L226)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `time_s` | `float` | `required` |
| `mass_kg` | `float` | `required` |
| `minimum_inventory_kg` | `float` | `required` |
| `lower_bracket_time_s` | `float` | `required` |
| `upper_bracket_time_s` | `float` | `required` |
| `native_tank_state` | `object` | `required` |
| `source_at_limit` | `SharedValveEvaluation` | `required` |


<a id="module-h2physics-adapters-lh2dt_pump_operation-finitespeedpump-run"></a>

## 펌프 속도 명령·운전 맵·NPSH 조건 검사 / Pump speed commands, map and NPSH admission

Family / navigation ID: `equipment.pump`

Import module: `h2physics.adapters.lh2dt_pump_operation`; selected entry: `FiniteSpeedPump.run`.

#### `h2physics.adapters.lh2dt_pump_operation.FiniteSpeedPump`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/lh2dt_pump_operation.py#L233)

Apply finite speed commands to one original native mapped pump.

```python
FiniteSpeedPump(native_pump, actuator: PumpSpeedActuator, pump_map: NormalizedPumpMap)
```

#### `h2physics.adapters.lh2dt_pump_operation.FiniteSpeedPump.run`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/lh2dt_pump_operation.py#L278)

```python
run(self, left_state, right_state, commands: Sequence[PumpSpeedCommand], sample_times_s: Sequence[float], *, clock_id: str, require_qualified_map: bool=False, require_accepted: bool=True)
```

The source has no explicit return annotation; inspect its return statements and the domain manual. No return type is invented by this generator.

### Returned value / 반환값

`PumpOperationTrace`

This return contract was reviewed from the implementation; it is not an annotation present in the source signature.

### Related input/return records / 관련 입력·반환 객체

#### `h2physics.adapters.lh2dt_pump_operation.PumpOperationTrace`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/lh2dt_pump_operation.py#L189)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `actuator` | `PumpSpeedActuator` | `required` |
| `pump_map` | `NormalizedPumpMap` | `required` |
| `commands` | `tuple[PumpSpeedCommand, ...]` | `required` |
| `points` | `tuple[PumpOperatingPoint, ...]` | `required` |
| `left_state` | `Any` | `field(repr=False, compare=False)` |
| `right_state` | `Any` | `field(repr=False, compare=False)` |
| `owner` | `Any` | `field(repr=False, compare=False)` |
| `input_sha256` | `str` | `required` |
| `output_sha256` | `str` | `required` |

#### `h2physics.adapters.lh2dt_pump_operation.PumpSpeedActuator`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/lh2dt_pump_operation.py#L117)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `actuator_id` | `str` | `required` |
| `clock_id` | `str` | `required` |
| `initial_speed_fraction` | `float` | `required` |
| `ramp_up_fraction_s` | `float` | `required` |
| `ramp_down_fraction_s` | `float` | `required` |
| `evidence_id` | `str` | `required` |

#### `h2physics.adapters.lh2dt_pump_operation.NormalizedPumpMap`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/lh2dt_pump_operation.py#L58)

One reference-speed curve used only to admit native operating points.

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `map_id` | `str` | `required` |
| `reference_speed_rpm` | `float` | `required` |
| `reference_mass_flow_kg_s` | `float` | `required` |
| `reference_pressure_rise_pa` | `float` | `required` |
| `reference_npsh_required_m` | `float` | `required` |
| `flow_fraction` | `tuple[float, ...]` | `required` |
| `pressure_rise_fraction` | `tuple[float, ...]` | `required` |
| `efficiency` | `tuple[float, ...]` | `required` |
| `npsh_required_fraction` | `tuple[float, ...]` | `required` |
| `evidence` | `PumpMapEvidence` | `required` |
| `relative_admission_tolerance` | `float` | `1e-06` |

#### `h2physics.adapters.lh2dt_pump_operation.PumpSpeedCommand`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/lh2dt_pump_operation.py#L145)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `command_id` | `str` | `required` |
| `start_s` | `float` | `required` |
| `end_s` | `float` | `required` |
| `target_speed_fraction` | `float` | `required` |
| `mode` | `Literal['operate', 'hold', 'stop']` | `'operate'` |

#### `h2physics.adapters.lh2dt_pump_operation.PumpMapEvidence`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/lh2dt_pump_operation.py#L36)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `evidence_id` | `str` | `required` |
| `source_uri` | `str` | `required` |
| `license_id` | `str` | `required` |
| `source_sha256` | `str` | `required` |
| `fluid_basis` | `str` | `required` |
| `pressure_basis` | `Literal['absolute']` | `'absolute'` |
| `flow_basis` | `Literal['mass']` | `'mass'` |
| `qualified_for_prediction` | `bool` | `False` |

#### `h2physics.adapters.lh2dt_pump_operation.PumpOperatingPoint`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/lh2dt_pump_operation.py#L168)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `time_s` | `float` | `required` |
| `receiver_pressure_pa` | `float` | `required` |
| `command` | `PumpSpeedCommand` | `required` |
| `speed_fraction` | `float` | `required` |
| `reduced_flow_fraction` | `float` | `required` |
| `expected_pressure_rise_pa` | `float` | `required` |
| `expected_npsh_required_m` | `float` | `required` |
| `pressure_rise_relative_error` | `float` | `required` |
| `npsh_relative_error` | `float` | `required` |
| `npsh_margin_m` | `float` | `required` |
| `capacity_admissible` | `bool` | `required` |
| `npsh_admissible` | `bool` | `required` |
| `native_result` | `Any` | `field(repr=False, compare=False)` |

Computed properties: `accepted`.


<a id="module-h2physics-adapters-lh2dt_compressor-lh2dtcompressiontrain-evaluate"></a>

## 다단 기체 압축과 지정 중간 냉각의 동력·열량 / Gas compression stages and prescribed intercooling

Family / navigation ID: `equipment.compressor`

Import module: `h2physics.adapters.lh2dt_compressor`; selected entry: `Lh2dtCompressionTrain.evaluate`.

#### `h2physics.adapters.lh2dt_compressor.Lh2dtCompressionTrain`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/lh2dt_compressor.py#L648)

Serial native stages with explicitly prescribed inter/aftercooling.

```python
Lh2dtCompressionTrain(stages: Sequence[Lh2dtCompressorStage], *, intercoolers: Sequence[PrescribedIntercooling | None]=(), aftercooler: PrescribedIntercooling | None=None, train_id: str)
```

Computed properties: `basis`.

#### `h2physics.adapters.lh2dt_compressor.Lh2dtCompressionTrain.evaluate`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/lh2dt_compressor.py#L720)

```python
evaluate(self, inlet: ThermoState, mass_flow_kg_s: float, *, mode: Literal['compressing', 'isolated']='compressing', finite_source: CompressorFiniteSource | None=None) -> CompressionTrainResult
```

### Returned value / 반환값

`CompressionTrainResult`

### Related input/return records / 관련 입력·반환 객체

#### `h2physics.adapters.lh2dt_compressor.PrescribedIntercooling`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/lh2dt_compressor.py#L574)

Specified outlet PT and pressure loss; no exchanger/utility prediction.

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `boundary_id` | `str` | `required` |
| `outlet_temperature_k` | `float` | `required` |
| `pressure_drop_pa` | `float` | `required` |
| `evidence_id` | `str` | `required` |

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

#### `h2physics.adapters.lh2dt_compressor.CompressorFiniteSource`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/lh2dt_compressor.py#L146)

Caller-declared accepted native snapshot; no acceptance replay or withdrawal.

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `source_id` | `str` | `required` |
| `clock_id` | `str` | `required` |
| `time_s` | `float` | `required` |
| `local_time_origin_s` | `float` | `required` |
| `clock_tolerance_s` | `float` | `required` |
| `node_id` | `str` | `required` |
| `native_owner` | `object` | `required` |
| `native_step` | `object` | `required` |
| `native_state` | `object` | `required` |
| `fluid` | `ThermoState` | `required` |
| `mass_kg` | `float` | `required` |
| `fluid_internal_energy_j` | `float` | `required` |
| `provenance` | `Lh2dtNativeProvenance` | `required` |

#### `h2physics.adapters.lh2dt_compressor.CompressionTrainResult`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/lh2dt_compressor.py#L610)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `train_id` | `str` | `required` |
| `mode` | `str` | `required` |
| `inlet` | `ThermoState` | `required` |
| `outlet` | `ThermoState &#124; None` | `required` |
| `mass_flow_kg_s` | `float` | `required` |
| `stages` | `tuple[CompressorStageResult, ...]` | `required` |
| `intercooling` | `tuple[IntercoolingResult, ...]` | `required` |
| `transfers` | `tuple[ConnectionTransfer, ...]` | `required` |
| `power` | `BoundaryPower` | `required` |
| `pressure_basis` | `str` | `'Pa_absolute'` |

Computed properties: `mass_residual_kg_s`, `energy_residual_w`, `native_components`, `native_stage_results`.

#### `h2physics.core.PropertyBasis`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/core.py#L97)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `fluid` | `str` | `required` |
| `reference_id` | `str` | `required` |
| `spin_composition` | `str` | `'unspecified'` |

#### `h2physics.adapters.lh2dt_compressor.Lh2dtNativeProvenance`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/lh2dt_compressor.py#L72)

Exact installed native source and original public callable bindings.

Capture reads source bytes only; it never imports the optional engine.
Caller property facades are bound separately and are not native-source attestation.

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `source_directory` | `Path` | `required` |
| `revision` | `str` | `required` |
| `package_sha256` | `str` | `required` |
| `files` | `tuple` | `required` |
| `bindings` | `tuple` | `field(repr=False)` |

Computed properties: `source_url`, `license_id`.

#### `h2physics.adapters.lh2dt_compressor.CompressorStageResult`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/lh2dt_compressor.py#L226)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `stage_id` | `str` | `required` |
| `mode` | `str` | `required` |
| `inlet` | `ThermoState` | `required` |
| `outlet` | `ThermoState &#124; None` | `required` |
| `mass_flow_kg_s` | `float` | `required` |
| `pressure_ratio` | `float` | `required` |
| `isentropic_efficiency` | `float` | `required` |
| `isentropic_outlet` | `ThermoState &#124; None` | `required` |
| `transfer` | `ConnectionTransfer` | `required` |
| `native_component` | `Any` | `required` |
| `native_result` | `Any &#124; None` | `required` |
| `native_inlet` | `Any &#124; None` | `required` |
| `native_isentropic_outlet` | `Any &#124; None` | `required` |
| `model_id` | `str` | `'lh2dt-native-adiabatic-compressor-operating-point'` |
| `native_provenance` | `Lh2dtNativeProvenance &#124; None` | `None` |
| `finite_source` | `CompressorFiniteSource &#124; None` | `None` |
| `source_boundary` | `str` | `'prescribed-steady-inlet-no-source-inventory'` |
| `pressure_basis` | `str` | `'Pa_absolute'` |

Computed properties: `power`, `energy_residual_w`.

#### `h2physics.adapters.lh2dt_compressor.IntercoolingResult`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/lh2dt_compressor.py#L591)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `specification` | `PrescribedIntercooling` | `required` |
| `inlet` | `ThermoState` | `required` |
| `outlet` | `ThermoState` | `required` |
| `mass_flow_kg_s` | `float` | `required` |
| `transfer` | `ConnectionTransfer` | `required` |
| `native_outlet` | `Any` | `required` |
| `native_properties` | `Any` | `required` |

Computed properties: `power`, `energy_residual_w`.

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

#### `h2physics.equipment.BoundaryPower`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/equipment.py#L14)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `heat_w` | `float` | `0.0` |
| `shaft_work_w` | `float` | `0.0` |

Computed properties: `total_w`.


<a id="module-h2physics-adapters-compressor_map-mappedcompressor-evaluate"></a>

## 사용자 압축기 맵 기반 운전영역 검사 / Caller-map operating-envelope admission

Family / navigation ID: `equipment.compressor`

Import module: `h2physics.adapters.compressor_map`; selected entry: `MappedCompressor.evaluate`.

#### `h2physics.adapters.compressor_map.MappedCompressor`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/compressor_map.py#L167)

Admit scheduled native stage points against a caller-owned map envelope.

```python
MappedCompressor(stage: Lh2dtCompressorStage, operating_map: CompressorOperatingMap)
```

#### `h2physics.adapters.compressor_map.MappedCompressor.evaluate`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/compressor_map.py#L201)

```python
evaluate(self, inlet: ThermoState, commands, *, clock_id: str, upstream_node: str | None=None, downstream_node: str | None=None)
```

The source has no explicit return annotation; inspect its return statements and the domain manual. No return type is invented by this generator.

### Returned value / 반환값

`MappedCompressorTrace`

This return contract was reviewed from the implementation; it is not an annotation present in the source signature.

### Related input/return records / 관련 입력·반환 객체

#### `h2physics.adapters.compressor_map.MappedCompressorTrace`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/compressor_map.py#L155)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `clock_id` | `str` | `required` |
| `points` | `tuple[MappedCompressorPoint, ...]` | `required` |
| `map_id` | `str` | `required` |
| `evidence_id` | `str` | `required` |

#### `h2physics.adapters.compressor_map.CompressorOperatingMap`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/compressor_map.py#L79)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `map_id` | `str` | `required` |
| `reference_temperature_k` | `float` | `required` |
| `reference_pressure_pa` | `float` | `required` |
| `lines` | `tuple[CompressorMapLine, ...]` | `required` |
| `evidence` | `CompressorMapEvidence` | `required` |

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

#### `h2physics.adapters.compressor_map.CompressorMapLine`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/compressor_map.py#L41)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `corrected_speed_rad_s` | `float` | `required` |
| `minimum_corrected_flow_kg_s` | `float` | `required` |
| `maximum_corrected_flow_kg_s` | `float` | `required` |
| `minimum_pressure_ratio` | `float` | `required` |
| `maximum_pressure_ratio` | `float` | `required` |
| `minimum_isentropic_efficiency` | `float` | `required` |
| `maximum_isentropic_efficiency` | `float` | `required` |

#### `h2physics.adapters.compressor_map.CompressorMapEvidence`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/compressor_map.py#L23)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `evidence_id` | `str` | `required` |
| `source_uri` | `str` | `required` |
| `license_id` | `str` | `required` |
| `source_sha256` | `str` | `required` |
| `pressure_basis` | `str` | `'absolute'` |
| `flow_basis` | `str` | `'inlet_mass_flow'` |

#### `h2physics.core.PropertyBasis`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/core.py#L97)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `fluid` | `str` | `required` |
| `reference_id` | `str` | `required` |
| `spin_composition` | `str` | `'unspecified'` |

#### `h2physics.adapters.compressor_map.MappedCompressorPoint`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/compressor_map.py#L146)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `command` | `CompressorCommand` | `required` |
| `corrected_flow_kg_s` | `float &#124; None` | `required` |
| `corrected_speed_rad_s` | `float &#124; None` | `required` |
| `limits` | `CompressorMapLimits &#124; None` | `required` |
| `native_result` | `CompressorStageResult` | `required` |


<a id="module-h2physics-adapters-compressor_anti_surge-compressorantisurgeguard-evaluate"></a>

## 운전점과 서지선 간 정적 여유 검사 / Static source-bound surge-margin screening

Family / navigation ID: `equipment.compressor`

Import module: `h2physics.adapters.compressor_anti_surge`; selected entry: `CompressorAntiSurgeGuard.evaluate`.

#### `h2physics.adapters.compressor_anti_surge.CompressorAntiSurgeGuard`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/compressor_anti_surge.py#L142)

Check a map trace against an explicit static boundary and margin policy.

```python
CompressorAntiSurgeGuard(boundary: SurgeBoundary, policy: AntiSurgeMarginPolicy)
```

#### `h2physics.adapters.compressor_anti_surge.CompressorAntiSurgeGuard.evaluate`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/compressor_anti_surge.py#L171)

```python
evaluate(self, compressor_trace: MappedCompressorTrace) -> AntiSurgeTrace
```

### Returned value / 반환값

`AntiSurgeTrace`

### Related input/return records / 관련 입력·반환 객체

#### `h2physics.adapters.compressor_anti_surge.SurgeBoundary`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/compressor_anti_surge.py#L54)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `boundary_id` | `str` | `required` |
| `points` | `tuple[SurgeLinePoint, ...]` | `required` |
| `evidence` | `SurgeBoundaryEvidence` | `required` |

#### `h2physics.adapters.compressor_anti_surge.AntiSurgeMarginPolicy`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/compressor_anti_surge.py#L85)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `policy_id` | `str` | `required` |
| `minimum_corrected_flow_margin_kg_s` | `float` | `required` |
| `evidence_id` | `str` | `required` |
| `tolerance_kg_s` | `float` | `0.0` |

#### `h2physics.adapters.compressor_map.MappedCompressorTrace`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/compressor_map.py#L155)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `clock_id` | `str` | `required` |
| `points` | `tuple[MappedCompressorPoint, ...]` | `required` |
| `map_id` | `str` | `required` |
| `evidence_id` | `str` | `required` |

#### `h2physics.adapters.compressor_anti_surge.AntiSurgeTrace`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/compressor_anti_surge.py#L118)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `compressor_trace` | `MappedCompressorTrace` | `required` |
| `boundary` | `SurgeBoundary` | `required` |
| `policy` | `AntiSurgeMarginPolicy` | `required` |
| `points` | `tuple[AntiSurgePoint, ...]` | `required` |

Computed properties: `feasible`.

#### `h2physics.adapters.compressor_anti_surge.SurgeLinePoint`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/compressor_anti_surge.py#L44)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `corrected_speed_rad_s` | `float` | `required` |
| `corrected_surge_flow_kg_s` | `float` | `required` |

#### `h2physics.adapters.compressor_anti_surge.SurgeBoundaryEvidence`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/compressor_anti_surge.py#L22)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `evidence_id` | `str` | `required` |
| `source_uri` | `str` | `required` |
| `license_id` | `str` | `required` |
| `source_sha256` | `str` | `required` |
| `speed_basis` | `str` | `'corrected_speed_rad_s'` |
| `flow_basis` | `str` | `'corrected_inlet_mass_flow_kg_s'` |

#### `h2physics.adapters.compressor_map.MappedCompressorPoint`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/compressor_map.py#L146)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `command` | `CompressorCommand` | `required` |
| `corrected_flow_kg_s` | `float &#124; None` | `required` |
| `corrected_speed_rad_s` | `float &#124; None` | `required` |
| `limits` | `CompressorMapLimits &#124; None` | `required` |
| `native_result` | `CompressorStageResult` | `required` |

#### `h2physics.adapters.compressor_anti_surge.AntiSurgePoint`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/compressor_anti_surge.py#L104)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `time_s` | `float` | `required` |
| `mode` | `str` | `required` |
| `corrected_speed_rad_s` | `float &#124; None` | `required` |
| `corrected_flow_kg_s` | `float &#124; None` | `required` |
| `surge_flow_kg_s` | `float &#124; None` | `required` |
| `flow_margin_kg_s` | `float &#124; None` | `required` |
| `required_margin_kg_s` | `float` | `required` |
| `applicable` | `bool` | `required` |
| `admissible` | `bool` | `required` |
| `native_result` | `object` | `field(repr=False, compare=False)` |


<a id="module-h2physics-adapters-counterflow_heat_exchanger-counterflowheatexchanger-solve"></a>

## 정상 공간 분할 대향류 열교환 / Steady spatial counterflow heat exchange

Family / navigation ID: `equipment.heat_exchanger`

Import module: `h2physics.adapters.counterflow_heat_exchanger`; selected entry: `CounterflowHeatExchanger.solve`.

#### `h2physics.adapters.counterflow_heat_exchanger.CounterflowHeatExchanger`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/counterflow_heat_exchanger.py#L152)

Solve cell-centred UA heat exchange using enthalpy as the primary state.

``state_ph(pressure_pa_absolute, enthalpy_j_kg)`` must return an object with
finite ``temperature_k``. The caller retains ownership of phase selection,
mixtures and property reference conventions.

```python
CounterflowHeatExchanger(definition: CounterflowDefinition, *, hot_state_ph: Callable, cold_state_ph: Callable, domain: CounterflowDomain, equation_relative_tolerance: float=1e-09, energy_absolute_tolerance_w: float=1e-06, maximum_evaluations: int=2000)
```

#### `h2physics.adapters.counterflow_heat_exchanger.CounterflowHeatExchanger.solve`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/counterflow_heat_exchanger.py#L216)

```python
solve(self, boundary: CounterflowBoundary) -> CounterflowResult
```

### Returned value / 반환값

`CounterflowResult`

### Related input/return records / 관련 입력·반환 객체

#### `h2physics.adapters.counterflow_heat_exchanger.CounterflowDefinition`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/counterflow_heat_exchanger.py#L62)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `equipment_id` | `str` | `required` |
| `hot_stream_id` | `str` | `required` |
| `cold_stream_id` | `str` | `required` |
| `conductance_w_k` | `tuple[float, ...]` | `required` |
| `conductance_source_id` | `str` | `required` |
| `area_coordinate_source_id` | `str` | `required` |

#### `h2physics.adapters.counterflow_heat_exchanger.CounterflowDomain`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/counterflow_heat_exchanger.py#L40)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `minimum_temperature_k` | `float` | `required` |
| `maximum_temperature_k` | `float` | `required` |
| `minimum_enthalpy_j_kg` | `float` | `required` |
| `maximum_enthalpy_j_kg` | `float` | `required` |
| `evidence_id` | `str` | `required` |

#### `h2physics.adapters.counterflow_heat_exchanger.CounterflowBoundary`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/counterflow_heat_exchanger.py#L88)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `hot_mass_flow_kg_s` | `float` | `required` |
| `cold_mass_flow_kg_s` | `float` | `required` |
| `hot_inlet_enthalpy_j_kg` | `float` | `required` |
| `cold_inlet_enthalpy_j_kg` | `float` | `required` |
| `hot_pressure_pa_absolute` | `tuple[float, ...]` | `required` |
| `cold_pressure_pa_absolute` | `tuple[float, ...]` | `required` |
| `source_id` | `str` | `required` |

#### `h2physics.adapters.counterflow_heat_exchanger.CounterflowResult`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/counterflow_heat_exchanger.py#L109)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `definition` | `CounterflowDefinition` | `required` |
| `boundary` | `CounterflowBoundary` | `required` |
| `hot_enthalpy_j_kg` | `np.ndarray` | `required` |
| `cold_enthalpy_j_kg` | `np.ndarray` | `required` |
| `hot_temperature_k` | `np.ndarray` | `required` |
| `cold_temperature_k` | `np.ndarray` | `required` |
| `cell_heat_w` | `np.ndarray` | `required` |
| `hot_heat_loss_w` | `float` | `required` |
| `cold_heat_gain_w` | `float` | `required` |
| `global_energy_residual_w` | `float` | `required` |
| `maximum_equation_residual` | `float` | `required` |
| `solver_evaluations` | `int` | `required` |
| `solver_message` | `str` | `required` |
| `pressure_basis` | `str` | `'Pa_absolute'` |
| `coordinate` | `str` | `'hot-inlet-to-hot-outlet; cold-flow-direction-is-reversed'` |


<a id="module-h2physics-adapters-lh2dt_heat_exchanger-lh2dtfiniteheatexchanger-run"></a>

## 양측 유체·벽의 유한 열저장·열교환 과도응답 / Finite two-side fluid/wall thermal storage

Family / navigation ID: `equipment.heat_exchanger`

Import module: `h2physics.adapters.lh2dt_heat_exchanger`; selected entry: `Lh2dtFiniteHeatExchanger.run`.

#### `h2physics.adapters.lh2dt_heat_exchanger.Lh2dtFiniteHeatExchanger`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/lh2dt_heat_exchanger.py#L286)

One native simultaneous integration of two sealed finite fluid/wall sides.

The native ambient-temperature argument is connected to the other current
wall, with equal native ambient_UA values. It is not an infinite heat bath.
No physical fluid/wall equation, heat law or RK combiner is reproduced here.

A port-free native network is integrator plumbing only; its representative
thermodynamic boundary is the left side, never a combined hydraulic state.
All physical side states/bases are returned separately. Material links and
external heat leakage are deliberately unavailable in this closed level.

```python
Lh2dtFiniteHeatExchanger(left: FiniteHeatExchangerSide, right: FiniteHeatExchangerSide, coupling: HeatExchangerCoupling, *, native_side_node_factory: Callable, native_network_factory: Callable, native_simulator_factory: Callable, equipment_id: str, inventory_tolerances: InventoryTolerances | None=None, heat_rate_tolerance_w: float=1e-09)
```

#### `h2physics.adapters.lh2dt_heat_exchanger.Lh2dtFiniteHeatExchanger.run`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/lh2dt_heat_exchanger.py#L391)

```python
run(self, *, duration_s: float, maximum_step_s: float, start_time_s: float, clock_id: str, clock_tolerance_s: float=1e-10) -> HeatExchangerTrace
```

### Returned value / 반환값

`HeatExchangerTrace`

### Related input/return records / 관련 입력·반환 객체

#### `h2physics.adapters.lh2dt_heat_exchanger.FiniteHeatExchangerSide`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/lh2dt_heat_exchanger.py#L65)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `side_id` | `str` | `required` |
| `native_component` | `object` | `required` |
| `initial_native_state` | `object` | `required` |
| `bridge` | `Lh2dtProperties` | `required` |
| `domain` | `HeatExchangerDomain` | `required` |
| `initial_source_id` | `str` | `required` |

#### `h2physics.adapters.lh2dt_heat_exchanger.HeatExchangerCoupling`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/lh2dt_heat_exchanger.py#L84)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `conductance_w_k` | `float` | `required` |
| `parameter_source_id` | `str` | `required` |
| `origin` | `Origin` | `required` |
| `native_source_id` | `str` | `required` |

#### `h2physics.dynamics.InventoryTolerances`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/dynamics.py#L33)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `mass_absolute_kg` | `float` | `1e-08` |
| `energy_absolute_j` | `float` | `0.0001` |
| `relative` | `float` | `1e-08` |

#### `h2physics.adapters.lh2dt_heat_exchanger.HeatExchangerTrace`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/lh2dt_heat_exchanger.py#L145)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `clock_id` | `str` | `required` |
| `requested_start_s` | `float` | `required` |
| `requested_end_s` | `float` | `required` |
| `coupling` | `HeatExchangerCoupling` | `required` |
| `points` | `tuple[HeatExchangerPoint, ...]` | `required` |
| `native_simulator` | `object` | `required` |
| `native_network` | `object` | `required` |
| `native_side_nodes` | `tuple` | `required` |
| `native_composite_node` | `object` | `required` |
| `native_components` | `tuple` | `required` |
| `evaluated_clock_bounds_s` | `tuple[float, float]` | `required` |
| `native_evaluation_count` | `int` | `required` |
| `inventory_tolerances` | `InventoryTolerances` | `required` |
| `source_boundary` | `str` | `'closed-two-finite-fluids-no-material-ports-no-external-heat'` |
| `clock_tolerance_s` | `float` | `1e-10` |
| `pressure_basis` | `str` | `'Pa_absolute'` |
| `native_provenance` | `Lh2dtNativeProvenance &#124; None` | `None` |
| `finite_sides` | `tuple[FiniteHeatExchangerSide, ...]` | `()` |

Computed properties: `time_s`.

#### `h2physics.adapters.lh2dt_heat_exchanger.HeatExchangerDomain`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/lh2dt_heat_exchanger.py#L32)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `minimum_temperature_k` | `float` | `required` |
| `maximum_temperature_k` | `float` | `required` |
| `minimum_pressure_pa` | `float` | `required` |
| `maximum_pressure_pa` | `float` | `required` |
| `minimum_inventory_kg` | `float` | `required` |
| `allowed_phases` | `tuple[str, ...]` | `required` |

#### `h2physics.adapters.lh2dt_heat_exchanger.HeatExchangerPoint`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/lh2dt_heat_exchanger.py#L132)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `time_s` | `float` | `required` |
| `sides` | `Mapping[str, HeatExchangerSideSnapshot]` | `required` |
| `global_energy_residual_j` | `float` | `required` |
| `integrated_coupling_residual_j` | `float` | `required` |
| `native_composite_state` | `HeatExchangerCompositeState` | `required` |
| `native_step` | `object &#124; None` | `required` |

#### `h2physics.adapters.lh2dt_compressor.Lh2dtNativeProvenance`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/lh2dt_compressor.py#L72)

Exact installed native source and original public callable bindings.

Capture reads source bytes only; it never imports the optional engine.
Caller property facades are bound separately and are not native-source attestation.

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `source_directory` | `Path` | `required` |
| `revision` | `str` | `required` |
| `package_sha256` | `str` | `required` |
| `files` | `tuple` | `required` |
| `bindings` | `tuple` | `field(repr=False)` |

Computed properties: `source_url`, `license_id`.


<a id="module-h2physics-adapters-lh2dt_reliquefier-lh2dtsteadyreliquefier-evaluate"></a>

## 냉각 용량 제한을 고려한 포화 냉각·액상 생산 / Capacity-limited saturation cooling and liquid production

Family / navigation ID: `equipment.reliquefier`

Import module: `h2physics.adapters.lh2dt_reliquefier`; selected entry: `Lh2dtSteadyReliquefier.evaluate`.

#### `h2physics.adapters.lh2dt_reliquefier.Lh2dtSteadyReliquefier`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/lh2dt_reliquefier.py#L210)

Capacity-limited native cooling point; no hydraulic/cycle performance law.

```python
Lh2dtSteadyReliquefier(native, bridge: Lh2dtProperties, *, state_factory: Callable, domain: ReliquefactionDomain, component_id: str, tolerances: EquipmentTolerances | None=None)
```

#### `h2physics.adapters.lh2dt_reliquefier.Lh2dtSteadyReliquefier.evaluate`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/lh2dt_reliquefier.py#L221)

```python
evaluate(self, inlet: ThermoState, *, outlet_pressure_pa: float, mass_flow_kg_s: float, target_quality: float=0.0) -> SteadyReliquefierResult
```

### Returned value / 반환값

`SteadyReliquefierResult`

### Related input/return records / 관련 입력·반환 객체

#### `h2physics.adapters.lh2dt_reliquefier.ReliquefactionDomain`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/lh2dt_reliquefier.py#L41)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `minimum_pressure_pa` | `float` | `required` |
| `maximum_pressure_pa` | `float` | `required` |
| `minimum_temperature_k` | `float` | `required` |
| `maximum_temperature_k` | `float` | `required` |
| `evidence_id` | `str` | `required` |

#### `h2physics.equipment.EquipmentTolerances`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/equipment.py#L87)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `mass_absolute_kg_s` | `float` | `1e-08` |
| `energy_absolute_w` | `float` | `0.05` |
| `momentum_absolute_pa` | `float` | `0.01` |
| `relative` | `float` | `1e-06` |

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

#### `h2physics.adapters.lh2dt_reliquefier.SteadyReliquefierResult`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/lh2dt_reliquefier.py#L159)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `inlet` | `ThermoState` | `required` |
| `outlet` | `ThermoState` | `required` |
| `target_quality` | `float` | `required` |
| `transfer` | `ConnectionTransfer` | `required` |
| `inlet_liquid_mass_fraction` | `float &#124; None` | `required` |
| `outlet_liquid_mass_fraction` | `float` | `required` |
| `net_liquid_production_kg_s` | `float &#124; None` | `required` |
| `native_component` | `Any` | `required` |
| `native_inlet` | `Any` | `required` |
| `native_result` | `Any` | `required` |

Computed properties: `power`, `liquid_outflow_kg_s`, `capacity_limited`, `energy_residual_w`.

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


<a id="module-h2physics-adapters-lh2dt_vent-lh2dtventstack-evaluate"></a>

## 저마하 벤트 유량·압력손실·열전달 / Low-Mach vent hydraulics and enthalpy transfer

Family / navigation ID: `equipment.vent`

Import module: `h2physics.adapters.lh2dt_vent`; selected entry: `Lh2dtVentStack.evaluate`.

#### `h2physics.adapters.lh2dt_vent.Lh2dtVentStack`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/lh2dt_vent.py#L114)

Actual native stack evaluation with independent pressure/thermal gates.

Returned outlet is a downstream-pressure PH transport state. It has no
inferred discharge velocity, source plane, choking state or atmospheric area.

```python
Lh2dtVentStack(native_stack, bridge: Lh2dtProperties, *, state_factory: Callable, envelope: VentEnvelope, component_id: str, evidence_id: str, allow_reverse: bool, viscosity_reader: Callable[[Any], float], sound_speed_reader: Callable[[Any], float], sound_speed_capability_id: str, hydraulic_pipe: Lh2dtDarcyPipe | None=None, tolerances: EquipmentTolerances | None=None, thermal_ua_relative_tolerance: float=1e-05, thermal_ua_absolute_tolerance_w_k: float=1e-08)
```

#### `h2physics.adapters.lh2dt_vent.Lh2dtVentStack.evaluate`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/lh2dt_vent.py#L202)

```python
evaluate(self, left: ThermoState, right: ThermoState, *, left_node: str, right_node: str, left_port_id: str, right_port_id: str) -> VentResult
```

### Returned value / 반환값

`VentResult`

### Related input/return records / 관련 입력·반환 객체

#### `h2physics.adapters.lh2dt_vent.VentEnvelope`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/lh2dt_vent.py#L22)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `minimum_pressure_pa` | `float` | `required` |
| `maximum_pressure_pa` | `float` | `required` |
| `minimum_temperature_k` | `float` | `required` |
| `maximum_temperature_k` | `float` | `required` |
| `maximum_pressure_fraction` | `float` | `required` |
| `maximum_density_change_fraction` | `float` | `required` |
| `maximum_mach_number` | `float` | `required` |
| `evidence_id` | `str` | `required` |

#### `h2physics.equipment.EquipmentTolerances`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/equipment.py#L87)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `mass_absolute_kg_s` | `float` | `1e-08` |
| `energy_absolute_w` | `float` | `0.05` |
| `momentum_absolute_pa` | `float` | `0.01` |
| `relative` | `float` | `1e-06` |

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

#### `h2physics.adapters.lh2dt_vent.VentResult`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/lh2dt_vent.py#L66)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `transfer` | `ConnectionTransfer` | `required` |
| `left` | `ThermoState` | `required` |
| `right` | `ThermoState` | `required` |
| `outlet` | `ThermoState &#124; None` | `required` |
| `native_outlet` | `Any &#124; None` | `required` |
| `native_stack` | `Any` | `required` |
| `original_native_stack` | `Any` | `required` |
| `native_result` | `Any` | `required` |
| `hydraulic_result` | `Any` | `required` |
| `friction_law_id` | `str` | `required` |
| `oriented_native_heat_w` | `float` | `required` |
| `independent_momentum_residual_pa` | `float &#124; None` | `required` |
| `thermal_audit` | `VentThermalAudit` | `required` |
| `direction_blocked` | `bool` | `required` |
| `evidence_id` | `str` | `required` |
| `potential_energy_change_j_kg` | `float &#124; None` | `None` |
| `upstream_hydraulic_kinetic_energy_j_kg` | `float &#124; None` | `None` |
| `upstream_mach_number` | `float &#124; None` | `None` |
| `downstream_section_mach_number` | `float &#124; None` | `None` |
| `energy_scope` | `str` | `'steady enthalpy transport; port kinetic/potential energy changes unresolved'` |
| `mach_scope` | `str` | `'upstream hydraulics and same-bore downstream pipe-section estimate; not an atmospheric plane'` |

Computed properties: `power`.

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

#### `h2physics.adapters.lh2dt_vent.VentThermalAudit`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/lh2dt_vent.py#L57)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `configured_ua_w_k` | `float` | `required` |
| `reconstructed_ua_w_k` | `float &#124; None` | `required` |
| `residual_w_k` | `float &#124; None` | `required` |
| `quadrature_error_w_k` | `float &#124; None` | `required` |
| `status` | `str` | `required` |


<a id="module-h2physics-adapters-lh2dt_instrumentation-lh2dttransmitter-run"></a>

## 단위·위치가 명시된 계측기 지연 응답 / Native held-input transmitter response

Family / navigation ID: `equipment.instrument`

Import module: `h2physics.adapters.lh2dt_instrumentation`; selected entry: `Lh2dtTransmitter.run`.

#### `h2physics.adapters.lh2dt_instrumentation.Lh2dtTransmitter`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/lh2dt_instrumentation.py#L63)

Evaluate the actual native instrument over a caller-declared held trajectory.

At t[0], output reads the explicit initial native state. On (t[i],t[i+1])
the driver is process[i]; output at t[i+1] is its left limit. In particular,
the final process sample does not drive an additional unrecorded interval.
An initial state is never guessed from an assumed sensor steady state.

```python
Lh2dtTransmitter(native_transmitter, *, evidence: TransmitterEvidence)
```

#### `h2physics.adapters.lh2dt_instrumentation.Lh2dtTransmitter.run`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/lh2dt_instrumentation.py#L122)

```python
run(self, process: TimeSeries, *, channel: str, initial_native_state, initial_time_s: float, location_id: str) -> TransmitterTrace
```

### Returned value / 반환값

`TransmitterTrace`

### Related input/return records / 관련 입력·반환 객체

#### `h2physics.adapters.lh2dt_instrumentation.TransmitterEvidence`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/lh2dt_instrumentation.py#L17)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `instrument_id` | `str` | `required` |
| `location_id` | `str` | `required` |
| `variable` | `Variable` | `required` |
| `calibration_id` | `str` | `required` |
| `response_id` | `str` | `required` |
| `source_ids` | `tuple[str, ...]` | `required` |
| `parameter_origin` | `Origin` | `required` |

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

#### `h2physics.adapters.lh2dt_instrumentation.TransmitterTrace`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/lh2dt_instrumentation.py#L42)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `prediction` | `TimeSeries` | `required` |
| `input_series` | `TimeSeries` | `required` |
| `input_channel` | `str` | `required` |
| `native_states` | `tuple[Any, ...]` | `required` |
| `native_readings` | `tuple[Any, ...]` | `required` |
| `native_transmitter` | `Any` | `required` |
| `evidence` | `TransmitterEvidence` | `required` |
| `hold_convention` | `str` | `'left-hold intervals; output is endpoint left limit'` |

Computed properties: `final_native_state`.

#### `h2physics.observations.Variable`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/observations.py#L16)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `name` | `str` | `required` |
| `quantity` | `str` | `required` |
| `unit` | `str` | `required` |
| `basis_id` | `str` | `''` |


## Maintaining this guide / 갱신

Curated purposes and entry selection live in `scripts/readme_module_guide.py`. Run `python scripts/readme_module_guide.py` to regenerate both README blocks and this file. Run `python scripts/readme_module_guide.py --check` to reject stale output, unresolved callables or missing catalog IDs. The script parses source with the standard library, imports no physical engine and runs no calculation. Review purpose/units/limits against domain manuals when an API changes. It preserves authored scientific attribution and performs no automatic translation of external material.
