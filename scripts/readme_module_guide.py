"""Maintain bilingual README module tables and source-derived Python I/O contracts.

Run without importing any scientific package. --check detects stale generated text.
The curated rows select useful entry points; catalog IDs are checked against source.
They describe use and do not assign new implementation or validation statuses.
"""

from __future__ import annotations

import argparse
import ast
import re
from pathlib import Path

# id | module below h2physics | callable | purpose (English) | purpose (Korean)
# A catalog family can have several rows for distinct selectable levels.
ROWS = """
thermo.pure_fluid|thermo.coolprop|CoolPropProperties.state_pt|Pure-fluid pressure/temperature flash with CoolProp|CoolProp 순수 유체 상태·물성 계산
thermo.acceleration|thermo.tables|QualifiedGasTable.state_pt|Qualified native-backed property acceleration within its admitted domain|오차·영역 자격을 확인한 물성 테이블 조회
thermo.spin|adapters.lh2dt_spin|Lh2dtOrthoPara.rate|Ortho/para conversion rate and conversion heat|오르토·파라 전환율과 전환열 계산
thermo.mixtures|thermo.coolprop_mixture|CoolPropMixtureProperties.state_pt|Fixed-composition real-fluid mixture flash|조성이 명시된 실제 혼합유체 상태 계산
thermo.mixtures|thermo.finite_mixture_inventory|run_finite_mixture_vu_intervals|Finite component and energy stocks with composition-dependent flashes|유한 혼합물 성분·에너지 재고와 상태 변화
equipment.gas_tank,equipment.lh2_tank,equipment.vaporizer|adapters.lh2dt_dynamics|Lh2dtDynamicEquipment.run|Native warm-gas/LH2 tank and stored-device inventory dynamics|기체·액화수소 탱크와 기화기 등의 유한 재고·벽 열응답
equipment.insulation|adapters.lh2dt_insulation|Lh2dtVacuumInsulation.evaluate|Vacuum insulation heat paths and wall allocation|진공 단열 열유입과 벽 구역별 열 배분
equipment.gas_pipe|hydraulics|solve_darcy_flow|Steady frozen-property pipe flow with injected friction law|마찰식을 교체할 수 있는 정상 배관 유량·압력손실
equipment.gas_pipe|hydraulics|solve_isothermal_compressible_gas_flow|Steady isothermal compressible gas flow with explicit EOS selection|EOS를 명시한 등온 압축성 기체 배관 유동
equipment.gas_pipe|real_gas_linepack|RealGasLinepackState.advance|One-cell real-gas pipeline inventory advance|실제 기체의 단일 셀 배관 저장량 변화
equipment.gas_pipe|isothermal_gas_pipe_network|IsothermalGasPipeNetwork.simulate|Segmented quasi-steady isothermal network inventories|구간별 등온 배관망 재고·유량 과도응답
equipment.gas_pipe|isothermal_pipe_waves|IsothermalPipeWaveModel.simulate|Single-pipe isothermal pressure and momentum waves|단일 등온 배관 압력·운동량 파동
equipment.gas_pipe|isothermal_pipe_network_waves|IsothermalPipeNetworkWaveModel.simulate|Branched isothermal pipe waves and junctions|분기 등온 배관망과 접합부 파동
equipment.gas_pipe|caloric_pipe_waves|CaloricPipeWaveModel.simulate|Single-phase pipe mass/momentum/energy waves|질량·운동량·에너지를 푸는 단상 배관 파동
equipment.gas_pipe|caloric_pipe_network_waves|CaloricPipeNetworkWaveModel.simulate|Branched caloric waves with mixing junctions|혼합 접합부를 포함한 에너지 배관망 파동
equipment.gas_pipe|caloric_pipe_finite_wall|simulate_caloric_pipe_with_finite_wall|Pipe gas coupled to finite wall thermal storage|배관 기체와 유한 열용량 벽의 열응답 결합
equipment.two_phase_pipe|adapters.lh2dt_hydraulics|Lh2dtDarcyPipe.evaluate|Native state/HEM pipe binding to shared Darcy closure|단상·균질평형 이상 배관과 공통 Darcy 계산 연결
equipment.valve|adapters.lh2dt_equipment|Lh2dtSharedValve.evaluate|Two-port throttling using the shared nozzle|공통 노즐을 이용한 두 포트 밸브 감압
equipment.valve|adapters.lh2dt_valve_actuator|FiniteStrokeValve.run|Finite-stroke actuation with a caller-supplied flow map|사용자 유량 맵에 따른 밸브 개도 과도응답
equipment.relief|adapters.lh2dt_relief|Lh2dtReliefTankDriver.run|Finite-tank relief opening/reseat with inventory accounting|탱크 안전밸브 개방·재폐쇄와 방출 재고 계산
equipment.pump|adapters.lh2dt_pump_operation|FiniteSpeedPump.run|Pump speed commands, map and NPSH admission|펌프 속도 명령·운전 맵·NPSH 조건 검사
equipment.compressor|adapters.lh2dt_compressor|Lh2dtCompressionTrain.evaluate|Gas compression stages and prescribed intercooling|다단 기체 압축과 지정 중간 냉각의 동력·열량
equipment.compressor|adapters.compressor_map|MappedCompressor.evaluate|Caller-map operating-envelope admission|사용자 압축기 맵 기반 운전영역 검사
equipment.compressor|adapters.compressor_anti_surge|CompressorAntiSurgeGuard.evaluate|Static source-bound surge-margin screening|운전점과 서지선 간 정적 여유 검사
equipment.heat_exchanger|adapters.counterflow_heat_exchanger|CounterflowHeatExchanger.solve|Steady spatial counterflow heat exchange|정상 공간 분할 대향류 열교환
equipment.heat_exchanger|adapters.lh2dt_heat_exchanger|Lh2dtFiniteHeatExchanger.run|Finite two-side fluid/wall thermal storage|양측 유체·벽의 유한 열저장·열교환 과도응답
equipment.reliquefier|adapters.lh2dt_reliquefier|Lh2dtSteadyReliquefier.evaluate|Capacity-limited saturation cooling and liquid production|냉각 용량 제한을 고려한 포화 냉각·액상 생산
equipment.vent|adapters.lh2dt_vent|Lh2dtVentStack.evaluate|Low-Mach vent hydraulics and enthalpy transfer|저마하 벤트 유량·압력손실·열전달
equipment.instrument|adapters.lh2dt_instrumentation|Lh2dtTransmitter.run|Native held-input transmitter response|단위·위치가 명시된 계측기 지연 응답
storage.cryo_compressed|adapters.cryo_compressed|CryoCompressedStorage.run|Finite cryogenic high-pressure storage and relief|고압 극저온 저장·벽 열응답·릴리프
storage.adsorption|adapters.finite_adsorption_vessel|FiniteAdsorptionVessel.snapshot|Free gas plus absolute-uptake vessel inventory|자유 기체와 절대 흡착량을 합친 저장 용기 재고
storage.extended_langmuir|adsorption|ExtendedLangmuirIsotherm.equilibrium|Competitive multicomponent Langmuir uptake and derivatives|다성분 경쟁 Langmuir 평형 흡착·미분값
storage.adsorption_delivery_mass_flow|storage.product_delivery|AdsorptionProductMassFlow|Accepted mole delivery converted to mass and interval-mean flow|흡착 용기 인도 몰수를 질량·구간 평균 유량으로 변환
storage.adsorption_thermal|adapters.psa|PsaDynaBed.snapshot|Native thermal adsorption-bed states and inventories|외부 흡착층의 온도·흡착량·성분 재고 읽기
storage.hydride_equilibrium|storage.hydride|VanthoffPlateau.fugacity_pa|Hydride equilibrium plateau, slope and hysteresis|수소화물 평형 압력·기울기·이력 효과
storage.hydride_dynamic|storage.finite_hydride|FiniteHydrideBed.simulate|Finite gas/solid storage, uptake kinetics and heat|유한 기체·고체 재고와 수소화 반응·열응답
storage.hydride_compressor|storage.hydride_compressor|HydrideThermalCompressor.run|Thermally cycled bed between finite source and receiver vessels|유한 공급·수신 탱크 사이 열구동 수소화물 압축
storage.carrier_reaction|adapters.carrier_conversion|FiniteCarrierConversion.run|Prescribed finite LOHC/ammonia conversion and takeoff|LOHC·암모니아의 지정 전환량·유한 재고·인출
storage.solid_reaction|storage.solid_reaction|FiniteSolidReactionReactor.run|Finite solid decomposition/hydrolysis with supplies and heat|고체 분해·가수분해의 유한 공급·반응·열수지
storage.microsphere|storage.microsphere|MicrosphereStorage.simulate|Finite gas cavity coupled to spherical wall transport|미소구 내부 기체와 구형 벽 수소 이동
storage.underground|adapters.underground_storage|Uh2scUndergroundStorage.run|Native cavern/wet-gas/rock model with independent ledgers|외부 지하 공동·습윤 기체·암반 모델과 수지 검사
storage.porous_reservoir|storage.porous_reservoir|PorousReservoir.run|Radial isothermal single-phase Darcy storage|방사형 등온 단상 다공성 저장소 주입·인출
production.electrolyzer,production.fuel_cell|electrochemistry|HydrogenStack.evaluate|Shared polarization, Faraday production/consumption and power|전해조·연료전지 공통 분극·수소 생성/소모·전력
production.electrolyzer|electrochemical_thermal|FiniteThermalStack.run|Finite stack thermal states with declared coolant boundary|냉각재 경계를 명시한 유한 스택 열응답
production.fuel_cell|adapters.cantera_fuel_cell|run_cantera_synchronized_fuel_cell|Native H2/O2/water-vapor channels and stack thermal dynamics|기체 채널·반응·스택 열응답의 동기화 계산
production.photo|photochemistry|photon_hydrogen_rate|Spectral photon budget, absorption and declared quantum yield|분광 광자수·흡수·양자수율에 따른 수소 생산율
production.thermochemical|thermochemical|FiniteThermochemicalCycle.run|Finite staged reaction extents, stocks and caloric duties|단계별 열화학 전환량·성분 재고·필요 열량
production.reforming|adapters.cantera_surface_reactor|CanteraCatalyticSurfaceReactor.run_flowing_cstr|Native catalytic reacting flow and surface chemistry|외부 촉매 표면반응·완전혼합 유동 반응기
production.gasification|adapters.cantera_multiphase|CanteraMultiphaseEquilibrium.equilibrate|Declared gas/solid multiphase equilibrium|지정된 기체·고체 상의 다상 평형
production.biological|adapters.biological|QsdSanAdm1Digester.run|Native ADM1 biological component and hydrogen accounting|외부 ADM1 생물 반응·성분·수소 수지
production.microbial_cell|adapters.microbial_cell|FiniteMicrobialCell.run|Finite microbial conversion and native electrode coupling|미생물 전환·유한 재고·전극 반응 결합
production.energy_coupling|adapters.pv_electrolysis|PVElectrolysis.run|PV electrical load-line coupling to electrolysis and storage|태양광 전기 운전점과 전해조·수신 재고 결합
separation.psa|adapters.psa_cycle|PsaDynaCycle.run|Native scheduled PSA cycle inventories and product accounting|외부 PSA 운전 주기·재고·제품 순도·회수량
separation.membrane|adapters.cantera_membrane|CanteraDustyGasTransport.flux|Multicomponent porous-membrane transport|다성분 다공성 막 투과 유속
materials.solubility|materials.transport|PowerLawSolubility.concentration_mol_m3|Declared-carrier concentration from hydrogen fugacity|수소 퓨가시티에 따른 명시 운반체 기준 용해 농도
materials.permeation|materials.transport|steady_permeation|Steady wall permeation from solubility and diffusivity|용해도·확산계수를 이용한 정상 벽 투과량
materials.diffusion|materials.finite_volume|DiffusionDomain.simulate|Conservative mobile/trapped hydrogen transport|이동·포획 수소의 보존형 유한체적 확산
materials.integrity|adapters.fracture_fatigue|integrate_fatigue_crack|Native hydrogen-assisted fatigue crack-growth law integration|외부 수소 영향 피로 균열 성장식 적분
materials.integrity|materials.elastic_cylinder|lame_stress_field|Elastic thick-cylinder pressure stress|두꺼운 원통의 탄성 압력 응력장
materials.integrity|materials.radial_heat|radial_cylinder_heat_history|Radial solid-wall thermal history|원통 고체 벽의 방사형 열전도 이력
materials.integrity|materials.radial_thermoelastic|radial_thermoelastic_cylinder|Radial thermal-gradient elastic stress|방사형 온도 구배에 따른 탄성 응력
release.gas,release.liquid,release.two_phase|release|HomogeneousIsentropicNozzle.solve|One EOS-based nozzle for gas, liquid and homogeneous-equilibrium two-phase discharge|기체·액체·균질평형 이상 방출을 푸는 공통 EOS 노즐
release.blowdown|adapters.lh2dt|Lh2dtBulkNozzleOutflow.sample|Native bulk-state nozzle outflow sample; inventory integration remains native|외부 탱크 상태의 노즐 방출 샘플·재고 적분은 외부 소유
release.near_field|adapters.degali|expand_nozzle_gas|Nozzle gas expanded to an ambient-pressure source plane|노즐 기체를 대기압 방출 평면으로 팽창
release.droplets|adapters.droplet_transport|SaturatedParcelFlight.run|Saturated spherical parcel flight, drag and evaporation|포화 구형 액적의 비행·항력·증발
release.impact|adapters.droplet_impact|FiniteSurfaceImpact.run|Finite liquid impact, surface heat and deposited batches|유한 액적 충돌·표면 열수지·침착 액체
surface.pool|adapters.pool|NativeDynamicPool.run|Native pool spreading/storage and finite vapor-source intervals|외부 액체 풀 퍼짐·저장량·구간별 증발 방출원
dispersion.outdoor|dispersion|run_preferred_gas_dispersion|Preferred high-pressure gas route: HyRAM+|고압 기체 수소 우선 확산 경로: HyRAM+
dispersion.outdoor|dispersion|run_preferred_lh2_dispersion|Preferred LH2-origin vapor-cloud route: SLABx-LH2|액화수소 유래 증기운 우선 확산 경로: SLABx-LH2
dispersion.fixed_flow_snapshots|adapters.hyram_finite_source_snapshots|run_hyram_finite_source_snapshots|Independent fixed-flow snapshot contract; compatible receiver required|고정 유량 독립 스냅숏 인터페이스·호환 수신기 필요
dispersion.enclosure|adapters.cantera_volume|CanteraOpenGasVolume.run|Finite well-mixed nonreacting volume and thermal pressure|유한 완전혼합 비반응 기체 공간의 압력·열응답
dispersion.buoyant_layer|buoyant_layer|run_two_vent_hydrogen_layer|Buoyant upper-layer accumulation with two vents|두 통풍구 공간의 부력 상부 수소층 축적
dispersion.compartment_network|compartment_network|simulate_hydrogen_compartment_network|Fixed-state room mixing with prescribed balanced molar transfers|지정 몰 이동량에 따른 고정 상태 구획 간 수소 혼합
dispersion.obstacle|adapters.obstacle_dispersion|CFDMesh|External FDS obstacle-case mesh and geometry contract|외부 FDS 장애물 확산 사례의 격자·형상 정의
dispersion.obstacle|adapters.obstacle_dispersion|run_obstacle_dispersion|Run a declared obstacle case with a separately installed FDS executable|별도 설치 FDS로 지정 장애물 확산 사례 실행
combustion.equilibrium|adapters.cantera|CanteraGas.equilibrium|Native HP/UV adiabatic reacting equilibrium|외부 HP/UV 단열 반응 평형
combustion.kinetics|adapters.cantera|CanteraGas.closed_reactor|Native closed reacting-vessel time integration|외부 밀폐 반응기의 시간별 반응·상태 계산
combustion.laminar_flame|adapters.cantera|CanteraGas.free_flame|Native one-dimensional premixed laminar flame|외부 1차원 예혼합 층류 화염속도
combustion.laminar_flame|combustion.counterflow|solve_counterflow_diffusion_flame|Native opposed-flow nonpremixed flame|외부 대향류 비예혼합 화염
combustion.jet_fire|adapters.hyram_flame|run_hyram_flame|Conditional native steady jet flame and radiation gates|조건부 외부 정상 제트 화염·복사와 허용영역 검사
combustion.pool_fire|adapters.pool_fire|FinitePoolFire.run|Conditional finite pool burning with supplied flux and ignition|연소율·점화가 주어진 조건부 유한 풀 연소
combustion.flash_fire|adapters.flash_front|run_material_front|Conditional material-path front and finite parcel burn|조건부 물질 경로 화염 전파·유한 구획 연소
combustion.piston_engine|combustion.closed_charge_engine|run_closed_charge_engine_segment|Native closed-charge engine interval with piston work|피스톤 체적·일을 포함한 밀폐 충전 엔진 구간
combustion.piston_engine|combustion.open_cylinder_engine|run_open_cylinder_segment|Native open-cylinder interval with declared valves and ports|밸브·유입출 경계를 명시한 개방 실린더 구간
combustion.gas_turbine|combustion.open_brayton|run_open_cycle_brayton|Native-equilibrium hydrogen Brayton reference|외부 반응 평형을 이용한 수소 Brayton 기준 사이클
combustion.gas_turbine|combustion.steady_map_solver|solve_steady_map_operating_point|Bounded component-map operating-point solve|기기 맵·유량·축 동력 잔차를 맞추는 운전점 해석
combustion.gas_turbine|combustion.shaft_transient|integrate_shaft_transient|One-shaft energy dynamics with supplied turbine/compressor powers|지정 터빈·압축기 동력에 따른 단축 회전 에너지 응답
combustion.overpressure|adapters.hyram_overpressure|HyRAMBauwensOverpressure.evaluate|Conditional unconfined peak from supplied participating energy|참여 수소 에너지를 입력한 조건부 비구속 최고 과압
combustion.detonation|adapters.detonation|SDToolboxDetonation.cj|Native equilibrium CJ detonation endpoint|외부 평형 CJ 폭굉 종단 상태
combustion.detonation|adapters.detonation|SDToolboxDetonation.frozen_shock|Native frozen ideal-gas normal shock|외부 동결 이상기체 정상 충격파
effects.heat_input|adapters.pifira_heat|PifiraClosedVesselHeat.run|Contents heat inferred from fixed-mass two-phase pressure history|고정 질량 이상 압력 이력에서 내용물 열유입 역산
effects.rupture|adapters.vessel_failure|HelprVesselFailure.predict|Conditional flaw/material pressure-path failure initiation|결함·재료·압력 이력에 따른 조건부 파손 개시
effects.fragment_trajectory|fragment_trajectory|integrate_fragment_flight|Conditional fragment flight from supplied launch state|초기 상태가 주어진 파편의 궤적·충돌
effects.fragment_trajectory|fragment_energy_bound|bound_fragment_speed_from_elastic_energy|Elastic strain-energy ceiling on a chosen fragment mass|탄성 저장 에너지로 계산한 지정 파편 속도 상한
effects.exposure|adapters.hyram_exposure|HyRAMExposure.thermal_response|Conditional response to supplied incident thermal exposure|지정 입사 열 노출에 대한 조건부 반응
effects.exposure|adapters.hyram_exposure|HyRAMExposure.pressure_response|Conditional response to supplied pressure peak/impulse|지정 압력 피크·충격량에 대한 조건부 반응
effects.cryogenic|adapters.oxygen_deficiency|CanteraOxygenRoom.run|Native homogeneous oxygen transport and criterion evaluation|외부 균질 산소 이동·농도 응답
effects.cryogenic|adapters.jos3_thermal|JOS3ThermalResponse.run|Separately selected ordinary-air human thermal response|별도 선택한 일반 공기 조건 인체 열응답
facility.network|adapters.lh2dt_supply|assemble_lh2dt_supply|Compose finite tank, pump, line, vaporizer and outlet|유한 탱크·펌프·배관·기화기·출구를 조립
facility.isolation|adapters.facility_protection|execute_protected|Execute prescribed protection against the same physical operation|동일 물리 운전 사례에 지정 보호·차단 조치 적용
facility.risk|adapters.conditional_risk|conditional_risk|Conditional branch risk with supplied frequency and harm evidence|빈도·피해 근거를 입력한 조건부 분기 위험도
facility.monitoring|adapters.gas_detection|evaluate_first_order_concentration_sensor|First-order concentration sensor response|농도 센서 1차 지연 응답
facility.monitoring|adapters.gas_detection|evaluate_concentration_alarm_voting|Same-clock k-of-n alarm voting|같은 시간축의 k-of-n 농도 경보 투표
facility.monitoring|adapters.process_monitoring|NativeResidualMonitor.evaluate|Native causal PCA residual monitoring|외부 인과적 PCA 잔차 감시
facility.detector_reliability|detector_reliability|evaluate_kofn_detector_reliability|Caller-probability k-of-n detector fail-to-alarm aggregation|사용자 확률에 따른 k-of-n 검출 실패 집계
research.uncertainty|uncertainty|propagate|Parameter-sample propagation with retained failed cases|실패 사례를 보존하는 파라미터 불확실성 전파
research.uncertainty|uncertainty|sobol_sensitivity|Independent-input Sobol sensitivity analysis|독립 입력의 Sobol 민감도 분석
research.economics|adapters.hydrogen_economics|evaluate_hydrogen_economics|Native annual hydrogen DCF with explicit financial/product basis|연간 제품·금융 기준이 명시된 수소 현금흐름 경제성
extension.indoor|adapters.indoor_release|run_hyram_indoor_release|Native indoor accumulation and ignition-delay conditional peaks|외부 실내 수소 축적·점화 지연별 조건부 압력 피크
extension.screening|combustion_screening|screen_combustion|Evidence/domain-bound necessary conditions for FA and DDT|근거·영역이 명시된 화염가속·DDT 필요조건 선별
extension.mechanical_energy|mechanical_rupture|isentropic_expansion_energy|CoolProp finite homogeneous isentropic net expansion work|CoolProp 유한 균질 등엔트로피 순팽창 일
extension.mechanical_load|mechanical_rupture|mechanical_rupture_load|Explicit mechanical energy allocation and supplied pressure provider|기계적 에너지 배분과 지정 압력 공급자 연결
extension.sdof|materials.sdof|solve_linear_sdof|Linear structural response to an actual pressure-time history|실제 압력 시간 이력에 따른 선형 구조 동응답
extension.rankine|adapters.thermal_cycles|solve_rankine_cycle|Actual TESPy Rankine network and first-law audit|실제 TESPy Rankine 네트워크·제1법칙 수지
extension.exergy|adapters.thermal_cycles|analyze_rankine_exergy|Actual ExerPy physical-exergy analysis of the retained network|실제 ExerPy를 이용한 원래 네트워크 물리 엑서지 분석
extension.liquefaction|adapters.liquefaction_cycle|solve_hydrogen_liquefaction|H2 compression/external-helium cooling/JT/separation reference|수소 압축·외부 헬륨 냉각·JT·기액 분리 기준 사이클
extension.redox|storage.redox_equilibrium|TwoSolidRedoxEquilibrium.equilibrate|Restricted two-solid native redox equilibrium|허용 두 고체 상에 한정한 외부 산화환원 평형
extension.electrode_ir|electrocatalyst_metrics|corrected_overpotential_v|Signed iR correction of electrode measurements|전극 측정값의 부호가 명시된 iR 보정
extension.electrode_tafel|electrocatalyst_metrics|fit_tafel|Explicit-window Tafel slope and exchange-current fit|지정 구간 Tafel 기울기·교환전류 밀도 추정
extension.electrode_fe|electrocatalyst_metrics|compare_product_to_charge|Time-aligned product/charge Faradaic-efficiency comparison|시간 정렬된 생성물·전하의 Faraday 효율 비교
extension.electrode_tof|electrocatalyst_metrics|turnover_frequency_from_product|Product-based site-mole turnover frequency|생성물·활성점 몰수 기준 회전빈도
extension.par|adapters.par_device|PARDevice.integrate|Capacity-law PAR gas flow, hydrogen removal and catalyst heat storage|용량식 기반 PAR 유동·수소 제거·촉매 열저장
support.state|core|ThermoState|Shared fluid/state/reference contract|공통 유체 상태·물성 기준 객체
support.series|core|TimeSeries|Named time-series columns, units and clocks|열 이름·단위·시간축을 가진 시계열 객체
support.reaction|reactions|StoichiometricReaction.convert|Shared finite stoichiometric conversion accounting|공통 유한 화학양론 전환 수지
support.sources|sources|IntervalMassSource|Conservative finite-window mass-source contract|구간 적분 질량을 유지하는 유한 방출원 객체
support.pressure_history|pressure_loads|PressureTimeHistory|One mechanical pressure load versus physical time|하나의 기계적 압력 하중에 대한 실제 시간 이력
support.continuity|facility_continuity|FacilityContinuityAudit.audit|Sampled node mass and energy continuity|샘플별 시설 노드 질량·에너지 연속성 검사
support.selection|model_selection|ModelRegistry.select|Exact family/level/provider selection without fallback|대체 경로 없이 분야·수준·공급자를 명시 선택
"""

