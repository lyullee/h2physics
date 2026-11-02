# 사용자 및 연구자 안내

## PEM 전류 리플 측정자료 읽기

Mendeley Data v2 자료는 CC BY 4.0 조건이며 저자·DOI·취득 바이트 해시는
[`research/data/pem-ripple-degradation.toml`](../research/data/pem-ripple-degradation.toml)에
기록되어 있습니다. 원본 ZIP은 저장소 밖의 무시된 `data/raw/`에 보관합니다.
사용 전 저장소 루트에서 `python scripts/acquire_data.py --keys pem-ripple-degradation`
를 실행해 원본을 받고 게시자 SHA-256을 확인하세요.

```python
from h2physics.data import (
    load_pem_ripple_archive,
    load_pem_ripple_iv_curve,
    load_pem_ripple_continuous_trace,
    load_pem_ripple_fit_table,
)

archive = load_pem_ripple_archive()
iv = load_pem_ripple_iv_curve(archive, cell_id="PEM1", cycle="Initial")
log = load_pem_ripple_continuous_trace(archive, cell_id="PEM1")
reported_fits = load_pem_ripple_fit_table(archive)
```

IV 값은 소스가 선언한 A, V 단위와 sweep index를 유지합니다. 연속 기록은
셀별로 메모리에 읽으므로 큰 로그는 필요한 셀 하나씩 처리하세요. `interval_s`의
시간 간격을 그대로 보존하며 로깅이 멈춘 구간을 보간하지 않습니다. 원본 CSV의
행 토큰이 필요하면 `iv.iter_source_rows()` 또는 `log.iter_source_rows()`를
끝까지 순회할 수 있습니다. `alpha`를 포함한 적합 결과는 측정값이 아니라
보고된 파생값입니다. 활성 면적이 없어 A/m²로 바꾸지 않으며, 온도·압력·급수
조건·교정·시간대·셀 간 동기화도 가정하지 않습니다. 자세한 범위와 라이선스는
[`PEM_RIPPLE_DEGRADATION.md`](PEM_RIPPLE_DEGRADATION.md)를 확인하세요.

## AHSS 1300 공개 투과 관측 데이터

`h2physics.data.load_ahss1300_permeation(path, dataset=receipt)`는 공개 Mendeley
버전 1 워크북의 메타데이터·첨부 목록·파일 SHA-256이 일치할 때 두 실험 시트를
원본 순서와 행 식별자를 포함해 읽는다. 결과의 시간·전류 숫자는 수정하지 않은
관측값이며 배열은 읽기 전용이다. 파일을 읽으려면 `data` 선택 패키지가 필요하다.
전류 단위 표기가 손상되어 단위는 미정으로 남고, 이 API는 수소 경계 플럭스 변환이나
확산계수 피팅을 하지 않는다. 출처와 적용 한계는 `DATA_QUALIFICATION.md`를 참조한다.

## 시작과 구현 범위

이 프로젝트는 수소 설비·저장·물리 안전 모델을 Python 객체로 조합하는 라이브러리다.
`MODEL_CATALOG.md`는 전체 연구 범위와 현재 실행 가능한 수준을 구분한다. 일부 수준이
구현된 항목에도 미구현된 공간 해상도, 경계 조건, 물리 현상이 남아 있다. 실험 검증을
통과한 범위를 넓혀 해석하지 않는다.

Python 3.12 환경에서 저장소 루트를 작업 디렉터리로 사용한다.

PV 직결 전해조 API는 Faradaic 효율이 1 미만인 구성을 현재 지원하지 않는다.
이 경우 finite material/energy 경로가 정의되지 않아 운전을 거부하며, 오류 객체는
요청한 효율, 미해결 손실 비율, 에너지 경로가 미할당 상태임을 보존한다. 이를
부산물 반응이나 폐열로 해석하지 않는다. 적용 한계와 모델 경계는 카탈로그 및
Request 023의 전기화학 계약을 확인한다.

Anaconda를 사용할 경우 저장소의 `environment.yml`에 Python 3.12와 `thermo`, `data`,
`chemistry`, `hydraulics`, `dev` 선택 extra를 포함한 개발 환경이 정의되어 있다.

```powershell
# Conda가 PowerShell에 초기화되지 않은 경우 현재 세션에서 먼저 실행
& "$env:USERPROFILE\miniconda3\shell\condabin\conda-hook.ps1"
conda env create -f environment.yml
conda activate h2physics-py312
python scripts/check_environment.py --profile research
```

이미 환경이 생성되어 있다면 `conda env create` 대신
`conda env update -n h2physics-py312 -f environment.yml`을 사용한다.

`thermo`, `data`, `chemistry`는 선택 설치 항목이다. 현재 검증 환경은
`requirements/validation-windows-py312-2026-10-27.txt`에 기록한다. 기존 설비 패키지와
한 환경에서 사용할 때에는 `DEPENDENCIES.md`에 기록된 SciPy·SLAB 버전 충돌을 먼저 해결한다.
`check_environment.py`는 모델을 실행하지 않고 프로파일별 설치 버전과 import 경로를
표시한다. 실제 Python import까지 확인하려면 `--imports`를 추가한다. `core`는 최소
의존성만 검사하고 `research`는 열역학·데이터·Cantera·유압·pytest 선택 의존성도 요구한다.
환경 확인과 과학적 모델 검증은 별개다. 이 프로젝트의 수치 모델 케이스는 Hangang 검증 계획으로 실행한다.

## 파라미터·데이터·함수의 교체

입출력은 dataclass, Protocol, NumPy 배열 및 Python 함수다. 서버나 직렬화 계층을
설치할 필요가 없다. 사용자 정의 물성 객체는 `basis`, `state_pt`, `state_ph`, `state_ps`를
제공하면 된다. 평형식, 반응속도, 확산계수, 경계 조건, 분극 손실은 각각 객체나 함수로
교체한다. 수치 단위가 같아도 의미가 다르면 호환된다고 보지 않는다.

압력은 절대압 Pa, 온도는 K, 시간은 s가 기본이다. 게이지압 입력에는 대기압이 필요하다.
표준 체적유량은 기준 가스 상태 없이 질량유량으로 바꾸지 않는다. 정상수소·파라수소와
에너지 기준은 `PropertyBasis`로 식별한다. 다른 기준의 엔탈피를 직접 더하지 않는다.
성분 분압 계산에는 `h2physics.partial_pressure_pa(p_abs, y)`를 쓸 수 있다.
이 함수는 절대압 Pa와 몰분율을 받아 이상 혼합물의 Dalton 분압을 반환하며,
퓨가시티나 EOS 화학퍼텐셜을 대신하지 않는다. 배열 입력은 NumPy 브로드캐스팅을
지원하고 반환 배열은 읽기 전용이다.
고정 조성 기체의 몰/질량 분율과 성분별 유량 변환은 `h2physics.mixtures.GasComposition`이
맡는다. 성분 몰질량을 명시하고 조성 ID를 부여해야 하며, 유량 부호는 방향 정보를 위해
보존한다. 반응·분리 뒤 조성은 새 객체로 표현한다. 이 API는 혼합물 EOS나 수송물성 혼합법을
계산하지 않으므로 열역학 상태에는 적절한 별도 물성 공급자를 연결한다.
CoolProp 고정 혼합물 공급자는 `state_pt`, `state_pq`, `state_tq`로 해당 네이티브
상태쌍을 호출한다. `state_pq`와 `state_tq`의 품질은 혼합물 몰 기준이다. 이를 순수
유체의 증기 질량분율로 취급하지 않는다. PH/PS/P-밀도 역산에는 단일 기상 구간의
명시적 온도 범위가 필요하며, 내부에너지 플래시는 아직 제공하지 않는다.
Cantera 기반 고정 이상기체 경로는
`CanteraFrozenGasProperties.from_gas_composition(phase, mechanism_basis, composition)`으로
연결한다. 메커니즘 종 몰질량과 조성을 확인하고, 조성 ID와 혼합 몰질량을 보존한다.
`ThermoState.heat_capacity_ratio`는 같은 상태에서 `cp`와 `cv`가 모두 제공될 때만 계산한다.
이 값은 방출식의 적용성이나 고압 혼합물 EOS를 보장하지 않으며, 네이티브 수소 스핀은
분해되지 않은 상태로 취급한다.

## CoolProp과 가속 테이블

준정상 배관 네트워크도 `IsothermalPipeCell.from_pressure(..., eos=...)`로
네이티브 셀을 구성할 수 있다. 셀 압력뿐 아니라 압축성 Darcy 유량식도 같은
CoolProp 밀도와 등온 미분값을 사용한다. 점도는 선언한 기준 상태의 값을
유로 전체에서 고정하는 근사이며, 온도 변화·음속 유량·상변화는 계산하지
않는다. `examples/isothermal_gas_pipe_network.py`는 CoolProp 점도와 설치된
`fluids` 마찰 상관식을 연결한다. 시간 세분화는 출력 시각만 바꾸지 말고
`maximum_step_s`로 실제 적분 단계 상한을 줄여 비교한다.

유체 열물성은 CoolProp 공급자 또는 해당 공급자와 오차를 대조한 테이블을
사용한다. `IsothermalPipeWaveModel`의 기본값은 CoolProp HEOS 수소이며,
의존성 누락이나 상태 거부를 이상기체식으로 자동 대체하지 않는다.
기존 압축기·흡착·전해 생산의 linepack 충전 API는 `RealGasLinepackState`도
받는다. 전해 충전은 선언한 재고 에너지 변화를 네이티브 양 끝 상태의
`m*u` 차이와 대조한다. 흡착 충전은 질량 전달 계약이며 미확정 원천 스핀에는
명시적 선언과 근거가 필요하다. 해석해 검증용 이상기체 타입은 명시적으로
선택하며 실제기체 상태로 이름만 바꾸어 연결하지 않는다.

고정 조성 고압 혼합물에는 CoolProp HEOS 혼합 provider를 연결할 수 있다.
`GasComposition`의 성분 ID와 CoolProp 유체명을 `fluid_names`로 명시하고, 선언한
성분 몰질량은 CoolProp 성분 몰질량과 대조한다. CoolProp 8 문서의 혼합물 입력쌍에
맞춘 PT·PQ·TQ 상태를 제공한다. 사용자가 역산 온도 범위를 지정하면 해당 구간의
기체상·양의 cp·단조성을 확인한 뒤 PH·PS·P-rho를 스칼라 root solve로 구한다. 구간을
지정하지 않으면 역산 요청을 거부한다. 혼합 임계점 단일값 처리와 별도 근거 없는 이상
혼합 transport closure는 제공하지 않는다. 상호작용 매개변수가 없는 성분쌍은 임의
추정하지 않고 실패하게 둔다.

```python
from h2physics import GasComposition
from h2physics.thermo import CoolPropMixtureProperties
from h2physics.release import HomogeneousIsentropicNozzle, NozzleOpening

feed = GasComposition(
    "compressor-feed-h2-n2-v1", ("H2", "N2"), (0.7, 0.3),
    (2.01588e-3, 28.0134e-3),
)
real_gas = CoolPropMixtureProperties(
    feed, fluid_names={"H2": "Hydrogen", "N2": "Nitrogen"},
    inverse_temperature_bounds_k=(280, 320),
    inverse_cache_size=512,
)
state = real_gas.state_pt(5_000_000, 300)
same_state = real_gas.state_ps(state.pressure_pa, state.entropy_j_kg_k)
release = HomogeneousIsentropicNozzle(real_gas).solve(
    state, back_pressure_pa=1_000_000,
    opening=NozzleOpening.circular(
        "compressor-relief", 0.01, effective_area_factor=0.8,
        area_basis_id="replace-with-source-or-explicit-assumption",
    ),
)
```

이 provider는 선택된 CoolProp 릴리스와 그 릴리스의 혼합 매개변수를 사용한다.
공식 혼합물 상호작용 모델을 사용하는 계산이지 혼합물 실험 검증은 아니다. 컴프레서
압축·상변화·조성 변화 및 설계 적합성은 별도 모델과 데이터가 필요하다. 노즐 사용 시
역산 온도범위는 상류와 등엔트로피 경로 전체를 포괄해야 한다. 예제 오리피스와
온도범위는 API 연결을 설명하기 위한 가정이므로 설계값으로 사용하면 안 된다.
역산 캐시는 같은 압력과 목표 상태량을 재요청할 때만 재사용하며, `inverse_cache_info`로
적중·실패·현재 크기를 확인하고 `clear_inverse_cache()`로 비울 수 있다.
서로 다른 역산 목표가 많다면 `prepare_inverse_grid(pressure_nodes_pa, temperature_nodes_k)`로
불변 `MixtureInverseGrid`를 만들 수 있다. 이 호출은 물성 계산을 수행하므로 계산 대상 환경에서
명시적으로 실행한다. 반환된 격자는 같은 조성 fingerprint, 물성 기준 및 역산 온도범위를 가진
다른 provider에도 `use_inverse_grid(grid)`로 연결할 수 있다. 압력·온도·물성 배열은 복사되어
읽기 전용이고 `grid.fingerprint`가 표본 payload를 식별한다. 격자 값은 초기 온도 bracket을
제안하는 데만 쓰며, 실제 질의 압력에서 양 끝점을 다시 계산해 bracket을 확인한다. 필요하면
격자 간격을 넓히고, 격자 범위 밖이면 기존 전체 범위 역산으로 돌아간다.
`clear_inverse_grid()`로 연결을 해제한다. 속도 이득은 아직 측정·검증하지 않았다.
같은 격자를 다음 실행에서도 재사용하려면 `grid.write_npz(path)`로 압축 NumPy 아카이브를
저장하고 `MixtureInverseGrid.read_npz(path)`로 복원한다. 복원은 pickle을 사용하지 않으며
물성 기준, 축, 단조성 및 내용 지문을 다시 검사한다. 이는 역산 bracket 가속 힌트이며 EOS
물성표가 아니고, 저장 지문에는 CoolProp 버전이 포함된 물성 기준이 반영된다.

```python
from h2physics.thermo import CoolPropProperties, GasEnvelope, QualifiedGasTable

properties = CoolPropProperties("ParaHydrogen")
liquid = properties.saturated(150_000, vapor_mass_fraction=0)
warm = properties.state_pt(5_000_000, 300)

table = QualifiedGasTable(
    properties, GasEnvelope(100_000, 90_000_000, 230, 400),
    validation_points=1000,
    internal_energy_policy="derive_from_h_p_rho",
)
print(table.qualification)
```

HEOS 직접 계산이 기준이다. 테이블은 액체·두 상·임계점 주변에 적용하지 않는다.
범위를 벗어나면 예외가 발생하며 다른 물성으로 자동 대체하지 않는다. 기본 `library`
옵션은 라이브러리의 내부에너지를 그대로 사용한다. 검토한 넓은 기체 범위에서 이 옵션은
`h-u-p/rho` 기준을 통과하지 못했다. 위의 명시적 옵션은 내부에너지를 `h-p/rho`로 계산하고
원래 값과의 차이, 직접 EOS 오차 및 실행 비용을 별도로 기록한다. 이 조치가 모든
열역학 미분 관계까지 일관되게 만든다는 뜻은 아니다. 자세한 결과는
`research/property_tables.md`에 있다. 실행 속도는 사용한 입력 쌍과 장비에 따라 달라진다.

## 금속수소화물

`storage.HydrideBed`는 기체 저장조가 공급하는 수소 퓨가시티를 경계 조건으로 받는
공간 평균 모델이다. 평형·흡탈장 속도·열용량·열전달을 별도로 교체한다.

```python
import numpy as np
from h2physics.storage import (
    ArrheniusRate, HydrideBed, HydrideBoundary, HydrideKinetics,
    HydrideParameters, HydrideState, VanthoffPlateau,
)

# 수치 검증용 가상 값이다. 특정 합금의 물성으로 사용하지 않는다.
equilibrium = VanthoffPlateau(24_000, 80, 100_000)
kinetics = HydrideKinetics(
    equilibrium, ArrheniusRate(.01, 0, 300), ArrheniusRate(.02, 0, 300),
)
bed = HydrideBed(HydrideParameters(.002, 1000, 12000, .002, 0), kinetics)
trajectory = bed.simulate(
    np.linspace(0, 50, 101), HydrideState(.1, 300),
    lambda time, state: HydrideBoundary(200_000, 300),
)
print(trajectory.reduced_energy_residual_j)
```

Van't Hoff 파라미터의 엔탈피·엔트로피는 **탈장 반응을 양수**로 정의하고 mol H2를
기준으로 한다. 이 평형 수준은 plateau 근사다. 전체 α/β 상 영역이나 합금별 열화를
계산하지 않는다. 흡장률이 양수일 때 `hydrogen_uptake_kg_s`를 공급 기체 측의 유출로
반영해야 한다. 모델은 유량 제한, 탱크 기체 압력, 벽 온도나 내부 공간 분포를 해결하지 않는다.
열 잔차는 명시된 축약 열수지의 잔차다. 실제 설비 전체의 에너지 수지로 해석하지 않는다.
스위칭 시점이 있으면 해당 시점에서 계산 구간을 나눈다.

## 재료 내 수소 이동

`materials.HydrogenCarrier`로 이동종이 H 원자인지 H2 분자인지 명시한다.
`PowerLawSolubility`는 사용자 계수와 퓨가시티 지수로 표면 평형을 계산한다.
`steady_permeation`은 평판의 벌크 확산 지배 정상 플럭스를 계산한다.
`DiffusionSlab`는 동일한 농도 기준으로 시간 의존 확산과 유한 용량 포획을 계산한다.

```python
import numpy as np
from h2physics.materials import (
    DiffusionSlab, HydrogenCarrier, SlabBoundary, SurfaceCondition,
)

carrier = HydrogenCarrier("atomic_hydrogen", .001)  # 가상 질량 기준
slab = DiffusionSlab(carrier, thickness_m=1, cells=80,
                     diffusivity_m2_s=lambda temperature: .1)
result = slab.simulate(
    np.linspace(0, 1, 51), np.zeros(80),
    boundary=lambda time: SlabBoundary(
        SurfaceCondition("concentration", 1), SurfaceCondition("concentration", 0)),
    temperature_k=lambda time: 300,
)
print(result.inventory_residual_mol_m2)
```

농도는 mol(이동종)/m³, 플럭스는 mol(이동종)/(m² s)다. 양쪽 경계 모두 좌→우 플럭스를
양수로 정의한다. H 원자 플럭스를 H2 상당 몰유량으로 바꾸면 2로 나눈다.
입자 개수 기준 자료를 연결할 때에는 농도를 아보가드로 수로 나누고, 포획 계수
`m³/(particle s)`는 아보가드로 수를 곱해 `m³/(mol s)`로 바꾼다. 방출 속도 `1/s`는 같다.
시간 적분은 희소 Jacobian 구조를 사용하는 BDF다. 농도를 임의로 0으로 잘라 잔차를
감추지 않는다. 허용한 절대 농도 오차보다 큰 음수 농도나 포획 용량 초과는 실패 처리한다.

