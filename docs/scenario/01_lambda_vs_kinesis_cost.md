# Lambda vs Kinesis 비용 비교 시나리오

상태: 검토 완료
기준일: 2026-05-27

## 배경

데이터 파이프라인 설계 시 IoT Core 수신 메시지를 처리하는 방식으로 **직접 Lambda 호출**과 **Kinesis 경유** 두 가지 후보를 검토했다. 초기 논의에서 "센서 150개 이상이면 Kinesis가 효율적이고, 현재는 그 미만이므로 Lambda를 선택한다"는 결론이 있었다. 이후 아키텍처와 데이터 파이프라인이 확정된 시점에 실제 수치로 재검토했다.

## 확정된 아키텍처 파라미터

| 항목 | 값 | 출처 |
|---|---|---|
| AWS 리전 | ap-south-1 (Mumbai) | `configs/runtime/runtime-config.yaml` |
| Lambda 메모리 | 512MB | `infra/data-pipeline/lambda.tf` |
| Lambda timeout | 60초 | `infra/data-pipeline/lambda.tf` |
| DynamoDB 과금 | PAY_PER_REQUEST | `infra/foundation/dynamodb.tf` |
| factory_state 발행 주기 | 3초 | `apps/dummy-sensor/factory_b_dummy_generator.py` |
| infra_state 발행 주기 | 20초 | `apps/dummy-sensor/factory_b_dummy_generator.py` |
| 현재 공장 수 | 3개 (factory-a/b/c) | `infra/data-pipeline/iot_rule.tf` |

**Lambda 메시지 1개당 실제 I/O 작업:**

```
factory_state 1건:
  DynamoDB: GetItem + UpdateItem + GetItem + PutItem = 4회
  S3 PUT:   factory_state + risk_score + state_snapshot = 3회
  IoT Rule: S3 raw PUT = 1회 (Lambda 외부, 별도)

infra_state 1건:
  DynamoDB: UpdateItem + GetItem + PutItem = 3회
  S3 PUT:   infra_state + state_snapshot = 2회
```

Lambda 1회 실행 예상 소요 시간: **약 350ms**

## Kinesis 구성 패턴 비교

Kinesis 도입 시 두 가지 패턴이 존재한다.

**패턴 A: IoT Rule → Kinesis 직접 PUT → Lambda Consumer**

```
IoT Core
  └─ IoT Rule Action: Kinesis PUT (Lambda 없음)
       └─ Kinesis Stream
            └─ Lambda Consumer (event source mapping, 배치당 1회 호출)
```

**패턴 B: IoT Rule → Lambda Producer → Kinesis → Lambda Consumer**

```
IoT Core
  └─ IoT Rule Action: Lambda Producer (메시지당 1회 호출)
       └─ Kinesis PUT
            └─ Kinesis Stream
                 └─ Lambda Consumer (event source mapping, 배치당 1회 호출)
```

### 이 프로젝트에 적용 가능한 패턴: A

현재 IoT Rule SQL이 `SELECT * FROM 'aegis/{factory_id}/+'` 형태로 변환 없이 메시지를 그대로 가져온다. IoT Core는 Kinesis PUT action을 내장 지원하므로 Producer Lambda가 불필요하다. 기존 `apps/data-processor/lambda_function.py`를 Consumer Lambda로 그대로 사용할 수 있다.

패턴 B는 Producer Lambda가 메시지마다 호출되므로 Direct Lambda와 호출 비용이 동일하면서 Kinesis 비용과 Consumer Lambda 비용이 추가된다. 센서 수와 무관하게 항상 Direct Lambda보다 비싸다.

## 비용 비교

### 현재 규모 (공장 3개, 약 3M건/월)

| 비용 항목 | Direct Lambda | Kinesis 패턴 A |
|---|---|---|
| Lambda 요청 | $0.40 | ~$0 |
| Lambda Duration | $2.08 | $2.08 (동일) |
| Kinesis 샤드 | $0 | $10.80 |
| Kinesis PUT | $0 | $0.04 |
| **합계** | **$2.48/월** | **$12.92/월** |

현재 규모에서 Kinesis는 Direct Lambda보다 **5.2배 비싸다.**

### 손익분기 계산

센서 1개당 월간 메시지 수: `1/3 msg/s × 3,600 × 24 × 30 = 864,000건/월`

Kinesis 도입 시 절감되는 비용은 Lambda 요청 횟수 감소분(배치 100개 기준)이며, 추가되는 비용은 Kinesis 샤드와 PUT 요금이다. Duration 비용은 순차 처리 기준으로 양쪽이 동일하다.

```
절감액: N × 864K × $0.20/1M × (1 - 1/100) = N × $0.171/월
추가액: $10.80 (샤드) + N × 864K × $0.014/1M = $10.80 + N × $0.0121/월

손익분기:
  N × $0.171 = $10.80 + N × $0.0121
  N × $0.159 = $10.80
  N ≈ 68 센서
```

| 처리 방식 | 손익분기 | 비고 |
|---|---|---|
| 순차 처리 (현재 코드 유지) | **약 68개 센서** | 코드 변경 없음 |
| 병렬 async 처리 | **약 4개 센서** | Lambda 내부 async 재설계 필요 |

## 공장 규모별 센서 수 기준

| 공장 규모 | 직원 수 기준 | 일반적인 센서 수 |
|---|---|---|
| 소규모 | 50명 미만, 라인 1~2개 | 10~50개 |
| 중소규모 | 50~150명, 라인 2~5개 | 50~150개 |
| 중규모 | 150~300명, 라인 5개 이상 | 150~500개 |
| 대규모 | 300명 이상 | 500개 이상 |

생산라인 1개 기준 센서 구성 예시:

```
온도/습도 센서 (구역별):      5~10개
기계 진동 센서 (장비별):      5~10개
전력 미터:                    3~5개
환경 센서 (CO2, 먼지, 소음):  3~5개
안전 센서 (연기, 비상정지):   5~10개
────────────────────────────────────
라인 1개 소계:                21~40개
```

라인 2개 기준이면 40~80개로 손익분기(68개)에 근접하거나 초과한다.

## 결론

현재 아키텍처(IoT Rule → Lambda 직접 호출)는 소규모 공장 타겟 기준으로 유효한 선택이다. 손익분기인 68개 센서는 소규모~중소규모 경계에 해당하며, 대규모로 보기 어렵다.

| 타겟 공장 규모 | 예상 센서 수 | 권장 방식 |
|---|---|---|
| 소규모 (라인 1~2개) | 10~50개 | Direct Lambda 유지 |
| 중소규모 (라인 2~5개) | 50~150개 | 68개 초과 시점에 Kinesis 패턴 A 전환 검토 |
| 중규모 이상 | 150개 이상 | Kinesis 패턴 A |

초기 논의에서 제시된 150개 임계값은 방향은 맞지만 실제 손익분기는 약 68개다. 현재 3개 공장(≈ 3개 센서 단위) 규모에서는 Lambda가 올바른 선택이며, 센서 수가 68개를 초과하는 시점에 Kinesis 패턴 A로 전환하면 비용 효율이 높아진다.
