# Issue Edit Notes

상태: superseded
기준일: 2026-05-15

## 현재 기준

이 파일은 과거 `edge-agent` 단일 이미지와 real/dummy mode를 검토하던 임시 메모를 대체한다.

최신 기준은 아래 문서를 source of truth로 사용한다.

- `docs/issues/M3_deploy-pipeline.md`
- `docs/issues/M4_data-plane.md`
- `docs/issues/M5_vm-spoke-expansion.md`
- `docs/planning/06_edge_agent_deployment_plan.md`
- `docs/specs/iot_data_format.md`
- `docs/specs/data_storage_pipeline.md`

## 2026-05-15 확정 방향

M3에서는 ECR, GitHub Actions build/push, Hub ArgoCD ApplicationSet, `factory-a` 보수적 rollout/rollback까지 완료했다.

M3 Issue 6 manifest tag update workflow, Issue 7 deploy verification workflow, Issue 8 push-to-rollout 검증은 실제 Edge data-plane image가 확정될 때까지 보류한다.

M4에서는 단일 `edge-agent`가 아니라 아래 두 계층으로 데이터 플레인을 구현한다.

```text
factory-a:
  factory-a-log-adapter
    -> canonical JSON
    -> local spool/outbox
  edge-iot-publisher
    -> AWS IoT Core
    -> S3 raw

factory-b/c:
  dummy-data-generator
    -> canonical JSON
    -> local spool/outbox
  edge-iot-publisher
    -> AWS IoT Core
    -> S3 raw
```

M4 완료 후에는 `factory-a-log-adapter`와 `edge-iot-publisher` 이미지를 기준으로 M3 Issue 6~8을 재개한다.

M5에서는 `factory-b/c`에 `dummy-data-generator`와 공통 `edge-iot-publisher`를 배포해 같은 데이터 플레인 경로를 검증한다.
