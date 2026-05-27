# Lambda 단일 함수 범용 처리 확장 시나리오

상태: 아이디어 단계 (향후 확장 검토)
기준일: 2026-05-27

## 배경

현재 `AEGIS-Lambda-DataProcessor`는 `factory_state`와 `infra_state` 두 가지 source_type만 처리하며, 센서 필드와 리스크 가중치가 코드에 하드코딩되어 있다. 센서 종류나 수가 늘어날 경우 Lambda 코드를 직접 수정해야 한다. 이 시나리오는 코드 수정 없이 센서 확장이 가능한 구조를 검토한다.

## 현재 구조의 한계

```
envelope.py  : VALID_SOURCE_TYPES = {"factory_state", "infra_state"} 하드코딩
normalizer.py: 특정 필드명을 직접 읽음 (temperature_celsius_avg 등)
risk.py      : 가중치 상수 하드코딩 (_TEMP_WEIGHT = 15.0 등)
```

새 센서(CO2, 진동 등) 추가 시:
- 새 필드는 S3 raw에는 저장되지만 S3 processed, DynamoDB에는 반영 안 됨
- risk 점수에도 반영 안 됨
- 새 source_type은 envelope 검증에서 거부됨

## 핵심 전제조건

Lambda가 범용으로 동작하려면 **generator가 어느 key가 센서 측정값인지를 구조로 알려줘야 한다.** 두 가지 방법이 있다.

### 방법 A: Naming Convention (generator 쪽 약속)

`sensor` 블록 안의 숫자 필드를 모두 측정값으로 인식한다. 새 센서는 `sensor` 블록에 추가하기만 하면 된다.

```json
"sensor": {
    "temperature_celsius_avg": 27.1,
    "humidity_percent_avg": 52.0,
    "co2_ppm_avg": 620.0,
    "vibration_rms_avg": 0.12
}
```

Lambda normalizer (generic):

```python
def normalize_generic(payload):
    sensor = payload.get("sensor", {})
    return {k: v for k, v in sensor.items() if isinstance(v, (int, float))}
```

generator가 `sensor` 블록 + 숫자값 규칙만 지키면 **Lambda 코드 수정 없이** 새 센서가 자동 처리된다.

### 방법 B: Config 기반 경로 정의 (Lambda 쪽 처리)

`runtime-config.yaml`에 필드 경로와 임계값을 정의하고, Lambda가 config를 읽어 처리한다.

```yaml
risk:
  source_types:
    factory_state:
      weight: 60
      field_weighting: auto
      fields:
        temperature_celsius:
          path: sensor.temperature_celsius_avg
          warning_threshold: 32.0
          critical_threshold: 38.0
        co2_ppm:
          path: sensor.co2_ppm_avg
          warning_threshold: 1000.0
          critical_threshold: 2000.0
    infra_state:
      weight: 40
      field_weighting: auto
      fields:
        nodes_not_ready_ratio:
          path: node_summary.not_ready_ratio
          warning_threshold: 0.33
          critical_threshold: 0.67
    machine_state:
      weight: 30
      field_weighting: auto
      fields:
        rpm_deviation:
          path: machine.rpm_deviation_avg
          warning_threshold: 200.0
          critical_threshold: 500.0
```

새 센서 추가 = config 수정만으로 완결. Lambda 코드는 그대로.

## 동적 Risk Score 설계

### 2계층 자동 가중치 분배

```
Risk Score (0 ~ 100, 높을수록 안전)

Tier 1: source_type 레벨 가중치 (합산 100)
  factory_state: 60
  infra_state:   40

Tier 2: source_type 내 필드 자동 균등 분배
  factory_state 필드 3개 → 각 60/3 = 20pt
  factory_state 필드 5개 → 각 60/5 = 12pt  (센서 추가 시 자동 재분배)

필드별 이상 점수 (0.0 ~ 1.0):
  정상 (value < warning)          → 0.0
  경고 (warning <= value < critical) → (value - warning) / (critical - warning)
  위험 (value >= critical)         → 1.0

최종:
  penalty = Σ (tier1_weight × 1/필드수 × anomaly_score)
  score   = 100 - penalty
```

### 계산 예시

