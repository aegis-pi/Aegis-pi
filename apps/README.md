# Apps

이 디렉터리는 Aegis-Pi에서 직접 구현할 애플리케이션 코드를 서비스별로 나누어 두는 공간이다.

현재는 대부분 구현 전 placeholder이다. 2026-05-15 최신 기준에서 Edge data-plane 구현 대상은 단일 `edge-agent`가 아니라 아래 두 계층으로 분리한다.

```text
factory-a-log-adapter
  raw/log/status -> canonical JSON -> local spool/outbox

edge-iot-publisher
  local spool/outbox canonical JSON -> AWS IoT Core

dummy-data-generator
  factory-b/c 테스트베드 canonical JSON 생성 -> local spool/outbox
```

IoT Core 이후 정규화/Risk 계산/latest 저장은 별도 `risk-normalizer`, `risk-score-engine`, `pipeline-status-aggregator` 파드가 아니라 Lambda data processor와 DynamoDB/S3 processed로 처리한다.

## 하위 폴더

| 경로 | 역할 |
| --- | --- |
| `edge-agent/` | M3 GitHub Actions/ECR 검증용 smoke image. 실제 Edge data-plane 로직은 M4에서 adapter/publisher로 분리 구현 |
| `dummy-sensor/` | legacy 이름의 placeholder. M5에서는 `dummy-data-generator` 기준으로 정리 |
| `risk-normalizer/` | legacy placeholder. 최신 기준에서는 Lambda data processor의 정규화 로직으로 대체 |
| `risk-score-engine/` | legacy placeholder. 최신 기준에서는 Lambda data processor의 Risk 계산 로직으로 대체 |
| `pipeline-status-aggregator/` | legacy placeholder. 최신 기준에서는 Lambda data processor가 DynamoDB LATEST/HISTORY에 `pipeline_status`를 갱신 |

## 2026-05-14 수정 방향

- `risk-normalizer`, `risk-score-engine`, `pipeline-status-aggregator`를 ECR 컨테이너 이미지 대상으로 잡지 않는다.
- M3 Issue 2의 ECR 범위였던 `edge-agent`는 smoke image 검증 경로다.
- M4에서는 실제 ECR 대상 후보를 `factory-a-log-adapter`, `edge-iot-publisher`, M5에서는 `dummy-data-generator`로 재정의한다.
- Lambda를 container image로 배포하기로 결정할 때만 별도 ECR repository를 추가하며, 그 이름은 기존 legacy 서비스명이 아니라 `aegis-data-processor` 같은 통합 Lambda 처리기 기준으로 정한다.
