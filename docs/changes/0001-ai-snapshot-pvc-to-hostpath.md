# 0001. AI Snapshot Storage: Longhorn PVC -> Node-local hostPath

상태: accepted
결정일: 2026-04-29
관련 범위: M0 factory-a, ai-apps, failover/failback

## 기존 계획

AI event snapshot을 Longhorn RWO PVC `safe-edge-ai-snapshots`에 저장한다.

Pod 내부 mount path는 `/app/snapshots`로 둔다.

## 변경된 실제 기준

AI event snapshot은 node-local hostPath `/var/lib/safe-edge/snapshots`에 저장한다.

Pod 내부 mount path는 기존과 같은 `/app/snapshots`다.

AI 추론 결과는 기존처럼 InfluxDB에 기록하고, InfluxDB PVC를 통해 Longhorn에 저장한다.

## 변경 이유

worker2 장애 시 기존 AI Pod와 VolumeAttachment가 남아 Longhorn RWO PVC Multi-Attach 문제가 발생했다.

그 결과 failover된 `safe-edge-integrated-ai` Pod가 worker1에서 `ContainerCreating` 상태에 머물 수 있었다.

Snapshot 이미지는 장기 보존 핵심 데이터가 아니라 임시 이벤트 이미지이므로, failover 안정성을 우선해 node-local hostPath로 변경했다.

## 영향

- AI Pod failover가 Longhorn RWO attach에 막히지 않는다.
- Snapshot 이미지는 노드 로컬 임시 데이터가 된다.
- Snapshot 장기 보존은 후속 edge-agent 또는 cloud upload 계층에서 처리한다.
- AI 추론 결과 자체는 InfluxDB PVC를 통해 Longhorn에 남는다.

## 업데이트 필요한 문서

- `docs/issues/M0_factory-a_safe-edge-baseline.md`
- `docs/ops/09_failover_failback_test_results.md`
- `docs/ops/10_edge_workload_placement.md`
- `docs/architecture/00_current_architecture.md`

## 검증

- worker2 `k3s-agent` 중지 테스트에서 AI/audio/BME worker1 failover 성공
- worker2 LAN 제거 테스트에서 AI/audio/BME worker1 failover 성공
- Longhorn Multi-Attach 재발 없음
