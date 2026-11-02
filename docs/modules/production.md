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

- [전해조·연료전지 공통 분극·수소 생성/소모·전력 / Shared polarization, Faraday production/consumption and power](#module-h2physics-electrochemistry-hydrogenstack-evaluate)
- [냉각재 경계를 명시한 유한 스택 열응답 / Finite stack thermal states with declared coolant boundary](#module-h2physics-electrochemical_thermal-finitethermalstack-run)
- [기체 채널·반응·스택 열응답의 동기화 계산 / Native H2/O2/water-vapor channels and stack thermal dynamics](#module-h2physics-adapters-cantera_fuel_cell-run_cantera_synchronized_fuel_cell)
- [분광 광자수·흡수·양자수율에 따른 수소 생산율 / Spectral photon budget, absorption and declared quantum yield](#module-h2physics-photochemistry-photon_hydrogen_rate)
- [단계별 열화학 전환량·성분 재고·필요 열량 / Finite staged reaction extents, stocks and caloric duties](#module-h2physics-thermochemical-finitethermochemicalcycle-run)
- [외부 촉매 표면반응·완전혼합 유동 반응기 / Native catalytic reacting flow and surface chemistry](#module-h2physics-adapters-cantera_surface_reactor-canteracatalyticsurfacereactor-run_flowing_cstr)
- [지정된 기체·고체 상의 다상 평형 / Declared gas/solid multiphase equilibrium](#module-h2physics-adapters-cantera_multiphase-canteramultiphaseequilibrium-equilibrate)
- [외부 ADM1 생물 반응·성분·수소 수지 / Native ADM1 biological component and hydrogen accounting](#module-h2physics-adapters-biological-qsdsanadm1digester-run)
- [미생물 전환·유한 재고·전극 반응 결합 / Finite microbial conversion and native electrode coupling](#module-h2physics-adapters-microbial_cell-finitemicrobialcell-run)
- [태양광 전기 운전점과 전해조·수신 재고 결합 / PV electrical load-line coupling to electrolysis and storage](#module-h2physics-adapters-pv_electrolysis-pvelectrolysis-run)

<a id="module-h2physics-electrochemistry-hydrogenstack-evaluate"></a>

## 전해조·연료전지 공통 분극·수소 생성/소모·전력 / Shared polarization, Faraday production/consumption and power

Family / navigation ID: `production.electrolyzer`, `production.fuel_cell`

Import module: `h2physics.electrochemistry`; selected entry: `HydrogenStack.evaluate`.

#### `h2physics.electrochemistry.HydrogenStack`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/electrochemistry.py#L182)

Native callbacks select thermochemistry and separate polarization losses.

Current density is a nonnegative magnitude. Electrolysis consumes positive
electrical power and produces positive hydrogen; fuel-cell outputs have
negative signs for those same boundary quantities. Faradaic inefficiency
changes the gas balance, but its chemical/thermal fate is not silently
assigned to heat. No cell aging, crossover or thermal inventory is implied.

```python
HydrogenStack(geometry: StackGeometry, thermochemistry: Callable[[float], ReactionEnergy], losses: Mapping[str, Callable[[float, float], float]])
```

#### `h2physics.electrochemistry.HydrogenStack.evaluate`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/electrochemistry.py#L200)

```python
evaluate(self, current_density_a_m2: float, temperature_k: float, *, mode: Literal['electrolysis', 'fuel_cell'], faradaic_efficiency: float=1.0) -> StackResult
```

### Returned value / 반환값

`StackResult`

### Related input/return records / 관련 입력·반환 객체

#### `h2physics.electrochemistry.StackGeometry`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/electrochemistry.py#L154)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `series_cells` | `int` | `required` |
| `active_area_m2` | `float` | `required` |
| `hydrogen_molar_mass_kg_mol` | `float` | `required` |

#### `h2physics.electrochemistry.ReactionEnergy`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/electrochemistry.py#L19)

Positive water-splitting reaction energies per mole H2 at the actual state.

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `gibbs_j_mol_h2` | `float` | `required` |
| `enthalpy_j_mol_h2` | `float` | `required` |
| `reference_id` | `str` | `required` |
| `water_phase` | `str` | `required` |

Computed properties: `reversible_voltage_v`, `thermoneutral_voltage_v`.

#### `h2physics.electrochemistry.StackResult`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/electrochemistry.py#L167)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `mode` | `str` | `required` |
| `reaction_energy` | `ReactionEnergy` | `required` |
| `current_a` | `float` | `required` |
| `cell_voltage_v` | `float` | `required` |
| `stack_voltage_v` | `float` | `required` |
| `loss_voltages` | `tuple[tuple[str, float], ...]` | `required` |
| `electric_input_w` | `float` | `required` |
| `hydrogen_production_mol_s` | `float` | `required` |
| `hydrogen_production_kg_s` | `float` | `required` |
| `reaction_enthalpy_rate_w` | `float` | `required` |
| `unallocated_energy_rate_w` | `float` | `required` |
| `isothermal_heat_rejection_w` | `float &#124; None` | `required` |


<a id="module-h2physics-electrochemical_thermal-finitethermalstack-run"></a>

## 냉각재 경계를 명시한 유한 스택 열응답 / Finite stack thermal states with declared coolant boundary

Family / navigation ID: `production.electrolyzer`

Import module: `h2physics.electrochemical_thermal`; selected entry: `FiniteThermalStack.run`.

#### `h2physics.electrochemical_thermal.FiniteThermalStack`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/electrochemical_thermal.py#L205)

Piecewise-held electrical operation with a finite stack heat capacity.

The coolant law is ``UA(T, T_coolant) * (T - T_coolant)`` and may reverse
sign.  The solver advances temperature and independent accumulated heat
ledgers together.  No controller, coolant inventory, crossover, ageing or
spatial cell temperature is inferred.

```python
FiniteThermalStack(stack: HydrogenStack, boundary: ThermalStackBoundary, *, relative_tolerance=1e-08, absolute_tolerance=1e-10, energy_tolerance_j=1e-05)
```

#### `h2physics.electrochemical_thermal.FiniteThermalStack.run`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/electrochemical_thermal.py#L229)

```python
run(self, initial_temperature_k: float, stages: Sequence[ThermalStackStage]) -> ThermalStackTrace
```

### Returned value / 반환값

`ThermalStackTrace`

### Related input/return records / 관련 입력·반환 객체

#### `h2physics.electrochemical_thermal.ThermalStackBoundary`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/electrochemical_thermal.py#L82)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `heat_capacity_j_k` | `float` | `required` |
| `conductance_w_k` | `Callable[[float, float], float]` | `required` |
| `temperature_bounds_k` | `tuple[float, float]` | `required` |
| `reference_id` | `str` | `required` |
| `coolant_boundary_id` | `str` | `required` |

#### `h2physics.electrochemical_thermal.ThermalStackStage`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/electrochemical_thermal.py#L114)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `identifier` | `str` | `required` |
| `start_s` | `float` | `required` |
| `end_s` | `float` | `required` |
| `current_density_a_m2` | `float` | `required` |
| `coolant_temperature_k` | `float` | `required` |
| `mode` | `str` | `required` |
| `faradaic_efficiency` | `float` | `1.0` |
| `auxiliary_heat_into_w` | `float` | `0.0` |

#### `h2physics.electrochemical_thermal.ThermalStackTrace`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/electrochemical_thermal.py#L163)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `initial_temperature_k` | `float` | `required` |
| `final_temperature_k` | `float` | `required` |
| `stages` | `tuple[ThermalStackStageResult, ...]` | `required` |
| `generated_heat_j` | `float` | `required` |
| `coolant_heat_out_j` | `float` | `required` |
| `auxiliary_heat_into_j` | `float` | `required` |
| `internal_energy_change_j` | `float` | `required` |
| `energy_residual_j` | `float` | `required` |
| `status` | `str` | `STATUS` |

#### `h2physics.electrochemical_thermal.ThermalStackStageResult`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/electrochemical_thermal.py#L144)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `command` | `ThermalStackStage` | `required` |
| `initial_temperature_k` | `float` | `required` |
| `final_temperature_k` | `float` | `required` |
| `generated_heat_j` | `float` | `required` |
| `coolant_heat_out_j` | `float` | `required` |
| `auxiliary_heat_into_j` | `float` | `required` |
| `internal_energy_change_j` | `float` | `required` |
| `energy_residual_j` | `float` | `required` |
| `initial_stack_result` | `StackResult` | `required` |
| `final_stack_result` | `StackResult` | `required` |
| `native_result` | `object` | `required` |
| `initial_coolant_state` | `ThermoState &#124; None` | `None` |
| `final_coolant_state` | `ThermoState &#124; None` | `None` |
| `external_coolant_heat_j` | `float` | `0.0` |
| `coolant_energy_residual_j` | `float` | `0.0` |


<a id="module-h2physics-adapters-cantera_fuel_cell-run_cantera_synchronized_fuel_cell"></a>

## 기체 채널·반응·스택 열응답의 동기화 계산 / Native H2/O2/water-vapor channels and stack thermal dynamics

Family / navigation ID: `production.fuel_cell`

Import module: `h2physics.adapters.cantera_fuel_cell`; selected entry: `run_cantera_synchronized_fuel_cell`.

#### `h2physics.adapters.cantera_fuel_cell.run_cantera_synchronized_fuel_cell`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/cantera_fuel_cell.py#L440)

Integrate three separated gas channels and one finite stack state together.

``current_density(view)`` is the caller's requested current/control policy.
Its response may use the live pressures/composition, but no current limiting
or automatic depletion shutdown is invented here. The heat partition callback
receives the native species-enthalpy transfer rate and returns signed heat
rates whose total closes it against electrical power.

```python
run_cantera_synchronized_fuel_cell(*, channels: Mapping[str, CanteraFuelCellChannel], stack: HydrogenStack, standard_reaction_energy: ReactionEnergy, thermal: StackThermalParameters, current_density: Callable[[NativeFuelCellTrialView], float], thermal_partition: Callable[[NativeFuelCellTrialView, FuelCellTrialExchange, float], FuelCellThermalPartition], time_s, clock_id: str, run_evidence_id: str, energy_reference_id: str, fugacity_provider: FuelCellFugacityActivityProvider | None=None, settings=CanteraFuelCellSettings())
```

The source has no explicit return annotation; inspect its return statements and the domain manual. No return type is invented by this generator.

### Returned value / 반환값

`CanteraFuelCellTrace`

This return contract was reviewed from the implementation; it is not an annotation present in the source signature.

### Related input/return records / 관련 입력·반환 객체

#### `h2physics.adapters.cantera_fuel_cell.CanteraFuelCellTrace`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/cantera_fuel_cell.py#L194)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `channels` | `Mapping[str, CanteraFuelCellChannel]` | `required` |
| `stack` | `HydrogenStack` | `field(repr=False, compare=False)` |
| `standard_reaction_energy` | `ReactionEnergy` | `required` |
| `thermal` | `StackThermalParameters` | `required` |
| `clock_id` | `str` | `required` |
| `run_evidence_id` | `str` | `required` |
| `settings` | `object` | `required` |
| `accepted` | `tuple[CanteraFuelCellSnapshot, ...]` | `required` |
| `native` | `NativeCanteraFuelCellObjects` | `field(repr=False, compare=False)` |
| `maximum_component_mole_residual_mol` | `float` | `required` |
| `maximum_channel_energy_residual_j` | `float` | `required` |
| `stack_energy_residual_j` | `float` | `required` |
| `combined_energy_residual_j` | `float` | `required` |

#### `h2physics.adapters.cantera_fuel_cell.CanteraFuelCellChannel`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/cantera_fuel_cell.py#L47)

One independently owned Cantera ideal-gas phase and rigid CV.

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `role` | `str` | `required` |
| `phase` | `object` | `field(repr=False, compare=False)` |
| `species_id` | `str` | `required` |
| `volume_m3` | `float` | `required` |
| `activity_reference_pressure_pa` | `float` | `required` |
| `activity_reference_id` | `str` | `required` |
| `energy_reference_id` | `str` | `required` |
| `evidence_id` | `str` | `required` |

#### `h2physics.electrochemistry.ReactionEnergy`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/electrochemistry.py#L19)

Positive water-splitting reaction energies per mole H2 at the actual state.

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `gibbs_j_mol_h2` | `float` | `required` |
| `enthalpy_j_mol_h2` | `float` | `required` |
| `reference_id` | `str` | `required` |
| `water_phase` | `str` | `required` |

Computed properties: `reversible_voltage_v`, `thermoneutral_voltage_v`.

#### `h2physics.adapters.cantera_fuel_cell.StackThermalParameters`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/cantera_fuel_cell.py#L74)

Explicit lumped stack sensible storage and coolant boundary.

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `heat_capacity_j_k` | `float` | `required` |
| `energy_reference_temperature_k` | `float` | `required` |
| `initial_temperature_k` | `float` | `required` |
| `coolant_temperature_k` | `float` | `required` |
| `conductance_w_k` | `float` | `required` |
| `energy_reference_id` | `str` | `required` |
| `boundary_evidence_id` | `str` | `required` |

#### `h2physics.adapters.cantera_fuel_cell.NativeFuelCellTrialView`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/cantera_fuel_cell.py#L125)

Live native channel coordinates passed to caller-owned control/heat callbacks.

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `time_s` | `float` | `required` |
| `clock_id` | `str` | `required` |
| `stack_temperature_k` | `float` | `required` |
| `channels` | `Mapping[str, FuelCellTrialGasState]` | `required` |

#### `h2physics.adapters.cantera_fuel_cell.FuelCellThermalPartition`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/cantera_fuel_cell.py#L99)

Caller-assigned heat rates into each gas channel and the stack.

The four signed values must sum to electrical power into the stack minus
the native channel species-enthalpy transfer rate. No physical split is
inferred by this adapter.

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `hydrogen_w` | `float` | `required` |
| `oxygen_w` | `float` | `required` |
| `water_vapor_w` | `float` | `required` |
| `stack_w` | `float` | `required` |
| `evidence_id` | `str` | `required` |

Computed properties: `total_into_device_w`.

#### `h2physics.adapters.fuel_cell_trial.FuelCellTrialExchange`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/fuel_cell_trial.py#L151)

Issued stack result and stoichiometric source terms for one trial only.

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `stack` | `HydrogenStack` | `field(repr=False)` |
| `trial` | `FuelCellSynchronizedTrial` | `required` |
| `standard_reaction_energy` | `ReactionEnergy` | `required` |
| `operating_state` | `FuelCellOperatingState` | `required` |
| `corrected_reaction_energy` | `ReactionEnergy` | `required` |
| `stack_result` | `StackResult` | `required` |
| `species_molar_rate_into_cv_mol_s` | `Mapping[str, float]` | `required` |
| `species_mass_rate_into_cv_kg_s` | `Mapping[str, float]` | `required` |
| `net_mass_rate_residual_kg_s` | `float` | `required` |
| `unresolved_energy_rate_w` | `float` | `required` |
| `fugacity_provider` | `FuelCellFugacityActivityProvider &#124; None` | `field(default=None, repr=False)` |
| `evidence_id` | `str` | `''` |

#### `h2physics.adapters.fuel_cell_activity_receipt.FuelCellFugacityActivityProvider`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/fuel_cell_activity_receipt.py#L23)

Caller-owned fugacity service used to form non-ideal gas activities.

The callback must return fugacity in Pa for the named pure channel at the
supplied absolute pressure and temperature. Existing property providers can
be adapted here; this type adds no equation of state or fugacity correlation.

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `evaluate_fugacity_pa` | `Callable[[str, float, float], float]` | `field(repr=False)` |
| `provider_id` | `str` | `required` |
| `evidence_id` | `str` | `required` |

#### `h2physics.adapters.fuel_cell_trial.FuelCellTrialGasState`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/fuel_cell_trial.py#L39)

Caller-projected state of one separated native gas control volume.

The producer supplies the mole fraction and reactive-species inventory
from its actual trial state. This value type cannot verify native origin.

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `role` | `str` | `required` |
| `species_id` | `str` | `required` |
| `time_s` | `float` | `required` |
| `clock_id` | `str` | `required` |
| `pressure_pa` | `float` | `required` |
| `temperature_k` | `float` | `required` |
| `volume_m3` | `float` | `required` |
| `species_mole_fraction` | `float` | `required` |
| `species_moles_mol` | `float` | `required` |
| `species_molar_mass_kg_mol` | `float` | `required` |
| `activity_reference_pressure_pa` | `float` | `required` |
| `activity_reference_id` | `str` | `required` |
| `evidence_id` | `str` | `required` |

Computed properties: `ideal_activity`.

#### `h2physics.adapters.fuel_cell_trial.FuelCellSynchronizedTrial`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/fuel_cell_trial.py#L102)

Three separate channel states and one stack command at an exact trial time.

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `time_s` | `float` | `required` |
| `clock_id` | `str` | `required` |
| `stack_temperature_k` | `float` | `required` |
| `current_density_a_m2` | `float` | `required` |
| `channels` | `Mapping[str, FuelCellTrialGasState]` | `required` |
| `evidence_id` | `str` | `required` |

#### `h2physics.electrochemistry.FuelCellOperatingState`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/electrochemistry.py#L44)

Explicit reversible-voltage state for separated fuel-cell channels.

Activities are dimensionless relative to the declared channel references.
This value object does not claim a simultaneous native device solve; it lets
callers bind pressure/activity-corrected thermochemistry to the existing
polarization stack without changing its temperature-only compatibility API.

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `temperature_k` | `float` | `required` |
| `anode_pressure_pa` | `float` | `required` |
| `cathode_pressure_pa` | `float` | `required` |
| `hydrogen_activity` | `float` | `required` |
| `oxygen_activity` | `float` | `required` |
| `water_activity` | `float` | `required` |
| `water_phase` | `str` | `required` |
| `hydrogen_reference_id` | `str` | `required` |
| `oxygen_reference_id` | `str` | `required` |
| `water_reference_id` | `str` | `required` |
| `state_evidence_id` | `str` | `required` |

#### `h2physics.electrochemistry.StackResult`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/electrochemistry.py#L167)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `mode` | `str` | `required` |
| `reaction_energy` | `ReactionEnergy` | `required` |
| `current_a` | `float` | `required` |
| `cell_voltage_v` | `float` | `required` |
| `stack_voltage_v` | `float` | `required` |
| `loss_voltages` | `tuple[tuple[str, float], ...]` | `required` |
| `electric_input_w` | `float` | `required` |
| `hydrogen_production_mol_s` | `float` | `required` |
| `hydrogen_production_kg_s` | `float` | `required` |
| `reaction_enthalpy_rate_w` | `float` | `required` |
| `unallocated_energy_rate_w` | `float` | `required` |
| `isothermal_heat_rejection_w` | `float &#124; None` | `required` |

#### `h2physics.adapters.cantera_fuel_cell.CanteraFuelCellSnapshot`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/cantera_fuel_cell.py#L162)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `time_s` | `float` | `required` |
| `channels` | `Mapping[str, NativeFuelCellChannelSnapshot]` | `required` |
| `stack_temperature_k` | `float` | `required` |
| `stack_energy_j` | `float` | `required` |
| `stack_electrical_energy_into_j` | `float` | `required` |
| `stack_coolant_energy_into_j` | `float` | `required` |
| `stack_assigned_heat_into_j` | `float` | `required` |
| `trial_view` | `NativeFuelCellTrialView` | `required` |
| `exchange` | `FuelCellTrialExchange` | `required` |
| `thermal_partition` | `FuelCellThermalPartition` | `required` |
| `native_species_enthalpy_transfer_w` | `float` | `required` |

#### `h2physics.adapters.cantera_fuel_cell.NativeCanteraFuelCellObjects`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/cantera_fuel_cell.py#L187)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `reactors` | `tuple[object, ...]` | `required` |
| `network` | `object` | `required` |
| `connection` | `object` | `field(repr=False, compare=False)` |


<a id="module-h2physics-photochemistry-photon_hydrogen_rate"></a>

## 분광 광자수·흡수·양자수율에 따른 수소 생산율 / Spectral photon budget, absorption and declared quantum yield

Family / navigation ID: `production.photo`

Import module: `h2physics.photochemistry`; selected entry: `photon_hydrogen_rate`.

#### `h2physics.photochemistry.photon_hydrogen_rate`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/photochemistry.py#L394)

Resolve each declared band/line; do not attenuate incident AQY twice.

```python
photon_hydrogen_rate(supply: PhotonSupply, path: BeerLambertPath, quantum_yield: PhotonYield) -> PhotoRate
```

### Returned value / 반환값

`PhotoRate`

### Related input/return records / 관련 입력·반환 객체

#### `h2physics.photochemistry.PhotonSupply`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/photochemistry.py#L126)

Immutable finite-band/line optical input at one declared incident plane.

Bands have flat power density per wavelength; line inputs are discrete.
Mean wavelength converts total optical power to exact photon amount for
either declared representation, without a guessed source bandwidth.

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `representative_wavelength_m` | `np.ndarray` | `required` |
| `incident_power_w` | `np.ndarray` | `required` |
| `incident_photons_mol_s` | `np.ndarray` | `required` |
| `wavelength_edges_m` | `np.ndarray &#124; None` | `required` |
| `geometry_id` | `str` | `required` |
| `source_id` | `str` | `required` |
| `representation` | `str` | `required` |

Computed properties: `spectral_grid_sha256`, `content_sha256`.

#### `h2physics.photochemistry.BeerLambertPath`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/photochemistry.py#L236)

Uniform nonscattering path, with constant alpha/reflectance in each band.

Reflection is at the input plane. No diffuse scattering, multiple reflection,
refraction, catalyst loading law or optical-to-reactor-area conversion is inferred.

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `depth_m` | `float` | `required` |
| `absorption_coefficient_m_inv` | `np.ndarray` | `required` |
| `reflectance` | `np.ndarray` | `required` |
| `geometry_id` | `str` | `required` |
| `evidence_id` | `str` | `required` |
| `spectral_grid_sha256` | `str` | `required` |

Computed properties: `absorbed_fraction`, `transmitted_fraction`.

#### `h2physics.photochemistry.PhotonYield`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/photochemistry.py#L285)

Electron-equivalent yield with its exact optical input and conditions.

Values are mol productive electron equivalents per mol incident or absorbed
photons. This level assumes at most one productive electron per absorbed
photon. H2 requires two electron equivalents. Values are fractions, not %.

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `values` | `np.ndarray` | `required` |
| `basis` | `str` | `required` |
| `supply_sha256` | `str` | `required` |
| `conditions` | `PhotoConditions` | `required` |
| `evidence_id` | `str` | `required` |
| `origin` | `Origin` | `required` |

#### `h2physics.photochemistry.PhotoRate`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/photochemistry.py#L322)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `supply` | `PhotonSupply` | `required` |
| `optical_path` | `BeerLambertPath` | `required` |
| `quantum_yield` | `PhotonYield` | `required` |
| `reflected_power_w` | `np.ndarray` | `required` |
| `absorbed_power_w` | `np.ndarray` | `required` |
| `transmitted_power_w` | `np.ndarray` | `required` |
| `absorbed_photons_mol_s` | `np.ndarray` | `required` |
| `productive_electrons_mol_s` | `np.ndarray` | `required` |
| `energy_residual_w` | `np.ndarray` | `required` |
| `photon_residual_mol_s` | `np.ndarray` | `required` |

Computed properties: `photon_budget_admitted`, `hydrogen_mol_s`, `specific_hydrogen_mol_kg_s`.

#### `h2physics.photochemistry.PhotoConditions`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/photochemistry.py#L220)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `catalyst_id` | `str` | `required` |
| `medium_id` | `str` | `required` |
| `catalyst_mass_kg` | `float` | `required` |
| `temperature_k` | `float` | `required` |
| `pressure_pa_absolute` | `float` | `required` |
| `geometry_id` | `str` | `required` |
| `evidence_id` | `str` | `required` |


<a id="module-h2physics-thermochemical-finitethermochemicalcycle-run"></a>

## 단계별 열화학 전환량·성분 재고·필요 열량 / Finite staged reaction extents, stocks and caloric duties

Family / navigation ID: `production.thermochemical`

Import module: `h2physics.thermochemical`; selected entry: `FiniteThermochemicalCycle.run`.

#### `h2physics.thermochemical.FiniteThermochemicalCycle`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/thermochemical.py#L236)

Constant-pressure staged species/enthalpy accounting, without a new ODE.

Pre-withdrawals leave at the previous inventory temperature. Feeds retain
their supplied temperature. Conditioning and prescribed reactions reach
the stage endpoint temperature. Component takeoff is an imposed operation,
not separation performance. Additive h_i(T,P) excludes mixture excess heat.

```python
FiniteThermochemicalCycle(enthalpy: MolarEnthalpyProvider, evidence: ThermochemicalEvidence, *, tolerances: ThermochemicalTolerances=ThermochemicalTolerances())
```

#### `h2physics.thermochemical.FiniteThermochemicalCycle.run`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/thermochemical.py#L319)

```python
run(self, initial: ThermochemicalInventory, stages, *, carrier_species, require_carrier_closed=True, require_temperature_closed=True, require_full_inventory_closed=False) -> ThermochemicalTrace
```

### Returned value / 반환값

`ThermochemicalTrace`

### Related input/return records / 관련 입력·반환 객체

#### `h2physics.reactions.MolarEnthalpyProvider`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/reactions.py#L146)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `species` | `tuple[ChemicalSpecies, ...]` | `required` |
| `basis_id` | `str` | `required` |

#### `h2physics.thermochemical.ThermochemicalEvidence`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/thermochemical.py#L126)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `process_id` | `str` | `required` |
| `additive_phase_caloric_assumption_id` | `str` | `required` |
| `component_withdrawal_assumption_id` | `str` | `required` |
| `thermal_boundary_assumption_id` | `str` | `required` |
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

#### `h2physics.thermochemical.ThermochemicalTrace`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/thermochemical.py#L187)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `initial` | `ThermochemicalInventory` | `required` |
| `final` | `ThermochemicalInventory` | `required` |
| `steps` | `tuple[ThermochemicalStageResult, ...]` | `required` |
| `species` | `tuple` | `required` |
| `elements` | `tuple[str, ...]` | `required` |
| `feed_mol` | `np.ndarray` | `required` |
| `exported_mol` | `np.ndarray` | `required` |
| `element_residual_mol` | `np.ndarray` | `required` |
| `mass_residual_kg` | `float` | `required` |
| `net_heat_required_j` | `float` | `required` |
| `gross_heat_input_j` | `float` | `required` |
| `gross_heat_rejection_j` | `float` | `required` |
| `energy_residual_j` | `float` | `required` |
| `carrier_species` | `tuple[str, ...]` | `required` |
| `carrier_residual_mol` | `np.ndarray` | `required` |
| `carrier_closed` | `bool` | `required` |
| `temperature_closed` | `bool` | `required` |
| `full_inventory_closed` | `bool` | `required` |
| `evidence` | `ThermochemicalEvidence` | `required` |
| `enthalpy_provider` | `object` | `required` |

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

#### `h2physics.thermochemical.ThermochemicalStageResult`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/thermochemical.py#L159)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `stage` | `ThermochemicalStage` | `required` |
| `before` | `ThermochemicalInventory` | `required` |
| `after` | `ThermochemicalInventory` | `required` |
| `conversions` | `tuple[ReactionConversion, ...]` | `required` |
| `feed_mol` | `np.ndarray` | `required` |
| `withdrawn_mol` | `np.ndarray` | `required` |
| `feed_enthalpy_j` | `float` | `required` |
| `withdrawn_enthalpy_j` | `float` | `required` |
| `before_enthalpy_j` | `float` | `required` |
| `after_enthalpy_j` | `float` | `required` |
| `conditioning_heat_required_j` | `float` | `required` |
| `reaction_heat_required_j` | `float` | `required` |
| `heat_required_j` | `float` | `required` |
| `energy_residual_j` | `float` | `required` |
| `element_residual_mol` | `np.ndarray` | `required` |
| `mass_residual_kg` | `float` | `required` |

Computed properties: `mean_required_heat_w`.


<a id="module-h2physics-adapters-cantera_surface_reactor-canteracatalyticsurfacereactor-run_flowing_cstr"></a>

## 외부 촉매 표면반응·완전혼합 유동 반응기 / Native catalytic reacting flow and surface chemistry

Family / navigation ID: `production.reforming`

Import module: `h2physics.adapters.cantera_surface_reactor`; selected entry: `CanteraCatalyticSurfaceReactor.run_flowing_cstr`.

#### `h2physics.adapters.cantera_surface_reactor.CanteraCatalyticSurfaceReactor`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/cantera_surface_reactor.py#L424)

Closed finite gas and evolving adsorbate stock on a native ideal surface.

```python
CanteraCatalyticSurfaceReactor(source, mechanism_basis, *, surface_phase_name, gas_phase_name)
```

#### `h2physics.adapters.cantera_surface_reactor.CanteraCatalyticSurfaceReactor.run_flowing_cstr`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/cantera_surface_reactor.py#L646)

Run a native finite-feed, pressure-controlled, well-mixed reactor.

Feed and exhaust are actual Cantera flow devices. The thermal boundary
is required so the open-system energy balance includes native gas energy
dynamics. Port integrals use the requested output grid and trapezoidal
quadrature; refine that grid to reduce ledger quadrature error.

```python
run_flowing_cstr(self, initial, time_s, *, initial_coverages, surface_area_m2, gas_volume_m3, flow_boundary, thermal_boundary, clock_id, evidence_id, maximum_time_step_s, relative_tolerance, absolute_tolerance, site_fraction_tolerance, minimum_gas_mass_kg)
```

The source has no explicit return annotation; inspect its return statements and the domain manual. No return type is invented by this generator.

### Returned value / 반환값

`CatalyticFlowTrace`

This return contract was reviewed from the implementation; it is not an annotation present in the source signature.

### Related input/return records / 관련 입력·반환 객체

#### `h2physics.adapters.cantera_surface_reactor.CatalyticFlowTrace`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/cantera_surface_reactor.py#L139)

Native finite-flow catalytic CSTR history with sampled flux closure.

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `owner` | `object` | `required` |
| `clock_id` | `str` | `required` |
| `evidence_id` | `str` | `required` |
| `flow_boundary` | `CatalyticFlowBoundary` | `required` |
| `thermal_boundary` | `CatalyticThermalBoundary` | `required` |
| `surface_area_m2` | `float` | `required` |
| `gas_volume_m3` | `float` | `required` |
| `site_fraction_tolerance` | `float` | `required` |
| `points` | `tuple` | `required` |
| `native_gas` | `object` | `required` |
| `native_interface` | `object` | `required` |
| `native_reactor` | `object` | `required` |
| `native_surface` | `object` | `required` |
| `native_network` | `object` | `required` |
| `native_inlet_reservoir` | `object` | `required` |
| `native_outlet_reservoir` | `object` | `required` |
| `native_inlet_controller` | `object` | `required` |
| `native_outlet_controller` | `object` | `required` |
| `native_wall` | `object` | `required` |
| `native_thermal_reservoir` | `object` | `required` |

#### `h2physics.adapters.cantera_surface_reactor.CatalyticFlowBoundary`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/cantera_surface_reactor.py#L82)

Fixed gas feed and pressure-controlled discharge for a stirred reactor.

The inlet composition and thermodynamic state are held by a native Cantera
Reservoir. The native mass-flow controller fixes the feed rate; a native
PressureController discharges to the declared outlet pressure. This is a
stirred control volume, not a plug-flow or pressure-drop model.

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `evidence_id` | `str` | `required` |
| `feed_state` | `ReactiveState` | `required` |
| `feed_mass_flow_kg_s` | `float` | `required` |
| `outlet_pressure_pa` | `float` | `required` |
| `pressure_controller_kg_s_pa` | `float` | `required` |
| `mass_balance_tolerance_kg` | `float` | `required` |
| `element_balance_tolerance_mol` | `float` | `required` |
| `energy_balance_tolerance_j` | `float` | `required` |

#### `h2physics.adapters.cantera_surface_reactor.CatalyticThermalBoundary`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/cantera_surface_reactor.py#L62)

Fixed-temperature external wall coupled to a nonisothermal native reactor.

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `evidence_id` | `str` | `required` |
| `wall_temperature_k` | `float` | `required` |
| `area_m2` | `float` | `required` |
| `heat_transfer_w_m2_k` | `float` | `required` |
| `energy_residual_absolute_tolerance_j` | `float` | `required` |
| `energy_residual_relative_tolerance` | `float` | `1e-06` |


<a id="module-h2physics-adapters-cantera_multiphase-canteramultiphaseequilibrium-equilibrate"></a>

## 지정된 기체·고체 상의 다상 평형 / Declared gas/solid multiphase equilibrium

Family / navigation ID: `production.gasification`

Import module: `h2physics.adapters.cantera_multiphase`; selected entry: `CanteraMultiphaseEquilibrium.equilibrate`.

#### `h2physics.adapters.cantera_multiphase.CanteraMultiphaseEquilibrium`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/cantera_multiphase.py#L312)

```python
CanteraMultiphaseEquilibrium(phases, *, tolerances: MultiphaseTolerances=MultiphaseTolerances())
```

#### `h2physics.adapters.cantera_multiphase.CanteraMultiphaseEquilibrium.equilibrate`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/cantera_multiphase.py#L328)

```python
equilibrate(self, feed: MultiphaseFeed, *, constraint='TP', settings=MultiphaseSettings(), require_accepted=True)
```

The source has no explicit return annotation; inspect its return statements and the domain manual. No return type is invented by this generator.

### Returned value / 반환값

`MultiphaseEquilibriumResult`

This return contract was reviewed from the implementation; it is not an annotation present in the source signature.

### Related input/return records / 관련 입력·반환 객체

#### `h2physics.adapters.cantera_multiphase.MultiphaseEquilibriumResult`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/cantera_multiphase.py#L161)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `phases` | `tuple[EquilibriumPhase, ...]` | `required` |
| `feed` | `MultiphaseFeed` | `required` |
| `constraint` | `str` | `required` |
| `settings` | `MultiphaseSettings` | `required` |
| `tolerances` | `MultiphaseTolerances` | `required` |
| `species_keys` | `tuple[tuple[str, str], ...]` | `required` |
| `element_names` | `tuple[str, ...]` | `required` |
| `initial` | `MultiphaseSnapshot` | `required` |
| `final` | `MultiphaseSnapshot` | `required` |
| `heat_into_j` | `float` | `required` |
| `pressure_volume_work_out_j` | `float` | `required` |
| `energy_balance_residual_j` | `float` | `required` |
| `enthalpy_constraint_residual_j` | `float` | `required` |
| `mass_residual_kg` | `float` | `required` |
| `element_residual_mol` | `np.ndarray` | `required` |
| `chemical_audit` | `ChemicalPotentialAudit` | `required` |
| `native_mixture` | `Any` | `required` |
| `source_phases` | `tuple` | `required` |
| `owned_phases` | `tuple` | `required` |
| `phase_copy_audits` | `tuple` | `required` |
| `gates` | `Mapping[str, bool]` | `required` |
| `accepted` | `bool` | `required` |

#### `h2physics.adapters.cantera_multiphase.MultiphaseTolerances`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/cantera_multiphase.py#L111)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `element_absolute_mol` | `float` | `1e-09` |
| `mass_absolute_kg` | `float` | `1e-10` |
| `energy_absolute_j` | `float` | `1e-05` |
| `relative` | `float` | `1e-08` |
| `chemical_potential_over_rt` | `float` | `1e-05` |
| `active_species_relative` | `float` | `1e-10` |
| `active_species_absolute_mol` | `float` | `1e-14` |

#### `h2physics.adapters.cantera_multiphase.MultiphaseFeed`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/cantera_multiphase.py#L60)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `temperature_k` | `float` | `required` |
| `pressure_pa` | `float` | `required` |
| `species_mol` | `Mapping[str, Mapping[str, float]]` | `required` |
| `source_id` | `str` | `required` |
| `origin` | `Origin` | `required` |

#### `h2physics.adapters.cantera_multiphase.EquilibriumPhase`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/cantera_multiphase.py#L43)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `phase_id` | `str` | `required` |
| `role` | `str` | `required` |
| `factory` | `Callable` | `required` |
| `mechanism_basis` | `MechanismBasis` | `required` |
| `energy_reference_id` | `str` | `required` |
| `hydrogen_partition_id` | `str` | `required` |

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

#### `h2physics.adapters.cantera_multiphase.MultiphaseSnapshot`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/cantera_multiphase.py#L126)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `temperature_k` | `float` | `required` |
| `pressure_pa` | `float` | `required` |
| `species_mol` | `np.ndarray` | `required` |
| `phase_mol` | `np.ndarray` | `required` |
| `element_mol` | `np.ndarray` | `required` |
| `mass_kg` | `float` | `required` |
| `enthalpy_j` | `float` | `required` |
| `internal_energy_j` | `float` | `required` |
| `entropy_j_k` | `float` | `required` |
| `gibbs_energy_j` | `float` | `required` |
| `volume_m3` | `float` | `required` |
| `chemical_potentials_j_mol` | `np.ndarray` | `required` |

#### `h2physics.adapters.cantera_multiphase.ChemicalPotentialAudit`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/cantera_multiphase.py#L146)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `element_potentials_j_mol` | `Mapping[str, float]` | `required` |
| `populated_species_count` | `int` | `required` |
| `feasible_trace_species_count` | `int` | `required` |
| `active_amount_threshold_mol` | `float` | `required` |
| `maximum_populated_affinity_over_rt` | `float` | `required` |
| `absent_solid_affinity_over_rt` | `Mapping[str, float]` | `required` |
| `element_matrix_rank` | `int` | `required` |


<a id="module-h2physics-adapters-biological-qsdsanadm1digester-run"></a>

## 외부 ADM1 생물 반응·성분·수소 수지 / Native ADM1 biological component and hydrogen accounting

Family / navigation ID: `production.biological`

Import module: `h2physics.adapters.biological`; selected entry: `QsdSanAdm1Digester.run`.

#### `h2physics.adapters.biological.QsdSanAdm1Digester`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/biological.py#L250)

One native, constant-temperature, no-retention liquid/headspace CSTR.

``model`` and ``components`` are actual caller-owned QSDsan objects. Initial
liquid values include every native component in kg(native measured basis)/m3.
Feed values include every component except bulk H2O in the same units; native
WasteStream closes its water volume. Headspace inputs are mol/m3 of each of
native S_h2, S_ch4 and S_IC (CO2), never a guessed air or dry-gas fraction.
Construction explicitly sets the native process-global thermo package; do
not concurrently replace native settings during construction/integration.

```python
QsdSanAdm1Digester(native: QsdSanNative, *, components: Any, model: Any, geometry: Adm1Geometry, evidence: BiologicalEvidence, feed_volume_flow_m3_s: float, feed_concentrations_kg_m3: Mapping[str, float], initial_liquid_concentrations_kg_m3: Mapping[str, float], initial_headspace_mol_m3: Mapping[str, float], audit: BiologicalAudit)
```

#### `h2physics.adapters.biological.QsdSanAdm1Digester.run`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/biological.py#L340)

Run the native BDF solver; sample its dense output for a separate ledger.

No requested sample is a declaration of an internal accepted solver step.
The retained native OdeResult.t/y are the accepted-step history. Sampled
Simpson ledgers need a separate temporal refinement check for each use.

```python
run(self, *, start_time_s: float, end_time_s: float, sample_count: int, rtol: float=1e-08, atol: float=1e-11, max_step_s: float=3600) -> BiologicalRun
```

### Returned value / 반환값

`BiologicalRun`

### Related input/return records / 관련 입력·반환 객체

#### `h2physics.adapters.biological.QsdSanNative`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/biological.py#L221)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `qsdsan` | `Any` | `required` |
| `biosteam` | `Any` | `required` |
| `thermosteam` | `Any` | `required` |
| `versions` | `Mapping[str, str]` | `required` |
| `source_hashes` | `Mapping[str, str]` | `required` |

#### `h2physics.adapters.biological.Adm1Geometry`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/biological.py#L67)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `liquid_volume_m3` | `float` | `required` |
| `headspace_volume_m3` | `float` | `required` |
| `gas_pipe_coefficient_m3_s_pa` | `float` | `required` |
| `external_pressure_pa` | `float` | `required` |
| `temperature_k` | `float` | `required` |

#### `h2physics.adapters.biological.BiologicalEvidence`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/biological.py#L46)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `source_id` | `str` | `required` |
| `parameter_source_id` | `str` | `required` |
| `initial_state_source_id` | `str` | `required` |
| `feed_source_id` | `str` | `required` |
| `temperature_source_id` | `str` | `required` |
| `component_basis_id` | `str` | `required` |
| `clock_id` | `str` | `required` |
| `support_start_s` | `float` | `required` |
| `support_end_s` | `float` | `required` |

#### `h2physics.adapters.biological.BiologicalAudit`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/biological.py#L84)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `component_absolute_tolerance_kg` | `float` | `required` |
| `invariant_absolute_tolerance_kg` | `float` | `required` |
| `maximum_pressure_pa` | `float` | `required` |
| `relative_tolerance` | `float` | `1e-06` |

#### `h2physics.adapters.biological.BiologicalRun`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/biological.py#L123)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `evidence` | `BiologicalEvidence` | `required` |
| `points` | `tuple[BiologicalPoint, ...]` | `required` |
| `balance` | `BiologicalBalance` | `required` |
| `native_system` | `Any` | `required` |
| `native_reactor` | `Any` | `required` |
| `native_model` | `Any` | `required` |
| `native_components` | `Any` | `required` |
| `native_solution` | `Any` | `required` |
| `native_initial_state` | `tuple[float, ...]` | `required` |
| `native_versions` | `Mapping[str, str]` | `required` |
| `native_source_hashes` | `Mapping[str, str]` | `required` |
| `native_threshold_zeroing_kg_m3_or_kmol_m3` | `float` | `1e-16` |
| `energy_balance_available` | `bool` | `False` |
| `hydrogen_identity` | `str` | `'biochemical-molecular-H2-spin-unresolved'` |

#### `h2physics.adapters.biological.BiologicalPoint`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/biological.py#L97)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `time_s` | `float` | `required` |
| `pressure_pa` | `float` | `required` |
| `gas_outflow_m3_s` | `float` | `required` |
| `measured_inventories_kg` | `Mapping[str, float]` | `required` |
| `liquid_hydrogen_kg` | `float` | `required` |
| `headspace_hydrogen_kg` | `float` | `required` |
| `native_state` | `tuple[float, ...]` | `required` |

#### `h2physics.adapters.biological.BiologicalBalance`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/biological.py#L108)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `component_residuals_kg` | `Mapping[str, float]` | `required` |
| `invariant_residuals_kg` | `Mapping[str, float]` | `required` |
| `inlet_measured_kg` | `Mapping[str, float]` | `required` |
| `liquid_outlet_measured_kg` | `Mapping[str, float]` | `required` |
| `dry_gas_outlet_measured_kg` | `Mapping[str, float]` | `required` |
| `reaction_measured_kg` | `Mapping[str, float]` | `required` |
| `hydrogen_formed_kg` | `float` | `required` |
| `hydrogen_consumed_kg` | `float` | `required` |
| `exported_hydrogen_kg` | `float` | `required` |
| `hydrogen_residual_kg` | `float` | `required` |
| `exported_dry_hydrogen_mole_fraction` | `float &#124; None` | `required` |


<a id="module-h2physics-adapters-microbial_cell-finitemicrobialcell-run"></a>

## 미생물 전환·유한 재고·전극 반응 결합 / Finite microbial conversion and native electrode coupling

Family / navigation ID: `production.microbial_cell`

Import module: `h2physics.adapters.microbial_cell`; selected entry: `FiniteMicrobialCell.run`.

#### `h2physics.adapters.microbial_cell.FiniteMicrobialCell`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/microbial_cell.py#L626)

Isothermal fixed-P batch, caller microbiology and native cathode current.

Growth is applied first, then current-coupled catabolism. No aqueous pH,
methanogenesis, gas transfer, electrical capacitance or anode-potential law
is invented. Connected stages require a positive qualified catabolic rate;
explicitly disconnected stages require zero catabolic rate.

```python
FiniteMicrobialCell(cathode, catabolism, growth, kinetics, caloric, geometry, evidence, *, substrate_id, biomass_id, hydrogen_id, liquid_volume_m3, electron_equivalents_mol_per_mol, noncathode_losses, tolerances=ThermochemicalTolerances(), current_absolute_tolerance_a=1e-09, current_relative_tolerance=1e-08, maximum_root_iterations=100)
```

#### `h2physics.adapters.microbial_cell.FiniteMicrobialCell.run`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/microbial_cell.py#L1024)

```python
run(self, initial, stages)
```

The source has no explicit return annotation; inspect its return statements and the domain manual. No return type is invented by this generator.

### Returned value / 반환값

`MicrobialCellTrace`

This return contract was reviewed from the implementation; it is not an annotation present in the source signature.

### Related input/return records / 관련 입력·반환 객체

#### `h2physics.adapters.microbial_cell.MicrobialCellTrace`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/microbial_cell.py#L526)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `initial` | `ThermochemicalInventory` | `required` |
| `final` | `ThermochemicalInventory` | `required` |
| `steps` | `tuple[MicrobialCellStep, ...]` | `required` |
| `electron_equivalent_residual_mol` | `float` | `required` |
| `hydrogen_generated_mol` | `float` | `required` |
| `transferred_electrons_mol` | `float` | `required` |
| `electric_work_into_j` | `float` | `required` |
| `isothermal_heat_required_into_j` | `float` | `required` |
| `hydrogen_residual_mol` | `float` | `required` |
| `mass_residual_kg` | `float` | `required` |
| `enthalpy_residual_j` | `float` | `required` |
| `evidence` | `MicrobialCellEvidence` | `required` |
| `native_cathode` | `CanteraMicrobialCathode` | `required` |
| `kinetics` | `MicrobialKinetics` | `required` |
| `caloric_provider` | `object` | `required` |
| `kernel` | `FiniteThermochemicalCycle` | `required` |
| `geometry` | `StackGeometry` | `required` |
| `owner` | `'FiniteMicrobialCell'` | `required` |
| `status` | `str` | `STATUS` |

Computed properties: `admission`.

#### `h2physics.thermochemical.ThermochemicalInventory`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/thermochemical.py#L62)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `amounts_mol` | `Mapping[str, float]` | `required` |
| `temperature_k` | `float` | `required` |
| `pressure_pa` | `float` | `required` |
| `energy_basis_id` | `str` | `required` |

#### `h2physics.adapters.microbial_cell.MicrobialCellStep`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/microbial_cell.py#L502)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `stage` | `MicrobialCellStage` | `required` |
| `before` | `ThermochemicalInventory` | `required` |
| `after` | `ThermochemicalInventory` | `required` |
| `rate_state` | `MicrobialRateState` | `required` |
| `rates` | `MicrobialRates` | `required` |
| `cathode` | `CathodePoint &#124; None` | `required` |
| `native_root_result` | `object &#124; None` | `required` |
| `cathode_trials` | `tuple[CathodePoint, ...]` | `required` |
| `kernel_trace` | `object` | `required` |
| `current_a` | `float` | `required` |
| `applied_voltage_v` | `float` | `required` |
| `noncathode_loss_voltages_v` | `tuple` | `required` |
| `transferred_electrons_mol` | `float` | `required` |
| `hydrogen_generated_mol` | `float` | `required` |
| `biomass_generated_mol` | `float` | `required` |
| `electric_work_into_j` | `float` | `required` |
| `isothermal_heat_required_into_j` | `float` | `required` |
| `current_residual_a` | `float` | `required` |
| `electron_residual_mol` | `float` | `required` |
| `energy_residual_j` | `float` | `required` |

#### `h2physics.adapters.microbial_cell.MicrobialCellEvidence`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/microbial_cell.py#L243)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `process_id` | `str` | `required` |
| `stoichiometry_source_id` | `str` | `required` |
| `electron_equivalent_source_id` | `str` | `required` |
| `caloric_basis_id` | `str` | `required` |
| `electrode_reference_id` | `str` | `required` |
| `anode_potential_source_id` | `str` | `required` |
| `fixed_activity_boundary_id` | `str` | `required` |
| `isothermal_fixed_pressure_boundary_id` | `str` | `required` |
| `noncathode_losses_source_id` | `str` | `required` |
| `clock_id` | `str` | `required` |
| `origin` | `Origin` | `required` |

#### `h2physics.adapters.microbial_cell.MicrobialKinetics`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/microbial_cell.py#L181)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `callback` | `Callable` | `required` |
| `source_id` | `str` | `required` |
| `parameter_source_id` | `str` | `required` |
| `origin` | `Origin` | `required` |
| `parameters` | `Mapping[str, float]` | `required` |
| `temperature_bounds_k` | `tuple[float, float]` | `required` |
| `substrate_concentration_bounds_mol_m3` | `tuple[float, float]` | `required` |
| `biomass_concentration_bounds_mol_m3` | `tuple[float, float]` | `required` |
| `native_model` | `object &#124; None` | `None` |

#### `h2physics.electrochemistry.StackGeometry`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/electrochemistry.py#L154)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `series_cells` | `int` | `required` |
| `active_area_m2` | `float` | `required` |
| `hydrogen_molar_mass_kg_mol` | `float` | `required` |


<a id="module-h2physics-adapters-pv_electrolysis-pvelectrolysis-run"></a>

## 태양광 전기 운전점과 전해조·수신 재고 결합 / PV electrical load-line coupling to electrolysis and storage

Family / navigation ID: `production.energy_coupling`

Import module: `h2physics.adapters.pv_electrolysis`; selected entry: `PVElectrolysis.run`.

#### `h2physics.adapters.pv_electrolysis.PVElectrolysis`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/pv_electrolysis.py#L453)

Quasi-steady held source stages; finite chemistry and native EOS endpoints.

Water and oxygen use an explicit isothermal/isobaric additive-enthalpy
reference. Only the H2 receiver is a fixed-volume native fluid inventory.
Source pressure support is declared separately; free pressurization is not
inferred from a mass source. No time integrator is introduced.

```python
PVElectrolysis(native: NativePV, system, stack: HydrogenStack, reaction: StoichiometricReaction, caloric: MolarEnthalpyProvider, gas: HydrideGasThermodynamics, *, water_id: str, hydrogen_id: str, oxygen_id: str, pressure: ProductPressureBoundary, evidence: PVBoundaryEvidence, domain: DirectDCDomain, faradaic_efficiency: float=1.0)
```

#### `h2physics.adapters.pv_electrolysis.PVElectrolysis.run`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/pv_electrolysis.py#L754)

```python
run(self, stages, *, initial_amounts_mol: Mapping[str, float], receiver_volume_m3: float, receiver_temperature_k: float) -> PVElectrolysisTrace
```

### Returned value / 반환값

`PVElectrolysisTrace`

### Related input/return records / 관련 입력·반환 객체

#### `h2physics.adapters.pv_electrolysis.NativePV`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/pv_electrolysis.py#L64)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `package` | `Any` | `required` |
| `pvsystem` | `Any` | `required` |
| `pandas` | `Any` | `required` |
| `source_sha256` | `str` | `required` |
| `call_bindings` | `tuple` | `required` |

#### `h2physics.reactions.StoichiometricReaction`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/reactions.py#L41)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `identifier` | `str` | `required` |
| `species` | `tuple[ChemicalSpecies, ...]` | `required` |
| `coefficients` | `tuple[float, ...]` | `required` |

#### `h2physics.reactions.MolarEnthalpyProvider`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/reactions.py#L146)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `species` | `tuple[ChemicalSpecies, ...]` | `required` |
| `basis_id` | `str` | `required` |

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

#### `h2physics.adapters.pv_electrolysis.ProductPressureBoundary`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/pv_electrolysis.py#L122)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `source_pressure_pa` | `float` | `required` |
| `evidence_id` | `str` | `required` |
| `included_in_reaction_gibbs` | `bool` | `required` |

#### `h2physics.adapters.pv_electrolysis.PVBoundaryEvidence`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/pv_electrolysis.py#L104)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `source_id` | `str` | `required` |
| `parameter_source_id` | `str` | `required` |
| `irradiance_plane_id` | `str` | `required` |
| `cell_temperature_source_id` | `str` | `required` |
| `clock_id` | `str` | `required` |
| `origin` | `Origin` | `required` |

#### `h2physics.adapters.pv_electrolysis.DirectDCDomain`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/pv_electrolysis.py#L256)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `minimum_temperature_k` | `float` | `required` |
| `maximum_temperature_k` | `float` | `required` |
| `maximum_irradiance_w_m2` | `float` | `required` |
| `maximum_array_voltage_v` | `float` | `required` |
| `maximum_array_current_a` | `float` | `required` |
| `maximum_current_density_a_m2` | `float` | `required` |
| `minimum_receiver_pressure_pa` | `float` | `required` |
| `maximum_receiver_pressure_pa` | `float` | `required` |
| `minimum_receiver_mass_kg` | `float` | `1e-12` |
| `current_residual_a` | `float` | `1e-07` |
| `energy_residual_j` | `float` | `1e-05` |
| `enthalpy_match_j_mol` | `float` | `1e-06` |
| `mass_residual_kg` | `float` | `1e-10` |
| `root_current_density_atol` | `float` | `1e-09` |

#### `h2physics.adapters.pv_electrolysis.PVElectrolysisTrace`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/pv_electrolysis.py#L368)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `initial` | `PVInventoryState` | `required` |
| `final` | `PVInventoryState` | `required` |
| `steps` | `tuple[PVProductionStep, ...]` | `required` |
| `native_pv` | `NativePV` | `required` |
| `native_system` | `Any` | `required` |
| `stack` | `HydrogenStack` | `required` |
| `gas` | `HydrideGasThermodynamics` | `required` |
| `caloric_provider` | `Any` | `required` |
| `pressure_boundary` | `ProductPressureBoundary` | `required` |
| `evidence` | `PVBoundaryEvidence` | `required` |
| `pressure_work_resolved` | `bool` | `required` |
| `owner` | `'PVElectrolysis'` | `required` |
| `required_external_pressure_work_j` | `None` | `None` |
| `continuous_pressure_feedback` | `bool` | `False` |
| `thermal_utility_availability_solved` | `bool` | `False` |
| `full_plant_energy_closed` | `bool` | `False` |
| `water_oxygen_vessel_dynamics_solved` | `bool` | `False` |
| `energy_coordinate` | `str` | `'finite H-water/O2 at fixed source P + finite H2 receiver U at fixed V'` |
| `status` | `str` | `STATUS` |

Computed properties: `admission`.

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

#### `h2physics.adapters.pv_electrolysis.PVInventoryState`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/pv_electrolysis.py#L318)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `time_s` | `float` | `required` |
| `amounts_mol` | `Mapping[str, float]` | `required` |
| `receiver` | `ThermoState` | `required` |
| `receiver_internal_energy_j` | `float` | `required` |

#### `h2physics.adapters.pv_electrolysis.PVProductionStep`

[Source](https://github.com/lyullee/h2physics/blob/main/src/h2physics/adapters/pv_electrolysis.py#L336)

Declared fields (input records or returned state; **not a direction inferred from the name**):

| Field | Type | Default / construction rule |
| --- | --- | --- |
| `point` | `DirectDCPoint` | `required` |
| `before` | `PVInventoryState` | `required` |
| `after` | `PVInventoryState` | `required` |
| `native_conversion` | `Any` | `required` |
| `extent_mol_h2` | `float` | `required` |
| `electricity_j` | `float` | `required` |
| `pv_electricity_j` | `float` | `required` |
| `direct_dc_energy_residual_j` | `float` | `required` |
| `reaction_enthalpy_j` | `float` | `required` |
| `stack_heat_rejected_j` | `float` | `required` |
| `hydrogen_inlet_enthalpy_j` | `float` | `required` |
| `receiver_heat_into_j` | `float` | `required` |
| `nonreceiver_enthalpy_change_j` | `float` | `required` |
| `reference_energy_change_j` | `float` | `required` |
| `caloric_residual_j` | `float` | `required` |
| `mass_residual_kg` | `float` | `required` |
| `native_inlet_state` | `ThermoState` | `required` |
| `molar_enthalpies_j_mol` | `tuple[float, ...]` | `required` |


## Maintaining this guide / 갱신

Curated purposes and entry selection live in `scripts/readme_module_guide.py`. Run `python scripts/readme_module_guide.py` to regenerate both README blocks and this file. Run `python scripts/readme_module_guide.py --check` to reject stale output, unresolved callables or missing catalog IDs. The script parses source with the standard library, imports no physical engine and runs no calculation. Review purpose/units/limits against domain manuals when an API changes. It preserves authored scientific attribution and performs no automatic translation of external material.
