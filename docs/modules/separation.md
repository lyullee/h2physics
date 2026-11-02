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

- [외부 PSA 운전 주기·재고·제품 순도·회수량 / Native scheduled PSA cycle inventories and product accounting](#module-h2physics-adapters-psa_cycle-psadynacycle-run)
- [다성분 다공성 막 투과 유속 / Multicomponent porous-membrane transport](#module-h2physics-adapters-cantera_membrane-canteradustygastransport-flux)

<a id="module-h2physics-adapters-psa_cycle-psadynacycle-run"></a>

## 외부 PSA 운전 주기·재고·제품 순도·회수량 / Native scheduled PSA cycle inventories and product accounting

Family / navigation ID: `separation.psa`

Import module: `h2physics.adapters.psa_cycle`; selected entry: `PsaDynaCycle.run`.

#### `h2physics.adapters.psa_cycle.PsaDynaCycle`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/psa_cycle.py#L218)

Native scheduled multibed run; native original solver objects are not exposed.

A separate actual Network performs admission/snapshot/inventory audits and
is labeled audit_network. The runner's internal Network/OdeResult cannot be
retained through the pinned API. Returned checkpoint arrays are the actual
native serialized states, never surrogate trajectories.

```python
PsaDynaCycle(native: PsaCycleNative, case: Mapping, *, basis: AdsorptionBasis, domain: AdsorptionDomain, evidence: PsaCycleEvidence, temporary_workspace: str | Path)
```

#### `h2physics.adapters.psa_cycle.PsaDynaCycle.run`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/psa_cycle.py#L322)

```python
run(self, *, start_time_s: float, clock_id: str) -> PsaCycleRun
```

### Returned value / 반환값

`PsaCycleRun`

### Related input/return records / 관련 입력·반환 객체

#### `h2physics.adapters.psa_cycle.PsaCycleNative`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/psa_cycle.py#L67)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `core` | `Any` | `required` |
| `schedules` | `Any` | `required` |
| `runner` | `Any` | `required` |
| `source_id` | `str` | `required` |

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

#### `h2physics.adapters.psa_cycle.PsaCycleEvidence`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/psa_cycle.py#L82)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `source_id` | `str` | `required` |
| `energy_reference_id` | `str` | `required` |
| `gas_phase_scope_id` | `str` | `required` |
| `parameter_origin` | `Origin` | `required` |
| `component_absolute_tolerance_mol` | `float` | `1e-08` |
| `energy_absolute_tolerance_j` | `float` | `0.0001` |

#### `h2physics.adapters.psa_cycle.PsaCycleRun`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/psa_cycle.py#L144)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `points` | `tuple[PsaCyclePoint, ...]` | `required` |
| `totals` | `PsaCycleTotals` | `required` |
| `final_cycle_totals` | `PsaCycleTotals` | `required` |
| `native_result` | `Mapping` | `required` |
| `native_call_results` | `tuple` | `required` |
| `native_checkpoint_metadata` | `Mapping` | `required` |
| `native_schedule` | `Mapping` | `required` |
| `audit_network` | `Any` | `required` |
| `bed_adapter` | `PsaDynaBed` | `required` |
| `native_bindings` | `PsaCycleNative` | `required` |
| `case_parameters` | `Mapping` | `required` |
| `evidence` | `PsaCycleEvidence` | `required` |
| `basis` | `AdsorptionBasis` | `required` |
| `domain` | `AdsorptionDomain` | `required` |
| `clock_id` | `str` | `required` |
| `start_time_s` | `float` | `required` |
| `input_sha256` | `str` | `required` |
| `native_code_sha256` | `str` | `required` |
| `original_integrator_objects_available` | `bool` | `False` |

#### `h2physics.adapters.psa_cycle.PsaCyclePoint`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/psa_cycle.py#L102)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `time_s` | `float` | `required` |
| `native_elapsed_s` | `float` | `required` |
| `completed_cycles` | `int` | `required` |
| `completed_slots_in_cycle` | `int` | `required` |
| `native_state` | `np.ndarray` | `required` |
| `beds` | `tuple` | `required` |
| `inventory_mol` | `np.ndarray` | `required` |
| `stored_energy_j` | `float` | `required` |
| `feed_mol` | `np.ndarray` | `required` |
| `product_mol` | `np.ndarray` | `required` |
| `tail_mol` | `np.ndarray` | `required` |
| `feed_enthalpy_j` | `float` | `required` |
| `product_enthalpy_j` | `float` | `required` |
| `tail_enthalpy_j` | `float` | `required` |
| `ambient_heat_j` | `float` | `required` |
| `vacuum_work_j` | `float` | `required` |
| `component_residual_mol` | `np.ndarray` | `required` |
| `energy_residual_j` | `float` | `required` |

#### `h2physics.adapters.psa_cycle.PsaCycleTotals`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/psa_cycle.py#L129)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `species` | `tuple[str, ...]` | `required` |
| `feed_mol` | `np.ndarray` | `required` |
| `product_mol` | `np.ndarray` | `required` |
| `tail_mol` | `np.ndarray` | `required` |
| `hydrogen_product_purity` | `float &#124; None` | `required` |
| `hydrogen_product_to_feed_ratio` | `float &#124; None` | `required` |
| `css_hydrogen_recovery` | `float &#124; None` | `required` |


<a id="module-h2physics-adapters-cantera_membrane-canteradustygastransport-flux"></a>

## 다성분 다공성 막 투과 유속 / Multicomponent porous-membrane transport

Family / navigation ID: `separation.membrane`

Import module: `h2physics.adapters.cantera_membrane`; selected entry: `CanteraDustyGasTransport.flux`.

#### `h2physics.adapters.cantera_membrane.CanteraDustyGasTransport`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/cantera_membrane.py#L257)

Fresh actual native objects per call; no finite device or reaction integration.

A factory may expose a shared source Solution: audited independent copies
protect its state. Returned mutable native diagnostics are never reused.
The source's full thermo/transport definitions must remain unchanged.

```python
CanteraDustyGasTransport(phase_factory: Callable, mechanism_basis: MechanismBasis, *, evidence: MembraneTransportEvidence)
```

#### `h2physics.adapters.cantera_membrane.CanteraDustyGasTransport.flux`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/cantera_membrane.py#L277)

```python
flux(self, left: MembraneEndpoint, right: MembraneEndpoint, geometry: PorousTransportGeometry) -> MembraneFlux
```

### Returned value / 반환값

`MembraneFlux`

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

#### `h2physics.adapters.cantera_membrane.MembraneTransportEvidence`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/cantera_membrane.py#L115)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `transport_source_id` | `str` | `required` |
| `gas_phase_id` | `str` | `required` |
| `gas_scope_id` | `str` | `required` |
| `energy_reference_id` | `str` | `required` |
| `hydrogen_partition_id` | `str` | `required` |

#### `h2physics.adapters.cantera_membrane.MembraneEndpoint`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/cantera_membrane.py#L80)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `temperature_k` | `float` | `required` |
| `pressure_pa_absolute` | `float` | `required` |
| `species` | `tuple[str, ...]` | `required` |
| `fractions` | `np.ndarray` | `required` |
| `composition_basis` | `str` | `required` |
| `boundary_id` | `str` | `required` |
| `phase_id` | `str` | `required` |
| `geometry_id` | `str` | `required` |
| `source_id` | `str` | `required` |
| `origin` | `Origin` | `required` |

Computed properties: `content_sha256`.

#### `h2physics.adapters.cantera_membrane.PorousTransportGeometry`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/cantera_membrane.py#L52)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `porosity` | `float` | `required` |
| `tortuosity` | `float` | `required` |
| `mean_pore_radius_m` | `float` | `required` |
| `permeability_m2` | `float` | `required` |
| `thickness_m` | `float` | `required` |
| `geometry_id` | `str` | `required` |
| `evidence_id` | `str` | `required` |
| `origin` | `Origin` | `required` |

#### `h2physics.adapters.cantera_membrane.MembraneFlux`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/cantera_membrane.py#L189)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `left` | `MembraneEndpoint` | `required` |
| `right` | `MembraneEndpoint` | `required` |
| `geometry` | `PorousTransportGeometry` | `required` |
| `mechanism_basis` | `MechanismBasis` | `required` |
| `evidence` | `MembraneTransportEvidence` | `required` |
| `species` | `tuple[str, ...]` | `required` |
| `left_state` | `MembraneGasSnapshot` | `required` |
| `right_state` | `MembraneGasSnapshot` | `required` |
| `native_mean_state` | `MembraneGasSnapshot` | `required` |
| `native_flux_kmol_m2_s` | `np.ndarray` | `required` |
| `molar_flux_mol_m2_s` | `np.ndarray` | `required` |
| `mass_flux_kg_m2_s` | `np.ndarray` | `required` |
| `molecular_weights_kg_mol` | `np.ndarray` | `required` |
| `native_multi_diffusion_m2_s` | `np.ndarray` | `required` |
| `source_phase` | `object` | `required` |
| `owned_endpoint_phases` | `tuple` | `required` |
| `native_dusty_gas` | `object` | `required` |
| `phase_copy_audits` | `tuple[NativePhaseCopyAudit, ...]` | `required` |
| `transport_copy_audits` | `tuple[NativeTransportCopyAudit, ...]` | `required` |
| `source_phase_sha256` | `str` | `required` |
| `owned_phase_sha256` | `str` | `required` |
| `input_sha256` | `str` | `required` |
| `frame` | `str` | `FLUX_FRAME` |
| `thermal_closure` | `str` | `'unresolved; endpoint enthalpies are native reference diagnostics, not an energy balance'` |

#### `h2physics.adapters.cantera_membrane.MembraneGasSnapshot`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/cantera_membrane.py#L128)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `temperature_k` | `float` | `required` |
| `pressure_pa_absolute` | `float` | `required` |
| `density_kg_m3` | `float` | `required` |
| `mole_fractions` | `np.ndarray` | `required` |
| `mass_fractions` | `np.ndarray` | `required` |
| `partial_molar_enthalpies_j_mol` | `np.ndarray` | `required` |

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

#### `h2physics.adapters.cantera_membrane.NativeTransportCopyAudit`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/cantera_membrane.py#L144)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `source_sha256` | `str` | `required` |
| `owned_sha256` | `str` | `required` |
| `maximum_relative_roundtrip` | `float` | `required` |
| `relative_roundtrip_limit` | `float` | `TRANSPORT_COPY_RELATIVE_LIMIT` |


## Maintaining this guide / 갱신

Curated purposes and entry selection live in `scripts/readme_module_guide.py`. Run `python scripts/readme_module_guide.py` to regenerate both README blocks and this file. Run `python scripts/readme_module_guide.py --check` to reject stale output, unresolved callables or missing catalog IDs. The script parses source with the standard library, imports no physical engine and runs no calculation. Review purpose/units/limits against domain manuals when an API changes. It preserves authored scientific attribution and performs no automatic translation of external material.
