# Apps

기준일: 2026-06-04

이 디렉터리는 Aegis-Pi에서 직접 구현할 애플리케이션 코드를 서비스별로 나누어 두는 공간이다.

2026-06-01 기준 Edge data-plane 구현 대상은 단일 `edge-agent`가 아니라 아래 계층으로 분리되어 있다.

```text
factory-a-log-adapter
  raw/log/status -> canonical JSON -> local spool/outbox

edge-iot-publisher
  local spool/outbox canonical JSON -> AWS IoT Core

dummy-sensor factory-b/c generator
  factory-b/c 테스트베드 canonical JSON 생성 -> local spool/outbox
```

IoT Core 이후 정규화/Risk 계산/latest 저장은 별도 `risk-normalizer`, `risk-score-engine`, `pipeline-status-aggregator` 파드가 아니라 Lambda data processor와 DynamoDB/S3 processed로 처리한다. 최근 그래프 read model은 `graph-metrics-aggregator` Lambda가 DynamoDB `HISTORY#STATE`를 읽어 `GRAPH#5M`과 S3 `processed_agg`로 집계한다. Cloud 상태는 `cloud-infra-collector`, Slack 알림은 `risk-alert-dispatcher`가 담당한다.

## 하위 폴더

| 경로 | 역할 |
| --- | --- |
| `factory-a-log-adapter/` | M4 Issue 2 실제 구현. InfluxDB/Kubernetes 상태를 canonical JSON으로 변환해 local spool/outbox에 기록 |
| `edge-iot-publisher/` | M4 Issue 3 실제 구현. local spool/outbox canonical JSON을 AWS IoT Core로 publish |
| `data-processor/` | M4 Issue 6 실제 구현. AWS Lambda data processor. IoT Core 수신 메시지 → DynamoDB LATEST/HISTORY#STATE, S3 processed 저장, Risk/pipeline_status 계산 |
| `graph-metrics-aggregator/` | 5분 그래프 집계 Lambda. DynamoDB `HISTORY#STATE` 조회 → DynamoDB `GRAPH#5M` 및 S3 `processed_agg/metrics_5m` 저장 |
| `cloud-infra-collector/` | 1분 fast/5분 slow Cloud infra collector. ECS/ALB/data-pipeline/EKS/Kubernetes 상태 → DynamoDB `CLOUD#infra`, S3 `processed/cloud_infra` 저장 |
| `risk-alert-dispatcher/` | Factory/Cloud processed snapshot의 warning/danger 평가, 연속 관측 확인, DynamoDB cooldown/dedupe, Slack 전송 |
| `edge-agent/` | M3 GitHub Actions/ECR 검증용 smoke image. 실제 Edge data-plane 로직은 M4에서 adapter/publisher로 분리 구현 |
| `dummy-sensor/` | legacy 이름을 유지하지만 실제 factory-b/c dummy generator, legacy/manual publisher, systemd unit/runbook, 테스트를 포함 |
| `risk-normalizer/` | legacy placeholder. 최신 기준에서는 Lambda data processor의 정규화 로직으로 대체 |
| `risk-score-engine/` | legacy placeholder. 최신 기준에서는 Lambda data processor의 Risk 계산 로직으로 대체 |
| `pipeline-status-aggregator/` | legacy placeholder. 최신 기준에서는 Lambda data processor가 DynamoDB LATEST/HISTORY#STATE에 `pipeline_status`를 갱신 |

## 2026-05-14 수정 방향

- `risk-normalizer`, `risk-score-engine`, `pipeline-status-aggregator`를 ECR 컨테이너 이미지 대상으로 잡지 않는다.
- M3 Issue 2의 ECR 범위였던 `edge-agent`는 smoke image 검증 경로다.
- M4에서는 실제 ECR 대상 후보를 `factory-a-log-adapter`, `edge-iot-publisher`, M5에서는 `dummy-data-generator`로 재정의한다.
- Lambda를 container image로 배포하기로 결정할 때만 별도 ECR repository를 추가하며, 그 이름은 기존 legacy 서비스명이 아니라 `aegis-data-processor` 같은 통합 Lambda 처리기 기준으로 정한다.