BASE = "https://github.com/lyullee/h2physics/blob/main/"
START = "<!-- BEGIN MODULE GUIDE -->"
END = "<!-- END MODULE GUIDE -->"
GROUPS = {
    "thermo": ("Thermodynamic properties", "열역학·물성"),
    "equipment": ("Equipment and transfer", "설비·이송"),
    "storage": ("Storage", "저장"),
    "production": ("Production and energy coupling", "생산·에너지 결합"),
    "separation": ("Separation", "분리"),
    "materials": ("Material transport and integrity", "재료 수송·건전성"),
    "release": ("Release sources", "방출원"),
    "surface": ("Liquid pools", "액체 풀"),
    "dispersion": ("Dispersion and enclosure transport", "확산·공간 내 이동"),
    "combustion": ("Combustion and conditional pressure", "연소·조건부 압력"),
    "effects": ("Thermal, pressure and fragment effects", "열·압력·파편 영향"),
    "facility": ("Facility composition and monitoring", "시설 조립·감시"),
    "research": ("Uncertainty and economics", "불확실성·경제성"),
    "extension": ("0.2.0 model extensions", "0.2.0 보완 모델"),
    "support": ("Shared Python connection objects", "공통 Python 연결 객체"),
}

# Reviewed return contracts for unannotated source. These are documentation,
# not new type annotations or results of executing native providers.
# Qualified class names are checked by the generator against their real source.
RETURNS = {
    "adapters.lh2dt_spin:Lh2dtOrthoPara.rate": "SpinRate",
    "thermo.finite_mixture_inventory:run_finite_mixture_vu_intervals": "FiniteMixtureVesselRun",
    "adapters.lh2dt_dynamics:Lh2dtDynamicEquipment.run": "DynamicEquipmentRun",
    "real_gas_linepack:RealGasLinepackState.advance": "tuple[RealGasLinepackState, RealGasLinepackStepLedger]",
    "adapters.lh2dt_hydraulics:Lh2dtDarcyPipe.evaluate": "DarcyPipeEvaluation",
    "adapters.lh2dt_equipment:Lh2dtSharedValve.evaluate": "SharedValveEvaluation",
    "adapters.lh2dt_pump_operation:FiniteSpeedPump.run": "PumpOperationTrace",
    "adapters.compressor_map:MappedCompressor.evaluate": "MappedCompressorTrace",
    "adapters.finite_adsorption_vessel:FiniteAdsorptionVessel.snapshot": "AdsorptionVesselSnapshot",
    "adapters.carrier_conversion:FiniteCarrierConversion.run": "CarrierConversionResult",
    "adapters.underground_storage:Uh2scUndergroundStorage.run": "UndergroundTrace",
    "adapters.cantera_fuel_cell:run_cantera_synchronized_fuel_cell": "CanteraFuelCellTrace",
    "adapters.cantera_surface_reactor:CanteraCatalyticSurfaceReactor.run_flowing_cstr": "CatalyticFlowTrace",
    "adapters.cantera_multiphase:CanteraMultiphaseEquilibrium.equilibrate": "MultiphaseEquilibriumResult",
    "adapters.microbial_cell:FiniteMicrobialCell.run": "MicrobialCellTrace",
    "materials.transport:PowerLawSolubility.concentration_mol_m3": "float",
    "adapters.lh2dt:Lh2dtBulkNozzleOutflow.sample": "h2physics.release:NozzleResult",
    "adapters.droplet_transport:SaturatedParcelFlight.run": "ParcelTrace",
    "dispersion:run_preferred_gas_dispersion": "h2physics.adapters.hyram:HyRAMJetRun",
    "dispersion:run_preferred_lh2_dispersion": "h2physics.adapters.slabx_lh2:SLABLH2Run",
    "adapters.obstacle_dispersion:run_obstacle_dispersion": "ObstacleDispersionResult",
    "adapters.hyram_overpressure:HyRAMBauwensOverpressure.evaluate": "BauwensPeakResult",
    "adapters.detonation:SDToolboxDetonation.cj": "CJWaveResult",
    "adapters.detonation:SDToolboxDetonation.frozen_shock": "FrozenShockResult",
    "adapters.vessel_failure:HelprVesselFailure.predict": "VesselFailurePrediction",
    "adapters.hyram_exposure:HyRAMExposure.thermal_response": "ExposureResult",
    "adapters.hyram_exposure:HyRAMExposure.pressure_response": "ExposureResult",
    "adapters.oxygen_deficiency:CanteraOxygenRoom.run": "OxygenRoomResult",
    "adapters.jos3_thermal:JOS3ThermalResponse.run": "ThermalResponse",
    "adapters.facility_protection:execute_protected": "ProtectedEquipmentRun",
    "adapters.gas_detection:evaluate_first_order_concentration_sensor": "FirstOrderConcentrationSensorTrace",
    "adapters.gas_detection:evaluate_concentration_alarm_voting": "ConcentrationAlarmVotingTrace",
    "adapters.hydrogen_economics:evaluate_hydrogen_economics": "HydrogenEconomicsResult",
    "electrocatalyst_metrics:corrected_overpotential_v": "float | numpy.ndarray",
    "model_selection:ModelRegistry.select": "ModelSelection",
}


