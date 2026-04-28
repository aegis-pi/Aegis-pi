# 데모 운영 메모

상태: source of truth
기준일: 2026-04-28

## 목적

`factory-a` 단독 데모 전에 확인해야 할 운영 항목을 기록한다.

## 데모 전 확인

```bash
kubectl get nodes -o wide
kubectl -n argocd get application
kubectl -n monitoring get pod -o wide
kubectl -n ai-apps get pod -o wide
kubectl -n longhorn-system get volumes.longhorn.io -o wide
```

정상 기준:

```text
All nodes Ready
ArgoCD Synced / Healthy
Grafana 접근 가능
Longhorn healthy
target Pods worker2 Running
```

## 브라우저 준비

```text
ArgoCD: http://10.10.10.200
Longhorn: http://10.10.10.201
Grafana: http://10.10.10.202
GitHub: https://github.com/aegis-pi/safe-edge-config-main.git
```

## 시연 중 주의

- 실제 전원/LAN 장애 테스트를 다시 수행할 경우 시작 전 상태와 timestamp를 기록한다.
- 장애 시작 후 첫 5분은 성공/실패 판정하지 않는다.
- worker2 Ready만으로 failback 완료로 보지 않는다.
- 대상 Pod 3개가 worker2 Running이어야 failback 완료다.

## 백업 플랜

실시간 장애 테스트가 어려우면 이미 기록된 결과를 사용한다.

```text
docs/ops/09_failover_failback_test_results.md
docs/ops/03_test_checklist.md
```

## 데모 메시지

- Safe-Edge를 버리지 않고 실제 운영형 기준선으로 복구했다.
- GitOps, monitoring, storage, failover/failback까지 검증했다.
- Hub/Risk Twin 확장은 이 기준선 위에 올린다.
