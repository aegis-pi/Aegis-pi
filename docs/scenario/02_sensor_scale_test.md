# 센서 규모 확장 테스트 시나리오

상태: 계획
기준일: 2026-05-27

## 개요

현재 factory-b, factory-c에서 각 1개씩 동작하는 더미 센서를 단계적으로 50 → 100 → 150개로 늘려 데이터 전송·저장·처리 속도가 유지되는지 검증한다. 이 테스트는 `docs/scenario/01_lambda_vs_kinesis_cost.md`에서 도출한 **68개 센서 손익분기** 전후의 실제 동작을 확인하는 목적도 겸한다.

## 현재 기준선

| 구분 | 내용 |
|---|---|
| factory-a | 실제 BME280 센서 1개 (Raspberry Pi) |
| factory-b | 더미 생성기 1개 인스턴스 (Mac mini VM) |
| factory-c | 더미 생성기 1개 인스턴스 (Windows VM) |
| **현재 총 센서 수** | **3개 단위** |
| factory_state 주기 | 3초 |
| infra_state 주기 | 20초 |
| 현재 총 메시지율 | 약 1.15 msg/s |

## 테스트 구현 방법

현재 더미 생성기는 `AEGIS_WORKER_NODE_ID` 환경변수로 센서 ID를 구분한다. 같은 outbox 디렉터리에 `message_id = {factory_id}:factory_state:{worker_node_id}:{timestamp}` 형태의 파일을 쓰므로, worker_node_id가 다르면 파일명이 겹치지 않는다.

여러 인스턴스를 서로 다른 `AEGIS_WORKER_NODE_ID`로 동시에 실행하면 센서 수를 늘릴 수 있다.

### 인스턴스 실행 예시

```bash
# sensor-001 ~ sensor-050 동시 실행 예시 (bash)
for i in $(seq -w 1 50); do
  AEGIS_FACTORY_ID=factory-b \
  AEGIS_WORKER_NODE_ID=sensor-${i} \
  AEGIS_OUTBOX_DIR=/var/lib/aegis/outbox \
  AEGIS_SEQUENCE_FILE=/var/lib/aegis/factory-b-seq-${i} \
  AEGIS_CLUSTER_STATE_MODE=synthetic \
  python3 /opt/aegis/dummy-sensor/factory_b_dummy_generator.py --loop &
done
```

단일 `edge-iot-publisher`가 동일 outbox를 스캔하여 순서대로 발행한다.

### 단계별 센서 수 및 메시지율

| 단계 | 센서 수 | factory_state msg/s | 총 msg/s | 월간 메시지 수 |
|---|---|---|---|---|
| 현재 | 3 | 1.0 | 1.15 | ~3M |
| 1단계 | 50 | 16.7 | 19.2 | ~50M |
| 2단계 | 100 | 33.3 | 38.3 | ~99M |
| 3단계 | 150 | 50.0 | 57.5 | ~149M |

## 확인 항목

### 1. Outbox 적체 (Edge 구간)

`edge-iot-publisher`는 outbox 파일을 순차적으로 스캔하고 파일당 새 TLS 연결을 맺는다. 센서 수가 늘면 생성 속도가 발행 속도를 초과할 수 있다.

| 확인 지표 | 방법 | 허용 기준 |
|---|---|---|
| outbox 파일 수 | `ls /var/lib/aegis/outbox \| wc -l` (주기적 모니터링) | 지속 증가 없이 안정 |
| publisher 로그 처리 속도 | systemd 로그에서 `published` 라인 수/분 확인 | 생성 속도 이상 유지 |
| quarantine 발생 여부 | `ls /var/lib/aegis/outbox/quarantine/` | 0건 |

### 2. IoT Core 수신율

| 확인 지표 | 방법 | 허용 기준 |
|---|---|---|
| 수신 메시지 수 | CloudWatch: `AWS/IoT > Protocol.PublishIn.Success` | 발행 수와 일치 |
| 수신 오류 | CloudWatch: `Protocol.PublishIn.ClientError` | 0 |

### 3. Lambda 처리 속도 및 안정성

| 확인 지표 | CloudWatch 지표 | 허용 기준 |
|---|---|---|
| 호출 수 | `Invocations` | 수신 메시지 수와 일치 |
| 실행 시간 | `Duration` (p50, p99) | p99 < 10초 |
| 에러율 | `Errors / Invocations` | 0% |
| Throttle | `Throttles` | 0 |
| 동시 실행 수 | `ConcurrentExecutions` | < 1,000 (기본 한도) |