def entries():
    rows = []
    for line in ROWS.strip().splitlines():
        ids, module, call, english, korean = line.split("|")
        rows.append(dict(ids=ids.split(","), module="h2physics." + module,
                         call=call, en=english, ko=korean))
    return rows


def escaped(value):
    return str(value).replace("|", "&#124;").replace("\n", " ")


class Source:
    """Resolve definitions and explicit relative imports without executing code."""

    def __init__(self, root):
        self.root = root
        self.cache = {}
        self.definitions = {}
        self.imports = {}
        self.lookups = {}

    def module(self, name):
        if name not in self.cache:
            path = self.root / "src" / Path(*name.split("."))
            path = path.with_suffix(".py") if path.with_suffix(".py").exists() else path / "__init__.py"
            tree = ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))
            self.cache[name] = (path, tree)
            self.definitions[name] = {
                n.name: n for n in tree.body
                if isinstance(n, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
            }
            self.imports[name] = {}
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom):
                    for alias in node.names:
                        self.imports[name].setdefault(alias.asname or alias.name, (node, alias))
        return self.cache[name]

    def resolve(self, module, name, seen=None):
        seen = set() if seen is None else seen
        if (module, name) in seen:
            raise ValueError(f"Cyclic definition lookup: {module}.{name}")
        seen.add((module, name))
        path, tree = self.module(module)
        if (module, name) in self.lookups:
            return self.lookups[(module, name)]
        if name in self.definitions[module]:
            result = module, path, self.definitions[module][name]
            self.lookups[(module, name)] = result
            return result
        if name in self.imports[module]:
            node, alias = self.imports[module][name]
            if node.level:
                package = module if path.name == "__init__.py" else module.rsplit(".", 1)[0]
                parent = package.split(".")[:len(package.split(".")) - node.level + 1]
                target = ".".join(parent + ((node.module or "").split(".") if node.module else []))
            else:
                target = node.module or ""
            if target.startswith("h2physics"):
                result = self.resolve(target, alias.name, seen)
                self.lookups[(module, name)] = result
                return result
        raise ValueError(f"Definition not found: {module}.{name}")

    def entry(self, row):
        parts = row["call"].split(".")
        module, path, owner = self.resolve(row["module"], parts[0])
        node = owner
        if len(parts) > 1:
            node = next((n for n in owner.body if isinstance(n, ast.FunctionDef) and n.name == parts[1]), None)
            if node is None:
                raise ValueError(f"Method not found: {row['module']}.{row['call']}")
        return module, path, owner, node


