# 0002. Failback Controller: Kubernetes CronJob -> Master OS Cron

상태: accepted
결정일: 2026-04-29
관련 범위: M0 factory-a, failover/failback

## 기존 계획

Kubernetes 내부 CronJob 또는 workload 기반 자동화로 worker2 복구 후 failback을 처리한다.

## 변경된 실제 기준

Failback은 master OS cron에서 실행하는 Kubernetes-only 스크립트로 처리한다.

스크립트는 SSH나 노드 비밀번호를 사용하지 않고 Kubernetes API와 `kubectl`만 사용한다.

현재 기준 스크립트:

```text
/usr/local/sbin/safe-edge-failback.sh
```

repository 기준:

```text
safe-edge/scripts/safe-edge-failback.sh
```

## 변경 이유

센서, 카메라, 오디오 workload는 실제 장치를 잡는 하드웨어 의존 Pod다.

Kubernetes 내부 CronJob 방식은 정상 Pod를 잘못 삭제하거나, 장애 중인 노드와 stale Pod 상태를 충분히 구분하지 못할 위험이 있었다.

master OS cron 방식은 control-plane에서 Kubernetes API 기준으로만 판단하며, 대상 Pod가 이미 worker2에 있으면 skip하도록 단순하게 만들 수 있다.

## 영향

- 정상 동작 중인 worker2 Pod를 불필요하게 죽이지 않는다.
- worker2 복구 후 대상 Pod가 worker1에 남아 있을 때만 정리할 수 있다.
- Failback 자동화가 Kubernetes 내부 workload에 의존하지 않는다.
- OS cron 상태도 운영 점검 대상에 포함해야 한다.

## 업데이트 필요한 문서

- `docs/issues/M0_factory-a_safe-edge-baseline.md`
- `docs/ops/03_test_checklist.md`
- `docs/ops/04_troubleshooting.md`
- `docs/ops/09_failover_failback_test_results.md`
- `docs/architecture/00_current_architecture.md`

## 검증

- failback log에서 대상 Pod가 worker2에 있으면 `SKIP` 처리 확인
- worker2 복구 후 AI/audio/BME가 worker2로 돌아오는 것 확인
- 시작 점검에서 `/var/log/safe-edge-failback.log` 정상 확인
