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

- [고압 극저온 저장·벽 열응답·릴리프 / Finite cryogenic high-pressure storage and relief](#module-h2physics-adapters-cryo_compressed-cryocompressedstorage-run)
- [자유 기체와 절대 흡착량을 합친 저장 용기 재고 / Free gas plus absolute-uptake vessel inventory](#module-h2physics-adapters-finite_adsorption_vessel-finiteadsorptionvessel-snapshot)
- [다성분 경쟁 Langmuir 평형 흡착·미분값 / Competitive multicomponent Langmuir uptake and derivatives](#module-h2physics-adsorption-extendedlangmuirisotherm-equilibrium)
- [흡착 용기 인도 몰수를 질량·구간 평균 유량으로 변환 / Accepted mole delivery converted to mass and interval-mean flow](#module-h2physics-storage-product_delivery-adsorptionproductmassflow)
- [외부 흡착층의 온도·흡착량·성분 재고 읽기 / Native thermal adsorption-bed states and inventories](#module-h2physics-adapters-psa-psadynabed-snapshot)
- [수소화물 평형 압력·기울기·이력 효과 / Hydride equilibrium plateau, slope and hysteresis](#module-h2physics-storage-hydride-vanthoffplateau-fugacity_pa)
- [유한 기체·고체 재고와 수소화 반응·열응답 / Finite gas/solid storage, uptake kinetics and heat](#module-h2physics-storage-finite_hydride-finitehydridebed-simulate)
- [유한 공급·수신 탱크 사이 열구동 수소화물 압축 / Thermally cycled bed between finite source and receiver vessels](#module-h2physics-storage-hydride_compressor-hydridethermalcompressor-run)
- [LOHC·암모니아의 지정 전환량·유한 재고·인출 / Prescribed finite LOHC/ammonia conversion and takeoff](#module-h2physics-adapters-carrier_conversion-finitecarrierconversion-run)
- [고체 분해·가수분해의 유한 공급·반응·열수지 / Finite solid decomposition/hydrolysis with supplies and heat](#module-h2physics-storage-solid_reaction-finitesolidreactionreactor-run)
- [미소구 내부 기체와 구형 벽 수소 이동 / Finite gas cavity coupled to spherical wall transport](#module-h2physics-storage-microsphere-microspherestorage-simulate)
- [외부 지하 공동·습윤 기체·암반 모델과 수지 검사 / Native cavern/wet-gas/rock model with independent ledgers](#module-h2physics-adapters-underground_storage-uh2scundergroundstorage-run)
- [방사형 등온 단상 다공성 저장소 주입·인출 / Radial isothermal single-phase Darcy storage](#module-h2physics-storage-porous_reservoir-porousreservoir-run)

<a id="module-h2physics-adapters-cryo_compressed-cryocompressedstorage-run"></a>

## 고압 극저온 저장·벽 열응답·릴리프 / Finite cryogenic high-pressure storage and relief

Family / navigation ID: `storage.cryo_compressed`

Import module: `h2physics.adapters.cryo_compressed`; selected entry: `CryoCompressedStorage.run`.

#### `h2physics.adapters.cryo_compressed.CryoCompressedStorage`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/cryo_compressed.py#L204)

Reusable native homogeneous fluid/wall + existing pressure-protection driver.

Each run creates fresh native protection state. A window below set pressure
is sealed. If set pressure is reached, the existing real native relief and
shared nozzle act; this is not a stop-at-threshold or an ideal isolation.

```python
CryoCompressedStorage(native: CryoCompressedNative, *, properties: CoolPropProperties, geometry: CryoCompressedGeometry, domain: CryoCompressedDomain, evidence: CryoCompressedEvidence, initial_pressure_pa_absolute: float, initial_temperature_k: float, initial_wall_temperature_k: float, opening: NozzleOpening, set_pressure_pa_absolute: float, reseat_pressure_pa_absolute: float, independent_properties_factory=CoolPropProperties, inventory_tolerances: InventoryTolerances | None=None, eos_mass_tolerance_kg: float=1e-10, eos_energy_tolerance_j: float=0.0001, eos_temperature_tolerance_k: float=1e-07, event_settings: ReliefEventSettings | None=None)
```

#### `h2physics.adapters.cryo_compressed.CryoCompressedStorage.run`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/cryo_compressed.py#L289)

```python
run(self, *, duration_s: float, maximum_step_s: float, start_time_s: float, clock_id: str, boundary: ReliefTankBoundary) -> CryoCompressedTrace
```

### Returned value / 반환값

`CryoCompressedTrace`

### Related input/return records / 관련 입력·반환 객체

#### `h2physics.adapters.cryo_compressed.CryoCompressedNative`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/cryo_compressed.py#L32)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `tank_module` | `Any` | `required` |
| `valve_module` | `Any` | `required` |
| `properties_module` | `Any` | `required` |
| `streams_module` | `Any` | `required` |
| `source_id` | `str` | `required` |

#### `h2physics.adapters.cryo_compressed.CryoCompressedGeometry`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/cryo_compressed.py#L49)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `volume_m3` | `float` | `required` |
| `wall_heat_capacity_j_k` | `float` | `required` |
| `ambient_ua_w_k` | `float` | `required` |
| `fluid_wall_ua_w_k` | `float` | `required` |

#### `h2physics.adapters.cryo_compressed.CryoCompressedDomain`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/cryo_compressed.py#L78)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `minimum_temperature_k` | `float` | `required` |
| `maximum_temperature_k` | `float` | `required` |
| `minimum_pressure_pa_absolute` | `float` | `required` |
| `maximum_pressure_pa_absolute` | `float` | `required` |
| `minimum_inventory_kg` | `float` | `required` |
| `maximum_initial_temperature_k` | `float` | `required` |
| `minimum_initial_pressure_to_critical_ratio` | `float` | `required` |
| `allowed_phases` | `tuple[str, ...]` | `required` |
| `evidence_id` | `str` | `required` |

#### `h2physics.adapters.cryo_compressed.CryoCompressedEvidence`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/cryo_compressed.py#L61)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `initial_state_source_id` | `str` | `required` |
| `geometry_source_id` | `str` | `required` |
| `heat_transfer_source_id` | `str` | `required` |
| `protection_source_id` | `str` | `required` |
| `phase_and_solid_exclusion_id` | `str` | `required` |
| `origin` | `Origin` | `required` |

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

#### `h2physics.dynamics.InventoryTolerances`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/dynamics.py#L33)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `mass_absolute_kg` | `float` | `1e-08` |
| `energy_absolute_j` | `float` | `0.0001` |
| `relative` | `float` | `1e-08` |

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

#### `h2physics.adapters.cryo_compressed.CryoCompressedTrace`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/cryo_compressed.py#L136)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `storage` | `Any` | `required` |
| `points` | `tuple[CryoCompressedPoint, ...]` | `required` |
| `native_trace` | `Any` | `required` |
| `native_driver` | `Any` | `required` |
| `protection` | `Any` | `required` |
| `independent_properties` | `Any` | `required` |
| `boundary` | `ReliefTankBoundary` | `required` |
| `inventory_tolerances` | `InventoryTolerances` | `required` |
| `critical_temperature_k` | `float` | `required` |
| `critical_pressure_pa` | `float` | `required` |
| `domain` | `CryoCompressedDomain` | `required` |
| `evidence` | `CryoCompressedEvidence` | `required` |
| `geometry` | `CryoCompressedGeometry` | `required` |
| `eos_mass_tolerance_kg` | `float` | `required` |
| `eos_energy_tolerance_j` | `float` | `required` |
| `eos_temperature_tolerance_k` | `float` | `required` |

Computed properties: `time_s`.

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

#### `h2physics.adapters.cryo_compressed.CryoCompressedPoint`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/cryo_compressed.py#L121)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `time_s` | `float` | `required` |
| `native_state` | `Any` | `required` |
| `fluid` | `ThermoState` | `required` |
| `independent_pt` | `ThermoState` | `required` |
| `independent_prho` | `ThermoState` | `required` |
| `inventory` | `ConservedInventory` | `required` |
| `balance` | `InventoryBalance` | `required` |
| `pt_mass_residual_kg` | `float` | `required` |
| `pt_energy_residual_j` | `float` | `required` |
| `prho_energy_residual_j` | `float` | `required` |
| `prho_temperature_residual_k` | `float` | `required` |


<a id="module-h2physics-adapters-finite_adsorption_vessel-finiteadsorptionvessel-snapshot"></a>

## 자유 기체와 절대 흡착량을 합친 저장 용기 재고 / Free gas plus absolute-uptake vessel inventory

Family / navigation ID: `storage.adsorption`

Import module: `h2physics.adapters.finite_adsorption_vessel`; selected entry: `FiniteAdsorptionVessel.snapshot`.

#### `h2physics.adapters.finite_adsorption_vessel.FiniteAdsorptionVessel`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/finite_adsorption_vessel.py#L476)

Endpoint inventory and usable-capacity accounting for a finite vessel.

```python
FiniteAdsorptionVessel(*, vessel_id, geometry, adsorption, gas)
```

#### `h2physics.adapters.finite_adsorption_vessel.FiniteAdsorptionVessel.snapshot`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/finite_adsorption_vessel.py#L499)

```python
snapshot(self, pressure_pa, temperature_k)
```

The source has no explicit return annotation; inspect its return statements and the domain manual. No return type is invented by this generator.

### Returned value / 반환값

`AdsorptionVesselSnapshot`

This return contract was reviewed from the implementation; it is not an annotation present in the source signature.

### Related input/return records / 관련 입력·반환 객체

#### `h2physics.adapters.finite_adsorption_vessel.AdsorptionVesselSnapshot`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/finite_adsorption_vessel.py#L234)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `vessel_id` | `str` | `required` |
| `geometry` | `AdsorptionVesselGeometry` | `required` |
| `adsorption_basis` | `AdsorptionBasis` | `required` |
| `gas_composition_id` | `str` | `required` |
| `gas_state` | `ThermoState` | `required` |
| `equilibrium` | `AdsorptionState` | `required` |
| `free_gas_component_mol` | `np.ndarray` | `required` |
| `adsorbed_component_mol` | `np.ndarray` | `required` |
| `total_component_mol` | `np.ndarray` | `required` |
| `adsorbed_standard_uncertainty_component_mol` | `np.ndarray &#124; None` | `None` |
| `uncertainty_semantics` | `str` | `'unqualified'` |
| `uncertainty_source_ids` | `tuple[str, ...]` | `()` |

Computed properties: `total_inventory_mol`.

#### `h2physics.adapters.finite_adsorption_vessel.AdsorptionVesselGeometry`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/finite_adsorption_vessel.py#L84)

Auditable physical volumes and adsorbent mass for one rigid vessel.

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `internal_volume_m3` | `float` | `required` |
| `adsorbent_mass_kg` | `float` | `required` |
| `solid_envelope_volume_m3` | `float` | `required` |
| `inaccessible_volume_m3` | `float` | `required` |
| `volume_basis_id` | `str` | `required` |

Computed properties: `void_volume_m3`.

#### `h2physics.adsorption.AdsorptionBasis`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adsorption.py#L13)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `material_id` | `str` | `required` |
| `species` | `tuple[str, ...]` | `required` |
| `amount_basis_id` | `str` | `required` |
| `engine_id` | `str` | `required` |
| `parameter_id` | `str` | `required` |
| `references` | `tuple[str, ...]` | `required` |
| `loading_definition` | `Literal['absolute', 'surface_excess', 'source_defined']` | `'source_defined'` |

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

#### `h2physics.adsorption.AdsorptionState`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adsorption.py#L121)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `basis` | `AdsorptionBasis` | `required` |
| `partial_pressures_pa` | `np.ndarray` | `required` |
| `temperature_k` | `float` | `required` |
| `site_loadings_mol_kg` | `np.ndarray` | `required` |
| `site_pressure_derivatives_mol_kg_pa` | `np.ndarray &#124; None` | `None` |
| `site_temperature_derivatives_mol_kg_k` | `np.ndarray &#124; None` | `None` |
| `source_observations` | `tuple[tuple[AdsorptionSourceObservation, ...], ...]` | `()` |
| `propagated_standard_uncertainty_mol_kg` | `np.ndarray &#124; None` | `None` |
| `uncertainty_semantics` | `str` | `'unqualified'` |
| `uncertainty_source_ids` | `tuple[str, ...]` | `()` |

Computed properties: `loadings_mol_kg`.


<a id="module-h2physics-adsorption-extendedlangmuirisotherm-equilibrium"></a>

## 다성분 경쟁 Langmuir 평형 흡착·미분값 / Competitive multicomponent Langmuir uptake and derivatives

Family / navigation ID: `storage.extended_langmuir`

Import module: `h2physics.adsorption`; selected entry: `ExtendedLangmuirIsotherm.equilibrium`.

#### `h2physics.adsorption.ExtendedLangmuirIsotherm`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adsorption.py#L232)

Competitive multicomponent Langmuir equilibrium on explicit sites.

`affinity_pa_inv(T)` returns a species-by-site matrix. The equilibrium
loading on each site is shared competitively among all declared species.
This idealized closure requires absolute uptake and remains caller
parameterized; it is not a universal porous-material equation of state.

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `basis` | `AdsorptionBasis` | `required` |
| `domain` | `AdsorptionDomain` | `required` |
| `site_capacity_mol_kg` | `np.ndarray` | `required` |
| `affinity_pa_inv` | `object` | `required` |
| `evidence_id` | `str` | `required` |
| `affinity_temperature_derivative_pa_inv_k` | `object &#124; None` | `None` |

#### `h2physics.adsorption.ExtendedLangmuirIsotherm.equilibrium`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adsorption.py#L279)

```python
equilibrium(self, partial_pressures_pa, temperature_k: float) -> AdsorptionState
```

### Returned value / 반환값

`AdsorptionState`

### Related input/return records / 관련 입력·반환 객체

#### `h2physics.adsorption.AdsorptionBasis`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adsorption.py#L13)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `material_id` | `str` | `required` |
| `species` | `tuple[str, ...]` | `required` |
| `amount_basis_id` | `str` | `required` |
| `engine_id` | `str` | `required` |
| `parameter_id` | `str` | `required` |
| `references` | `tuple[str, ...]` | `required` |
| `loading_definition` | `Literal['absolute', 'surface_excess', 'source_defined']` | `'source_defined'` |

#### `h2physics.adsorption.AdsorptionDomain`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adsorption.py#L39)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `minimum_temperature_k` | `float` | `required` |
| `maximum_temperature_k` | `float` | `required` |
| `maximum_total_pressure_pa` | `float` | `required` |
| `minimum_total_pressure_pa` | `float` | `0.0` |

#### `h2physics.adsorption.AdsorptionState`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adsorption.py#L121)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `basis` | `AdsorptionBasis` | `required` |
| `partial_pressures_pa` | `np.ndarray` | `required` |
| `temperature_k` | `float` | `required` |
| `site_loadings_mol_kg` | `np.ndarray` | `required` |
| `site_pressure_derivatives_mol_kg_pa` | `np.ndarray &#124; None` | `None` |
| `site_temperature_derivatives_mol_kg_k` | `np.ndarray &#124; None` | `None` |
| `source_observations` | `tuple[tuple[AdsorptionSourceObservation, ...], ...]` | `()` |
| `propagated_standard_uncertainty_mol_kg` | `np.ndarray &#124; None` | `None` |
| `uncertainty_semantics` | `str` | `'unqualified'` |
| `uncertainty_source_ids` | `tuple[str, ...]` | `()` |

Computed properties: `loadings_mol_kg`.

#### `h2physics.adsorption.AdsorptionSourceObservation`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adsorption.py#L66)

One weighted, species-qualified source-row receipt for an adsorption site.

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `species` | `str` | `required` |
| `source_row` | `int` | `required` |
| `interpolation_weight` | `float` | `required` |
| `source_loading_mol_kg` | `float` | `required` |
| `standard_uncertainty_mol_kg` | `float &#124; None` | `None` |
| `detection_limit_mol_kg` | `float &#124; None` | `None` |
| `quantification_limit_mol_kg` | `float &#124; None` | `None` |
| `source_dataset_id` | `str &#124; None` | `None` |
| `source_sha256` | `str &#124; None` | `None` |
| `uncertainty_kind` | `str` | `'unqualified'` |
| `covariance_group_id` | `str &#124; None` | `None` |


<a id="module-h2physics-storage-product_delivery-adsorptionproductmassflow"></a>

## 흡착 용기 인도 몰수를 질량·구간 평균 유량으로 변환 / Accepted mole delivery converted to mass and interval-mean flow

Family / navigation ID: `storage.adsorption_delivery_mass_flow`

Import module: `h2physics.storage.product_delivery`; selected entry: `AdsorptionProductMassFlow`.

#### `h2physics.storage.product_delivery.AdsorptionProductMassFlow`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/storage/product_delivery.py#L23)

Signed species mass changes and interval-average delivery rates.

``molar_masses_kg_mol`` must follow the exact species order in the accepted
vessel ledger. ``elapsed_s`` is supplied by the caller and defines only the
averaging interval; this receipt does not imply a time-resolved flow profile.

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `delivery` | `AdsorptionVesselDelivery` | `required` |
| `species` | `tuple[str, ...]` | `required` |
| `molar_masses_kg_mol` | `np.ndarray` | `required` |
| `elapsed_s` | `float` | `required` |
| `component_mass_change_kg` | `np.ndarray` | `field(init=False)` |
| `component_average_mass_rate_kg_s` | `np.ndarray` | `field(init=False)` |
| `delivered_product_mass_kg` | `float` | `field(init=False)` |
| `delivered_product_average_mass_rate_kg_s` | `float` | `field(init=False)` |

### Returned value / 반환값

`AdsorptionProductMassFlow`

### Related input/return records / 관련 입력·반환 객체

#### `h2physics.adapters.finite_adsorption_vessel.AdsorptionVesselDelivery`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/finite_adsorption_vessel.py#L308)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `charged` | `AdsorptionVesselSnapshot` | `required` |
| `discharged` | `AdsorptionVesselSnapshot` | `required` |
| `free_gas_change_mol` | `np.ndarray` | `required` |
| `adsorbed_change_mol` | `np.ndarray` | `required` |
| `total_change_mol` | `np.ndarray` | `required` |
| `delivery_species` | `tuple[str, ...]` | `required` |
| `delivered_product_mol` | `float` | `required` |

#### `h2physics.adapters.finite_adsorption_vessel.AdsorptionVesselSnapshot`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/finite_adsorption_vessel.py#L234)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `vessel_id` | `str` | `required` |
| `geometry` | `AdsorptionVesselGeometry` | `required` |
| `adsorption_basis` | `AdsorptionBasis` | `required` |
| `gas_composition_id` | `str` | `required` |
| `gas_state` | `ThermoState` | `required` |
| `equilibrium` | `AdsorptionState` | `required` |
| `free_gas_component_mol` | `np.ndarray` | `required` |
| `adsorbed_component_mol` | `np.ndarray` | `required` |
| `total_component_mol` | `np.ndarray` | `required` |
| `adsorbed_standard_uncertainty_component_mol` | `np.ndarray &#124; None` | `None` |
| `uncertainty_semantics` | `str` | `'unqualified'` |
| `uncertainty_source_ids` | `tuple[str, ...]` | `()` |

Computed properties: `total_inventory_mol`.


<a id="module-h2physics-adapters-psa-psadynabed-snapshot"></a>

## 외부 흡착층의 온도·흡착량·성분 재고 읽기 / Native thermal adsorption-bed states and inventories

Family / navigation ID: `storage.adsorption_thermal`

Import module: `h2physics.adapters.psa`; selected entry: `PsaDynaBed.snapshot`.

#### `h2physics.adapters.psa.PsaDynaBed`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/psa.py#L62)

Expose an existing loading-LDF native Bed to a Python composition solver.

This adapter does not implement a PSA schedule or duplicate bed equations.
The caller supplies all internal/boundary face transfers in the explicit
native energy reference. Native ideal/PR energy is not a CoolProp reference.
The caller owns the native bed configuration; changing it invalidates the
declared basis/parameter evidence until that identity is updated.

```python
PsaDynaBed(native_bed, basis: AdsorptionBasis, domain: AdsorptionDomain, *, energy_reference_id: str)
```

#### `h2physics.adapters.psa.PsaDynaBed.snapshot`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/psa.py#L94)

```python
snapshot(self, state) -> BedSnapshot
```

### Returned value / 반환값

`BedSnapshot`

### Related input/return records / 관련 입력·반환 객체

#### `h2physics.adsorption.AdsorptionBasis`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adsorption.py#L13)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `material_id` | `str` | `required` |
| `species` | `tuple[str, ...]` | `required` |
| `amount_basis_id` | `str` | `required` |
| `engine_id` | `str` | `required` |
| `parameter_id` | `str` | `required` |
| `references` | `tuple[str, ...]` | `required` |
| `loading_definition` | `Literal['absolute', 'surface_excess', 'source_defined']` | `'source_defined'` |

#### `h2physics.adsorption.AdsorptionDomain`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adsorption.py#L39)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `minimum_temperature_k` | `float` | `required` |
| `maximum_temperature_k` | `float` | `required` |
| `maximum_total_pressure_pa` | `float` | `required` |
| `minimum_total_pressure_pa` | `float` | `0.0` |

#### `h2physics.adapters.psa.BedSnapshot`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/psa.py#L41)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `basis` | `AdsorptionBasis` | `required` |
| `energy_reference_id` | `str` | `required` |
| `gas_inventory_mol` | `np.ndarray` | `required` |
| `loading_mol_kg` | `np.ndarray` | `required` |
| `temperature_k` | `np.ndarray` | `required` |
| `wall_temperature_k` | `np.ndarray` | `required` |
| `pressure_pa` | `np.ndarray` | `required` |
| `mole_fractions` | `np.ndarray` | `required` |
| `total_inventory_mol` | `np.ndarray` | `required` |
| `stored_energy_j` | `float` | `required` |


<a id="module-h2physics-storage-hydride-vanthoffplateau-fugacity_pa"></a>

## 수소화물 평형 압력·기울기·이력 효과 / Hydride equilibrium plateau, slope and hysteresis

Family / navigation ID: `storage.hydride_equilibrium`

Import module: `h2physics.storage.hydride`; selected entry: `VanthoffPlateau.fugacity_pa`.

#### `h2physics.storage.hydride.VanthoffPlateau`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/storage/hydride.py#L37)

Desorption-positive ΔH/ΔS per mole H2; optional log-fugacity slope/gap.

ln(f_eq/f_ref) = ΔS/R − ΔH/(R T) + slope (x − 0.5) ± gap/2.
This is a plateau approximation, not a full alpha/beta PCT equation.
Use a different native equilibrium object for nonideal phase transitions.

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `desorption_enthalpy_j_mol_h2` | `float` | `required` |
| `desorption_entropy_j_mol_h2_k` | `float` | `required` |
| `reference_fugacity_pa` | `float` | `required` |
| `log_fugacity_slope` | `float` | `0.0` |
| `log_hysteresis_gap` | `float` | `0.0` |

#### `h2physics.storage.hydride.VanthoffPlateau.fugacity_pa`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/storage/hydride.py#L59)

```python
fugacity_pa(self, temperature_k: float, fraction: float, branch: Branch) -> float
```

### Returned value / 반환값

`float`


<a id="module-h2physics-storage-finite_hydride-finitehydridebed-simulate"></a>

## 유한 기체·고체 재고와 수소화 반응·열응답 / Finite gas/solid storage, uptake kinetics and heat

Family / navigation ID: `storage.hydride_dynamic`

Import module: `h2physics.storage.finite_hydride`; selected entry: `FiniteHydrideBed.simulate`.

#### `h2physics.storage.finite_hydride.FiniteHydrideBed`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/storage/finite_hydride.py#L549)

A constant-free-volume gas/solid core, with a closed simulation convenience.

The host owns these new conservation equations and delegates every gas state,
fugacity and derivative to native thermodynamics. Existing HydrideKinetics
owns the reaction rate, including hysteresis. ``simulate`` remains closed;
ported compositions reuse ``snapshot_from_inventory`` and ``rates`` directly.

```python
FiniteHydrideBed(parameters: HydrideParameters, kinetics: HydrideKinetics, gas: HydrideGasThermodynamics, energy_reference: BoundHydrogenEnergyReference, domain: FiniteHydrideDomain, *, free_gas_volume_m3: float, gas_solid_conductance_w_k: float, gas_ambient_conductance_w_k: float=0.0)
```

#### `h2physics.storage.finite_hydride.FiniteHydrideBed.simulate`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/storage/finite_hydride.py#L710)

Integrate a closed bed or one bed with an explicit signed H2 stream.

A supplied gas port contributes native stream enthalpy and net material
to cumulative trace ledgers. It does not provide a pressure-flow law.

```python
simulate(self, time_s, initial_solid: HydrideState, initial_gas: ThermoState, *, boundary: FiniteHydrideHeatBoundary, clock_id: str, maximum_step_s: float, relative_tolerance: float=1e-09, energy_scale_j: float=1000.0, isothermal_temperature_k: float | None=None, gas_port: FiniteHydrideGasPortBoundary | None=None) -> FiniteHydrideTrace
```

### Returned value / 반환값

`FiniteHydrideTrace`

### Related input/return records / 관련 입력·반환 객체

#### `h2physics.storage.hydride.HydrideParameters`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/storage/hydride.py#L117)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `hydrogen_capacity_kg` | `float` | `required` |
| `heat_capacity_j_k` | `float` | `required` |
| `reaction_heat_j_mol_h2` | `float` | `required` |
| `hydrogen_molar_mass_kg_mol` | `float` | `required` |
| `ambient_conductance_w_k` | `float` | `required` |

Computed properties: `full_reaction_heat_j`.

#### `h2physics.storage.hydride.HydrideKinetics`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/storage/hydride.py#L93)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `equilibrium` | `HydrideEquilibrium` | `required` |
| `absorption_rate` | `Callable[[float], float]` | `required` |
| `desorption_rate` | `Callable[[float], float]` | `required` |

#### `h2physics.storage.finite_hydride.HydrideGasThermodynamics`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/storage/finite_hydride.py#L33)

Pure H2 thermodynamic functions, with actual caller-owned native objects.

``isothermal_mass_energy_derivative`` returns d[m*u(m/V,T)]/dm at fixed T,V
in J/kg, using the native EOS. It is only required by isothermal reference
runs. Normal/para identity and the energy zero are in ``basis``; no spin
conversion is performed by this contract.

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `basis` | `PropertyBasis` | `required` |
| `molar_mass_kg_mol` | `float` | `required` |
| `state_rho_u` | `Callable[[float, float], ThermoState]` | `required` |
| `state_pt` | `Callable[[float, float], ThermoState]` | `required` |
| `fugacity_pa` | `Callable[[ThermoState], float]` | `required` |
| `source_id` | `str` | `required` |
| `native_objects` | `tuple` | `required` |
| `state_rho_t` | `Callable &#124; None` | `None` |
| `isothermal_mass_energy_derivative` | `Callable &#124; None` | `None` |

#### `h2physics.storage.finite_hydride.BoundHydrogenEnergyReference`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/storage/finite_hydride.py#L118)

One bound-H2 chemical internal-energy increment on the native gas zero.

With negligible condensed-phase PV, e_bound = h_H2,ref - DeltaH_des,ref.
Thus closed-system absorption DeltaU = P*v_mol - DeltaH_des at reference,
which becomes RT - DeltaH_des for an ideal gas, rather than -DeltaH_des.
Constant solid heat capacity is independent of loading in this reduced level.

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `gas_reference_state` | `ThermoState` | `required` |
| `hydrogen_molar_mass_kg_mol` | `float` | `required` |
| `desorption_enthalpy_j_mol_h2` | `float` | `required` |
| `evidence_id` | `str` | `required` |

Computed properties: `bound_energy_j_mol_h2`, `reference_absorption_internal_energy_j_mol_h2`.

#### `h2physics.storage.finite_hydride.FiniteHydrideDomain`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/storage/finite_hydride.py#L159)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `minimum_temperature_k` | `float` | `required` |
| `maximum_temperature_k` | `float` | `required` |
| `minimum_pressure_pa` | `float` | `required` |
| `maximum_pressure_pa` | `float` | `required` |
| `minimum_gas_mass_kg` | `float` | `required` |

#### `h2physics.storage.hydride.HydrideState`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/storage/hydride.py#L150)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `fraction` | `float` | `required` |
| `temperature_k` | `float` | `required` |

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

#### `h2physics.storage.finite_hydride.FiniteHydrideHeatBoundary`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/storage/finite_hydride.py#L207)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `clock_id` | `str` | `required` |
| `support_start_s` | `float` | `required` |
| `support_end_s` | `float` | `required` |
| `callback` | `Callable[[float, FiniteHydrideSnapshot], FiniteHydrideHeatInput]` | `required` |
| `source_id` | `str` | `required` |

#### `h2physics.storage.finite_hydride.FiniteHydrideGasPortBoundary`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/storage/finite_hydride.py#L259)

Caller-owned H2 stream schedule on the same absolute clock as the bed.

The callback supplies the signed mass flow and its native stream state.
The bed still owns the native EOS, finite inventory, existing hydride rates
and energy balance; this boundary does not calculate a pressure-flow law.

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `clock_id` | `str` | `required` |
| `support_start_s` | `float` | `required` |
| `support_end_s` | `float` | `required` |
| `callback` | `Callable[[float, FiniteHydrideSnapshot], FiniteHydrideGasPortInput]` | `required` |
| `source_id` | `str` | `required` |

#### `h2physics.storage.finite_hydride.FiniteHydrideTrace`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/storage/finite_hydride.py#L330)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `time_s` | `np.ndarray` | `required` |
| `snapshots` | `tuple[FiniteHydrideSnapshot, ...]` | `required` |
| `integrated_external_gas_heat_j` | `np.ndarray` | `required` |
| `integrated_external_solid_heat_j` | `np.ndarray` | `required` |
| `integrated_material_enthalpy_to_solid_j` | `np.ndarray` | `required` |
| `integrated_gas_solid_heat_to_gas_j` | `np.ndarray` | `required` |
| `integrated_nominal_reaction_heat_j` | `np.ndarray` | `required` |
| `integrated_hydrogen_uptake_kg` | `np.ndarray` | `required` |
| `integrated_gas_thermostat_heat_j` | `np.ndarray` | `required` |
| `integrated_solid_thermostat_heat_j` | `np.ndarray` | `required` |
| `gas_energy_residual_j` | `np.ndarray` | `required` |
| `solid_energy_residual_j` | `np.ndarray` | `required` |
| `total_energy_residual_j` | `np.ndarray` | `required` |
| `total_hydrogen_residual_kg` | `np.ndarray` | `required` |
| `gas_transfer_residual_kg` | `np.ndarray` | `required` |
| `solid_transfer_residual_kg` | `np.ndarray` | `required` |
| `gas_integrated_state_residual_j` | `np.ndarray` | `required` |
| `clock_id` | `str` | `required` |
| `termination` | `str` | `required` |
| `event_time_s` | `float &#124; None` | `required` |
| `isothermal_temperature_k` | `float &#124; None` | `required` |
| `gas_thermodynamics` | `HydrideGasThermodynamics` | `required` |
| `energy_reference` | `BoundHydrogenEnergyReference` | `required` |
| `native_solution` | `object` | `required` |
| `energy_scale_j` | `float` | `required` |
| `integrated_external_gas_mass_kg` | `np.ndarray &#124; None` | `None` |
| `integrated_external_gas_enthalpy_j` | `np.ndarray &#124; None` | `None` |
| `gas_port_boundary` | `FiniteHydrideGasPortBoundary &#124; None` | `None` |

#### `h2physics.core.PropertyBasis`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/core.py#L97)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `fluid` | `str` | `required` |
| `reference_id` | `str` | `required` |
| `spin_composition` | `str` | `'unspecified'` |

#### `h2physics.storage.finite_hydride.FiniteHydrideHeatInput`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/storage/finite_hydride.py#L195)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `bath_temperature_k` | `float` | `required` |
| `gas_heat_w` | `float` | `0.0` |
| `solid_heat_w` | `float` | `0.0` |

#### `h2physics.storage.finite_hydride.FiniteHydrideSnapshot`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/storage/finite_hydride.py#L175)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `time_s` | `float` | `required` |
| `fraction` | `float` | `required` |
| `solid_temperature_k` | `float` | `required` |
| `gas_mass_kg` | `float` | `required` |
| `solid_hydrogen_mass_kg` | `float` | `required` |
| `gas` | `ThermoState` | `required` |
| `gas_internal_energy_j` | `float` | `required` |
| `solid_internal_energy_j` | `float` | `required` |

Computed properties: `total_hydrogen_mass_kg`, `total_internal_energy_j`.

#### `h2physics.storage.finite_hydride.FiniteHydrideGasPortInput`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/storage/finite_hydride.py#L234)

One signed H2 mass stream with a state on the bed's native basis.

Positive mass flow enters the bed; negative flow leaves it. Stream enthalpy
is taken from the original provider state and is never inferred from the
bed state for an inlet. An outlet must use the exact current bed state.

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `mass_flow_kg_s` | `float` | `required` |
| `stream_state` | `ThermoState` | `required` |
| `evidence_id` | `str` | `required` |

Computed properties: `enthalpy_flow_w`.


<a id="module-h2physics-storage-hydride_compressor-hydridethermalcompressor-run"></a>

## 유한 공급·수신 탱크 사이 열구동 수소화물 압축 / Thermally cycled bed between finite source and receiver vessels

Family / navigation ID: `storage.hydride_compressor`

Import module: `h2physics.storage.hydride_compressor`; selected entry: `HydrideThermalCompressor.run`.

#### `h2physics.storage.hydride_compressor.HydrideThermalCompressor`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/storage/hydride_compressor.py#L365)

One bed, finite source/receiver and staged ports in one coupled solve.

Heating/cooling baths are explicit external utilities, not finite H2
reservoirs. Receiver mixing retains donor stagnation enthalpy, including
nozzle kinetic energy that dissipates inside the receiving control volume.

```python
HydrideThermalCompressor(native: HydrideCompressorNative, *, bed: FiniteHydrideBed, source: FiniteHydrideGasVessel, receiver: FiniteHydrideGasVessel, nozzle: HomogeneousIsentropicNozzle, inlet_opening: NozzleOpening, outlet_opening: NozzleOpening, evidence: HydrideCompressorEvidence, tolerances: InventoryTolerances | None=None)
```

#### `h2physics.storage.hydride_compressor.HydrideThermalCompressor.run`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/storage/hydride_compressor.py#L487)

```python
run(self, stages: Sequence[HydrideCompressorStage], *, initial_solid: HydrideState, initial_bed_gas: ThermoState, sample_interval_s: float, maximum_step_s: float, relative_tolerance: float=1e-08, energy_scale_j: float=1000.0) -> HydrideCompressorTrace
```

### Returned value / 반환값

`HydrideCompressorTrace`

### Related input/return records / 관련 입력·반환 객체

#### `h2physics.storage.hydride_compressor.HydrideCompressorNative`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/storage/hydride_compressor.py#L114)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `tank` | `Any` | `required` |
| `properties` | `Any` | `required` |
| `streams` | `Any` | `required` |
| `source_id` | `str` | `required` |

#### `h2physics.storage.hydride_compressor.FiniteHydrideGasVessel`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/storage/hydride_compressor.py#L129)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `vessel_id` | `str` | `required` |
| `native_tank` | `Any` | `required` |
| `initial_native_state` | `Any` | `required` |
| `bridge` | `Lh2dtProperties` | `required` |
| `minimum_gas_mass_kg` | `float` | `required` |
| `source_id` | `str` | `required` |

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

#### `h2physics.storage.hydride_compressor.HydrideCompressorEvidence`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/storage/hydride_compressor.py#L170)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `source_id` | `str` | `required` |
| `material_parameter_source_id` | `str` | `required` |
| `thermal_and_geometry_source_id` | `str` | `required` |
| `initial_inventory_source_id` | `str` | `required` |
| `cycle_source_id` | `str` | `required` |
| `clock_id` | `str` | `required` |
| `origin` | `Origin` | `required` |

#### `h2physics.dynamics.InventoryTolerances`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/dynamics.py#L33)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `mass_absolute_kg` | `float` | `1e-08` |
| `energy_absolute_j` | `float` | `0.0001` |
| `relative` | `float` | `1e-08` |

#### `h2physics.storage.hydride_compressor.HydrideCompressorStage`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/storage/hydride_compressor.py#L188)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `stage_id` | `str` | `required` |
| `start_time_s` | `float` | `required` |
| `end_time_s` | `float` | `required` |
| `inlet_opening_fraction` | `float` | `required` |
| `outlet_opening_fraction` | `float` | `required` |
| `bed_heat` | `FiniteHydrideHeatBoundary` | `required` |
| `source_bath_temperature_k` | `float` | `required` |
| `receiver_bath_temperature_k` | `float` | `required` |
| `source_wall_heat_w` | `float` | `0.0` |
| `receiver_wall_heat_w` | `float` | `0.0` |

#### `h2physics.storage.hydride.HydrideState`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/storage/hydride.py#L150)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `fraction` | `float` | `required` |
| `temperature_k` | `float` | `required` |

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

#### `h2physics.storage.hydride_compressor.HydrideCompressorTrace`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/storage/hydride_compressor.py#L273)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `compressor` | `Any` | `required` |
| `evidence` | `HydrideCompressorEvidence` | `required` |
| `initial_snapshot` | `HydrideCompressorSnapshot` | `required` |
| `segments` | `tuple[HydrideCompressorSegment, ...]` | `required` |
| `termination` | `str` | `required` |
| `event_time_s` | `float &#124; None` | `required` |
| `energy_scale_j` | `float` | `required` |

Computed properties: `points`, `delivered_hydrogen_kg`, `admitted_hydrogen_kg`, `delivered_above_source_mass_kg`.

#### `h2physics.storage.finite_hydride.FiniteHydrideHeatBoundary`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/storage/finite_hydride.py#L207)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `clock_id` | `str` | `required` |
| `support_start_s` | `float` | `required` |
| `support_end_s` | `float` | `required` |
| `callback` | `Callable[[float, FiniteHydrideSnapshot], FiniteHydrideHeatInput]` | `required` |
| `source_id` | `str` | `required` |

#### `h2physics.core.PropertyBasis`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/core.py#L97)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `fluid` | `str` | `required` |
| `reference_id` | `str` | `required` |
| `spin_composition` | `str` | `'unspecified'` |

#### `h2physics.storage.hydride_compressor.HydrideCompressorSnapshot`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/storage/hydride_compressor.py#L220)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `time_s` | `float` | `required` |
| `stage_id` | `str` | `required` |
| `bed` | `FiniteHydrideSnapshot` | `required` |
| `source_native_state` | `Any` | `required` |
| `receiver_native_state` | `Any` | `required` |
| `source` | `ThermoState` | `required` |
| `receiver` | `ThermoState` | `required` |
| `bed_inventory` | `ConservedInventory` | `required` |
| `source_inventory` | `ConservedInventory` | `required` |
| `receiver_inventory` | `ConservedInventory` | `required` |

Computed properties: `total_hydrogen_mass_kg`, `total_internal_energy_j`.

#### `h2physics.storage.hydride_compressor.HydrideCompressorSegment`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/storage/hydride_compressor.py#L264)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `stage` | `HydrideCompressorStage` | `required` |
| `points` | `tuple[HydrideCompressorPoint, ...]` | `required` |
| `native_solution` | `Any` | `required` |
| `source_receiver_pressure_crossings_s` | `tuple[float, ...]` | `required` |
| `delivered_above_source_mass_kg` | `float` | `required` |


<a id="module-h2physics-adapters-carrier_conversion-finitecarrierconversion-run"></a>

## LOHC·암모니아의 지정 전환량·유한 재고·인출 / Prescribed finite LOHC/ammonia conversion and takeoff

Family / navigation ID: `storage.carrier_reaction`

Import module: `h2physics.adapters.carrier_conversion`; selected entry: `FiniteCarrierConversion.run`.

#### `h2physics.adapters.carrier_conversion.FiniteCarrierConversion`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/carrier_conversion.py#L513)

One declared carrier path, finite packets and shared constant-P calorimetry.

Stage temperature/extent/withdrawal are supplied constraints. Feeds are
uniquely identified finite packets, consumed once in this run, not infinite
or automatically replenished reservoirs. There is no new physical ODE.

```python
FiniteCarrierConversion(pathway, caloric_source, evidence, *, tolerances=ThermochemicalTolerances())
```

#### `h2physics.adapters.carrier_conversion.FiniteCarrierConversion.run`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/carrier_conversion.py#L595)

```python
run(self, initial, stages, *, feed_bindings=None)
```

The source has no explicit return annotation; inspect its return statements and the domain manual. No return type is invented by this generator.

### Returned value / 반환값

`CarrierConversionResult`

This return contract was reviewed from the implementation; it is not an annotation present in the source signature.

### Related input/return records / 관련 입력·반환 객체

#### `h2physics.adapters.carrier_conversion.CarrierConversionResult`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/carrier_conversion.py#L389)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `owner` | `'FiniteCarrierConversion'` | `required` |
| `pathway` | `CarrierPathway` | `required` |
| `caloric_source` | `CarrierCaloricSource` | `required` |
| `kernel` | `FiniteThermochemicalCycle` | `required` |
| `process_trace` | `object` | `required` |
| `evidence` | `CarrierProcessEvidence` | `required` |
| `hydrogen_initial_mol` | `float` | `required` |
| `hydrogen_final_mol` | `float` | `required` |
| `hydrogen_formed_mol` | `float` | `required` |
| `hydrogen_consumed_mol` | `float` | `required` |
| `hydrogen_withdrawn_mol` | `float` | `required` |
| `hydrogen_species_residual_mol` | `float` | `required` |
| `feed_bindings` | `tuple` | `required` |
| `status` | `str` | `STATUS` |

Computed properties: `hydrogen_mass_ledger_kg`.

#### `h2physics.adapters.carrier_conversion.CarrierPathway`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/carrier_conversion.py#L213)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `identifier` | `str` | `required` |
| `kind` | `str` | `required` |
| `reaction` | `StoichiometricReaction` | `required` |
| `hydrogen_id` | `str` | `required` |
| `carrier_species` | `tuple[str, ...]` | `required` |
| `phase_reference_id` | `str` | `required` |
| `source_id` | `str` | `required` |
| `origin` | `Origin` | `required` |
| `original_source` | `object` | `None` |

#### `h2physics.adapters.carrier_conversion.CarrierProcessEvidence`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/carrier_conversion.py#L373)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `process_id` | `str` | `required` |
| `clock_id` | `str` | `required` |
| `region_id` | `str` | `required` |
| `phase_reference_id` | `str` | `required` |
| `extent_source_id` | `str` | `required` |
| `thermal_boundary_id` | `str` | `required` |
| `withdrawal_assumption_id` | `str` | `required` |
| `origin` | `Origin` | `required` |


<a id="module-h2physics-storage-solid_reaction-finitesolidreactionreactor-run"></a>

## 고체 분해·가수분해의 유한 공급·반응·열수지 / Finite solid decomposition/hydrolysis with supplies and heat

Family / navigation ID: `storage.solid_reaction`

Import module: `h2physics.storage.solid_reaction`; selected entry: `FiniteSolidReactionReactor.run`.

#### `h2physics.storage.solid_reaction.FiniteSolidReactionReactor`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/storage/solid_reaction.py#L332)

One forward reaction, common T and externally maintained constant P.

The existing thermochemical kernel owns every phase caloric/material step.
This class adds finite supply debits, frozen-start-rate time discretization,
optional declared limiting-reactant truncation and thermal root assembly.
It predicts no equilibrium, gas EOS, volume, separation or intrinsic rate.

```python
FiniteSolidReactionReactor(enthalpy: MolarEnthalpyProvider, kinetics: SolidReactionKinetics, evidence: SolidReactionEvidence, *, hydrogen_species: str, mode: str, water_species: str | None=None, tolerances: ThermochemicalTolerances=ThermochemicalTolerances(), maximum_temperature_iterations: int=100)
```

#### `h2physics.storage.solid_reaction.FiniteSolidReactionReactor.run`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/storage/solid_reaction.py#L587)

```python
run(self, initial: ThermochemicalInventory, steps, *, supplies=()) -> SolidReactionTrace
```

### Returned value / 반환값

`SolidReactionTrace`

### Related input/return records / 관련 입력·반환 객체

#### `h2physics.reactions.MolarEnthalpyProvider`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/reactions.py#L146)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `species` | `tuple[ChemicalSpecies, ...]` | `required` |
| `basis_id` | `str` | `required` |

#### `h2physics.storage.solid_reaction.SolidReactionKinetics`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/storage/solid_reaction.py#L114)

Caller rate in mol extent/s, evaluated once after beginning-of-step mixing.

Parameters are explicit immutable scalars. Neither their units nor their
material applicability are inferred; the source identity must describe them.

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `reaction` | `StoichiometricReaction` | `required` |
| `rate` | `Callable[[SolidRateState, Mapping[str, float]], float]` | `required` |
| `identifier` | `str` | `required` |
| `source_id` | `str` | `required` |
| `origin` | `Origin` | `required` |
| `parameters` | `Mapping[str, float]` | `field(default_factory=dict)` |

#### `h2physics.storage.solid_reaction.SolidReactionEvidence`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/storage/solid_reaction.py#L81)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `process_id` | `str` | `required` |
| `stoichiometry_source_id` | `str` | `required` |
| `caloric_basis_id` | `str` | `required` |
| `common_temperature_assumption_id` | `str` | `required` |
| `fixed_pressure_boundary_id` | `str` | `required` |
| `component_takeoff_assumption_id` | `str` | `required` |
| `origin` | `Origin` | `required` |

#### `h2physics.thermochemical.ThermochemicalTolerances`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/thermochemical.py#L146)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `amount_mol` | `float` | `1e-10` |
| `mass_kg` | `float` | `1e-12` |
| `energy_j` | `float` | `1e-06` |
| `temperature_k` | `float` | `1e-09` |
| `relative` | `float` | `1e-10` |

#### `h2physics.thermochemical.ThermochemicalInventory`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/thermochemical.py#L62)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `amounts_mol` | `Mapping[str, float]` | `required` |
| `temperature_k` | `float` | `required` |
| `pressure_pa` | `float` | `required` |
| `energy_basis_id` | `str` | `required` |

#### `h2physics.storage.solid_reaction.SolidReactionTrace`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/storage/solid_reaction.py#L256)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `initial` | `ThermochemicalInventory` | `required` |
| `final` | `ThermochemicalInventory` | `required` |
| `initial_supplies` | `tuple[SolidSupply, ...]` | `required` |
| `remaining_supplies` | `tuple[SolidSupply, ...]` | `required` |
| `steps` | `tuple[SolidReactionStepResult, ...]` | `required` |
| `species` | `tuple` | `required` |
| `elements` | `tuple[str, ...]` | `required` |
| `exported_mol` | `np.ndarray` | `required` |
| `exported_enthalpy_j` | `float` | `required` |
| `hydrogen_generated_mol` | `float` | `required` |
| `heat_input_j` | `float` | `required` |
| `element_residual_mol` | `np.ndarray` | `required` |
| `mass_residual_kg` | `float` | `required` |
| `enthalpy_residual_j` | `float` | `required` |
| `evidence` | `SolidReactionEvidence` | `required` |
| `kinetics` | `SolidReactionKinetics` | `required` |
| `enthalpy_provider` | `object` | `required` |
| `kernel` | `FiniteThermochemicalCycle` | `required` |

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

#### `h2physics.reactions.StoichiometricReaction`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/reactions.py#L41)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `identifier` | `str` | `required` |
| `species` | `tuple[ChemicalSpecies, ...]` | `required` |
| `coefficients` | `tuple[float, ...]` | `required` |

#### `h2physics.storage.solid_reaction.SolidRateState`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/storage/solid_reaction.py#L105)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `time_s` | `float` | `required` |
| `clock_id` | `str` | `required` |
| `inventory` | `ThermochemicalInventory` | `required` |
| `accumulated_extent_mol` | `float` | `required` |
| `forward_extent_limit_mol` | `float` | `required` |

#### `h2physics.storage.solid_reaction.SolidSupply`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/storage/solid_reaction.py#L145)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `identifier` | `str` | `required` |
| `inventory` | `ThermochemicalInventory` | `required` |
| `source_id` | `str` | `required` |
| `origin` | `Origin` | `required` |

#### `h2physics.storage.solid_reaction.SolidReactionStepResult`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/storage/solid_reaction.py#L230)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `step` | `SolidReactionStep` | `required` |
| `before` | `ThermochemicalInventory` | `required` |
| `mixed` | `ThermochemicalInventory` | `required` |
| `after` | `ThermochemicalInventory` | `required` |
| `rate_state` | `SolidRateState` | `required` |
| `rate_mol_extent_s` | `float` | `required` |
| `requested_extent_mol` | `float` | `required` |
| `accepted_extent_mol` | `float` | `required` |
| `inventory_limited` | `bool` | `required` |
| `limiting_species` | `tuple[str, ...]` | `required` |
| `mixing` | `SolidThermalSolve &#124; None` | `required` |
| `reaction` | `SolidThermalSolve` | `required` |
| `takeoff` | `ThermochemicalTrace &#124; None` | `required` |
| `hydrogen_generated_mol` | `float` | `required` |
| `feed_mol` | `np.ndarray` | `required` |
| `removed_mol` | `np.ndarray` | `required` |
| `feed_enthalpy_j` | `float` | `required` |
| `removed_enthalpy_j` | `float` | `required` |


<a id="module-h2physics-storage-microsphere-microspherestorage-simulate"></a>

## 미소구 내부 기체와 구형 벽 수소 이동 / Finite gas cavity coupled to spherical wall transport

Family / navigation ID: `storage.microsphere`

Import module: `h2physics.storage.microsphere`; selected entry: `MicrosphereStorage.simulate`.

#### `h2physics.storage.microsphere.MicrosphereStorage`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/storage/microsphere.py#L71)

Rigid single cavity and homogeneous spherical membrane with finite storage.

Molecular H2 crosses equilibrium surfaces; D(T), solubility and optional
trap kinetics are caller-owned. Native density/T states and fugacity reuse
the existing finite-gas property contract, without a second EOS or ODE.
Uniform gas/wall temperature is prescribed on one explicit clock. Thermal
duty, stress, fracture, optical effects and a sphere-size population are
unresolved at this level.

```python
MicrosphereStorage(*, inner_radius_m: float, outer_radius_m: float, cells: int, diffusivity_m2_s: Callable[[float], float], solubility: PowerLawSolubility, gas: HydrideGasThermodynamics, domain: MicrosphereDomain, parameter_evidence: str, traps: tuple[TrapPopulation, ...]=())
```

#### `h2physics.storage.microsphere.MicrosphereStorage.simulate`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/storage/microsphere.py#L125)

```python
simulate(self, time_s, initial_gas_mol: float, initial_mobile_mol_m3, *, temperature_k: Callable[[float], float], external_hydrogen_fugacity_pa: Callable[[float], float] | None=None, external_wall_condition: Callable[[float, float], SurfaceCondition] | None=None, clock_id: str, boundary_evidence: str, initial_trapped_mol_m3=None, relative_tolerance: float=1e-08, absolute_tolerance_mol_m3: float=1e-10, maximum_step_s: float=np.inf) -> MicrosphereResult
```

### Returned value / 반환값

`MicrosphereResult`

### Related input/return records / 관련 입력·반환 객체

#### `h2physics.materials.transport.PowerLawSolubility`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/materials/transport.py#L66)

Surface concentration = coefficient(T) × hydrogen fugacity**exponent.

coefficient(T) has units mol(entity) / (m³ Pa**exponent). An exponent of
0.5 represents a Sieverts-type equilibrium and 1 a Henry-type equilibrium;
choosing either requires appropriate material and surface evidence.

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `carrier` | `HydrogenCarrier` | `required` |
| `coefficient` | `Callable[[float], float]` | `required` |
| `exponent` | `float` | `required` |

#### `h2physics.storage.finite_hydride.HydrideGasThermodynamics`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/storage/finite_hydride.py#L33)

Pure H2 thermodynamic functions, with actual caller-owned native objects.

``isothermal_mass_energy_derivative`` returns d[m*u(m/V,T)]/dm at fixed T,V
in J/kg, using the native EOS. It is only required by isothermal reference
runs. Normal/para identity and the energy zero are in ``basis``; no spin
conversion is performed by this contract.

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `basis` | `PropertyBasis` | `required` |
| `molar_mass_kg_mol` | `float` | `required` |
| `state_rho_u` | `Callable[[float, float], ThermoState]` | `required` |
| `state_pt` | `Callable[[float, float], ThermoState]` | `required` |
| `fugacity_pa` | `Callable[[ThermoState], float]` | `required` |
| `source_id` | `str` | `required` |
| `native_objects` | `tuple` | `required` |
| `state_rho_t` | `Callable &#124; None` | `None` |
| `isothermal_mass_energy_derivative` | `Callable &#124; None` | `None` |

#### `h2physics.storage.microsphere.MicrosphereDomain`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/storage/microsphere.py#L28)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `minimum_temperature_k` | `float` | `required` |
| `maximum_temperature_k` | `float` | `required` |
| `minimum_pressure_pa` | `float` | `required` |
| `maximum_pressure_pa` | `float` | `required` |
| `minimum_gas_inventory_mol` | `float` | `required` |

#### `h2physics.materials.transport.TrapPopulation`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/materials/transport.py#L565)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `site_concentration_mol_m3` | `float` | `required` |
| `capture_m3_mol_s` | `Callable[[float], float]` | `required` |
| `release_s_inv` | `Callable[[float], float]` | `required` |

#### `h2physics.materials.transport.SurfaceCondition`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/materials/transport.py#L390)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `kind` | `Literal['concentration', 'flux']` | `required` |
| `value` | `float` | `required` |

#### `h2physics.storage.microsphere.MicrosphereResult`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/storage/microsphere.py#L44)

Prescribed-temperature mass transport, not a coupled energy prediction.

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `transport` | `TransportResult` | `required` |
| `gas_states` | `tuple[ThermoState, ...]` | `required` |
| `gas_fugacity_pa` | `np.ndarray` | `required` |
| `gas_transfer_residual_mol` | `np.ndarray` | `required` |
| `total_hydrogen_mass_kg` | `np.ndarray` | `required` |
| `clock_id` | `str` | `required` |
| `boundary_evidence` | `str` | `required` |
| `parameter_evidence` | `str` | `required` |

Computed properties: `time_s`, `gas_inventory_mol`.

#### `h2physics.materials.transport.HydrogenCarrier`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/materials/transport.py#L51)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `identity` | `Literal['atomic_hydrogen', 'molecular_hydrogen']` | `required` |
| `molar_mass_kg_mol` | `float` | `required` |

Computed properties: `hydrogen_atoms_per_entity`.

#### `h2physics.core.PropertyBasis`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/core.py#L97)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `fluid` | `str` | `required` |
| `reference_id` | `str` | `required` |
| `spin_composition` | `str` | `'unspecified'` |

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

#### `h2physics.materials.finite_volume.TransportResult`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/materials/finite_volume.py#L288)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `carrier` | `HydrogenCarrier` | `required` |
| `mesh` | `DiffusionMesh` | `required` |
| `time_s` | `np.ndarray` | `required` |
| `mobile_mol_m3` | `np.ndarray` | `required` |
| `trapped_mol_m3` | `np.ndarray` | `required` |
| `left_integrated_mol` | `np.ndarray` | `required` |
| `right_integrated_mol` | `np.ndarray` | `required` |
| `wall_inventory_mol` | `np.ndarray` | `required` |
| `wall_residual_mol` | `np.ndarray` | `required` |
| `total_residual_mol` | `np.ndarray` | `required` |
| `left_inventory_mol` | `np.ndarray &#124; None` | `required` |
| `right_inventory_mol` | `np.ndarray &#124; None` | `required` |
| `native_solution` | `object` | `required` |
| `stress_potential` | `HydrostaticStressPotential &#124; None` | `field(default=None, repr=False, compare=False)` |

Computed properties: `function_evaluations`.


<a id="module-h2physics-adapters-underground_storage-uh2scundergroundstorage-run"></a>

## 외부 지하 공동·습윤 기체·암반 모델과 수지 검사 / Native cavern/wet-gas/rock model with independent ledgers

Family / navigation ID: `storage.underground`

Import module: `h2physics.adapters.underground_storage`; selected entry: `Uh2scUndergroundStorage.run`.

#### `h2physics.adapters.underground_storage.Uh2scUndergroundStorage`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/underground_storage.py#L606)

Actual whole-native cylindrical cavern + ideal adiabatic well + finite rock.

Rejected native/conservation cases raise with original objects and full audited
evidence. No fallback to a simpler tank or modified rock equation is supplied.

```python
Uh2scUndergroundStorage(evidence: UndergroundEvidence, domain: UndergroundDomain, budgets: UndergroundAuditBudgets, *, native_model_factory=None, property_factory=CoolPropProperties)
```

#### `h2physics.adapters.underground_storage.Uh2scUndergroundStorage.run`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/underground_storage.py#L700)

```python
run(self, inputs, *, solver_options: Mapping)
```

The source has no explicit return annotation; inspect its return statements and the domain manual. No return type is invented by this generator.

### Returned value / 반환값

`UndergroundTrace`

This return contract was reviewed from the implementation; it is not an annotation present in the source signature.

### Related input/return records / 관련 입력·반환 객체

#### `h2physics.adapters.underground_storage.UndergroundTrace`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/underground_storage.py#L227)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `evidence` | `UndergroundEvidence` | `required` |
| `domain` | `UndergroundDomain` | `required` |
| `budgets` | `UndergroundAuditBudgets` | `required` |
| `native_model` | `object` | `required` |
| `native_run_return` | `object` | `required` |
| `native_log_records` | `tuple` | `required` |
| `snapshots` | `tuple[UndergroundSnapshot, ...]` | `required` |
| `boundary_integrals` | `np.ndarray` | `required` |
| `residuals` | `np.ndarray` | `required` |
| `native_source_sha256` | `Mapping` | `required` |
| `original_inputs` | `Mapping` | `required` |
| `input_sha256` | `str` | `required` |
| `native_version_labels` | `tuple[str, str]` | `required` |
| `independent_properties` | `tuple` | `required` |
| `failures` | `tuple[str, ...]` | `required` |
| `numerically_admitted` | `bool` | `required` |
| `software_status` | `str` | `'implemented_unverified'` |
| `integral_method` | `str` | `'native implicit-step right-endpoint flux audit; no continuous-history accuracy claim'` |
| `residual_columns` | `tuple` | `('hydrogen_mass_kg', 'water_mass_kg', 'fluid_internal_energy_j', 'rock_energy_j', 'combined_thermal_energy_j', 'requested_well_mass_kg')` |
| `integral_columns` | `tuple` | `('hydrogen_in_kg', 'water_in_kg', 'enthalpy_in_j', 'heat_into_rock_j', 'heat_outer_out_j', 'heat_farfield_out_j')` |

#### `h2physics.adapters.underground_storage.UndergroundEvidence`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/underground_storage.py#L113)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `clock_id` | `str` | `required` |
| `frame_id` | `str` | `required` |
| `site_id` | `str` | `required` |
| `source_id` | `str` | `required` |
| `start_time_s` | `float` | `required` |
| `geometry_evidence_id` | `str` | `required` |
| `rock_property_evidence_id` | `str` | `required` |
| `farfield_boundary_evidence_id` | `str` | `required` |
| `well_history_evidence_id` | `str` | `required` |
| `pure_water_surrogate_evidence_id` | `str` | `required` |
| `omitted_mechanical_energy_evidence_id` | `str` | `required` |
| `origin` | `Origin` | `required` |

#### `h2physics.adapters.underground_storage.UndergroundDomain`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/underground_storage.py#L150)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `minimum_pressure_pa_absolute` | `float` | `required` |
| `maximum_pressure_pa_absolute` | `float` | `required` |
| `minimum_temperature_k` | `float` | `required` |
| `maximum_temperature_k` | `float` | `required` |
| `maximum_water_vapor_mass_fraction` | `float` | `required` |
| `evidence_id` | `str` | `required` |

#### `h2physics.adapters.underground_storage.UndergroundAuditBudgets`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/underground_storage.py#L180)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `hydrogen_mass_kg` | `float` | `required` |
| `water_mass_kg` | `float` | `required` |
| `thermal_energy_j` | `float` | `required` |
| `relative` | `float` | `required` |
| `eos_relative` | `float` | `required` |
| `final_time_s` | `float` | `required` |

#### `h2physics.adapters.underground_storage.UndergroundSnapshot`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/underground_storage.py#L196)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `native_time_s` | `float` | `required` |
| `time_s` | `float` | `required` |
| `raw_solution` | `object` | `required` |
| `raw_independent_variables` | `object` | `required` |
| `hydrogen_mass_kg` | `float` | `required` |
| `liquid_water_mass_kg` | `float` | `required` |
| `water_vapor_mass_kg` | `float` | `required` |
| `gas_volume_m3` | `float` | `required` |
| `liquid_volume_m3` | `float` | `required` |
| `total_pressure_pa_absolute` | `float` | `required` |
| `dry_hydrogen` | `object` | `required` |
| `liquid_water` | `object` | `required` |
| `water_vapor` | `object` | `required` |
| `wall_temperature_k` | `float` | `required` |
| `rock_temperature_k` | `np.ndarray` | `required` |
| `fluid_internal_energy_j` | `float` | `required` |
| `rock_energy_change_j` | `float` | `required` |
| `hydrogen_rate_into_kg_s` | `float` | `required` |
| `water_rate_into_kg_s` | `float` | `required` |
| `enthalpy_rate_into_w` | `float` | `required` |
| `heat_into_rock_w` | `float` | `required` |
| `heat_out_outer_rock_w` | `float` | `required` |
| `heat_out_farfield_w` | `float` | `required` |
| `eos_relative_defect` | `float` | `required` |


<a id="module-h2physics-storage-porous_reservoir-porousreservoir-run"></a>

## 방사형 등온 단상 다공성 저장소 주입·인출 / Radial isothermal single-phase Darcy storage

Family / navigation ID: `storage.porous_reservoir`

Import module: `h2physics.storage.porous_reservoir`; selected entry: `PorousReservoir.run`.

#### `h2physics.storage.porous_reservoir.PorousReservoir`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/storage/porous_reservoir.py#L241)

One-dimensional fixed-temperature single-gas Darcy reservoir.

Cell temperatures are prescribed and do not evolve. An implicit
backward-Euler mass balance is solved per interval. The well
source may be a prescribed signed mass rate or an inner-face pressure
boundary connected by the same single-phase radial Darcy closure. An
optional sampled outer pressure adds another pressure boundary. No
wellbore, skin, multiphase or site law is inferred.

```python
PorousReservoir(*, geometry: PorousReservoirGeometry, density_kg_m3: Callable[[float, float], float] | None=None, viscosity_pa_s: Callable[[float, float], float] | None=None, property_provider: PropertyProvider | None=None, property_evidence_id: str)
```

#### `h2physics.storage.porous_reservoir.PorousReservoir.run`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/storage/porous_reservoir.py#L314)

Solve the sampled schedule; failed convergence raises ``RuntimeError``.

```python
run(self, schedule: PorousReservoirSchedule, *, outer_pressure_pa=None, outer_temperature_k: float | None=None, well_temperature_k: float | None=None, max_nfev: int=300, xtol: float=1e-10, ftol: float=1e-10, gtol: float=1e-10) -> PorousReservoirResult
```

### Returned value / 반환값

`PorousReservoirResult`

### Related input/return records / 관련 입력·반환 객체

#### `h2physics.storage.porous_reservoir.PorousReservoirGeometry`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/storage/porous_reservoir.py#L52)

Caller-defined concentric-cell geometry and uniform rock properties.

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `radial_faces_m` | `np.ndarray` | `required` |
| `thickness_m` | `float` | `required` |
| `porosity` | `np.ndarray` | `required` |
| `permeability_m2` | `np.ndarray` | `required` |
| `temperature_k` | `np.ndarray` | `required` |
| `evidence_id` | `str` | `required` |

Computed properties: `cell_count`, `pore_volume_m3`, `radial_centers_m`.

#### `h2physics.storage.porous_reservoir.PorousReservoirSchedule`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/storage/porous_reservoir.py#L97)

Sampled pressure boundaries and signed well flow on one declared clock.

Positive well flow injects mass; negative flow withdraws it. Select exactly
one of a prescribed well-flow series or a well-pressure series. Pressure
samples use the same clock and bounds as the reservoir and act at the inner
radial face through the model's single-phase Darcy transmissibility.

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `time_s` | `np.ndarray` | `required` |
| `initial_pressure_pa` | `np.ndarray` | `required` |
| `minimum_pressure_pa` | `float` | `required` |
| `maximum_pressure_pa` | `float` | `required` |
| `well_mass_flow_kg_s` | `np.ndarray &#124; None` | `required` |
| `clock_id` | `str` | `required` |
| `well_pressure_pa` | `np.ndarray &#124; None` | `None` |

#### `h2physics.storage.porous_reservoir.PorousReservoirResult`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/storage/porous_reservoir.py#L151)

Implicit-step pressure and mass ledger for a single-phase radial run.

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `time_s` | `np.ndarray` | `required` |
| `pressure_pa` | `np.ndarray` | `required` |
| `cell_gas_mass_kg` | `np.ndarray` | `required` |
| `cumulative_well_mass_kg` | `np.ndarray` | `required` |
| `cumulative_outer_boundary_mass_kg` | `np.ndarray` | `required` |
| `per_step_mass_residual_kg` | `np.ndarray` | `required` |
| `geometry` | `PorousReservoirGeometry` | `required` |
| `schedule` | `PorousReservoirSchedule` | `required` |
| `property_evidence_id` | `str` | `required` |
| `outer_boundary_temperature_k` | `float` | `required` |
| `well_boundary_temperature_k` | `float` | `required` |


## Maintaining this guide / 갱신

Curated purposes and entry selection live in `scripts/readme_module_guide.py`. Run `python scripts/readme_module_guide.py` to regenerate both README blocks and this file. Run `python scripts/readme_module_guide.py --check` to reject stale output, unresolved callables or missing catalog IDs. The script parses source with the standard library, imports no physical engine and runs no calculation. Review purpose/units/limits against domain manuals when an API changes. It preserves authored scientific attribution and performs no automatic translation of external material.