def fields(node):
    if not isinstance(node, ast.ClassDef):
        return []
    return [n for n in node.body if isinstance(n, ast.AnnAssign)
            and isinstance(n.target, ast.Name) and not n.target.id.startswith("_")]


def initializer(node):
    if isinstance(node, ast.ClassDef):
        return next((n for n in node.body if isinstance(n, ast.FunctionDef) and n.name == "__init__"), None)
    return node


def arguments(node):
    fn = initializer(node)
    if fn is not None:
        names = [n.arg for n in (*fn.args.posonlyargs, *fn.args.args, *fn.args.kwonlyargs)
                 if n.arg not in {"self", "cls"}]
        if fn.args.vararg:
            names.append("*" + fn.args.vararg.arg)
        if fn.args.kwarg:
            names.append("**" + fn.args.kwarg.arg)
        return names
    return [n.target.id for n in fields(node) if not (
        isinstance(n.value, ast.Call) and any(k.arg == "init" and isinstance(k.value, ast.Constant)
                                            and k.value.value is False for k in n.value.keywords))]


def short_names(names, limit=6):
    rendered = ", ".join(f"`{name}`" for name in names[:limit]) or "—"
    if len(names) > limit:
        rendered += ", …"
    return rendered


def result_contract(source, module, owner, node, row):
    if isinstance(node, ast.ClassDef):
        return module, node.name, node
    key = row["module"].removeprefix("h2physics.") + ":" + row["call"]
    if node.returns is None and key not in RETURNS:
        raise ValueError(f"Unreviewed unannotated return contract: {key}")
    annotation = RETURNS[key] if node.returns is None else ast.unparse(node.returns).strip("'\"")
    if ":" in annotation:
        target_module, annotation = annotation.split(":", 1)
        _, _, target = source.resolve(target_module, annotation)
        return target_module, annotation, target
    if re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", annotation):
        try:
            target_module, _, target = source.resolve(module, annotation)
            return target_module, annotation, target
        except ValueError:
            pass
    return None, annotation, None


