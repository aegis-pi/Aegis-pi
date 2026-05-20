# 0018. IoT Rule factory-c raw S3 extension

상태: accepted
결정일: 2026-05-20

## 기존 계획

초기 IoT Rule 검증은 `factory-a` raw 데이터 적재를 중심으로 진행했다.

## 변경된 실제 기준

`factory-c` 테스트베드도 독립 MQTT topic과 S3 raw prefix를 사용한다.

```text
topic: aegis/factory-c/+
S3: raw/factory-c/{source_type}/yyyy=.../{message_id}.json
```

`factory-b`도 같은 원칙으로 `raw/factory-b/...`에 분리 적재한다.

## 변경 이유

M5의 목적은 실제 센서 정확도 검증이 아니라 멀티 factory 식별, 배포, 수집, prefix 분리, 후속 Dashboard 카드 분리 표시를 검증하는 것이다. 따라서 `factory-a`와 같은 raw data-plane 계약을 VM 테스트베드에도 적용해야 한다.

## 영향

- IoT Core topic filter와 S3 prefix가 factory별로 분리된다.
- Lambda data processor는 `factory_id` 기준으로 DynamoDB LATEST/HISTORY item을 독립 갱신해야 한다.
- S3 raw는 `factory-a`, `factory-b`, `factory-c` prefix를 모두 갖는다.

## 검증

2026-05-20 기준 `factory-c` local dummy generator와 publisher를 통해 `raw/factory-c/...` 적재를 확인했다. `factory-b`도 같은 방식으로 `raw/factory-b/...` 적재를 확인했다.
