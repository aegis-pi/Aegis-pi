# Change 0022 - DataProcessor freshness refresh

상태: accepted
기준일: 2026-05-29

## 배경

`factory-a`가 2026-05-28T07:54Z 이후 새 IoT 메시지를 보내지 않았는데 DynamoDB `LATEST`에는 이전 `risk.score=100` 값이 남아 있었다. 기존 DataProcessor는 `factory_state` 또는 `infra_state` 메시지를 수신할 때만 `pipeline_status`와 `risk`를 재계산했기 때문에, 입력이 완전히 끊긴 factory는 stale safe 상태로 보일 수 있었다.

## 결정

`infra/data-pipeline`에 EventBridge Scheduler `AEGIS-Schedule-DataProcessorRefresh1m`를 추가한다. 이 Scheduler는 1분마다 `AEGIS-Lambda-DataProcessor`를 아래 action으로 호출한다.

```json
{"action":"refresh_pipeline_status","factories":["factory-a","factory-b","factory-c"]}
```

DataProcessor는 각 factory의 DynamoDB `LATEST`를 읽고, `last_infra_state_at` 기준으로 `pipeline_status`를 다시 계산한 뒤 최신 `factory_state`/`infra_state`와 함께 `risk-v0.2.0` risk를 재계산한다. 결과는 `LATEST`, `HISTORY#STATE`, S3 `processed/{factory_id}/state_snapshot/`에 저장한다.

## 영향

- 새 IoT 메시지가 없어도 Dashboard/API가 읽는 DynamoDB `LATEST`의 `pipeline_status`와 `risk`가 현재 시각 기준으로 갱신된다.
- stale `risk.score=100` 표시를 방지한다.
- `factory-a` 입력 중단 상태는 `pipeline_status=critical`, `risk.level=danger`, `risk.score=0`으로 표시된다.
- `factory-b/c`는 정상 입력 기준 `pipeline_status=normal`, `risk.level=safe`, `risk.score=100`으로 유지된다.

## 검증

- `python -m pytest apps/data-processor/tests`: 24 passed.
- `terraform -chdir=infra/data-pipeline validate`: success.
- `terraform -chdir=infra/data-pipeline apply`: complete, 4 added and 1 changed.
- Lambda config: `FACTORY_IDS=factory-a,factory-b,factory-c`, `LastUpdateStatus=Successful`.
- Scheduler: `AEGIS-Schedule-DataProcessorRefresh1m`, `ENABLED`, `rate(1 minute)`.
- Manual refresh invoke 결과: `factory-a critical/danger/0`, `factory-b/c normal/safe/100`.
- CloudWatch `/aws/lambda/AEGIS-Lambda-DataProcessor`: `pipeline refresh done` 반복 확인.