def input_summary(source, module, owner, node, ko):
    pieces = []
    if isinstance(owner, ast.ClassDef) and node is not owner:
        pieces.append(("구성: " if ko else "Setup: ") + short_names(arguments(owner), 4))
    pieces.append(("호출: " if ko else "Call: ") + short_names(arguments(node), 7))
    # Show nested spec fields when a single object would otherwise conceal I/O.
    fn = initializer(node)
    if fn is not None:
        params = [n for n in (*fn.args.posonlyargs, *fn.args.args, *fn.args.kwonlyargs)
                  if n.arg not in {"self", "cls"}]
        if len(params) <= 2:
            for param in params:
                if isinstance(param.annotation, ast.Name):
                    try:
                        _, _, contract = source.resolve(module, param.annotation.id)
                    except ValueError:
                        continue
                    if fields(contract):
                        pieces.append(f"`{param.arg}`: " + short_names([n.target.id for n in fields(contract)], 6))
    return "<br>".join(pieces)


def anchor(row):
    return "module-" + row["module"].replace(".", "-") + "-" + row["call"].replace(".", "-").lower()


def contract_path(row):
    return "docs/modules/" + row["ids"][0].split(".")[0] + ".md"


def readme_block(source, rows, ko=False):
    count = len({i for row in rows for i in row["ids"] if not i.startswith(("extension.", "support."))})
    if ko:
        lines = [START, "## 모듈별 목적·입력·출력", "",
                 "아래에서 **할 일 → Python 호출 → 필요한 입력 → 반환 결과**를 바로 고를 수 있습니다. "
                 "`h2physics.` 아래의 실제 모듈 경로와 호출명을 표시했습니다. "
                 "외부 엔진 연결 객체, 물리 계산, 자료 분석·집계는 목적 설명으로 구별합니다.", "",
                 f"**기존 카탈로그 {count}개 식별자를 모두 연결**하고, 같은 분야의 주요 선택 수준과 0.2.0 보완 API, "
                 "공통 연결 객체도 별도 행으로 표시했습니다. 행 수는 독립 물리 모델 수나 검증 완료 개수가 아닙니다.", "",
                 "입력 칸은 **주요 파라미터 이름**입니다. `구성`은 생성자, `호출`은 계산 메서드의 인자입니다. "
                 "`…`가 있으면 나머지 인자가 있습니다. 각 호출 링크의 "
                 "[전체 입출력 명세](" + BASE + "docs/MODULE_IO_REFERENCE.md)에서 **전체 인자·타입·기본값·반환 필드·원본 코드**를 확인하세요. "
                 "한 행은 해당 분야의 선택한 사용 경로이며, 다른 수준과 적용 한계는 분야별 설명서를 함께 확인합니다.", "",
                 "단위 접미사는 `_pa`=Pa, `_k`=K, `_kg`=kg, `_mol`=mol, `_s`=s, "
                 "`_w`=W, `_j`=J, `_m`=m이며 조합 단위도 이름에 표시합니다. "
                 "유체 상태 압력은 절대압이고, 압력차·과압·잔차는 해당 API가 정한 차이 기준입니다. "
                 "`basis`·`evidence`·`clock_id`·공급자 객체는 물질/에너지 기준·근거·시간축·실제 엔진을 지정하는 입력입니다. "
                 "스칼라나 배열의 물리적 의미와 형상은 연결된 객체 명세·사용 설명서를 따릅니다.", ""]
    else:
        lines = [START, "## Module purposes, inputs and outputs", "",
                 "Choose a task, find its Python entry point, inspect the inputs, and read the returned result. "
                 "Paths below are actual modules under `h2physics.`. Purpose descriptions distinguish "
                 "physical calculations, native-engine bindings and supporting analysis/accounting.", "",
                 f"These tables map **all {count} existing catalog identifiers**, with extra rows for important "
                 "selectable levels, 0.2.0 extensions and shared connection objects. Rows are navigation choices, "
                 "not counts of independent physical models or completed qualifications.", "",
                 "Inputs show **key parameter names**: `Setup` is the constructor; `Call` is the method/function. "
                 "`…` means more parameters exist. Each callable links to the "
                 "[complete I/O reference](" + BASE + "docs/MODULE_IO_REFERENCE.md) with **all arguments, types, "
                 "defaults, result fields and source links**. Each row selects one usable interface/level; "
                 "consult its domain manual for other levels and applicability.", "",
                 "Unit suffixes: `_pa` = Pa, `_k` = K, `_kg` = kg, `_mol` = mol, `_s` = s, "
                 "`_w` = W, `_j` = J, `_m` = m; compound units follow the same naming. "
                 "Fluid-state pressures are absolute; pressure differences, overpressure and residuals follow their stated difference basis. "
                 "`basis`, `evidence`, `clock_id` and provider objects specify material/energy references, "
                 "evidence, clock identity and the actual engine. Object contracts/manuals define array axes and physical meaning.", ""]
    lines.append(("분야 바로가기: " if ko else "Jump to: ") + " · ".join(
        f"[{pair[int(ko)]}](#module-group-{group})" for group, pair in GROUPS.items()))
    lines.append("")
    for group, pair in GROUPS.items():
        lines += [f'<a id="module-group-{group}"></a>', "", "### " + pair[int(ko)], "",
                  "| 모듈·분야 식별자 | 목적·선택 수준 | Python 호출·전체 명세 | 주요 입력 | 출력 |" if ko else
                  "| Module / family | Purpose / selected level | Python entry / full contract | Key inputs | Output |",
                  "| --- | --- | --- | --- | --- |"]
        for row in rows:
            if row["ids"][0].split(".")[0] != group:
                continue
            module, _, owner, node = source.entry(row)
            _, return_name, result = result_contract(source, module, owner, node, row)
            result_names = [n.target.id for n in fields(result)]
            # Contract metadata is retained in the full reference; show useful physical fields first.
            physical = [n for n in result_names if n not in {"basis", "evidence", "settings", "spec", "owner"}]
            output = f"`{escaped(return_name)}`"
            if physical:
                output += "<br>" + short_names(physical, 5)
            label = row["module"].removeprefix("h2physics.")
            family = ", ".join(f"`{identity}`" for identity in row["ids"])
            lines.append(f"| `{label}`<br>{family} | {escaped(row['ko' if ko else 'en'])} | "
                         f"[`{row['call']}`]({BASE}{contract_path(row)}#{anchor(row)}) | "
                         f"{input_summary(source, module, owner, node, ko)} | {output} |")
        lines.append("")
    lines += [("선택 경계: " if ko else "Selection boundaries: ") + (
        "고압 기체 확산은 HyRAM+, 액화수소 유래 확산은 SLABx-LH2를 우선합니다. "
        "실내 점화 지연별 압력 피크는 한 사건의 압력 시간 이력이 아니므로 `solve_linear_sdof`에 직접 넣지 않습니다. "
        "`CFDMesh`는 사례 정의 객체이며 FDS 계산 실행 결과가 아닙니다. 고정 유량 스냅숏에는 호환 수신기가 필요하며 "
        "기존 정상 HyRAM API가 계산하는 유량을 강제로 바꾸는 기능이 아닙니다. "
        "외부 공급자는 별도 설치와 적합한 버전·입력 근거가 필요합니다. "
        "이 표는 기존 시험 상태나 물리적 자격을 갱신하지 않습니다."
        if ko else
        "HyRAM+ is preferred for high-pressure gas dispersion; SLABx-LH2 for LH2-origin dispersion. "
        "Indoor ignition-delay peak curves are not one event's pressure-time history and cannot be passed directly "
        "to `solve_linear_sdof`. `CFDMesh` defines a case; it is not an executed FDS solution. Fixed-flow snapshots "
        "require a compatible receiver and cannot override the existing steady HyRAM API's own orifice-flow calculation. "
        "External providers require separate installation, compatible revisions and qualified inputs. "
        "These tables do not update existing test or physical-qualification status."), "", END]
    return "\n".join(lines)