이 수준은 균질 평판과 주어진 공간 균일 온도를 다룬다. 응력 보조 이동, 균열,
구형·원통형 다층 구조, 표면 반응은 별도 수준이다. 다차원 재료 연구에서는
FESTIM/FEniCSx를 우선 검토하며 현재 Windows 환경에는 직접 설치하지 않았다.

## 전해조와 연료전지

`electrochemistry.HydrogenStack` 하나를 두 운전 모드에 사용한다. 사용자는 실제 상태의
수전해 기준 반응 Gibbs 에너지·엔탈피와 물의 상을 제공한다. 교환전류, 활성화 손실,
면적 저항, 물질전달 한계는 독립 함수로 교체한다. 유효 전하 전달 전자 수와 전체 반응의
전자 수를 혼동하지 않는다. 전체 수소 반응은 H2 1 mol당 전자 2 mol이다.

`evaluate(j, T, mode="electrolysis")`에서 전력·수소 생성률은 양수다.
`mode="fuel_cell"`에서는 같은 경계 정의에 따라 두 값이 음수다. 전류밀도는 양의 크기로
입력한다. PV 직결 유한 전해조는 현재 Faradaic 효율이 1보다 작은 구성을 거부한다.
손실 반응의 물질·열 경로가 정의되지 않아 `PVElectrolysisError.failure_code`에
`unresolved_faradaic_loss_path`를 기록하고 요청 효율과 미할당 손실 비율을 보존한다.
손실을 부산물이나 폐열로 추정하지 않는다. 공유 스택의 단일점 API에서
`isothermal_heat_rejection_w=None`은 열 배정이 미해결임을 나타내며, PV 유한 생산
trace가 해당 운전을 수행했다는 뜻은 아니다. 열용량, crossover, 열화 및 플랜트
보조기기는 별도 모델 범위다.

## Cantera를 통한 반응·화염

`adapters.cantera.CanteraGas`는 매 계산마다 새 `cantera.Solution`을 만드는 Python 함수와
`MechanismBasis`를 받는다. 반응기구 식별자, 원본 SHA-256, 이용 조건, 참고 문헌 및 적용
범위를 명시한다. 하나의 기본 기구가 모든 수소 조건에 적합하다고 가정하지 않는다.
고정 이상기체 물성에는 `CanteraFrozenGasProperties.from_gas_composition`을 사용해
공통 `GasComposition`을 연결할 수 있다. 이 경로는 몰분율을 Cantera가 받는 질량분율로
변환하고 각 선언 몰질량이 네이티브 종 몰질량과 맞는지 확인한다. EOS와 열역학 물성은
Cantera가 소유한다. 부동소수점 합 오차에 대한 기본 보정은 machine precision 범위로
제한되고 `FrozenCompositionCorrection`에 남는다. 이 기능은 이상기체·고정조성 범위이며
Nurion 이연 사례는 아직 실행 전이다.

`equilibrium`은 HP/UV 평형을, `closed_reactor`는 같은 제약의 닫힌 단열 반응기를 계산한다.
`temperature_rise_event`는 지정한 온도 상승의 시간 구간과 선형 추정 시점을 반환한다.
발견되지 않은 사건은 `None`이다. 화염은 `free_flame`으로 계산하며 실제 Cantera 객체를
반환하므로 후속 해석에서 직접 접근할 수 있다. 반환 객체를 수정하면 이전 검증 요약은
더 이상 그 상태를 설명하지 않는다.

`research/native_cantera.md`에는 원소·에너지 수지, 기구 다항식의 1000 K 연결점 문제,
화염 격자·영역 크기 민감도가 기록되어 있다. 온도 상승 표식은 점화 확률이 아니며
평면 자유 화염은 밀폐 폭발이나 폭굉 모델이 아니다.

## 오픈 데이터 재현

```powershell
.venv\Scripts\python scripts/acquire_data.py --keys hydrogen-channel ab2-hydride-tank
.venv\Scripts\python scripts/audit_data.py
.venv\Scripts\python scripts/check_channel_ingestion.py
.venv\Scripts\python scripts/check_hydride_ingestion.py
.venv\Scripts\python scripts/compare_acoustic_data.py
```

기존 공개 기록과 **동일한 바이트**를 재현할 때에는 최신 메타데이터 탐색 대신 다음을 쓴다.
이 명령은 기록된 버전·URL·크기·SHA-256으로 이미 확보했던 파일만 재현하고 원본 기록을 바꾸지 않는다.

```powershell
.venv\Scripts\python scripts/replay_data.py hydrogen-channel hydrogen-sound-speed
```

수화물 압축기의 큰 보관 파일은 다음처럼 파일 제한을 별도로 늘린다.

```powershell
.venv\Scripts\python scripts/acquire_data.py --keys hydride-compressor --maximum-mb 500 --maximum-file-mb 500
```

원본은 `data/raw`에만 저장하며 Git·배포물에서 제외한다. 공개 기록에는 DOI, 저자,
라이선스, 버전, 파일 해시, 누락·실패 상태를 남긴다. `DATA_INVENTORY.md`와
`DATA_SCHEMA_AUDIT.md`는 확보와 구조 점검 결과다. 다운로드했다고 검증용으로 적합한 것은 아니다.
데이터를 새로 맞춘 경우 parameter fitting과 별도 실험 검증을 구분하고, 같은 실험의
시간 행을 무작위로 나누어 독립 검증이라고 부르지 않는다.

채널 방출 자료의 유량 시간·질량유량은 명시된 단위로 읽는다. 농도 센서 시간의 단위와
상대 시간 정렬은 미확정이므로 기본 실행은 센서 이력을 보류한다. 명시적인 호출자 선언이
필요할 때에만 `--sensor-time-unit`를 사용하고 근거·가정을 별도로 남긴다.
AB2 자료에서는 확인된 벽 온도와 상대 시간만 읽는다. 벽 온도를 내부 bed 온도로
치환하지 않는다. 각 실험의 미확정 조건은 `DATA_QUALIFICATION.md`에 정리한다.

## 기존 모듈 연결과 연구 이어가기

LH2DT 연결은 `adapters/lh2dt.py`와 `research/native_lh2dt.toml`을 참고한다.
상태·유량은 실제 네이티브 객체를 주고받는다. 다른 저장소에 필요한 변경은 `requests/`에
별도로 정리하며, 현재 저장소가 그 기능을 이미 제공한다고 가정하지 않는다.
개발 재개 시 `HANDOFF.md`, `DEVELOPMENT_LOG.md`, `MODEL_CATALOG.md`와 관련 실험 기록을
함께 읽는다. 공개 전에는 실제 빌드 산출물의 파일 목록·라이선스·데이터 제외를 확인한다.

## 등온선·분극 곡선과 파라미터 적합

`observations.ObservationTable`은 시간축 없이 데이터를 보관한다. 각 열에는
`Variable`로 물리량·단위·기준을 붙이고, 각 행에는 원본 행 식별자와 실험 그룹을 붙인다.
출처는 열별로 측정·계산·재구성·미확정을 구분한다. `p/p`, STP 체적, 흡착량의
절대량·초과량 구분은 이름이나 숫자 범위만 보고 바꾸지 않는다.

`split_experiments`는 실험 그룹을 통째로 나눈다. `research.fit_observations`에는
`BoundedParameter`와 Python 예측 함수를 전달한다. 예측 함수 안에서 기존 네이티브 모델을
그대로 호출할 수 있다. 적합 결과에는 사용 데이터의 SHA-256, 변수 기준, 제외 행,
파라미터 경계 및 Jacobian 특이값을 남긴다. 수치 rank가 충분하더라도 과학적 식별성이
입증된 것은 아니다. 잔차가 작다는 이유로 신뢰구간이나 검증 완료 상태를 만들지 않는다.

전압 자료의 측정·계산 출처가 미확정인 경우 `purpose="curve_reproduction"`으로만
적합한다. 보류 곡선 비교는 `assess_held_out`을 사용하며 적합에 쓴 행이나 그룹을
다시 넣으면 거부한다. 같은 장치의 다른 온도 곡선이라는 사실만으로 독립 실험 검증을
주장하지 않는다. 실행 예시와 실제 결과는 다음 명령과 연결 문서에 있다.

```powershell
.venv\Scripts\python scripts/check_static_ingestion.py
.venv\Scripts\python scripts/fit_sofc_reproduction.py
```

자세한 계약은 `OBSERVATIONS_AND_FITTING.md`와 `research/sofc_reproduction.md`를 참고한다.

## 기존 PSA 모듈 연계

`adapters.psa.PsaDynaEquilibrium`은 실제 PSA-Dyna 평형 함수를 호출한다. Pa↔bar뿐 아니라
미분값의 단위도 변환한다. 재료·성분 순서·실험 기준·절대/초과 흡착량 정의를 일치시켜야 한다.
`PsaDynaBed`는 실제 loading-LDF 충전층의 SI 상태와 RHS를 제공한다. 유량은 성분별
mol/s, 에너지 전달은 명시한 네이티브 기준의 W이며 CoolProp 엔탈피 기준과 자동 호환되지 않는다.

현재 상온 닫힌 충전층의 수지 검증은 통과했다. 기존 엔진의 100 K 하한은 유지하며,
20 K 조건을 허용하는 변경은 물성·상변화·에너지 수지를 함께 확장해야 한다.
`NATIVE_ADSORPTION.md`와 `requests/005_psa_cryogenic_adsorption.md`에 계약과 인수 조건을 적었다.

## 공통 노즐과 저장조 방출

`release.HomogeneousIsentropicNozzle` 하나로 기체·액체·포화·두상 유입을 계산한다.
입력은 정체 상태 `ThermoState`, 절대 배압, 개구 객체와 개방 비율이다. 포화 상태는
P/T만으로 액체·증기·혼합물을 구분할 수 없으므로 CoolProp의 `saturated(P, quality)`처럼
명시적인 상태를 넘긴다. 이동하는 배관의 정적 상태를 그대로 정체 상태로 사용하면 안 된다.

```python
from h2physics.thermo import CoolPropProperties
from h2physics.release import HomogeneousIsentropicNozzle, NozzleOpening

properties = CoolPropProperties("ParaHydrogen")
state = properties.saturated(500_000., 0.2)
hole = NozzleOpening.circular("tank-A/nozzle-B", 0.002,
    effective_area_factor=0.8, area_basis_id="사용자가 선언한 유효면적 가정")
result = HomogeneousIsentropicNozzle(properties).solve(
    state, back_pressure_pa=101_325., opening=hole)
print(result.mass_flow_kg_s, result.regime, result.energy_residual_w)
```

유효면적 계수는 반드시 직접 선언한다. 질량유량 계수만으로 실제 수축 면적과 속도 손실을
따로 알 수 없으므로 출력 추력은 선언한 유효면적 가정에 따른 값이다. 균질 평형·무마찰·단열
가정이 적용되며 지연 비등·상간 속도 차이·긴 배관의 압력손실은 이 수준에서 풀지 않는다.
압력 탐색은 배압 끝점을 포함한다. 물성 오류를 건너뛰지 않으며, 격자 세분화로 유량·압력
수렴을 확인한다. 검증된 따뜻한 기체 물성표가 극저온 방출에서도 검증된 것은 아니다.

`Lh2dtBulkNozzleOutflow`를 기존 LH2DT 탱크의 유량 callback으로 바로 전달할 수 있다.
현재 네이티브 탱크는 유출 엔탈피를 평균 상태로 고정하므로 균질 혼합물 취출만 지원한다.
액상 배출관이나 기상 벤트는 요청서 001의 변경이 필요하다. 계산 중간 RK 단계는 소스 이력으로
저장하지 않고, 승인된 탱크 상태에서 `sample(t, state)`을 호출한다. 불연속 차단 명령은 적분
구간을 나누고 각 구간의 한쪽 경계 값을 적용한다.

`SourceHistory`는 시계·좌표계·위치·방향·개구·종료 사유를 보존한다. 노즐 출구의 액체 비율을
지면 유입량으로 바꾸지 않는다. 대기 팽창·액적·충돌·증발 계산이 더 필요하다. 기체와 극저온
유한 재고의 실제 연결 검증은 `scripts/check_release_integration.py`, 결과는
`research/native_release.md`, 상세 계약은 `RELEASE_AND_SOURCE.md`에 있다. 이 기록은
합성 조건에서의 수치 수지 확인이며 독립 실험 검증은 아직 수행하지 않았다.

## 공개 방출 실험을 연결한 연구 예제

`data.preslhy.load_discha_member`는 공개 PRESLHY DisCha 묶음의 선택한 실험을 원래
압축파일에서 직접 읽는다. 원본 workbook의 SHA-256, 개구 지름, 압력·온도·반력·장치
총무게의 독립 기록과 저자가 제공한 동기화 시각을 보존한다. 압력의 절대·게이지 기준과
게이지 기준 압력은 반드시 지정한다. 습도 신호는 백분율·분율 기준을 명시할 때만 읽는다.

일반 Excel 로더도 관측 이름 행, 시간 이름 행, 데이터 시작 행을 각각 지정할 수 있다.
`data.sampling.bin_means`에는 같은 시계의 구간 경계와 최소 샘플 수를 전달한다.
`linear_sample`에는 최대 연결 간격을 지정한다. 보간 범위 밖과 결측 구간은 마스크로
남기며, 자동 시계 이동·정렬·빈칸 채우기는 하지 않는다. 평균·보간 결과는 재구성 출처다.

```powershell
.venv\Scripts\python scripts/acquire_data.py --keys preslhy-discharge --maximum-mb 1400 --maximum-file-mb 260 --include-suffixes .zip .pdf --minimum-download-interval-s 60
.venv\Scripts\python scripts/compare_discha_release.py
```

서버가 HTTP 429를 반환하면 즉시 반복 요청하지 않고 그 자료의 남은 다운로드를 보류한다.
완료 파일만 체크섬으로 확인하며 실제 완료·보류 범위는 `research/data/` 기록을 따른다.
원본 자료는 Git과 배포물에 포함하지 않는다.

현재 예제는 1mm 상온 실험 4건의 압력과 닫힌 열전대 3개의 평균 온도로 재고를 재구성하고,
같은 조건에서 공통 노즐의 누적 유량을 계산한다. 하나의 실험을 통째로 보류한 결과
초기 구간 재고 대비 RMSE는 약 0.003612, 적합에 쓴 실험의 RMSE는 약 0.02265다.
온도는 관측 입력이며 탱크 에너지 방정식의 예측값이 아니다. 센서 간 온도 차이는 20K를
넘는 구간도 있어 평균 온도가 체적 평균 밀도를 정확히 대표한다고 보장할 수 없다.
적합한 약 0.6111은 장치·관측 조건에 종속된 유효계수다. 독립 유량 검증이나 보편적인
노즐 계수, 신뢰구간으로 해석하지 않는다. `PRESLHY_COMPARISON.md`에 계약과 한계를 적었다.

실자료에서 발견한 평평한 최대점은 단상의 음속 조건을 이용해 수렴성을 보강했다.
두상 음속은 만들어내지 않는다. CoolProp이 상 경계에서 극히 작은 음수 기상분율을
반환할 때 기본 동작은 오류다. `quality_roundoff_tolerance=1e-8`처럼 사용자가 예산을
명시하면 그 범위에서만 끝점 조정을 허용하고 원래 값과 최대 조정량을 보존한다.
엔탈피·밀도는 바꾸지 않으며, 임계 유량·압력 수렴 기준도 완화하지 않았다.

## 네이티브 설비를 연결한 공급 모델

`adapters.Lh2dtEquipmentNetwork`는 기존 LH2DT의 실제 그래프와 부품을 그대로 사용한다.
이 프로젝트는 `BoundaryPower`로 열과 축동력을 구분하고, `ConnectionTransfer`로 유량
방향·포트·유입 상태·전달 상태를 보존한다. 양의 열과 축동력은 유체에 들어가는 방향이다.
유량이 역전되면 실제 상류 노드도 바뀌며, 유량이 0이면 전달 상태는 없다.
현재 설비 원장은 정상 엔탈피 전달 수준이다. 포트의 유한 운동·위치 에너지는 포함하지 않는다.

펌프·배관·기화기·탱크의 방정식과 시간 적분은 네이티브 엔진이 담당한다. 연결할 때
`power_reader`를 직접 지정해 열·축동력을 가져온다. 열교환 링크에 다른 열원이나 축동력이
있는 유압 부품을 붙였다면 그 항도 포함해야 한다. 잘못된 원장은 수지 검사에서 거부한다.
`native_component_results`에는 펌프 맵·NPSH 같은 실제 네이티브 결과가 남는다.

`Lh2dtSharedValve`는 공통 노즐 커널을 네이티브 2포트 밸브로 연결한다. `.native`는 기존
형식이고 `.nozzle`은 진짜 노즐 출구와 수치 진단이다. 원격 혼합 포트가 전달하는 엔탈피와
노즐의 정적 엔탈피·운동에너지는 구분한다. 닫힌 경우 네이티브 숫자형 목 압력 필드는 호환용
자리값이므로 물리적 출구로 사용하지 않는다. `.nozzle.exit_state`는 이때 None이다.

성층 탱크의 액상 포트를 선택해 펌프–가열 배관–기화기–밸브를 연결한 예제를 제공한다.
기존 균질 탱크의 평균 혼합물 취출과 다른 모델 수준이다. 일반 동적 원장에 성층 탱크의
외부 열 두 항을 전달하는 `stratified_node_with_heat_ledger`도 추가했다. 기존 방정식은
유지하며, 닫힌 탱크에서 확인한 약 5.52J 원장 누락을 바로잡는다.

```powershell
.venv\Scripts\python scripts/check_lh2dt_property_provider.py
.venv\Scripts\python scripts/check_equipment_network.py
```

합성 조건의 2초 연결 계산은 약 3.09g을 전달한다. 전체 외부 질량·에너지 수지, 각 RK 단계의
부품 수지, 시간 간격 비교와 펌프 운전 조건을 확인했다. 수학적으로 수지가 닫혀도 NPSH
조건을 어기면 운전점으로 승인하지 않는다. 운동량 진단이 없는 부품은 None으로 남긴다.
중간 적분 단계는 소스 이력의 승인 시점과 구분한다. 유한 배관 재고·완전 차단·독립 설비
실험 검증까지 끝난 상태는 아니다.

속도는 기존 CoolProp EOS를 유지하면서 상태당 한 번만 플래시하는
`Lh2dtLowLevelProperties`로 개선했다. 60개 변환 비교가 통과했고, 상태 생성 시험에서는
약 22.7배, 동일 간격의 전체 연결 계산에서는 약 2.34배 빨랐다. 두 수치는 다른 작업이다.
극저온 물성표를 외삽하거나 지원하지 않는 메서드를 다른 엔진으로 자동 대체하지 않는다.
현재 지원하는 네이티브 API 부분집합과 실행 예제, 적용 한계는 `NATIVE_EQUIPMENT.md`,
실제 검증 값과 해시는 `research/native_equipment_network.md`에 있다.

