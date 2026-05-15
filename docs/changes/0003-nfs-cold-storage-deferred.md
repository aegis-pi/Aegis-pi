# 0003. NFS Cold Storage and Hot/Cold Tiering Deferred

상태: accepted
결정일: 2026-04-29
관련 범위: M0 factory-a, data retention, automation

## 기존 계획

Host PC NFS cold storage와 hot/cold tiering을 M0 범위에 포함해 장기 보존 경로를 만든다.

Ansible 기반 복구/자동화도 함께 검토한다.

## 변경된 실제 기준

NFS cold storage와 hot/cold tiering은 M0 핵심 완료 조건에서 제외한다.

M0에서는 로컬 저장소 증가를 제한하기 위해 아래 정책을 우선 적용한다.

```text
InfluxDB safe_edge_db retention: 1d
AI snapshot cleanup: 24h
AI snapshot daily purge: every day 03:00 KST
```

장기 보존은 후속 Edge data-plane, IoT Core, S3 데이터 플레인에서 다룬다.

## 변경 이유

M0의 핵심 목표는 `factory-a` Safe-Edge 기준선 복구와 장애 시 failover/failback 검증이다.

NFS와 hot/cold tiering은 운영 복잡도를 늘리지만, M0 장애 검증의 필수 경로는 아니었다.

Cloud 데이터 플레인이 후속 범위로 분리되면서 장기 보존 책임도 S3 중심 구조로 넘기는 편이 더 단순하다.

## 영향

- M0 완료 범위가 더 명확해졌다.
- 로컬 디스크 증가는 retention/purge 정책으로 제한한다.
- 장기 이력 보존은 M4 이후 IoT Core/S3 파이프라인에서 검증한다.
- Ansible 자동화는 M7 통합 검증 반복성 확보 단계에서 다시 검토한다.

## 업데이트 필요한 문서

- `docs/issues/M0_factory-a_safe-edge-baseline.md`
- `docs/issues/MASTER_CHECKLIST.md`
- `docs/ops/08_data_retention.md`
- `docs/ops/11_ansible_test_automation.md`
- `docs/planning/02_implementation_plan.md`

## 검증

- InfluxDB retention policy 1일 적용 확인
- AI snapshot 24시간 cleanup sidecar 적용 확인
- worker1/worker2 daily purge CronJob 적용 확인