def source_url(source, path, node):
    return BASE + path.relative_to(source.root).as_posix() + f"#L{node.lineno}"


def render_definition(source, module, path, node, qualified):
    lines = [f"#### `{qualified}`", "", f"[Source]({source_url(source, path, node)})", ""]
    doc = ast.get_docstring(node)
    if doc:
        lines += [doc, ""]
    if isinstance(node, ast.ClassDef):
        init = initializer(node)
        if init is not None:
            constructor_args = re.sub(r"^(self|cls)(, )?", "", ast.unparse(init.args))
            lines += ["```python", f"{node.name}({constructor_args})", "```", ""]
        fs = fields(node)
        if fs:
            lines += ["Declared fields (input records or returned state; **not a direction inferred from the name**):", "",
                      "| Field | Type | Default / construction rule |", "| --- | --- | --- |"]
            for n in fs:
                default = ast.unparse(n.value) if n.value is not None else "required"
                lines.append(f"| `{n.target.id}` | `{escaped(ast.unparse(n.annotation))}` | `{escaped(default)}` |")
            lines.append("")
        if init is None and not fs:
            lines += ["No explicit local constructor fields; consult the retained source and inherited/provider contract.", ""]
        properties = [n for n in node.body if isinstance(n, ast.FunctionDef)
                      and not n.name.startswith("_") and any(isinstance(d, ast.Name) and d.id == "property" for d in n.decorator_list)]
        if properties:
            lines += ["Computed properties: " + ", ".join(f"`{n.name}`" for n in properties) + ".", ""]
    else:
        returns = " -> " + ast.unparse(node.returns) if node.returns is not None else ""
        lines += ["```python", f"{node.name}({ast.unparse(node.args)}){returns}", "```", ""]
        if node.returns is None:
            lines += ["The source has no explicit return annotation; inspect its return statements and the domain manual. "
                      "No return type is invented by this generator.", ""]
    return lines