## 배관·기화기 재고와 지정 시각 차단

`Lh2dtDynamicEquipment`는 기존 엔진의 유한 배관·기화기 모델을 연결해 실행한다.
각 장치는 유체 질량, 유체 내부에너지, 벽체 온도를 보존 상태로 유지한다. 장치별
`Lh2dtInventoryNode`에 실제 네이티브 노드와 재고 읽기 함수를 넣는다. 배관·기화기는
`lumped_inventory_reader(벽체_열용량, 물성_기준)`을 쓸 수 있다. 다른 상태 구조는
`ConservedInventory`를 반환하는 Python 함수를 직접 연결한다. 벽체가 둘인 성층 탱크에
단일 벽체 함수를 적용하면 안 된다. 그 탱크의 액상·기상·두 벽체 에너지를 모두 읽어야 한다.

질량 변화는 경계 질량 이송 적분과, 유체·벽체 에너지 변화의 합은 경계 엔탈피 이송과
외부 열 적분의 합과 비교한다. 유체와 벽체 사이의 열은 내부 교환이므로 전체에서 상쇄한다.
열역학 기준에 따른 음의 내부에너지는 가능하다. 기준 에너지의 절대값이 크다는 이유로
수지 오차 허용치를 늘리지 않고 실제 변화량과 이송량을 기준으로 검사한다.

```powershell
.venv\Scripts\python scripts/check_dynamic_inventory.py
```

합성 예제는 0.137초에 공급을, 0.411초에 출구를 닫는다. 두 시각은 기본 시간 간격과
일치하지 않으므로 적분 구간을 그 위치에서 나눈다. 닫기 전 마지막 RK 단계에는 이전
밸브 상태를, 다음 구간에는 닫힌 상태를 사용한다. 공급을 닫은 뒤에도 약 4.66mg이
남은 재고에서 방출된다. 출구까지 닫으면 외부 질량 이송은 멈추지만 내부 재분배와
가열은 계속된다. 출구 유량이 0이라는 조건이 재고 0을 뜻하지 않는다.

`run(..., clock_id=..., start_time_s=...)`의 명령과 결과는 같은 절대 운전 시각을 쓴다.
구간마다 0으로 다시 시작하는 네이티브 내부 시각은 어댑터가 변환한다. 온도·미분·연속
제어 콜백에도 절대 시각을 전달한다. 같은 시각의 명령은 입력 순서대로 한 번 실행한다.
명령은 기기 모드를 바꾸며, 유한 재고의 압력·엔탈피를 직접 덮어쓰려 하면 거부한다.
압력에 반응해 임계 시각을 찾는 제어는 아직 이 지정 시각 API의 검증 범위가 아니다.

`result.steps`는 승인된 시점만 담고 실제 네이티브 상태와 부품 결과를 유지한다. 명령
시각에서 해당 단계의 기기 결과는 닫기 직전 값이다. 직후 값은 `result.transitions`의
`after`에서 읽는다. 두 유량을 임의로 직선 보간하면 차단 시각의 방출량이 달라진다.
승인 결과는 실제 네이티브 해 객체의 동일성으로 찾으므로 RK 호출 횟수를 추정하지 않는다.

세 시간 간격, 역방향 이송, 절대 시각의 해석적 벽체 가열 조건을 확인했다. 시간 구간을
나누지 않은 제어는 자체 수지가 닫혀도 최종 질량이 약 0.70mg 달라졌다. 따라서 수지와
명령 시각은 별도로 검증한다. 잘못된 벽체 열용량, 외부 열 누락, 승인 결과 불일치도
거부한다. 잘못된 계산을 질량 잘라내기나 다른 물성 엔진으로 자동 대체하지 않는다.

이번 유한 장치 예제의 외부 공급은 저장조 경계다. 앞의 유한 성층 탱크·펌프 계산과
이번 배관·기화기 재고를 하나의 과도 설비로 합친 검증은 남아 있다. 유동 파동, 공간
분포, 상 완전 소진, 밸브 구동 시간·기밀성, 서리와 독립 설비 실험도 추가해야 한다.
구체적 API와 예제 구성은 `DYNAMIC_INVENTORY.md`, 입력·수치·해시는
`research/native_dynamic_inventory.md`에 기록했다.

동적 배관 냉각량은 `audit_dynamic_line_cooldown()`으로 승인된 native run과 연결한다.
호출자는 같은 운전 시계·시간 구간에서 계산한 유입 수소 질량 적분과 입출구 엔탈피
차를 제공한다. `integrate_unidirectional_equipment_rate()`는 승인 표본 각각의 부호를
보존하고 관측된 역류를 거부한다. 표본 사이 역류 여부는 시간 간격을 줄여 확인한다.
선택한 배관 경계의 에너지 이송이 냉각 수소 하나뿐이라는 전제는
`coolant_only_energy_transport=True`로 호출자가 선언해야 하며 함수가 자동 추론하지 않는다.
함수는 배관의 native 이송 엔탈피, 주변 열, 저장에너지 변화와 필요
수소 질량을 분리해 반환한다. native 배관 수지가 닫히지 않거나 운전 시계/물성 기준이
맞지 않으면 거부한다. 총 유량은 승인 표본 사다리꼴 적분이므로 별도 시간 간격 수렴을
확인해야 한다. `compare_unidirectional_equipment_integrals(coarse, fine)`은 동일 운전
시계·구간·trajectory ID가 같고 coarse 시간이 fine 표본에 포함되는 적분의 변화량과 interval 비율을 보고한다.
호출자가 정한 정규화 허용치 충족 여부도 기록하며, 그 결과를 audit에 보존할 수 있다.
이는 오차 상한이나 수렴 증명은 아니다. 연결 계약은 아직 과학 검증되지 않았다.
`integrate_unidirectional_equipment_rate()`가 만든 적분은 원본 run, accepted equipment
snapshot들과 rate reader를 보유한다. `audit_dynamic_line_cooldown()`은 동일한 run에서
만든 적분만 받으며, `require_current()`는 원본 snapshot lineage와 재계산한 rate를 함께
확인한다. 다른 모듈로 전달하기 전 `coolant.require_current()`,
`refinement.require_current()`, `audit.require_current()`를 호출하면 원본과 파생 receipt의
사후 변경을 검사한다. 이 연결 계약은 아직 실행 검증되지 않았다.

## 유한 탱크·펌프·배관·기화기를 하나로 조립하기

`assemble_lh2dt_supply`로 성층 탱크의 액상 포트, 맵 기반 펌프, 재고가 있는 배관,
명시적인 저항 배관, 재고가 있는 기화기와 출구 밸브를 연결할 수 있다. 네이티브 모델과
초기 상태를 직접 넣으므로 형상, 펌프 맵, 열전달 계수, 벽체 용량과 초기 충전량을
교체할 수 있다. 모든 기기는 같은 물성 인스턴스를 사용해야 한다. 서버나 JSON 변환은
필요 없다. 조립 함수가 추가 배관 반쪽을 자동 삽입하지 않으므로 저항·체적을 중복 계산하지 않는다.

반환된 `assembly.driver`로 계산하고 `assembly.pump`, `assembly.outlet`에 명령을 준다.
`assembly.native_models`와 승인 단계의 실제 네이티브 상태·부품 결과도 계속 접근할 수 있다.
성층 탱크 재고는 `stratified_inventory_reader`가 액상·기상과 두 벽체를 모두 합산한다.
기본 노드 이름은 `node_ids`로 변경할 수 있다. 다른 토폴로지는 기존 그래프 API로 직접 구성한다.

`Lh2dtModeSwitch`는 운전 모드마다 실제 부품과 그 부품의 열·축동력 읽기 함수를
지정한다. 운전 중에는 기존 펌프 결과를, 예제의 차단 모드에서는 이미 닫힌 공통 밸브
결과를 사용한다. 다른 기기에도 같은 선택 인터페이스를 적용할 수 있다. 수렴 실패나
맵 범위 초과가 임의로 차단 모드를 선택하지 않는다. 기밀성·펌프 감속·케이싱 재고·모터
손실을 포함하려면 그 상태와 입력이 필요하다. 현재 예제는 이상적인 순간 정지·차단
한계이며, 실제 정지 기계 모델의 확장 조건은 요청서 008에 정리했다.

```powershell
.venv\Scripts\python scripts/check_finite_supply.py
```

통합 합성 예제는 0.037초에 공급 펌프 조립체를 차단하고 0.073초에 출구를 닫는다.
짧은 계산의 총 전달량은 약 30.35mg이며, 이 중 약 15.10mg이 공급 차단 후에 나온다.
탱크·배관·기화기 각각의 재고 수지와 전체 외부 수지를 별도로 검사한다. 외부 검사는
관측 시점의 출구 질량·엔탈피·축동력을 적분하고, 모든 벽체 온도와 명시한 UA로
주변 열을 다시 계산한다. 펌프 일을 누락하거나 맵 밖 운전점을 넣으면 거부한다.

`integrate_equipment_rate`에 결과와 읽기 함수를 넣으면 승인 표본의 사다리꼴 적분을
명시적으로 수행한다. 차단 직전·직후 값을 모두 넣어 차단 지점을 가로지르는 삼각형
면적을 만들지 않는다. 결과에는 물성 기준, 속도량·적분량 단위, 시계·시간 구간과
방법 이름이 남는다. 부호는 그대로 유지한다. 이것은 표본 사이를 선형으로 연결한
적분이므로 네이티브 RK 단계의 적분과 구분하고 시간 간격을 줄여 오차를 확인해야 한다.

1초까지의 밀폐 가열에서는 내부 이송 방향이 바뀐다. 처음 비교한 0.0025/0.00125초
간격은 수지는 닫혔지만 최종 상태 오차 기준을 넘었다. 허용치를 유지하고
0.00125/0.000625초로 줄이면 그 기준은 통과했지만, 추가 Darcy 검사에서 별도 문제가
드러났다. Reynolds 수 약 2296의 한 점에서 기존 엔진은 잔차를 0으로 보고했으나
최종 마찰계수·유량으로 재계산한 압력손실은 약 44Pa 어긋났다. 같은 불연속 마찰식을
근 풀이로 바꾸기만 해도 해가 없는 구간이 남아 거부된다. 공통 Darcy 근 풀이와
명시적으로 선택한 fluids의 연속 Churchill 상관식으로 고쳤다. 점성·상 상태는 기존
HEM 모델에서 가져온다. 상관식 변경과 수치 수렴 개선은 구분하며, 실제 이상유동의
실험 정확도가 높아졌다고 주장하지 않는다. 상세 조건은 `HYDRAULICS.md`와 요청서 009에 있다.
따라서 짧은 구간의 성공을 긴 가열·다른 운전 조건에 그대로 확대 적용하면 안 된다.

직접 조립하는 코드와 부품 교체 방법은 `FINITE_SUPPLY.md`, 정확한 입력·검증 결과와
해시는 `research/native_finite_supply.md`에 있다. 압력 트리거, 상·질량 완전 고갈,
공간 분포·유동 파동, 실제 기계·밸브 운동과 독립 설비 실험은 추가 개발·검증 범위다.

## PEM 수전해 실측 임피던스와 파라미터 연결

`.[eis]`를 설치하면 impedance.py의 실제 `CustomCircuit` 객체를 선택적으로 연결할 수
있다. 회로 요소·파서는 기존 엔진을 사용하고, 파라미터 추정·SVD·전체 실험 구간 비교는
이미 있는 공통 API를 쓴다. 주파수 응답은 한 운전점 주변의 작은 전기적 변화에 대한
근사다. 기존 정적 전압·Faraday·에너지 모델과 구분하며 공정 적분기를 하나 더 만들지 않는다.

```powershell
.venv\Scripts\python -m pip install -e ".[eis,test]"
.venv\Scripts\python scripts/replay_data.py pem-crossover
.venv\Scripts\python scripts/check_pem_ingestion.py
.venv\Scripts\python scripts/fit_pem_impedance.py
```

공개 CC BY 4.0 데이터의 네 셀 CSV 약 2,376만 행을 모두 해시 검사한다. 모델 입력은
초기 두 POL_GEIS 프로토콜에서 고른 14,971행과 144개 주파수 스윕이다. 0 Hz·0 Ω은
직류 구간의 자리 표시 값이므로 수치를 보존하면서 스펙트럼에서 마스킹한다. 각 셀의
시간·원본 행·프로토콜 번호를 보존한다. 명목상 17단계와 달리 실제로는 18회 측정이며,
마지막 전류가 셀에 따라 12 A 반복 또는 14 A이다. 이를 임의로 삭제하지 않는다.

`load_pem_csv`에 바이너리 스트림, 셀·출처, 프로토콜·카운터, 활성 면적과 위상 부호를
직접 넣는다. `pem_spectra`는 직전 직류 유지 구간으로 운전점을 복원한다. 재현 스크립트는
최대 120초 간격을 명시적으로 선택하며, 이를 넘는 28개 스펙트럼의 운전점은 미상으로 둔다.
AC 측정 중 흔들리는 전류를 반올림해 운전점으로 쓰지 않는다. 블록 온도는 반응 온도와
같지 않으며, 희소한 GC 농도를 보간하거나 막 투과 유량으로 바꾸지 않는다.

`NativeCircuitOperator`에 네이티브 생성자, 회로 문자열과 순서가 명확한 파라미터 이름을
넣는다. `.evaluate`는 실제 회로 객체와 읽기 전용 복소 배열·네이티브 단위를 반환한다.
`ImpedanceSpectrum.cartesian_observations()`는 공통 관측 테이블로 변환한다. 실수·허수
두 행은 같은 측정의 상관된 성분이므로 독립 실험 두 개로 세면 안 된다. API를 직접
호출하고 객체·배열·함수를 교체할 수 있으며 JSON이나 서버를 요구하지 않는다.

실제 예제는 각 셀의 첫 12 A 스윕 한 개에 같은 회로·초깃값·경계를 적용한다. 적합 오차는
작았지만 전체 스윕을 보류한 8개 비교 중 4개가 사전 기준을 넘었고, Reference 계수를 다른
세 셀에 그대로 전달한 결과도 모두 기준을 넘었다. 실패를 지우거나 기준을 바꾸지 않았다.
수치 조건수는 약 3,209~69,680이며 일부 파라미터는 경계에 도달한다. 회로가 곡선에 맞는다고
전극 반응·막 저항·촉매·열화 원인을 고유하게 식별한 것은 아니다. CPE의 Q도 일반적으로
단순한 정전용량이 아니다. 데이터 불확도·선형성·독립 출처 검증은 추가 과제다.

R0×활성 면적을 기존 `OhmicLoss`의 함수 입력으로 바로 연결하는 예제도 포함했다.
단위가 맞는 연결을 확인한 것이며, 접촉·배선 등의 기여를 분리하지 않고 막의 고유 저항으로
해석하거나 기존 옴 손실과 중복 합산하면 안 된다. 상세 Python 예제·변수·변환·재현 절차는
`PEM_IMPEDANCE.md`, 실제 계수·보류 비교·해시는 `research/pem_impedance.md`에 있다.

## 동적 액체수소 풀과 보존적인 증발 소스

`.[pool]`은 DynamicLH2PoolX 0.2.0rc2를 설치한다. 기존 엔진의 반경 방향 확산·액체 재고·
접촉 시간 기반 열전달·증발 계산을 그대로 사용한다. `DeclaredGroundInflow`에는 실제
네이티브 유입 객체, 이미 지표에 도달한 포화액 상태, 유한 시간 구간, 시계·좌표계와 출처를
넣는다. 노즐 출구의 액체 비율을 지표 유입량으로 자동 변환하지 않는다. 현재 엔진은
normal Hydrogen을 고정 사용하므로 para-hydrogen 상태를 연결하면 거부한다.

```powershell
.venv\Scripts\python -m pip install -e ".[pool,test]"
.venv\Scripts\python scripts/check_pool_integration.py
```

`NativeDynamicPool`에 실제 계산 함수, 물성 객체, 엔진 식별자와 허용치를 넣고, `.run`에
네이티브 설정·유입·출력 시각·증발 소스 위치를 직접 전달한다. 반환값에는 실제 결과·설정·
입력 객체와 별도로 다시 계산한 질량수지 검사가 남는다. 원래의 단계형 유입량을 적분해
공급·잔류 액체·증발·영역 유출·수치 질량 조정을 비교한다. 기본 수치 조정·영역 유출
허용량은 모두 0이다. 실패 결과도 보존하고, 진단 모드가 실패한 소스를 정상 소스로 내보내지는 않는다.

이 검사에서 네이티브 시간 비교 문제를 재현했다. 차단 시각 바로 앞에 남은 부동소수점
오차 때문에 공급이 한 단계 더 이어져 0.25 g이 추가되었지만 내부 수지 잔차는 거의 0이었다.
양성 예제는 시간 오차 예산 1e-10초를 명시해 실제 네이티브 입력 함수에 알려진 경계 시각을
전달한다. 모든 보정이 남고 최대 보정은 약 4.44e-15초였다. 기본 시간 예산은 0이며, 엔진
내부를 바꾸거나 질량 허용치를 완화하지 않는다. 근본 수정과 물성·재시작·소스 개선은 요청서 010에 있다.

공급을 끊어도 풀의 액체가 남으면 증발은 계속된다. 합성 예제는 약 28.25 g을 공급하고
차단 뒤 약 24.42 g을 더 증발시킨다. 2초의 보고 반경은 0이지만 액체 약 16.23 g이 남는다.
보고 반경은 깊이 검출 기준에 따른 값이므로 이를 실제 젖은 면적이나 완전 소멸과 같게
취급하면 안 된다. 매우 작은 잔류 질량도 임의로 0으로 바꾸지 않는다.

`IntervalMassSource.require_current()`로 다른 모델에 넘기기 전 원본 위치, 물성 상태,
근거·종료 의미, 시간/질량 구간이 생성 뒤 바뀌지 않았는지 확인한다. 질량 조회·유량·window·
rebin 메서드도 자동 확인하며, downstream adapter는 변조된 source를 다시 해시해 승인하지 않는다.
이 검사는 객체 변경을 감지할 뿐 측정이나 예측의 물리적 정확성을 보증하지 않는다.

`evaporation_source()`는 누적 증발량 차이로 `IntervalMassSource`를 만든다. 각 시간 구간의
질량과 평균 유량을 구분하고, 다른 구간으로 다시 나눠도 총 질량을 보존한다. 서로 다른
시계나 구간 밖 외삽은 거부한다. 구간 내부를 일정 평균으로 나타내는 선택이므로, 세밀한
변동을 새로 복원한 것은 아니다. 순간처럼 보이는 드문 출력값을 사다리꼴 적분한 결과는
이 예제에서 약 31.96 g으로 과대 계산된다. 실제 방출 질량은 약 28.25 g이다.

