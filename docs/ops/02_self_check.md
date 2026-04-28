# 셀프 체크 가이드

상태: source of truth
기준일: 2026-04-28

## 목적

`factory-a` Safe-Edge 기준선이 현재 운영 가능한 상태인지 빠르게 확인하기 위한 점검표다.

## 현재 상태

- `factory-a`는 3노드 K3s, ArgoCD, Helm, Longhorn, InfluxDB, Grafana 기준선 구성이 완료됐다.
- GitOps 원격 저장소는 `https://github.com/aegis-pi/safe-edge-config-main.git`를 사용한다.
- ArgoCD repository 등록과 sync 조작은 UI에서 수행한다.
- Hub, `factory-b`, `factory-c`, AWS IoT Core, S3, Risk Twin은 후속 단계다.

## 범위

- K3s 노드 상태
- GitOps/ArgoCD 상태
- 모니터링 및 데이터 수집 상태
- Longhorn 복제 상태
- Failover/Failback 준비 상태
- 후속 Hub 확장 전 확인 항목

## 기본 접속 정보

| 항목 | 값 |
| --- | --- |
| master | `10.10.10.10` |
| worker1 | `10.10.10.11` |
| worker2 | `10.10.10.12` |
| ArgoCD UI | `http://10.10.10.200` |
| Longhorn UI | `http://10.10.10.201` |
| Grafana UI | `http://10.10.10.202` |

## 시작 전 체크

아래 항목은 세션을 시작할 때마다 확인한다.

```bash
kubectl get nodes -o wide
kubectl -n argocd get application
kubectl -n monitoring get pod -o wide
kubectl -n ai-apps get pod -o wide
kubectl -n ai-apps get ds safe-edge-image-prepull -o wide
kubectl -n monitoring get pvc
kubectl -n ai-apps get pvc
kubectl -n longhorn-system get volumes.longhorn.io -o wide
```

## 판정 원칙

- 노드 3개는 모두 `Ready`여야 한다.
- ArgoCD Application은 `Synced`와 `Healthy`여야 한다.
- `monitoring`, `ai-apps`의 핵심 Pod는 `Running`이어야 한다.
- Longhorn volume은 `healthy` 또는 의도한 복구 중 상태여야 한다.
- Failover/Failback 테스트 직후에는 데이터 공백과 중복 write 가능성을 함께 확인한다.

## Safe-Edge 기준선 점검

| 점검 항목 | 확인 방법 | 통과 기준 |
| --- | --- | --- |
| K3s 노드 | `kubectl get nodes -o wide` | master, worker1, worker2 모두 `Ready` |
| ArgoCD 앱 | `kubectl -n argocd get application` | `safe-edge-monitoring`, `safe-edge-ai-apps`가 `Synced/Healthy` |
| 모니터링 Pod | `kubectl -n monitoring get pod -o wide` | InfluxDB, Grafana, Prometheus 계열 Pod 정상 |
| AI 앱 Pod | `kubectl -n ai-apps get pod -o wide` | 대상 AI Pod가 정상 노드에서 `Running` |
| 이미지 prepull | `kubectl -n ai-apps get ds safe-edge-image-prepull -o wide` | worker1/worker2에 이미지 사전 적재 |
| PVC | `kubectl -n monitoring get pvc`, `kubectl -n ai-apps get pvc` | 필요한 PVC가 `Bound` |
| Longhorn | `kubectl -n longhorn-system get volumes.longhorn.io -o wide` | replica 상태 정상 |

## Grafana/InfluxDB 점검

Grafana는 `http://10.10.10.202`에서 확인한다.

| 패널 | 데이터 소스 | 기준 |
| --- | --- | --- |
| 현장 온도 | InfluxDB `environment_data.temperature` | 최근 값과 추세 표시 |
| 현장 습도 | InfluxDB `environment_data.humidity` | 최근 값과 추세 표시 |
| 현장 기압 | InfluxDB `environment_data.pressure` | 최근 값과 추세 표시 |
| 화재 감지 | InfluxDB `ai_detection.fire_detected` 최근 N개 평균 | 안전/주의/화재 |
| 넘어짐 감지 | InfluxDB `ai_detection.fallen_detected` 최근 N개 평균 | 안전/주의/넘어짐 |
| 굽힘 감지 | InfluxDB `ai_detection.bending_detected` 최근 N개 평균 | 안전/주의/굽힘 |
| 이상 소음 | InfluxDB `acoustic_detection.is_danger` 최근 N개 평균 | 안전/주의/필터링된 소리 레이블 |
| 노드 상태 | Prometheus dashboard `1860` | CPU, memory, disk, network 확인 |

최근 N개 기본값은 `LIMIT 10`으로 본다. Grafana 패널 Query의 InfluxQL에서 이 값을 조정하면 된다.

## 보존 정책 점검

- InfluxDB retention policy는 1일 보존 기준이다.
- Longhorn replica도 InfluxDB가 보존하는 데이터 범위만 복제한다.
- AI detect snapshot은 `/app/snapshots`에 저장되고 Longhorn PVC에 붙어 있다.
- `snapshot-cleanup` sidecar가 24시간이 지난 이미지 파일을 정리한다.

## Failover/Failback 점검

실제 장애 테스트는 `docs/ops/03_test_checklist.md`와 `docs/ops/09_failover_failback_test_results.md`를 기준으로 진행한다.

핵심 판정:

- worker2 장애 시 대상 Pod가 worker1로 이동하는가
- worker1 이동 후 하드웨어 입력이 유지되는가
- worker2 복구 후 failback 스크립트가 worker2 상태를 확인한 뒤에만 대상 Pod를 되돌리는가
- worker2가 이미 대상 Pod를 잡고 있으면 failback 스크립트가 실행되지 않는가
- failback 이후 InfluxDB 10초/1초 bucket 기준으로 데이터 공백과 중복 write 여부를 확인했는가

## 후속 Hub 확장 전 체크

아래 항목은 아직 현재 완료 범위가 아니다. `factory-a` 기준선이 안정적으로 유지된 뒤 진행한다.

- AWS EKS Hub 구성
- Tailscale 기반 Hub-Spoke 연결
- AWS IoT Core 및 S3 적재
- GitHub Actions/ECR 이미지 빌드 파이프라인
- `factory-b`, `factory-c` 테스트베드형 Spoke
- Risk Twin 대시보드

## 실패 시 먼저 볼 문서

- `docs/ops/00_quick_start.md`
- `docs/ops/01_safe_edge_bootstrap.md`
- `docs/ops/04_troubleshooting.md`
- `docs/ops/06_argocd_gitops.md`
- `docs/ops/07_grafana_dashboard.md`
- `docs/ops/08_data_retention.md`
- `docs/ops/09_failover_failback_test_results.md`