```
factory_state (weight=60), 필드 3개 → 각 20pt
  temperature = 35°C  (warning=32, critical=38) → anomaly = 0.5  → 10pt 감점
  humidity    = 50%   (정상)                    → anomaly = 0.0  →  0pt 감점
  co2_ppm     = 800   (정상)                    → anomaly = 0.0  →  0pt 감점

infra_state (weight=40), 필드 2개 → 각 20pt
  nodes_not_ready_ratio = 0.0 (정상)            → anomaly = 0.0  →  0pt 감점

최종 score = 100 - 10 = 90 (safe)
```

센서가 늘어나도 penalty 합산 상한은 100으로 유지된다.

## 비숫자 필드 처리 (제약사항)

`abnormal_sound: "intermittent vibration"` 같은 문자열은 anomaly_score 공식에 넣을 수 없다. generator에서 숫자 점수로 변환해서 보내는 것이 전제다.

```python
# generator에서: 문자열 대신 점수로 변환
"abnormal_sound_score": 0.3 if anomaly else 0.0
```

Lambda는 숫자 필드로 동일하게 처리한다.

## 단일 Lambda 범용 처리 흐름

```
Lambda handler
  ├─ envelope 검증
  │    config에 등록된 source_type → 등록 스키마로 처리
  │    config에 없는 source_type   → S3 raw 저장만, 에러 없음
  │
  ├─ 범용 normalizer
  │    config의 field path 기반으로 값 추출
  │    (없는 필드 → 0.0, 추가 필드 → raw_extras에 보존)
  │
  ├─ 범용 risk calculator
  │    config의 weight + threshold 기반 2계층 자동 계산
  │
  ├─ DynamoDB
  │    pk = FACTORY#{factory_id}, sk = LATEST
  │    source_type별 상태 누적 저장
  │    {factory_state: {...}, infra_state: {...}, machine_state: {...}}
  │
  └─ S3 processed
       processed/{factory_id}/{source_type}/yyyy=.../...
       (s3_writer.py의 dataset 파라미터가 이미 동적 구조)
```

## 이미 호환되는 부분

| 컴포넌트 | 현재 상태 |
|---|---|
| `s3_writer.py` | `dataset` 파라미터로 경로 결정 → source_type 추가 시 코드 수정 불필요 |
| `dynamo.py._to_dynamo()` | 재귀적 dict 변환 → 어떤 구조도 DynamoDB에 저장 가능 |
| `lambda_function.py` | factory_id 기반으로 분기 없음 → 공장별 Lambda 분리 불필요 |

## 변경이 필요한 파일과 범위

| 파일 | 변경 방향 |
|---|---|
| `envelope.py` | VALID_SOURCE_TYPES 제거 → config 기반 또는 전체 허용 |
| `normalizer.py` | 특정 필드명 제거 → config path 기반 또는 convention 기반 추출 |
| `risk.py` | 상수 제거 → config 가중치·임계값 기반 2계층 계산 |
| `dynamo.py` | source_type별 저장 키 구조 소폭 조정 |
| `s3_writer.py` | 거의 변경 없음 |
| `runtime-config.yaml` | risk 스키마 섹션 추가 |
| `lambda_function.py` | config 로딩 + 범용 핸들러 분기 추가 |

## 공장별 Lambda 분리 여부

현재 시점에서 Lambda를 공장별로 분리할 필요는 없다. 단, 아래 조건 중 하나라도 해당하면 분리를 검토한다.

- 공장별로 source_type이 완전히 달라 처리 로직이 공유 불가한 경우
- 공장별 risk 가중치가 달라 config 단일 파일로 관리가 어려운 경우
- Lambda timeout 내에 처리하기 어려운 복잡한 로직이 공장마다 달리 필요한 경우

## 실현 가능 여부 요약

| 조건 | 가능 여부 | 비고 |
|---|---|---|
| source_type 자유롭게 추가 | 가능 | config 등록만 하면 됨 |
| 센서 수 증가 시 risk score 자동 계산 | 가능 | 2계층 자동 분배 |
| 센서 종류 추가 시 processed 저장 | 가능 | s3_writer 이미 동적 구조 |
| Lambda 코드 수정 없이 새 센서 적용 | 가능 | generator naming convention 또는 config path 정의 전제 |
| 문자열 센서값 risk 자동 반영 | 불가 | generator에서 숫자 점수로 변환 필요 |
| Lambda 공장별 분리 | 현재 불필요 | 처리 로직 차이 없음 |