격자·시간을 줄인 세 비교는 사전 재고 기준을 넘었고 더 세밀한 비교에서 약 0.734%로
통과했다. 시간 비교는 작지만 단조 감소하지 않아 수렴 차수나 통계적 불확도로 해석하지
않는다. 현재 전달 경계는 질량과 포화증기 상태이며, 미확정인 구간 면적·수직 운동량·
대기 혼합이나 독립 열수지를 자동 생성하지 않는다. 원시 실험을 사용한 정확도 검증도 아니다.

관련 PRESLHY E3.4의 11개 첨부자료는 CC BY-SA 조건을 확인해 현재 재사용 정책에서 확보를
보류했다. 출처·저자·버전·메타데이터 해시와 보류 파일 목록은 남겼다. 상세 객체 사용법은
`NATIVE_POOL.md`, 수치 검증·실패 사례·해시는 `research/native_pool.md`에서 확인할 수 있다.

## 기체 노즐과 기존 DEGALI 제트 연결

`h2physics.adapters.degali`는 공통 노즐의 결과를 실제 DEGALI 팽창·제트 객체에 전달한다.
노즐을 다시 풀거나 제트 방정식을 복제하지 않는다. 가스 상태의 수소·파라수소를 대기압
방출면으로 바꾸는 질량·운동량·에너지 전달을 확인했고, 짧은 무풍 수소 제트의 수치 기준을
통과했다. 차가운 파라수소 제트는 정밀 격자에서도 에너지 기준을 넘었으므로 사용 가능한
검증 사례로 분류하지 않는다. 현재 72개 모델군 중 16개 부분 모델과 14개 네이티브 연결
수준이 있으며, 전체 시설·사고 모델이 완성된 상태는 아니다.

설치는 별도 정확한 소스 버전을 사용한다. 네이티브 버전 문자열은 0.3.0이며, 현재 PyPI의
0.1.0을 같은 구현으로 취급하지 않는다. 다음 명령의 마지막 검증은 두 유체를 모두 검사해
현재 파라수소 에너지 실패 때문에 0이 아닌 종료 코드를 반환한다. 보고서는 먼저 보존된다.

```powershell
.venv\Scripts\python -m pip install -e ".[thermo,test]"
.venv\Scripts\python -m pip install -r requirements/native-degali-pinned.txt
.venv\Scripts\python scripts/check_degali_integration.py --plot
```

`NATIVE_JETS.md`의 전체 Python 예제는 통과한 수소 조건을 그대로 실행한다. 입력·물성
객체·실제 네이티브 설정·실행 옵션을 직접 바꿀 수 있으며 JSON이나 서버를 거치지 않는다.
실제 엔진과 결과는 `run.model`, `run.native`에 남아 다른 Python 모듈에서 바로 사용할 수 있다.

`expand_nozzle_gas`에는 다음 의미를 명시해야 한다.

- `SHARED_AREA`: 노즐의 유효 유동 면적을 압력 추력의 면적으로도 쓰는 폐쇄 조건이다.
  명목 구멍 면적이나 속도 계수와 자동으로 바꾸지 않는다. 두 면적이 다른 실물 모델은
  별도의 네이티브 확장·검증이 필요하다.
- `location`, `location_basis_id`: 가상 대기압 방출면의 위치와 그 근거다. 팽창 모델이
  축 방향 위치를 예측한 것으로 해석하지 않는다.
- `PropertyProvider`: 동일한 유체·스핀·엔탈피 기준을 유지한다. 수용 압력/엔탈피에서
  온도·밀도를 다시 확인하고 액체·액적·혼합 품질은 이 기체 경계에서 거부한다.

`JetPlane`은 전역 좌표계에서 서로 직교하는 수평·수직 축과 지면 원점을 정한다. 방출면
위치·방향이 이 단면을 벗어나면 거부한다. `axisymmetric_boundary`는 실제 네이티브
소스/엔탈피 팩토리에 정적 엔탈피 차이와 별도의 절대 수소 기준을 전달한다. 수용 모델이
자기 성분 기준으로 변환할 때 운동에너지를 중복해서 더하지 않도록 분리한 것이다.

현재 밀도 분포 방식의 초기 보존식은 두 자체 사례에서 해를 닫지 못한다. 온도·조성을
독립적으로 표현하는 방식을 명시적으로 선택하면 초기 네 보존식을 만족하지만, 이때의
밀도는 가우스 밀도차 분포가 아니다. `profile_integrated_buoyancy_type`은 실제 엔진의
하위 클래스를 반환해 수직 부력 항만 그 단면의 실제 밀도 적분으로 바꾼다. 나머지
분포·야코비안·공기 유입·적분은 기존 엔진에 맡긴다. 계수를 실험 곡선에 맞춰 바꾸거나
엔진 파일·전역 함수를 수정하지 않는다. 동반 유동은 현재 연결에서 허용하지 않는다.

`run_axisymmetric_jet`는 초기 네 보존식, 수소 질량, 수평 운동량, 엔탈피+운동에너지,
기준 변환과 지면 간격을 검사한다. 에너지는 큰 항의 상쇄 때문에 순 에너지 값만으로
정규화하지 않고 원래 엔탈피·운동에너지 항의 크기를 함께 사용한다. 절대 W 오차도 남긴다.
정밀 수소 사례의 최대 에너지 수지 오차는 약 0.025 W다. 파라수소는 641점에서도 약
0.346 W로, 사전 기준 약 0.238 W를 넘었다. 이는 수치 수지 오차이며 실험 예측 오차가 아니다.
기본값에서는 `JetCouplingError`가 발생하고 `error.run`에서 실패한 결과를 확인할 수 있다.
`require_closed=False`는 진단용 결과 확인을 허용하지만 실패 상태를 지우지 않는다.

`radial_observations`는 거리·반경·전체 혼합물 수소 질량분율·벌크 밀도·온도를 불변
`ObservationTable`로 반환한다. 응축된 공기 성분이 있으면 이 질량분율은 기상 센서의
몰분율과 다르다. 전체를 기체라고 놓고 변환해 실험 농도와 비교하지 않는다. 측정 자료를
붙일 때는 기상/전체 혼합물 기준, 센서 위치·부피·응답, 방출 조건과 관측 연산자를 먼저
맞춰야 한다. 계산 범위 밖 표본은 거부하며 정상 공간 계산에 가짜 시간 축을 만들지 않는다.

이 모델은 차단 후 유한 질량의 이동 시간, 지면 충돌, 장애물·횡풍, 스핀 전환이나 완전한
실제 혼합물 EOS를 해결하지 않는다. 풀 증기도 면적·운동량·상태가 확인되어야 제트와 연결할
수 있다. 관련 확장은 `requests/011_degali_profile_flux_and_source_contracts.md`에 별도로
작성했다. 초기 기체 연결 단계는 자체 입력으로 검사했으며, 이어지는 공개 실험 자료 적용은
아래 절에서 설명한다.

## 목표 대비 진행과 공개 공간 제트 실험

전체 프로그램의 작업량 기준 진행은 현재 약 **25-35%**로 추정한다. 정확히 측정한 과학적
완료율은 아니다. 72개 모델군 중 16개 부분 구현과 14개 기존 엔진 연결, 즉 30/72의 첫 실행
범위 약 42%와 구분한다. 이들 모델군 내부에도 추가 물리·실험 검증·설비 통합이 남아 있다.
`PROGRESS.md`에 단계별 근거와 남은 작업을 기록했다.

HyTunnel-CS 공개 자료의 농도 파일 4개에서 42개 시트·5,256개 공간 센서 행을 읽었다.
각 행은 시간 표본이 아니라 축 방향 위치를 옮겨 측정한 공간 관측과 평균·최대·최소 통계다.
반복 헤더에서 센서 위치가 바뀌는 경우도 보존한다. 압력·온도 표기가 충돌하는 시트,
He/H2 표기가 충돌하는 시트, 음수·누락·통계 순서 오류는 임의로 수정하지 않는다.
정상적인 0은 유효 관측으로 남긴다. 상세 API는 `HYTUNNEL_JETS.md`에 있다.

```powershell
.venv\Scripts\python scripts/acquire_data.py --keys mechanical-ventilation --include-suffixes .xlsx .zip .pdf --maximum-mb 20 --maximum-file-mb 15 --workers 1
.venv\Scripts\python scripts/compare_hytunnel_jets.py --native-packages artifacts/native_dispersion_packages --plot
```

