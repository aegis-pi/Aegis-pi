# Pipeline Status Aggregator

상태: legacy placeholder

이 디렉터리는 이전 설계에서 IoT Core 수신과 S3 적재 상태를 기준으로 `pipeline_status`를 계산하는 보조 서비스 코드를 두기 위한 자리였다.

## 2026-05-14 수정 방향

최신 기준에서는 별도 `pipeline-status-aggregator` 컨테이너 서비스/파드를 구현하지 않는다.

`pipeline_status` 계산은 Lambda data processor가 `infra_state` 수신 시점, S3 raw 적재 시각, heartbeat 필드를 바탕으로 수행하고 DynamoDB LATEST/HISTORY에 반영한다.
