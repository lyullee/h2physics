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

- [수소 퓨가시티에 따른 명시 운반체 기준 용해 농도 / Declared-carrier concentration from hydrogen fugacity](#module-h2physics-materials-transport-powerlawsolubility-concentration_mol_m3)
- [용해도·확산계수를 이용한 정상 벽 투과량 / Steady wall permeation from solubility and diffusivity](#module-h2physics-materials-transport-steady_permeation)
- [이동·포획 수소의 보존형 유한체적 확산 / Conservative mobile/trapped hydrogen transport](#module-h2physics-materials-finite_volume-diffusiondomain-simulate)
- [외부 수소 영향 피로 균열 성장식 적분 / Native hydrogen-assisted fatigue crack-growth law integration](#module-h2physics-adapters-fracture_fatigue-integrate_fatigue_crack)
- [두꺼운 원통의 탄성 압력 응력장 / Elastic thick-cylinder pressure stress](#module-h2physics-materials-elastic_cylinder-lame_stress_field)
- [원통 고체 벽의 방사형 열전도 이력 / Radial solid-wall thermal history](#module-h2physics-materials-radial_heat-radial_cylinder_heat_history)
- [방사형 온도 구배에 따른 탄성 응력 / Radial thermal-gradient elastic stress](#module-h2physics-materials-radial_thermoelastic-radial_thermoelastic_cylinder)

<a id="module-h2physics-materials-transport-powerlawsolubility-concentration_mol_m3"></a>

## 수소 퓨가시티에 따른 명시 운반체 기준 용해 농도 / Declared-carrier concentration from hydrogen fugacity

Family / navigation ID: `materials.solubility`

Import module: `h2physics.materials.transport`; selected entry: `PowerLawSolubility.concentration_mol_m3`.

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

#### `h2physics.materials.transport.PowerLawSolubility.concentration_mol_m3`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/materials/transport.py#L81)

```python
concentration_mol_m3(self, hydrogen_fugacity_pa: float, temperature_k: float)
```

The source has no explicit return annotation; inspect its return statements and the domain manual. No return type is invented by this generator.

### Returned value / 반환값

`float`

This return contract was reviewed from the implementation; it is not an annotation present in the source signature.

### Related input/return records / 관련 입력·반환 객체

#### `h2physics.materials.transport.HydrogenCarrier`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/materials/transport.py#L51)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `identity` | `Literal['atomic_hydrogen', 'molecular_hydrogen']` | `required` |
| `molar_mass_kg_mol` | `float` | `required` |

Computed properties: `hydrogen_atoms_per_entity`.


<a id="module-h2physics-materials-transport-steady_permeation"></a>

## 용해도·확산계수를 이용한 정상 벽 투과량 / Steady wall permeation from solubility and diffusivity

Family / navigation ID: `materials.permeation`

Import module: `h2physics.materials.transport`; selected entry: `steady_permeation`.

#### `h2physics.materials.transport.steady_permeation`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/materials/transport.py#L186)

Signed bulk-limited flux across a homogeneous, isothermal planar membrane.

```python
steady_permeation(solubility: PowerLawSolubility, *, diffusivity_m2_s: float, thickness_m: float, upstream_fugacity_pa: float, downstream_fugacity_pa: float, temperature_k: float) -> PermeationResult
```

### Returned value / 반환값

`PermeationResult`

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

#### `h2physics.materials.transport.PermeationResult`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/materials/transport.py#L95)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `carrier` | `HydrogenCarrier` | `required` |
| `mobile_entity_flux_mol_m2_s` | `float` | `required` |
| `hydrogen_mass_flux_kg_m2_s` | `float` | `required` |
| `h2_equivalent_flux_mol_m2_s` | `float` | `required` |

#### `h2physics.materials.transport.HydrogenCarrier`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/materials/transport.py#L51)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `identity` | `Literal['atomic_hydrogen', 'molecular_hydrogen']` | `required` |
| `molar_mass_kg_mol` | `float` | `required` |

Computed properties: `hydrogen_atoms_per_entity`.


<a id="module-h2physics-materials-finite_volume-diffusiondomain-simulate"></a>

## 이동·포획 수소의 보존형 유한체적 확산 / Conservative mobile/trapped hydrogen transport

Family / navigation ID: `materials.diffusion`

Import module: `h2physics.materials.finite_volume`; selected entry: `DiffusionDomain.simulate`.

#### `h2physics.materials.finite_volume.DiffusionDomain`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/materials/finite_volume.py#L374)

Shared BDF finite-volume integration, including optional finite faces.

```python
DiffusionDomain(carrier: HydrogenCarrier, mesh: DiffusionMesh, diffusivity_m2_s: Callable[[float], float], *, traps: tuple[TrapPopulation, ...]=())
```

#### `h2physics.materials.finite_volume.DiffusionDomain.simulate`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/materials/finite_volume.py#L383)

```python
simulate(self, time_s, initial_mobile_mol_m3, *, boundary: Callable[[float], TransportBoundary] | PowerLawSolubilityBoundary, temperature_k: Callable[[float], float], initial_trapped_mol_m3=None, left_inventory: FiniteSurfaceInventory | None=None, right_inventory: FiniteSurfaceInventory | None=None, stress_potential: HydrostaticStressPotential | None=None, relative_tolerance: float=1e-08, absolute_tolerance_mol_m3: float=1e-10, maximum_step_s: float=np.inf) -> TransportResult
```

### Returned value / 반환값

`TransportResult`

### Related input/return records / 관련 입력·반환 객체

#### `h2physics.materials.transport.HydrogenCarrier`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/materials/transport.py#L51)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `identity` | `Literal['atomic_hydrogen', 'molecular_hydrogen']` | `required` |
| `molar_mass_kg_mol` | `float` | `required` |

Computed properties: `hydrogen_atoms_per_entity`.

#### `h2physics.materials.finite_volume.DiffusionMesh`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/materials/finite_volume.py#L107)

Positive-area one-dimensional control volumes with oriented faces.

``conductance_m`` multiplies D times a concentration difference to give
mol/s. Its first/last entries connect a surface to the adjacent center;
interior entries connect centers. No solid sphere origin is supported.

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `face_positions_m` | `np.ndarray` | `required` |
| `cell_centers_m` | `np.ndarray` | `required` |
| `face_areas_m2` | `np.ndarray` | `required` |
| `cell_volumes_m3` | `np.ndarray` | `required` |
| `conductance_m` | `np.ndarray` | `required` |
| `geometry` | `str` | `required` |

#### `h2physics.materials.transport.TrapPopulation`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/materials/transport.py#L565)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `site_concentration_mol_m3` | `float` | `required` |
| `capture_m3_mol_s` | `Callable[[float], float]` | `required` |
| `release_s_inv` | `Callable[[float], float]` | `required` |

#### `h2physics.materials.transport.PowerLawSolubilityBoundary`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/materials/transport.py#L452)

Equilibrium concentration boundary driven by caller fugacity histories.

The finite-volume solver supplies the same time and spatially uniform
temperature used by its diffusivity model. This object applies only the
declared ``PowerLawSolubility`` relation; it adds no surface kinetics.

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `solubility` | `PowerLawSolubility` | `required` |
| `upstream_hydrogen_fugacity_pa` | `float &#124; Callable[[float], float]` | `required` |
| `downstream_hydrogen_fugacity_pa` | `float &#124; Callable[[float], float]` | `required` |
| `evidence_id` | `str` | `required` |

#### `h2physics.materials.finite_volume.TransportBoundary`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/materials/finite_volume.py#L256)

Use None at a face owned by a finite surface inventory.

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `left` | `SurfaceCondition &#124; SurfaceFilmCondition &#124; None` | `required` |
| `right` | `SurfaceCondition &#124; SurfaceFilmCondition &#124; None` | `required` |

#### `h2physics.materials.finite_volume.FiniteSurfaceInventory`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/materials/finite_volume.py#L264)

An amount in mol(mobile entity), exchanging only through its own face.

The callback receives time in seconds and the current amount in moles.
It may prescribe concentration or signed coordinate flux. A positive
floor guards property callbacks; crossing it rejects the integration
window, without clipping mass or claiming a localized depletion event.

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `initial_mol` | `float` | `required` |
| `minimum_mol` | `float` | `required` |
| `condition` | `Callable[[float, float], SurfaceCondition]` | `required` |
| `evidence` | `str` | `required` |

#### `h2physics.materials.stress_transport.HydrostaticStressPotential`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/materials/stress_transport.py#L21)

One-way prescribed stress, with ``mu_stress = -V_H * sigma_h``.

``hydrostatic_stress_pa(time_s, positions_m)`` returns one stress per
requested material coordinate. It receives immutable coordinate storage.
Time has the same seconds and origin as the diffusion solve; ``clock_id``
records that caller-declared correspondence. No stress/diffusion feedback,
temperature gradient, plasticity or stress-dependent trap law is inferred.

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `carrier` | `HydrogenCarrier` | `required` |
| `hydrostatic_stress_pa` | `Callable` | `required` |
| `partial_molar_volume_m3_mol` | `float` | `required` |
| `temperature_domain_k` | `tuple[float, float]` | `required` |
| `stress_field_id` | `str` | `required` |
| `partial_molar_volume_evidence_id` | `str` | `required` |
| `clock_id` | `str` | `required` |
| `origin` | `Origin` | `required` |

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

#### `h2physics.materials.transport.SurfaceCondition`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/materials/transport.py#L390)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `kind` | `Literal['concentration', 'flux']` | `required` |
| `value` | `float` | `required` |

#### `h2physics.materials.transport.SurfaceFilmCondition`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/materials/transport.py#L403)

Linear surface-transfer resistance against a declared solid-basis concentration.

``bulk_concentration_mol_m3`` is the mobile-entity concentration that would
be in equilibrium with the adjacent external phase, already mapped onto
the same carrier and concentration basis as the solid. The coefficient has
units m/s. Neither quantity is inferred from gas pressure or fugacity.
Callbacks receive ``(time_s, temperature_k)``.

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `bulk_concentration_mol_m3` | `float &#124; Callable[[float, float], float]` | `required` |
| `transfer_velocity_m_s` | `float &#124; Callable[[float, float], float]` | `required` |
| `evidence_id` | `str` | `required` |


<a id="module-h2physics-adapters-fracture_fatigue-integrate_fatigue_crack"></a>

## 외부 수소 영향 피로 균열 성장식 적분 / Native hydrogen-assisted fatigue crack-growth law integration

Family / navigation ID: `materials.integrity`

Import module: `h2physics.adapters.fracture_fatigue`; selected entry: `integrate_fatigue_crack`.

#### `h2physics.adapters.fracture_fatigue.integrate_fatigue_crack`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/fracture_fatigue.py#L723)

Finite supplied cycle sequence; no rainflow, initiation or transport inference.

Every block is constant amplitude and constant gas environment. Frequency is
recorded/admitted from its explicit two clocks, not used to invent a rate or
dwell correction. A later block can restart a threshold-arrested crack unless
stop_at_arrest was explicitly selected. Strict out-of-domain native trials
fail; user-declared bounded numerical extensions are retained as such.

```python
integrate_fatigue_crack(law: HelprFatigueLaw, history: LoadCycleHistory, geometry: CrackGeometryCallback, material: FractureMaterialDomain, conditions: CrackStopConditions, *, initial_crack_m: float, settings=FractureIntegrationSettings()) -> FractureGrowthResult
```

### Returned value / 반환값

`FractureGrowthResult`

### Related input/return records / 관련 입력·반환 객체

#### `h2physics.adapters.fracture_fatigue.LoadCycleHistory`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/fracture_fatigue.py#L221)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `blocks` | `tuple[LoadCycleBlock, ...]` | `required` |
| `cycle_clock_id` | `str` | `required` |
| `physical_clock_id` | `str` | `required` |
| `stress_basis_id` | `str` | `required` |
| `ordering_evidence_id` | `str` | `required` |
| `source_id` | `str` | `required` |
| `origin` | `Origin` | `required` |

#### `h2physics.adapters.fracture_fatigue.CrackGeometryCallback`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/fracture_fatigue.py#L273)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `geometry_id` | `str` | `required` |
| `stress_intensity` | `Callable[[float, LoadCycleBlock], ModeIStressIntensity]` | `required` |
| `minimum_crack_m` | `float` | `required` |
| `maximum_physical_crack_m` | `float` | `required` |
| `maximum_trial_crack_m` | `float` | `required` |
| `geometry_evidence_id` | `str` | `required` |
| `trial_extension_evidence_id` | `str` | `required` |

#### `h2physics.adapters.fracture_fatigue.FractureMaterialDomain`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/fracture_fatigue.py#L114)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `pressure_pa` | `tuple[float, float]` | `required` |
| `temperature_k` | `tuple[float, float]` | `required` |
| `fugacity_pa` | `tuple[float, float]` | `required` |
| `stress_intensity_ratio` | `tuple[float, float]` | `required` |
| `frequency_hz` | `tuple[float, float]` | `required` |
| `growth_delta_k_pa_sqrt_m` | `tuple[float, float]` | `required` |
| `maximum_trial_delta_k_pa_sqrt_m` | `float` | `required` |
| `material_id` | `str` | `required` |
| `curve_id` | `str` | `required` |
| `environment_qualification_id` | `str` | `required` |
| `small_scale_yielding_evidence_id` | `str` | `required` |
| `numerical_extension_evidence_id` | `str` | `required` |
| `origin` | `Origin` | `required` |

#### `h2physics.adapters.fracture_fatigue.CrackStopConditions`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/fracture_fatigue.py#L313)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `maximum_crack_m` | `float` | `required` |
| `critical_k_max_pa_sqrt_m` | `float` | `required` |
| `arrest_delta_k_pa_sqrt_m` | `float` | `required` |
| `fracture_evidence_id` | `str` | `required` |
| `arrest_evidence_id` | `str` | `required` |
| `stop_at_arrest` | `bool` | `required` |

#### `h2physics.adapters.fracture_fatigue.FractureGrowthResult`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/fracture_fatigue.py#L616)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `history` | `LoadCycleHistory` | `required` |
| `geometry` | `CrackGeometryCallback` | `required` |
| `material_domain` | `FractureMaterialDomain` | `required` |
| `conditions` | `CrackStopConditions` | `required` |
| `settings` | `FractureIntegrationSettings` | `required` |
| `selection` | `HelprLawSelection` | `required` |
| `snapshots` | `tuple[FractureSnapshot, ...]` | `required` |
| `native_owners` | `tuple[NativeHelprObjects, ...]` | `required` |
| `native_solutions` | `tuple` | `required` |
| `native_calls` | `tuple[NativeGrowthCall, ...]` | `required` |
| `termination` | `str` | `required` |
| `source_sha256` | `Mapping` | `required` |
| `input_sha256` | `str` | `required` |
| `software_status` | `str` | `'implemented_unverified'` |
| `trajectory_owner` | `str` | `'SciPy solve_ivp with native HELPR constitutive calls'` |

#### `h2physics.adapters.fracture_fatigue.LoadCycleBlock`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/fracture_fatigue.py#L180)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `block_id` | `str` | `required` |
| `start_cycle` | `float` | `required` |
| `end_cycle` | `float` | `required` |
| `start_time_s` | `float` | `required` |
| `end_time_s` | `float` | `required` |
| `minimum_stress_pa` | `float` | `required` |
| `maximum_stress_pa` | `float` | `required` |
| `environment` | `HydrogenCrackEnvironment` | `required` |

Computed properties: `frequency_hz`.

#### `h2physics.adapters.fracture_fatigue.ModeIStressIntensity`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/fracture_fatigue.py#L251)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `minimum_pa_sqrt_m` | `float` | `required` |
| `maximum_pa_sqrt_m` | `float` | `required` |

Computed properties: `range_pa_sqrt_m`, `ratio`.

#### `h2physics.adapters.fracture_fatigue.FractureIntegrationSettings`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/fracture_fatigue.py#L518)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `method` | `str` | `'DOP853'` |
| `relative_tolerance` | `float` | `1e-08` |
| `absolute_tolerance_m` | `float` | `1e-11` |
| `maximum_cycle_step` | `float` | `50.0` |
| `maximum_native_calls` | `int` | `100000` |
| `event_size_admission_m` | `float` | `1e-09` |
| `event_k_admission_pa_sqrt_m` | `float` | `1.0` |

#### `h2physics.adapters.fracture_fatigue.HelprLawSelection`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/fracture_fatigue.py#L332)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `model_name` | `str` | `required` |
| `model_evidence_id` | `str` | `required` |
| `paris_coefficient_si` | `float &#124; None` | `None` |
| `paris_exponent` | `float &#124; None` | `None` |
| `reference_pressure_pa` | `float &#124; None` | `None` |
| `fugacity_compatibility_relative_budget` | `float` | `1e-10` |

#### `h2physics.adapters.fracture_fatigue.FractureSnapshot`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/fracture_fatigue.py#L563)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `block_id` | `str` | `required` |
| `cycle` | `float` | `required` |
| `physical_time_s` | `float` | `required` |
| `crack_size_m` | `float` | `required` |
| `stress_intensity` | `ModeIStressIntensity` | `required` |
| `growth_rate_m_per_cycle` | `float` | `required` |
| `native_call` | `NativeGrowthCall &#124; None` | `required` |
| `reason` | `str` | `required` |

#### `h2physics.adapters.fracture_fatigue.NativeHelprObjects`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/fracture_fatigue.py#L366)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `growth` | `object` | `required` |
| `environment` | `object &#124; None` | `required` |
| `arguments` | `Mapping` | `required` |
| `definition_sha256` | `str` | `required` |

#### `h2physics.adapters.fracture_fatigue.NativeGrowthCall`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/fracture_fatigue.py#L547)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `block_id` | `str` | `required` |
| `cycle` | `float` | `required` |
| `crack_size_m` | `float` | `required` |
| `stress_intensity` | `ModeIStressIntensity` | `required` |
| `native_owner` | `NativeHelprObjects` | `required` |
| `native_delta_k_mpa_sqrt_m` | `float` | `required` |
| `native_r_ratio` | `float` | `required` |
| `native_delta_n` | `float` | `required` |
| `raw_result` | `object` | `required` |
| `rate_m_per_cycle` | `float &#124; None` | `required` |
| `purpose` | `str` | `required` |
| `numerical_extension` | `bool` | `required` |


<a id="module-h2physics-materials-elastic_cylinder-lame_stress_field"></a>

## 두꺼운 원통의 탄성 압력 응력장 / Elastic thick-cylinder pressure stress

Family / navigation ID: `materials.integrity`

Import module: `h2physics.materials.elastic_cylinder`; selected entry: `lame_stress_field`.

#### `h2physics.materials.elastic_cylinder.lame_stress_field`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/materials/elastic_cylinder.py#L271)

Evaluate the elastic Lamé field through a long, uniform cylinder wall.

For radii ``ri <= r <= ro``, the radial and hoop stresses are
``A - B/r**2`` and ``A + B/r**2`` respectively, where
``A=(Pi*ri**2-Po*ro**2)/(ro**2-ri**2)`` and
``B=(Pi-Po)*ri**2*ro**2/(ro**2-ri**2)``. Closed ends use axial stress A;
open ends use zero axial pressure stress. All inputs and outputs use metres
and absolute Pa. The caller remains responsible for any reference/stress
transformations, loads beyond uniform pressure, and applicability evidence.

```python
lame_stress_field(geometry: CylinderGeometry, load: CylinderPressureLoad, radius_m: float | np.ndarray, *, evidence_id: str) -> CylinderStressField
```

### Returned value / 반환값

`CylinderStressField`

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

#### `h2physics.materials.elastic_cylinder.CylinderStressField`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/materials/elastic_cylinder.py#L59)

Returned Cauchy stress components; positive values denote tension.

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `radius_m` | `np.ndarray` | `required` |
| `radial_stress_pa` | `np.ndarray` | `required` |
| `hoop_stress_pa` | `np.ndarray` | `required` |
| `axial_stress_pa` | `np.ndarray` | `required` |
| `von_mises_stress_pa` | `np.ndarray` | `required` |
| `geometry` | `CylinderGeometry` | `required` |
| `load` | `CylinderPressureLoad` | `required` |
| `evidence_id` | `str` | `required` |


<a id="module-h2physics-materials-radial_heat-radial_cylinder_heat_history"></a>

## 원통 고체 벽의 방사형 열전도 이력 / Radial solid-wall thermal history

Family / navigation ID: `materials.integrity`

Import module: `h2physics.materials.radial_heat`; selected entry: `radial_cylinder_heat_history`.

#### `h2physics.materials.radial_heat.radial_cylinder_heat_history`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/materials/radial_heat.py#L626)

Integrate a finite cylindrical wall using conservative radial volumes.

Internal heat rates use the exact cylindrical conduction resistance between
radial nodes. Boundary ledgers are integrated as solver states, so the
reported stored-energy residual compares the wall's temperature-dependent
enthalpy change against both cumulative face heat inputs.

```python
radial_cylinder_heat_history(inner_radius_m: float, outer_radius_m: float, length_m: float, material: RadialSolidMaterial, initial_temperature_k, time_s, inner_boundary: RadialThermalBoundary, outer_boundary: RadialThermalBoundary, *, cells: int=40, reference_temperature_k: float | None=None, relative_tolerance: float=1e-07, absolute_tolerance_k: float=1e-07, maximum_step_s: float=np.inf, history_id: str, clock_id: str, evidence_id: str) -> RadialHeatResult
```

### Returned value / 반환값

`RadialHeatResult`

### Related input/return records / 관련 입력·반환 객체

#### `h2physics.materials.radial_heat.RadialSolidMaterial`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/materials/radial_heat.py#L214)

Homogeneous solid properties; callbacks return SI units at kelvin.

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `density_kg_m3` | `float` | `required` |
| `heat_capacity_j_kg_k` | `Callable[[float], float]` | `required` |
| `conductivity_w_m_k` | `Callable[[float], float]` | `required` |
| `material_id` | `str` | `required` |
| `evidence_id` | `str` | `required` |

#### `h2physics.materials.radial_heat.RadialThermalBoundary`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/materials/radial_heat.py#L240)

One wall-face boundary; positive heat flux is directed into the solid.

``kind`` is ``adiabatic``, ``temperature``, ``heat_flux``, ``convection``
or ``radiation``.
A temperature boundary value is face temperature in K; heat flux is W/m2;
convection value is fluid temperature in K and ``coefficient`` is W/m2/K.
Scalar values or time-only callbacks may be supplied. For convection, the
half-cell solid resistance and film resistance are placed in series. A
radiation boundary uses an effective irradiation temperature in ``value``
and an emissivity-view-factor product in ``coefficient``.

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `kind` | `str` | `required` |
| `value` | `float &#124; Callable[[float], float]` | `required` |
| `evidence_id` | `str` | `required` |
| `coefficient` | `float &#124; Callable[[float], float] &#124; None` | `None` |

#### `h2physics.materials.radial_heat.RadialHeatResult`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/materials/radial_heat.py#L287)

Cell-centered temperatures and an explicit global thermal ledger.

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `time_s` | `np.ndarray` | `required` |
| `radius_m` | `np.ndarray` | `required` |
| `temperature_k` | `np.ndarray` | `required` |
| `inner_heat_into_solid_j` | `np.ndarray` | `required` |
| `outer_heat_into_solid_j` | `np.ndarray` | `required` |
| `stored_energy_j` | `np.ndarray` | `required` |
| `energy_residual_j` | `np.ndarray` | `required` |
| `inner_surface_temperature_k` | `np.ndarray` | `required` |
| `outer_surface_temperature_k` | `np.ndarray` | `required` |
| `inner_radius_m` | `float` | `required` |
| `outer_radius_m` | `float` | `required` |
| `cylinder_length_m` | `float` | `required` |
| `material` | `RadialSolidMaterial` | `required` |
| `inner_boundary` | `RadialThermalBoundary` | `required` |
| `outer_boundary` | `RadialThermalBoundary` | `required` |
| `reference_temperature_k` | `float` | `required` |
| `native_solution` | `object` | `required` |
| `history_id` | `str` | `required` |
| `clock_id` | `str` | `required` |
| `evidence_id` | `str` | `required` |


<a id="module-h2physics-materials-radial_thermoelastic-radial_thermoelastic_cylinder"></a>

## 방사형 온도 구배에 따른 탄성 응력 / Radial thermal-gradient elastic stress

Family / navigation ID: `materials.integrity`

Import module: `h2physics.materials.radial_thermoelastic`; selected entry: `radial_thermoelastic_cylinder`.

#### `h2physics.materials.radial_thermoelastic.radial_thermoelastic_cylinder`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/materials/radial_thermoelastic.py#L1165)

Solve the original pressure-plus-temperature long-cylinder problem.

```python
radial_thermoelastic_cylinder(geometry: CylinderGeometry, load: CylinderPressureLoad, temperature: RadialTemperatureProfile, material: IsotropicThermoelasticMaterial, radius_m: float | np.ndarray, *, axial_restraint: str, evidence_id: str, tolerance: float=1e-07, max_nodes: int=10000) -> RadialThermoelasticStressField
```

### Returned value / 반환값

`RadialThermoelasticStressField`

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

#### `h2physics.materials.radial_thermoelastic.RadialTemperatureProfile`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/materials/radial_thermoelastic.py#L78)

Absolute temperatures sampled from the inner to outer cylinder surface.

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `radius_m` | `np.ndarray` | `required` |
| `temperature_k` | `np.ndarray` | `required` |
| `reference_temperature_k` | `float` | `required` |
| `profile_id` | `str` | `required` |
| `evidence_id` | `str` | `required` |

#### `h2physics.materials.elastic_cylinder.IsotropicThermoelasticMaterial`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/materials/elastic_cylinder.py#L166)

Caller-supplied constant isotropic elastic and thermal properties.

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `young_modulus_pa` | `float` | `required` |
| `poisson_ratio` | `float` | `required` |
| `linear_expansion_per_k` | `float` | `required` |
| `material_id` | `str` | `required` |
| `property_evidence_id` | `str` | `required` |

#### `h2physics.materials.radial_thermoelastic.RadialThermoelasticStressField`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/materials/radial_thermoelastic.py#L381)

Pressure and radial-temperature stresses at requested wall radii.

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `radius_m` | `np.ndarray` | `required` |
| `radial_stress_pa` | `np.ndarray` | `required` |
| `hoop_stress_pa` | `np.ndarray` | `required` |
| `axial_stress_pa` | `np.ndarray` | `required` |
| `von_mises_stress_pa` | `np.ndarray` | `required` |
| `axial_strain` | `float` | `required` |
| `axial_support_reaction_n` | `float` | `required` |
| `max_bvp_rms_residual` | `float` | `required` |
| `max_normalized_boundary_residual` | `float` | `required` |
| `bvp_iterations` | `int` | `required` |
| `geometry` | `CylinderGeometry` | `required` |
| `load` | `CylinderPressureLoad` | `required` |
| `material` | `IsotropicThermoelasticMaterial` | `required` |
| `temperature` | `RadialTemperatureProfile` | `required` |
| `axial_restraint` | `str` | `required` |
| `evidence_id` | `str` | `required` |


## Maintaining this guide / 갱신

Curated purposes and entry selection live in `scripts/readme_module_guide.py`. Run `python scripts/readme_module_guide.py` to regenerate both README blocks and this file. Run `python scripts/readme_module_guide.py --check` to reject stale output, unresolved callables or missing catalog IDs. The script parses source with the standard library, imports no physical engine and runs no calculation. Review purpose/units/limits against domain manuals when an API changes. It preserves authored scientific attribution and performs no automatic translation of external material.