현재 전체 비교 명령은 기준 미달 결과를 먼저 보존한 뒤 0이 아닌 종료 코드를 반환한다.
`--case d4_m1`이나 `--quick`은 제한된 진단이며, 그 결과로 전체 공개 기록을 덮어쓰지 않는다.
`--plot`에는 별도 Matplotlib가 필요하다. 출처는 Grune·Sempert의
[공개 데이터](https://doi.org/10.5281/zenodo.4668554), CC BY 4.0이며 원본 그림을 복제하지 않는다.

`infer_nozzle_stagnation_pressure`는 명시한 수소 T0·면적과 측정 유량에서 기존 노즐을
역산한다. 결과 압력은 해당 가정에서의 등가 입구 압력이며 측정값이 아니다. 배관 계측
압력을 곧바로 노즐 정체압으로 넣거나, 유량 하나로 정체압·방출 계수·온도를 동시에
추정하지 않는다. 온도 가정과 유량 근거, 압력 구간·단조성 표본·최종 수지 오차를 기록한다.

일부 실제 조건에서는 기존 초기 보존식의 순 에너지가 작은 값으로 상쇄되어 수치 해를
찾지 못했다. `hydrogen_energy_gauge_type`은 실제 네이티브 하위 클래스에서 에너지를
`E + C × 수소 질량유량`으로 표현하고 소스 기준도 동일하게 바꾼다. 물성표·물리 분포·
계수·근 찾기·적분기는 기존 엔진에 둔다. 검사할 때는 원래 에너지로 되돌리며 허용 오차를
넓히지 않는다. 원시 네이티브 에너지는 선택한 기준이고 `run.physical_energy_flux_w`는
원래 모델 기준으로 되돌린 불변 배열이다. 혼합물 전체 유량으로 수소 기준을 보정하지 않는다.

기준 C와 2C를 사용한 초기 상태와 전체 관측값을 비교했다. 원래 물리 기준의 통과·실패
판정도 유지됐다. 이는 초기 수치 조건을 개선한 것이며, 남은 적분 수지나 농도 예측 오차를
없앤 것은 아니다. 무풍 5조건 중 정밀 계산 4개는 수치 수지를 통과했지만, 4 mm / 1 g/s는
에너지 기준을 넘었다. 농도 RMSE는 약 0.91-2.90 퍼센트포인트, 최대 차이는 6.49-18.07
포인트로, 5조건 모두 사전에 정한 정확도 기준 일부에 미달했다. 계수를 이 자료에 맞추지 않았다.

`observe_native_gas_jet`는 센서의 상대 좌표를 실제 곡선 제트 경로에 투영한다. 건조 기체,
200-300 K·200 kPa 이하에서 기상 부피분율을 근사하며, 응축 혼합물의 전체 질량분율을
그대로 기상 센서 값으로 바꾸지 않는다. 축 범위 밖은 외삽하지 않고, 반경 방향 꼬리는
마스크 또는 실제 네이티브 가우스 분포 연장 중 하나를 명시한다. `ground_vertical_coordinate_m=None`
은 지면이 없는 상대 자유장 모델을 명시하므로 실제 방출 높이를 만들어 넣지 않는다.
흡입 프로브 응답, 습도, 벽·바람·미확정 T0와 소스 위치 가정은 독립적인 적용 한계다.

자동 테스트는 183개를 통과했다. 모델 보존식 검증, 실험 정확도, 시설 안전 적용 판정은
각각 별도로 남긴다. 실제 비교 결과·실패·입력과 코드 해시는 `research/hytunnel_jets.md`,
기존 엔진에 필요한 공개 에너지·관측·적분 계약은 확장 요청서 011에서 확인할 수 있다.

## 저장체 반응량·수소량·반응열 연결

`CARRIER_REACTIONS.md`에는 유한 재고와 지정 반응량을 사용하는 Python 예제가 있다.
`StoichiometricReaction`에 성분의 원자수·전하·분자량·상과 반응계수를 넣고,
`convert(초기_몰수, extent_mol=반응진행량)`으로 남은 저장체와 생성 수소를 계산한다.
정방향과 역방향 모두 실제 남은 성분이 허용하는 범위에서만 계산한다. 배열은 읽기 전용이며
질량 오차와 끝점 부동소수점 보정량을 결과에 남긴다. 반응속도를 이 값으로 가정하지 않는다.

확보한 공개 QM9-LOHC 10373행을 실제 RDKit 분자로 검사했다. 고유 분자 쌍은 10345개다.
반복된 28쌍은 엔탈피가 서로 달라, 해당 56행의 열량을 자동 모델 입력에서 보류한다.
원본 행·열값·출처·체크섬을 남기고 평균이나 첫 값을 선택하지 않는다. 따라서 모델 입력에는
`audit_qm9_lohc_dataset`을 사용해야 한다. 단일 행 검사만으로 중복의 모순을 찾을 수 없다.

허용된 10317행의 반응열은 계산 자료이며 기상 탈수소화, 298.15 K·101325 Pa 기준이다.
원본은 수소 1몰당 kJ이므로 수소 화학양론 계수를 곱해 반응진행량 1몰당 J로 바꾼다.
양의 열은 물질에 공급하는 열이다. 액상이나 다른 온도에 적용하려면 적합한 상별 물성과
반응 에너지 기준이 필요하다. CoolProp의 임의 현열 기준을 서로 다른 화학종의 생성열로
바꾸어 합산할 수 없다. 계산된 유기 분자라고 해서 실제 액체·안전한 저장체가 되는 것도 아니다.

`FunctionalMolarEnthalpy`로 자체 물성 함수를 연결하거나 `CanteraMolarEnthalpy`로 실제
Cantera 기체 물성을 재사용할 수 있다. 공급 열과 지정 반응진행량에서 생성물 온도를 풀되,
촉매 반응속도나 평형 전환율을 계산한 것으로 해석하지 않는다. 기체 평형과 반응기 시간 적분은
기존 Cantera 인터페이스를 사용한다. 이 단계까지 전체 자동 테스트는 204개를 통과했다.

## 선호 확산 엔진과 진행률 보고

고압 기체수소는 HyRAM, 액화수소에서 시작한 확산은 SLABx-LH2를 우선한다.
현재 기상이라고 해서 액체수소 풀에서 나온 증기를 고압 기체 방출로 바꾸지 않는다.
DEGALI는 비교 연구용으로 남기며 선호 엔진이 실패하면 자동으로 대체하지 않는다.
`PREFERRED_DISPERSION.md`에 실제 객체 입력, 호환 환경, 실행 명령과 한계를 정리했다.

지연 실행 시나리오는 `h2physics.dispersion.DispersionScenario`에
`HydrogenReleaseFamily`와 어댑터 입력 매핑을 전달해 만든다. `scenario.provider_id`로
선택된 제공자를 확인하고 `scenario.run()`으로 실행한다. 반환된 `DispersionExecution`은
기원·제공자·소스 증거 ID·어댑터 결과와 제공자가 보고한 수락 상태를 함께 보존한다.
고압 기체는 HyRAM, 액화수소
기원은 SLABx-LH2로만 전달되며, 반대 경로 입력은 자동 대체 없이 거부한다. LH₂ 경로의
입력 소스는 이미 형성된 일정 수소 증기 방출과 고정 발자국 면적을 뜻한다. 액체 방출,
풀의 퍼짐·증발, 가변 증기 유량은 이 연결에서 계산하지 않는다. 세부 인자와 호출 가능한
함수 API는 `docs/API.md`와 `PREFERRED_DISPERSION.md`를 참조한다.

HyRAM 6.1은 별도 SciPy1.16.3 환경에서 실행되지만 이번 입력의 가우스 초기화 수소
유량은 상류의 약 76.69%여서 엄격한 소스 수지 기준에서 보류한다. SLABx-LH2의
일정 증기 방출은 질량·적용 조건을 확인했고, 저풍속 적용 한계는 실패로 남겼다.
8개 연계 계약 테스트를 추가해 이 단계의 전체 212개를 두 SciPy 환경에서 통과했다.
이는 새로운 실험 정확도 검증이나 모델군 추가 완료를 뜻하지 않는다.

앞으로 주요 작업 완료·실패·의미 있는 전환마다 전체 작업량 추정, 초기 실행 모델군
비율, 수치검증과 실험검증 상태를 함께 보고한다. 계산은 로컬 프로세스에서 수행하며
독립적인 데이터·물성·모델 개발은 병렬로 진행한다. 설치·조사·요청서 작성만으로
완료 비율을 올리지 않는다. 현재 전체 추정은 25-35%, 초기 실행은 31/72개다.

## 병렬로 추가한 실험 자료·혼합물·유한 기체 수지

PRESSURE_PEAKING_DATA.md는 실제 확보한 MAT8개·XLSX9개의 전체 검사와 블록 읽기를 설명한다.
유량 기록7999992행, 압력 기록33310586행, 센서 기록78272행을 검사했지만, 별도 장비의
시계를 자동으로 맞추거나 음의 유량을0으로 바꾸지 않는다. 계기 압력의 절대/게이지 기준,
농도 기준과 가이드/내보낸 채널 충돌도 남긴다. 따라서 바로 모델 경계로 간주하면 안 된다.

FROZEN_GAS_PROPERTIES.md의 실제 Cantera 혼합물 물성은 기존 공통 노즐을 재사용한다.
H2 기작 물성의 스핀은 미확정이며 CoolProp의 normal/para 기준과 자동으로 섞지 않는다.
엄격한 조성 검사가 기본이다. 네이티브 미분 계산의 합계 이탈에 한해 호출자가 허용량과
근거 ID를 명시하면 보정 종·부호·양을 기록한다. 음의 성분을 잘라내지는 않는다.

OPEN_GAS_VOLUME.md의 개방 기체 제어체적은 실제 네이티브 반응기·유량 장치·벽·적분기를
보존한다. 유한 질량·조성·온도·압력과 경계 열량을 계산하고 수지를 확인한다. 이는 공간
농도나 층상 확산을 대신하는 모델이 아니라0D열역학 기준 수준이다. 검증된 물성으로 공통
노즐을 연결한 배출 경계도 실행했다. 현재 최초 실행 범위는33/72개로 늘었으며, 독립적인
실험 검증과 나머지39개 모델군 및 시설 전체 연계는 계속 진행해야 한다.

## 단열·압축기·유한 수소화물 저장

NATIVE_INSULATION.md는 기존 네이티브 진공 단열의 복사·잔류기체·지지부·국부 열교를
재사용한다. 벽체별 면적과 개별 관통부 배분을 명시하고 실제 층상 탱크에 연결해
유체와 벽의 에너지를 따로 확인한다. 온도차가 반대이면 열량 부호도 보존한다.
실제 단열재나 진공도 이력에 맞는 계수는 추가 실험 근거가 필요하다.

NATIVE_COMPRESSION.md는 실제 압축기 단계를 조립한다. 압력비·등엔트로피 효율·유량과
운전 범위를 넣으면 단계별 상태, 축동력과 냉각 부하를 얻는다. 중간 냉각은 지정한
출구 온도·압력손실을 경계로 사용한다. 실제 장비 맵, 처리 용량, 모터·기동 과도와
열교환기 성능을 예측하는 수준은 추가 개발 대상이다.

FINITE_HYDRIDE.md는 공통 흡수·방출 속도식을 유지하면서 유한 기체와 고체의 수소량,
기체·고체 온도와 내부에너지를 함께 계산한다. 반응 엔탈피와 밀폐계 내부에너지
차이를 구분하여 반응열을 중복 가산하지 않는다. HYDRIDE_DATA.md의 실험 읽기 API는
전체365402행을 보존하지만, 압력 단위·유량 기준상태·고체층 온도 관측이 미확정이므로
현재의 예제 계수를 이 실험에 맞춘 값으로 해석하면 안 된다.

이 단계의 첫 실행 모델군은35/72개(약49%)다. 전체 개발량은25-35% 정도로 추정하며,
독립적인 실험검증과 나머지37개 모델군 및 시설 전체 연계는 계속 남아 있다.

## 압력 보호·벤트·재액화·계기 응답

NATIVE_RELIEF.md는 실제 상류 압력에 따라 개방·재폐쇄하는 릴리프 밸브를 유한 탱크와
연결한다. 중간 수치계산이 밸브 래치를 바꾸지 않도록 실제 네이티브 객체의 시험 평가와
확정 전이를 구분한다. 이벤트 전후의 방출 상태와 질량·에너지 수지를 확인하지만,
장비 선정·용량 인증이나 임의의 시간 간격 안에서 숨은 모든 압력 변동 검출을 보장하지 않는다.

NATIVE_VENT.md는 실제 배관 저항과 유한 UA 열전달을 재사용한다. 역방향 유동의 열량
부호를 보존하고, 반환 유량에서 압력손실을 다시 검사하며, 열전달 계산이 충분히 세밀한지
별도 확인한다. 저마하수·압력·밀도 변화의 적용 범위를 지켜야 한다. 이 출구 PH 상태는
임계 방출면이나 대기 중 확산 소스가 아니므로 속도·면적을 임의로 만들어 붙이지 않는다.

NATIVE_RELIQUEFACTION.md는 냉각 용량을 지정한 정상 재액화와 유체·벽의 유한 재고를
가진 냉각 과도를 제공한다. 내부 열전달 제한과 저온 저장소의 열 추출을 구분한다.
액체 재고 증가, 출구 액체 유량, 실제 회수 제품량은 서로 다른 값이다. 전력이나 COP는
별도의 냉동 사이클·장비 근거가 있을 때 연결해야 한다.

NATIVE_INSTRUMENTATION.md는 실제 네이티브 계기의 지연·이득·바이어스·포화·분해능을
공정 예측 위에 적용한다. 최초 계기 상태와 시간, 위치, 물리량·단위·기준을 직접 지정한다.
입력은 구간 왼쪽 값으로 유지하고 출력은 구간 끝 왼쪽 극한으로 계산한다. 계기 오차 한계를
표준편차나 안전 확률로 해석하지 않으며, 미확정 실험 압력을 자동으로 절대압력으로 바꾸지 않는다.

이 단계의 초기 실행 범위는39/72개(약54%)이며, 전체 작업량 완성도는30-40%로 다시
추정한다. 이는 수치검증된 첫 수준의 확장을 반영한 계획값이다. 독립적인 실험 정확도,
장비 인증·시설 적용성과 나머지33개 모델군까지 완료했다는 뜻은 아니다.

## 스핀 전환·양측 유한 열교환·반응성 공정

NATIVE_SPIN.md는 실제 네이티브 회전자 평형·전환 속도·정온 해를 사용한다.
촉매 계수와 전환 엔탈피는 근거를 가진 입력으로 지정한다. 유한 열량계에서는 상압
전체 엔탈피와 동결 조성의 현열 열용량을 구분하여 전환 에너지를 중복 가산하지 않는다.
이 수준만으로 액체 스핀 혼합물 EOS나 밀폐 탱크 압력·보일오프를 계산하지 않는다.

NATIVE_HEAT_EXCHANGER.md는 유체 두 개와 벽 두 개의 실제 네이티브 유한 재고를
한 적분기 안에서 동시에 계산한다. 상대편 현재 벽 온도에 반응하므로 열 흐름의 반전도
얻을 수 있다. 현재는 밀폐 양측 열과도 수준이며, 유동식 인터쿨러 용량·압력손실·공간적
대향류나 실제 장비 성능은 추가 연계 대상이다.

REACTIVE_PROCESS.md는 기존 기체 체적 API의 `chemistry="finite_rate"`를 설명한다.
유입·유출과 내부 화학종 생성량을 따로 기록하고 원소·에너지 수지를 검사한다.
시간만 사용하는 유량 함수는 `phase_access="time_only"`로 지정해 계산 비용을 줄일 수 있다.
현재 공개 재현 사례는 메탄·수증기의 균일 기상 반응 기준 문제다. 실제 촉매 개질기나
산업 수소 수율을 검증한 모델로 해석하지 않는다.

HYDRIDE_COMPRESSOR_DATA.md는 MHC29개 실험의 기록계를 분리해서 읽는 방법을 설명한다.
선별 사이클은 원본과 같은 실험이므로 독립 검증 자료로 다시 나눌 수 없다. 게이지압 기준,
정상 유량의 기준 온도·압력, 각 기록계 시계와 센서 위치를 확인한 뒤 물리 모델에 연결한다.
원본 음수·결측·문자 셀은 보존하며 임의 보정이나 동기화를 하지 않는다.

재현은 `check_spin_integration.py`, `check_heat_exchanger_integration.py`,
`check_reactive_process.py`, `check_hydride_compressor_data.py`를 사용한다.
이번 추가 범위는42/72개(약58%)의 첫 실행 수준이며 전체 개발량 추정은30-40%를 유지한다.
실측 검증·장비별 계수·남은30개 모델군과 시설 전체 연결은 계속 개발 대상이다.

## 화재 진단·조건부 과압·순열량 역산과 열 영향 실험

NATIVE_JET_FIRE.md는 실제 HyRAM 화염을 계산한 뒤 입력 수소량과 화염 내부의 수소
기원 물질량, 열역학 식과 복사 출력을 따로 검사한다. 현재 네 가지 계산은 질량·열역학
수용 조건에서 실패한다. 기본 API는 원래 객체와 결과를 가진 예외를 반환하고, 복사장은
명시적으로 요청한 진단값으로만 제공한다. 이를 정상 화재 예측이나 벽체 입사 열유속으로
사용하지 않는다. 재현 스크립트의 종료코드1도 이 실패를 유지한 결과다.

NATIVE_OVERPRESSURE.md는 사용자가 근거를 명시한 참여 수소 질량·연소 에너지·대기압과
사건 중심을 받아 실제 네이티브 상관식의 최대 압력 상승을 구한다. 참여량·점화·폭굉 전이를
추정하지 않으며 압력 파형이나 충격량도 없다. 역산 반경은 주어진 에너지·상관식의 조건부
계산값이다. 안전거리나 시설 전체 사고 예측으로 바꾸려면 별도의 물리·실험 근거가 필요하다.

NATIVE_FIRE_HEAT.md는 고정 질량·체적의 이상화된 2상 용기에서 압력 이력으로 유체
내부에너지 증가율을 구한다. 냉각이면 음수도 보존한다. 벽의 열저장·열손실·일·벤트가
포함되는 입사 화재 열량과는 구분한다. 각도별 벽 온도의 T⁴ 형상과 같은 축 좌표의 접촉
구간으로 조건부 면적을 구하고, 서로 겹치지 않으면 면적0을 유지해 열유속 나눗셈을 막는다.
평균 온도만으로 평균 T⁴를 만들거나 미확정 게이지압을 절대압력으로 변환하지 않는다.

THERMAL_EFFECTS_DATA.md는 확보한 8개 실험·10개 첨부파일의 전체 관측을 읽는 방법을
설명한다. 약1억5800만 원본 수치를 검사했으며 음수 신호와 비물리 온도의 원값을 보존했다.
시계 단위·동기화가 미확정이므로 자동으로 초 단위 TimeSeries나 열량·선량을 만들지 않는다.
길이만 같은 RHF3와timech7는 기본으로 연결하지 않으며, 별도 근거가 있을 때만 명시적으로
관계를 선언한다. 미터·볼트 온도, 총열유속 파생값, 복사 열유속의 의미도 구분해야 한다.

첫 실행 수준은44/72개(약61%)다. 제트화재 진단은 성공한 모델 수에 더하지 않았다.
전체 개발량 추정30–40%와 독립 실험 검증 여부는 별도로 관리한다. requests/016은
실패한 화염 보존식, 열량 배분과 관측 조건에 대해 다른 개발 세션에서 필요한 확장을 명시한다.

## 저온 고압 저장·스핀 열물성·구형 저장재와 발효 관측

CRYO_COMPRESSED_STORAGE.md는 실제 네이티브 탱크·벽체·압력 이벤트·공통 노즐을
조합한다. 초기20MPa/25K의 정상·파라·오르토 수소가 같은 상태방정식과 적분기를
사용해 가열된다. 임계온도보다 높은 온도로 올라가는 것과 임계점을 통과하는 것은
다르다. 질량·내부에너지·벽 에너지, 독립 물성 역산, 밸브 개방과 양의 재고 하한을
따로 검사한다. 실제 충전 설비·냉동 사이클·용기 강도를 검증한 결과는 아니다.

NATIVE_SPIN_THERMOCHEMISTRY.md는 pifira의 온도 의존 회전자 에너지·열용량·전환율을
기존 Python 상태와 연결한다. 회전자 에너지를 이미 포함한 고정 조성 EOS에 같은
에너지를 다시 더하면 중복된다. 기준 조성 대비 보정과 PV 가정을 명시해야 한다.
경험적 전환식의 온도·밀도·조성 범위를 유지하며 새로운 전용 ODE를 추가하지 않았다.
이 기능만으로 조성이 변하는 액체 수소 EOS가 완성되지는 않는다.

MICROSPHERE_STORAGE.md는 구 내부의 유한 수소 재고와 구형 벽의 확산·포획을 연결한다.
기존 평판 확산도 같은 유한체적 코어를 사용한다. D(T), 용해도, 벽 두께, 초기 재고와
외부 퓨가시티 또는 벽면 유속을 직접 바꿀 수 있다. 기체량이 줄면 실제 CoolProp EOS로
압력이 변한다. 온도는 사용자가 주는 균일 이력이며 열부하·열응력·파손·광반응을
계산한 것으로 해석하지 않는다. 실제 재료 계수와 독립 실험이 추가로 필요하다.

FERMENTATION_DATA.md는 기존에 확보한 발효 실험830행을 원래 반응기·행·결측·시간
좌표와 함께 읽는다. 수소 생산량·수율의 파생 열은 독립 측정값이 아니며, 반복된 날짜와
원본 계산 불일치도 보존한다. 가스 기준 상태, 생산성 단위의 분모, 기질·바이오매스,
반응기별 독립성이 미확정이므로 임의 Monod 적합이나 질량 수율 변환을 하지 않는다.

첫 실행 수준은46/72개(약64%)이며 전체 개발량 추정30–40%와는 별도 지표다.
request017에 네이티브 이벤트·스핀 에너지·물성·재료 및 생물 공정의 다음 확장 조건을
기록했다. 전체 모델·독립 실험 검증·시설 사고 연계 개발 목표는 계속 진행 중이다.

## 광자 수지·기체/고체 평형·반복 PSA 운전

PHOTOCHEMISTRY.md는 실제로 선언한 파장 구간/단색광의 광량을 몰 광자 유량으로
바꾸고 반사·흡수·투과, 입사/흡수 전자 양자수율을 구분한다. H2당 전자2개의
수지를 사용하며 기존 반응물 재고·열량 코어를 재사용한다. 반응물이 부족하면
노출을 임의 종료하지 않고 거절한다. 필요한 등온 열량은 계산하지만 실제 열원,
자유에너지 가능성이나 촉매 반응속도가 검증됐다는 뜻은 아니다.

PHOTOCATALYSIS_DATA.md는 확보된37개 TXT의 모든 원행·열·결측·기호·파장축을
보존한다. 특정 생산률과 AQY는 출처가 있는 단위 매핑을 별도로 선언해 읽는다.
같은 연구의 중복 파일·재사용 control을 독립 실험으로 나누지 않으며 미확정
광원 세기·온도/압력·GC교정·오차막대를 임의 보완하지 않는다.

MULTIPHASE_CONVERSION.md는 실제 Cantera의 기체/순수 고체 평형을 연결한다.
유한 몰수와 고체 후보를 유지하며 TP 열량, HP 엔탈피, 압력·체적 일과 원소 수지를
검사한다. 고체 탄소 생성·소멸을 계산하지만 원료 조성·재·표면적·체류시간·반응
속도가 들어가는 실제 가스화 장치를 검증한 것은 아니다. 일부 HP 수렴 실패는
원래 객체와 원인으로 남기며 고체 후보 삭제나 다른 솔버로 자동 대체하지 않는다.

NATIVE_PSA_CYCLE.md는 기존 엔진의 두 흡착탑·밸브·열·압력 사이클을 실행한다.
선언한 기준에서56사이클 후 주기 정상상태를 확인했고 실제 출입 몰수로 순도와
주기 회수율을 계산한다. 가상 재료의 제품 H2 분율이 공급보다 낮은 결과도 유지한다.
사용자 API는 Python 객체이며 내부 네이티브 파일 연결은 임시 작업 폴더에서
처리한다. 원래 적분기 객체와 임의 callback 연결은 request018의 확장 과제다.

첫 실행 수준은49/72개(약68%)다. 전체 목표 대비 개발량 추정30–40%와 독립
실험 검증은 다른 지표이며, 남은23개 모델군 및 전체 시설/사고 연결은 계속 개발한다.

## 다공성 막과 열화학 단계 모델

막 모델은 실제 Cantera DustyGas를 호출해 다성분 확산, Knudsen 수송과
압력차에 의한 Darcy 수송을 함께 계산한다. 양쪽의 전체 조성·온도·절대압력과
공극률·굴곡도·공극 반경·투과도·두께를 직접 넣는다. 출력은 고체 기준의
성분별 총 몰 유속이다. 유효 수송계수에 공극률이 이미 반영되므로 면적에
다시 공극률을 곱하지 않는다. 유한 공급량, 투과·잔류측 재고와 열수지는
아직 별도 결합이 필요하며, 이 유속만으로 회수율·제품 순도를 주장할 수 없다.
구성과 단위는 NATIVE_MEMBRANE_TRANSPORT.md에 정리되어 있다.

열화학 모델은 기존 반응 코어를 재사용해 유한 반응물, 공급·회수와 온도
단계를 구성한다. MULTIPHASE_CALORIMETRY.md의 기체·순수 고체 공통 기준
엔탈피를 연결하거나 같은 Python 물성 계약을 직접 제공할 수 있다.
THERMOCHEMICAL_CYCLES.md의 전체 예제에서 반응진행량과 온도는 사용자가
지정한다. 캐리어 조성 복귀, 온도 복귀와 전체 재고 복귀를 따로 확인하며,
가열량·제거 열량·순 열량을 구분한다. 예제는 원소·질량·열량 검증용이며
해당 철계 사이클의 평형·속도·실제 운전 가능성이나 태양 효율을 증명하지 않는다.

생물 공정은 NATIVE_BIOLOGICAL_PROCESS.md의 별도 네이티브 환경과 소스
검증을 사용한다. 기존 발효 관측 자료의 단위·배양·가스 기준 누락은
라이브러리 설치나 수치 수지 검증으로 해소되지 않는다.

## 유한 장치와 불확실성 연결

FINITE_MEMBRANE_DEVICE.md의 막 장치는 양쪽 기체를 실제 유한 체적으로 둔다.
성분별 반대 방향 이동을 그대로 적분하고 압력·조성을 갱신한다. 온도는
양쪽 동일하게 지정하며, 그 온도를 유지하는 열량을 각 측 수지에 남긴다.
네이티브 내부 수치 시험 상태와 사용자가 요청한 출력 상태를 구분하고,
재고 한계 거부를 정확한 고갈 이벤트 시각으로 해석하지 않는다.

HYDRIDE_COMPRESSOR.md는 기존 수소화물 반응·열량 코어, 네이티브 공급·수신
탱크와 공통 노즐을 연결한다. 흡장·격리 가열·토출·격리 냉각을 구성하며
수신 탱크로 실제 이송된 수소와 모든 열·재고를 확인한다. 초기 저장된
수소가 결과에 기여할 수 있으므로 한 번의 이송을 정상 주기 회수율이나
지속 압축 성능으로 부르지 않는다. 재료·밸브·열경계는 근거를 붙여 교체한다.

UNCERTAINTY.md에서는 기존 Python 모델 함수에 입력 분포와 단위를 붙이고
네이티브 샘플·민감도 분석을 실행한다. 입력 독립성과 모델 초기화 근거를
직접 제공해야 하며, 상관된 식별 파라미터를 임의로 독립 샘플링하지 않는다.
실패 사례는 원래 입력·물리 객체·원인과 함께 남는다. 샘플 분위수는 연간
사고 빈도나 실험적 신뢰구간을 뜻하지 않는다.

EMBRITTLEMENT_DATA.md는113개 편집 문헌 관측을 물성·환경별로 불러온다.
공기 외에도 He·N2·Ar·미충전 기준이 있으며, 조성표40개 충돌은 자동 덮어쓰기
하지 않는다. 원래 시험편·가스·가압/충전·변형률·파괴 정의가 확보되기 전에는
통합 취화 상수나 독립 검증된 파괴 법칙을 만들지 않는다.

## 안전 endpoint·노출·빈도 연결

NATIVE_DETONATION.md는 실제 SDToolbox/Cantera로 기체 CJ endpoint와 동결
충격파 상태를 계산한다. 질량·운동량·총엔탈피·원소·음속 조건을 확인하지만,
DDT·점화·시설 지형에 따른 과압을 자동으로 제공하지 않는다. 실제 내부
탐색 상태를 얻을 수 없는 부분과 메커니즘의 범위를 그대로 기록한다.

NATIVE_EXPOSURE.md에서는 입사 복사열과 흡수열, 압력 peak와 양의 impulse,
시간 적분·모델 선택·평균 기준을 명시한다. 결과의 확률이나 모델만 바꾸고
이전 네이티브 근거를 재사용할 수 없도록 실제 계산 경로로 재검증한다.
열유속·압력은 사용자가 제공한 수용점 입력이며 source→화재 예측의 누락을
해결하는 값으로 해석하지 않는다.

CONDITIONAL_RISK.md는 이 노출 결과와 실제 유한 소스 객체, 사용자 발생
빈도, 배타적 분기와 보호 credit를 기존 네이티브 Python 모듈에 연결한다.
모든 입력 근거·시계·좌표와 원본 객체를 보존한다. 연간 빈도는 연간 발생
확률과 다르며, 알람·질량·위험 점수에서 자동 추정하지 않는다. 이 결과는
명시된 가정의 한 LOC 사례이며 시설 전체 QRA나 독립 실험 검증은 남아 있다.

SHOCK_TUBE_DATA.md의 액화수소 BLEVE 자료는 모든 확보 신호를 읽되 압력
기준, 기록계 동기화, 온도 dummy값과 중복 시계 문제를 보존한다. 모순된
샘플링 설명을 자동 수정하지 않으며, 연소파 모델 검증에 필요한 혼합기
초기 상태가 확보되지 않았다는 점을 기록한다.

## 산소 재고·인체 열상태·물리 관측을 연결할 때

OXYGEN_DEFICIENCY.md는 기존 Cantera 유한 용적에 실제 방출 구간·환기·벽 열을
연결하는 방법을 설명한다. 산소 kg/mol, 젖은/건조 기준 몰분율, 절대 분압은 서로
다르다. 기준을 선택할 때 물리량·압력·고도·근거를 함께 넘긴다. 계산된 산소 요약과
실제 네이티브 이력이 다르면 평가를 거부한다. 표본 사이 선형 보간으로 구한 기준
통과 시각은 원래 solver의 정확한 event root나 인체 위해 확률이 아니다.

층상 모델의 상부 수소 조성으로 건조 공기 캐리어의 O₂ 몰분율을 추적하려면
[층상 산소 조성 투영 가이드](LAYER_OXYGEN_PROJECTION.md)의
`project_layer_oxygen()`을 사용할 수 있다. 이 계산은 호출자가 고정 건조 공기의
O₂ 조성을 명시하는 경우에만 적용된다. 결과는 상부층 조성 시계열이며 실내 평균,
공간 노출 판정, 안전 인증이나 인체 생리 반응이 아니다.
이 상부층 신호를 호출자가 설정한 기존 센서·경보 API로 전달하는 방법은
[층상 산소 결핍 센서·경보 핸드오프 가이드](LAYER_OXYGEN_ALARM_HANDOFF.md)에 있다.

JOS3_THERMAL.md는 실제85노드·17부위 열조절 객체를 준비하고 피험자·의복·습도·
활동량·일반 공기 환경을 명시하는 예제를 제공한다. 원래 준비 상태는 복제되어
보존되고 원래 native 출력·열용량·노드 의미와 K 단위 스냅샷이 함께 남는다. 수소가
섞인 기체의 대류, 극저온 접촉·동결, 호흡기 손상이나 산소 부족 생리학을 이 엔진이
자동으로 제공하지 않는다. 일반 공기 열모델과 수소 방출실 모델은 각각의 적용 영역이다.

PROCESS_MONITORING.md에서는 동일 시계·위치·물리량·기준·단위의 예측과 관측을
네이티브 잔차 및 운전 모드별 학습 모델로 연결한다. 학습·정상 보정·평가의 실험
그룹은 분리한다. 결측·시계 단절·모르는 모드에서 억지로 점수를 채우지 않는다.
점수는 설정한 기준 집단과의 편차이며 누출 원인, 보호 조치 또는 연간 위험을 뜻하지 않는다.

OXYGEN_OBSERVATION_DATA.md에는 신규 ELVHYS4.2 전체 확보·검사와 미확정 의미가
정리되어 있다. 현재 파일의 H2 관측에서 실제 O2 이력이나 수소 질량 방출량을 만들어
쓰지 않는다. 필요한 source·시계·센서 정보는 Request022의 구체적 요청으로 남겼다.
다른 저장소는 직접 고치지 않았고, 재현 가능한 네이티브 진단 실패도 원래 상태로 남겼다.

## 병렬 코딩 단계와 이후 실행

사용자 지시에 따라 새 태양광·전해조, 균열·피로, 고체 반응 코드는 로컬 계산 없이
작성했다. 각 설명서의 implemented_unverified는 실제 실행·물리 검증 전이라는 뜻이다.
Ruff나 문법 검사는 단위·수지·수치 정확도·수명·발생률 검증이 아니다.

예제와22개 검증 케이스는 나중 누리온 실행에 사용할 정의다. 누리온 연결 뒤 실제
Linux 환경·native 라이브러리·계정/큐/자원을 정하고, 고정한 Git/계획 버전으로 실행한다.
NURION_VALIDATION_PLAN.md를 따른다. 현재 연결·작업 제출·검증 성공은 주장하지 않는다.
마지막 실행 확인 기록6eae06c와 이후 코드 작성 상태를 구분해 연구를 이어간다.


## 추가 병렬 모듈과 연결 경계

풀 화재는 `h2physics.adapters.pool_fire`, 용기 파손 개시는
`h2physics.adapters.vessel_failure`, 경제성은
`h2physics.adapters.hydrogen_economics`, 액적 비행·증발은
`h2physics.adapters.droplet_transport`에 있다. 네 모듈 모두 실행 전이다.
POOL_FIRE.md, VESSEL_FAILURE.md, HYDROGEN_ECONOMICS.md,
DROPLET_TRANSPORT.md에서 실제 객체와 필수 입력을 확인한다.

풀 화재에는 점화 시각·연소 질량유속·산소 재고·유한 외부 열공급을 명시한다.
용기 파손에는 결함 형상·차압·벽 온도별 재료 강도를 제공한다. 경제성에는
생산량과 재고·판매량을 구분하고 연간 대표성·제품 경계·비용 기준을 입력한다.
액적에는 포화 물성·외부 유동·적용 영역·근거가 있는 열전달 함수를 제공한다.
액적의 지면 도달량을 곧바로 풀 유입량으로 바꾸지 않는다.

초기 액상 방출은 `flash_initial_liquid_release(...)`가 기존 물성 제공자의 PH 상태와
포화 액·증기 끝점을 이용해 사용자가 지정한 등엔탈피 감압의 상분배를 계산한다.
반환된 `launch_liquid_mass_kg`는 후속 액적 비행의 초기 질량으로 연결할 수 있다.
이 결과는 순간 평형 플래시 가정의 수지일 뿐이며 플래싱 제트, 기상 운동량, 에어로졸
수율이나 액적 크기를 계산하지 않는다. 새 참조 계약은 작성했지만 아직 실행되지 않았다.

후속 검증은 기존22개에 신규19개를 더한41개 사례로 준비했다. 새 코드에 대한
로컬 계산·테스트는 실행하지 않았으며 누리온 연결도 아직 하지 않았다.
코드 보유 범위66/72개와 실행 확인 범위59/72개는 서로 다른 지표다.
타 저장소 확장 요청은 requests/024_fire_failure_parcel_and_economics.md에 있다.


## 지하 저장·미생물 전해·충돌·물질 좌표 화염 경로

`Uh2scUndergroundStorage`는 실제 UH2SC 공동/암반 해석과 독립 내부에너지·질량
장부를 연결한다. 알려진 소스 우려를 수정하거나 정상 결과로 포장하지 않는다.
`CanteraMicrobialCathode`와 `FiniteMicrobialCell`에는 실제 전극 메커니즘과 별도
미생물 속도·성장·물성 근거를 붙인다. 등온 배치 결과를 수확/판매·유틸리티 예측으로
바로 쓰지 않는다. DOI10.34810/data2866 전극 데이터는 공개 Dataverse에서 확보하고
23개 파일 스키마와 해시를 확인했다. 하지만 수소 생산률·Faradaic 효율·미생물 활성은
없어 전체 MEC 검증에는 쓸 수 없다. 파일별 권리 예외 필드가 제공되지 않아 원자료는
Git과 공개 배포물 밖에 보관한다. 자세한 인수 기록은
`research/microbial_electrolysis_data_candidate.toml`에 있다.

공개 ODS를 기존 관측 객체로 읽을 때는 `raw_root` 아래에 원본 폴더
`mec_data2866_1.0/`가 있어야 한다. 아래 예시는 모델을 실행하지 않고 LSV
관측 배열과 유효 마스크에 접근한다.

```python
from pathlib import Path
from h2physics.data import load_cora_mec_electrode_dataset

dataset = load_cora_mec_electrode_dataset(Path("data/raw"))
series = dataset.lsv_series[0]
potential, potential_valid = series.observations.column("potential_v")
current, current_valid = series.observations.column("current_a")
```

마스크와 행 출처를 유지하고, 서로 다른 전극 조건을 독립 실험으로 취급하기 전에
실험 그룹 구성을 확인한다. 이 데이터로 주파수 기반 EIS 회로를 적합하거나 전체 셀
수소 수지를 검증할 수 없다. 로더의 해시·행·단위 확인 사례들은 누리온 실행 전 상태다.

`FiniteSurfaceImpact`는 실제 incident parcel과 유한 표면 열재고를 받고, 증발·잔류
액체·반동·마운트 충격량을 함께 계산한다. 침착 재고를 기존 고정면적 풀에 넘길 때는
같은 벽체 열이 이어진 것으로 간주하지 않고 별도 열소유자를 명시한다.
`run_material_front`는 실제 Cantera 예혼합 화염과 HP 반응을 물질 좌표 경로에
연결한다. 실제 공간 화염·장애물 유동·인체 열피해 모델은 아니며, 절대 시계 투영의
오차 예산을 필수 입력으로 받아 양의 전달 시간이 반올림되어 사라지면 거부한다.

각 모델의 독립 설명서는 UNDERGROUND_STORAGE.md, MICROBIAL_CELL.md,
DROPLET_IMPACT.md, FLASH_FRONT.md다. 코드·예제·누리온 검증 정의는 있지만
실행 전이다. 미실행 모델군11개를 포함한 코드 보유 범위70/72개와, 과거 실행 확인
범위59/72개를 구분한다. 확장 계약은 Request025, 누리온 캠페인 준비는
NURION_VALIDATION_PLAN.md에서 이어간다. 후속 검증 사례62개는 통과 기록이 아니다.


## 장애물 해석·제트 화재 진단·경제성·검증 기록

`obstacle_dispersion`의 CFDMesh/CartesianObstacle/HydrogenCFDSource와
`run_obstacle_dispersion`은 실제 선택한 FDS6.11.1 바이너리에 원작성 입력을 넘긴다.
현재는 따뜻한 저마하·단일 격자·밀폐 기준 공간이다. HyRAM 고압 기체나 SLABx-LH2
결과의 자동 대체가 아니며, 고압 방출·액화수소·화재 연쇄를 검증한 것으로 보지 않는다.
실제 바이너리 경로·SHA와 런타임 권리는 누리온 설정 시 별도로 확인해야 한다.

`HyRAMFlameConservation`은 기존 화염의 질량·원소·형성엔탈피·운동에너지·방사를
같은 장부에서 진단한다. 기존 실패를 보존하며, 미폐쇄 에너지에서 임의의 열원을
만들지 않는다. `MicrobialCostProjection`은 실제 MEC trace를 기존 가격·연간·pyH2A
계산에 연결하지만, 미확정 수확·판매·보조비용을0으로 두거나 자동 연간화하지 않는다.

`cluster_evidence`는 나중에 실제 결과가 존재할 때 사용하는 읽기 전용 수집 API다.
실제 잡 선택, Git/계획/환경과 케이스를 대조하고 누락·불완전·불일치·거부·실패를 구분한다.
결과 파일을 해시하지만 계산·케이스 import·PBS 조회는 하지 않는다. 기록이 완성되어도
독립 실측·물리 모델 검증이 자동 성립하지 않는다. CLUSTER_EVIDENCE.md를 참고한다.
새14개 검증 정의를 더해 후속 사례는76개이며 모두 현재 단계에서 미실행이다.

최근 병렬 구현에서는 PV·미생물 전기화학 결과에 원본 생산자 검증을 연결하고,
LOHC/암모니아의 유한 전환·실제 인출 패킷, 압축기/열교환기의 native 결과 소유권,
시설 alarm→지연 action→유한 source→조건부 위험 연결을 추가했다. 기존 반응·장치·위험
해석기를 재사용하며 촉매 성능, 기계 map, 보호 신뢰도와 사고 빈도를 자동 생성하지 않는다.
누리온 실행 대기 정의는 총106개다. 이 숫자는 통과 수나 물리 검증률이 아니다.

추가 병렬 구현에서는 모델을 `(family_id, level_id, provider_id)`로 정확히
선택하고 유한 연료전지·유한 송출/수신 저장소·열 유틸리티 장부를 연결했다.
자동 대체 공급자, 임의 충전 프로토콜, COP·가격·가용성 추정은 하지 않는다.
누리온 실행 대기 정의는27개 늘어난 총133개이며 모두 미실행이다. 전체 목표
진행률 추정은30–40%이고 과거1088개 테스트는 이번 코드를 검증하지 않는다.

다음 병렬 구현은 흡착 용기의 자유기체+흡착 재고, 밸브 유한 스트로크,
릴리프 유한 리프트·누설·상 선택, 시설 노드 질량·엔탈피 연속성 감사를 추가했다.
기존 물성·흡착·노즐·장치 결과를 재사용하며 제어기나 누락 경계를 추정하지 않는다.
누리온 실행 대기 정의는25개 늘어난 총158개이며 모두 미실행이다.

다음 구현은 펌프 유한 속도·맵, 압축기 corrected-coordinate 맵 입장 검사,
두 유동 포트 열교환기, 재액화 제품·냉열 예산 장부를 추가했다. 제조사 성능,
제어기, COP, 분리기나 공간 열교환을 자동 추정하지 않는다. 누리온 대기
정의는25개 늘어난 총183개이며 모두 미실행이다.

## 2026-10-29 병렬 구현과 누리온 재개

이번 구현 체크포인트에서는 공개 4130X 피로 데이터 적재 API를 추가했다. 원본 XLSX는
저장소의 원시자료 정책에 따라 Git 추적 대상이 아니므로, 사용자는 별도 경로에 원본을
준비하고 `load_oedi_4130x_fatigue(path)`에 경로를 전달한다. 로더는 SHA-256과 MD5를 확인하고
5개 실험 시리즈를 `ObservationTable`로 반환하며 출처 URL, 제공기관, 라이선스, 워크북
행·열, 측정 단위와 시험 조건을 보존한다. 원본 워크북은 CC BY 4.0 표기와 귀속을 함께
보존해야 한다. 관련 HyMatBase 기록에는 4.5 MPa가 적혔지만 그 레코드의 파일 MD5가
원본과 일치하고, 워크북 조건 셀과 Sandia 연구 기록은 45 MPa를 지지한다. API는 관측
조건을 45 MPa로 인정하면서 메타데이터 불일치도 함께 보존한다. `condition_identity_admitted`
는 해당 출처 데이터를 조건 기준으로 비교에 쓸 수 있다는 뜻이지 모델 검증 통과를 뜻하지
않는다. `compare_oedi_fatigue_series`는 명시적으로 선택한 실제 HELPR 법칙을 각 ΔK에서
평가하고 계수를 적합하지 않는다. 호출자가 실제 적용 온도와 가스 몰분율을 공급해야
하며, 원자료가 시험가스 순도를 제공하지 않으므로 `gas_composition_interpretation_id`에
그 조성의 출처 또는 순수 H2 근사 같은 가정을 명시해야 한다. 선언은 결과에 저장되지만
가정이 맞는지는 검증하지 않는다.
비교 결과의 `points` 속성은 출처 행 ID, ΔK, 관측 da/dN, HELPR 원 반환, 허용된 예측률과
비율을 한 개의 불변 점 객체(`OediFatiguePoint`)로 묶는다. 이 뷰는 보유 배열을 행 단위로
정리하며 HELPR를 다시 호출하지 않는다. 데이터 해시·URL·라이선스, 시리즈 ID와 원본 열쌍도
각 점에 포함하므로 단일 점만 전달해도 출처를 유지한다.
`FatigueGrowthSeries`와 `OediFatigueDataset`를 직접 만들 때에도 시리즈 순서·압력·원본 열쌍,
행 ID·관측 스키마·워크북 체크섬 문맥이 서로 맞아야 한다. 이는 잘못 묶인 Python 객체를
거부하는 계약이며 실제 파일 적재와 독립 피로 검증을 대신하지 않는다. 원본 파일 해시와 측정값을
실제로 묶기 위해 public 데이터 객체 발급은 체크섬을 확인한 로더로 제한하며, 직접 생성·복사한
객체는 거부된다.

### 4130X 자료를 HELPR와 비교하기

원본 XLSX는 공개 Data.gov/OEDI 배포 파일에서 따로 받아 `data/raw/oedi-h2-materials/`
아래에 둔다. 해당 파일의 체크섬은 로더가 확인한다. HELPR는 프로젝트 기본 의존성이
아니며, 검토한 버전·라이선스와 미검증 설치 상태는 `DEPENDENCIES.md`에 기록되어 있다.
비교 API 실제 import는 `h2physics.data`의 지연 facade를 쓸 수 있다.

```python
import inspect
from pathlib import Path

from helpr.physics.environment import EnvironmentSpecification
from h2physics.adapters.fracture_fatigue import (
    HelprFatigueLaw,
    HelprLawSelection,
    HydrogenCrackEnvironment,
)
from h2physics.core import Origin
from h2physics.data import compare_oedi_fatigue_series, load_oedi_4130x_fatigue

dataset = load_oedi_4130x_fatigue(
    Path("data/raw/oedi-h2-materials/low-alloy-tempered-martensite-1211san11fat.xlsx")
)
series = next(item for item in dataset.series if item.environment == "H2")
temperature_k = 298.15  # RT를 수치 온도로 해석한 재구성 가정
hydrogen_fraction = 1.0  # 시험가스 순도 자료가 없어 선택한 순수 H2 근사

reference_pressure_mpa = inspect.signature(
    EnvironmentSpecification
).parameters["reference_pressure"].default
native_environment = EnvironmentSpecification(
    series.pressure_mpa,
    series.pressure_mpa,
    temperature_k,
    hydrogen_fraction,
    reference_pressure=reference_pressure_mpa,
)
law = HelprFatigueLaw(HelprLawSelection(
    "g_202006",
    "replace-with-your-reviewed-model-evidence-id",
    reference_pressure_pa=reference_pressure_mpa * 1e6,
))
environment = HydrogenCrackEnvironment(
    maximum_pressure_pa=series.pressure_mpa * 1e6,
    minimum_pressure_pa=series.pressure_mpa * 1e6,
    temperature_k=temperature_k,
    hydrogen_mole_fraction=hydrogen_fraction,
    hydrogen_fugacity_pa=float(native_environment.fugacity) * 1e6,
    fugacity_basis_id="HELPR-native-Abel-Noble",
    evidence_id="replace-with-your-condition-and-composition-evidence-id",
    origin=Origin.RECONSTRUCTED,
)
comparison = compare_oedi_fatigue_series(
    dataset,
    series.series_id,
    law,
    environment,
    temperature_interpretation_id="25 C 연관 기록을 298.15 K로 해석; RT 자체는 정확한 온도 아님",
    gas_composition_interpretation_id="원자료에 순도 없음; 순수 H2 근사",
)
for point in comparison.points:
    print(point.source_row_id, point.delta_k_pa_sqrt_m,
          point.observed_growth_m_per_cycle, point.predicted_growth_m_per_cycle)
```

이 코드는 비교 입력을 연결하는 예이며 수치 검증 결과가 아니다. `replace-with-...`
식별자는 실제 검토한 근거 ID로 바꿔야 한다. native 어댑터는 승인된 HELPR 버전·소스만
허용하며 자동 대체 엔진을 사용하지 않는다. 온도와 순수 H2는 원자료의 측정값이 아닌
재구성/가정이다. 비교는 각 점의 속도 잔차만 계산하며 1 Hz 주파수 효과, 재료 heat,
균열 이력·부품 형상 전이 또는 용기 수명 검증을 제공하지 않는다. Nurion 지연 케이스는
별도 원자료 staging과 native 실행을 요구하며 수용 임계값은 부여하지 않는다.

지연 Nurion 사례는 별도 스테이징한 XLSX와 HELPR를 써서 비교값만 기록하며 수용 기준은
적용하지 않는다. 1 Hz 영향, 시험별 heat 식별, 시험편에서 설비로의 전이는 미검증이다.

이번 추가 구현의 정적 확인은 구문 검사·Ruff·diff 검사에 한정했다. 모델 수치 계산,
새 검증 사례 실행, 또는 새 누리온 제출을 하지 않았다. 따라서 이 새 코드의 검증 상태는
`implemented_unverified`로 유지하고, 기존 batch 결과와 섞어 기록하지 않는다.

현재 진행은 모델 구현과 누리온 검증을 서로 분리해 병행한다. 최신 소스 고정 전의
counterflow data-ingestion case가 누리온에 올라가 실행되었으나, 처음에는 검증 계획이
`CASES` 목록 대신 함수만 내보내 runner가 case에 진입하지 못했다. 결과는0건이다.
계획을 수정해 job `24229654.pbs`와 수집기 `24229655.pbs`를 다시 제출했다. case는
40.96초에 통과했고 결과1건·누락0건이 수집되었다. 아카이브/워크북 해시와8개 소거율
관측,9개 온도·12개 종 프로파일,60개 정규화 광학 프로파일 및 밴드/스펙트럼 시리즈를
확인한 데이터 적재 근거다. 화염 해석·실험 비교나 순수 수소 검증은 아니다. 실행 기록과
해시는 DEVELOPMENT_LOG.md, HANDOFF.md에 있다.

동시에 세 가지 `implemented_unverified` 확장을 준비했다. [PV-전해 연계](PV_ELECTROLYSIS.md)는
시간·출처·기원을 보존하는 제한 간격 irradiance/셀 온도 프로파일을 midpoint 단계로
변환한다. [액적 충돌](DROPLET_IMPACT.md)은 충돌 사이의 근거가 있는 적분 열량과 표면
온도 극값을 받아 유한 벽 상태를 이어간다. [두꺼운 원통 응력](FRACTURE_FATIGUE.md)은
내·외압 Lamé 응력과 균일 벽 온도 변화에 대한 축 구속 열탄성을 계산할 수 있다.
추가한 방사상 온도구배 해석은 SciPy 경계값 풀이를 쓰는 별도 미검증 단계이며,
[적용 가정과 수식](../research/radial_thermoelastic_cylinder.md)에 기술했다. 두 원통
응력 모델도 균열 응력확대계수나 파손 판정을 만들지 않는다.

공개 API는 `h2physics.materials`에서 가져온다. `RadialTemperatureProfile`에는
내·외벽을 포함한 반경 좌표, 절대온도 표본, 기준 온도, 출처·근거 식별자를 넣는다.
`radial_thermoelastic_cylinder`에는 기존 원통 형상·압력·등방 재료 객체와 응력 조회
반경을 전달한다. 자유/고정 축방향 조건을 명시하고 계산 결과의 `max_bvp_rms_residual`
과 함께 적용 범위를 검토한다. 구현은 긴 원통·소변형·상수 물성을 가정하며 Nurion
수치 검증 전이다. 자세한 API 계약은 연구 노트에 기록했다.
시간별 압력·온도 표본은 `radial_thermoelastic_history`로 연결할 수 있다. 시각마다 압력
하중과 반경 온도분포를 하나씩 제공해야 하며, 결과는 시간-반경 배열로 원본 입력과
함께 반환된다. 이는 각 표본을 독립된 정적 상태로 풀이하는 준정적 계산이다. 시각 사이
열전도·구조 동역학이나 미관측 시각의 극값을 계산하지 않는다. 한 시각에서 실패하면
`RadialThermoelasticHistoryError`가 실패 인덱스와 먼저 완료된 결과를 보존한다.
각 표본의 BVP 반복 횟수도 이력에 남는다. 특정 계산 시각의 응력장을 넘길 때는
`history.stress_field_at(index)`를 사용하면 원본 압력 하중·온도 프로필·시계·수렴 진단을
포함한 `RadialThermoelasticStressSample`을 얻는다. 정수 표본 인덱스만 허용하며, 새 시각으로
보간하지 않는다. 소비 전 `sample.require_current()`로 이력과 응력장 연결을 확인한다.
후속 어댑터가 결과를 소비하기 전에는 `history.require_current()`를 호출해 원본 응력 배열,
압력 하중, 재료 선언, 방사 온도 프로필의 객체 동일성과 수치 내용 지문을 다시 확인할 수 있다.
계산 후 배열을 바꾸거나 같은 값의 배열로 교체한 경우 거부한다. 이 검사는 연동 데이터 무결성
확인이지 응력을 다시 풀거나 별도 검증 근거를 추가하는 기능은 아니다.

원통 벽의 과도 방사 열전도는 별도 API `radial_cylinder_heat_history`에서 제공한다.
`RadialSolidMaterial`에 밀도와 온도 의존 열전도율·비열 함수를 전달하고, 안쪽과 바깥쪽
면마다 단열·지정 표면온도·벽으로 들어가는 양의 열유속·대류·순복사 중 하나를 선언한다.
복사는 유효 조사온도와 방사율-형상계수 곱으로 경계면 복사수지를 계산한다. 결과는
셀 중심 온도장, 표면온도, 양면 누적 열량 및 전역 에너지 잔차를 보존한다. 온도 표본을
`RadialTemperatureProfile`로 연결해 기존 열탄성 해석에 순차 전달할 수 있다. 각 열이력은
고유 `history_id`와 물리 시계 `clock_id`가 필요하며, 파생 프로파일 ID에 원본 이력과 표본 시각이
보존된다. `thermoelastic_history` 조합 API에 표본별 압력 하중을 전달하면 같은 시계의 열·응력
이력을 함께 반환한다. 이는 준정적 조합이며 구조 동역학, 크리프, 유체-벽 동시연성이나
축방향 열전도를 계산하지 않는다. 지연 Nurion 케이스는 작성 및
등록됐으며 아직 실행하지 않았다. 상세 계약은 [방사 열전도 문서](RADIAL_HEAT_TRANSFER.md)를
참조한다.
물성 함수의 적용 온도 구간이 정해져 있으면
`guard_radial_material_temperature_domain(material, (T_min, T_max), preflight_samples=9)`로
사전 표본과 solver 호출 시점의 경계를 걸 수 있다. 범위 밖 평가와 0 이하 물성은 거부하고,
함수값은 보간·외삽하지 않는다. 사전 표본만으로 표본 사이 구간의 유효성이나 재료 근거를
증명하지는 않는다.
방사 열이력을 기존 파손 이력에 연결하려면
`adapters.bind_radial_thermal_history_to_vessel`에 압력 표본, HELPR 문맥, 실제 열이력과
균열/관심 영역을 대표한다고 판단한 명시적 반경을 전달한다. 시간 격자와 시계, 실린더
내·외면은 정확히 일치해야 한다. 반경 온도 매핑의 공학적 타당성은 별도 근거가 필요하며,
이 브리지는 파손 수명이나 파열 후 결과를 계산하지 않는다. 자세한 계약은
[열이력-파손 이력 연결 문서](RADIAL_FAILURE_HISTORY_BRIDGE.md)에 있다.
기존 바인딩과 계산된 전체 벽 열탄성 응력장을 합치려면
`adapters.bind_radial_thermoelastic_history_to_vessel`을 사용한다. 실제 `RadialThermomechanicalHistory`,
동일한 `RadialHeatResult`, 압력 geometry/load 객체, clock와 표본 시각을 요구하며,
`field_convention="total_pressure_plus_thermal"`만 허용한다. 이 응력 결과는 이미 압력
트랙션과 열변형을 함께 반영하므로 이후 SIF 소비자는 압력 응력을 추가 합산하면 안 된다.
특정 시각에서 압력·온도 로딩과 응력장을 함께 전달할 때는
`thermoelastic_binding.sample_at(index)`를 사용한다. 반환되는
`RadialThermoelasticVesselSample`은 원래 `VesselLoading`과 응력 표본을 함께 보존하고,
둘의 시계·압력·매핑 온도·원본 객체가 일치하는지 `require_current()`로 다시 확인한다.
표본 사이 시각은 만들지 않는다.

### 원통 확산 결과를 수소 농도 응력으로 연결

`adapters.bind_cylindrical_transport_to_eigenstrain()`은 원통형 `TransportResult`의
이동성 수소 셀 중심 농도를 정확한 시각별 준정적 응력 해석에 연결한다. 확산 mesh의
내·외면 반경은 응력 실린더의 내·외면과 같아야 한다. 확산 결과에는 표면 농도가 포함되지
않으므로 각 시각의 내면·외면 농도 2개를 호출자가 직접 제공하고, 그 표면·셀 매핑과
운전 시계 연결 근거를 식별해야 한다. carrier, 농도 basis, 기준 농도·온도, 선형 팽창계수,
압력 표본, 방사 온도 프로필, 축 구속 및 방정식 근거도 명시한다. 시간축 연결 근거와 축 방향 균일 농도 가정의 근거는 각각 분리해 기록한다.

반환된 `TransportEigenstrainBinding`은 원본 transport와 stress 이력을 함께 보존하며
`require_current()`로 결과가 변경되지 않았는지 확인한다. 표본 시각 사이를 보간하지 않고,
트랩 농도를 이동성 농도에 더하거나 응력이 확산에 되먹임되는 계산도 수행하지 않는다.
표면 농도와 팽창계수는 재료별 근거가 필요한 호출자 입력이다. 모델 수준과 한계는
[수소 농도 eigenstrain 설명서](HYDROGEN_EIGENSTRAIN.md)를 참고한다.

현재 HELPR 어댑터에는 이 스트레스 필드를 직접 처리하는 SIF API가 없다. 별도로
`adapters.evaluate_radial_stress_intensity_samples(binding, calculator, calculation_evidence_id=...)`는
사용자가 제공한 SIF 계산기를 각 원본 응력 표본에 적용하고 signed 결과를 보존한다. 계산기,
결함 형상과 재료 적용성은 호출자 책임이며, 보간이나 수명 예측은 수행하지 않는다. 이미 계산한
계열의 구간 요약은 `series.sampled_window(start_time_s, end_time_s)`에 정확한 출력 시각을 넣는다.
세 기존 증분은 commit `c521f57`에 고정해 Nurion 수치 사례를 완료했다. 첫 배열
`24229801[]`에서 impact·pressure-boundary 원통 사례는 통과했지만 PV 사례는 입력
파일 경로 오류로 사례 실행 전에 실패했다. 경로를 수정한 PV 재시도 `24229849.pbs` 뒤
collector `24229850.pbs`가 원본 두 사례와 재시도를 다시 모아 3건 통과·실패 0·누락 0을
기록했다. 이 결과는 해당 고정 commit의 좁은 authored 수치 불변조건만 뒷받침한다.
이후 추가한 원통 압력 이력, 복사 열경계, 열-응력 연동 및 결과 무결성 변경은 이 캠페인에
포함되지 않았으며 누리온 검증 전이다. 별도 제출 요청이 있기 전까지 추가 작업은 제출하지
않는다.

흡착 저장 용기의 평형 상태에서 압력을 역산하려면
`FiniteAdsorptionVessel.pressure_for_inventory(target_inventory_mol, species_id,
temperature_k, pressure_bounds_pa, ...)`를 사용한다. 사용자 지정 압력 구간 안에서
33개 기본 표본으로 성분 재고의 단조성을 확인하고, 브래킷된 구간에서만 근을 구한다.
반환된 `AdsorptionPressureSolution`은 최종 snapshot, 목표·도달 재고량, 잔차, 압력 구간,
표본 수와 허용오차를 보존한다. 이 표본 검사는 점 사이의 단조성을 증명하지 않으며,
온도와 혼합 기체 조성은 고정된다. 압력 과도, 흡착 속도, 열이동 및 순환 용량 예측으로
해석하면 안 된다. 이 API의 deferred contract는 Nurion 대기 계획에 추가됐으며 아직 실행되지 않았다.

시설 source 경계의 시간별 누적 질량·에너지 수지를 열람할 때는
`FiniteFacilitySource.ledger_history()`를 사용한다. 네이티브 accepted time축에서 선택한
저장 재고 변화, 네이티브 외부 경계 질량·에너지, 운반 엔탈피, 주변 열 및 source 출구
엔탈피를 보존한다. source 상태를 고정해 계산한 엔탈피 투영은 네이티브 출구 적분과
별도 열에 남기므로 두 값을 같은 에너지 closure로 해석하지 않는다. 결과 배열은 불변이고,
미관측 시각은 보간하지 않는다. 전용 cumulative-ledger case는 계획에만 등록됐으며 수치
계산과 독립 시설 검증은 대기 중이다.

현재 전체 목표 진행률은 불확실한30–40% 추정이며, 마지막으로 수용된 first-level 실행
근거는59/72(약82%)다. 원통 응력, 액적 충돌 및 PV 프로파일 case가 모두 통과했고
collector `24229850.pbs`에서 3건·실패0·누락0으로 수집되었다. 이후 원통 압력 샘플
시리즈 API와 deferred case가 추가되었으므로 다음 source pin에 포함해야 한다. 이 추가분은
기존 `VesselFailureHistory`로 압력·시계·온도 샘플을 연결하는 어댑터도 포함하며, 로컬
Ruff·구문·diff 정적 검토만 마쳤다. 두 추가 case는 아직 계산 검증 전이고 별도 제출
요청을 기다린다. 최신 코드·큐 작업·통과 기록은 서로 다른 상태로 추적한다.

## 최근 추가된 공개 데이터·장치·안전 API

지질 재료 흡착 관측자료는 `h2physics.data.load_geological_adsorption_isotherm(archive_path, material_id)`로 불러온다. Zenodo 최신 CC BY 4.0 압축 파일 경로를 직접 넘기며, 로더는 파일 해시를 확인하고 처리된 재료별 CSV 한 개만 메모리에서 읽는다. 각 관측은 원본 행과 문자열 필드를 보존한다. 측정량은 부호가 있는 초과 흡착량이다. 연구 비교를 위해 `table.surface_excess_provider(temperature_k=...)`로 실제 `AdsorptionProvider` 인터페이스에 연결할 수 있지만, 측정 온도 하나에서의 H₂ 단일성분·측정 압력 구간 내 log(P) 보간만 허용한다. 다성분·온도 보간과 압력 외삽은 거부하며, provider의 `surface_excess` basis는 유한 흡착용기 inventory에 사용할 수 없다. 세부 권리·단위·미해결 사항은 `docs/GEOLOGICAL_ADSORPTION.md`와 데이터 영수증에서 확인한다.

액화수소 이송관 예비 냉각량은 `h2physics.estimate_line_cooldown()`으로 계산할 수 있다. 사용자가 관 구간별 금속 질량, 열용량 함수, 시작/목표 온도와 필요 시 잔류 수소 상태·엔탈피 함수를 제공한다. 공용 EOS와 연결할 때는 `h2physics.IsobaricEnthalpyPath`에 압력·물성 기준·허용 상을 명시하고, `estimate_line_cooldown_with_provider()`에 넘기면 입출구 `ThermoState`와 수소 질량 하한을 하나의 확인 가능한 결과로 받는다. 결과에는 구간별 열부하와 총 수소 질량의 이상적 하한이 남는다. 정상 상태나 과도 유동, 막비등, 냉각 전선, 열누설은 자동 계산하지 않으며, 선택한 상태와 열용량 경로를 사용자가 근거와 함께 지정해야 한다. 자세한 한계는 `docs/LINE_COOLDOWN.md`에 있다.

질량과 에너지 결과 속성을 읽을 때 저장된 열량 콜백을 자동 재평가하며, 명시적으로 `result.require_current()`를 호출해 전체 receipt를 확인할 수도 있다. 구간·근거 ID·에너지 장부의 사후 변경은 거부한다. 콜백이 내부 상태만 바꾸면서 계산점에서 같은 값을 반환하는 경우까지 판별하지는 않으므로 물성 함수의 버전과 출처는 호출자가 관리한다.

EOS 연결 결과도 압력·물성 기준·허용 상·근거 ID와 냉각재 입출구 상태를 묶어 보관하고, 결과를 읽기 전에 provider에 endpoint 상태를 다시 요청한다. 제공자 내부 구현이나 상태가 같은 endpoint 답을 내는 한에서는 달라진 내부 구현을 식별할 수 없으므로 provider 버전·설정은 별도 연구 provenance에 기록한다.

고압 수소 분산에 선택한 HyRAM 결과는 `adapters.project_hyram_jet_to_finite_source()`로 공용 `IntervalMassSource`와 연결할 수 있다. 정상 누출률을 사용자가 정한 시계 구간에 적분하고, 상류 상태와 source 대표 상태 사이의 엔탈피 차이 및 질량률 잔차를 각각 보존한다. 실패한 네이티브 HyRAM 결과는 연결하지 않으며, 이 API가 Gaussian 단면의 질량 불일치를 보정하지 않는다. 과도 누출 이력도 추론하지 않는다. 세부 조건은 `docs/HYRAM_FINITE_SOURCE.md`에 기록되어 있다.

외부 모델의 시간변화 수소 방출량을 각 구간별 정상 분산 계산으로 넘길 때는 `adapters.run_hyram_finite_source_snapshots()`와 `HyRAMFixedFlowReceiver` 계약을 사용한다. 입력은 왼쪽 구간값을 유지하는 `NozzleSourceProjection`이어야 하며, 받는 모델은 요청 질량률과 실제 source-plane 채택률을 각각 반환해야 한다. 현재 프로젝트의 `run_hyram_gas_jet()`는 자체 오리피스 유량을 계산하므로 이 fixed-flow 계약에 해당하지 않는다. 따라서 해당 네이티브 경로에 이 API를 연결했다고 가정하면 안 되며, 외부 receiver가 정확한 고정 유량 경계를 지원하는지 먼저 확인해야 한다. 결과는 독립 정상 스냅샷의 묶음으로서 플룸 기억, 구간 사이 농도 보간 또는 연속 노출량을 포함하지 않는다. 상세 계약은 `docs/HYRAM_FINITE_SOURCE_SNAPSHOTS.md`에 있다.

`RadialThermoelasticStressHistory.stress_path_at(index, radii)`는 기존 열응력 계산에서 지정 시점의 벽 두께 방향 응력 성분을 요청 좌표로 내보낸다. 시간 보간·벽 외삽 없이 전체 압력+열 응력 텐서의 방사·원주·축 응력과 von Mises 값을 제공한다. 후속 파괴역학 코드가 비균일 응력을 처리할 때 쓸 수 있는 입력 인터페이스이며, 응력확대계수(SIF)나 파손시점을 계산하지 않는다. 현재 HELPR 경로는 별도로 압력 기반이며, 전체 계약은 `docs/RADIAL_STRESS_PATH.md`에 있다.
지질 흡착 provider의 `AdsorptionState.source_observations`에는 사이트별
`AdsorptionSourceObservation` 불변 객체가 연결된다. H2 성분 ID, 원자료 행 번호와
signed loading, log 압력 보간 가중치, 보고된 표준불확도, LOD, LLOQ를 mol/kg 단위로
보존한다. 원자료 mmol/g와 수치가 같으며, 가중 원자료 loading이 반환된 사이트 loading과
일치하는지 확인한다. 통계적 불확도 전파는 하지 않고, 결측 통계량은 `None`으로 남는다.

## 시설·사고·불확실성의 Python 조합

`h2physics.OperationalScenario`는 기존 모델 호출을 `ScenarioNode`로 묶는다.
고정 입력은 `ScenarioValue`, 다른 노드 결과는 `ScenarioOutput`으로 지정한다.
노드 간 순환·없는 의존 항목은 준비 단계에서 거부하고, `run(targets=(... ,))`는
선택 결과에 필요한 상위 노드만 실행한다. 원래 결과와 실패 직전까지 완료한 결과를
보존한다. 구성만으로 모델 계산이 실행되지는 않는다.

`adapters.parcel_population`은 명시한 액적 수·개별 질량·초기 위치·속도로 기존 비행
해석을 호출하고 플래시 이후 액상 질량과 가중 질량수지를 비교한다. 지면에 도착한
액체에는 별도 충돌 해석이 필요하다. `adapters.parcel_pool_chain`은 승인된 침적
결과를 기존 고정 면적 풀 초기 재고로 넘기고 누적 증발량에서 증기 질량 구간을 만든다.
이후 `quasi_steady_dispersion()`은 기존 SLABx-LH2의 독립 정상상태 구간 해석을 사용한다.
전후 구간의 플룸을 연결하는 비정상 해석은 이 결과에 포함되지 않는다.

`adapters.facility_accident_chain`은 기존 유한 운전·방출원·선호 확산 요청의 동일 객체,
시계·구간별 질량·엔탈피를 확인하며 연결한다. `adapters.electrochemical_operation`은
열 스택과 유한 연료전지 결과의 공통 운전 명령·에너지 기준 및 등온 근사 범위를 확인한다.
`adapters.radial_radiation_target`은 명시한 흡수율과 원주 방향 균일성 가정 아래 입사열
구간을 기존 벽 열전도 모델에 연결한다. `adapters.adsorption_operation`은 셀별 흡착제
질량으로 절대 흡착 재고를 합산하고 네이티브 재고와의 차이를 그대로 보고한다.

`research.joint_uncertainty`는 사용자가 제시한 잠재변수→상관 입력 변환을 기존 QMC와
연결한다. 변환 근거·버전·각 물리량 범위를 명시해야 한다. 시나리오 결과를 읽는 함수는
`scenario_uncertain_model()`에 전달한다. 원래 시나리오 결과와 실패 원인은 유지된다.
이 신규 연결 코드는 수치 실행 전이며, 상세 계약은 SCENARIO_COMPOSITION.md와
JOINT_UNCERTAINTY.md에 있다. 누리온 검증 전에는 물리적 정확성을 인정하지 않는다.

## 유한 냉각수와 혼합물 평형 분리

`electrochemical_thermal.FiniteCoolantReservoir`에는 질량·절대압·원래 물성 제공자,
액상 온도 범위와 외부 열경계 함수를 넣는다. `FiniteThermalStack.run_with_coolant()`는
기존 스택 열 방정식에 냉각수 비엔탈피를 함께 적분하며, 스택에서 빠진 열과 냉각수로
들어간 열을 반대 부호로 기록한다. 고정 압력에서 냉각수 저장량은 엔탈피 차이로 계산한다.
액상 영역 이탈과 상변화는 거부한다. 결과 `require_current()`는 원래 설정과 수치배열을
재검사한다. 해석 실패에는 완료한 구간과 원래 반환된 네이티브 결과를 남긴다.
상세 입력과 적용 범위는 FINITE_ELECTROCHEMICAL_COOLANT.md에 있다.

혼합물은 `CoolPropMixtureProperties.phase_partition_pq()`에서 같은 평형 계산의 상별
조성·엔탈피·밀도를 얻는다. `split_mass()`와 `split_moles()`는 각 상의 성분량을
반환한다. 명시한 품질 구간의 `phase_partition_ph()` 역산은 표본 단조성·성분 수지·
엔탈피 잔차를 검사하며, 전역적인 평형 분기 유일성을 주장하지 않는다.
`adapters.mixture_flash_separator.separate_equilibrium_mixture()`는 이 계산으로
유한 등엔탈피 감압 후 성분 질량과 상별 엔탈피 장부를 만든다. 기계적 에너지 무시와
평형 가정의 근거, 분기 선택과 잔차 허용치는 사용자가 지정해야 한다.
이 신규 물리 수준은 모두 누리온에서 실행·검증하기 전이다.

## 촉매 표면과 사고 열경계의 새 연결

`h2physics.adapters.cantera_surface_reactor.CanteraCatalyticSurfaceReactor`는
검토한 반응기구 원본 바이트와 SHA-256·권리·상태 범위를 받아 Cantera의
기체상과 표면상을 연결한다. `run`에 기체 초기 상태, 전체 표면 피복률,
표면적·기체 부피·출력 시간·적분 및 원소/사이트 허용오차를 명시한다.
이 수준은 닫힌 강체 등온계다. 실제 촉매 장치의 열전달이나 유동 개질기
수율을 예측한다고 해석하면 안 된다. 계산 결과는 아직 미검증이다.
`trace.species_inventory_series("H2", phase="gas")`처럼 기상 또는 표면종의
몰수를 원래 accepted 시간축으로 추출할 수 있다. 이 값은 기존 점 결과의 읽기용
투영이며 연속 급·배기, 촉매 열용량 또는 유동 반응기 동역학을 추가하지 않는다.
자세한 입력과 보존 경계는 [촉매 표면 설명서](CATALYTIC_SURFACE_REACTOR.md)에 있다.

축방향 물질·온도·표면 피복 변화를 보는 수준은
`h2physics.adapters.CanteraCatalyticPFR`로 선택한다. 사용자가 제공한 Cantera 3.2
기체/촉매 표면 반응기구, 입구 조성, 질량유량, 단면적, 촉매 면적비와 축방향
출력점을 사용한다. 네이티브 `FlowReactor`가 정상 1차원 반응을 계산하며,
마찰 없는 단열 기체 흐름을 가정한다. 압력강하·촉매 열용량·기공 확산·수명은
포함하지 않는다. 독립 실험 대조 전이므로 연구 적용 한계와 사용 예를
[공간형 촉매 PFR 안내](CATALYTIC_PLUG_FLOW.md)에서 확인한다.

다중 압력 뱅크 충전의 단계 선택에는
`h2physics.adapters.GenericCascadeRefillSequencer`를 사용할 수 있다. 각 뱅크의
순서, 수신기 절대압력 전환점과 최소 압력 여유는 모두 사용자가 넣는다.
시퀀서는 샘플된 압력으로 한 뱅크만 활성화하고, 계측 ID·소유자·시계가
바뀌면 거부한다. 실제 유량, 밸브 개도, 온도, 열 반응이나 표준 충전 절차를
계산하지 않으므로 기존 PI/밸브/유한 이송 모델과 감독 계층으로만 연결한다.
[다중 뱅크 순서 안내](CASCADE_REFILL.md)에 적용 범위와 예제가 있다.

충돌 후 풀의 마지막 재고는 `continuation.fire_seed(...)`로 기존 풀화재에
연결할 수 있다. 점화·연소율·산소 조건은 별도 입력이다. 제트 복사의 한
수용점은 `incident_history_from_jet_radiation(...)`로 원래 정상상태 시간
안에서 열경계에 전달한다. 표면 방향·흡수율·원주 균일성은 목표물 모델의
별도 근거가 필요하다. 이 연결도 누리온 검증 전이다.

지질 재료 흡착 원시자료는 `h2physics.data.load_geological_calibration(path)`로
읽을 수 있다. 이 API는 원본 압력 역할과 행 정보를 유지하며, 빈 헬륨 보정값과
COx 시료 설정 누락을 `None`으로 남긴다. 절대압/게이지압 기준, COx 연결
워크북 입력, 흡착 보정은 미해결이므로 EOS 또는 용기 용량 계산에 바로 넣지 않는다.

## 원통 벽 확산과 수소 농도 경보

`DiffusionMesh.cylindrical_shell()`은 파이프나 용기 벽을 반경 방향 유한체적으로
나눈다. 외·내면 반지름, 유효 길이, 셀 수를 직접 넣고 기존 `DiffusionDomain`의
수소 운반체, 확산계수, 트랩과 표면 경계를 연결한다. 길이 방향 변화나 끝면 유속은
계산하지 않으며, 원통 재료 계수는 실험·문헌에서 별도로 제공해야 한다. 정상
로그 프로파일·유속·재고 사례는 아직 실행 전이다. 상세 경계는
[재료 수송 설명서](MATERIAL_TRANSPORT.md)를 참고한다.
고체 표면 바깥의 선형 물질전달 저항은 `SurfaceFilmCondition`으로 넣을 수 있다.
외부 농도는 이미 같은 수소 운반체·고체 농도 기준으로 변환한 값을 제공하고,
막 전달속도(m/s)와 표면 근거 ID도 직접 지정한다. 고체 반쪽 셀 저항과 막 저항은
유한체적 경계에서 직렬 결합된다. 이는 용해도/퓨가시티 변환이나 표면 반응속도를
추정하지 않는다. 사용 범위는 [표면막 경계 설명서](HYDROGEN_SURFACE_FILM.md)를 참고한다.

감지기 시간응답까지 포함하려면 `FirstOrderConcentrationSensorConfig`에
시간상수·초기 표시값·단위·시계·최대 입력 간격과 보정 근거를 제공하고
`evaluate_first_order_concentration_sensor()`를 호출한다. 두 입력 샘플 사이의 실제
농도는 선형 변화로 가정해 1차 지연식의 닫힌형태 해를 구간별로 계산하며, 입력과
표시값은 같은 농도 기준·단위를 유지한다. 응답 이력은 원래 농도 입력, 근거, 운전 모드,
에피소드와 출처 origin을 함께 보존한다.
이 표시 이력을 경보에 연결할 때는 감지기 위치·단위·농도 기준·센서 근거가 모두
일치하는 `ConcentrationAlarmConfig`를 만들고
`evaluate_concentration_alarm_from_sensor()`를 호출한다. 상승/해제 임계값·연속 확인
샘플 수·최대 허용 시계 간격과 별도 근거 ID도 직접 넣는다. 확인된 경보는
`ConcentrationAlarmEvidence`로 묶어 기존 `ScheduledProtection`의 명시적 오프라인
재생에 연결할 수 있다. 이 모델은 센서 화학, 교차감도, 포화, 잡음, 통신 지연이나
권장 임계값을 계산하지 않는다. 안전 설정값으로 예제 수치를 재사용하지 않는다. 자세한 한계는
[농도 경보 설명서](GAS_CONCENTRATION_ALARM.md)에 있다.
여러 감지기는 각 경보 이력을 같은 시각 격자에 정렬한 뒤
`evaluate_concentration_alarm_voting()`에 명시적 k-of-n 투표 수를 전달할 수 있다.
이 결합은 감지기 독립성·공통원인 고장·투표 적합성이나 고장 확률을 추정하지 않는다.

## MS1700/QP1180 정규화 투과 관측 읽기

[Mendeley Data 공개자료](https://doi.org/10.17632/zj7zh24frt.1)는 CC BY 4.0으로
배포되며 MAT 파일의 원본 해시를 데이터 영수증에 고정했다. `Msdata`와 `QPdata`
행렬은 `h2physics.data.load_mendeley_normalized_permeation(path, dataset=...)`로
읽는다. `dataset`은 `resolve_dataset()`으로 해당 버전의 게시자 메타데이터와
첨부 목록을 확인해 얻는다. 결과는 두 강종의 행 순서와 정규화 시간/플럭스 좌표를
그대로 유지한다. SciPy MAT reader가 필요하다.

현재 출처 정보만으로는 정규화 식, 시편 두께 기준 및 플럭스 단위를 확정할 수 없다.
따라서 결과를 확산계수, 용해도, 투과도 또는 트랩 계수로 변환하지 않는다. 원자료는
Git 패키지에 포함되지 않고 `data/raw`에 별도 보관되며, 누리온 계약 실행 전 명시적으로
스테이징해야 한다. 자세한 출처·API·한계는 [재료 수송 설명서](MATERIAL_TRANSPORT.md)를
참고한다.

## 수소엔진 닫힌 실린더와 입력 시간축

현재 `SliderCrank`와 `run_closed_charge_engine_segment()`는 일정 회전수에서
균질 수소 혼합물의 닫힌 실린더 구간을 Cantera로 적분한다. `EngineBoundarySchedule`과
`engine_schedule_from_crank_angle()`은 사용자가 제공한 각도-값 표본을 구간 시작 시각과
일정 회전수로 절대시간 표본으로 변환한다. 이는 입력 정렬 API이며 밸브 유동, 분사,
점화, 벽 열전달이나 전체 사이클을 구현하지 않는다. 자세한 물리 범위와 미실행
원격 계약은 [엔진 주기 모델 경계](ENGINE_CYCLE.md)를 참고한다.

추가된 `run_open_cylinder_segment()`는 별도 수준의 Cantera 3.2 개방 제어체적 구간이다.
고정 상태의 caller 지정 유입 기체와 시간표 유량, 현재 혼합기체를 내보내는 시간표 출구,
슬라이더-크랭크 이동 벽을 하나의 `ReactorNet`에 연결한다. 유량은 밸브나 인젝터 법칙에서
계산하지 않으며, 배기는 실린더 순간 혼합 조성을 따른다. 질량·성분 전달과 제1법칙 잔차는
요청 출력 시각의 표본 적분 진단이므로 accepted 내부 스텝 기준 보존 증명이나 완전한 사이클
폐합이 아니다. 미실행 합성 계약과 코드 예시는 [개방 실린더 설명서](ENGINE_OPEN_CYLINDER.md)에 있다.

## 수소엔진 화염·피스톤 벽면 관측 자료

TU Darmstadt 공개 자료는 `DATASETS`에서 `hydrogen-engine-flame-wall` seed를 찾아
`resolve_dataset(seed)`로 메타데이터를 확인한다. 항목, ORIGINAL bundle, bitstream 목록
세 응답만 읽고, DOI·라이선스·공식 호스트 링크를 확인한다. 파일 본문은 이 단계에서
가져오지 않는다. `.h5` 원본 취득은 `acquire_dataset()`으로 가능하지만 패키지나 공개
GitHub 자료로 포함하는 설정은 허용되지 않는다. `h2physics.data.inspect_hdf5_metadata(path)`로
파일 해시와 HDF5 그룹, 배열 모양·자료형·저장 설정, 속성 및 링크를 목록화할 수 있다.
이 기능은 배열 값을 읽지 않고 단위나 물리량도 추정하지 않는다. 원본 스키마와 단위를
확인한 뒤 별도 관측 매핑을 작성해야 수치 관측 블록을 만들 수 있다. 이 자료의 figure
메타데이터 스냅샷을 다시 쓸 때는 `inventory.require_current()`로 reader 발급·내용 봉인과
원본 경로의 파일 크기·SHA-256을 함께 확인한다. 복제나 내용 변경은 무효화된다. 이 확인은
출판사 진위나 재배포 권한을 증명하지 않는다.
그림 수준의 화염 전파와 피스톤 표면온도 관측은
크랭크각 압력·사이클 일 자료를 대신하지 않으므로 엔진 사이클 검증에는 사용할 수 없다.
자세한 영수증과 한계는 [데이터 인벤토리](DATA_INVENTORY.md) 및
[엔진 주기 모델 경계](ENGINE_CYCLE.md)를 참고한다.

## 가스터빈 공통축 과도 응답

`ShaftTransientInputs`에 같은 시각축의 터빈 축출력, 압축기 축요구동력,
부하 토크와 회전자 관성을 제공하면 `integrate_shaft_transient()`가 회전자
운동에너지와 누적 일 항을 함께 적분한다. 최소·최대 회전수 경계는 사건에서
계산을 종료하며 값을 경계에 맞춰 잘라내지 않는다. 각 축출력은 기존 Brayton
주기 및 압축기·터빈 모델이 계산한 결과를 공급해야 한다. 이 모듈은 회전축의
응답만 계산하고 가스 경로·제어기·다축 장비를 풀지 않는다. 합성 Hangang 계약은
아직 실행되지 않았다. 자세한 입력·에너지 부호와 적용 한계는
[과도 축 응답 설명서](BRAYTON_SHAFT_TRANSIENT.md)를 참고한다.

## 일정 전류 연료전지의 재고 한계 종료

`h2physics.adapters.run_fuel_cell_until_reserve`에 기존 연료전지 객체,
초기 몰 재고, `FuelCellStep` 스케줄과 H2/O2 잔여량 기준을 전달합니다.
반환값은 원래 요청과 실행된 앞부분, 실제 연료전지 결과를 보존합니다.
공급은 구간 시작 시 전량 추가되며, 조기 종료를 이유로 공급량을 줄이지
않습니다. 시작 경계에서 이미 기준 이하이면 명시적으로 거부합니다.
[실행 예제와 적용 한계](FUEL_CELL_INVENTORY_EVENT.md)를 확인하세요.
연속적으로 상태·전류가 변하는 Cantera 모델의 이벤트 탐지는 별도 범위입니다.
