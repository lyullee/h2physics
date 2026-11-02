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

- [실패 사례를 보존하는 파라미터 불확실성 전파 / Parameter-sample propagation with retained failed cases](#module-h2physics-uncertainty-propagate)
- [독립 입력의 Sobol 민감도 분석 / Independent-input Sobol sensitivity analysis](#module-h2physics-uncertainty-sobol_sensitivity)
- [연간 제품·금융 기준이 명시된 수소 현금흐름 경제성 / Native annual hydrogen DCF with explicit financial/product basis](#module-h2physics-adapters-hydrogen_economics-evaluate_hydrogen_economics)

<a id="module-h2physics-uncertainty-propagate"></a>

## 실패 사례를 보존하는 파라미터 불확실성 전파 / Parameter-sample propagation with retained failed cases

Family / navigation ID: `research.uncertainty`

Import module: `h2physics.uncertainty`; selected entry: `propagate`.

#### `h2physics.uncertainty.propagate`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/uncertainty.py#L901)

```python
propagate(design: ParameterDesign, model: UncertainModel) -> PropagationResult
```

### Returned value / 반환값

`PropagationResult`

### Related input/return records / 관련 입력·반환 객체

#### `h2physics.uncertainty.ParameterDesign`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/uncertainty.py#L562)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `space` | `IndependentParameterSpace` | `required` |
| `space_sha256` | `str` | `required` |
| `values` | `np.ndarray` | `required` |
| `unit_cube` | `np.ndarray` | `required` |
| `seed` | `int` | `required` |
| `native_engine` | `Any` | `required` |
| `content_sha256` | `str` | `field(init=False)` |

#### `h2physics.uncertainty.UncertainModel`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/uncertainty.py#L308)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `callback` | `Callable[[Mapping[str, float]], Mapping[str, float] &#124; ModelOutput]` | `required` |
| `outputs` | `tuple[Variable, ...]` | `required` |
| `evidence` | `UncertaintyEvidence` | `required` |

#### `h2physics.uncertainty.PropagationResult`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/uncertainty.py#L712)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `design` | `ParameterDesign` | `required` |
| `model` | `UncertainModel` | `required` |
| `evaluations` | `tuple[CaseEvaluation, ...]` | `required` |
| `values` | `np.ndarray` | `required` |

#### `h2physics.uncertainty.IndependentParameterSpace`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/uncertainty.py#L232)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `parameters` | `tuple[ParameterDistribution, ...]` | `required` |
| `independence_evidence_id` | `str` | `required` |
| `space_id` | `str` | `required` |

Computed properties: `content_sha256`.

#### `h2physics.uncertainty.ModelOutput`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/uncertainty.py#L302)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `values` | `Mapping[str, float]` | `required` |
| `raw` | `Any` | `None` |

#### `h2physics.observations.Variable`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/observations.py#L16)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `name` | `str` | `required` |
| `quantity` | `str` | `required` |
| `unit` | `str` | `required` |
| `basis_id` | `str` | `''` |

#### `h2physics.uncertainty.UncertaintyEvidence`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/uncertainty.py#L280)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `model_id` | `str` | `required` |
| `model_revision_id` | `str` | `required` |
| `deterministic_reset_evidence_id` | `str` | `required` |
| `statistical_scope_id` | `str` | `required` |
| `origin` | `Origin` | `required` |

#### `h2physics.uncertainty.CaseEvaluation`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/uncertainty.py#L327)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `index` | `int` | `required` |
| `batch_index` | `int` | `required` |
| `parameters` | `Mapping[str, float]` | `required` |
| `outputs` | `Mapping[str, float]` | `required` |
| `raw` | `Any` | `required` |


<a id="module-h2physics-uncertainty-sobol_sensitivity"></a>

## 독립 입력의 Sobol 민감도 분석 / Independent-input Sobol sensitivity analysis

Family / navigation ID: `research.uncertainty`

Import module: `h2physics.uncertainty`; selected entry: `sobol_sensitivity`.

#### `h2physics.uncertainty.sobol_sensitivity`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/uncertainty.py#L1021)

Native Saltelli indices for the declared independent, deterministic model.

Finite-sample negative estimates remain unchanged. Constant-output indices
have no variance denominator and are exposed as NaN with a false mask,
separately from the actual native result's zero convention.

```python
sobol_sensitivity(space: IndependentParameterSpace, model: UncertainModel, *, power: int, seed: int, maximum_evaluations: int=1000000) -> SobolSensitivity
```

### Returned value / 반환값

`SobolSensitivity`

### Related input/return records / 관련 입력·반환 객체

#### `h2physics.uncertainty.IndependentParameterSpace`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/uncertainty.py#L232)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `parameters` | `tuple[ParameterDistribution, ...]` | `required` |
| `independence_evidence_id` | `str` | `required` |
| `space_id` | `str` | `required` |

Computed properties: `content_sha256`.

#### `h2physics.uncertainty.UncertainModel`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/uncertainty.py#L308)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `callback` | `Callable[[Mapping[str, float]], Mapping[str, float] &#124; ModelOutput]` | `required` |
| `outputs` | `tuple[Variable, ...]` | `required` |
| `evidence` | `UncertaintyEvidence` | `required` |

#### `h2physics.uncertainty.SobolSensitivity`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/uncertainty.py#L930)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `space` | `IndependentParameterSpace` | `required` |
| `space_sha256` | `str` | `required` |
| `model` | `UncertainModel` | `required` |
| `native_result` | `Any` | `required` |
| `evaluations` | `tuple[CaseEvaluation, ...]` | `required` |
| `batches` | `tuple[tuple[np.ndarray, np.ndarray], ...]` | `required` |
| `first_order` | `np.ndarray` | `required` |
| `total_order` | `np.ndarray` | `required` |
| `variance_resolved` | `np.ndarray` | `required` |
| `n_base` | `int` | `required` |
| `seed` | `int` | `required` |

#### `h2physics.uncertainty.ParameterDistribution`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/uncertainty.py#L187)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `variable` | `Variable` | `required` |
| `distribution` | `Any` | `required` |
| `distribution_id` | `str` | `required` |
| `source_id` | `str` | `required` |
| `origin` | `Origin` | `required` |
| `admitted_minimum` | `float` | `required` |
| `admitted_maximum` | `float` | `required` |
| `native_definition_sha256` | `str` | `field(init=False)` |
| `native_definition_snapshot` | `Mapping[str, Any]` | `field(init=False)` |

#### `h2physics.uncertainty.ModelOutput`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/uncertainty.py#L302)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `values` | `Mapping[str, float]` | `required` |
| `raw` | `Any` | `None` |

#### `h2physics.observations.Variable`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/observations.py#L16)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `name` | `str` | `required` |
| `quantity` | `str` | `required` |
| `unit` | `str` | `required` |
| `basis_id` | `str` | `''` |

#### `h2physics.uncertainty.UncertaintyEvidence`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/uncertainty.py#L280)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `model_id` | `str` | `required` |
| `model_revision_id` | `str` | `required` |
| `deterministic_reset_evidence_id` | `str` | `required` |
| `statistical_scope_id` | `str` | `required` |
| `origin` | `Origin` | `required` |

#### `h2physics.uncertainty.CaseEvaluation`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/uncertainty.py#L327)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `index` | `int` | `required` |
| `batch_index` | `int` | `required` |
| `parameters` | `Mapping[str, float]` | `required` |
| `outputs` | `Mapping[str, float]` | `required` |
| `raw` | `Any` | `required` |


<a id="module-h2physics-adapters-hydrogen_economics-evaluate_hydrogen_economics"></a>

## 연간 제품·금융 기준이 명시된 수소 현금흐름 경제성 / Native annual hydrogen DCF with explicit financial/product basis

Family / navigation ID: `research.economics`

Import module: `h2physics.adapters.hydrogen_economics`; selected entry: `evaluate_hydrogen_economics`.

#### `h2physics.adapters.hydrogen_economics.evaluate_hydrogen_economics`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/hydrogen_economics.py#L958)

Execute only on explicit call; preserve the actual native object even on failure.

```python
evaluate_hydrogen_economics(projection, annual_basis, financial_inputs, *, native, window_cost=None)
```

The source has no explicit return annotation; inspect its return statements and the domain manual. No return type is invented by this generator.

### Returned value / 반환값

`HydrogenEconomicsResult`

This return contract was reviewed from the implementation; it is not an annotation present in the source signature.

### Related input/return records / 관련 입력·반환 객체

#### `h2physics.adapters.hydrogen_economics.HydrogenEconomicsResult`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/hydrogen_economics.py#L860)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `lcoh_usd_kg` | `float` | `required` |
| `denominator` | `str` | `required` |
| `currency` | `str` | `required` |
| `base_year` | `int` | `required` |
| `projection` | `PhysicalEconomicProjection` | `required` |
| `annual_basis` | `AnnualFinancialBasis` | `required` |
| `financial_inputs` | `AnnualFinancialInputs` | `required` |
| `window_utility_cost` | `WindowUtilityCost &#124; None` | `required` |
| `native_provider` | `NativeHydrogenEconomics` | `required` |
| `native_object` | `object` | `required` |
| `native_input_before` | `Mapping` | `required` |
| `native_npv` | `Mapping` | `required` |
| `native_contributions` | `Mapping` | `required` |
| `annual_arrays` | `Mapping` | `required` |
| `native_cash_flow_return` | `float` | `required` |
| `native_stdout` | `str` | `required` |
| `input_fingerprint` | `str` | `required` |
| `status` | `str` | `STATUS` |

#### `h2physics.adapters.physical_economics.PhysicalEconomicProjection`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/physical_economics.py#L540)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `source` | `object` | `required` |
| `window` | `ReportingWindow` | `required` |
| `hydrogen_id` | `str` | `required` |
| `quantities` | `Mapping[str, float &#124; None]` | `required` |
| `unresolved` | `tuple[str, ...]` | `required` |
| `source_fingerprint` | `str` | `required` |
| `source_binding` | `ValidatedSourceBinding` | `required` |

#### `h2physics.adapters.hydrogen_economics.AnnualFinancialBasis`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/hydrogen_economics.py#L491)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `currency` | `str` | `required` |
| `base_year` | `int` | `required` |
| `operating_year_label` | `int` | `required` |
| `seconds_in_operating_year` | `float` | `required` |
| `annual_product_kg_at_gate` | `float` | `required` |
| `annual_generated_h2_kg` | `float` | `required` |
| `annual_initial_h2_inventory_kg` | `float` | `required` |
| `annual_final_h2_inventory_kg` | `float` | `required` |
| `annual_nonproduct_h2_out_kg` | `float` | `required` |
| `product_grade_id` | `str` | `required` |
| `product_pressure_pa` | `float` | `required` |
| `product_gate_evidence_id` | `str` | `required` |
| `representation` | `str` | `required` |
| `representation_evidence_id` | `str` | `required` |
| `annual_inventory_reconciliation_id` | `str` | `required` |
| `annual_repetition_evidence_id` | `str` | `required` |
| `capacity_factor` | `float &#124; None` | `required` |
| `capacity_factor_evidence_id` | `str` | `required` |
| `unresolved_cost_resolutions` | `Mapping[str, str]` | `required` |
| `window_repetitions` | `float &#124; None` | `None` |
| `origin` | `Origin` | `Origin.UNRESOLVED` |

#### `h2physics.adapters.hydrogen_economics.AnnualFinancialInputs`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/hydrogen_economics.py#L627)

All native financial scalars and annual monetary quantities are caller inputs.

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `financial_values` | `Mapping[str, float &#124; str]` | `required` |
| `construction_fractions` | `tuple[float, ...]` | `required` |
| `depreciable_capital_usd` | `float` | `required` |
| `nondepreciable_capital_usd` | `float` | `required` |
| `fixed_operating_cost_usd_year` | `float` | `required` |
| `variable_operating_cost_usd_year` | `float` | `required` |
| `additional_variable_cost_usd_year` | `float` | `required` |
| `replacement_usd_by_analysis_year` | `tuple[float, ...]` | `required` |
| `financial_evidence` | `Mapping[str, str]` | `required` |
| `utility_scope_evidence_id` | `str` | `required` |
| `variable_cost_annual_basis_id` | `str` | `required` |
| `capital_scope_evidence_id` | `str` | `required` |
| `native_lookup_evidence_id` | `str` | `required` |

#### `h2physics.adapters.physical_economics.WindowUtilityCost`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/physical_economics.py#L662)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `projection` | `PhysicalEconomicProjection` | `required` |
| `line_items` | `tuple` | `required` |
| `total_usd` | `float` | `required` |
| `currency` | `str` | `required` |
| `base_year` | `int` | `required` |
| `physical_fingerprint` | `str` | `required` |

#### `h2physics.adapters.hydrogen_economics.NativeHydrogenEconomics`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/hydrogen_economics.py#L761)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `module` | `object` | `required` |
| `native_class` | `object` | `required` |
| `root` | `Path` | `required` |
| `source_sha256` | `str` | `required` |
| `call_bindings` | `tuple` | `required` |


## Maintaining this guide / 갱신

Curated purposes and entry selection live in `scripts/readme_module_guide.py`. Run `python scripts/readme_module_guide.py` to regenerate both README blocks and this file. Run `python scripts/readme_module_guide.py --check` to reject stale output, unresolved callables or missing catalog IDs. The script parses source with the standard library, imports no physical engine and runs no calculation. Review purpose/units/limits against domain manuals when an API changes. It preserves authored scientific attribution and performs no automatic translation of external material.