def related_records(source, module, owner, node):
    """Include typed records reachable from setup/call/return, to two record edges."""
    seeds = [owner, node]
    found = {}
    queue = [(module, seed, 0) for seed in seeds]
    while queue:
        current_module, current, depth = queue.pop(0)
        annotations = []
        if isinstance(current, ast.ClassDef):
            annotations += [f.annotation for f in fields(current)]
        fn = initializer(current)
        if fn is not None:
            annotations += [a.annotation for a in (*fn.args.posonlyargs, *fn.args.args, *fn.args.kwonlyargs)
                            if a.annotation is not None]
            if fn.returns is not None:
                annotations.append(fn.returns)
        for annotation in annotations:
            if isinstance(annotation, ast.Constant) and isinstance(annotation.value, str):
                try:
                    annotation = ast.parse(annotation.value, mode="eval").body
                except SyntaxError:
                    continue
            for name in sorted({a.id for a in ast.walk(annotation) if isinstance(a, ast.Name)}):
                try:
                    target_module, path, target = source.resolve(current_module, name)
                except ValueError:
                    continue
                key = (target_module, target.name)
                if key in found or target is owner or target is node or not fields(target):
                    continue
                found[key] = (target_module, path, target)
                if depth < 1:
                    queue.append((target_module, target, depth + 1))
    return list(found.values())


def reference(source, rows):
    lines = ["# Module inputs and outputs / 모듈 입출력 전체 명세", "",
             "This source-derived companion expands every entry in the English and Korean README module tables. "
             "Start with those task/purpose tables to select a level, then use the exact signatures below.", "",
             "README의 분야별 목적 표에서 경로를 고른 뒤 이 문서의 생성자·계산 인자·연결 객체·반환 필드를 확인하세요. "
             "전체 인자 이름·타입 주석·기본값은 실제 소스에서 추출합니다. 제공된 타입 주석 자체가 런타임 보증은 아닙니다.", "",
             "## Reading the contracts / 읽는 방법", "",
             "- Import from the displayed `h2physics.*` module; construct the owner before calling an instance method. "
             "`self` and `cls` in source signatures are bound by Python, not user inputs.",
             "- A parameter with no default is required. `field(init=False)` is computed, not a constructor input. "
             "`field(default_factory=...)` supplies a factory default. Class/protocol fields remain declarations, "
             "not a claim that every class has a generated dataclass constructor.",
             "- Setup and execution are distinct. Inject actual provider objects, callbacks, material coefficients, "
             "boundaries and clocks; preserve the original result when a receiving API requires it.",
             "- Source-linked input/return records include their declared fields and computed-property names. "
             "Related records are expanded to two record edges; more deeply nested contracts, inherited behavior "
             "and unannotated callbacks stay in their linked source/domain manuals.",
             "- Unit-bearing names follow SI: Pa, K, kg, mol, m, s, W, J, with their stated compound units. "
             "Fluid-state pressure is absolute; pressure differences, overpressure and residuals use their declared difference basis. "
             "Native/provider objects can use their own explicitly documented field spellings and conventions. "
             "Read angle, rpm, fraction, percentage, H/H2, phase, spin, formation/sensible enthalpy and signed-power bases explicitly.",
             "- A `Trace` usually retains multiple samples/stages; a state/point usually describes one state. "
             "Neither object naming nor source extraction proves numerical execution or experimental qualification.", "",
             "## Navigation / 바로가기", ""]
    for row in rows:
        lines.append(f"- [{row['ko']} / {row['en']}](#{anchor(row)})")
    for row in rows:
        module, path, owner, node = source.entry(row)
        lines += ["", f'<a id="{anchor(row)}"></a>', "", f"## {row['ko']} / {row['en']}", "",
                  "Family / navigation ID: " + ", ".join(f"`{i}`" for i in row["ids"]), "",
                  f"Import module: `{row['module']}`; selected entry: `{row['call']}`.", ""]
        if isinstance(owner, ast.ClassDef):
            lines += render_definition(source, module, path, owner, module + "." + owner.name)
        if node is not owner or not isinstance(owner, ast.ClassDef):
            lines += render_definition(source, module, path, node, module + "." + row["call"])
        records = related_records(source, module, owner, node)
        rm, return_name, result = result_contract(source, module, owner, node, row)
        lines += ["### Returned value / 반환값", "", f"`{escaped(return_name)}`", ""]
        if node is not owner or not isinstance(owner, ast.ClassDef):
            if node.returns is None:
                lines += ["This return contract was reviewed from the implementation; it is not an annotation "
                          "present in the source signature.", ""]
        if result is not None and result is not owner and all(rn is not result for _, _, rn in records):
            rp, _ = source.module(rm)
            records.insert(0, (rm, rp, result))
        if not isinstance(node, ast.ClassDef):
            # Reviewed unannotated/compound returns also expose their nested records.
            return_module = rm or module
            fake = ast.FunctionDef(name="return_contract", args=ast.arguments(
                posonlyargs=[], args=[], kwonlyargs=[], kw_defaults=[], defaults=[]),
                body=[], decorator_list=[], returns=ast.parse(return_name, mode="eval").body)
            for record in related_records(source, return_module, fake, fake):
                if record[2] is not owner and all(rn is not record[2] for _, _, rn in records):
                    records.append(record)
        if records:
            lines += ["### Related input/return records / 관련 입력·반환 객체", ""]
            for rm, rp, rn in records:
                lines += render_definition(source, rm, rp, rn, rm + "." + rn.name)
    lines += ["", "## Maintaining this guide / 갱신", "",
              "Curated purposes and entry selection live in `scripts/readme_module_guide.py`. "
              "Run `python scripts/readme_module_guide.py` to regenerate both README blocks and this file. "
              "Run `python scripts/readme_module_guide.py --check` to reject stale output, unresolved callables "
              "or missing catalog IDs. The script parses source with the standard library, imports no physical "
              "engine and runs no calculation. Review purpose/units/limits against domain manuals when an API changes. "
              "It preserves authored scientific attribution and performs no automatic translation of external material.", ""]
    return "\n".join(lines)