Lambda 동시 실행 수 예상값:

```
센서 50개:  16.7 msg/s × 0.35s Duration ≈ 동시 6개
센서 100개: 33.3 msg/s × 0.35s Duration ≈ 동시 12개
센서 150개: 50.0 msg/s × 0.35s Duration ≈ 동시 18개
```

기본 한도(1,000개) 대비 여유가 크므로 Throttle은 발생하지 않을 것으로 예상한다.

### 4. DynamoDB 저장 속도

| 확인 지표 | CloudWatch 지표 | 허용 기준 |
|---|---|---|
| Write 소비량 | `ConsumedWriteCapacityUnits` | 스로틀 없음 |
| 읽기 소비량 | `ConsumedReadCapacityUnits` | 스로틀 없음 |
| 시스템 오류 | `SystemErrors` | 0 |

PAY_PER_REQUEST 모드이므로 자동 스케일된다. 스로틀은 발생하지 않을 것으로 예상한다.

### 5. S3 저장 속도

| 확인 지표 | 방법 | 허용 기준 |
|---|---|---|
| PUT 성공율 | CloudWatch S3 `PutRequests` vs `5xxErrors` | 에러 0 |
| 파일 생성 확인 | S3 콘솔에서 `processed/factory-b/` 하위 파일 수 확인 | 센서 수에 비례 |

메시지 1건당 S3 PUT 수:

```
factory_state: raw(IoT Rule) + factory_state + risk_score + state_snapshot = 4회
infra_state:   raw(IoT Rule) + infra_state + state_snapshot = 3회
```

센서 150개 기준 최대 S3 PUT 속도: 약 50 msg/s × 4 = 200 PUT/s. S3 기본 한도(3,500 PUT/s) 대비 여유롭다.

### 6. End-to-End 지연

센서 발행 시점부터 S3 processed 파일 생성까지의 전체 지연을 측정한다.

```
측정 기준:
  시작: factory_state의 source_timestamp
  종료: S3 processed/{factory_id}/factory_state/.../message_id.json 의 processed_at

허용 기준: p99 < 5초
```

## 예상 병목 지점

### edge-iot-publisher (가장 높은 위험)

현재 publisher는 파일당 TLS 연결을 새로 맺는다. 센서 수 증가 시 outbox 파일이 쌓이는 속도가 발행 속도를 초과할 수 있다.

```
TLS 연결 1회 소요 시간: ~100~200ms (추정)
센서 50개 생성 속도: 16.7 파일/s
publisher 처리 가능 속도: 1 / 0.15s ≈ 6.7 파일/s (추정)
→ 50개 단계부터 적체 발생 가능
```

이 경우 publisher의 persistent connection 유지 또는 병렬 발행 방식 검토가 필요하다.

### Lambda Duration 증가

DynamoDB 및 S3 호출이 동기 순차 방식이므로 Lambda 동시 실행 수 증가 시 네트워크 지연이 누적될 수 있다. Duration p99가 10초를 초과하면 처리 지연 경보로 본다.

## 아키텍처 판단 연계

`01_lambda_vs_kinesis_cost.md`에서 도출한 손익분기를 실측으로 확인한다.

| 단계 | 센서 수 | Lambda vs Kinesis 비용 관계 | 주목 지점 |
|---|---|---|---|
| 1단계 | 50 | Lambda 유리 (68개 미만) | 기준선 확인 |
| 2단계 | 100 | Kinesis 유리 (68개 초과) | Kinesis 전환 타당성 검토 시작 |
| 3단계 | 150 | Kinesis 유리 | 전환 시 월 비용 절감 실측 |

100개 단계에서 실제 Lambda Duration과 CloudWatch 비용 지표를 측정하여 이론값(01 시나리오)과 비교한다.

## 테스트 순서

1. factory-b VM에서 단계별 인스턴스 실행
2. 각 단계에서 10분 이상 안정 동작 확인
3. 위 확인 항목 지표를 CloudWatch에서 수집
4. outbox 적체 여부 주기적으로 확인 (1분 간격)
5. e2e 지연 샘플 10건 이상 측정
6. 다음 단계로 이동 전 인스턴스 전체 종료 후 outbox 비우기
