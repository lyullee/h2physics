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

- [기체·액체·균질평형 이상 방출을 푸는 공통 EOS 노즐 / One EOS-based nozzle for gas, liquid and homogeneous-equilibrium two-phase discharge](#module-h2physics-release-homogeneousisentropicnozzle-solve)
- [외부 탱크 상태의 노즐 방출 샘플·재고 적분은 외부 소유 / Native bulk-state nozzle outflow sample; inventory integration remains native](#module-h2physics-adapters-lh2dt-lh2dtbulknozzleoutflow-sample)
- [노즐 기체를 대기압 방출 평면으로 팽창 / Nozzle gas expanded to an ambient-pressure source plane](#module-h2physics-adapters-degali-expand_nozzle_gas)
- [포화 구형 액적의 비행·항력·증발 / Saturated spherical parcel flight, drag and evaporation](#module-h2physics-adapters-droplet_transport-saturatedparcelflight-run)
- [유한 액적 충돌·표면 열수지·침착 액체 / Finite liquid impact, surface heat and deposited batches](#module-h2physics-adapters-droplet_impact-finitesurfaceimpact-run)

<a id="module-h2physics-release-homogeneousisentropicnozzle-solve"></a>

## 기체·액체·균질평형 이상 방출을 푸는 공통 EOS 노즐 / One EOS-based nozzle for gas, liquid and homogeneous-equilibrium two-phase discharge

Family / navigation ID: `release.gas`, `release.liquid`, `release.two_phase`

Import module: `h2physics.release`; selected entry: `HomogeneousIsentropicNozzle.solve`.

#### `h2physics.release.HomogeneousIsentropicNozzle`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/release.py#L129)

One EOS path for gas, liquid and equilibrium two-phase inlet states.

Both pressure endpoints participate. Every sampled interior maximum is refined
in log pressure, and a finer grid must reproduce the selected flux and pressure.
Provider errors and nonconvergence are surfaced rather than skipped. This is a
numerical convergence check, not proof of global optimality or physical validity.

```python
HomogeneousIsentropicNozzle(properties: PropertyProvider, *, search: NozzleSearch | None=None)
```

#### `h2physics.release.HomogeneousIsentropicNozzle.solve`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/release.py#L142)

```python
solve(self, upstream_stagnation: ThermoState, *, back_pressure_pa: float, opening: NozzleOpening, opening_fraction: float=1.0) -> NozzleResult
```

### Returned value / 반환값

`NozzleResult`

### Related input/return records / 관련 입력·반환 객체

#### `h2physics.release.NozzleSearch`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/release.py#L58)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `initial_grid_points` | `int` | `33` |
| `maximum_refinements` | `int` | `3` |
| `relative_flux_tolerance` | `float` | `1e-07` |
| `relative_pressure_tolerance` | `float` | `1e-06` |
| `upstream_relative_tolerance` | `float` | `2e-06` |
| `enthalpy_roundoff_j_kg` | `float` | `1e-05` |

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

#### `h2physics.core.PropertyBasis`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/core.py#L97)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `fluid` | `str` | `required` |
| `reference_id` | `str` | `required` |
| `spin_composition` | `str` | `'unspecified'` |

#### `h2physics.release.NozzleDiagnostics`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/release.py#L79)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `property_evaluations` | `int` | `required` |
| `grid_refinements` | `int` | `required` |
| `relative_flux_change` | `float` | `required` |
| `relative_pressure_change` | `float` | `required` |
| `maximum_negative_enthalpy_roundoff_j_kg` | `float` | `required` |
| `maximum_quality_roundoff` | `float` | `0.0` |
| `sonic_refinements` | `int` | `0` |


<a id="module-h2physics-adapters-lh2dt-lh2dtbulknozzleoutflow-sample"></a>

## 외부 탱크 상태의 노즐 방출 샘플·재고 적분은 외부 소유 / Native bulk-state nozzle outflow sample; inventory integration remains native

Family / navigation ID: `release.blowdown`

Import module: `h2physics.adapters.lh2dt`; selected entry: `Lh2dtBulkNozzleOutflow.sample`.

#### `h2physics.adapters.lh2dt.Lh2dtBulkNozzleOutflow`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/lh2dt.py#L77)

Native homogeneous-tank callback; tank equations stay in LH2DT.

This deliberately supports only bulk-mixture withdrawal. The reviewed native
tank overrides every negative flow's enthalpy with its bulk enthalpy. A liquid
dip tube or vapor vent needs the receiving-engine extension in request 001.
Histories are sampled separately, since native RK stages/retries are not
accepted observation times. Split integration at discontinuous commands.

```python
Lh2dtBulkNozzleOutflow(nozzle: HomogeneousIsentropicNozzle, opening: NozzleOpening, *, back_pressure_pa: float | Callable[[float], float], opening_fraction: float | Callable[[float], float], flow_factory: Callable[..., Any])
```

#### `h2physics.adapters.lh2dt.Lh2dtBulkNozzleOutflow.sample`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/lh2dt.py#L97)

```python
sample(self, time_s: float, native_state: Lh2dtState)
```

The source has no explicit return annotation; inspect its return statements and the domain manual. No return type is invented by this generator.

### Returned value / 반환값

`NozzleResult`

This return contract was reviewed from the implementation; it is not an annotation present in the source signature.

### Related input/return records / 관련 입력·반환 객체

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

#### `h2physics.adapters.lh2dt.Lh2dtState`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/lh2dt.py#L15)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `pressure_Pa` | `float` | `required` |
| `temperature_K` | `float` | `required` |
| `density_kg_m3` | `float` | `required` |
| `specific_enthalpy_J_kg` | `float` | `required` |
| `specific_internal_energy_J_kg` | `float` | `required` |
| `specific_entropy_J_kgK` | `float` | `required` |
| `quality` | `float &#124; None` | `required` |
| `phase` | `str` | `required` |

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

#### `h2physics.release.NozzleDiagnostics`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/release.py#L79)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `property_evaluations` | `int` | `required` |
| `grid_refinements` | `int` | `required` |
| `relative_flux_change` | `float` | `required` |
| `relative_pressure_change` | `float` | `required` |
| `maximum_negative_enthalpy_roundoff_j_kg` | `float` | `required` |
| `maximum_quality_roundoff` | `float` | `0.0` |
| `sonic_refinements` | `int` | `0` |


<a id="module-h2physics-adapters-degali-expand_nozzle_gas"></a>

## 노즐 기체를 대기압 방출 평면으로 팽창 / Nozzle gas expanded to an ambient-pressure source plane

Family / navigation ID: `release.near_field`

Import module: `h2physics.adapters.degali`; selected entry: `expand_nozzle_gas`.

#### `h2physics.adapters.degali.expand_nozzle_gas`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/degali.py#L61)

Delegate the supplied throat to an actual native ambient-plane expander.

The selected area closure treats the shared kernel's effective area as both
stream area and pressure-force area. It does not identify a physical vena
contracta or predict the axial position of the receiving virtual plane.

```python
expand_nozzle_gas(nozzle: NozzleResult, properties: PropertyProvider, *, expander: Callable, location: SourceLocation, location_basis_id: str, pressure_area_policy: str) -> ExpandedGasPlane
```

### Returned value / 반환값

`ExpandedGasPlane`

### Related input/return records / 관련 입력·반환 객체

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

#### `h2physics.adapters.degali.ExpandedGasPlane`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/degali.py#L39)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `native` | `Any` | `required` |
| `nozzle` | `NozzleResult` | `required` |
| `state` | `ThermoState` | `required` |
| `location` | `SourceLocation` | `required` |
| `location_basis_id` | `str` | `required` |
| `pressure_area_policy` | `str` | `required` |
| `origin` | `Origin` | `field(default=Origin.PREDICTED, init=False)` |

Computed properties: `mass_flow_kg_s`, `velocity_m_s`, `diameter_m`.

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

#### `h2physics.release.NozzleDiagnostics`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/release.py#L79)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `property_evaluations` | `int` | `required` |
| `grid_refinements` | `int` | `required` |
| `relative_flux_change` | `float` | `required` |
| `relative_pressure_change` | `float` | `required` |
| `maximum_negative_enthalpy_roundoff_j_kg` | `float` | `required` |
| `maximum_quality_roundoff` | `float` | `0.0` |
| `sonic_refinements` | `int` | `0` |


<a id="module-h2physics-adapters-droplet_transport-saturatedparcelflight-run"></a>

## 포화 구형 액적의 비행·항력·증발 / Saturated spherical parcel flight, drag and evaporation

Family / navigation ID: `release.droplets`

Import module: `h2physics.adapters.droplet_transport`; selected entry: `SaturatedParcelFlight.run`.

#### `h2physics.adapters.droplet_transport.SaturatedParcelFlight`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/droplet_transport.py#L364)

One isolated parcel; constant saturation pressure and fixed carrier field.

Isotropic evaporation leaves with parcel velocity. Added mass, buoyancy,
breakup, collisions and gas back-reaction are excluded by the supplied
dilute/high-density-ratio boundary qualification. No air phase model is
inferred from a heat callback. Positive residual mass is always retained.

```python
SaturatedParcelFlight(properties, pressure_pa, boundary: ParcelBoundary, boiling_heat: Callable[[ParcelState], BoilingHeat], *, force_approximation_evidence_id: str)
```

#### `h2physics.adapters.droplet_transport.SaturatedParcelFlight.run`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/droplet_transport.py#L405)

Integrate with SciPy, retaining native trials and original failures.

Absolute tolerances have 17 entries in the order documented with the
state vector below. Trial excursions are rejected, never clipped.
Ground crossing reports incident liquid only, never deposited liquid.

```python
run(self, *, start_s, end_s, position_m, velocity_m_s, mass_kg, residual_mass_floor_kg, maximum_step_s, relative_tolerance, absolute_tolerances, ground_z_m=None)
```

The source has no explicit return annotation; inspect its return statements and the domain manual. No return type is invented by this generator.

### Returned value / 반환값

`ParcelTrace`

This return contract was reviewed from the implementation; it is not an annotation present in the source signature.

### Related input/return records / 관련 입력·반환 객체

#### `h2physics.adapters.droplet_transport.ParcelTrace`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/droplet_transport.py#L243)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `boundary` | `ParcelBoundary` | `required` |
| `native_result` | `object` | `required` |
| `trials` | `tuple` | `required` |
| `states` | `tuple` | `required` |
| `end_reason` | `str` | `required` |
| `evaporated_mass_kg` | `float` | `required` |
| `heat_into_liquid_j` | `float` | `required` |
| `drag_work_j` | `float` | `required` |
| `vapor_total_energy_out_j` | `float` | `required` |
| `vapor_momentum_out_kg_m_s` | `tuple` | `required` |
| `ambient_pressure_work_into_j` | `float` | `required` |
| `mass_residual_kg` | `float` | `required` |
| `total_energy_residual_j` | `float` | `required` |
| `momentum_residual_kg_m_s` | `tuple` | `required` |

#### `h2physics.adapters.droplet_transport.ParcelBoundary`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/droplet_transport.py#L39)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `clock_id` | `str` | `required` |
| `frame_id` | `str` | `required` |
| `evidence_id` | `str` | `required` |
| `carrier_density_kg_m3` | `float` | `required` |
| `carrier_viscosity_pa_s` | `float` | `required` |
| `carrier_velocity_m_s` | `tuple` | `required` |
| `gravity_m_s2` | `tuple` | `required` |
| `maximum_reynolds` | `float` | `required` |
| `maximum_weber` | `float` | `required` |
| `surface_tension_n_m` | `float` | `required` |
| `maximum_laplace_pressure_fraction` | `float` | `required` |

#### `h2physics.adapters.droplet_transport.BoilingHeat`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/droplet_transport.py#L223)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `heat_into_liquid_w` | `float` | `required` |
| `evidence_id` | `str` | `required` |
| `raw_result` | `object` | `None` |

#### `h2physics.adapters.droplet_transport.ParcelState`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/droplet_transport.py#L68)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `time_s` | `float` | `required` |
| `position_m` | `tuple` | `required` |
| `velocity_m_s` | `tuple` | `required` |
| `mass_kg` | `float` | `required` |
| `diameter_m` | `float` | `required` |
| `reynolds` | `float` | `required` |
| `weber` | `float` | `required` |
| `liquid_state` | `object` | `required` |
| `vapor_state` | `object` | `required` |


<a id="module-h2physics-adapters-droplet_impact-finitesurfaceimpact-run"></a>

## 유한 액적 충돌·표면 열수지·침착 액체 / Finite liquid impact, surface heat and deposited batches

Family / navigation ID: `release.impact`

Import module: `h2physics.adapters.droplet_impact`; selected entry: `FiniteSurfaceImpact.run`.

#### `h2physics.adapters.droplet_impact.FiniteSurfaceImpact`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/droplet_impact.py#L439)

Conditional dry-patch impact with finite heat/recoil and a fixed mount.

Contact is a lumped event: passive collision/recoil, inelastic grounding,
then finite-G contact boiling. Coefficients are held over the event; the
vapor mass and mechanical heat are solved together. No impact regime or
empirical LH2 deposition fraction is inferred by this model.

```python
FiniteSurfaceImpact(properties, patch: SurfacePatch, closure: QualifiedImpactClosure, *, tolerances: ImpactTolerances=ImpactTolerances(), intercontact_heat: Callable[[IntercontactThermalContext], IntercontactThermalResult] | None=None)
```

#### `h2physics.adapters.droplet_impact.FiniteSurfaceImpact.run`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/droplet_impact.py#L624)

Sequence on a thermally finite patch with an explicit gap boundary.

The dry-patch clearing boundary sends each deposited batch to a separate
at-rest receiver. It carries liquid energy; it does not erase heat or
pool inventory. A wet-pool impact is outside this model.

```python
run(self, incidents) -> SurfaceImpactTrace
```

### Returned value / 반환값

`SurfaceImpactTrace`

### Related input/return records / 관련 입력·반환 객체

#### `h2physics.adapters.droplet_impact.SurfacePatch`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/droplet_impact.py#L52)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `location` | `SourceLocation` | `required` |
| `initial_time_s` | `float` | `required` |
| `effective_recoil_mass_kg` | `float` | `required` |
| `heat_capacity_j_k` | `float` | `required` |
| `initial_temperature_k` | `float` | `required` |
| `minimum_temperature_k` | `float` | `required` |
| `maximum_temperature_k` | `float` | `required` |
| `radius_m` | `float` | `required` |
| `material_evidence_id` | `str` | `required` |
| `fixed_mount_arrest_evidence_id` | `str` | `required` |
| `dry_patch_clearing_evidence_id` | `str` | `required` |
| `intercontact_thermal_evidence_id` | `str` | `required` |
| `origin` | `Origin` | `required` |
| `material_owner` | `Any` | `required` |

#### `h2physics.adapters.droplet_impact.QualifiedImpactClosure`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/droplet_impact.py#L199)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `qualification` | `ImpactQualification` | `required` |
| `evaluate` | `Callable[[ImpactContext], ImpactOutcome]` | `required` |
| `owner` | `Any` | `required` |

#### `h2physics.adapters.droplet_impact.ImpactTolerances`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/droplet_impact.py#L211)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `mass_kg` | `float` | `1e-12` |
| `energy_j` | `float` | `1e-08` |
| `momentum_kg_m_s` | `float` | `1e-11` |
| `position_m` | `float` | `1e-08` |
| `clock_s` | `float` | `1e-09` |
| `property_relative` | `float` | `1e-08` |
| `root_mass_kg` | `float` | `1e-15` |

#### `h2physics.adapters.droplet_impact.IntercontactThermalContext`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/droplet_impact.py#L159)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `patch` | `SurfacePatch` | `required` |
| `start_time_s` | `float` | `required` |
| `end_time_s` | `float` | `required` |
| `initial_temperature_k` | `float` | `required` |
| `heat_capacity_j_k` | `float` | `required` |

#### `h2physics.adapters.droplet_impact.IntercontactThermalResult`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/droplet_impact.py#L168)

Integrated external heat over a gap; the caller owns its trajectory.

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `start_time_s` | `float` | `required` |
| `end_time_s` | `float` | `required` |
| `heat_into_patch_j` | `float` | `required` |
| `minimum_temperature_k` | `float` | `required` |
| `maximum_temperature_k` | `float` | `required` |
| `evidence_id` | `str` | `required` |
| `origin` | `Origin` | `required` |
| `raw_result` | `Any` | `None` |

#### `h2physics.adapters.droplet_impact.SurfaceImpactTrace`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/droplet_impact.py#L279)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `patch` | `SurfacePatch` | `required` |
| `closure` | `QualifiedImpactClosure` | `required` |
| `native_property_owner` | `Any` | `required` |
| `steps` | `tuple[ImpactStep, ...]` | `required` |
| `final_wall_temperature_k` | `float` | `required` |
| `total_incident_mass_kg` | `float` | `required` |
| `deposited_mass_kg` | `float` | `required` |
| `rebound_mass_kg` | `float` | `required` |
| `vapor_mass_kg` | `float` | `required` |
| `mass_residual_kg` | `float` | `required` |
| `total_energy_residual_j` | `float` | `required` |
| `regime_prediction_solved` | `bool` | `False` |
| `surface_spreading_solved` | `bool` | `False` |
| `simultaneous_pool_continuation_solved` | `bool` | `False` |
| `measured_hydrogen_validation` | `bool` | `False` |
| `status` | `str` | `STATUS` |

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

#### `h2physics.adapters.droplet_impact.ImpactQualification`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/droplet_impact.py#L85)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `evidence_id` | `str` | `required` |
| `origin` | `Origin` | `required` |
| `pressure_bounds_pa` | `tuple[float, float]` | `required` |
| `wall_temperature_bounds_k` | `tuple[float, float]` | `required` |
| `diameter_bounds_m` | `tuple[float, float]` | `required` |
| `normal_speed_bounds_m_s` | `tuple[float, float]` | `required` |
| `impact_weber_bounds` | `tuple[float, float]` | `required` |
| `lumped_capacity_evidence_id` | `str` | `required` |
| `negligible_external_work_evidence_id` | `str` | `required` |
| `phase_equilibrium_evidence_id` | `str` | `required` |

#### `h2physics.adapters.droplet_impact.ImpactContext`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/droplet_impact.py#L148)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `incident_trace` | `ParcelTrace` | `required` |
| `incident` | `ParcelState` | `required` |
| `patch` | `SurfacePatch` | `required` |
| `wall_temperature_k` | `float` | `required` |
| `liquid_state` | `ThermoState` | `required` |
| `vapor_state` | `ThermoState` | `required` |
| `impact_weber` | `float` | `required` |

#### `h2physics.adapters.droplet_impact.ImpactOutcome`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/droplet_impact.py#L111)

Evidence-qualified frozen coefficients, not an inferred impact regime.

Deposition fraction concerns only liquid remaining after solved evaporation.
Vapor velocity is relative to the intermediate recoiling patch. Interfacial
energy is an explicit signed internal-energy change, not a contact-angle fit.

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `deposited_fraction_of_remaining_liquid` | `float` | `required` |
| `normal_restitution` | `float` | `required` |
| `tangential_retention` | `float` | `required` |
| `vapor_velocity_relative_to_recoil_m_s` | `tuple[float, float, float]` | `required` |
| `contact_conductance_w_k` | `float` | `required` |
| `contact_duration_s` | `float` | `required` |
| `interfacial_internal_energy_change_j` | `float` | `required` |
| `evidence_id` | `str` | `required` |
| `origin` | `Origin` | `required` |
| `raw_result` | `Any` | `required` |

#### `h2physics.adapters.droplet_impact.ImpactStep`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/droplet_impact.py#L257)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `context` | `ImpactContext` | `required` |
| `outcome` | `ImpactOutcome` | `required` |
| `mechanical` | `MechanicalTrial` | `required` |
| `intercontact_thermal` | `IntercontactThermalResult` | `required` |
| `contact_end_s` | `float` | `required` |
| `active_boiling_duration_s` | `float` | `required` |
| `dryout` | `bool` | `required` |
| `wall_final_temperature_k` | `float` | `required` |
| `wall_internal_energy_change_j` | `float` | `required` |
| `latent_heat_j` | `float` | `required` |
| `fluid_internal_energy_change_j` | `float` | `required` |
| `ambient_pressure_work_into_j` | `float` | `required` |
| `interfacial_internal_energy_change_j` | `float` | `required` |
| `total_energy_residual_j` | `float` | `required` |
| `mass_residual_kg` | `float` | `required` |
| `native_root_result` | `Any` | `required` |
| `trials` | `tuple[MechanicalTrial, ...]` | `required` |
| `deposited_batch` | `DepositedBatch` | `required` |


## Maintaining this guide / 갱신

Curated purposes and entry selection live in `scripts/readme_module_guide.py`. Run `python scripts/readme_module_guide.py` to regenerate both README blocks and this file. Run `python scripts/readme_module_guide.py --check` to reject stale output, unresolved callables or missing catalog IDs. The script parses source with the standard library, imports no physical engine and runs no calculation. Review purpose/units/limits against domain manuals when an API changes. It preserves authored scientific attribution and performs no automatic translation of external material.
