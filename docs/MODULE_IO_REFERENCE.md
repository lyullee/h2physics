# Module inputs and outputs / 모듈 입출력 전체 명세

[English README](../README.md#module-purposes-inputs-and-outputs) · [한국어 README](../README_KO.md#모듈별-목적입력출력) · [API contracts](API.md) · [All public symbols](PUBLIC_API_INDEX.md)

The README tables show each task, module, callable, key inputs and output. This index opens the full contracts by subject. Each subject file includes every selected constructor/method argument, type annotation, default, returned record and linked source. The guide maps all 82 catalog identifiers and additional levels/extensions; it is not a model-validation count.

README 표에서 목적·모듈·호출·주요 입력·출력을 먼저 고르고, 아래 분야별 명세에서 전체 파라미터를 확인하세요. 긴 한 파일에 내용을 모으지 않고 분야별로 나누어 탐색할 수 있게 했습니다. 반환 타입 주석이 없는 API는 구현에서 직접 확인한 반환 객체를 구분하여 표시합니다.

## Parameter meanings / 파라미터 읽기

| Input kind / 입력 유형 | What to supply / 넣는 값 | Examples / 예 |
| --- | --- | --- |
| Physical scalar / 물리 스칼라 | Value in the explicit unit; absolute/gauge, phase and sign follow the selected contract / 명시 단위·압력 기준·상·부호 유지 | `pressure_pa`, `temperature_k`, `mass_flow_kg_s` |
| Parameter record / 파라미터 객체 | Construct the named class with its required fields; preserve material/geometry identity / 필수 필드·물질·형상을 지정해 생성 | `DarcyGeometry`, `StackGeometry`, `RankineCycleSpec` |
| State or result / 상태·이전 결과 | Pass the retained object from the selected producer; inspect its basis and admission / 생산 모듈의 원래 객체·기준·허용 상태 전달 | `ThermoState`, `NozzleResult`, `IntervalMassSource` |
| Array / 배열 | Numeric values with explicit axis order and shape / 시간·공간·성분 축의 순서·형상 유지 | `time_s`, `initial_component_moles`, `initial_pressure_pa` |
| Function or law / 함수·구성식 | Caller callback with the documented signature and return unit / 정해진 호출 인자·반환 단위를 가진 사용자 함수 | `friction_law`, `thermochemistry`, `diffusivity_m2_s` |
| Provider or native model / 공급자·외부 모델 | Actual installed compatible engine object; installed separately / 별도 설치된 호환 엔진 객체 | CoolProp, Cantera, HyRAM+, SLABx-LH2 |
| Basis, evidence, clock / 기준·근거·시간축 | Real identities and compatible references; a label does not qualify an unknown condition / 실제 식별정보·호환 기준 지정 | `basis`, `evidence_id`, `clock_id` |
| Numerical control / 수치 제어 | Solver tolerance, mesh or step limit within the chosen model's domain / 모델 영역에 맞는 허용오차·격자·시간 간격 | `maximum_step_s`, `relative_tolerance`, `cell_count` |

SI suffixes include Pa, K, kg, mol, m, s, J and W plus compound units. Fluid-state pressure is absolute; differences, overpressure and residuals retain their stated difference basis. Do not assume a fractional input is a percentage, or an arbitrary provider's native units are SI. The full signature preserves positional-only `/`, keyword-only `*`, required arguments, optional defaults and `**kwargs`. An optional-looking default can still require another explicit input for the selected level.

단위 접미사와 함께 비율/백분율·몰/질량·H/H₂·기체/액체·오르토/파라·현열/생성열·동력 부호를 확인하세요. `field(init=False)`는 사용자가 넣는 값이 아니라 생성 후 계산되는 필드입니다. `self`·`cls`는 Python이 연결하며 사용자가 넘기지 않습니다.

## Working example / 입력에서 출력까지

Install `h2physics[thermo,hydraulics]`. The following uses CoolProp fluid properties and a selected steady frozen-property Darcy level. Geometry is an input record; friction is an injected function; the returned object exposes a mass flow and numerical residual. The geometry and operating point are demonstration inputs, not calibrated equipment data.

```python
from dataclasses import replace
from fluids.friction import friction_factor
from h2physics.hydraulics import DarcyGeometry, solve_darcy_flow
from h2physics.thermo import CoolPropProperties

properties = CoolPropProperties("Hydrogen")
state = properties.state_pt(pressure_pa=200_000.0, temperature_k=300.0)
base = DarcyGeometry(length_m=10.0, diameter_m=0.01, roughness_m=1e-6)
geometry = replace(base, diameter_m=0.02)  # customize the input record

result = solve_darcy_flow(
    geometry,
    density_kg_m3=state.density_kg_m3,
    viscosity_pa_s=state.viscosity_pa_s,
    driving_pressure_pa=1_000.0,
    friction_law=lambda re, e_d: friction_factor(re, e_d),
)
print(result.mass_flow_kg_s)        # kg/s
print(result.momentum_residual_pa)  # Pa
```

For data-driven laws, preserve the same callback arguments, units and domain, and attach the dataset/version/calibration evidence required by that model. This example selects a steady frozen-property pipe: it does not choose the transient, heated, network or two-phase level.

## Full contracts by subject / 분야별 전체 명세

| Subject / 분야 | Selected entry points / 호출 경로 | Full signatures and records / 전체 명세 |
| --- | --- | --- |
| Thermodynamic properties / 열역학·물성 | 5 | [thermo](modules/thermo.md) |
| Equipment and transfer / 설비·이송 | 24 | [equipment](modules/equipment.md) |
| Storage / 저장 | 13 | [storage](modules/storage.md) |
| Production and energy coupling / 생산·에너지 결합 | 10 | [production](modules/production.md) |
| Separation / 분리 | 2 | [separation](modules/separation.md) |
| Material transport and integrity / 재료 수송·건전성 | 7 | [materials](modules/materials.md) |
| Release sources / 방출원 | 5 | [release](modules/release.md) |
| Liquid pools / 액체 풀 | 1 | [surface](modules/surface.md) |
| Dispersion and enclosure transport / 확산·공간 내 이동 | 8 | [dispersion](modules/dispersion.md) |
| Combustion and conditional pressure / 연소·조건부 압력 | 15 | [combustion](modules/combustion.md) |
| Thermal, pressure and fragment effects / 열·압력·파편 영향 | 8 | [effects](modules/effects.md) |
| Facility composition and monitoring / 시설 조립·감시 | 7 | [facility](modules/facility.md) |
| Uncertainty and economics / 불확실성·경제성 | 3 | [research](modules/research.md) |
| 0.2.0 model extensions / 0.2.0 보완 모델 | 14 | [extension](modules/extension.md) |
| Shared Python connection objects / 공통 Python 연결 객체 | 7 | [support](modules/support.md) |

## Direct entry index / 개별 호출 바로가기

- [`h2physics.thermo.coolprop.CoolPropProperties.state_pt`](modules/thermo.md#module-h2physics-thermo-coolprop-coolpropproperties-state_pt) — CoolProp 순수 유체 상태·물성 계산 / Pure-fluid pressure/temperature flash with CoolProp
- [`h2physics.thermo.tables.QualifiedGasTable.state_pt`](modules/thermo.md#module-h2physics-thermo-tables-qualifiedgastable-state_pt) — 오차·영역 자격을 확인한 물성 테이블 조회 / Qualified native-backed property acceleration within its admitted domain
- [`h2physics.adapters.lh2dt_spin.Lh2dtOrthoPara.rate`](modules/thermo.md#module-h2physics-adapters-lh2dt_spin-lh2dtorthopara-rate) — 오르토·파라 전환율과 전환열 계산 / Ortho/para conversion rate and conversion heat
- [`h2physics.thermo.coolprop_mixture.CoolPropMixtureProperties.state_pt`](modules/thermo.md#module-h2physics-thermo-coolprop_mixture-coolpropmixtureproperties-state_pt) — 조성이 명시된 실제 혼합유체 상태 계산 / Fixed-composition real-fluid mixture flash
- [`h2physics.thermo.finite_mixture_inventory.run_finite_mixture_vu_intervals`](modules/thermo.md#module-h2physics-thermo-finite_mixture_inventory-run_finite_mixture_vu_intervals) — 유한 혼합물 성분·에너지 재고와 상태 변화 / Finite component and energy stocks with composition-dependent flashes
- [`h2physics.adapters.lh2dt_dynamics.Lh2dtDynamicEquipment.run`](modules/equipment.md#module-h2physics-adapters-lh2dt_dynamics-lh2dtdynamicequipment-run) — 기체·액화수소 탱크와 기화기 등의 유한 재고·벽 열응답 / Native warm-gas/LH2 tank and stored-device inventory dynamics
- [`h2physics.adapters.lh2dt_insulation.Lh2dtVacuumInsulation.evaluate`](modules/equipment.md#module-h2physics-adapters-lh2dt_insulation-lh2dtvacuuminsulation-evaluate) — 진공 단열 열유입과 벽 구역별 열 배분 / Vacuum insulation heat paths and wall allocation
- [`h2physics.hydraulics.solve_darcy_flow`](modules/equipment.md#module-h2physics-hydraulics-solve_darcy_flow) — 마찰식을 교체할 수 있는 정상 배관 유량·압력손실 / Steady frozen-property pipe flow with injected friction law
- [`h2physics.hydraulics.solve_isothermal_compressible_gas_flow`](modules/equipment.md#module-h2physics-hydraulics-solve_isothermal_compressible_gas_flow) — EOS를 명시한 등온 압축성 기체 배관 유동 / Steady isothermal compressible gas flow with explicit EOS selection
- [`h2physics.real_gas_linepack.RealGasLinepackState.advance`](modules/equipment.md#module-h2physics-real_gas_linepack-realgaslinepackstate-advance) — 실제 기체의 단일 셀 배관 저장량 변화 / One-cell real-gas pipeline inventory advance
- [`h2physics.isothermal_gas_pipe_network.IsothermalGasPipeNetwork.simulate`](modules/equipment.md#module-h2physics-isothermal_gas_pipe_network-isothermalgaspipenetwork-simulate) — 구간별 등온 배관망 재고·유량 과도응답 / Segmented quasi-steady isothermal network inventories
- [`h2physics.isothermal_pipe_waves.IsothermalPipeWaveModel.simulate`](modules/equipment.md#module-h2physics-isothermal_pipe_waves-isothermalpipewavemodel-simulate) — 단일 등온 배관 압력·운동량 파동 / Single-pipe isothermal pressure and momentum waves
- [`h2physics.isothermal_pipe_network_waves.IsothermalPipeNetworkWaveModel.simulate`](modules/equipment.md#module-h2physics-isothermal_pipe_network_waves-isothermalpipenetworkwavemodel-simulate) — 분기 등온 배관망과 접합부 파동 / Branched isothermal pipe waves and junctions
- [`h2physics.caloric_pipe_waves.CaloricPipeWaveModel.simulate`](modules/equipment.md#module-h2physics-caloric_pipe_waves-caloricpipewavemodel-simulate) — 질량·운동량·에너지를 푸는 단상 배관 파동 / Single-phase pipe mass/momentum/energy waves
- [`h2physics.caloric_pipe_network_waves.CaloricPipeNetworkWaveModel.simulate`](modules/equipment.md#module-h2physics-caloric_pipe_network_waves-caloricpipenetworkwavemodel-simulate) — 혼합 접합부를 포함한 에너지 배관망 파동 / Branched caloric waves with mixing junctions
- [`h2physics.caloric_pipe_finite_wall.simulate_caloric_pipe_with_finite_wall`](modules/equipment.md#module-h2physics-caloric_pipe_finite_wall-simulate_caloric_pipe_with_finite_wall) — 배관 기체와 유한 열용량 벽의 열응답 결합 / Pipe gas coupled to finite wall thermal storage
- [`h2physics.adapters.lh2dt_hydraulics.Lh2dtDarcyPipe.evaluate`](modules/equipment.md#module-h2physics-adapters-lh2dt_hydraulics-lh2dtdarcypipe-evaluate) — 단상·균질평형 이상 배관과 공통 Darcy 계산 연결 / Native state/HEM pipe binding to shared Darcy closure
- [`h2physics.adapters.lh2dt_equipment.Lh2dtSharedValve.evaluate`](modules/equipment.md#module-h2physics-adapters-lh2dt_equipment-lh2dtsharedvalve-evaluate) — 공통 노즐을 이용한 두 포트 밸브 감압 / Two-port throttling using the shared nozzle
- [`h2physics.adapters.lh2dt_valve_actuator.FiniteStrokeValve.run`](modules/equipment.md#module-h2physics-adapters-lh2dt_valve_actuator-finitestrokevalve-run) — 사용자 유량 맵에 따른 밸브 개도 과도응답 / Finite-stroke actuation with a caller-supplied flow map
- [`h2physics.adapters.lh2dt_relief.Lh2dtReliefTankDriver.run`](modules/equipment.md#module-h2physics-adapters-lh2dt_relief-lh2dtrelieftankdriver-run) — 탱크 안전밸브 개방·재폐쇄와 방출 재고 계산 / Finite-tank relief opening/reseat with inventory accounting
- [`h2physics.adapters.lh2dt_pump_operation.FiniteSpeedPump.run`](modules/equipment.md#module-h2physics-adapters-lh2dt_pump_operation-finitespeedpump-run) — 펌프 속도 명령·운전 맵·NPSH 조건 검사 / Pump speed commands, map and NPSH admission
- [`h2physics.adapters.lh2dt_compressor.Lh2dtCompressionTrain.evaluate`](modules/equipment.md#module-h2physics-adapters-lh2dt_compressor-lh2dtcompressiontrain-evaluate) — 다단 기체 압축과 지정 중간 냉각의 동력·열량 / Gas compression stages and prescribed intercooling
- [`h2physics.adapters.compressor_map.MappedCompressor.evaluate`](modules/equipment.md#module-h2physics-adapters-compressor_map-mappedcompressor-evaluate) — 사용자 압축기 맵 기반 운전영역 검사 / Caller-map operating-envelope admission
- [`h2physics.adapters.compressor_anti_surge.CompressorAntiSurgeGuard.evaluate`](modules/equipment.md#module-h2physics-adapters-compressor_anti_surge-compressorantisurgeguard-evaluate) — 운전점과 서지선 간 정적 여유 검사 / Static source-bound surge-margin screening
- [`h2physics.adapters.counterflow_heat_exchanger.CounterflowHeatExchanger.solve`](modules/equipment.md#module-h2physics-adapters-counterflow_heat_exchanger-counterflowheatexchanger-solve) — 정상 공간 분할 대향류 열교환 / Steady spatial counterflow heat exchange
- [`h2physics.adapters.lh2dt_heat_exchanger.Lh2dtFiniteHeatExchanger.run`](modules/equipment.md#module-h2physics-adapters-lh2dt_heat_exchanger-lh2dtfiniteheatexchanger-run) — 양측 유체·벽의 유한 열저장·열교환 과도응답 / Finite two-side fluid/wall thermal storage
- [`h2physics.adapters.lh2dt_reliquefier.Lh2dtSteadyReliquefier.evaluate`](modules/equipment.md#module-h2physics-adapters-lh2dt_reliquefier-lh2dtsteadyreliquefier-evaluate) — 냉각 용량 제한을 고려한 포화 냉각·액상 생산 / Capacity-limited saturation cooling and liquid production
- [`h2physics.adapters.lh2dt_vent.Lh2dtVentStack.evaluate`](modules/equipment.md#module-h2physics-adapters-lh2dt_vent-lh2dtventstack-evaluate) — 저마하 벤트 유량·압력손실·열전달 / Low-Mach vent hydraulics and enthalpy transfer
- [`h2physics.adapters.lh2dt_instrumentation.Lh2dtTransmitter.run`](modules/equipment.md#module-h2physics-adapters-lh2dt_instrumentation-lh2dttransmitter-run) — 단위·위치가 명시된 계측기 지연 응답 / Native held-input transmitter response
- [`h2physics.adapters.cryo_compressed.CryoCompressedStorage.run`](modules/storage.md#module-h2physics-adapters-cryo_compressed-cryocompressedstorage-run) — 고압 극저온 저장·벽 열응답·릴리프 / Finite cryogenic high-pressure storage and relief
- [`h2physics.adapters.finite_adsorption_vessel.FiniteAdsorptionVessel.snapshot`](modules/storage.md#module-h2physics-adapters-finite_adsorption_vessel-finiteadsorptionvessel-snapshot) — 자유 기체와 절대 흡착량을 합친 저장 용기 재고 / Free gas plus absolute-uptake vessel inventory
- [`h2physics.adsorption.ExtendedLangmuirIsotherm.equilibrium`](modules/storage.md#module-h2physics-adsorption-extendedlangmuirisotherm-equilibrium) — 다성분 경쟁 Langmuir 평형 흡착·미분값 / Competitive multicomponent Langmuir uptake and derivatives
- [`h2physics.storage.product_delivery.AdsorptionProductMassFlow`](modules/storage.md#module-h2physics-storage-product_delivery-adsorptionproductmassflow) — 흡착 용기 인도 몰수를 질량·구간 평균 유량으로 변환 / Accepted mole delivery converted to mass and interval-mean flow
- [`h2physics.adapters.psa.PsaDynaBed.snapshot`](modules/storage.md#module-h2physics-adapters-psa-psadynabed-snapshot) — 외부 흡착층의 온도·흡착량·성분 재고 읽기 / Native thermal adsorption-bed states and inventories
- [`h2physics.storage.hydride.VanthoffPlateau.fugacity_pa`](modules/storage.md#module-h2physics-storage-hydride-vanthoffplateau-fugacity_pa) — 수소화물 평형 압력·기울기·이력 효과 / Hydride equilibrium plateau, slope and hysteresis
- [`h2physics.storage.finite_hydride.FiniteHydrideBed.simulate`](modules/storage.md#module-h2physics-storage-finite_hydride-finitehydridebed-simulate) — 유한 기체·고체 재고와 수소화 반응·열응답 / Finite gas/solid storage, uptake kinetics and heat
- [`h2physics.storage.hydride_compressor.HydrideThermalCompressor.run`](modules/storage.md#module-h2physics-storage-hydride_compressor-hydridethermalcompressor-run) — 유한 공급·수신 탱크 사이 열구동 수소화물 압축 / Thermally cycled bed between finite source and receiver vessels
- [`h2physics.adapters.carrier_conversion.FiniteCarrierConversion.run`](modules/storage.md#module-h2physics-adapters-carrier_conversion-finitecarrierconversion-run) — LOHC·암모니아의 지정 전환량·유한 재고·인출 / Prescribed finite LOHC/ammonia conversion and takeoff
- [`h2physics.storage.solid_reaction.FiniteSolidReactionReactor.run`](modules/storage.md#module-h2physics-storage-solid_reaction-finitesolidreactionreactor-run) — 고체 분해·가수분해의 유한 공급·반응·열수지 / Finite solid decomposition/hydrolysis with supplies and heat
- [`h2physics.storage.microsphere.MicrosphereStorage.simulate`](modules/storage.md#module-h2physics-storage-microsphere-microspherestorage-simulate) — 미소구 내부 기체와 구형 벽 수소 이동 / Finite gas cavity coupled to spherical wall transport
- [`h2physics.adapters.underground_storage.Uh2scUndergroundStorage.run`](modules/storage.md#module-h2physics-adapters-underground_storage-uh2scundergroundstorage-run) — 외부 지하 공동·습윤 기체·암반 모델과 수지 검사 / Native cavern/wet-gas/rock model with independent ledgers
- [`h2physics.storage.porous_reservoir.PorousReservoir.run`](modules/storage.md#module-h2physics-storage-porous_reservoir-porousreservoir-run) — 방사형 등온 단상 다공성 저장소 주입·인출 / Radial isothermal single-phase Darcy storage
- [`h2physics.electrochemistry.HydrogenStack.evaluate`](modules/production.md#module-h2physics-electrochemistry-hydrogenstack-evaluate) — 전해조·연료전지 공통 분극·수소 생성/소모·전력 / Shared polarization, Faraday production/consumption and power
- [`h2physics.electrochemical_thermal.FiniteThermalStack.run`](modules/production.md#module-h2physics-electrochemical_thermal-finitethermalstack-run) — 냉각재 경계를 명시한 유한 스택 열응답 / Finite stack thermal states with declared coolant boundary
- [`h2physics.adapters.cantera_fuel_cell.run_cantera_synchronized_fuel_cell`](modules/production.md#module-h2physics-adapters-cantera_fuel_cell-run_cantera_synchronized_fuel_cell) — 기체 채널·반응·스택 열응답의 동기화 계산 / Native H2/O2/water-vapor channels and stack thermal dynamics
- [`h2physics.photochemistry.photon_hydrogen_rate`](modules/production.md#module-h2physics-photochemistry-photon_hydrogen_rate) — 분광 광자수·흡수·양자수율에 따른 수소 생산율 / Spectral photon budget, absorption and declared quantum yield
- [`h2physics.thermochemical.FiniteThermochemicalCycle.run`](modules/production.md#module-h2physics-thermochemical-finitethermochemicalcycle-run) — 단계별 열화학 전환량·성분 재고·필요 열량 / Finite staged reaction extents, stocks and caloric duties
- [`h2physics.adapters.cantera_surface_reactor.CanteraCatalyticSurfaceReactor.run_flowing_cstr`](modules/production.md#module-h2physics-adapters-cantera_surface_reactor-canteracatalyticsurfacereactor-run_flowing_cstr) — 외부 촉매 표면반응·완전혼합 유동 반응기 / Native catalytic reacting flow and surface chemistry
- [`h2physics.adapters.cantera_multiphase.CanteraMultiphaseEquilibrium.equilibrate`](modules/production.md#module-h2physics-adapters-cantera_multiphase-canteramultiphaseequilibrium-equilibrate) — 지정된 기체·고체 상의 다상 평형 / Declared gas/solid multiphase equilibrium
- [`h2physics.adapters.biological.QsdSanAdm1Digester.run`](modules/production.md#module-h2physics-adapters-biological-qsdsanadm1digester-run) — 외부 ADM1 생물 반응·성분·수소 수지 / Native ADM1 biological component and hydrogen accounting
- [`h2physics.adapters.microbial_cell.FiniteMicrobialCell.run`](modules/production.md#module-h2physics-adapters-microbial_cell-finitemicrobialcell-run) — 미생물 전환·유한 재고·전극 반응 결합 / Finite microbial conversion and native electrode coupling
- [`h2physics.adapters.pv_electrolysis.PVElectrolysis.run`](modules/production.md#module-h2physics-adapters-pv_electrolysis-pvelectrolysis-run) — 태양광 전기 운전점과 전해조·수신 재고 결합 / PV electrical load-line coupling to electrolysis and storage
- [`h2physics.adapters.psa_cycle.PsaDynaCycle.run`](modules/separation.md#module-h2physics-adapters-psa_cycle-psadynacycle-run) — 외부 PSA 운전 주기·재고·제품 순도·회수량 / Native scheduled PSA cycle inventories and product accounting
- [`h2physics.adapters.cantera_membrane.CanteraDustyGasTransport.flux`](modules/separation.md#module-h2physics-adapters-cantera_membrane-canteradustygastransport-flux) — 다성분 다공성 막 투과 유속 / Multicomponent porous-membrane transport
- [`h2physics.materials.transport.PowerLawSolubility.concentration_mol_m3`](modules/materials.md#module-h2physics-materials-transport-powerlawsolubility-concentration_mol_m3) — 수소 퓨가시티에 따른 명시 운반체 기준 용해 농도 / Declared-carrier concentration from hydrogen fugacity
- [`h2physics.materials.transport.steady_permeation`](modules/materials.md#module-h2physics-materials-transport-steady_permeation) — 용해도·확산계수를 이용한 정상 벽 투과량 / Steady wall permeation from solubility and diffusivity
- [`h2physics.materials.finite_volume.DiffusionDomain.simulate`](modules/materials.md#module-h2physics-materials-finite_volume-diffusiondomain-simulate) — 이동·포획 수소의 보존형 유한체적 확산 / Conservative mobile/trapped hydrogen transport
- [`h2physics.adapters.fracture_fatigue.integrate_fatigue_crack`](modules/materials.md#module-h2physics-adapters-fracture_fatigue-integrate_fatigue_crack) — 외부 수소 영향 피로 균열 성장식 적분 / Native hydrogen-assisted fatigue crack-growth law integration
- [`h2physics.materials.elastic_cylinder.lame_stress_field`](modules/materials.md#module-h2physics-materials-elastic_cylinder-lame_stress_field) — 두꺼운 원통의 탄성 압력 응력장 / Elastic thick-cylinder pressure stress
- [`h2physics.materials.radial_heat.radial_cylinder_heat_history`](modules/materials.md#module-h2physics-materials-radial_heat-radial_cylinder_heat_history) — 원통 고체 벽의 방사형 열전도 이력 / Radial solid-wall thermal history
- [`h2physics.materials.radial_thermoelastic.radial_thermoelastic_cylinder`](modules/materials.md#module-h2physics-materials-radial_thermoelastic-radial_thermoelastic_cylinder) — 방사형 온도 구배에 따른 탄성 응력 / Radial thermal-gradient elastic stress
- [`h2physics.release.HomogeneousIsentropicNozzle.solve`](modules/release.md#module-h2physics-release-homogeneousisentropicnozzle-solve) — 기체·액체·균질평형 이상 방출을 푸는 공통 EOS 노즐 / One EOS-based nozzle for gas, liquid and homogeneous-equilibrium two-phase discharge
- [`h2physics.adapters.lh2dt.Lh2dtBulkNozzleOutflow.sample`](modules/release.md#module-h2physics-adapters-lh2dt-lh2dtbulknozzleoutflow-sample) — 외부 탱크 상태의 노즐 방출 샘플·재고 적분은 외부 소유 / Native bulk-state nozzle outflow sample; inventory integration remains native
- [`h2physics.adapters.degali.expand_nozzle_gas`](modules/release.md#module-h2physics-adapters-degali-expand_nozzle_gas) — 노즐 기체를 대기압 방출 평면으로 팽창 / Nozzle gas expanded to an ambient-pressure source plane
- [`h2physics.adapters.droplet_transport.SaturatedParcelFlight.run`](modules/release.md#module-h2physics-adapters-droplet_transport-saturatedparcelflight-run) — 포화 구형 액적의 비행·항력·증발 / Saturated spherical parcel flight, drag and evaporation
- [`h2physics.adapters.droplet_impact.FiniteSurfaceImpact.run`](modules/release.md#module-h2physics-adapters-droplet_impact-finitesurfaceimpact-run) — 유한 액적 충돌·표면 열수지·침착 액체 / Finite liquid impact, surface heat and deposited batches
- [`h2physics.adapters.pool.NativeDynamicPool.run`](modules/surface.md#module-h2physics-adapters-pool-nativedynamicpool-run) — 외부 액체 풀 퍼짐·저장량·구간별 증발 방출원 / Native pool spreading/storage and finite vapor-source intervals
- [`h2physics.dispersion.run_preferred_gas_dispersion`](modules/dispersion.md#module-h2physics-dispersion-run_preferred_gas_dispersion) — 고압 기체 수소 우선 확산 경로: HyRAM+ / Preferred high-pressure gas route: HyRAM+
- [`h2physics.dispersion.run_preferred_lh2_dispersion`](modules/dispersion.md#module-h2physics-dispersion-run_preferred_lh2_dispersion) — 액화수소 유래 증기운 우선 확산 경로: SLABx-LH2 / Preferred LH2-origin vapor-cloud route: SLABx-LH2
- [`h2physics.adapters.hyram_finite_source_snapshots.run_hyram_finite_source_snapshots`](modules/dispersion.md#module-h2physics-adapters-hyram_finite_source_snapshots-run_hyram_finite_source_snapshots) — 고정 유량 독립 스냅숏 인터페이스·호환 수신기 필요 / Independent fixed-flow snapshot contract; compatible receiver required
- [`h2physics.adapters.cantera_volume.CanteraOpenGasVolume.run`](modules/dispersion.md#module-h2physics-adapters-cantera_volume-canteraopengasvolume-run) — 유한 완전혼합 비반응 기체 공간의 압력·열응답 / Finite well-mixed nonreacting volume and thermal pressure
- [`h2physics.buoyant_layer.run_two_vent_hydrogen_layer`](modules/dispersion.md#module-h2physics-buoyant_layer-run_two_vent_hydrogen_layer) — 두 통풍구 공간의 부력 상부 수소층 축적 / Buoyant upper-layer accumulation with two vents
- [`h2physics.compartment_network.simulate_hydrogen_compartment_network`](modules/dispersion.md#module-h2physics-compartment_network-simulate_hydrogen_compartment_network) — 지정 몰 이동량에 따른 고정 상태 구획 간 수소 혼합 / Fixed-state room mixing with prescribed balanced molar transfers
- [`h2physics.adapters.obstacle_dispersion.CFDMesh`](modules/dispersion.md#module-h2physics-adapters-obstacle_dispersion-cfdmesh) — 외부 FDS 장애물 확산 사례의 격자·형상 정의 / External FDS obstacle-case mesh and geometry contract
- [`h2physics.adapters.obstacle_dispersion.run_obstacle_dispersion`](modules/dispersion.md#module-h2physics-adapters-obstacle_dispersion-run_obstacle_dispersion) — 별도 설치 FDS로 지정 장애물 확산 사례 실행 / Run a declared obstacle case with a separately installed FDS executable
- [`h2physics.adapters.cantera.CanteraGas.equilibrium`](modules/combustion.md#module-h2physics-adapters-cantera-canteragas-equilibrium) — 외부 HP/UV 단열 반응 평형 / Native HP/UV adiabatic reacting equilibrium
- [`h2physics.adapters.cantera.CanteraGas.closed_reactor`](modules/combustion.md#module-h2physics-adapters-cantera-canteragas-closed_reactor) — 외부 밀폐 반응기의 시간별 반응·상태 계산 / Native closed reacting-vessel time integration
- [`h2physics.adapters.cantera.CanteraGas.free_flame`](modules/combustion.md#module-h2physics-adapters-cantera-canteragas-free_flame) — 외부 1차원 예혼합 층류 화염속도 / Native one-dimensional premixed laminar flame
- [`h2physics.combustion.counterflow.solve_counterflow_diffusion_flame`](modules/combustion.md#module-h2physics-combustion-counterflow-solve_counterflow_diffusion_flame) — 외부 대향류 비예혼합 화염 / Native opposed-flow nonpremixed flame
- [`h2physics.adapters.hyram_flame.run_hyram_flame`](modules/combustion.md#module-h2physics-adapters-hyram_flame-run_hyram_flame) — 조건부 외부 정상 제트 화염·복사와 허용영역 검사 / Conditional native steady jet flame and radiation gates
- [`h2physics.adapters.pool_fire.FinitePoolFire.run`](modules/combustion.md#module-h2physics-adapters-pool_fire-finitepoolfire-run) — 연소율·점화가 주어진 조건부 유한 풀 연소 / Conditional finite pool burning with supplied flux and ignition
- [`h2physics.adapters.flash_front.run_material_front`](modules/combustion.md#module-h2physics-adapters-flash_front-run_material_front) — 조건부 물질 경로 화염 전파·유한 구획 연소 / Conditional material-path front and finite parcel burn
- [`h2physics.combustion.closed_charge_engine.run_closed_charge_engine_segment`](modules/combustion.md#module-h2physics-combustion-closed_charge_engine-run_closed_charge_engine_segment) — 피스톤 체적·일을 포함한 밀폐 충전 엔진 구간 / Native closed-charge engine interval with piston work
- [`h2physics.combustion.open_cylinder_engine.run_open_cylinder_segment`](modules/combustion.md#module-h2physics-combustion-open_cylinder_engine-run_open_cylinder_segment) — 밸브·유입출 경계를 명시한 개방 실린더 구간 / Native open-cylinder interval with declared valves and ports
- [`h2physics.combustion.open_brayton.run_open_cycle_brayton`](modules/combustion.md#module-h2physics-combustion-open_brayton-run_open_cycle_brayton) — 외부 반응 평형을 이용한 수소 Brayton 기준 사이클 / Native-equilibrium hydrogen Brayton reference
- [`h2physics.combustion.steady_map_solver.solve_steady_map_operating_point`](modules/combustion.md#module-h2physics-combustion-steady_map_solver-solve_steady_map_operating_point) — 기기 맵·유량·축 동력 잔차를 맞추는 운전점 해석 / Bounded component-map operating-point solve
- [`h2physics.combustion.shaft_transient.integrate_shaft_transient`](modules/combustion.md#module-h2physics-combustion-shaft_transient-integrate_shaft_transient) — 지정 터빈·압축기 동력에 따른 단축 회전 에너지 응답 / One-shaft energy dynamics with supplied turbine/compressor powers
- [`h2physics.adapters.hyram_overpressure.HyRAMBauwensOverpressure.evaluate`](modules/combustion.md#module-h2physics-adapters-hyram_overpressure-hyrambauwensoverpressure-evaluate) — 참여 수소 에너지를 입력한 조건부 비구속 최고 과압 / Conditional unconfined peak from supplied participating energy
- [`h2physics.adapters.detonation.SDToolboxDetonation.cj`](modules/combustion.md#module-h2physics-adapters-detonation-sdtoolboxdetonation-cj) — 외부 평형 CJ 폭굉 종단 상태 / Native equilibrium CJ detonation endpoint
- [`h2physics.adapters.detonation.SDToolboxDetonation.frozen_shock`](modules/combustion.md#module-h2physics-adapters-detonation-sdtoolboxdetonation-frozen_shock) — 외부 동결 이상기체 정상 충격파 / Native frozen ideal-gas normal shock
- [`h2physics.adapters.pifira_heat.PifiraClosedVesselHeat.run`](modules/effects.md#module-h2physics-adapters-pifira_heat-pifiraclosedvesselheat-run) — 고정 질량 이상 압력 이력에서 내용물 열유입 역산 / Contents heat inferred from fixed-mass two-phase pressure history
- [`h2physics.adapters.vessel_failure.HelprVesselFailure.predict`](modules/effects.md#module-h2physics-adapters-vessel_failure-helprvesselfailure-predict) — 결함·재료·압력 이력에 따른 조건부 파손 개시 / Conditional flaw/material pressure-path failure initiation
- [`h2physics.fragment_trajectory.integrate_fragment_flight`](modules/effects.md#module-h2physics-fragment_trajectory-integrate_fragment_flight) — 초기 상태가 주어진 파편의 궤적·충돌 / Conditional fragment flight from supplied launch state
- [`h2physics.fragment_energy_bound.bound_fragment_speed_from_elastic_energy`](modules/effects.md#module-h2physics-fragment_energy_bound-bound_fragment_speed_from_elastic_energy) — 탄성 저장 에너지로 계산한 지정 파편 속도 상한 / Elastic strain-energy ceiling on a chosen fragment mass
- [`h2physics.adapters.hyram_exposure.HyRAMExposure.thermal_response`](modules/effects.md#module-h2physics-adapters-hyram_exposure-hyramexposure-thermal_response) — 지정 입사 열 노출에 대한 조건부 반응 / Conditional response to supplied incident thermal exposure
- [`h2physics.adapters.hyram_exposure.HyRAMExposure.pressure_response`](modules/effects.md#module-h2physics-adapters-hyram_exposure-hyramexposure-pressure_response) — 지정 압력 피크·충격량에 대한 조건부 반응 / Conditional response to supplied pressure peak/impulse
- [`h2physics.adapters.oxygen_deficiency.CanteraOxygenRoom.run`](modules/effects.md#module-h2physics-adapters-oxygen_deficiency-canteraoxygenroom-run) — 외부 균질 산소 이동·농도 응답 / Native homogeneous oxygen transport and criterion evaluation
- [`h2physics.adapters.jos3_thermal.JOS3ThermalResponse.run`](modules/effects.md#module-h2physics-adapters-jos3_thermal-jos3thermalresponse-run) — 별도 선택한 일반 공기 조건 인체 열응답 / Separately selected ordinary-air human thermal response
- [`h2physics.adapters.lh2dt_supply.assemble_lh2dt_supply`](modules/facility.md#module-h2physics-adapters-lh2dt_supply-assemble_lh2dt_supply) — 유한 탱크·펌프·배관·기화기·출구를 조립 / Compose finite tank, pump, line, vaporizer and outlet
- [`h2physics.adapters.facility_protection.execute_protected`](modules/facility.md#module-h2physics-adapters-facility_protection-execute_protected) — 동일 물리 운전 사례에 지정 보호·차단 조치 적용 / Execute prescribed protection against the same physical operation
- [`h2physics.adapters.conditional_risk.conditional_risk`](modules/facility.md#module-h2physics-adapters-conditional_risk-conditional_risk) — 빈도·피해 근거를 입력한 조건부 분기 위험도 / Conditional branch risk with supplied frequency and harm evidence
- [`h2physics.adapters.gas_detection.evaluate_first_order_concentration_sensor`](modules/facility.md#module-h2physics-adapters-gas_detection-evaluate_first_order_concentration_sensor) — 농도 센서 1차 지연 응답 / First-order concentration sensor response
- [`h2physics.adapters.gas_detection.evaluate_concentration_alarm_voting`](modules/facility.md#module-h2physics-adapters-gas_detection-evaluate_concentration_alarm_voting) — 같은 시간축의 k-of-n 농도 경보 투표 / Same-clock k-of-n alarm voting
- [`h2physics.adapters.process_monitoring.NativeResidualMonitor.evaluate`](modules/facility.md#module-h2physics-adapters-process_monitoring-nativeresidualmonitor-evaluate) — 외부 인과적 PCA 잔차 감시 / Native causal PCA residual monitoring
- [`h2physics.detector_reliability.evaluate_kofn_detector_reliability`](modules/facility.md#module-h2physics-detector_reliability-evaluate_kofn_detector_reliability) — 사용자 확률에 따른 k-of-n 검출 실패 집계 / Caller-probability k-of-n detector fail-to-alarm aggregation
- [`h2physics.uncertainty.propagate`](modules/research.md#module-h2physics-uncertainty-propagate) — 실패 사례를 보존하는 파라미터 불확실성 전파 / Parameter-sample propagation with retained failed cases
- [`h2physics.uncertainty.sobol_sensitivity`](modules/research.md#module-h2physics-uncertainty-sobol_sensitivity) — 독립 입력의 Sobol 민감도 분석 / Independent-input Sobol sensitivity analysis
- [`h2physics.adapters.hydrogen_economics.evaluate_hydrogen_economics`](modules/research.md#module-h2physics-adapters-hydrogen_economics-evaluate_hydrogen_economics) — 연간 제품·금융 기준이 명시된 수소 현금흐름 경제성 / Native annual hydrogen DCF with explicit financial/product basis
- [`h2physics.adapters.indoor_release.run_hyram_indoor_release`](modules/extension.md#module-h2physics-adapters-indoor_release-run_hyram_indoor_release) — 외부 실내 수소 축적·점화 지연별 조건부 압력 피크 / Native indoor accumulation and ignition-delay conditional peaks
- [`h2physics.combustion_screening.screen_combustion`](modules/extension.md#module-h2physics-combustion_screening-screen_combustion) — 근거·영역이 명시된 화염가속·DDT 필요조건 선별 / Evidence/domain-bound necessary conditions for FA and DDT
- [`h2physics.mechanical_rupture.isentropic_expansion_energy`](modules/extension.md#module-h2physics-mechanical_rupture-isentropic_expansion_energy) — CoolProp 유한 균질 등엔트로피 순팽창 일 / CoolProp finite homogeneous isentropic net expansion work
- [`h2physics.mechanical_rupture.mechanical_rupture_load`](modules/extension.md#module-h2physics-mechanical_rupture-mechanical_rupture_load) — 기계적 에너지 배분과 지정 압력 공급자 연결 / Explicit mechanical energy allocation and supplied pressure provider
- [`h2physics.materials.sdof.solve_linear_sdof`](modules/extension.md#module-h2physics-materials-sdof-solve_linear_sdof) — 실제 압력 시간 이력에 따른 선형 구조 동응답 / Linear structural response to an actual pressure-time history
- [`h2physics.adapters.thermal_cycles.solve_rankine_cycle`](modules/extension.md#module-h2physics-adapters-thermal_cycles-solve_rankine_cycle) — 실제 TESPy Rankine 네트워크·제1법칙 수지 / Actual TESPy Rankine network and first-law audit
- [`h2physics.adapters.thermal_cycles.analyze_rankine_exergy`](modules/extension.md#module-h2physics-adapters-thermal_cycles-analyze_rankine_exergy) — 실제 ExerPy를 이용한 원래 네트워크 물리 엑서지 분석 / Actual ExerPy physical-exergy analysis of the retained network
- [`h2physics.adapters.liquefaction_cycle.solve_hydrogen_liquefaction`](modules/extension.md#module-h2physics-adapters-liquefaction_cycle-solve_hydrogen_liquefaction) — 수소 압축·외부 헬륨 냉각·JT·기액 분리 기준 사이클 / H2 compression/external-helium cooling/JT/separation reference
- [`h2physics.storage.redox_equilibrium.TwoSolidRedoxEquilibrium.equilibrate`](modules/extension.md#module-h2physics-storage-redox_equilibrium-twosolidredoxequilibrium-equilibrate) — 허용 두 고체 상에 한정한 외부 산화환원 평형 / Restricted two-solid native redox equilibrium
- [`h2physics.electrocatalyst_metrics.corrected_overpotential_v`](modules/extension.md#module-h2physics-electrocatalyst_metrics-corrected_overpotential_v) — 전극 측정값의 부호가 명시된 iR 보정 / Signed iR correction of electrode measurements
- [`h2physics.electrocatalyst_metrics.fit_tafel`](modules/extension.md#module-h2physics-electrocatalyst_metrics-fit_tafel) — 지정 구간 Tafel 기울기·교환전류 밀도 추정 / Explicit-window Tafel slope and exchange-current fit
- [`h2physics.electrocatalyst_metrics.compare_product_to_charge`](modules/extension.md#module-h2physics-electrocatalyst_metrics-compare_product_to_charge) — 시간 정렬된 생성물·전하의 Faraday 효율 비교 / Time-aligned product/charge Faradaic-efficiency comparison
- [`h2physics.electrocatalyst_metrics.turnover_frequency_from_product`](modules/extension.md#module-h2physics-electrocatalyst_metrics-turnover_frequency_from_product) — 생성물·활성점 몰수 기준 회전빈도 / Product-based site-mole turnover frequency
- [`h2physics.adapters.par_device.PARDevice.integrate`](modules/extension.md#module-h2physics-adapters-par_device-pardevice-integrate) — 용량식 기반 PAR 유동·수소 제거·촉매 열저장 / Capacity-law PAR gas flow, hydrogen removal and catalyst heat storage
- [`h2physics.core.ThermoState`](modules/support.md#module-h2physics-core-thermostate) — 공통 유체 상태·물성 기준 객체 / Shared fluid/state/reference contract
- [`h2physics.core.TimeSeries`](modules/support.md#module-h2physics-core-timeseries) — 열 이름·단위·시간축을 가진 시계열 객체 / Named time-series columns, units and clocks
- [`h2physics.reactions.StoichiometricReaction.convert`](modules/support.md#module-h2physics-reactions-stoichiometricreaction-convert) — 공통 유한 화학양론 전환 수지 / Shared finite stoichiometric conversion accounting
- [`h2physics.sources.IntervalMassSource`](modules/support.md#module-h2physics-sources-intervalmasssource) — 구간 적분 질량을 유지하는 유한 방출원 객체 / Conservative finite-window mass-source contract
- [`h2physics.pressure_loads.PressureTimeHistory`](modules/support.md#module-h2physics-pressure_loads-pressuretimehistory) — 하나의 기계적 압력 하중에 대한 실제 시간 이력 / One mechanical pressure load versus physical time
- [`h2physics.facility_continuity.FacilityContinuityAudit.audit`](modules/support.md#module-h2physics-facility_continuity-facilitycontinuityaudit-audit) — 샘플별 시설 노드 질량·에너지 연속성 검사 / Sampled node mass and energy continuity
- [`h2physics.model_selection.ModelRegistry.select`](modules/support.md#module-h2physics-model_selection-modelregistry-select) — 대체 경로 없이 분야·수준·공급자를 명시 선택 / Exact family/level/provider selection without fallback

## Maintenance / 유지 관리

`python scripts/readme_module_guide.py` regenerates the two README blocks, this index and 15 subject files from curated purposes and actual source AST. `python scripts/readme_module_guide.py --check` checks coverage, symbol resolution and output freshness. It does not import scientific providers or run models. API inventories describe interfaces, not new test/experimental evidence. See [model selection](MODEL_SELECTION.md), [domain manuals](PUBLIC_API_INDEX.md), [dependency installation](DEPENDENCIES.md) and [recorded limitations](PROGRESS.md).
