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

- [외부 실내 수소 축적·점화 지연별 조건부 압력 피크 / Native indoor accumulation and ignition-delay conditional peaks](#module-h2physics-adapters-indoor_release-run_hyram_indoor_release)
- [근거·영역이 명시된 화염가속·DDT 필요조건 선별 / Evidence/domain-bound necessary conditions for FA and DDT](#module-h2physics-combustion_screening-screen_combustion)
- [CoolProp 유한 균질 등엔트로피 순팽창 일 / CoolProp finite homogeneous isentropic net expansion work](#module-h2physics-mechanical_rupture-isentropic_expansion_energy)
- [기계적 에너지 배분과 지정 압력 공급자 연결 / Explicit mechanical energy allocation and supplied pressure provider](#module-h2physics-mechanical_rupture-mechanical_rupture_load)
- [실제 압력 시간 이력에 따른 선형 구조 동응답 / Linear structural response to an actual pressure-time history](#module-h2physics-materials-sdof-solve_linear_sdof)
- [실제 TESPy Rankine 네트워크·제1법칙 수지 / Actual TESPy Rankine network and first-law audit](#module-h2physics-adapters-thermal_cycles-solve_rankine_cycle)
- [실제 ExerPy를 이용한 원래 네트워크 물리 엑서지 분석 / Actual ExerPy physical-exergy analysis of the retained network](#module-h2physics-adapters-thermal_cycles-analyze_rankine_exergy)
- [수소 압축·외부 헬륨 냉각·JT·기액 분리 기준 사이클 / H2 compression/external-helium cooling/JT/separation reference](#module-h2physics-adapters-liquefaction_cycle-solve_hydrogen_liquefaction)
- [허용 두 고체 상에 한정한 외부 산화환원 평형 / Restricted two-solid native redox equilibrium](#module-h2physics-storage-redox_equilibrium-twosolidredoxequilibrium-equilibrate)
- [전극 측정값의 부호가 명시된 iR 보정 / Signed iR correction of electrode measurements](#module-h2physics-electrocatalyst_metrics-corrected_overpotential_v)
- [지정 구간 Tafel 기울기·교환전류 밀도 추정 / Explicit-window Tafel slope and exchange-current fit](#module-h2physics-electrocatalyst_metrics-fit_tafel)
- [시간 정렬된 생성물·전하의 Faraday 효율 비교 / Time-aligned product/charge Faradaic-efficiency comparison](#module-h2physics-electrocatalyst_metrics-compare_product_to_charge)
- [생성물·활성점 몰수 기준 회전빈도 / Product-based site-mole turnover frequency](#module-h2physics-electrocatalyst_metrics-turnover_frequency_from_product)
- [용량식 기반 PAR 유동·수소 제거·촉매 열저장 / Capacity-law PAR gas flow, hydrogen removal and catalyst heat storage](#module-h2physics-adapters-par_device-pardevice-integrate)

<a id="module-h2physics-adapters-indoor_release-run_hyram_indoor_release"></a>

## 외부 실내 수소 축적·점화 지연별 조건부 압력 피크 / Native indoor accumulation and ignition-delay conditional peaks

Family / navigation ID: `extension.indoor`

Import module: `h2physics.adapters.indoor_release`; selected entry: `run_hyram_indoor_release`.

#### `h2physics.adapters.indoor_release.run_hyram_indoor_release`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/indoor_release.py#L196)

Run actual separately installed HyRAM+ 6.1 with native CoolProp properties.

A steady source prescribes constant upstream conditions; its vessel volume
does not impose a finite depletion limit. Blowdown uses native finite stock.
No alternate model is used when import, native solving or admission fails.

```python
run_hyram_indoor_release(source: IndoorHydrogenSource, enclosure: IndoorEnclosure, settings: IndoorReleaseSettings) -> IndoorIgnitionDelayPeaks
```

### Returned value / 반환값

`IndoorIgnitionDelayPeaks`

### Related input/return records / 관련 입력·반환 객체

#### `h2physics.adapters.indoor_release.IndoorHydrogenSource`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/indoor_release.py#L65)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `pressure_pa_absolute` | `float` | `required` |
| `temperature_k` | `float` | `required` |
| `vessel_volume_m3` | `float` | `required` |
| `orifice_diameter_m` | `float` | `required` |
| `source_id` | `str` | `required` |
| `boundary_evidence_id` | `str` | `required` |
| `discharge_coefficient` | `float` | `1.0` |

#### `h2physics.adapters.indoor_release.IndoorEnclosure`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/indoor_release.py#L40)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `height_m` | `float` | `required` |
| `floor_area_m2` | `float` | `required` |
| `release_height_m` | `float` | `required` |
| `release_to_wall_m` | `float` | `required` |
| `ceiling_vent` | `IndoorVent` | `required` |
| `floor_vent` | `IndoorVent` | `required` |
| `geometry_evidence_id` | `str` | `required` |

#### `h2physics.adapters.indoor_release.IndoorReleaseSettings`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/indoor_release.py#L85)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `duration_s` | `float` | `required` |
| `clock_id` | `str` | `required` |
| `source_start_time_s` | `float` | `0.0` |
| `ambient_pressure_pa_absolute` | `float` | `101325.0` |
| `ambient_temperature_k` | `float` | `293.15` |
| `steady_source` | `bool` | `False` |
| `blowdown_steps` | `int` | `100` |
| `steady_steps` | `int` | `5` |
| `jet_relative_tolerance` | `float` | `1e-05` |
| `jet_max_steps` | `int` | `100000` |
| `release_angle_rad` | `float` | `0.0` |

#### `h2physics.adapters.indoor_release.IndoorIgnitionDelayPeaks`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/indoor_release.py#L130)

Snapshots indexed by release age, not by time since explosion.

``peak_overpressure_pa_gauge`` is the native conditional enclosure peak.
Native ``x_layer`` is already a mole fraction; its convenience method
``concentration`` uses percent, and is deliberately not used here.

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `source` | `IndoorHydrogenSource` | `required` |
| `enclosure` | `IndoorEnclosure` | `required` |
| `settings` | `IndoorReleaseSettings` | `required` |
| `native_version` | `str` | `required` |
| `native` | `object` | `field(repr=False, compare=False)` |
| `ignition_delay_s` | `np.ndarray` | `required` |
| `layer_hydrogen_mole_fraction` | `np.ndarray` | `required` |
| `layer_depth_m` | `np.ndarray` | `required` |
| `peak_overpressure_pa_gauge` | `np.ndarray` | `required` |
| `flammable_jet_hydrogen_mass_kg` | `np.ndarray` | `required` |
| `flammable_layer_hydrogen_mass_kg` | `np.ndarray` | `required` |
| `axis_kind` | `str` | `field(default='release_age_at_hypothetical_ignition', init=False)` |

Computed properties: `ignition_clock_time_s`, `conditional_peak_pressure_pa_absolute`.

#### `h2physics.adapters.indoor_release.IndoorVent`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/indoor_release.py#L25)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `area_m2` | `float` | `required` |
| `height_m` | `float` | `required` |
| `discharge_coefficient` | `float` | `1.0` |
| `imposed_volume_flow_m3_s` | `float` | `0.0` |


<a id="module-h2physics-combustion_screening-screen_combustion"></a>

## 근거·영역이 명시된 화염가속·DDT 필요조건 선별 / Evidence/domain-bound necessary conditions for FA and DDT

Family / navigation ID: `extension.screening`

Import module: `h2physics.combustion_screening`; selected entry: `screen_combustion`.

#### `h2physics.combustion_screening.screen_combustion`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/combustion_screening.py#L296)

Compare bounded necessary conditions, retaining out-of-domain ambiguity.

Cell data must refer to the exact mixture-condition identity. A met result
leaves ignition, flame run-up and sufficient geometry unresolved. A not-met
result only fails this selected route; it does not exclude direct initiation
or establish safety of a facility.

```python
screen_combustion(expansion: MixtureExpansion, geometry: ScreeningGeometry, flame: FlameAccelerationCriterion, cell: DetonationCellCriterion) -> CombustionScreen
```

### Returned value / 반환값

`CombustionScreen`

### Related input/return records / 관련 입력·반환 객체

#### `h2physics.combustion_screening.MixtureExpansion`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/combustion_screening.py#L118)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `condition` | `HydrogenMixtureCondition` | `required` |
| `density_unburned_kg_m3` | `float` | `required` |
| `density_burned_kg_m3` | `float` | `required` |
| `burned_temperature_k` | `float` | `required` |
| `thermochemistry_evidence_id` | `str` | `required` |
| `definition` | `str` | `'adiabatic_constant_pressure_equilibrium'` |

Computed properties: `expansion_ratio`.

#### `h2physics.combustion_screening.FlameAccelerationCriterion`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/combustion_screening.py#L183)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `critical_expansion_ratio` | `EvidenceInterval` | `required` |
| `domain` | `ScreeningDomain` | `required` |
| `source_id` | `str` | `required` |

#### `h2physics.combustion_screening.DetonationCellCriterion`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/combustion_screening.py#L249)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `cell_width_m` | `EvidenceInterval` | `required` |
| `characteristic_length_m` | `EvidenceInterval` | `required` |
| `domain` | `ScreeningDomain` | `required` |
| `cell_data_condition_id` | `str` | `required` |
| `geometry_length_definition_id` | `str` | `required` |
| `source_id` | `str` | `required` |
| `required_cell_multiples` | `float` | `7.0` |

#### `h2physics.combustion_screening.CombustionScreen`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/combustion_screening.py#L276)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `expansion` | `MixtureExpansion` | `required` |
| `geometry` | `ScreeningGeometry` | `required` |
| `flame_criterion` | `FlameAccelerationCriterion` | `required` |
| `cell_criterion` | `DetonationCellCriterion` | `required` |
| `flame_acceleration` | `NecessaryConditionStatus` | `required` |
| `cell_size` | `NecessaryConditionStatus` | `required` |
| `combined_ddt` | `NecessaryConditionStatus` | `required` |
| `reasons` | `tuple[str, ...]` | `required` |
| `predicts_initiation` | `bool` | `False` |

#### `h2physics.combustion_screening.HydrogenMixtureCondition`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/combustion_screening.py#L44)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `temperature_k` | `float` | `required` |
| `pressure_pa_absolute` | `float` | `required` |
| `hydrogen_mole_fraction` | `float` | `required` |
| `steam_mole_fraction` | `float` | `required` |
| `condition_id` | `str` | `required` |

#### `h2physics.combustion_screening.EvidenceInterval`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/combustion_screening.py#L21)

Closed physical uncertainty/support interval, not a confidence claim.

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `lower` | `float` | `required` |
| `upper` | `float` | `required` |
| `evidence_id` | `str` | `required` |

#### `h2physics.combustion_screening.ScreeningDomain`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/combustion_screening.py#L62)

Source-qualified envelope supplied by the research application.

Bounds are not inferred from an isolated coefficient or a single passing
calculation. The evidence must also establish tube/layer geometry, obstacle
and characteristic-length definitions and the oxidizer/diluent mixture.

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `minimum_temperature_k` | `float` | `required` |
| `maximum_temperature_k` | `float` | `required` |
| `minimum_pressure_pa_absolute` | `float` | `required` |
| `maximum_pressure_pa_absolute` | `float` | `required` |
| `minimum_hydrogen_mole_fraction` | `float` | `required` |
| `maximum_hydrogen_mole_fraction` | `float` | `required` |
| `maximum_steam_mole_fraction` | `float` | `required` |
| `geometries` | `tuple[ScreeningGeometry, ...]` | `required` |
| `evidence_id` | `str` | `required` |
| `mixture_family` | `str` | `'hydrogen_air_steam'` |


<a id="module-h2physics-mechanical_rupture-isentropic_expansion_energy"></a>

## CoolProp 유한 균질 등엔트로피 순팽창 일 / CoolProp finite homogeneous isentropic net expansion work

Family / navigation ID: `extension.mechanical_energy`

Import module: `h2physics.mechanical_rupture`; selected entry: `isentropic_expansion_energy`.

#### `h2physics.mechanical_rupture.isentropic_expansion_energy`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/mechanical_rupture.py#L49)

Evaluate m*(u1-u2) - p0*m*(v2-v1), with p2=p0 and s2=s1.

This is net useful work along the stated reversible path, excluding ambient
displacement. It is not the complete thermal exergy, vessel strain energy,
a shock-conversion efficiency, or chemical energy. The initial stock is a
homogeneous equilibrium state; stratified tanks need a different model.
Two-phase endpoints are retained when the native state solver supports them.

```python
isentropic_expansion_energy(properties: CoolPropProperties, *, source_id: str, inventory_mass_kg: float, initial_pressure_pa: float, initial_temperature_k: float, ambient_pressure_pa: float) -> IsentropicExpansionEnergy
```

### Returned value / 반환값

`IsentropicExpansionEnergy`

### Related input/return records / 관련 입력·반환 객체

#### `h2physics.mechanical_rupture.IsentropicExpansionEnergy`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/mechanical_rupture.py#L23)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `source_id` | `str` | `required` |
| `inventory_mass_kg` | `float` | `required` |
| `initial_state` | `ThermoState` | `required` |
| `final_state` | `ThermoState` | `required` |
| `gross_expansion_work_j` | `float` | `required` |
| `ambient_displacement_work_j` | `float` | `required` |
| `net_mechanical_work_j` | `float` | `required` |
| `native_version` | `str` | `required` |

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


<a id="module-h2physics-mechanical_rupture-mechanical_rupture_load"></a>

## 기계적 에너지 배분과 지정 압력 공급자 연결 / Explicit mechanical energy allocation and supplied pressure provider

Family / navigation ID: `extension.mechanical_load`

Import module: `h2physics.mechanical_rupture`; selected entry: `mechanical_rupture_load`.

#### `h2physics.mechanical_rupture.mechanical_rupture_load`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/mechanical_rupture.py#L216)

Hand mechanical energy to an explicit pressure owner without TNT substitution.

A caller may supply a measured waveform provider. The local energy reference
alone cannot determine pulse duration, reflection or peak pressure. A single
receptor history does not independently establish total radiated energy.

```python
mechanical_rupture_load(request: MechanicalLoadRequest, provider: MechanicalPressureProvider) -> MechanicalRuptureLoad
```

### Returned value / 반환값

`MechanicalRuptureLoad`

### Related input/return records / 관련 입력·반환 객체

#### `h2physics.mechanical_rupture.MechanicalLoadRequest`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/mechanical_rupture.py#L124)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `allocation` | `MechanicalEnergyAllocation` | `required` |
| `distance_m` | `float` | `required` |
| `clock_id` | `str` | `required` |
| `load_id` | `str` | `required` |

#### `h2physics.mechanical_rupture.MechanicalRuptureLoad`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/mechanical_rupture.py#L211)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `request` | `MechanicalLoadRequest` | `required` |
| `pressure` | `PressureTimeHistory` | `required` |

#### `h2physics.mechanical_rupture.MechanicalEnergyAllocation`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/mechanical_rupture.py#L86)

Caller-declared disjoint shares; no universal shock fraction is assumed.

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `expansion` | `IsentropicExpansionEnergy` | `required` |
| `shock_fraction` | `float` | `required` |
| `fragment_fraction` | `float` | `required` |
| `wall_fraction` | `float` | `required` |
| `allocation_evidence_id` | `str` | `required` |

Computed properties: `shock_energy_j`, `fragment_energy_j`, `wall_energy_j`, `remaining_energy_j`.

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


<a id="module-h2physics-materials-sdof-solve_linear_sdof"></a>

## 실제 압력 시간 이력에 따른 선형 구조 동응답 / Linear structural response to an actual pressure-time history

Family / navigation ID: `extension.sdof`

Import module: `h2physics.materials.sdof`; selected entry: `solve_linear_sdof`.

#### `h2physics.materials.sdof.solve_linear_sdof`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/materials/sdof.py#L68)

Integrate at every waveform corner, then sample the requested times.

Initial conditions belong to ``time_s[0]``, which must equal the load's first
timestamp. The output may continue into free vibration after load support.
Work and damping are integrated as states, independently of output cadence.

```python
solve_linear_sdof(model: LinearSDOF, load: PressureTimeHistory, time_s, *, initial_displacement_m=0.0, initial_velocity_m_s=0.0, relative_tolerance=1e-09, absolute_tolerance=1e-11) -> SDOFResponse
```

### Returned value / 반환값

`SDOFResponse`

### Related input/return records / 관련 입력·반환 객체

#### `h2physics.materials.sdof.LinearSDOF`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/materials/sdof.py#L19)

Generalized quantities must all use the same displacement coordinate.

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `mass_kg` | `float` | `required` |
| `stiffness_n_m` | `float` | `required` |
| `damping_n_s_m` | `float` | `required` |
| `effective_loaded_area_m2` | `float` | `required` |
| `model_id` | `str` | `required` |

Computed properties: `natural_angular_frequency_rad_s`.

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

#### `h2physics.materials.sdof.SDOFResponse`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/materials/sdof.py#L42)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `model` | `LinearSDOF` | `required` |
| `load` | `PressureTimeHistory` | `required` |
| `time_s` | `np.ndarray` | `required` |
| `displacement_m` | `np.ndarray` | `required` |
| `velocity_m_s` | `np.ndarray` | `required` |
| `acceleration_m_s2` | `np.ndarray` | `required` |
| `restoring_force_n` | `np.ndarray` | `required` |
| `kinetic_energy_j` | `np.ndarray` | `required` |
| `elastic_energy_j` | `np.ndarray` | `required` |
| `input_work_j` | `np.ndarray` | `required` |
| `damping_dissipation_j` | `np.ndarray` | `required` |
| `energy_residual_j` | `np.ndarray` | `required` |


<a id="module-h2physics-adapters-thermal_cycles-solve_rankine_cycle"></a>

## 실제 TESPy Rankine 네트워크·제1법칙 수지 / Actual TESPy Rankine network and first-law audit

Family / navigation ID: `extension.rankine`

Import module: `h2physics.adapters.thermal_cycles`; selected entry: `solve_rankine_cycle`.

#### `h2physics.adapters.thermal_cycles.solve_rankine_cycle`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/thermal_cycles.py#L87)

Build and solve a real TESPy network, using CoolProp-backed fluids.

The two finite-temperature water streams provide resolved heat supply and
rejection. The result is a thermal power-cycle example suitable for coupling
net shaft power to a separately defined electrolyzer; it is not an H2
liquefier, a geothermal reservoir model or a measured plant qualification.

```python
solve_rankine_cycle(spec: RankineCycleSpec=RankineCycleSpec()) -> SolvedRankineCycle
```

### Returned value / 반환값

`SolvedRankineCycle`

### Related input/return records / 관련 입력·반환 객체

#### `h2physics.adapters.thermal_cycles.RankineCycleSpec`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/thermal_cycles.py#L18)

Pure-fluid, steady Rankine cycle with explicit hot/cold water boundaries.

This four-component level omits recuperation, generator/motor losses,
mechanical pressure losses on the working-fluid side and hydrogen chemistry.
Changing ``working_fluid`` selects CoolProp's native pure-fluid properties.

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `working_fluid` | `str` | `'R245fa'` |
| `mass_flow_kg_s` | `float` | `1.0` |
| `turbine_inlet_temperature_k` | `float` | `400.0` |
| `high_pressure_pa` | `float` | `2000000.0` |
| `low_pressure_pa` | `float` | `200000.0` |
| `turbine_isentropic_efficiency` | `float` | `0.85` |
| `pump_isentropic_efficiency` | `float` | `0.75` |
| `hot_inlet_temperature_k` | `float` | `450.0` |
| `hot_outlet_temperature_k` | `float` | `420.0` |
| `hot_pressure_pa` | `float` | `1000000.0` |
| `cold_inlet_temperature_k` | `float` | `290.0` |
| `cold_outlet_temperature_k` | `float` | `300.0` |
| `cold_pressure_pa` | `float` | `200000.0` |
| `external_pressure_ratio` | `float` | `0.99` |
| `source_id` | `str` | `'declared-design-case'` |

#### `h2physics.adapters.thermal_cycles.SolvedRankineCycle`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/thermal_cycles.py#L81)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `network` | `object` | `required` |
| `spec` | `RankineCycleSpec` | `required` |
| `energy` | `CycleEnergyAudit` | `required` |

#### `h2physics.adapters.thermal_cycles.CycleEnergyAudit`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/thermal_cycles.py#L61)

Signed external duties; positive heat/work enters the working fluid.

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `heat_input_w` | `float` | `required` |
| `heat_rejected_w` | `float` | `required` |
| `turbine_output_w` | `float` | `required` |
| `pump_input_w` | `float` | `required` |
| `net_output_w` | `float` | `required` |
| `first_law_residual_w` | `float` | `required` |
| `maximum_mass_residual_kg_s` | `float` | `required` |
| `source_id` | `str` | `required` |
| `tespy_version` | `str` | `required` |
| `coolprop_version` | `str` | `required` |

Computed properties: `thermal_efficiency`.


<a id="module-h2physics-adapters-thermal_cycles-analyze_rankine_exergy"></a>

## 실제 ExerPy를 이용한 원래 네트워크 물리 엑서지 분석 / Actual ExerPy physical-exergy analysis of the retained network

Family / navigation ID: `extension.exergy`

Import module: `h2physics.adapters.thermal_cycles`; selected entry: `analyze_rankine_exergy`.

#### `h2physics.adapters.thermal_cycles.analyze_rankine_exergy`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/thermal_cycles.py#L218)

Hot stream and any consumed coolant exergy supply net shaft output.

Cooling water below the reference temperature may LOSE physical exergy
while absorbing heat: that decrease is an additional resource. A net
coolant exergy increase is instead a declared rejected-stream loss. The
difference uses native connection h/s on the same water reference; it does
not require a new fluid-property closure.

```python
analyze_rankine_exergy(cycle: SolvedRankineCycle, *, environment_temperature_k=298.15, environment_pressure_pa=101325.0) -> PhysicalExergyAudit
```

### Returned value / 반환값

`PhysicalExergyAudit`

### Related input/return records / 관련 입력·반환 객체

#### `h2physics.adapters.thermal_cycles.SolvedRankineCycle`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/thermal_cycles.py#L81)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `network` | `object` | `required` |
| `spec` | `RankineCycleSpec` | `required` |
| `energy` | `CycleEnergyAudit` | `required` |

#### `h2physics.adapters.thermal_cycles.PhysicalExergyAudit`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/thermal_cycles.py#L160)

Native physical-exergy balance with caller-defined useful-product boundary.

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `analysis` | `object` | `required` |
| `environment_temperature_k` | `float` | `required` |
| `environment_pressure_pa` | `float` | `required` |
| `fuel_exergy_w` | `float` | `required` |
| `product_exergy_w` | `float` | `required` |
| `loss_exergy_w` | `float` | `required` |
| `destruction_exergy_w` | `float` | `required` |
| `balance_residual_w` | `float` | `required` |
| `component_destruction_w` | `Mapping[str, float]` | `required` |
| `exerpy_version` | `str` | `required` |

#### `h2physics.adapters.thermal_cycles.RankineCycleSpec`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/thermal_cycles.py#L18)

Pure-fluid, steady Rankine cycle with explicit hot/cold water boundaries.

This four-component level omits recuperation, generator/motor losses,
mechanical pressure losses on the working-fluid side and hydrogen chemistry.
Changing ``working_fluid`` selects CoolProp's native pure-fluid properties.

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `working_fluid` | `str` | `'R245fa'` |
| `mass_flow_kg_s` | `float` | `1.0` |
| `turbine_inlet_temperature_k` | `float` | `400.0` |
| `high_pressure_pa` | `float` | `2000000.0` |
| `low_pressure_pa` | `float` | `200000.0` |
| `turbine_isentropic_efficiency` | `float` | `0.85` |
| `pump_isentropic_efficiency` | `float` | `0.75` |
| `hot_inlet_temperature_k` | `float` | `450.0` |
| `hot_outlet_temperature_k` | `float` | `420.0` |
| `hot_pressure_pa` | `float` | `1000000.0` |
| `cold_inlet_temperature_k` | `float` | `290.0` |
| `cold_outlet_temperature_k` | `float` | `300.0` |
| `cold_pressure_pa` | `float` | `200000.0` |
| `external_pressure_ratio` | `float` | `0.99` |
| `source_id` | `str` | `'declared-design-case'` |

#### `h2physics.adapters.thermal_cycles.CycleEnergyAudit`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/thermal_cycles.py#L61)

Signed external duties; positive heat/work enters the working fluid.

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `heat_input_w` | `float` | `required` |
| `heat_rejected_w` | `float` | `required` |
| `turbine_output_w` | `float` | `required` |
| `pump_input_w` | `float` | `required` |
| `net_output_w` | `float` | `required` |
| `first_law_residual_w` | `float` | `required` |
| `maximum_mass_residual_kg_s` | `float` | `required` |
| `source_id` | `str` | `required` |
| `tespy_version` | `str` | `required` |
| `coolprop_version` | `str` | `required` |

Computed properties: `thermal_efficiency`.


<a id="module-h2physics-adapters-liquefaction_cycle-solve_hydrogen_liquefaction"></a>

## 수소 압축·외부 헬륨 냉각·JT·기액 분리 기준 사이클 / H2 compression/external-helium cooling/JT/separation reference

Family / navigation ID: `extension.liquefaction`

Import module: `h2physics.adapters.liquefaction_cycle`; selected entry: `solve_hydrogen_liquefaction`.

#### `h2physics.adapters.liquefaction_cycle.solve_hydrogen_liquefaction`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/liquefaction_cycle.py#L98)

Solve a single-pass externally precooled H2 liquefaction process.

No vapor recycle, recuperation, ortho/para conversion, finite tank cooldown,
refrigerant compressor or cold-box electricity is implied. The saturated
products and every connection remain actual TESPy/CoolProp results.

```python
solve_hydrogen_liquefaction(spec: HydrogenLiquefactionSpec) -> SolvedHydrogenLiquefactionCycle
```

### Returned value / 반환값

`SolvedHydrogenLiquefactionCycle`

### Related input/return records / 관련 입력·반환 객체

#### `h2physics.adapters.liquefaction_cycle.HydrogenLiquefactionSpec`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/liquefaction_cycle.py#L15)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `compressor_isentropic_efficiency` | `float` | `required` |
| `source_id` | `str` | `required` |
| `hydrogen_fluid` | `str` | `'Hydrogen'` |
| `feed_mass_flow_kg_s` | `float` | `0.01` |
| `feed_temperature_k` | `float` | `300.0` |
| `feed_pressure_pa_absolute` | `float` | `101325.0` |
| `compression_pressure_pa_absolute` | `float` | `5000000.0` |
| `precooler_outlet_temperature_k` | `float` | `28.0` |
| `separator_pressure_pa_absolute` | `float` | `101325.0` |
| `utility_fluid` | `str` | `'Helium'` |
| `utility_inlet_temperature_k` | `float` | `15.0` |
| `utility_outlet_temperature_k` | `float` | `250.0` |
| `utility_pressure_pa_absolute` | `float` | `200000.0` |
| `utility_pressure_ratio` | `float` | `1.0` |
| `hydrogen_cooler_pressure_ratio` | `float` | `1.0` |
| `precooler_sections` | `int` | `128` |

#### `h2physics.adapters.liquefaction_cycle.SolvedHydrogenLiquefactionCycle`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/liquefaction_cycle.py#L92)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `network` | `object` | `required` |
| `spec` | `HydrogenLiquefactionSpec` | `required` |
| `audit` | `LiquefactionCycleAudit` | `required` |

#### `h2physics.adapters.liquefaction_cycle.LiquefactionCycleAudit`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/liquefaction_cycle.py#L73)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `liquid_mass_flow_kg_s` | `float` | `required` |
| `vapor_mass_flow_kg_s` | `float` | `required` |
| `liquid_mass_fraction` | `float` | `required` |
| `compressor_shaft_input_w` | `float` | `required` |
| `external_cold_utility_heat_absorbed_w` | `float` | `required` |
| `cold_utility_mass_flow_kg_s` | `float` | `required` |
| `hydrogen_first_law_residual_w` | `float` | `required` |
| `utility_heat_balance_residual_w` | `float` | `required` |
| `separator_mass_residual_kg_s` | `float` | `required` |
| `separator_energy_residual_w` | `float` | `required` |
| `jt_enthalpy_residual_j_kg` | `float` | `required` |
| `precooler_sampled_minimum_approach_k` | `float` | `required` |
| `precooler_sections` | `int` | `required` |
| `tespy_version` | `str` | `required` |
| `coolprop_version` | `str` | `required` |


<a id="module-h2physics-storage-redox_equilibrium-twosolidredoxequilibrium-equilibrate"></a>

## 허용 두 고체 상에 한정한 외부 산화환원 평형 / Restricted two-solid native redox equilibrium

Family / navigation ID: `extension.redox`

Import module: `h2physics.storage.redox_equilibrium`; selected entry: `TwoSolidRedoxEquilibrium.equilibrate`.

#### `h2physics.storage.redox_equilibrium.TwoSolidRedoxEquilibrium`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/storage/redox_equilibrium.py#L45)

One reaction spanning one reacting gas and two pure stoichiometric solids.

Candidate gas species must be exactly those mapped to the balanced reaction.
Competing oxides, nonstoichiometric vacancies, solid solutions, nucleation,
transport and intrinsic rates require a different declared material model.

```python
TwoSolidRedoxEquilibrium(phases, species_mapping, coefficients, *, identifier: str, solid_density_evidence: Mapping[str, SolidDensityEvidence], source_id: str)
```

Computed properties: `basis_id`.

#### `h2physics.storage.redox_equilibrium.TwoSolidRedoxEquilibrium.equilibrate`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/storage/redox_equilibrium.py#L85)

Predict signed finite extent and isothermal heat; no conversion input.

Positive extent follows the declared balanced reaction. A negative result
means reverse conversion is favoured by the supplied finite composition.
The required fixed-T/P heat is supplied externally; it is not a heat-
recovery prediction. The native result retains all original audit gates.

```python
equilibrate(self, amounts_mol: Mapping[str, float], *, temperature_k: float, pressure_pa: float, source_id: str, origin: Origin=Origin.PREDICTED, settings: MultiphaseSettings=MultiphaseSettings()) -> RedoxEquilibriumResult
```

### Returned value / 반환값

`RedoxEquilibriumResult`

### Related input/return records / 관련 입력·반환 객체

#### `h2physics.adapters.cantera_caloric.SolidDensityEvidence`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/cantera_caloric.py#L24)

Evidence for the actual factory's constant-volume density, in kg/m3.

A synthetic value is an authored calorimetry fixture, not a measurement or
evidence that a thermochemical species database supplies a solid EOS.

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `density_kg_m3` | `float` | `required` |
| `source_id` | `str` | `required` |
| `origin` | `Origin` | `required` |
| `description` | `str` | `required` |

#### `h2physics.adapters.cantera_multiphase.MultiphaseSettings`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/cantera_multiphase.py#L90)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `solver` | `str` | `'vcs'` |
| `relative_tolerance` | `float` | `1e-10` |
| `maximum_steps` | `int` | `2000` |
| `maximum_iterations` | `int` | `300` |
| `estimate_equilibrium` | `int` | `0` |

#### `h2physics.storage.redox_equilibrium.RedoxEquilibriumResult`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/storage/redox_equilibrium.py#L34)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `conversion` | `ReactionConversion` | `required` |
| `temperature_k` | `float` | `required` |
| `pressure_pa` | `float` | `required` |
| `heat_into_j` | `float` | `required` |
| `caloric_basis_id` | `str` | `required` |
| `source_id` | `str` | `required` |
| `maximum_stoichiometry_residual_mol` | `float` | `required` |
| `native_result` | `object` | `required` |

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


<a id="module-h2physics-electrocatalyst_metrics-corrected_overpotential_v"></a>

## 전극 측정값의 부호가 명시된 iR 보정 / Signed iR correction of electrode measurements

Family / navigation ID: `extension.electrode_ir`

Import module: `h2physics.electrocatalyst_metrics`; selected entry: `corrected_overpotential_v`.

#### `h2physics.electrocatalyst_metrics.corrected_overpotential_v`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/electrocatalyst_metrics.py#L25)

Return signed E-Eeq-I*R using resistance still present in the observations.

Currents are signed (anodic positive). If the instrument already compensates
part of the resistance, pass only the remaining resistance to avoid applying
compensation twice. Potentials must share one reference electrode scale.

```python
corrected_overpotential_v(measured_potential_v, equilibrium_potential_v, current_a, *, remaining_uncompensated_resistance_ohm)
```

The source has no explicit return annotation; inspect its return statements and the domain manual. No return type is invented by this generator.

### Returned value / 반환값

`float &#124; numpy.ndarray`

This return contract was reviewed from the implementation; it is not an annotation present in the source signature.


<a id="module-h2physics-electrocatalyst_metrics-fit_tafel"></a>

## 지정 구간 Tafel 기울기·교환전류 밀도 추정 / Explicit-window Tafel slope and exchange-current fit

Family / navigation ID: `extension.electrode_tafel`

Import module: `h2physics.electrocatalyst_metrics`; selected entry: `fit_tafel`.

#### `h2physics.electrocatalyst_metrics.fit_tafel`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/electrocatalyst_metrics.py#L77)

Fit |eta| = a + b*log10(|j|/(1 A/m2)) within a caller-declared window.

Cathodic inputs must have negative current and negative overpotential;
anodic inputs must have positive signs. Values outside the fit window may
belong to other regimes. Standard uncertainties, when supplied, describe
independent voltage errors only; current error/correlation is not modeled.
Covariance order is intercept, slope. j0 is a model extrapolation.

```python
fit_tafel(overpotential_v, current_density_a_m2, *, branch: str, area_basis: str, protocol_id: str, current_density_window_a_m2: tuple[float, float], overpotential_standard_uncertainty_v=None) -> TafelFit
```

### Returned value / 반환값

`TafelFit`

### Related input/return records / 관련 입력·반환 객체

#### `h2physics.electrocatalyst_metrics.TafelFit`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/electrocatalyst_metrics.py#L53)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `slope_v_decade` | `float` | `required` |
| `intercept_v_at_1_a_m2` | `float` | `required` |
| `exchange_current_density_a_m2` | `float` | `required` |
| `covariance` | `np.ndarray` | `required` |
| `selected_indices` | `np.ndarray` | `required` |
| `residual_v` | `np.ndarray` | `required` |
| `r_squared` | `float` | `required` |
| `branch` | `str` | `required` |
| `area_basis` | `str` | `required` |
| `protocol_id` | `str` | `required` |
| `current_density_window_a_m2` | `tuple[float, float]` | `required` |


<a id="module-h2physics-electrocatalyst_metrics-compare_product_to_charge"></a>

## 시간 정렬된 생성물·전하의 Faraday 효율 비교 / Time-aligned product/charge Faradaic-efficiency comparison

Family / navigation ID: `extension.electrode_fe`

Import module: `h2physics.electrocatalyst_metrics`; selected entry: `compare_product_to_charge`.

#### `h2physics.electrocatalyst_metrics.compare_product_to_charge`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/electrocatalyst_metrics.py#L157)

Compare collected H2 (2e) or O2 (4e) with time-aligned electrode charge.

Product is the amount collected in each interval, already corrected for any
independently known collection losses/transport delay. Current magnitude is
integrated piecewise-linearly without extrapolation. Polarity reversal is
rejected: forward and reverse reaction intervals must be analyzed separately.
Efficiencies > 1 are retained as a measurement/balance diagnostic, not clipped.

```python
compare_product_to_charge(current_time_s, current_a, *, interval_edges_s, product_mol, product: str, current_clock_id: str, collection_clock_id: str, measurement_id: str) -> ProductChargeComparison
```

### Returned value / 반환값

`ProductChargeComparison`

### Related input/return records / 관련 입력·반환 객체

#### `h2physics.electrocatalyst_metrics.ProductChargeComparison`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/electrocatalyst_metrics.py#L142)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `product` | `str` | `required` |
| `electrons_per_product_molecule` | `int` | `required` |
| `interval_edges_s` | `np.ndarray` | `required` |
| `product_mol` | `np.ndarray` | `required` |
| `charge_magnitude_c` | `np.ndarray` | `required` |
| `faradaic_efficiency` | `np.ndarray` | `required` |
| `clock_id` | `str` | `required` |
| `measurement_id` | `str` | `required` |


<a id="module-h2physics-electrocatalyst_metrics-turnover_frequency_from_product"></a>

## 생성물·활성점 몰수 기준 회전빈도 / Product-based site-mole turnover frequency

Family / navigation ID: `extension.electrode_tof`

Import module: `h2physics.electrocatalyst_metrics`; selected entry: `turnover_frequency_from_product`.

#### `h2physics.electrocatalyst_metrics.turnover_frequency_from_product`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/electrocatalyst_metrics.py#L204)

Moles product/(moles counted active sites*s), requiring an explicit site basis.

```python
turnover_frequency_from_product(product_rate_mol_s: float, *, active_site_amount_mol: float, site_basis_id: str) -> float
```

### Returned value / 반환값

`float`


<a id="module-h2physics-adapters-par_device-pardevice-integrate"></a>

## 용량식 기반 PAR 유동·수소 제거·촉매 열저장 / Capacity-law PAR gas flow, hydrogen removal and catalyst heat storage

Family / navigation ID: `extension.par`

Import module: `h2physics.adapters.par_device`; selected entry: `PARDevice.integrate`.

#### `h2physics.adapters.par_device.PARDevice`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/par_device.py#L182)

Performance-map PAR with dynamic catalyst and quasi-steady gas channel.

Cantera supplies density, heat capacity and species formation/sensible
enthalpies on one native mechanism reference. No new gas EOS is introduced.
The only chemical transformation here is H2 + 0.5 O2 -> H2O(vapor), whose
extent is set by the supplied performance law and available feed.

```python
PARDevice(gas: CanteraGas, parameters: PARDeviceParameters, capacity: PARCapacityLaw)
```

#### `h2physics.adapters.par_device.PARDevice.integrate`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/par_device.py#L314)

Integrate catalyst storage and cumulative ports for a fixed inlet.

The room boundary remains prescribed: a compartment solver must receive
the returned species and heat ports if a finite room is required.

```python
integrate(self, inlet: ReactiveState, *, initial_catalyst_temperature_k: float, time_s, clock_id: str, relative_tolerance=1e-07, maximum_step_s=1.0) -> PARThermalTrace
```

### Returned value / 반환값

`PARThermalTrace`

### Related input/return records / 관련 입력·반환 객체

#### `h2physics.adapters.par_device.PARDeviceParameters`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/par_device.py#L99)

Caller-supplied lumped geometry and thermal coefficients, all SI.

Loss coefficient uses inlet-area mass flux and the mean of inlet/outlet
gas densities. Background flow is an imposed exchange-flow floor; it is
not calculated diffusion or a model of autonomous cold startup.

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `evidence_id` | `str` | `required` |
| `chimney_height_m` | `float` | `required` |
| `inlet_area_m2` | `float` | `required` |
| `loss_coefficient` | `float` | `required` |
| `catalyst_heat_capacity_j_k` | `float` | `required` |
| `catalyst_to_gas_ua_w_k` | `float` | `required` |
| `catalyst_to_room_ua_w_k` | `float` | `required` |
| `radiating_area_m2` | `float` | `required` |
| `emissivity` | `float` | `required` |
| `reaction_heat_to_catalyst_fraction` | `float` | `required` |
| `maximum_mass_flow_kg_s` | `float` | `required` |
| `background_mass_flow_kg_s` | `float` | `0.0` |
| `gravity_m_s2` | `float` | `9.80665` |

#### `h2physics.adapters.par_device.PARCapacityLaw`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/par_device.py#L39)

Explicit device capacity in mol H2/s, before finite-feed limitation.

``evidence_id`` identifies a calibration, manufacturer map or explicitly
synthetic reference. Declaring it does not establish experimental validity.
Callbacks must be deterministic and side-effect free during root solving.

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `evidence_id` | `str` | `required` |
| `hydrogen_capacity_mol_s` | `Callable[[PARCapacityCondition], float]` | `required` |
| `catalyst_temperature_bounds_k` | `tuple[float, float]` | `required` |
| `inlet_temperature_bounds_k` | `tuple[float, float]` | `required` |
| `pressure_bounds_pa` | `tuple[float, float]` | `required` |
| `hydrogen_mole_fraction_bounds` | `tuple[float, float]` | `required` |
| `oxygen_mole_fraction_bounds` | `tuple[float, float]` | `required` |
| `maximum_mass_flow_kg_s` | `float` | `required` |

#### `h2physics.adapters.cantera.ReactiveState`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/cantera.py#L51)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `temperature_k` | `float` | `required` |
| `pressure_pa` | `float` | `required` |
| `mole_fractions` | `Mapping[str, float]` | `required` |

#### `h2physics.adapters.par_device.PARThermalTrace`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/par_device.py#L177)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `clock_id` | `str` | `required` |
| `samples` | `tuple[PARThermalSample, ...]` | `required` |

#### `h2physics.adapters.par_device.PARCapacityCondition`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/par_device.py#L30)

Inputs to a measured/calibrated whole-device removal-capacity law.

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `catalyst_temperature_k` | `float` | `required` |
| `inlet` | `ReactiveState` | `required` |
| `inlet_mass_flow_kg_s` | `float` | `required` |

#### `h2physics.adapters.par_device.PARThermalSample`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/par_device.py#L166)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `time_s` | `float` | `required` |
| `point` | `PARDevicePoint` | `required` |
| `cumulative_hydrogen_removed_mol` | `float` | `required` |
| `cumulative_inlet_enthalpy_j` | `float` | `required` |
| `cumulative_outlet_enthalpy_j` | `float` | `required` |
| `cumulative_heat_to_room_j` | `float` | `required` |
| `energy_residual_j` | `float` | `required` |


## Maintaining this guide / 갱신

Curated purposes and entry selection live in `scripts/readme_module_guide.py`. Run `python scripts/readme_module_guide.py` to regenerate both README blocks and this file. Run `python scripts/readme_module_guide.py --check` to reject stale output, unresolved callables or missing catalog IDs. The script parses source with the standard library, imports no physical engine and runs no calculation. Review purpose/units/limits against domain manuals when an API changes. It preserves authored scientific attribution and performs no automatic translation of external material.