def reference_index(rows):
    lines = ["# Module inputs and outputs / 모듈 입출력 전체 명세", "",
             "[English README](../README.md#module-purposes-inputs-and-outputs) · "
             "[한국어 README](../README_KO.md#모듈별-목적입력출력) · "
             "[API contracts](API.md) · [All public symbols](PUBLIC_API_INDEX.md)", "",
             "The README tables show each task, module, callable, key inputs and output. "
             "This index opens the full contracts by subject. Each subject file includes every selected "
             "constructor/method argument, type annotation, default, returned record and linked source. "
             "The guide maps all 82 catalog identifiers and additional levels/extensions; it is not a model-validation count.", "",
             "README 표에서 목적·모듈·호출·주요 입력·출력을 먼저 고르고, 아래 분야별 명세에서 전체 파라미터를 확인하세요. "
             "긴 한 파일에 내용을 모으지 않고 분야별로 나누어 탐색할 수 있게 했습니다. "
             "반환 타입 주석이 없는 API는 구현에서 직접 확인한 반환 객체를 구분하여 표시합니다.", "",
             "## Parameter meanings / 파라미터 읽기", "",
             "| Input kind / 입력 유형 | What to supply / 넣는 값 | Examples / 예 |",
             "| --- | --- | --- |",
             "| Physical scalar / 물리 스칼라 | Value in the explicit unit; absolute/gauge, phase and sign follow the selected contract / 명시 단위·압력 기준·상·부호 유지 | `pressure_pa`, `temperature_k`, `mass_flow_kg_s` |",
             "| Parameter record / 파라미터 객체 | Construct the named class with its required fields; preserve material/geometry identity / 필수 필드·물질·형상을 지정해 생성 | `DarcyGeometry`, `StackGeometry`, `RankineCycleSpec` |",
             "| State or result / 상태·이전 결과 | Pass the retained object from the selected producer; inspect its basis and admission / 생산 모듈의 원래 객체·기준·허용 상태 전달 | `ThermoState`, `NozzleResult`, `IntervalMassSource` |",
             "| Array / 배열 | Numeric values with explicit axis order and shape / 시간·공간·성분 축의 순서·형상 유지 | `time_s`, `initial_component_moles`, `initial_pressure_pa` |",
             "| Function or law / 함수·구성식 | Caller callback with the documented signature and return unit / 정해진 호출 인자·반환 단위를 가진 사용자 함수 | `friction_law`, `thermochemistry`, `diffusivity_m2_s` |",
             "| Provider or native model / 공급자·외부 모델 | Actual installed compatible engine object; installed separately / 별도 설치된 호환 엔진 객체 | CoolProp, Cantera, HyRAM+, SLABx-LH2 |",
             "| Basis, evidence, clock / 기준·근거·시간축 | Real identities and compatible references; a label does not qualify an unknown condition / 실제 식별정보·호환 기준 지정 | `basis`, `evidence_id`, `clock_id` |",
             "| Numerical control / 수치 제어 | Solver tolerance, mesh or step limit within the chosen model's domain / 모델 영역에 맞는 허용오차·격자·시간 간격 | `maximum_step_s`, `relative_tolerance`, `cell_count` |", "",
             "SI suffixes include Pa, K, kg, mol, m, s, J and W plus compound units. "
             "Fluid-state pressure is absolute; differences, overpressure and residuals retain their stated difference basis. "
             "Do not assume a fractional input is a percentage, or an arbitrary provider's native units are SI. "
             "The full signature preserves positional-only `/`, keyword-only `*`, required arguments, optional defaults "
             "and `**kwargs`. An optional-looking default can still require another explicit input for the selected level.", "",
             "단위 접미사와 함께 비율/백분율·몰/질량·H/H₂·기체/액체·오르토/파라·현열/생성열·동력 부호를 확인하세요. "
             "`field(init=False)`는 사용자가 넣는 값이 아니라 생성 후 계산되는 필드입니다. "
             "`self`·`cls`는 Python이 연결하며 사용자가 넘기지 않습니다.", "",
             "## Working example / 입력에서 출력까지", "",
             "Install `h2physics[thermo,hydraulics]`. The following uses CoolProp fluid properties and "
             "a selected steady frozen-property Darcy level. Geometry is an input record; friction is an injected "
             "function; the returned object exposes a mass flow and numerical residual. "
             "The geometry and operating point are demonstration inputs, not calibrated equipment data.", "",
             "```python", "from dataclasses import replace", "from fluids.friction import friction_factor",
             "from h2physics.hydraulics import DarcyGeometry, solve_darcy_flow",
             "from h2physics.thermo import CoolPropProperties", "",
             'properties = CoolPropProperties("Hydrogen")',
             "state = properties.state_pt(pressure_pa=200_000.0, temperature_k=300.0)",
             "base = DarcyGeometry(length_m=10.0, diameter_m=0.01, roughness_m=1e-6)",
             "geometry = replace(base, diameter_m=0.02)  # customize the input record", "",
             "result = solve_darcy_flow(", "    geometry,",
             "    density_kg_m3=state.density_kg_m3,", "    viscosity_pa_s=state.viscosity_pa_s,",
             "    driving_pressure_pa=1_000.0,",
             "    friction_law=lambda re, e_d: friction_factor(re, e_d),", ")",
             "print(result.mass_flow_kg_s)        # kg/s", "print(result.momentum_residual_pa)  # Pa", "```", "",
             "For data-driven laws, preserve the same callback arguments, units and domain, and attach "
             "the dataset/version/calibration evidence required by that model. This example selects a "
             "steady frozen-property pipe: it does not choose the transient, heated, network or two-phase level.", "",
             "## Full contracts by subject / 분야별 전체 명세", "",
             "| Subject / 분야 | Selected entry points / 호출 경로 | Full signatures and records / 전체 명세 |",
             "| --- | --- | --- |"]
    for group, pair in GROUPS.items():
        selected = [r for r in rows if r["ids"][0].split(".")[0] == group]
        lines.append(f"| {pair[0]} / {pair[1]} | {len(selected)} | [{group}](modules/{group}.md) |")
    lines += ["", "## Direct entry index / 개별 호출 바로가기", ""]
    for row in rows:
        lines.append(f"- [`{row['module']}.{row['call']}`]({contract_path(row).removeprefix('docs/')}#{anchor(row)}) — {row['ko']} / {row['en']}")
    lines += ["", "## Maintenance / 유지 관리", "",
              "`python scripts/readme_module_guide.py` regenerates the two README blocks, this index and "
              "15 subject files from curated purposes and actual source AST. "
              "`python scripts/readme_module_guide.py --check` checks coverage, symbol resolution and output freshness. "
              "It does not import scientific providers or run models. "
              "API inventories describe interfaces, not new test/experimental evidence. "
              "See [model selection](MODEL_SELECTION.md), [domain manuals](PUBLIC_API_INDEX.md), "
              "[dependency installation](DEPENDENCIES.md) and [recorded limitations](PROGRESS.md).", ""]
    return "\n".join(lines)


def replace_block(text, block, ko):
    if START in text:
        if text.count(START) != 1 or text.count(END) != 1:
            raise ValueError("README must contain exactly one complete module guide block")
        start = text.index(START)
        end = text.index(END, start) + len(END)
        return text[:start] + block + text[end:]
    insertion = "## 설치와 첫 실행" if ko else "## What is included"
    if insertion not in text:
        raise ValueError("README insertion heading is missing")
    return text.replace(insertion, block + "\n\n" + insertion, 1)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    root = args.root.resolve()
    source, rows = Source(root), entries()
    _, tree = source.module("h2physics.catalog")
    catalog = {ast.literal_eval(n.args[0]) for n in ast.walk(tree) if isinstance(n, ast.Call)
               and isinstance(n.func, ast.Name) and n.func.id == "ModelSpec"}
    covered = {i for row in rows for i in row["ids"] if not i.startswith(("extension.", "support."))}
    if covered != catalog:
        raise ValueError(f"Catalog mismatch: missing={catalog - covered}; unknown={covered - catalog}")
    anchors = [anchor(row) for row in rows]
    if len(set(anchors)) != len(anchors):
        raise ValueError("Duplicate entry anchors")
    for row in rows:
        source.entry(row)
    products = {root / "docs/MODULE_IO_REFERENCE.md": reference_index(rows)}
    for group in GROUPS:
        selected = [r for r in rows if r["ids"][0].split(".")[0] == group]
        products[root / f"docs/modules/{group}.md"] = reference(source, selected)
    for name, ko in (("README.md", False), ("README_KO.md", True)):
        path = root / name
        products[path] = replace_block(path.read_text(encoding="utf-8"), readme_block(source, rows, ko), ko)
    stale = []
    for path, content in products.items():
        if args.check:
            if not path.exists() or path.read_text(encoding="utf-8") != content:
                stale.append(path.relative_to(root).as_posix())
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            temporary = path.with_suffix(path.suffix + ".tmp")
            temporary.write_text(content, encoding="utf-8", newline="\n")
            temporary.replace(path)
    if stale:
        raise SystemExit("Stale generated documentation: " + ", ".join(stale))
    print(f"Module guide: {len(rows)} entry points; {len(catalog)}/{len(catalog)} catalog IDs; "
          f"{len(products)} documents {'current' if args.check else 'written'}; source resolution PASS")


if __name__ == "__main__":
    main()
